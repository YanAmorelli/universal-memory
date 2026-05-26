# Story 2.4: Listar Auditoria e Snapshots

Status: done

## Story

Como um usuário auditando alterações automáticas,  
eu quero consultar eventos de auditoria e snapshots disponíveis,  
para que eu entenda o que foi alterado, quando, por qual ação e como posso recuperar o estado anterior.

## Acceptance Criteria

1. **Dado** eventos existentes em `.umem/audit/events.jsonl`
   **Quando** o usuário consulta auditoria por use case ou CLI
   **Então** o sistema lista timestamp, ação, escopo, origem, resultado e referência do snapshot quando existir
   **E** a consulta pode ser feita em menos de 2 comandos a partir do diretório do projeto (ex: `umem audit list`)
   **E** com `--format json`, retorna JSON puro com `events[]` contendo `timestamp`, `action`, `scope`, `origin`, `result`, `snapshot_reference` e `audit_reference`
   **E** a saída segue a especificação definida em `_bmad-output/planning-artifacts/devex-interaction-spec.md`

2. **Dado** snapshots existentes em `.umem/snapshots/`
   **Quando** o usuário lista snapshots
   **Então** o sistema mostra timestamp, escopo, origem, ação responsável, caminho relativo e hash
   **E** a saída humana é legível e a saída estruturada é adequada para automação futura
   **E** com `--format json`, retorna JSON puro com `snapshots[]` contendo `timestamp`, `scope`, `origin`, `action`, `relative_path`, `hash` e `manifest_path`

3. **Dado** não há eventos ou snapshots
   **Quando** o usuário executa as consultas
   **Então** o sistema retorna estado vazio de forma explícita
   **E** não trata a ausência de dados como erro
   **E** com `--format json`, retorna listas vazias em `events` ou `snapshots`, sem texto Rich/ansi misturado

## Tasks / Subtasks

- [x] **Task 1: Escrever testes unitários (RED) para os Use Cases de consulta** (AC: 1, 2, 3)
  - [x] Criar `tests/application/security/test_list_audit_log_use_case.py` cobrindo a listagem de eventos com e sem filtro de escopo.
  - [x] Criar `tests/application/security/test_list_snapshots_use_case.py` cobrindo a listagem de snapshots com e sem filtro de escopo e status.
  - [x] Garantir que ambos os use cases retornem listas vazias se os dados não existirem, sem lançar exceções.

- [x] **Task 2: Implementar os Use Cases de consulta no Application Layer** (AC: 1, 2, 3)
  - [x] Criar `src/universal_memory/application/security/list_audit_log_use_case.py` contendo a classe `ListAuditLogUseCase` que usa `AuditLogRepository`.
  - [x] Criar `src/universal_memory/application/security/list_snapshots_use_case.py` contendo a classe `ListSnapshotsUseCase` que usa `SnapshotRepository`.
  - [x] Exportar ambos os use cases e seus respectivos commands/results em `src/universal_memory/application/security/__init__.py`.

- [x] **Task 3: Escrever testes unitários e de integração (RED) para a CLI** (AC: 1, 2, 3)
  - [x] Criar `tests/interfaces/cli/test_list_commands.py` para cobrir a execução de `umem audit list` e `umem snapshots list` nas versões human e json.
  - [x] Testar cenários com banco de dados de teste contendo múltiplos eventos e snapshots, garantindo ordenação cronológica adequada.
  - [x] Testar cenários de estado vazio (quando não há eventos ou snapshots), validando o retorno de JSON com arrays vazios.

- [x] **Task 4: Implementar subparsers e handlers no CLI Adapter** (AC: 1, 2)
  - [x] Modificar `src/universal_memory/interfaces/cli/init_command.py` para adicionar os subparsers de `audit` e `snapshots` com a ação `list`.
  - [x] Adicionar suporte ao argumento `--format` (human ou json) e ao filtro opcional `--scope` (project ou global) nos comandos de listagem.
  - [x] Integrar injeção de dependências para injetar `LocalAuditLogRepository` e `LocalSnapshotRepository` nos use cases dentro de `bootstrap/cli.py` e passar os handlers de execução de forma limpa.

- [x] **Task 5: Garantir conformidade rigorosa com DevEx Interaction Specification** (AC: 1, 2, 3)
  - [x] Assegurar que `--format json` retorne o envelope padrão de sucesso do `devex-interaction-spec.md` (`"ok": true, "operation": "audit", "scope": "project", "data": {"events": [...]}, "warnings": []}` e `"operation": "snapshots"`, respectivamente).
  - [x] Certificar-se de que a formatação `human` é concisa e limpa.
  - [x] Tratar ausência de dados retornando uma mensagem clara amigável na saída humana (ex: "Nenhum evento de auditoria encontrado.") e sem misturar Rich markup com saída pura de JSON sob `--format json`.

