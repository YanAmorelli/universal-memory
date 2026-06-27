# Research: Skill Authoring Flow

## Decision: Make Native Runtime Sync Explicit

**Decision**: Change new canonical skill creation to canonical-only by default, with explicit sync available through `--sync`, publish-with-sync, or `skills sync`.

**Rationale**: The core product issue is premature distribution of incomplete skills. The current `CreateSkillUseCase` already accepts `targets=[]`, so the implementation can make the safer default small while preserving the current behavior through an explicit option.

**Alternatives considered**: Keep create-and-sync as default and add warnings; this still allows accidental runtime writes. Remove create-and-sync entirely; this breaks efficient one-step workflows.

## Decision: Represent Drafts With Existing Skill Storage Concepts

**Decision**: Store drafts as skill records with draft status and draft paths, then publish by validating, moving content into canonical skill location, and activating the record.

**Rationale**: `AgentSkillStatus` already includes `draft`, and reusing the repository, audit, and safe-write conventions avoids a parallel persistence system. Drafts remain excluded from active canonical list/detail unless explicitly requested.

**Alternatives considered**: Use loose files with no registry entry; this makes drafts hard to list and recover. Create a separate draft repository; this adds storage duplication with little benefit.

## Decision: Add Adopt As User-Facing Workflow

**Decision**: Add `skills adopt` for existing local skill folders, and keep `skills import` compatible as the lower-level copy/adopt operation.

**Rationale**: The user mental model is "UMEM should adopt this directory." A dedicated command can detect `.umem/skills/<slug>` in-place adoption, avoid suffixed duplicates, and emit clearer conflict guidance without breaking existing import behavior.

**Alternatives considered**: Rename import to adopt; this breaks existing docs and automation. Only improve import messages; this leaves the discoverability problem unresolved.

## Decision: Add Dedicated Canonical Maintenance Use Cases

**Decision**: Add focused use cases for canonical update, slug rename, validation, cleanup, and repair instead of making `UpdateSkillUseCase` handle every lifecycle path.

**Rationale**: Existing `UpdateSkillUseCase` is latent/generated-skill oriented. Canonical maintenance touches active skill records, canonical file trees, native target manifests, and summary output; focused use cases keep rollback and tests easier to reason about.

**Alternatives considered**: Extend `UpdateSkillUseCase` with broad conditional behavior; this increases ambiguity and preserves confusing command semantics. Require manual edits and sync; this does not solve the feature.

## Decision: Validate Skill Content Before Publishing Or Adopting

**Decision**: Introduce a shared validation use case that can inspect draft paths, canonical paths, and arbitrary local skill paths.

**Rationale**: Validation must be consistent across draft publish, adopt, canonical update, and explicit validate commands. The current parser checks frontmatter basics, but this feature needs user-facing checks for placeholders, local relative links, unsafe paths, and risky command patterns.

**Alternatives considered**: Duplicate validation in each command; this risks divergent behavior. Validate only frontmatter; this misses the operational quality issues named in the feature.

## Decision: Use Managed Manifests For Cleanup Safety

**Decision**: Cleanup and repair remove only paths UMEM can prove were managed through native target manifests or recorded installations, with dry-run as the primary interactive mode.

**Rationale**: Runtime directories can contain user-authored files. The safest default is managed-only removal with an explicit affected-path report.

**Alternatives considered**: Remove matching slug directories wholesale; this risks deleting user work. Only print manual instructions; this does not solve accidental-target cleanup.

## Decision: Add Summary Output Without Weakening JSON

**Decision**: Add `--format summary` for noisy skill lifecycle operations while preserving full JSON payloads.

**Rationale**: Automation needs complete audit and hash data; humans need concise status. The existing output path can treat summary as a specialized human renderer for skill commands.

**Alternatives considered**: Make human output shorter globally; this may remove useful detail from existing commands. Add separate `--quiet`; that does not provide affected paths and warnings.

## Decision: Warn On Git Ignore And Tracked Runtime Targets

**Decision**: Sync and publish-with-sync perform best-effort repository checks for affected runtime roots and report unignored or tracked target paths.

**Rationale**: The reported issue came from discovering generated runtime directories through git status. A warning before or during sync helps users decide whether to update ignore rules.

**Alternatives considered**: Update `.gitignore` automatically; this is too intrusive. Ignore repository status entirely; this preserves the current surprise.
