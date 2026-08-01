# Sprint Change Proposal - universal-memory

> Superseded note (2026-06-27): the agent-support tier recommendations in this
> 2026-05-31 proposal were refined by
> `sprint-change-proposal-2026-06-12-agent-support-evolution.md` and
> `spec-agent-support-evolution-tiers-and-mcp-fallback.md`. The current direction
> selects a small Tier 1 through market and maintenance analysis, scales Tier 2
> through portable `AGENTS.md` or Agent Skill instructions plus the UMEM CLI,
> treats manually configured/unprogrammed MCP as Tier 3, and keeps
> `manual-context.md` as a cross-tier and unsupported-host handoff utility.

**Date:** 2026-05-31
**User:** Yan
**Review Mode:** Batch
**Scope:** Moderate

## 1. Issue Summary

### Trigger

The current planning for `universal-memory` covers an MVP with local memory, CLI, MCP, `AGENTS.md`, `CLAUDE.md`, Agent Skills creation, and two MVP hosts (`codex` and `claude_code`). During the product direction review, four product and architectural changes emerged:

1. Add terminal visual identity for `umem`, using the metaphor of a USB flash drive connected to the terminal.
2. Add English support and make English the default product language.
3. Expand onboarding to multiple runtimes/agents, including OpenCode, Antigravity, and Cursor, with multi-selection similar to the GSD workflow.
4. Install skills into the native folders of each agent when the agent natively consumes skills, for example, `.agents/`, `.claude/`, `.cursor/`, `.opencode/`, and equivalents.

### Problem Statement

The current plan treats host support mainly as instruction file configuration (`AGENTS.md`, `CLAUDE.md`) and context reading validation. This model is insufficient for modern agents that have native directories for skills, rules, or configuration. In addition, the product needs to be internationalized from the MVP stage, with English as the default language, to reduce rework in the CLI, docs, and generated artifacts. The onboarding experience also needs to evolve from single host selection to multi-runtime selection with explicit paths and recognizable visual feedback.

### Evidence

- Example of desired UX: terminal prompt with multi-selection of runtimes, such as `Which runtime(s) would you like to install for?`, listing Claude Code, Antigravity, Cursor, OpenCode, and others.
- Explicit user requirement: skills must reside in native agent folders for native consumption, not just in `.umem/skills/`.
- Current PRD FR7-FR8 refers generically to Claude, Gemini, and ChatGPT, but does not model native paths or the runtime registry.
- Current architecture limits the MVP to `codex` and `claude_code` and treats `.cursor`, `.github/copilot-instructions.md`, `.windsurf`, `.continue`, and others as post-MVP.

### Visual Identity Terminology

The most likely technical name for the USB drawing in the terminal is **ASCII art** when using only ASCII characters, **ANSI art** when including color/style via escape codes, and **FIGlet/TOIlet banner** when the text/logo is rendered by terminal fonts. For `umem`, the proposal is to use a small **ANSI/ASCII splash banner**, independent of external tools, with a no-color fallback.

## 2. Impact Analysis

### Checklist Summary

| Item | Status | Finding |
| --- | --- | --- |
| 1.1 Triggering story | [N/A] | There is no active implementation story that revealed the problem. The change came from a product review prior to implementation. |
| 1.2 Core problem | [x] | New product requirement and architectural adjustments for host/runtime/skills. |
| 1.3 Evidence | [x] | GSD screenshot/reference, requirement for native folders, and gaps in PRD/architecture/epics. |
| 2.1 Current epic impact | [x] | Epic 5 and Epic 6 need to be expanded; Epic 1 and Epic 4 receive secondary impact. |
| 2.2 Epic-level changes | [x] | Modify Epic 5, modify Epic 6, and add cross-cutting i18n/branding support. |
| 2.3 Remaining epics | [x] | Epic 1 needs to support locale/default language configuration; Epic 4 needs to standardize messages in English by default. |
| 2.4 Future epics invalidated | [x] | No epics become obsolete; some features previously marked as post-MVP should be included in the MVP or in an explicit MVP+ phase. |
| 2.5 Priority/order | [x] | Runtime registry must precede host setup and native skill installation. |
| 3.1 PRD conflicts | [x] | FR7-FR8, MVP scope, host matrix, CLI examples, and NFRs need to be updated. |
| 3.2 Architecture conflicts | [x] | Current host adapters are too narrow; missing Runtime Registry, Native Skill Target, and i18n/message catalog. |
| 3.3 UX impact | [x] | No visual UX, but CLI DevEx changes: splash, default language, multi-selection. |
| 3.4 Other artifacts | [x] | README/docs, devex interaction spec, CLI/MCP tests, and sprint status will need updates after approval. |
| 4.1 Direct adjustment | [x] Viable | Best path: adjust artifacts and stories without rollback. |
| 4.2 Rollback | [N/A] | There is no consolidated implementation to revert. |
| 4.3 MVP review | [x] Viable | MVP remains achievable, but runtimes need to be classified as Tier 1 vs Tier 2. |
| 4.4 Recommendation | [x] | Hybrid: Direct Adjustment + MVP scope clarification. |

