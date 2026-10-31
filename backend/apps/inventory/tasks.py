from datetime import timedelta

from celery import shared_task
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import F, Q
from django.utils import timezone

from apps.users.models import Tenant

from .models import Product


@shared_task(autoretry_for=(OSError,), retry_backoff=True, max_retries=3)
def send_low_stock_alerts():
    """Daily maximum per product. Row locks serialize concurrent periodic workers."""
    sent = 0
    cutoff = timezone.now() - timedelta(hours=24)
    for tenant in Tenant.objects.filter(is_active=True).iterator():
        recipients = list(
            tenant.user_set.filter(role__in=["ADMIN", "MANAGER"], is_active=True).values_list(
                "email", flat=True
            )
        )
        if not recipients:
            continue
        with transaction.atomic():
            products = list(
                Product.objects.select_for_update()
                .filter(
                    tenant=tenant,
                    is_active=True,
                    quantity__lte=F("reserved_quantity") + F("reorder_level"),
                )
                .filter(
                    Q(last_low_stock_alert_at__isnull=True) | Q(last_low_stock_alert_at__lt=cutoff)
                )
            )
            if not products:
                continue
            lines = [
                f"{p.sku} — {p.name}: {p.available_quantity} available (reorder at {p.reorder_level})"
                for p in products
            ]
            send_mail(
                f"Low stock · {tenant.name}",
                "\n".join(lines),
                settings.DEFAULT_FROM_EMAIL,
                recipients,
                fail_silently=False,
            )
            Product.objects.filter(pk__in=[p.pk for p in products]).update(
                last_low_stock_alert_at=timezone.now()
            )
            sent += 1
    return sent
