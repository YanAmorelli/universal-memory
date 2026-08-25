from __future__ import annotations

import re
from pathlib import Path

EXPECTED_INIT_RUNS = 2


def read(path: str) -> str:
    return Path(path).read_text(encoding="utf-8")


def test_public_docs_keep_python_312_as_runtime_floor() -> None:
    docs = "\n".join(
        read(path)
        for path in (
            "docs/users/getting-started.md",
            "docs/contributors/development.md",
            "docs/contributors/release-readiness.md",
            "docs/contributors/architecture.md",
        )
    )

    assert "Python 3.12" in docs
    assert not re.search(r"Python 3\.11 (?:or newer|or later|\+|supported)", docs)


def test_user_docs_use_zero_flag_init_and_contributor_docs_keep_automation() -> None:
    user_docs = "\n".join(
        read(path)
        for path in (
            "docs/index.md",
            "docs/users/getting-started.md",
        )
    )
    contributor_docs = read("docs/contributors/alpha-validation.md")

    assert "umem init" in user_docs
    assert "umem init --runtime" not in user_docs
    assert "umem connect" in user_docs
    assert "umem init --yes --runtime codex --runtime claude_code --format json" in (
        contributor_docs
    )
    assert "umem init --hosts" not in f"{user_docs}\n{contributor_docs}"


def test_contributor_nav_uses_durable_release_and_alpha_names() -> None:
    rendered = read("mkdocs.yml")

    assert "Release Readiness" in rendered
    assert "contributors/release-readiness.md" in rendered
    assert "Alpha Validation" in rendered
    assert "contributors/alpha-validation.md" in rendered
    assert "Release And Alpha Testing" not in rendered
    assert "Alpha Sandbox Test Plan" not in rendered
    assert "contributors/release-and-alpha.md" not in rendered
    assert "contributors/alpha-sandbox-test-plan.md" not in rendered


def test_public_docs_do_not_link_old_contributor_page_names() -> None:
    docs = "\n".join(
        path.read_text(encoding="utf-8")
        for path in Path("docs").rglob("*.md")
        if path.name not in {"release-and-alpha.md", "alpha-sandbox-test-plan.md"}
    )

    assert "release-and-alpha.md" not in docs
    assert "alpha-sandbox-test-plan.md" not in docs


def test_agent_docs_show_cli_mcp_parity_and_canonical_skills() -> None:
    docs = "\n".join(
        read(path)
        for path in (
            "docs/agents/mcp-and-skills.md",
            "docs/agents/operating-protocol.md",
        )
    )

    assert "CLI is the canonical contract" in docs
    assert "umem bootstrap --format json" in docs
    assert "bootstrap()" in docs
    assert "data.context" in docs
    assert "data.skills.list" in docs
    assert 'context(scope="project")' in docs
    assert "remember_fact" in docs
    assert "import_skill" in docs
    assert "sync_skills" in docs
    assert ".umem/skills/<slug>/SKILL.md" in docs


def test_user_docs_present_agent_handoff_and_mcp_launch() -> None:
    docs = read("docs/users/getting-started.md")

    assert "Hand It To Your Agent" in docs
    assert "umem bootstrap --format json" in docs
    assert "data.context" in docs
    assert "data.skills.list" in docs
    assert '"command": "uvx"' in docs
    assert '"--from", "universal-memory", "umem-mcp"' in docs
    assert '"command": "umem-mcp"' in docs
    assert "project memory" in docs.lower()
    assert "global memory" in docs.lower()


def test_contributor_docs_explain_testing_and_parity() -> None:
    docs = read("docs/contributors/development.md")

    assert "Testing Contract" in docs
    assert "uv run --group docs mkdocs build --strict" in docs
    assert "tests/interfaces/test_parity.py" in docs
    assert "docs/reference/cli-mcp-parity.md" in docs
    assert "tests/docs/" in docs


def test_alpha_validation_covers_skills_and_mcp_smoke() -> None:
    docs = read("docs/contributors/alpha-validation.md")

    assert 'MCP_PROJECT="$SANDBOX/mcp-project"' in docs
    assert (
        docs.count("umem init --yes --runtime codex --runtime claude_code --format json")
        >= EXPECTED_INIT_RUNS
    )
    assert "umem skills import" in docs
    assert "umem skills sync" in docs
    assert "initialize_project" in docs
    assert "remember_fact(content=" in docs
    assert "host_setup(host_id=" in docs
    assert "create_skill(name=" in docs
    assert "import_skill(path=" in docs
    assert "sync_instructions(apply=true)" in docs
    assert 'rollback_scope(scope="project", confirm=true)' in docs


def test_readme_uses_absolute_image_urls_for_pypi_rendering() -> None:
    readme = read("README.md")
    image_urls = [
        *re.findall(r"<img[^>]+src=\"([^\"]+)\"", readme),
        *re.findall(r"!\[[^\]]*\]\(([^)]+)\)", readme),
    ]

    assert image_urls
    assert all(url.startswith(("https://", "http://")) for url in image_urls)


def test_readme_covers_released_agent_support_and_existing_project_maintenance() -> None:
    readme = read("README.md")

    for term in (
        "Tier 1 — Native/Managed",
        "Tier 2 — Directed CLI",
        "Tier 3 — Unmanaged MCP",
        "skills@1.5.20",
        "/tree/v0.5.1/skills/universal-memory",
        "--agent pi --copy -y",
        ".antigravity/rules/universal-memory.md",
        "Windsurf",
        "Frozen legacy adapter",
        "umem update --check",
        "umem update --skills",
        "umem connect",
        ".umem/skills/use-universal-memory/",
    ):
        assert term in readme


def test_skill_lifecycle_docs_cover_summary_and_gitignore_warnings() -> None:
    docs = read("docs/reference/skill-lifecycle.md")

    assert "--format summary" in docs
    assert "--check-gitignore" in docs
    assert "tracked by git" in docs
    assert "ignore rules" in docs
    assert "does not edit `.gitignore`" in docs
    assert "after target planning/writes" in docs
    assert "dry-run by default" in docs


def test_agent_lifecycle_guidance_covers_purpose_safety_and_alternatives() -> None:
    docs = read("skills/universal-memory/references/skills-lifecycle.md")

    for term in (
        "Draft a skill when content may need validation before publish",
        "Adopt existing canonical work in place",
        "Import an existing local or native skill directory",
        "canonical source plus complete synchronized native copies",
        "do not edit `.gitignore`",
        "after target planning/writes",
        "dry-run/apply status",
        "skills canonical update",
        "skills repair",
    ):
        assert term in docs


def test_skill_lifecycle_docs_mention_new_mcp_tool_names() -> None:
    docs = "\n".join(
        read(path)
        for path in (
            "docs/reference/skill-lifecycle.md",
            "skills/universal-memory/references/skills-lifecycle.md",
        )
    )

    for tool in (
        "create_skill_draft",
        "validate_skill",
        "publish_skill",
        "adopt_skill",
        "update_canonical_skill",
        "rename_skill",
        "cleanup_skill",
        "repair_skills",
    ):
        assert tool in docs


def test_shared_root_docs_keep_operational_state_private() -> None:
    docs = "\n".join(
        read(path)
        for path in (
            "specs/002-shared-project-root/plan.md",
            "specs/002-shared-project-root/quickstart.md",
        )
    )

    assert "umem/project.toml" in docs
    assert "umem/memory" in docs
    assert "umem/skills" in docs
    assert ".umem/locks" in docs
    assert "use-universal-memory` remains operational under `.umem/skills" in docs
