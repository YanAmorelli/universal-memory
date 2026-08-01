# Story 5.8: Evolve The Runtime Registry To Capability-Aware Support Tiers

Status: done

## Story

As a maintainer governing agent support,
I want support tier and integration channels modeled independently,
so that native investment remains selective while portable compatibility can scale broadly.

**Requirements covered:** FR7, FR8, FR15.

## Acceptance Criteria

1. **Capability-aware support tiers**

   **Given** the completed legacy runtime registry,
   **When** the support model is migrated,
   **Then** supported tier values are `tier_1_native_managed`, `tier_2_directed_cli`, and `tier_3_unmanaged_mcp`,
   **And** tier is modeled independently from management, instructions, CLI, skills, MCP, validation, evidence, and limitations.

2. **Evidence-backed Tier 1**

   **Given** a Tier 1 runtime entry,
   **When** the registry contract is validated,
   **Then** it is UMEM-managed and includes dated evidence for market relevance, demand, internal use, strategic value, validation feasibility, and maintenance capacity,
   **And** invalid or incomplete Tier 1 declarations are rejected.

3. **Generic Tier 2 portable profile**

   **Given** an agent that consumes `AGENTS.md`, the official UMEM Agent Skill, or both and can execute the UMEM CLI,
   **When** support is resolved,
   **Then** a generic Directed CLI profile represents the contract without requiring a host-specific adapter,
   **And** its validation level requires instruction presence, CLI access, and a context read.

4. **Generic Tier 3 unmanaged MCP profile**

   **Given** a manually configured MCP host without a programmed UMEM workflow,
   **When** support is represented,
   **Then** a generic Unmanaged MCP profile represents it without claiming host-specific behavior,
   **And** validation is limited to MCP availability.

5. **Safe compatibility and registry invariants**

   **Given** existing runtime IDs, paths, instruction targets, and native skill targets,
   **When** the registry evolves,
   **Then** those stable identifiers and target contracts remain available where safe,
   **And** invalid tier/capability combinations, duplicate profiles, and invalid shared-manifest ownership are rejected.

## Tasks / Subtasks

- [x] Add explicit enums/models for instruction channels, CLI access, skill support/installer, MCP mode, validation level, and Tier 1 selection evidence.
- [x] Migrate `RuntimeSupportTier` to the three capability-aware values.
- [x] Enrich maintained runtime adapters with independent capability declarations and Tier 1 evidence where applicable.
- [x] Add generic Directed CLI and Unmanaged MCP support profiles without creating fake host adapters.
- [x] Enforce cross-field invariants for each support tier and registry uniqueness.
- [x] Preserve existing runtime IDs, target paths, single-writer ownership, and safe config compatibility.
- [x] Add RED/GREEN domain tests for valid profiles, default registry declarations, evidence, invalid capability combinations, and compatibility.
- [x] Run focused tests, formatting/linting, and relevant regression tests.

### Review Follow-ups

- [x] [Review][High] Align Cursor/Antigravity instruction channels with their equivalent-rule surfaces without inventing Agent Skill support.
- [x] [Review][High] Gate native skill synchronization by declared skill capability and installer, not target presence alone.
- [x] [Review][Medium] Verify Story 5.9 integration keeps technical tier enums out of default human output.
- [x] [Review][Medium] Reject `.` and paths that normalize to an empty/current-directory detection signal.
- [x] [Review][Low] Allow an empty `known_limitations` list.
- [x] [Review][Low] Export `RuntimeSupportCapabilities` through the public entities API.
- [x] [Re-review][High] Reject Tier 2 declarations without a portable or explicitly valid equivalent-rule instruction contract.
- [x] [Re-review][High] Enforce coherent Agent Skill channel, support, and installer combinations.
- [x] [Re-review][Medium] Add direct negative regression tests for native import and orphan-scan capability gates.

## Dev Notes

- Sources of truth: `_bmad-output/implementation-artifacts/spec-agent-support-evolution-tiers-and-mcp-fallback.md`, `_bmad-output/planning-artifacts/architecture.md` section "Declarative Runtime Registry & Adapter Model", and `_bmad-output/planning-artifacts/epics.md` Story 5.8.
- Tier 2 compatibility is a portable contract and must not require one registry adapter per external agent.
- Tier 3 represents unmanaged MCP capability only. Portable export is not a tier.
- This story changes the domain registry contract only. Onboarding, external skill installation, and the official UMEM Agent Skill belong to later stories.

## Dev Agent Record

### Debug Log

