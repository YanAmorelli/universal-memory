# Story 2.5: Reverter Última Mutação por Escopo

Status: done

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

### Review Findings

- [x] [Review][Decision] Inconsistência transacional entre a alteração física de arquivos e o registro de auditoria — A escrita de arquivos físicos ocorre antes de persistir o evento de auditoria no log. Se a auditoria falhar (ex: disco cheio), o rollback já mudou o arquivo fisicamente, gerando inconsistência transacional no use case.
- [x] [Review][Decision] Snapshot restaurado permanece com status 'created' na persistência — O status do snapshot restaurado nunca é atualizado para `SnapshotStatus.restored` pós-rollback, deixando o enum sem uso e o snapshot listável como 'created'. Se marcarmos como `restored`, ele não poderá ser usado em novos rollbacks, o que afeta regras de negócio de mutabilidade múltipla.
- [x] [Review][Decision] Log de auditoria física sem campo para persistência de evidências de falha de integridade — O AC 3 exige salvar "evidências suficientes da falha de integridade no log". O modelo `AuditEvent` não prevê detalhes ou payload extras para guardar tais dados, exigindo alteração no modelo de domínio de auditoria.
- [x] [Review][Patch] Divergência de fuso horário e ordenação na seleção do snapshot mais recente [src/universal_memory/bootstrap/cli.py:54]
- [x] [Review][Patch] Vulnerabilidade de Path Traversal no repositório de snapshots [src/universal_memory/infrastructure/security/local_snapshot_repository.py:88]
- [x] [Review][Patch] Travamento por EOFError e KeyboardInterrupt na interação humana do CLI [src/universal_memory/interfaces/cli/init_command.py:301]
- [x] [Review][Patch] Bypass da confirmação interativa de rollback no formato JSON sem a flag --yes [src/universal_memory/interfaces/cli/init_command.py:298]
- [x] [Review][Patch] Perda permanente de permissões especiais do arquivo de destino pós-rollback [src/universal_memory/application/security/rollback_use_case.py:110]
- [x] [Review][Patch] Validação de segurança burla no Path de destino por TOCTOU e retorno não resolvido [src/universal_memory/application/security/rollback_use_case.py:100]
- [x] [Review][Patch] Exceção `StorageError` de leitura do backup desprotegida e sem auditoria de falha [src/universal_memory/application/security/rollback_use_case.py:60]
- [x] [Review][Patch] Mensagem de 'recovery_hint' genérica e incorreta no envelope JSON de erro [src/universal_memory/interfaces/cli/init_command.py:503]
- [x] [Review][Patch] Captura genérica de 'BaseException' interceptando sinais vitais do interpretador [src/universal_memory/application/security/rollback_use_case.py:78]
- [x] [Review][Patch] Risco de OOM (Out of Memory) com carregamento total em memória para cálculo de Hash [src/universal_memory/application/security/rollback_use_case.py:60]
- [x] [Review][Patch] Lacuna de cobertura de testes para rollback quando o arquivo original foi excluído [tests/application/security/test_rollback_use_case.py:1]

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
