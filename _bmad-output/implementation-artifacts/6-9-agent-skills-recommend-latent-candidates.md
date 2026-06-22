# Story 6.9: Agent Skills Recommend Latent Candidates

Status: done

## Story

As a user or MCP-consuming agent,
I want to list actionable latent skill recommendations with clear reasons,
so that I can decide whether recurring workflow evidence is worth promoting without UMEM creating or syncing skills automatically.

## Acceptance Criteria

1. **Given** no latent skill candidates meet the recommendation threshold, **When** `umem skills recommend --format json` runs, **Then** it returns an empty `recommendations` list, the default threshold policy, the evidence sources used, and an honest limitation that the first implementation only evaluates explicit `skills track` latent records.

2. **Given** a proposed project latent skill has `recurrence_count >= 2` and at least two evidence summaries, **When** `umem skills recommend --format json` runs, **Then** it returns that candidate with `id`, `name`, `description`, `scope`, `status`, `recurrence_count`, `evidence_summaries`, `tags`, `confidence`, `reasons`, and a safe next action such as `umem skills promote <id>`.

3. **Given** a proposed latent skill has `recurrence_count < 2` by default, **When** recommendations are requested without overriding thresholds, **Then** the candidate is excluded and the response explains the minimum recurrence threshold.

4. **Given** a caller provides `--min-recurrence 1` or MCP `min_recurrence=1`, **When** a latent candidate has at least one evidence summary, **Then** the candidate can be returned with reasons that clearly show the lower threshold used.

5. **Given** a latent candidate is ignored, already active/promoted, missing evidence, or outside the requested scope, **When** recommendations are requested, **Then** it is not presented as an actionable recommendation.

6. **Given** canonical skills exist in `.umem/memory/skills.jsonl`, **When** `umem skills list --format json` runs, **Then** the payload continues to include canonical `skills` and may include actionable `recommendations`, without mixing recommendation candidates into canonical skills.

7. **Given** an MCP client calls `recommend_skills(scope="project", min_recurrence=None, dry_run=True)`, **When** recommendations are available, **Then** MCP delegates to the same application use case as CLI and returns the same semantic payload as CLI JSON.

8. **Given** recommendation commands run through CLI or MCP, **When** they complete successfully, **Then** they perform no canonical skill creation, no native target sync, no import, no promotion, and no mutation of latent records.

9. **Given** CLI help, MCP tool descriptions, or guide references mention latent recommendations, **When** they are inspected, **Then** they describe `skills track` as explicit evidence capture and `skills recommend` as read-only candidate review, reserving promotion for a separate explicit approval flow.

## Tasks / Subtasks

- [x] **Task 1: Inspect current latent recommendation-adjacent code** (AC: 1, 2, 5, 6, 8)
  - [x] Review `TrackLatentSkillUseCase`, `ProposeSkillUseCase`, `ListSkillsUseCase`, `LocalLatentSkillRepository`, CLI skills commands, MCP skills tools, and existing tests before editing.
  - [x] Confirm current latent statuses and evidence metadata shape from `TrackLatentSkillUseCase` before deriving eligibility.
  - [x] Verify canonical listing behavior introduced in story 6.7 remains separate from latent recommendations.

- [x] **Task 2: Add read-only recommendation application use case** (AC: 1, 2, 3, 4, 5, 8)
  - [x] Create `RecommendSkillsCommand`, `SkillRecommendationItem`, `RecommendSkillsResult`, and `RecommendSkillsUseCase` under `src/universal_memory/application/skills/`.
  - [x] Read latent records through `LatentSkillRepository.list()` and do not call repository write methods.
  - [x] Default `min_recurrence` to `2`; validate overrides so values below `1` fail with existing validation error policy.
  - [x] Include only actionable proposed candidates that meet recurrence, evidence, and scope requirements.
  - [x] Extract only sanitized evidence summaries already present in latent metadata; do not read prompts, raw logs, chat transcripts, audit contents, native skill files, or memory fact text in this story.
  - [x] Return `evidence_sources` with explicit source `latent_skills` and a limitation message that facts/audit/host feedback are not scanned yet.
  - [x] Compute a simple deterministic confidence/reason payload from recurrence count, evidence count, tags, status, and threshold used.

