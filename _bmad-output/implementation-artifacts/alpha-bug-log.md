# Alpha Bug Log

## Objective

This file centralizes the bugs found during the alpha testing phase of `universal-memory`.

Suggested combined usage:

- register new bugs here as soon as they are observed;
- investigate ambiguous bugs with `bmad-investigate`;
- fix small bugs with `bmad-quick-dev`;
- fix bugs linked to story/sprint with `bmad-dev-story` or the normal story workflow.

## Status

- `open`: bug confirmed and not yet fixed
- `investigating`: bug under analysis
- `blocked`: depends on external decision or context
- `fixed`: correction applied
- `verified`: correction validated manually or by a relevant test
- `deferred`: known bug, but deferred

## Severity

- `high`: blocks onboarding, breaks main workflow, or compromises basic trust
- `medium`: does not block everything, but causes a relevant failure, poor UX, or inconsistent behavior
- `low`: minor rough edge, cosmetic issue, or ergonomics improvement

## Template

```md
## BUG-XXX - Short title

- Status: verified
- Severity: medium
- Surface: CLI | MCP | Packaging | Docs | Global State | Host Setup
- Found on: 2026-05-29
- Context: where and how it appeared

### Reproduction

1. step 1
2. step 2
3. step 3

### Expected

- expected behavior

### Obtained

- observed behavior

### Evidence

- file paths
- relevant output
- relevant audit

### Hypothesis / Root Cause

- fill in when available

### Fix

- fill in when fixed

### Verification

- tests run
- manual validation
```

## Bugs

## BUG-012 - Read-only bootstrap commands can fail with `storage_error` due to read locks

- Status: verified
- Severity: high
- Surface: CLI | Global State | Storage
- Found on: 2026-06-05
- Context: mandatory UMEM bootstrap for agents can call `umem context --scope project --format json` and `umem skills list --format json`; these read-oriented commands were observed failing with `storage_error`.

### Reproduction

1. Use a project where UMEM bootstrap is required.
2. Run `umem status --format json`.
3. Run `umem context --scope project --format json`.
4. Run `umem skills list --format json`.

### Expected

- Read-oriented bootstrap commands should not require creating storage lock files just to inspect missing global facts or latent skills.
- Missing global JSONL files should be treated as empty storage.

### Obtained

- `umem context --scope project --format json` failed with `storage_error` / `Failed to read facts`.
- `umem skills list --format json` failed with `storage_error` / `Failed to read latent skills`.

### Evidence

- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`
- `_bmad-output/implementation-artifacts/spec-bug-012-storage-error-read-locks.md`

### Hypothesis / Root Cause

- Fact and latent skill repository read paths acquired the same JSONL lock used for mutations.
- The lock path creation makes reads non-read-only: missing global storage can cause parent directory and lock creation under `~/.local/share/umem`, which is fragile in sandboxed bootstrap contexts.

### Fix

- Removed lock acquisition from read-only fact loading.
- Removed lock acquisition from read-only latent skill loading.
- Kept lock acquisition on write/delete/purge and batch mutation paths.
- Added storage regression tests proving missing global storage reads return empty results and do not create global lock files.

### Verification

- `uv run pytest tests/infrastructure/storage/test_local_fact_repository.py tests/infrastructure/storage/test_local_latent_skill_repository.py` -> 27 passed
- `uv run pytest tests/application/memory/test_assemble_context_summary_use_case.py tests/application/skills/test_list_skills.py tests/interfaces/cli/test_skills_list.py` -> 18 passed
- `uv run pytest` -> 489 passed
- Isolated sandbox smoke with `uv --project /private/tmp/umem-worktrees/umem-storage-bugfix run umem context --scope project --format json` -> `ok: true`
- Isolated sandbox smoke with `uv --project /private/tmp/umem-worktrees/umem-storage-bugfix run umem skills list --format json` -> `ok: true`
- `find <sandbox-home>/.local/share/umem -name '*.lock' -print` -> no UMEM lock files after read-only commands

## BUG-001 - Generated `CLAUDE.md` does not satisfy the validator of `claude_code` itself

- Status: verified
- Severity: high
- Surface: Host Setup
- Found on: 2026-05-29
- Context: during manual smoke test in a clean project, `umem init` configured `claude_code`, but `umem status` returned failure for this host.

### Reproduction

1. create an empty folder
2. run `umem init`
3. accept the configuration of `claude_code`
4. run `umem status`

### Expected

- `claude_code` configured with status `success`
- `CLAUDE.md` generated in compliance with the host validation

### Obtained

- `claude_code` appears with status `failure`
- validation indicates the absence of reference to `universal-memory`, `MCP/FastMCP` or commands like `umem context/status`

### Evidence

- test project: `/Users/amorelliaoyan/projects/smart-studio/app`
- file: `/Users/amorelliaoyan/projects/smart-studio/app/CLAUDE.md`
- audit: `4bba24fd-48e4-4dfd-812f-6e60136e1f70`
- audit after clean reinstall: `996761b9-5258-478c-a979-667fcea58476`
- event: `host_validation.claude_code`
- method: `claude_md_delta_validator`

### Hypothesis / Root Cause

- the `CLAUDE.md` renderer generates a minimal block without MCP reference when there are no specific deltas
- the validator always requires this reference
- there is an inconsistency between generation and validation

### Fix

- `CLAUDE.md` generated for `claude_code` now includes a fixed operational reference to `universal-memory`, `umem context`, `umem status` and MCP/FastMCP in the managed UMEM block.
- Added regression test covering `claude_code` setup without deltas followed by successful `check=True`.

### Verification

- `uv run pytest tests/application/test_setup_host.py` -> 15 passed
- smoke in temporary sandbox: `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem init --hosts claude_code --yes --format json` -> `validation_status: success`
- smoke in temporary sandbox: `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem status --format json` -> `host_validation.claude_code.status: success`
- `uv run pytest` -> 386 passed

## BUG-003 - `umem skills list` message when no skills exist suggests a barely actionable command

- Status: verified
- Severity: low
- Surface: CLI
- Found on: 2026-05-29
- Context: during smoke test in a clean project, `umem skills list` returned an empty state with a suggestion that requires a `latent_skill_id` that the user does not have yet.

### Reproduction

1. create a clean project
2. run `umem init`
3. run `umem skills list`

### Expected

- message should guide the user to an executable next step without registered skills
- example: explain how latent skills arise or suggest an earlier workflow that generates/proposes a candidate

### Obtained

- `No skills registered.`
- `Run `umem skills propose <latent_skill_id>` to review a candidate skill.`

### Evidence

- test project: `/Users/amorelliaoyan/projects/smart-studio/app`
- command: `umem skills list`

### Hypothesis / Root Cause

- the message assumes a known candidate latent skill already exists, but in a clean onboarding there is no ID available to the user

### Fix

- The default recommendation for the empty state of `umem skills list` now explains that latent skills appear when `universal-memory` records recurring patterns.
- The message suggests an executable next step without requiring a non-existent ID: continue recording memory with `umem remember "..."` and run `umem skills list` again to track skills when a candidate appears.
- Application and CLI tests were updated to protect against the reintroduction of the direct suggestion of `umem skills propose <latent_skill_id>` in the empty state.

### Verification

- `uv run pytest tests/application/skills/test_list_skills.py tests/interfaces/cli/test_skills_list.py` -> 10 passed

## BUG-002 - Global storage strategy uses different paths by data type

- Status: verified
- Severity: medium
- Surface: Global State
- Found on: 2026-05-29
- Context: when inspecting the global state on macOS, it became clear that config, facts/rules, and latent skills use different global roots.

### Reproduction

1. inspect the code of local repositories and the config loader
2. compare the global paths used by config, facts, rules, and skills

### Expected

- consistent and predictable global strategy for all storage types

### Obtained

- global config in `~/.config/universal-memory/config.toml`
- global facts and rules in `~/.umem/`
- global latent skills in `~/.local/share/universal-memory/`

### Evidence

- `src/universal_memory/infrastructure/config/toml_loader.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `src/universal_memory/infrastructure/storage/local_rule_repository.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`

### Hypothesis / Root Cause

- the incremental evolution of the project left different global conventions between subsystems

### Fix

- Default global config moved to `~/.config/umem/config.toml`.
- Global facts, rules, and latent skills now use `~/.local/share/umem/memory/`.
- Global writes via SafeWrite for facts/rules now use the XDG data root, preserving `.umem/memory/*` only for project scope.
- Regression tests cover XDG global paths with the name `umem`.

### Verification

- `uv run pytest tests/infrastructure/config/test_toml_loader.py tests/infrastructure/storage/test_local_fact_repository.py tests/infrastructure/storage/test_local_rule_repository.py tests/infrastructure/storage/test_local_latent_skill_repository.py tests/interfaces/cli/test_skills_propose.py` -> 44 passed
- `uv run pytest tests/infrastructure/security/test_local_audit_log_repository.py::test_concurrent_writes_preserve_all_jsonl_events` -> 1 passed after transient concurrent failure in the first complete suite run
- `uv run pytest` -> 390 passed

## BUG-004 - Rollback fails when the snapshot represents a non-existent file before the mutation

