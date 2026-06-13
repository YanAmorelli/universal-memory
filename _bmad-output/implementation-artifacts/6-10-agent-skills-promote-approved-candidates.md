# Story 6.10: Agent Skills Promote Approved Candidates

Status: done

## Story

As a user or MCP-consuming agent,
I want to explicitly approve and promote an existing latent skill candidate into a canonical Agent Skill,
so that recurring workflow evidence can become a managed skill only after deliberate user approval.

## Acceptance Criteria

1. **Given** an existing latent skill candidate in `proposed` status, **When** `umem skills promote <latent-skill-id> --yes --format json` runs, **Then** the command creates a canonical Agent Skill using the same validation, registry, canonical path, native target handling, audit, and snapshot behavior as direct `skills create`, **And** records the latent candidate as the source recommendation.

2. **Given** an MCP client calls `promote_skill_recommendation(recommendation_id, edits=None, targets=None)`, **When** the referenced latent candidate is eligible and approved by that caller action, **Then** MCP delegates to the same application use case as CLI promotion and returns the same semantic payload as CLI JSON.

3. **Given** promotion includes optional edits for `name`, `description`, or `triggers`, **When** the promotion executes, **Then** the canonical skill uses the edited values, validates them with the existing Agent Skills validation rules, and still preserves source recommendation provenance.

4. **Given** promotion includes `targets=[]`, **When** the operation executes through MCP, **Then** canonical creation and registry persistence still occur, **And** native target installation is skipped consistently with direct `create_skill` behavior.

5. **Given** the latent candidate is missing, ignored, already promoted, or otherwise not in an eligible state, **When** CLI or MCP promotion is requested, **Then** no canonical skill files or registry records are written, **And** the caller receives a mapped validation error that follows existing CLI/MCP error policies.

6. **Given** canonical creation succeeds but latent-candidate status/provenance update fails, **When** promotion handles the failure, **Then** the operation avoids leaving an untraceable promotion by either rolling back the just-created canonical artifacts or returning a clear failure without marking the latent candidate promoted.

7. **Given** promotion succeeds, **When** `umem skills list --format json` or `umem skills detail <id-or-name> --format json` runs, **Then** the canonical skill appears with recommendation provenance such as `source_recommendation_id`, **And** the original latent candidate is no longer presented as an actionable unpromoted candidate.

8. **Given** existing `skills propose` and `skills generate` compatibility flows are still present, **When** this story is implemented, **Then** those flows continue to work or delegate without data loss, **And** new promotion functionality does not require implementing `skills recommend`, host sync/repair, native import, or evidence-source expansion.

## Tasks / Subtasks

- [x] **Task 1: Inspect current latent and canonical skill promotion-adjacent code** (AC: 1, 5, 8)
  - [x] Review `ProposeSkillUseCase`, `GenerateSkillUseCase`, `CreateSkillUseCase`, `ListSkillsUseCase`, and detail use cases before editing.
  - [x] Identify the smallest implementation path that reuses direct canonical `CreateSkillUseCase` rather than duplicating Agent Skills rendering or native sync logic.
  - [x] Confirm current latent statuses and decide the exact post-promotion status/metadata representation without changing unrelated lifecycle semantics.

- [x] **Task 2: Add application use case for explicit promotion** (AC: 1, 3, 4, 5, 6)
  - [x] Create `PromoteSkillRecommendationCommand`, `PromoteSkillRecommendationResult`, and `PromoteSkillRecommendationUseCase` under `src/universal_memory/application/skills/`.
  - [x] Read the latent candidate by ID and reject missing or ineligible candidates before any write.
  - [x] Build a `CreateSkillCommand` from latent candidate fields plus optional approved edits.
  - [x] Pass MCP `targets` through to `CreateSkillUseCase`; CLI may use the default direct-create target behavior unless CLI target flags already exist.
  - [x] Persist provenance on the canonical skill, including at minimum `source_recommendation_id` and a promotion metadata marker.
  - [x] Update the latent candidate after successful canonical creation so it is not actionable as an unpromoted recommendation.
  - [x] Handle failure ordering explicitly so canonical artifacts are not left without promotion provenance or an updated latent source record.

