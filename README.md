# Tool Schema Replay

Tool Schema Replay checks whether saved synthetic MCP tool calls remain valid after a tool schema change.

Install from a clean checkout:

    python -m pip install -e ".[dev]"

A compatible call exits 0:

    tool-schema-replay examples/old-tools.json examples/new-tools.json examples/calls-compatible.json

A call rejected by the new schema exits 1 and reports its validation path:

    tool-schema-replay examples/old-tools.json examples/new-tools.json examples/calls-breaking.json

Use --format json for a deterministic machine-readable report. Exit code 2 means malformed input, invalid schemas, or a call that was already invalid under its old schema. The checker uses JSON Schema 2020-12, accepts only local references, and never fetches remote resources.

All examples are synthetic. The tool does not connect to MCP servers, execute tools, capture traffic, or make claims about runtime behavior. AgentCompat directly covers the broader old/new trace-validation workflow, and MCP Recorder projects cover session capture/replay. This project makes no novelty or superiority claim.
