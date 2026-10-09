"""CLI output and documented exit-code contract tests."""

import json
from pathlib import Path

from tool_schema_replay import cli


EXAMPLES = Path(__file__).resolve().parents[1] / "examples"


def test_json_output_is_deterministic(capsys):
    args = ["--format", "json", str(EXAMPLES / "old-tools.json"), str(EXAMPLES / "new-tools.json"), str(EXAMPLES / "calls.json")]
    assert cli.main(args) == 1
    first = capsys.readouterr().out
    assert cli.main(args) == 1
    second = capsys.readouterr().out
    assert first == second
    assert json.loads(first)["summary"]["breaking"] == 1


def test_text_output_is_deterministic_and_reports_breakage(capsys):
    args = ["--format", "text", str(EXAMPLES / "old-tools.json"), str(EXAMPLES / "new-tools.json"), str(EXAMPLES / "calls.json")]
    assert cli.main(args) == 1
    first = capsys.readouterr().out
    assert cli.main(args) == 1
    second = capsys.readouterr().out
    assert first == second
    assert first.strip()


def test_all_compatible_exit_code_is_zero(tmp_path, capsys):
    old = {"tools": [{"name": "lookup", "inputSchema": {"$schema": "https://json-schema.org/draft/2020-12/schema", "type": "object", "properties": {"key": {"type": "string"}}, "required": ["key"]}}]}
    calls = {"version": 1, "calls": [{"id": "c1", "tool": "lookup", "arguments": {"key": "synthetic"}}]}
    old_file = tmp_path / "old.json"
    new_file = tmp_path / "new.json"
    calls_file = tmp_path / "calls.json"
    old_file.write_text(json.dumps(old), encoding="utf-8")
    new_file.write_text(json.dumps(old), encoding="utf-8")
    calls_file.write_text(json.dumps(calls), encoding="utf-8")
    assert cli.main([str(old_file), str(new_file), str(calls_file)]) == 0
    capsys.readouterr()


def test_invalid_input_exit_code_is_two(tmp_path, capsys):
    invalid = tmp_path / "invalid.json"
    valid = tmp_path / "valid.json"
    calls = tmp_path / "calls.json"
    invalid.write_text("{", encoding="utf-8")
    valid.write_text('{"tools": []}', encoding="utf-8")
    calls.write_text('{"version": 1, "calls": []}', encoding="utf-8")
    assert cli.main([str(invalid), str(valid), str(calls)]) == 2
    capsys.readouterr()
