from __future__ import annotations

from pathlib import Path

DOC_PATHS = (
    Path("README.md"),
    Path("docs/users/getting-started.md"),
    Path("docs/agents/mcp-and-skills.md"),
    Path("docs/contributors/release-readiness.md"),
)


def test_published_mcp_docs_use_project_independent_uvx_command() -> None:
    docs = "\n".join(path.read_text(encoding="utf-8") for path in DOC_PATHS)

    assert "uv run --package" not in docs
    assert "uvx --from universal-memory umem-mcp" in docs
    assert '"command": "uvx"' in docs
    assert '"--from", "universal-memory", "umem-mcp"' in docs


def test_mcp_docs_include_persistent_entrypoint_option() -> None:
    docs = "\n".join(path.read_text(encoding="utf-8") for path in DOC_PATHS)

    assert '"command": "umem-mcp"' in docs
