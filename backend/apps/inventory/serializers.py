from decimal import Decimal

from rest_framework import serializers

from apps.suppliers.models import Supplier

from .models import Product, StockMovement


class ProductSerializer(serializers.ModelSerializer):
    supplier_name = serializers.CharField(source="supplier.name", read_only=True, default="")
    available_quantity = serializers.IntegerField(read_only=True)
    is_low_stock = serializers.BooleanField(read_only=True)
    cost_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )
    sale_price = serializers.DecimalField(
        max_digits=12, decimal_places=2, min_value=Decimal("0"), required=False
    )

    class Meta:
        model = Product
        fields = [
            "id",
            "name",
            "sku",
            "barcode",
            "description",
            "category",
            "supplier",
            "supplier_name",
            "quantity",
            "reserved_quantity",
            "available_quantity",
            "reorder_level",
            "cost_price",
            "sale_price",
            "is_active",
            "is_low_stock",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "quantity", "reserved_quantity", "created_at", "updated_at"]
        validators = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        request = self.context.get("request")
        self.fields["supplier"].queryset = (
            Supplier.objects.filter(tenant_id=request.user.tenant_id)
            if request and request.user.is_authenticated
            else Supplier.objects.none()
        )

    def validate_sku(self, value):
        value = value.upper()
        qs = Product.objects.filter(
            tenant_id=self.context["request"].user.tenant_id, sku__iexact=value
        )
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("A product with this SKU already exists.")
        return value


class AdjustmentSerializer(serializers.Serializer):
    quantity_delta = serializers.IntegerField(min_value=-1000000000, max_value=1000000000)
    note = serializers.CharField(max_length=500)

    def validate_quantity_delta(self, value):
        if value == 0:
            raise serializers.ValidationError("Adjustment must change the quantity.")
        return value


class StockMovementSerializer(serializers.ModelSerializer):
    product_name = serializers.CharField(source="product.name", read_only=True)
    sku = serializers.CharField(source="product.sku", read_only=True)
    actor = serializers.CharField(source="created_by.email", read_only=True, default="System")

    class Meta:
        model = StockMovement
        fields = [
            "id",
            "product",
            "product_name",
            "sku",
            "kind",
            "quantity_delta",
            "reserved_delta",
            "balance_after",
            "reserved_after",
            "reference",
            "note",
            "actor",
            "created_at",
        ]
        read_only_fields = fields
