---
title: "Refresh MkDocs documentation for users, agents, contributors, and alpha testing"
type: "documentation"
created: "2026-06-25"
status: "done"
baseline_commit: "37c5dcc1aac2076fe7d4341a0d7c4e126113ea63"
context:
  - "mkdocs.yml"
  - "README.md"
  - "pyproject.toml"
  - "docs/"
  - "docs/reference/cli-mcp-parity.md"
  - "docs/reference/skill-lifecycle.md"
  - ".umem/skills/use-universal-memory/references/cli-mcp-parity.md"
  - ".umem/skills/use-universal-memory/references/guardrails-and-recording.md"
  - "_bmad-output/implementation-artifacts/spec-mkdocs-documentation-structure.md"
  - "_bmad-output/implementation-artifacts/spec-mcp-setup-ux-hardening.md"
---

<frozen-after-approval reason="human-owned intent - do not modify unless human renegotiates">

## Intent

**Problem:** The MkDocs site exists, but it no longer explains the current product shape
well enough for its three core audiences. Contributor docs do not make CLI/MCP parity
and testing expectations explicit. The current release and alpha validation pages are
stale relative to the current runtime, MCP, skills, host-sync, and release validation
flows, and their names read like internal planning artifacts instead of durable
documentation. User docs still read too much like manual CLI instructions instead of
telling users how to hand memory work to an agent. Agent docs explain mechanics, but they
do not yet work as a compelling "why an agent should use this" showcase.

**Approach:** Refresh the MkDocs information architecture in place without changing the
product contract. Keep the CLI as the canonical contract, document MCP as the equivalent
agent automation surface, present `.umem/skills/<slug>/SKILL.md` as the source of truth
for Agent Skills, and clarify the memory model: project-scoped working memory for the
current repository plus global long-lived preferences and durable context. Preserve
Python 3.12+ as the documented floor unless a separate compatibility story explicitly
adds and verifies Python 3.11 support.

## Boundaries And Constraints

**Always:**

- Write public docs in English and use relative paths.
- Keep `README.md` as the repository/package entrypoint and MkDocs as the curated docs
  site.
- Treat `pyproject.toml` as the runtime support source of truth. Current contract is
  `requires-python = ">=3.12"` with Ruff `py312` and Pyright `pythonVersion = "3.12"`.
- Use `--runtime` in new `umem init` examples. Mention `--hosts` only as a legacy alias
  where useful.
- Document the CLI as canonical and MCP as equivalent for agents and hosts.
- Keep `.umem/skills/<slug>/SKILL.md` as the canonical Agent Skills source. Native
  runtime directories such as `.agents/skills/`, `.opencode/skills/`, and
  `.antigravity/rules/` are synchronized copies.
- Explain safe mutation behavior: validation, secret scanning, snapshots, audit events,
  and rollback.
- Prefer concise docs that point to detailed reference pages instead of duplicating the
  full operating manual on every page.

**Ask First:**

- Lowering runtime support from Python 3.12+ to Python 3.11+.
- Changing public CLI flags, MCP tool names, JSON envelope keys, or skill lifecycle
  semantics.
- Adding new MkDocs top-level navigation sections.
- Removing alpha warnings or presenting the package as broadly stable.

**Never:**

- Do not claim Python 3.11 support while `pyproject.toml`, classifiers, Ruff, Pyright, CI,
  and tests still target Python 3.12.
- Do not document MCP-only behavior unless it is explicitly MCP-only.
- Do not tell users to manually edit managed instruction files, facts, or native skill
  copies as the normal workflow.
- Do not publish raw `_bmad-output/` material in MkDocs navigation.

</frozen-after-approval>

## Product Decisions To Encode

### Python Runtime

The docs should say Python 3.12 or newer is required.

Python 3.11 might be technically possible for parts of the source because `tomllib`
exists in 3.11, but it is not the current product contract. Evidence:

- `pyproject.toml` declares `requires-python = ">=3.12"`.
- Package classifiers include Python 3.12 only.
- Ruff targets `py312`.
- Pyright targets Python 3.12.
- Tests already include Python 3.12 syntax such as `type MethodExpectations = ...`.

