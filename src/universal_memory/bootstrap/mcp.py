from __future__ import annotations

from pathlib import Path

from fastmcp import FastMCP

from universal_memory.application.memory import (
    AssembleContextSummaryUseCase,
    GetMemoryStatusUseCase,
)
from universal_memory.application.security import SafeWriteUseCase
from universal_memory.bootstrap.cli import EmptyLatentSkillRepository, EmptyRuleRepository
from universal_memory.infrastructure.config import LocalProjectLayoutPort
from universal_memory.infrastructure.security import (
    EntropySecretScanner,
    LocalAuditLogRepository,
    LocalSnapshotRepository,
)
from universal_memory.infrastructure.storage import (
    LocalContextSummaryRepository,
    LocalFactRepository,
)
from universal_memory.interfaces.mcp import MCPUseCases, configure_server, create_mcp_server


def build_server(project_root: Path | None = None) -> FastMCP:
    try:
        root = project_root or Path.cwd()
    except Exception:
        root = Path(".")
    data_root = root / ".umem"
    layout_port = LocalProjectLayoutPort()
    audit_log_repository = LocalAuditLogRepository(project_root=root, data_root=data_root)
    snapshot_repository = LocalSnapshotRepository(project_root=root, data_root=data_root)
    secret_scanner = EntropySecretScanner()
    safe_write_use_case = SafeWriteUseCase(
        project_root=root,
        secret_scanner=secret_scanner,
        snapshot_repository=snapshot_repository,
        audit_log_repository=audit_log_repository,
    )
    fact_repository = LocalFactRepository(
        project_root=root,
        data_root=data_root,
        safe_write_use_case=safe_write_use_case,
    )
    rule_repository = EmptyRuleRepository()
    status_use_case = GetMemoryStatusUseCase(
        fact_repository=fact_repository,
        rule_repository=rule_repository,
        latent_skill_repository=EmptyLatentSkillRepository(),
        layout_port=layout_port,
        data_root=data_root,
    )
    context_use_case = AssembleContextSummaryUseCase(
        fact_repository=fact_repository,
        rule_repository=rule_repository,
        secret_scanner=secret_scanner,
        audit_log_repository=audit_log_repository,
        context_summary_repository=LocalContextSummaryRepository(
            project_root=root,
            data_root=data_root,
        ),
    )
    return configure_server(
        create_mcp_server(),
        MCPUseCases(status=status_use_case.execute, context=context_use_case.execute),
        project_root=root,
    )


def main() -> None:
    build_server().run()


if __name__ == "__main__":
    main()
