---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
  - step-e-01-discovery
  - step-e-02-review
  - step-e-03-edit
releaseMode: phased
inputDocuments: []
documentCounts:
  briefCount: 0
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 0
classification:
  projectType: Developer Tool / AI Middleware
  domain: AI Infrastructure / Developer Experience (DevEx)
  complexity: Medium-High
  projectContext: greenfield
workflowType: 'prd'
date: '2026-04-25'
lastEdited: '2026-05-31'
editHistory:
  - date: '2026-05-31'
    changes: 'Sprint change proposal integration: terminal visual identity, English as default, multi-runtime onboarding, native skill directories, and interactive skill updates/synchronization with conflict warning guardrails.'
  - date: '2026-05-19'
    changes: 'Validation-guided edit: measurable success criteria, post-MVP import/export, developer-tool sections, measurable NFRs, and implementation-leakage cleanup.'
  - date: '2026-05-19'
    changes: 'Added explicit Backup & Recovery requirements and raised runtime baseline to Python 3.12+.'
---

# Product Requirements Document - universal-memory

**Author:** Yan
**Date:** 2026-04-25

<!-- This document will be built incrementally during the PRD creation workflow -->

## Executive Summary

**universal-memory** is an agnostic cognitive persistence layer designed to eliminate the "repetition tax" in workflows with multiple AI agents. The system acts as an "identity pen drive," allowing the user to seamlessly transport their context, preferences, and interaction history across different sessions and models. The core objective is operational cohesion: instead of the user adapting to each new session, the agent ecosystem automatically adapts to the user's behavior and instructions through a global settings synchronization engine (`AGENTS.md`).

### What Makes This Special

*   **Identity Portability:** Full decoupling from specific vendors or products, ensuring the user's "brain" remains sovereign and migratable.
*   **Active Behavioral Adaptation:** Not only stores data, but translates interactions into system instructions, automatically updating configuration files (`AGENTS.md`) to align all auxiliary agents with the user's mental model.
*   **Context and Cost Efficiency:** Drastic reduction in the need to re-explain tasks and concepts, optimizing token consumption and response times through a shared short- and long-term memory.

## Project Classification

*   **Project Type:** Developer Tool / AI Middleware
*   **Domain:** AI Infrastructure / Developer Experience (DevEx)
*   **Complexity:** Medium-High (Configuration automation and system file manipulation)
*   **Project Context:** Greenfield (New Product)

## Success Criteria

### User Success

*   **Friction Reduction:** After 5 saved facts, the user initiates a complex task on a new supported agent with at least 80% less initial guidance text than the manual baseline.
*   **Adoption by Necessity:** After 10 active memory sessions, the user maintains usage of universal-memory in at least 2 supported tools/agents and considers the absence of memory a relevant operational blocker.
*   **Token Savings:** The average volume of tokens spent on repetitive preambles drops by at least 60% across 10 comparable sessions.

### Business Success

*   **Vendor Agnosticism:** The MVP operates with at least 2 different AI hosts/agents using the same memory base and consistent instructions.
*   **Operational Efficiency:** Onboarding time for a new supported tool drops to under 10 minutes, measured from the start of configuration to the first successful context read.

### Technical Success

*   **Vendor Agnosticism:** The memory engine and the `AGENTS.md` file must be successfully interpreted and applied across at least two different LLM providers (e.g., OpenAI and Anthropic).
*   **Configuration Integrity:** The auto-adaptation engine must update `AGENTS.md` without corrupting existing instructions or creating conflicting behavioral loops.
*   **Injection Latency:** Memory retrieval and context assembly add less than 200ms to the start of a local session in 95% of test executions.

### Measurable Outcomes

*   An 80% decrease in "initial guidance messages" in new sessions after the first 5 facts are saved in the universal memory.
*   Zero manual edits to the `AGENTS.md` file by the user after the adaptation engine is activated.

## Product Scope

### MVP - Minimum Viable Product

