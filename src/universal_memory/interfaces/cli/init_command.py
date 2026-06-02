import json
import os
import sys
import traceback
from collections.abc import Callable, Sequence
from dataclasses import asdict
from inspect import signature
from pathlib import Path
from typing import Annotated, Any

import click
import typer
from pydantic import ValidationError
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from universal_memory.application.host import (
    ConfigureHostCommand,
    ConfigureHostResult,
    SyncInstructionsCommand,
    SyncInstructionsResult,
)
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
    DEFAULT_ENABLED_HOST_IDS,
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
from universal_memory.application.skills import (
    ActivateSkillCommand,
    ActivateSkillResult,
    DeactivateSkillCommand,
    DeactivateSkillResult,
    GenerateSkillCommand,
    GenerateSkillResult,
    GetSkillDetailCommand,
    GetSkillDetailResult,
    ListSkillsCommand,
    ListSkillsResult,
    ProposeSkillCommand,
    ProposeSkillDecision,
    ProposeSkillResult,
    UpdateSkillCommand,
    UpdateSkillResult,
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
    LatentSkillScope,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.interfaces.cli.message_catalog import human_message, project_locale
from universal_memory.interfaces.errors import (
    DOMAIN_ERROR_TYPES,
    error_descriptor,
    error_payload,
    recovery_hint,
)

DEFAULT_CONTEXT_MAX_SIZE_CHARS = 4000
AUDIT_REFERENCE_PLACEHOLDER = "not-implemented-yet"
INIT_SPLASH_MARKER = "USB"
INIT_SPLASH_LINES = (
    "umem",
    "[USB]====[universal-memory]====[terminal]",
    "portable memory for AI agents",
)
SetupProjectCommand = (
    Callable[[Path, list[str] | None], SetupProjectResult] | Callable[[Path], SetupProjectResult]
)
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
ConfigureHostCommandHandler = Callable[[ConfigureHostCommand], ConfigureHostResult]
SyncInstructionsCommandHandler = Callable[[SyncInstructionsCommand], SyncInstructionsResult]
ProposeSkillCommandHandler = Callable[[ProposeSkillCommand], ProposeSkillResult]
GenerateSkillCommandHandler = Callable[[GenerateSkillCommand], GenerateSkillResult]
ListSkillsCommandHandler = Callable[[ListSkillsCommand], ListSkillsResult]
GetSkillDetailCommandHandler = Callable[[GetSkillDetailCommand], GetSkillDetailResult]
ActivateSkillCommandHandler = Callable[[ActivateSkillCommand], ActivateSkillResult]
DeactivateSkillCommandHandler = Callable[[DeactivateSkillCommand], DeactivateSkillResult]
UpdateSkillCommandHandler = Callable[[UpdateSkillCommand], UpdateSkillResult]
OutputFormatOption = Annotated[
    str | None,
    typer.Option(
        "--format",
        "-f",
        help="Output format.",
        case_sensitive=False,
        click_type=click.Choice(["human", "json"], case_sensitive=False),
    ),
]
YesOption = Annotated[bool, typer.Option("--yes", "-y", help="Skip interactive confirmation.")]


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
    host_setup_command: ConfigureHostCommandHandler | None = None,
    host_check_command: ConfigureHostCommandHandler | None = None,
    host_sync_command: SyncInstructionsCommandHandler | None = None,
    propose_skill_command: ProposeSkillCommandHandler | None = None,
    generate_skill_command: GenerateSkillCommandHandler | None = None,
    list_skills_command: ListSkillsCommandHandler | None = None,
    get_skill_detail_command: GetSkillDetailCommandHandler | None = None,
    activate_skill_command: ActivateSkillCommandHandler | None = None,
    deactivate_skill_command: DeactivateSkillCommandHandler | None = None,
    update_skill_command: UpdateSkillCommandHandler | None = None,
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
        host_setup_command=host_setup_command,
        host_check_command=host_check_command,
        host_sync_command=host_sync_command,
        propose_skill_command=propose_skill_command,
        generate_skill_command=generate_skill_command,
        list_skills_command=list_skills_command,
        get_skill_detail_command=get_skill_detail_command,
        activate_skill_command=activate_skill_command,
        deactivate_skill_command=deactivate_skill_command,
        update_skill_command=update_skill_command,
    )
    try:
        result = app(args=list(argv) if argv is not None else None, standalone_mode=False)
    except click.exceptions.ClickException as e:
        _stderr_console().print(f"[bold red]Error:[/bold red] {e.format_message()}")
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
    host_setup_command: ConfigureHostCommandHandler | None = None,
    host_check_command: ConfigureHostCommandHandler | None = None,
    host_sync_command: SyncInstructionsCommandHandler | None = None,
    propose_skill_command: ProposeSkillCommandHandler | None = None,
    generate_skill_command: GenerateSkillCommandHandler | None = None,
    list_skills_command: ListSkillsCommandHandler | None = None,
    get_skill_detail_command: GetSkillDetailCommandHandler | None = None,
    activate_skill_command: ActivateSkillCommandHandler | None = None,
    deactivate_skill_command: DeactivateSkillCommandHandler | None = None,
    update_skill_command: UpdateSkillCommandHandler | None = None,
) -> typer.Typer:
    app = typer.Typer(help="Universal Memory CLI", no_args_is_help=True)
    facts_app = typer.Typer(help="Gerenciar fatos de memoria")
    audit_app = typer.Typer(help="Inspecionar eventos de auditoria")
    snapshots_app = typer.Typer(help="Inspecionar snapshots")
    host_app = typer.Typer(help="Configurar hosts de agente")
    skills_app = typer.Typer(help="Gerenciar skills")

    app.add_typer(facts_app, name="facts")
    app.add_typer(audit_app, name="audit")
    app.add_typer(snapshots_app, name="snapshots")
    app.add_typer(host_app, name="host")
    app.add_typer(skills_app, name="skills")

    @app.callback()
    def callback(
        ctx: typer.Context,
        output_format: Annotated[
            str,
            typer.Option(
                "--format",
                "-f",
                help="Global output format.",
                case_sensitive=False,
                click_type=click.Choice(["human", "json"], case_sensitive=False),
            ),
        ] = "human",
    ) -> None:
        ctx.obj = {"output_format": output_format.lower()}

    @app.command("init")
    def init_command(
        ctx: typer.Context,
        hosts: Annotated[
            list[str] | None,
            typer.Option("--hosts", help="Host to configure. May be used multiple times."),
        ] = None,
        yes: YesOption = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if setup_project_command is None:
            msg = "CLI setup_project_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_init(
                setup_project_command,
                _effective_format(ctx, output_format),
                selected_hosts=hosts,
                yes=yes,
                host_setup_command=host_setup_command,
                host_check_command=host_check_command,
            )
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

    @host_app.command("setup")
    def host_setup(  # noqa: PLR0913
        ctx: typer.Context,
        host_id: Annotated[str, typer.Argument(help="Host a configurar.")],
        yes: YesOption = False,
        max_lines: Annotated[
            int, typer.Option("--max-lines", help="Limite maximo de linhas.")
        ] = 100,
        max_chars: Annotated[
            int, typer.Option("--max-chars", help="Limite maximo de caracteres.")
        ] = 4000,
        output_format: OutputFormatOption = None,
    ) -> None:
        if host_setup_command is None:
            msg = "CLI host_setup_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_host_setup(
                host_setup_command,
                output_format=_effective_format(ctx, output_format),
                host_id=host_id,
                yes=yes,
                max_lines=max_lines,
                max_chars=max_chars,
            )
        )

    @host_app.command("check")
    def host_check(
        ctx: typer.Context,
        host_id: Annotated[str, typer.Argument(help="Host a validar.")],
        max_lines: Annotated[
            int, typer.Option("--max-lines", help="Limite maximo de linhas.")
        ] = 100,
        max_chars: Annotated[
            int, typer.Option("--max-chars", help="Limite maximo de caracteres.")
        ] = 4000,
        output_format: OutputFormatOption = None,
    ) -> None:
        if host_check_command is None:
            msg = "CLI host_check_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_host_check(
                host_check_command,
                output_format=_effective_format(ctx, output_format),
                host_id=host_id,
                max_lines=max_lines,
                max_chars=max_chars,
            )
        )

    @host_app.command("sync")
    def host_sync(
        ctx: typer.Context,
        apply: Annotated[
            bool,
            typer.Option(
                "--apply/--no-apply",
                help="Aplicar a sincronizacao ou apenas exibir preview.",
            ),
        ] = False,
        yes: YesOption = False,
        host_id: Annotated[
            list[str] | None,
            typer.Option("--host", help="Host a sincronizar. Pode ser usado multiplas vezes."),
        ] = None,
        output_format: OutputFormatOption = None,
    ) -> None:
        if host_sync_command is None:
            msg = "CLI host_sync_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_host_sync(
                host_sync_command,
                output_format=_effective_format(ctx, output_format),
                host_ids=host_id or ["codex", "claude_code"],
                apply=apply,
                yes=yes,
            )
        )

    @skills_app.command("propose")
    def skills_propose(
        ctx: typer.Context,
        latent_skill_id: Annotated[str, typer.Argument(help="ID da latent skill.")],
        decision: Annotated[
            str | None,
            typer.Option(
                "--decision",
                help="Decisao explicita: sim, sempre ou nao.",
                click_type=click.Choice(
                    ["sim", "s", "sempre", "e", "nao", "não", "n"], case_sensitive=False
                ),
            ),
        ] = None,
        yes: YesOption = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if propose_skill_command is None:
            msg = "CLI propose_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_propose(
                propose_skill_command,
                output_format=_effective_format(ctx, output_format),
                latent_skill_id=latent_skill_id,
                decision=_skill_decision(decision),
                yes=yes,
            )
        )

    @skills_app.command("list")
    def skills_list(ctx: typer.Context, output_format: OutputFormatOption = None) -> None:
        if list_skills_command is None:
            msg = "CLI list_skills_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_list(
                list_skills_command,
                output_format=_effective_format(ctx, output_format),
            )
        )

    @skills_app.command("detail")
    def skills_detail(
        ctx: typer.Context,
        name_or_id: Annotated[str, typer.Argument(help="Nome ou ID da skill.")],
        output_format: OutputFormatOption = None,
    ) -> None:
        if get_skill_detail_command is None:
            msg = "CLI get_skill_detail_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_detail(
                get_skill_detail_command,
                output_format=_effective_format(ctx, output_format),
                name_or_id=name_or_id,
            )
        )

    @skills_app.command("generate")
    def skills_generate(
        ctx: typer.Context,
        latent_skill_id: Annotated[str, typer.Argument(help="ID da latent skill aprovada.")],
        yes: YesOption = False,
        update_existing: Annotated[
            bool,
            typer.Option(
                "--update-existing",
                help="Atualizar skill existente em vez de criar slug alternativo.",
            ),
        ] = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if generate_skill_command is None:
            msg = "CLI generate_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_generate(
                generate_skill_command,
                output_format=_effective_format(ctx, output_format),
                latent_skill_id=latent_skill_id,
                yes=yes,
                update_existing=update_existing,
            )
        )

    @skills_app.command("activate")
    def skills_activate(
        ctx: typer.Context,
        latent_skill_id: Annotated[str, typer.Argument(help="ID da latent skill.")],
        output_format: OutputFormatOption = None,
    ) -> None:
        if activate_skill_command is None:
            msg = "CLI activate_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_activate(
                activate_skill_command,
                output_format=_effective_format(ctx, output_format),
                latent_skill_id=latent_skill_id,
            )
        )

    @skills_app.command("deactivate")
    def skills_deactivate(
        ctx: typer.Context,
        latent_skill_id: Annotated[str, typer.Argument(help="ID da latent skill.")],
        output_format: OutputFormatOption = None,
    ) -> None:
        if deactivate_skill_command is None:
            msg = "CLI deactivate_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_deactivate(
                deactivate_skill_command,
                output_format=_effective_format(ctx, output_format),
                latent_skill_id=latent_skill_id,
            )
        )

    @skills_app.command("update")
    def skills_update(  # noqa: PLR0913
        ctx: typer.Context,
        latent_skill_id: Annotated[str, typer.Argument(help="ID da latent skill.")],
        name: Annotated[str | None, typer.Option("--name", help="Novo nome da skill.")] = None,
        description: Annotated[
            str | None,
            typer.Option("--description", help="Nova descricao da skill."),
        ] = None,
        trigger: Annotated[
            list[str] | None,
            typer.Option("--trigger", help="Gatilho da skill. Pode ser usado multiplas vezes."),
        ] = None,
        file: Annotated[
            Path | None,
            typer.Option("--file", help="Arquivo markdown com novo conteudo da skill."),
        ] = None,
        output_format: OutputFormatOption = None,
    ) -> None:
        if update_skill_command is None:
            msg = "CLI update_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_update(
                update_skill_command,
                output_format=_effective_format(ctx, output_format),
                latent_skill_id=latent_skill_id,
                name=name,
                description=description,
                triggers=trigger,
                file=file,
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
    host_setup_command: ConfigureHostCommandHandler,
    host_check_command: ConfigureHostCommandHandler,
    host_sync_command: SyncInstructionsCommandHandler,
    propose_skill_command: ProposeSkillCommandHandler | None = None,
    generate_skill_command: GenerateSkillCommandHandler | None = None,
    list_skills_command: ListSkillsCommandHandler | None = None,
    get_skill_detail_command: GetSkillDetailCommandHandler | None = None,
    activate_skill_command: ActivateSkillCommandHandler | None = None,
    deactivate_skill_command: DeactivateSkillCommandHandler | None = None,
    update_skill_command: UpdateSkillCommandHandler | None = None,
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
            host_setup_command=host_setup_command,
            host_check_command=host_check_command,
            host_sync_command=host_sync_command,
            propose_skill_command=propose_skill_command,
            generate_skill_command=generate_skill_command,
            list_skills_command=list_skills_command,
            get_skill_detail_command=get_skill_detail_command,
            activate_skill_command=activate_skill_command,
            deactivate_skill_command=deactivate_skill_command,
            update_skill_command=update_skill_command,
        )

    return configured_main


