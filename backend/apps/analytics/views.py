from datetime import timedelta
from decimal import Decimal

from django.db.models import DecimalField, ExpressionWrapper, F, Sum
from django.db.models.functions import TruncDate
from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.inventory.models import Product
from apps.inventory.serializers import ProductSerializer
from apps.orders.models import SalesOrder, SalesOrderItem, money
from apps.orders.serializers import SalesOrderSerializer


class DailySalesSerializer(serializers.Serializer):
    date = serializers.DateField()
    revenue = serializers.DecimalField(max_digits=24, decimal_places=2)


class DashboardSerializer(serializers.Serializer):
    currency = serializers.CharField()
    product_count = serializers.IntegerField()
    low_stock_count = serializers.IntegerField()
    units_on_hand = serializers.IntegerField()
    units_reserved = serializers.IntegerField()
    inventory_value = serializers.DecimalField(max_digits=24, decimal_places=2)
    shipped_revenue = serializers.DecimalField(max_digits=24, decimal_places=2)
    open_sales_orders = serializers.IntegerField()
    recent_orders = SalesOrderSerializer(many=True)
    low_stock_products = ProductSerializer(many=True)
    daily_sales = DailySalesSerializer(many=True)


class DashboardView(APIView):
    @extend_schema(responses=DashboardSerializer)
    def get(self, request):
        tenant = request.user.tenant
        products = Product.objects.filter(tenant=tenant)
        low = products.filter(
            is_active=True, quantity__lte=F("reserved_quantity") + F("reorder_level")
        )
        aggregates = products.aggregate(
            units=Sum("quantity"),
            reserved=Sum("reserved_quantity"),
            value=Sum(
                ExpressionWrapper(
                    F("quantity") * F("cost_price"),
                    output_field=DecimalField(max_digits=24, decimal_places=2),
                )
            ),
        )
        orders = SalesOrder.objects.filter(tenant=tenant)
        shipped = orders.filter(status="SHIPPED").prefetch_related("items")
        # Sales revenue is pre-tax and recognized at shipment, never at draft/confirmation.
        revenue = SalesOrderItem.objects.filter(order__in=shipped).aggregate(
            value=Sum(
                ExpressionWrapper(
                    F("quantity") * F("unit_price"),
                    output_field=DecimalField(max_digits=24, decimal_places=2),
                )
            )
        )["value"] or Decimal(0)
        start = timezone.localdate() - timedelta(days=29)
        daily = (
            SalesOrderItem.objects.filter(
                tenant=tenant, order__status="SHIPPED", order__shipped_at__date__gte=start
            )
            .annotate(date=TruncDate("order__shipped_at"))
            .values("date")
            .annotate(
                revenue=Sum(
                    ExpressionWrapper(
                        F("quantity") * F("unit_price"),
                        output_field=DecimalField(max_digits=24, decimal_places=2),
                    )
                )
            )
            .order_by("date")
        )
        by_day = {d["date"]: money(d["revenue"]) for d in daily}
        context = {"request": request}
        data = {
            "currency": tenant.currency,
            "product_count": products.filter(is_active=True).count(),
            "low_stock_count": low.count(),
            "units_on_hand": aggregates["units"] or 0,
            "units_reserved": aggregates["reserved"] or 0,
            "inventory_value": money(aggregates["value"] or 0),
            "shipped_revenue": money(revenue),
            "open_sales_orders": orders.filter(status__in=["DRAFT", "CONFIRMED"]).count(),
            "recent_orders": orders.select_related("created_by").prefetch_related("items")[:5],
            "low_stock_products": low.select_related("supplier").order_by("quantity")[:5],
            "daily_sales": [
                {
                    "date": start + timedelta(days=i),
                    "revenue": by_day.get(start + timedelta(days=i), Decimal(0)),
                }
                for i in range(30)
            ],
        }
        return Response(DashboardSerializer(data, context=context).data)
