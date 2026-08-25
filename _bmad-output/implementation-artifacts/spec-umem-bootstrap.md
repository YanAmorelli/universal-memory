---
title: 'Add one-command UMEM session bootstrap'
type: 'feature'
created: '2026-08-03'
status: 'done'
route: 'dev-story'
baseline_commit: '1297dfbb22704ddc1b22d7920f13848c30ba1c01'
context:
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/devex-interaction-spec.md'
  - '_bmad-output/implementation-artifacts/4-3-implement-cli-mcp-parity-matrix.md'
  - '_bmad-output/implementation-artifacts/4-4-map-domain-errors-to-cli-and-json-rpc.md'
  - '_bmad-output/implementation-artifacts/4-5-validate-mcp-compliance-and-interface-contracts.md'
  - 'src/universal_memory/application/onboarding/setup_project.py'
  - 'src/universal_memory/application/host/setup_host_use_case.py'
---
<frozen-after-approval reason="human-owned intent and contract decisions - do not modify unless human renegotiates">

## Intent

**Problem:** Agents currently need three public calls at the start of a conversation or
session to validate UMEM, load active project context, and discover available skills. The
sequence consumes three round-trips, repeats transport metadata, and delays useful work.

**Approach:** Add one shared session-bootstrap orchestration exposed as
`umem bootstrap --format json` and the MCP/FastMCP `bootstrap` tool. It executes the
existing status, project-context, and skills-list application capabilities in that order
and returns one compact aggregate envelope. Agents still select relevant skills and request
their details separately.

## Approved Contract Decisions

1. The aggregate uses one standard success envelope rather than nesting three complete
 public envelopes.
2. `data.status`, `data.context`, and `data.skills.list` are faithful projections of the
 existing `data` payloads. They do not rename, remove, reinterpret, or synthesize fields.
3. `data.skills.list` is an object, not only an array, because the current skills-list
 payload may contain `skills`, `recommendations`, and `recommended_action`.
4. CLI and MCP preserve adapter-native error representations while maintaining semantic
 parity: the same failure category, sanitized detail, recovery meaning, interruption
 point, and execution history.
5. Execution is sequential and fail-fast in the order `status -> context -> skills list`.
 The bootstrap does not return partial success results.
6. The bootstrap is a consumer workflow executed once at the beginning of a conversation
 or session. UMEM does not persist session state or attempt to detect repeat calls.
7. Skill detail is never loaded automatically. The consuming agent selects relevant items
 from the list and calls the existing detail capability separately.

</frozen-after-approval>

## User Story

As an agent starting work in a UMEM-enabled project,
I want one bootstrap call that validates the integration, returns active project context,
and lists available skills,
so that I can begin with fewer round-trips and load details only for relevant skills.

## Boundaries &amp; Constraints

**Always:**

- Reuse the existing status, context, and skills-list application handlers and result
contracts.
- Keep orchestration outside the CLI and MCP adapters so both surfaces execute the same
steps, defaults, and fail-fast behavior.
- Keep adapters thin: they may select their native presentation and error code, but they
must not choose different business behavior.
- Preserve the current canonical payload serializers for status, context, and skills list.
Extract shared payload helpers where needed instead of copying serializer logic.
- Preserve the current error descriptors, sanitization, and CLI-to-JSON-RPC mappings.
- Keep all project paths in specs, docs, generated instructions, tests, and reports
relative.
- Keep `AGENTS.md` and `CLAUDE.md` managed blocks within their existing compactness limits
and free of memory dumps or bootstrap results.
- Keep operation offline after installation.

**Ask First:**

- Changing the fields of the existing status, context, or skills-list payloads.
- Adding a new error descriptor, error code, recovery policy, or schema version.
- Adding bootstrap parameters beyond the approved fixed functional defaults.
- Returning partial results after a failed step.
- Adding persisted session tracking, repeat-call detection, caching, or automatic skill
selection.

