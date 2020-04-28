import pytest

from iglu_client.core import SchemaKey, SchemaVer, IgluError


class TestSchemaKey:
    def test_parse_iglu_uri(self):
        assert (
            SchemaKey.parse_key(
                "iglu:com.snowplowanalytics.snowplow/event/jsonschema/1-0-1"
            ).as_uri()
            == SchemaKey(
                "com.snowplowanalytics.snowplow",
                "event",
                "jsonschema",
                SchemaVer(1, 0, 1),
            ).as_uri()
        )

    def test_parse_schemaver(self):
        assert (
            SchemaVer.parse_schemaver("2-0-3").as_string()
            == SchemaVer(2, 0, 3).as_string()
        )

    def test_parse_schemaver_multi_digits(self):
        assert (
            SchemaVer.parse_schemaver("10-0-112").as_string()
            == SchemaVer(10, 0, 112).as_string()
        )

    def test_parse_invalid_schemaver_has_letters_and_numers(self):
        with pytest.raises(IgluError):
            SchemaVer.parse_schemaver("10-a-1")

    def test_parse_invalid_schemaver_0_based_versioning(self):
        with pytest.raises(IgluError):
            SchemaVer.parse_schemaver("0-1-2")

    def test_parse_invalid_schemaver_lower_case_letters(self):
        with pytest.raises(IgluError):
            SchemaVer.parse_schemaver("a-b-c")

    def test_parse_invalid_schemaver_upper_case_letters(self):
        with pytest.raises(IgluError):
            SchemaVer.parse_schemaver("A-B-C")

    def test_parse_invalid_schemaver_dot_formatted(self):
        with pytest.raises(IgluError):
            SchemaVer.parse_schemaver("2.0.3")

    def test_parse_schema_key_missing_iglu_protocol(self):
        with pytest.raises(IgluError):
            SchemaKey.parse_key("com.snowplowanalytics.snowplow/event/jsonschema/1-0-1")

    def test_parse_schema_key_invalid_version(self):
        with pytest.raises(IgluError):
            SchemaKey.parse_key("com.snowplowanalytics.snowplow/event/jsonschema/1-a-1")