- [x] **Task 3: Expose promotion through CLI** (AC: 1, 3, 5, 7, 8)
  - [x] Add `umem skills promote <latent-skill-id>` to the existing skills CLI group.
  - [x] Require explicit approval in non-interactive and JSON modes via `--yes` or equivalent existing confirmation style.
  - [x] Support optional approved edits for `--name`, `--description`, and repeated `--trigger` flags.
  - [x] Return a JSON success envelope whose payload is semantically aligned with `skills create`, plus promotion provenance fields.
  - [x] Add concise human output that shows canonical path, affected paths, audit/snapshot references, and source recommendation ID.

- [x] **Task 4: Expose promotion through MCP and parity inventory** (AC: 2, 3, 4, 5)
  - [x] Add `promote_skill_recommendation(recommendation_id, edits=None, targets=None)` to `src/universal_memory/interfaces/mcp/server.py`.
  - [x] Wire the use case in `src/universal_memory/bootstrap/mcp.py` and CLI bootstrap as needed.
  - [x] Ensure MCP error mapping follows the existing JSON-RPC/domain error policy.
  - [x] Update CLI/MCP parity tests and MCP compliance inventory for the new promotion tool.

- [x] **Task 5: Update list/detail provenance behavior only as needed** (AC: 7)
  - [x] Ensure canonical skill records created through promotion expose `source_recommendation_id` in list/detail payloads.
  - [x] Ensure promoted latent candidates are not surfaced as actionable unpromoted recommendations.
  - [x] Avoid implementing recommendation discovery, recommendation ranking, host sync/repair commands, orphan detection, or native import.

