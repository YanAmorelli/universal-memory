# Sprint Change Proposal - Agent Support Evolution

**Date:** 2026-06-12
**Revised:** 2026-07-31
**User:** Yan
**Review Mode:** Incremental
**Scope:** Moderate
**Source Spec:** `_bmad-output/implementation-artifacts/spec-agent-support-evolution-tiers-and-mcp-fallback.md`

## 1. Issue Summary

The existing planning artifacts conflate native host support, portable agent instructions, generic MCP availability, and manual context fallback. This creates an expensive native-adapter promise and places MCP in the wrong support tier.

The revised direction uses native support selectively while distributing UMEM broadly through portable instructions and the CLI:

- Tier 1 Native/Managed for hosts selected and maintained by UMEM after market and product analysis.
- Tier 2 Directed CLI for agents that consume `AGENTS.md` or the official UMEM Agent Skill and can execute the UMEM CLI.
- Tier 3 Unmanaged MCP for manually connected hosts without a programmed or validated UMEM integration.
- `manual-context.md` remains a portable handoff/fallback utility outside the tier definition.
- The open Agent Skills ecosystem, including optional `npx skills` distribution, provides broad reach without requiring a native adapter per agent.
- The primary experience is `umem init` with no mandatory runtime flags: detect agents, recommend a safe project-scoped plan, ask once, connect, validate, and report readiness.
- Tier labels, target paths, `npx`, copy/symlink mechanics, and MCP details remain available in details and JSON but stay out of the normal success path.
- `umem connect` adds an agent later without reinitializing project memory; `umem doctor` remains the recovery path.
- After setup, users work with agents normally and do not need to prompt them explicitly to use UMEM.

## 2. Confirmed Direction

| Decision | Confirmed outcome |
| --- | --- |
| Native support strategy | Small, maintained Tier 1 selected through release-time market and product analysis |
| Tier 1 quota | No fixed Top-5 requirement and no automatic promotion from external compatibility lists |
| Portable support | Tier 2 through directed instructions plus executable UMEM CLI |
| `AGENTS.md` | A qualifying Tier 2 instruction channel when the agent can also execute the CLI |
| Agent Skills | Official UMEM skill using the open format |
| `npx skills` | Optional external distribution bridge; not a core dependency or support authority |
| Primary onboarding | `umem init` without required flags, automatic detection, one recommended confirmation, connection, validation, and concise readiness summary |
| Infrastructure disclosure | Outcome-oriented by default; tiers, commands, paths, network, and mutation details available progressively |
| Installer privacy | Disable anonymous `skills` telemetry for UMEM-initiated external installation |
| Additional agents | `umem connect` discovers or adds agents after initialization |
| Natural use | Agent instructions activate UMEM; the user continues normal conversation |
| MCP fallback | Tier 3 only when manually forced/configured in an unprogrammed host |
| Manual export | Cross-tier and unsupported-host utility, not a support tier |
| Promotion | Evidence-backed decision considering market, demand, internal use, strategic value, validation, and maintenance |

## 3. Impact Analysis

### Epic Impact

**Epic 4: Interfaces and Parity**

- Keep CLI as the portable integration contract.
- Keep portable context export as an explicit parity exception and handoff utility.
- Document the difference between a managed MCP integration and Tier 3 Unmanaged MCP.

**Epic 5: Runtimes, Hosts, and Instruction Synchronization**

- Replace fixed host promotion and Generic MCP Tier 2 with capability-aware tiers.
- Allow a generic Tier 2 profile instead of requiring a registry adapter for every agent.
- Resolve onboarding internally across Native Hosts, Directed CLI Agents, and Unmanaged MCP guidance without making tier selection part of the golden path.
- Make tier grouping an internal/details concern and expose detected agents plus recommended connection outcomes in the primary onboarding.
- Add an idempotent `umem connect` use case and keep `umem doctor` as the single recovery entry point.
- Add market/maintenance evidence and explicit promotion/demotion rules for Tier 1.

**Epic 6: Skills**

- Preserve `.umem/skills/` as the canonical source.
- Add an official UMEM Agent Skill for the Tier 2 operating contract.
- Add optional `npx skills` command generation or confirmed execution with clear external-mutation boundaries.
- Add a compact `AGENTS.md` bootstrap plus a detailed official UMEM Agent Skill so normal prompts activate the workflow without user ceremony.
- Keep native skill installation conditional on capability rather than tier.

### Artifact Impact

**PRD:** revise the tier matrix, Tier 1 selection policy, Tier 2 portable contract, Tier 3 MCP limitation, usage examples, and functional requirements.

**Architecture:** separate tier from instruction, CLI, skill, MCP, validation, management, evidence, and limitations; add the optional Agent Skills distribution bridge.

**Epics:** keep completed Stories 5.1, 5.4, and 5.6 historically accurate; add Stories 4.7, 5.8, 5.9, 5.10, and 6.13 for portable export, registry migration, golden-path onboarding/validation, post-init agent connection, and official UMEM skill distribution.

**DevEx:** rename onboarding groups, disclose external installer behavior, and keep portable export independent from Tier 3.

## 4. Recommended Approach

### Selected Path