- Status: verified
- Severity: high
- Surface: CLI | MCP | Snapshots | Rollback
- Found on: 2026-05-29
- Context: during the execution of the plan `docs/alpha-sandbox-test-plan.md`, rollback in a newly initialized sandbox failed after creating the project's first fact.

### Reproduction

1. create a clean sandbox with isolated `HOME`, `XDG_CONFIG_HOME`, and `XDG_DATA_HOME`
2. run `uv run --project <repo> umem init --yes --format json`
3. run `uv run --project <repo> umem remember "Fato antes do rollback." --scope project --format json`
4. run `uv run --project <repo> umem rollback --scope project --yes --format json`

### Expected

- rollback uses the most recent snapshot
- `.umem/memory/facts.jsonl` returns to the expected previous state
- rollback event appears successfully in the audit log

### Obtained

- rollback returns a storage error
- message: `Snapshot backup file not found: <snapshot-id>`
- memory file still has the active fact
- audit log records `rollback` with `result=failure`

### Evidence

- observed sandbox: `/tmp/umem-rollback.0RhTdN/project`
- CLI error: `Snapshot backup file not found: cdedaf37-f300-4cf9-a4ed-a94d38092a39`
- manifest registers `write_fact` snapshot for `.umem/memory/facts.jsonl`
- `.umem/snapshots/files/` directory was empty in the case where the file did not exist before the first write
- the same symptom appeared via MCP in `rollback_scope(scope="project", confirm=true)`: `Snapshot backup file not found: 27f1cf91-3c5f-44e5-870f-43cb271f7c27`

### Hypothesis / Root Cause

- `SafeWriteUseCase` creates a snapshot with hash of `previous_bytes=b""` when the target file does not yet exist
- `LocalSnapshotRepository._copy_current_file()` returns `None` when the source file does not exist and does not create a physical empty backup in `.umem/snapshots/files/<snapshot-id>`
- `RollbackUseCase` always calls `snapshot_repository.get_content(snapshot.id)`, so snapshots without a physical file are not restorable

### Fix

- `Snapshot` now records `previous_file_existed`, allowing to distinguish absent previous state from empty existing file.
- `SafeWriteUseCase` populates this metadata before creating the snapshot.
- `RollbackUseCase` removes the target file when the snapshot represents previous absence; normal snapshots continue to require physical backup and SHA-256 validation.
- Rollback validates empty hash before removing a created file and handles legacy snapshots without `previous_file_existed` when the physical backup is absent and the hash is of empty content.
- Application, infrastructure, CLI, and MCP tests cover rollback after first mutation in a clean sandbox, legacy manifest, and inconsistent hash rejection.

### Verification

- `uv run pytest tests/application/security/test_rollback_use_case.py tests/infrastructure/security/test_local_snapshot_repository.py tests/interfaces/cli/test_rollback_command.py tests/interfaces/mcp/test_server.py::test_real_mcp_rollback_removes_file_created_by_first_remember` -> 27 passed
- smoke CLI in isolated sandbox: `umem init`, `umem remember "Fato antes do rollback." --scope project`, `umem rollback --scope project --yes --format json`, followed by `test ! -e .umem/memory/facts.jsonl` -> rollback `ok=true`
- real MCP test with `initialize_project`, `remember_fact` and `rollback_scope(scope="project", confirm=true)` -> rollback `ok=true` and file removed
- `uv run pytest` -> 395 passed

## BUG-005 - MCP errors do not preserve uniform envelope with `operation`, `scope` and `warnings`

- Status: verified
- Severity: medium
- Surface: MCP
- Found on: 2026-05-29
- Context: during black-box MCP test via `stdio` with a real FastMCP client, controlled errors returned a partial payload different from the envelope required by the plan.

### Reproduction

1. start `umem-mcp` via MCP client in a clean sandbox
2. initialize project with `initialize_project`
3. create/list a fact to obtain `id`
4. call `purge_fact(id=<id>, confirm=false)`

### Expected

- all MCP responses follow an envelope with `ok`, `operation`, `scope`, `data`, `warnings`
- destructive errors without confirmation return a controlled error keeping operation and scope metadata

### Obtained

- error returns only `ok=false` and `error`
- `operation`, `scope`, and `warnings` are missing
- same pattern appeared in errors from `rollback_scope`, `activate_skill`, and `update_skill`

### Evidence

- observed sandbox: `/tmp/umem-mcp.TgpvXe/project`
- call: `purge_fact(id=<id>, confirm=false)`
- observed payload: keys `error`, `ok`
- error: `Validation failed.`, detail `Purging facts is destructive and requires explicit confirmation. Please call this tool with confirm=True.`
- additional sandbox: `/tmp/umem-mcp2.pDb3Xp/project`
- failed `rollback_scope` also returned only `error`, `ok`

