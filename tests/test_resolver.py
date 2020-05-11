import json
import pytest
import time
import requests
from unittest.mock import patch

from iglu_client.resolver import Resolver
from iglu_client.core import IgluError, SchemaKey, SchemaVer
from iglu_client.registries import (
    RegistryRefConfig,
    HttpRegistryRef,
    get_bootstrap_registry,
)


@pytest.fixture
def json_config():
    config = """
    {
      "schema": "iglu:com.snowplowanalytics.iglu/resolver-config/jsonschema/1-0-0",
      "data": {
        "cacheSize": 500,
        "repositories": [
          {
            "name": "Iglu Central",
            "priority": 1,
            "vendorPrefixes": [
              "com.snowplowanalytics"
            ],
            "connection": {
              "http": {
                "uri": "http://iglucentral.com"
              }
            }
          },
          {
            "name": "Iglu Local",
            "priority": 2,
            "vendorPrefixes": [
              "com.snowplowanalytics"
            ],
            "connection": {
              "embedded": {
                "path": "."
              }
            }
          }
        ]
      }
    }
    """
    return config


@pytest.fixture
def invalid_config():
    # cacheSize cannot be null
    invalid_config = """
    {
      "schema": "iglu:com.snowplowanalytics.iglu/resolver-config/jsonschema/1-0-0",
      "data": {
        "cacheSize": null,
        "repositories": [
          {
            "name": "Iglu Central",
            "priority": 1,
            "vendorPrefixes": [
              "com.snowplowanalytics"
            ],
            "connection": {
              "http": {
                "uri": "http://iglucentral.com"
              }
            }
          }
        ]
      }
    }
    """
    return invalid_config


@pytest.fixture
def config_with_cacheTtl():
    config_with_cacheTtl = """
    {
      "schema": "iglu:com.snowplowanalytics.iglu/resolver-config/jsonschema/1-0-2",
      "data": {
        "cacheSize": 500,
        "cacheTtl": 1,
        "repositories": [
          {
            "name": "Iglu Central",
            "priority": 0,
            "vendorPrefixes": [
              "com.snowplowanalytics"
            ],
            "connection": {
              "http": {
                "uri": "http://iglucentral.com"
              }
            }
          }
        ]
      }
    }
    """
    return config_with_cacheTtl


@pytest.fixture
def config_with_null_cacheTtl():
    config_with_null_cacheTtl = """
    {
      "schema": "iglu:com.snowplowanalytics.iglu/resolver-config/jsonschema/1-0-2",
      "data": {
        "cacheSize": 500,
        "cacheTtl": null,
        "repositories": [
          {
            "name": "Iglu Central",
            "priority": 0,
            "vendorPrefixes": [
              "com.snowplowanalytics"
            ],
            "connection": {
              "http": {
                "uri": "http://iglucentral.com"
              }
            }
          }
        ]
      }
    }
    """
    return config_with_null_cacheTtl


@pytest.fixture
def config_with_api_key():
    config = """
    {
      "schema": "iglu:com.snowplowanalytics.iglu/resolver-config/jsonschema/1-0-2",
      "data": {
        "cacheSize": 500,
        "repositories": [
          {
            "name": "Iglu Central",
            "priority": 1,
            "vendorPrefixes": [
              "com.snowplowanalytics"
            ],
            "connection": {
              "http": {
                "uri": "http://iglucentral.com",
                "apikey": "fake-key"
              }
            }
          }
        ]
      }
    }
    """
    return config


