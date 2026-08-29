from httpx import AsyncClient


async def _create_business(client: AsyncClient, headers: dict) -> str:
    response = await client.post(
        "/api/v1/businesses",
        headers=headers,
        json={"name": "CineMax Kochi", "business_type": "cinema", "city": "Kochi"},
    )
    return response.json()["id"]


async def test_new_business_starts_on_starter_trial(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="billing-owner-1", email="billing-owner1@example.com")
    business_id = await _create_business(client, headers)

    subscription_response = await client.get(f"/api/v1/businesses/{business_id}/billing/subscription", headers=headers)
    assert subscription_response.status_code == 200
    subscription = subscription_response.json()
    assert subscription["plan_id"] == "STARTER"
    assert subscription["state"] == "TRIAL"


async def test_list_plans_and_upgrade(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="billing-owner-2", email="billing-owner2@example.com")
    business_id = await _create_business(client, headers)

    plans_response = await client.get("/api/v1/billing/plans")
    assert plans_response.status_code == 200
    plan_ids = {p["id"] for p in plans_response.json()}
    assert plan_ids == {"STARTER", "GROWTH", "SCALE"}

    upgrade_response = await client.post(
        f"/api/v1/businesses/{business_id}/billing/subscription", headers=headers, json={"plan_id": "GROWTH"}
    )
    assert upgrade_response.status_code == 200
    assert upgrade_response.json()["plan_id"] == "GROWTH"


async def test_billing_requires_permission(client: AsyncClient, auth_headers):
    owner_headers = auth_headers(sub="billing-owner-3", email="billing-owner3@example.com")
    manager_headers = auth_headers(sub="billing-manager-3", email="billing-manager3@example.com")
    business_id = await _create_business(client, owner_headers)

    await client.post(
        f"/api/v1/businesses/{business_id}/staff",
        headers=owner_headers,
        json={"name": "Manager", "email": "billing-manager3@example.com", "role": "MANAGER"},
    )
    await client.get("/api/v1/me", headers=manager_headers)

    # MANAGER has no billing.manage permission.
    response = await client.get(f"/api/v1/businesses/{business_id}/billing/subscription", headers=manager_headers)
    assert response.status_code == 403
