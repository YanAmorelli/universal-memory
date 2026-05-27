import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from universal_memory.application.memory import (
    GetMemoryStatusCommand,
    GetMemoryStatusResult,
)
from universal_memory.application.onboarding.setup_project import (
    SetupProjectResult,
    setup_project,
)
from universal_memory.application.security import (
    ListAuditLogCommand,
    ListAuditLogResult,
    ListSnapshotsCommand,
    ListSnapshotsResult,
    RollbackCommand,
    RollbackResult,
)
from universal_memory.domain import (
    ConfigValidationPort,
    InvalidConfigError,
    ProjectLayoutPort,
    SnapshotFailedError,
    StorageError,
    ValidationFailedError,
)
from universal_memory.domain.entities import (
    AuditEventScope,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)

AUDIT_REFERENCE_PLACEHOLDER = "not-implemented-yet"
SetupProjectCommand = Callable[[Path], SetupProjectResult]
ListAuditLogCommandHandler = Callable[[ListAuditLogCommand], ListAuditLogResult]
ListSnapshotsCommandHandler = Callable[[ListSnapshotsCommand], ListSnapshotsResult]
RollbackCommandHandler = Callable[[RollbackCommand], RollbackResult]
RollbackPreviewHandler = Callable[[SnapshotScope], Snapshot]
StatusCommandHandler = Callable[[GetMemoryStatusCommand], GetMemoryStatusResult]


def main(  # noqa: PLR0913
    argv: Sequence[str] | None = None,
    *,
    setup_project_command: SetupProjectCommand | None = None,
    audit_list_command: ListAuditLogCommandHandler | None = None,
    snapshots_list_command: ListSnapshotsCommandHandler | None = None,
    rollback_command: RollbackCommandHandler | None = None,
    rollback_preview_command: RollbackPreviewHandler | None = None,
    status_command: StatusCommandHandler | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        if setup_project_command is None:
            msg = "CLI setup_project_command dependency was not configured."
            raise RuntimeError(msg)
        command = setup_project_command
        return _run_init(command, output_format=args.output_format)

    if args.command == "status":
        if status_command is None:
            msg = "CLI status_command dependency was not configured."
            raise RuntimeError(msg)
        return _run_status(status_command, output_format=args.output_format)

    if args.command == "audit" and args.audit_command == "list":
        if audit_list_command is None:
            msg = "CLI audit_list_command dependency was not configured."
            raise RuntimeError(msg)
        return _run_audit_list(
            audit_list_command,
            output_format=args.output_format,
            scope=_audit_scope(args.scope),
        )

    if args.command == "snapshots" and args.snapshots_command == "list":
        if snapshots_list_command is None:
            msg = "CLI snapshots_list_command dependency was not configured."
            raise RuntimeError(msg)
        return _run_snapshots_list(
            snapshots_list_command,
            output_format=args.output_format,
            scope=_snapshot_scope(args.scope),
        )

    if args.command == "rollback":
        if rollback_command is None:
            msg = "CLI rollback_command dependency was not configured."
            raise RuntimeError(msg)
        if rollback_preview_command is None:
            msg = "CLI rollback_preview_command dependency was not configured."
            raise RuntimeError(msg)
        return _run_rollback(
            rollback_command,
            rollback_preview_command=rollback_preview_command,
            output_format=args.output_format,
            scope=_snapshot_scope(args.scope),
            yes=args.yes,
        )

    parser.print_help()
    return 0


def build_main(  # noqa: PLR0913
    *,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
    audit_list_command: ListAuditLogCommandHandler,
    snapshots_list_command: ListSnapshotsCommandHandler,
    rollback_command: RollbackCommandHandler,
    rollback_preview_command: RollbackPreviewHandler,
    status_command: StatusCommandHandler,
) -> Callable[[Sequence[str] | None], int]:
    command = _build_setup_project_command(
        layout_port=layout_port,
        config_validation_port=config_validation_port,
    )

    def configured_main(argv: Sequence[str] | None = None) -> int:
        return main(
            argv,
            setup_project_command=command,
            audit_list_command=audit_list_command,
            snapshots_list_command=snapshots_list_command,
            rollback_command=rollback_command,
            rollback_preview_command=rollback_preview_command,
            status_command=status_command,
        )

    return configured_main


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="umem")
    subparsers = parser.add_subparsers(dest="command")

    init_parser = subparsers.add_parser("init", help="Initialize local universal-memory state")
    init_parser.add_argument(
        "--format",
        choices=["human", "json"],
        default="human",
        dest="output_format",
        help="Output format",
    )

    status_parser = subparsers.add_parser("status", help="Inspect local memory status")
    status_parser.add_argument(
        "--format",
        choices=["human", "json"],
        default="human",
        dest="output_format",
        help="Output format",
    )

    audit_parser = subparsers.add_parser("audit", help="Inspect audit events")
    audit_subparsers = audit_parser.add_subparsers(dest="audit_command")
    audit_list_parser = audit_subparsers.add_parser("list", help="List audit events")
    audit_list_parser.add_argument(
        "--format",
        choices=["human", "json"],
        default="human",
        dest="output_format",
        help="Output format",
    )
    audit_list_parser.add_argument(
        "--scope",
        choices=["project", "global"],
        default="project",
        help="Scope filter",
    )

    snapshots_parser = subparsers.add_parser("snapshots", help="Inspect snapshots")
    snapshots_subparsers = snapshots_parser.add_subparsers(dest="snapshots_command")
    snapshots_list_parser = snapshots_subparsers.add_parser("list", help="List snapshots")
    snapshots_list_parser.add_argument(
        "--format",
        choices=["human", "json"],
        default="human",
        dest="output_format",
        help="Output format",
    )
    snapshots_list_parser.add_argument(
        "--scope",
        choices=["project", "global"],
        default="project",
        help="Scope filter",
    )

    rollback_parser = subparsers.add_parser("rollback", help="Restore latest snapshot")
    rollback_parser.add_argument(
        "--format",
        choices=["human", "json"],
        default="human",
        dest="output_format",
        help="Output format",
    )
    rollback_parser.add_argument(
        "--scope",
        choices=["project", "global"],
        default="project",
        help="Scope to roll back",
    )
    rollback_parser.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Skip interactive confirmation",
    )

    return parser


