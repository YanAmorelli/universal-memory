import json
import os
import sys
import traceback
from collections.abc import Callable, Sequence
from dataclasses import asdict, dataclass
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

from universal_memory import __version__
from universal_memory.application.diagnostics import (
    DoctorCommand,
    DoctorResult,
)
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
    DEFAULT_ENABLED_RUNTIME_IDS,
    DEFAULT_UMEM_SKILL_ID,
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
    AdoptSkillCommand,
    AdoptSkillResult,
    CleanupSkillCommand,
    CleanupSkillResult,
    CreateSkillCommand,
    CreateSkillDraftCommand,
    CreateSkillResult,
    DeactivateSkillCommand,
    DeactivateSkillResult,
    DraftSkillResult,
    GenerateSkillCommand,
    GenerateSkillResult,
    GetSkillDetailCommand,
    GetSkillDetailResult,
    ImportSkillCommand,
    ImportSkillResult,
    ListSkillsCommand,
    ListSkillsResult,
    PromoteSkillRecommendationCommand,
    PromoteSkillRecommendationResult,
    ProposeSkillCommand,
    ProposeSkillDecision,
    ProposeSkillResult,
    PublishSkillCommand,
    PublishSkillResult,
    RecommendSkillsCommand,
    RecommendSkillsResult,
    RenameSkillCommand,
    RenameSkillResult,
    RepairSkillsCommand,
    RepairSkillsResult,
    SyncSkillResult,
    SyncSkillsCommand,
    SyncSkillsResult,
    TrackLatentSkillCommand,
    TrackLatentSkillResult,
    UpdateCanonicalSkillCommand,
    UpdateCanonicalSkillResult,
    UpdateSkillCommand,
    UpdateSkillResult,
    ValidateSkillCommand,
    ValidateSkillResult,
)
from universal_memory.application.skills.import_skill import NO_NATIVE_INSTALLATIONS_NOTE
from universal_memory.application.skills.native_skill_sync import DRIFT_WARNING, NativeDriftDecision
from universal_memory.application.update import (
    UpdateBenchmarksCommand,
    UpdateBenchmarksResult,
    UpdateCheckCommand,
    UpdateCheckResult,
    UpdateManagedSkillsCommand,
    UpdateManagedSkillTemplateResult,
    UpdateMigrateCommand,
    UpdateMigrateResult,
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
    LatentSkillStatus,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.domain.entities.base import format_utc_iso
from universal_memory.domain.entities.runtime import RuntimeAdapter, default_runtime_registry
from universal_memory.interfaces.cli.message_catalog import (
    DEFAULT_LOCALE,
    human_message,
)
from universal_memory.interfaces.errors import (
    DOMAIN_ERROR_TYPES,
    error_descriptor,
    error_payload,
    recovery_hint,
)

DEFAULT_CONTEXT_MAX_SIZE_CHARS = 4000
AUDIT_REFERENCE_PLACEHOLDER = "not-implemented-yet"
INIT_SPLASH_MARKER = "UMem"
INIT_SPLASH_LINES = (
    " _    _ __  __                \n"
    "| |  | |  \\/  |               \n"
    "| |  | | \\  / | ___ _ __ ___  \n"
    "| |  | | |\\/| |/ _ \\ '_ ` _ \\ \n"
    "| |__| | |  | |  __/ | | | | |\n"
    " \\____/|_|  |_|\\___|_| |_| |_|",
    "  persistent context for AI agents",
)
SetupProjectCommand = (
    Callable[[Path, list[str] | None], SetupProjectResult] | Callable[[Path], SetupProjectResult]
)
LEGACY_CONFIGURABLE_RUNTIME_IDS = {"claude_code", "codex"}
ListAuditLogCommandHandler = Callable[[ListAuditLogCommand], ListAuditLogResult]
ListSnapshotsCommandHandler = Callable[[ListSnapshotsCommand], ListSnapshotsResult]
RollbackCommandHandler = Callable[[RollbackCommand], RollbackResult]
RollbackPreviewHandler = Callable[[SnapshotScope], Snapshot]
StatusCommandHandler = Callable[[GetMemoryStatusCommand], GetMemoryStatusResult]
DoctorCommandHandler = Callable[[DoctorCommand], DoctorResult]
ContextCommandHandler = Callable[[AssembleContextSummaryCommand], AssembleContextSummaryResult]
RememberFactCommandHandler = Callable[[RememberFactCommand], RememberFactResult]
ListFactsCommandHandler = Callable[[ListFactsCommand], ListFactsResult]
PurgeFactCommandHandler = Callable[[PurgeFactCommand], PurgeFactResult]
ContextHygieneCommandHandler = Callable[[ContextHygieneCommand], ContextHygieneResult]
ConfigureHostCommandHandler = Callable[[ConfigureHostCommand], ConfigureHostResult]
SyncInstructionsCommandHandler = Callable[[SyncInstructionsCommand], SyncInstructionsResult]
ProposeSkillCommandHandler = Callable[[ProposeSkillCommand], ProposeSkillResult]
TrackLatentSkillCommandHandler = Callable[[TrackLatentSkillCommand], TrackLatentSkillResult]
GenerateSkillCommandHandler = Callable[[GenerateSkillCommand], GenerateSkillResult]
CreateSkillCommandHandler = Callable[[CreateSkillCommand], CreateSkillResult]
CreateSkillDraftCommandHandler = Callable[[CreateSkillDraftCommand], DraftSkillResult]
PublishSkillCommandHandler = Callable[[PublishSkillCommand], PublishSkillResult]
ValidateSkillCommandHandler = Callable[[ValidateSkillCommand], ValidateSkillResult]
AdoptSkillCommandHandler = Callable[[AdoptSkillCommand], AdoptSkillResult]
UpdateCanonicalSkillCommandHandler = Callable[
    [UpdateCanonicalSkillCommand], UpdateCanonicalSkillResult
]
RenameSkillCommandHandler = Callable[[RenameSkillCommand], RenameSkillResult]
CleanupSkillCommandHandler = Callable[[CleanupSkillCommand], CleanupSkillResult]
RepairSkillsCommandHandler = Callable[[RepairSkillsCommand], RepairSkillsResult]
PromoteSkillRecommendationCommandHandler = Callable[
    [PromoteSkillRecommendationCommand], PromoteSkillRecommendationResult
]
ImportSkillCommandHandler = Callable[[ImportSkillCommand], ImportSkillResult]
RecommendSkillsCommandHandler = Callable[[RecommendSkillsCommand], RecommendSkillsResult]
SyncSkillsCommandHandler = Callable[[SyncSkillsCommand], SyncSkillsResult]
ListSkillsCommandHandler = Callable[[ListSkillsCommand], ListSkillsResult]
GetSkillDetailCommandHandler = Callable[[GetSkillDetailCommand], GetSkillDetailResult]
ActivateSkillCommandHandler = Callable[[ActivateSkillCommand], ActivateSkillResult]
DeactivateSkillCommandHandler = Callable[[DeactivateSkillCommand], DeactivateSkillResult]
UpdateSkillCommandHandler = Callable[[UpdateSkillCommand], UpdateSkillResult]
UpdateCheckCommandHandler = Callable[[UpdateCheckCommand], UpdateCheckResult]
UpdateManagedSkillsCommandHandler = Callable[
    [UpdateManagedSkillsCommand], list[UpdateManagedSkillTemplateResult]
]
UpdateMigrateCommandHandler = Callable[[UpdateMigrateCommand], UpdateMigrateResult]
UpdateBenchmarksCommandHandler = Callable[[UpdateBenchmarksCommand], UpdateBenchmarksResult]
UpdateSkillsItem = UpdateSkillResult | UpdateManagedSkillTemplateResult | SyncSkillResult


@dataclass(frozen=True, slots=True)
class UpdateSkillsRunResult:
    skills: list[UpdateSkillsItem]
    updated_count: int
    preserved_count: int
    warnings: list[str]


LocaleResolver = Callable[[], str]
OutputFormatOption = Annotated[
    str | None,
    typer.Option(
        "--format",
        "-f",
        help="Output format.",
        case_sensitive=False,
        click_type=click.Choice(["human", "json", "summary"], case_sensitive=False),
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
    doctor_command: DoctorCommandHandler | None = None,
    context_command: ContextCommandHandler | None = None,
    remember_command: RememberFactCommandHandler | None = None,
    facts_list_command: ListFactsCommandHandler | None = None,
    facts_purge_command: PurgeFactCommandHandler | None = None,
    facts_hygiene_command: ContextHygieneCommandHandler | None = None,
    host_setup_command: ConfigureHostCommandHandler | None = None,
    host_check_command: ConfigureHostCommandHandler | None = None,
    host_sync_command: SyncInstructionsCommandHandler | None = None,
    propose_skill_command: ProposeSkillCommandHandler | None = None,
    track_latent_skill_command: TrackLatentSkillCommandHandler | None = None,
    generate_skill_command: GenerateSkillCommandHandler | None = None,
    create_skill_command: CreateSkillCommandHandler | None = None,
    create_skill_draft_command: CreateSkillDraftCommandHandler | None = None,
    publish_skill_command: PublishSkillCommandHandler | None = None,
    validate_skill_command: ValidateSkillCommandHandler | None = None,
    adopt_skill_command: AdoptSkillCommandHandler | None = None,
    update_canonical_skill_command: UpdateCanonicalSkillCommandHandler | None = None,
    rename_skill_command: RenameSkillCommandHandler | None = None,
    cleanup_skill_command: CleanupSkillCommandHandler | None = None,
    repair_skills_command: RepairSkillsCommandHandler | None = None,
    promote_skill_recommendation_command: PromoteSkillRecommendationCommandHandler | None = None,
    import_skill_command: ImportSkillCommandHandler | None = None,
    recommend_skills_command: RecommendSkillsCommandHandler | None = None,
    sync_skills_command: SyncSkillsCommandHandler | None = None,
    list_skills_command: ListSkillsCommandHandler | None = None,
    get_skill_detail_command: GetSkillDetailCommandHandler | None = None,
    activate_skill_command: ActivateSkillCommandHandler | None = None,
    deactivate_skill_command: DeactivateSkillCommandHandler | None = None,
    update_skill_command: UpdateSkillCommandHandler | None = None,
    update_check_command: UpdateCheckCommandHandler | None = None,
    update_managed_skills_command: UpdateManagedSkillsCommandHandler | None = None,
    update_migrate_command: UpdateMigrateCommandHandler | None = None,
    update_benchmarks_command: UpdateBenchmarksCommandHandler | None = None,
    locale_resolver: LocaleResolver | None = None,
) -> int:
    app = create_typer_app(
        setup_project_command=setup_project_command,
        audit_list_command=audit_list_command,
        snapshots_list_command=snapshots_list_command,
        rollback_command=rollback_command,
        rollback_preview_command=rollback_preview_command,
        status_command=status_command,
        doctor_command=doctor_command,
        context_command=context_command,
        remember_command=remember_command,
        facts_list_command=facts_list_command,
        facts_purge_command=facts_purge_command,
        facts_hygiene_command=facts_hygiene_command,
        host_setup_command=host_setup_command,
        host_check_command=host_check_command,
        host_sync_command=host_sync_command,
        propose_skill_command=propose_skill_command,
        track_latent_skill_command=track_latent_skill_command,
        generate_skill_command=generate_skill_command,
        create_skill_command=create_skill_command,
        create_skill_draft_command=create_skill_draft_command,
        publish_skill_command=publish_skill_command,
        validate_skill_command=validate_skill_command,
        adopt_skill_command=adopt_skill_command,
        update_canonical_skill_command=update_canonical_skill_command,
        rename_skill_command=rename_skill_command,
        cleanup_skill_command=cleanup_skill_command,
        repair_skills_command=repair_skills_command,
        promote_skill_recommendation_command=promote_skill_recommendation_command,
        import_skill_command=import_skill_command,
        recommend_skills_command=recommend_skills_command,
        sync_skills_command=sync_skills_command,
        list_skills_command=list_skills_command,
        get_skill_detail_command=get_skill_detail_command,
        activate_skill_command=activate_skill_command,
        deactivate_skill_command=deactivate_skill_command,
        update_skill_command=update_skill_command,
        update_check_command=update_check_command,
        update_managed_skills_command=update_managed_skills_command,
        update_migrate_command=update_migrate_command,
        update_benchmarks_command=update_benchmarks_command,
        locale_resolver=locale_resolver,
    )
    try:
        result = app(args=list(argv) if argv is not None else None, standalone_mode=False)
    except click.exceptions.ClickException as e:
        fmt = _determine_output_format(argv)
        _print_expected_error(ValidationFailedError(e.format_message()), output_format=fmt)
        return e.exit_code
    except click.exceptions.Exit as exit_error:
        code = exit_error.exit_code
        return int(code) if code is not None else 0
    except click.exceptions.Abort:
        fmt = _determine_output_format(argv)
        if fmt == "json":
            print(
                json.dumps(
                    {
                        "ok": False,
                        "error": {
                            "code": "aborted",
                            "detail": "Command execution was aborted by user or system signal.",
                        },
                        "warnings": [],
                    },
                    sort_keys=True,
                )
            )
        else:
            sys.stderr.write("Aborted.\n")
        return 1
    except RuntimeError:
        raise
    except Exception as e:
        fmt = _determine_output_format(argv)
        _print_unexpected_error(e, output_format=fmt)
        return 1
    if isinstance(result, int):
        return result
    return 0


def _version_callback(value: bool) -> None:
    if value:
        typer.echo(f"umem {__version__}")
        raise typer.Exit()


def create_typer_app(  # noqa: PLR0913, PLR0915
    *,
    setup_project_command: SetupProjectCommand | None = None,
    audit_list_command: ListAuditLogCommandHandler | None = None,
    snapshots_list_command: ListSnapshotsCommandHandler | None = None,
    rollback_command: RollbackCommandHandler | None = None,
    rollback_preview_command: RollbackPreviewHandler | None = None,
    status_command: StatusCommandHandler | None = None,
    doctor_command: DoctorCommandHandler | None = None,
    context_command: ContextCommandHandler | None = None,
    remember_command: RememberFactCommandHandler | None = None,
    facts_list_command: ListFactsCommandHandler | None = None,
    facts_purge_command: PurgeFactCommandHandler | None = None,
    facts_hygiene_command: ContextHygieneCommandHandler | None = None,
    host_setup_command: ConfigureHostCommandHandler | None = None,
    host_check_command: ConfigureHostCommandHandler | None = None,
    host_sync_command: SyncInstructionsCommandHandler | None = None,
    propose_skill_command: ProposeSkillCommandHandler | None = None,
    track_latent_skill_command: TrackLatentSkillCommandHandler | None = None,
    generate_skill_command: GenerateSkillCommandHandler | None = None,
    create_skill_command: CreateSkillCommandHandler | None = None,
    create_skill_draft_command: CreateSkillDraftCommandHandler | None = None,
    publish_skill_command: PublishSkillCommandHandler | None = None,
    validate_skill_command: ValidateSkillCommandHandler | None = None,
    adopt_skill_command: AdoptSkillCommandHandler | None = None,
    update_canonical_skill_command: UpdateCanonicalSkillCommandHandler | None = None,
    rename_skill_command: RenameSkillCommandHandler | None = None,
    cleanup_skill_command: CleanupSkillCommandHandler | None = None,
    repair_skills_command: RepairSkillsCommandHandler | None = None,
    promote_skill_recommendation_command: PromoteSkillRecommendationCommandHandler | None = None,
    import_skill_command: ImportSkillCommandHandler | None = None,
    recommend_skills_command: RecommendSkillsCommandHandler | None = None,
    sync_skills_command: SyncSkillsCommandHandler | None = None,
    list_skills_command: ListSkillsCommandHandler | None = None,
    get_skill_detail_command: GetSkillDetailCommandHandler | None = None,
    activate_skill_command: ActivateSkillCommandHandler | None = None,
    deactivate_skill_command: DeactivateSkillCommandHandler | None = None,
    update_skill_command: UpdateSkillCommandHandler | None = None,
    update_check_command: UpdateCheckCommandHandler | None = None,
    update_managed_skills_command: UpdateManagedSkillsCommandHandler | None = None,
    update_migrate_command: UpdateMigrateCommandHandler | None = None,
    update_benchmarks_command: UpdateBenchmarksCommandHandler | None = None,
    locale_resolver: LocaleResolver | None = None,
) -> typer.Typer:
    app = typer.Typer(help="Universal Memory CLI", no_args_is_help=True)
    facts_app = typer.Typer(help="Manage memory facts")
    audit_app = typer.Typer(help="Inspect audit events")
    snapshots_app = typer.Typer(help="Inspect snapshots")
    host_app = typer.Typer(help="Configure agent hosts")
    skills_app = typer.Typer(
        help=(
            "Manage skills. Use create for new canonical skills, import for existing "
            "native/local skills, track/recommend/promote for recurring workflows, and "
            "sync to materialize canonical skills into native runtime copies."
        )
    )
    skills_draft_app = typer.Typer(help="Create and validate draft skills before publish.")
    skills_canonical_app = typer.Typer(help="Maintain published canonical skills safely.")

    app.add_typer(facts_app, name="facts")
    app.add_typer(audit_app, name="audit")
    app.add_typer(snapshots_app, name="snapshots")
    app.add_typer(host_app, name="host")
    app.add_typer(skills_app, name="skills")
    skills_app.add_typer(skills_draft_app, name="draft")
    skills_app.add_typer(skills_canonical_app, name="canonical")

    @app.callback()
    def callback(
        ctx: typer.Context,
        version: Annotated[
            bool,
            typer.Option(
                "--version",
                help="Show installed version and exit.",
                callback=_version_callback,
                is_eager=True,
            ),
        ] = False,
        output_format: Annotated[
            str,
            typer.Option(
                "--format",
                "-f",
                help="Global output format.",
                case_sensitive=False,
                click_type=click.Choice(["human", "json", "summary"], case_sensitive=False),
            ),
        ] = "human",
    ) -> None:
        _ = version
        ctx.obj = {"output_format": output_format.lower()}

    @app.command("init")
    def init_command(
        ctx: typer.Context,
        runtimes: Annotated[
            list[str] | None,
            typer.Option("--runtime", help="Runtime to configure. May be used multiple times."),
        ] = None,
        hosts: Annotated[
            list[str] | None,
            typer.Option("--hosts", help="Legacy host option. Prefer --runtime."),
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
                selected_runtimes=runtimes,
                selected_hosts=hosts,
                yes=yes,
                host_setup_command=host_setup_command,
                host_check_command=host_check_command,
                locale_resolver=locale_resolver,
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

    @app.command("doctor")
    def doctor(ctx: typer.Context, output_format: OutputFormatOption = None) -> None:
        if doctor_command is None:
            msg = "CLI doctor_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_doctor(doctor_command, output_format=_effective_format(ctx, output_format))
        )

    @app.command("update")
    def update(  # noqa: PLR0913
        ctx: typer.Context,
        check: Annotated[bool, typer.Option("--check", help="Check local update status.")] = False,
        migrate: Annotated[
            bool,
            typer.Option("--migrate", help="Migrate config and memory to the current schema."),
        ] = False,
        benchmarks: Annotated[
            bool,
            typer.Option("--benchmarks", help="Update local benchmarks offline."),
        ] = False,
        skills: Annotated[
            bool,
            typer.Option(
                "--skills",
                help=(
                    "Update managed UMEM skill templates and synchronize active skills into "
                    "native runtime targets."
                ),
            ),
        ] = False,
        yes: YesOption = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if update_check_command is None and not any([migrate, benchmarks, skills]):
            msg = "CLI update_check_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_update(
                check_command=update_check_command,
                migrate_command=update_migrate_command,
                benchmarks_command=update_benchmarks_command,
                list_skills_command=list_skills_command,
                sync_skills_command=sync_skills_command,
                update_skill_command=update_skill_command,
                update_managed_skills_command=update_managed_skills_command,
                output_format=_effective_format(ctx, output_format),
                check=check,
                migrate=migrate,
                benchmarks=benchmarks,
                skills=skills,
                yes=yes,
            )
        )

    @app.command("context")
    def context(
        ctx: typer.Context,
        scope: Annotated[
            str,
            typer.Option(
                "--scope",
                help="Context scope.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = "project",
        max_size_chars: Annotated[
            int,
            typer.Option("--max-size-chars", min=1, help="Maximum context size in chars."),
        ] = DEFAULT_CONTEXT_MAX_SIZE_CHARS,
        agent_session_key: Annotated[
            str | None,
            typer.Option("--agent-session-key", help="Agent session key."),
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
        content: Annotated[str, typer.Argument(help="Fact content to store.")],
        scope: Annotated[
            str,
            typer.Option(
                "--scope",
                help="Fact scope.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = "project",
        tags: Annotated[
            list[str] | None,
            typer.Option("--tag", help="Fact tag. May be used multiple times."),
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
                help="Scope filter.",
                click_type=click.Choice(["project", "global"], case_sensitive=False),
            ),
        ] = None,
        status: Annotated[
            str | None,
            typer.Option(
                "--status",
                help="Status filter.",
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
        id: Annotated[str | None, typer.Option("--id", help="Fact ID to purge.")] = None,
        scope: Annotated[
            str | None,
            typer.Option(
                "--scope",
                help="Scope to purge.",
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
                ValidationFailedError("Provide exactly one option: --id or --scope."),
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
                help="Scope filter.",
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
                help="Scope filter.",
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
                help="Rollback scope.",
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
        host_id: Annotated[str, typer.Argument(help="Host to configure.")],
        yes: YesOption = False,
        max_lines: Annotated[int, typer.Option("--max-lines", help="Maximum line count.")] = 100,
        max_chars: Annotated[
            int, typer.Option("--max-chars", help="Maximum character count.")
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
        host_id: Annotated[str, typer.Argument(help="Host to validate.")],
        max_lines: Annotated[int, typer.Option("--max-lines", help="Maximum line count.")] = 100,
        max_chars: Annotated[
            int, typer.Option("--max-chars", help="Maximum character count.")
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
    def host_sync(  # noqa: PLR0913
        ctx: typer.Context,
        apply: Annotated[
            bool,
            typer.Option(
                "--apply/--no-apply",
                help="Apply synchronization or only show a preview.",
            ),
        ] = False,
        yes: YesOption = False,
        host_id: Annotated[
            list[str] | None,
            typer.Option("--host", help="Host to synchronize. May be used multiple times."),
        ] = None,
        max_lines: Annotated[int, typer.Option("--max-lines", help="Maximum line count.")] = 100,
        max_chars: Annotated[
            int, typer.Option("--max-chars", help="Maximum character count.")
        ] = 4000,
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
                max_lines=max_lines,
                max_chars=max_chars,
            )
        )

    @skills_app.command("propose")
    def skills_propose(
        ctx: typer.Context,
        latent_skill_id: Annotated[str, typer.Argument(help="Latent skill ID.")],
        decision: Annotated[
            str | None,
            typer.Option(
                "--decision",
                help="Explicit decision: yes, always, or no.",
                click_type=click.Choice(
                    [
                        "yes",
                        "y",
                        "always",
                        "no",
                        "n",
                    ],
                    case_sensitive=False,
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

    @skills_app.command("recommend")
    def skills_recommend(
        ctx: typer.Context,
        scope: Annotated[
            str,
            typer.Option(
                "--scope",
                help="Recommendation scope.",
                click_type=click.Choice(["project", "global", "all"], case_sensitive=False),
            ),
        ] = "project",
        min_recurrence: Annotated[
            int | None,
            typer.Option("--min-recurrence", min=1, help="Minimum recurrence threshold."),
        ] = None,
        output_format: OutputFormatOption = None,
    ) -> None:
        if recommend_skills_command is None:
            msg = "CLI recommend_skills_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_recommend(
                recommend_skills_command,
                output_format=_effective_format(ctx, output_format),
                scope=_latent_skill_scope_optional_all(scope),
                min_recurrence=min_recurrence,
            )
        )

    @skills_app.command("detail")
    def skills_detail(
        ctx: typer.Context,
        name_or_id: Annotated[str, typer.Argument(help="Skill name or ID.")],
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

    @skills_app.command("track")
    def skills_track(  # noqa: PLR0913
        ctx: typer.Context,
        name: Annotated[str, typer.Option("--name", help="Skill name.")],
        description: Annotated[str, typer.Option("--description", help="Skill description.")],
        scope: Annotated[
            LatentSkillScope,
            typer.Option("--scope", help="Skill scope (project or global)."),
        ] = LatentSkillScope.project,
        evidence_summary: Annotated[
            str,
            typer.Option(
                "--evidence-summary",
                "--evidence",
                help="Summary of the evidence that triggered this skill tracking.",
            ),
        ] = "Manual user invocation via CLI.",
        tag: Annotated[
            list[str] | None,
            typer.Option(
                "--tag",
                help="Tag/trigger for the skill. May be used multiple times.",
            ),
        ] = None,
        output_format: OutputFormatOption = None,
    ) -> None:
        if track_latent_skill_command is None:
            msg = "CLI track_latent_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_track(
                track_latent_skill_command,
                output_format=_effective_format(ctx, output_format),
                name=name,
                description=description,
                scope=scope,
                evidence_summary=evidence_summary,
                tags=tag or [],
            )
        )

    @skills_app.command(
        "create",
        help=(
            "Create a canonical skill directly. Use draft create first when the content "
            "needs review; native targets are not synced unless --sync is used."
        ),
    )
    def skills_create(  # noqa: PLR0913
        ctx: typer.Context,
        name: Annotated[str, typer.Option("--name", help="Skill name.")],
        description: Annotated[str, typer.Option("--description", help="Skill description.")],
        slug: Annotated[str | None, typer.Option("--slug", help="Explicit skill slug.")] = None,
        sync: Annotated[
            bool,
            typer.Option(
                "--sync",
                help="Also synchronize the new canonical skill into native runtime targets.",
            ),
        ] = False,
        target: Annotated[
            list[str] | None,
            typer.Option("--target", help="Runtime target to sync. May be used multiple times."),
        ] = None,
        trigger: Annotated[
            list[str] | None,
            typer.Option("--trigger", help="Skill trigger. May be used multiple times."),
        ] = None,
        scope: Annotated[
            LatentSkillScope,
            typer.Option("--scope", help="Skill scope (project or global)."),
        ] = LatentSkillScope.project,
        output_format: OutputFormatOption = None,
    ) -> None:
        if create_skill_command is None:
            msg = "CLI create_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_create(
                create_skill_command,
                output_format=_effective_format(ctx, output_format),
                name=name,
                description=description,
                triggers=trigger,
                scope=scope,
                slug=slug,
                sync=sync,
                targets=target,
            )
        )

    @skills_draft_app.command(
        "create",
        help=(
            "Start an editable draft without native side effects. Use skills create "
            "for a known-good skill that can become canonical immediately."
        ),
    )
    def skills_draft_create(  # noqa: PLR0913
        ctx: typer.Context,
        name: Annotated[str, typer.Option("--name", help="Draft skill name.")],
        description: Annotated[str, typer.Option("--description", help="Draft skill description.")],
        slug: Annotated[str | None, typer.Option("--slug", help="Explicit draft slug.")] = None,
        trigger: Annotated[
            list[str] | None,
            typer.Option("--trigger", help="Draft trigger. May be used multiple times."),
        ] = None,
        scope: Annotated[
            LatentSkillScope,
            typer.Option("--scope", help="Skill scope (project or global)."),
        ] = LatentSkillScope.project,
        output_format: OutputFormatOption = None,
    ) -> None:
        if create_skill_draft_command is None:
            msg = "CLI create_skill_draft_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_draft_create(
                create_skill_draft_command,
                output_format=_effective_format(ctx, output_format),
                name=name,
                description=description,
                slug=slug,
                triggers=trigger,
                scope=scope,
            )
        )

    @skills_draft_app.command(
        "validate",
        help=(
            "Validate a draft skill before publish. Use skills validate for an already "
            "canonical skill or an arbitrary skill path."
        ),
    )
    def skills_draft_validate(
        ctx: typer.Context,
        draft_or_path: Annotated[str, typer.Argument(help="Draft slug, id, name, or path.")],
        output_format: OutputFormatOption = None,
    ) -> None:
        if validate_skill_command is None:
            msg = "CLI validate_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_validate(
                validate_skill_command,
                output_format=_effective_format(ctx, output_format),
                skill_or_path=draft_or_path,
            )
        )

    @skills_app.command(
        "publish",
        help=(
            "Publish a validated draft into .umem/skills. Native targets are not synced "
            "unless --sync is used."
        ),
    )
    def skills_publish(  # noqa: PLR0913
        ctx: typer.Context,
        draft_or_path: Annotated[str, typer.Argument(help="Draft slug, id, name, or path.")],
        slug: Annotated[str | None, typer.Option("--slug", help="Published skill slug.")] = None,
        sync: Annotated[
            bool,
            typer.Option(
                "--sync",
                help="Sync native targets after publish. Default is canonical-only.",
            ),
        ] = False,
        target: Annotated[
            list[str] | None,
            typer.Option("--target", help="Runtime target to sync. May be used multiple times."),
        ] = None,
        output_format: OutputFormatOption = None,
    ) -> None:
        if publish_skill_command is None:
            msg = "CLI publish_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_publish(
                publish_skill_command,
                output_format=_effective_format(ctx, output_format),
                draft_or_path=draft_or_path,
                slug=slug,
                sync=sync,
                targets=target,
            )
        )

    @skills_app.command("promote")
    def skills_promote(  # noqa: PLR0913
        ctx: typer.Context,
        recommendation_id: Annotated[str, typer.Argument(help="Latent skill recommendation ID.")],
        name: Annotated[str | None, typer.Option("--name", help="Approved skill name.")] = None,
        description: Annotated[
            str | None,
            typer.Option("--description", help="Approved skill description."),
        ] = None,
        trigger: Annotated[
            list[str] | None,
            typer.Option("--trigger", help="Approved trigger. May be used multiple times."),
        ] = None,
        yes: YesOption = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if promote_skill_recommendation_command is None:
            msg = "CLI promote_skill_recommendation_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_promote(
                promote_skill_recommendation_command,
                output_format=_effective_format(ctx, output_format),
                recommendation_id=recommendation_id,
                name=name,
                description=description,
                triggers=trigger,
                yes=yes,
            )
        )

    @skills_app.command("import")
    def skills_import(  # noqa: PLR0913
        ctx: typer.Context,
        path: Annotated[
            Path,
            typer.Argument(
                help=(
                    "Existing Agent Skills directory or its SKILL.md file, for example "
                    ".agents/skills/review-helper or .agents/skills/review-helper/SKILL.md."
                )
            ),
        ],
        scope: Annotated[
            LatentSkillScope,
            typer.Option("--scope", help="Skill scope (project or global)."),
        ] = LatentSkillScope.project,
        replace_native: Annotated[
            bool,
            typer.Option(
                "--replace-native",
                help=(
                    "After import, rewrite the matching managed native source target from "
                    "the canonical copy. Omit to adopt without rewriting."
                ),
            ),
        ] = False,
        sync_after_import: Annotated[
            bool,
            typer.Option(
                "--sync",
                help=(
                    "After importing into .umem/skills, synchronize complete copies to "
                    "configured native runtime targets."
                ),
            ),
        ] = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if import_skill_command is None:
            msg = "CLI import_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_import(
                import_skill_command,
                output_format=_effective_format(ctx, output_format),
                path=path,
                scope=scope,
                replace_native=replace_native,
                sync_after_import=sync_after_import,
            )
        )

    @skills_app.command(
        "adopt",
        help=(
            "Register an existing .umem/skills directory in place. Use import for "
            "native directories such as .agents/skills or .opencode/skills."
        ),
    )
    def skills_adopt(  # noqa: PLR0913
        ctx: typer.Context,
        path: Annotated[Path, typer.Argument(help="Existing skill directory or SKILL.md.")],
        slug: Annotated[str | None, typer.Option("--slug", help="Slug to register.")] = None,
        scope: Annotated[
            LatentSkillScope,
            typer.Option("--scope", help="Skill scope (project or global)."),
        ] = LatentSkillScope.project,
        replace_native: Annotated[
            bool,
            typer.Option(
                "--replace-native",
                help="Rewrite the matching managed native source after adoption.",
            ),
        ] = False,
        sync_after_adopt: Annotated[
            bool,
            typer.Option(
                "--sync",
                help="Sync native targets after adoption. Default only registers canonical.",
            ),
        ] = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if adopt_skill_command is None:
            msg = "CLI adopt_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_adopt(
                adopt_skill_command,
                output_format=_effective_format(ctx, output_format),
                path=path,
                slug=slug,
                scope=scope,
                replace_native=replace_native,
                sync_after_adopt=sync_after_adopt,
            )
        )

    @skills_app.command(
        "validate",
        help=(
            "Validate canonical skill content or a skill path. Use draft validate "
            "when checking an unpublished draft."
        ),
    )
    def skills_validate(
        ctx: typer.Context,
        skill_or_path: Annotated[str, typer.Argument(help="Skill id, slug, name, or path.")],
        output_format: OutputFormatOption = None,
    ) -> None:
        if validate_skill_command is None:
            msg = "CLI validate_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_validate(
                validate_skill_command,
                output_format=_effective_format(ctx, output_format),
                skill_or_path=skill_or_path,
            )
        )

    @skills_canonical_app.command(
        "update",
        help=(
            "Replace canonical SKILL.md content after validation. Use skills update "
            "only for latent/generated skill metadata."
        ),
    )
    def skills_canonical_update(  # noqa: PLR0913
        ctx: typer.Context,
        skill_id_or_name: Annotated[str, typer.Argument(help="Canonical skill id, slug, or name.")],
        file: Annotated[Path, typer.Option("--file", help="Replacement SKILL.md path.")],
        sync: Annotated[
            bool,
            typer.Option(
                "--sync",
                help="Sync native targets after update. Default updates canonical only.",
            ),
        ] = False,
        drift_decision: Annotated[
            str,
            typer.Option(
                "--drift-decision",
                click_type=click.Choice(["keep", "overwrite"], case_sensitive=False),
            ),
        ] = "keep",
        output_format: OutputFormatOption = None,
    ) -> None:
        if update_canonical_skill_command is None:
            msg = "CLI update_canonical_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_canonical_update(
                update_canonical_skill_command,
                output_format=_effective_format(ctx, output_format),
                skill_id_or_name=skill_id_or_name,
                file=file,
                sync=sync,
                drift_decision=drift_decision,
            )
        )

    @skills_app.command(
        "rename",
        help=(
            "Rename a canonical skill slug. Run skills sync afterward when native "
            "runtime targets should move too."
        ),
    )
    def skills_rename(
        ctx: typer.Context,
        skill_id_or_name: Annotated[str, typer.Argument(help="Canonical skill id, slug, or name.")],
        slug: Annotated[str, typer.Option("--slug", help="New slug.")],
        output_format: OutputFormatOption = None,
    ) -> None:
        if rename_skill_command is None:
            msg = "CLI rename_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_rename(
                rename_skill_command,
                output_format=_effective_format(ctx, output_format),
                skill_id_or_name=skill_id_or_name,
                slug=slug,
            )
        )

    @skills_app.command(
        "cleanup",
        help=(
            "Preview or apply managed target cleanup for one skill. Default is dry-run; "
            "use --apply to delete removable managed paths."
        ),
    )
    def skills_cleanup(  # noqa: PLR0913
        ctx: typer.Context,
        skill_id_or_name: Annotated[str, typer.Argument(help="Canonical skill id, slug, or name.")],
        apply: Annotated[
            bool,
            typer.Option(
                "--apply",
                help="Delete removable managed paths. Default is dry-run preview.",
            ),
        ] = False,
        targets: Annotated[
            bool,
            typer.Option("--targets", help="Plan native target cleanup for this skill."),
        ] = True,
        dry_run: Annotated[
            bool,
            typer.Option("--dry-run", help="Preview cleanup without deleting managed paths."),
        ] = True,
        output_format: OutputFormatOption = None,
    ) -> None:
        if cleanup_skill_command is None:
            msg = "CLI cleanup_skill_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_cleanup(
                cleanup_skill_command,
                output_format=_effective_format(ctx, output_format),
                skill_id_or_name=skill_id_or_name,
                targets=targets,
                dry_run=dry_run and not apply,
            )
        )

    @skills_app.command(
        "repair",
        help=(
            "Preview or apply project-wide repair for orphan managed targets. Default "
            "is dry-run; use --apply with --remove-orphan-targets to delete."
        ),
    )
    def skills_repair(
        ctx: typer.Context,
        remove_orphan_targets: Annotated[
            bool,
            typer.Option(
                "--remove-orphan-targets",
                help="Plan cleanup for managed native targets without a canonical skill.",
            ),
        ] = False,
        apply: Annotated[
            bool,
            typer.Option(
                "--apply",
                help="Delete removable managed orphan targets. Default is dry-run preview.",
            ),
        ] = False,
        dry_run: Annotated[
            bool,
            typer.Option("--dry-run", help="Preview repair without deleting managed paths."),
        ] = True,
        output_format: OutputFormatOption = None,
    ) -> None:
        if repair_skills_command is None:
            msg = "CLI repair_skills_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_repair(
                repair_skills_command,
                output_format=_effective_format(ctx, output_format),
                remove_orphan_targets=remove_orphan_targets,
                dry_run=dry_run and not apply,
            )
        )

    @skills_app.command(
        "sync",
        help=(
            "Materialize canonical skills into native runtime targets. Use "
            "--check-gitignore for diagnostics; it does not edit .gitignore."
        ),
    )
    def skills_sync(  # noqa: PLR0913
        ctx: typer.Context,
        skill_id_or_name: Annotated[
            str | None,
            typer.Argument(help="Optional canonical skill ID, slug, or exact name."),
        ] = None,
        target: Annotated[
            list[str] | None,
            typer.Option("--target", help="Native runtime ID. May be used multiple times."),
        ] = None,
        drift_decision: Annotated[
            str,
            typer.Option(
                "--drift-decision",
                help="How to handle managed native drift.",
                click_type=click.Choice(["keep", "overwrite"], case_sensitive=False),
            ),
        ] = "keep",
        check_gitignore: Annotated[
            bool,
            typer.Option(
                "--check-gitignore",
                help=(
                    "After planning/writing targets, warn when generated runtime paths "
                    "are tracked or not ignored by git. Does not edit .gitignore."
                ),
            ),
        ] = False,
        output_format: OutputFormatOption = None,
    ) -> None:
        if sync_skills_command is None:
            msg = "CLI sync_skills_command dependency was not configured."
            raise RuntimeError(msg)
        raise typer.Exit(
            code=_run_skills_sync(
                sync_skills_command,
                output_format=_effective_format(ctx, output_format),
                skill_id_or_name=skill_id_or_name,
                targets=target,
                drift_decision=drift_decision,
                check_gitignore=check_gitignore,
            )
        )

    @skills_app.command("generate")
    def skills_generate(
        ctx: typer.Context,
        latent_skill_id: Annotated[str, typer.Argument(help="Approved latent skill ID.")],
        yes: YesOption = False,
        update_existing: Annotated[
            bool,
            typer.Option(
                "--update-existing",
                help="Update an existing skill instead of creating an alternate slug.",
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
        latent_skill_id: Annotated[str, typer.Argument(help="Latent skill ID.")],
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
        latent_skill_id: Annotated[str, typer.Argument(help="Latent skill ID.")],
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
        latent_skill_id: Annotated[str, typer.Argument(help="Latent skill ID.")],
        name: Annotated[str | None, typer.Option("--name", help="New skill name.")] = None,
        description: Annotated[
            str | None,
            typer.Option("--description", help="New skill description."),
        ] = None,
        trigger: Annotated[
            list[str] | None,
            typer.Option("--trigger", help="Skill trigger. May be used multiple times."),
        ] = None,
        file: Annotated[
            Path | None,
            typer.Option("--file", help="Markdown file with new skill content."),
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
                yes=False,
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
    doctor_command: DoctorCommandHandler,
    context_command: ContextCommandHandler,
    remember_command: RememberFactCommandHandler,
    facts_list_command: ListFactsCommandHandler,
    facts_purge_command: PurgeFactCommandHandler,
    facts_hygiene_command: ContextHygieneCommandHandler,
    host_setup_command: ConfigureHostCommandHandler,
    host_check_command: ConfigureHostCommandHandler,
    host_sync_command: SyncInstructionsCommandHandler,
    propose_skill_command: ProposeSkillCommandHandler | None = None,
    track_latent_skill_command: TrackLatentSkillCommandHandler | None = None,
    generate_skill_command: GenerateSkillCommandHandler | None = None,
    create_skill_command: CreateSkillCommandHandler | None = None,
    create_skill_draft_command: CreateSkillDraftCommandHandler | None = None,
    publish_skill_command: PublishSkillCommandHandler | None = None,
    validate_skill_command: ValidateSkillCommandHandler | None = None,
    adopt_skill_command: AdoptSkillCommandHandler | None = None,
    update_canonical_skill_command: UpdateCanonicalSkillCommandHandler | None = None,
    rename_skill_command: RenameSkillCommandHandler | None = None,
    cleanup_skill_command: CleanupSkillCommandHandler | None = None,
    repair_skills_command: RepairSkillsCommandHandler | None = None,
    promote_skill_recommendation_command: PromoteSkillRecommendationCommandHandler | None = None,
    import_skill_command: ImportSkillCommandHandler | None = None,
    recommend_skills_command: RecommendSkillsCommandHandler | None = None,
    sync_skills_command: SyncSkillsCommandHandler | None = None,
    list_skills_command: ListSkillsCommandHandler | None = None,
    get_skill_detail_command: GetSkillDetailCommandHandler | None = None,
    activate_skill_command: ActivateSkillCommandHandler | None = None,
    deactivate_skill_command: DeactivateSkillCommandHandler | None = None,
    update_skill_command: UpdateSkillCommandHandler | None = None,
    update_check_command: UpdateCheckCommandHandler | None = None,
    update_managed_skills_command: UpdateManagedSkillsCommandHandler | None = None,
    update_migrate_command: UpdateMigrateCommandHandler | None = None,
    update_benchmarks_command: UpdateBenchmarksCommandHandler | None = None,
    locale_resolver: LocaleResolver | None = None,
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
            doctor_command=doctor_command,
            context_command=context_command,
            remember_command=remember_command,
            facts_list_command=facts_list_command,
            facts_purge_command=facts_purge_command,
            facts_hygiene_command=facts_hygiene_command,
            host_setup_command=host_setup_command,
            host_check_command=host_check_command,
            host_sync_command=host_sync_command,
            propose_skill_command=propose_skill_command,
            track_latent_skill_command=track_latent_skill_command,
            generate_skill_command=generate_skill_command,
            create_skill_command=create_skill_command,
            create_skill_draft_command=create_skill_draft_command,
            publish_skill_command=publish_skill_command,
            validate_skill_command=validate_skill_command,
            adopt_skill_command=adopt_skill_command,
            update_canonical_skill_command=update_canonical_skill_command,
            rename_skill_command=rename_skill_command,
            cleanup_skill_command=cleanup_skill_command,
            repair_skills_command=repair_skills_command,
            promote_skill_recommendation_command=promote_skill_recommendation_command,
            import_skill_command=import_skill_command,
            recommend_skills_command=recommend_skills_command,
            sync_skills_command=sync_skills_command,
            list_skills_command=list_skills_command,
            get_skill_detail_command=get_skill_detail_command,
            activate_skill_command=activate_skill_command,
            deactivate_skill_command=deactivate_skill_command,
            update_skill_command=update_skill_command,
            update_check_command=update_check_command,
            update_managed_skills_command=update_managed_skills_command,
            update_migrate_command=update_migrate_command,
            update_benchmarks_command=update_benchmarks_command,
            locale_resolver=locale_resolver,
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
    value = os.environ.get("CI")
    if value is None:
        return False
    return value.strip().lower() not in {"", "0", "false", "no", "off"}


def _should_render_init_splash(output_format: str) -> bool:
    return (
        output_format != "json"
        and _stream_is_tty(sys.stdout)
        and _stream_is_tty(sys.stdin)
        and not _ci_environment_enabled()
    )


def _render_init_splash() -> None:
    sys.stdout.write("\n".join(INIT_SPLASH_LINES) + "\n")


def _confirm(prompt: str, default: bool = False) -> bool:
    answer = input(prompt)
    val = answer.strip().lower()
    if not val:
        return default
    return val in {"y", "yes"}


def _prompt(prompt: str) -> str:
    return input(prompt)


def _run_init(  # noqa: PLR0913
    command: SetupProjectCommand,
    output_format: str,
    *,
    selected_runtimes: list[str] | None = None,
    selected_hosts: list[str] | None = None,
    yes: bool = False,
    host_setup_command: ConfigureHostCommandHandler | None = None,
    host_check_command: ConfigureHostCommandHandler | None = None,
    locale_resolver: LocaleResolver | None = None,
) -> int:
    resolve_locale = locale_resolver or (lambda: DEFAULT_LOCALE)
    locale = resolve_locale() if output_format != "json" else DEFAULT_LOCALE
    try:
        if _should_render_init_splash(output_format):
            _render_init_splash()
        runtime_ids = _selected_init_runtimes(
            selected_runtimes,
            selected_hosts=selected_hosts,
            output_format=output_format,
            yes=yes,
            locale=locale,
        )
        if output_format == "json":
            result = _execute_setup_project(command, Path.cwd(), runtime_ids)
        else:
            with _stderr_console().status(
                human_message("Initializing project scaffold...", locale=locale), spinner="dots"
            ):
                result = _execute_setup_project(command, Path.cwd(), runtime_ids)
            locale = resolve_locale()
        host_results = _configure_init_hosts(
            runtime_ids,
            output_format=output_format,
            locale=locale,
            host_setup_command=host_setup_command,
            host_check_command=host_check_command,
        )
    except (KeyboardInterrupt, EOFError):
        _stdout_console().print("\n" + human_message("Operation cancelled by user.", locale=locale))
        return 1
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format, locale=locale)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format, locale=locale)
        return 1

    if output_format == "json":
        payload = _success_envelope(result)
        payload.update(_init_runtime_payload(runtime_ids, host_results))
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
    enabled_runtime_ids: list[str],
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
            or "enabled_runtime_ids" in sig.parameters
            or "enabled_host_ids" in sig.parameters
        ):
            return command(project_root, enabled_runtime_ids)  # type: ignore
    except (ValueError, TypeError):
        pass
    return command(project_root)  # type: ignore


def _selected_init_runtimes(
    runtimes: list[str] | None,
    *,
    selected_hosts: list[str] | None = None,
    output_format: str,
    yes: bool,
    locale: str = DEFAULT_LOCALE,
) -> list[str]:
    if runtimes:
        return _normalize_supported_runtimes(runtimes)
    if selected_hosts:
        return _normalize_supported_runtimes(selected_hosts)
    if output_format == "json" or yes:
        return list(DEFAULT_ENABLED_RUNTIME_IDS)
    if not sys.stdin.isatty():
        return list(DEFAULT_ENABLED_RUNTIME_IDS)

    registry = default_runtime_registry()
    _stdout_console().print(
        human_message("Which runtime(s) would you like to install for?", locale=locale)
    )
    for index, runtime in enumerate(registry.runtimes, start=1):
        _stdout_console().print(f"{index}. {runtime.display_name} ({runtime.support_tier.value})")
    answer = _prompt(
        human_message(
            "Which runtime(s) would you like to install for? [1 2 3 4 5]: ",
            locale=locale,
        )
    )
    return _parse_runtime_index_selection(answer, registry.runtimes)


def _normalize_supported_runtimes(runtimes: list[str]) -> list[str]:
    normalized: list[str] = []
    for runtime_id in runtimes:
        cleaned = "_".join(runtime_id.strip().lower().split("-"))
        if cleaned not in normalized:
            normalized.append(cleaned)
    supported = {runtime_id.value for runtime_id in default_runtime_registry().runtime_ids}
    unsupported = [runtime_id for runtime_id in normalized if runtime_id not in supported]
    if unsupported:
        raise ValidationFailedError(f"Unsupported runtimes: {', '.join(unsupported)}")
    return normalized


def _parse_runtime_index_selection(
    raw_selection: str,
    runtimes: list[RuntimeAdapter],
) -> list[str]:
    if not raw_selection.strip():
        return [runtime.runtime_id.value for runtime in runtimes]
    tokens = [
        token for comma_part in raw_selection.split(",") for token in comma_part.split() if token
    ]
    selected: list[str] = []
    invalid: list[str] = []
    for token in tokens:
        if not token.isdecimal():
            invalid.append(token)
            continue
        index = int(token)
        if index < 1 or index > len(runtimes):
            invalid.append(token)
            continue
        runtime_id = runtimes[index - 1].runtime_id.value
        if runtime_id not in selected:
            selected.append(runtime_id)
    if invalid:
        raise ValidationFailedError(
            "Invalid runtime selection: "
            f"{', '.join(invalid)}. Use numbers from 1 to {len(runtimes)}."
        )
    return selected


def _init_runtime_payload(
    selected_runtime_ids: list[str],
    host_results: list[ConfigureHostResult],
) -> dict[str, Any]:
    registry = default_runtime_registry()
    selected = set(selected_runtime_ids)
    target_paths: dict[str, list[str]] = {}
    for result in host_results:
        if result.host_id not in selected:
            continue
        paths = target_paths.setdefault(result.host_id, [])
        for change in result.planned_changes:
            path = change.get("path")
            if isinstance(path, str) and path not in paths:
                paths.append(path)

    manual_steps_pending = [
        {"runtime_id": result.host_id, "step": step}
        for result in host_results
        for step in result.manual_steps
    ]
    return {
        "runtimes_selected": selected_runtime_ids,
        "runtimes_skipped": [
            runtime.runtime_id.value
            for runtime in registry.runtimes
            if runtime.runtime_id.value not in selected
        ],
        "target_paths": target_paths,
        "manual_steps_pending": manual_steps_pending,
    }


def _configure_init_hosts(
    host_ids: list[str],
    *,
    output_format: str,
    locale: str = "en",
    host_setup_command: ConfigureHostCommandHandler | None,
    host_check_command: ConfigureHostCommandHandler | None,
) -> list[ConfigureHostResult]:
    host_ids = [host_id for host_id in host_ids if host_id in LEGACY_CONFIGURABLE_RUNTIME_IDS]
    if host_ids and (host_setup_command is None or host_check_command is None):
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


def _run_doctor(command: DoctorCommandHandler, *, output_format: str) -> int:
    try:
        result = command(DoctorCommand(project_root=Path.cwd()))
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
        print(json.dumps(_doctor_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_doctor_output(result))

    return 0 if result.ok else 1


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
                "The --yes / -y flag is required to run purge with JSON output."
            )
        if output_format != "json":
            _stdout_console().print(_format_human_purge_preview(id=id, scope=scope))
            if not yes:
                if not _confirm("Confirm permanent purge? [y/N]: ", default=False):
                    _stdout_console().print("Purge cancelled.")
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
                "[yellow]Warning: facts hygiene will optimize and clean memory context, "
                "and may archive obsolete facts.[/yellow]"
            )
            if not yes:
                if not _confirm("Proceed with hygiene? [y/N]: ", default=False):
                    _stdout_console().print("Hygiene cancelled.")
                    return 1

        if output_format == "json":
            result = command(ContextHygieneCommand(scope=scope))
        else:
            with _stderr_console().status("Running context hygiene...", spinner="dots"):
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
                "The --yes / -y flag is required to run rollback with JSON output."
            )
        preview = rollback_preview_command(scope)
        if output_format != "json":
            _stdout_console().print(_format_human_rollback_preview(preview))
            if not yes:
                if not _confirm("Proceed with rollback? [y/N]: ", default=False):
                    _stdout_console().print("Rollback cancelled.")
                    return 1

        if output_format == "json":
            result = command(RollbackCommand(scope=scope, origin="cli"))
        else:
            with _stderr_console().status("Restoring snapshot (rollback)...", spinner="dots"):
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
                "The --yes / -y flag is required to run host setup with JSON output."
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
                if not _confirm("Apply host configuration? [y/N]: ", default=False):
                    _stdout_console().print("Host setup cancelled.")
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


