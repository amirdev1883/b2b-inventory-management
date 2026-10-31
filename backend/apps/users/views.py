from django.conf import settings
from django.contrib.auth import authenticate
from django.contrib.auth.tokens import default_token_generator
from django.core.mail import send_mail
from django.db import transaction
from django.middleware.csrf import get_token
from django.utils.decorators import method_decorator
from django.utils.encoding import force_bytes
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import generics, mixins, serializers, viewsets
from rest_framework.exceptions import AuthenticationFailed
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.exceptions import TokenError
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.utils import get_md5_hash_password

from apps.common.permissions import IsBusinessAdmin

from .models import Tenant, User
from .serializers import (
    LoginSerializer,
    PasswordChangeSerializer,
    PasswordResetConfirmSerializer,
    PasswordResetRequestSerializer,
    RegistrationSerializer,
    SessionSerializer,
    TenantSerializer,
    UserSerializer,
    check_password,
)


def session_response(user, status=200):
    refresh = RefreshToken.for_user(user)
    response = Response(
        {
            "access": str(refresh.access_token),
            "user": UserSerializer(user).data,
            "business": TenantSerializer(user.tenant).data,
        },
        status=status,
    )
    set_refresh_cookie(response, str(refresh))
    return response


def set_refresh_cookie(response, token):
    response.set_cookie(
        settings.REFRESH_COOKIE_NAME,
        token,
        httponly=True,
        secure=settings.REFRESH_COOKIE_SECURE,
        samesite="Lax",
        path="/api/auth/",
        max_age=int(settings.SIMPLE_JWT["REFRESH_TOKEN_LIFETIME"].total_seconds()),
    )


@method_decorator(csrf_protect, name="dispatch")
class PublicAuthView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def get_authenticate_header(self, request):
        return "Bearer"


class CsrfView(PublicAuthView):
    throttle_classes = []

    @extend_schema(
        responses={200: {"type": "object", "properties": {"csrfToken": {"type": "string"}}}}
    )
    def get(self, request):
        return Response({"csrfToken": get_token(request)})


class RegisterView(PublicAuthView):
    @extend_schema(request=RegistrationSerializer, responses={201: SessionSerializer})
    def post(self, request):
        serializer = RegistrationSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        return session_response(serializer.save(), status=201)


class LoginView(PublicAuthView):
    @extend_schema(request=LoginSerializer, responses=SessionSerializer)
    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = authenticate(
            request,
            email=serializer.validated_data["email"].strip().lower(),
            password=serializer.validated_data["password"],
        )
        if not user or not user.tenant_id or not user.tenant.is_active:
            raise AuthenticationFailed("Invalid email or password.")
        return session_response(user)


class RefreshView(PublicAuthView):
    throttle_scope = "session"

    @extend_schema(request=None, responses=SessionSerializer)
    def post(self, request):
        try:
            # Lock the token row to serialize rotations, preventing concurrent replay.
            from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

            raw = request.COOKIES.get(settings.REFRESH_COOKIE_NAME, "")
            with transaction.atomic():
                refresh = RefreshToken(raw)
                OutstandingToken.objects.select_for_update().get(jti=refresh["jti"])
                refresh.check_blacklist()
                user = User.objects.select_related("tenant").get(
                    pk=refresh["user_id"], is_active=True
                )
                if not user.tenant_id or not user.tenant.is_active:
                    raise AuthenticationFailed("An active business account is required.")
                if refresh.get("hash_password") != get_md5_hash_password(user.password):
                    raise AuthenticationFailed("Password changed. Please sign in again.")
                refresh.blacklist()
                return session_response(user)
        except (TokenError, User.DoesNotExist, OutstandingToken.DoesNotExist) as exc:
            raise AuthenticationFailed("Session expired. Please sign in again.") from exc


class LogoutView(PublicAuthView):
    throttle_scope = "session"

    @extend_schema(request=None, responses={204: None})
    def post(self, request):
        try:
            RefreshToken(request.COOKIES.get(settings.REFRESH_COOKIE_NAME, "")).blacklist()
        except TokenError:
            pass
        response = Response(status=204)
        response.delete_cookie(settings.REFRESH_COOKIE_NAME, path="/api/auth/", samesite="Lax")
        return response


class MeView(generics.RetrieveAPIView):
    serializer_class = UserSerializer

    def get_object(self):
        return self.request.user


