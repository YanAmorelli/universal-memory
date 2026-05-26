import argparse
import json
import sys
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from universal_memory.application.onboarding.setup_project import (
    SetupProjectResult,
    setup_project,
)
from universal_memory.application.security import (
    ListAuditLogCommand,
    ListAuditLogResult,
    ListSnapshotsCommand,
    ListSnapshotsResult,
)
from universal_memory.domain import (
    ConfigValidationPort,
    InvalidConfigError,
    ProjectLayoutPort,
    StorageError,
    ValidationFailedError,
)
from universal_memory.domain.entities import (
    AuditEventScope,
    SnapshotScope,
    SnapshotStatus,
)

AUDIT_REFERENCE_PLACEHOLDER = "not-implemented-yet"
SetupProjectCommand = Callable[[Path], SetupProjectResult]
ListAuditLogCommandHandler = Callable[[ListAuditLogCommand], ListAuditLogResult]
ListSnapshotsCommandHandler = Callable[[ListSnapshotsCommand], ListSnapshotsResult]


def main(
    argv: Sequence[str] | None = None,
    *,
    setup_project_command: SetupProjectCommand | None = None,
    audit_list_command: ListAuditLogCommandHandler | None = None,
    snapshots_list_command: ListSnapshotsCommandHandler | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        if setup_project_command is None:
            msg = "CLI setup_project_command dependency was not configured."
            raise RuntimeError(msg)
        command = setup_project_command
        return _run_init(command, output_format=args.output_format)

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

    parser.print_help()
    return 0


def build_main(
    *,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
    audit_list_command: ListAuditLogCommandHandler,
    snapshots_list_command: ListSnapshotsCommandHandler,
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


def _print_expected_error(error: Exception, output_format: str) -> None:
    code = _error_code(error)
    detail = str(error)
    payload = {
        "ok": False,
        "error": {
            "code": code,
            "message": _error_message(error),
            "detail": detail,
            "recovery_hint": "Verifique o layout local e execute umem init na raiz do projeto.",
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
    if isinstance(error, InvalidConfigError):
        return "invalid_config"
    if isinstance(error, ValidationFailedError):
        return "validation_failed"
    return "storage_error"


def _error_message(error: Exception) -> str:
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