**Never:**

- Do not call skill detail for every listed skill.
- Do not infer relevant skills inside UMEM.
- Do not include sync, install, host configuration, path detection, repair, migration, or
other initialization work.
- Do not initialize an uninitialized project as a side effect.
- Do not redesign or fork the existing status, context, skills-list, or error contracts.
- Do not add `schemaVersion` or `schema_version` unless the existing public response
standard adopts it in a separately approved change.
- Do not store returned memory or skill dumps in `AGENTS.md` or `CLAUDE.md`.

## Public Interfaces

### CLI

```bash
umem bootstrap --format json
```

The CLI continues using the existing global output-format mechanism. JSON is the normative
agent contract and the format used by documentation and parity tests. Human or summary
rendering is presentation-only and must not change orchestration, defaults, or errors.

### MCP/FastMCP

```text
bootstrap()
```

The tool has no functional parameters. MCP structured content uses the same success payload
as CLI JSON. The CLI-only `--format` option is a transport presentation concern and is not an
MCP capability difference.

## Functional Defaults


| Step | Shared application call | Fixed input/default                                              |
| ---- | ----------------------- | ---------------------------------------------------------------- |
| 1    | status                  | current project root                                             |
| 2    | context                 | `scope=project`, `max_size_chars=4000`, `agent_session_key=None` |
| 3    | skills list             | current unfiltered defaults: all supported scopes and statuses   |


The value `4000` must come from one shared constant used by the existing context interfaces
and bootstrap. Do not introduce another copied fallback constant.

## Success Contract

```json
{
  "ok": true,
  "operation": "bootstrap",
  "scope": "project",
  "data": {
    "status": {},
    "context": {},
    "skills": {
      "list": {}
    }
  },
  "warnings": []
}
```

Projection rules:

- `data.status` equals the complete current `data` payload from status.
- `data.context` equals the complete current `data` payload from project context with the
approved defaults.
- `data.skills.list` equals the complete current `data` payload from skills list. In the
current contract this includes the `skills` array and may also include `recommendations`
and `recommended_action`.
- The aggregate does not include the child envelopes' `ok`, `operation`, `scope`, or
`warnings` fields.
- The top-level `warnings` remains the standard list. The three source operations currently
return no success warnings. If any source later adds warnings, bootstrap and the shared
contract tests must evolve in the same change rather than silently dropping them.
- No new schema-version field is introduced.

The apparently repetitive path `data.skills.list.skills` is intentional: the outer
`skills.list` identifies the composed capability, while the inner payload remains unchanged.

## Execution and Failure Semantics

1. Execute status exactly once.
2. If status raises, stop. Do not execute context or skills list.
3. If status succeeds with `initialized=false`, stop before context or skills list with the
 existing validation error category. Do not initialize, write bootstrap state, or continue
 with an empty context.
4. Execute context exactly once with the approved fixed defaults.
5. If context raises, stop. Do not execute skills list and do not return the completed status
 payload as a partial result.
6. Execute skills list exactly once with its current unfiltered defaults.
7. If skills list raises, return the adapter-native error and no partial aggregate.
8. Only after all three steps succeed, serialize and return the aggregate success envelope.

The uninitialized-project guard makes the composite behavior deterministic and matches the
existing MCP project-context precondition. It does not change the standalone status or
context commands.

### Semantic Error Parity

For the same injected or real failure:

- both interfaces stop after the same completed calls;
- both resolve the same shared error descriptor;
- both expose sanitized detail and equivalent recovery guidance;
- CLI JSON keeps the existing textual error code and exits non-zero;
- MCP keeps the existing JSON-RPC numeric code and tool-error representation;
- neither interface returns successful child payloads alongside the error;
- unexpected errors remain generic by default and preserve existing debug-only diagnostics.

Literal error-envelope equality is not required and would conflict with the approved
adapter-native architecture.

