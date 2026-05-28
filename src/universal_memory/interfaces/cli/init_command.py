import json
import os
import sys
import traceback
from collections.abc import Callable, Sequence
from dataclasses import asdict
from pathlib import Path
from typing import Annotated, Any

import click
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from universal_memory.application.memory import (
    AssembleContextSummaryCommand,
    AssembleContextSummaryResult,
    ContextHygieneCommand,
    ContextHygieneResult,
    GetMemoryStatusCommand,
    GetMemoryStatusResult,
    ListFactsCommand,
    ListFactsResult,
    PurgeFactCommand,
    PurgeFactResult,
    RememberFactCommand,
    RememberFactResult,
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
    ProjectLayoutPort,
    SnapshotFailedError,
    StorageError,
    ValidationFailedError,
)
from universal_memory.domain.entities import (
    AuditEventScope,
    ContextSummaryScope,
    Fact,
    FactScope,
    FactStatus,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.interfaces.errors import (
    DOMAIN_ERROR_TYPES,
    error_descriptor,
    error_payload,
    recovery_hint,
)

DEFAULT_CONTEXT_MAX_SIZE_CHARS = 4000
AUDIT_REFERENCE_PLACEHOLDER = "not-implemented-yet"
SetupProjectCommand = Callable[[Path], SetupProjectResult]
ListAuditLogCommandHandler = Callable[[ListAuditLogCommand], ListAuditLogResult]
ListSnapshotsCommandHandler = Callable[[ListSnapshotsCommand], ListSnapshotsResult]
RollbackCommandHandler = Callable[[RollbackCommand], RollbackResult]
RollbackPreviewHandler = Callable[[SnapshotScope], Snapshot]
StatusCommandHandler = Callable[[GetMemoryStatusCommand], GetMemoryStatusResult]
ContextCommandHandler = Callable[[AssembleContextSummaryCommand], AssembleContextSummaryResult]
RememberFactCommandHandler = Callable[[RememberFactCommand], RememberFactResult]
ListFactsCommandHandler = Callable[[ListFactsCommand], ListFactsResult]
PurgeFactCommandHandler = Callable[[PurgeFactCommand], PurgeFactResult]
ContextHygieneCommandHandler = Callable[[ContextHygieneCommand], ContextHygieneResult]
OutputFormatOption = Annotated[
    str | None,
    typer.Option(
        "--format",
        "-f",
        help="Formato de saida.",
        case_sensitive=False,
        click_type=click.Choice(["human", "json"], case_sensitive=False),
    ),
]
YesOption = Annotated[bool, typer.Option("--yes", "-y", help="Ignorar confirmacao interativa.")]


def _determine_output_format(argv: Sequence[str] | None) -> str:
    if argv is None:
        return "human"
    args = [arg.lower() for arg in argv]
    for i, arg in enumerate(args):
        if arg in ("--format", "-f") and i + 1 < len(args):
            return args[i + 1]
        if arg.startswith("--format="):
            return arg.split("=", 1)[1]
    return "human"


def main(  # noqa: PLR0913
    argv: Sequence[str] | None = None,
    *,
    setup_project_command: SetupProjectCommand | None = None,
    audit_list_command: ListAuditLogCommandHandler | None = None,
    snapshots_list_command: ListSnapshotsCommandHandler | None = None,
    rollback_command: RollbackCommandHandler | None = None,
    rollback_preview_command: RollbackPreviewHandler | None = None,
    status_command: StatusCommandHandler | None = None,
    context_command: ContextCommandHandler | None = None,
    remember_command: RememberFactCommandHandler | None = None,
    facts_list_command: ListFactsCommandHandler | None = None,
    facts_purge_command: PurgeFactCommandHandler | None = None,
    facts_hygiene_command: ContextHygieneCommandHandler | None = None,
) -> int:
    app = create_typer_app(
        setup_project_command=setup_project_command,
        audit_list_command=audit_list_command,
        snapshots_list_command=snapshots_list_command,
        rollback_command=rollback_command,
        rollback_preview_command=rollback_preview_command,
        status_command=status_command,
        context_command=context_command,
        remember_command=remember_command,
        facts_list_command=facts_list_command,
        facts_purge_command=facts_purge_command,
        facts_hygiene_command=facts_hygiene_command,
    )
    try:
        result = app(args=list(argv) if argv is not None else None, standalone_mode=False)
    except click.exceptions.ClickException as e:
        _stderr_console().print(f"[bold red]Erro:[/bold red] {e.format_message()}")
        return e.exit_code
    except click.exceptions.Exit as exit_error:
        code = exit_error.exit_code
        return int(code) if code is not None else 0
    except RuntimeError:
        raise
    except Exception as e:
        fmt = _determine_output_format(argv)
        _print_unexpected_error(e, output_format=fmt)
        return 1
    if isinstance(result, int):
        return result
    return 0


def create_typer_app(  # noqa: PLR0913, PLR0915
    *,
    setup_project_command: SetupProjectCommand | None = None,
    audit_list_command: ListAuditLogCommandHandler | None = None,
    snapshots_list_command: ListSnapshotsCommandHandler | None = None,
    rollback_command: RollbackCommandHandler | None = None,
    rollback_preview_command: RollbackPreviewHandler | None = None,
    status_command: StatusCommandHandler | None = None,
    context_command: ContextCommandHandler | None = None,
    remember_command: RememberFactCommandHandler | None = None,
    facts_list_command: ListFactsCommandHandler | None = None,
    facts_purge_command: PurgeFactCommandHandler | None = None,
    facts_hygiene_command: ContextHygieneCommandHandler | None = None,
) -> typer.Typer:
    app = typer.Typer(help="Universal Memory CLI", no_args_is_help=True)
    facts_app = typer.Typer(help="Gerenciar fatos de memoria")
    audit_app = typer.Typer(help="Inspecionar eventos de auditoria")
    snapshots_app = typer.Typer(help="Inspecionar snapshots")

    app.add_typer(facts_app, name="facts")
    app.add_typer(audit_app, name="audit")
    app.add_typer(snapshots_app, name="snapshots")

    @app.callback()
    def callback(
        ctx: typer.Context,
        output_format: Annotated[
            str,
            typer.Option(
                "--format",
                "-f",
                help="Formato global de saida.",
                case_sensitive=False,
                click_type=click.Choice(["human", "json"], case_sensitive=False),
            ),
        ] = "human",
    ) -> None:
        ctx.obj = {"output_format": output_format.lower()}

    @app.command("init")
    def init_command(ctx: typer.Context, output_format: OutputFormatOption = None) -> None:
        if setup_project_command is None:
            msg = "CLI setup_project_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_init(setup_project_command, _effective_format(ctx, output_format))
        )

    @app.command("status")
    def status(ctx: typer.Context, output_format: OutputFormatOption = None) -> None:
        if status_command is None:
            msg = "CLI status_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_status(status_command, output_format=_effective_format(ctx, output_format))
        )

    @app.command("context")
    def context(
        ctx: typer.Context,
        scope: Annotated[
            str,
            typer.Option(
                "--scope",
                help="Escopo de contexto.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = "project",
        max_size_chars: Annotated[
            int,
            typer.Option("--max-size-chars", min=1, help="Limite maximo do contexto em chars."),
        ] = DEFAULT_CONTEXT_MAX_SIZE_CHARS,
        agent_session_key: Annotated[
            str | None,
            typer.Option("--agent-session-key", help="Chave de sessao do agente."),
        ] = None,
        output_format: OutputFormatOption = None,
    ) -> None:
        if context_command is None:
            msg = "CLI context_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_context(
                context_command,
                output_format=_effective_format(ctx, output_format),
                scope=_context_scope(scope),
                max_size_chars=max_size_chars,
                agent_session_key=agent_session_key,
            )
        )

    @app.command("remember")
    def remember(
        ctx: typer.Context,
        content: Annotated[str, typer.Argument(help="Conteudo do fato a gravar.")],
        scope: Annotated[
            str,
            typer.Option(
                "--scope",
                help="Escopo do fato.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = "project",
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", help="Tag do fato. Pode ser usada multiplas vezes."),
        ] = None,
        output_format: OutputFormatOption = None,
    ) -> None:
        if remember_command is None:
            msg = "CLI remember_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_remember(
                remember_command,
                output_format=_effective_format(ctx, output_format),
                content=content,
                scope=_fact_scope(scope) or FactScope.project,
                tags=tags or [],
            )
        )

    @facts_app.command("list")
    def facts_list(
        ctx: typer.Context,
        scope: Annotated[
            str | None,
            typer.Option(
                "--scope",
                help="Filtro de escopo.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = None,
        status: Annotated[
            str | None,
            typer.Option(
                "--status",
                help="Filtro de status.",
                click_type=click.Choice(
                    ["active", "stale", "archived", "purged"], case_sensitive=False
                ),
            ),
        ] = None,
        output_format: OutputFormatOption = None,
    ) -> None:
        if facts_list_command is None:
            msg = "CLI facts_list_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_facts_list(
                facts_list_command,
                output_format=_effective_format(ctx, output_format),
                scope=_fact_scope(scope),
                status=_fact_status(status) if status is not None else FactStatus.active,
            )
        )

    @facts_app.command("purge")
    def facts_purge(
        ctx: typer.Context,
        id: Annotated[str | None, typer.Option("--id", help="ID do fato para purgar.")] = None,
        scope: Annotated[
            str | None,
            typer.Option(
                "--scope",
                help="Escopo para purgar.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = None,
        yes: YesOption = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if facts_purge_command is None:
            msg = "CLI facts_purge_command dependency was not configured."
            raise RuntimeError(msg)
        if (id is None and scope is None) or (id is not None and scope is not None):
            _print_expected_error(
                ValidationFailedError("Informe exatamente uma opcao: --id ou --scope."),
                output_format=_effective_format(ctx, output_format),
            )
            raise typer.Exit(code=1)
        raise typer.Exit(
            code=_run_facts_purge(
                facts_purge_command,
                output_format=_effective_format(ctx, output_format),
                id=id,
                scope=_fact_scope(scope),
                yes=yes,
            )
        )

    @facts_app.command("hygiene")
    def facts_hygiene(
        ctx: typer.Context,
        yes: YesOption = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if facts_hygiene_command is None:
            msg = "CLI facts_hygiene_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_facts_hygiene(
                facts_hygiene_command,
                output_format=_effective_format(ctx, output_format),
                yes=yes,
            )
        )

    @audit_app.command("list")
    def audit_list(
        ctx: typer.Context,
        scope: Annotated[
            str,
            typer.Option(
                "--scope",
                help="Filtro de escopo.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = "project",
        output_format: OutputFormatOption = None,
    ) -> None:
        if audit_list_command is None:
            msg = "CLI audit_list_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_audit_list(
                audit_list_command,
                output_format=_effective_format(ctx, output_format),
                scope=_audit_scope(scope),
            )
        )

    @snapshots_app.command("list")
    def snapshots_list(
        ctx: typer.Context,
        scope: Annotated[
            str,
            typer.Option(
                "--scope",
                help="Filtro de escopo.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = "project",
        output_format: OutputFormatOption = None,
    ) -> None:
        if snapshots_list_command is None:
            msg = "CLI snapshots_list_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_snapshots_list(
                snapshots_list_command,
                output_format=_effective_format(ctx, output_format),
                scope=_snapshot_scope(scope),
            )
        )

    @app.command("rollback")
    def rollback(
        ctx: typer.Context,
        scope: Annotated[
            str,
            typer.Option(
                "--scope",
                help="Escopo para rollback.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = "project",
        yes: YesOption = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if rollback_command is None:
            msg = "CLI rollback_command dependency was not configured."
            raise RuntimeError(msg)
        if rollback_preview_command is None:
            msg = "CLI rollback_preview_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_rollback(
                rollback_command,
                rollback_preview_command=rollback_preview_command,
                output_format=_effective_format(ctx, output_format),
                scope=_snapshot_scope(scope),
                yes=yes,
            )
        )

    return app


def build_main(  # noqa: PLR0913
    *,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
    audit_list_command: ListAuditLogCommandHandler,
    snapshots_list_command: ListSnapshotsCommandHandler,
    rollback_command: RollbackCommandHandler,
    rollback_preview_command: RollbackPreviewHandler,
    status_command: StatusCommandHandler,
    context_command: ContextCommandHandler,
    remember_command: RememberFactCommandHandler,
    facts_list_command: ListFactsCommandHandler,
    facts_purge_command: PurgeFactCommandHandler,
    facts_hygiene_command: ContextHygieneCommandHandler,
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
            context_command=context_command,
            remember_command=remember_command,
            facts_list_command=facts_list_command,
            facts_purge_command=facts_purge_command,
            facts_hygiene_command=facts_hygiene_command,
        )

    return configured_main


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


def _effective_format(ctx: typer.Context | None, output_format: str | None) -> str:
    if output_format is not None:
        return output_format.lower()
    if ctx is None:
        return "human"
    if isinstance(ctx.obj, dict):
        return str(ctx.obj.get("output_format", "human")).lower()
    parent = ctx.parent
    while parent is not None:
        if isinstance(parent.obj, dict):
            return str(parent.obj.get("output_format", "human")).lower()
        parent = parent.parent
    return "human"


def _stdout_console() -> Console:
    return Console(file=sys.stdout, width=200)


def _stderr_console() -> Console:
    return Console(file=sys.stderr, width=200)


def _confirm(prompt: str, default: bool = False) -> bool:
    try:
        answer = input(prompt)
    except (EOFError, KeyboardInterrupt):
        return False
    val = answer.strip().lower()
    if not val:
        return default
    return val in {"s", "sim", "y", "yes"}


def _run_init(command: SetupProjectCommand, output_format: str) -> int:
    try:
        if output_format == "json":
            result = command(Path.cwd())
        else:
            with _stderr_console().status("Inicializando scaffold do projeto...", spinner="dots"):
                result = command(Path.cwd())
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_init_output(result))

    return 0


def _run_status(command: StatusCommandHandler, *, output_format: str) -> int:
    try:
        result = command(GetMemoryStatusCommand(project_root=Path.cwd()))
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1
    except ValidationError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1
    except Exception as error:
        _print_unexpected_error(error, output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_status_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_status_output(result))

    return 0


def _run_context(
    command: ContextCommandHandler,
    *,
    output_format: str,
    scope: ContextSummaryScope,
    max_size_chars: int,
    agent_session_key: str | None = None,
) -> int:
    try:
        result = command(
            AssembleContextSummaryCommand(
                scope=scope,
                max_size_chars=max_size_chars,
                agent_session_key=agent_session_key,
            )
        )
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1
    except ValidationError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1
    except ValueError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1

    if output_format == "json":
        payload = _context_success_envelope(
            result,
            scope=scope,
            max_size_chars=max_size_chars,
        )
        print(json.dumps(payload, sort_keys=True))
    else:
        _stdout_console().print(_format_human_context_output(result))

    return 0


def _run_remember(
    command: RememberFactCommandHandler,
    *,
    output_format: str,
    content: str,
    scope: FactScope,
    tags: list[str],
) -> int:
    try:
        result = command(
            RememberFactCommand(
                content=content,
                scope=scope,
                source="cli",
                tags=tags,
                origin="cli",
            )
        )
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1
    except ValidationError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1
    except ValueError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_remember_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_remember_output(result))

    return 0


def _run_facts_list(
    command: ListFactsCommandHandler,
    *,
    output_format: str,
    scope: FactScope | None,
    status: FactStatus,
) -> int:
    try:
        result = command(ListFactsCommand(scope=scope, status=status))
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1
    except ValidationError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_facts_list_success_envelope(result, scope=scope), sort_keys=True))
    else:
        _stdout_console().print(_format_human_facts_list_output(result))

    return 0


