import pytest
from apps.inventory.models import Product
from apps.suppliers.models import Supplier
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db


def test_cross_tenant_lists_details_and_relations(
    client, outsider, product, supplier, sale_payload, purchase_payload
):
    other_product = Product.objects.create(tenant=outsider.tenant, name="Hidden", sku="HIDDEN")
    other_supplier = Supplier.objects.create(tenant=outsider.tenant, name="Secret")
    assert client.get("/api/products/").data["count"] == 1
    assert client.get(f"/api/products/{other_product.pk}/").status_code == 404
    assert client.patch(f"/api/products/{other_product.pk}/", {"name": "Stolen"}).status_code == 404
    assert (
        client.post(
            f"/api/products/{other_product.pk}/adjust/", {"quantity_delta": 100, "note": "steal"}
        ).status_code
        == 404
    )
    assert (
        client.post(
            "/api/products/", {"name": "Test", "sku": "TEST", "supplier": str(other_supplier.pk)}
        ).status_code
        == 400
    )
    sale_payload["items"][0]["product"] = str(other_product.pk)
    assert client.post("/api/sales-orders/", sale_payload).status_code == 400
    purchase_payload["supplier"] = str(other_supplier.pk)
    assert client.post("/api/purchase-orders/", purchase_payload).status_code == 400
    assert client.get(f"/api/users/{outsider.pk}/").status_code == 404


def test_cross_tenant_order_and_invoice_access(client, outsider, sale_payload, purchase_payload):
    sale = client.post("/api/sales-orders/", sale_payload).data
    purchase = client.post("/api/purchase-orders/", purchase_payload).data
    other_client = APIClient()
    other_client.force_authenticate(outsider)
    for endpoint in [
        f"sales-orders/{sale['id']}/",
        f"sales-orders/{sale['id']}/invoice/",
        f"purchase-orders/{purchase['id']}/",
    ]:
        assert other_client.get(f"/api/{endpoint}").status_code == 404
    for endpoint in [
        f"sales-orders/{sale['id']}/confirm/",
        f"sales-orders/{sale['id']}/ship/",
        f"sales-orders/{sale['id']}/cancel/",
        f"purchase-orders/{purchase['id']}/receive/",
    ]:
        assert other_client.post(f"/api/{endpoint}", {}).status_code == 404
    assert other_client.get("/api/sales-orders/").data["count"] == 0
    assert other_client.get("/api/stock-movements/").data["count"] == 0
    assert other_client.get("/api/analytics/dashboard/").data["product_count"] == 0


def test_staff_permissions(client, staff, product, sale_payload, purchase_payload):
    client.force_authenticate(staff)
    assert client.get("/api/products/").status_code == 200
    assert client.post("/api/products/", {"name": "X", "sku": "X"}).status_code == 403
    assert client.patch(f"/api/products/{product.pk}/", {"name": "X"}).status_code == 403
    assert (
        client.post(
            f"/api/products/{product.pk}/adjust/", {"quantity_delta": 2, "note": "x"}
        ).status_code
        == 403
    )
    assert client.post("/api/purchase-orders/", purchase_payload).status_code == 403
    sale = client.post("/api/sales-orders/", sale_payload)
    assert sale.status_code == 201
    assert client.post(f"/api/sales-orders/{sale.data['id']}/confirm/", {}).status_code == 403
    assert client.get("/api/users/").status_code == 403
    assert client.patch("/api/business/", {"name": "X"}).status_code == 403


def test_manager_cannot_manage_users(client, manager, product):
    client.force_authenticate(manager)
    assert client.patch(f"/api/products/{product.pk}/", {"name": "New"}).status_code == 200
    assert client.get("/api/users/").status_code == 403
    assert client.patch("/api/business/", {"name": "X"}).status_code == 403


def test_tenant_and_stock_fields_cannot_be_overridden(client, outsider, product):
    response = client.patch(
        f"/api/products/{product.pk}/",
        {"tenant": str(outsider.tenant_id), "quantity": 9999, "reserved_quantity": 100},
    )
    assert response.status_code == 200
    product.refresh_from_db()
    assert product.quantity == 20
    assert product.reserved_quantity == 0
    assert product.tenant_id != outsider.tenant_id
