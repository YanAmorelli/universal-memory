---
title: 'BUG-002 - Unify global XDG storage in umem'
type: 'bugfix'
created: '2026-05-29'
status: 'done'
baseline_commit: '7a0709071768113cf0cbb9ed078b81e19769227e'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Global storage uses different roots: config in `~/.config/universal-memory/config.toml`, facts/rules in `~/.umem/`, and latent skills in `~/.local/share/universal-memory/`. This makes the global state difficult to predict, inspect, and document during alpha testing.

**Approach:** Standardize global state in XDG paths with the short name `umem`: global config in `~/.config/umem/config.toml` and global data in `~/.local/share/umem/memory/*`. Keep project-specific storage in `<project>/.umem/` unchanged.

## Boundaries & Constraints

**Always:** Preserve `global_home` as an injection point for testing; keep project scope in `.umem`; keep SafeWrite, snapshot, and auditing working for global writes; update tests that hardcode old paths.

**Ask First:** Any migration/reading of legacy paths (`~/.umem`, `~/.config/universal-memory`, `~/.local/share/universal-memory`), changes to public command names, or modifications to the CLI/MCP payload contract.

**Never:** Add backward compatibility without human approval; move project storage to XDG; relax safe write validations to accommodate path changes.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Default global config | `load_config(project_root=...)` without `global_config_path`, with `HOME=/tmp/home` | `global_config_path` resolves to `/tmp/home/.config/umem/config.toml` | Missing config continues to return `{}` |
| Global facts/rules | Repositories with `global_home=/tmp/home` write global-scope entities | Global JSONL resides in `/tmp/home/.local/share/umem/memory/facts.jsonl` and `rules.jsonl` | I/O failures remain mapped to `StorageError` |
| Global latent skills | `LocalLatentSkillRepository` writes `LatentSkillScope.global_` | Global JSONL resides in `/tmp/home/.local/share/umem/memory/latent_skills.jsonl` | Global SafeWrite uses the correct XDG root for snapshot/audit |
| Project scope | Any repository writes project-scope entity | Files remain in `<project>/.umem/memory/*` | No local path regression |

</frozen-after-approval>

## Code Map

- `src/universal_memory/infrastructure/config/toml_loader.py` -- Defines the default path for the global config and resolves relative config paths.
- `src/universal_memory/infrastructure/storage/local_fact_repository.py` -- Defines the global facts root and global SafeWrite currently based on `global_home/.umem`.
- `src/universal_memory/infrastructure/storage/local_rule_repository.py` -- Defines the global rules root and global SafeWrite currently based on `global_home/.umem`.
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py` -- Already uses XDG for global data, but with the name `universal-memory` instead of `umem`.
- `tests/infrastructure/config/test_toml_loader.py` -- Protects the default path of the global config.
- `tests/infrastructure/storage/test_local_fact_repository.py` -- Must cover the new global facts path.
- `tests/infrastructure/storage/test_local_rule_repository.py` -- Must cover the new global rules path.
- `tests/infrastructure/storage/test_local_latent_skill_repository.py` -- Contains the current expectation for `.local/share/universal-memory`.
- `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Alpha log of BUG-002 to be updated after fix and verification.

## Tasks & Acceptance