If Python 3.11 support becomes desired, create a separate compatibility spec that:

- changes `requires-python`, classifiers, Ruff target, Pyright version, and CI matrix;
- removes or gates Python 3.12-only syntax in tests and source;
- validates every runtime dependency under Python 3.11;
- runs the full test suite under both Python versions;
- updates user, contributor, and release docs only after the compatibility change lands.

### Audience Model

- **Users:** Explain what to install, how to initialize, and why the ideal workflow is to
  let the agent use UMEM through MCP or the CLI after bootstrap. Manual commands remain
  available, but should read as inspection and fallback tools.
- **Agents:** Present UMEM as useful infrastructure for agents: current context retrieval,
  durable fact recording, skill adoption, safe host sync, auditability, and recovery.
  The page should make an agent want to call the tools because it reduces repeated
  context gathering and avoids unsafe direct file edits.
- **Contributors:** Explain the architecture contract and the testing contract. Any public
  capability exposed through the CLI should have equivalent MCP coverage or an explicit
  documented exclusion.

### Contributor Page Names

Rename the stale contributor pages while refreshing their content:

- `docs/contributors/release-and-alpha.md` -> `docs/contributors/release-readiness.md`
  with the nav title `Release Readiness`.
- `docs/contributors/alpha-sandbox-test-plan.md` -> `docs/contributors/alpha-validation.md`
  with the nav title `Alpha Validation`.

The new names should appear in `mkdocs.yml`, page headings, links, and tests. The old
paths should not remain in the MkDocs navigation.

### Memory Model

Use consistent terms:

- **Project memory / working memory:** repository-scoped facts, rules, active task
  context, and project constraints stored under `.umem/`.
- **Global memory / long-term memory:** durable user preferences and cross-project context
  stored in the configured user-level UMEM storage root.
- **Context assembly:** `umem context --scope project` combines relevant project facts,
  project rules, active skills guidance, and global preferences into a compact context
  payload for agents.
- **Skill memory:** repeated workflows should become Agent Skills when they are stable
  enough to reuse. `.umem/skills/` is the canonical repository for those skills.

## Code Map

- `mkdocs.yml` - Preserve existing top-level navigation unless implementation discovers a
  strong reason to add a small page.
- `docs/index.md` - Align homepage examples with current `--runtime` onboarding and the
  three-audience positioning.
- `docs/users/getting-started.md` - Rework user setup around persistent install, project
  initialization, MCP/agent handoff, memory scopes, and skills adoption.
- `docs/users/cli.md` - Keep as manual/reference material and ensure commands reflect
  current flags.
- `docs/users/safety-and-recovery.md` - Cross-link from user and alpha docs for snapshots,
  audit events, rollback, and secret scanning.
- `docs/agents/operating-protocol.md` - Make the startup flow crisp for agents and include
  both CLI and MCP forms.
- `docs/agents/mcp-and-skills.md` - Turn into the agent showcase page: why MCP, why
  skills, canonical skill store, common flows, and exact tool equivalents.
- `docs/agents/instruction-files.md` - Reiterate that instruction files are bootstraps,
  not memory dumps.
- `docs/contributors/development.md` - Add contributor testing protocol and CLI/MCP parity
  responsibilities.
- `docs/contributors/release-readiness.md` - Rename from
  `docs/contributors/release-and-alpha.md`; refresh release readiness, clean install,
  published-package MCP startup, docs build, and alpha tester focus.
- `docs/contributors/alpha-validation.md` - Rename from
  `docs/contributors/alpha-sandbox-test-plan.md`; replace stale smoke flow with an
  isolated real-user validation guide that covers CLI, MCP, host sync, facts, skills,
  audit, snapshots, rollback, and docs examples.
- `docs/reference/cli-mcp-parity.md` - Keep as canonical public parity table and link to it
  from contributor and agent docs.
- `docs/reference/skill-lifecycle.md` - Keep as canonical skill lifecycle reference and
  link to it from user and agent docs.