def _build_setup_project_command(
    *,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
) -> SetupProjectCommand:
    def command(project_root: Path) -> SetupProjectResult:
        return setup_project(
            project_root,
            layout_port=layout_port,
            config_validation_port=config_validation_port,
        )

    return command


def _run_init(command: SetupProjectCommand, output_format: str) -> int:
    try:
        result = command(Path.cwd())
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except (InvalidConfigError, StorageError, ValidationFailedError) as error:
        _print_expected_error(error, output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_success_envelope(result), sort_keys=True))
    else:
        print(_format_human_init_output(result))

    return 0


def _run_status(command: StatusCommandHandler, *, output_format: str) -> int:
    try:
        result = command(GetMemoryStatusCommand(project_root=Path.cwd()))
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except StorageError as error:
        _print_expected_error(error, output_format=output_format)
        return 1
    except ValidationError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1
    except Exception as error:
        _print_expected_error(
            StorageError(f"Erro inesperado: {error}"), output_format=output_format
        )
        return 1

    if output_format == "json":
        print(json.dumps(_status_success_envelope(result), sort_keys=True))
    else:
        print(_format_human_status_output(result))

    return 0


def _run_audit_list(
    command: ListAuditLogCommandHandler,
    *,
    output_format: str,
    scope: AuditEventScope,
) -> int:
    try:
        result = command(ListAuditLogCommand(scope=scope))
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except StorageError as error:
        _print_expected_error(error, output_format=output_format)
        return 1
    except ValidationError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_audit_success_envelope(result, scope=scope), sort_keys=True))
    else:
        print(_format_human_audit_output(result))

    return 0


def _run_snapshots_list(
    command: ListSnapshotsCommandHandler,
    *,
    output_format: str,
    scope: SnapshotScope,
) -> int:
    try:
        result = command(ListSnapshotsCommand(scope=scope, status=SnapshotStatus.created))
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except StorageError as error:
        _print_expected_error(error, output_format=output_format)
        return 1
    except ValidationError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_snapshots_success_envelope(result, scope=scope), sort_keys=True))
    else:
        print(_format_human_snapshots_output(result))

    return 0