### Epic Impact

**Epic 1: Local Foundation, Models, and Contracts**

Secondary impact. Must add configuration for default language (`en`) and optional output language. The `.umem/config.toml` structure must persist runtime selection and locale.

**Epic 4: CLI and MCP Parity**

Secondary impact. Human-facing CLI messages will default to English; JSON field names remain language-independent. The MCP must receive stable errors/messages with codes and a `recovery_hint` in English by default.

**Epic 5: Hosts and Instruction Synchronization**

Primary impact. Must stop being just `codex` + `claude_code` and start modeling runtimes/agents as adapters with native paths, capabilities, and installation targets.

**Epic 6: Latent Skills and Skill Management**

Primary impact. `.umem/skills/` remains the registry/canonical store, but installation/replication for native consumption must use targets per runtime, for example, `.agents/skills/`, `.claude/skills/`, `.opencode/skills/`, `.cursor/rules/` where applicable.

### Artifact Impact

**PRD:** update MVP scope, FR7-FR8, FR20-FR21, host support matrix, CLI examples, language requirements, and onboarding journey.

**Architecture:** add Runtime Registry, Runtime Adapter, Native Skill Installer, Message Catalog/i18n, Terminal Branding Presenter, and Tiered Runtime Support strategy.

**Epics:** rewrite Epic 5 and adjust Epic 6; add specific stories for default language, CLI banner, and runtime selection.

**UX/DevEx:** update `_bmad-output/planning-artifacts/devex-interaction-spec.md` if it exists, or create/edit an equivalent section in the artifacts to cover multi-selection, non-interactive fallback, and JSON output.

## 3. Recommended Approach

### Selected Path

**Hybrid: Direct Adjustment + MVP Scope Clarification.**

No rollback is needed. The change should be incorporated by updating the PRD, applying an architectural patch, and restructuring epics/stories. The critical point is to avoid letting "supporting many agents" turn into a promise of deep integration for all of them in the MVP.

### Tiered Runtime Support

To control scope, it is recommended to classify runtimes into tiers:

| Tier | Meaning | Acceptance Criteria |
| --- | --- | --- |
| Tier 1 | Full MVP Support | Setup, native paths, instructions, skill install where applicable, local validation, and tests. |
| Tier 2 | Basic MVP Support | Detects path, installs instructions/skills when the format is known, validation can be manual/documented. |
| Tier 3 | Catalog/Documented | Appears as planned or experimental, without blocking the MVP. |

Initial proposal:

| Runtime | Recommended Tier | Initial Target Path |
| --- | --- | --- |
| Claude Code | Tier 1 | `~/.claude/`, `.claude/`, `CLAUDE.md` according to scope |
| OpenCode | Tier 1 | `~/.config/opencode/`, `.opencode/`, `AGENTS.md` according to support |
| Cursor | Tier 2 | `~/.cursor/`, `.cursor/rules/` |
| Antigravity | Tier 2 | `~/.gemini/antigravity/` or path confirmed by runtime adapter |
| Codex | Tier 1 or rename to OpenAI/Codex | `AGENTS.md`, applicable config path |
| Gemini | Tier 2 | `~/.gemini/`, `GEMINI.md` when applicable |

### Effort Estimate

**Medium.** Most of the work is modeling and CLI/onboarding; deep integration per runtime should be incremental.

### Risk Level

**Medium.** The main risk is promising native compatibility without stable contracts from each agent. Mitigation: declarative registry, tiers, and per-adapter testing.

### Timeline Impact

Adds work before completing Epic 5 and Epic 6. It does not block Epics 1-3, except for basic locale and config structure.

## 4. Detailed Change Proposals

### PRD Changes

#### Product Scope / MVP

OLD:

```md
* **Auto-Adaptation Motor:** A dedicated agent/routine that analyzes memory and updates the AGENTS.md file (global instructions) to reflect user behavior.
* **On-Demand Skill Creation:** Ability to generate new skills (tools/scripts) based on the needs detected during the workflow.
```

NEW:

