from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from httpx import AsyncClient

from app.models.user import User


async def _promote_to_platform_admin(db_session: AsyncSession, email: str) -> None:
    user = (await db_session.execute(select(User).where(User.email == email))).scalar_one()
    user.is_platform_admin = True
    await db_session.commit()


async def test_platform_routes_require_platform_admin(client: AsyncClient, auth_headers):
    owner_headers = auth_headers(sub="platform-owner-1", email="platform-owner1@example.com")
    await client.post(
        "/api/v1/businesses", headers=owner_headers, json={"name": "Regular Biz", "business_type": "cafe", "city": "Kochi"}
    )
    response = await client.get("/api/v1/platform/tenants", headers=owner_headers)
    assert response.status_code == 403


async def test_platform_admin_sees_rollups(client: AsyncClient, auth_headers, db_session: AsyncSession):
    owner_headers = auth_headers(sub="platform-owner-2", email="platform-owner2@example.com")
    admin_headers = auth_headers(sub="platform-admin-2", email="platform-admin2@example.com")

    await client.post(
        "/api/v1/businesses", headers=owner_headers, json={"name": "Someone's Venue", "business_type": "cafe", "city": "Kochi"}
    )
    await client.get("/api/v1/me", headers=admin_headers)
    await _promote_to_platform_admin(db_session, "platform-admin2@example.com")

    tenants_response = await client.get("/api/v1/platform/tenants", headers=admin_headers)
    assert tenants_response.status_code == 200
    assert len(tenants_response.json()) >= 1

    businesses_response = await client.get("/api/v1/platform/businesses", headers=admin_headers)
    assert businesses_response.status_code == 200
    assert any(b["name"] == "Someone's Venue" for b in businesses_response.json())

    analytics_response = await client.get("/api/v1/platform/analytics", headers=admin_headers)
    assert analytics_response.status_code == 200
    assert analytics_response.json()["business_count"] >= 1
