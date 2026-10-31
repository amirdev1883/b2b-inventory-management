import pytest
from apps.inventory.models import Product, StockMovement
from django.db import IntegrityError, transaction

pytestmark = pytest.mark.django_db


def test_adjustment_audits_and_rejects_negative_stock(client, product):
    path = f"/api/products/{product.pk}/adjust/"
    response = client.post(path, {"quantity_delta": -5, "note": "Damaged stock"})
    assert response.status_code == 200
    assert response.data["quantity"] == 15
    movement = StockMovement.objects.first()
    assert movement.quantity_delta == -5 and movement.balance_after == 15
    assert movement.note == "Damaged stock"
    assert client.post(path, {"quantity_delta": -16, "note": "Invalid"}).status_code == 400
    assert client.post(path, {"quantity_delta": 0, "note": "Noop"}).status_code == 400
    assert client.post(path, {"quantity_delta": 1}).status_code == 400
    product.refresh_from_db()
    assert product.quantity == 15


def test_case_insensitive_sku_and_supplier_uniqueness(client, product, supplier, outsider):
    assert (
        client.post("/api/products/", {"name": "Duplicate", "sku": product.sku.lower()}).status_code
        == 400
    )
    assert client.post("/api/suppliers/", {"name": supplier.name.lower()}).status_code == 400
    Product.objects.create(tenant=outsider.tenant, name="Same SKU elsewhere", sku=product.sku)
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.create(tenant=product.tenant, name="Duplicate DB", sku=product.sku.lower())


def test_product_archive_and_protected_deletion(client, product):
    assert client.delete(f"/api/products/{product.pk}/").status_code == 409
    assert client.patch(f"/api/products/{product.pk}/", {"is_active": False}).status_code == 200
    assert (
        client.post(
            f"/api/products/{product.pk}/adjust/", {"quantity_delta": 1, "note": "No"}
        ).status_code
        == 400
    )


def test_price_and_quantity_constraints(client, product):
    assert client.patch(f"/api/products/{product.pk}/", {"cost_price": "-1"}).status_code == 400
    assert client.patch(f"/api/products/{product.pk}/", {"sale_price": "2.001"}).status_code == 400
    with pytest.raises(IntegrityError), transaction.atomic():
        Product.objects.filter(pk=product.pk).update(reserved_quantity=21)


def test_search_filter_pagination_and_low_stock(client, product):
    assert client.get("/api/products/?search=lamp").data["count"] == 1
    assert client.get("/api/products/?search=missing").data["count"] == 0
    assert client.get("/api/products/?low_stock=true").data["count"] == 0
    client.post(f"/api/products/{product.pk}/adjust/", {"quantity_delta": -17, "note": "Count"})
    assert client.get("/api/products/?low_stock=true").data["count"] == 1
