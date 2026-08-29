from httpx import AsyncClient


async def _setup_orderable_business(client: AsyncClient, headers: dict) -> dict:
    business_id = (
        await client.post(
            "/api/v1/businesses", headers=headers, json={"name": "Malabar Kitchen", "business_type": "restaurant", "city": "Kochi"}
        )
    ).json()["id"]
    category_id = (
        await client.post(
            f"/api/v1/businesses/{business_id}/menu/categories", headers=headers, json={"name": "Mains"}
        )
    ).json()["id"]
    item = (
        await client.post(
            f"/api/v1/businesses/{business_id}/menu/items",
            headers=headers,
            json={
                "category_id": category_id,
                "name": "Chicken Biryani",
                "price": "300.00",
                "addons": [{"name": "Extra Raita", "price": "30.00"}],
            },
        )
    ).json()
    area_id = (
        await client.post(
            f"/api/v1/businesses/{business_id}/service/areas", headers=headers, json={"name": "Main Hall"}
        )
    ).json()["id"]
    point = (
        await client.post(
            f"/api/v1/businesses/{business_id}/service/points",
            headers=headers,
            json={"area_id": area_id, "code": "T7", "kind": "TABLE", "label": "Table 7"},
        )
    ).json()
    return {"business_id": business_id, "item": item, "point": point}


async def test_create_order_recomputes_price_server_side(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="order-owner-1", email="order-owner1@example.com")
    setup = await _setup_orderable_business(client, headers)

    order_response = await client.post(
        f"/api/v1/public/businesses/{setup['business_id']}/orders",
        json={
            "service_point_id": setup["point"]["id"],
            "customer_phone": "9876543210",
            "items": [
                {"menu_item_id": setup["item"]["id"], "quantity": 2, "addon_names": ["Extra Raita"]}
            ],
        },
    )
    assert order_response.status_code == 201
    order = order_response.json()
    # (300 + 30) * 2 = 660 subtotal; default tax_rate_bp is 1800 (18%) -> 118.80 tax.
    assert order["subtotal"] == "660.00"
    assert order["tax_amount"] == "118.80"
    assert order["total"] == "778.80"
    assert order["status"] == "NEW"
    assert order["paid"] is False


async def test_create_order_rejects_client_supplied_price_tampering(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="order-owner-2", email="order-owner2@example.com")
    setup = await _setup_orderable_business(client, headers)

    # No `price` field is even accepted in OrderItemCreate — only ids/qty/addon
    # names — so there is nothing for a malicious client to override.
    order_response = await client.post(
        f"/api/v1/public/businesses/{setup['business_id']}/orders",
        json={
            "service_point_id": setup["point"]["id"],
            "customer_phone": "9876543210",
            "items": [{"menu_item_id": setup["item"]["id"], "quantity": 1, "price": "1.00"}],
        },
    )
    assert order_response.status_code == 201
    assert order_response.json()["subtotal"] == "300.00"


async def test_order_status_flow_and_invalid_transition(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="order-owner-3", email="order-owner3@example.com")
    setup = await _setup_orderable_business(client, headers)

    order = (
        await client.post(
            f"/api/v1/public/businesses/{setup['business_id']}/orders",
            json={
                "service_point_id": setup["point"]["id"],
                "customer_phone": "9876543211",
                "items": [{"menu_item_id": setup["item"]["id"], "quantity": 1}],
            },
        )
    ).json()

    advance1 = await client.post(
        f"/api/v1/businesses/{setup['business_id']}/orders/{order['id']}/advance", headers=headers
    )
    assert advance1.json()["status"] == "ACCEPTED"

    # Can't skip straight to DELIVERED.
    skip_response = await client.patch(
        f"/api/v1/businesses/{setup['business_id']}/orders/{order['id']}/status",
        headers=headers,
        json={"status": "DELIVERED"},
    )
    assert skip_response.status_code == 400

    for expected in ["PREPARING", "READY", "OUT_FOR_DELIVERY", "DELIVERED"]:
        response = await client.post(
            f"/api/v1/businesses/{setup['business_id']}/orders/{order['id']}/advance", headers=headers
        )
        assert response.json()["status"] == expected

    # Nothing comes after DELIVERED via advance().
    final_advance = await client.post(
        f"/api/v1/businesses/{setup['business_id']}/orders/{order['id']}/advance", headers=headers
    )
    assert final_advance.status_code == 400


async def test_customer_order_lookup_is_phone_scoped(client: AsyncClient, auth_headers):
    headers = auth_headers(sub="order-owner-4", email="order-owner4@example.com")
    setup = await _setup_orderable_business(client, headers)

    order = (
        await client.post(
            f"/api/v1/public/businesses/{setup['business_id']}/orders",
            json={
                "service_point_id": setup["point"]["id"],
                "customer_phone": "9111111111",
                "items": [{"menu_item_id": setup["item"]["id"], "quantity": 1}],
            },
        )
    ).json()

    own_lookup = await client.get(f"/api/v1/public/orders/{order['id']}", params={"phone": "9111111111"})
    assert own_lookup.status_code == 200

    wrong_phone_lookup = await client.get(f"/api/v1/public/orders/{order['id']}", params={"phone": "9000000000"})
    assert wrong_phone_lookup.status_code == 404