def _build_setup_project_command(
    *,
    layout_port: ProjectLayoutPort,
    config_validation_port: ConfigValidationPort,
) -> SetupProjectCommand:
    def command(
        project_root: Path,
        enabled_host_ids: list[str] | None = None,
    ) -> SetupProjectResult:
        return setup_project(
            project_root,
            layout_port=layout_port,
            config_validation_port=config_validation_port,
            enabled_host_ids=enabled_host_ids,
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


def _stream_is_tty(stream: Any) -> bool:
    try:
        return bool(stream.isatty())
    except Exception:
        return False


def _ci_environment_enabled() -> bool:
    return bool(os.environ.get("CI"))


def _terminal_color_enabled() -> bool:
    if "NO_COLOR" in os.environ:
        return False
    return os.environ.get("TERM", "") != "dumb"


def _should_render_init_splash(output_format: str) -> bool:
    return (
        output_format != "json"
        and _stream_is_tty(sys.stdout)
        and _stream_is_tty(sys.stdin)
        and not _ci_environment_enabled()
    )


def _render_init_splash() -> None:
    banner = "\n".join(INIT_SPLASH_LINES) + "\n"
    if _terminal_color_enabled():
        banner = (
            f"\x1b[36m{INIT_SPLASH_LINES[0]}\x1b[0m\n"
            f"\x1b[90m{INIT_SPLASH_LINES[1]}\x1b[0m\n"
            f"{INIT_SPLASH_LINES[2]}\n"
        )
    sys.stdout.write(banner)


def _confirm(prompt: str, default: bool = False) -> bool:
    answer = input(prompt)
    val = answer.strip().lower()
    if not val:
        return default
    return val in {"s", "sim", "y", "yes"}


def _run_init(  # noqa: PLR0913
    command: SetupProjectCommand,
    output_format: str,
    *,
    selected_hosts: list[str] | None = None,
    yes: bool = False,
    host_setup_command: ConfigureHostCommandHandler | None = None,
    host_check_command: ConfigureHostCommandHandler | None = None,
) -> int:
    locale = project_locale(Path.cwd()) if output_format != "json" else "en"
    try:
        if _should_render_init_splash(output_format):
            _render_init_splash()
        host_ids = _selected_init_hosts(
            selected_hosts,
            output_format=output_format,
            yes=yes,
            locale=locale,
        )
        if output_format == "json":
            result = _execute_setup_project(command, Path.cwd(), host_ids)
        else:
            with _stderr_console().status(
                human_message("Initializing project scaffold...", locale=locale), spinner="dots"
            ):
                result = _execute_setup_project(command, Path.cwd(), host_ids)
            locale = project_locale(Path.cwd())
        host_results = _configure_init_hosts(
            host_ids,
            output_format=output_format,
            locale=locale,
            host_setup_command=host_setup_command,
            host_check_command=host_check_command,
        )
    except (KeyboardInterrupt, EOFError):
        _stdout_console().print(
            "\n" + human_message("Operation cancelled by user.", locale=locale)
        )
        return 1
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format, locale=locale)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format, locale=locale)
        return 1

    if output_format == "json":
        payload = _success_envelope(result)
        if host_results:
            payload["hosts"] = [asdict(res) for res in host_results]
        print(json.dumps(payload, sort_keys=True))
    else:
        _stdout_console().print(_format_human_init_output(result, locale=locale))
        if host_results:
            _stdout_console().print(_format_human_init_host_results(host_results, locale=locale))

    return 0


