---
title: 'Agent support evolution: native support, directed CLI, and unmanaged MCP'
type: 'product-implementation-spec'
created: '2026-06-10'
revised: '2026-07-31'
status: 'final'
related_artifacts:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - '_bmad-output/planning-artifacts/epics.md'
  - '_bmad-output/planning-artifacts/devex-interaction-spec.md'
scope: 'incremental-change'
---

# Agent Support Evolution: Native, Directed CLI, And Unmanaged MCP

## Problem

Universal Memory needs broad agent reach without committing to native adapters for every host in a fast-moving market. The existing planning artifacts mix three different promises: hosts that UMEM actively maintains, agents that can follow portable instructions and call the UMEM CLI, and arbitrary hosts where a user manually connects MCP.

The product must distinguish those promises. Reading `AGENTS.md`, loading an Agent Skill, executing the CLI, and exposing MCP tools are independent capabilities. None of them alone proves that UMEM maintains or behaviorally validates a particular host.

## Decisions

- Adopt three support tiers: Tier 1 Native/Managed, Tier 2 Directed CLI, and Tier 3 Unmanaged MCP.
- Keep the UMEM CLI and its structured output as the portable integration contract.
- Treat every agent that consumes UMEM instructions through `AGENTS.md` or the official UMEM Agent Skill and can execute the UMEM CLI as eligible for at least Tier 2.
- Use the open Agent Skills format as a portable instruction package and evaluate `npx skills` as an optional distribution bridge across its maintained agent catalog.
- Do not make Node.js, `npx`, `skills.sh`, or the `skills` package a mandatory runtime dependency of UMEM.
- Do not infer Tier 1 from popularity, an external compatibility list, or Agent Skill installation alone.
- Select Tier 1 hosts through a release-time product decision based on market analysis, observed demand, strategic value, internal use, integration stability, validation feasibility, and maintenance capacity.
- Define Tier 3 as a user-forced or manually configured MCP connection in a host for which UMEM has no programmed integration or validated workflow.
- Keep `manual-context.md` or equivalent portable export as a cross-tier handoff and fallback utility, not as a support tier.
- Model support tier separately from instruction, CLI, skill, and MCP capabilities.
- Make `umem init` with no runtime flags the primary user journey: detect relevant agents, recommend the correct connection path, ask for one combined confirmation, apply setup, validate, and report outcomes.
- Keep tier names, runtime paths, `npx`, copy/symlink mechanics, and MCP details out of the default onboarding unless the user requests details or a recovery action requires them.
- Present outcomes in user language: agent found, connected, context verified, skipped, or action required.
- Treat `npx skills` as implementation plumbing. The default experience asks whether to make UMEM available to the detected agent, not whether to run an NPX command.
- Maintain one complete canonical `universal-memory` skill tree for public distribution, packaged fallback, project initialization, and native synchronization; derived package resources must remain byte-identical to that source.
- Pin a reviewed local agent-to-project-skill-path catalog to the exact `skills` package version, execute one project-scoped `npx skills add`, and validate the complete expected tree without a discovery installation or `skills ls` subprocess.
- Keep the Windsurf adapter as a frozen compatibility adapter. Do not add Windsurf-specific behavior, targets, or support promises while evolving the portable path.
- Disable anonymous `skills` telemetry for installations invoked by UMEM and disclose network/external-installer use before the single confirmation.
- Prefer project-scoped connections and require a separate explicit action for global installation.
- Add `umem connect` as the simple post-initialization command for discovering or adding another agent.
- Keep `umem doctor` as the recovery command and never require users to diagnose tiers or target directories first.
- After successful setup, users should work with agents naturally; they should not need to say "use Universal Memory" in normal tasks.

## Tier Model

