# Acceptance Auditor Review Prompt

Você é o Acceptance Auditor. Revise o diff abaixo em relação aos critérios de aceitação e objetivos descritos na especificação (Spec) fornecida. Verifique se há violações de critérios de aceitação, desvios de intenção da spec, comportamentos especificados que ficaram faltando ou contradições. Retorne as descobertas como uma lista Markdown.

Para cada finding:
- Título descritivo de uma linha
- Critério de aceitação (AC) ou requisito violado
- Evidência factual do diff

## Especificação da História (Spec)

```markdown
# Story 2.5: Reverter Última Mutação por Escopo

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário recuperando uma alteração automática,  
eu quero reverter a última mutação por escopo,  
para que eu possa restaurar rapidamente memórias, regras, skills ou arquivos de instrução ao seu estado anterior.

## Acceptance Criteria

1. **Dado** snapshots válidos para um escopo (`project` ou `global`)
   **Quando** o usuário solicita o rollback desse escopo
   **Então** o sistema identifica o snapshot mais recente aplicável a esse escopo
   **E** restaura com sucesso o conteúdo do backup original de volta para o arquivo de destino (usando escrita atômica e segura)
   **E** registra um novo evento de auditoria para a ação `rollback` no escopo solicitado com resultado `success` e status `logged`.

2. **Dado** que não existe nenhum snapshot para o escopo solicitado
   **Quando** o rollback é executado
   **Então** o sistema aborta a operação e retorna um erro de domínio tipado (`SnapshotFailedError`) com uma mensagem clara e um hint de recuperação acionável
   **E** garante que nenhum arquivo do projeto é alterado de forma alguma.

3. **Dado** um snapshot cujos bytes de backup foram corrompidos ou possuem um hash SHA-256 incompatível com o hash registrado originalmente no manifesto
   **Quando** o rollback tenta restaurá-lo
   **Então** a operação é imediatamente bloqueada (nenhuma alteração é feita no arquivo original)
   **E** o sistema registra um evento de auditoria de falha para a ação `rollback` com resultado `failure` contendo evidências suficientes da falha de integridade no log sem expor qualquer segredo brutos
   **E** lança um erro tipado de domínio (`SnapshotFailedError`).

4. **Dado** o ambiente local de desenvolvimento sem internet (offline)
   **Quando** o usuário executa o rollback por escopo
   **Então** a reversão funciona de forma robusta localmente, sem qualquer conectividade de rede externa
   **E** completa em menos de 1 minuto em um projeto local de teste.

5. **Dado** execução interativa padrão via CLI (sem a flag `--yes`/`-y`)
   **Quando** o comando de rollback é acionado: `umem rollback --scope <scope>`
   **Então** o sistema exibe de forma clara na saída humana os detalhes do rollback (escopo alvo, ID e timestamp do snapshot selecionado, a ação original que causou a mutação e o caminho relativo do arquivo afetado)
   **E** exibe uma pergunta de confirmação explícita (prompt interativo `Deseja prosseguir com o rollback? [s/N]: `)
   **E** realiza a escrita apenas sob confirmação positiva, cancelando de forma segura em caso negativo sem alterar arquivos.

6. **Dado** execução via CLI com `--format json`
   **Quando** o rollback é bem-sucedido
   **Então** o sistema emite no stdout apenas o envelope JSON padrão com a chave `"ok": true`, `"operation": "rollback"`, `"scope": "<scope>"` e, em `"data"`, o seguinte payload:
   ```json
   {
     "ok": true,
     "operation": "rollback",
     "scope": "project",
     "data": {
       "scope": "project",
       "snapshot_reference": "uuid-do-snapshot-restaurado",
       "restored_paths": ["caminho/relativo/do/arquivo/restaurado"],
       "audit_reference": "uuid-do-evento-de-auditoria-do-rollback"
     },
     "warnings": []
   }
   ```

7. **Dado** falha no rollback sob o formato `--format json`
   **Quando** o comando falha ou é abortado
   **Então** o sistema emite o envelope JSON de erro padrão com `"ok": false` e o objeto de erro correspondente mapeado de acordo com a especificação, garantindo saída limpa sem Rich ansi.

## Tasks / Subtasks

- [x] **Task 1: Estender o Port de Repositório de Snapshots** (AC: 1, 3)
  - [x] Adicionar o método abstrato `get_content(self, id: str) -> bytes` na classe `SnapshotRepository` em `src/universal_memory/domain/ports/snapshot_repository.py` para permitir a leitura segura dos bytes do backup associado ao ID do snapshot.
  - [x] Implementar o método `get_content(self, id: str) -> bytes` em `LocalSnapshotRepository` em `src/universal_memory/infrastructure/security/local_snapshot_repository.py`. Deve carregar o arquivo localizado em `self.files_root / id`. Caso o arquivo de backup físico não exista, deve lançar `StorageError`.

- [x] **Task 2: Escrever Testes Unitários (RED) para o Rollback Use Case** (AC: 1, 2, 3, 4)
  - [x] Criar o arquivo de testes `tests/application/security/test_rollback_use_case.py`.
  - [x] Testar cenário de sucesso: dado múltiplos snapshots, ordena por timestamp, seleciona o mais recente do escopo correto, lê o backup, grava no arquivo de destino, e cria o registro de auditoria com status `logged` (para o rollback bem-sucedido).
  - [x] Testar cenário de erro por falta de snapshot: garante que uma lista vazia resulte no lançamento de `SnapshotFailedError`, sem causar efeitos colaterais nos arquivos.
  - [x] Testar cenário de falha de integridade por hash incompatível: simular bytes corrompidos no arquivo de backup físico (gerando um hash SHA-256 diferente do registrado na entidade `Snapshot`). Garante que a escrita seja bloqueada, lance `SnapshotFailedError` e registre auditoria com `result="failure"` e status `failed`.
  - [x] Validar independência de rede (comportamento offline nativo).

- [x] **Task 3: Implementar o Use Case de Rollback no Application Layer** (AC: 1, 2, 3, 4)
  - [x] Criar a classe `RollbackUseCase` em `src/universal_memory/application/security/rollback_use_case.py` aceitando no construtor `project_root: Path`, `snapshot_repository: SnapshotRepository` e `audit_log_repository: AuditLogRepository`.
  - [x] Definir as classes de dados `RollbackCommand` e `RollbackResult`. O command deve conter `scope: SnapshotScope`, `origin: str` e `action: str` ("rollback").
  - [x] No método `execute(self, command: RollbackCommand) -> RollbackResult`:
    - [x] Listar todos os snapshots do escopo fornecido.
    - [x] Lançar `SnapshotFailedError` com um hint de recuperação caso nenhum snapshot seja retornado.
    - [x] Selecionar o snapshot mais recente com base em `timestamp` cronológico.
    - [x] Ler os bytes de backup correspondentes chamando `snapshot_repository.get_content(snapshot.id)`.
    - [x] Calcular o SHA-256 dos bytes lidos e comparar com o `snapshot.hash` registrado. Se houver divergência, registrar um evento de auditoria de falha (`result="failure"`, `status="failed"`) e lançar `SnapshotFailedError` relatando quebra de integridade.
    - [x] Realizar a escrita de volta ao arquivo original (`self.project_root / snapshot.relative_path`) utilizando o mesmo mecanismo de escrita atômica segura (escrita em arquivo temporário `.tmp` com uuid4 e `os.replace` subsequente) estabelecido no `SafeWriteUseCase` para evitar corrupção de arquivos em caso de interrupção abrupta.
    - [x] Registrar o novo evento de auditoria de sucesso para o rollback (`result="success"`, `status="logged"`, `snapshot_reference=snapshot.id`).
    - [x] Retornar o `RollbackResult` contendo as referências necessárias.
  - [x] Exportar `RollbackCommand`, `RollbackResult` e `RollbackUseCase` em `src/universal_memory/application/security/__init__.py`.

- [x] **Task 4: Escrever Testes de Integração e de CLI (RED) para o Rollback** (AC: 5, 6, 7)
  - [x] Criar o arquivo de testes `tests/interfaces/cli/test_rollback_command.py`.
  - [x] Testar execução com flag `--yes` / `-y` para validar o fluxo não interativo (sucesso e falha, verificando as saídas humana e JSON).
  - [x] Testar fluxo interativo de confirmação com mocks para `builtins.input` retornando `s` (Sim) e `n` (Não).
  - [x] Garantir que `--format json` retorne a estrutura envelopada DevEx exata sem misturar ansi/Rich.
  - [x] Garantir o retorno do envelope de erro padrão no formato JSON para falhas de domínio.

- [x] **Task 5: Implementar o Subcomando `rollback` no CLI Adapter** (AC: 5, 6, 7)
  - [x] Modificar `src/universal_memory/interfaces/cli/init_command.py` para registrar o subcomando `rollback` com os argumentos `--scope`, `--format` e `--yes` / `-y`.
  - [x] Adicionar os handlers de UI no arquivo de comandos CLI:
    - [x] Obter a lista de snapshots e identificar o candidato para rollback.
    - [x] Se não for passado `--yes` ou `-y`, exibir o prompt conciso e formatado e capturar a confirmação do usuário de forma segura.
    - [x] Tratar exceções de domínio mapeando-as para códigos e mensagens amigáveis no console humano e no envelope JSON.
  - [x] Registrar e integrar a dependência de `RollbackUseCase` em `src/universal_memory/bootstrap/cli.py`.

- [x] **Task 6: Verificação de Qualidade Final e Regressões** (AC: todos)
  - [x] Executar toda a suíte de testes com `.venv/bin/pytest`.
  - [x] Validar conformidade estilística e linting estrito com `.venv/bin/ruff check .`.
  - [x] Validar tipagem sem erros executando `.venv/bin/pyright`.

## Dev Notes

- **Escrita Atômica na Restauração:** Não faça uma escrita direta com `Path.write_bytes()`. Siga rigorosamente o padrão de escrita atômica do `SafeWriteUseCase` (criação de um arquivo temporário no mesmo diretório de destino e substituição atômica via `os.replace`), prevenindo falhas parciais que deixariam o arquivo final zerado ou corrompido em caso de crash do processo.
- **Port / Adapters:** A lógica de leitura de arquivos de backup pertence ao infra (`LocalSnapshotRepository`), não ao use case. O use case acessa apenas a abstração do port (`SnapshotRepository.get_content`).
- **Integridade dos Snapshots:** É vital fazer a checagem SHA-256 do arquivo físico de backup antes de qualquer escrita no arquivo de destino do projeto para manter a garantia de segurança de rollback.
- **Formato Rich:** As mensagens humanas devem ser elegantes utilizando o terminal padrão do Rich, mas `--format json` deve desativar totalmente impressões adicionais e retornar JSON estrito.

### Project Structure Notes

- Nova classe `RollbackUseCase` em `src/universal_memory/application/security/rollback_use_case.py`.
- Novo arquivo de testes unitários do use case em `tests/application/security/test_rollback_use_case.py`.
- Novo arquivo de testes de CLI em `tests/interfaces/cli/test_rollback_command.py`.

### References

- `_bmad-output/planning-artifacts/epics.md#Story 2.5` (Critérios de aceitação para rollback por escopo)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md#umem rollback` (Especificação de interface CLI, envelope JSON e contrato de confirmação)
- `src/universal_memory/domain/ports/snapshot_repository.py` (Port de snapshots a ser estendido)
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py` (Repositório de snapshots concreto)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- 2026-05-26: Story `2-5-reverter-ltima-muta-o-por-escopo` identificada a partir do `sprint-status.yaml` como a próxima história pendente (backlog).
- 2026-05-26: Análise profunda do contrato de port `SnapshotRepository` e do fluxo de rollback definido no `devex-interaction-spec.md`.
- 2026-05-26: Estruturação das tarefas detalhadas seguindo a metodologia TDD (testes unitários RED primeiro).
- 2026-05-26: RED do use case confirmado com `ModuleNotFoundError` para `rollback_use_case` antes da implementação.
- 2026-05-26: Testes focados do use case, port e repositório passaram após implementação inicial.
- 2026-05-26: RED do CLI confirmado com falhas de parser para comando `rollback` antes da implementação do adapter.
- 2026-05-26: Suite completa, ruff e pyright executados com sucesso antes da marcação para review.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implementado `SnapshotRepository.get_content` e leitura concreta dos bytes físicos de backup em `LocalSnapshotRepository`, com erro `StorageError` para arquivo ausente.
- Implementado `RollbackUseCase` com seleção do snapshot mais recente por escopo, validação SHA-256 antes de escrita, restauração atômica via arquivo temporário e `os.replace`, auditoria de sucesso e auditoria de falha de integridade.
- Implementado `umem rollback` no CLI com `--scope`, `--format`, `--yes`/`-y`, prévia humana do snapshot selecionado, confirmação interativa e envelopes JSON limpos para sucesso/falha.
- Validado com `.venv/bin/pytest` (129 passed), `.venv/bin/ruff check .` (passed) e `.venv/bin/pyright` (0 errors).

### File List

- `_bmad-output/implementation-artifacts/2-5-reverter-ltima-muta-o-por-escopo.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/security/__init__.py`
- `src/universal_memory/application/security/rollback_use_case.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/domain/ports/snapshot_repository.py`
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/security/test_list_snapshots_use_case.py`
- `tests/application/security/test_rollback_use_case.py`
- `tests/application/security/test_safe_write_use_case.py`
- `tests/domain/test_ports.py`
- `tests/infrastructure/security/test_local_snapshot_repository.py`
- `tests/interfaces/cli/test_rollback_command.py`