*   **Core Memory Engine:** Local persistence system (JSON/Markdown) for storing facts, preferences, and consolidated history.
*   **Auto-Adaptation Motor:** A dedicated agent/routine that analyzes memory and updates shared manifests and native runtime files of supported runtimes to reflect user behavior without drift.
*   **On-Demand Skill Creation and Native Skill Installation:** Ability to generate canonical Agent Skills and install them in native directories of supported agents when the runtime consumes skills natively.
*   **Natural Agent Onboarding:** Zero-flag `umem init` detects relevant agents, recommends a safe project-scoped plan, asks once, connects and validates them, with English as the default language and concise visual terminal feedback.
*   **Interactive Update & Synchronization:** Ability to update canonical skills, propagate changes to local runtimes, synchronize local benchmarks/data, and actively interact with the user in case of conflicts in native rules (e.g., Cursor).
*   **Universal Interface:** CLI or simple protocol allowing any agent to read/write from/to memory.
*   **Backup & Rollback Guardrails:** Local protection against data loss prior to automatic mutations in memories, rules, skills, and instruction files.

### Growth Features (Post-MVP)

*   **Multi-Machine Sync:** Cloud or Git repository synchronization to keep memory consistent across different devices.
*   **Memory Import/Export:** Memory base import/export tools for manual migration, external backup, and portability across environments.
*   **Session Sharing:** Ability to share specific "chunks" of memory or sessions across different users or teams.
*   **Memory Pruning:** Intelligent memory management to prevent context from becoming "polluted" with obsolete information.

### Vision (Future)

*   **Autonomous Optimization:** An agent acting as a "Workflow Coach," suggesting proactive automations and improvements even before the user senses the need.
*   **Ecosystem Integration:** Native integration with IDEs and terminals for passive context capture (without requiring explicit input).

### Out of Scope for MVP

*   Automatic multi-machine synchronization.
*   Complete import/export of memory bases.
*   Hosted web interfaces for usage outside of local environments.
*   Memory sharing between users or teams.
*   Proactive autonomous optimization outside of flows explicitly approved by the user.

## User Journeys

### Journey 1: The Multi-Agent Engineer (Short-Term Memory Access)
*   **Persona:** Yan, working in a complex repository with multiple sub-agents.
*   **Scenario:** Yan invokes a new QA-specialized agent to create integration tests.
*   **The Journey:**
    *   **Start:** The agent reads the global `AGENTS.md` file, which contains the directive: "Before starting, check the Short Term Memory of this repository."
    *   **Action:** The agent executes the memory reading tool and obtains a summary: "Yan is using TDD, module X was refactored 10 minutes ago, and the current priority is coverage of the /auth endpoint."
    *   **Climax:** Without Yan typing anything, the agent responds: "Understood, Yan. I read the project memory. I will focus on integration tests for the new /auth endpoint following the TDD pattern you established."
    *   **Resolution:** Yan saves ~300 preamble tokens and 5 minutes of explanation. Workflow proceeds immediately.

### Journey 2: The Instruction Curator (Adaptation by Recurrence)
*   **Persona:** The "Adaptation Agent" (background routine).
*   **Scenario:** During the day, Yan mentions in different chats that he prefers to use `tomllib` instead of `pyyaml` for configuration files.
*   **The Journey:**
    *   **Start:** The universal memory engine records these mentions as "latent facts."
    *   **Action:** At the end of the cycle (or after the 3rd mention), the Adaptation Agent analyzes the recurrence: "The user expressed a preference for tomllib 3 times in 2 different sessions. Relevance: High."
    *   **Climax:** The agent proposes or executes an update to `AGENTS.md`: "Added rule: Always prefer tomllib for parsing TOML files."
    *   **Resolution:** Yan no longer needs to remember to inform agents about his preferred library; the environment has "learned" the behavior.

### Journey 3: The Skill Creator (Capability Expansion)
*   **Persona:** Yan, instructing the system on a new methodology (e.g., SDD - Spec Driven Development).
*   **Scenario:** Yan explains in detail how he wants specifications to be generated before code.
*   **The Journey:**
    *   **Start:** The system detects a complex and repetitive methodological instruction.
    *   **Action:** The Adaptation Agent identifies that this logic can be encapsulated into a reusable tool to reduce cognitive load.
    *   **Climax:** The system generates the boilerplate and logic for a new skill `generate-sdd-spec` and registers it in the system.
    *   **Resolution:** Next time, Yan simply says "create the SDD spec for module Y," invoking the skill instead of re-explaining the methodology.

