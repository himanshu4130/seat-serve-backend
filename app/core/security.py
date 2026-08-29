import time

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.core.db import get_db
from app.models.user import User
from app.repositories.staff_role_repository import StaffRoleRepository
from app.repositories.user_repository import UserRepository

_bearer_scheme = HTTPBearer(auto_error=False)

_JWKS_CACHE_TTL_SECONDS = 3600
_jwks_cache: dict[str, tuple[float, list[dict]]] = {}


def _fetch_jwks(jwks_url: str) -> list[dict]:
    """Separated out so tests can monkeypatch this one function instead of
    mocking the network — real fetch/cache logic stays exercised as-is."""
    response = httpx.get(jwks_url, timeout=10.0)
    response.raise_for_status()
    return response.json()["keys"]


def _get_jwks(jwks_url: str, *, force_refresh: bool = False) -> list[dict]:
    cached = _jwks_cache.get(jwks_url)
    if not force_refresh and cached is not None and time.time() - cached[0] < _JWKS_CACHE_TTL_SECONDS:
        return cached[1]
    keys = _fetch_jwks(jwks_url)
    _jwks_cache[jwks_url] = (time.time(), keys)
    return keys


def _decode_via_jwks(token: str, *, supabase_url: str) -> dict:
    jwks_url = f"{supabase_url.rstrip('/')}/auth/v1/.well-known/jwks.json"
    unverified_header = jwt.get_unverified_header(token)
    kid = unverified_header.get("kid")

    keys = _get_jwks(jwks_url)
    key = next((k for k in keys if k.get("kid") == kid), None)
    if key is None:
        # The signing key may have rotated since we last cached — refresh
        # once before giving up, rather than staying wrong for an hour.
        keys = _get_jwks(jwks_url, force_refresh=True)
        key = next((k for k in keys if k.get("kid") == kid), None)
    if key is None:
        raise JWTError(f"Unknown signing key id: {kid}")

    return jwt.decode(token, key, algorithms=[key.get("alg", "ES256")], options={"verify_aud": False})


def decode_supabase_jwt(token: str) -> dict:
    """Verify a Supabase-issued access token.

    Projects created since Supabase's move to per-project asymmetric signing
    keys (the default today) publish a JWKS at
    `{supabase_url}/auth/v1/.well-known/jwks.json` — verify against that when
    `supabase_url` is configured. Older projects (or local dev/tests, with no
    network available) fall back to the legacy shared HS256 secret.
    """
    settings = get_settings()
    try:
        if settings.supabase_url:
            return _decode_via_jwks(token, supabase_url=settings.supabase_url)
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            options={"verify_aud": False},
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid or expired token"
        ) from exc
    except httpx.HTTPError as exc:
        # The token itself may well be fine — we just couldn't reach Supabase
        # to fetch its signing keys. That's a 503, not "your token is bad".
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Could not verify token (JWKS unreachable)"
        ) from exc


async def get_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(_bearer_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    if credentials is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")

    payload = decode_supabase_jwt(credentials.credentials)
    supabase_user_id = payload.get("sub")
    email = payload.get("email")
    if not supabase_user_id or not email:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token missing subject/email")

    users = UserRepository(db)
    user = await users.get_by_supabase_id(supabase_user_id)
    if user is None:
        # Just-in-time provisioning: Supabase Auth owns signup, we only mirror
        # the identity into our own table the first time we see it.
        name = payload.get("user_metadata", {}).get("name", "") or email.split("@")[0]
        user = await users.create(supabase_user_id=supabase_user_id, email=email, name=name)

        # A staff invite may have been created for this email before the
        # person ever signed in — link it now so their role becomes active.
        staff_roles = StaffRoleRepository(db)
        for invite in await staff_roles.list_pending_invites_for_email(email):
            await staff_roles.link_user(invite, user_id=user.id)
    return user