def _run_facts_purge(
    command: PurgeFactCommandHandler,
    *,
    output_format: str,
    id: str | None,
    scope: FactScope | None,
    yes: bool,
) -> int:
    try:
        if output_format == "json" and not yes:
            raise ValidationFailedError(
                "A flag --yes / -y e obrigatoria para executar purge com saida JSON."
            )
        if output_format != "json":
            _stdout_console().print(_format_human_purge_preview(id=id, scope=scope))
            if not yes:
                if not _confirm("Confirmar purga permanente? [y/N]: ", default=False):
                    _stdout_console().print("Purga cancelada.")
                    return 1

        result = command(PurgeFactCommand(id=id, scope=scope, origin="cli"))
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_facts_purge_success_envelope(result, scope=scope), sort_keys=True))
    else:
        _stdout_console().print(_format_human_purge_success(result))

    return 0


def _run_facts_hygiene(
    command: ContextHygieneCommandHandler,
    *,
    output_format: str,
    yes: bool,
) -> int:
    scope = FactScope.project
    try:
        if output_format != "json":
            _stdout_console().print(
                "[yellow]Aviso: A execucao de fatos higiene ira otimizar e limpar "
                "o contexto de memoria, podendo arquivar fatos obsoletos.[/yellow]"
            )
            if not yes:
                if not _confirm("Deseja prosseguir com a higiene? [s/N]: ", default=False):
                    _stdout_console().print("Higiene cancelada.")
                    return 1

        if output_format == "json":
            result = command(ContextHygieneCommand(scope=scope))
        else:
            with _stderr_console().status("Executando higiene de contexto...", spinner="dots"):
                result = command(ContextHygieneCommand(scope=scope))
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_facts_hygiene_success_envelope(result, scope=scope), sort_keys=True))
    else:
        _stdout_console().print(_format_human_hygiene_success(result))

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
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1
    except ValidationError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_audit_success_envelope(result, scope=scope), sort_keys=True))
    else:
        _stdout_console().print(_format_human_audit_output(result))

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
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1
    except ValidationError as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_snapshots_success_envelope(result, scope=scope), sort_keys=True))
    else:
        _stdout_console().print(_format_human_snapshots_output(result))

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
            _stdout_console().print(_format_human_rollback_preview(preview))
            if not yes:
                if not _confirm("Deseja prosseguir com o rollback? [s/N]: ", default=False):
                    _stdout_console().print("Rollback cancelado.")
                    return 1

        if output_format == "json":
            result = command(RollbackCommand(scope=scope, origin="cli"))
        else:
            with _stderr_console().status("Restaurando snapshot (rollback)...", spinner="dots"):
                result = command(RollbackCommand(scope=scope, origin="cli"))
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_rollback_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_rollback_success(result))

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


