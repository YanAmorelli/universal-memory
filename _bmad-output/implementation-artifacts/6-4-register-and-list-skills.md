# Story 6.4: Register and List Skills

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

As a user managing learned capabilities,
I want to list and inspect the registered skills in the system,
so that I know which methodologies have been formalized, which are candidates, and which are available.

## Acceptance Criteria

1. **Given** skills registered in the local (project) or global base, **When** the user lists skills via use case or CLI, **Then** the system shows name, scope, status, relative path, creation date, last update, and origin, **And** visually differentiates (or in fields) active, disabled, and candidate skills, **And** with `--format json`, returns pure JSON with `skills[]` containing `name`, `scope`, `status`, `relative_path`, `created_at`, `updated_at`, `origin`, and `audit_reference`, **And** the output follows the standard defined in `_bmad-output/planning-artifacts/devex-interaction-spec.md`.
2. **Given** no skills registered in the local or global base, **When** the listing is executed, **Then** the system returns an explicit empty state, **And** proactively suggests the command or skill proposal workflow without automatically creating any files, **And** with `--format json`, returns an object containing `skills: []` and the `recommended_action` key with the action suggestion.
3. **Given** a specific skill, **When** the user requests its details, **Then** the system shows its metadata, relative path, usage triggers (`triggers`), and the audit reference, **And** does not unnecessarily load large files contained in the `references/` subdirectory unless explicitly requested by the user, **And** with `--format json`, returns an object containing the keys `name`, `scope`, `status`, `relative_path`, `triggers`, `audit_reference`, and `references_loaded: false` by default.

## Tasks / Subtasks

- [x] **Task 1: Write unit and integration tests (RED) for the Skills Listing and Details Use Case** (AC: 1, 2, 3)
  - [x] Create the `tests/application/skills/test_list_skills.py` file.
  - [x] Cover the empty listing and ensure that the result contains `skills: []` and `recommended_action`.
  - [x] Cover the listing of latent skills and active/disabled/candidate skills in both local and global scopes.
  - [x] Validate that the relative path (`relative_path`) is correctly resolved based on the skill's scope and status (e.g., `.umem/skills/<slug>/SKILL.md` for active local, or `None` for candidate).
  - [x] Cover the details use case of a specific skill, validating the populating of `triggers`, audit metadata, and the `references_loaded: False` flag.

- [x] **Task 2: Implement use cases `ListSkillsUseCase` and `GetSkillDetailUseCase`** (AC: 1, 2, 3)
  - [x] Create the `src/universal_memory/application/skills/list_skills.py` file.
  - [x] Define commands and results: `ListSkillsCommand`, `ListSkillsResult`, `GetSkillDetailCommand`, `GetSkillDetailResult`.
  - [x] Implement the logic in `ListSkillsUseCase`:
    - Read latent skills from the repository (`LatentSkillRepository.list()`).
    - For each latent skill, map to a DTO containing: `name`, `scope`, `status` (differentiating `proposed` as candidate, `active` as active, and `ignored` as disabled), `created_at`, `updated_at`, `origin`, `audit_reference`, and calculate the corresponding `relative_path` (using the slugification logic from the `propose_skill` or `generate_skill` use case to verify the existence of the physical `SKILL.md` file in `.umem/skills/<slug>/SKILL.md` or `skills/<slug>/SKILL.md`).
    - Return the list sorted by dates or priority.
  - [x] Implement the logic in `GetSkillDetailUseCase`:
    - Retrieve the corresponding latent skill by ID or name.
    - If it is active and physically materialized, read the triggers (`triggers`) directly from the YAML frontmatter of the `SKILL.md` or from the backup latent skill metadata.
    - Ensure that large files in `references/` are not read unless requested.
    - Return the DTO with the corresponding keys.
  - [x] Register and export the new use cases in the bootstrap and in `src/universal_memory/application/skills/__init__.py`.

