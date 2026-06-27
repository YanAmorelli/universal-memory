# Feature Specification: Skill Authoring Flow

**Feature Branch**: `001-skill-authoring-flow`

**Created**: 2026-06-26

**Status**: Draft

**Input**: User description: "Improve UMEM skill authoring flow by separating draft authoring, canonical registration, and native runtime distribution"

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Author a Skill Without Runtime Side Effects (Priority: P1)

As an agent or maintainer creating a new skill, I want to draft and validate the skill before it is registered or distributed, so incomplete work does not appear in native runtime directories.

**Why this priority**: This removes the most disruptive failure mode: incomplete skills being copied into multiple host runtimes before the author is done.

**Independent Test**: Can be tested by creating a draft skill, checking that it is editable and validatable, and verifying that no runtime target is created until publish or sync is requested.

**Acceptance Scenarios**:

1. **Given** no existing skill with the requested slug, **When** a user creates a draft skill, **Then** the draft is created in an authoring location and is not listed as an active canonical skill.
2. **Given** a draft skill with required metadata and content, **When** the user publishes it without sync, **Then** the canonical registry is updated and no native runtime directories are written.
3. **Given** a published canonical skill, **When** the user explicitly requests sync, **Then** supported native runtime targets are updated from the canonical copy.

---

### User Story 2 - Adopt Existing Skill Work Safely (Priority: P1)

As an agent or maintainer who already created a skill folder manually, I want UMEM to detect and adopt that work, so I do not need to recreate it or accept an unwanted slug suffix.

**Why this priority**: Manual folder creation is a natural recovery path today, but UMEM currently treats the folder and registry as separate realities.

**Independent Test**: Can be tested by placing a valid unregistered skill directory under the project, listing skills, adopting the directory, and verifying the canonical record uses the requested slug.

**Acceptance Scenarios**:

1. **Given** an unregistered valid skill directory exists, **When** a user lists skills, **Then** the output identifies the unregistered directory and suggests adoption.
2. **Given** an unregistered valid skill directory exists, **When** a user adopts it with a slug, **Then** UMEM registers that directory without creating a suffixed duplicate.
3. **Given** a requested slug collides with an active skill, **When** a user attempts adoption, **Then** UMEM blocks the adoption and explains how to choose a safe slug or resolve the conflict.

---

### User Story 3 - Maintain Canonical Skills With Explicit Commands (Priority: P2)

As a maintainer of an existing canonical skill, I want clear commands for updating, validating, renaming, and cleaning up a skill, so normal maintenance does not require manual registry edits.

**Why this priority**: Once a skill is canonical, users need safe maintenance workflows that update metadata, paths, manifests, and runtime targets consistently.

**Independent Test**: Can be tested by updating a canonical skill file through the supported command, renaming its slug, validating it, and dry-running cleanup of obsolete targets.

**Acceptance Scenarios**:

1. **Given** an active canonical skill, **When** a user updates it through the canonical update flow, **Then** the canonical file and registry metadata are updated atomically.
2. **Given** an active canonical skill, **When** a user renames its slug, **Then** the canonical path, registry metadata, native target manifests, and detail/list output refer to the new slug.
3. **Given** accidental or obsolete managed runtime targets exist, **When** a user runs cleanup in dry-run mode, **Then** UMEM reports the targets that would be removed without deleting files.

---

### User Story 4 - Operate With Human-Friendly Feedback (Priority: P3)

As a user running skill lifecycle commands interactively, I want short summaries and actionable warnings, so I can understand what happened without reading large machine-oriented payloads.

**Why this priority**: The current machine output is useful for automation, but interactive authoring needs concise status and recovery guidance.

**Independent Test**: Can be tested by running create, adopt, sync, validate, and cleanup flows with human or summary output and verifying the output includes actions, paths, warnings, and next steps.

**Acceptance Scenarios**:

1. **Given** a skill command succeeds, **When** summary output is requested, **Then** the output shows canonical status, target sync status, drift status, warnings, and affected paths.
2. **Given** native runtime targets are not covered by ignore rules or are already tracked, **When** a sync or publish-with-sync operation is requested, **Then** UMEM warns before or during the operation with clear paths.
3. **Given** a user invokes the wrong update command for a canonical skill, **When** the command fails, **Then** the message points to the exact canonical file and the correct update or sync flow.

### Edge Cases

