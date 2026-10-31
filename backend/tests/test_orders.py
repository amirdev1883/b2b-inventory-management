import pytest
from apps.inventory.models import Product, StockMovement
from apps.orders.models import SalesOrder

pytestmark = pytest.mark.django_db


def create_sale(client, payload):
    response = client.post("/api/sales-orders/", payload)
    assert response.status_code == 201, response.data
    return f"/api/sales-orders/{response.data['id']}/", response.data


def test_sales_lifecycle_money_reservations_and_idempotent_actions(client, product, sale_payload):
    path, sale = create_sale(client, sale_payload)
    assert sale["subtotal"] == "75.75"
    assert sale["tax_amount"] == "9.85"
    assert sale["total"] == "85.60"
    assert client.get(path + "invoice/").status_code == 400
    assert client.post(path + "ship/", {}).status_code == 400
    assert client.post(path + "confirm/", {}).status_code == 200
    assert client.post(path + "confirm/", {}).status_code == 200
    product.refresh_from_db()
    assert (product.quantity, product.reserved_quantity, product.available_quantity) == (20, 3, 17)
    assert (
        client.post(
            f"/api/products/{product.pk}/adjust/",
            {"quantity_delta": -18, "note": "Cannot take reserved stock"},
        ).status_code
        == 400
    )
    assert client.patch(path, {"customer_name": "Changed"}).status_code == 400
    assert client.post(path + "ship/", {}).status_code == 200
    assert client.post(path + "ship/", {}).status_code == 200
    product.refresh_from_db()
    assert (product.quantity, product.reserved_quantity) == (17, 0)
    assert StockMovement.objects.filter(kind="RESERVE").count() == 1
    assert StockMovement.objects.filter(kind="SALE").count() == 1
    assert client.post(path + "cancel/", {}).status_code == 400
    response = client.get(path + "invoice/")
    assert response.status_code == 200
    assert response["Content-Type"] == "application/pdf"
    assert b"".join(response.streaming_content).startswith(b"%PDF")


def test_cancellation_releases_stock_once(client, product, sale_payload):
    path, _ = create_sale(client, sale_payload)
    client.post(path + "confirm/", {})
    assert client.post(path + "cancel/", {}).status_code == 200
    assert client.post(path + "cancel/", {}).status_code == 200
    product.refresh_from_db()
    assert (product.quantity, product.reserved_quantity) == (20, 0)
    assert StockMovement.objects.filter(kind="RELEASE").count() == 1


def test_overselling_rolls_back_all_product_reservations(client, product, sale_payload, tenant):
    empty = Product.objects.create(tenant=tenant, name="Empty", sku="EMPTY")
    sale_payload["items"].append({"product": str(empty.pk), "quantity": 1})
    path, _ = create_sale(client, sale_payload)
    assert client.post(path + "confirm/", {}).status_code == 400
    product.refresh_from_db()
    assert product.reserved_quantity == 0
    assert StockMovement.objects.filter(kind="RESERVE").count() == 0
    assert SalesOrder.objects.first().status == "DRAFT"


def test_draft_cancel_no_movements(client, sale_payload):
    path, _ = create_sale(client, sale_payload)
    before = StockMovement.objects.count()
    assert client.post(path + "cancel/", {}).status_code == 200
    assert StockMovement.objects.count() == before


def test_price_and_seller_snapshots(client, product, sale_payload, tenant):
    path, sale = create_sale(client, sale_payload)
    client.post(path + "confirm/", {})
    tenant.name = "Renamed business"
    tenant.save()
    client.patch(f"/api/products/{product.pk}/", {"name": "New Name", "sale_price": "99.99"})
    updated = client.get(path).data
    assert updated["items"][0]["product_name"] == "Desk Lamp"
    assert updated["items"][0]["unit_price"] == "25.25"
    assert SalesOrder.objects.get(pk=sale["id"]).invoice_snapshot["name"] == "Northstar Supply"


def test_draft_edit_recalculates_totals(client, product, sale_payload):
    path, _ = create_sale(client, sale_payload)
    response = client.patch(
        path,
        {
            "items": [{"product": str(product.pk), "quantity": 2, "unit_price": "10.50"}],
            "tax_rate": "0",
        },
    )
    assert response.status_code == 200
    assert response.data["total"] == "21.00"
    assert len(response.data["items"]) == 1


@pytest.mark.parametrize("change", [{"items": []}, {"tax_rate": "101"}, {"tax_rate": "-1"}])
def test_invalid_order_data(client, sale_payload, change):
    sale_payload.update(change)
    assert client.post("/api/sales-orders/", sale_payload).status_code == 400


def test_invalid_items(client, sale_payload, product):
    sale_payload["items"][0]["quantity"] = 0
    assert client.post("/api/sales-orders/", sale_payload).status_code == 400
    sale_payload["items"][0]["quantity"] = 1
    sale_payload["items"].append(sale_payload["items"][0].copy())
    assert client.post("/api/sales-orders/", sale_payload).status_code == 400


def test_purchase_receiving_once_and_no_edits(client, product, purchase_payload):
    response = client.post("/api/purchase-orders/", purchase_payload)
    assert response.status_code == 201, response.data
    path = f"/api/purchase-orders/{response.data['id']}/"
    assert response.data["total"] == "95.00"
    assert client.post(path + "receive/", {}).status_code == 200
    assert client.post(path + "receive/", {}).status_code == 200
    product.refresh_from_db()
    assert product.quantity == 30
    assert StockMovement.objects.filter(kind="PURCHASE").count() == 1
    assert client.patch(path, {"notes": "edit"}).status_code == 400
    assert client.post(path + "cancel/", {}).status_code == 400


def test_purchase_cancel_never_increases_stock(client, product, purchase_payload):
    response = client.post("/api/purchase-orders/", purchase_payload)
    path = f"/api/purchase-orders/{response.data['id']}/"
    assert client.post(path + "cancel/", {}).status_code == 200
    assert client.post(path + "receive/", {}).status_code == 400
    product.refresh_from_db()
    assert product.quantity == 20


def test_idempotency_key_replay_and_conflict(client, sale_payload):
    first = client.post("/api/sales-orders/", sale_payload, HTTP_IDEMPOTENCY_KEY="test-request-key")
    second = client.post(
        "/api/sales-orders/", sale_payload, HTTP_IDEMPOTENCY_KEY="test-request-key"
    )
    assert first.status_code == 201
    assert second.status_code == 200
    assert first.data["id"] == second.data["id"]
    assert SalesOrder.objects.count() == 1
    sale_payload["customer_name"] = "Different"
    assert (
        client.post(
            "/api/sales-orders/", sale_payload, HTTP_IDEMPOTENCY_KEY="test-request-key"
        ).status_code
        == 409
    )


def test_payment_transitions_and_cancel_guard(client, sale_payload):
    path, _ = create_sale(client, sale_payload)
    assert client.post(path + "payment/", {"payment_status": "PAID"}).status_code == 400
    client.post(path + "confirm/", {})
    assert client.post(path + "payment/", {"payment_status": "PAID"}).status_code == 200
    assert client.post(path + "cancel/", {}).status_code == 400
    assert client.post(path + "payment/", {"payment_status": "UNPAID"}).status_code == 200
    assert client.post(path + "cancel/", {}).status_code == 200