- [x] **Task 3: Expose `umem skills recommend` through CLI** (AC: 1, 2, 3, 4, 8, 9)
  - [x] Add a `recommend` command to the existing Typer `skills` group.
  - [x] Support `--scope project|global|all`, `--min-recurrence`, and `--format json` using existing output conventions.
  - [x] Return a JSON envelope aligned with existing `skills.*` operations and include thresholds, evidence sources, limitations, recommendations, and recommended next actions.
  - [x] Add concise human output for empty state and non-empty recommendations.
  - [x] Ensure command execution is read-only and does not ask for approval or invoke promotion.

- [x] **Task 4: Expose `recommend_skills` through MCP** (AC: 4, 7, 8, 9)
  - [x] Add `recommend_skills(scope="project", min_recurrence=None, dry_run=True)` to `src/universal_memory/interfaces/mcp/server.py`.
  - [x] Wire the use case in `src/universal_memory/bootstrap/mcp.py` and CLI bootstrap as needed.
  - [x] Keep `dry_run` accepted for API clarity, but reject or ignore non-read-only behavior; this story must not mutate state.
  - [x] Update MCP compliance inventory and CLI/MCP parity tests for the new read-only tool.

- [x] **Task 5: Integrate actionable recommendations into list payload only if minimal** (AC: 6)
  - [x] If `ListSkillsUseCase` already has a `recommendations` field, reuse the new recommendation logic or align its filtering so actionable candidates follow the same threshold policy.
  - [x] Preserve canonical `skills` output exactly as canonical records; do not represent recommendations as canonical skills.
  - [x] Preserve existing compatibility behavior for latent records where required by previous tests.

- [x] **Task 6: Update read-only recommendation guidance** (AC: 9)
  - [x] Update only concise CLI/MCP help text or UMEM guide references needed to document `skills recommend` as read-only candidate review.
  - [x] State that `skills track` records explicit observed evidence and does not automatically scan history.
  - [x] State that promotion/import/sync are separate workflows and not part of recommendation listing.

- [x] **Task 7: Add focused tests and validation** (AC: 1, 2, 3, 4, 5, 6, 7, 8, 9)
  - [x] Add application tests for empty state, eligible candidate, default threshold exclusion, threshold override, ignored/active exclusion, missing evidence exclusion, and read-only repository behavior.
  - [x] Add CLI tests for JSON and human `umem skills recommend`, `--scope`, `--min-recurrence`, and validation errors.
  - [x] Add MCP tests for `recommend_skills`, scope filtering, threshold override, and read-only behavior.
  - [x] Add list regression coverage if `skills list` recommendation behavior changes.
  - [x] Run focused tests for application skills, CLI, MCP, and parity slices.
  - [x] Run `uv run ruff check .`.
  - [x] Run `uv run ruff format --check .`.
  - [x] Run `uv run pyright`.
  - [x] Run `uv run pytest` if feasible before moving to review.

## Dev Notes

- **Spec source:** `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`, especially FR7, FR8, FR12, Phase 4, and acceptance criteria 6-7.

- **Strict scope:** Implement recommendation/listing of latent candidates only. Do not implement promotion, native sync/repair, orphan detection, native import, automatic evidence expansion from facts/audit events, or LLM-based skill authoring in this story.

- **Recommended implementation boundary:** Add a new application use case that reads existing latent skill records and returns a recommendation payload. Keep CLI/MCP adapters thin and delegate all eligibility/reasoning to the use case.

- **Current latent evidence shape:** `TrackLatentSkillUseCase` writes candidates with `status=proposed`, `recurrence_count`, `metadata["tags"]`, and `metadata["evidence"]` entries shaped as `{"origin": ..., "summary": ...}`. Recommendation output should use these curated summaries only.

- **Default policy:** Minimum recurrence is `2` by default and candidates should also have evidence. The spec allows the first implementation to use only explicit `latent_skills.jsonl` records, but the output must say so honestly.

- **Status eligibility:** Treat `proposed` latent candidates as actionable. Do not present `ignored` candidates or candidates that have already been approved/promoted as actionable recommendations. If a dedicated promoted status does not exist yet, use the minimal existing metadata/status checks and avoid broad status migrations.

- **List behavior caution:** `ListSkillsResult` already has `skills`, optional `recommendations`, and `recommended_action`. If changing list behavior, keep canonical skills in `skills` and recommendation candidates in `recommendations`. Do not regress story 6.7 canonical listing behavior or story 6.8 guidance tests.