def _execute_setup_project(
    command: SetupProjectCommand,
    project_root: Path,
    enabled_host_ids: list[str],
) -> SetupProjectResult:
    try:
        sig = signature(command)
        params = list(sig.parameters.values())
        has_var_args = any(p.kind in (p.VAR_POSITIONAL, p.VAR_KEYWORD) for p in params)
        positional_params = [
            p for p in params if p.kind in (p.POSITIONAL_ONLY, p.POSITIONAL_OR_KEYWORD)
        ]
        min_positional_args = 2
        if (
            len(positional_params) >= min_positional_args
            or has_var_args
            or "enabled_host_ids" in sig.parameters
        ):
            return command(project_root, enabled_host_ids)  # type: ignore
    except (ValueError, TypeError):
        pass
    return command(project_root)  # type: ignore


def _selected_init_hosts(
    hosts: list[str] | None,
    *,
    output_format: str,
    yes: bool,
    locale: str = "en",
) -> list[str]:
    if hosts:
        return _normalize_supported_hosts(hosts)
    if output_format == "json" or yes:
        return list(DEFAULT_ENABLED_HOST_IDS)
    if not sys.stdin.isatty():
        return list(DEFAULT_ENABLED_HOST_IDS)

    selected = []
    prompts = {
        "codex": human_message(
            "Configure host 'codex' (AGENTS.md support)? [Y/n]: ", locale=locale
        ),
        "claude_code": human_message(
            "Configure host 'claude_code' (CLAUDE.md support)? [Y/n]: ", locale=locale
        ),
    }
    for host_id in DEFAULT_ENABLED_HOST_IDS:
        if _confirm(prompts[host_id], default=True):
            selected.append(host_id)
    return selected