- [x] **Task 6: Verificação de qualidade final e regressões** (AC: 1, 2, 3)
  - [x] Executar toda a suíte de testes usando `.venv/bin/pytest`.
  - [x] Garantir linting limpo rodando `.venv/bin/ruff check .`.
  - [x] Garantir tipagem estrita sem erros rodando `.venv/bin/pyright`.

## Dev Notes

- **Escopo desta story:** Foco total em leitura e exibição estruturada e humana dos dados. Nenhuma mutação ou escrita deve ocorrer nestes comandos.
- **Acoplamento Arquitetural:** CLI chama use cases de aplicação, que acessam repositories (ports no domínio, implementados em infraestrutura). A injeção de dependência deve ser centralizada no Composition Root (`src/universal_memory/bootstrap/cli.py`).
- **Segurança de Segredos:** Por mais que estas sejam operações de leitura, garanta que caminhos ou dados de configuração sensíveis nunca sejam expostos e que nenhuma parte das strings de metadados em auditorias contenha segredos brutos.

### Project Structure Notes

- Os Use Cases devem morar na pasta `src/universal_memory/application/security/`.
- Os testes devem ser estruturados em `tests/application/security/` e `tests/interfaces/cli/`.
- Seguir o padrão de nomenclatura snake_case para propriedades JSON.

### References

- `_bmad-output/planning-artifacts/epics.md#Story 2.4` (Critérios de aceitação de listagem de auditoria e snapshots)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md#umem audit list` e `umem snapshots list` (Envelope de saída JSON, formato de dados)
- `src/universal_memory/domain/ports/audit_log_repository.py` (Assinatura do Port de Auditoria)
- `src/universal_memory/domain/ports/snapshot_repository.py` (Assinatura do Port de Snapshots)
- `src/universal_memory/infrastructure/security/local_audit_log_repository.py`
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-26: Story `2-4-listar-auditoria-e-snapshots` identificada a partir do `sprint-status.yaml` como a próxima história pendente (backlog).
- 2026-05-26: Análise profunda do contrato de port `AuditLogRepository` e `SnapshotRepository`, bem como das especificações do `devex-interaction-spec.md`.
- 2026-05-26: Estruturação das tarefas detalhadas seguindo a metodologia TDD (testes unitários RED primeiro).
- 2026-05-26: RED confirmado com falhas de import para os use cases ainda inexistentes.
- 2026-05-26: GREEN confirmado com 12 testes focados passando para use cases e CLI.
- 2026-05-26: Regressão completa confirmada com 118 testes passando; `ruff` e `pyright` limpos.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- Implementados `ListAuditLogUseCase` e `ListSnapshotsUseCase` com DTOs de consulta ordenados e filtros por escopo/status.
- Adicionados comandos `umem audit list` e `umem snapshots list` com saída humana concisa e JSON puro no envelope DevEx.
- Snapshots agora carregam `origin` com fallback `unknown` para dados legados e `SafeWriteUseCase` persiste a origem de novas mutações.
- Configurado `pyright` para usar a `.venv`, mantendo a checagem de tipos executável pelo comando exigido da story.
- Validações executadas: `.venv/bin/pytest` (118 passed), `.venv/bin/ruff check .` (passed), `.venv/bin/pyright` (0 errors).

### File List

- `_bmad-output/implementation-artifacts/2-4-listar-auditoria-e-snapshots.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `pyproject.toml`
- `src/universal_memory/application/security/__init__.py`
- `src/universal_memory/application/security/list_audit_log_use_case.py`
- `src/universal_memory/application/security/list_snapshots_use_case.py`
- `src/universal_memory/application/security/safe_write_use_case.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/domain/entities/snapshot.py`
- `src/universal_memory/infrastructure/security/local_audit_log_repository.py`
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/security/test_list_audit_log_use_case.py`
- `tests/application/security/test_list_snapshots_use_case.py`
- `tests/interfaces/cli/test_list_commands.py`
- `tests/interfaces/test_adapter_mutation_guardrails.py`

### Change Log

- 2026-05-26: Implementada a story 2.4 com listagem de auditoria/snapshots, contratos CLI JSON/human e validações completas.

### Review Findings

- [x] [Review][Patch] ValidationError não capturado na CLI [src/universal_memory/interfaces/cli/init_command.py:653]
- [x] [Review][Patch] Duplicação do helper _format_utc [src/universal_memory/application/security/list_audit_log_use_case.py:264]
- [x] [Review][Patch] Acoplamento de manifest_path na camada de aplicação [src/universal_memory/application/security/list_snapshots_use_case.py:286]
- [x] [Review][Defer] STALE_LOCK_SECONDS estático de 10.0 segundos [src/universal_memory/infrastructure/security/local_audit_log_repository.py:34] — deferred, pre-existing
- [x] [Review][Defer] Leitura concorrente de auditoria sem lock [src/universal_memory/infrastructure/security/local_audit_log_repository.py:102] — deferred, pre-existing

