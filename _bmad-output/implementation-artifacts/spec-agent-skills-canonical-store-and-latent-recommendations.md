---
title: "Agent Skills canonical store, host sync, and latent recommendations"
type: "feature-evolution"
created: "2026-06-09"
status: "draft"
context:
  - "docs/reference/skill-lifecycle.md"
  - "_bmad-output/implementation-artifacts/6-1-register-latent-skills-by-recurrence.md"
  - "_bmad-output/implementation-artifacts/6-3-generate-canonical-skill-and-install-in-native-targets.md"
  - "_bmad-output/implementation-artifacts/6-4-register-and-list-skills.md"
  - "_bmad-output/implementation-artifacts/6-6-expose-skills-management-via-cli-and-mcp.md"
---

# Agent Skills Canonical Store, Host Sync, and Latent Recommendations

## Problem

Universal Memory currently models skills primarily as `LatentSkill` records. The physical Agent Skill folder under `.umem/skills/` is generated only after a latent candidate is approved, and `umem skills list` lists repository records rather than a first-class canonical Agent Skills registry.

This creates three product problems:

1. Users and MCP clients cannot directly create a decided Agent Skill without going through `track -> propose -> generate`.
2. Native host directories can contain skill folders that are invisible to `umem skills list` when they were not created from a latent skill record.
3. Latent skills do not currently recommend themselves automatically; the system only records them when a CLI/MCP caller explicitly invokes `skills track`.
4. Agents are not currently instructed strongly enough to observe repeated workflows and call the latent skill APIs, so the feature remains invisible in normal use.

The result is a confusing lifecycle: `.umem/skills/` is described as the source of truth, but the actual list/detail/update APIs are anchored to latent skill records, and direct Agent Skills workflows are not first-class.

## Current Behavior Evidence

- `TrackLatentSkillUseCase` creates or increments proposed latent skills only when called explicitly. It does not scan memory facts, audit events, prompts, or usage history.
- `MATCH_THRESHOLD = 0.72` and token-overlap matching only decide whether a new `skills track` call increments an existing candidate.
- `ProposeSkillUseCase` only reviews or approves an existing latent skill ID.
- `GenerateSkillUseCase` writes `.umem/skills/<slug>/SKILL.md` and synchronizes native targets only after the latent skill is already active.
- `ListSkillsUseCase` reads `LatentSkillRepository.list()` and then resolves physical paths, so orphan native skills or canonical folders without matching latent records are invisible.

Conclusion: latent skills are a passive capture mechanism today. They do not yet constitute an automatic recommendation engine.

## Product Gap: Agent Behavior

Universal Memory does not contain an LLM. It is a CLI/MCP memory and skill substrate. Therefore, any pattern recognition that depends on semantic judgment must be performed by the consuming agent, not by UMEM itself.

Today, the agent-facing instructions tell agents to load UMEM context and list skills, but they do not create a strong operating loop for skill discovery. As a result, agents may use memory but never call `track_latent_skill`, even when they repeatedly execute the same workflow.

The latent skill feature should be treated as incomplete until host instructions and the `use-universal-memory` guide skill teach agents when and how to use it.

Required agent behavior:

1. Observe repeated workflows, not just repeated facts.
2. Decide whether the repeated behavior is durable enough to become a candidate skill.
3. Call `track_latent_skill` only with curated summaries, not raw transcripts.
4. Re-check candidates during substantial work completion.
5. Recommend promotion only when evidence crosses configured thresholds.
6. Prefer direct `create_skill` when the user explicitly asks to create a skill.
7. Avoid creating or tracking skills for one-off tasks, secrets, raw logs, or uncertain patterns.

## Target Model

Universal Memory should support two distinct but connected workflows.

### Workflow A: Explicit Agent Skill Creation

Use this when a user or MCP client already knows the desired skill.

1. Create or update a canonical Agent Skill under `.umem/skills/<slug>/`.
2. Validate the canonical `SKILL.md` against Agent Skills requirements.
3. Register the skill in a first-class UMEM skill registry.
4. Synchronize the canonical folder into enabled native host targets.
5. Validate each native target after writing.
6. Return canonical path, target status, audit references, snapshots, and warnings.

This is the primary MCP-friendly workflow.

### Workflow B: Latent Recommendation and Promotion

Use this when repeated behavior suggests a reusable skill but no one has explicitly created it.

1. Observe recurring evidence from curated sources.
2. Cluster evidence into candidate recommendations.
3. Surface recommendations only when confidence and recurrence thresholds are met.
4. User or MCP client accepts, edits, defers, or rejects the recommendation.
5. Accepted recommendations become explicit Agent Skills via Workflow A.

This workflow is useful, but it must not be the only way to create skills.

## Core Product Decisions

