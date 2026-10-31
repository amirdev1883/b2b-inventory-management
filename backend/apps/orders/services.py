from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.inventory.models import Product, StockMovement
from apps.inventory.services import record_movement

from .models import SalesOrder


def locked_products(order):
    items = list(order.items.all())
    products = {
        p.pk: p
        for p in Product.objects.select_for_update()
        .filter(tenant_id=order.tenant_id, pk__in=[i.product_id for i in items])
        .order_by("pk")
    }
    if not items or len(products) != len(items):
        raise ValidationError({"detail": "Order has no valid product lines."})
    return items, products


@transaction.atomic
def transition_sales(*, order_id, tenant, actor, action):
    order = SalesOrder.objects.select_for_update().get(pk=order_id, tenant=tenant)
    targets = {"confirm": "CONFIRMED", "ship": "SHIPPED", "cancel": "CANCELLED"}
    if order.status == targets[action]:
        return order
    allowed = {"confirm": {"DRAFT"}, "ship": {"CONFIRMED"}, "cancel": {"DRAFT", "CONFIRMED"}}
    if order.status not in allowed[action]:
        raise ValidationError({"detail": f"Cannot {action} a {order.status.lower()} sales order."})
    if action == "cancel" and order.payment_status == "PAID":
        raise ValidationError(
            {"detail": "Mark the order unpaid after arranging the refund before cancelling."}
        )
    if action != "cancel" or order.status == "CONFIRMED":
        items, products = locked_products(order)
        for item in items:
            product = products[item.product_id]
            if action == "confirm":
                if not product.is_active:
                    raise ValidationError({"detail": f"Product {product.sku} is archived."})
                record_movement(
                    product,
                    actor,
                    StockMovement.Kind.RESERVE,
                    reserved_delta=item.quantity,
                    reference=order.number,
                )
            elif action == "ship":
                record_movement(
                    product,
                    actor,
                    StockMovement.Kind.SALE,
                    quantity_delta=-item.quantity,
                    reserved_delta=-item.quantity,
                    reference=order.number,
                )
            else:
                record_movement(
                    product,
                    actor,
                    StockMovement.Kind.RELEASE,
                    reserved_delta=-item.quantity,
                    reference=order.number,
                )
    if action == "confirm":
        order.confirmed_at = timezone.now()
        order.invoice_snapshot = {
            "name": tenant.name,
            "address": tenant.address,
            "email": tenant.email,
            "phone": tenant.phone,
            "tax_number": tenant.tax_number,
        }
    if action == "ship":
        order.shipped_at = timezone.now()
    order.status = targets[action]
    order.save()
    return order