def _run_host_sync(  # noqa: PLR0913
    command: SyncInstructionsCommandHandler,
    *,
    output_format: str,
    host_ids: list[str],
    apply: bool,
    yes: bool,
    max_lines: int = 100,
    max_chars: int = 4000,
) -> int:
    try:
        if apply and output_format == "json" and not yes:
            raise ValidationFailedError(
                "The --yes / -y flag is required to run host sync with JSON output."
            )
        if apply and output_format != "json":
            preview = command(
                SyncInstructionsCommand(
                    host_ids=host_ids,
                    apply=False,
                    max_managed_lines=max_lines,
                    max_managed_chars=max_chars,
                    origin="cli",
                )
            )
            _stdout_console().print(_format_human_sync_plan(preview))
            if not yes:
                if not (sys.stdin.isatty() and sys.stdout.isatty()):
                    raise ValidationFailedError(
                        "Non-TTY environment requires --yes to apply host sync. "
                        "Use `umem host sync --apply --yes --format json` for automation."
                    )
                if not _confirm("Apply instruction synchronization? [y/N]: ", default=False):
                    _stdout_console().print("Instruction synchronization cancelled.")
                    return 1

        result = command(
            SyncInstructionsCommand(
                host_ids=host_ids,
                apply=apply,
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
        print(json.dumps(_host_success_envelope(result, operation="host_sync"), sort_keys=True))
    else:
        if not apply:
            _stdout_console().print(_format_human_sync_plan(result))
            _stdout_console().print()
        _stdout_console().print(_format_human_sync_success(result))
    return 0


def _run_update(  # noqa: PLR0911, PLR0912, PLR0913, PLR0915
    *,
    check_command: UpdateCheckCommandHandler | None,
    migrate_command: UpdateMigrateCommandHandler | None,
    benchmarks_command: UpdateBenchmarksCommandHandler | None,
    list_skills_command: ListSkillsCommandHandler | None,
    sync_skills_command: SyncSkillsCommandHandler | None,
    update_skill_command: UpdateSkillCommandHandler | None,
    update_managed_skills_command: UpdateManagedSkillsCommandHandler | None,
    output_format: str,
    check: bool,
    migrate: bool,
    benchmarks: bool,
    skills: bool,
    yes: bool,
) -> int:
    apply_default_update = not any([check, migrate, benchmarks, skills])
    selected_count = sum([check, migrate, benchmarks, skills])
    if not apply_default_update and selected_count != 1:
        _print_expected_error(
            ValidationFailedError("Provide only one update option per execution."),
            output_format=output_format,
        )
        return 1

    try:
        if apply_default_update:
            if check_command is None:
                raise RuntimeError("CLI update_check_command dependency was not configured.")
            check_result = check_command(UpdateCheckCommand(project_root=Path.cwd()))
            migrate_result: UpdateMigrateResult | None = None
            if check_result.migration_required:
                if migrate_command is None:
                    raise RuntimeError("CLI update_migrate_command dependency was not configured.")
                if output_format == "json" and not yes:
                    raise ValidationFailedError(
                        "The --yes / -y flag is required to run update with JSON output when "
                        "migration is required."
                    )
                if output_format != "json":
                    _stdout_console().print(_format_human_update_check(check_result))
                    _stdout_console().print()
                    _stdout_console().print(_format_human_update_mutation_plan("update.migrate"))
                    if not yes:
                        if not _confirm("Apply pending update migration? [y/N]: ", default=False):
                            _stdout_console().print("Update cancelled.")
                            return 1
                migrate_result = migrate_command(
                    UpdateMigrateCommand(project_root=Path.cwd(), origin="cli")
                )
            if output_format == "json":
                print(
                    json.dumps(
                        _update_apply_success_envelope(check_result, migrate_result),
                        sort_keys=True,
                    )
                )
            else:
                _stdout_console().print(_format_human_update_apply(check_result, migrate_result))
            return 0

        if check:
            if check_command is None:
                raise RuntimeError("CLI update_check_command dependency was not configured.")
            result = check_command(UpdateCheckCommand(project_root=Path.cwd()))
            if output_format == "json":
                print(json.dumps(_update_check_success_envelope(result), sort_keys=True))
            else:
                _stdout_console().print(_format_human_update_check(result))
            return 0

        if migrate:
            if migrate_command is None:
                raise RuntimeError("CLI update_migrate_command dependency was not configured.")
            if output_format == "json" and not yes:
                raise ValidationFailedError(
                    "The --yes / -y flag is required to run update --migrate with JSON output."
                )
            if output_format != "json":
                _stdout_console().print(_format_human_update_mutation_plan("update.migrate"))
                if not yes:
                    if not _confirm("Apply schema migration? [y/N]: ", default=False):
                        _stdout_console().print("Migration cancelled.")
                        return 1
            result = migrate_command(UpdateMigrateCommand(project_root=Path.cwd(), origin="cli"))
            if output_format == "json":
                print(json.dumps(_update_migrate_success_envelope(result), sort_keys=True))
            else:
                _stdout_console().print(_format_human_update_migrate(result))
            return 0

        if benchmarks:
            if benchmarks_command is None:
                raise RuntimeError("CLI update_benchmarks_command dependency was not configured.")
            if output_format == "json" and not yes:
                raise ValidationFailedError(
                    "The --yes / -y flag is required to run update --benchmarks with JSON output."
                )
            if output_format != "json":
                _stdout_console().print(_format_human_update_mutation_plan("update.benchmarks"))
                if not yes:
                    if not _confirm("Update local benchmarks? [y/N]: ", default=False):
                        _stdout_console().print("Benchmark update cancelled.")
                        return 1
            result = benchmarks_command(
                UpdateBenchmarksCommand(project_root=Path.cwd(), origin="cli")
            )
            if output_format == "json":
                print(json.dumps(_update_benchmarks_success_envelope(result), sort_keys=True))
            else:
                _stdout_console().print(_format_human_update_benchmarks(result))
            return 0

        if skills:
            if (
                list_skills_command is None
                or sync_skills_command is None
                or update_skill_command is None
            ):
                raise RuntimeError("CLI skill update dependencies were not configured.")
            result = _sync_active_skills_for_update(
                list_skills_command,
                sync_skills_command,
                update_skill_command,
                update_managed_skills_command,
                output_format=output_format,
                yes=yes,
            )
            if output_format == "json":
                print(json.dumps(_update_skills_success_envelope(result), sort_keys=True))
            else:
                _stdout_console().print(_format_human_update_skills(result))
            return 0
    except OSError as error:
        _print_expected_error(StorageError(str(error)), output_format=output_format)
        return 1
    except (ValidationError, ValueError) as error:
        _print_expected_error(ValidationFailedError(str(error)), output_format=output_format)
        return 1
    except DOMAIN_ERROR_TYPES as error:
        _print_expected_error(error, output_format=output_format)
        return 1

    return 1


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


def _run_skills_recommend(
    command: RecommendSkillsCommandHandler,
    *,
    output_format: str,
    scope: LatentSkillScope | None,
    min_recurrence: int | None,
) -> int:
    try:
        result = command(RecommendSkillsCommand(scope=scope, min_recurrence=min_recurrence))
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_read_error(error), output_format=output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_recommend_success_envelope(result, scope=scope), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_recommend(result))
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
        return ValidationFailedError("Skill not found.")
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
        answer = input("Decision [yes/always/no]: ")
    except (EOFError, KeyboardInterrupt):
        _stdout_console().print("\nCancelled.")
        return None
    prompted_decision = _skill_decision(answer)
    if prompted_decision is None:
        raise ValidationFailedError("Invalid decision provided. Use yes, always, or no.")
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
            f"Latent skill '{latent_skill_id}' not found in the repository."
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
        resolved_decision = ProposeSkillDecision.yes if yes and decision is None else decision
        if resolved_decision is None and not sys.stdin.isatty():
            raise ValidationFailedError("Non-TTY environment requires --decision or --yes.")
        if output_format == "json" and resolved_decision is None:
            raise ValidationFailedError(
                "Provide --decision or --yes to run skills propose with JSON output."
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
            f"[bold yellow]WARNING: skill directory '{result.slug}' "
            "already exists and will be overwritten![/bold yellow]"
        )
        if not _confirm("Confirm overwrite and generation? [y/N]: ", default=False):
            _stdout_console().print("Skill generation cancelled.")
            return False, 1
        return True, 0

    _stdout_console().print(
        f"[bold yellow]Conflict: skill directory '{result.slug}' already exists.[/bold yellow]"
    )
    _stdout_console().print(
        f"Alternative suggestion proposed by the system: '{result.suggested_slug}'"
    )
    choice = ""
    prompt_msg = (
        "What do you want to do? [u] Update existing, "
        "[a] Use proposed alternate slug, [c] Cancel [u/a/C]: "
    )
    while choice not in {"u", "a", "c"}:
        choice = input(prompt_msg).strip().lower()
        if not choice:
            choice = "c"
    if choice == "c":
        _stdout_console().print("Skill generation cancelled.")
        return False, 1
    return choice == "u", 0


def _run_skills_track(  # noqa: PLR0913
    command: TrackLatentSkillCommandHandler,
    *,
    output_format: str,
    name: str,
    description: str,
    scope: LatentSkillScope,
    evidence_summary: str,
    tags: list[str],
) -> int:
    try:
        result = command(
            TrackLatentSkillCommand(
                name=name,
                description=description,
                scope=scope,
                origin="cli",
                evidence_summary=evidence_summary,
                tags=tags,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, name), output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_track_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_track(result))
    return 0


def _run_skills_create(  # noqa: PLR0913
    command: CreateSkillCommandHandler,
    *,
    output_format: str,
    name: str,
    description: str,
    triggers: list[str] | None,
    scope: LatentSkillScope,
    slug: str | None,
    sync: bool,
    targets: list[str] | None,
) -> int:
    try:
        result = command(
            CreateSkillCommand(
                name=name.strip(),
                description=description.strip(),
                scope=scope,
                origin="cli",
                triggers=[trigger.strip() for trigger in triggers or [] if trigger.strip()],
                slug=slug,
                sync=sync,
                targets=targets,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, name), output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_create_success_envelope(result), sort_keys=True))
    elif output_format == "summary":
        _stdout_console().print(
            _format_summary_payload("skills.create", result.to_payload(), result.warnings)
        )
    else:
        _stdout_console().print(_format_human_skill_create_success(result))
    return 0


