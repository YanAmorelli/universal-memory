# Story 6.11: Agent Skills Sync Canonical to Native Targets

Status: done

## Story

As a user or MCP-consuming agent,
I want to synchronize canonical UMEM Agent Skills into configured native host skill targets,
so that native agent directories can be repaired from `.umem/skills` without making native targets authoritative.

## Acceptance Criteria

1. **Given** one or more active canonical `AgentSkill` records exist in `.umem/memory/skills.jsonl`, **When** `umem skills sync --format json` runs, **Then** each selected canonical skill is read from the canonical store and synchronized to enabled native runtimes using the existing runtime registry target definitions, **And** native host files are materialized from the canonical `.umem/skills/<slug>/` source.
2. **Given** a specific skill is requested by ID or exact name, **When** `umem skills sync <skill-id-or-name>` runs, **Then** only that canonical skill is synchronized, **And** ambiguous names or missing skills fail with a safe validation error before any native target is written.
3. **Given** `--target` is provided one or more times, **When** sync runs, **Then** only those native runtimes are considered, **And** unsupported runtime IDs fail with the same validation policy used by `NativeSkillSync`.
4. **Given** a native target is missing, **When** sync runs, **Then** the missing native target is created through `SafeWriteUseCase`, **And** the response includes target-level runtime, path, status, audit reference, snapshot reference, canonical hash, target hash, and affected paths.
5. **Given** a previously managed native target has manual drift, **When** non-interactive sync or JSON sync runs without an explicit overwrite choice, **Then** drift is reported and the native target is not overwritten by default, **And** the response includes a warning using the existing drift warning semantics.
6. **Given** a previously managed native target has manual drift, **When** interactive human CLI sync is run and the user chooses overwrite, **Then** a snapshot is created before overwrite, the native target is rewritten from canonical content, and the response records the overwrite warning, audit reference, and snapshot reference.
7. **Given** an existing native skill folder is not registered as a managed installation for the selected canonical skill, **When** sync runs with the default keep behavior, **Then** it is reported as `unmanaged_native` and preserved, **And** no import, registry adoption, or canonical overwrite is performed.
8. **Given** a canonical skill record references a missing or invalid canonical `SKILL.md`, **When** sync runs, **Then** sync fails for that skill before any native write, **And** the error identifies the skill and relative canonical path without exposing absolute project paths or secrets.
9. **Given** MCP calls `sync_skills(skill_id_or_name=None, targets=None, drift_decision="keep")`, **When** the tool executes, **Then** it delegates to the same application use case as the CLI, returns the same semantic payload as CLI JSON, and maps expected domain errors through the existing JSON-RPC error policy.
10. **Given** the sync story is implemented, **When** CLI/MCP parity tests and focused skill sync tests run, **Then** they prove no recommend, promote, import, latent recommendation, or orphan-adoption workflow is introduced by this story.

## Tasks / Subtasks

- [x] **Task 1: Add canonical sync application use case** (AC: 1, 2, 3, 4, 5, 7, 8)
  - [x] Create `SyncSkillsUseCase`, command, per-skill result, and aggregate result in `src/universal_memory/application/skills/`.
  - [x] Inject `AgentSkillRepository`, `SafeWriteUseCase`, optional global safe write support, and optional `RuntimeRegistry` through the application layer.
  - [x] Resolve all active canonical skills by default; resolve a single skill by ID or exact case-insensitive name when `skill_id_or_name` is provided.
  - [x] Fail ambiguous or missing skill selectors with `ValidationFailedError` before writing any native targets.
  - [x] Validate canonical skill files before native sync by parsing Agent Skills frontmatter with the existing skill markdown parser/validation path.
  - [x] Keep paths in use-case payloads relative to the project root or canonical UMEM data root.
