## Deferred from: UMEM 0.4 multi-repository adoption (2026-07-08)

- Bug: legacy-to-shared skill migration can leave shadowed skill registry records in `.umem/memory/skills.jsonl` after copying the same skills into `umem/skills/skills.jsonl`. Facts are cleaned up after successful migration; skill registry records should receive equivalent cleanup so `layout status` and `doctor` do not report avoidable overlaps.
- Bug: `umem layout migrate --to shared --apply --yes --format json` returned a generic unexpected error in some repositories, while retrying the same apply command without `--yes` succeeded. The CLI should either accept `--yes` consistently or return a specific validation error.
- Improvement: multi-repository UMEM upgrades through Maestri/Codex hit repeated sandbox permission prompts for `umem doctor`, `umem host sync`, and cross-repository checks. Provide a documented orchestration checklist or pre-approved command set for release adoption across many repositories.
- Improvement: `uv tool upgrade universal-memory` may keep the installed tool pinned at an exact package version and only upgrade dependencies. Upgrade guidance should instruct users to verify `umem --version` and reinstall with `uv tool install universal-memory@latest --force` when the installed tool was pinned or sourced outside normal PyPI latest resolution.
- Improvement: partial `.umem/` operational layouts can coexist with shared `umem/` metadata and make `umem doctor` fail until `umem init --yes` repairs missing operational paths. Migration/apply flows should either repair required operational paths automatically or report that next step directly.
- Improvement: package upgrades install newer managed skill templates, but they do not automatically apply those templates to project-local `.umem/skills/use-universal-memory/`. Release/adoption guidance should explicitly pair package upgrades with `umem update --skills --yes --format json`, explain the `update.skills` JSON contract (`managed`, `updated_paths`, `preserved_paths`, `warnings`), and tell users how to verify whether `use-universal-memory` is already up to date.
- Bug: `umem update --skills` can be blocked by an active skill registry entry whose `canonical_path` is missing from the working tree, such as an internal workflow skill registered at `.umem/skills/manage-release-flow/SKILL.md` after the file was intentionally kept private or absent. The update flow should report the missing skill as a per-skill warning or skip it instead of preventing managed template update reporting for unrelated skills.

## Deferred from: code review of 1-4-create-local-umem-layout-and-toml-configuration.md (2026-05-24)

- Define a resilient self-healing strategy for specific `.umem/` states, including explicit criteria to distinguish fatal corruption from safely repairable partial layout, before allowing automatic recovery during onboarding.

## Deferred from: code review of 2-4-list-audit-and-snapshots.md (2026-05-26)

- Risk of concurrent collisions if write operations exceed the fixed limit of `STALE_LOCK_SECONDS = 10.0` in `local_audit_log_repository.py` and `local_snapshot_repository.py`.
- Concurrent reading of the audit log (`LocalAuditLogRepository.list`) is performed without acquiring a lock, which could raise a JSON decoding error or a `ValidationError` if it reads a truncated line during a concurrent write.

## Deferred from: Codex sandbox UMEM bootstrap investigation (2026-06-05)

- `umem status`, `umem context`, and `umem skills list` can fail with `storage_error` inside sandboxed agent environments even when the same CLI command succeeds in a normal local shell. Confirmed trigger: read paths acquire exclusive `.jsonl.lock` files for global scope under `~/.local/share/umem`, which is outside the writable workspace roots in Codex sandboxed execution. Product direction: separate read-only operations from write locks where safe, support shared/read locks or a no-write global read path, and improve the error payload so permission/sandbox lock failures identify the affected storage path and scope instead of only suggesting `umem init`.

## Deferred from: code review of 3-2-query-local-context-with-text-search.md (2026-05-27)

- Weak Domain Port Typing for `write()` and Abundant `cast(Any, ...)` Workarounds: Dynamic dynamic type checking and casts (`cast(Any, ...)`) due to domain port returning `object | None` instead of typed structures or split ports, indicating leaky design. [src/universal_memory/domain/ports/fact_repository.py:50]
- Clean Architecture Violation: Dynamic Runtime State and Injection on Repository Port: Injecting fields dynamically onto repository instances inside Use Case violating stateless Clean Architecture boundaries. [src/universal_memory/application/memory/remember_fact_use_case.py:40]
- **Agent Skills (UMEM Capabilities)**: Create specific BMad/Agent Skills to document and explain to external AI agents each capability delivered by UMEM (such as offline substring/regex search with highlighting metadata, safe atomic write with auditing and restoration, etc.), allowing agents to use and manage local memory fully autonomously.

