from decimal import Decimal

from django.db import transaction
from rest_framework import serializers

from apps.inventory.models import Product
from apps.suppliers.models import Supplier

from .models import PurchaseOrder, PurchaseOrderItem, SalesOrder, SalesOrderItem


class ItemSerializer(serializers.Serializer):
    id = serializers.UUIDField(read_only=True)
    product = serializers.PrimaryKeyRelatedField(queryset=Product.objects.none())
    product_name = serializers.CharField(read_only=True)
    sku = serializers.CharField(read_only=True)
    quantity = serializers.IntegerField(min_value=1, max_value=1000000)
    unit_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    line_total = serializers.DecimalField(max_digits=20, decimal_places=2, read_only=True)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        if request and request.user.is_authenticated:
            fields["product"].queryset = Product.objects.filter(
                tenant_id=request.user.tenant_id, is_active=True
            )
        return fields


class OrderSerializer(serializers.ModelSerializer):
    items = ItemSerializer(many=True, allow_empty=False, max_length=100)
    subtotal = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)
    tax_amount = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)
    total = serializers.DecimalField(max_digits=22, decimal_places=2, read_only=True)
    tax_rate = serializers.DecimalField(
        max_digits=5,
        decimal_places=2,
        min_value=Decimal("0"),
        max_value=Decimal("100"),
        required=False,
    )
    created_by_name = serializers.CharField(source="created_by.get_full_name", read_only=True)

    def validate_items(self, value):
        ids = [item["product"].pk for item in value]
        if len(ids) != len(set(ids)):
            raise serializers.ValidationError("Combine duplicate products into a single line.")
        return value

    def validate(self, attrs):
        if self.instance and self.instance.status != "DRAFT":
            raise serializers.ValidationError({"detail": "Only draft orders can be edited."})
        return attrs

    def _write_items(self, order, items):
        item_model = SalesOrderItem if isinstance(order, SalesOrder) else PurchaseOrderItem
        price_field = "sale_price" if isinstance(order, SalesOrder) else "cost_price"
        item_model.objects.bulk_create(
            [
                item_model(
                    order=order,
                    tenant=order.tenant,
                    product=item["product"],
                    product_name=item["product"].name,
                    sku=item["product"].sku,
                    quantity=item["quantity"],
                    unit_price=item.get("unit_price", getattr(item["product"], price_field)),
                )
                for item in items
            ]
        )

    @transaction.atomic
    def create(self, validated_data):
        items = validated_data.pop("items")
        if "supplier" in validated_data:
            validated_data["supplier_name"] = validated_data["supplier"].name
        order = self.Meta.model.objects.create(**validated_data)
        self._write_items(order, items)
        return order

    @transaction.atomic
    def update(self, instance, validated_data):
        items = validated_data.pop("items", None)
        if "supplier" in validated_data:
            validated_data["supplier_name"] = validated_data["supplier"].name
        instance = super().update(instance, validated_data)
        if items is not None:
            instance.items.all().delete()
            self._write_items(instance, items)
        instance._prefetched_objects_cache = {}
        return instance


class SalesOrderSerializer(OrderSerializer):
    class Meta:
        model = SalesOrder
        fields = [
            "id",
            "number",
            "customer_name",
            "customer_email",
            "customer_address",
            "currency",
            "status",
            "payment_status",
            "tax_rate",
            "notes",
            "items",
            "subtotal",
            "tax_amount",
            "total",
            "created_by_name",
            "created_at",
            "updated_at",
            "confirmed_at",
            "shipped_at",
        ]
        read_only_fields = [
            "id",
            "number",
            "currency",
            "status",
            "payment_status",
            "created_at",
            "updated_at",
            "confirmed_at",
            "shipped_at",
        ]


class PurchaseOrderSerializer(OrderSerializer):
    class Meta:
        model = PurchaseOrder
        fields = [
            "id",
            "number",
            "supplier",
            "supplier_name",
            "currency",
            "status",
            "tax_rate",
            "notes",
            "items",
            "subtotal",
            "tax_amount",
            "total",
            "created_by_name",
            "created_at",
            "updated_at",
            "received_at",
        ]
        read_only_fields = [
            "id",
            "number",
            "supplier_name",
            "currency",
            "status",
            "created_at",
            "updated_at",
            "received_at",
        ]

    def get_fields(self):
        fields = super().get_fields()
        request = self.context.get("request")
        fields["supplier"].queryset = (
            Supplier.objects.filter(tenant_id=request.user.tenant_id, is_active=True)
            if request and request.user.is_authenticated
            else Supplier.objects.none()
        )
        return fields


class PaymentSerializer(serializers.Serializer):
    payment_status = serializers.ChoiceField(choices=SalesOrder.Payment.choices)
