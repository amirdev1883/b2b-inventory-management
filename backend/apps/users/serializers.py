from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import IntegrityError, transaction
from rest_framework import serializers

from .models import Tenant, User


def check_password(value, user):
    try:
        validate_password(value, user)
    except DjangoValidationError as exc:
        raise serializers.ValidationError(list(exc.messages)) from exc
    return value


class TenantSerializer(serializers.ModelSerializer):
    class Meta:
        model = Tenant
        fields = ["id", "name", "currency", "address", "email", "phone", "tax_number"]
        read_only_fields = ["id", "currency"]


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False, min_length=10, max_length=128)

    class Meta:
        model = User
        fields = [
            "id",
            "email",
            "first_name",
            "last_name",
            "role",
            "is_active",
            "password",
            "date_joined",
        ]
        read_only_fields = ["id", "date_joined"]

    def validate_email(self, value):
        value = value.strip().lower()
        qs = User.objects.filter(email__iexact=value)
        if self.instance:
            qs = qs.exclude(pk=self.instance.pk)
        if qs.exists():
            raise serializers.ValidationError("An account with this email already exists.")
        return value

    def validate(self, attrs):
        if not self.instance and not attrs.get("password"):
            raise serializers.ValidationError({"password": "A password is required."})
        if "password" in attrs:
            check_password(attrs["password"], self.instance or User(email=attrs.get("email", "")))
        return attrs

    def create(self, validated_data):
        return User.objects.create_user(**validated_data)

    def update(self, instance, validated_data):
        password = validated_data.pop("password", None)
        for field, value in validated_data.items():
            setattr(instance, field, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance


class RegistrationSerializer(serializers.Serializer):
    business_name = serializers.CharField(max_length=160)
    currency = serializers.ChoiceField(
        choices=Tenant._meta.get_field("currency").choices, default="CAD"
    )
    email = serializers.EmailField()
    first_name = serializers.CharField(max_length=150)
    last_name = serializers.CharField(max_length=150, required=False, allow_blank=True)
    password = serializers.CharField(write_only=True, min_length=10, max_length=128)

    def validate(self, attrs):
        attrs["email"] = attrs["email"].strip().lower()
        check_password(
            attrs["password"], User(email=attrs["email"], first_name=attrs["first_name"])
        )
        if User.objects.filter(email__iexact=attrs["email"]).exists():
            raise serializers.ValidationError(
                {"email": "An account with this email already exists."}
            )
        return attrs

    def create(self, validated_data):
        try:
            with transaction.atomic():
                tenant = Tenant.objects.create(
                    name=validated_data.pop("business_name"),
                    currency=validated_data.pop("currency"),
                )
                return User.objects.create_user(
                    tenant=tenant, role=User.Role.ADMIN, **validated_data
                )
        except IntegrityError as exc:
            raise serializers.ValidationError(
                {"email": "An account with this email already exists."}
            ) from exc


class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, max_length=128)


class SessionSerializer(serializers.Serializer):
    access = serializers.CharField()
    user = UserSerializer()
    business = TenantSerializer()


class PasswordResetRequestSerializer(serializers.Serializer):
    email = serializers.EmailField()


class PasswordResetConfirmSerializer(serializers.Serializer):
    uid = serializers.CharField(max_length=100)
    token = serializers.CharField(max_length=200)
    password = serializers.CharField(write_only=True, min_length=10, max_length=128)


class PasswordChangeSerializer(serializers.Serializer):
    current_password = serializers.CharField(write_only=True, max_length=128)
    new_password = serializers.CharField(write_only=True, min_length=10, max_length=128)
