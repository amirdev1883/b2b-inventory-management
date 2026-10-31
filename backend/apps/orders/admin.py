from django.contrib import admin

from apps.common.admin import ReadOnlyBusinessAdmin

from .models import PurchaseOrder, SalesOrder


@admin.register(SalesOrder)
class SalesOrderAdmin(ReadOnlyBusinessAdmin):
    list_display = ["number", "tenant", "customer_name", "status", "payment_status", "created_at"]
    list_filter = ["status", "payment_status"]
    search_fields = ["number", "customer_name"]


@admin.register(PurchaseOrder)
class PurchaseOrderAdmin(ReadOnlyBusinessAdmin):
    list_display = ["number", "tenant", "supplier_name", "status", "created_at"]
    list_filter = ["status"]
    search_fields = ["number", "supplier_name"]
