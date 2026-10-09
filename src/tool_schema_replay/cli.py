"""Command-line interface for offline synthetic tool-schema replay."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any, Sequence


def _read_json(path: str) -> Any:
    """Read one local UTF-8 JSON document, translating input failures cleanly."""
    try:
        with Path(path).open("r", encoding="utf-8") as handle:
            return json.load(handle)
    except (OSError, UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError(f"{path}: {exc}") from exc


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="tool-schema-replay",
        description="Replay synthetic tool arguments against local tool schemas.",
    )
    parser.add_argument("old_tools", metavar="OLD_TOOLS.json")
    parser.add_argument("new_tools", metavar="NEW_TOOLS.json")
    parser.add_argument("calls", metavar="CALLS.json")
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def _format_text(result: dict[str, Any]) -> str:
    lines: list[str] = []
    for call in result["calls"]:
        lines.append(f"{call['id']}\t{call['tool']}\t{call['status']}")
        for error in call["errors"]:
            path = error["path"] or "/"
            lines.append(f"  error path: {path}")
    summary = result["summary"]
    lines.append(
        f"Summary: {summary['compatible']} compatible, {summary['breaking']} breaking"
    )
    return "\n".join(lines) + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    try:
        old_snapshot = _read_json(args.old_tools)
        new_snapshot = _read_json(args.new_tools)
        calls_document = _read_json(args.calls)
    except ValueError as exc:
        print(f"tool-schema-replay: {exc}", file=sys.stderr)
        return 2

    # Import after argument parsing and file reading so --help and local input
    # diagnostics remain available while the engine is developed independently.
    from .engine import InputError, evaluate

    try:
        result = evaluate(old_snapshot, new_snapshot, calls_document)
    except InputError as exc:
        print(f"tool-schema-replay: {exc}", file=sys.stderr)
        return 2

    if args.format == "json":
        print(json.dumps(result, ensure_ascii=False, sort_keys=True, indent=2))
    else:
        sys.stdout.write(_format_text(result))
    return 1 if result["summary"]["breaking"] else 0
