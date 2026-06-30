# Feature Specification: Shared Project Root

**Feature Branch**: `spec/shared-project-root`

**Created**: 2026-06-27

**Status**: Draft

**Input**: User description: "Criar uma feature para separar memórias e skills de projeto em uma pasta sem ponto, commitável, preservando `.umem` para estado operacional e mantendo compatibilidade com projetos existentes. A skill `use-universal-memory` é operacional e não deve ser commitada por padrão em projetos de usuários, salvo decisão explícita do repo."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Share Curated Project Memory (Priority: P1)

As a repository owner, I want project-level memories and user-facing skills to live in a visible shared project root so agents and teammates can review and commit them intentionally.

**Why this priority**: The current hidden project storage makes valuable shared context easy to ignore accidentally, which reduces agent continuity across clones and collaborators.

**Independent Test**: Initialize or migrate a project into the shared layout, create a project memory and a user-facing project skill, then confirm the shared files are visible in normal repository review while operational files remain local.

**Acceptance Scenarios**:

1. **Given** a new project using the shared layout, **When** a user records a project memory, **Then** the memory is written to the visible shared project root and appears as reviewable repository content.
2. **Given** a new project using the shared layout, **When** a user creates or publishes a user-facing project skill, **Then** the canonical skill appears under the visible shared project root and can be committed intentionally.
3. **Given** a project using the shared layout, **When** operational events, snapshots, locks, summaries, or drafts are created, **Then** they remain in local operational storage and are not presented as shared repository content.

---

### User Story 2 - Migrate Without Breaking Existing Projects (Priority: P2)

As an existing Universal Memory user, I want to adopt the shared layout without breaking current commands, active memories, or canonical skills.

**Why this priority**: Existing projects rely on `.umem` paths today, so a layout change must be opt-in and reversible enough to avoid disrupting established agent workflows.

**Independent Test**: Start with a project that has existing `.umem` project memories and skills, run the migration flow, and confirm the same user-facing data is available through normal commands with no data loss.

**Acceptance Scenarios**:

1. **Given** an existing project with project memories under the legacy layout, **When** the user runs the shared-layout migration, **Then** curated project memories are moved or copied into the visible shared root and remain available through existing memory commands.
2. **Given** an existing project with canonical project skills under the legacy layout, **When** the user runs the shared-layout migration, **Then** user-facing canonical skills are moved or copied into the visible shared root and remain available through existing skill commands.
3. **Given** an existing project that has not opted into the shared layout, **When** users run existing commands, **Then** behavior remains compatible with the legacy layout.

---

### User Story 3 - Keep Operational Skills Private By Default (Priority: P3)

As a repository maintainer, I want operational skills such as `use-universal-memory` to stay local by default unless my repository explicitly chooses to publish or commit them.

**Why this priority**: Operational bootstrap guidance is useful for local agent behavior but can be noise or policy leakage in repositories that do not intend to distribute that guidance.

**Independent Test**: Initialize a shared-layout project and confirm operational UMEM guidance is available to agents locally but is not automatically categorized as user-facing shared content.

**Acceptance Scenarios**:

1. **Given** a shared-layout project with default UMEM bootstrap guidance, **When** the user reviews shared project content, **Then** operational guide skills are not included by default.
2. **Given** a repository that wants to commit an operational guide skill, **When** the maintainer explicitly marks it as shared, **Then** it becomes reviewable project content and the decision is visible in project metadata.

---

### User Story 4 - Verify Layout Health With Doctor (Priority: P4)

As a repository maintainer or agent, I want the project health check to verify the shared layout so I can detect hidden shared content, tracked operational state, migration conflicts, and unsafe defaults before committing or continuing work.

**Why this priority**: The shared layout reduces ambiguity only if users can quickly validate that repository visibility, migration state, and operational privacy are correct.

**Independent Test**: Run the project health check against healthy, legacy, partially migrated, and misconfigured projects, then confirm it reports clear pass, warning, or failure statuses with actionable next steps.

**Acceptance Scenarios**:

1. **Given** a healthy shared-layout project, **When** the user runs the project health check, **Then** it confirms shared memory, shared skills, operational state, and repository visibility are configured correctly.
2. **Given** shared project content hidden by repository ignore rules, **When** the user runs the project health check, **Then** it warns that collaborators will not receive that content and suggests the appropriate visibility fix.
3. **Given** operational `.umem` state tracked by the repository, **When** the user runs the project health check, **Then** it warns that local operational state is exposed and suggests keeping it private.
4. **Given** both legacy and shared roots contain overlapping project memories or skills, **When** the user runs the project health check, **Then** it reports the conflict and tells the user which layout currently takes precedence.

---

### Edge Cases

