# Tool Schema Replay

Tool Schema Replay checks whether saved synthetic MCP tool calls remain valid after a tool schema change.

This offline Python CLI reads two tools/list snapshots and historical synthetic arguments. It verifies each call against its old schema, then reports whether the new schema still accepts it.

    python -m pip install -e ".[dev]"
    tool-schema-replay examples/old-tools.json examples/new-tools.json examples/calls.json

Exit codes: 0 all baseline-valid calls remain valid; 1 at least one breaks under the new snapshot; 2 invalid input or a call that was already invalid under the old snapshot.

All examples are synthetic. The tool does not connect to MCP servers, execute tools, capture traffic, or make claims about runtime behavior. AgentCompat and MCP Recorder cover broader neighboring workflows; this project makes no novelty or superiority claim.