## Deferred from: code review of 3-3-implement-retrieval-benchmark.md (2026-05-27)

- Duplication of the `MIN_REGEX_QUERY_LENGTH` constant across multiple test and production files (`search_facts_use_case.py`, `local_fact_repository.py`, `test_memory_use_cases.py`), reducing DRY.
- Duplication of text normalization logic (accent removal via `unicodedata` and `casefold`) between production and the benchmark script.
- Silent and unsafe silencing of Regular Expression exceptions (`except re.error: pass`), hiding invalid queries in the fact repository.
- Theoretical exposure to Regular Expression Denial of Service (ReDoS) vulnerabilities in pattern searching via direct string input without length validation.

## Deferred from: code review of 3-5-display-memory-status.md (2026-05-27)

- Inefficient full-database scan to count facts: The status command fetches all facts in memory via `fact_repository.list()` and iterates over them to count them by scope and status. If a user has a massive repository history, this full scan will consume excessive memory and CPU. The repository interface should expose a lightweight count or metadata method instead. [src/universal_memory/application/memory/get_memory_status_use_case.py]

## Deferred from: code review of 4-2-implement-base-mcp-server-with-fastmcp.md (2026-05-28)

- Tool calls catch-all wrapper prevents standard JSON-RPC error signaling: The server catches all exceptions and wraps them in a standard JSON response (`{"ok": False, "error": ...}`) within the success stream, rather than raising exceptions that the JSON-RPC host can catch and mark as failed tool executions. Returning a success status blocks the standard error handling flow of the MCP protocol. [src/universal_memory/interfaces/mcp/server.py:58]
- Static project root binding prevents dynamic multi-project directory switching: The project root is statically bound at configuration time to `Path.cwd()`. Long-running MCP processes used across different editor windows or workspaces will always query the startup directory instead of dynamically adapting to the client's current file path. [src/universal_memory/bootstrap/mcp.py:26]

## Deferred from: code review of 4-3-implement-cli-mcp-parity-matrix.md (2026-05-28)

- Localization Bleed (Portuguese in CLI Option Help vs English Codebase): The CLI help texts are written in Portuguese while the entire rest of the codebase (including MCP tools, options, JSON keys, and exception names) is designed in English. [src/universal_memory/interfaces/cli/init_command.py:195]
- Crude and Hardcoded Token Count Estimation: Both CLI and MCP approximate token counts using a crude, hardcoded divide-by-four logic rather than leveraging a real tokenizer. [src/universal_memory/interfaces/cli/init_command.py:1008]
- Hardcoded "not-implemented-yet" Placeholders in Production Contracts: The CLI `AUDIT_REFERENCE_PLACEHOLDER` and the MCP `_init_payload` both fallback to the hardcoded string "not-implemented-yet" for the `audit_reference` field, violating production contract readiness. [src/universal_memory/interfaces/cli/init_command.py:64]

## Deferred from: code review of 4-4-map-domain-errors-to-cli-and-json-rpc.md (2026-05-28)

- Redundant import and polluted namespace: Imports the entire `errors` module under the alias `interface_errors` and, in the immediate sequence, individually imports functions and keys from the same module, polluting the local namespace. [src/universal_memory/interfaces/mcp/server.py:44-50]
- Simplistic regular expressions in sanitization of absolute paths and keys: Path regular expressions do not match paths containing spaces, nor dangerous relative paths. API key regexes may suffer from false positives on legitimate variables. [src/universal_memory/interfaces/errors.py]
- Hardcoded internationalization (locale) logic in error payloads: The `error_payload` method performs a simple binary check based on the `"pt-BR"` string to decide whether to translate the technical message, mixing interface localization logic directly into data construction. [src/universal_memory/interfaces/errors.py:157-165]
- Direct access to environment variables (os.environ) in CLI adapters: Direct static calls to `os.environ.get("UMEM_DEBUG_ERRORS")` make isolated unit testing and programmatic control of CLI behavior difficult. [src/universal_memory/interfaces/cli/init_command.py:1282]
- DRY violation in repeated OSError exception handling logic in CLI: Repeated `OSError` handling and identical mapping of errors in almost all CLI commands (`_run_init`, `_run_status`, etc.), generating unnecessary boilerplate code. [src/universal_memory/interfaces/cli/init_command.py]

## Deferred from: code review of 5-1-model-runtime-and-target-registry.md (2026-05-28)

