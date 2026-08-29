import json

from httpx import AsyncClient


async def test_payment_config_reflects_provider_configuration(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="pay-owner-1", email="pay-owner1@example.com")
    business_id = (
        await client.post(
            "/api/v1/businesses", headers=headers, json={"name": "Lounge 9", "business_type": "lounge", "city": "Kochi"}
        )
    ).json()["id"]

    # No RAZORPAY_KEY_ID/SECRET set in the test environment -> not configured.
    response = await client.get(f"/api/v1/businesses/{business_id}/payments/config", headers=headers)
    assert response.status_code == 200
    assert response.json()["status"] == "ACTION_REQUIRED"


async def test_creating_payment_without_provider_configured_returns_503(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="pay-owner-2", email="pay-owner2@example.com")
    business_id = (
        await client.post(
            "/api/v1/businesses", headers=headers, json={"name": "Lounge 10", "business_type": "lounge", "city": "Kochi"}
        )
    ).json()["id"]
    category_id = (
        await client.post(f"/api/v1/businesses/{business_id}/menu/categories", headers=headers, json={"name": "Drinks"})
    ).json()["id"]
    item = (
        await client.post(
            f"/api/v1/businesses/{business_id}/menu/items",
            headers=headers,
            json={"category_id": category_id, "name": "Mocktail", "price": "150.00"},
        )
    ).json()
    area_id = (
        await client.post(f"/api/v1/businesses/{business_id}/service/areas", headers=headers, json={"name": "Bar"})
    ).json()["id"]
    point = (
        await client.post(
            f"/api/v1/businesses/{business_id}/service/points",
            headers=headers,
            json={"area_id": area_id, "code": "B1", "kind": "COUNTER"},
        )
    ).json()
    order = (
        await client.post(
            f"/api/v1/public/businesses/{business_id}/orders",
            json={"service_point_id": point["id"], "customer_phone": "9555555555", "items": [{"menu_item_id": item["id"], "quantity": 1}]},
        )
    ).json()

    # No fake_payment_provider fixture here -> real build_payment_provider()
    # runs, sees no credentials, and the dependency turns that into a 503.
    response = await client.post(f"/api/v1/public/orders/{order['id']}/payment", params={"phone": "9555555555"})
    assert response.status_code == 503


async def test_webhook_rejects_invalid_signature_and_is_idempotent(client: AsyncClient, fake_payment_provider):
    payload = {"event": "payment.captured", "payload": {"payment": {"entity": {"id": "pay_x", "order_id": "order_x"}}}}
    body = json.dumps(payload)

    bad_response = await client.post(
        "/api/v1/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": "wrong-signature"}
    )
    assert bad_response.status_code == 400

    good_response = await client.post(
        "/api/v1/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": "valid-webhook-signature"}
    )
    assert good_response.status_code == 200

    # Redelivering the exact same payload is a no-op, not a second attempt to
    # process — this should still return 200 rather than erroring.
    replay_response = await client.post(
        "/api/v1/webhooks/razorpay", content=body, headers={"X-Razorpay-Signature": "valid-webhook-signature"}
    )
    assert replay_response.status_code == 200