class TestResolver:
    @pytest.mark.usefixtures("json_config")
    def test_standard_configuration(self, json_config):
        resolver = Resolver.parse(json_config)
        assert len(resolver.registries) == 3
        assert resolver.cacheTtl is None
        assert resolver.registries[1].config.name == "Iglu Central"
        assert resolver.registries[2].config.name == "Iglu Local"

    @pytest.mark.usefixtures("config_with_cacheTtl")
    def test_config_with_cacheTtl(self, config_with_cacheTtl):
        resolver = Resolver.parse(config_with_cacheTtl)
        assert len(resolver.registries) == 2
        assert resolver.cacheTtl == 1
        assert resolver.registries[1].config.name == "Iglu Central"

    @pytest.mark.usefixtures("config_with_null_cacheTtl")
    def test_config_with_null_cacheTtl(self, config_with_null_cacheTtl):
        resolver = Resolver.parse(config_with_null_cacheTtl)
        assert len(resolver.registries) == 2
        assert resolver.cacheTtl is None
        assert resolver.registries[1].config.name == "Iglu Central"

    @pytest.mark.usefixtures("config_with_cacheTtl")
    def test_resolve_cache_invalidated_per_cacheTtl(self, config_with_cacheTtl):
        resolver = Resolver.parse(config_with_cacheTtl)
        assert len(resolver.cache) == 0

        schema = resolver.lookup_schema(
            "iglu:com.snowplowanalytics.iglu/resolver-config/jsonschema/1-0-0"
        )
        assert len(resolver.cache) == 1

        time.sleep(resolver.cacheTtl)

        schema = resolver.lookup_schema(
            "iglu:com.snowplowanalytics.iglu/resolver-config/jsonschema/1-0-0"
        )
        assert len(resolver.cache) == 1
        assert schema["self"]["version"] == "1-0-0"

    @pytest.mark.usefixtures("invalid_config")
    def test_invalid_config_throws_error(self, invalid_config):
        with pytest.raises(IgluError):
            Resolver.parse(invalid_config)

    @pytest.mark.usefixtures("json_config")
    def test_stores_schemas_in_cache(self, json_config):
        ref_config = RegistryRefConfig("Test registry ref", 5, [])
        registry = HttpRegistryRef(ref_config, "http://iglucentral.com")
        resolver = Resolver([registry])
        key1 = SchemaKey(
            "com.snowplowanalytics.snowplow.enrichments",
            "api_request_enrichment_config",
            "jsonschema",
            SchemaVer(1, 0, 0),
        )
        key2 = SchemaKey(
            "com.snowplowanalytics.snowplow",
            "duplicate",
            "jsonschema",
            SchemaVer(1, 0, 0),
        )
        key3 = SchemaKey(
            "com.snowplowanalytics.iglu",
            "resolver-config",
            "jsonschema",
            SchemaVer(1, 0, 0),
        )
        key4 = SchemaKey(
            "com.snowplowanalytics.iglu",
            "resolver-config",
            "jsonschema",
            SchemaVer(1, 0, 0),
        )

        resolver.lookup_schema(key1)
        resolver.lookup_schema(key2)
        resolver.lookup_schema(key2)
        resolver.lookup_schema(key3)
        resolver.lookup_schema(key4)

        assert len(resolver.cache) == 3

    @pytest.mark.usefixtures("json_config")
    def test_can_lookup_schema_in_bootstrap_resolver(self, json_config):
        schema_key = SchemaKey(
            "com.snowplowanalytics.iglu",
            "resolver-config",
            "jsonschema",
            SchemaVer(1, 0, 0),
        )
        schema = get_bootstrap_registry().lookup_schema(schema_key)
        expected = '{ "$schema": "http://iglucentral.com/schemas/com.snowplowanalytics.self-desc/schema/jsonschema/1-0-0#", "description": "Schema for an Iglu resolver\'s configuration", "self": { "vendor": "com.snowplowanalytics.iglu", "name": "resolver-config", "format": "jsonschema", "version": "1-0-0" }, "type": "object", "properties": { "cacheSize": { "type": "number" }, "repositories": { "type": "array", "items": { "type": "object", "properties": { "name": { "type": "string" }, "priority": { "type": "number" }, "vendorPrefixes": { "type": "array", "items": { "type": "string" } }, "connection": { "type": "object", "oneOf": [ { "properties": { "embedded": { "type": "object", "properties": { "path": { "type": "string" } }, "required": ["path"], "additionalProperties": false } }, "required": ["embedded"], "additionalProperties": false }, { "properties": { "http": { "type": "object", "properties": { "uri": { "type": "string", "format": "uri" } }, "required": ["uri"], "additionalProperties": false } }, "required": ["http"], "additionalProperties": false } ] } }, "required": ["name", "priority", "vendorPrefixes", "connection"], "additionalProperties": false } } }, "required": ["cacheSize", "repositories"], "additionalProperties": false }'
        assert schema == json.loads(expected)

    @pytest.mark.usefixtures("config_with_api_key")
    def test_config_with_api_key(self, config_with_api_key):
        with patch.object(requests, "get", wraps=requests.get) as wrapped_get:
            resolver = Resolver.parse(config_with_api_key)
            resolver.lookup_schema(
                "iglu:com.snowplowanalytics.self-desc/schema/jsonschema/1-0-0"
            )
            wrapped_get.assert_called_with(
                "http://iglucentral.com/schemas/com.snowplowanalytics.self-desc/schema/jsonschema/1-0-0",
                headers={"apiKey": "fake-key"},
                timeout=3,
            )