def _run_skills_draft_create(  # noqa: PLR0913
    command: CreateSkillDraftCommandHandler,
    *,
    output_format: str,
    name: str,
    description: str,
    slug: str | None,
    triggers: list[str] | None,
    scope: LatentSkillScope,
) -> int:
    try:
        result = command(
            CreateSkillDraftCommand(
                name=name.strip(),
                description=description.strip(),
                scope=scope,
                origin="cli",
                slug=slug,
                triggers=[trigger.strip() for trigger in triggers or [] if trigger.strip()],
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, name), output_format)
        return 1
    envelope = _skill_lifecycle_envelope("skills.draft.create", scope.value, result)
    if output_format == "json":
        print(json.dumps(envelope, sort_keys=True))
    else:
        _stdout_console().print(
            _format_summary_payload("skills.draft.create", result.to_payload(), result.warnings)
        )
    return 0


def _run_skills_validate(
    command: ValidateSkillCommandHandler,
    *,
    output_format: str,
    skill_or_path: str,
) -> int:
    try:
        result = command(ValidateSkillCommand(skill_or_path=skill_or_path))
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, skill_or_path), output_format)
        return 1
    payload = result.to_payload()
    warnings = result.report.warnings
    envelope = {
        "ok": True,
        "operation": "skills.validate",
        "scope": "project",
        "data": payload,
        "warnings": warnings,
    }
    if output_format == "json":
        print(json.dumps(envelope, sort_keys=True))
    else:
        _stdout_console().print(_format_summary_payload("skills.validate", payload, warnings))
    return 0 if result.report.status != "fail" else 1