### Journey 4: The Multi-Runtime Integrator (Onboarding and Portability)
*   **Persona:** Yan, configuring the environment to work simultaneously with Claude Code, OpenCode, and Cursor.
*   **Scenario:** Yan wants to initialize context in a new project and configure all tools at once.
*   **The Journey:**
    *   **Start:** Yan runs `umem init` in the terminal. He is greeted by a beautiful ASCII/ANSI art simulating plugging in a pendrive in the terminal in a minimalist way.
    *   **Action:** UMEM detects Claude Code, OpenCode, and Cursor, then asks once: `Connect Universal Memory to all three? [Y/n]`. Yan does not choose tiers, paths, MCP modes, or installation mechanics.
    *   **Climax:** The installer protects UMEM-managed mutations, connects each agent through the correct native or portable path, optionally uses the external Agent Skills bridge behind the connection experience, and validates real context access.
    *   **Resolution:** The CLI reports each agent as connected and verified, then says that Yan is ready to work normally. Adding another agent later requires only `umem connect`.

### Journey 5: The Version Curator (Updates with Drift Protection)
*   **Persona:** Yan, who manually customized a native Cursor instruction rule (`.cursor/rules/sdd-rules.md`).
*   **Scenario:** `umem` updates the local library and proposes updating the respective canonical skill across all runtimes.
*   **The Journey:**
    *   **Start:** Yan runs `umem update --skills` to propagate skill improvements.
    *   **Action:** `umem` detects that the local Cursor file has diverged from the canonical version.
    *   **Climax:** Instead of silently overwriting, the `umem` CLI displays a highlighted interactive warning in English: `Warning: Native Cursor target sdd-rules.md has manual changes. Overwriting it might break your current agent workflow. Keep local Cursor version or Overwrite with canonical library version? [Keep/Overwrite]`.
    *   **Resolution:** Yan chooses `Keep`. `umem` preserves his local Cursor customization, creates a backup snapshot of the skill, and updates the other tools without cognitive drift.

### Journey Requirements Summary

These journeys reveal the need for the following capabilities:
*   **Initialization Protocol:** Standardized rule in `AGENTS.md` to force reading the Short-Term Memory.
*   **Relevance Analysis Engine:** Recurrence-based scoring logic (2-3 times) to transform ephemeral facts into permanent rules.
*   **Metadata Repository per Repo:** Ability to separate what is "Universal" from what is specific to a project/folder.
*   **Code Generation Engine (Skills):** Infrastructure allowing an agent to write, test, and register new scripts/tools in the user's environment.
*   **Host Integration Flow:** Repeatable procedure to set up multiple runtimes, configure their native skill/rule directories, validate memory reading, and confirm end-to-end behavioral consistency.
*   **Synchronization and Conflict Resolution Engine:** Logic to detect discrepancies between native runtime files and the canonical skill repository, with flow-break confirmation prompts for the user.

## Domain-Specific Requirements

### Compliance & Safety (Local MVP)
- **Secret & ENV Guardrails:** The system must implement a passive detection engine to prevent API keys, credentials, or sensitive environment variables from being inadvertently persisted in memory (short or long-term).
- **Data Sovereignty:** By operating locally, the user retains full control over the persistence files, but there must be a clear interface for selective fact purging.

### Technical Constraints & Memory Model
- **Dual Memory Architecture:** Rigid separation between **Short-Term Memory** (ephemeral, project/folder-specific, focused on immediate tasks and constraints) and **Universal Memory** (persistent, global, focused on behaviors and preferences).
- **Context Management (Signal-to-Noise):** The short-term memory must be dynamically summarized and prioritized to ensure that injection into the agent's context buffer does not degrade performance or cause token overflow.
- **Cross-Vendor Behavior Sync:** The final output of the "memory" is not just raw data, but the active adaptation of the `AGENTS.md` file (or equivalent), ensuring that agents from different providers (OpenAI, Anthropic, etc.) operate under the same behavioral directives of the user.
- **Retrieval Strategy Gate:** The architecture must compare local textual search and semantic search before selecting the retrieval pattern, using benchmarks of latency, result quality, operational cost, and offline simplicity.

### Risk Mitigations
- **Context Hygiene:** Automatic routines for removing obsolete facts from short-term memory after task completion, preventing "cognitive pollution."
- **Skill Encapsulation:** Transformation of recurring complex instructions into formal "Skills" to reduce the risk of hallucination or misinterpretation of raw facts by the agent.

