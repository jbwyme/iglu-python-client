import re
import jsonschema


# Regular expression to extract metadata from self-describing JSON
URI_REGEX = "^iglu:([a-zA-Z0-9\\-_.]+)/([a-zA-Z0-9\\-_]+)/([a-zA-Z0-9\\-_]+)/([1-9][0-9]*(?:-(?:0|[1-9][0-9]*)){2})$"

# Regular expression to extract all parts of SchemaVer: MODEL, REVISION,
# ADDITION
SCHEMAVER_REGEX = "^([1-9][0-9]*)-(0|[1-9][0-9]*)-(0|[1-9][0-9]*)$"

# Let jsonschema know about the self-describing meta-schema
jsonschema.validators.meta_schemas[
    "http://iglucentral.com/schemas/com.snowplowanalytics.self-desc/schema/jsonschema/1-0-0"
] = jsonschema.validators.Draft4Validator


class SchemaVer(object):
    def __init__(self, model: int, revision: int, addition: int):
        self.model = model
        self.revision = revision
        self.addition = addition

    def as_string(self) -> str:
        return "%d-%d-%d" % (self.model, self.revision, self.addition)

    @staticmethod
    def parse_schemaver(version: str):
        m = re.match(SCHEMAVER_REGEX, version)
        if not m:
            raise IgluError(
                "Schema version {version} is not a valid Iglu SchemaVer".format(
                    version=version
                )
            )
        else:
            model, revision, addition = m.groups()
            return SchemaVer(int(model), int(revision), int(addition))


class SchemaKey(object):
    def __init__(self, vendor: str, name: str, format: str, version: SchemaVer):
        self.vendor = vendor
        self.name = name
        self.format = format
        self.version = version

    def as_uri(self) -> str:
        return "iglu:{path}".format(path=self.as_path())

    def as_path(self) -> str:
        return "{vendor}/{name}/{format}/{version}".format(
            vendor=self.vendor,
            name=self.name,
            format=self.format,
            version=self.version.as_string(),
        )

    # Construct SchemaKey from URI
    @staticmethod
    def parse_key(key):
        m = re.match(URI_REGEX, key)
        if not m:
            raise IgluError("Schema key [{key}] is not valid Iglu URI".format(key=key))
        else:
            vendor, name, format, version = m.groups()
            schema_ver = SchemaVer.parse_schemaver(version)
            return SchemaKey(vendor, name, format, schema_ver)


# Common Iglu error
class IgluError(Exception):
    def __init__(self, message):
        self.message = message
