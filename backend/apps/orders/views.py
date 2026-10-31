import hashlib
import json
import re

from django.db import transaction
from django.http import FileResponse
from drf_spectacular.utils import OpenApiTypes, extend_schema
from rest_framework import mixins, serializers, viewsets
from rest_framework.decorators import action
from rest_framework.exceptions import PermissionDenied
from rest_framework.response import Response

from apps.common.permissions import ManagerOrReadOnly
from apps.users.models import Tenant

from .invoices import render_invoice
from .models import PurchaseOrder, SalesOrder
from .purchasing import transition_purchase
from .serializers import PaymentSerializer, PurchaseOrderSerializer, SalesOrderSerializer
from .services import transition_sales


class OrderViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        return self.queryset.filter(tenant_id=self.request.user.tenant_id)

    @transaction.atomic
    def create(self, request, *args, **kwargs):
        tenant = Tenant.objects.select_for_update().get(pk=request.user.tenant_id)
        key = request.headers.get("Idempotency-Key")
        if key and not re.fullmatch(r"[A-Za-z0-9_-]{8,128}", key):
            raise serializers.ValidationError(
                {"detail": "Idempotency-Key must be 8–128 letters, digits, underscores or hyphens."}
            )
        fingerprint = hashlib.sha256(
            json.dumps(request.data, sort_keys=True, separators=(",", ":")).encode()
        ).hexdigest()
        if key:
            existing = self.get_queryset().filter(request_key=key).first()
            if existing:
                if existing.request_fingerprint != fingerprint:
                    return Response(
                        {"detail": "Idempotency-Key was already used with different data."},
                        status=409,
                    )
                return Response(self.get_serializer(existing).data)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save(
            tenant=tenant,
            currency=tenant.currency,
            created_by=request.user,
            request_key=key,
            request_fingerprint=fingerprint,
        )
        return Response(serializer.data, status=201)

    @transaction.atomic
    def update(self, request, *args, **kwargs):
        instance = self.get_queryset().select_for_update(of=("self",)).get(pk=self.get_object().pk)
        serializer = self.get_serializer(
            instance, data=request.data, partial=kwargs.pop("partial", False)
        )
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data)

    def require_manager(self):
        if self.request.user.role not in {"ADMIN", "MANAGER"}:
            raise PermissionDenied("Only admins and managers may perform this action.")


class SalesOrderViewSet(OrderViewSet):
    queryset = SalesOrder.objects.select_related("created_by").prefetch_related("items")
    serializer_class = SalesOrderSerializer
    search_fields = ["number", "customer_name", "customer_email"]
    filterset_fields = ["status", "payment_status"]
    ordering_fields = ["created_at", "customer_name", "number"]

    def transition(self, request, action):
        self.require_manager()
        order = self.get_object()
        result = transition_sales(
            order_id=order.pk, tenant=request.user.tenant, actor=request.user, action=action
        )
        return Response(self.get_serializer(result).data)

    @extend_schema(request=None, responses=SalesOrderSerializer)
    @action(detail=True, methods=["post"])
    def confirm(self, request, pk=None):
        return self.transition(request, "confirm")

    @extend_schema(request=None, responses=SalesOrderSerializer)
    @action(detail=True, methods=["post"])
    def ship(self, request, pk=None):
        return self.transition(request, "ship")

    @extend_schema(request=None, responses=SalesOrderSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self.transition(request, "cancel")

    @extend_schema(request=PaymentSerializer, responses=SalesOrderSerializer)
    @action(detail=True, methods=["post"])
    @transaction.atomic
    def payment(self, request, pk=None):
        self.require_manager()
        order = SalesOrder.objects.select_for_update().get(
            pk=self.get_object().pk, tenant=request.user.tenant
        )
        if order.status not in {"CONFIRMED", "SHIPPED"}:
            raise serializers.ValidationError(
                {"detail": "Payment can only be recorded for confirmed or shipped orders."}
            )
        serializer = PaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        order.payment_status = serializer.validated_data["payment_status"]
        order.save(update_fields=["payment_status", "updated_at"])
        return Response(self.get_serializer(order).data)

    @extend_schema(responses={(200, "application/pdf"): OpenApiTypes.BINARY})
    @action(detail=True, methods=["get"])
    def invoice(self, request, pk=None):
        order = self.get_object()
        if order.status not in {"CONFIRMED", "SHIPPED"}:
            raise serializers.ValidationError(
                {"detail": "Confirm the order before generating its invoice."}
            )
        return FileResponse(
            render_invoice(order),
            as_attachment=True,
            filename=f"INV-{order.number[3:]}.pdf",
            content_type="application/pdf",
        )


class PurchaseOrderViewSet(OrderViewSet):
    queryset = PurchaseOrder.objects.select_related("supplier", "created_by").prefetch_related(
        "items"
    )
    serializer_class = PurchaseOrderSerializer
    permission_classes = [ManagerOrReadOnly]
    search_fields = ["number", "supplier_name"]
    filterset_fields = ["status", "supplier"]
    ordering_fields = ["created_at", "number"]

    def transition(self, request, action):
        order = self.get_object()
        result = transition_purchase(
            order_id=order.pk, tenant=request.user.tenant, actor=request.user, action=action
        )
        return Response(self.get_serializer(result).data)

    @extend_schema(request=None, responses=PurchaseOrderSerializer)
    @action(detail=True, methods=["post"])
    def receive(self, request, pk=None):
        return self.transition(request, "receive")

    @extend_schema(request=None, responses=PurchaseOrderSerializer)
    @action(detail=True, methods=["post"])
    def cancel(self, request, pk=None):
        return self.transition(request, "cancel")
