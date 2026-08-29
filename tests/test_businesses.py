from httpx import AsyncClient
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.user import User


async def test_create_business_makes_caller_the_owner(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="owner-1", email="owner1@example.com")

    create_response = await client.post(
        "/api/v1/businesses",
        headers=headers,
        json={"name": "Spice Garden", "business_type": "restaurant", "city": "Kochi", "emoji": "🍽️"},
    )
    assert create_response.status_code == 201
    business = create_response.json()
    assert business["name"] == "Spice Garden"
    assert business["subscription_state"] == "TRIAL"

    me_response = await client.get("/api/v1/me", headers=headers)
    me = me_response.json()
    assert len(me["businesses"]) == 1
    assert me["businesses"][0]["role"] == "OWNER"
    assert me["businesses"][0]["business"]["id"] == business["id"]


async def test_tenant_isolation_a_user_cannot_see_another_users_business(client: AsyncClient, auth_headers):
    owner_headers = auth_headers(sub="owner-2", email="owner2@example.com")
    stranger_headers = auth_headers(sub="stranger-1", email="stranger1@example.com")

    create_response = await client.post(
        "/api/v1/businesses",
        headers=owner_headers,
        json={"name": "Private Cafe", "business_type": "cafe", "city": "Delhi"},
    )
    business_id = create_response.json()["id"]

    # The owner can fetch it directly.
    owner_get = await client.get(f"/api/v1/businesses/{business_id}", headers=owner_headers)
    assert owner_get.status_code == 200

    # A different, unrelated authenticated user cannot.
    stranger_get = await client.get(f"/api/v1/businesses/{business_id}", headers=stranger_headers)
    assert stranger_get.status_code == 403

    # And it doesn't show up in the stranger's own business list.
    stranger_list = await client.get("/api/v1/businesses", headers=stranger_headers)
    assert stranger_list.json() == []


async def test_platform_admin_sees_every_business(client: AsyncClient, auth_headers, db_session: AsyncSession):
    owner_headers = auth_headers(sub="owner-3", email="owner3@example.com")
    admin_headers = auth_headers(sub="admin-1", email="admin1@example.com")

    await client.post(
        "/api/v1/businesses",
        headers=owner_headers,
        json={"name": "Someone Else's Business", "business_type": "bar", "city": "Mumbai"},
    )

    # Provision the admin user via a first request, then promote them.
    await client.get("/api/v1/me", headers=admin_headers)
    admin_user = (
        await db_session.execute(select(User).where(User.email == "admin1@example.com"))
    ).scalar_one()
    admin_user.is_platform_admin = True
    await db_session.commit()

    admin_list = await client.get("/api/v1/businesses", headers=admin_headers)
    assert len(admin_list.json()) == 1

    admin_get = await client.get(
        f"/api/v1/businesses/{admin_list.json()[0]['id']}", headers=admin_headers
    )
    assert admin_get.status_code == 200
