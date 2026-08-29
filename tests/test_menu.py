from httpx import AsyncClient


async def _create_business(client: AsyncClient, headers: dict) -> str:
    response = await client.post(
        "/api/v1/businesses",
        headers=headers,
        json={"name": "Spice Garden", "business_type": "restaurant", "city": "Kochi"},
    )
    return response.json()["id"]


async def test_menu_category_and_item_crud(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="menu-owner-1", email="menu-owner1@example.com")
    business_id = await _create_business(client, headers)

    category_response = await client.post(
        f"/api/v1/businesses/{business_id}/menu/categories", headers=headers, json={"name": "Starters"}
    )
    assert category_response.status_code == 201
    category_id = category_response.json()["id"]

    item_response = await client.post(
        f"/api/v1/businesses/{business_id}/menu/items",
        headers=headers,
        json={
            "category_id": category_id,
            "name": "Paneer Tikka",
            "price": "249.00",
            "addons": [{"name": "Extra chutney", "price": "20.00"}],
        },
    )
    assert item_response.status_code == 201
    item = item_response.json()
    assert item["available"] is True
    assert item["addons"] == [{"name": "Extra chutney", "price": "20.00"}]

    toggle_response = await client.post(
        f"/api/v1/businesses/{business_id}/menu/items/{item['id']}/toggle", headers=headers
    )
    assert toggle_response.json()["available"] is False

    list_response = await client.get(f"/api/v1/businesses/{business_id}/menu/items", headers=headers)
    assert len(list_response.json()) == 1

    delete_response = await client.delete(
        f"/api/v1/businesses/{business_id}/menu/items/{item['id']}", headers=headers
    )
    assert delete_response.status_code == 204

    empty_list = await client.get(f"/api/v1/businesses/{business_id}/menu/items", headers=headers)
    assert empty_list.json() == []


async def test_staff_can_view_menu_but_not_manage_it(client: AsyncClient, auth_headers):
    owner_headers = auth_headers(sub="menu-owner-2", email="menu-owner2@example.com")
    staff_headers = auth_headers(sub="menu-staff-1", email="menu-staff1@example.com")
    business_id = await _create_business(client, owner_headers)

    invite_response = await client.post(
        f"/api/v1/businesses/{business_id}/staff",
        headers=owner_headers,
        json={"name": "Line Staff", "email": "menu-staff1@example.com", "role": "STAFF"},
    )
    assert invite_response.status_code == 201

    # First authenticated request as this email links the pending invite and
    # activates it (see get_current_user's just-in-time linking).
    me_response = await client.get("/api/v1/me", headers=staff_headers)
    assert me_response.json()["businesses"][0]["role"] == "STAFF"

    # STAFF has menu.view but not menu.manage (see ROLE_PERMISSIONS).
    view_response = await client.get(f"/api/v1/businesses/{business_id}/menu/items", headers=staff_headers)
    assert view_response.status_code == 200

    manage_response = await client.post(
        f"/api/v1/businesses/{business_id}/menu/categories", headers=staff_headers, json={"name": "Mains"}
    )
    assert manage_response.status_code == 403