## I/O and Edge-Case Matrix


| Scenario                                | Input / State                                                        | Expected output or behavior                                                             | Error handling                                              |
| --------------------------------------- | -------------------------------------------------------------------- | --------------------------------------------------------------------------------------- | ----------------------------------------------------------- |
| Healthy initialized project             | All three handlers succeed                                           | One aggregate envelope with faithful status, context, and skills-list payloads          | Exit 0 / MCP success                                        |
| No registered skills                    | Skills list returns its current empty payload and recommended action | Preserve the complete skills-list payload under `data.skills.list`; do not load details | Success                                                     |
| Recommendations are present             | Skills list includes recommendations                                 | Preserve them under `data.skills.list`; do not promote or inspect them                  | Success                                                     |
| Uninitialized project                   | Status succeeds with `initialized=false`                             | Stop before context and skills list; do not create files                                | Existing validation category, adapter-native representation |
| Status failure                          | Status raises a domain or unexpected exception                       | Context and skills list are not called                                                  | Existing mapping; no partial result                         |
| Context failure                         | Status succeeds; context raises                                      | Skills list is not called                                                               | Existing mapping; no partial result                         |
| Skills-list failure                     | Status and context succeed; skills list raises                       | Aggregate success is not emitted                                                        | Existing mapping; no partial result                         |
| Secret or absolute path in error detail | Any step raises with sensitive detail                                | Both adapters sanitize through existing shared helpers                                  | Existing code mapping and safe detail                       |
| Repeat call in one session              | Consumer invokes bootstrap again                                     | UMEM executes normally; no session state is read or written                             | Consumer guidance, not server enforcement                   |
| Large skill catalog                     | Many skills exist                                                    | Return list metadata only                                                               | Never call skill detail automatically                       |


## Architecture and Code Map

- `src/universal_memory/application/onboarding/session_bootstrap.py` -- New shared command,
result, and sequential orchestration use case.
- `src/universal_memory/application/onboarding/__init__.py` -- Export the session-bootstrap
application types.
- `src/universal_memory/interfaces/payloads.py` -- Shared status, context, and skills-list
payload projections extracted from adapter-local helpers as needed.
- `src/universal_memory/interfaces/cli/init_command.py` -- Register `umem bootstrap`, invoke
the shared orchestration, and render the standard aggregate envelope or existing CLI error.
- `src/universal_memory/interfaces/mcp/server.py` -- Register `bootstrap`, invoke the same
orchestration, and use existing MCP success/error translation.
- `src/universal_memory/bootstrap/cli.py` -- Compose and inject the session-bootstrap use case.
- `src/universal_memory/bootstrap/mcp.py` -- Compose and inject the same session-bootstrap use
case.
- `src/universal_memory/application/onboarding/setup_project.py` -- Replace the three-command
startup guidance and MCP equivalents with the single bootstrap plus selective skill detail.
- `src/universal_memory/application/host/setup_host_use_case.py` -- Keep generated `AGENTS.md`
and `CLAUDE.md` compact while pointing to the single startup capability.
- `docs/agents/mcp-and-skills.md` and `docs/users/getting-started.md` -- Document the one-call
startup flow, fallback order, active-context interpretation, and once-per-session rule.
- `tests/application/test_session_bootstrap.py` -- Verify order, fixed defaults,
fail-fast behavior, and absence of automatic detail calls.
- `tests/interfaces/cli/test_bootstrap_command.py` -- Verify CLI success and adapter-native
error contracts.
- `tests/interfaces/mcp/test_bootstrap.py` -- Verify tool registration, structured success,
and MCP-native error contracts.
- `tests/interfaces/test_parity.py` -- Add public capability inventory and deep bootstrap
success/error semantic parity scenarios.
- `tests/interfaces/mcp/test_compliance.py` -- Add the tool to the offline compliance inventory
and exact contract-key/type checks.
- `tests/application/test_setup_project.py`, `tests/application/test_setup_host.py`, and
`tests/docs/test_mkdocs_content_contracts.py` -- Protect compact, once-per-session agent
guidance.
- `benchmarks/bootstrap.py` and `tests/infrastructure/test_bootstrap_benchmark.py` -- Measure
the current three-call baseline against one bootstrap call without making timing a flaky CI
assertion.

