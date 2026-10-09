# Tool Schema Replay 0.1.0 launch note

Tool Schema Replay answers a narrow CI question: do synthetic MCP tool arguments that were valid against an older input schema remain valid against a new one?

Install with `python -m pip install -e .`, then run the compatible fixture:

    tool-schema-replay examples/old-tools.json examples/new-tools.json examples/calls-compatible.json

Run the adversarial fixture with `--format json`; it exits 1 because the new schema requires `priority` for a call that was valid under the old schema.

The checker uses JSON Schema 2020-12, accepts only local references, and never connects to a server or executes a tool. It reports schema-level input compatibility; it does not establish runtime behavior. AgentCompat covers a broader old/new trace-validation workflow, so this release makes no novelty or superiority claim.
