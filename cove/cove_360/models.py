from django.db import models
from cove.input.models import SuppliedData
import json


class SuppliedDataStatus(models.Model):
    supplied_data = models.ForeignKey(SuppliedData, on_delete=models.CASCADE)
    passed = models.BooleanField(default=False)
    _publisher = models.TextField(null=True, blank=True)

    @property
    def publisher(self):
        if self._publisher:
            return json.loads(self._publisher)
        return None

    @property
    def can_publish(self):
        if self.publisher:
            return (self.publisher["self_publish"]["enabled"] and self.passed)

        return False
