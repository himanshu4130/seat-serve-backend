from httpx import AsyncClient


async def _create_business(client: AsyncClient, headers: dict) -> str:
    response = await client.post(
        "/api/v1/businesses",
        headers=headers,
        json={"name": "Ocean View Resort", "business_type": "resort", "city": "Kochi"},
    )
    return response.json()["id"]


async def test_invite_flow_and_activation_on_first_login(client: AsyncClient, auth_headers):
    owner_headers = auth_headers(sub="staff-owner-1", email="staff-owner1@example.com")
    manager_headers = auth_headers(sub="staff-manager-1", email="staff-manager1@example.com")
    business_id = await _create_business(client, owner_headers)

    invite_response = await client.post(
        f"/api/v1/businesses/{business_id}/staff",
        headers=owner_headers,
        json={"name": "New Manager", "email": "staff-manager1@example.com", "role": "MANAGER", "phone": "9000000001"},
    )
    assert invite_response.status_code == 201
    invited = invite_response.json()
    assert invited["status"] == "INVITED"
    assert invited["user_id"] is None

    list_response = await client.get(f"/api/v1/businesses/{business_id}/staff", headers=owner_headers)
    assert len(list_response.json()) == 2  # the owner (auto-created) + the invite

    # The invited manager's first authenticated request should link + activate them.
    me_response = await client.get("/api/v1/me", headers=manager_headers)
    assert me_response.json()["businesses"][0]["role"] == "MANAGER"

    list_after = await client.get(f"/api/v1/businesses/{business_id}/staff", headers=owner_headers)
    manager_row = next(s for s in list_after.json() if s["email"] == "staff-manager1@example.com")
    assert manager_row["status"] == "ACTIVE"
    assert manager_row["user_id"] is not None


async def test_cannot_invite_same_email_twice(client: AsyncClient, auth_headers):
    owner_headers = auth_headers(sub="staff-owner-2", email="staff-owner2@example.com")
    business_id = await _create_business(client, owner_headers)

    payload = {"name": "Dup", "email": "dup-staff@example.com", "role": "STAFF"}
    first = await client.post(f"/api/v1/businesses/{business_id}/staff", headers=owner_headers, json=payload)
    assert first.status_code == 201

    second = await client.post(f"/api/v1/businesses/{business_id}/staff", headers=owner_headers, json=payload)
    assert second.status_code == 409


async def test_cannot_disable_the_last_owner(client: AsyncClient, auth_headers):
    owner_headers = auth_headers(sub="staff-owner-3", email="staff-owner3@example.com")
    co_owner_headers = auth_headers(sub="staff-co-owner-3", email="co-owner3@example.com")
    business_id = await _create_business(client, owner_headers)

    staff_list = (await client.get(f"/api/v1/businesses/{business_id}/staff", headers=owner_headers)).json()
    owner_row = staff_list[0]
    assert owner_row["role"] == "OWNER"

    disable_response = await client.patch(
        f"/api/v1/businesses/{business_id}/staff/{owner_row['id']}", headers=owner_headers, json={"status": "DISABLED"}
    )
    assert disable_response.status_code == 400

    # An invited-but-not-yet-accepted co-owner doesn't count as an active
    # owner — only after they actually log in should the guard release.
    await client.post(
        f"/api/v1/businesses/{business_id}/staff",
        headers=owner_headers,
        json={"name": "Co-owner", "email": "co-owner3@example.com", "role": "OWNER"},
    )
    still_blocked = await client.patch(
        f"/api/v1/businesses/{business_id}/staff/{owner_row['id']}", headers=owner_headers, json={"status": "DISABLED"}
    )
    assert still_blocked.status_code == 400

    await client.get("/api/v1/me", headers=co_owner_headers)  # activates the invite

    second_disable = await client.patch(
        f"/api/v1/businesses/{business_id}/staff/{owner_row['id']}", headers=owner_headers, json={"status": "DISABLED"}
    )
    assert second_disable.status_code == 200


async def test_disabled_staff_loses_access(client: AsyncClient, auth_headers):
    owner_headers = auth_headers(sub="staff-owner-4", email="staff-owner4@example.com")
    staff_headers = auth_headers(sub="staff-member-4", email="staff-member4@example.com")
    business_id = await _create_business(client, owner_headers)

    await client.post(
        f"/api/v1/businesses/{business_id}/staff",
        headers=owner_headers,
        json={"name": "Member", "email": "staff-member4@example.com", "role": "STAFF"},
    )
    await client.get("/api/v1/me", headers=staff_headers)  # activates the invite

    staff_row = next(
        s
        for s in (await client.get(f"/api/v1/businesses/{business_id}/staff", headers=owner_headers)).json()
        if s["email"] == "staff-member4@example.com"
    )
    await client.patch(
        f"/api/v1/businesses/{business_id}/staff/{staff_row['id']}", headers=owner_headers, json={"status": "DISABLED"}
    )

    denied = await client.get(f"/api/v1/businesses/{business_id}/menu/items", headers=staff_headers)
    assert denied.status_code == 403