```md
* **Auto-Adaptation Motor:** A dedicated agent/routine that analyzes memory and updates shared manifests and native files of supported runtimes to reflect user behavior without drift.
* **On-Demand Skill Creation and Native Skill Installation:** Ability to generate canonical Agent Skills and install them in native directories of supported agents when the runtime natively consumes skills.
* **Multi-Runtime Onboarding:** CLI flow for multi-selection of runtimes/agents, with English as the default language and terminal visual feedback.
```

Rationale: expands the MVP to reflect that the integration unit is a runtime/adapter, not just an instruction file.

#### FR7-FR8

OLD:

```md
- **FR7:** During initial configuration, the system must allow the user to select supported agent providers (e.g., Claude, Gemini, ChatGPT).
- **FR8:** The system must automatically configure the instruction files of the selected agents (e.g., `CLAUDE.md`, `AGENTS.md`) to initialize the use of universal memory immediately after installation.
```

NEW:

```md
- **FR7:** During initial setup, the system must allow the user to select one or more supported runtimes/agents from a registry, including at least Claude Code, OpenCode and Codex/OpenAI-class AGENTS.md hosts, with Cursor and Antigravity represented according to their support tier.
- **FR8:** The system must configure the selected runtimes by writing or updating their supported instruction targets and native skill targets, such as `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, `.cursor/`, `.opencode/` or equivalent runtime-specific paths, with snapshot and audit protection before every mutation.
```

Rationale: makes the requirement testable and compatible with native installation.

#### New Language Requirement

NEW:

```md
- **FR29:** The product must use English as the default language for CLI prompts, help text, generated instructions, skill scaffolds and documentation templates, while allowing an explicit locale configuration for other supported languages such as Portuguese.
```

Rationale: avoids i18n retrofitting after the CLI, docs, and templates are already scattered.

#### New Branding Requirement

NEW:

```md
- **FR30:** The CLI onboarding experience should include a compact terminal brand element for `umem`, implemented as ANSI/ASCII splash art with a no-color fallback and disabled automatically for JSON/non-interactive output.
```

Rationale: improves product recognition without breaking automation.

#### FR20-FR21

OLD:

```md
- **FR20:** The system must generate the folder structure and the `SKILL.md` file following the `agentskills.io` standard.
- **FR21:** The user must be able to list, activate, edit, and deactivate registered Skills via the CLI.
```

NEW:

```md
- **FR20:** The system must generate a canonical Agent Skill structure with `SKILL.md`, optional `scripts/` and optional `references/`, then install or link it into native skill directories for selected runtimes when supported by that runtime adapter.
- **FR21:** The user must be able to list, activate, edit, disable and inspect both canonical skills and per-runtime installed skill targets through CLI and MCP-equivalent capabilities.
```

Rationale: separates canonical skills from runtime-specific installations.

### Architecture Changes

#### Add Runtime Registry

NEW section:

```md
### Runtime Registry and Adapter Model

The system must model each supported agent/runtime through a declarative runtime adapter.

Each adapter declares:
- `runtime_id`
- display name
- support tier
- default global paths
- default project paths
- instruction targets
- native skill targets
- MCP configuration method
- validation strategy
- mutation/rollback behavior
- known limitations

Runtime selection is stored in global or project TOML config and drives onboarding, instruction sync and native skill installation.
```

Rationale: avoids hardcoded logic and allows adding agents without redesigning the workflow.

#### Add Native Skill Installation Strategy

NEW section:

```md
### Canonical Skills vs Native Skill Targets

`.umem/skills/` remains the canonical registry and source of truth for generated skills.

Runtime-specific directories are installation targets, not the canonical source. The installer may copy, render, link or generate runtime-specific wrappers depending on adapter support.

Every native skill installation must pass through the mutation pipeline: validate, secret scan, snapshot, atomic write, audit.
```

Rationale: avoids drift and keeps rollback/auditing centralized.

#### Add i18n / Message Catalog

NEW section:

```md
### Language Defaults and Message Catalog

English is the default product language for CLI, generated files, templates and documentation scaffolds.

Human-facing strings should be routed through a minimal message catalog or presenter layer. JSON field names, domain enums and config keys remain stable English identifiers regardless of locale.

`--format json`, MCP responses and non-interactive output must never include localized labels in machine-readable field names.
```

Rationale: keeps automation stable and allows Portuguese without breaking contracts.

#### Add Terminal Branding Presenter

NEW section:

```md
### Terminal Branding Presenter

The CLI may render a compact ANSI/ASCII `umem` splash during interactive onboarding.