1. `.umem/skills/<slug>/` is the canonical source of truth for Agent Skill content created or managed by UMEM.
2. Native host directories are materialized targets, not authoritative sources.
3. `umem skills list` lists canonical skills and recommendation candidates, not just latent skill records.
4. MCP gets direct skill creation and sync tools; it does not need to manufacture latent skill proposals for explicit user intent.
5. Latent skills become a recommendation subsystem with explicit evidence sources, thresholds, and user decisions.
6. Existing `track -> propose -> generate` remains as compatibility, but is reframed as recommendation/promotion, not the main creation path.
7. Agent instructions are part of the feature contract. Without updated host instructions and `use-universal-memory` guidance, latent recommendations are not product-complete.

## Requirements

### FR1: Canonical Agent Skill Registry

The system shall persist a canonical skill registry independent from latent recommendation records.

Each canonical skill record must include:

- `id`
- `name`
- `slug`
- `description`
- `scope`
- `status`: `active`, `disabled`, or `draft`
- `canonical_path`
- `created_at`
- `updated_at`
- `origin`
- `audit_reference`
- `content_hash`
- `native_installations[]`
- optional `source_recommendation_id`

Storage may be introduced as `.umem/memory/skills.jsonl` or an equivalent versioned store. Do not overload `latent_skills.jsonl` for canonical Agent Skills.

### FR2: Direct Skill Creation

Add a direct creation use case and expose it via CLI and MCP.

CLI:

```bash
umem skills create \
  --name "Launch Funnel Operator" \
  --description "Operate launch funnel scheduling, CTAs, UTMs, metrics, and readiness gates." \
  --trigger "when creating launch schedules" \
  --trigger "when reviewing UTM links" \
  --scope project
```

MCP:

```text
create_skill(name, description, scope="project", triggers=[], raw_markdown=None, targets=None)
```

Behavior:

- If `raw_markdown` is absent, render a valid Agent Skills `SKILL.md` from provided fields.
- If `raw_markdown` is present, validate it and extract metadata.
- Write canonical content to `.umem/skills/<slug>/SKILL.md`.
- Register the canonical skill.
- Sync native targets for enabled runtimes unless `targets=[]` explicitly disables installation.
- Return target-by-target status.

### FR3: Agent Skills Format Validation

Before writing or syncing, validate `SKILL.md` as Agent Skills compatible.

Required validation:

- File starts with YAML frontmatter delimited by `---`.
- YAML parses with a real YAML parser or a strict equivalent.
- `name` exists and is a non-empty string.
- `description` exists and is a non-empty string.
- Optional `triggers` is a list of non-empty strings.
- Rendered frontmatter safely quotes or escapes scalars containing `:`, quotes, newlines, brackets, or other YAML-sensitive characters.
- No absolute project paths are emitted into canonical or native skill files unless explicitly allowed by future policy.
- Secret scanning runs before persistence.

Validation errors must fail before any native target is written.

### FR4: Native Host Sync

Canonical skills shall sync to runtime-native targets declared by the runtime registry.

Current expected target behavior:

- Claude Code: `.claude/skills/<slug>/SKILL.md`
- OpenCode: `.opencode/skills/<slug>/SKILL.md`
- Cursor: `.cursor/rules/<slug>/SKILL.mdc`
- Antigravity: `.antigravity/rules/<slug>/SKILL.md`
- Codex/OpenAI-class: no native Agent Skills target unless a supported target is added; keep AGENTS.md guidance only.

Open question: determine whether `.agents/skills/<slug>/SKILL.md` should be added as a shared Agent Skills target for hosts that follow the broader `agentskills.io` convention. If added, it must be represented in the runtime registry, not created ad hoc.

### FR5: Skill List and Detail Must Reflect Canonical and Native State

`umem skills list --format json` should return canonical skills plus recommendation candidates.

Proposed shape:

```json
{
  "skills": [
    {
      "id": "skill-id",
      "name": "Launch Funnel Operator",
      "scope": "project",
      "status": "active",
      "canonical_path": ".umem/skills/launch-funnel-operator/SKILL.md",
      "created_at": "2026-06-09T00:00:00Z",
      "updated_at": "2026-06-09T00:00:00Z",
      "origin": "mcp",
      "audit_reference": "audit-id",
      "targets": [
        {
          "runtime": "opencode",
          "path": ".opencode/skills/launch-funnel-operator/SKILL.md",
          "status": "synced",
          "drift_detected": false
        }
      ]
    }
  ],
  "recommendations": []
}
```

`umem skills detail <id-or-name>` should return canonical metadata, frontmatter metadata, target status, drift warnings, and recommendation provenance if applicable.

### FR6: Skill Sync and Repair

Add an explicit sync command/API.

CLI:

```bash
umem skills sync
umem skills sync <skill-id-or-name>
umem skills sync --target opencode --target claude_code
```

