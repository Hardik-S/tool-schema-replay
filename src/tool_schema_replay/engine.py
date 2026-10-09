"""Offline validation of synthetic tool calls against schema snapshots."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from jsonschema import Draft202012Validator
from jsonschema.exceptions import SchemaError
from referencing import Registry, Resource


class InputError(ValueError):
    """Raised when snapshots or captured calls are malformed or invalid."""


def _object(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise InputError(f"{where} must be an object")
    return value


def _keys(value: Mapping[str, Any], required: set[str], optional: set[str], where: str) -> None:
    missing = required - value.keys()
    extra = value.keys() - required - optional
    if missing:
        raise InputError(f"{where} is missing required keys: {', '.join(sorted(missing))}")
    if extra:
        raise InputError(f"{where} has unexpected keys: {', '.join(sorted(extra))}")


def _pointer(parts: Any) -> str:
    escaped = [str(part).replace("~", "~0").replace("/", "~1") for part in parts]
    return "/" + "/".join(escaped) if escaped else ""


def _schema_validator(schema: Any, where: str) -> Draft202012Validator:
    if not isinstance(schema, Mapping):
        raise InputError(f"{where} must be a JSON Schema object")
    try:
        Draft202012Validator.check_schema(schema)
    except SchemaError as exc:
        raise InputError(f"{where} is not a valid JSON Schema: {exc.message}") from exc

    # Permit only references within this schema document and resolve every ref
    # up front, including refs hidden in conditional or otherwise unused branches.
    registry = Registry().with_resource("", Resource.from_contents(dict(schema)))
    pending = [schema]
    while pending:
        node = pending.pop()
        if isinstance(node, Mapping):
            ref = node.get("$ref")
            if ref is not None:
                if not isinstance(ref, str) or not ref.startswith("#"):
                    raise InputError(f"{where} uses a non-local $ref: {ref!r}")
                try:
                    registry.resolver().lookup(ref)
                except Exception as exc:
                    raise InputError(f"{where} has an unresolved $ref {ref!r}") from exc
            pending.extend(node.values())
        elif isinstance(node, (list, tuple)):
            pending.extend(node)

    return Draft202012Validator(dict(schema), registry=registry)


def _tools(snapshot: Any, where: str) -> dict[str, Draft202012Validator]:
    obj = _object(snapshot, where)
    _keys(obj, {"tools"}, set(), where)
    items = obj["tools"]
    if not isinstance(items, list):
        raise InputError(f"{where}.tools must be an array")
    result: dict[str, Draft202012Validator] = {}
    for index, raw in enumerate(items):
        label = f"{where}.tools[{index}]"
        tool = _object(raw, label)
        _keys(tool, {"name", "inputSchema"}, {"description", "title", "annotations", "outputSchema", "icons", "_meta"}, label)
        name = tool["name"]
        if not isinstance(name, str) or not name:
            raise InputError(f"{label}.name must be a non-empty string")
        if name in result:
            raise InputError(f"{where} contains duplicate tool name {name!r}")
        result[name] = _schema_validator(tool["inputSchema"], f"{label}.inputSchema")
    return result


def evaluate(old_snapshot: Any, new_snapshot: Any, calls_document: Any) -> dict[str, Any]:
    """Compare whether each saved call remains accepted by the new tool schema.

    Inputs are in-memory JSON values. No tools are executed and no resources
    are fetched; schema references are restricted to the schema document.
    """
    old_tools = _tools(old_snapshot, "old_snapshot")
    new_tools = _tools(new_snapshot, "new_snapshot")

    calls_obj = _object(calls_document, "calls_document")
    _keys(calls_obj, {"calls"}, set(), "calls_document")
    raw_calls = calls_obj["calls"]
    if not isinstance(raw_calls, list):
        raise InputError("calls_document.calls must be an array")

    seen_ids: set[str] = set()
    output: list[dict[str, Any]] = []
    for index, raw in enumerate(raw_calls):
        label = f"calls_document.calls[{index}]"
        call = _object(raw, label)
        _keys(call, {"id", "tool", "arguments"}, set(), label)
        call_id, tool_name = call["id"], call["tool"]
        if not isinstance(call_id, str) or not call_id:
            raise InputError(f"{label}.id must be a non-empty string")
        if call_id in seen_ids:
            raise InputError(f"calls_document contains duplicate call id {call_id!r}")
        seen_ids.add(call_id)
        if not isinstance(tool_name, str) or not tool_name:
            raise InputError(f"{label}.tool must be a non-empty string")
        old_validator = old_tools.get(tool_name)
        if old_validator is None:
            raise InputError(f"{label} refers to tool {tool_name!r} absent from old_snapshot")

        old_errors = list(old_validator.iter_errors(call["arguments"]))
        if old_errors:
            raise InputError(
                f"{label} arguments are invalid under the old schema at "
                f"{_pointer(old_errors[0].absolute_path)}: {old_errors[0].message}"
            )

        new_validator = new_tools.get(tool_name)
        validation_errors: list[dict[str, str]] = []
        if new_validator is None:
            validation_errors.append({"path": "/tool", "message": "tool is absent from new_snapshot"})
        else:
            for error in new_validator.iter_errors(call["arguments"]):
                validation_errors.append({
                    "path": "/arguments" + _pointer(error.absolute_path),
                    "message": error.message,
                })
            validation_errors.sort(key=lambda item: (item["path"], item["message"]))
        output.append({
            "id": call_id,
            "tool": tool_name,
            "status": "breaking" if validation_errors else "compatible",
            "errors": validation_errors,
        })

    breaking = sum(item["status"] == "breaking" for item in output)
    return {
        "version": 1,
        "summary": {"compatible": len(output) - breaking, "breaking": breaking},
        "calls": output,
    }
