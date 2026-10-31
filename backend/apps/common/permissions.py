from rest_framework.permissions import SAFE_METHODS, BasePermission


class IsBusinessAdmin(BasePermission):
    def has_permission(self, request, view):
        return bool(request.user.is_authenticated and request.user.role == "ADMIN")


class ManagerOrReadOnly(BasePermission):
    def has_permission(self, request, view):
        return bool(
            request.user.is_authenticated
            and (request.method in SAFE_METHODS or request.user.role in {"ADMIN", "MANAGER"})
        )