## Innovation & Novel Patterns

### Detected Innovation Areas
- **Consolidation of Fragmented Patterns:** The system not only creates new capabilities, but orchestrates existing market patterns (RAG, profiles, system prompts) into a cohesive and vendor-agnostic solution.
- **"Invisible" Behavioral Adaptation:** The metric of success is silence — reducing the need for the user to explain repetitive assumptions and preferences.
- **Active Confirmation Learning:** Introduction of a feedback loop at the end of the session where the agent asks: "I learned [X], may I save it?". The user controls the evolution of their own "universal agent" with options of "Yes", "Always", or "No".

### Validation Approach
- **Repetition Metric:** Monitoring the frequency of user correction or guidance messages on the same topics in subsequent sessions.
- **Token Efficiency:** Measuring the reduction in the size of the system prompt required to achieve the same level of operational precision after memory injection.

### Risk Mitigation
- **Human Feedback Loop:** Every fact promoted to a "rule" goes through an optional but recommended confirmation, mitigating undesired behavioral drift (preference hallucination).
- **Behavior Regression Testing:** Continuous verification that newly injected rules do not conflict with pre-existing guidelines in `AGENTS.md`.

## Developer Tool Specific Requirements

### Language & Runtime Support
- **Primary Runtime:** The MVP must support Python 3.12+ as the local execution runtime.
- **Package Support:** The MVP must publish installation via PyPI and isolated execution via `uvx`.
- **Host Support Matrix:** The MVP must document, for each supported host/agent, the instruction file used, the MCP connection method, and the memory read/write status.
- **Offline Operation:** All essential MVP capabilities must function without external connectivity after local installation and configuration.

### Runtime & Host Support Matrix

The ecosystem is modeled into **Runtime Support Tiers** to separate native maintenance from portable distribution and unmanaged interoperability:

| Tier | Meaning | Support Promise |
| --- | --- | --- |
| **Tier 1: Native/Managed** | Hosts selected at release time through market, demand, internal-use, strategic-value, validation, and maintenance analysis | UMEM maintains the adapter, native setup/sync, host-specific docs, safety protections, and repeatable context-read validation within documented limits. |
| **Tier 2: Directed CLI** | Agents that consume UMEM instructions through `AGENTS.md`, the official UMEM Agent Skill, or both, and can execute the UMEM CLI | UMEM supports the portable instruction-plus-CLI contract without promising every host-specific configuration surface or behavior. |
| **Tier 3: Unmanaged MCP** | Hosts where the user manually connects UMEM MCP without a programmed or validated integration | MCP tools may be available, but UMEM does not guarantee instruction loading, tool invocation, context use, or durable-memory behavior. |

The Tier 1 host list is selected and documented during release planning. Existing adapters are candidates, not automatic commitments; no external compatibility catalog or fixed market-rank quota determines native support.

Support profiles:

| Profile | Tier | Integration Path |
| --- | --- | --- |
| **Release-selected native hosts** | Tier 1 | Maintained host-specific adapter and validated native targets |
| **`AGENTS.md` + CLI agents** | Tier 2 | Project `AGENTS.md` directs the agent to `umem status`, `umem context`, and safe write commands |
| **Agent Skills + CLI agents** | Tier 2 | Official UMEM Agent Skill installed natively, manually, or through an optional bridge such as `npx skills` |
| **Manually connected MCP hosts** | Tier 3 | User-configured MCP server without a maintained UMEM host workflow |
| **Prompt/export-only hosts** | Outside the support matrix | `manual-context.md` or copy/paste prompt as a best-effort fallback |

#### Runtime Integration Acceptance Criteria:

| Surface | MVP Support Target | Acceptance Criteria |
| --- | --- | --- |
| Python runtime | Python 3.12+ | `universal-memory --version` runs successfully in a clean Python 3.12 environment. |
| Package install | PyPI and `uvx` | Installation via `pip install universal-memory` and execution via `uvx universal-memory --help` documented and verified. |
| Tier 1 Hosts | Release-selected native/managed integrations | Host-specific setup, protected native mutations, documentation, limitations, and repeatable context-read validation. |
| Tier 2 Agents | Portable instruction-plus-CLI contract | Instruction presence, executable UMEM CLI, at least one successful context read, and clear host-specific limitation language. |
| Tier 3 MCP | Manually connected/unprogrammed MCP hosts | MCP server and tool availability check only, with no behavioral guarantee. |
| Portable fallback | Any tier or unsupported host | Generated `manual-context.md` or equivalent safe export for handoff, offline work, and debugging without changing support tier. |
| Offline mode | CLI, MCP, persistence, audit, and rollback | Read, write, audit, and rollback flow passes with network disabled after local installation. |