| Tier | Name | Supported path | Product promise |
| --- | --- | --- | --- |
| Tier 1 | Native/Managed | Maintained host adapter, native setup/sync, host-specific instructions, optional native skills and MCP, documentation, and repeatable validation | UMEM owns and tests the integration within documented limits. |
| Tier 2 | Directed CLI | `AGENTS.md` or official UMEM Agent Skill directs a shell-capable agent to the UMEM CLI | UMEM supports the portable instruction-plus-CLI contract, but does not promise every host-specific behavior or configuration surface. |
| Tier 3 | Unmanaged MCP | User manually connects the UMEM MCP server to a host without a programmed or validated UMEM integration | MCP tools may be available, but UMEM does not guarantee instruction loading, tool invocation, context use, or durable-memory behavior. |

Hosts without a usable CLI, a usable MCP channel, or a supported instruction surface are outside the support matrix. Portable context export and copy/paste prompts may still help those workflows, but they are fallback utilities rather than a claimed support tier.

## Product Experience Principles

The integration experience follows a simple-outside, rigorous-inside standard:

- one obvious primary path;
- detection instead of configuration questions;
- safe, project-scoped defaults;
- one confirmation for the recommended connection plan;
- progressive disclosure for tiers, commands, paths, and installer mechanics;
- clear results instead of infrastructure terminology;
- graceful degradation when optional dependencies are unavailable;
- reversible managed mutations and honest boundaries for external mutations;
- quiet operation when healthy and actionable guidance only when needed.

Tier classification is a product and diagnostic concern. It must not become a required choice in the normal onboarding UI.

## Golden Path

Persistent installation and initialization should require only:

```bash
uv tool install universal-memory
umem init
```

The default interactive flow is:

```text
Universal Memory

Found in this workspace:
  Codex
  Cursor

Connect Universal Memory to both? [Y/n]

✓ Project memory initialized
✓ Codex connected natively
✓ Cursor connected through portable instructions
✓ Context access verified

You're ready. Work with your agents normally.
```

Rules for this flow:

- automatically detect agents and existing instruction/skill surfaces before prompting;
- recommend all safely detected project agents by default;
- combine compatible project-scoped actions into one confirmation;
- do not display tier numbers in the default success path;
- do not ask users to choose target directories, MCP modes, or copy/symlink strategies unless automatic resolution is unsafe or ambiguous;
- validate instruction presence, CLI availability, and context reading before reporting a Tier 2 connection as ready;
- show details, the generated command, and technical tier through a details/verbose path and structured JSON;
- keep existing explicit `--runtime` flags for automation and advanced control, not as the primary quick start.

If no agent is detected, onboarding asks the user which agent they use or offers `umem connect` without blocking project memory initialization. If a new agent appears later, `umem connect` repeats detection and connection without reinitializing memory.

## User Command Model

The primary mental model is limited to:

```bash
umem init
umem connect
umem doctor
```

- `umem init` initializes project memory and connects safely detected agents.
- `umem connect` discovers or adds agents after initialization, defaulting to project scope.
- `umem doctor` diagnoses missing CLI exposure, instructions, skills, MCP configuration, and context-read failures with a recommended recovery action.

Advanced commands and runtime flags remain available, but the quick start and first-run success message must not require them.

## Tier 1 Selection Policy

Tier 1 is intentionally small and controlled by the maintainers. There is no fixed Top-5 quota and no automatic promotion based on an external agent catalog.

At release planning time, maintainers evaluate:

- documented user demand and recurring setup friction;
- market relevance, adoption trend, and ecosystem fit;
- actual use by the UMEM maintainers and contributors;
- strategic distribution or demonstration value;
- stability of instruction, skill, configuration, CLI, and MCP surfaces;
- ability to implement safe setup, sync, snapshot, audit, rollback, and validation;
- availability of repeatable context-read checks;
- ongoing maintenance cost and capacity.

The selected list and dated rationale must be recorded in release planning or the support matrix. Market position informs the decision but does not create an obligation to support a specific number of hosts.

Tier 1 promotion requires a working adapter and repeatable validation. A host may be demoted to Tier 2 when its integration becomes broken, unsafe, unstable, unmaintainable, or impossible to validate. Promotion and demotion must be documented.

## Tier 2 Portable Contract

