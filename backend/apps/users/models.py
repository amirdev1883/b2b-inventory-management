from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models.functions import Lower

from apps.common.models import TimestampedModel


class Tenant(TimestampedModel):
    name = models.CharField(max_length=160)
    currency = models.CharField(
        max_length=3, default="CAD", choices=[(c, c) for c in ["CAD", "USD", "EUR", "GBP", "AUD"]]
    )
    address = models.TextField(blank=True, max_length=1000)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    tax_number = models.CharField(max_length=80, blank=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name


class UserManager(BaseUserManager):
    use_in_migrations = True

    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required.")
        user = self.model(email=email.strip().lower(), **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault("is_staff", True)
        extra_fields.setdefault("is_superuser", True)
        extra_fields.setdefault("role", "ADMIN")
        if not extra_fields["is_staff"] or not extra_fields["is_superuser"]:
            raise ValueError("A superuser must have is_staff and is_superuser enabled.")
        return self.create_user(email, password, **extra_fields)


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = "ADMIN", "Admin"
        MANAGER = "MANAGER", "Manager"
        STAFF = "STAFF", "Staff"

    username = None
    email = models.EmailField(unique=True)
    tenant = models.ForeignKey(Tenant, null=True, blank=True, on_delete=models.PROTECT)
    role = models.CharField(max_length=10, choices=Role.choices, default=Role.STAFF)
    objects = UserManager()
    USERNAME_FIELD = "email"
    REQUIRED_FIELDS = []

    class Meta:
        constraints = [
            models.UniqueConstraint(Lower("email"), name="unique_user_email_ci"),
            models.CheckConstraint(
                condition=models.Q(tenant__isnull=False) | models.Q(is_superuser=True),
                name="user_requires_tenant",
            ),
        ]

    def __str__(self):
        return self.email
