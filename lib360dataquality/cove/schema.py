from urllib.parse import urljoin

from libcove.lib.common import SchemaJsonMixin, get_schema_codelist_paths, load_core_codelists, load_codelist
from libcove.lib.tools import get_request
from .settings import COVE_CONFIG as config
import requests
import json_merge_patch
import json
import os
from typing import Optional

EXTENSIONS_REGISTRY_BASE_URL = "https://raw.githubusercontent.com/ThreeSixtyGiving/extensions-registry/main/extensions/"


class ExtensionsError(Exception):
    pass


class Schema360(SchemaJsonMixin):

    codelists = config["codelists_host"]
    schema_name = config["schema_item_name"]
    pkg_schema_name = config["schema_name"]
    pkg_schema_url = ""  # required by libcove but not in use
    extended = False  # required by libcove but not in use
    extension_codelist_urls = []

    _pkg_schema_obj = {}
    _schema_obj = {}

    def __init__(self, data_dir) -> None:
        # Create dedicated location for schema work
        self.working_dir = os.path.join(data_dir, "schema")
        try:
            os.mkdir(self.working_dir)
        except FileExistsError:
            pass

        # required by lib-cove for CustomRefResolver the trailing / is needed to make sure
        # urljoin does not discard the final part of the location.
        self.schema_host = f"{self.working_dir}/"

        schema_url = urljoin(config["schema_host"], self.schema_name)
        pkg_schema_url = urljoin(config["schema_host"], self.pkg_schema_name)

        self._pkg_schema_obj = get_request(pkg_schema_url).json()
        self._schema_obj = get_request(schema_url).json()

        # Update the pkg schema to no longer point to an external reference for the
        # grants schema.
        # If an extension is applied this will be the local merged version of the grant
        # schema.
        self._pkg_schema_obj["properties"]["grants"]["items"]["$ref"] = self.schema_file

        self.write_pkg_schema_file()
        self.write_schema_file()

        super().__init__()

    @property
    def schema_file(self):
        return os.path.join(self.working_dir, self.schema_name)

    @property
    def pkg_schema_file(self):
        return os.path.join(self.working_dir, self.pkg_schema_name)

    @property
    def schema_str(self):
        return json.dumps(self._schema_obj)

    @property
    def pkg_schema_str(self):
        return json.dumps(self._pkg_schema_obj)

    def write_schema_file(self):
        with open(self.schema_file, "w") as fp:
            fp.write(self.schema_str)

    def write_pkg_schema_file(self):
        with open(self.pkg_schema_file, "w") as fp:
            fp.write(self.pkg_schema_str)

    def process_codelists(self):
        # From libcove common but with support for codelists from 360Giving extensions added.

        self.core_codelist_schema_paths = get_schema_codelist_paths(
            self, use_extensions=False
        )

        extension_unique_files = frozenset(
            url.split("/")[-1] for url in self.extension_codelist_urls
        )

        core_unique_files = frozenset(
            value[0] for value in self.core_codelist_schema_paths.values() if value[0] not in extension_unique_files
        )

        # This loader uses the codelist host from the config + filename that was taken out of the schema
        self.core_codelists = load_core_codelists(
            self.codelists,
            core_unique_files,
            config=self.config if hasattr(self, "config") else None,
        )

        extension_codelists = {}

        for extension_codelist_url in self.extension_codelist_urls:
            codelist_file = extension_codelist_url.split("/")[-1]

            extension_codelists[codelist_file] = load_codelist(
                extension_codelist_url,
                config=self.config if hasattr(self, "config") else None)

        # Update the codelists with any specified by the extension
        # This has the unfortunate side-effect of making cove think these are part of
        # the main standard however we have no current way to differentiate the paths
        self.core_codelists.update(extension_codelists)

        # Ignore. Properties required by libcove:
        self.extended_codelist_schema_paths = self.core_codelist_schema_paths
        self.extended_codelists = self.core_codelists
        self.extended_codelist_urls = {}
        # End ignore

        # we do not want to cache if the requests failed.
        if not self.core_codelists:
            load_core_codelists.cache_clear()
            return

    def resolve_extension(self, json_data) -> Optional[list]:
        """
        If json_data contains an extension id this patches the schemas if the extension is valid
        the internal representation of the schema is replaced with the new patched version.
        We write the new schema file(s) to disk for flattentool and caching purposes.

        Returns an array of extension_infos or None
        """

        try:
            extension_ids = json_data["extensions"]
        except KeyError:
            return None

        if len(extension_ids) == 0:
            raise ExtensionsError("Extension key found but with no value(s)")

        extension_metadatas = []

        for extension_id in extension_ids:
            try:
                r = requests.get(f"{EXTENSIONS_REGISTRY_BASE_URL}/{extension_id}.json")
                r.raise_for_status()
                extension_metadata = r.json()
                extension_metadatas.append(extension_metadata)
            except (json.JSONDecodeError, requests.HTTPError):
                raise ExtensionsError("Couldn't not fetch or parse extension metadata")

            for extension_schemas in extension_metadata["schemas"]:
                try:
                    r = requests.get(extension_schemas["uri"])
                    r.raise_for_status()
                    extension = r.json()
                except (json.JSONDecodeError, requests.HTTPError) as e:
                    raise ExtensionsError(f"Unable to fetch and decode supplied extension: {e}")

                if extension_schemas["target"] not in [
                    self.schema_name,
                    self.pkg_schema_name,
                ]:
                    raise ExtensionsError(f"Unknown target for extension {extension_schemas['target']} not in {[self.schema_name, self.pkg_schema_name]}")

                # Schema (grants) extension
                if extension_schemas["target"] == self.schema_name:
                    self._schema_obj = json_merge_patch.merge(
                        self._schema_obj, extension
                    )

                # Package schema extension
                if extension_schemas["target"] == self.pkg_schema_name:
                    self._pkg_schema_obj = json_merge_patch.merge(
                        self._pkg_schema_obj, extension
                    )

                self.extension_codelist_urls.extend(extension_metadata["codelists"])

        # Write out the new schema objects
        self.write_pkg_schema_file()
        self.write_schema_file()

        return extension_metadatas