### Hypothesis / Root Cause

- MCP exception handling builds a JSON-RPC error envelope without filling the common fields used in the success envelope
- MCP error contract is not aligned with the contract documented in the alpha plan

### Fix

- `_mcp_tool_error` now preserves the uniform MCP envelope in failures as well, filling in `ok=false`, `operation`, `scope`, `data`, `warnings`, and `error`.
- MCP tools explicitly pass the expected operation and scope when building controlled errors, including `purge_fact`, `rollback_scope`, `activate_skill`, and `update_skill`.
- Regression tests cover destructive errors without confirmation and skill mutation errors maintaining `operation`, `scope`, and `warnings`.

### Verification

- `uv run pytest tests/interfaces/mcp/test_server.py tests/interfaces/mcp/test_skills.py` -> 25 passed
- `uv run pytest tests/interfaces/mcp` -> 29 passed
- Validated by automated regression that error responses include `ok`, `operation`, `scope`, `data`, `warnings`, and `error`.

## BUG-006 - MCP allows mutation before initialization and leaves a partial `.umem` layout

- Status: verified
- Severity: high
- Surface: MCP | Onboarding | Storage
- Found on: 2026-05-29
- Context: during black-box MCP testing, an invalid call to `initialize_project` followed by mutation (`remember_fact`) created part of the `.umem` layout; afterwards, `initialize_project` could not repair the partial state.

### Reproduction

1. create a clean sandbox for MCP
2. call `initialize_project` with invalid arguments, for example `yes` and `hosts`
3. call `remember_fact(content="MCP grava fatos corretamente", scope="project", tags=["mcp"])`
4. call `initialize_project` again without arguments

### Expected

- mutations before initialization are blocked with a controlled error without creating a partial layout, or
- `initialize_project` repairs/completes a partial layout created by previous operations

### Obtained

- `remember_fact` executes and creates a partial state
- subsequent call to `initialize_project {}` fails with `storage_error`
- detail: `Project layout '.umem' is partial or corrupted; missing canonical paths: .umem/config.toml, .umem/skills, .umem/benchmarks, .umem/benchmarks/retrieval-results.json`

### Evidence

- observed sandbox: `/tmp/umem-mcp.TgpvXe/project`
- `initialize_project` with arguments `yes` and `hosts` failed due to unexpected arguments
- `remember_fact` immediately after returned `ok=true`
- `initialize_project {}` later returned a partial/corrupted layout error
- in a clean MCP sandbox, `initialize_project {}` worked correctly, isolating the issue to the partial state created before init

### Hypothesis / Root Cause

- mutation MCP tools do not require the project to be initialized before writing to `.umem`
- layout validation/repair in onboarding treats partial layout as fatal corruption instead of completing missing canonical paths

### Fix

- MCP tools with `project` scope now require the project to be initialized before accessing use cases that read or write local state.
- The guard uses `status(GetMemoryStatusCommand(project_root=...))` and returns a controlled error with a uniform MCP envelope when the layout does not yet exist, guiding to call `initialize_project` first.
- `initialize_project` and `status` remain allowed before initialization; `global` operations remain available without creating the project's `.umem`.
- Added real regression test for `remember_fact(scope="project")` before init, ensuring that `.umem` is not partially created and that a subsequent `initialize_project {}` completes the canonical layout.

### Verification

- `uv run pytest tests/interfaces/mcp/test_server.py` -> 18 passed
- `uv run pytest tests/interfaces/mcp` -> 30 passed
- `uv run pytest` -> 397 passed

## BUG-007 - Alpha plan uses incorrect arguments for skill MCP tools

- Status: verified
- Severity: low
- Surface: Docs | MCP | Skills
- Found on: 2026-05-30
- Context: during a new black-box execution of the plan `docs/alpha-sandbox-test-plan.md` with a real FastMCP client via `stdio`, the skill MCP workflow failed when executed with arguments inferred from the plan/CLI.

### Reproduction

1. create an isolated sandbox with `HOME`, `XDG_CONFIG_HOME`, and `XDG_DATA_HOME`
2. start `umem-mcp` via a real FastMCP client using `uv run --project <repo> umem-mcp`
3. initialize project with `initialize_project`
4. create a valid fixture in `.umem/memory/latent_skills.jsonl`
5. call `get_skill_detail(latent_skill_id=<id>)`
6. call `generate_skill(latent_skill_id=<id>, confirm=true)`

### Expected

