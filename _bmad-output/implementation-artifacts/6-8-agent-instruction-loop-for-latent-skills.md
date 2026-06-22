# Story 6.8: Agent Instruction Loop for Latent Skills

Status: done

## Story

As an agent using Universal Memory,
I want clear UMEM instructions for when to track latent skill opportunities and when to avoid tracking them,
so that latent recommendations become a deliberate, safe, agent-driven workflow instead of a passive API that is rarely used.

## Acceptance Criteria

1. **Given** an agent reads `.umem/skills/use-universal-memory/SKILL.md`, **When** it performs substantial work, **Then** the guide includes a concise decision loop telling the agent to consider repeated workflows before final response.

2. **Given** a repeated methodology, checklist, transformation, review pattern, or domain workflow is observed, **When** it appears durable and reusable, **Then** the guide instructs the agent to call `track_latent_skill` with a short name, description, tags, and sanitized evidence summary.

3. **Given** the user explicitly asks to create a skill, **When** the agent follows UMEM guidance, **Then** it uses direct `create_skill` instead of creating a latent candidate first.

4. **Given** no repeated durable workflow was observed, **When** the agent completes work, **Then** the instructions explicitly tell it not to call `track_latent_skill` just to satisfy a checklist.

5. **Given** a request includes secrets, raw logs, raw prompts, private customer data, uncertain patterns, or one-off preferences, **When** the agent evaluates latent tracking, **Then** the guide explicitly forbids tracking that content and routes durable preferences to memory facts instead.

6. **Given** host instruction sync updates `AGENTS.md` or `CLAUDE.md`, **When** generated managed blocks are inspected, **Then** they remain compact and point to UMEM/`use-universal-memory` guidance instead of embedding long candidate lists, raw evidence, or memory dumps.

7. **Given** UMEM skill lifecycle reference material exists, **When** agents need deeper instructions, **Then** `.umem/skills/use-universal-memory/references/skills-lifecycle.md` contains positive/negative criteria, examples, and safe CLI/MCP action guidance for `track_latent_skill`, recommendations, direct `create_skill`, and promotion approval.

8. **Given** automated tests or snapshots cover generated host instructions, **When** the host sync logic runs, **Then** compact latent skill guidance is preserved and no large latent candidate/evidence dump is emitted.

## Tasks / Subtasks

- [x] **Task 1: Inspect current UMEM guide skill and host instruction templates** (AC: 1, 6, 7)
  - [x] Read `.umem/skills/use-universal-memory/SKILL.md` and all files under `.umem/skills/use-universal-memory/references/`.
  - [x] Locate host instruction rendering/sync templates that produce `AGENTS.md` and `CLAUDE.md` managed blocks.
  - [x] Identify current tests or snapshots covering host sync compactness.

- [x] **Task 2: Update the guide skill with the concise latent-skill decision loop** (AC: 1, 2, 3, 4, 5)
  - [x] Add a short section to `.umem/skills/use-universal-memory/SKILL.md` explaining when to consider latent tracking during work and before final response.
  - [x] State that explicit user skill creation must use direct `create_skill`/`umem skills create`, not `track_latent_skill`.
  - [x] State that no durable repeated workflow means no latent skill tracking.
  - [x] Keep the guide compact; deeper procedural detail belongs in references.

- [x] **Task 3: Expand `references/skills-lifecycle.md` with operational criteria and examples** (AC: 2, 3, 4, 5, 7)
  - [x] Add positive criteria for recurring workflows: methodology, review pattern, checklist, transformation, domain process, or repeatable multi-step operating procedure.
  - [x] Add negative criteria: one-off task, vague preference, secrets, raw logs, raw prompts, private data, speculative or uncertain pattern, and checklist-only tracking.
  - [x] Add safe evidence summary examples using curated summaries and relative paths only.
  - [x] Add guidance for promotion recommendation: surface reasons and ask user approval; never auto-promote.
  - [x] Add guidance that direct skill creation is the correct path when the user already knows the desired skill.

- [x] **Task 4: Add compact host instruction pointer for latent tracking** (AC: 6)
  - [x] Update host instruction sync output so managed blocks remind agents to consider latent tracking only for repeated workflows.
  - [x] Keep `AGENTS.md` and `CLAUDE.md` compact and pointer-based.
  - [x] Do not embed current recommendations, memory facts, raw evidence, or long procedural detail in host files.

- [x] **Task 5: Add tests or snapshots for guide and host compactness** (AC: 6, 8)
  - [x] Add or update tests around host sync output to assert compact latent-skill guidance appears.
  - [x] Assert host output does not include raw latent evidence or large candidate lists.
  - [x] Add reference/guide content assertions only where stable enough to avoid brittle prose tests.

- [x] **Task 6: Validate the story** (AC: 1, 2, 3, 4, 5, 6, 7, 8)
  - [x] Run focused tests for host sync and skill guide materialization.
  - [x] Run `uv run ruff check .` and `uv run ruff format --check .` if code files changed.
  - [x] Run `uv run pytest` if feasible before moving to review.

### Review Follow-ups (AI)

