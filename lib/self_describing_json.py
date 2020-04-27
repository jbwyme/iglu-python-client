from .core import IgluError, SchemaKey
from .resolver import Resolver


class SelfDescribingJson(object):

    # Constructor. To initalize from string - use static parse_schemaver
    def __init__(self, schema, data):
        self.schema = schema
        self.data = data
        self.isValid = False

    def to_json(self) -> dict:
        return {
            "schema": self.schema.as_uri(),
            "data": self.data,
        }

    def validate(self, resolver: Resolver) -> True:
        resolver.validate(self.to_json())
        self.isValid = True
        return self.isValid

    def valid(self, resolver: Resolver) -> bool:
        try:
            return self.isValid or self.validate(resolver)
        except Exception:
            return False

    @classmethod
    def parse_json(cls, json):
        schema = json.get("schema")
        data = json.get("data")
        if not schema or not data:
            raise IgluError("Not a self-describing JSON")
        schema_key = SchemaKey.parse_key(schema)
        return cls(schema_key, data)