- `tests/docs/` - Add or update content contract tests for high-risk docs claims.

## Page-Level Requirements

### `docs/users/getting-started.md`

- Keep the opening requirement: Python 3.12 or newer.
- Recommend persistent install for ongoing use:
  `uv tool install universal-memory`, with `uvx --from universal-memory umem --help` for
  trials and `pip install universal-memory` as an alternative.
- Use `umem init --runtime codex --runtime claude_code` or another current runtime-based
  example.
- Add a short "Hand It To Your Agent" section:
  - initialize the project;
  - configure MCP or host instructions;
  - tell the agent to run the UMEM bootstrap and use UMEM for durable facts and skills;
  - use manual CLI commands for inspection, review, and recovery.
- Explain project memory vs global memory with one example of each.
- Explain that skills live canonically under `.umem/skills/<slug>/SKILL.md`; runtime
  folders are generated copies.
- Include the published-package MCP launch patterns from `spec-mcp-setup-ux-hardening.md`
  if that spec is already merged in the target branch. If not merged, avoid duplicating
  conflicting examples and leave a forward reference.

### `docs/agents/mcp-and-skills.md`

- Start from agent value, not only mechanics:
  - get current repository context without asking the user again;
  - record durable learnings safely;
  - turn recurring workflows into skills;
  - sync instruction targets without direct edits;
  - use audit/snapshot/rollback for recovery.
- Keep the CLI/MCP relationship explicit:
  "CLI is the canonical contract; MCP is the equivalent automation surface for agents."
- Include a compact parity example:
  - `umem context --scope project --format json` equals MCP `context(scope="project")`;
  - `umem remember ... --format json` equals MCP `remember_fact(...)`;
  - `umem skills import ... --sync --format json` equals MCP `import_skill(...,
    sync_after_import=true)`;
  - `umem skills sync <slug> --format json` equals MCP `sync_skills(...)`.
- Explain `.umem/skills/<slug>/SKILL.md` as the source of truth and native runtime
  folders as complete synchronized copies.
- Clarify when to use:
  - `skills create`;
  - `skills import`;
  - `skills track`;
  - `skills recommend`;
  - `skills sync`;
  - `umem update --skills`.

### `docs/agents/operating-protocol.md`

- Keep the mandatory startup sequence:
  `status`, `context(scope="project")`, `list_skills`, then inspect relevant skill detail.
- Explain when to record memory:
  durable preference, architecture decision, bug fix, obsolete fact cleanup, or repeated
  workflow candidate.
- Explain what not to record:
  secrets, raw logs, raw prompts, transient task progress, private customer data, or
  unverified guesses.
- Point agents to the installed `use-universal-memory` skill references for exact
  procedures.

### `docs/contributors/development.md`

- Add a "Testing Contract" section:
  - `uv run pytest` for the full suite;
  - targeted pytest paths for local iteration;
  - `uv run ruff check .`;
  - `uv run ruff format --check .`;
  - `uv run pyright`;
  - `uv run --group docs mkdocs build --strict`;
  - package build via `uv build` when packaging metadata or entrypoints change.
- Add "What To Test By Change Type":
  - domain/application use cases: application/domain unit tests;
  - CLI behavior: `tests/interfaces/cli/`;
  - MCP behavior: `tests/interfaces/mcp/`;
  - CLI/MCP public capability parity: `tests/interfaces/test_parity.py`;
  - docs examples and content guarantees: `tests/docs/`;
  - dependency and packaging contract: `tests/packaging/` if present.
- Add "CLI/MCP Parity Rule":
  - new public CLI capability must have an MCP equivalent or a documented exclusion;
  - CLI JSON and MCP tool responses should share the success envelope and equivalent
    `data` keys;
  - update `docs/reference/cli-mcp-parity.md` and parity tests together.

### `docs/contributors/release-readiness.md`

- Refresh release path around alpha reality:
  1. local engineering checks;
  2. docs build and docs content tests;
  3. package build;
  4. clean virtualenv install from wheel;
  5. published-package style MCP launch check;
  6. isolated sandbox alpha test;
  7. alpha tester report checklist.
