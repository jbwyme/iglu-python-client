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


class LocalFileSystemRegistryRef(RegistryRef):
    def __init__(self, config: RegistryRefConfig, path: str):
        self.config = config
        self.class_priority = 1
        self.descriptor = "embedded"
        self.root = path

    def lookup_schema(self, schema_key: SchemaKey) -> dict:
        schema_path = os.path.join(self.root, "schemas", schema_key.as_path())
        try:
            with open(schema_path) as f:
                return json.loads(f.read())
        except FileNotFoundError:
            return None


class HttpRegistryRef(RegistryRef):
    def __init__(self, config: RegistryRefConfig, uri: str):
        self.config = config
        self.class_priority = 100
        self.descriptor = "HTTP"
        self.uri = uri

    def lookup_schema(self, schema_key: SchemaKey, max_retries=3) -> str:
        schema_uri = "{uri}/schemas/{schema_path}".format(
            uri=self.uri, schema_path=schema_key.as_path()
        )
        times_retried = 0

        while True:
            r = None

            try:
                r = requests.get(schema_uri, timeout=3)
            except requests.exceptions.ConnectionError as e:
                raise IgluError(
                    "Iglu registry {config_name} is not available: {error}".format(
                        config_name=self.config.name, error=e.message
                    )
                )

            if r.ok:
                return r.json()
            elif times_retried == max_retries:
                return None

            times_retried += 1


class NotFound(object):
    def __init__(self, registry: str):
        self.registry = registry

    def __str__(self):
        return "Not found in {registry}".format(registry=self.registry)

    def __repr__(self):
        return "Not found in {registry}".format(registry=self.registry)


class LookupFailure(object):
    def __init__(self, registry: str, reason: str):
        self.reason = reason
        self.registry = registry

    def __str__(self):
        return "Lookup failure at {registry} because {reason}".format(
            registry=self.registry, reason=self.reason
        )

    def __repr__(self):
        return "Lookup failure at {registry} because {reason}".format(
            registry=self.registry, reason=self.reason
        )


_bootstrap_registry = None


def get_bootstrap_registry() -> LocalFileSystemRegistryRef:
    global _bootstrap_registry
    if not _bootstrap_registry:
        _config = RegistryRefConfig(
            name="Iglu Client Embedded", priority=0, vendor_prefixes=[]
        )
        _root = os.path.dirname(os.path.realpath(__file__))
        _path = os.path.join(_root, "embedded-repo")
        _bootstrap_registry = LocalFileSystemRegistryRef(_config, _path)
    return _bootstrap_registry
