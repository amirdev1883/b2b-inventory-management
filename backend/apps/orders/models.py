import uuid
from decimal import ROUND_HALF_UP, Decimal

from django.conf import settings
from django.db import models

from apps.common.models import TenantModel


def sales_number():
    return f"SO-{uuid.uuid4().hex[:12].upper()}"


def purchase_number():
    return f"PO-{uuid.uuid4().hex[:12].upper()}"


def money(value):
    return Decimal(value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


class Order(TenantModel):
    currency = models.CharField(max_length=3)
    tax_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0)
    notes = models.TextField(blank=True, max_length=2000)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT)
    request_key = models.CharField(max_length=128, null=True, blank=True, editable=False)
    request_fingerprint = models.CharField(max_length=64, blank=True, editable=False)

    class Meta(TenantModel.Meta):
        abstract = True

    @property
    def subtotal(self):
        return money(sum((item.line_total for item in self.items.all()), Decimal("0")))

    @property
    def tax_amount(self):
        return money(self.subtotal * self.tax_rate / 100)

    @property
    def total(self):
        return self.subtotal + self.tax_amount


class SalesOrder(Order):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        CONFIRMED = "CONFIRMED", "Confirmed"
        SHIPPED = "SHIPPED", "Shipped"
        CANCELLED = "CANCELLED", "Cancelled"

    class Payment(models.TextChoices):
        UNPAID = "UNPAID", "Unpaid"
        PAID = "PAID", "Paid"

    number = models.CharField(max_length=24, unique=True, default=sales_number, editable=False)
    customer_name = models.CharField(max_length=180)
    customer_email = models.EmailField(blank=True)
    customer_address = models.TextField(blank=True, max_length=1000)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    payment_status = models.CharField(max_length=8, choices=Payment.choices, default=Payment.UNPAID)
    confirmed_at = models.DateTimeField(null=True, blank=True)
    shipped_at = models.DateTimeField(null=True, blank=True)
    invoice_snapshot = models.JSONField(default=dict, editable=False)

    class Meta(Order.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "request_key"], name="sales_request_key_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(tax_rate__gte=0, tax_rate__lte=100), name="valid_sales_tax"
            ),
        ]


class PurchaseOrder(Order):
    class Status(models.TextChoices):
        DRAFT = "DRAFT", "Draft"
        RECEIVED = "RECEIVED", "Received"
        CANCELLED = "CANCELLED", "Cancelled"

    number = models.CharField(max_length=24, unique=True, default=purchase_number, editable=False)
    supplier = models.ForeignKey("suppliers.Supplier", on_delete=models.PROTECT)
    supplier_name = models.CharField(max_length=160)
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.DRAFT)
    received_at = models.DateTimeField(null=True, blank=True)

    class Meta(Order.Meta):
        constraints = [
            models.UniqueConstraint(
                fields=["tenant", "request_key"], name="purchase_request_key_unique"
            ),
            models.CheckConstraint(
                condition=models.Q(tax_rate__gte=0, tax_rate__lte=100), name="valid_purchase_tax"
            ),
        ]


class OrderItem(TenantModel):
    product = models.ForeignKey("inventory.Product", on_delete=models.PROTECT)
    product_name = models.CharField(max_length=180)
    sku = models.CharField(max_length=64)
    quantity = models.PositiveIntegerField()
    unit_price = models.DecimalField(max_digits=12, decimal_places=2)

    class Meta(TenantModel.Meta):
        abstract = True
        ordering = ["created_at", "id"]

    @property
    def line_total(self):
        return money(self.quantity * self.unit_price)


class SalesOrderItem(OrderItem):
    order = models.ForeignKey(SalesOrder, on_delete=models.CASCADE, related_name="items")

    class Meta(OrderItem.Meta):
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="sales_unique_product"),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0, unit_price__gte=0), name="valid_sales_item"
            ),
        ]


class PurchaseOrderItem(OrderItem):
    order = models.ForeignKey(PurchaseOrder, on_delete=models.CASCADE, related_name="items")

    class Meta(OrderItem.Meta):
        constraints = [
            models.UniqueConstraint(fields=["order", "product"], name="purchase_unique_product"),
            models.CheckConstraint(
                condition=models.Q(quantity__gt=0, unit_price__gte=0), name="valid_purchase_item"
            ),
        ]