- Include Python 3.12+ in release prerequisites.
- Include clean environment package validation:
  - `python3.12 -m venv .venv-alpha`;
  - install `dist/*.whl`;
  - `umem --help`;
  - `umem doctor --format json`;
  - `umem-mcp --help` or published-package equivalent if available.
- Include `uvx --from universal-memory umem-mcp --help` as the published-package MCP
  launch validation when package metadata is available.
- Add release focus for:
  - runtime install friction;
  - `umem init --runtime ...`;
  - JSON envelopes;
  - MCP startup and parity;
  - host setup/check/sync;
  - snapshots/audit/rollback;
  - skill create/import/sync/list/detail;
  - docs examples matching real commands.

### `docs/contributors/alpha-validation.md`

- Keep the "real user without pytest" premise.
- Use an isolated project and isolated HOME/XDG roots.
- Use current commands:
  - `umem init --yes --runtime codex --runtime claude_code --format json`;
  - `umem status --format json`;
  - `umem context --scope project --format json`;
  - `umem remember ... --scope project --tag ... --format json`;
  - `umem facts list --scope project --format json`;
  - `umem host setup codex --yes --format json`;
  - `umem host check codex --format json`;
  - `umem host sync --apply --yes --format json`;
  - `umem skills create ... --format json`;
  - `umem skills import <path> --scope project --sync --format json`;
  - `umem skills sync <slug> --format json`;
  - `umem audit list --scope project --format json`;
  - `umem snapshots list --scope project --format json`;
  - `umem rollback --scope project --yes --format json`.
- Add an MCP parity smoke with equivalent MCP tools:
  `initialize_project`, `status`, `context`, `remember_fact`, `list_facts`,
  `host_setup`, `host_check`, `sync_instructions`, `create_skill`, `import_skill`,
  `sync_skills`, `list_skills`, `get_skill_detail`, `list_audit_events`,
  `list_snapshots`, and `rollback_scope`.
- Add expected result checks:
  - JSON output parses;
  - standard envelope has `ok`, `operation`, `scope`, `data`, and `warnings`;
  - paths are relative where user-facing;
  - direct generated files exist in the sandbox;
  - no secrets or absolute unrelated machine paths leak in errors;
  - repeated initialization is idempotent.

## I/O And Edge-Case Matrix

| Scenario | Input / State | Expected Documentation Behavior | Regression Guard |
| --- | --- | --- | --- |
| Python support question | User asks whether 3.11 is supported | Docs say Python 3.12+ only; 3.11 requires a separate compatibility change | Docs test blocks "Python 3.11" support claims unless packaging changes |
| Agent adoption | Agent reads `docs/agents/mcp-and-skills.md` | Agent sees concrete reasons and commands/tools for using UMEM instead of direct edits | Docs content test checks for MCP/CLI parity and canonical skill store language |
| User onboarding | User wants memory managed by an agent | Docs show install/init plus agent handoff guidance, not only manual CLI usage | Docs content test checks for "agent handoff" section and MCP mention |
| Contributor adds public command | New CLI capability appears | Contributor docs require MCP equivalent, docs parity update, and parity tests | Existing `tests/interfaces/test_parity.py` plus docs guidance |
| Alpha release prep | Maintainer validates a build | Release docs include code checks, docs build, package build, clean install, MCP startup, and sandbox smoke | Manual checklist and optional docs test for key commands |
| Existing native skill adoption | User has `.agents/skills/review-protocol` | Docs route through `umem skills import ... --sync` and canonical `.umem/skills/...` editing | Docs content test checks import/sync examples |

## Tasks & Acceptance

**Execution:**

- [x] `docs/users/getting-started.md` - Reframe setup around Python 3.12+, persistent
  install, `--runtime` initialization, agent handoff, project/global memory, and canonical
  skills - Users understand how to use UMEM manually and why handing it to the agent is
  the preferred workflow.
