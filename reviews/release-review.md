# Independent release review

**Result: BLOCK**

**Reviewed:** `Hardik-S/tool-schema-replay` at `631bc09139549ac3c444b14fcf84807ea74b7459` (issue #4 frozen review target).

## Findings

1. **Valid literal data is mistaken for a schema reference.** `src/tool_schema_replay/engine.py:49-60` recursively treats every mapping key named `$ref` as a JSON Schema keyword, including data beneath `const`, `enum`, `default`, or annotations. Reproduction: a valid Draft 2020-12 schema with `"const": {"$ref":"https://example.invalid/schema.json"}` is rejected as a non-local reference. Traverse schema-bearing keyword locations, not arbitrary instance/annotation data, while still checking refs in unused schema branches.

2. **The local-reference restriction omits `$dynamicRef`, and active remote dynamic references escape the CLI input-error path.** Draft 2020-12 defines `$dynamicRef` as a reference keyword. Reproduction: a schema with `properties.unused.$dynamicRef = "https://example.invalid/schema.json"` and call arguments `{}` is accepted as compatible. Supplying that property causes `_WrappedReferencingError: Unresolvable: https://example.invalid/schema.json` to escape `evaluate`; `cli.main` catches only `InputError`, so a CLI invocation would traceback instead of returning documented malformed/unsupported-input exit code 2. Recognize and validate `$dynamicRef` under the local-only rule, resolving local dynamic references without retrieving external resources, and normalize unsupported/unresolvable references to `InputError`.

## Verification evidence

- `python -m pytest -q`: **23 passed**.
- `python -m pip install -e ".[dev]"`: **passed** in the repository `.venv`; editable entry point installed.
- Installed CLI quickstart: `examples/calls-compatible.json` returned 0; `examples/calls-breaking.json --format json` returned 1 with deterministic JSON and the expected breaking summary.
- Synthetic version probes: missing, `null`, `1.0`, `true`, and `2` rejected with `InputError`; exact integer `1` accepted.
- Existing tests cover old-schema-invalid calls, local `$ref`, malformed/unresolved or remote `$ref`, stable JSON/text output, and exit codes 0/1/2.
- The two findings above were reproduced directly against `evaluate`; no external network request was made.
- GitHub preflight for `Hardik-S/tool-schema-replay`: account `Hardik-S`, `auth-ok`, origin remote present, checkout clean before review. Public/private ACL state was not reported by preflight.

The reviewed commit meets the tested version, baseline, determinism, exit-code, installation, and quickstart checks, but the two JSON Schema reference defects contradict the stated Draft 2020-12 and local-only behavior, so release is blocked pending repair and regression coverage.

## Follow-up review: commit `ae1c98c5dd408ea05984f6d96efde18688ceb197`

**Result for this reviewed commit: PASS.** The original `BLOCK` above remains the result for the earlier frozen commit `631bc09139549ac3c444b14fcf84807ea74b7459`; this follow-up records the later target separately.

The two earlier findings are resolved at this target. `_schema_validator` now inspects `$ref` and `$dynamicRef` only while walking Draft 2020-12 schema-bearing positions (`$defs`, `properties`, `patternProperties`, `dependentSchemas`, applicator/conditional keywords, and content schema), leaving values under `const`, `enum`, `default`, and annotations as data. It rejects non-local references even in unused branches and resolves local references through an in-memory `referencing.Registry`.

### Follow-up evidence

- Reviewed checkout: `ae1c98c5dd408ea05984f6d96efde18688ceb197` (`main`, matching `origin/main`).
- `python -m pytest -q`: **26 passed**. Tests include a literal `$ref` under `const`, rejection of remote `$dynamicRef` in both unused and active positions, local `$ref`, and exact integer calls version validation.
- `python -m pip install -e ".[dev]"`: **passed**. The console script was installed under the user Python Scripts directory; invoking it by full path avoided the PATH warning.
- Installed quickstart example with `examples/calls-compatible.json`: exit **0**, one compatible call. `examples/calls-breaking.json --format json`: exit **1**, deterministic JSON reporting the expected missing `priority` field.
- Synthetic `evaluate` probes accepted remote-looking `$ref` values as literal `const`, `enum`, `default`, and `examples` data; rejected unused and active remote `$dynamicRef` as `InputError`; resolved a local `$dynamicRef`; and rejected a call invalid under the old schema.
- The same synthetic probe replaced `socket.create_connection` and `socket.socket.connect` with fail-fast counters. It completed with **zero socket connection attempts**, including on remote-looking schema references. Together with the local-only registry construction and no retrieval callback, this confirms these code paths do not request network resources.
- Existing CLI tests verify repeatable text/JSON output and exit codes 0, 1, and 2. README installation and quickstart commands match the successful installed invocation; the documented synthetic/offline scope is supported by the inspected code and checks.

No actionable release blocker remained in this bounded follow-up pass.