Tier 2 scales through portable instructions rather than a host-specific adapter. An agent qualifies when it can:

- consume project instructions from `AGENTS.md`, the official UMEM Agent Skill, or both;
- execute the `umem` CLI in the current workspace;
- read structured or human output from `umem status` and `umem context`;
- follow UMEM safety and confirmation rules.

The official Tier 2 operating instructions must direct the agent to:

- run `umem status` and load `umem context` before durable planning, implementation, review, or structured workflows;
- reconcile UMEM context with current repository files and the user's current instructions;
- consult memory before recording architecture decisions, persistent preferences, bug fixes, workflow rules, or skill recommendations;
- persist only stable, reusable, and safe information;
- never persist secrets, credentials, raw logs, stack traces, sensitive environment values, or transient task progress;
- respect confirmation requirements for rule promotion, skill creation, destructive actions, and instruction changes;
- report durable facts recorded or proposed at the end of the task when requested by the instruction contract.

Tier 2 validation proves the portable contract, not native host support. At minimum it checks instruction presence, CLI availability, and one successful context-read operation. Behavioral automation is optional when the host does not expose a reliable test harness.

### Two-Layer Instruction Model

Tier 2 uses two complementary instruction layers:

1. A compact `AGENTS.md` bootstrap that is loaded predictably and tells the agent to load UMEM context before planning, implementation, or review, follow the official UMEM skill when available, and persist only stable and safe information.
2. The official UMEM Agent Skill containing the complete CLI workflow, memory-safety rules, durable-fact guidance, confirmations, examples, and edge cases.

`AGENTS.md` must remain short and must not duplicate the full skill. The skill should allow progressive disclosure through relative references. When the host supports only one of the two layers, that layer must contain enough instruction to complete the Tier 2 validation contract.

After setup, the expected user behavior is normal conversation such as "continue the authentication implementation". The agent instructions, not the user prompt, are responsible for activating the UMEM workflow.

## Agent Skills And `npx skills`

UMEM should provide an official canonical Agent Skill containing the Tier 2 workflow. The skill remains owned by UMEM and follows the open Agent Skills structure with `SKILL.md` plus optional `references/`, `scripts/`, and `assets/`.

`npx skills` is an optional distribution bridge because it maintains mappings for many agent-specific skill directories, supports local and Git sources, and supports project/global installation through copy or symlink. UMEM must not copy its external agent catalog into a hardcoded support promise.

Initial integration rules:

- prefer project-scoped installation until global-path and removal behavior are validated for the target host;
- detect `node` and `npx` before offering the bridge;
- keep the exact command and target mechanics in a details view while the primary prompt asks whether to connect the detected agent;
- combine the external installation with the recommended project connection plan under one explicit confirmation;
- preserve UMEM snapshot and audit guarantees for mutations performed by UMEM itself;
- label mutations delegated to `npx skills` as externally executed unless UMEM can inspect and protect the complete write plan;
- disable anonymous `skills` telemetry for UMEM-initiated installation and document Node.js requirements, deterministic project-copy behavior, network use, and the external mutation boundary in details and logs;
- provide a manual copy or UMEM-native installation path when `npx` is unavailable;
- validate the installed skill and a real `umem context` read before reporting Tier 2 readiness.

The intended project-scoped external command is equivalent to:

```bash
DISABLE_TELEMETRY=1 npx --yes skills@1.5.20 add https://github.com/YanAmorelli/universal-memory/tree/v0.5.0/skills/universal-memory --skill universal-memory --agent <agent> --copy -y
```

The exact command may evolve with the external CLI, but the product contract remains: UMEM selects the official skill and detected agent, project scope is the default, anonymous installer telemetry is disabled, the user confirms once, and readiness is validated afterward.

`npx skills use` may also be documented as a transient bootstrap that generates the skill prompt or starts a supported agent without permanent installation. This is useful for experimentation but does not promote a host to Tier 1.

## Capabilities By Tier