def _run_skills_publish(  # noqa: PLR0913
    command: PublishSkillCommandHandler,
    *,
    output_format: str,
    draft_or_path: str,
    slug: str | None,
    sync: bool,
    targets: list[str] | None,
) -> int:
    try:
        result = command(
            PublishSkillCommand(
                draft_or_path=draft_or_path,
                origin="cli",
                slug=slug,
                sync=sync,
                targets=targets,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, draft_or_path), output_format)
        return 1
    envelope = _skill_lifecycle_envelope("skills.publish", result.agent_skill.scope.value, result)
    if output_format == "json":
        print(json.dumps(envelope, sort_keys=True))
    else:
        _stdout_console().print(
            _format_summary_payload("skills.publish", result.to_payload(), result.warnings)
        )
    return 0


def _run_skills_promote(  # noqa: PLR0913
    command: PromoteSkillRecommendationCommandHandler,
    *,
    output_format: str,
    recommendation_id: str,
    name: str | None,
    description: str | None,
    triggers: list[str] | None,
    yes: bool,
) -> int:
    try:
        if output_format == "json" and not yes:
            raise ValidationFailedError(
                "The --yes / -y flag is required to promote a skill with JSON output."
            )
        if output_format != "json" and not yes:
            if not (sys.stdin.isatty() and sys.stdout.isatty()):
                raise ValidationFailedError(
                    "Non-TTY environment requires --yes to promote a skill."
                )
            _stdout_console().print(
                f"Promote latent skill recommendation '{recommendation_id}' into a canonical Agent Skill."
            )
            if not _confirm("Promote skill recommendation? [y/N]: ", default=False):
                _stdout_console().print("Skill promotion cancelled.")
                return 1
        result = command(
            PromoteSkillRecommendationCommand(
                recommendation_id=recommendation_id,
                origin="cli",
                name=name.strip() if name is not None else None,
                description=description.strip() if description is not None else None,
                triggers=[trigger.strip() for trigger in triggers or [] if trigger.strip()]
                if triggers is not None
                else None,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, recommendation_id), output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_promote_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_promote_success(result))
    return 0


