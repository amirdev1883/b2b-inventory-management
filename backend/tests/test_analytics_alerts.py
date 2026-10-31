from decimal import Decimal

import pytest
from apps.inventory.models import Product
from apps.inventory.tasks import send_low_stock_alerts
from django.core import mail

pytestmark = pytest.mark.django_db


def test_dashboard_recognizes_only_shipped_pre_tax_revenue(client, product, sale_payload):
    initial = client.get("/api/analytics/dashboard/").data
    assert initial["inventory_value"] == "202.00"
    path = f"/api/sales-orders/{client.post('/api/sales-orders/', sale_payload).data['id']}/"
    client.post(path + "confirm/", {})
    assert client.get("/api/analytics/dashboard/").data["shipped_revenue"] == "0.00"
    client.post(path + "ship/", {})
    dashboard = client.get("/api/analytics/dashboard/").data
    assert dashboard["shipped_revenue"] == "75.75"
    assert dashboard["units_on_hand"] == 17
    assert len(dashboard["daily_sales"]) == 30
    assert sum(Decimal(d["revenue"]) for d in dashboard["daily_sales"]) == Decimal("75.75")


def test_low_stock_alerts_tenant_scope_dedup_and_restock_reset(
    tenant, admin, manager, staff, product, outsider, client
):
    client.post(f"/api/products/{product.pk}/adjust/", {"quantity_delta": -18, "note": "Count"})
    Product.objects.create(tenant=outsider.tenant, name="Other empty", sku="OTHER")
    assert send_low_stock_alerts() == 2
    assert len(mail.outbox) == 2
    ours = next(message for message in mail.outbox if admin.email in message.to)
    assert set(ours.to) == {admin.email, manager.email}
    assert "Other empty" not in ours.body
    assert staff.email not in ours.to
    assert send_low_stock_alerts() == 0
    client.post(f"/api/products/{product.pk}/adjust/", {"quantity_delta": 10, "note": "Restock"})
    product.refresh_from_db()
    assert product.last_low_stock_alert_at is None
    client.post(f"/api/products/{product.pk}/adjust/", {"quantity_delta": -10, "note": "Count"})
    assert send_low_stock_alerts() == 1


def test_health_readiness_and_schema(client):
    assert client.get("/health/").json() == {"status": "ok"}
    assert client.get("/ready/").json() == {"status": "ready"}
    response = client.get("/api/schema/")
    assert response.status_code == 200
    assert b"/api/sales-orders/{id}/confirm/" in response.content


def test_archiving_products_preserves_inventory_valuation(client, product):
    client.patch(f"/api/products/{product.pk}/", {"is_active": False})
    dashboard = client.get("/api/analytics/dashboard/").data
    assert dashboard["product_count"] == 0
    assert dashboard["units_on_hand"] == 20
    assert dashboard["inventory_value"] == "202.00"
    assert dashboard["low_stock_count"] == 0