| Capability | Tier 1 | Tier 2 | Tier 3 |
| --- | --- | --- | --- |
| Host-specific maintained adapter | Required | Not required | No |
| Portable UMEM instructions | Yes | Required | Recommended but not guaranteed |
| `AGENTS.md` support | Adapter-dependent | Qualifying instruction surface when available | Not assumed |
| UMEM Agent Skill | Installed when supported | Primary portable option when supported | Optional manual aid |
| UMEM CLI | Supported | Required | Optional, not the defining channel |
| MCP | Adapter-dependent | Optional | Required and manually configured |
| Native host mutation | Managed with snapshot/audit/rollback | Not promised | No |
| Validation | Host setup/sync plus context-read check | Instruction presence plus CLI context-read check | MCP availability only |
| Behavior confidence | Managed and validated | Directed by portable instructions | Unmanaged and not guaranteed |

## Registry Model

The registry must not encode all capabilities in the tier enum. Each entry should declare independently:

- `runtime_id` and display name;
- `support_tier` (`tier_1_native_managed`, `tier_2_directed_cli`, or `tier_3_unmanaged_mcp`);
- `managed_by_umem`;
- `instruction_channels`, including `agents_md`, native instruction files, or Agent Skill;
- `cli_access` and CLI validation method;
- `skill_support` and optional `skill_installer` such as `umem_native`, `npx_skills`, or `manual`;
- `mcp_mode` such as `managed`, `optional`, `unmanaged`, or `unavailable`;
- native instruction and skill targets when UMEM owns them;
- validation level and known limitations;
- dated selection evidence for Tier 1.

Tier 2 does not require one registry entry per agent. A generic directed-CLI profile can represent agents that satisfy the portable contract, while named entries may exist for detection, documentation, or installation-command generation.

## Portable Context Export

UMEM provides a safe context export such as `manual-context.md` for explicit agent handoff, offline work, debugging, and hosts outside the support matrix. It is not the definition of Tier 3.

The export must:

- run through the same retrieval and secret-safety constraints as `umem context`;
- avoid mutating host files;
- produce human-readable Markdown by default and pure JSON when requested;
- state that exported context may become stale;
- instruct the target agent to report durable facts and decisions after the session;
- require review before facts from a host without UMEM write access are persisted.

## Requirements