- A project has both legacy and shared roots with the same memory or skill records.
- A shared root exists but is empty while legacy `.umem` contains project data.
- A repository ignores the shared root in its repository ignore rules.
- A repository tracks operational `.umem` files that should remain local.
- A project health check runs in a repository without Git metadata.
- A project health check runs before the user has chosen the shared layout.
- A project has global memories or global skills; these must not be moved into project commit-friendly content.
- A migration is interrupted after some files are moved or copied.
- A canonical skill is internal to the repository workflow rather than user-facing project knowledge.
- A user wants a private project memory that should not be committed even though the project uses the shared layout.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST support a visible shared project root for curated project-level memories and user-facing project skills.
- **FR-002**: The system MUST keep operational project state separate from shared project content.
- **FR-003**: The system MUST preserve compatibility for existing projects that continue using the legacy hidden layout.
- **FR-004**: Users MUST be able to opt a project into the shared layout without changing the meaning of existing memory and skill commands.
- **FR-005**: Users MUST be able to migrate curated project memories from the legacy layout to the shared layout.
- **FR-006**: Users MUST be able to migrate user-facing canonical project skills from the legacy layout to the shared layout.
- **FR-007**: The system MUST NOT migrate global memories or global skills into project repository content.
- **FR-008**: The system MUST NOT classify operational skills such as `use-universal-memory` as shared commit-worthy content by default.
- **FR-009**: Users MUST be able to explicitly mark an operational skill as shared when repository policy requires committing it.
- **FR-010**: The system MUST warn when project shared content is hidden by repository ignore rules.
- **FR-011**: The system MUST warn when operational project state is tracked as repository content.
- **FR-012**: Migration output MUST show which content was shared, which remained operational, which was skipped, and what review steps remain.
- **FR-013**: Migration MUST be safe to re-run without duplicating memories, duplicating skill registrations, or changing already migrated shared content unexpectedly.
- **FR-014**: When both legacy and shared content exist, the system MUST use a deterministic precedence rule and report potential conflicts.
- **FR-015**: Users MUST be able to keep specific project memories or project skills private even when the project uses a shared root.
- **FR-016**: Agent-facing guidance MUST explain when to use the shared root, when to keep content operational, and when to ask before publishing repository context.
- **FR-017**: The project health check MUST verify whether the active layout is legacy, shared, or partially migrated.
- **FR-018**: The project health check MUST verify that shared project memories and user-facing project skills are not hidden from normal repository review.
- **FR-019**: The project health check MUST verify that operational project state remains local and is not tracked as repository content.
- **FR-020**: The project health check MUST report overlapping legacy and shared memories or skills with the active precedence rule and a recommended resolution.
- **FR-021**: The project health check MUST produce actionable status output that distinguishes healthy checks, warnings, and failures.

### Key Entities

- **Project Shared Root**: Visible repository location for curated project memories, repository rules, and user-facing project skills intended for team review.
- **Project Operational Root**: Hidden local location for audit records, snapshots, locks, temporary files, summaries, drafts, and runtime-only guidance.
- **Curated Project Memory**: A project-scoped fact or rule that is stable enough to be shared across agents and collaborators.
- **Private Project Memory**: A project-scoped fact or rule that remains local even when the project uses a shared root.
- **User-Facing Project Skill**: A canonical skill intended to be shared with future agents and collaborators working in the repository.
- **Operational Skill**: A skill used for local agent bootstrap or internal workflow operation that is not shared by default.
- **Layout Migration Report**: User-facing summary of moved, copied, skipped, conflicting, and still-local content.
- **Layout Health Check**: User-facing diagnostic result that verifies layout selection, repository visibility, operational privacy, and migration conflicts.
- **Repository Visibility Policy**: The project's decision about which UMEM paths should be committed, ignored, or explicitly reviewed.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In a new shared-layout project, a user can create a project memory and identify the reviewable shared file in under 2 minutes.
- **SC-002**: In a new shared-layout project, a user can create a user-facing project skill and identify the reviewable shared skill path in under 3 minutes.
- **SC-003**: Existing projects using the legacy layout continue to pass all existing memory and skill workflows without migration.
- **SC-004**: Migration of a populated legacy project reports every curated memory and user-facing skill as migrated, skipped, private, or conflicting.
- **SC-005**: Re-running migration on an already migrated project results in no duplicate memories or duplicate canonical skill registrations.
- **SC-006**: At least 95% of repository visibility diagnostics produce an actionable next step that tells users whether to commit, ignore, migrate, or keep content private.
- **SC-007**: No global memories or global skills appear in project shared-root migration results.
- **SC-008**: Default shared-layout initialization keeps operational guide skills out of shared repository content unless explicitly marked as shared.
- **SC-009**: In under 30 seconds, a user can run a project health check and understand whether the project is healthy, needs migration, has hidden shared content, or exposes operational state.
- **SC-010**: For all detected layout conflicts, the project health check identifies the affected content category and gives at least one safe next step.

## Assumptions

- The visible shared project root will be used only for project-scoped, curated repository knowledge.
- The hidden operational root remains necessary for local audit, rollback, runtime, and temporary state.
- Existing `.umem` projects must remain valid until users explicitly choose a shared layout.
- Repository owners decide whether a specific project skill is user-facing or operational when the default classification is not enough.
- Private project memories and private project skills remain possible even in repositories that otherwise share curated project context.
- Global memory and global skills remain outside repository commit flows.