class BusinessView(generics.RetrieveUpdateAPIView):
    serializer_class = TenantSerializer
    http_method_names = ["get", "patch", "head", "options"]

    def get_permissions(self):
        return super().get_permissions() if self.request.method == "GET" else [IsBusinessAdmin()]

    def get_object(self):
        return self.request.user.tenant


class UserViewSet(
    mixins.ListModelMixin,
    mixins.RetrieveModelMixin,
    mixins.CreateModelMixin,
    mixins.UpdateModelMixin,
    viewsets.GenericViewSet,
):
    permission_classes = [IsBusinessAdmin]
    serializer_class = UserSerializer
    queryset = User.objects.order_by("email")
    search_fields = ["email", "first_name", "last_name"]
    filterset_fields = ["role", "is_active"]

    def get_queryset(self):
        if getattr(self, "swagger_fake_view", False):
            return self.queryset.none()
        return self.queryset.filter(tenant_id=self.request.user.tenant_id, is_superuser=False)

    def perform_create(self, serializer):
        serializer.save(tenant=self.request.user.tenant)

    def update(self, request, *args, **kwargs):
        with transaction.atomic():
            Tenant.objects.select_for_update().get(pk=request.user.tenant_id)
            instance = self.get_object()
            serializer = self.get_serializer(
                instance, data=request.data, partial=kwargs.pop("partial", False)
            )
            serializer.is_valid(raise_exception=True)
            data = serializer.validated_data
            removing_admin = data.get("role", instance.role) != "ADMIN" or not data.get(
                "is_active", instance.is_active
            )
            if instance.role == "ADMIN" and instance.is_active and removing_admin:
                if (
                    not self.get_queryset()
                    .filter(role="ADMIN", is_active=True)
                    .exclude(pk=instance.pk)
                    .exists()
                ):
                    raise serializers.ValidationError(
                        {"detail": "At least one active admin must remain."}
                    )
            serializer.save()
            return Response(serializer.data)


class PasswordResetRequestView(PublicAuthView):
    throttle_scope = "password_reset"

    @extend_schema(request=PasswordResetRequestSerializer, responses={200: {"type": "object"}})
    def post(self, request):
        serializer = PasswordResetRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.filter(
            email__iexact=serializer.validated_data["email"], is_active=True, tenant__is_active=True
        ).first()
        if user:
            uid = urlsafe_base64_encode(force_bytes(user.pk))
            token = default_token_generator.make_token(user)
            origin = settings.FRONTEND_URL
            send_mail(
                "Reset your B2B workspace password",
                f"Reset your password: {origin}/?reset_uid={uid}&reset_token={token}\nThis link expires in one hour.",
                settings.DEFAULT_FROM_EMAIL,
                [user.email],
            )
        return Response({"detail": "If an active account exists, a reset link has been sent."})


class PasswordResetConfirmView(PublicAuthView):
    @extend_schema(request=PasswordResetConfirmSerializer, responses={200: {"type": "object"}})
    @transaction.atomic
    def post(self, request):
        serializer = PasswordResetConfirmSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            uid = urlsafe_base64_decode(data["uid"]).decode()
            user = User.objects.select_for_update(of=("self",)).get(
                pk=uid, is_active=True, tenant__is_active=True
            )
        except (ValueError, UnicodeDecodeError, User.DoesNotExist) as exc:
            raise serializers.ValidationError({"detail": "Invalid or expired reset link."}) from exc
        if not default_token_generator.check_token(user, data["token"]):
            raise serializers.ValidationError({"detail": "Invalid or expired reset link."})
        check_password(data["password"], user)
        user.set_password(data["password"])
        user.save(update_fields=["password"])
        return Response({"detail": "Password updated. Please sign in."})


class PasswordChangeView(APIView):
    @extend_schema(request=PasswordChangeSerializer, responses=SessionSerializer)
    @transaction.atomic
    def post(self, request):
        serializer = PasswordChangeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = User.objects.select_for_update().get(pk=request.user.pk)
        if not user.check_password(serializer.validated_data["current_password"]):
            raise serializers.ValidationError(
                {"current_password": "Current password is incorrect."}
            )
        password = check_password(serializer.validated_data["new_password"], user)
        user.set_password(password)
        user.save(update_fields=["password"])
        return session_response(user)