### Installation & Environment
- **Multi-Package Manager Support:** The system must be available via PyPI (`pip install universal-memory`) and support direct/isolated execution via `uvx` for Python 3.12+.
- **Local Persistence Layer:** Storage based on human-readable files, with structured metadata for automation, audit, and optional Git control.

### CLI Command Surface
- **Project Initialization:** Command to initialize universal-memory in a project directory and register local short-term memory.
- **Memory Read/Write:** Commands to write facts, list active facts, query context, and purge selected facts.
- **Status & Diagnostics:** Command to display database size, configured hosts, active rules, registered skills, and the latest health check result.
- **Host Setup:** Command to configure or verify integration with instruction files of supported agents.
- **Audit Review:** Command to list automatic changes made to instructions, facts, and skills.

### Communication & Interoperability
- **MCP Protocol Implementation:** The primary API must follow the **Model Context Protocol (MCP)** standard over JSON-RPC, allowing plug-and-play integration with Claude Desktop and other MCP hosts.
- **CLI/API Parity:** All functionality exposed by the memory server must be invocable via equivalent CLI commands for automation and manual use.

### MCP/API Surface
- **Context Retrieval:** MCP operation to retrieve the short-term memory summary, universal preferences, and active rules applicable to the current project.
- **Fact Capture:** MCP operation to propose or record new facts with scope, origin, and expiration classification.
- **Rule Proposal:** MCP operation to propose the promotion of recurring facts to persistent rules, requiring confirmation when applicable.
- **Skill Proposal:** MCP operation to register a latent skill opportunity and query the associated recurrence counter.
- **Health Check:** MCP operation to verify the availability of the local database, write permissions, server version, and configured hosts.

### Output Formats & Config Schema
- **Human-Readable Storage:** Persisted files must be readable and editable by humans.
- **Structured Metadata:** Facts, rules, latent skills, and audit events must contain minimum metadata of scope, origin, timestamp, and status.
- **CLI Output Modes:** Commands must support human-readable output by default and structured output for automation.
- **Config Schema:** Local settings must declare memory paths, enabled hosts, confirmation policy, and context limits.

### Usage Examples
- **New Project (Golden Path):** `umem init` detects relevant workspace agents, recommends a safe project-scoped connection plan, asks for one combined confirmation, connects through the correct native or portable path, validates context access, and ends with a concise readiness message.
- **Natural Usage:** After setup, the user talks to the agent normally; `AGENTS.md` or the official UMEM Agent Skill activates context loading without requiring the user to say "use Universal Memory."
- **Agent Skill Distribution:** When Node.js is available and a portable skill path is useful, `umem init` may invoke `npx skills` behind the connection experience with anonymous installer telemetry disabled. The command and external mutation boundary appear in details/logs, not as required user knowledge.
- **Additional Agent:** `umem connect` detects or lets the user select another agent, connects it without recreating project memory, and validates the chosen channel.
- **New Project (Non-interactive):** `umem init --runtime claude-code --runtime opencode --format json` registers project memory and configures explicit runtimes without interaction.
- **Portable Context Export:** `umem context export --manual --output manual-context.md` creates a safe context package for explicit handoff, offline/debug workflows, and hosts outside the support matrix without changing their tier.
- **Save Fact:** `umem remember --scope project "Prioritize TDD for authentication endpoints"` writes a local fact and returns the identifier, scope, and origin.
- **Query Context:** `umem context --format json` returns a memory summary applicable to the current directory, including project facts, universal preferences, and active rules.
- **New Rule:** `umem rules propose --from-recurrence` lists recurring candidate preferences for promotion and requires an explicit response: `yes`, `always`, or `no`.
- **New Host:** `umem host setup --host <host-id>` detects the supported instruction file, proposes the change, creates a snapshot, and executes a context-reading health check.
- **MCP Context Retrieval:** An MCP host invokes the context retrieval operation and receives a structured response with `project_summary`, `universal_preferences`, `active_rules`, and `audit_reference`.

