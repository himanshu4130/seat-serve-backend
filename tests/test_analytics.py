from httpx import AsyncClient


async def test_analytics_summary_reflects_real_orders(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="analytics-owner-1", email="analytics-owner1@example.com")
    business_id = (
        await client.post(
            "/api/v1/businesses", headers=headers, json={"name": "Malabar Kitchen", "business_type": "restaurant", "city": "Kochi"}
        )
    ).json()["id"]
    category_id = (
        await client.post(f"/api/v1/businesses/{business_id}/menu/categories", headers=headers, json={"name": "Mains"})
    ).json()["id"]
    item = (
        await client.post(
            f"/api/v1/businesses/{business_id}/menu/items",
            headers=headers,
            json={"category_id": category_id, "name": "Fish Curry", "price": "200.00"},
        )
    ).json()
    area_id = (
        await client.post(f"/api/v1/businesses/{business_id}/service/areas", headers=headers, json={"name": "Hall"})
    ).json()["id"]
    point = (
        await client.post(
            f"/api/v1/businesses/{business_id}/service/points",
            headers=headers,
            json={"area_id": area_id, "code": "T1", "kind": "TABLE"},
        )
    ).json()

    for phone in ["9000000001", "9000000002"]:
        order = (
            await client.post(
                f"/api/v1/public/businesses/{business_id}/orders",
                json={
                    "service_point_id": point["id"],
                    "customer_phone": phone,
                    "items": [{"menu_item_id": item["id"], "quantity": 1}],
                },
            )
        ).json()
        # Analytics revenue only counts paid orders — mark paid directly via
        # the order-status endpoints isn't possible for `paid`, so simulate
        # payment isn't wired here; assert order_count still reflects all orders.
        assert order["status"] == "NEW"

    summary_response = await client.get(f"/api/v1/businesses/{business_id}/analytics/summary", headers=headers)
    assert summary_response.status_code == 200
    summary = summary_response.json()
    assert summary["order_count"] == 2
    # Neither order is paid yet, so revenue/AOV are zero even though 2 orders
    # exist — but top_products reflects demand (what was ordered), not money
    # collected, so it still counts both.
    assert summary["revenue"] == "0"
    assert summary["average_order_value"] == "0"
    assert summary["top_products"][0] == {"name": "Fish Curry", "quantity_sold": 2, "revenue": "400.00"}
    # hourly's revenue column must agree with the top-level revenue figure
    # (paid orders only) even though order_count counts every order.
    assert summary["hourly"][0]["order_count"] == 2
    assert summary["hourly"][0]["revenue"] == "0"


async def test_analytics_requires_reports_view_permission(client: AsyncClient, auth_headers):
    owner_headers = auth_headers(sub="analytics-owner-2", email="analytics-owner2@example.com")
    kitchen_headers = auth_headers(sub="analytics-kitchen-2", email="analytics-kitchen2@example.com")
    business_id = (
        await client.post(
            "/api/v1/businesses", headers=owner_headers, json={"name": "Ocean View", "business_type": "resort", "city": "Kochi"}
        )
    ).json()["id"]

    await client.post(
        f"/api/v1/businesses/{business_id}/staff",
        headers=owner_headers,
        json={"name": "Kitchen", "email": "analytics-kitchen2@example.com", "role": "KITCHEN"},
    )
    await client.get("/api/v1/me", headers=kitchen_headers)

    response = await client.get(f"/api/v1/businesses/{business_id}/analytics/summary", headers=kitchen_headers)
    assert response.status_code == 403
