from django.db import models
from cove.input.models import SuppliedData
import requests
import os
import json
from urllib.parse import urlparse


class SuppliedDataStatus(models.Model):
    supplied_data = models.ForeignKey(SuppliedData, on_delete=models.CASCADE)
    passed = models.BooleanField(default=False)
    publisher = models.TextField(null=True, blank=True)

    @property
    def can_publish(self):
        if self.publisher:
            publisher = json.loads(self.publisher)
            return (publisher["self_publish"]["enabled"] and self.passed)

        return False


    def save(self, *args, **kwargs):
        registry_url = os.environ.get(
            "REGISTRY_PUBLISHERS_URL",
            "https://data.threesixtygiving.org/publishers.json",
        )
        r = requests.get(registry_url)
        r.raise_for_status()

        publishers = r.json()

        data_domain = urlparse(self.supplied_data.source_url).netloc

        for publisher in publishers.values():
            if data_domain in publisher["self_publish"]["authorised_domains"]:
                self.publisher = json.dumps(publisher)
                break

        super(SuppliedDataStatus, self).save(*args, **kwargs)
