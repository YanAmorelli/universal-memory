# Story 6.5: Activating, Deactivating, and Editing Skills Safely

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user adjusting existing skills,
I want to activate, deactivate, and edit registered skills with guardrails,
so that I can control which capabilities are available in the system without losing the history of formalized methodologies.

## Acceptance Criteria

1. **Given** a skill with active status (`status: active`), **When** the user requests its deactivation, **Then** the skill status in the repository (`LatentSkillRepository`) changes to `ignored`, **And** the change generates an audit log entry (`AuditEventScope`) with the action `deactivate_skill` and the provided origin, **And** the corresponding physical files (such as `SKILL.md`) are **not** deleted from the filesystem to preserve history and allow reactivation.
2. **Given** a deactivated skill (`status: ignored`), **When** the user requests its activation, **Then** the skill status in the repository changes back to `active` if, and only if, the corresponding mandatory physical file `SKILL.md` still exists in the expected path, **And** the status transition generates an audit log entry with the action `activate_skill` and the provided origin, **And** if the `SKILL.md` file is missing or corrupted (invalid frontmatter), the system reports a clear error (`ValidationFailedError`) and keeps the original status unchanged.
3. **Given** an edit to a skill's metadata or content, **When** the change is applied, **Then** the system executes the write to disk in a transactional manner and creates a backup snapshot before writing using `SafeWriteUseCase`, **And** preemptively validates the new content against leakage of credentials or sensitive keys with the `SecretScannerPort`, **And** keeps the rollback history per scope available for the executed change.

## Tasks / Subtasks

- [x] **Task 1: Write unit and integration tests (RED) for the Activation, Deactivation, and Edition Use Cases** (AC: 1, 2, 3)
  - [x] Create the test file `tests/application/skills/test_update_skill.py`.
  - [x] Write test cases for deactivation: verify that the entity's status in the repository changes to `ignored`, ensure that the `SKILL.md` file was not physically or logically deleted, and verify that the audit log was recorded with the `deactivate_skill` action.
  - [x] Write test cases for successful activation: simulate a skill in `ignored` status, ensure that the corresponding physical `SKILL.md` file exists and is intact, and verify the transition to `active` with the `activate_skill` audit log.
  - [x] Write test cases for failed activation: simulate a skill in `ignored` status but with the `SKILL.md` file missing or with a corrupted frontmatter, validating that a `ValidationFailedError` is raised and ensuring that the status remained `ignored`.
  - [x] Write test cases for editing metadata and content: inject test doubles for `SafeWriteUseCase` and verify that snapshots are triggered preemptively, sensitive secrets are scanned and rejected with a `SecretDetectedError`, and rollback is operational in case of a failure during the process.