MCP:

```text
sync_skills(skill_id_or_name=None, targets=None, drift_decision="keep")
```

Behavior:

- Read canonical skills.
- Install missing targets for enabled runtimes.
- Detect drift using previous target hash.
- Keep by default in non-interactive mode.
- Overwrite only when explicitly requested.
- Snapshot before overwrite.
- Report target-level results.

### FR7: Latent Recommendation Engine

Replace the expectation that latent skills recommend themselves with a real recommendation use case.

Add:

```bash
umem skills recommend
umem skills recommend --format json
```

MCP:

```text
recommend_skills(scope="project", min_recurrence=None, dry_run=True)
```

Recommendation sources, in priority order:

1. Existing `latent_skills.jsonl` records created by `skills track`.
2. Curated memory facts tagged with workflow/process/task patterns.
3. Audit events for repeated UMEM operations, excluding sensitive content.
4. Future explicit host feedback events, if added.

Initial implementation may use only source 1, but must state that limitation in the output.

Minimum recommendation policy:

- Do not recommend candidates with `recurrence_count < 2` by default.
- Do not recommend candidates without at least two evidence entries or one explicit user/MCP-created candidate.
- Do not auto-create canonical skills.
- Return clear reasons: recurrence count, evidence summaries, tags, and confidence.

### FR8: Latent Track Must Be Honest About Its Role

Update CLI/MCP help and docs so `skills track` is described as manual evidence capture, not automatic discovery.

Current behavior should be documented as:

- `skills track` records that a user/agent observed a recurring workflow.
- Similar future `track` calls increment recurrence.
- It does not inspect prior facts automatically.
- Use `skills recommend` to review candidates.
- Use `skills create` when the user already knows the desired skill.

### FR9: Promotion From Recommendation

Add a promotion path that turns a recommendation into a canonical skill using the same create use case.

CLI:

```bash
umem skills promote <recommendation-id>
umem skills promote <recommendation-id> --name "..." --description "..." --trigger "..."
```

MCP:

```text
promote_skill_recommendation(recommendation_id, edits=None, targets=None)
```

Compatibility:

- Existing `skills propose <latent_skill_id> --decision yes` may continue to mark the latent skill active.
- Existing `skills generate <latent_skill_id>` may delegate internally to the new canonical create/promote use case.
- New users should be guided toward `recommend -> promote` or direct `create`.

### FR10: Agent Instruction Loop for Latent Skills

Update `.umem/skills/use-universal-memory/SKILL.md` and its references so agents know when to call skill lifecycle tools.

The guide skill must include a concise decision loop:

1. At startup, load context and list skills as it does today.
2. During work, if the same methodology, review pattern, checklist, transformation, or domain workflow appears repeatedly, consider whether it should be tracked.
3. Before final response on substantial work, ask internally whether a durable workflow pattern was observed.
4. If yes, call `track_latent_skill` with a short name, description, tags, and sanitized evidence summary.
5. If existing candidates are ready for promotion, surface them to the user with clear reasons.
6. If the user explicitly requests a skill, use direct `create_skill`, not `track_latent_skill`.

The instructions must also define negative criteria:

- Do not track a skill for a single one-off request.
- Do not track secrets, raw logs, raw prompts, or private customer data.
- Do not track vague preferences that belong as memory facts.
- Do not auto-promote without user approval.
- Do not call `track_latent_skill` on every session.

### FR11: Host Instruction Integration

Host sync output must include compact skill-discovery guidance in host instruction files without turning them into memory dumps.

Required behavior:

- `AGENTS.md` and `CLAUDE.md` continue pointing to UMEM and the guide skill.
- The managed block includes a short reminder that agents should consider latent skill tracking for repeated workflows.
- Detailed procedures live in `.umem/skills/use-universal-memory/references/skills-lifecycle.md`.
- Host instructions must not include large lists of candidates or raw memory.

### FR12: Agent-Facing Candidate Surfacing

Provide a low-friction way for agents to discover actionable candidates without manually composing several commands.

Options:

- `umem skills recommend --format json`
- `recommend_skills()` MCP tool
- Include `recommendations[]` in `skills list` payload when candidates are actionable

The output must explain:

- why the candidate is recommended;
- recurrence count;
- evidence summaries;
- confidence;
- safe next command or MCP action;
- whether the current implementation used only explicit `skills track` evidence or additional sources.

## Non-Goals

- Do not build an LLM-based autonomous skill authoring system in this iteration.
- Do not ingest raw prompts or full chat transcripts into memory to detect latent skills.
- Do not make native host directories authoritative.
- Do not auto-overwrite host skill files with drift in non-interactive mode.
- Do not require latent recommendation flow for explicit user-created skills.

## Migration Plan

### Phase 1: Canonical Registry and Direct Create

