from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from apps.inventory.models import StockMovement
from apps.orders.models import SalesOrder, SalesOrderItem
from apps.orders.purchasing import transition_purchase
from apps.orders.services import transition_sales
from apps.users.models import User
from django.db import close_old_connections, connection
from rest_framework.exceptions import ValidationError
from rest_framework.test import APIClient

pytestmark = [
    pytest.mark.django_db(transaction=True),
    pytest.mark.postgres,
    pytest.mark.skipif(connection.vendor != "postgresql", reason="Requires PostgreSQL row locks"),
]


def run_together(functions):
    barrier = Barrier(len(functions))

    def execute(fn):
        close_old_connections()
        try:
            barrier.wait(timeout=10)
            return fn()
        finally:
            close_old_connections()

    with ThreadPoolExecutor(max_workers=len(functions)) as executor:
        return list(executor.map(execute, functions))


def test_competing_orders_cannot_oversell(product, tenant, admin):
    orders = []
    for index in range(2):
        order = SalesOrder.objects.create(
            tenant=tenant, created_by=admin, currency="CAD", customer_name=f"Buyer {index}"
        )
        SalesOrderItem.objects.create(
            tenant=tenant,
            order=order,
            product=product,
            product_name=product.name,
            sku=product.sku,
            quantity=15,
            unit_price=product.sale_price,
        )
        orders.append(order)

    def confirm(order):
        try:
            transition_sales(order_id=order.pk, tenant=tenant, actor=admin, action="confirm")
            return "confirmed"
        except ValidationError:
            return "insufficient"

    results = run_together([lambda: confirm(orders[0]), lambda: confirm(orders[1])])
    assert sorted(results) == ["confirmed", "insufficient"]
    product.refresh_from_db()
    assert product.quantity == 20 and product.reserved_quantity == 15
    assert StockMovement.objects.filter(kind="RESERVE").count() == 1


def test_concurrent_duplicate_receipts_add_stock_once(
    client, product, tenant, admin, purchase_payload
):
    response = client.post("/api/purchase-orders/", purchase_payload)
    order_id = response.data["id"]

    def receive():
        return transition_purchase(
            order_id=order_id, tenant=tenant, actor=admin, action="receive"
        ).status

    assert run_together([receive, receive]) == ["RECEIVED", "RECEIVED"]
    product.refresh_from_db()
    assert product.quantity == 30
    assert StockMovement.objects.filter(kind="PURCHASE").count() == 1


def test_concurrent_order_retries_create_once(admin, sale_payload):
    def create():
        client = APIClient()
        client.force_authenticate(User.objects.get(pk=admin.pk))
        return client.post(
            "/api/sales-orders/", sale_payload, HTTP_IDEMPOTENCY_KEY="concurrent-retry-key"
        ).status_code

    assert sorted(run_together([create, create])) == [200, 201]
    assert SalesOrder.objects.count() == 1


def test_concurrent_admin_demotions_preserve_an_admin(tenant, admin):
    second = User.objects.create_user(
        "second@example.com", "Long-password-983!", tenant=tenant, role="ADMIN"
    )

    def demote(user):
        client = APIClient()
        client.force_authenticate(user)
        return client.patch(f"/api/users/{user.pk}/", {"role": "STAFF"}).status_code

    assert sorted(run_together([lambda: demote(admin), lambda: demote(second)])) == [200, 400]
    assert User.objects.filter(tenant=tenant, role="ADMIN", is_active=True).count() == 1