- 2026-07-31: Added domain tests first. The focused test collection failed because the new capability enums did not exist, confirming RED.
- 2026-07-31: Implemented capability models, tier invariants, structured Tier 1 evidence, generic support profiles, and explicit detection signals separated from configuration targets.
- 2026-07-31: The first broader regression run found only the legacy interactive onboarding assertion for old `tier_1`/`tier_2` labels. That assertion belongs to Story 5.9 and was intentionally not edited here.
- 2026-07-31: Ruff, Pyright, 39 focused domain tests, and 150 relevant skills/setup/config regression tests passed.
- 2026-07-31: Code review reopened the story for six follow-ups. New RED tests exposed missing capability gating, current-directory detection paths, required placeholder limitations, and the missing public capability export.
- 2026-07-31: Separated named adapter instruction surfaces from canonical skill synchronization. Cursor and Antigravity now declare their real native-file instruction surface; the generic Directed CLI profile alone enforces `AGENTS.md` or Agent Skill portability.
- 2026-07-31: Added registry and consumer-level native skill gates, including import and orphan inspection paths. Ruff, Pyright, focused onboarding/CLI tests, and the full 784-test suite passed after the fixes.
- 2026-07-31: Re-review added RED coverage for empty Tier 2 instruction contracts and incoherent Agent Skill/support/installer combinations. Direct negative import and orphan-scan tests already passed against the consumer gates.
- 2026-07-31: Tier 2 now requires `AGENTS.md`, Agent Skill, or `native_file + equivalent_rules` with an explicit UMEM-native/manual installer. Agent Skill, portable, equivalent-rule, and NPX declarations are cross-validated semantically.
- 2026-07-31: Final re-review gates passed with Ruff, Pyright, diff-check, and 83 scoped domain/skill tests. The global gate was not used as the completion signal while Story 5.9 concurrently refactored its onboarding executor and temporarily exposed unrelated lint/import failures.

### Completion Notes

- Replaced the two legacy tier values with the three final machine-stable support tiers.
- Added independently modeled management, instruction, CLI, skill, installer, MCP, validation, evidence, limitation, and detection dimensions.
- Added structured and dated Tier 1 evidence for the maintained Claude Code, OpenCode, and Codex entries. Existing runtime IDs, paths, targets, and shared `AGENTS.md` ownership remain stable.
- Kept Cursor and Antigravity as named Tier 2 metadata while introducing a generic `directed_cli` profile that avoids one adapter per compatible agent.
- Added the generic `unmanaged_mcp` profile with capability-only validation and no behavioral promise.
- Added typed project/global path and executable detection signals so onboarding does not infer detection from mutation targets.
- Preserved `[runtimes]` and legacy `[hosts]` config behavior because no persisted support-tier value required migration.
- Native skill targets now require native/equivalent-rules support with the UMEM native installer, and all native synchronization consumers check that declared capability rather than target presence alone.
- Named Tier 2 adapters may describe their real instruction surface without falsely claiming Agent Skill support. The generic Directed CLI profile retains the portable instruction-plus-CLI invariant.
- Detection rejects current-directory paths, limitations may be empty, and `RuntimeSupportCapabilities` is part of the public domain API.
- Story 5.9 integration was verified: technical support tiers remain in structured output and are absent from the default human runtime selection.
- Re-review tightened Tier 2 eligibility without rejecting Cursor/Antigravity's explicit equivalent-rule contract, and added end-to-end negative coverage for import adoption and orphan discovery.

## File List

- `src/universal_memory/domain/entities/runtime.py`
- `src/universal_memory/domain/entities/__init__.py`
- `src/universal_memory/application/skills/native_skill_sync.py`
- `src/universal_memory/application/skills/import_skill.py`
- `tests/domain/test_host.py`
- `tests/application/skills/test_sync_skills.py`
- `tests/application/skills/test_import_skill.py`
- `tests/application/skills/test_cleanup_skill.py`
- `_bmad-output/implementation-artifacts/5-8-evolve-runtime-registry-to-capability-aware-support-tiers.md`

## Change Log

- 2026-07-31: Implemented capability-aware runtime support tiers, generic Directed CLI and Unmanaged MCP profiles, typed detection signals, Tier 1 evidence, validation invariants, and tests.
- 2026-07-31: Resolved code-review findings for instruction-surface semantics, native skill capability gates, progressive disclosure, path safety, optional limitations, and public API exports.
- 2026-07-31: Resolved re-review findings for Tier 2 instruction eligibility, channel/support/installer semantics, and direct import/orphan gate coverage.
- 2026-07-31: Independent final review approved the story with no remaining findings; 83 focused tests and the integrated 823-test suite passed.
