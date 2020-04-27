import json
import pytest

from lib.registries import RegistryRefConfig, HttpRegistryRef
from lib.resolver import Resolver
from lib.self_describing_json import SelfDescribingJson


@pytest.fixture
def resolver():
    ref_config = RegistryRefConfig("Test registry ref", 5, [])
    registry = HttpRegistryRef(ref_config, "http://iglucentral.com")
    return Resolver([registry])


class TestSelfDescribingJson:
    @pytest.mark.usefixtures("resolver")
    def test_self_describing_json(self, resolver):
        instance = """
    {
      "schema": "iglu:com.parrable/decrypted_payload/jsonschema/1-0-0",
      "data": {
        "browserid": "9b5cfd54-3b90-455c-9455-9d215ec1c414",
        "deviceid": "asdfasdfasdfasdfcwer234fa$#ds±f324jo"
      }
    }
    """
        assert SelfDescribingJson.parse_json(json.loads(instance)).valid(resolver)

    @pytest.mark.usefixtures("resolver")
    def test_invalid_self_describing_json(self, resolver):
        instance = """
    {
      "schema": "iglu:com.parrable/decrypted_payload/jsonschema/1-0-0",
      "data": {
        "browserid": "9b5cfd54-3b90-455c-9455-9d215ec1c414",
        "deviceid": "asdfasdfasdfasdfcwer234fa$#ds±f324joaddddd"
      }
    }
    """
        assert not SelfDescribingJson.parse_json(json.loads(instance)).valid(resolver)
