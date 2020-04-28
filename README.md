# Python client for Iglu [![Travis-CI Build Status](https://travis-ci.com/jbwyme/iglu-python-client.svg?branch=master&status=passed)](https://travis-ci.com/github/jbwyme/iglu-python-client)



A Python client and resolver for **[Iglu schema repositories][iglu-wiki]**

# Installation
`pip install iglu_client`

# Usage

```py
import json
import jsonschema

from iglu_client import SchemaResolver, SelfDescribingJson

resolver_conf = """
{
    "schema": "iglu:com.snowplowanalytics.iglu/resolver-config/jsonschema/1-0-2",
    "data": {
        "cacheSize": 500,
        "repositories": [
            {
                "name": "My Private Repo",
                "priority": 0,
                "vendorPrefixes": ["com.mycompany"],
                "connection": {"http": {"uri": "http://myprivaterepo.com", "apikey": "api-key"}}
            },
            {
                "name": "Iglu Central",
                "priority": 1,
                "vendorPrefixes": ["com.snowplowanalytics.snowplow"],
                "connection": {"http": {"uri": "http://iglucentral.com"}}
            }
        ]
    }
}
"""
resolver = SchemaResolver.parse(resolver_conf)

# Retrieve a schema
schema = resolver.lookup_schema("iglu:com.snowplowanalytics.snowplow/link_click/jsonschema/1-0-0")
print("schema: %s" % schema)


# Validate a self-describing JSON
event = """
{
    "schema": "iglu:com.snowplowanalytics.snowplow/link_click/jsonschema/1-0-0",
    "data": {
        "targetUrl": "https://mixpanel.com"
    }
}
"""
data = SelfDescribingJson.parse(event)
try:
    data.validate(resolver) # will throw an exception if the event is invalid
    print("event is valid")
except jsonschema.exceptions.ValidationError as e:
    print("event is invalid")

if data.valid(resolver): # will return True or False
    print("event is valid")
else:
    print("event is invalid")

```