- the alpha plan should reflect the real names of the MCP arguments exposed by the tools' schemas
- a person following the plan should not need to infer differences between CLI and MCP

### Obtained

- `get_skill_detail` rejects `latent_skill_id`; the real argument is `name_or_id`
- `generate_skill` rejects `confirm`; the real MCP tool accepts `latent_skill_id` and `update_existing`
- when correcting the flow to `get_skill_detail(name_or_id=<id>)` and `generate_skill(latent_skill_id=<id>)`, the tools succeed with a valid MCP envelope

### Evidence

- MCP sandbox failing due to argument: `/var/folders/f1/xg5dn91j7bj59zh2ljy9czlm0000gn/T/umem-mcp-smoke.yvochg57/project`
- observed error in `get_skill_detail`: `Missing required argument name_or_id` and `Unexpected keyword argument latent_skill_id`
- observed error in `generate_skill`: `Unexpected keyword argument confirm`
- MCP code: `src/universal_memory/interfaces/mcp/server.py`
- observed signatures: `get_skill_detail(name_or_id: str)` and `generate_skill(latent_skill_id: str, update_existing: bool = False)`

### Hypothesis / Root Cause

- the alpha plan mixes the CLI contract (`skills detail <id>`, `skills generate <id> --yes`) with the real MCP contract
- the plan documentation was not updated after the stabilization of the skill MCP signatures

### Fix

- `docs/alpha-sandbox-test-plan.md` updated to use `get_skill_detail(name_or_id=<id>)` in the skill MCP workflow.
- `generate_skill` in the MCP workflow now uses `generate_skill(latent_skill_id=<id>, update_existing=false)` and validation documents that MCP tools must not reuse CLI flags like `--yes` or `confirm`.
- The recommended MCP sequence now explicitly includes the skill steps with argument names exposed by the real MCP schema.

### Verification

- corrected flow validated via a real FastMCP client in sandbox: `/var/folders/f1/xg5dn91j7bj59zh2ljy9czlm0000gn/T/umem-mcp-skills.pmuawni_/project`
- corrected skill MCP checks: 19 passed, 0 failed
- document inspection: `docs/alpha-sandbox-test-plan.md` now references `get_skill_detail(name_or_id=<id>)` and `generate_skill(latent_skill_id=<id>, update_existing=false)`, without `confirm` in the skill MCP workflow.

## BUG-008 - Alpha plan does not list `deactivate_skill` among expected MCP tools

- Status: verified
- Severity: low
- Surface: Docs | MCP | Skills
- Found on: 2026-05-30
- Context: during a new black-box execution of the plan `docs/alpha-sandbox-test-plan.md`, the complete MCP skill workflow required `deactivate_skill` to validate `generate -> deactivate -> activate -> update`, but the list of expected tools in the plan omits this tool.

### Reproduction

1. open `docs/alpha-sandbox-test-plan.md`
2. verify section `8. MCP Black-Box`
3. compare the list of expected tools with the real tools exposed by the MCP server

### Expected

- the plan's MCP tool list should include all public tools relevant to the alpha skill workflow
- the MCP workflow should mirror CLI coverage where applicable

### Obtained

- the list includes `activate_skill` and `update_skill`, but does not include `deactivate_skill`
- `deactivate_skill` is exposed by the MCP server and passed the corrected black-box test

### Evidence

- plan: `docs/alpha-sandbox-test-plan.md`, section `8. MCP Black-Box`
- MCP code: `src/universal_memory/interfaces/mcp/server.py`
- real tool observed via `client.list_tools()`: `deactivate_skill`
- corrected validation: `/var/folders/f1/xg5dn91j7bj59zh2ljy9czlm0000gn/T/umem-mcp-skills.pmuawni_/project`

### Hypothesis / Root Cause

- documentation gap in the alpha plan after the introduction of the skill deactivation MCP tool

### Fix

- `deactivate_skill` added to the expected MCP tools list in `docs/alpha-sandbox-test-plan.md`.
- The MCP skill workflow now explicitly includes `deactivate_skill(latent_skill_id=<id>)` before `activate_skill(latent_skill_id=<id>)`.

### Verification

- corrected workflow with `deactivate_skill` validated via a real FastMCP client: 19 passed, 0 failed
- document inspection: `docs/alpha-sandbox-test-plan.md` lists `deactivate_skill` and includes the step `deactivate_skill(latent_skill_id=<id>)` before `activate_skill(latent_skill_id=<id>)`.

## BUG-009 - Alpha plan uses singular `trigger` in `update_skill` MCP