def _run_skills_sync(  # noqa: PLR0913
    command: SyncSkillsCommandHandler,
    *,
    output_format: str,
    skill_id_or_name: str | None,
    targets: list[str] | None,
    drift_decision: str,
    check_gitignore: bool = False,
) -> int:
    try:
        resolved_decision: NativeDriftDecision = (
            "overwrite" if drift_decision == "overwrite" else "keep"
        )
        result = command(
            SyncSkillsCommand(
                skill_id_or_name=skill_id_or_name.strip() if skill_id_or_name else None,
                targets=targets,
                drift_decision=resolved_decision,
                origin="cli",
                check_gitignore=check_gitignore,
            )
        )
        if (
            output_format != "json"
            and resolved_decision == "keep"
            and sys.stdin.isatty()
            and _sync_result_has_managed_drift(result)
            and _confirm(f"{DRIFT_WARNING} ", default=False)
        ):
            result = command(
                SyncSkillsCommand(
                    skill_id_or_name=skill_id_or_name.strip() if skill_id_or_name else None,
                    targets=targets,
                    drift_decision="overwrite",
                    origin="cli",
                    check_gitignore=check_gitignore,
                )
            )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(
            _map_skill_mutation_error(error, skill_id_or_name or "skills"), output_format
        )
        return 1

    if output_format == "json":
        print(json.dumps(_skill_sync_success_envelope(result), sort_keys=True))
    elif output_format == "summary":
        _stdout_console().print(
            _format_summary_payload("skills.sync", result.to_payload(), result.warnings)
        )
    else:
        _stdout_console().print(_format_human_skill_sync_success(result))
    return 0


def _sync_result_has_managed_drift(result: SyncSkillsResult) -> bool:
    return any(
        target.get("status") == "drift_kept" for skill in result.skills for target in skill.targets
    )


def _run_skills_import(  # noqa: PLR0913
    command: ImportSkillCommandHandler,
    *,
    output_format: str,
    path: Path,
    scope: LatentSkillScope,
    replace_native: bool,
    sync_after_import: bool,
) -> int:
    try:
        result = command(
            ImportSkillCommand(
                path=path,
                scope=scope,
                origin="cli",
                replace_native=replace_native,
                sync_after_import=sync_after_import,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_import_error(error), output_format)
        return 1

    if output_format == "json":
        print(json.dumps(_skill_import_success_envelope(result), sort_keys=True))
    else:
        _stdout_console().print(_format_human_skill_import_success(result))
    return 0


def _run_skills_adopt(  # noqa: PLR0913
    command: AdoptSkillCommandHandler,
    *,
    output_format: str,
    path: Path,
    slug: str | None,
    scope: LatentSkillScope,
    replace_native: bool,
    sync_after_adopt: bool,
) -> int:
    try:
        result = command(
            AdoptSkillCommand(
                path=path,
                scope=scope,
                origin="cli",
                slug=slug,
                replace_native=replace_native,
                sync_after_adopt=sync_after_adopt,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, str(path)), output_format)
        return 1
    envelope = _skill_lifecycle_envelope("skills.adopt", result.agent_skill.scope.value, result)
    if output_format == "json":
        print(json.dumps(envelope, sort_keys=True))
    else:
        _stdout_console().print(
            _format_summary_payload("skills.adopt", result.to_payload(), result.warnings)
        )
    return 0


def _run_skills_canonical_update(  # noqa: PLR0913
    command: UpdateCanonicalSkillCommandHandler,
    *,
    output_format: str,
    skill_id_or_name: str,
    file: Path,
    sync: bool,
    drift_decision: str,
) -> int:
    try:
        result = command(
            UpdateCanonicalSkillCommand(
                skill_id_or_name=skill_id_or_name,
                origin="cli",
                file=file.as_posix(),
                sync=sync,
                drift_decision="overwrite" if drift_decision == "overwrite" else "keep",
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, skill_id_or_name), output_format)
        return 1
    envelope = _skill_lifecycle_envelope(
        "skills.canonical.update", result.agent_skill.scope.value, result
    )
    if output_format == "json":
        print(json.dumps(envelope, sort_keys=True))
    else:
        _stdout_console().print(
            _format_summary_payload("skills.canonical.update", result.to_payload(), result.warnings)
        )
    return 0


def _run_skills_rename(
    command: RenameSkillCommandHandler,
    *,
    output_format: str,
    skill_id_or_name: str,
    slug: str,
) -> int:
    try:
        result = command(
            RenameSkillCommand(skill_id_or_name=skill_id_or_name, slug=slug, origin="cli")
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, skill_id_or_name), output_format)
        return 1
    envelope = _skill_lifecycle_envelope("skills.rename", result.agent_skill.scope.value, result)
    if output_format == "json":
        print(json.dumps(envelope, sort_keys=True))
    else:
        _stdout_console().print(
            _format_summary_payload("skills.rename", result.to_payload(), result.warnings)
        )
    return 0


def _run_skills_cleanup(
    command: CleanupSkillCommandHandler,
    *,
    output_format: str,
    skill_id_or_name: str,
    targets: bool,
    dry_run: bool,
) -> int:
    try:
        result = command(
            CleanupSkillCommand(
                skill_id_or_name=skill_id_or_name,
                origin="cli",
                targets=targets,
                dry_run=dry_run,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, skill_id_or_name), output_format)
        return 1
    envelope = _skill_lifecycle_envelope("skills.cleanup", "project", result)
    if output_format == "json":
        print(json.dumps(envelope, sort_keys=True))
    else:
        _stdout_console().print(
            _format_summary_payload("skills.cleanup", result.to_payload(), result.warnings)
        )
    return 0


def _run_skills_repair(
    command: RepairSkillsCommandHandler,
    *,
    output_format: str,
    remove_orphan_targets: bool,
    dry_run: bool,
) -> int:
    try:
        result = command(
            RepairSkillsCommand(
                origin="cli",
                remove_orphan_targets=remove_orphan_targets,
                dry_run=dry_run,
            )
        )
    except (KeyError, OSError, ValidationError, ValueError, *DOMAIN_ERROR_TYPES) as error:
        _print_expected_error(_map_skill_mutation_error(error, "skills"), output_format)
        return 1
    envelope = _skill_lifecycle_envelope("skills.repair", "project", result)
    if output_format == "json":
        print(json.dumps(envelope, sort_keys=True))
    else:
        _stdout_console().print(
            _format_summary_payload("skills.repair", result.to_payload(), result.warnings)
        )
    return 0


def _skill_lifecycle_envelope(operation: str, scope: str, result: Any) -> dict[str, Any]:
    warnings = list(getattr(result, "warnings", []) or [])
    return {
        "ok": True,
        "operation": operation,
        "scope": scope,
        "data": result.to_payload(),
        "warnings": warnings,
    }


def _format_summary_payload(operation: str, payload: dict[str, Any], warnings: list[str]) -> str:
    lines = [f"Operation: {operation}"]
    for key in (
        "skill_file",
        "draft_path",
        "canonical_path",
        "old_path",
        "new_path",
        "adopted_source",
    ):
        value = payload.get(key)
        if value:
            lines.append(f"{key.replace('_', ' ').title()}: {value}")
    _append_summary_native_targets(lines, payload)
    affected = payload.get("affected_paths") or payload.get("removed_paths") or []
    if affected:
        lines.append("Affected paths:")
        lines.extend(f"  - {path}" for path in affected)
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in warnings)
    validation = payload.get("validation")
    if isinstance(validation, dict):
        lines.append(f"Validation: {validation.get('status', 'unknown')}")
        for issue in validation.get("blocking_issues", [])[:3]:
            lines.append(f"  - {issue}")
    lines.extend(_summary_action_lines(operation, payload, warnings))
    return "\n".join(lines)