### Migration & Onboarding
- **Existing Instructions:** Onboarding must detect existing instruction files and propose modifications without overwriting manual content without confirmation.
- **Manual Memory Workflows:** Onboarding must allow registering initial memories from user-approved local notes.
- **Rollback Path:** Every automatic change to instruction files must have a documented and auditable rollback path.
- **Post-MVP Portability:** Complete import/export of memory bases remains out of scope for the MVP, but the data model must avoid decisions that prevent this future capability.

### Backup & Recovery
- **Snapshot Before Mutation:** Every automatic change to memories, rules, skills, or instruction files must create a local snapshot before writing.
- **Rollback by Scope:** The user must be able to roll back the last change by scope: project, universal memory, rule, skill, or instruction file.
- **Backup Inspection:** The user must be able to list available snapshots, view the origin of the change, timestamp, affected scope, and responsible command/action.
- **Retention Policy:** The MVP must maintain a minimum local retention policy that protects against accidental loss without requiring external synchronization.
- **Failure Behavior:** If the snapshot fails, the automatic change must not proceed.

### Skill Creation Engine (Agent Skills Standard)
- **Skill Standard:** The system must adopt the **Agent Skills** standard (as per agentskills.io), using the folder structure with `SKILL.md` (instructions), `scripts/` (executable code), and `references/` (context).
- **Proactive Generation Flow:**
  1. **Detection:** The agent identifies when a methodology or procedural flow is being explained.
  2. **Context Interpolation:** The agent queries the memory (short and long-term) to consolidate instructions related to the topic.
  3. **Proposal:** The agent asks the user if they wish to create a formal Skill to encapsulate this knowledge.
  4. **Approval:** If approved, the system generates the folder structure and the `SKILL.md` file following the standard.
- **Latent Skill Tracking:** If the user is "in a hurry," the agent must record a summarized memory fact with a recurrence counter. When the pattern repeats *N* times, the system re-proposes the creation of the Skill based on the accumulated history.
- **Skill Registry:** Interface for the developer to list, test, and version the skills learned by the system.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy
**MVP Approach:** Focused on immediately resolving the "repetition tax" through local persistence, an MCP interface, and a passive behavioral adaptation engine. The goal is to validate the value of "invisibility" and token savings in DevEx workflows.

### MVP Feature Set (Phase 1)
**Core User Journeys Supported:**
- Access to Short-Term Memory for immediate context injection in new sessions.
- Adaptation by Recurrence: Transforming latent facts into rules in `AGENTS.md` (via user approval).
- Proactive Skill Creation: Detecting and encapsulating methodologies into the `Agent Skills` standard.

**Must-Have Capabilities:**
- MCP Server (JSON-RPC) for native integration.
- CLI for memory management and manual injection.
- Portable Context Export for explicit agent handoff, offline/debug workflows, and best-effort unsupported-host usage, producing `manual-context.md` or equivalent safe copy/paste output.
- Local human-readable persistence engine compatible with structured metadata.
- Security guardrails for Secrets and ENVs.
- Rule confirmation mechanism (Yes/Always/No).
- Host configuration flow for at least two supported agents/tools.
- Zero-flag `umem init` agent detection and connection flow with safe defaults, progressive disclosure, and at most one confirmation for an unambiguous project-scoped plan.
- `umem connect` flow for adding agents after initialization without recreating project memory.
- Local snapshots and rollback for automatic changes.

### Post-MVP Features
**Phase 2 (Growth):**
- **Multi-Machine Sync:** Synchronization via Git or a centralized repository.
- **Cloud Gateway:** Enable memory usage in web interfaces (ChatGPT, Gemini.com) via cloud storage service.
- **Memory Import/Export:** Complete memory base import/export for manual migration, external backup, and portability between environments.
- **Session Sharing:** Sharing of specific contexts between teams.

**Phase 3 (Vision):**
- **Autonomous Optimization:** AI that suggests proactive workflow improvements before the user asks.
- **Native IDE Integration:** Passive context capture directly from VS Code/JetBrains without explicit commands.