def _normalize_supported_hosts(hosts: list[str]) -> list[str]:
    normalized: list[str] = []
    for host_id in hosts:
        cleaned = host_id.strip().lower()
        if cleaned not in normalized:
            normalized.append(cleaned)
    unsupported = [host_id for host_id in normalized if host_id not in DEFAULT_ENABLED_HOST_IDS]
    if unsupported:
        raise ValidationFailedError(f"Unsupported hosts: {', '.join(unsupported)}")
    return normalized


def _configure_init_hosts(
    host_ids: list[str],
    *,
    output_format: str,
    locale: str = "en",
    host_setup_command: ConfigureHostCommandHandler | None,
    host_check_command: ConfigureHostCommandHandler | None,
) -> list[ConfigureHostResult]:
    if host_ids and (host_setup_command is None or host_check_command is None):
        _stderr_console().print(
            "[yellow]Warning: CLI host_setup_command or "
            "host_check_command dependency was not configured. "
            "Skipping automatic host setup.[/yellow]"
        )
        return []
    if not host_ids:
        return []

    if host_setup_command is None or host_check_command is None:
        raise ValidationFailedError("CLI host dependencies were not configured.")

    results: list[ConfigureHostResult] = []
    for host_id in host_ids:
        try:
            setup_result = host_setup_command(
                ConfigureHostCommand(host_id=host_id, apply=True, origin="cli_init")
            )
            check_result = host_check_command(
                ConfigureHostCommand(host_id=host_id, apply=False, check=True, origin="cli_init")
            )
            results.extend([setup_result, check_result])
            if output_format != "json":
                for step in check_result.manual_steps:
                    _stdout_console().print(
                        human_message(
                            "Pending manual step ({host_id}): {step}",
                            locale=locale,
                            host_id=host_id,
                            step=step,
                        )
                    )
        except Exception as error:
            msg = human_message(
                "Host setup failed for '{host_id}': {error}",
                locale=locale,
                host_id=host_id,
                error=error,
            )
            raise ValidationFailedError(msg) from error
    return results


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


