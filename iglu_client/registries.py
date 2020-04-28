import json
import requests
import os

from .core import SchemaKey, IgluError


class RegistryRefConfig(object):
    def __init__(self, name, priority, vendor_prefixes):
        self.name = name
        self.priority = priority
        self.vendor_prefixes = vendor_prefixes

    @staticmethod
    def parse(config):
        return RegistryRefConfig(
            config["name"], config["priority"], config["vendorPrefixes"]
        )


class RegistryRef(object):
    config: RegistryRefConfig = None
    class_priority: int = None
    descriptor: str = None

    def lookup_schema(self, schema_key: SchemaKey) -> str:
        raise Exception("lookup_schema must be implement")

    def vendor_matched(self, schema_key: SchemaKey) -> bool:
        matches = [
            p for p in self.config.vendor_prefixes if schema_key.vendor.startswith(p)
        ]
        return len(matches) > 0


class EmbeddedRegistryRef(RegistryRef):
    def __init__(self, config: RegistryRefConfig, path: str):
        self.config = config
        self.class_priority = 1
        self.descriptor = "bootstrap"
        self.root = path

    def lookup_schema(self, schema_key: SchemaKey) -> dict:
        schema_path = os.path.join(self.root, "schemas", schema_key.as_path())
        try:
            with open(schema_path) as f:
                return json.loads(f.read())
        except FileNotFoundError:
            return None


class HttpRegistryRef(RegistryRef):
    def __init__(self, config: RegistryRefConfig, uri: str, api_key=None):
        self.config = config
        self.class_priority = 100
        self.descriptor = "HTTP"
        self.uri = uri
        self.api_key = api_key

    def lookup_schema(self, schema_key: SchemaKey, max_retries=3) -> str:
        schema_uri = "{uri}/schemas/{schema_path}".format(
            uri=self.uri, schema_path=schema_key.as_path()
        )
        times_retried = 0

        headers = {}
        if self.api_key:
            headers["apiKey"] = self.api_key

        while True:
            r = None

            try:
                r = requests.get(schema_uri, headers=headers, timeout=3)
            except requests.exceptions.ConnectionError as e:
                raise IgluError(
                    "Iglu registry {config_name} is not available: {error}".format(
                        config_name=self.config.name, error=e
                    )
                )

            if r.ok:
                return r.json()
            elif times_retried == max_retries:
                return None

            times_retried += 1


_bootstrap_registry = None


def get_bootstrap_registry() -> EmbeddedRegistryRef:
    global _bootstrap_registry
    if not _bootstrap_registry:
        _config = RegistryRefConfig(
            name="Iglu Client Bootstrap", priority=0, vendor_prefixes=[]
        )
        _bootstrap_registry = EmbeddedRegistryRef(
            _config, os.path.dirname(os.path.realpath(__file__))
        )
    return _bootstrap_registry