- [x] **Task 2: Reuse and minimally extend native sync behavior** (AC: 1, 3, 4, 5, 6, 7)
  - [x] Reuse `NativeSkillSync.sync`; do not create a second native-target writer.
  - [x] Preserve the existing `keep` default for non-interactive/automation flows.
  - [x] Support explicit overwrite by passing `drift_decision="overwrite"` only when the CLI/MCP caller explicitly requested it.
  - [x] Ensure missing targets, managed drift, and unmanaged native targets return explicit target statuses.
  - [x] Persist updated `native_installations` and content/target metadata back to `AgentSkillRepository` after successful per-skill sync.
- [x] **Task 3: Expose `umem skills sync` in the CLI** (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [x] Add `umem skills sync [skill-id-or-name]` to the Typer skills command group.
  - [x] Add repeatable `--target <runtime-id>` options.
  - [x] Add an explicit overwrite option for automation, for example `--drift-decision overwrite` or equivalent existing CLI style; keep default as `keep` for JSON/non-interactive flows.
  - [x] For interactive human output, prompt before overwriting managed drift using the existing `DRIFT_WARNING` text and choices, then pass `overwrite` only after user confirmation.
  - [x] Ensure `--format json` emits JSON only and includes `warnings[]`, `affected_paths[]`, per-skill results, and per-target results.
- [x] **Task 4: Expose `sync_skills` in MCP** (AC: 2, 3, 5, 7, 9)
  - [x] Add `sync_skills(skill_id_or_name=None, targets=None, drift_decision="keep")` to the MCP server.
  - [x] Wire the use case in `src/universal_memory/bootstrap/mcp.py` and CLI bootstrap as needed.
  - [x] Reject any drift decision other than `keep` or `overwrite` with `ValidationFailedError`.
  - [x] Return the same semantic fields as CLI JSON without transport-specific leakage.
- [x] **Task 5: Add focused tests and parity coverage** (AC: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
  - [x] Add application tests for syncing all canonical active skills and syncing one selected skill.
  - [x] Add tests for missing native targets, managed drift kept by default, overwrite with snapshot, and unmanaged native target preservation.
  - [x] Add tests for missing/invalid canonical `SKILL.md` failing before native writes.
  - [x] Add CLI tests for human output semantics and JSON parseability.
  - [x] Add MCP tests for `sync_skills` payloads and error mapping.
  - [x] Update CLI/MCP parity tests so public sync capability is present on both surfaces.
  - [x] Add explicit regression assertions that this story does not add import, recommend, promote, or orphan-adoption behavior.
- [x] **Task 6: Validate and hand off for BMAD review** (AC: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
  - [x] Run focused tests for new sync use case, CLI, MCP, and parity coverage.
  - [x] Run `uv run pytest` if feasible before moving to review.
  - [x] Run `uv run ruff check .`.
  - [x] Run `uv run ruff format --check .`.
  - [x] Run `uv run pyright`.
  - [x] Move this story to `review` only after implementation and validation are complete.

## Dev Notes

- **Spec source:** `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`, especially FR4, FR6, Phase 2, acceptance criteria 4 and 5, and the non-goals that native directories are not authoritative.
- **Scope boundary:** This story is only sync/repair from canonical `.umem/skills` to native host targets. Do not implement `skills recommend`, `recommend_skills`, `skills promote`, `promote_skill_recommendation`, `skills import`, native orphan adoption, candidate surfacing, recommendation thresholds, or evidence expansion.
- **Canonical source of truth:** Read canonical records from `AgentSkillRepository` and canonical content from `.umem/skills/<slug>/SKILL.md` for project scope or the global UMEM skill root for global scope. Native host directories are materialized targets only.
- **Existing code to reuse:** `src/universal_memory/application/skills/native_skill_sync.py` already handles enabled runtime discovery, target filtering, canonical tree hashing, missing target writes, managed drift keep/overwrite, unmanaged native target preservation, and safe writes. Extend it only if the story cannot be satisfied through the current API.
- **Existing parser/validation:** `src/universal_memory/application/skills/update_skill.py` exposes `_parse_skill_markdown`; `CreateSkillUseCase` already uses it to validate direct-create raw markdown. Reuse existing validation behavior rather than adding a separate parser.
- **Repository pattern:** `src/universal_memory/infrastructure/storage/local_agent_skill_repository.py` is the canonical registry implementation. Use repository methods rather than reading or writing `.umem/memory/skills.jsonl` directly from CLI/MCP adapters.
- **Adapter thinness:** CLI and MCP must delegate to the application use case. Do not put sync, drift, or repository logic in `src/universal_memory/interfaces/cli/init_command.py` or `src/universal_memory/interfaces/mcp/server.py` beyond argument parsing and response formatting.
- **Drift behavior:** Keep is the safe default in non-interactive and JSON paths. Overwrite must be explicit, and interactive human CLI overwrite must prompt with the existing `DRIFT_WARNING` copy before writing.
- **Payload guidance:** Prefer a payload shape like `skills[]`, each with `skill_id`, `name`, `scope`, `status`, `canonical_path`, `affected_paths[]`, `targets[]`, `warnings[]`, `audit_reference`, and `snapshot_reference`. Target entries should include runtime, path, status, drift flag, canonical hash, target hash, audit reference, and snapshot reference where available.
- **Global skill caution:** Direct create already supports global canonical storage by passing the global safe write use case and `canonical_base_path`. Sync must preserve that distinction when resolving canonical paths while still materializing native project targets only when requested/enabled.
- **Previous story intelligence:** Story 6.7 established the canonical `AgentSkill` entity, direct create use case, local registry, CLI/MCP create path, list/detail canonical support, and native target preservation. Story 6.8 updated agent-facing latent-skill guidance and host instruction compactness. Do not regress either behavior.
- **Known handover fixes to preserve:** Unmanaged native targets must not be overwritten under keep/default behavior; create failure cleanup must not be weakened; MCP `create_skill` must continue supporting `targets=[]` to disable native installation.

### Project Structure Notes

- Expected new application file: `src/universal_memory/application/skills/sync_skills.py`.
- Expected exports: `src/universal_memory/application/skills/__init__.py`.
- Expected bootstrap wiring: `src/universal_memory/bootstrap/cli.py` and `src/universal_memory/bootstrap/mcp.py`.
- Expected CLI/MCP adapters: `src/universal_memory/interfaces/cli/init_command.py`, `src/universal_memory/interfaces/mcp/server.py`, and MCP use-case container definitions.
- Expected tests: focused application tests under `tests/application/skills/`, CLI tests under `tests/interfaces/cli/`, MCP tests under `tests/interfaces/mcp/`, and parity tests in `tests/interfaces/test_parity.py`.

### References

- `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md` (FR4, FR6, Phase 2, AC4-AC5, Non-Goals)
- `_bmad-output/implementation-artifacts/6-7-agent-skills-canonical-registry-and-direct-create.md`
- `_bmad-output/implementation-artifacts/6-8-agent-instruction-loop-for-latent-skills.md`
- `_bmad-output/planning-artifacts/epics.md` (Story 6.3 FR31/FR32 sync/drift behavior; Story 6.6 CLI/MCP parity)
- `_bmad-output/planning-artifacts/prd.md` (FR20-FR21, FR31-FR32, FR22-FR28 safety guardrails)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (JSON output, confirmation, and MCP parity contracts)
- `src/universal_memory/application/skills/native_skill_sync.py`
- `src/universal_memory/application/skills/create_skill.py`
- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/infrastructure/storage/local_agent_skill_repository.py`

## Dev Agent Record

### Agent Model Used

gpt-5.5

### Debug Log References

- `uv run pytest tests/application/skills/test_sync_skills.py tests/interfaces/cli/test_skills_sync.py tests/interfaces/mcp/test_skills.py tests/interfaces/test_parity.py` - passed, 48 tests.
- `uv run pytest` - failed with 6 failures from concurrent/non-6.11 files: default UMEM skill template mismatch, promote CLI failures, MCP compliance inventory containing promote/import/sync, and missing promote import in MCP tests.
- `uv run ruff check .` - failed on concurrent import/promote files plus one sync line-length issue; sync issue fixed afterward.
- `uv run ruff format --check .` - failed on files with concurrent phase formatting drift plus shared touched files.
- `uv run pyright` - failed on missing `PromoteSkillRecommendationCommand` in concurrent MCP promote tests.
- `uv run ruff check src/universal_memory/application/skills/sync_skills.py tests/application/skills/test_sync_skills.py tests/interfaces/cli/test_skills_sync.py` - passed.
- `uv run ruff format --check src/universal_memory/application/skills/sync_skills.py tests/application/skills/test_sync_skills.py tests/interfaces/cli/test_skills_sync.py` - passed.
- `uv run pytest tests/application/skills/test_sync_skills.py tests/interfaces/cli/test_skills_sync.py tests/interfaces/mcp/test_skills.py::test_sync_skills_tool_uses_mcp_origin_and_success_envelope tests/interfaces/test_parity.py::test_public_cli_capabilities_have_matching_mcp_tools` - passed, 9 tests.
- Post-review fix validation: `uv run pytest tests/application/skills/test_sync_skills.py tests/interfaces/cli/test_skills_sync.py tests/interfaces/mcp/test_skills.py::test_sync_skills_tool_uses_mcp_origin_and_success_envelope tests/interfaces/test_parity.py::test_public_cli_capabilities_have_matching_mcp_tools tests/interfaces/test_parity.py::test_cli_and_mcp_json_data_keys_match_for_public_capabilities` - passed, 32 tests.
- Post-review fix validation: `uv run pytest` - passed, 562 tests.
- Post-review fix validation: `uv run ruff check .` - passed.
- Post-review fix validation: `uv run ruff format --check .` - passed, 166 files already formatted.
- Post-review fix validation: `uv run pyright` - passed, 0 errors.

### Completion Notes List

- Added canonical `SyncSkillsUseCase` that resolves active canonical `AgentSkill` records by all/ID/exact name, validates canonical `SKILL.md` with the existing parser before writes, and delegates native materialization to `NativeSkillSync.sync`.
- Added CLI `umem skills sync [skill-id-or-name]` with repeatable `--target` and `--drift-decision keep|overwrite`; JSON/non-interactive default remains `keep`.
- Added MCP `sync_skills(skill_id_or_name=None, targets=None, drift_decision="keep")` using the same use case and semantic payload as CLI JSON.
- Minimally extended native sync installation metadata with target `status`, `drift_detected`, `audit_reference`, and `snapshot_reference` fields for sync reporting.
- Did not implement recommend, promote, import, latent recommendation, or orphan adoption in this story; existing concurrent changes in those areas were preserved.
- Post-review fix: unmanaged native targets are reported but not persisted as managed sync baselines; even explicit sync overwrite preserves them.
- Post-review fix: target-filtered sync merges managed results into existing `native_installations` so omitted runtime installs are preserved.
- Post-review fix: human CLI sync now runs safe keep first and prompts for overwrite only when actual managed drift is detected; unmanaged targets do not trigger overwrite prompting.
- Post-review validation is fully passing.
- Kestrel re-review found no open issues; final coordinator validation passed with `uv run pytest` 569 passed, `uv run ruff check .` passed, `uv run ruff format --check .` passed, and `uv run pyright` passed.

### File List

- `src/universal_memory/application/skills/sync_skills.py`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/application/skills/native_skill_sync.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/skills/test_sync_skills.py`
- `tests/interfaces/cli/test_skills_sync.py`
- `tests/interfaces/mcp/test_skills.py`
- `tests/interfaces/test_parity.py`
- `_bmad-output/implementation-artifacts/6-11-agent-skills-sync-canonical-to-native-targets.md`