### Risk Mitigation Strategy
- **Technical Risks:** Asynchronous context injection to avoid performance degradation; rigid separation between memories to avoid token buffer pollution.
- **Market Risks:** Full focus on the open MCP protocol to ensure immediate interoperability and prevent ecosystem lock-in.
- **Resource Risks:** 100% local start to simplify infrastructure and focus on the quality of the adaptation engine.

## Functional Requirements

### 1. Core Memory Management
- **FR1:** The system must persist facts and user preferences in human-readable local storage compatible with structured metadata.
- **FR2:** The system must logically differentiate between Short-Term Memory (repository-specific) and Long-Term Memory (global).
- **FR3:** The system must retrieve context through local search modes defined by the architecture, with the default mode selection based on a benchmark of latency, result quality, operational cost, and offline operation.
- **FR4:** The user must be able to view and manually edit the persistence files directly in the filesystem.
- **FR5:** The system must allow selective purging (deletion) of specific facts or complete memory databases.
- **FR6:** The system must execute "Context Hygiene" routines to archive or remove obsolete short-term facts after task completion.

### 2. Onboarding & Setup
- **FR7:** During initial setup, the system must internally distinguish release-selected Tier 1 Native Hosts, Tier 2 Directed CLI Agents, and advanced Tier 3 Unmanaged MCP guidance without requiring the user to choose a tier or requiring one adapter entry per portable Tier 2 agent.
- **FR8:** The system must configure Tier 1 native targets through protected UMEM mutations and configure Tier 2 through portable `AGENTS.md` or Agent Skill instructions plus CLI validation, while presenting detected agents and connection outcomes in the primary human experience and reporting technical tiers, externally delegated actions, and manual steps through progressive details and structured output.
- **FR9:** The user must be able to initialize `universal-memory` in a new project/directory via CLI command (e.g., `umem init`).

### 3. Command Line Interface (CLI)
- **FR10:** The user must be able to query the memory status (size, active rules, available skills) via CLI.
- **FR11:** Every capability exposed by the API/MCP must have an equivalent CLI command for manual usage.

### 4. Model Context Protocol (MCP) Interface
- **FR12:** The system must expose its capabilities through a native MCP server running over JSON-RPC.
- **FR13:** The system must allow external agents (e.g., Claude Desktop) to read the updated memory context.
- **FR14:** The system must allow external agents to record new facts and propose rules in memory via MCP commands.

### 5. Auto-Adaptation & Synchronization
- **FR15:** The system must dynamically update the instructions contained in the agents' files (`AGENTS.md`, `CLAUDE.md`) as new rules and facts are consolidated in memory.
- **FR16:** The system must make the Short-Term Memory summary available in the initial context of the agents and expose, via status or audit, evidence of the last read, summary origin, and injection failures when they occur.
- **FR17:** The system must ensure that context injection respects size limits (summarization) so as not to cause token overflow in the LLM.

### 6. Skill Creation Engine (Agent Skills Standard)
- **FR18:** The system must track and count "Latent Skills" (recurring user instructions/methodologies).
- **FR19:** The system must request explicit approval (Yes/Always/No) upon reaching the recurrence trigger to create a new Skill.
- **FR20:** The system must generate a canonical Agent Skill structure with `SKILL.md`, optional `scripts/` and optional `references/`, then install or link it into native skill directories only when declared capability and the selected installation method allow it.
- **FR21:** The user must be able to list, activate, edit, disable and inspect both canonical skills and per-runtime installed skill targets through CLI and MCP-equivalent capabilities.

### 7. Security & Safety Guardrails
- **FR22:** The system must passively scan all received data to intercept API keys, credentials, or sensitive environment variables before writing.
- **FR23:** The system must prevent the persistence of detected secrets, notifying the user of the attempt.
- **FR24:** The system must maintain a local audit log of all changes made automatically to agent configurations and new skill creations.

### 8. Backup & Recovery Guardrails
- **FR25:** The system must create a local snapshot before any automatic change to memories, rules, skills, or instruction files.
- **FR26:** The system must block the automatic change when the preceding snapshot fails.
- **FR27:** The user must be able to list available snapshots and identify the timestamp, scope, origin, and action responsible for each snapshot.
- **FR28:** The user must be able to roll back the last automatic change by scope via CLI.