- R1: The support model must distinguish Tier 1 Native/Managed, Tier 2 Directed CLI, and Tier 3 Unmanaged MCP.
- R2: Tier 1 hosts must be selected through documented market, demand, strategic, internal-use, validation, and maintenance analysis rather than a fixed market-rank quota.
- R3: Tier 1 hosts must declare native targets, bootstrap behavior, validation checks, docs, supported channels, limitations, and skill capability.
- R4: Every Tier 1 mutation must use snapshot, audit, atomic-write, and rollback protections.
- R5: Tier 2 must have portable UMEM instructions delivered through `AGENTS.md`, the official UMEM Agent Skill, or both.
- R6: Tier 2 must require executable access to the UMEM CLI and validate at least one context-read operation.
- R7: Tier 2 documentation must state that UMEM supports the portable contract rather than every host-specific behavior.
- R8: UMEM must publish or package an official canonical Agent Skill for directed CLI usage.
- R9: `npx skills` integration must remain optional and must not become a mandatory UMEM runtime dependency.
- R10: Automatic invocation of `npx skills` must require explicit confirmation and disclose target, scope, mutation method, network use, and telemetry controls.
- R11: A host listed by `npx skills` must not be promoted automatically to Tier 1.
- R12: Tier 3 documentation must state that unmanaged MCP exposes capability without behavioral guarantees.
- R13: Tier 3 validation must verify only MCP server/tool availability unless a stronger host workflow is separately programmed and promoted.
- R14: `manual-context.md` or equivalent export must remain available as a cross-tier and unsupported-host handoff utility.
- R15: Native skill installation must be conditional on declared capability, not tier alone.
- R16: The runtime registry must model tier, instruction, CLI, skill, MCP, validation, management, evidence, and limitation dimensions separately.
- R17: Tier 2 may use a generic profile and must not require a hardcoded registry entry for every compatible agent.
- R18: Tier promotion and demotion must be explicit, evidence-backed, and documented.
- R19: The primary onboarding path must be `umem init` without mandatory runtime flags or tier selection.
- R20: Interactive onboarding must detect relevant project agents and recommend a safe combined connection plan.
- R21: The default onboarding must ask for no more than one confirmation when all proposed project-scoped actions are safe and unambiguous.
- R22: The default human output must describe agents and outcomes without requiring tier, path, MCP, `npx`, or copy/symlink knowledge.
- R23: UMEM-initiated `npx skills` execution must disable anonymous `skills` telemetry and disclose external network and mutation boundaries before confirmation.
- R24: If Node.js or `npx` is unavailable, core initialization must succeed and UMEM must use `AGENTS.md`, manual skill copy, UMEM-native installation, or an actionable later step as appropriate.
- R25: The product must provide `umem connect` to discover or add agents after initialization without recreating project memory.
- R26: Successful onboarding must end with a concise readiness summary and a natural-language next step rather than a list of infrastructure commands.
- R27: Normal agent usage after setup must not require the user to explicitly ask the agent to use UMEM.
- R28: The public, packaged, initialized, and natively synchronized Universal Memory skill must derive from one complete canonical skill tree.
- R29: The external installer package pin and its local agent-to-project-skill-path catalog must be reviewed and updated atomically.
- R30: A fresh portable installation must invoke `npx skills add` exactly once, invoke no discovery installation and no `skills ls`, and validate the complete tree at the pinned project target afterward.
- R31: Unknown external agent IDs must not execute `npx`; they must fall back to a managed or manual path.
- R32: Existing complete `use-universal-memory` installations must be recognized as a legacy alias without silently creating a duplicate skill tree or overwriting customized files; incomplete legacy roots or coexistence with the canonical root must fail with an explicit non-destructive diagnostic.

## Non-Goals

- Do not maintain native adapters for every agent supported by an external installer.
- Do not copy the external catalog into the Tier 1 runtime registry or treat the pinned
  installation-path catalog as a native support promise.
- Do not equate `AGENTS.md` consumption with shell or CLI capability without validation.
- Do not equate Agent Skill installation with correct execution behavior.
- Do not claim that arbitrary MCP hosts will consult or update memory automatically.
- Do not make Node.js a mandatory dependency for core UMEM workflows.
- Do not classify prompt-only or export-only workflows as Tier 3 support.
- Do not build a cloud gateway for web-only agents as part of this change.

## Acceptance Criteria

- Given a host support entry, when it is reviewed, then tier and channel capabilities are explicit and independent.
- Given a Tier 1 candidate, when release planning evaluates it, then dated market, demand, internal-use, strategic, validation, and maintenance evidence is recorded before promotion.
- Given a Tier 1 setup, when UMEM mutates host files, then snapshot, audit, atomic write, rollback, and context-read validation apply.
- Given an agent reads `AGENTS.md` and can run the UMEM CLI, when the Tier 2 setup is validated, then it successfully executes at least one `umem context` read.
- Given an Agent Skills-compatible host with CLI access, when the official UMEM skill is installed or used, then it directs the agent through the same Tier 2 CLI and safety contract.
- Given `npx` is unavailable, when Tier 2 setup is requested, then UMEM provides an `AGENTS.md`, manual skill copy, or UMEM-native alternative without blocking core initialization.
- Given UMEM offers to invoke `npx skills`, when the user reviews the plan, then agent, scope, command, deterministic copy behavior, network requirement, and external-mutation boundary are visible before confirmation.
- Given `npx skills` lists a new agent, when UMEM detects it, then the agent is not automatically marked Tier 1.
- Given a user manually connects MCP to an unmodeled host, when setup is reported, then the integration is labeled Tier 3 Unmanaged MCP and no behavior guarantee is claimed.
- Given an explicit handoff or unsupported host, when context is exported, then UMEM produces `manual-context.md` or equivalent safe output without changing the host's tier.
- Given a host loses a stable integration surface or maintenance ownership, when the support matrix is reviewed, then it can be demoted from Tier 1 with documented rationale and a Tier 2 path when possible.
- Given a new project with detectable agents, when the user runs `umem init`, then UMEM recommends the detected agents, requests one confirmation, applies the appropriate native or portable paths, validates context access, and reports readiness without exposing tiers by default.
- Given optional Agent Skill distribution is required, when onboarding presents the recommended plan, then the user sees a simple connection outcome while technical details disclose the external installer, network use, disabled telemetry, scope, and mutation boundary.
- Given Node.js or `npx` is missing, when the user accepts initialization, then project memory still initializes and every detected agent receives the best available safe fallback or an explicit pending action.
- Given initialization is complete and another agent is installed later, when the user runs `umem connect`, then UMEM detects or lets the user select the agent, connects it without recreating memory, and validates the selected channel.
- Given setup succeeds, when the success message is rendered, then it ends with guidance equivalent to "You're ready. Work with your agents normally" and does not require an explicit UMEM invocation prompt.