- Status: verified
- Severity: low
- Surface: Docs | MCP | Skills
- Found on: 2026-05-30
- Context: during a new black-box execution of the plan `docs/alpha-sandbox-test-plan.md` with a real FastMCP client via `stdio`, the final step of MCP skills failed when following the plan literally.

### Reproduction

1. create an isolated sandbox with `HOME`, `XDG_CONFIG_HOME`, and `XDG_DATA_HOME`
2. start `umem-mcp` via a real FastMCP client using `uv run --project <repo> umem-mcp`
3. initialize project with `initialize_project`
4. create a valid fixture in `.umem/memory/latent_skills.jsonl`
5. execute the MCP skill workflow up to `activate_skill(latent_skill_id=<id>)`
6. call `update_skill(latent_skill_id=<id>, name="Nova Skill", trigger="when reviewing context")`

### Expected

- the alpha plan should use the real names of the MCP arguments exposed by the tool schema
- the `update_skill` step should be executable by a person following the plan literally

### Obtained

- FastMCP rejects `trigger` as an unexpected argument
- observed error: `Unexpected keyword argument` in `trigger`
- the corrected call `update_skill(latent_skill_id=<id>, name="Nova Skill", triggers=["when reviewing context"])` works

### Evidence

- MCP sandbox: `/tmp/umem-alpha.CVvZrW/mcp-project-full2`
- real tool: `update_skill(latent_skill_id: str, name: str | None = None, description: str | None = None, triggers: list[str] | None = None, raw_markdown: str | None = None)`
- plan: `docs/alpha-sandbox-test-plan.md`, section `8. MCP Black-Box`, step 19

### Hypothesis / Root Cause

- the plan reused the singular CLI concept `--trigger`, but the stabilized MCP tool uses plural `triggers` in a list format

### Fix

- `docs/alpha-sandbox-test-plan.md` updated to use `update_skill(latent_skill_id=<id>, name="Nova Skill", triggers=["when reviewing context"])`.

### Verification

- corrected MCP workflow validated via a real FastMCP client: `MCP_ALPHA_OK project=/tmp/umem-alpha.CVvZrW/mcp-project-full2 fact_id=1fad751f-27d6-49ec-9531-d04901731843 latent_skill_id=9e5b5b6f-30bc-4d67-ab85-6e382e38278e`
- CLI/MCP compatibility validated in the same sandbox: `CLI_MCP_COMPAT_OK project=/tmp/umem-alpha.CVvZrW/mcp-project-full2 global_home=/tmp/umem-alpha.CVvZrW/home`

## BUG-010 - Alpha plan passes `scope` to `list_skills` MCP, but the tool does not accept filters

- Status: verified
- Severity: low
- Surface: Docs | MCP | Skills
- Found on: 2026-05-30
- Context: during a new black-box execution of the plan `docs/alpha-sandbox-test-plan.md` with a real FastMCP client via `stdio`, the MCP skill workflow failed when following the step `list_skills(scope="project")` literally.

### Reproduction

1. create an isolated sandbox with `HOME`, `XDG_CONFIG_HOME`, and `XDG_DATA_HOME`
2. start `umem-mcp` via a real FastMCP client using `uv run --project <repo> umem-mcp`
3. initialize project with `initialize_project`
4. create a valid fixture in `.umem/memory/latent_skills.jsonl`
5. call `list_skills(scope="project")`

### Expected

- the alpha plan should use only arguments exposed by the real MCP schema
- the MCP skill workflow should be executable literally by a person following the plan

### Obtained

- FastMCP rejects `scope` as an unexpected argument in `list_skills`
- the real tool is exposed as `list_skills()` without arguments
- when correcting the call to `list_skills()`, the complete MCP workflow succeeds

### Evidence

- MCP sandbox failing due to argument: `/var/folders/f1/xg5dn91j7bj59zh2ljy9czlm0000gn/T/umem-alpha-smoke.ds51m9tj/mcp-project`
- observed error: `Unexpected keyword argument` in `scope`
- MCP code: `src/universal_memory/interfaces/mcp/server.py`
- observed signature: `list_skills()`

### Hypothesis / Root Cause

- the alpha plan reused the scope filtering pattern from other MCP tools, but `list_skills` MCP currently lists skills without accepting arguments

### Fix

- `docs/alpha-sandbox-test-plan.md` updated to use `list_skills()` in the MCP skill workflow.
- Document validation now makes it explicit that MCP skill tools should not receive unexposed filters like `scope` in `list_skills()`.

### Verification

- complete alpha workflow validated via a sandbox runner with a real FastMCP client over `stdio`: `ALPHA_SMOKE_OK sandbox=/var/folders/f1/xg5dn91j7bj59zh2ljy9czlm0000gn/T/umem-alpha-smoke.mq1so31a`
- the validated workflow covered CLI, MCP, CLI/MCP compatibility, hosts, snapshots, rollback, purge, local/global memory, and skill generation/activation/updating.

