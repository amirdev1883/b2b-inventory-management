from apps.common.permissions import ManagerOrReadOnly
from apps.common.views import TenantViewSet

from .models import Supplier
from .serializers import SupplierSerializer


class SupplierViewSet(TenantViewSet):
    queryset = Supplier.objects.all()
    serializer_class = SupplierSerializer
    permission_classes = [ManagerOrReadOnly]
    search_fields = ["name", "email", "phone"]
    filterset_fields = ["is_active"]
    ordering_fields = ["name", "created_at"]