**Direct Adjustment.** No completed implementation needs rollback because the revised support evolution has not been implemented yet.

### Rationale

- Broad compatibility moves to a stable portable contract instead of a growing adapter list.
- Native engineering investment can follow evidence and maintenance capacity.
- `AGENTS.md` and Agent Skills provide complementary instruction surfaces.
- The UMEM CLI remains under product control and is testable across hosts.
- MCP availability is no longer mistaken for behavioral integration.
- Optional external distribution accelerates reach without adding Node.js to the UMEM core runtime.

### Effort Estimate

**Medium.** Planning changes are direct; implementation affects registry modeling, onboarding, the official UMEM skill, optional installer integration, validation, and documentation.

### Risk Level

**Medium.** Main risks are overclaiming Tier 2 host behavior, delegating unprotected mutations to an external installer, and treating an external catalog as authoritative. Mitigations are contract-level language, explicit confirmation, project-first installation, real CLI validation, and independent Tier 1 governance.

## 5. Detailed Change Proposals

### PRD Deltas

- Define Tier 1 Native/Managed, Tier 2 Directed CLI, and Tier 3 Unmanaged MCP.
- Replace the fixed Top-5 rule with release-time market and product analysis.
- Make portable instructions plus CLI the Tier 2 contract.
- Add the official UMEM Agent Skill and optional `npx skills` distribution path.
- Add the zero-configuration golden path, automatic agent detection, one combined confirmation, graceful fallback, and natural post-setup usage.
- Add `umem connect` for post-initialization discovery and connection.
- State that `AGENTS.md` consumption must be paired with executable CLI access.
- Keep `manual-context.md` as portable handoff/fallback without assigning a tier.

### Architecture Deltas

- Add `managed_by_umem`, `instruction_channels`, `cli_access`, `skill_support`, `skill_installer`, `mcp_mode`, `validation_level`, `selection_evidence`, and `limitations` independently from `support_tier`.
- Support a generic Tier 2 profile and named detection/documentation entries without native adapters.
- Define a subprocess boundary for optional `npx skills` integration.
- Disable anonymous `skills` telemetry for UMEM-initiated installation.
- Define agent detection and an idempotent connection-plan use case shared by `umem init` and `umem connect`.
- Require explicit user confirmation and disclosure before external installation.
- Validate instruction presence, CLI availability, and one context read for Tier 2.
- Limit Tier 3 validation to MCP capability.

### Epic Deltas

- Epic 4: retain portable context export as handoff/fallback and document unmanaged MCP limits.
- Epic 5: add follow-up stories for registry migration, golden-path validation/onboarding, `umem connect`, and promotion/demotion policy without reopening completed legacy stories implicitly.
- Epic 6: add a follow-up story for the official UMEM Agent Skill and optional multi-agent distribution bridge.

### DevEx Deltas

- `umem init` shows detected agents and recommended outcomes, not tier categories, in the default path.
- A safe unambiguous project plan uses one combined confirmation.
- Tier 2 output explains portable limitations only when relevant or requested, without making the user choose a tier.
- Unmanaged MCP appears as guidance or an explicit advanced path rather than a normal native selection.
- Optional `npx skills` execution shows agent, scope, command, method, network requirement, telemetry controls, and mutation ownership before confirmation.
- The primary prompt says that UMEM will make itself available to the agent; `npx` remains a details/log concern.
- Success ends with a short message equivalent to `You're ready. Work with your agents normally.`
- JSON output reports tier, channels, validation results, external actions, and pending manual steps.

## 6. Implementation Handoff

### Scope Classification

**Moderate.** The change replaces an unimplemented planning direction and does not require rollback of working product behavior.

### Recommended Sequence

1. Correct registry types and capability fields without claiming unimplemented hosts.
2. Implement the Tier 2 instruction-plus-CLI validation contract.
3. Package the official UMEM Agent Skill and compact `AGENTS.md` bootstrap.
4. Implement shared agent detection and connection planning for `umem init` and `umem connect`.
5. Add optional `npx skills` execution with disabled telemetry, progressive disclosure, and graceful fallback.
6. Implement the one-confirmation golden path, readiness summary, and structured details/JSON.
7. Add Tier 3 unmanaged MCP language and validation boundaries.
8. Update public support documentation after tests establish the final Tier 1 list.

### Success Criteria

- All artifacts use the same three tier definitions.
- No artifact requires a fixed number of Tier 1 hosts.
- No unimplemented host is presented as already completed or supported natively.
- Tier 2 is validated through instructions, CLI availability, and a real context read.
- `npx skills` expands distribution without becoming a mandatory dependency or native-support authority.
- `umem init` connects safely detected agents without mandatory flags or tier knowledge.
- A normal safe project setup requires at most one confirmation.
- Missing Node.js or `npx` never prevents core project initialization.
- `umem connect` adds another agent without recreating memory.
- Users can work naturally after setup without explicitly requesting UMEM usage.
- Tier 3 clearly communicates unmanaged MCP limitations.
- Portable context export remains available without determining tier.

## 7. Approval Status

Status: Approved and revised on 2026-07-31.

Next step: apply these deltas consistently to PRD, architecture, epics, DevEx, and affected implementation stories before implementation begins.
