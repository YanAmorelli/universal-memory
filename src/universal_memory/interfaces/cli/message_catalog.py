from pathlib import Path

from universal_memory.infrastructure.config.toml_loader import load_config

DEFAULT_LOCALE = "en"
PT_BR_LOCALE = "pt-BR"

PT_BR_MESSAGES = {
    "Local memory created at .umem/.": "Memoria local criada em .umem/.",
    "Local memory already initialized.": "Memoria local ja inicializada.",
    "Created paths:": "Caminhos criados:",
    "Reused paths:": "Caminhos reutilizados:",
    "Audit: {audit_reference}": "Auditoria: {audit_reference}",
    "Suggested next command: umem status": "Proximo comando sugerido: umem status",
    "Hosts configured during onboarding:": "Hosts configurados no onboarding:",
    "files": "arquivos",
    "validation": "validacao",
    "snapshot": "snapshot",
    "audit": "auditoria",
    "Operation cancelled by user.": "Operacao cancelada pelo usuario.",
    "Initializing project scaffold...": "Inicializando scaffold do projeto...",
    "Configure host 'codex' (AGENTS.md support)? [Y/n]: ": (
        "Deseja configurar o host 'codex' (suporte a AGENTS.md)? [S/n]: "
    ),
    "Configure host 'claude_code' (CLAUDE.md support)? [Y/n]: ": (
        "Deseja configurar o host 'claude_code' (suporte a CLAUDE.md)? [S/n]: "
    ),
    "Pending manual step ({host_id}): {step}": "Passo manual pendente ({host_id}): {step}",
    "Unsupported hosts: {hosts}": "Hosts nao suportados: {hosts}",
    "Host setup failed for '{host_id}': {error}": "Falha ao configurar host '{host_id}': {error}",
    "Failure:": "Falha:",
    "Detail:": "Detalhe:",
    "Recovery:": "Recuperacao:",
    "Error": "Erro",
}


def normalize_locale(value: object) -> str:
    if not isinstance(value, str):
        return DEFAULT_LOCALE
    normalized = "-".join(value.strip().split("_"))
    if normalized.lower() == "pt-br":
        return PT_BR_LOCALE
    return DEFAULT_LOCALE


def project_locale(project_root: Path) -> str:
    try:
        loaded = load_config(project_root)
    except Exception:
        return DEFAULT_LOCALE
    preferences = loaded.merged.get("preferences")
    if not isinstance(preferences, dict):
        return DEFAULT_LOCALE
    return normalize_locale(preferences.get("locale"))


def human_message(message: str, *, locale: str = DEFAULT_LOCALE, **kwargs: object) -> str:
    template = (
        PT_BR_MESSAGES.get(message, message)
        if normalize_locale(locale) == PT_BR_LOCALE
        else message
    )
    return template.format(**kwargs) if kwargs else template
