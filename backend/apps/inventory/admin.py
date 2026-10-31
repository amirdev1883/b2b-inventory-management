from django.contrib import admin

from apps.common.admin import ReadOnlyBusinessAdmin

from .models import Product, StockMovement


@admin.register(Product)
class ProductAdmin(ReadOnlyBusinessAdmin):
    list_display = ["sku", "name", "tenant", "quantity", "reserved_quantity", "is_active"]
    search_fields = ["sku", "name"]
    list_filter = ["is_active"]


@admin.register(StockMovement)
class StockMovementAdmin(ReadOnlyBusinessAdmin):
    list_display = ["product", "tenant", "kind", "quantity_delta", "balance_after", "created_at"]
    list_filter = ["kind"]