- [x] `docs/agents/mcp-and-skills.md` - Rewrite as an agent-facing showcase with concrete
  CLI/MCP parity examples and skill source-of-truth guidance - Agents have a clear reason
  and procedure for using UMEM.
- [x] `docs/agents/operating-protocol.md` and `docs/agents/instruction-files.md` - Tighten
  bootstrap, recording, and direct-edit guardrails - Agent docs remain operationally safe.
- [x] `docs/contributors/development.md` - Add testing contract and CLI/MCP parity rule -
  Contributors know which tests to add and run for each change type.
- [x] `docs/contributors/release-readiness.md` - Rename
  `docs/contributors/release-and-alpha.md`, refresh release readiness, package validation,
  docs validation, MCP launch validation, and tester focus - Release docs match the current
  alpha surface.
- [x] `docs/contributors/alpha-validation.md` - Rename
  `docs/contributors/alpha-sandbox-test-plan.md`, replace stale command flow with a
  current isolated CLI/MCP/user validation guide - Alpha testing validates real behavior
  without relying on pytest.
- [x] `mkdocs.yml` - Update contributor navigation to `Release Readiness` and
  `Alpha Validation`, pointing at the renamed files - The published IA no longer exposes
  the stale names.
- [x] `docs/reference/cli-mcp-parity.md` and `docs/reference/skill-lifecycle.md` - Update
  only if the refreshed pages reveal stale or incomplete reference details - Reference
  pages remain canonical and linked from audience pages.
- [x] `tests/docs/test_mkdocs_content_contracts.py` - Add focused docs content regression
  tests for Python 3.12+, runtime-based init examples, canonical skill source, CLI/MCP
  parity language, and no 3.11 support claim - Prevents high-risk docs drift.

**Acceptance Criteria:**

- Given a new user reads `docs/users/getting-started.md`, when they finish the page, then
  they know how to install UMEM, initialize a project, distinguish project/global memory,
  and hand memory work to an agent via MCP or host instructions.
- Given an agent reads `docs/agents/mcp-and-skills.md`, when it needs context or wants to
  persist a learning, then the page gives it the CLI/MCP-equivalent route and warns it away
  from direct file edits.
- Given a contributor adds or changes a public CLI capability, when they read
  `docs/contributors/development.md`, then they know to update MCP parity, payload tests,
  docs references, and relevant CLI/MCP tests.
- Given release prep starts, when the maintainer follows
  `docs/contributors/release-readiness.md`, then code checks, docs checks, package checks,
  clean install, MCP startup, and alpha sandbox validation are all covered.
- Given a tester follows `docs/contributors/alpha-validation.md`, when they run the
  commands in an isolated sandbox, then they cover facts, context, host sync, skills,
  snapshots, audit, rollback, CLI JSON envelopes, and MCP equivalent tool calls.
- Given no separate Python compatibility story has landed, when docs mention runtime
  support, then they say Python 3.12+ and do not present Python 3.11 as supported.

## Suggested Docs Test Contracts

Add a small `tests/docs/test_mkdocs_content_contracts.py` that reads selected Markdown
files and asserts:

- all public install/setup pages mention Python 3.12 or newer;
- no selected public page claims Python 3.11 support;
- new initialization examples use `--runtime`, while `--hosts` appears only as legacy;
- agent docs include both CLI and MCP forms for context retrieval;
- contributor docs reference `tests/interfaces/test_parity.py`;
- contributor docs include `uv run --group docs mkdocs build --strict`;
- skill docs mention `.umem/skills/<slug>/SKILL.md` as canonical;
- alpha sandbox docs include `umem skills import`, `umem skills sync`, and MCP tool names
  for parity smoke.

Keep these tests content-focused and resilient. Avoid brittle full-paragraph assertions.

## Spec Change Log

- Review finding: the implementation intentionally reused MCP launch guidance from the
  `mcp-setup-ux-hardening` branch even though its spec file was not present in this
  worktree. Amendment: treat the user's explicit instruction to use those docs changes as
  approval to include the published-package MCP launch examples here. Known-bad state
  avoided: omitting current MCP setup guidance from the docs refresh. KEEP: preserve the
  `uvx --from universal-memory umem-mcp` and persistent `umem-mcp` examples, and keep docs
  tests that protect them.