If the implementation finds a more appropriate existing shared payload module, reuse it
instead of creating a second contracts location. The invariant is one serializer per child
payload, consumed by both adapters and bootstrap.

## Tasks and Acceptance

### Application orchestration

- [x] Add `SessionBootstrapCommand`, `SessionBootstrapResult`, and

  `SessionBootstrapUseCase` with injected status, context, and skills-list handlers.
- [x] Execute handlers exactly once in the approved order with the approved defaults.
- [x] Add the uninitialized-project validation guard after status and before context.
- [x] Keep the use case unaware of CLI, MCP, JSON-RPC, Typer, Rich, and FastMCP.
- [x] Add focused application tests for success, uninitialized state, and a failure at each

  step using recording fakes.

### Shared payload contract

- [x] Extract or centralize status and context payload serialization so standalone CLI,

  standalone MCP, and bootstrap consume the same helpers.
- [x] Reuse `ListSkillsResult.to_payload()` as the canonical skills-list data projection.
- [x] Add a bootstrap success presenter that creates only the approved top-level envelope.
- [x] Prove through regression tests that standalone command payloads do not change.

### CLI and MCP surfaces

- [x] Register `umem bootstrap` and support `umem bootstrap --format json` through existing

  CLI composition and error handling.
- [x] Register MCP/FastMCP `bootstrap()` with no functional parameters.
- [x] Inject the same application orchestration into both composition roots.
- [x] Extend the public parity matrix and MCP compliance inventory.
- [x] Add shared scenarios that compare complete aggregate `data` values, not only key sets.
- [x] Add semantic error parity tests for failures at status, context, and skills list.

### Agent and user documentation

- [x] Replace startup sequences in the generated `use-universal-memory` skill and its

  startup reference with MCP `bootstrap()` first and CLI fallback
  `umem bootstrap --format json`.
- [x] Preserve separate `skills detail` guidance for agent-selected relevant skills.
- [x] Update generated `AGENTS.md` and `CLAUDE.md` managed blocks without storing dynamic

  results and while preserving content outside the managed delimiters.
- [x] Update curated user and agent docs and capability tables.
- [x] Protect the phrases and commands with focused substring/structure tests rather than

  brittle full-Markdown snapshots.

### Measurement

- [x] Add an offline benchmark with warm-up and repeated samples for the three-call baseline

  and the one-call bootstrap path.
- [x] Record at least round-trip count, median duration, p95 duration, serialized request

  size, serialized response size, a documented token proxy derived from serialized
  characters, and sample count. Do not present the proxy as an exact model-billing token
  count.
- [x] Report CLI subprocess measurements separately from in-process MCP tool-call

  measurements.
- [x] Assert deterministic metric structure and the round-trip reduction in CI; do not gate

  CI on wall-clock thresholds.
- [x] Record the observed timing comparison in completion notes. If the one-call path does

  not improve median routine time in the controlled benchmark, investigate before marking
  the feature done.

## Acceptance Criteria

1. Given an initialized project, when CLI runs `umem bootstrap --format json`, then it exits
 0 and returns the approved aggregate envelope.
2. Given the same initialized state, when MCP calls `bootstrap()`, then its structured
 success `data` is deeply equivalent to CLI JSON `data`, and both use the approved
 top-level success metadata.
3. Given the aggregate response, then `data.status`, `data.context`, and
 `data.skills.list` equal the current standalone command `data` payloads for the same
 handlers and defaults.
4. Given project context in the aggregate, then a consumer can treat `data.context` as active
 context without an additional context call.