Rules:
- render only for TTY interactive human output
- disable for `--format json`, `NO_COLOR`, CI and non-interactive mode
- keep width safe for common terminals
- avoid external runtime dependencies for the MVP
```

Rationale: visual identity without risk to scripts/agents.

### Epic Changes

#### Epic 1 Add Story

NEW Story 1.6: Configure Language Defaults

```md
As a user or agent initializing umem,
I want English to be the default language with explicit locale configuration,
So that CLI output, generated instructions and skill templates are consistent and automation-safe.

Acceptance Criteria:
- Given a clean config, when `umem init` runs, then default locale is `en` unless explicitly overridden.
- Given `--format json`, when any command runs, then JSON field names remain stable English identifiers independent of locale.
- Given a supported locale override such as Portuguese, when human output is rendered, then only human-facing labels are localized.
```

#### Epic 4 Add Story

NEW Story 4.6: Render Terminal Branding Safely

```md
As a user running interactive onboarding,
I want a compact umem terminal splash using ANSI/ASCII art,
So that the product has recognizable identity without breaking automation.

Acceptance Criteria:
- Given an interactive TTY, when onboarding starts, then a compact umem USB/terminal splash may be shown.
- Given `--format json`, CI, `NO_COLOR` or non-interactive output, when the command runs, then no splash or ANSI escape codes are emitted.
- Given narrow terminal width, when the splash is rendered, then it falls back to plain text.
```

#### Epic 5 Rewrite Summary

OLD:

```md
The user can configure supported hosts, validate context reading, and keep `AGENTS.md` and `CLAUDE.md` synchronized without duplication, drift, or ambiguous ownership.
```

NEW:

```md
The user can select multiple supported runtimes/agents, configure their instruction targets and native skill targets, validate context reading, and keep shared manifests and native files synchronized without duplication, drift, or ambiguous ownership.
```

#### Epic 5 Story Changes

Story 5.1 should become **Model Runtime Registry and Targets**.

Key AC additions:

- Runtime adapters declare support tier, global paths, project paths, instruction targets and native skill targets.
- Registry includes at least Claude Code, OpenCode and Codex/OpenAI-class AGENTS.md support.
- Cursor and Antigravity are represented as Tier 2 unless validated to Tier 1.

Story 5.6 should become **Multi-Runtime Selection Onboarding**.

Key AC additions:

- Interactive prompt asks: `Which runtime(s) would you like to install for?`
- User can select multiple runtimes via comma-separated or space-separated indices.
- Defaults are safe and visible.
- Non-interactive mode accepts explicit flags such as `--runtime claude-code --runtime opencode`.
- JSON output reports selected runtimes, skipped runtimes, target paths and pending manual steps.

#### Epic 6 Story Changes

Story 6.3 should become **Generate Canonical Skill and Install Native Targets**.

Key AC additions:

- Canonical skill is generated under `.umem/skills/` or configured global canonical store.
- Runtime-specific targets are installed only for selected runtimes that support native skills.
- Each installed target records source skill ID, target runtime, path and audit reference.
- Deactivation disables/removes installed targets according to adapter policy without deleting canonical skill by default.

## 5. Implementation Handoff

### Scope Classification

**Moderate.** This is not a full strategic reset, but it requires coordinated updates to PRD, architecture and epics before implementation.

### Recommended Handoff

1. Product Manager / PRD edit: update PRD requirements, scope, language defaults and runtime support matrix.
2. Architect: patch architecture with Runtime Registry, Native Skill Installer, i18n/presenter rules and terminal branding rules.
3. PO/Planning: update Epic 5 and Epic 6 stories, add language/branding stories and update acceptance criteria.
4. Developer agent: implement only after the above artifacts are approved.

### Implementation Sequencing

1. Add language default and config support early in Epic 1.
2. Add CLI branding presenter in Epic 4 after base CLI exists.
3. Implement Runtime Registry before any concrete runtime adapter.
4. Implement Tier 1 adapters first.
5. Implement native skill installation after canonical skill generation is stable.

### Success Criteria

- `umem init` defaults to English human output.
- Interactive onboarding supports multiple runtime selection.
- Non-interactive onboarding supports explicit runtime flags and JSON output.
- Runtime registry lists Claude Code, OpenCode, Codex/OpenAI-class AGENTS.md support, Cursor and Antigravity with support tiers.
- Canonical skills can be installed into native target directories for selected runtimes with snapshot, audit and rollback.
- Terminal splash never appears in JSON, CI or non-interactive output.

## 6. Recommendation

Approve this proposal, then run the next BMad steps in this order:

1. `bmad-edit-prd` to update the PRD.
2. `bmad-create-architecture` or an architecture patch workflow to update architecture decisions.
3. `bmad-create-epics-and-stories` to update the epic/story breakdown.
4. `bmad-create-story` for the first implementation-ready story after the artifacts are aligned.