def _append_summary_native_targets(lines: list[str], payload: dict[str, Any]) -> None:
    native_installations = payload.get("native_installations")
    if isinstance(native_installations, list):
        target_lines = _summary_target_lines(native_installations)
        if target_lines:
            lines.append("Native targets:")
            lines.extend(target_lines)
        elif not native_installations:
            lines.append("Native targets: not synced by this command")

    sync_skills = payload.get("skills")
    if isinstance(sync_skills, list) and sync_skills:
        target_lines = _summary_sync_target_lines(sync_skills)
        if target_lines:
            lines.append("Native targets:")
            lines.extend(target_lines)


def _summary_target_lines(targets: list[Any]) -> list[str]:
    lines: list[str] = []
    for target in targets[:5]:
        if not isinstance(target, dict):
            continue
        path = target.get("path") or target.get("target_path")
        status = target.get("status", "written")
        if path:
            lines.append(f"  - {path} ({status})")
    return lines


def _summary_sync_target_lines(skills: list[Any]) -> list[str]:
    lines: list[str] = []
    for skill in skills:
        if isinstance(skill, dict):
            lines.extend(_summary_target_lines(skill.get("targets", [])))
    return lines


def _summary_action_lines(
    operation: str, payload: dict[str, Any], warnings: list[str]
) -> list[str]:
    if operation == "skills.cleanup":
        return _cleanup_summary_action_lines(payload)
    if operation == "skills.repair":
        return _repair_summary_action_lines(payload)
    if operation == "skills.sync":
        return _sync_summary_action_lines(payload, warnings)

    next_steps = _generic_skill_next_steps(operation, payload)
    if not next_steps:
        return []
    return ["Next steps:", *[f"  - {step}" for step in next_steps]]


def _generic_skill_next_steps(operation: str, payload: dict[str, Any]) -> list[str]:
    slug = str(payload.get("slug") or payload.get("skill_id") or "<skill>")
    if operation == "skills.validate":
        return _validation_next_steps(payload)
    if operation == "skills.rename":
        new_path = payload.get("new_path")
        renamed = Path(str(new_path)).parent.name if new_path else slug
        return [f"Run `umem skills sync {renamed}` when native targets should move too."]

    static_steps = _static_skill_next_steps(slug, payload)
    return static_steps.get(operation, [])


def _static_skill_next_steps(slug: str, payload: dict[str, Any]) -> dict[str, list[str]]:
    sync_step = f"Run `umem skills sync {slug}` when native runtimes should receive it."
    synced_step = "Review the synced native targets and git status."
    create_steps = [synced_step] if payload.get("native_installations") else [sync_step]
    return {
        "skills.draft.create": [
            f"Edit {payload.get('draft_path', 'the draft')} if needed.",
            f"Run `umem skills draft validate {slug}` before publish.",
        ],
        "skills.create": create_steps,
        "skills.publish": create_steps,
        "skills.adopt": [synced_step]
        if payload.get("native_installations")
        else [
            f"Run `umem skills detail {slug}` to inspect the canonical record.",
            sync_step,
        ],
        "skills.canonical.update": create_steps,
    }


def _validation_next_steps(payload: dict[str, Any]) -> list[str]:
    validation = payload.get("validation")
    status = validation.get("status") if isinstance(validation, dict) else "unknown"
    if status == "pass":
        return ["Skill is ready for publish, canonical update, adopt, or sync."]
    return ["Fix blocking validation issues before publish, update, adopt, or sync."]


def _cleanup_summary_action_lines(payload: dict[str, Any]) -> list[str]:
    plan = payload.get("plan")
    if not isinstance(plan, dict):
        return []
    dry_run = bool(plan.get("dry_run", True))
    removable = [str(path) for path in plan.get("removable_paths", [])]
    blocked = [str(path) for path in plan.get("blocked_paths", [])]
    removed = [str(path) for path in payload.get("removed_paths", [])]

    lines = [f"Mode: {'dry-run preview' if dry_run else 'apply'}"]
    if dry_run and removable:
        lines.append("Removable managed paths:")
        lines.extend(f"  - {path}" for path in removable)
    if removed:
        lines.append("Removed managed paths:")
        lines.extend(f"  - {path}" for path in removed)
    if blocked:
        lines.append("Blocked paths:")
        lines.extend(f"  - {path}" for path in blocked)
    if not removable and not removed and not blocked:
        lines.append("Nothing to clean up.")

    lines.append("Next steps:")
    if dry_run and removable:
        skill = plan.get("skill", "<skill>")
        lines.append(f"  - Re-run `umem skills cleanup {skill} --targets --apply` to delete.")
    elif dry_run:
        lines.append("  - No apply step is needed.")
    elif blocked:
        lines.append("  - Review blocked paths manually; UMEM only deletes managed targets.")
    else:
        lines.append("  - Review git status after the applied cleanup.")
    return lines


def _repair_summary_action_lines(payload: dict[str, Any]) -> list[str]:
    plans = payload.get("plans")
    if not isinstance(plans, list):
        return []
    dry_run = any(isinstance(plan, dict) and plan.get("dry_run", True) for plan in plans)
    removable: list[str] = []
    blocked: list[str] = []
    for plan in plans:
        if not isinstance(plan, dict):
            continue
        removable.extend(str(path) for path in plan.get("removable_paths", []))
        blocked.extend(str(path) for path in plan.get("blocked_paths", []))
    removed = [str(path) for path in payload.get("removed_paths", [])]

    lines = [f"Mode: {'dry-run preview' if dry_run else 'apply'}"]
    if removable:
        lines.append("Removable orphan targets:")
        lines.extend(f"  - {path}" for path in removable)
    if removed:
        lines.append("Removed orphan targets:")
        lines.extend(f"  - {path}" for path in removed)
    if blocked:
        lines.append("Blocked paths:")
        lines.extend(f"  - {path}" for path in blocked)
    if not plans:
        lines.append("No repair action selected.")
    elif not removable and not removed and not blocked:
        lines.append("Nothing to repair.")

    lines.append("Next steps:")
    if dry_run and removable:
        lines.append("  - Re-run `umem skills repair --remove-orphan-targets --apply` to delete.")
    elif dry_run:
        lines.append("  - No apply step is needed.")
    elif blocked:
        lines.append("  - Review blocked paths manually; UMEM only deletes managed targets.")
    else:
        lines.append("  - Review git status after the applied repair.")
    return lines


def _sync_summary_action_lines(payload: dict[str, Any], warnings: list[str]) -> list[str]:
    lines: list[str] = []
    affected = [str(path) for path in payload.get("affected_paths", [])]
    removed = [str(path) for path in payload.get("removed_paths", [])]
    if removed:
        lines.append("Removed managed paths:")
        lines.extend(f"  - {path}" for path in removed)
    if _has_gitignore_warning(warnings):
        lines.extend(
            [
                "Gitignore check: ran after target planning/writes.",
                "Gitignore check: diagnostic only; .gitignore was not edited.",
            ]
        )
    if not affected and not removed:
        lines.append("No native target changes were needed.")

    next_steps = ["Review git status and ignore rules intentionally."]
    if _has_gitignore_warning(warnings):
        next_steps.append("Update .gitignore or untrack generated targets if that is policy.")
    lines.append("Next steps:")
    lines.extend(f"  - {step}" for step in next_steps)
    return lines


def _has_gitignore_warning(warnings: list[str]) -> bool:
    return any(
        "not ignored by git" in warning or "tracked by git" in warning for warning in warnings
    )


def _skill_track_success_envelope(result: TrackLatentSkillResult) -> dict[str, Any]:
    skill = result.latent_skill
    return {
        "ok": True,
        "operation": "skills.track",
        "scope": skill.scope.value,
        "data": {
            "latent_skill": {
                "id": skill.id,
                "name": skill.name,
                "description": skill.description,
                "scope": skill.scope.value,
                "status": skill.status.value,
                "recurrence_count": skill.recurrence_count,
                "metadata": skill.metadata,
                "created_at": format_utc_iso(skill.created_at),
                "updated_at": format_utc_iso(skill.updated_at),
            },
            "matched_existing": result.matched_existing,
            "audit_reference": result.audit_reference,
            "snapshot_reference": result.snapshot_reference,
        },
        "warnings": [],
    }


def _format_human_skill_track(result: TrackLatentSkillResult) -> str:
    skill = result.latent_skill
    affected_paths = [_latent_skill_store_path(skill.scope)]
    lines = [
        "Operation: skills.track",
        f"Scope: {skill.scope.value}",
        f"Latent skill: {skill.id}",
        f"Name: {skill.name}",
        f"Status: {skill.status.value}",
        f"Recurrence count: {skill.recurrence_count}",
        f"Matched existing: {'Yes' if result.matched_existing else 'No'}",
        "Affected relative paths:",
    ]
    lines.extend(f"  - {path}" for path in affected_paths)
    lines.extend(
        [
            f"Snapshot: {result.snapshot_reference}",
            f"Audit: {result.audit_reference}",
        ]
    )
    return "\n".join(lines)


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
                "The --yes / -y flag is required to run skills generate with JSON output."
            )
        if output_format != "json":
            if not yes and (not sys.stdin.isatty() or not sys.stdout.isatty()):
                raise ValidationFailedError(
                    "Non-TTY environment requires --yes to generate a skill."
                )

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
                elif not _confirm("Generate skill structure? [y/N]: ", default=False):
                    _stdout_console().print("Skill generation cancelled.")
                    return 1

        result = command(
            GenerateSkillCommand(
                latent_skill_id=latent_skill_id,
                origin="cli",
                update_existing=update_existing,
                dry_run=False,
            )
        )
        if output_format != "json" and not yes and _has_native_drift_warning(result):
            choice = _prompt_native_drift_decision()
            if choice == "overwrite":
                result = command(
                    GenerateSkillCommand(
                        latent_skill_id=latent_skill_id,
                        origin="cli",
                        update_existing=True,
                        dry_run=False,
                        native_drift_decision="overwrite",
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


def _has_native_drift_warning(result: GenerateSkillResult | UpdateSkillResult) -> bool:
    return any(
        "Warning: Native target has manual changes." in warning for warning in result.warnings
    )


def _prompt_native_drift_decision() -> str:
    prompt_msg = (
        "Warning: Native target has manual changes. Overwriting it might break your "
        "current agent workflow. Keep local version or Overwrite with canonical library "
        "version? [Keep/Overwrite] "
    )
    choice = ""
    while choice not in {"keep", "overwrite"}:
        choice = input(prompt_msg).strip().lower()
        if not choice:
            choice = "keep"
    return choice


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
    yes: bool,
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
                native_drift_decision=_default_native_drift_decision(output_format),
            )
        )
        if _should_prompt_native_drift(result, output_format=output_format, yes=yes):
            choice = _prompt_native_drift_decision()
            if choice == "overwrite":
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
                        native_drift_decision="overwrite",
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
        raise ValidationFailedError(f"Markdown file not found: {path.as_posix()}")
    try:
        return path.read_text(encoding="utf-8")
    except OSError as error:
        raise StorageError(str(error)) from error


def _default_native_drift_decision(output_format: str) -> NativeDriftDecision | None:
    if output_format == "json" or not (sys.stdin.isatty() and sys.stdout.isatty()):
        return "keep"
    return None


def _should_prompt_native_drift(
    result: UpdateSkillResult,
    *,
    output_format: str,
    yes: bool,
) -> bool:
    return (
        output_format != "json"
        and not yes
        and sys.stdin.isatty()
        and sys.stdout.isatty()
        and _has_native_drift_warning(result)
    )


def _sync_active_skills_for_update(  # noqa: PLR0913
    list_command: ListSkillsCommandHandler,
    sync_command: SyncSkillsCommandHandler,
    update_command: UpdateSkillCommandHandler,
    update_managed_command: UpdateManagedSkillsCommandHandler | None,
    *,
    output_format: str,
    yes: bool,
) -> UpdateSkillsRunResult:
    list_result = list_command(ListSkillsCommand(status=LatentSkillStatus.active))
    managed_results = (
        update_managed_command(UpdateManagedSkillsCommand(project_root=Path.cwd()))
        if update_managed_command is not None
        else []
    )
    canonical_skill_ids = _active_canonical_project_skill_ids(list_result)
    legacy_skill_ids = _active_project_skill_ids(Path.cwd(), exclude_ids=set(canonical_skill_ids))
    results: list[UpdateSkillsItem] = [*managed_results]
    drift_decision = _default_native_drift_decision(output_format)
    for skill_id in canonical_skill_ids:
        sync_result = sync_command(
            SyncSkillsCommand(
                skill_id_or_name=skill_id,
                origin="cli_update_skills",
                drift_decision=drift_decision or "keep",
            )
        )
        results.extend(sync_result.skills)
    for skill_id in legacy_skill_ids:
        result = update_command(
            UpdateSkillCommand(
                latent_skill_id=skill_id,
                origin="cli_update_skills",
                native_drift_decision=drift_decision,
            )
        )
        if _should_prompt_native_drift(result, output_format=output_format, yes=yes):
            choice = _prompt_native_drift_decision()
            if choice == "overwrite":
                result = update_command(
                    UpdateSkillCommand(
                        latent_skill_id=skill_id,
                        origin="cli_update_skills",
                        native_drift_decision="overwrite",
                    )
                )
        results.append(result)
    return UpdateSkillsRunResult(
        skills=results,
        updated_count=sum(1 for result in results if _update_skills_item_updated(result)),
        preserved_count=sum(1 for result in results if not _update_skills_item_updated(result)),
        warnings=[warning for result in results for warning in result.warnings],
    )


def _update_skills_item_updated(result: UpdateSkillsItem) -> bool:
    updated_paths = getattr(result, "updated_paths", None)
    if isinstance(updated_paths, list):
        return bool(updated_paths)
    affected_paths = getattr(result, "affected_paths", None)
    if isinstance(affected_paths, list):
        return bool(affected_paths)
    return True


def _active_canonical_project_skill_ids(result: ListSkillsResult) -> list[str]:
    skill_ids: list[str] = []
    for skill in result.skills:
        if skill.scope != LatentSkillScope.project.value:
            continue
        if skill.status != "active" or skill.id is None:
            continue
        if skill.id == DEFAULT_UMEM_SKILL_ID:
            continue
        if skill.canonical_path is None:
            continue
        skill_ids.append(skill.id)
    return skill_ids


