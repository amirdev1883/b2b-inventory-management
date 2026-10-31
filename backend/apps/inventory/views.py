from django.db.models import F
from drf_spectacular.utils import extend_schema
from rest_framework import mixins, viewsets
from rest_framework.decorators import action
from rest_framework.response import Response

from apps.common.permissions import ManagerOrReadOnly
from apps.common.views import TenantViewSet

from .models import Product, StockMovement
from .serializers import AdjustmentSerializer, ProductSerializer, StockMovementSerializer
from .services import adjust_stock


class ProductViewSet(TenantViewSet):
    queryset = Product.objects.select_related("supplier")
    serializer_class = ProductSerializer
    permission_classes = [ManagerOrReadOnly]
    search_fields = ["name", "sku", "barcode", "category"]
    filterset_fields = ["is_active", "category", "supplier"]
    ordering_fields = ["name", "sku", "quantity", "sale_price", "created_at"]

    def get_queryset(self):
        qs = super().get_queryset()
        if self.request.query_params.get("low_stock") == "true":
            qs = qs.filter(
                quantity__lte=F("reserved_quantity") + F("reorder_level"), is_active=True
            )
        return qs

    @extend_schema(request=AdjustmentSerializer, responses=ProductSerializer)
    @action(detail=True, methods=["post"])
    def adjust(self, request, pk=None):
        product = self.get_object()
        serializer = AdjustmentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product = adjust_stock(
            product_id=product.pk,
            tenant=request.user.tenant,
            actor=request.user,
            **serializer.validated_data,
        )
        return Response(self.get_serializer(product).data)


class StockMovementViewSet(
    mixins.ListModelMixin, mixins.RetrieveModelMixin, viewsets.GenericViewSet
):
    serializer_class = StockMovementSerializer
    queryset = StockMovement.objects.select_related("product", "created_by")
    filterset_fields = ["product", "kind"]
    search_fields = ["product__name", "product__sku", "reference", "note"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        return self.queryset.filter(tenant_id=self.request.user.tenant_id)
