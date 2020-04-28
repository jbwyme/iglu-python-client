import json
import jsonschema

from .core import IgluError, SchemaKey
from .resolver import Resolver


class SelfDescribingJson(object):

    # Constructor. To initalize from string - use static parse_schemaver
    def __init__(self, schema_key: SchemaKey, data: dict):
        self.schema_key = schema_key
        self.data = data
        self.isValid = False

    def to_json(self) -> dict:
        return json.dumps({"schema": self.schema_key.as_uri(), "data": self.data})

    def validate(self, resolver: Resolver) -> True:
        schema = resolver.lookup_schema(self.schema_key)
        jsonschema.validate(instance=self.data, schema=schema)
        self.isValid = True
        return self.isValid

    def valid(self, resolver: Resolver) -> bool:
        try:
            return self.isValid or self.validate(resolver)
        except Exception:
            return False

    @classmethod
    def parse(cls, payload_json: str):
        payload = json.loads(payload_json)

        schema_uri = payload.get("schema")
        if not schema_uri:
            raise IgluError(
                "JSON instance is not self-describing (schema property is absent):\n {json}".format(
                    json=json.to_json()
                )
            )

        data = payload.get("data")
        if not data:
            raise IgluError(
                "JSON instance is not self-describing (data proprty is absent):\n {json}".format(
                    json=json.to_json()
                )
            )

        schema_key = SchemaKey.parse_key(schema_uri)
        return cls(schema_key, data)
