from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.authentication import JWTAuthentication


class ActiveTenantJWTAuthentication(JWTAuthentication):
    def get_user(self, validated_token):
        user = super().get_user(validated_token)
        if not user.tenant_id or not user.tenant.is_active:
            raise AuthenticationFailed("An active business account is required.")
        return user