**Execution:**
- [x] `src/universal_memory/infrastructure/config/toml_loader.py` -- Change the global config default to `Path.home() / ".config" / "umem" / "config.toml"` -- Aligns config with the decided XDG name.
- [x] `src/universal_memory/infrastructure/storage/local_fact_repository.py` -- Change the global root to `global_home/.local/share/umem` and adjust the global SafeWrite for this root -- Centralizes global facts in the same XDG data dir.
- [x] `src/universal_memory/infrastructure/storage/local_rule_repository.py` -- Change the global root to `global_home/.local/share/umem` and adjust the global SafeWrite for this root -- Centralizes global rules in the same XDG data dir.
- [x] `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py` -- Change the app name in the global data dir from `universal-memory` to `umem`, including Windows -- Keeps latent skills under the same naming convention.
- [x] `tests/infrastructure/config/test_toml_loader.py`, `tests/infrastructure/storage/test_local_fact_repository.py`, `tests/infrastructure/storage/test_local_rule_repository.py`, `tests/infrastructure/storage/test_local_latent_skill_repository.py` -- Update/add tests for global paths -- Prevents regression to the three old roots.
- [x] `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Mark BUG-002 as fixed/verified with summary and executed commands -- Maintains alpha traceability.

**Acceptance Criteria:**
- Given an isolated `HOME`, when the default global config is loaded, then the path used is `~/.config/umem/config.toml`.
- Given repositories of facts, rules, and latent skills with an isolated `global_home`, when global entities are written, then all global JSONLs are located under `~/.local/share/umem/memory/`.
- Given project-scope entities, when repositories write data, then the project paths remain under `<project>/.umem/memory/`.
- Given the relevant storage/config suite, when tests are run, then there is no remaining expectation for `~/.umem`, `~/.config/universal-memory`, or `~/.local/share/universal-memory` as the default global path.

## Spec Change Log

## Verification

**Commands:**
- `uv run pytest tests/infrastructure/config/test_toml_loader.py tests/infrastructure/storage/test_local_fact_repository.py tests/infrastructure/storage/test_local_rule_repository.py tests/infrastructure/storage/test_local_latent_skill_repository.py` -- expected: global paths tests pass.
- `uv run pytest tests/interfaces/cli/test_skills_propose.py` -- expected: human output of global proposal uses `~/.config/umem/config.toml`.
- `uv run pytest` -- expected: complete suite passes with no regressions in CLI/MCP/storage.

## Suggested Review Order

**Global Path Contract**

- Main entry point of the XDG decision for global config.
  [`toml_loader.py:49`](../../src/universal_memory/infrastructure/config/toml_loader.py#L49)

- Global facts use XDG data root and isolated global SafeWrite.
  [`local_fact_repository.py:60`](../../src/universal_memory/infrastructure/storage/local_fact_repository.py#L60)

- Global rules mirror the same strategy as facts.
  [`local_rule_repository.py:58`](../../src/universal_memory/infrastructure/storage/local_rule_repository.py#L58)

- Latent skills maintain XDG, now named `umem`.
  [`local_latent_skill_repository.py:65`](../../src/universal_memory/infrastructure/storage/local_latent_skill_repository.py#L65)

**SafeWrite And Audit**

- Global facts writes use `memory/facts.jsonl` under the XDG root.
  [`local_fact_repository.py:327`](../../src/universal_memory/infrastructure/storage/local_fact_repository.py#L327)

- Global rules SafeWrite creates snapshot and audit in the XDG root.
  [`local_rule_repository.py:65`](../../src/universal_memory/infrastructure/storage/local_rule_repository.py#L65)

- Human message for global proposal points to the new config.
  [`init_command.py:2373`](../../src/universal_memory/interfaces/cli/init_command.py#L2373)

**Regression Coverage**

- Default config protects `~/.config/umem/config.toml`.
  [`test_toml_loader.py:55`](../../tests/infrastructure/config/test_toml_loader.py#L55)

- Global facts validate JSONL, audit, and snapshots in XDG.
  [`test_local_fact_repository.py:70`](../../tests/infrastructure/storage/test_local_fact_repository.py#L70)

- Global rules cover project and global separately.
  [`test_local_rule_repository.py:30`](../../tests/infrastructure/storage/test_local_rule_repository.py#L30)

- Latent skills validate global data, audit, and snapshots.
  [`test_local_latent_skill_repository.py:133`](../../tests/infrastructure/storage/test_local_latent_skill_repository.py#L133)

- CLI protects against regression to `universal-memory/config.toml`.
  [`test_skills_propose.py:68`](../../tests/interfaces/cli/test_skills_propose.py#L68)
