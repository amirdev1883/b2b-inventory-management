from apps.analytics.views import DashboardView
from apps.common.views import health, readiness
from apps.inventory.views import ProductViewSet, StockMovementViewSet
from apps.orders.views import PurchaseOrderViewSet, SalesOrderViewSet
from apps.suppliers.views import SupplierViewSet
from apps.users.views import (
    BusinessView,
    CsrfView,
    LoginView,
    LogoutView,
    MeView,
    PasswordChangeView,
    PasswordResetConfirmView,
    PasswordResetRequestView,
    RefreshView,
    RegisterView,
    UserViewSet,
)
from django.contrib import admin
from django.urls import include, path, re_path
from django.views.generic import TemplateView
from drf_spectacular.views import SpectacularAPIView, SpectacularRedocView, SpectacularSwaggerView
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("products", ProductViewSet)
router.register("suppliers", SupplierViewSet)
router.register("sales-orders", SalesOrderViewSet)
router.register("purchase-orders", PurchaseOrderViewSet)
router.register("stock-movements", StockMovementViewSet)
router.register("users", UserViewSet)
urlpatterns = [
    path("health/", health),
    path("ready/", readiness),
    path("admin/", admin.site.urls),
    path("api/auth/csrf/", CsrfView.as_view()),
    path("api/auth/register/", RegisterView.as_view()),
    path("api/auth/login/", LoginView.as_view()),
    path("api/auth/refresh/", RefreshView.as_view()),
    path("api/auth/logout/", LogoutView.as_view()),
    path("api/auth/me/", MeView.as_view()),
    path("api/auth/password-change/", PasswordChangeView.as_view()),
    path("api/auth/password-reset/", PasswordResetRequestView.as_view()),
    path("api/auth/password-reset/confirm/", PasswordResetConfirmView.as_view()),
    path("api/business/", BusinessView.as_view()),
    path("api/analytics/dashboard/", DashboardView.as_view()),
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path("api/redoc/", SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path("api/", include(router.urls)),
    re_path(
        r"^(?!api/|admin/|health/|ready/|static/).*$",
        TemplateView.as_view(template_name="index.html"),
    ),
]
admin.site.site_header = "B2B platform administration"
admin.site.site_title = "B2B administration"