def _context_success_envelope(
    result: AssembleContextSummaryResult,
    *,
    scope: ContextSummaryScope,
    max_size_chars: int,
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "context",
        "scope": scope.value,
        "data": _context_payload(result, max_size_chars=max_size_chars),
        "warnings": [],
    }


def _remember_success_envelope(result: RememberFactResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "remember",
        "scope": result.fact.scope.value,
        "data": _remember_payload(result),
        "warnings": [],
    }


def _facts_list_success_envelope(
    result: ListFactsResult, *, scope: FactScope | None
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "facts.list",
        "scope": scope.value if scope is not None else "all",
        "data": {"facts": [_fact_payload(fact) for fact in result.facts]},
        "warnings": [],
    }


def _facts_purge_success_envelope(
    result: PurgeFactResult, *, scope: FactScope | None
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "facts.purge",
        "scope": scope.value if scope is not None else "fact",
        "data": {
            "purged_count": result.purged_count,
            "affected_ids": result.affected_ids,
            "audit_reference": result.audit_reference,
        },
        "warnings": [],
    }


def _facts_hygiene_success_envelope(
    result: ContextHygieneResult, *, scope: FactScope
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "facts.hygiene",
        "scope": scope.value,
        "data": {
            "stale_count": result.stale_count,
            "archived_count": result.archived_count,
            "audit_reference": result.audit_reference,
        },
        "warnings": [],
    }