- Review finding: alpha/release validation examples were not executable enough.
  Amendment: require repeated init for idempotency, concrete MCP tool arguments, isolated
  MCP project setup, explicit wheel path in clean install validation, and temp-dir `uvx`
  validation. Known-bad state avoided: docs that claim real-user validation but cannot be
  followed literally. KEEP: alpha validation remains a non-pytest real-user flow.

## Verification

**Implementation should run:**

- `uv run pytest tests/docs` -- passed: 8 tests.
- `uv run --group docs mkdocs build --strict` -- passed.
- `uv run pytest tests/interfaces/test_parity.py tests/interfaces/mcp/test_compliance.py`
  -- passed: 30 tests.
- `uv run ruff check .` -- passed.
- `uv run ruff format --check .` -- passed: 167 files already formatted.
- `uv run pyright` -- passed: 0 errors, 0 warnings, 0 informations.

**Optional release-level checks after implementation:**

- `uv run pytest`
- `uv build`
- clean virtualenv wheel install smoke
- isolated alpha validation smoke from `docs/contributors/alpha-validation.md`

## Open Questions

- Should the docs site add a dedicated `Users / Let Your Agent Use UMEM` page, or should
  that remain a section in `docs/users/getting-started.md`?
- Should Python 3.11 compatibility be intentionally rejected in docs, or tracked as a
  future compatibility spike?
- Should `docs/contributors/alpha-validation.md` include a concrete MCP client harness, or
  remain tool-name oriented so testers can use their own MCP host?

## Suggested Review Order

**User And Agent Positioning**

- User entrypoint now frames agent handoff as the normal workflow.
  [getting-started.md:41](../../docs/users/getting-started.md#L41)

- MCP launch guidance reuses the hardening branch setup examples.
  [getting-started.md:108](../../docs/users/getting-started.md#L108)

- Agent page leads with why an agent should use UMEM.
  [mcp-and-skills.md:3](../../docs/agents/mcp-and-skills.md#L3)

- CLI/MCP parity table makes equivalent agent calls explicit.
  [mcp-and-skills.md:55](../../docs/agents/mcp-and-skills.md#L55)

**Contributor Workflow**

- Contributor guide now defines the required testing contract.
  [development.md:27](../../docs/contributors/development.md#L27)

- CLI/MCP parity responsibilities are tied to tests and reference docs.
  [development.md:50](../../docs/contributors/development.md#L50)

- Release readiness replaces the old release-and-alpha page.
  [release-readiness.md:1](../../docs/contributors/release-readiness.md#L1)

- Clean package validation now uses explicit temp-dir and wheel paths.
  [release-readiness.md:50](../../docs/contributors/release-readiness.md#L50)

- Alpha validation replaces the old sandbox test plan.
  [alpha-validation.md:1](../../docs/contributors/alpha-validation.md#L1)

- Alpha smoke now validates idempotent init with repeated commands.
  [alpha-validation.md:27](../../docs/contributors/alpha-validation.md#L27)

- MCP parity smoke now uses a separate project and concrete tool calls.
  [alpha-validation.md:125](../../docs/contributors/alpha-validation.md#L125)

**Navigation And Regression Tests**

- MkDocs navigation now exposes durable contributor page names.
  [mkdocs.yml:48](../../mkdocs.yml#L48)

- Docs tests pin Python floor and runtime-based init examples.
  [test_mkdocs_content_contracts.py:13](../../tests/docs/test_mkdocs_content_contracts.py#L13)

- Docs tests prevent stale contributor page links from returning.
  [test_mkdocs_content_contracts.py:56](../../tests/docs/test_mkdocs_content_contracts.py#L56)

- Docs tests enforce concrete alpha MCP and skill coverage.
  [test_mkdocs_content_contracts.py:105](../../tests/docs/test_mkdocs_content_contracts.py#L105)