5. Given listed skills or recommendations, then bootstrap returns metadata only and never
 invokes skill detail, creation, sync, promotion, or mutation capabilities.
6. Given a failure at any step, then both surfaces stop at the same point, return no partial
 success aggregate, and preserve semantically equivalent adapter-native errors.
7. Given an uninitialized project, then bootstrap does not execute context or skills list and
 does not initialize or create project files.
8. Given contract tests, then status, context, and skills-list standalone payloads remain
 unchanged after shared serializer extraction.
9. Given generated or curated agent instructions, then they prefer MCP `bootstrap()` when
 available, fall back to `umem bootstrap --format json`, treat context as active, select
 relevant skills, request only selected details, and prohibit repeating bootstrap during
 the same conversation/session.
10. Given generated `AGENTS.md` and `CLAUDE.md`, then the managed blocks remain within current
  compactness limits, contain no dynamic memory dump, and preserve manual content outside
  UMEM delimiters.
11. Given benchmark results, then the startup routine uses one public round-trip instead of
  three, a reduction of `66.7%`, and completion evidence records the controlled timing
  comparison and a lower serialized request-plus-response token proxy than the three-call
  baseline.
12. Given MCP compliance and public inventory tests, then the feature cannot be completed if
  either CLI or MCP is missing the capability or differs in functional defaults, execution
  order, success semantics, or error semantics.

## Verification

**Focused commands:**

```bash
uv run pytest tests/application/test_session_bootstrap.py
uv run pytest tests/interfaces/cli/test_bootstrap_command.py tests/interfaces/mcp/test_bootstrap.py
uv run pytest tests/interfaces/test_parity.py tests/interfaces/mcp/test_compliance.py
uv run pytest tests/application/test_setup_project.py tests/application/test_setup_host.py
uv run pytest tests/docs/test_mkdocs_content_contracts.py
uv run pytest tests/infrastructure/test_bootstrap_benchmark.py
```

**Quality gates:**

```bash
uv run pytest
uv run ruff check .
uv run ruff format --check .
uv run pyright
```

**Manual smoke:**

```bash
uv run umem bootstrap --format json
uv run python benchmarks/bootstrap.py --format json
```

Expected smoke evidence:

- stdout contains one JSON object for CLI bootstrap;
- `operation` is `bootstrap` and `scope` is `project`;
- all three approved `data` projections are present;
- no skill detail content is present;
- benchmark output reports three baseline round-trips and one bootstrap round-trip;
- all reported project paths are relative.

## Suggested Review Order

1. Review `src/universal_memory/application/onboarding/session_bootstrap.py` for order,
 defaults, fail-fast behavior, and absence of interface concerns.
2. Review shared payload helpers and standalone contract regression tests for zero drift.
3. Review CLI and MCP adapters together with deep parity and error scenarios.
4. Review generated host instructions and the default UMEM skill for compact one-call
 guidance.
5. Review benchmark methodology and recorded results last; timing is evidence, not a flaky
 CI threshold.

## Completion Notes

- Implemented one shared session-bootstrap orchestration with faithful child payload projections and thin CLI/MCP adapters.
- Verified public round trips changed from `3 -> 1` (`66.7%` reduction).
- Five-sample benchmark: CLI median changed from `501.334 ms` to `167.805 ms`; MCP median changed from `6.407 ms` to `3.545 ms`.
- Token proxy changed from `1791 -> 1729` for CLI and `1752 -> 1710` for MCP. The proxy uses four serialized characters per token and is not a billing-token measurement.
- Verification passed: `904` full-suite tests, Ruff lint, Ruff format check, Pyright, isolated CLI smoke, CLI/MCP parity, and offline compliance.
- Review fixes normalize raw bootstrap read failures before adapter-native presentation, add per-step semantic error parity coverage, and align generated guidance with fail-fast once-per-session behavior.