- [x] [AI-Review][High] Correct direct-create CLI documentation to remove invalid `--file` usage and document the supported `--trigger` option.
- [x] [AI-Review][Medium] Correct generated host guidance so newly observed recurring workflows use `umem skills track` with sanitized evidence, reserving `umem skills propose` for existing latent candidates after approval.

## Dev Notes

- **Spec source:** `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`, Phase 1.5, FR10-FR12, and acceptance criteria 10-12.

- **Product decision:** UMEM is a CLI/MCP substrate and does not contain an LLM. Semantic judgment for repeated workflows is agent-facing behavior. Therefore this story is product-critical even though it is mostly instruction/docs/template work.

- **Instruction placement:** Keep `.umem/skills/use-universal-memory/SKILL.md` as the single guide-style skill. Do not split UMEM startup, facts, host sync, or skill lifecycle into separate skills unless the user explicitly approves that design change.

- **Host file guardrail:** `AGENTS.md` and `CLAUDE.md` must remain compact routing/policy manifests. They should point agents to UMEM and the guide skill, not contain memory dumps, raw recommendations, or detailed lifecycle procedures.

- **Memory-vs-skill distinction:** Durable preferences and project facts belong in UMEM facts. Repeatable operational procedures may become latent skill candidates. Do not track a skill for a vague preference.

- **Direct-create distinction:** When the user explicitly requests a skill, route to direct creation (`create_skill` MCP or `umem skills create`) rather than latent tracking.

- **Safety distinction:** Never persist raw prompts, raw logs, secrets, credentials, private customer data, or uncertain evidence as latent skill evidence. Use curated summaries only.

## References

- `_bmad-output/implementation-artifacts/spec-agent-skills-canonical-store-and-latent-recommendations.md`
- `_bmad-output/planning-artifacts/architecture.md` (Instruction Target Ownership, Rules and Manifest Strategy)
- `.umem/skills/use-universal-memory/SKILL.md`
- `.umem/skills/use-universal-memory/references/skills-lifecycle.md`
- `.umem/skills/use-universal-memory/references/guardrails-and-recording.md`
- `.umem/skills/use-universal-memory/references/host-instructions-sync.md`
- `AGENTS.md`
- `CLAUDE.md`

## Dev Agent Record

### Agent Model Used

openai/gpt-5.5

### Debug Log References

- `uv run pytest tests/application/test_setup_project.py tests/application/host/test_sync_instructions.py` - 19 passed.
- `uv run pytest` - 510 passed.
- `uv run ruff check .` - passed.
- `uv run ruff format --check .` - 155 files already formatted.
- `uv run pyright` - 0 errors, 0 warnings, 0 informations.
- Review fix validation: `uv run pytest tests/application/test_setup_project.py tests/application/host/test_sync_instructions.py` - 20 passed.
- Review fix validation: `uv run pytest` - 511 passed.
- Review fix validation: `uv run ruff check .` - passed.
- Review fix validation: `uv run ruff format --check .` - 155 files already formatted.
- Review fix validation: `uv run pyright` - 0 errors, 0 warnings, 0 informations.
- Sentry re-review validation: both review findings resolved; focused guide/host tests passed with 20 tests.
- Final Sentry BMAD review: no findings; `uv run pytest` passed with 511 tests, `ruff check`, `ruff format --check`, and `pyright` passed.

### Completion Notes List

- Added a compact latent-skill decision loop to the default UMEM guide, including direct-create routing, no-op guidance when no durable workflow exists, and safety exclusions for secrets/raw/private/uncertain evidence.
- Expanded `skills-lifecycle.md` with positive and negative criteria, safe evidence examples, direct `create_skill` guidance, and explicit user-approval requirements for promotion.
- Added compact host instruction guidance for `AGENTS.md`/`CLAUDE.md` managed blocks without embedding latent candidate lists, raw evidence, or memory dumps.
- Added stable guide/host compactness assertions and validated the full suite.
- Resolved Sentry review finding [High]: replaced invalid documented `umem skills create --file` usage with the supported `--trigger` option in the guide reference and default materialization template.
- Resolved Sentry review finding [Medium]: changed generated host proactive-loop guidance from proposing on new recurring patterns to tracking newly observed repeated workflows with sanitized evidence.
- Sentry verified both review findings are resolved.
- Final Sentry BMAD review found no remaining blocking or non-blocking issues.

### File List

- `.umem/skills/use-universal-memory/SKILL.md`
- `.umem/skills/use-universal-memory/references/skills-lifecycle.md`
- `_bmad-output/implementation-artifacts/6-8-agent-instruction-loop-for-latent-skills.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/host/setup_host_use_case.py`
- `src/universal_memory/application/onboarding/setup_project.py`
- `tests/application/host/test_sync_instructions.py`
- `tests/application/test_setup_project.py`

### Change Log

- 2026-06-11: Created BMAD story for Phase 1.5 agent instruction loop before further implementation.
- 2026-06-11: Implemented latent skill decision loop, lifecycle guidance, compact host pointers, and validation tests; moved story to review.
- 2026-06-11: Addressed Sentry review findings for valid direct-create CLI documentation and track-before-propose host guidance.
- 2026-06-11: Sentry verified the review findings are resolved after focused validation.
- 2026-06-12: Final Sentry BMAD review found no remaining issues; moved story to done.
