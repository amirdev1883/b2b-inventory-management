from django.db import models
from django.db.models.functions import Lower

from apps.common.models import TenantModel


class Supplier(TenantModel):
    name = models.CharField(max_length=160)
    email = models.EmailField(blank=True)
    phone = models.CharField(max_length=40, blank=True)
    address = models.TextField(blank=True, max_length=1000)
    notes = models.TextField(blank=True, max_length=2000)
    is_active = models.BooleanField(default=True)

    class Meta(TenantModel.Meta):
        constraints = [
            models.UniqueConstraint(Lower("name"), "tenant", name="unique_supplier_name_per_tenant")
        ]

    def __str__(self):
        return self.name