- [x] **Task 3: Write unit and integration tests (RED) for the CLI (`umem skills list` and `umem skills detail`)** (AC: 1, 2, 3)
  - [x] Create the `tests/interfaces/cli/test_skills_list.py` file.
  - [x] Test terminal display for the default listing (showing a Rich table formatted with name, scope, colored status, relative path, and origin).
  - [x] Test empty listing display showing the warning state and proactive message suggesting `umem skills propose`.
  - [x] Test the listing with the `--format json` flag, validating that the envelope contains `ok: true`, `operation: "skills.list"`, and in the `data` field, the list of `skills` in the specified format.
  - [x] Test CLI details command (`umem skills detail <name_or_id>`) and its JSON output with the default envelope.

- [x] **Task 4: Implement the CLI commands `umem skills list` and `umem skills detail`** (AC: 1, 2, 3)
  - [x] Add the corresponding CLI commands in `src/universal_memory/interfaces/cli/init_command.py` under the `skills_app` subgroup.
  - [x] Format the listing output with high visual fidelity Rich tables, clearly showing the differentiation between active, candidate, and disabled skills.
  - [x] Format the display of skill details with a Rich layout presenting YAML frontmatter, relative paths, and triggers in a user-friendly way.
  - [x] Ensure compliance with `--format json` returning clean envelopes on success and mapped errors with hints.
  - [x] Register command routes and perform bindings in CLI bootstrapping.

- [x] **Task 5: Implement and expose corresponding MCP tools `list_skills` and `get_skill_detail`** (AC: 1, 2, 3)
  - [x] Add `@server.tool(name="list_skills")` and `@server.tool(name="get_skill_detail")` on the FastMCP server in `src/universal_memory/interfaces/mcp/server.py`.
  - [x] Ensure full semantic parity of returned JSON keys with the CLI (in compliance with `devex-interaction-spec.md`).
  - [x] Add test cases for the new MCP tools in `tests/interfaces/mcp/test_server.py`.

- [x] **Task 6: Final quality and compliance check** (AC: 1, 2, 3)
  - [x] Run the repository's full test suite: `uv run pytest`.
  - [x] Run style and format checks: `uv run ruff check .` and `uv run ruff format --check .`.
  - [x] Run static type checks: `uv run pyright`.

## Dev Notes

- **Scope of this story:** Exclusive focus on the reading and inspection flow of skills. Physical or status mutations are not part of this story (they are in the scope of stories 6.3 and 6.5).
- **Status differentiation:**
  - **Active:** Latent skill with `active` status. The `relative_path` points to `.umem/skills/<slug>/SKILL.md` (local) or `skills/<slug>/SKILL.md` (global).
  - **Disabled/Ignored:** Latent skill with `ignored` status.
  - **Candidate:** Latent skill with `proposed` status. The `relative_path` is `None` because the markdown file scaffold has not been created yet.
- **Path Resolution:** Always return paths relative to the project to maintain compliance with environmental rules and avoid exposing absolute paths of the host operating system.
- **Audit reference:** In the skill listing or details, also return the `audit_reference` related to the last mutation/creation in the latent skills repository.

### Project Structure Notes

