from django.conf import settings
from django.db import models
from django.db.models.functions import Lower

from apps.common.models import TenantModel


class Product(TenantModel):
    name = models.CharField(max_length=180)
    sku = models.CharField(max_length=64)
    barcode = models.CharField(max_length=80, blank=True)
    description = models.TextField(blank=True, max_length=4000)
    category = models.CharField(max_length=100, blank=True)
    supplier = models.ForeignKey(
        "suppliers.Supplier", null=True, blank=True, on_delete=models.PROTECT
    )
    quantity = models.PositiveIntegerField(default=0)
    reserved_quantity = models.PositiveIntegerField(default=0)
    reorder_level = models.PositiveIntegerField(default=5)
    cost_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    sale_price = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    is_active = models.BooleanField(default=True)
    last_low_stock_alert_at = models.DateTimeField(null=True, blank=True)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(Lower("sku"), "tenant", name="unique_product_sku_per_tenant"),
            models.CheckConstraint(
                condition=models.Q(quantity__gte=models.F("reserved_quantity")),
                name="stock_covers_reservations",
            ),
            models.CheckConstraint(
                condition=models.Q(cost_price__gte=0) & models.Q(sale_price__gte=0),
                name="nonnegative_product_prices",
            ),
        ]

    @property
    def available_quantity(self):
        return self.quantity - self.reserved_quantity

    @property
    def is_low_stock(self):
        return self.available_quantity <= self.reorder_level

    def __str__(self):
        return f"{self.sku} — {self.name}"


class StockMovement(TenantModel):
    class Kind(models.TextChoices):
        ADJUSTMENT = "ADJUSTMENT", "Adjustment"
        PURCHASE = "PURCHASE", "Purchase received"
        RESERVE = "RESERVE", "Sales reservation"
        RELEASE = "RELEASE", "Reservation released"
        SALE = "SALE", "Sales shipment"

    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="movements")
    kind = models.CharField(max_length=12, choices=Kind.choices)
    quantity_delta = models.IntegerField()
    reserved_delta = models.IntegerField(default=0)
    balance_after = models.PositiveIntegerField()
    reserved_after = models.PositiveIntegerField(default=0)
    reference = models.CharField(max_length=80, blank=True)
    note = models.CharField(max_length=500, blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.PROTECT)
