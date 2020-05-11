import jsonschema
import time
from typing import List, Union

from .core import SchemaKey, IgluError
from .registries import (
    RegistryRef,
    RegistryRefConfig,
    HttpRegistryRef,
    EmbeddedRegistryRef,
    get_bootstrap_registry,
)


class Resolver(object):
    def __init__(self, registries: List[RegistryRef], cacheTtl: int = None):
        self.registries = [get_bootstrap_registry()] + registries
        self.cache = {}
        self.cacheTtl = cacheTtl

    # Lookup schema in cache or try to fetch
    def lookup_schema(self, schema_key: Union[str, SchemaKey]) -> dict:
        lookup_time = time.time()
        if isinstance(schema_key, str):
            schema_key = SchemaKey.parse_key(schema_key)

        schema_path = schema_key.as_path()
        failures = []

        cache_result = self.cache.get(schema_path)
        if cache_result:
            if self.cacheTtl:
                store_time = cache_result[1]
                time_diff = lookup_time - store_time
                if time_diff >= self.cacheTtl:
                    del self.cache[schema_path]
                    cache_result = None
                else:
                    return cache_result[0]
            else:
                return cache_result[0]

        if not cache_result:  # Fetch from every registry
            for registry in Resolver.prioritize_repos(schema_key, self.registries):
                try:
                    lookup_result = registry.lookup_schema(schema_key)
                except Exception as e:
                    failures.append(LookupFailure(registry.config.name, e))
                else:
                    if lookup_result is None:
                        failures.append(NotFound(registry.config.name))
                    else:
                        break

            if not lookup_result:
                raise ResolverError(failures, schema_key)
            else:
                store_time = time.time()
                self.cache[schema_path] = [lookup_result, store_time]
                return lookup_result

    @classmethod
    def parse(cls, conf_json: str):
        from .self_describing_json import SelfDescribingJson

        conf = SelfDescribingJson.parse(conf_json)
        resolver = Resolver([])
        try:
            conf.validate(resolver)
        except jsonschema.exceptions.ValidationError as e:
            raise IgluError(
                "Invalid resolver configuration. Data did not validate against schema: %s"
                % e.message
            )

        registries = [
            cls.parse_registry(registry) for registry in conf.data["repositories"]
        ]
        cacheTtl = conf.data.get("cacheTtl")
        return Resolver(registries, cacheTtl)

    @staticmethod
    def parse_registry(config: dict) -> RegistryRef:
        ref_config = RegistryRefConfig.parse(config)
        if config.get("connection", {}).get("http"):
            return HttpRegistryRef(
                ref_config,
                config["connection"]["http"]["uri"],
                config["connection"]["http"].get("apikey"),
            )
        elif config.get("connection", {}).get("embedded"):
            return EmbeddedRegistryRef(
                ref_config, config["connection"]["embedded"]["path"]
            )
        else:
            raise IgluError("Incorrect RegistryRef")

    def prioritize_repos(
        schema_key: SchemaKey, registry_refs: List[RegistryRef]
    ) -> List[RegistryRef]:
        registry_refs = sorted(
            registry_refs, key=lambda ref: -1 if ref.vendor_matched(schema_key) else 1
        )
        registry_refs = sorted(registry_refs, key=lambda ref: ref.class_priority)
        registry_refs = sorted(registry_refs, key=lambda ref: ref.config.priority)
        return registry_refs


class ResolverError(Exception):
    def __init__(self, failures, schema_key: SchemaKey):
        self.failures = failures
        self.schema_key = schema_key
        failures_str = "; ".join([str(failure) for failure in failures])
        self.message = "Schema [{schema_uri}] was not found in [{lookup_count}] registries with following attempts: [{failures}]".format(
            schema_uri=schema_key.as_uri(),
            lookup_count=len(failures),
            failures=failures_str,
        )


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
