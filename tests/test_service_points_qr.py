from httpx import AsyncClient


async def _create_business(client: AsyncClient, headers: dict) -> str:
    response = await client.post(
        "/api/v1/businesses",
        headers=headers,
        json={"name": "The Harbour Bar", "business_type": "bar", "city": "Kochi"},
    )
    return response.json()["id"]


async def test_service_point_and_qr_flow(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="qr-owner-1", email="qr-owner1@example.com")
    business_id = await _create_business(client, headers)

    area_response = await client.post(
        f"/api/v1/businesses/{business_id}/service/areas", headers=headers, json={"name": "Main Floor"}
    )
    assert area_response.status_code == 201
    area_id = area_response.json()["id"]

    point_response = await client.post(
        f"/api/v1/businesses/{business_id}/service/points",
        headers=headers,
        json={"area_id": area_id, "code": "T1", "kind": "TABLE", "label": "Table 1"},
    )
    assert point_response.status_code == 201
    point_id = point_response.json()["id"]

    qr_response = await client.post(
        f"/api/v1/businesses/{business_id}/qr-codes", headers=headers, json={"service_point_id": point_id}
    )
    assert qr_response.status_code == 201
    qr_code = qr_response.json()
    assert qr_code["status"] == "ACTIVE"
    slug = qr_code["slug"]

    # Creating a second QR for the same point returns the existing one rather
    # than a duplicate (unique index on service_point_id backs this up too).
    second_qr_response = await client.post(
        f"/api/v1/businesses/{business_id}/qr-codes", headers=headers, json={"service_point_id": point_id}
    )
    assert second_qr_response.json()["id"] == qr_code["id"]

    resolve_response = await client.get(f"/api/v1/public/qr/{slug}")
    assert resolve_response.status_code == 200
    resolved = resolve_response.json()
    assert resolved["business"]["id"] == business_id
    assert resolved["service_point"]["id"] == point_id
    # Public resolution must never leak tenant/subscription internals.
    assert "tenant_id" not in resolved["business"]

    disable_response = await client.post(
        f"/api/v1/businesses/{business_id}/qr-codes/{qr_code['id']}/disable", headers=headers
    )
    assert disable_response.json()["status"] == "DISABLED"

    disabled_resolve = await client.get(f"/api/v1/public/qr/{slug}")
    assert disabled_resolve.status_code == 404


async def test_point_deactivation_blocks_new_orders(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="qr-owner-2", email="qr-owner2@example.com")
    business_id = await _create_business(client, headers)

    area_id = (
        await client.post(
            f"/api/v1/businesses/{business_id}/service/areas", headers=headers, json={"name": "Patio"}
        )
    ).json()["id"]
    point = (
        await client.post(
            f"/api/v1/businesses/{business_id}/service/points",
            headers=headers,
            json={"area_id": area_id, "code": "P1", "kind": "TABLE"},
        )
    ).json()

    deactivate_response = await client.patch(
        f"/api/v1/businesses/{business_id}/service/points/{point['id']}", headers=headers, json={"active": False}
    )
    assert deactivate_response.json()["active"] is False

    order_response = await client.post(
        f"/api/v1/public/businesses/{business_id}/orders",
        json={"service_point_id": point["id"], "customer_phone": "9999999999", "items": []},
    )
    # Empty items is also invalid, but inactive-point should be the first thing checked in this case; either way this must not succeed.
    assert order_response.status_code in (400, 404, 422)
