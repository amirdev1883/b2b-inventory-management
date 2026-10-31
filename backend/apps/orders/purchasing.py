from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import ValidationError

from apps.inventory.models import StockMovement
from apps.inventory.services import record_movement

from .models import PurchaseOrder
from .services import locked_products


@transaction.atomic
def transition_purchase(*, order_id, tenant, actor, action):
    order = PurchaseOrder.objects.select_for_update().get(pk=order_id, tenant=tenant)
    target = "RECEIVED" if action == "receive" else "CANCELLED"
    if order.status == target:
        return order
    if order.status != "DRAFT":
        raise ValidationError(
            {"detail": f"Cannot {action} a {order.status.lower()} purchase order."}
        )
    if action == "receive":
        items, products = locked_products(order)
        for item in items:
            record_movement(
                products[item.product_id],
                actor,
                StockMovement.Kind.PURCHASE,
                quantity_delta=item.quantity,
                reference=order.number,
            )
        order.received_at = timezone.now()
    order.status = target
    order.save()
    return order