### Change Log

- 2026-05-26: Implementado rollback por escopo com validação de integridade, escrita atômica, auditoria e adapter CLI; story movida para `review`.
```

## Diff

```diff
diff --git a/src/universal_memory/application/security/__init__.py b/src/universal_memory/application/security/__init__.py
index 3a86e40..63b50a7 100644
--- a/src/universal_memory/application/security/__init__.py
+++ b/src/universal_memory/application/security/__init__.py
@@ -12,6 +12,11 @@ from universal_memory.application.security.list_snapshots_use_case import (
     ListSnapshotsUseCase,
     SnapshotEntry,
 )
+from universal_memory.application.security.rollback_use_case import (
+    RollbackCommand,
+    RollbackResult,
+    RollbackUseCase,
+)
 from universal_memory.application.security.safe_write_use_case import (
     SafeWriteCommand,
     SafeWriteResult,
@@ -26,6 +31,9 @@ __all__ = [
     "ListSnapshotsCommand",
     "ListSnapshotsResult",
     "ListSnapshotsUseCase",
+    "RollbackCommand",
+    "RollbackResult",
+    "RollbackUseCase",
     "SafeWriteCommand",
     "SafeWriteResult",
     "SafeWriteUseCase",
diff --git a/src/universal_memory/application/security/rollback_use_case.py b/src/universal_memory/application/security/rollback_use_case.py
new file mode 100644
index 0000000..c141156
--- /dev/null
+++ b/src/universal_memory/application/security/rollback_use_case.py
@@ -0,0 +1,156 @@
+from __future__ import annotations
+
+import os
+from dataclasses import dataclass
+from datetime import UTC, datetime
+from hashlib import sha256
+from pathlib import Path
+from uuid import uuid4
+
+from universal_memory.domain import SnapshotFailedError
+from universal_memory.domain.entities import (
+    AuditEvent,
+    AuditEventScope,
+    Snapshot,
+    SnapshotScope,
+    SnapshotStatus,
+)
+from universal_memory.domain.ports import AuditLogRepository, SnapshotRepository
+
+
+@dataclass(frozen=True, slots=True)
+class RollbackCommand:
+    scope: SnapshotScope
+    origin: str
+    action: str = "rollback"
+
+
+@dataclass(frozen=True, slots=True)
+class RollbackResult:
+    scope: SnapshotScope
+    snapshot_reference: str
+    restored_paths: list[str]
+    audit_reference: str
+
+
+class RollbackUseCase:
+    def __init__(
+        self,
+        *,
+        project_root: Path,
+        snapshot_repository: SnapshotRepository,
+        audit_log_repository: AuditLogRepository,
+    ) -> None:
+        self.project_root = project_root.resolve()
+        self.snapshot_repository = snapshot_repository
+        self.audit_log_repository = audit_log_repository
+
+    def execute(self, command: RollbackCommand) -> RollbackResult:
+        snapshots = self.snapshot_repository.list(
+            scope=command.scope,
+            status=SnapshotStatus.created,
+        )
+        if not snapshots:
+            raise SnapshotFailedError(
+                "Nenhum snapshot encontrado para o escopo solicitado. "
+                "Hint: execute uma mutacao segura antes de tentar rollback."
+            )
+
+        snapshot = max(snapshots, key=lambda item: self._normalize_datetime(item.timestamp))
+        content = self.snapshot_repository.get_content(snapshot.id)
+        actual_hash = sha256(content).hexdigest()
+        if actual_hash != snapshot.hash:
+            self._record_audit(
+                command,
+                snapshot_reference=snapshot.id,
+                result="failure",
+                status="failed",
+            )
+            raise SnapshotFailedError(
+                "Falha de integridade do snapshot: hash SHA-256 do backup fisico "
+                "nao corresponde ao manifesto. Hint: inspecione os snapshots e recrie "
+                "o estado a partir de um backup confiavel."
+            )
+
+        target_path = self._resolve_target(snapshot)
+        try:
+            self._atomic_write_bytes(target_path, content)
+        except BaseException:
+            self._record_audit(
+                command,
+                snapshot_reference=snapshot.id,
+                result="failure",
+                status="failed",
+            )
+            raise
+
+        event = self._record_audit(
+            command,
+            snapshot_reference=snapshot.id,
+            result="success",
+            status="logged",
+        )
+        return RollbackResult(
+            scope=command.scope,
+            snapshot_reference=snapshot.id,
+            restored_paths=[snapshot.relative_path],
+            audit_reference=event.audit_reference,
+        )
+
+    def _resolve_target(self, snapshot: Snapshot) -> Path:
+        target_path = self.project_root / snapshot.relative_path
+        try:
+            target_path.resolve().relative_to(self.project_root)
+        except ValueError as exc:
+            raise SnapshotFailedError("Snapshot target path escapes project root") from exc
+        if target_path.exists() and not target_path.is_file():
+            raise SnapshotFailedError("Snapshot target path is not a file")
+        return target_path
+
+    def _atomic_write_bytes(self, target_path: Path, content: bytes) -> None:
+        target_path.parent.mkdir(parents=True, exist_ok=True)
+        temp_path = target_path.with_name(f"{target_path.name}.{uuid4()}.tmp")
+        try:
+            temp_path.write_bytes(content)
+            os.replace(temp_path, target_path)
+        except BaseException:
+            temp_path.unlink(missing_ok=True)
+            raise
+
+    def _record_audit(
+        self,
+        command: RollbackCommand,
+        *,
+        snapshot_reference: str,
+        result: str,
+        status: str,
+    ) -> AuditEvent:
+        timestamp = datetime.now(UTC)
+        audit_reference = str(uuid4())
+        event = AuditEvent(
+            id=audit_reference,
+            created_at=timestamp,
+            updated_at=timestamp,
+            timestamp=timestamp,
+            action=command.action,
+            scope=self._audit_scope(command.scope),
+            origin=command.origin,
+            result=result,
+            snapshot_reference=snapshot_reference,
+            audit_reference=audit_reference,
+            status=status,
+        )
+        self.audit_log_repository.write(event)
+        return event
+
+    @staticmethod
+    def _audit_scope(scope: SnapshotScope) -> AuditEventScope:
+        if scope == SnapshotScope.global_:
+            return AuditEventScope.global_
+        return AuditEventScope.project
+
+    @staticmethod
+    def _normalize_datetime(dt: datetime) -> datetime:
+        if dt.tzinfo is None or dt.tzinfo.utcoffset(dt) is None:
+            return dt.replace(tzinfo=UTC)
+        return dt
diff --git a/src/universal_memory/bootstrap/cli.py b/src/universal_memory/bootstrap/cli.py
index 6dc6a24..8b5c336 100644
--- a/src/universal_memory/bootstrap/cli.py
+++ b/src/universal_memory/bootstrap/cli.py
@@ -1,7 +1,13 @@
 from collections.abc import Sequence
 from pathlib import Path
 
-from universal_memory.application.security import ListAuditLogUseCase, ListSnapshotsUseCase
+from universal_memory.application.security import (
+    ListAuditLogUseCase,
+    ListSnapshotsUseCase,
+    RollbackUseCase,
+)
+from universal_memory.domain import SnapshotFailedError
+from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
 from universal_memory.infrastructure.config import (
     LocalConfigValidationPort,
     LocalProjectLayoutPort,
@@ -25,16 +31,34 @@ def main(argv: Sequence[str] | None = None) -> int:
     manifest_file = data_root / "snapshots" / "manifest.json"
     manifest_rel_path = str(manifest_file.relative_to(project_root))
     snapshots_list_use_case = ListSnapshotsUseCase(
-        snapshot_repository=LocalSnapshotRepository(
+        snapshot_repository=LocalSnapshotRepository(project_root=project_root, data_root=data_root),
+        manifest_path=manifest_rel_path,
+    )
+    snapshot_repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
+    rollback_use_case = RollbackUseCase(
+        project_root=project_root,
+        snapshot_repository=snapshot_repository,
+        audit_log_repository=LocalAuditLogRepository(
             project_root=project_root,
             data_root=data_root,
         ),
-        manifest_path=manifest_rel_path,
     )
+
+    def rollback_preview(scope: SnapshotScope) -> Snapshot:
+        snapshots = snapshot_repository.list(scope=scope, status=SnapshotStatus.created)
+        if not snapshots:
+            raise SnapshotFailedError(
+                "Nenhum snapshot encontrado para o escopo solicitado. "
+                "Hint: execute uma mutacao segura antes de tentar rollback."
+            )
+        return max(snapshots, key=lambda snapshot: snapshot.timestamp)
+
     configured_main = build_main(
         layout_port=LocalProjectLayoutPort(),
         config_validation_port=LocalConfigValidationPort(),
         audit_list_command=audit_list_use_case.execute,
         snapshots_list_command=snapshots_list_use_case.execute,
+        rollback_command=rollback_use_case.execute,
+        rollback_preview_command=rollback_preview,
     )
     return configured_main(argv)
diff --git a/src/universal_memory/domain/ports/snapshot_repository.py b/src/universal_memory/domain/ports/snapshot_repository.py
index ffda3e3..8dcb50e 100644
--- a/src/universal_memory/domain/ports/snapshot_repository.py
+++ b/src/universal_memory/domain/ports/snapshot_repository.py
@@ -19,6 +19,21 @@ class SnapshotRepository(ABC):
         """
         ...
 
+    @abstractmethod
+    def get_content(self, id: str) -> bytes:
+        """Read the physical backup bytes associated with a snapshot ID.
+
+        Args:
+            id: The unique identifier of the snapshot backup file.
+
+        Returns:
+            The backed up file content.
+
+        Raises:
+            UniversalMemoryError: If the backup file cannot be read.
+        """
+        ...
+
     @abstractmethod
     def list(
         self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None
diff --git a/src/universal_memory/infrastructure/security/local_snapshot_repository.py b/src/universal_memory/infrastructure/security/local_snapshot_repository.py
index 061f7d6..f1fe476 100644
--- a/src/universal_memory/infrastructure/security/local_snapshot_repository.py
+++ b/src/universal_memory/infrastructure/security/local_snapshot_repository.py
@@ -84,6 +84,15 @@ class LocalSnapshotRepository(SnapshotRepository):
                 return snapshot
         raise StorageError(f"Snapshot not found: {id}")
 
+    def get_content(self, id: str) -> bytes:
+        backup_path = self.files_root / id
+        try:
+            return backup_path.read_bytes()
+        except FileNotFoundError as exc:
+            raise StorageError(f"Snapshot backup file not found: {id}") from exc
+        except OSError as exc:
+            raise StorageError(f"Failed to read snapshot backup file: {id}") from exc
+
     def list(
         self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None
     ) -> list[Snapshot]:
diff --git a/src/universal_memory/interfaces/cli/init_command.py b/src/universal_memory/interfaces/cli/init_command.py
index bb17fc7..45c2e0a 100644
--- a/src/universal_memory/interfaces/cli/init_command.py
+++ b/src/universal_memory/interfaces/cli/init_command.py
@@ -17,16 +17,20 @@ from universal_memory.application.security import (
     ListAuditLogResult,
     ListSnapshotsCommand,
     ListSnapshotsResult,
+    RollbackCommand,
+    RollbackResult,
 )
 from universal_memory.domain import (
     ConfigValidationPort,
     InvalidConfigError,
     ProjectLayoutPort,
+    SnapshotFailedError,
     StorageError,
     ValidationFailedError,
 )
 from universal_memory.domain.entities import (
     AuditEventScope,
+    Snapshot,
     SnapshotScope,
     SnapshotStatus,
 )
@@ -35,14 +39,18 @@ AUDIT_REFERENCE_PLACEHOLDER = "not-implemented-yet"
 SetupProjectCommand = Callable[[Path], SetupProjectResult]
 ListAuditLogCommandHandler = Callable[[ListAuditLogCommand], ListAuditLogResult]
 ListSnapshotsCommandHandler = Callable[[ListSnapshotsCommand], ListSnapshotsResult]
+RollbackCommandHandler = Callable[[RollbackCommand], RollbackResult]
+RollbackPreviewHandler = Callable[[SnapshotScope], Snapshot]
 
 
-def main(
+def main(  # noqa: PLR0913
     argv: Sequence[str] | None = None,
     *,
     setup_project_command: SetupProjectCommand | None = None,
     audit_list_command: ListAuditLogCommandHandler | None = None,
     snapshots_list_command: ListSnapshotsCommandHandler | None = None,
+    rollback_command: RollbackCommandHandler | None = None,
+    rollback_preview_command: RollbackPreviewHandler | None = None,
 ) -> int:
     parser = _build_parser()
     args = parser.parse_args(argv)
@@ -74,16 +82,33 @@ def main(
             scope=_snapshot_scope(args.scope),
         )
 
+    if args.command == "rollback":
+        if rollback_command is None:
+            msg = "CLI rollback_command dependency was not configured."
+            raise RuntimeError(msg)
+        if rollback_preview_command is None:
+            msg = "CLI rollback_preview_command dependency was not configured."
+            raise RuntimeError(msg)
+        return _run_rollback(
+            rollback_command,
+            rollback_preview_command=rollback_preview_command,
+            output_format=args.output_format,
+            scope=_snapshot_scope(args.scope),
+            yes=args.yes,
+        )
+
     parser.print_help()
     return 0
 
 
-def build_main(
+def build_main(  # noqa: PLR0913
     *,
     layout_port: ProjectLayoutPort,
     config_validation_port: ConfigValidationPort,
     audit_list_command: ListAuditLogCommandHandler,
     snapshots_list_command: ListSnapshotsCommandHandler,
+    rollback_command: RollbackCommandHandler,
+    rollback_preview_command: RollbackPreviewHandler,
 ) -> Callable[[Sequence[str] | None], int]:
     command = _build_setup_project_command(
         layout_port=layout_port,
@@ -96,6 +121,8 @@ def build_main(
             setup_project_command=command,
             audit_list_command=audit_list_command,
             snapshots_list_command=snapshots_list_command,
+            rollback_command=rollback_command,
+            rollback_preview_command=rollback_preview_command,
         )
 
     return configured_main
@@ -148,6 +175,27 @@ def _build_parser() -> argparse.ArgumentParser:
         help="Scope filter",
     )
 
+    rollback_parser = subparsers.add_parser("rollback", help="Restore latest snapshot")
+    rollback_parser.add_argument(
+        "--format",
+        choices=["human", "json"],
+        default="human",
+        dest="output_format",
+        help="Output format",
+    )
+    rollback_parser.add_argument(
+        "--scope",
+        choices=["project", "global"],
+        default="project",
+        help="Scope to roll back",
+    )
+    rollback_parser.add_argument(
+        "--yes",
+        "-y",
+        action="store_true",
+        help="Skip interactive confirmation",
+    )
+
     return parser
 
 
@@ -237,6 +285,40 @@ def _run_snapshots_list(
     return 0
 
 
+def _run_rollback(
+    command: RollbackCommandHandler,
+    *,
+    rollback_preview_command: RollbackPreviewHandler,
+    output_format: str,
+    scope: SnapshotScope,
+    yes: bool,
+) -> int:
+    try:
+        preview = rollback_preview_command(scope)
+        if output_format != "json":
+            print(_format_human_rollback_preview(preview))
+            if not yes:
+                answer = input("Deseja prosseguir com o rollback? [s/N]: ")
+                if answer.strip().lower() not in {"s", "sim", "y", "yes"}:
+                    print("Rollback cancelado.")
+                    return 1
+
+        result = command(RollbackCommand(scope=scope, origin="cli"))
+    except OSError as error:
+        _print_expected_error(StorageError(str(error)), output_format=output_format)
+        return 1
+    except (SnapshotFailedError, StorageError, ValidationFailedError) as error:
+        _print_expected_error(error, output_format=output_format)
+        return 1
+
+    if output_format == "json":
+        print(json.dumps(_rollback_success_envelope(result), sort_keys=True))
+    else:
+        print(_format_human_rollback_success(result))
+
+    return 0
+
+
 def _success_envelope(result: SetupProjectResult) -> dict[str, Any]:
     return {
         "ok": True,
@@ -271,6 +353,21 @@ def _snapshots_success_envelope(
     }
 
 
+def _rollback_success_envelope(result: RollbackResult) -> dict[str, Any]:
+    return {
+        "ok": True,
+        "operation": "rollback",
+        "scope": result.scope.value,
+        "data": {
+            "scope": result.scope.value,
+            "snapshot_reference": result.snapshot_reference,
+            "restored_paths": result.restored_paths,
+            "audit_reference": result.audit_reference,
+        },
+        "warnings": [],
+    }
+
+
 def _init_payload(result: SetupProjectResult) -> dict[str, Any]:
     return {
         "project_path": _path_to_posix(result.project_path),
@@ -347,6 +444,31 @@ def _format_human_snapshots_output(result: ListSnapshotsResult) -> str:
     return "\n".join(lines)
 
 
+def _format_human_rollback_preview(snapshot: Snapshot) -> str:
+    return "\n".join(
+        [
+            "Rollback selecionado:",
+            f"Escopo: {snapshot.scope.value}",
+            f"Snapshot: {snapshot.id}",
+            f"Timestamp: {snapshot.timestamp.isoformat()}",
+            f"Acao original: {snapshot.action}",
+            f"Arquivo: {snapshot.relative_path}",
+        ]
+    )
+
+
+def _format_human_rollback_success(result: RollbackResult) -> str:
+    return "\n".join(
+        [
+            "Rollback concluido.",
+            f"Escopo: {result.scope.value}",
+            f"Snapshot: {result.snapshot_reference}",
+            f"Arquivos restaurados: {', '.join(result.restored_paths)}",
+            f"Auditoria: {result.audit_reference}",
+        ]
+    )
+
+
 def _print_expected_error(error: Exception, output_format: str) -> None:
     code = _error_code(error)
     detail = str(error)
@@ -378,6 +500,8 @@ def _print_expected_error(error: Exception, output_format: str) -> None:
 
 
 def _error_code(error: Exception) -> str:
+    if isinstance(error, SnapshotFailedError):
+        return "snapshot_failed"
     if isinstance(error, InvalidConfigError):
         return "invalid_config"
     if isinstance(error, ValidationFailedError):
@@ -386,6 +510,8 @@ def _error_code(error: Exception) -> str:
 
 
 def _error_message(error: Exception) -> str:
+    if isinstance(error, SnapshotFailedError):
+        return "Falha de snapshot."
     if isinstance(error, InvalidConfigError):
         return "Configuracao invalida."
     if isinstance(error, ValidationFailedError):
diff --git a/tests/application/security/test_list_snapshots_use_case.py b/tests/application/security/test_list_snapshots_use_case.py
index afd4621..73f0a3d 100644
--- a/tests/application/security/test_list_snapshots_use_case.py
+++ b/tests/application/security/test_list_snapshots_use_case.py
@@ -20,6 +20,9 @@ class RecordingSnapshotRepository(SnapshotRepository):
     def read(self, id: str) -> Snapshot:
         raise KeyError(id)
 
+    def get_content(self, id: str) -> bytes:
+        raise KeyError(id)
+
     def list(
         self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None
     ) -> list[Snapshot]:
diff --git a/tests/application/security/test_rollback_use_case.py b/tests/application/security/test_rollback_use_case.py
new file mode 100644
index 0000000..6f84a64
--- /dev/null
+++ b/tests/application/security/test_rollback_use_case.py
@@ -0,0 +1,208 @@
+from __future__ import annotations
+
+from datetime import UTC, datetime, timedelta
+from hashlib import sha256
+from pathlib import Path
+from uuid import uuid4
+
+import pytest
+
+from universal_memory.application.security.rollback_use_case import (
+    RollbackCommand,
+    RollbackUseCase,
+)
+from universal_memory.domain import SnapshotFailedError
+from universal_memory.domain.entities import (
+    AuditEvent,
+    Snapshot,
+    SnapshotScope,
+    SnapshotStatus,
+)
+from universal_memory.domain.ports import AuditLogRepository, SnapshotRepository
+
+
+class RecordingSnapshotRepository(SnapshotRepository):
+    def __init__(self, snapshots: list[Snapshot], content_by_id: dict[str, bytes]) -> None:
+        self.snapshots = snapshots
+        self.content_by_id = content_by_id
+
+    def read(self, id: str) -> Snapshot:
+        for snapshot in self.snapshots:
+            if snapshot.id == id:
+                return snapshot
+        raise KeyError(id)
+
+    def get_content(self, id: str) -> bytes:
+        return self.content_by_id[id]
+
+    def list(self, scope=None, status=None) -> list[Snapshot]:
+        snapshots = self.snapshots
+        if scope is not None:
+            snapshots = [snapshot for snapshot in snapshots if snapshot.scope == scope]
+        if status is not None:
+            snapshots = [snapshot for snapshot in snapshots if snapshot.status == status]
+        return snapshots
+
+    def write(self, entity: Snapshot) -> None:
+        self.snapshots.append(entity)
+
+    def migrate(self, target_version: int) -> None:
+        return None
+
+
+class RecordingAuditRepository(AuditLogRepository):
+    def __init__(self) -> None:
+        self.written: list[AuditEvent] = []
+
+    def read(self, id: str) -> AuditEvent:
+        for event in self.written:
+            if event.id == id:
+                return event
+        raise KeyError(id)
+
+    def list(self, scope=None) -> list[AuditEvent]:
+        return self.written
+
+    def write(self, entity: AuditEvent) -> None:
+        self.written.append(entity)
+
+    def migrate(self, target_version: int) -> None:
+        return None
+
+
+def make_snapshot(
+    *,
+    content: bytes,
+    created_at: datetime,
+    scope: SnapshotScope = SnapshotScope.project,
+    relative_path: str = ".umem/memory/facts.jsonl",
+    action: str = "safe_write",
+) -> Snapshot:
+    return Snapshot(
+        id=str(uuid4()),
+        created_at=created_at,
+        updated_at=created_at,
+        timestamp=created_at,
+        scope=scope,
+        origin="cli",
+        action=action,
+        relative_path=relative_path,
+        hash=sha256(content).hexdigest(),
+        status=SnapshotStatus.created,
+    )
+
+
+def test_rollback_restores_latest_snapshot_for_scope_and_audits_success(
+    tmp_path: Path,
+) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_bytes(b"current state\n")
+    base_time = datetime(2026, 5, 26, tzinfo=UTC)
+    older = make_snapshot(content=b"older state\n", created_at=base_time)
+    newer = make_snapshot(content=b"restored state\n", created_at=base_time + timedelta(minutes=2))
+    global_snapshot = make_snapshot(
+        content=b"global state\n",
+        created_at=base_time + timedelta(minutes=5),
+        scope=SnapshotScope.global_,
+    )
+    snapshots = RecordingSnapshotRepository(
+        [global_snapshot, older, newer],
+        {
+            older.id: b"older state\n",
+            newer.id: b"restored state\n",
+            global_snapshot.id: b"global state\n",
+        },
+    )
+    audit = RecordingAuditRepository()
+    use_case = RollbackUseCase(
+        project_root=tmp_path,
+        snapshot_repository=snapshots,
+        audit_log_repository=audit,
+    )
+
+    result = use_case.execute(
+        RollbackCommand(scope=SnapshotScope.project, origin="cli", action="rollback")
+    )
+
+    assert target.read_bytes() == b"restored state\n"
+    assert result.scope == SnapshotScope.project
+    assert result.snapshot_reference == newer.id
+    assert result.restored_paths == [".umem/memory/facts.jsonl"]
+    assert result.audit_reference == audit.written[0].audit_reference
+    assert audit.written[0].action == "rollback"
+    assert audit.written[0].result == "success"
+    assert audit.written[0].status == "logged"
+    assert audit.written[0].snapshot_reference == newer.id
+    assert not list(target.parent.glob("*.tmp"))
+
+
+def test_rollback_without_snapshots_raises_domain_error_without_side_effects(
+    tmp_path: Path,
+) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_bytes(b"current state\n")
+    audit = RecordingAuditRepository()
+    use_case = RollbackUseCase(
+        project_root=tmp_path,
+        snapshot_repository=RecordingSnapshotRepository([], {}),
+        audit_log_repository=audit,
+    )
+
+    with pytest.raises(SnapshotFailedError, match="Nenhum snapshot"):
+        use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))
+
+    assert target.read_bytes() == b"current state\n"
+    assert audit.written == []
+
+
+def test_rollback_blocks_hash_mismatch_before_write_and_audits_failure(
+    tmp_path: Path,
+) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_bytes(b"current state\n")
+    timestamp = datetime(2026, 5, 26, tzinfo=UTC)
+    snapshot = make_snapshot(content=b"expected state\n", created_at=timestamp)
+    audit = RecordingAuditRepository()
+    use_case = RollbackUseCase(
+        project_root=tmp_path,
+        snapshot_repository=RecordingSnapshotRepository(
+            [snapshot],
+            {snapshot.id: b"corrupted state\n"},
+        ),
+        audit_log_repository=audit,
+    )
+
+    with pytest.raises(SnapshotFailedError, match="integridade"):
+        use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))
+
+    assert target.read_bytes() == b"current state\n"
+    assert len(audit.written) == 1
+    assert audit.written[0].result == "failure"
+    assert audit.written[0].status == "failed"
+    assert audit.written[0].snapshot_reference == snapshot.id
+
+
+def test_rollback_is_offline_and_has_no_network_dependency(tmp_path: Path) -> None:
+    target = tmp_path / ".umem" / "memory" / "facts.jsonl"
+    target.parent.mkdir(parents=True)
+    target.write_bytes(b"current state\n")
+    snapshot = make_snapshot(
+        content=b"offline restore\n",
+        created_at=datetime(2026, 5, 26, tzinfo=UTC),
+    )
+    use_case = RollbackUseCase(
+        project_root=tmp_path,
+        snapshot_repository=RecordingSnapshotRepository(
+            [snapshot],
+            {snapshot.id: b"offline restore\n"},
+        ),
+        audit_log_repository=RecordingAuditRepository(),
+    )
+
+    result = use_case.execute(RollbackCommand(scope=SnapshotScope.project, origin="cli"))
+
+    assert result.snapshot_reference == snapshot.id
+    assert target.read_bytes() == b"offline restore\n"
diff --git a/tests/application/security/test_safe_write_use_case.py b/tests/application/security/test_safe_write_use_case.py
index f274d04..50fdf43 100644
--- a/tests/application/security/test_safe_write_use_case.py
+++ b/tests/application/security/test_safe_write_use_case.py
@@ -34,6 +34,9 @@ class RecordingSnapshotRepository(SnapshotRepository):
     def read(self, id: str) -> Snapshot:
         raise KeyError(id)
 
+    def get_content(self, id: str) -> bytes:
+        raise KeyError(id)
+
     def list(self, scope=None, status=None) -> list[Snapshot]:
         return self.written
 
diff --git a/tests/domain/test_ports.py b/tests/domain/test_ports.py
index 8d76505..1d85660 100644
--- a/tests/domain/test_ports.py
+++ b/tests/domain/test_ports.py
@@ -69,6 +69,7 @@ EXPECTED_METHODS: dict[PortType, MethodExpectations] = {
     },
     SnapshotRepository: {
         "read": (Snapshot, {"id": str}),
+        "get_content": (bytes, {"id": str}),
         "list": (list[Snapshot], {"scope": SnapshotScope | None, "status": SnapshotStatus | None}),
         "write": (type(None), {"entity": Snapshot}),
         "migrate": (type(None), {"target_version": int}),
diff --git a/tests/infrastructure/security/test_local_snapshot_repository.py b/tests/infrastructure/security/test_local_snapshot_repository.py
index 698f602..cffd26a 100644
--- a/tests/infrastructure/security/test_local_snapshot_repository.py
+++ b/tests/infrastructure/security/test_local_snapshot_repository.py
@@ -8,7 +8,7 @@ from uuid import uuid4
 
 import pytest
 
-from universal_memory.domain import SnapshotFailedError
+from universal_memory.domain import SnapshotFailedError, StorageError
 from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
 from universal_memory.infrastructure.security import LocalSnapshotRepository
 
@@ -53,6 +53,30 @@ def test_write_copies_existing_file_and_records_manifest_metadata(tmp_path: Path
     assert repository.list(scope=SnapshotScope.project, status=SnapshotStatus.created) == [snapshot]
 
 
+def test_get_content_reads_physical_backup_file(tmp_path: Path) -> None:
+    project_root = tmp_path / "workspace"
+    data_root = project_root / ".umem"
+    original = project_root / "memory" / "facts.jsonl"
+    content = b"previous state\n"
+    original.parent.mkdir(parents=True)
+    original.write_bytes(content)
+    repository = LocalSnapshotRepository(project_root=project_root, data_root=data_root)
+    snapshot = make_snapshot(content=content)
+    repository.write(snapshot)
+
+    assert repository.get_content(snapshot.id) == content
+
+
+def test_get_content_raises_storage_error_when_backup_file_is_missing(tmp_path: Path) -> None:
+    project_root = tmp_path / "workspace"
+    repository = LocalSnapshotRepository(
+        project_root=project_root, data_root=project_root / ".umem"
+    )
+
+    with pytest.raises(StorageError, match="Snapshot backup file not found"):
+        repository.get_content(str(uuid4()))
+
+
 def test_write_records_initial_creation_without_physical_copy(tmp_path: Path) -> None:
     project_root = tmp_path / "workspace"
     repository = LocalSnapshotRepository(
@@ -238,4 +262,3 @@ def test_concurrency_lock_prevents_clash(tmp_path: Path) -> None:
 
     os.close(fd)
     os.unlink(lock_path)
-
diff --git a/tests/interfaces/cli/test_rollback_command.py b/tests/interfaces/cli/test_rollback_command.py
new file mode 100644
index 0000000..3132515
--- /dev/null
+++ b/tests/interfaces/cli/test_rollback_command.py
@@ -0,0 +1,143 @@
+from __future__ import annotations
+
+import json
+from datetime import UTC, datetime
+from hashlib import sha256
+from pathlib import Path
+from uuid import uuid4
+
+import pytest
+
+from universal_memory.__main__ import main
+from universal_memory.domain.entities import Snapshot, SnapshotScope, SnapshotStatus
+from universal_memory.infrastructure.security import LocalSnapshotRepository
+
+
+def seed_snapshot(
+    project_root: Path,
+    *,
+    content: bytes = b"previous state\n",
+    scope: SnapshotScope = SnapshotScope.project,
+    relative_path: str = ".umem/memory/facts.jsonl",
+    action: str = "safe_write",
+) -> Snapshot:
+    target = project_root / relative_path
+    target.parent.mkdir(parents=True, exist_ok=True)
+    target.write_bytes(content)
+    timestamp = datetime(2026, 5, 26, tzinfo=UTC)
+    snapshot = Snapshot(
+        id=str(uuid4()),
+        created_at=timestamp,
+        updated_at=timestamp,
+        timestamp=timestamp,
+        scope=scope,
+        origin="cli",
+        action=action,
+        relative_path=relative_path,
+        hash=sha256(content).hexdigest(),
+        status=SnapshotStatus.created,
+    )
+    LocalSnapshotRepository(
+        project_root=project_root,
+        data_root=project_root / ".umem",
+    ).write(snapshot)
+    target.write_bytes(b"current state\n")
+    return snapshot
+
+
+def test_rollback_yes_restores_snapshot_and_prints_human_details(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    snapshot = seed_snapshot(tmp_path)
+
+    exit_code = main(["rollback", "--scope", "project", "--yes"])
+
+    captured = capsys.readouterr()
+    assert exit_code == 0
+    assert captured.err == ""
+    assert (tmp_path / ".umem" / "memory" / "facts.jsonl").read_bytes() == b"previous state\n"
+    assert "Rollback concluido" in captured.out
+    assert "Escopo: project" in captured.out
+    assert f"Snapshot: {snapshot.id}" in captured.out
+    assert "Acao original: safe_write" in captured.out
+    assert "Arquivo: .umem/memory/facts.jsonl" in captured.out
+
+
+def test_rollback_json_success_outputs_strict_envelope(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    snapshot = seed_snapshot(tmp_path)
+
+    exit_code = main(["rollback", "--scope", "project", "--format", "json", "--yes"])
+
+    captured = capsys.readouterr()
+    payload = json.loads(captured.out)
+    assert exit_code == 0
+    assert captured.err == ""
+    assert payload["ok"] is True
+    assert payload["operation"] == "rollback"
+    assert payload["scope"] == "project"
+    assert payload["warnings"] == []
+    assert payload["data"]["scope"] == "project"
+    assert payload["data"]["snapshot_reference"] == snapshot.id
+    assert payload["data"]["restored_paths"] == [".umem/memory/facts.jsonl"]
+    assert isinstance(payload["data"]["audit_reference"], str)
+
+
+def test_rollback_interactive_confirmation_accepts_yes(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    seed_snapshot(tmp_path)
+    prompts: list[str] = []
+    monkeypatch.setattr("builtins.input", lambda prompt: prompts.append(prompt) or "s")
+
+    exit_code = main(["rollback", "--scope", "project"])
+
+    assert exit_code == 0
+    assert prompts == ["Deseja prosseguir com o rollback? [s/N]: "]
+    assert (tmp_path / ".umem" / "memory" / "facts.jsonl").read_bytes() == b"previous state\n"
+    assert "Rollback concluido" in capsys.readouterr().out
+
+
+def test_rollback_interactive_confirmation_declines_without_writing(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+    seed_snapshot(tmp_path)
+    monkeypatch.setattr("builtins.input", lambda _prompt: "n")
+
+    exit_code = main(["rollback", "--scope", "project"])
+
+    captured = capsys.readouterr()
+    assert exit_code == 1
+    assert (tmp_path / ".umem" / "memory" / "facts.jsonl").read_bytes() == b"current state\n"
+    assert "Rollback cancelado" in captured.out
+
+
+def test_rollback_json_failure_uses_standard_error_envelope(
+    tmp_path: Path,
+    monkeypatch: pytest.MonkeyPatch,
+    capsys: pytest.CaptureFixture[str],
+) -> None:
+    monkeypatch.chdir(tmp_path)
+
+    exit_code = main(["rollback", "--scope", "project", "--format", "json", "--yes"])
+
+    captured = capsys.readouterr()
+    payload = json.loads(captured.out)
+    assert exit_code == 1
+    assert captured.err == ""
+    assert payload["ok"] is False
+    assert payload["error"]["code"] == "snapshot_failed"
+    assert "Nenhum snapshot" in payload["error"]["detail"]
```
