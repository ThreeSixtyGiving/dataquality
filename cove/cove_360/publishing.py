import requests
import os
from urllib.parse import urlparse

from django.conf import settings


def extract_domain(source_url):
    return urlparse(source_url).netloc


def lookup_publisher_by_domain(source_url):
    """Looks up to see if we have a matching domain for source_url in the publisher
    data from REGISTRY_PUBLISHERS_URL. Returns None or Publisher dict"""

    if not settings.DATA_SUBMISSION_ENABLED:
        print("Data submission is not enabled")
        return None

    registry_url = os.environ.get(
        "REGISTRY_PUBLISHERS_URL",
        "https://registry.threesixtygiving.org/publishers.json",
    )

    try:
        r = requests.get(
            registry_url,
            auth=(
                os.environ.get("REGISTRY_PUBLISHERS_USER", None),
                os.environ.get("REGISTRY_PUBLISHERS_PASS", None),
            ),
        )
    except KeyError as e:
        print("Username and password for registry publishers file not set")
        raise e

    r.raise_for_status()

    publishers = r.json()

    data_domain = extract_domain(source_url)

    for publisher in publishers.values():
        if data_domain in publisher["self_publish"]["authorised_domains"]:
            return publisher

    if not publisher:
        print("Domain name for publisher could not be found")

    return None