def _init_payload(result: SetupProjectResult) -> dict[str, Any]:
    project_root = result.project_path
    return {
        "project_path": _relative_path(result.project_path, project_root),
        "config_path": _relative_path(result.config_path, project_root),
        "memory_path": _relative_path(result.memory_path, project_root),
        "audit_path": _relative_path(result.audit_path, project_root),
        "snapshots_path": _relative_path(result.snapshots_path, project_root),
        "created": result.created_paths,
        "already_initialized": result.already_initialized,
        "audit_reference": AUDIT_REFERENCE_PLACEHOLDER,
    }


def _fact_payload(fact: Fact) -> dict[str, Any]:
    return {
        "id": fact.id,
        "content": fact.content,
        "scope": fact.scope.value,
        "source": fact.source,
        "status": fact.status.value,
        "recurrence_count": fact.recurrence_count,
        "tags": fact.tags,
        "metadata": fact.metadata,
        "created_at": format_utc_iso(fact.created_at),
        "updated_at": format_utc_iso(fact.updated_at),
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


def _context_payload(
    result: AssembleContextSummaryResult,
    *,
    max_size_chars: int,
) -> dict[str, Any]:
    summary = result.context_summary
    markdown_size = len(result.context_markdown)
    return {
        "project_summary": summary.project_summary,
        "universal_preferences": summary.universal_preferences,
        "active_rules": summary.active_rules,
        "source_fact_ids": result.included_fact_ids,
        "truncated": markdown_size >= max_size_chars,
        "token_estimate": max(1, round(markdown_size / 4)),
        "last_read_at": format_utc_iso(summary.created_at),
    }


def _remember_payload(result: RememberFactResult) -> dict[str, Any]:
    fact = result.fact
    return {
        "fact_id": fact.id,
        "scope": fact.scope.value,
        "status": fact.status.value,
        "tags": fact.tags,
        "created_at": format_utc_iso(fact.created_at),
        "audit_reference": result.audit_reference,
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


def _format_human_context_output(result: AssembleContextSummaryResult) -> str:
    summary = result.context_summary
    lines = [
        "Contexto montado.",
        f"Resumo do projeto: {summary.project_summary or '(vazio)'}",
        f"Preferencias universais: {summary.universal_preferences or '(vazio)'}",
        f"Regras ativas: {summary.active_rules or '(vazio)'}",
        "Fontes: "
        f"{', '.join(result.included_fact_ids) if result.included_fact_ids else '(nenhuma)'}",
    ]
    return "\n".join(lines)


def _format_human_remember_output(result: RememberFactResult) -> str:
    fact = result.fact
    return "\n".join(
        [
            "Fato salvo.",
            f"ID: {fact.id}",
            f"Escopo: {fact.scope.value}",
            f"Status: {fact.status.value}",
            f"Tags: {', '.join(fact.tags) if fact.tags else '(nenhuma)'}",
            f"Auditoria: {result.audit_reference}",
        ]
    )


def _format_human_facts_list_output(result: ListFactsResult) -> Table | str:
    if not result.facts:
        return "Nenhum fato encontrado."

    table = Table(title="Fatos:", show_header=True)
    table.add_column("ID")
    table.add_column("Escopo")
    table.add_column("Status")
    table.add_column("Fonte")
    table.add_column("Conteudo")
    for fact in result.facts:
        table.add_row(
            fact.id,
            fact.scope.value,
            fact.status.value,
            fact.source,
            fact.content,
        )
    return table


def _format_human_purge_preview(*, id: str | None, scope: FactScope | None) -> str:
    target = f"ID: {id}" if id is not None else f"Escopo: {scope.value if scope else 'n/a'}"
    return "\n".join(
        [
            "Purga permanente selecionada:",
            target,
            "Caminho afetado: .umem/memory/facts.jsonl",
            "Snapshot: criado pelo pipeline seguro quando configurado",
            "Auditoria: evento de mutacao segura esperado",
            "Padrao: nao confirmar.",
        ]
    )


def _format_human_purge_success(result: PurgeFactResult) -> str:
    return "\n".join(
        [
            "Purga concluida.",
            f"Itens purgados: {result.purged_count}",
            f"IDs afetados: {', '.join(result.affected_ids)}",
            f"Auditoria: {result.audit_reference}",
        ]
    )


def _format_human_hygiene_success(result: ContextHygieneResult) -> str:
    return "\n".join(
        [
            "Higiene de contexto concluida.",
            f"Fatos marcados como stale: {result.stale_count}",
            f"Fatos arquivados: {result.archived_count}",
            f"Auditoria: {result.audit_reference}",
        ]
    )


def _format_human_audit_output(result: ListAuditLogResult) -> Table | str:
    if not result.events:
        return "Nenhum evento de auditoria encontrado."

    table = Table(title="Eventos de auditoria:", show_header=True)
    table.add_column("Timestamp")
    table.add_column("Escopo")
    table.add_column("Origem")
    table.add_column("Acao")
    table.add_column("Resultado")
    table.add_column("Auditoria")
    table.add_column("Snapshot")
    for event in result.events:
        table.add_row(
            event.timestamp,
            event.scope,
            event.origin,
            event.action,
            event.result,
            f"audit={event.audit_reference}",
            f"snapshot={event.snapshot_reference}",
        )
    return table


def _format_human_snapshots_output(result: ListSnapshotsResult) -> Table | str:
    if not result.snapshots:
        return "Nenhum snapshot encontrado."

    table = Table(title="Snapshots:", show_header=True)
    table.add_column("Timestamp")
    table.add_column("Escopo")
    table.add_column("Origem")
    table.add_column("Acao")
    table.add_column("Arquivo")
    table.add_column("Hash")
    table.add_column("Manifesto")
    for snapshot in result.snapshots:
        table.add_row(
            snapshot.timestamp,
            snapshot.scope,
            snapshot.origin,
            snapshot.action,
            snapshot.relative_path,
            snapshot.hash,
            snapshot.manifest_path,
        )
    return table


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
    return recovery_hint(error)


def _print_expected_error(error: Exception, output_format: str) -> None:
    payload = {
        "ok": False,
        "error": error_payload(error, message_locale="pt-BR"),
    }

    if output_format == "json":
        print(json.dumps(payload, sort_keys=True))
        return

    panel = Panel(
        Text.from_markup(
            "\n".join(
                [
                    f"[bold]Falha:[/bold] {payload['error']['message']}",
                    f"[bold]Detalhe:[/bold] {payload['error']['detail']}",
                    f"[bold]Recuperacao:[/bold] {payload['error']['recovery_hint']}",
                ]
            )
        ),
        title="Erro",
        border_style="red",
    )
    _stderr_console().print(panel)


def _print_unexpected_error(error: Exception, output_format: str) -> None:
    if os.environ.get("UMEM_DEBUG_ERRORS") == "1":
        traceback.print_exc(file=sys.stderr)
    _print_expected_error(error, output_format=output_format)


def _error_code(error: Exception) -> str:
    return error_descriptor(error).slug


def _error_message(error: Exception) -> str:
    return error_descriptor(error).cli_message


def _relative_path(path: Path, project_root: Path) -> str:
    try:
        return path.resolve().relative_to(project_root.resolve()).as_posix()
    except (ValueError, OSError, RuntimeError):
        return path.as_posix()


def _audit_scope(value: str) -> AuditEventScope:
    return AuditEventScope.global_ if value == "global" else AuditEventScope.project


def _snapshot_scope(value: str) -> SnapshotScope:
    return SnapshotScope.global_ if value == "global" else SnapshotScope.project


def _fact_scope(value: str | None) -> FactScope | None:
    if value is None:
        return None
    return FactScope.global_ if value == "global" else FactScope.project


def _context_scope(value: str) -> ContextSummaryScope:
    return ContextSummaryScope.global_ if value == "global" else ContextSummaryScope.project


def _fact_status(value: str) -> FactStatus:
    return FactStatus(value)