- [x] **Task 6: Add focused tests and regression coverage** (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [x] Add application tests for successful promotion, edited promotion, ineligible latent candidate rejection, MCP `targets=[]`, and failure/rollback ordering.
  - [x] Add CLI tests for `umem skills promote`, JSON output, approval requirement, optional edits, and mapped errors.
  - [x] Add MCP tests for `promote_skill_recommendation`, edits, `targets=[]`, and error mapping.
  - [x] Add list/detail regression tests for `source_recommendation_id` and non-actionable promoted candidates.
  - [x] Add parity/compliance tests for the new CLI/MCP surface.

- [x] **Task 7: Validate and update story record** (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [x] Run focused tests for promotion, create/list/detail, CLI, MCP, and parity slices.
  - [x] Run `uv run ruff check .`.
  - [x] Run `uv run ruff format --check .`.
  - [x] Run `uv run pyright`.
  - [x] Run `uv run pytest` if feasible before moving to review.
  - [x] Update this story's Dev Agent Record with touched files, validation commands, completion notes, and review status.

## Dev Notes

- **Spec source:** `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`, especially FR9 and acceptance criteria 8-9. This story is the promotion slice of Phase 4 only.

- **Strict scope:** Implement explicit approval/promotion of an already-existing latent candidate into a canonical Agent Skill. Do not implement `umem skills recommend`, recommendation discovery, evidence expansion, threshold/ranking logic, host sync/repair, orphan detection, or native import in this story.

- **Approval model:** Promotion is an explicit user/MCP decision. Do not auto-promote based on recurrence count, confidence, or latent status alone.

- **Reuse direct create:** Promotion must reuse `CreateSkillUseCase` or its application-level semantics for canonical content, validation, registry persistence, native target handling, audit, snapshots, and cleanup. Do not fork a second markdown renderer or native sync path.

- **Compatibility guardrail:** Existing `skills propose` and `skills generate` remain compatibility flows. This story may add delegation or shared internals only if it is the smallest safe path and does not break existing tests or data.

- **Provenance requirement:** Canonical skills created from latent candidates must record `source_recommendation_id` or equivalent stable provenance on the canonical record/payload so users can trace the promotion back to the approved candidate.

- **State transition caution:** Current latent candidates use statuses such as `proposed`, `active`, and `ignored`. If no dedicated `promoted` status exists, prefer minimal metadata/provenance that prevents duplicate actionable surfacing without a broad status model migration.

- **Path and safety constraints:** Keep paths relative in payloads. Continue using safe write, audit, snapshot, and secret scanning paths. Do not write directly from CLI/MCP adapters.

- **Native target constraint:** Promotion may use direct-create native target behavior and MCP `targets` filtering. Do not add a separate `skills sync` or repair command in this story.

## References

- `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`
- `_bmad-output/implementation-artifacts/6-7-agent-skills-canonical-registry-and-direct-create.md`
- `_bmad-output/implementation-artifacts/6-8-agent-instruction-loop-for-latent-skills.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/devex-interaction-spec.md`
- `src/universal_memory/application/skills/create_skill.py`
- `src/universal_memory/application/skills/propose_skill.py`
- `src/universal_memory/application/skills/generate_skill.py`
- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/skills/`
- `tests/interfaces/cli/`
- `tests/interfaces/mcp/`
- `tests/interfaces/test_parity.py`

## Dev Agent Record

### Agent Model Used

openai/gpt-5.5

### Debug Log References

- `uv run pytest tests/application/skills/test_promote_skill.py tests/application/skills/test_list_skills.py tests/interfaces/cli/test_skills_promote.py tests/interfaces/mcp/test_skills.py tests/interfaces/mcp/test_compliance.py tests/interfaces/test_parity.py -q` -> 67 passed.
- `uv run ruff check .` -> passed.
- `uv run ruff format --check .` -> failed only on pre-existing out-of-scope `src/universal_memory/application/skills/native_skill_sync.py` formatting.
- `uv run pyright` -> passed, 0 errors.
- `uv run pytest` -> 559 passed.
- Review fix validation: `uv run pytest tests/application/skills/test_promote_skill.py tests/interfaces/mcp/test_skills.py tests/interfaces/cli/test_skills_promote.py -q` -> 32 passed.
- Review fix validation: `uv run ruff check .` -> passed.
- Review fix validation: `uv run ruff format --check .` -> passed, 166 files already formatted.
- Review fix validation: `uv run pyright` -> passed, 0 errors.
- Review fix validation: `uv run pytest` -> 564 passed.

### Completion Notes List

- Implemented explicit promotion of existing proposed latent candidates into canonical Agent Skills through a new application use case that delegates canonical creation to `CreateSkillUseCase`.
- Added CLI `umem skills promote <latent-skill-id>` with `--yes` approval enforcement for JSON/non-TTY modes and optional `--name`, `--description`, and repeated `--trigger` edits.
- Added MCP `promote_skill_recommendation(recommendation_id, edits=None, targets=None)` with shared use-case delegation and `targets=[]` passthrough.
- Persisted and exposed `source_recommendation_id` provenance on canonical skill records and payloads, and hid promoted latent recommendations from actionable recommendation output.
- Preserved scope boundaries: no new recommendation discovery/ranking, host sync/repair, orphan detection, or native import behavior was implemented.
- Final validation is green: full pytest, ruff check, ruff format check, and pyright pass after adjacent sync/native formatting fixes landed.
- Fixed Sable review blocker: MCP promotion no longer requires project initialization before reading the recommendation. MCP now passes initialization state to the promotion use case, which rejects uninitialized project-scoped promotion after reading scope while allowing global latent recommendations without project init.
- Added regression coverage for global MCP promotion without project initialization and project-scoped promotion rejection when `project_initialized=False`.
- Sable re-review found no open scoped issues; final coordinator validation passed with `uv run pytest` 569 passed, `uv run ruff check .` passed, `uv run ruff format --check .` passed, and `uv run pyright` passed.

### File List

- `_bmad-output/implementation-artifacts/6-10-agent-skills-promote-approved-candidates.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/application/skills/create_skill.py`
- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/application/skills/promote_skill.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/skills/test_list_skills.py`
- `tests/application/skills/test_promote_skill.py`
- `tests/interfaces/cli/test_skills_promote.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_skills.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-06-12: Created BMAD story for explicit promotion of approved latent candidates into canonical Agent Skills.
- 2026-06-12: Implemented explicit CLI/MCP promotion of approved latent candidates into canonical Agent Skills with provenance and tests.
- 2026-06-12: Addressed review blocker for global MCP promotion from uninitialized project contexts.
- 2026-06-13: Sable re-review found no open issues; moved story to done after final validation passed.
