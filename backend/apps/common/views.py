from django.db import connection
from django.http import JsonResponse
from rest_framework import viewsets


class TenantViewSet(viewsets.ModelViewSet):
    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        return self.queryset.filter(tenant_id=self.request.user.tenant_id)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)


def health(request):
    return JsonResponse({"status": "ok"})


def readiness(request):
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
    except Exception:
        return JsonResponse({"status": "unavailable"}, status=503)
    return JsonResponse({"status": "ready"})