- Add canonical skill entity, repository, and safe storage.
- Add Agent Skills validation utility.
- Add `skills create` CLI and `create_skill` MCP.
- Make create write `.umem/skills` and sync native targets.
- Add list/detail support for canonical records.

### Phase 1.5: Agent Instruction Loop

- Update the `use-universal-memory` guide skill with latent skill observation rules.
- Update `references/skills-lifecycle.md` with positive/negative criteria and examples.
- Update host sync managed instructions with a compact pointer to the latent skill loop.
- Add tests or snapshots proving host files stay compact.

### Phase 2: Sync, Repair, and Orphan Detection

- Add `skills sync` CLI and MCP.
- Add target validation and drift reporting.
- Detect orphan native skills under configured target directories.
- Report orphan skills as `unmanaged_native` in diagnostics, with an import option.

### Phase 3: Import Existing Native Skills

- Add `skills import <path>` for native skills created outside UMEM.
- Validate imported `SKILL.md`.
- Copy into `.umem/skills/<slug>`.
- Register canonical record.
- Optionally replace native folder with managed synchronized copy.

### Phase 4: Latent Recommendations

- Add `skills recommend` over existing latent records.
- Update `skills track` docs and help copy.
- Add `skills promote` as create-from-recommendation.
- Keep old `propose/generate` commands as compatibility aliases or advanced flows.

### Phase 5: Evidence Expansion

- Add optional recommendation sources from curated facts and audit metadata.
- Add configurable thresholds under `.umem/config.toml`.
- Add user-visible reasons and suppression decisions.

## Acceptance Criteria

1. Given a direct MCP `create_skill` call with a description containing `:`, when the skill is created, then `.umem/skills/<slug>/SKILL.md` and native target files contain valid YAML frontmatter.
2. Given a skill created via UMEM, when `umem skills list --format json` runs, then it returns the canonical skill and target status without relying on `latent_skills.jsonl`.
3. Given an enabled OpenCode runtime, when a canonical skill is created, then the corresponding `.opencode/skills/<slug>/SKILL.md` target is written and validated.
4. Given a native target manually changed after sync, when `umem skills sync --format json` runs, then drift is reported and not overwritten by default.
5. Given a valid native skill folder not registered in UMEM, when diagnostics or sync inventory runs, then it is reported as unmanaged rather than silently ignored.
6. Given no repeated latent evidence, when `umem skills recommend` runs, then it returns an honest empty state explaining the current evidence sources and thresholds.
7. Given a latent skill with recurrence count 2 and evidence, when `umem skills recommend` runs, then it returns a recommendation with reasons and a promotion command.
8. Given a recommendation is promoted, when the operation completes, then the resulting canonical skill uses the same validation and native sync path as direct creation.
9. Given existing `track -> propose -> generate` usage, when the commands are called, then they continue to work or return migration guidance without data loss.
10. Given an agent reads `use-universal-memory`, when it completes substantial repeated workflow work, then the instructions clearly tell it when to call `track_latent_skill` and when not to.
11. Given a user explicitly asks to create a skill, when the agent follows UMEM guidance, then it uses direct `create_skill` instead of creating a latent candidate first.
12. Given no durable repeated workflow was observed, when the agent follows UMEM guidance, then it does not call `track_latent_skill` just to satisfy a checklist.

## Implementation Notes

- Prefer a real YAML parser for validation and serialization if dependency policy allows it. If not, keep a strict internal serializer/parser but cover YAML-sensitive scalars with tests.
- Avoid duplicating validation in CLI/MCP adapters; validation belongs in application/domain services.
- Keep all paths relative in payloads.
- Add parity tests for every new CLI JSON command and MCP tool.
- Add regression tests for colon-containing descriptions in canonical and native target files.
- Add regression tests for orphan native skill inventory using `.agents/skills` if that target is adopted.

## Open Questions

1. Should `.agents/skills` be a first-class shared Agent Skills target in the default runtime registry?
2. Should canonical global skills live under a global UMEM root and materialize into project host targets on demand, or should global skills only be referenced until explicitly installed per project?
3. Should `skills propose/generate` remain public long-term, or become compatibility aliases for `recommend/promote`?
4. Should recommendations use only explicit `skills track` evidence for now, or also scan curated facts tagged with workflow-like tags in the first implementation?

## Recommended First Story

Implement Phase 1 only: canonical skill registry, Agent Skills validation, direct `skills create` CLI/MCP, and list/detail support for canonical records. This unlocks the main user and MCP workflow without depending on the harder latent recommendation problem.

## Recommended Parallel Story

Implement Phase 1.5 in parallel with Phase 1: update agent-facing UMEM guidance so agents start using latent tracking deliberately. This is required because UMEM has no built-in IA; without agent behavior changes, latent skills remain a passive API even after the backend is improved.