## BUG-011 - `umem init` ANSI banner still renders broken

- Status: open
- Severity: low
- Surface: CLI
- Found on: 2026-06-02
- Context: during the inclusion of the visual identity for `umem init`, the ANSI banner was saved even though it still showed a broken rendering.

### Reproduction

1. run `umem init` in a terminal with color support
2. observe the splash displayed before the runtime selection prompt

### Expected

- visual banner aligned, legible, and consistent in common terminals
- legible colorless fallback when ANSI is not enabled

### Obtained

- ANSI banner known to be broken/misaligned
- change was preserved for a later fix

### Evidence

- `src/universal_memory/interfaces/cli/init_command.py`
- `assets/umem-logo.png`

### Hypothesis / Root Cause

- conversion of the visual asset to ANSI needs adjustment of width, palette, or rendering strategy

### Fix

- pending

### Verification

- pending

## BUG-012 - UMEM bootstrap can be ignored when a skill workflow takes priority

- Status: verified
- Severity: medium
- Surface: Host Setup | Skills | Runtime Behavior
- Found on: 2026-06-02
- Context: during real testing with Claude Code in another project, the UMEM block in `CLAUDE.md` was present and validated, but the agent only executed `umem status/context/skills` when the user explicitly requested it. In a session with BMad workflow, the structured activation of the skill competed with the manifest instructions and took operational priority.

### Reproduction

1. initialize a project with `umem init` for `claude_code`
2. confirm `umem status --format json` has `host_validation.claude_code.status: success`
3. start a task via a skill/workflow with strong activation, such as code review
4. observe if the agent executes `umem status --format json`, `umem context --scope project --format json`, and `umem skills list --format json` before the workflow

### Expected

- the agent must load the UMEM context before planning, editing, investigating, reviewing, implementing, or running skill workflows
- if `umem` is unavailable or not initialized, the agent must explicitly report this before continuing without external memory
- the operational contract must make it clear that the UMEM bootstrap precedes skills, slash commands, and structured workflows

### Obtained

- the UMEM block in `CLAUDE.md` can be read as a declarative instruction, but not as an inevitable preflight
- skill workflows with detailed activation steps can capture the agent's attention before it runs the UMEM bootstrap
- the user needs to explicitly ask the agent to use `umem` to ensure loading

### Evidence

- generated `CLAUDE.md` contains commands `umem status --format json`, `umem context --scope project --format json`, `umem skills list --format json` and reference to `.umem/skills/use-universal-memory/SKILL.md`
- `src/universal_memory/application/host/setup_host_use_case.py` renders the managed blocks in `AGENTS.md` and `CLAUDE.md`
- `tests/application/test_setup_host.py` validates the presence of commands and host reading, but does not validate execution priority over skill workflows
- `.umem/skills/use-universal-memory/SKILL.md` describes the operational procedure, but native activation still relies on the agent respecting the manifest
- Operational validation in this session: even when initiated by `$bmad-dev-story`, execution ran `umem status --format json`, `umem context --scope project --format json` and `umem skills list --format json` before the skill activation; the commands reported a storage error, which was made explicit before continuing.

### Hypothesis / Root Cause

- the product validates the textual presence of the bootstrap, but lacks an operational guarantee of execution order
- agents prioritize more procedural and recent instructions when a skill enters activation mode
- the current instruction does not make it strong enough that the UMEM bootstrap must run before any skill, slash command, or structured workflow

### Fix

- The text generated for `AGENTS.md` now declares the UMEM bootstrap as a mandatory preflight before planning, editing, investigating, reviewing, skill workflow, slash command, or structured workflow.
- The text generated for `CLAUDE.md`, both in full manifest mode and delta mode with an existing `AGENTS.md`, now reinforces that the UMEM bootstrap precedes skill workflows and requires explicit reporting when `umem` is unavailable or not initialized.
- The default skill `.umem/skills/use-universal-memory/SKILL.md` generated by `umem init` now instructs that skills, slash commands, and structured workflows do not replace the UMEM preflight.
- Regression tests were updated to validate the operational priority of the preflight in host blocks and the default skill.

### Verification

