import time

import pytest
from httpx import ASGITransport, AsyncClient
from jose import jwk, jwt

from app.core import security
from app.core.config import get_settings
from app.main import app


@pytest.fixture
def es256_keypair():
    """A throwaway EC P-256 keypair, exported as a JWK, mimicking what a real
    Supabase project's JWKS endpoint publishes (see the ES256 keys returned
    by <project>.supabase.co/auth/v1/.well-known/jwks.json). Only the public
    key goes into the published JWK — a JWKS endpoint never hands out `d`."""
    from cryptography.hazmat.primitives.asymmetric import ec

    private_key = ec.generate_private_key(ec.SECP256R1())
    public_jwk = jwk.construct(private_key.public_key(), algorithm="ES256").to_dict()
    public_jwk["kid"] = "test-kid-1"
    public_jwk["use"] = "sig"
    return private_key, public_jwk


@pytest.fixture
def jwks_server(monkeypatch, es256_keypair):
    _private_key, public_jwk = es256_keypair
    monkeypatch.setattr(security, "_fetch_jwks", lambda jwks_url: [public_jwk])
    security._jwks_cache.clear()
    get_settings().supabase_url = "https://fake-project.supabase.co"
    yield public_jwk
    get_settings().supabase_url = ""
    security._jwks_cache.clear()


def make_es256_token(*, private_key, kid: str, sub: str, email: str, name: str = "") -> str:
    headers = {"kid": kid}
    payload = {
        "sub": sub,
        "email": email,
        "user_metadata": {"name": name},
        "exp": int(time.time()) + 3600,
    }
    return jwt.encode(payload, private_key, algorithm="ES256", headers=headers)


async def test_jwks_verified_token_is_accepted(client: AsyncClient, jwks_server, es256_keypair):
    private_key, public_jwk = es256_keypair
    token = make_es256_token(
        private_key=private_key, kid=public_jwk["kid"], sub="jwks-user-1", email="jwks-user1@example.com", name="JWKS User"
    )

    response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json()["user"]["email"] == "jwks-user1@example.com"


async def test_jwks_token_with_wrong_key_is_rejected(client: AsyncClient, jwks_server):
    from cryptography.hazmat.primitives.asymmetric import ec

    wrong_key = ec.generate_private_key(ec.SECP256R1())
    # Signed by a key that doesn't match any kid published in the (fake) JWKS.
    token = jwt.encode(
        {"sub": "attacker", "email": "attacker@example.com", "exp": int(time.time()) + 3600},
        wrong_key,
        algorithm="ES256",
        headers={"kid": "not-a-real-kid"},
    )

    response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 401


async def test_jwks_fetch_failure_returns_503(client: AsyncClient, monkeypatch, es256_keypair):
    private_key, public_jwk = es256_keypair

    def _raise(jwks_url):
        import httpx

        raise httpx.ConnectError("no route to host")

    monkeypatch.setattr(security, "_fetch_jwks", _raise)
    security._jwks_cache.clear()
    get_settings().supabase_url = "https://fake-project-unreachable.supabase.co"
    try:
        token = make_es256_token(
            private_key=private_key, kid=public_jwk["kid"], sub="u", email="u@example.com"
        )
        response = await client.get("/api/v1/me", headers={"Authorization": f"Bearer {token}"})
        assert response.status_code == 503
    finally:
        get_settings().supabase_url = ""
        security._jwks_cache.clear()
