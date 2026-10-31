from django.contrib import admin

from apps.common.admin import ReadOnlyBusinessAdmin

from .models import Supplier


@admin.register(Supplier)
class SupplierAdmin(ReadOnlyBusinessAdmin):
    list_display = ["name", "tenant", "email", "is_active"]
    search_fields = ["name", "email"]
