# Blind Hunter Review Prompt

Você é o Blind Hunter. Revise o diff abaixo sem contexto adicional do projeto. Procure bugs, regressões comportamentais, suposições quebradas, inconsistências internas, APIs mal definidas, problemas de idempotência, riscos de manutenção e lacunas de teste. Produza apenas findings acionáveis em Markdown.

Para cada finding:
- Título de uma linha
- Severidade: high, medium ou low
- Evidência objetiva no diff
- Impacto concreto

## Diff

```diff
diff --git a/_bmad-output/implementation-artifacts/1-4-criar-layout-local-umem-e-configura-o-toml.md b/_bmad-output/implementation-artifacts/1-4-criar-layout-local-umem-e-configura-o-toml.md
new file mode 100644
index 0000000..d3c7b7a
--- /dev/null
+++ b/_bmad-output/implementation-artifacts/1-4-criar-layout-local-umem-e-configura-o-toml.md
@@ -0,0 +1,188 @@
+# Story 1.4: Criar Layout Local `.umem/` e Configuração TOML
+
+Status: review
+
+<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->
+
+## Story
+
+Como um usuário inicializando um projeto,
+eu quero que o `universal-memory` crie e reconheça uma estrutura local legível,
+para que eu possa versionar, inspecionar e editar manualmente a memória do projeto.
+
+## Acceptance Criteria
+
+1. **Dado** testes de inicialização de projeto escritos primeiro,
+   **Quando** o comando/use case de inicialização roda em um diretório limpo,
+   **Então** a estrutura `.umem/` é criada com `config.toml`, `memory/`, `audit/events.jsonl`, `snapshots/`, `skills/` e `benchmarks/`;
+   **E** os arquivos iniciais são legíveis por humanos e seguros para edição manual.
+
+2. **Dado** uma configuração global e uma configuração de projeto,
+   **Quando** a configuração é carregada,
+   **Então** TOML é lido com `tomllib` e preparado para escrita com `tomli-w`;
+   **E** caminhos globais e locais são resolvidos sem depender de rede.
+
+## Tasks / Subtasks
+
+- [x] **Task 1: Escrever testes RED para layout local e carregamento de config** (AC: 1, 2)
+  - [x] Criar `tests/application/test_setup_project.py` cobrindo a inicialização em diretório limpo e a idempotência básica do fluxo de setup sem CLI.
+  - [x] Criar `tests/infrastructure/test_project_layout.py` validando a criação da árvore `.umem/` canônica e dos arquivos iniciais legíveis por humanos.
+  - [x] Criar `tests/infrastructure/config/test_toml_loader.py` validando leitura com `tomllib`, serialização com `tomli-w` e merge/resolução entre config global e config de projeto.
+  - [x] Confirmar a fase RED com falhas por ausência das implementações de `application/onboarding/` e `infrastructure/config/`.
+
+- [x] **Task 2: Implementar o modelo de configuração e o layout persistente local** (AC: 1, 2)
+  - [x] Criar `src/universal_memory/infrastructure/config/__init__.py`.
+  - [x] Criar `src/universal_memory/infrastructure/config/project_layout.py` com helpers explícitos para materializar e reconhecer `.umem/`.
+  - [x] Criar `src/universal_memory/infrastructure/config/toml_loader.py` com leitura usando `tomllib` e escrita preparada via `tomli-w`, sem dependência de rede.
+  - [x] Definir valores iniciais legíveis para:
+    - [x] `.umem/config.toml`
+    - [x] `.umem/audit/events.jsonl`
+    - [x] `.umem/benchmarks/retrieval-results.json`
+  - [x] Garantir que a árvore criada siga exatamente o layout canônico da arquitetura:
+    - [x] `.umem/config.toml`
+    - [x] `.umem/memory/`
+    - [x] `.umem/audit/events.jsonl`
+    - [x] `.umem/snapshots/`
+    - [x] `.umem/skills/`
+    - [x] `.umem/benchmarks/`
+
+- [x] **Task 3: Implementar o use case de onboarding sem acoplar a CLI** (AC: 1, 2)
+  - [x] Criar `src/universal_memory/application/__init__.py` caso ainda não exista.
+  - [x] Criar `src/universal_memory/application/onboarding/__init__.py`.
+  - [x] Criar `src/universal_memory/application/onboarding/setup_project.py` para orquestrar a inicialização do projeto e retornar um resultado estruturado para consumo futuro pela CLI e MCP.
+  - [x] Garantir que o use case permaneça síncrono e que qualquer I/O de filesystem/TOML fique encapsulado em `infrastructure/config/`.
+  - [x] Não introduzir adapter CLI nesta story; `src/universal_memory/__main__.py` deve continuar mínimo até a Story 1.5.
+
+- [x] **Task 4: Validar reconhecimento e resolução de configuração global + projeto** (AC: 2)
+  - [x] Cobrir o caminho global `~/.config/universal-memory/config.toml` apenas como entrada de leitura/resolução nesta story.
+  - [x] Garantir que a configuração de projeto viva em `.umem/config.toml`.
+  - [x] Garantir que caminhos de projeto retornados sejam relativos quando fizer sentido para output/diagnóstico e absolutos apenas internamente quando necessário para I/O.
+  - [x] Garantir que cenários inválidos de TOML resultem em `InvalidConfigError`, sem uso de `ValueError`/`RuntimeError` para erros conhecidos.
+
+- [x] **Task 5: Fechar GREEN com suíte, tipagem e verificação de regressão** (AC: 1, 2)
+  - [x] Executar `uv run pytest tests/application/test_setup_project.py tests/infrastructure/test_project_layout.py tests/infrastructure/config/test_toml_loader.py`.
+  - [x] Executar `uv run pytest` para validar ausência de regressões nas stories 1.1–1.3.
+  - [x] Executar `uv run ruff check .` e `uv run pyright`.
diff --git a/_bmad-output/implementation-artifacts/sprint-status.yaml b/_bmad-output/implementation-artifacts/sprint-status.yaml
index 2d100d2..2250e60 100644
--- a/_bmad-output/implementation-artifacts/sprint-status.yaml
+++ b/_bmad-output/implementation-artifacts/sprint-status.yaml
@@ -35,7 +35,7 @@
 # - Dev moves story to 'review', then runs code-review (fresh context, different LLM recommended)
 
 generated: "2026-05-22T21:17:01.194515Z"
-last_updated: "2026-05-22T23:15:00Z"
+last_updated: "2026-05-24T03:15:00Z"
 project: universal-memory
 project_key: NOKEY
 tracking_system: file-system
@@ -47,7 +47,7 @@ development_status:
 
   1-2-definir-modelos-de-dom-nio-para-mem-ria: done
   1-3-definir-exce-es-e-ports-de-dom-nio: done
-  1-4-criar-layout-local-umem-e-configura-o-toml: backlog
+  1-4-criar-layout-local-umem-e-configura-o-toml: review
   1-5-implementar-inicializa-o-cli-m-nima: backlog
   epic-1-retrospective: optional
   epic-2: backlog
diff --git a/src/universal_memory/application/__init__.py b/src/universal_memory/application/__init__.py
new file mode 100644
index 0000000..9e1cd78
--- /dev/null
+++ b/src/universal_memory/application/__init__.py
@@ -0,0 +1 @@
+"""Application layer for universal-memory."""
diff --git a/src/universal_memory/application/onboarding/__init__.py b/src/universal_memory/application/onboarding/__init__.py
new file mode 100644
index 0000000..fbbd6b9
--- /dev/null
+++ b/src/universal_memory/application/onboarding/__init__.py
@@ -0,0 +1,8 @@
+"""Onboarding use cases for universal-memory."""
+
+from universal_memory.application.onboarding.setup_project import (
+    SetupProjectResult,
+    setup_project,
+)
+
+__all__ = ["SetupProjectResult", "setup_project"]
diff --git a/src/universal_memory/application/onboarding/setup_project.py b/src/universal_memory/application/onboarding/setup_project.py
new file mode 100644
index 0000000..d92af55
--- /dev/null
+++ b/src/universal_memory/application/onboarding/setup_project.py
@@ -0,0 +1,44 @@
+from dataclasses import dataclass
+from pathlib import Path
+
+from universal_memory.infrastructure.config.project_layout import ensure_project_layout
+from universal_memory.infrastructure.config.toml_loader import load_config
+
+
+@dataclass(frozen=True, slots=True)
+class SetupProjectResult:
+    project_path: Path
+    config_path: Path
+    memory_path: Path
+    audit_path: Path
+    snapshots_path: Path
+    created: bool
+    already_initialized: bool
+    created_paths: list[str]
+    existing_paths: list[str]
+
+
+def setup_project(
+    project_root: Path, global_config_path: Path | None = None
+) -> SetupProjectResult:
+    normalized_project_root = project_root.resolve()
+    layout_result = ensure_project_layout(normalized_project_root)
+
+    # Load config after materializing defaults so downstream adapters can rely on valid TOML.
+    load_config(
+        project_root=normalized_project_root,
+        global_config_path=global_config_path,
+    )
+
+    umem_root = normalized_project_root / ".umem"
+    return SetupProjectResult(
+        project_path=normalized_project_root,
+        config_path=umem_root / "config.toml",
+        memory_path=umem_root / "memory",
+        audit_path=umem_root / "audit" / "events.jsonl",
+        snapshots_path=umem_root / "snapshots",
+        created=layout_result.created,
+        already_initialized=not layout_result.created,
+        created_paths=layout_result.created_paths,
+        existing_paths=layout_result.existing_paths,
+    )
diff --git a/src/universal_memory/infrastructure/__init__.py b/src/universal_memory/infrastructure/__init__.py
new file mode 100644
index 0000000..a05ab65
--- /dev/null
+++ b/src/universal_memory/infrastructure/__init__.py
@@ -0,0 +1 @@
+"""Infrastructure layer for universal-memory."""
diff --git a/src/universal_memory/infrastructure/config/__init__.py b/src/universal_memory/infrastructure/config/__init__.py
new file mode 100644
index 0000000..2316848
--- /dev/null
+++ b/src/universal_memory/infrastructure/config/__init__.py
@@ -0,0 +1,23 @@
+"""Project layout and configuration I/O helpers."""
+
+from universal_memory.infrastructure.config.project_layout import (
+    PROJECT_LAYOUT_PATHS,
+    ProjectLayoutResult,
+    ensure_project_layout,
+    is_project_initialized,
+)
+from universal_memory.infrastructure.config.toml_loader import (
+    LoadedConfig,
+    dump_toml_document,
+    load_config,
+)
+
+__all__ = [
+    "PROJECT_LAYOUT_PATHS",
+    "LoadedConfig",
+    "ProjectLayoutResult",
+    "dump_toml_document",
+    "ensure_project_layout",
+    "is_project_initialized",
+    "load_config",
+]
diff --git a/src/universal_memory/infrastructure/config/project_layout.py b/src/universal_memory/infrastructure/config/project_layout.py
new file mode 100644
index 0000000..b5e0f64
--- /dev/null
+++ b/src/universal_memory/infrastructure/config/project_layout.py
@@ -0,0 +1,78 @@
+from dataclasses import dataclass
+from pathlib import Path
+
+PROJECT_LAYOUT_PATHS = [
+    ".umem/config.toml",
+    ".umem/memory",
+    ".umem/audit/events.jsonl",
+    ".umem/snapshots",
+    ".umem/skills",
+    ".umem/benchmarks/retrieval-results.json",
+]
+
+DEFAULT_CONFIG_TOML = '[project]\nname = ""\ncreated_by = "universal-memory"\n'
+DEFAULT_AUDIT_EVENTS_JSONL = ""
+DEFAULT_RETRIEVAL_RESULTS_JSON = "{\n}\n"
+
+
+@dataclass(frozen=True, slots=True)
+class ProjectLayoutResult:
+    created: bool
+    created_paths: list[str]
+    existing_paths: list[str]
+
+
+def ensure_project_layout(project_root: Path) -> ProjectLayoutResult:
+    umem_root = project_root / ".umem"
+    umem_root.mkdir(parents=True, exist_ok=True)
+
+    tracked_paths = {
+        ".umem/config.toml": umem_root / "config.toml",
+        ".umem/memory": umem_root / "memory",
+        ".umem/audit/events.jsonl": umem_root / "audit" / "events.jsonl",
+        ".umem/snapshots": umem_root / "snapshots",
+        ".umem/skills": umem_root / "skills",
+        ".umem/benchmarks/retrieval-results.json": umem_root
+        / "benchmarks"
+        / "retrieval-results.json",
+    }
+    default_files = {
+        ".umem/config.toml": DEFAULT_CONFIG_TOML,
+        ".umem/audit/events.jsonl": DEFAULT_AUDIT_EVENTS_JSONL,
+        ".umem/benchmarks/retrieval-results.json": DEFAULT_RETRIEVAL_RESULTS_JSON,
+    }
+
+    created_paths: list[str] = []
+    existing_paths: list[str] = []
+    for relative_path in PROJECT_LAYOUT_PATHS:
+        target = tracked_paths[relative_path]
+        if target.exists():
+            existing_paths.append(relative_path)
+            continue
+
+        if relative_path in default_files:
+            target.parent.mkdir(parents=True, exist_ok=True)
+            target.write_text(default_files[relative_path])
+        else:
+            target.mkdir(parents=True, exist_ok=True)
+        created_paths.append(relative_path)
+
+    return ProjectLayoutResult(
+        created=bool(created_paths),
+        created_paths=created_paths,
+        existing_paths=existing_paths,
+    )
+
+
+def is_project_initialized(project_root: Path) -> bool:
+    umem_root = project_root / ".umem"
+    required_paths = [
+        umem_root / "config.toml",
+        umem_root / "memory",
+        umem_root / "audit" / "events.jsonl",
+        umem_root / "snapshots",
+        umem_root / "skills",
+        umem_root / "benchmarks",
+        umem_root / "benchmarks" / "retrieval-results.json",
+    ]
+    return all(path.exists() for path in required_paths)
diff --git a/src/universal_memory/infrastructure/config/toml_loader.py b/src/universal_memory/infrastructure/config/toml_loader.py
new file mode 100644
index 0000000..bfdc23c
--- /dev/null
+++ b/src/universal_memory/infrastructure/config/toml_loader.py
@@ -0,0 +1,80 @@
+from dataclasses import dataclass
+from pathlib import Path
+from typing import Any
+
+import tomli_w
+
+from universal_memory.domain import InvalidConfigError
+
+try:
+    import tomllib
+except ModuleNotFoundError as error:  # pragma: no cover
+    raise RuntimeError("Python 3.11+ with tomllib is required") from error
+
+
+TomlData = dict[str, Any]
+
+
+@dataclass(frozen=True, slots=True)
+class LoadedConfig:
+    global_config_path: Path
+    project_config_path: Path
+    global_data: TomlData
+    project_data: TomlData
+    merged: TomlData
+
+
+def load_config(
+    project_root: Path, global_config_path: Path | None = None
+) -> LoadedConfig:
+    normalized_project_root = project_root.resolve()
+    resolved_global_config_path = (
+        global_config_path.resolve()
+        if global_config_path is not None
+        else Path.home() / ".config" / "universal-memory" / "config.toml"
+    )
+    project_config_path = normalized_project_root / ".umem" / "config.toml"
+
+    global_data = _read_toml_document(resolved_global_config_path)
+    project_data = _read_toml_document(project_config_path)
+    merged = _deep_merge(global_data, project_data)
+
+    return LoadedConfig(
+        global_config_path=resolved_global_config_path,
+        project_config_path=project_config_path,
+        global_data=global_data,
+        project_data=project_data,
+        merged=merged,
+    )
+
+
+def dump_toml_document(document: TomlData) -> str:
+    return tomli_w.dumps(document)
+
+
+def _read_toml_document(path: Path) -> TomlData:
+    if not path.exists():
+        return {}
+
+    try:
+        with path.open("rb") as handle:
+            data = tomllib.load(handle)
+    except tomllib.TOMLDecodeError as error:
+        raise InvalidConfigError(f"Invalid TOML in {path.name}: {error}") from error
+
+    if not isinstance(data, dict):
+        raise InvalidConfigError(f"Invalid TOML in {path.name}: root must be a table")
+    return data
+
+
+def _deep_merge(base: TomlData, override: TomlData) -> TomlData:
+    merged: TomlData = {**base}
+
+    for key, value in override.items():
+        current = merged.get(key)
+        if isinstance(current, dict) and isinstance(value, dict):
+            merged[key] = _deep_merge(current, value)
+            continue
+        merged[key] = value
+
+    return merged
diff --git a/tests/application/test_setup_project.py b/tests/application/test_setup_project.py
new file mode 100644
index 0000000..60b893d
--- /dev/null
+++ b/tests/application/test_setup_project.py
@@ -0,0 +1,43 @@
+from pathlib import Path
+
+from universal_memory.application.onboarding.setup_project import setup_project
+
+
+def test_setup_project_initializes_layout_and_returns_structured_result(
+    tmp_path: Path,
+) -> None:
+    result = setup_project(tmp_path)
+
+    assert result.created is True
+    assert result.already_initialized is False
+    assert result.project_path == tmp_path
+    assert result.config_path == tmp_path / ".umem" / "config.toml"
+    assert result.memory_path == tmp_path / ".umem" / "memory"
+    assert result.audit_path == tmp_path / ".umem" / "audit" / "events.jsonl"
+    assert result.snapshots_path == tmp_path / ".umem" / "snapshots"
+    assert result.created_paths == [
+        ".umem/config.toml",
+        ".umem/memory",
+        ".umem/audit/events.jsonl",
+        ".umem/snapshots",
+        ".umem/skills",
+        ".umem/benchmarks/retrieval-results.json",
+    ]
+
+
+def test_setup_project_is_idempotent_and_reports_existing_layout(tmp_path: Path) -> None:
+    first_result = setup_project(tmp_path)
+    second_result = setup_project(tmp_path)
+
+    assert first_result.created is True
+    assert second_result.created is False
+    assert second_result.already_initialized is True
+    assert second_result.created_paths == []
+    assert second_result.existing_paths == [
+        ".umem/config.toml",
+        ".umem/memory",
+        ".umem/audit/events.jsonl",
+        ".umem/snapshots",
+        ".umem/skills",
+        ".umem/benchmarks/retrieval-results.json",
+    ]
diff --git a/tests/infrastructure/config/test_toml_loader.py b/tests/infrastructure/config/test_toml_loader.py
new file mode 100644
index 0000000..ad41031
--- /dev/null
+++ b/tests/infrastructure/config/test_toml_loader.py
@@ -0,0 +1,85 @@
+from pathlib import Path
+
+import pytest
+
+from universal_memory.domain import InvalidConfigError
+from universal_memory.infrastructure.config.toml_loader import (
+    dump_toml_document,
+    load_config,
+)
+
+
+def test_load_config_merges_global_and_project_config(tmp_path: Path) -> None:
+    global_config = tmp_path / "global.toml"
+    project_root = tmp_path / "workspace"
+    project_config = project_root / ".umem" / "config.toml"
+
+    global_config.write_text(
+        """
+[paths]
+storage_root = "/global/storage"
+
+[defaults]
+scope = "project"
+""".lstrip()
+    )
+    project_config.parent.mkdir(parents=True)
+    project_config.write_text(
+        """
+[paths]
+storage_root = ".umem/memory"
+
+[defaults]
+scope = "session"
+""".lstrip()
+    )
+
+    config = load_config(project_root=project_root, global_config_path=global_config)
+
+    assert config.global_config_path == global_config
+    assert config.project_config_path == project_config
+    assert config.merged["paths"]["storage_root"] == ".umem/memory"
+    assert config.merged["defaults"]["scope"] == "session"
+    assert config.global_data == {
+        "paths": {"storage_root": "/global/storage"},
+        "defaults": {"scope": "project"},
+    }
+    assert config.project_data == {
+        "paths": {"storage_root": ".umem/memory"},
+        "defaults": {"scope": "session"},
+    }
+
+
+def test_load_config_uses_default_global_path_when_not_overridden(
+    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
+) -> None:
+    monkeypatch.setenv("HOME", str(tmp_path))
+    project_root = tmp_path / "workspace"
+    project_config = project_root / ".umem" / "config.toml"
+
+    project_config.parent.mkdir(parents=True)
+    project_config.write_text("[project]\nname = \"demo\"\n")
+
+    config = load_config(project_root=project_root)
+
+    assert config.global_config_path == tmp_path / ".config" / "universal-memory" / "config.toml"
+    assert config.project_config_path == project_config
+    assert config.merged["project"]["name"] == "demo"
+
+
+def test_load_config_raises_invalid_config_error_for_invalid_toml(tmp_path: Path) -> None:
+    broken_config = tmp_path / "broken.toml"
+    broken_config.write_text("[project\nname = \"demo\"\n")
+
+    with pytest.raises(InvalidConfigError, match=r"broken\.toml"):
+        load_config(project_root=tmp_path, global_config_path=broken_config)
+
+
+def test_dump_toml_document_serializes_with_tomli_w_style() -> None:
+    document = {"project": {"name": "demo"}, "paths": {"storage_root": ".umem/memory"}}
+
+    rendered = dump_toml_document(document)
+
+    assert rendered == (
+        '[project]\nname = "demo"\n\n[paths]\nstorage_root = ".umem/memory"\n'
+    )
diff --git a/tests/infrastructure/test_project_layout.py b/tests/infrastructure/test_project_layout.py
new file mode 100644
index 0000000..27c0150
--- /dev/null
+++ b/tests/infrastructure/test_project_layout.py
@@ -0,0 +1,40 @@
+from pathlib import Path
+
+from universal_memory.infrastructure.config.project_layout import (
+    PROJECT_LAYOUT_PATHS,
+    ensure_project_layout,
+    is_project_initialized,
+)
+
+
+def test_ensure_project_layout_creates_canonical_tree_with_human_readable_files(
+    tmp_path: Path,
+) -> None:
+    result = ensure_project_layout(tmp_path)
+    umem_root = tmp_path / ".umem"
+
+    assert result.created is True
+    assert result.created_paths == PROJECT_LAYOUT_PATHS
+    assert umem_root.is_dir()
+    assert (umem_root / "memory").is_dir()
+    assert (umem_root / "audit").is_dir()
+    assert (umem_root / "snapshots").is_dir()
+    assert (umem_root / "skills").is_dir()
+    assert (umem_root / "benchmarks").is_dir()
+    assert (umem_root / "config.toml").read_text() == (
+        '[project]\nname = ""\ncreated_by = "universal-memory"\n'
+    )
+    assert (umem_root / "audit" / "events.jsonl").read_text() == ""
+    assert (umem_root / "benchmarks" / "retrieval-results.json").read_text() == "{\n}\n"
+    assert is_project_initialized(tmp_path) is True
+
+
+def test_ensure_project_layout_is_idempotent_and_reports_existing_paths(tmp_path: Path) -> None:
+    ensure_project_layout(tmp_path)
+
+    result = ensure_project_layout(tmp_path)
+
+    assert result.created is False
+    assert result.created_paths == []
+    assert result.existing_paths == PROJECT_LAYOUT_PATHS
+    assert is_project_initialized(tmp_path) is True
```
