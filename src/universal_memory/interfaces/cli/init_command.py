import argparse
import json
import sys
from collections.abc import Callable, Sequence
from pathlib import Path
from typing import Any

from universal_memory.application.onboarding.setup_project import (
    SetupProjectResult,
    setup_project,
)
from universal_memory.domain import (
    ConfigValidationPort,
    InvalidConfigError,
    ProjectLayoutPort,
    StorageError,
    ValidationFailedError,
)

AUDIT_REFERENCE_PLACEHOLDER = "not-implemented-yet"
SetupProjectCommand = Callable[[Path], SetupProjectResult]


def main(
    argv: Sequence[str] | None = None,
    *,
    setup_project_command: SetupProjectCommand | None = None,
) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command == "init":
        if setup_project_command is None:
            msg = "CLI setup_project_command dependency was not configured."
            raise RuntimeError(msg)
        command = setup_project_command
        return _run_init(command, output_format=args.output_format)

    parser.print_help()
    return 0


def build_main(
    *,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
) -> Callable[[Sequence[str] | None], int]:
    command = _build_setup_project_command(
        layout_port=layout_port,
        config_validation_port=config_validation_port,
    )

    def configured_main(argv: Sequence[str] | None = None) -> int:
        return main(argv, setup_project_command=command)

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


def _success_envelope(result: SetupProjectResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "init",
        "scope": "project",
        "data": _init_payload(result),
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
