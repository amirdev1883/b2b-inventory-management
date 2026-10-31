from django.db import transaction
from rest_framework.exceptions import ValidationError

from .models import Product, StockMovement


def record_movement(
    product, actor, kind, quantity_delta=0, reserved_delta=0, reference="", note=""
):
    product.quantity += quantity_delta
    product.reserved_quantity += reserved_delta
    if product.quantity < product.reserved_quantity or product.reserved_quantity < 0:
        raise ValidationError({"detail": f"Insufficient available stock for {product.sku}."})
    if product.quantity > 2147483647:
        raise ValidationError({"detail": "Stock exceeds the supported quantity limit."})
    if product.available_quantity > product.reorder_level:
        product.last_low_stock_alert_at = None
    product.save(
        update_fields=["quantity", "reserved_quantity", "last_low_stock_alert_at", "updated_at"]
    )
    StockMovement.objects.create(
        tenant_id=product.tenant_id,
        product=product,
        kind=kind,
        quantity_delta=quantity_delta,
        reserved_delta=reserved_delta,
        balance_after=product.quantity,
        reserved_after=product.reserved_quantity,
        reference=reference,
        note=note,
        created_by=actor,
    )


@transaction.atomic
def adjust_stock(*, product_id, tenant, actor, quantity_delta, note):
    product = Product.objects.select_for_update().get(pk=product_id, tenant=tenant)
    if not product.is_active:
        raise ValidationError({"detail": "Activate the product before adjusting its stock."})
    record_movement(
        product, actor, StockMovement.Kind.ADJUSTMENT, quantity_delta=quantity_delta, note=note
    )
    return product
