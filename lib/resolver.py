import jsonschema
import time
from typing import List

from .core import SchemaKey, IgluError
from .registries import (
    LookupFailure,
    NotFound,
    ResolverError,
    RegistryRef,
    RegistryRefConfig,
    HttpRegistryRef,
    get_bootstrap_registry,
)

# Iglu Client. Able to fetch schemas only from Iglu Central


class Resolver(object):
    def __init__(self, registries: List[RegistryRef], cacheTtl: int = None):
        self.registries = [get_bootstrap_registry()] + registries
        self.cache = {}
        self.cacheTtl = cacheTtl

    # Lookup schema in cache or try to fetch
    def lookup_schema(self, schema_key: SchemaKey) -> dict:
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
    def parse(cls, json):
        schema_key = Resolver.get_schema_key(json)
        # todo: figure this out
        schema = get_bootstrap_registry().lookup_schema(schema_key)
        data = cls.get_data(json)
        try:
            print("schema: %s" % schema)
            jsonschema.validate(instance=data, schema=schema)
        except jsonschema.exceptions.ValidationError as e:
            raise IgluError(
                "Invalid resolver configuration. Data did not validate against schema: %s"
                % e.message
            )

        registries = [cls.parse_registry(registry) for registry in data["repositories"]]
        cacheTtl = json["data"].get("cacheTtl")
        return Resolver(registries, cacheTtl)

    @staticmethod
    def parse_registry(config) -> RegistryRef:
        ref_config = RegistryRefConfig.parse(config)
        if config.get("connection", {}).get("http"):
            return HttpRegistryRef(ref_config, config["connection"]["http"]["uri"])
        else:
            raise IgluError("Incorrect RegistryRef")

    @staticmethod
    def get_schema_key(json) -> SchemaKey:
        schema_uri = json.get("schema")
        if not schema_uri:
            raise IgluError(
                "JSON instance is not self-describing (schema property is absent):\n {json}".format(
                    json=json.to_json()
                )
            )
        else:
            return SchemaKey.parse_key(schema_uri)

    @staticmethod
    def get_data(json) -> dict:
        data = json.get("data")
        if not data:
            raise IgluError(
                "JSON instance is not self-describing (data proprty is absent):\n {json}".format(
                    json=json.to_json()
                )
            )
        else:
            return data

    # Return true or throw exception
    def validate(self, json) -> True:
        schema_key = Resolver.get_schema_key(json)
        data = Resolver.get_data(json)
        schema = self.lookup_schema(schema_key)
        print("schema: %s" % schema)
        jsonschema.validate(instance=data, schema=schema)
        return True

    def prioritize_repos(
        schema_key: SchemaKey, registry_refs: List[RegistryRef]
    ) -> List[RegistryRef]:
        registry_refs = sorted(
            registry_refs, key=lambda ref: -1 if ref.vendor_matched(schema_key) else 1
        )
        registry_refs = sorted(registry_refs, key=lambda ref: ref.class_priority)
        registry_refs = sorted(registry_refs, key=lambda ref: ref.config.priority)
        return registry_refs
