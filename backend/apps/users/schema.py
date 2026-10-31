from drf_spectacular.contrib.rest_framework_simplejwt import SimpleJWTScheme


class TenantJWTScheme(SimpleJWTScheme):
    target_class = "apps.users.authentication.ActiveTenantJWTAuthentication"
    priority = 1
