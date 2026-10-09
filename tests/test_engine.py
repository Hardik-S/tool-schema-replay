"""Contract tests for offline schema replay using synthetic calls only."""

import copy
import json

import pytest

from tool_schema_replay import engine


def snapshot(*tools):
    return {"tools": list(tools)}


def tool(name, schema):
    return {"name": name, "inputSchema": schema}


def call(call_id, name, arguments):
    return {"id": call_id, "tool": name, "arguments": arguments}


BASE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "type": "object",
    "properties": {"key": {"type": "string"}, "optional": {"type": "boolean"}},
    "required": ["key"],
    "additionalProperties": False,
}


def test_compatible_call_is_reported_as_compatible():
    old = snapshot(tool("lookup", BASE_SCHEMA))
    new = copy.deepcopy(old)
    result = engine.evaluate(old, new, {"version": 1, "calls": [call("c1", "lookup", {"key": "synthetic"})]})
    assert result["summary"]["breaking"] == 0


def test_newly_required_property_breaks_old_call():
    old_schema = copy.deepcopy(BASE_SCHEMA)
    new_schema = copy.deepcopy(BASE_SCHEMA)
    new_schema["required"].append("optional")
    result = engine.evaluate(
        snapshot(tool("lookup", old_schema)), snapshot(tool("lookup", new_schema)),
        {"version": 1, "calls": [call("c1", "lookup", {"key": "synthetic"})]},
    )
    assert result["summary"]["breaking"] == 1


def test_removed_tool_breaks_call():
    result = engine.evaluate(
        snapshot(tool("lookup", BASE_SCHEMA)), snapshot(),
        {"version": 1, "calls": [call("c1", "lookup", {"key": "synthetic"})]},
    )
    assert result["summary"]["breaking"] == 1


def test_call_invalid_under_old_schema_is_rejected_as_input():
    with pytest.raises(engine.InputError):
        engine.evaluate(
            snapshot(tool("lookup", BASE_SCHEMA)), snapshot(tool("lookup", BASE_SCHEMA)),
            {"version": 1, "calls": [call("c1", "lookup", {"wrong": "synthetic"})]},
        )


@pytest.mark.parametrize("document", ["{", {"tools": "not-an-array"}, {"tools": [{"name": "x"}]}])
def test_malformed_snapshot_is_rejected(document):
    with pytest.raises(engine.InputError):
        engine.evaluate(document, snapshot(), {"version": 1, "calls": []})


@pytest.mark.parametrize("schema", [
    {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "not-a-json-schema-type"},
    {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "#/definitions/missing"},
    {"$schema": "https://json-schema.org/draft/2020-12/schema", "$ref": "https://example.invalid/schema.json"},
])
def test_invalid_or_unresolvable_schema_is_rejected(schema):
    with pytest.raises(engine.InputError):
        engine.evaluate(snapshot(tool("x", schema)), snapshot(tool("x", schema)), {"version": 1, "calls": []})


@pytest.mark.parametrize("old,new", [
    (snapshot(tool("same", BASE_SCHEMA), tool("same", BASE_SCHEMA)), snapshot()),
    (snapshot(), snapshot(tool("same", BASE_SCHEMA), tool("same", BASE_SCHEMA))),
])
def test_duplicate_tool_names_are_rejected(old, new):
    with pytest.raises(engine.InputError):
        engine.evaluate(old, new, {"calls": []})


def test_duplicate_call_ids_are_rejected():
    with pytest.raises(engine.InputError):
        engine.evaluate(
            snapshot(tool("x", BASE_SCHEMA)), snapshot(tool("x", BASE_SCHEMA)),
            {"version": 1, "calls": [call("same", "x", {"key": "a"}), call("same", "x", {"key": "b"})]},
        )


def test_local_reference_resolves_without_external_access():
    schema = {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "$defs": {"payload": {"type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}},
        "$ref": "#/$defs/payload",
    }
    result = engine.evaluate(
        snapshot(tool("x", schema)), snapshot(tool("x", schema)),
        {"version": 1, "calls": [call("c1", "x", {"key": "synthetic"})]},
    )
    assert result["summary"]["breaking"] == 0


@pytest.mark.parametrize("version", [None, 1.0, True, 2])
def test_calls_document_requires_exact_integer_version_one(version):
    with pytest.raises(engine.InputError):
        engine.evaluate(
            snapshot(tool("x", BASE_SCHEMA)), snapshot(tool("x", BASE_SCHEMA)),
            {"version": version, "calls": []},
        )


def test_calls_document_requires_version_field():
    with pytest.raises(engine.InputError):
        engine.evaluate(snapshot(), snapshot(), {"calls": []})