def _run_host_setup(  # noqa: PLR0913
    command: ConfigureHostCommandHandler,
    *,
    output_format: str,
    host_id: str,
    yes: bool,
    max_lines: int,
    max_chars: int,
) -> int:
    try:
        if output_format == "json" and not yes:
            raise ValidationFailedError(
                "A flag --yes / -y e obrigatoria para executar host setup com saida JSON."
            )
        if output_format != "json":
            preview = command(
                ConfigureHostCommand(
                    host_id=host_id,
                    apply=False,
                    max_managed_lines=max_lines,
                    max_managed_chars=max_chars,
                    origin="cli",
                )
            )
            _stdout_console().print(_format_human_host_plan(preview, operation="setup"))
            if not yes:
                if not _confirm("Aplicar configuracao do host? [s/N]: ", default=False):
                    _stdout_console().print("Setup de host cancelado.")
                    return 1

        result = command(
            ConfigureHostCommand(
                host_id=host_id,
                apply=True,
                max_managed_lines=max_lines,
                max_managed_chars=max_chars,
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
        print(json.dumps(_host_success_envelope(result, operation="host_setup"), sort_keys=True))
    else:
        _stdout_console().print(_format_human_host_success(result, operation="setup"))
    return 0


def _run_host_check(
    command: ConfigureHostCommandHandler,
    *,
    output_format: str,
    host_id: str,
    max_lines: int,
    max_chars: int,
) -> int:
    try:
        result = command(
            ConfigureHostCommand(
                host_id=host_id,
                apply=False,
                check=True,
                max_managed_lines=max_lines,
                max_managed_chars=max_chars,
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
        print(json.dumps(_host_success_envelope(result, operation="host_check"), sort_keys=True))
    else:
        _stdout_console().print(_format_human_host_success(result, operation="check"))
    return 0


def _run_host_sync(
    command: SyncInstructionsCommandHandler,
    *,
    output_format: str,
    host_ids: list[str],
    apply: bool,
    yes: bool,
) -> int:
    try:
        if apply and output_format == "json" and not yes:
            raise ValidationFailedError(
                "A flag --yes / -y e obrigatoria para executar host sync com saida JSON."
            )
        if apply and output_format != "json":
            preview = command(
                SyncInstructionsCommand(
                    host_ids=host_ids,
                    apply=False,
                    origin="cli",
                )
            )
            _stdout_console().print(_format_human_sync_plan(preview))
            if not yes:
                if not _confirm("Aplicar sincronizacao de instrucoes? [s/N]: ", default=False):
                    _stdout_console().print("Sincronizacao de instrucoes cancelada.")
                    return 1

        result = command(
            SyncInstructionsCommand(
                host_ids=host_ids,
                apply=apply,
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
        print(json.dumps(_host_success_envelope(result, operation="host_sync"), sort_keys=True))
    else:
        if not apply:
            _stdout_console().print(_format_human_sync_plan(result))
            _stdout_console().print()
        _stdout_console().print(_format_human_sync_success(result))
    return 0


def _run_skills_list(
    command: ListSkillsCommandHandler,
    *,
    output_format: str,
) -> int:
    try:
        result = command(ListSkillsCommand())
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_read_error(error), output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_list_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_list(result))
    return 0


def _run_skills_detail(
    command: GetSkillDetailCommandHandler,
    *,
    output_format: str,
    name_or_id: str,
) -> int:
    try:
        result = command(GetSkillDetailCommand(name_or_id=name_or_id))
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_read_error(error), output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_detail_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_detail(result))
    return 0


def _map_skill_read_error(error: Exception) -> Exception:
    if isinstance(error, KeyError):
        return ValidationFailedError("Skill nao encontrada.")
    if isinstance(error, (ValidationError, ValueError)):
        return ValidationFailedError(str(error))
    if isinstance(error, OSError) and not isinstance(error, DOMAIN_ERROR_TYPES):
        return StorageError(str(error))
    return error


def _prompt_skills_decision(
    latent_skill_id: str,
    command: ProposeSkillCommandHandler,
    result: ProposeSkillResult,
) -> ProposeSkillResult | None:
    _stdout_console().print(_format_human_skill_proposal(result))
    try:
        answer = input("Decisao [Sim/Sempre/Não]: ")
    except (EOFError, KeyboardInterrupt):
        _stdout_console().print("\nCancelado.")
        return None
    prompted_decision = _skill_decision(answer)
    if prompted_decision is None:
        raise ValidationFailedError("Decisao invalida fornecida. Use Sim, Sempre ou Não.")
    return command(
        ProposeSkillCommand(
            latent_skill_id=latent_skill_id,
            decision=prompted_decision,
            origin="cli",
        )
    )


def _map_propose_error(error: Exception, latent_skill_id: str) -> Exception:
    if isinstance(error, KeyError):
        return ValidationFailedError(
            f"Latent skill '{latent_skill_id}' nao encontrada no repositorio."
        )
    if isinstance(error, (ValidationError, ValueError)):
        return ValidationFailedError(str(error))
    if isinstance(error, OSError) and not isinstance(error, DOMAIN_ERROR_TYPES):
        return StorageError(str(error))
    return error


def _run_skills_propose(
    command: ProposeSkillCommandHandler,
    *,
    output_format: str,
    latent_skill_id: str,
    decision: ProposeSkillDecision | None,
    yes: bool,
) -> int:
    try:
        resolved_decision = ProposeSkillDecision.sim if yes and decision is None else decision
        if resolved_decision is None and not sys.stdin.isatty():
            raise ValidationFailedError("Ambiente nao-TTY exige --decision ou --yes.")
        if output_format == "json" and resolved_decision is None:
            raise ValidationFailedError(
                "Informe --decision ou --yes para executar skills propose com saida JSON."
            )
        if resolved_decision is not None:
            result = command(
                ProposeSkillCommand(
                    latent_skill_id=latent_skill_id,
                    decision=resolved_decision,
                    origin="cli",
                )
            )
        else:
            result = command(ProposeSkillCommand(latent_skill_id=latent_skill_id, origin="cli"))
            if output_format != "json" and sys.stdin.isatty():
                prompted = _prompt_skills_decision(latent_skill_id, command, result)
                if prompted is None:
                    return 1
                result = prompted
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        exc = _map_propose_error(error, latent_skill_id)
        _print_expected_error(exc, output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_proposal_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_proposal(result))
    return 0


def _prompt_generate_collision(
    result: GenerateSkillResult,
    update_existing: bool,
) -> tuple[bool, int]:
    if update_existing:
        _stdout_console().print(
            f"[bold yellow]AVISO: O diretorio da skill '{result.slug}' "
            "ja existe e sera SOBRESCRITO![/bold yellow]"
        )
        if not _confirm("Confirmar sobreescrita e geracao? [s/N]: ", default=False):
            _stdout_console().print("Geracao de skill cancelada.")
            return False, 1
        return True, 0

    _stdout_console().print(
        f"[bold yellow]Conflito: O diretorio da skill '{result.slug}' ja existe.[/bold yellow]"
    )
    _stdout_console().print(
        f"Sugestao alternativa proposta pelo sistema: '{result.suggested_slug}'"
    )
    choice = ""
    prompt_msg = (
        "O que deseja fazer? [u] Atualizar existente, "
        "[a] Usar slug alternativo proposto, [c] Cancelar [u/a/C]: "
    )
    while choice not in {"u", "a", "c"}:
        choice = input(prompt_msg).strip().lower()
        if not choice:
            choice = "c"
    if choice == "c":
        _stdout_console().print("Geracao de skill cancelada.")
        return False, 1
    return choice == "u", 0


def _run_skills_generate(
    command: GenerateSkillCommandHandler,
    *,
    output_format: str,
    latent_skill_id: str,
    yes: bool,
    update_existing: bool,
) -> int:
    try:
        if output_format == "json" and not yes:
            raise ValidationFailedError(
                "A flag --yes / -y e obrigatoria para executar skills generate com saida JSON."
            )
        if output_format != "json":
            if not yes and (not sys.stdin.isatty() or not sys.stdout.isatty()):
                raise ValidationFailedError("Ambiente nao-TTY exige --yes para gerar skill.")

            # Perform a dry_run to get real resolved paths and check for collision
            dry_run_result = command(
                GenerateSkillCommand(
                    latent_skill_id=latent_skill_id,
                    origin="cli",
                    update_existing=update_existing,
                    dry_run=True,
                )
            )
            _stdout_console().print(_format_human_skill_generate_plan(dry_run_result))

            if not yes:
                if dry_run_result.collision_detected:
                    update_existing, code = _prompt_generate_collision(
                        dry_run_result, update_existing
                    )
                    if code != 0:
                        return code
                elif not _confirm("Gerar estrutura da skill? [s/N]: ", default=False):
                    _stdout_console().print("Geracao de skill cancelada.")
                    return 1

        result = command(
            GenerateSkillCommand(
                latent_skill_id=latent_skill_id,
                origin="cli",
                update_existing=update_existing,
                dry_run=False,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        exc = _map_generate_error(error, latent_skill_id)
        _print_expected_error(exc, output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_generate_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_generate_success(result))
    return 0


def _run_skills_activate(
    command: ActivateSkillCommandHandler,
    *,
    output_format: str,
    latent_skill_id: str,
) -> int:
    try:
        result = command(ActivateSkillCommand(latent_skill_id=latent_skill_id, origin="cli"))
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, latent_skill_id), output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_activate_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_mutation_success("skills.activate", result))
    return 0


def _run_skills_deactivate(
    command: DeactivateSkillCommandHandler,
    *,
    output_format: str,
    latent_skill_id: str,
) -> int:
    try:
        result = command(DeactivateSkillCommand(latent_skill_id=latent_skill_id, origin="cli"))
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, latent_skill_id), output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_deactivate_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_mutation_success("skills.deactivate", result))
    return 0


def _run_skills_update(  # noqa: PLR0913
    command: UpdateSkillCommandHandler,
    *,
    output_format: str,
    latent_skill_id: str,
    name: str | None,
    description: str | None,
    triggers: list[str] | None,
    file: Path | None,
) -> int:
    try:
        raw_markdown = _read_skill_update_file(file) if file is not None else None
        result = command(
            UpdateSkillCommand(
                latent_skill_id=latent_skill_id,
                origin="cli",
                name=name.strip() if name is not None else None,
                description=description.strip() if description is not None else None,
                triggers=[trigger.strip() for trigger in triggers or [] if trigger.strip()]
                if triggers is not None
                else None,
                raw_markdown=raw_markdown,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, latent_skill_id), output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_update_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_mutation_success("skills.update", result))
    return 0


def _read_skill_update_file(path: Path) -> str:
    if not path.is_file():
        raise ValidationFailedError(f"Arquivo markdown nao encontrado: {path.as_posix()}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise StorageError(str(error)) from error


def _map_skill_mutation_error(error: Exception, latent_skill_id: str) -> Exception:
    if isinstance(error, KeyError):
        return ValidationFailedError(
            f"Latent skill '{latent_skill_id}' nao encontrada no repositorio."
        )
    if isinstance(error, StorageError) and str(error) == (
        f"Latent skill not found: {latent_skill_id}"
    ):
        return ValidationFailedError(
            f"Latent skill '{latent_skill_id}' nao encontrada no repositorio."
        )
    if isinstance(error, (ValidationError, ValueError)):
        return ValidationFailedError(str(error))
    if isinstance(error, OSError) and not isinstance(error, DOMAIN_ERROR_TYPES):
        return StorageError(str(error))
    return error


def _map_generate_error(error: Exception, latent_skill_id: str) -> Exception:
    if isinstance(error, KeyError):
        return ValidationFailedError(
            f"Latent skill '{latent_skill_id}' nao encontrada no repositorio."
        )
    if isinstance(error, (ValidationError, ValueError)):
        return ValidationFailedError(str(error))
    if isinstance(error, OSError) and not isinstance(error, DOMAIN_ERROR_TYPES):
        return StorageError(str(error))
    return error


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


def _skill_proposal_success_envelope(result: ProposeSkillResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.propose",
        "scope": result.latent_skill.scope.value,
        "data": _skill_proposal_payload(result),
        "warnings": [],
    }


def _skill_generate_success_envelope(result: GenerateSkillResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.generate",
        "scope": result.latent_skill.scope.value,
        "data": result.to_payload(),
        "warnings": result.warnings,
    }


def _skill_list_success_envelope(result: ListSkillsResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.list",
        "scope": "all",
        "data": result.to_payload(),
        "warnings": [],
    }


def _skill_detail_success_envelope(result: GetSkillDetailResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.detail",
        "scope": result.scope,
        "data": result.to_payload(),
        "warnings": [],
    }


def _skill_activate_success_envelope(result: ActivateSkillResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.activate",
        "scope": result.latent_skill.scope.value,
        "data": _skill_mutation_payload(result),
        "warnings": [],
    }


def _skill_deactivate_success_envelope(result: DeactivateSkillResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.deactivate",
        "scope": result.latent_skill.scope.value,
        "data": _skill_mutation_payload(result),
        "warnings": [],
    }


def _skill_update_success_envelope(result: UpdateSkillResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.update",
        "scope": result.latent_skill.scope.value,
        "data": _skill_mutation_payload(result),
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


def _skill_proposal_payload(result: ProposeSkillResult) -> dict[str, Any]:
    return {
        "skill_id": result.latent_skill.id,
        "suggested_name": result.proposal["suggested_name"],
        "status": result.latent_skill.status.value,
        "accepted": result.accepted,
        "auto_approval_recorded": result.auto_approval_recorded,
        "audit_reference": result.audit_reference,
        "snapshot_reference": result.snapshot_reference,
        "choices": result.choices,
        "requires_decision": result.requires_decision,
        "evidence": result.proposal["evidence"],
    }


def _skill_mutation_payload(
    result: ActivateSkillResult | DeactivateSkillResult | UpdateSkillResult,
) -> dict[str, Any]:
    skill = result.latent_skill
    payload: dict[str, Any] = {
        "latent_skill": {
            "id": skill.id,
            "name": skill.name,
            "description": skill.description,
            "status": skill.status.value,
            "scope": skill.scope.value,
            "triggers": _skill_triggers(skill),
        },
        "audit_reference": result.audit_reference,
        "snapshot_reference": result.snapshot_reference,
    }
    skill_file = getattr(result, "skill_file", None)
    if skill_file is not None:
        payload["skill_file"] = skill_file
    return payload


def _skill_triggers(skill: Any) -> list[str]:
    metadata = skill.metadata or {}
    raw_triggers = metadata.get("triggers") or []
    if isinstance(raw_triggers, list):
        return [str(trigger) for trigger in raw_triggers]
    return [str(raw_triggers)]


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


def _host_success_envelope(
    result: ConfigureHostResult | SyncInstructionsResult,
    *,
    operation: str,
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": operation,
        "scope": "project",
        "data": result.to_payload(),
        "warnings": result.warnings,
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


def _format_human_init_output(result: SetupProjectResult, *, locale: str = "en") -> str:
    status = (
        "Local memory created at .umem/." if result.created else "Local memory already initialized."
    )
    paths_label = "Created paths:" if result.created else "Reused paths:"
    paths = result.created_paths if result.created else result.existing_paths
    rendered_paths = "\n".join(f"- {path}" for path in paths)

    return "\n".join(
        [
            human_message(status, locale=locale),
            human_message(paths_label, locale=locale),
            rendered_paths,
            human_message(
                "Audit: {audit_reference}",
                locale=locale,
                audit_reference=AUDIT_REFERENCE_PLACEHOLDER,
            ),
            human_message("Suggested next command: umem status", locale=locale),
        ]
    )


def _format_human_init_host_results(
    results: list[ConfigureHostResult], *, locale: str = "en"
) -> str:
    lines = [human_message("Hosts configured during onboarding:", locale=locale)]
    for result in results:
        changes = ", ".join(change["path"] for change in result.planned_changes) or (
            "(" + human_message("validation", locale=locale) + ")"
        )
        lines.append(
            f"- {result.host_id}: {result.validation_status}; "
            f"{human_message('files', locale=locale)}={changes}; "
            f"{human_message('snapshot', locale=locale)}={result.snapshot_reference}; "
            f"{human_message('audit', locale=locale)}={result.audit_reference}"
        )
    return "\n".join(lines)


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
    for host, validation in result.host_validation.items():
        status = validation.get("status", "unconfigured")
        method = validation.get("method")
        audit_reference = validation.get("audit_reference")
        suffix_parts = []
        if method:
            suffix_parts.append(f"metodo={method}")
        if audit_reference:
            suffix_parts.append(f"auditoria={audit_reference}")
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        lines.append(f"- {host}: {status}{suffix}")
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


def _format_human_skill_proposal(result: ProposeSkillResult) -> str:
    scope = result.proposal["scope"]
    is_global = scope == "global"

    skill_path = "memory/latent_skills.jsonl" if is_global else ".umem/memory/latent_skills.jsonl"
    config_path = "~/.config/umem/config.toml" if is_global else ".umem/config.toml"

    lines = [
        "Operacao: skills.propose",
        f"Escopo: {scope}",
        f"Nome sugerido: {result.proposal['suggested_name']}",
        f"Proposito: {result.proposal['purpose']}",
        "Evidencias:",
    ]
    evidence = result.proposal.get("evidence", [])
    lines.extend(f"  - {item}" for item in evidence)

    lines.extend(
        [
            "",
            "Caminhos relativos afetados:",
            f"  - Decisao Sim: {skill_path}",
            f"  - Decisao Sempre: {skill_path} E {config_path}",
            f"  - Decisao Nao: {skill_path}",
            "",
            "Snapshot: Um snapshot de seguranca sera criado antes de qualquer gravacao.",
            "Evento de auditoria esperado: propose_skill_decision ou "
            "update_skill_auto_approval (para Sempre).",
            "Opcoes: Sim, Sempre, Não",
        ]
    )

    if result.audit_reference:
        lines.append(f"Auditoria: {result.audit_reference}")
    if result.snapshot_reference:
        lines.append(f"Snapshot: {result.snapshot_reference}")
    return "\n".join(lines)


def _format_human_skill_list(result: ListSkillsResult) -> Table | str:
    if not result.skills:
        lines = ["Nenhuma skill registrada."]
        if result.recommended_action:
            lines.append(result.recommended_action)
        return "\n".join(lines)

    table = Table(title="Skills registradas")
    table.add_column("Nome")
    table.add_column("Escopo")
    table.add_column("Status")
    table.add_column("Caminho relativo")
    table.add_column("Origem")
    table.add_column("Criada em")
    table.add_column("Atualizada em")
    status_styles = {
        "active": "green",
        "candidate": "yellow",
        "disabled": "dim",
    }
    for skill in result.skills:
        table.add_row(
            skill.name,
            skill.scope,
            Text(skill.status, style=status_styles.get(skill.status, "")),
            skill.relative_path or "-",
            skill.origin,
            skill.created_at,
            skill.updated_at,
        )
    return table


def _format_human_skill_detail(result: GetSkillDetailResult) -> str:
    lines = [
        "Operacao: skills.detail",
        f"Nome: {result.name}",
        f"Escopo: {result.scope}",
        f"Status: {result.status}",
        f"Caminho relativo: {result.relative_path or '-'}",
        "Gatilhos:",
    ]
    lines.extend(f"  - {trigger}" for trigger in result.triggers)
    lines.extend(
        [
            f"Auditoria: {result.audit_reference}",
            f"References carregadas: {str(result.references_loaded).lower()}",
        ]
    )
    return "\n".join(lines)


def _format_human_skill_generate_plan(result: GenerateSkillResult) -> str:
    lines = [
        "Operacao: skills.generate",
        f"Escopo: {result.latent_skill.scope.value}",
        f"Latent skill: {result.latent_skill.id}",
        "Caminhos relativos afetados:",
        f"  - {result.skill_file}",
    ]
    metadata = result.latent_skill.metadata or {}
    if bool(metadata.get("include_scripts") or metadata.get("scripts")):
        lines.append(f"  - {result.skill_dir}/scripts/.gitkeep")
    if bool(metadata.get("include_references") or metadata.get("references")):
        lines.append(f"  - {result.skill_dir}/references/.gitkeep")
    lines.extend(
        [
            "Snapshot: criado pelo pipeline seguro antes de cada gravacao.",
            "Auditoria: evento generate_skill esperado.",
            "Padrao: nao confirmar.",
        ]
    )
    return "\n".join(lines)


def _format_human_skill_generate_success(result: GenerateSkillResult) -> str:
    lines = [
        "Operacao: skills.generate",
        f"Escopo: {result.latent_skill.scope.value}",
        f"Nome: {result.latent_skill.name}",
        f"Slug: {result.slug}",
        "Caminhos relativos afetados:",
    ]
    lines.extend(f"  - {path}" for path in result.affected_paths)
    lines.extend(
        [
            f"Snapshot: {result.snapshot_reference}",
            f"Auditoria: {result.audit_reference}",
        ]
    )
    if result.collision_detected and result.suggested_slug and result.suggested_slug != result.slug:
        lines.append(f"Colisao: slug alternativo usado ({result.suggested_slug}).")
    return "\n".join(lines)


def _format_human_skill_mutation_success(
    operation: str,
    result: ActivateSkillResult | DeactivateSkillResult | UpdateSkillResult,
) -> str:
    payload = _skill_mutation_payload(result)
    skill = result.latent_skill
    affected_paths = [_latent_skill_store_path(skill.scope)]
    skill_file = payload.get("skill_file")
    if isinstance(skill_file, str):
        affected_paths.insert(0, skill_file)

    lines = [
        f"Operacao: {operation}",
        f"Escopo: {skill.scope.value}",
        f"Latent skill: {skill.id}",
        f"Nome: {skill.name}",
        f"Status: {skill.status.value}",
        "Caminhos relativos afetados:",
    ]
    lines.extend(f"  - {path}" for path in affected_paths)
    lines.extend(
        [
            f"Snapshot: {result.snapshot_reference}",
            f"Auditoria: {result.audit_reference}",
        ]
    )
    rollback_hint = getattr(result, "rollback_hint", None)
    if rollback_hint:
        lines.append(f"Rollback: {rollback_hint}")
    return "\n".join(lines)


def _latent_skill_store_path(scope: Any) -> str:
    if scope == LatentSkillScope.global_:
        return "memory/latent_skills.jsonl"
    return ".umem/memory/latent_skills.jsonl"


def _format_human_host_plan(result: ConfigureHostResult, *, operation: str) -> Table | str:
    if not result.planned_changes:
        return f"Nenhuma alteracao planejada para host {result.host_id}."

    table = Table(title=f"Plano de {operation} do host {result.host_id}", show_header=True)
    table.add_column("Alvo")
    table.add_column("Acao")
    table.add_column("Caminho")
    table.add_column("Snapshot")
    table.add_column("Auditoria")
    for change in result.planned_changes:
        table.add_row(
            change["target"],
            change["action"],
            change["path"],
            result.snapshot_reference,
            "host_setup",
        )
    return table


def _format_human_host_success(result: ConfigureHostResult, *, operation: str) -> str | Panel:
    if operation == "check":
        status_styles = {
            "success": "green",
            "failure": "red",
            "manual_pending": "yellow",
        }
        style = status_styles.get(result.validation_status, "white")
        lines = [
            "[bold]Host check concluido.[/bold]",
            f"Host: {result.host_id}",
            f"Alvos: {', '.join(result.instruction_targets)}",
            f"Validacao: [{style}]{result.validation_status}[/{style}]",
            f"Auditoria: {result.audit_reference}",
        ]
        if result.warnings:
            if result.validation_status == "failure":
                lines.append("Erros de Validação:")
            else:
                lines.append("Alertas:")
            lines.extend(f"- {warning}" for warning in result.warnings)
        return Panel.fit("\n".join(lines), border_style=style)

    changes = ", ".join(change["path"] for change in result.planned_changes) or "(nenhuma)"
    return "\n".join(
        [
            f"Host {operation} concluido.",
            f"Host: {result.host_id}",
            f"Alvos: {', '.join(result.instruction_targets)}",
            f"Arquivos: {changes}",
            f"Validacao: {result.validation_status}",
            f"Auditoria: {result.audit_reference}",
        ]
    )


def _format_human_sync_success(result: SyncInstructionsResult) -> str:
    changes = ", ".join(change["path"] for change in result.planned_changes) or "(nenhuma)"
    msg = (
        "Host sync concluido."
        if result.validation_status == "success"
        else "Dry-run concluido. Nenhuma alteracao foi aplicada ao sistema de arquivos."
    )
    return "\n".join(
        [
            msg,
            f"Hosts: {', '.join(result.host_ids)}",
            f"Alvos: {', '.join(result.instruction_targets)}",
            f"Arquivos: {changes}",
            f"Validacao: {result.validation_status}",
            f"Auditoria: {result.audit_reference}",
            f"Snapshots: {result.snapshot_reference}",
        ]
    )


def _format_human_sync_plan(result: SyncInstructionsResult) -> Table | str:
    if not result.planned_changes:
        return "Nenhuma alteracao planejada para sincronizacao de instrucoes."

    table = Table(title="Plano de sincronizacao de instrucoes", show_header=True)
    table.add_column("Alvo")
    table.add_column("Acao")
    table.add_column("Caminho")
    table.add_column("Escopo")
    table.add_column("Snapshot")
    table.add_column("Auditoria")
    for change in result.planned_changes:
        table.add_row(
            change["target"],
            change["action"],
            change["path"],
            "project",
            result.snapshot_reference,
            "host_sync",
        )
    return table


def _recovery_hint(error: Exception) -> str:
    return recovery_hint(error)


def _print_expected_error(
    error: Exception, output_format: str, *, locale: str | None = None
) -> None:
    message_locale = "en" if output_format == "json" else (locale or "pt-BR")
    payload = {
        "ok": False,
        "error": error_payload(error, message_locale=message_locale),
    }

    if output_format == "json":
        print(json.dumps(payload, sort_keys=True))
        return

    panel = Panel(
        Text.from_markup(
            "\n".join(
                [
                    f"[bold]{human_message('Failure:', locale=message_locale)}[/bold] "
                    f"{payload['error']['message']}",
                    f"[bold]{human_message('Detail:', locale=message_locale)}[/bold] "
                    f"{payload['error']['detail']}",
                    f"[bold]{human_message('Recovery:', locale=message_locale)}[/bold] "
                    f"{payload['error']['recovery_hint']}",
                ]
            )
        ),
        title=human_message("Error", locale=message_locale),
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


def _skill_decision(value: str | None) -> ProposeSkillDecision | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if normalized in {"s", "sim", "y", "yes"}:
        return ProposeSkillDecision.sim
    if normalized in {"e", "sempre", "always"}:
        return ProposeSkillDecision.sempre
    if normalized in {"n", "nao", "não", "no"}:
        return ProposeSkillDecision.nao
    return None