def _active_project_skill_ids(
    project_root: Path, *, exclude_ids: set[str] | None = None
) -> list[str]:
    path = project_root / ".umem" / "memory" / "latent_skills.jsonl"
    if not path.is_file():
        return []
    exclude_ids = exclude_ids or set()
    skill_ids: list[str] = []
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError as error:
        raise StorageError(str(error)) from error
    for line in lines:
        if not line.strip():
            continue
        try:
            payload = json.loads(line)
        except json.JSONDecodeError as error:
            raise ValidationFailedError(
                f"Invalid latent skills store: {path.as_posix()}"
            ) from error
        if payload.get("id") == DEFAULT_UMEM_SKILL_ID:
            continue
        if payload.get("id") in exclude_ids:
            continue
        if payload.get("status") == LatentSkillStatus.active.value and isinstance(
            payload.get("id"), str
        ):
            skill_ids.append(payload["id"])
    return skill_ids


def _map_skill_mutation_error(error: Exception, latent_skill_id: str) -> Exception:
    if isinstance(error, KeyError):
        return ValidationFailedError(
            f"Latent skill '{latent_skill_id}' not found in the repository. "
            "If this is an imported canonical Agent Skill from `skills list` or "
            "`skills detail`, edit `.umem/skills/<slug>/SKILL.md` and run "
            "`umem skills sync <slug> --format json` instead of `skills update`."
        )
    if isinstance(error, StorageError) and str(error) == (
        f"Latent skill not found: {latent_skill_id}"
    ):
        return ValidationFailedError(
            f"Latent skill '{latent_skill_id}' not found in the repository. "
            "If this is an imported canonical Agent Skill from `skills list` or "
            "`skills detail`, edit `.umem/skills/<slug>/SKILL.md` and run "
            "`umem skills sync <slug> --format json` instead of `skills update`."
        )
    if isinstance(error, (ValidationError, ValueError)):
        return ValidationFailedError(str(error))
    if isinstance(error, OSError) and not isinstance(error, DOMAIN_ERROR_TYPES):
        return StorageError(str(error))
    return error


def _map_generate_error(error: Exception, latent_skill_id: str) -> Exception:
    if isinstance(error, KeyError):
        return ValidationFailedError(
            f"Latent skill '{latent_skill_id}' not found in the repository."
        )
    if isinstance(error, (ValidationError, ValueError)):
        return ValidationFailedError(str(error))
    if isinstance(error, OSError) and not isinstance(error, DOMAIN_ERROR_TYPES):
        return StorageError(str(error))
    return error


def _map_import_error(error: Exception) -> Exception:
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


def _skill_create_success_envelope(result: CreateSkillResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.create",
        "scope": result.latent_skill.scope.value,
        "data": result.to_payload(),
        "warnings": result.warnings,
    }


def _skill_promote_success_envelope(
    result: PromoteSkillRecommendationResult,
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.promote",
        "scope": result.promoted_recommendation.scope.value,
        "data": result.to_payload(),
        "warnings": result.warnings,
    }


def _skill_import_success_envelope(result: ImportSkillResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.import",
        "scope": result.latent_skill.scope.value,
        "data": result.to_payload(),
        "warnings": result.warnings,
    }


def _skill_sync_success_envelope(result: SyncSkillsResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.sync",
        "scope": "all",
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


def _skill_recommend_success_envelope(
    result: RecommendSkillsResult,
    *,
    scope: LatentSkillScope | None,
) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "skills.recommend",
        "scope": scope.value if scope is not None else "all",
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
        "warnings": result.warnings,
    }


def _update_skills_success_envelope(result: UpdateSkillsRunResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "update.skills",
        "scope": "project",
        "data": {
            "updated_count": result.updated_count,
            "preserved_count": result.preserved_count,
            "skills": [_update_skills_item_payload(item) for item in result.skills],
        },
        "warnings": result.warnings,
    }


def _update_skills_item_payload(result: UpdateSkillsItem) -> dict[str, Any]:
    if isinstance(result, UpdateManagedSkillTemplateResult):
        return {"managed": True, **result.to_payload()}
    if isinstance(result, SyncSkillResult):
        return {"managed": False, **result.to_payload()}
    return {"managed": False, **_skill_mutation_payload(result)}


def _status_success_envelope(result: GetMemoryStatusResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "status",
        "scope": "project",
        "data": _status_payload(result),
        "warnings": [],
    }


def _doctor_success_envelope(result: DoctorResult) -> dict[str, Any]:
    return {
        "ok": result.ok,
        "operation": "doctor",
        "scope": "environment",
        "data": result.to_payload(),
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


def _update_check_success_envelope(result: UpdateCheckResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "update.check",
        "scope": "project",
        "data": result.to_payload(),
        "warnings": result.warnings,
    }


def _update_migrate_success_envelope(result: UpdateMigrateResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "update.migrate",
        "scope": "project",
        "data": result.to_payload(),
        "warnings": result.warnings,
    }


def _update_benchmarks_success_envelope(result: UpdateBenchmarksResult) -> dict[str, Any]:
    return {
        "ok": True,
        "operation": "update.benchmarks",
        "scope": "project",
        "data": result.to_payload(),
        "warnings": result.warnings,
    }


def _update_apply_success_envelope(
    check_result: UpdateCheckResult,
    migrate_result: UpdateMigrateResult | None,
) -> dict[str, Any]:
    warnings = [*check_result.warnings]
    if migrate_result is not None:
        warnings.extend(migrate_result.warnings)
    return {
        "ok": True,
        "operation": "update",
        "scope": "project",
        "data": {
            "check": check_result.to_payload(),
            "migration_applied": migrate_result is not None,
            "migrated_files": migrate_result.migrated_files if migrate_result is not None else [],
            "audit_reference": migrate_result.audit_reference if migrate_result is not None else "",
            "snapshot_references": (
                migrate_result.snapshot_references if migrate_result is not None else []
            ),
        },
        "warnings": warnings,
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
            "installed_version": result.installed_version,
            "recommended_action": result.recommended_action,
        }

    return {
        "initialized": True,
        "project_path": result.project_path,
        "installed_version": result.installed_version,
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
                "Local memory is not initialized.",
                f"Project: {result.project_path}",
                f"Installed version: {result.installed_version}",
                f"Next action: {result.recommended_action}",
            ]
        )

    lines = [
        "Local memory initialized.",
        f"Project: {result.project_path}",
        f"Installed version: {result.installed_version}",
        f"Approximate size: {result.approximate_size_bytes} bytes",
        f"Last health check: {result.last_health_check}",
        f"Active rules: {result.active_rules_count}",
        f"Registered canonical skills: {result.registered_skills_count}",
        "Hosts:",
    ]
    for host, validation in result.host_validation.items():
        status = validation.get("status", "unconfigured")
        method = validation.get("method")
        audit_reference = validation.get("audit_reference")
        suffix_parts = []
        if method:
            suffix_parts.append(f"method={method}")
        if audit_reference:
            suffix_parts.append(f"audit={audit_reference}")
        suffix = f" ({', '.join(suffix_parts)})" if suffix_parts else ""
        lines.append(f"- {host}: {status}{suffix}")
    lines.append("Facts by scope/status:")
    for scope, counts in result.fact_counts.items():
        rendered_counts = ", ".join(f"{status}: {count}" for status, count in counts.items())
        lines.append(f"- {scope} {rendered_counts}")
    return "\n".join(lines)


def _format_human_doctor_output(result: DoctorResult) -> str:
    lines = [
        "universal-memory Doctor - Health Report",
        "========================================",
        "",
    ]
    for check in result.checks:
        marker = "[OK]" if check.status == "success" else "[FAIL]"
        label = " ".join(check.name.split("_")).title()
        detail = f" - {check.detail}" if check.detail else ""
        lines.append(f"{marker} {label}{detail}")
        if check.error:
            lines.append(f"    Error: {check.error}")
        if check.recovery_hint:
            lines.append(f"    Recovery: {check.recovery_hint}")

    summary = result.summary
    lines.extend(
        [
            "",
            (
                "Final status: all checks passed."
                if result.ok
                else f"Final status: {summary.failed} failure(s) found."
            ),
        ]
    )
    return "\n".join(lines)


def _format_human_context_output(result: AssembleContextSummaryResult) -> str:
    summary = result.context_summary
    lines = [
        "Context assembled.",
        f"Project summary: {summary.project_summary or '(empty)'}",
        f"Universal preferences: {summary.universal_preferences or '(empty)'}",
        f"Active rules: {summary.active_rules or '(empty)'}",
        f"Sources: {', '.join(result.included_fact_ids) if result.included_fact_ids else '(none)'}",
    ]
    return "\n".join(lines)


def _format_human_update_check(result: UpdateCheckResult) -> str:
    memory = ", ".join(
        f"{name}: {versions or ['legacy']}"
        for name, versions in sorted(result.memory_schema_versions.items())
    )
    lines = [
        "Local maintenance check completed.",
        "Scope: project",
        f"Running package version: {result.installed_version}",
        f"Target schema: {result.target_schema_version}",
        f"Config schema: {result.project_config_schema_version or 'legacy'}",
        f"Memory schemas: {memory or '(no files found)'}",
        f"Benchmarks: {result.benchmarks_status}",
        "Package upgrade check: not performed (offline command)",
        f"Migration required: {str(result.migration_required).lower()}",
    ]
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)
    if result.migration_required:
        lines.append("Next action: umem update --yes")
    else:
        lines.append("Next action: no local maintenance action required.")
    return "\n".join(lines)


def _format_human_update_apply(
    check_result: UpdateCheckResult,
    migrate_result: UpdateMigrateResult | None,
) -> str:
    lines = [
        "Local maintenance completed.",
        "Scope: project",
        f"Running package version: {check_result.installed_version}",
        f"Target schema: {check_result.target_schema_version}",
        "Package upgrade check: not performed (offline command)",
        f"Migration required: {str(check_result.migration_required).lower()}",
        f"Migration applied: {str(migrate_result is not None).lower()}",
    ]
    if migrate_result is not None:
        lines.append("Migrated files:")
        lines.extend(f"- {path}" for path in migrate_result.migrated_files)
        snapshots = (
            ", ".join(migrate_result.snapshot_references)
            if migrate_result.snapshot_references
            else "(none)"
        )
        lines.extend(
            [
                f"Snapshots: {snapshots}",
                f"Audit: {migrate_result.audit_reference or '(no changes)'}",
            ]
        )
    else:
        lines.append("No local maintenance actions were required.")
    warnings = [*check_result.warnings]
    if migrate_result is not None:
        warnings.extend(migrate_result.warnings)
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in warnings)
    return "\n".join(lines)


def _format_human_update_mutation_plan(operation: str) -> str:
    return "\n".join(
        [
            f"Operation: {operation}",
            "Scope: project",
            "Snapshot: created by the safe pipeline before each write.",
            "Audit: safe mutation event expected.",
            "Default: do not confirm.",
        ]
    )


def _format_human_update_migrate(result: UpdateMigrateResult) -> str:
    lines = [
        "Migration completed.",
        "Scope: project",
        f"Target schema: {result.target_schema_version}",
        "Migrated files:",
    ]
    lines.extend(f"- {path}" for path in result.migrated_files)
    snapshots = ", ".join(result.snapshot_references) if result.snapshot_references else "(none)"
    lines.extend(
        [
            f"Snapshots: {snapshots}",
            f"Audit: {result.audit_reference or '(no changes)'}",
        ]
    )
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _format_human_update_benchmarks(result: UpdateBenchmarksResult) -> str:
    lines = [
        "Benchmarks updated.",
        "Scope: project",
        f"File: {result.retrieval_results_path}",
        f"Synthetic facts: {result.fact_count}",
        f"Queries: {result.query_count}",
        f"Default strategy: {result.selected_default_strategy}",
        f"p95 latency ms: {result.p95_latency_ms}",
        f"Snapshot: {result.snapshot_reference}",
        f"Audit: {result.audit_reference}",
    ]
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"- {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _format_human_remember_output(result: RememberFactResult) -> str:
    fact = result.fact
    return "\n".join(
        [
            "Fact saved.",
            f"ID: {fact.id}",
            f"Scope: {fact.scope.value}",
            f"Status: {fact.status.value}",
            f"Tags: {', '.join(fact.tags) if fact.tags else '(none)'}",
            f"Audit: {result.audit_reference}",
        ]
    )


def _format_human_facts_list_output(result: ListFactsResult) -> Table | str:
    if not result.facts:
        return "No facts found."

    table = Table(title="Facts:", show_header=True)
    table.add_column("ID")
    table.add_column("Scope")
    table.add_column("Status")
    table.add_column("Source")
    table.add_column("Content")
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
    target = f"ID: {id}" if id is not None else f"Scope: {scope.value if scope else 'n/a'}"
    return "\n".join(
        [
            "Permanent purge selected:",
            target,
            "Affected path: .umem/memory/facts.jsonl",
            "Snapshot: created by the safe pipeline when configured",
            "Audit: safe mutation event expected",
            "Default: do not confirm.",
        ]
    )


def _format_human_purge_success(result: PurgeFactResult) -> str:
    return "\n".join(
        [
            "Purge completed.",
            f"Purged items: {result.purged_count}",
            f"Affected IDs: {', '.join(result.affected_ids)}",
            f"Audit: {result.audit_reference}",
        ]
    )


def _format_human_hygiene_success(result: ContextHygieneResult) -> str:
    return "\n".join(
        [
            "Context hygiene completed.",
            f"Facts marked stale: {result.stale_count}",
            f"Facts archived: {result.archived_count}",
            f"Audit: {result.audit_reference}",
        ]
    )


def _format_human_audit_output(result: ListAuditLogResult) -> Table | str:
    if not result.events:
        return "No audit events found."

    table = Table(title="Audit events:", show_header=True)
    table.add_column("Timestamp")
    table.add_column("Scope")
    table.add_column("Origin")
    table.add_column("Action")
    table.add_column("Result")
    table.add_column("Audit")
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
        return "No snapshots found."

    table = Table(title="Snapshots:", show_header=True)
    table.add_column("Timestamp")
    table.add_column("Scope")
    table.add_column("Origin")
    table.add_column("Action")
    table.add_column("File")
    table.add_column("Hash")
    table.add_column("Manifest")
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
            "Rollback selected:",
            f"Scope: {snapshot.scope.value}",
            f"Snapshot: {snapshot.id}",
            f"Timestamp: {snapshot.timestamp.isoformat()}",
            f"Original action: {snapshot.action}",
            f"File: {snapshot.relative_path}",
        ]
    )


def _format_human_rollback_success(result: RollbackResult) -> str:
    return "\n".join(
        [
            "Rollback completed.",
            f"Scope: {result.scope.value}",
            f"Snapshot: {result.snapshot_reference}",
            f"Restored files: {', '.join(result.restored_paths)}",
            f"Audit: {result.audit_reference}",
        ]
    )