- `uv run pytest tests/application/test_setup_host.py tests/application/test_setup_project.py tests/application/host/test_sync_instructions.py` -> 30 passed
- `uv run pytest` -> 457 passed
- Temporary sandbox in `/private/tmp/umem-bug012.STlwSX`: `uv run umem init --hosts claude_code --yes --format json` -> `validation_status: success`
- Temporary sandbox in `/private/tmp/umem-bug012.STlwSX`: `uv run umem host check claude_code --format json` -> `validation_status: success`
- Temporary sandbox in `/private/tmp/umem-bug012.STlwSX`: `rg -n 'mandatory preflight|skill workflow|slash command|not initialized|Do not let the workflow replace this preflight' CLAUDE.md .umem/skills/use-universal-memory/SKILL.md` confirmed the reinforced contract in `CLAUDE.md` and the default skill.

## BUG-013 - Host synchronization fails (exceeds maximum size) due to fact / memory dump in AGENTS.md and CLAUDE.md

- Status: verified
- Severity: high
- Surface: Host Setup
- Found on: 2026-06-02
- Context: When the user or agent registers multiple facts in memory via `umem remember`, the `umem host sync` command tries to actively synchronize all facts in the consolidated policies section of the host files (`AGENTS.md` and `CLAUDE.md`). This rapidly bloats those files and causes the line/character limit validation (100 lines / 4000 characters) to fail, preventing the synchronization of legitimate rules.

### Reproduction

1. create multiple facts via `umem remember "Fato X" --scope project`
2. run `umem host sync --apply`
3. observe validation error: `ValidationFailedError: AGENTS.md manifest must remain compact; move long content to docs/.`

### Expected

- The agent should be able to load and synchronize legitimate rules without facts and memories exploding the physical size of the host's static instruction files.
- Dynamic context facts/memories should be consumed on demand via the `umem context` command and not duplicated/injected textually into static manifests.

### Obtained

- Synchronization failed when exceeding 100 lines or 4000 characters in `AGENTS.md` due to the accumulation of dynamic memories.
- Absence of global configuration keys for limits in `.umem/config.toml` or CLI flags `--max-lines`/`--max-chars` in `host sync` made fine control of limits difficult.

### Evidence

- `src/universal_memory/application/host/setup_host_use_case.py`
- `src/universal_memory/application/host/sync_instructions_use_case.py`
- `tests/application/host/test_sync_instructions.py`

### Hypothesis / Root Cause

- The UMEM design intends for dynamic context facts and memories to be consumed by the agent dynamically via the `umem context` command. Therefore, dumping the entire history of facts into static host text files (`AGENTS.md`/`CLAUDE.md`) causes redundancy and unnecessarily blows past physical size limits.

### Fix

- We decoupled fact persistence from `ConfigureHostUseCase` and `SyncInstructionsUseCase`. Now, only fact rules (`Rule`) are compiled into host manifests.
- We added persistent support for size limits (`max_managed_lines` and `max_managed_chars`) in the `.umem/config.toml` file (tables `[runtimes]` or `[hosts]`) and CLI flags `--max-lines` / `--max-chars` in the `host sync` command to give full flexibility to the user.
- Host manifests remain static, stable, and compact, directing the agent to use `umem context` for dynamic reading of facts.

### Verification

- Tests added in `test_sync_instructions.py` and `test_host_sync.py` validate support for size limits via `config.toml` and CLI.
- Entire suite of 459 tests passing (`uv run pytest`).

## BUG-014 - `umem host sync --host codex` rejects a supported host as if none was provided

- Status: open
- Severity: medium
- Surface: CLI | Host Setup
- Found on: 2026-06-05
- Context: after recording a project memory fact, the required `umem host sync` follow-up could not be completed for the configured `codex` runtime because the CLI rejected the explicit host argument.

### Reproduction

1. in a project with `.umem/config.toml` containing `runtimes.enabled = ["opencode", "codex", "antigravity"]`
2. run `umem host sync --host codex --apply --yes --format json`
3. run `umem host sync --host=codex --apply --yes --format json`

### Expected

- the CLI should accept `codex` as a supported host/runtime for synchronization
- the command should synchronize the `AGENTS.md` host instructions or return a specific validation error about the target file

### Obtained

- both command forms fail with `validation_failed`
- error detail: `Nenhum host suportado informado para sincronizacao.`

### Evidence

- `.umem/config.toml`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/application/host/sync_instructions_use_case.py`
- observed command output: `{"error": {"code": "validation_failed", "detail": "Nenhum host suportado informado para sincronizacao."}, "ok": false}`

### Hypothesis / Root Cause

- the CLI parser or command adapter may not be passing the `--host` option into `SyncInstructionsCommand.host_ids` as expected, despite `codex` being listed in `DEFAULT_SYNC_HOSTS`
- another possibility is a mismatch between runtime-enabled values and sync-supported hosts that collapses the normalized host list to empty

### Fix

- pending

### Verification

- pending