### 9. Language & Visual Identity Guardrails
- **FR29:** The product must use English as the default language for CLI prompts, help text, generated instructions, skill scaffolds and documentation templates, while allowing an explicit locale configuration for other supported languages such as Portuguese.
- **FR30:** The CLI onboarding experience should include a compact terminal brand element for `umem`, implemented as ANSI/ASCII splash art with a no-color fallback and disabled automatically for JSON/non-interactive output.

### 10. Update & Synchronization Guardrails
- **FR31:** The system must allow the user to trigger updates and synchronize local canonical skills from `.umem/skills/` or local package templates to declared native targets, portable Tier 2 targets, or explicitly delegated external installers without assuming every agent uses the same path.
- **FR32:** During synchronization, if a native target file has been modified manually and diverges from the canonical source, the system must interactively prompt the user with choices (Keep Local Target / Overwrite with Canonical) and display a warning that overwriting could break the custom agent workflow.
- **FR33:** The CLI must support checking for new library versions, migrating local configuration schema safely, and updating local benchmark datasets without losing user history or custom rules.
- **FR34:** The system must generate a safe `manual-context.md` export, or equivalent command output, containing current context and operating instructions for explicit handoff, offline/debug workflows, and best-effort hosts outside the support matrix without assigning or changing support tier.
- **FR35:** The system must package an official UMEM Agent Skill for the Tier 2 directed-CLI contract and may distribute it through an optional bridge such as `npx skills`, with explicit confirmation, dependency and telemetry disclosure, external-mutation boundaries, and a non-Node fallback.
- **FR36:** Running `umem init` without runtime flags must detect relevant workspace agents, recommend a safe project-scoped plan, require at most one confirmation when the plan is unambiguous, connect and validate the agents, and finish with outcome-oriented readiness guidance without requiring tier, path, MCP, `npx`, or copy/symlink knowledge.
- **FR37:** The system must provide `umem connect` to discover or add agents after initialization without recreating memory, using the same connection planning, confirmation, fallback, validation, and output contracts as onboarding.
- **FR38:** UMEM-initiated `npx skills` installation must disable anonymous `skills` telemetry, default to project scope, remain optional, and never prevent core initialization when Node.js, `npx`, network access, or an external agent mapping is unavailable.

## Non-Functional Requirements

### Performance
- **Retrieval Latency:** Local context queries must respond in less than 150ms at the 95th percentile on a test database with at least 1,000 facts, measured by an automated benchmark on a development machine.
- **Initialization Impact:** Memory reading and initial context assembly must not add more than 200ms at the 95th percentile to the start of a configured agent session, measured by a local integration test.
- **Retrieval Benchmark:** Before the final architecture, local textual search and semantic search must be compared on at least 30 representative queries, measuring latency, result quality on a 1-5 scale defined in the benchmark protocol, operational cost, and offline operation; the default strategy must be justified by the results.

### Security
- **Secret Detection:** The system must block 100% of secret patterns covered by the security test suite before persistence, measured by automated tests with positive and negative examples.
- **Access Audit:** Change logs and secret interception alerts must be queryable via CLI in fewer than 2 commands from the project directory, validated by an acceptance test.

### Reliability
- **Local Backup Strategy:** Prior to any automatic change in instruction files or fact databases, the system must create a recoverable local snapshot and maintain at least the 5 most recent versions per scope, validated by a rollback test.
- **Rollback:** The user must be able to roll back the last automatic change in less than 1 minute using the CLI, measured by an acceptance test on instruction files and the fact database.

### Integration
- **MCP Compliance:** The server must pass 100% of the compliance suite defined by the architecture for the Model Context Protocol, including at least health check, context retrieval, fact recording/proposal, rule proposal, and JSON-RPC error handling.
- **Alternative Storage Readiness:** The persistence logic must isolate read, write, list, and versioning operations behind a testable internal contract; switching the storage backend must not require changes to the rules engine, MCP, or CLI, validated by contract tests.
- **Host Compatibility:** The MVP must validate context reading on at least 2 supported hosts/agents, measured by a documented manual test or integration test when the host allows automation.

### Accessibility
- **Offline-First:** The CLI, persistence engine, and MCP server must perform reads, writes, queries, audits, and rollbacks with network disabled, validated by automated tests or a reproducible manual checklist.