def _run_rollback(
    command: RollbackCommandHandler,
    *,
    rollback_preview_command: RollbackPreviewHandler,
    output_format: str,
    scope: SnapshotScope,
    yes: bool,
) -> int:
    try:
        if output_format == "json" and not yes:
            raise SnapshotFailedError(
                "A flag --yes / -y e obrigatoria para executar rollback com saida JSON."
            )
        preview = rollback_preview_command(scope)
        if output_format != "json":
            print(_format_human_rollback_preview(preview))
            if not yes:
                try:
                    answer = input("Deseja prosseguir com o rollback? [s/N]: ")
                except (EOFError, KeyboardInterrupt):
                    print("\nRollback cancelado.")
                    return 1
                if answer.strip().lower() not in {"s", "sim", "y", "yes"}:
                    print("Rollback cancelado.")
                    return 1

        result = command(RollbackCommand(scope=scope, origin="cli"))
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except (SnapshotFailedError, StorageError, ValidationFailedError) as error:
        _print_expected_error(error, output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_rollback_success_envelope(result), sort_keys=True))
    else:
        print(_format_human_rollback_success(result))

    return 0


def _success_envelope(result: SetupProjectResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "init",
        "scope": "project",
        "data": _init_payload(result),
        "warnings": [],
    }


def _audit_success_envelope(
    result: ListAuditLogResult, *, scope: AuditEventScope
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "audit",
        "scope": scope.value,
        "data": {"events": [asdict(event) for event in result.events]},
        "warnings": [],
    }


def _snapshots_success_envelope(
    result: ListSnapshotsResult, *, scope: SnapshotScope
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "snapshots",
        "scope": scope.value,
        "data": {"snapshots": [asdict(snapshot) for snapshot in result.snapshots]},
        "warnings": [],
    }


def _rollback_success_envelope(result: RollbackResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "rollback",
        "scope": result.scope.value,
        "data": {
            "scope": result.scope.value,
            "snapshot_reference": result.snapshot_reference,
            "restored_paths": result.restored_paths,
            "audit_reference": result.audit_reference,
        },
        "warnings": [],
    }


def _status_success_envelope(result: GetMemoryStatusResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "status",
        "scope": "project",
        "data": _status_payload(result),
        "warnings": [],
    }


def _init_payload(result: SetupProjectResult) -> dict[str, Any]:
    return {
        "project_path": _path_to_posix(result.project_path),
        "config_path": _path_to_posix(result.config_path),
        "memory_path": _path_to_posix(result.memory_path),
        "audit_path": _path_to_posix(result.audit_path),
        "snapshots_path": _path_to_posix(result.snapshots_path),
        "created": result.created_paths,
        "already_initialized": result.already_initialized,
        "audit_reference": AUDIT_REFERENCE_PLACEHOLDER,
    }


def _status_payload(result: GetMemoryStatusResult) -> dict[str, Any]:
    if not result.initialized:
        return {
            "initialized": False,
            "project_path": result.project_path,
            "recommended_action": result.recommended_action,
        }

    return {
        "initialized": True,
        "project_path": result.project_path,
        "fact_counts": result.fact_counts,
        "active_rules_count": result.active_rules_count,
        "registered_skills_count": result.registered_skills_count,
        "approximate_size_bytes": result.approximate_size_bytes,
        "last_health_check": result.last_health_check,
        "host_validation": result.host_validation,
    }


def _format_human_init_output(result: SetupProjectResult) -> str:
    status = (
        "Memoria local criada em .umem/." if result.created else "Memoria local ja inicializada."
    )
    paths_label = "Caminhos criados:" if result.created else "Caminhos reutilizados:"
    paths = result.created_paths if result.created else result.existing_paths
    rendered_paths = "\n".join(f"- {path}" for path in paths)

    return "\n".join(
        [
            status,
            paths_label,
            rendered_paths,
            f"Auditoria: {AUDIT_REFERENCE_PLACEHOLDER}",
            "Proximo comando sugerido: umem status",
        ]
    )


def _format_human_status_output(result: GetMemoryStatusResult) -> str:
    if not result.initialized:
        return "\n".join(
            [
                "Memoria local nao inicializada.",
                f"Projeto: {result.project_path}",
                f"Proxima acao: {result.recommended_action}",
            ]
        )

    lines = [
        "Memoria local inicializada.",
        f"Projeto: {result.project_path}",
        f"Tamanho aproximado: {result.approximate_size_bytes} bytes",
        f"Ultimo health check: {result.last_health_check}",
        f"Regras ativas: {result.active_rules_count}",
        f"Skills registradas: {result.registered_skills_count}",
        "Hosts:",
    ]
    for host, status in result.host_validation.items():
        lines.append(f"- {host}: {status}")
    lines.append("Fatos por escopo/status:")
    for scope, counts in result.fact_counts.items():
        rendered_counts = ", ".join(f"{status}: {count}" for status, count in counts.items())
        lines.append(f"- {scope} {rendered_counts}")
    return "\n".join(lines)


