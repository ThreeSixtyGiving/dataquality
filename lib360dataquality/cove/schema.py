from urllib.parse import urljoin

from libcove.lib.common import SchemaJsonMixin
from .settings import COVE_CONFIG as config


class Schema360(SchemaJsonMixin):
    schema_host = config['schema_host']
    schema_name = config['schema_item_name']
    pkg_schema_name = config['schema_name']
    schema_url = urljoin(schema_host, schema_name)
    pkg_schema_url = urljoin(schema_host, pkg_schema_name)
    codelists = config['codelists_host']