- The use case must reside in `src/universal_memory/application/skills/list_skills.py`.
- The registration of CLI commands must be integrated into `src/universal_memory/interfaces/cli/init_command.py`.
- MCP integration must be in `src/universal_memory/interfaces/mcp/server.py`.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR21) - [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)
- `_bmad-output/planning-artifacts/architecture.md` (Skill Engine, CLI to MCP Parity Matrix) - [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (Output Contract, Command Contracts: skills list/detail) - [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- `src/universal_memory/domain/entities/latent_skill.py` - [latent_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/entities/latent_skill.py)
- `src/universal_memory/application/skills/generate_skill.py` - [generate_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/skills/generate_skill.py)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- 2026-05-29: Created story from the bmad create-story flow for epic-6 story-4 (Register and List Skills).
- 2026-05-29: RED application: `uv run pytest tests/application/skills/test_list_skills.py` failed due to missing new exported contracts.
- 2026-05-29: GREEN application: `uv run pytest tests/application/skills/test_list_skills.py` passed with 3 tests.
- 2026-05-29: RED CLI: `uv run pytest tests/interfaces/cli/test_skills_list.py` failed due to missing list/detail handlers/commands.
- 2026-05-29: GREEN CLI: `uv run pytest tests/interfaces/cli/test_skills_list.py` passed with 4 tests.
- 2026-05-29: RED MCP: `uv run pytest tests/interfaces/mcp/test_server.py -k 'list_skills or get_skill_detail'` failed due to missing MCP handlers.
- 2026-05-29: GREEN MCP: `uv run pytest tests/interfaces/mcp/test_server.py -k 'list_skills or get_skill_detail'` passed with 2 tests.
- 2026-05-29: Focused validation: `uv run pytest tests/application/skills/test_list_skills.py tests/interfaces/cli/test_skills_list.py tests/interfaces/mcp/test_server.py` passed with 22 tests.
- 2026-05-29: Initial complete validation: `uv run pytest` failed in `tests/interfaces/mcp/test_compliance.py` due to out-of-date MCP inventory.
- 2026-05-29: Final validation: `uv run pytest` passed with 347 tests.
- 2026-05-29: Final validation: `uv run ruff check .`, `uv run ruff format --check .`, and `uv run pyright` passed.

### Completion Notes List

- Implemented `ListSkillsUseCase` and `GetSkillDetailUseCase` with DTOs/payloads for empty listing, normalized statuses (`active`, `candidate`, `disabled`), relative paths, audit/origin, and reading frontmatter triggers without loading `references/`.
- Added CLI commands `umem skills list` and `umem skills detail` with human output via Rich and pure JSON envelopes `skills.list`/`skills.detail`.
- Exposed MCP tools `list_skills` and `get_skill_detail`, with semantic contract aligned with the CLI and coverage in the MCP compliance test.
- All Acceptance Criteria were covered by application, CLI, and MCP tests.

### File List

- `src/universal_memory/application/skills/list_skills.py`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `src/universal_memory/bootstrap/mcp.py`
- `tests/application/skills/test_list_skills.py`
- `tests/interfaces/cli/test_skills_list.py`
- `tests/interfaces/mcp/test_server.py`
- `tests/interfaces/mcp/test_compliance.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/6-4-registrar-e-listar-skills.md`

### Change Log

- 2026-05-29: Implemented skill list/detail in use cases, CLI, and MCP; added test and compliance coverage; story marked as ready for review.

### Review Findings

- [x] [Review][Patch] Human output of `skills list` does not show `created_at` [src/universal_memory/interfaces/cli/init_command.py:2155]  
  The story requires that CLI listing shows name, scope, status, relative path, creation date, last update, and origin. `_format_human_skill_list()` renders only `Name`, `Scope`, `Status`, `Relative path`, `Origin`, and `Updated at`, without exposing the creation date.
- [x] [Review][Patch] Resolution of `relative_path` can point to wrong slug [src/universal_memory/application/skills/list_skills.py:159]  
  `skills list/detail` re-derives the path as `.../{_slug(skill.name)}/SKILL.md`, but `generate_skill` can materialize an alternative slug in case of collision (`foo-2`) or fallback hash (`skill-<hash>`). In these cases, listing starts returning a non-existent path and `skills detail` stops reading the actual `triggers` from the file.
- [x] [Review][Patch] `skills detail <name>` does not handle ambiguous names [src/universal_memory/application/skills/list_skills.py:133]  
  `_find_skill()` returns the first match by `name.casefold()` without disambiguating by scope or occurrence count. If there are two skills with the same name, the CLI/MCP may silently display the wrong skill instead of requiring an ID or reporting ambiguity.
- [x] [Review][Patch] Manual frontmatter parser loses valid `triggers` [src/universal_memory/application/skills/list_skills.py:176]  
  `_read_frontmatter_triggers()` depends on `---\n` and the literal prefix `"  - "`, so it fails with BOM, `CRLF`, inline YAML lists, or escaped scalars generated by the project itself. The effect is a silent fallback to metadata or skill name, producing incorrect details without an explicit error.