def _format_human_skill_proposal(result: ProposeSkillResult) -> str:
    scope = result.proposal["scope"]
    is_global = scope == "global"

    skill_path = "memory/latent_skills.jsonl" if is_global else ".umem/memory/latent_skills.jsonl"
    config_path = "~/.config/umem/config.toml" if is_global else ".umem/config.toml"

    lines = [
        "Operation: skills.propose",
        f"Scope: {scope}",
        f"Suggested name: {result.proposal['suggested_name']}",
        f"Purpose: {result.proposal['purpose']}",
        "Evidence:",
    ]
    evidence = result.proposal.get("evidence", [])
    lines.extend(f"  - {item}" for item in evidence)

    lines.extend(
        [
            "",
            "Affected relative paths:",
            f"  - Decision yes: {skill_path}",
            f"  - Decision always: {skill_path} AND {config_path}",
            f"  - Decision no: {skill_path}",
            "",
            "Snapshot: a safety snapshot will be created before any write.",
            "Expected audit event: propose_skill_decision or "
            "update_skill_auto_approval (for always).",
            "Options: yes, always, no",
        ]
    )

    if result.audit_reference:
        lines.append(f"Audit: {result.audit_reference}")
    if result.snapshot_reference:
        lines.append(f"Snapshot: {result.snapshot_reference}")
    return "\n".join(lines)


def _format_human_skill_list(result: ListSkillsResult) -> Table | str:
    if not result.skills:
        lines = ["No skills registered."]
        if result.recommended_action:
            lines.append(result.recommended_action)
        return "\n".join(lines)

    table = Table(title="Registered skills")
    table.add_column("Name")
    table.add_column("Scope")
    table.add_column("Status")
    table.add_column("Relative path")
    table.add_column("Origin")
    table.add_column("Created at")
    table.add_column("Updated at")
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


def _format_human_skill_recommend(result: RecommendSkillsResult) -> str:
    threshold = result.thresholds["min_recurrence"]
    lines = [
        "Operation: skills.recommend",
        f"Minimum recurrence: {threshold}",
        "Evidence sources:",
    ]
    lines.extend(
        f"  - {source['source']}: {source['description']}" for source in result.evidence_sources
    )
    lines.append("Limitations:")
    lines.extend(f"  - {limitation}" for limitation in result.limitations)
    if not result.recommendations:
        lines.append("No actionable latent skill recommendations found.")
        return "\n".join(lines)

    lines.append("Recommendations:")
    for item in result.recommendations:
        lines.extend(
            [
                f"  - {item.name} ({item.id})",
                f"    Scope: {item.scope}",
                f"    Recurrence: {item.recurrence_count}",
                f"    Confidence: {item.confidence}",
                f"    Next action: {item.recommended_action}",
            ]
        )
    return "\n".join(lines)


def _format_human_skill_detail(result: GetSkillDetailResult) -> str:
    lines = [
        "Operation: skills.detail",
        f"Name: {result.name}",
        f"Scope: {result.scope}",
        f"Status: {result.status}",
        f"Relative path: {result.relative_path or '-'}",
        "Triggers:",
    ]
    lines.extend(f"  - {trigger}" for trigger in result.triggers)
    lines.extend(
        [
            f"Audit: {result.audit_reference}",
            f"References loaded: {str(result.references_loaded).lower()}",
        ]
    )
    return "\n".join(lines)


def _format_human_skill_generate_plan(result: GenerateSkillResult) -> str:
    lines = [
        "Operation: skills.generate",
        f"Scope: {result.latent_skill.scope.value}",
        f"Latent skill: {result.latent_skill.id}",
        "Affected relative paths:",
        f"  - {result.skill_file}",
    ]
    metadata = result.latent_skill.metadata or {}
    if bool(metadata.get("include_scripts") or metadata.get("scripts")):
        lines.append(f"  - {result.skill_dir}/scripts/.gitkeep")
    if bool(metadata.get("include_references") or metadata.get("references")):
        lines.append(f"  - {result.skill_dir}/references/.gitkeep")
    lines.extend(
        [
            "Snapshot: created by the safe pipeline before each write.",
            "Audit: generate_skill event expected.",
            "Default: do not confirm.",
        ]
    )
    return "\n".join(lines)


def _format_human_skill_generate_success(result: GenerateSkillResult) -> str:
    lines = [
        "Operation: skills.generate",
        f"Scope: {result.latent_skill.scope.value}",
        f"Name: {result.latent_skill.name}",
        f"Slug: {result.slug}",
        "Affected relative paths:",
    ]
    lines.extend(f"  - {path}" for path in result.affected_paths)
    lines.extend(
        [
            f"Snapshot: {result.snapshot_reference}",
            f"Audit: {result.audit_reference}",
        ]
    )
    if result.collision_detected and result.suggested_slug and result.suggested_slug != result.slug:
        lines.append(f"Collision: alternate slug used ({result.suggested_slug}).")
    return "\n".join(lines)


def _format_human_skill_create_success(result: CreateSkillResult) -> str:
    lines = [
        "Operation: skills.create",
        f"Scope: {result.latent_skill.scope.value}",
        f"Name: {result.latent_skill.name}",
        f"Slug: {result.slug}",
        "Affected relative paths:",
    ]
    lines.extend(f"  - {path}" for path in result.affected_paths)
    lines.extend(
        [
            f"Canonical path: {result.skill_file}",
            f"Snapshot: {result.snapshot_reference}",
            f"Audit: {result.audit_reference}",
            "Next action: run `umem skills sync "
            f"{result.slug} --format json` to materialize the canonical skill into "
            "configured native runtimes when needed.",
        ]
    )
    return "\n".join(lines)


def _format_human_skill_sync_success(result: SyncSkillsResult) -> str:
    removed_paths = set(result.removed_paths)
    affected_paths = [path for path in result.affected_paths if path not in removed_paths]
    lines = [
        "Operation: skills.sync",
        f"Skills synced: {len(result.skills)}",
        "Affected relative paths:",
    ]
    lines.extend(f"  - {path}" for path in affected_paths)
    if result.removed_paths:
        lines.append("Removed managed paths:")
        lines.extend(f"  - {path}" for path in result.removed_paths)
    target_lines = _skill_sync_target_lines(result)
    if target_lines:
        lines.append("Native runtime targets:")
        lines.extend(target_lines)
        lines.append(
            "Worktree note: skills sync may create or update runtime directories. "
            "Review git status and ignore rules intentionally."
        )
    lines.extend(
        [
            f"Snapshot: {result.snapshot_reference}",
            f"Audit: {result.audit_reference}",
        ]
    )
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in result.warnings)
    return "\n".join(lines)


def _skill_sync_target_lines(result: SyncSkillsResult) -> list[str]:
    lines: list[str] = []
    for skill in result.skills:
        for target in skill.targets:
            runtime = target.get("runtime", "unknown")
            path = target.get("path", "unknown")
            status = target.get("status", "unknown")
            lines.append(f"  - {runtime}: {path} ({status})")
    return lines


def _format_human_skill_promote_success(result: PromoteSkillRecommendationResult) -> str:
    create_result = result.create_result
    lines = [
        "Operation: skills.promote",
        f"Scope: {result.promoted_recommendation.scope.value}",
        f"Source recommendation: {result.source_recommendation.id}",
        f"Canonical skill: {create_result.agent_skill.id}",
        f"Name: {create_result.agent_skill.name}",
        f"Slug: {create_result.slug}",
        f"Canonical path: {create_result.skill_file}",
        "Affected relative paths:",
    ]
    lines.extend(f"  - {path}" for path in create_result.affected_paths)
    lines.append(f"  - {_latent_skill_store_path(result.promoted_recommendation.scope)}")
    lines.extend(
        [
            f"Snapshot: {result.snapshot_reference}",
            f"Audit: {result.audit_reference}",
        ]
    )
    return "\n".join(lines)


def _format_human_skill_import_success(result: ImportSkillResult) -> str:
    lines = [
        "Operation: skills.import",
        f"Scope: {result.latent_skill.scope.value}",
        f"Name: {result.latent_skill.name}",
        f"Slug: {result.slug}",
        "Affected relative paths:",
    ]
    lines.extend(f"  - {path}" for path in result.affected_paths)
    lines.extend(
        [
            f"Canonical path: {result.skill_file}",
            f"Snapshot: {result.snapshot_reference}",
            f"Audit: {result.audit_reference}",
            "Import note: `.umem/skills/<slug>/SKILL.md` is now the canonical source. "
            "The `--replace-native` flag only rewrites a matching managed native source; "
            "use `--sync` to materialize configured runtime copies during import.",
        ]
    )
    if result.native_installations:
        lines.append("Native runtime targets:")
        lines.extend(
            f"  - {installation.get('path')} ({installation.get('status', 'synced')})"
            for installation in result.native_installations
        )
    else:
        lines.extend(
            [
                "Next action: run `umem skills sync "
                f"{result.slug} --format json` or re-run import with `--sync` to "
                "materialize the canonical skill into configured native runtimes when needed.",
            ]
        )
    if not result.native_installations:
        lines.append(f"Native target note: {NO_NATIVE_INSTALLATIONS_NOTE}")
    if result.warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in result.warnings)
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
        f"Operation: {operation}",
        f"Scope: {skill.scope.value}",
        f"Latent skill: {skill.id}",
        f"Name: {skill.name}",
        f"Status: {skill.status.value}",
        "Affected relative paths:",
    ]
    lines.extend(f"  - {path}" for path in affected_paths)
    lines.extend(
        [
            f"Snapshot: {result.snapshot_reference}",
            f"Audit: {result.audit_reference}",
        ]
    )
    rollback_hint = getattr(result, "rollback_hint", None)
    if rollback_hint:
        lines.append(f"Rollback: {rollback_hint}")
    warnings = getattr(result, "warnings", [])
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in warnings)
    return "\n".join(lines)


def _format_human_update_skills(result: UpdateSkillsRunResult) -> str:
    lines = ["Operation: update.skills", f"Updated skills: {result.updated_count}"]
    if result.preserved_count:
        lines.append(f"Preserved skills: {result.preserved_count}")
    for item in result.skills:
        if isinstance(item, UpdateManagedSkillTemplateResult):
            lines.append(f"Managed skill: {item.name} ({item.status})")
            if item.updated_paths:
                lines.append("Updated paths:")
                lines.extend(f"  - {path}" for path in item.updated_paths)
            if item.preserved_paths:
                lines.append("Preserved paths:")
                lines.extend(f"  - {path}" for path in item.preserved_paths)
        elif isinstance(item, SyncSkillResult):
            lines.append(f"Canonical skill: {item.name} ({item.status})")
            removed_paths = set(item.removed_paths)
            synced_paths = [path for path in item.affected_paths if path not in removed_paths]
            if synced_paths:
                lines.append("Synced paths:")
                lines.extend(f"  - {path}" for path in synced_paths)
            if item.removed_paths:
                lines.append("Removed managed paths:")
                lines.extend(f"  - {path}" for path in item.removed_paths)
    warnings = result.warnings
    if warnings:
        lines.append("Warnings:")
        lines.extend(f"  - {warning}" for warning in warnings)
    return "\n".join(lines)


def _latent_skill_store_path(scope: Any) -> str:
    if scope == LatentSkillScope.global_:
        return "memory/latent_skills.jsonl"
    return ".umem/memory/latent_skills.jsonl"


def _format_human_host_plan(result: ConfigureHostResult, *, operation: str) -> Table | str:
    if not result.planned_changes:
        return f"No changes planned for host {result.host_id}."

    table = Table(title=f"Host {operation} plan for {result.host_id}", show_header=True)
    table.add_column("Target")
    table.add_column("Action")
    table.add_column("Path")
    table.add_column("Snapshot")
    table.add_column("Audit")
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
            "[bold]Host check completed.[/bold]",
            f"Host: {result.host_id}",
            f"Targets: {', '.join(result.instruction_targets)}",
            f"Validation: [{style}]{result.validation_status}[/{style}]",
            f"Audit: {result.audit_reference}",
        ]
        if result.warnings:
            if result.validation_status == "failure":
                lines.append("Validation errors:")
            else:
                lines.append("Warnings:")
            lines.extend(f"- {warning}" for warning in result.warnings)
        return Panel.fit("\n".join(lines), border_style=style)

    changes = ", ".join(change["path"] for change in result.planned_changes) or "(none)"
    return "\n".join(
        [
            f"Host {operation} completed.",
            f"Host: {result.host_id}",
            f"Targets: {', '.join(result.instruction_targets)}",
            f"Files: {changes}",
            f"Validation: {result.validation_status}",
            f"Audit: {result.audit_reference}",
        ]
    )


def _format_human_sync_success(result: SyncInstructionsResult) -> str:
    changes = ", ".join(change["path"] for change in result.planned_changes) or "(none)"
    if result.validation_status == "success" and result.planned_changes:
        msg = "Host sync applied instruction updates."
    elif result.validation_status == "success":
        msg = "Host sync completed. No instruction files needed changes."
    else:
        msg = "Dry-run completed. No changes were applied to the filesystem."
    audit = result.audit_reference
    if result.audit_reference == "not-applied":
        audit = "not-applied (no filesystem write was needed)"
    return "\n".join(
        [
            msg,
            f"Hosts: {', '.join(result.host_ids)}",
            f"Targets: {', '.join(result.instruction_targets)}",
            f"Files: {changes}",
            f"Validation: {result.validation_status}",
            f"Audit: {audit}",
            f"Snapshots: {result.snapshot_reference}",
        ]
    )


def _format_human_sync_plan(result: SyncInstructionsResult) -> Table | str:
    if not result.planned_changes:
        return "No changes planned for instruction synchronization."

    table = Table(title="Instruction synchronization plan", show_header=True)
    table.add_column("Target")
    table.add_column("Action")
    table.add_column("Path")
    table.add_column("Scope")
    table.add_column("Snapshot")
    table.add_column("Audit")
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
    message_locale = DEFAULT_LOCALE if output_format == "json" else (locale or DEFAULT_LOCALE)
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


def _latent_skill_scope_optional_all(value: str | None) -> LatentSkillScope | None:
    if value is None or value == "project":
        return LatentSkillScope.project
    if value == "global":
        return LatentSkillScope.global_
    if value == "all":
        return None
    raise ValidationFailedError("scope must be 'project', 'global', or 'all'.")


def _context_scope(value: str) -> ContextSummaryScope:
    return ContextSummaryScope.global_ if value == "global" else ContextSummaryScope.project


def _fact_status(value: str) -> FactStatus:
    return FactStatus(value)


def _skill_decision(value: str | None) -> ProposeSkillDecision | None:
    if value is None:
        return None
    normalized = value.strip().casefold()
    if normalized in {"y", "yes"}:
        return ProposeSkillDecision.yes
    if normalized == "always":
        return ProposeSkillDecision.always
    if normalized in {"n", "no"}:
        return ProposeSkillDecision.no
    return None