## Promotion Criteria: Tier 2 To Tier 1

A Tier 2 host can be promoted when:

- market analysis, user demand, internal use, or strategic value justifies native investment;
- instruction, skill, CLI, configuration, or MCP surfaces are stable and documented;
- UMEM can maintain an adapter without brittle private assumptions;
- setup and context reading can be checked through a repeatable test or checklist;
- all native mutations can satisfy UMEM safety guarantees;
- maintenance ownership and release capacity exist;
- limitations can be stated accurately.

Popularity is evidence, not an automatic promotion rule. Skill-directory compatibility by itself is insufficient.

## Artifact Deltas

### PRD

- Replace Top-5-plus-existing and generic-MCP Tier 2 language with the revised model.
- State that Tier 1 selection is a documented market and maintenance decision.
- Add the portable instruction-plus-CLI contract and optional Agent Skills distribution bridge.
- Reclassify unmanaged MCP as Tier 3.
- Keep portable context export as a cross-tier fallback utility.

### Architecture

- Separate tier from instruction, CLI, skill, MCP, validation, management, evidence, and limitation capabilities.
- Add an official UMEM Agent Skill and optional `npx skills` bridge boundary.
- Define zero-flag `umem init`, automatic agent detection, a single recommended confirmation, and outcome-oriented output as the primary interaction architecture.
- Add `umem connect` as an idempotent post-initialization agent-connection use case.
- Keep Tier 2 generic so broad coverage does not require an adapter per host.
- Restrict Tier 3 validation to MCP capability unless a maintained integration is added.

### Epics And DevEx

- Update registry and onboarding stories for Native Hosts, Directed CLI Agents, and Unmanaged MCP.
- Add golden-path acceptance criteria that hide tier and installer mechanics by default while preserving details and JSON observability.
- Add `umem connect` and graceful no-Node fallback acceptance criteria.
- Add official UMEM Agent Skill distribution and validation acceptance criteria.
- Add explicit confirmation and external-mutation disclosure for optional `npx skills` execution.
- Retain the context export story as handoff/fallback rather than Tier 3 implementation.

## Resolved Scope Questions

- Tier 1 selection: release-time market and product analysis, without a fixed quota or automatic host list.
- Tier 2 minimum: portable UMEM instructions plus executable UMEM CLI and a successful context-read check.
- Agent Skills: official UMEM skill, with `npx skills` as an optional external distribution bridge.
- Tier 3: manually configured/unprogrammed MCP with capability-only guarantees.
- Portable export: cross-tier and unsupported-host utility, not a tier definition.
- External catalog: useful for reach and discovery, never authoritative for native UMEM support.
- Primary UX: `umem init` detects and connects agents with one confirmation; users work normally afterward.
- Ongoing connection: `umem connect` adds agents later without reinitializing memory.
- Infrastructure visibility: `npx skills` is hidden from the default path, disclosed in details, and invoked with anonymous telemetry disabled.