async def test_order_payment_create_verify_and_refund(client: AsyncClient, auth_headers, fake_payment_provider):
    headers = auth_headers(sub="order-owner-5", email="order-owner5@example.com")
    setup = await _setup_orderable_business(client, headers)

    order = (
        await client.post(
            f"/api/v1/public/businesses/{setup['business_id']}/orders",
            json={
                "service_point_id": setup["point"]["id"],
                "customer_phone": "9222222222",
                "items": [{"menu_item_id": setup["item"]["id"], "quantity": 1}],
            },
        )
    ).json()

    create_payment = await client.post(
        f"/api/v1/public/orders/{order['id']}/payment", params={"phone": "9222222222"}
    )
    assert create_payment.status_code == 200
    payment = create_payment.json()
    assert payment["provider_order_id"] == "order_fake_1"
    assert payment["key_id"] == "rzp_test_key"

    verify_response = await client.post(
        "/api/v1/public/payments/verify",
        json={
            "transaction_id": payment["transaction_id"],
            "provider_payment_id": "pay_fake_1",
            "provider_signature": f"valid:{payment['provider_order_id']}:pay_fake_1",
        },
    )
    assert verify_response.status_code == 200
    assert verify_response.json()["status"] == "SUCCESS"

    order_after_payment = await client.get(
        f"/api/v1/businesses/{setup['business_id']}/orders/{order['id']}", headers=headers
    )
    assert order_after_payment.json()["paid"] is True

    # A replayed bad-signature verify on this *same, already-settled*
    # transaction must be a no-op, never a downgrade back to FAILED.
    replay_bad_verify = await client.post(
        "/api/v1/public/payments/verify",
        json={
            "transaction_id": payment["transaction_id"],
            "provider_payment_id": "pay_fake_1",
            "provider_signature": "not-the-right-signature",
        },
    )
    assert replay_bad_verify.status_code == 200
    assert replay_bad_verify.json()["status"] == "SUCCESS"

    # Walk the order to DELIVERED so a refund is a valid transition.
    for _ in range(5):
        await client.post(f"/api/v1/businesses/{setup['business_id']}/orders/{order['id']}/advance", headers=headers)

    refund_response = await client.post(
        f"/api/v1/businesses/{setup['business_id']}/orders/{order['id']}/refund",
        headers=headers,
        json={"reason": "Customer changed their mind"},
    )
    assert refund_response.status_code == 200
    assert refund_response.json()["status"] == "PROCESSED"

    refunded_order = await client.get(
        f"/api/v1/businesses/{setup['business_id']}/orders/{order['id']}", headers=headers
    )
    assert refunded_order.json()["status"] == "REFUNDED"


async def test_verify_payment_rejects_bad_signature_on_first_attempt(
    client: AsyncClient, auth_headers, fake_payment_provider
):
    headers = auth_headers(sub="order-owner-5b", email="order-owner5b@example.com")
    setup = await _setup_orderable_business(client, headers)

    order = (
        await client.post(
            f"/api/v1/public/businesses/{setup['business_id']}/orders",
            json={
                "service_point_id": setup["point"]["id"],
                "customer_phone": "9222222223",
                "items": [{"menu_item_id": setup["item"]["id"], "quantity": 1}],
            },
        )
    ).json()
    payment = (
        await client.post(f"/api/v1/public/orders/{order['id']}/payment", params={"phone": "9222222223"})
    ).json()

    bad_verify = await client.post(
        "/api/v1/public/payments/verify",
        json={
            "transaction_id": payment["transaction_id"],
            "provider_payment_id": "pay_fake_bad",
            "provider_signature": "not-the-right-signature",
        },
    )
    assert bad_verify.status_code == 400

    order_after = await client.get(
        f"/api/v1/businesses/{setup['business_id']}/orders/{order['id']}", headers=headers
    )
    assert order_after.json()["paid"] is False


async def test_cannot_create_payment_for_already_paid_order(client: AsyncClient, auth_headers, fake_payment_provider):
    headers = auth_headers(sub="order-owner-6", email="order-owner6@example.com")
    setup = await _setup_orderable_business(client, headers)

    order = (
        await client.post(
            f"/api/v1/public/businesses/{setup['business_id']}/orders",
            json={
                "service_point_id": setup["point"]["id"],
                "customer_phone": "9333333333",
                "items": [{"menu_item_id": setup["item"]["id"], "quantity": 1}],
            },
        )
    ).json()

    payment = (
        await client.post(f"/api/v1/public/orders/{order['id']}/payment", params={"phone": "9333333333"})
    ).json()
    await client.post(
        "/api/v1/public/payments/verify",
        json={
            "transaction_id": payment["transaction_id"],
            "provider_payment_id": "pay_fake_x",
            "provider_signature": f"valid:{payment['provider_order_id']}:pay_fake_x",
        },
    )

    second_attempt = await client.post(
        f"/api/v1/public/orders/{order['id']}/payment", params={"phone": "9333333333"}
    )
    assert second_attempt.status_code == 400