- Untyped escape hatch in metadata field: `dict[str, Any]` allows arbitrary data without domain validation. [src/universal_memory/domain/entities/host.py:86]
- Missing access mode classification (read-only vs write) for Host targets: Deferred to the use cases layer (application layer) in subsequent stories.
- Missing Instruction Entity and Serialization Validation: Deferred to subsequent stories (5.2/5.3), keeping the scope of 5.1 on basic infrastructure for hosts and targets.
- Lack of relationship validation between Host and InstructionTarget ownership: Deferred to validation in the application/service layer where repositories will be accessible.

## Deferred from: code review of 5-3-configure-claude-code-host-with-claude-md.md (2026-05-28)

- Lack of Transactional Multi-File Rollback: The sequential write loop for canonical documents and target file does not implement rollbacks on intermediate failure, despite the host configuring `rollback_behavior="snapshot_rollback"`. [src/universal_memory/application/host/setup_host_use_case.py:321-344]

## Deferred from: code review of 5-4-validate-context-reading-by-host.md (2026-05-29)

- In-memory O(N) linear scan scalability bottleneck in audit log listing: The status use case loads all project-scoped audit events and groups/filters them in memory to find the latest check. As the audit log grows, this will degrade command response time linearly. [src/universal_memory/application/memory/get_memory_status_use_case.py:323-349]
- Missing implementation of "manual_pending" validation status: AC 1 specifies that validation must return "success", "failure", or "manual_pending". [src/universal_memory/application/host/setup_host_use_case.py:188-194] — Simplify the MVP with 100% automated and binary validations, postponing manual onboarding flows.

## Deferred from: code review of 5-6-cli-multi-runtime-selection-onboarding.md (2026-05-29)

- Clean Architecture layer violation (use case importing infrastructure): The `SyncInstructionsUseCase` use case imports and uses `load_config` directly from the infrastructure layer (`toml_loader.py`), violating the dependency inversion rule. [src/universal_memory/application/host/sync_instructions_use_case.py:27]
- Coupled dependency on system clock (datetime.now(UTC)): The use case directly uses `datetime.now(UTC)` within its execution logic, making isolated unit testing and test determinism difficult. [src/universal_memory/application/host/sync_instructions_use_case.py:63]
- Validation of supported hosts in the use case instead of a dedicated validation layer: The structural validation of which configured hosts in the TOML file are supported is implemented directly in the use case flow instead of a structural validation port. [src/universal_memory/application/host/sync_instructions_use_case.py:360]
- Absence of testing and specificity in list merging behavior of `_deep_merge`: The `update_project_config` function uses `_deep_merge` to merge configuration data without formal guarantees against list item duplication in subsequent runs. [src/universal_memory/infrastructure/config/toml_loader.py:174]

## Deferred from: code review of 6-1-register-latent-skills-by-recurrence.md (2026-05-29)

- High concurrency and lock redundancy (repeated listings and writes): The Use Case makes multiple `list()` calls and then `write()` calls, each individually contending for and acquiring exclusive locks. Batch I/O optimizations or shared locks for reading are recommended in the future. [src/universal_memory/application/skills/track_latent_skill.py:83-90]
- Absence of interactive confirmation flow in ambiguous occurrences: The Use Case only registers separate proposed candidates for low similarities, with no hook for interactive user confirmation. [src/universal_memory/application/skills/track_latent_skill.py:81-90]

## Deferred from: code review of 6-3-generate-canonical-skill-and-install-in-native-targets.md (2026-05-29)

- TOCTOU (Time-of-check to time-of-use) in slug resolution: There is a time window between verifying the existence of the slug and the physical creation, but it is of extremely low risk in the current single-product local ecosystem. [src/universal_memory/application/skills/generate_skill.py:178-189]
- Aesthetic handling of Pydantic's ValidationError in the CLI: The CLI passes through the raw ValidationError string, which is ugly/verbose, but does not break functionality. [src/universal_memory/interfaces/cli/init_command.py:501-504]
- Path handling when project_root is resolved to /: If the project root is /, path substitutions can corrupt relative paths, but the root will never be / in users' actual development environments. [src/universal_memory/application/skills/generate_skill.py:249]

## Deferred from: code review of spec-cli-version-status.md (2026-06-04)

- Version fallback is hardcoded when package metadata is unavailable. The fallback in `src/universal_memory/__init__.py` should stay aligned with the package version declared in `pyproject.toml`.