- [x] **Task 2: Implement use cases `ActivateSkillUseCase`, `DeactivateSkillUseCase`, and `UpdateSkillUseCase`** (AC: 1, 2, 3)
  - [x] Create the file `src/universal_memory/application/skills/update_skill.py`.
  - [x] Define the corresponding commands and results for each use case:
    - `ActivateSkillCommand`, `ActivateSkillResult`
    - `DeactivateSkillCommand`, `DeactivateSkillResult`
    - `UpdateSkillCommand`, `UpdateSkillResult` (fields to granularly edit metadata such as name, triggers, etc., or accept the complete raw markdown of the updated `SKILL.md` file).
  - [x] Implement `DeactivateSkillUseCase`:
    - Read the latent skill from the repository (`LatentSkillRepository.read`). If the status is not `active`, raise `ValidationFailedError`.
    - Update the status to `ignored` in the `LatentSkill` entity and call `repository.write`. (The repository will already handle the registry's default audit).
  - [x] Implement `ActivateSkillUseCase`:
    - Read the latent skill from the repository. If the status is not `ignored`, raise `ValidationFailedError`.
    - Resolve the expected physical path of the `SKILL.md` file (e.g., `.umem/skills/<slug>/SKILL.md` for local or `skills/<slug>/SKILL.md` for global).
    - Verify if the physical file exists in the filesystem. If it does not exist, raise an explanatory `ValidationFailedError` indicating the missing path.
    - If it exists, perform a quick check of the markdown frontmatter integrity to ensure it remains mapable to the entity. If it is corrupted or invalid, raise a `ValidationFailedError`.
    - Update the status of the entity to `active` and save it to the repository.
  - [x] Implement `UpdateSkillUseCase`:
    - Read the latent skill from the repository by ID.
    - If the call is to update granular metadata (such as changing triggers or description), rebuild the `LatentSkill` entity and regenerate the markdown content of the corresponding `SKILL.md` using the default template, saving it via `SafeWriteUseCase` (which creates snapshots and runs the scanner).
    - If the call is to save a complete raw markdown (direct file editing by the user), parse the YAML frontmatter of the new markdown to extract fields such as `name`, `description`, `triggers` and update the `LatentSkill` entity data.
    - Write the updated markdown content to `SKILL.md` using the `SafeWriteUseCase` corresponding to the skill scope.
    - Save the updated `LatentSkill` entity in the repository `LatentSkillRepository.write`.
    - Handle transactional errors: revert database writes (`latent_skills.jsonl`) if writing the `SKILL.md` to disk fails or vice-versa, maintaining a consistent state.
  - [x] Register and export the new use cases and DTOs in the CLI/MCP bootstrap file and in `src/universal_memory/application/skills/__init__.py`.

- [x] **Task 3: Final quality and compliance check** (AC: 1, 2, 3)
  - [x] Run the repository's complete test suite: `uv run pytest`.
  - [x] Run style and formatting checks: `uv run ruff check .` and `uv run ruff format --check .`.
  - [x] Run static type checking: `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Preserve the origin provided in activation and deactivation audit events [src/universal_memory/infrastructure/storage/local_latent_skill_repository.py:249]
- [x] [Review][Patch] Fix skill rename to keep the `SKILL.md` path consistent with the current slug [src/universal_memory/application/skills/update_skill.py:179]
- [x] [Review][Patch] Protect file rollback from masking the original failure or leaving a divergent state [src/universal_memory/application/skills/update_skill.py:194]
- [x] [Review][Patch] Synchronize removal or clearing of `triggers` when updating via raw markdown [src/universal_memory/application/skills/update_skill.py:224]
- [x] [Review][Patch] Accept valid `SKILL.md` with BOM or CRLF when validating frontmatter [src/universal_memory/application/skills/update_skill.py:294]

## Dev Notes

- **Separation of Layers (Clean Architecture)**:
  - Strictly respect the architectural boundary. All file verification and markdown frontmatter parsing logic must reside in the application layer (`application/skills/update_skill.py`). CLI/MCP adapters only interact with DTOs.
  - The CLI and MCP interfaces and delivery for these operations are not part of this story and should only be exposed in Story 6.6.
- **Snapshots and Safe Writes**:
  - Editing physical markdown content must obligatorily invoke the `SafeWriteUseCase` corresponding to the scope (`global` or `project`).
  - The `LatentSkillRepository` repository inherits the `safe_write_use_case` in its constructor, ensuring that updates to the latent skills database also generate local snapshots and automated audit logs.
- **Exception Handling**:
  - Raise `ValidationFailedError` for any invalid status transitions or missing physical skill file.
  - Raise `SecretDetectedError` if the passive scanner finds private keys or sensitive credentials in the markdown content being saved.

### Project Structure Notes

- The edit/toggle use case file must reside in `src/universal_memory/application/skills/update_skill.py`.
- Registration of the new use cases must be done in `src/universal_memory/application/skills/__init__.py`.
- Application unit/integration tests must reside in `tests/application/skills/test_update_skill.py`.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR21, FR22, FR23, FR24, FR25, FR26) - [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)
- `_bmad-output/planning-artifacts/architecture.md` (Skill Engine, CLI to MCP Parity Matrix) - [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md)
- `src/universal_memory/domain/entities/latent_skill.py` - [latent_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/entities/latent_skill.py)
- `src/universal_memory/application/skills/generate_skill.py` - [generate_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/skills/generate_skill.py)
- `src/universal_memory/application/skills/propose_skill.py` - [propose_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/skills/propose_skill.py)

## Dev Agent Record

### Agent Model Used

Codex GPT-5

### Debug Log References

- `uv run pytest tests/application/skills/test_update_skill.py` - 10 passed
- `uv run pytest` - 360 passed
- `uv run ruff check .` - passed
- `uv run ruff format --check .` - passed
- `uv run pyright` - 0 errors

### Completion Notes List

- Implemented `ActivateSkillUseCase`, `DeactivateSkillUseCase`, and `UpdateSkillUseCase` in `src/universal_memory/application/skills/update_skill.py`.
- Deactivation and activation validate status transitions and use specific auditing `deactivate_skill` and `activate_skill` in the local repository.
- Activation validates the existence and minimum frontmatter of `SKILL.md` before changing the latent skill's status.
- Granular and raw markdown editing writes `SKILL.md` via `SafeWriteUseCase`, triggers scanner/snapshot/auditing, and restores the previous file if the repository write fails.
- DTOs and use cases exported in `src/universal_memory/application/skills/__init__.py`; CLI/MCP bootstrap builds the new dependencies without exposing interface commands in this story.

### File List

- `_bmad-output/implementation-artifacts/6-5-ativar-desativar-e-editar-skills-com-seguran-a.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/application/skills/update_skill.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`
- `tests/application/skills/test_list_skills.py`
- `tests/application/skills/test_update_skill.py`

### Change Log

- 2026-05-29: Implemented use cases for activation, deactivation, and safe editing of skills; added tests and complete validations; story moved to review.