- **Read-only guarantee:** `skills recommend` and `recommend_skills` must not write repositories, canonical files, native targets, config, audit records, snapshots, or host files. Tests should use a repository double or assertions that fail on write.

- **User action wording:** Recommendation output can suggest `umem skills promote <id>` as a next action, but must not implement or invoke that command in this story.

- **Architecture constraints:** Follow Clean Architecture: domain entities/ports define storage contracts, application owns recommendation logic, infrastructure stays storage-only, and CLI/MCP only adapt inputs/outputs. Keep paths relative and preserve existing CLI/MCP error mapping.

## References

- `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`
- `_bmad-output/implementation-artifacts/6-7-agent-skills-canonical-registry-and-direct-create.md`
- `_bmad-output/implementation-artifacts/6-8-agent-instruction-loop-for-latent-skills.md`
- `_bmad-output/planning-artifacts/architecture.md`
- `_bmad-output/planning-artifacts/devex-interaction-spec.md`
- `src/universal_memory/application/skills/track_latent_skill.py`
- `src/universal_memory/application/skills/propose_skill.py`
- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `tests/application/skills/`
- `tests/interfaces/cli/`
- `tests/interfaces/mcp/`
- `tests/interfaces/test_parity.py`

## Dev Agent Record

### Agent Model Used

gpt-5.5

### Debug Log References

- 2026-06-12: BMAD customization resolver and config were absent in this worktree; proceeded from explicit story and repository conventions.
- 2026-06-12: Confirmed `TrackLatentSkillUseCase` stores proposed latent records with `recurrence_count`, `metadata["tags"]`, and curated `metadata["evidence"][].summary` entries.
- 2026-06-13: Vigil re-review fixes applied: actionable list recommendations now include latent candidate `id` and `recommended_action`; empty list guidance points to explicit `umem skills track` evidence capture; evidence threshold no longer scales beyond two summaries when `min_recurrence` is higher.
- 2026-06-13: Current validation after Vigil fixes: focused recommendation/interface tests passed with 77 tests; `uv run pytest` passed with 569 tests; `uv run pyright` passed; `uv run ruff format --check .` passed; `uv run ruff check .` passed.
- 2026-06-13: Final coordinator validation passed: `uv run pytest` 569 passed, `uv run ruff check .` passed, `uv run ruff format --check .` passed, and `uv run pyright` passed; moved story to done.

### Completion Notes List

- Added read-only latent skill recommendation use case with deterministic thresholds, reasons, confidence, safe next action text, evidence source metadata, and explicit limitations.
- Added `umem skills recommend` CLI command and MCP `recommend_skills` tool that delegate to the same application use case and do not mutate latent, canonical, native, config, audit, snapshot, or host state.
- Aligned `skills list` canonical-mode recommendations with the actionable recommendation policy while keeping canonical `skills` separate.
- Updated concise UMEM guide/default-template and CLI/MCP parity guidance to describe `skills track` as explicit evidence capture and `skills recommend` as read-only review.
- Added focused application, CLI, MCP, compliance, parity, and list regression tests.
- Addressed Vigil review by exposing actionable candidate promotion IDs/actions from list payloads, replacing empty guidance with explicit `skills track` evidence capture, and adding `min_recurrence=3` coverage that remains eligible with two evidence summaries.

### File List

- `_bmad-output/implementation-artifacts/6-9-agent-skills-recommend-latent-candidates.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `.umem/skills/use-universal-memory/references/cli-mcp-parity.md`
- `.umem/skills/use-universal-memory/references/skills-lifecycle.md`
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/application/skills/recommend_skills.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/skills/test_list_skills.py`
- `tests/application/skills/test_recommend_skills.py`
- `tests/application/test_setup_project.py`
- `tests/interfaces/cli/test_skills.py`
- `tests/interfaces/cli/test_skills_list.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_skills.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-06-12: Created BMAD story for read-only latent skill recommendation/listing.
- 2026-06-12: Implemented read-only latent skill recommendation use case, CLI/MCP adapters, list integration, guidance updates, tests, and moved story to review.
- 2026-06-13: Addressed Vigil review findings for list actionability, empty guidance, and evidence threshold policy.
- 2026-06-13: Moved story to done after Vigil re-review findings were resolved and final validation passed.
