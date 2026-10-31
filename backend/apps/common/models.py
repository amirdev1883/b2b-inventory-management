import uuid

from django.core.exceptions import ValidationError
from django.db import models


class TimestampedModel(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True
        ordering = ["-created_at"]


class TenantModel(TimestampedModel):
    tenant = models.ForeignKey("users.Tenant", on_delete=models.PROTECT)

    class Meta(TimestampedModel.Meta):
        abstract = True

    def clean(self):
        super().clean()
        for field in self._meta.fields:
            if field.is_relation and field.name != "tenant" and getattr(self, field.attname):
                related = getattr(self, field.name)
                if hasattr(related, "tenant_id") and related.tenant_id != self.tenant_id:
                    raise ValidationError({field.name: "Must belong to the same business."})