def _format_human_audit_output(result: ListAuditLogResult) -> str:
    if not result.events:
        return "Nenhum evento de auditoria encontrado."

    lines = ["Eventos de auditoria:"]
    for event in result.events:
        lines.append(
            " | ".join(
                [
                    event.timestamp,
                    event.scope,
                    event.origin,
                    event.action,
                    event.result,
                    f"audit={event.audit_reference}",
                    f"snapshot={event.snapshot_reference}",
                ]
            )
        )
    return "\n".join(lines)


def _format_human_snapshots_output(result: ListSnapshotsResult) -> str:
    if not result.snapshots:
        return "Nenhum snapshot encontrado."

    lines = ["Snapshots:"]
    for snapshot in result.snapshots:
        lines.append(
            " | ".join(
                [
                    snapshot.timestamp,
                    snapshot.scope,
                    snapshot.origin,
                    snapshot.action,
                    snapshot.relative_path,
                    snapshot.hash,
                    snapshot.manifest_path,
                ]
            )
        )
    return "\n".join(lines)


def _format_human_rollback_preview(snapshot: Snapshot) -> str:
    return "\n".join(
        [
            "Rollback selecionado:",
            f"Escopo: {snapshot.scope.value}",
            f"Snapshot: {snapshot.id}",
            f"Timestamp: {snapshot.timestamp.isoformat()}",
            f"Acao original: {snapshot.action}",
            f"Arquivo: {snapshot.relative_path}",
        ]
    )


def _format_human_rollback_success(result: RollbackResult) -> str:
    return "\n".join(
        [
            "Rollback concluido.",
            f"Escopo: {result.scope.value}",
            f"Snapshot: {result.snapshot_reference}",
            f"Arquivos restaurados: {', '.join(result.restored_paths)}",
            f"Auditoria: {result.audit_reference}",
        ]
    )


def _recovery_hint(error: Exception) -> str:
    msg = str(error)
    if "Hint: " in msg:
        return msg.split("Hint: ", 1)[1]
    if isinstance(error, SnapshotFailedError):
        return "Execute uma mutacao segura antes de tentar rollback ou verifique o escopo."
    if isinstance(error, InvalidConfigError):
        return "Verifique as configuracoes no arquivo config.toml."
    if isinstance(error, ValidationFailedError):
        return "Corrija os dados invalidos informados."
    return "Verifique o layout local e execute umem init na raiz do projeto."


def _print_expected_error(error: Exception, output_format: str) -> None:
    code = _error_code(error)
    detail = str(error)
    payload = {
        "ok": False,
        "error": {
            "code": code,
            "message": _error_message(error),
            "detail": detail,
            "recovery_hint": _recovery_hint(error),
            "audit_reference": None,
        },
    }

    if output_format == "json":
        print(json.dumps(payload, sort_keys=True))
        return

    print(
        "\n".join(
            [
                f"Falha: {payload['error']['message']}",
                f"Detalhe: {detail}",
                f"Recuperacao: {payload['error']['recovery_hint']}",
            ]
        ),
        file=sys.stderr,
    )


def _error_code(error: Exception) -> str:
    if isinstance(error, SnapshotFailedError):
        return "snapshot_failed"
    if isinstance(error, InvalidConfigError):
        return "invalid_config"
    if isinstance(error, ValidationFailedError):
        return "validation_failed"
    return "storage_error"


def _error_message(error: Exception) -> str:
    if isinstance(error, SnapshotFailedError):
        return "Falha de snapshot."
    if isinstance(error, InvalidConfigError):
        return "Configuracao invalida."
    if isinstance(error, ValidationFailedError):
        return "Validacao falhou."
    return "Falha de armazenamento."


def _path_to_posix(path: Path) -> str:
    return path.as_posix()


def _audit_scope(value: str) -> AuditEventScope:
    return AuditEventScope.global_ if value == "global" else AuditEventScope.project


def _snapshot_scope(value: str) -> SnapshotScope:
    return SnapshotScope.global_ if value == "global" else SnapshotScope.project