- A draft, canonical skill, or native target already exists with the requested slug.
- A manually created skill directory has valid frontmatter but is missing optional references or scripts.
- A manually created skill directory has invalid frontmatter, unsafe links, placeholders, or unsupported file paths.
- Native runtime targets contain unmanaged local edits or previously managed files no longer present in canonical content.
- Cleanup would remove a path that UMEM cannot prove it previously managed.
- A slug rename is requested while matching runtime target directories already exist.
- Summary output is requested by an automated caller that still needs a stable exit code.
- The repository ignores some runtime roots but tracks others.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: Users MUST be able to create a draft skill without registering it as an active canonical skill and without writing native runtime targets.
- **FR-002**: Users MUST be able to validate a draft skill before publishing it.
- **FR-003**: Users MUST be able to publish a valid draft as a canonical skill without syncing native runtime targets by default.
- **FR-004**: Users MUST be able to explicitly request native runtime sync during publish or as a separate operation.
- **FR-005**: Creating a canonical skill from scratch MUST default to canonical-only behavior unless sync is explicitly requested.
- **FR-006**: Existing one-step create-and-sync behavior MUST remain available through an explicit sync option.
- **FR-007**: Users MUST be able to adopt an existing local skill directory into the canonical registry without copying it to a suffixed duplicate when the requested slug is available.
- **FR-008**: Skill listing MUST surface valid unregistered skill directories and provide adoption guidance.
- **FR-009**: Adoption MUST fail with actionable guidance when the requested slug conflicts with an existing canonical skill.
- **FR-010**: Users MUST be able to rename the slug of an active canonical skill through a safe command.
- **FR-011**: Slug rename MUST update the canonical path, registry metadata, native target metadata, manifests, and user-facing list/detail output consistently.
- **FR-012**: Users MUST be able to update canonical skill content through a supported command or clearly documented canonical update flow.
- **FR-013**: When a user attempts an unsupported update path for a canonical skill, UMEM MUST explain the correct command or exact file-and-sync workflow.
- **FR-014**: Users MUST be able to validate canonical or local skill content for required metadata, triggers, placeholders, relative paths, broken local links, risky command patterns, and unsupported file layout.
- **FR-015**: Users MUST be able to dry-run cleanup for accidental or orphaned managed runtime targets.
- **FR-016**: Cleanup and repair operations MUST only remove files UMEM can prove are managed by UMEM unless the user explicitly chooses a broader unsafe mode.
- **FR-017**: Sync and publish-with-sync flows MUST warn when affected native runtime roots are not ignored or are already tracked by the repository.
- **FR-018**: Skill lifecycle commands with verbose machine data MUST offer a concise human summary format.
- **FR-019**: Machine-readable output MUST remain available for automation and include the full data needed for audit, snapshots, target status, and drift handling.
- **FR-020**: All user-facing paths in docs, command output, and generated guidance MUST be relative to the project when the path is inside the project.
- **FR-021**: Every new or changed skill lifecycle command MUST include concise help text that states what the command does, when to use it, key safety defaults, and the nearest alternative command.
- **FR-022**: Agent-facing skill guidance MUST include a command selection guide that lets an agent choose the correct draft, adopt, publish, update, sync, validate, cleanup, or repair flow without consulting command help for normal usage.
- **FR-023**: MCP tool descriptions MUST include purpose, when-to-use guidance, required inputs, and side-effect expectations for every new skill lifecycle tool.

### Key Entities

- **Draft Skill**: A work-in-progress skill that can be edited and validated before canonical registration.
- **Canonical Skill**: The UMEM-owned source of truth for a skill, with name, slug, description, scope, status, canonical path, content hash, and metadata.
- **Native Runtime Target**: A synchronized runtime-specific copy or rule directory generated from a canonical skill.
- **Skill Validation Report**: A user-facing report describing pass/fail checks, warnings, affected paths, and recommended fixes.
- **Managed Target Manifest**: The record that proves which native target files UMEM owns and can safely update or remove.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of new draft skill creations complete without writing native runtime targets.
- **SC-002**: 100% of canonical skill creations without an explicit sync option leave native runtime directories unchanged.
- **SC-003**: Users can adopt a valid existing skill directory with an available slug in one command and see it in skill detail/list output immediately afterward.
- **SC-004**: Users can identify and resolve invalid skill content before publish using validation output that names every blocking issue.
- **SC-005**: Users can preview cleanup of accidental managed runtime targets without file deletion in dry-run mode.
- **SC-006**: Summary output for common skill lifecycle commands fits within 25 lines for a single-skill operation while still showing affected paths and warnings.
- **SC-007**: Existing automation using machine-readable output continues to receive stable success envelopes and full audit data.
- **SC-008**: No supported safe maintenance flow requires manual editing of the skill registry.
- **SC-009**: A coding agent can complete the quickstart scenarios using only the updated UMEM skill guidance and command examples, without needing to inspect `--help`.

## Assumptions

- The feature preserves existing canonical and native skill concepts.
- Existing create-and-sync behavior remains available through an explicit option for users who prefer the one-step workflow.
- Drafts are local authoring artifacts and are not distributed to host runtimes until publish or explicit sync.
- Adoption is the user-facing term for registering existing skill work, while import may remain available for compatibility.
- Cleanup defaults to dry-run or managed-only behavior to prevent accidental deletion of user-authored files.
- Agent-facing workflow guidance improves the existing `use-universal-memory` skill and its lifecycle reference instead of creating a separate new project skill, unless a future requirement explicitly asks for a new skill.
- Existing sections in `.umem/skills/use-universal-memory/references/skills-lifecycle.md` and `.umem/skills/use-universal-memory/references/cli-mcp-parity.md` should be extended in place instead of duplicating lifecycle guidance in a new reference file.
