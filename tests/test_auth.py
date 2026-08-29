from httpx import AsyncClient


async def test_unauthenticated_request_is_rejected(client: AsyncClient):
    response = await client.get("/api/v1/me")
    assert response.status_code == 401


async def test_first_request_just_in_time_provisions_user(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="supabase-user-1", email="owner@example.com", name="Ada Owner")

    response = await client.get("/api/v1/me", headers=headers)

    assert response.status_code == 200
    body = response.json()
    assert body["user"]["email"] == "owner@example.com"
    assert body["user"]["name"] == "Ada Owner"
    assert body["user"]["is_platform_admin"] is False
    assert body["businesses"] == []


async def test_same_token_maps_back_to_the_same_user(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="supabase-user-2", email="repeat@example.com")

    first = await client.get("/api/v1/me", headers=headers)
    second = await client.get("/api/v1/me", headers=headers)

    assert first.json()["user"]["id"] == second.json()["user"]["id"]


async def test_invalid_token_is_rejected(client: AsyncClient):
    response = await client.get("/api/v1/me", headers={"Authorization": "Bearer not-a-real-token"})
    assert response.status_code == 401
