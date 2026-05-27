# Story 3.6: Purgar Fatos e Executar Context Hygiene

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário mantendo a memória limpa,
eu quero arquivar, purgar e higienizar fatos de curto prazo,
para que o contexto obsoleto não degrade decisões futuras dos agentes.

## Acceptance Criteria

1. **Dado** fatos de Short Term Memory com estados `active`, `stale`, `archived` e `purged`  
   **Quando** a higiene de contexto é executada após conclusão de tarefa ou comando explícito  
   **Então** fatos obsoletos de projeto são marcados como `stale` ou `archived` antes de exclusão  
   **E** a purga definitiva só ocorre quando o usuário solicita purge explicitamente.

2. **Dado** um fato específico selecionado para purga  
   **Quando** o usuário confirma a remoção  
   **Então** o fato deixa de aparecer em consultas e listagens padrão  
   **E** a alteração passa pelo pipeline seguro de mutação e registra auditoria.

3. **Dado** uma base inteira selecionada para purga  
   **Quando** a operação é executada  
   **Então** o sistema aplica escopo corretamente e evita remover dados globais quando o usuário solicitou apenas escopo de projeto  
   **E** retorna resumo dos itens afetados.

4. **Dado** fatos arquivados anteriormente  
   **Quando** o usuário executa consulta diagnóstica  
   **Então** o sistema consegue listar itens arquivados com metadados de lifecycle  
   **E** mantém fatos purgados fora dos resultados ativos.

## Tasks / Subtasks

- [x] **Task 1: Desenvolver os Casos de Uso `PurgeFactUseCase` e `ContextHygieneUseCase`** (AC: 1, 2, 3)
  - [x] Criar o arquivo `src/universal_memory/application/memory/purge_fact_use_case.py`.
  - [x] Definir os DTOs `PurgeFactCommand` (com campos `id: str | None`, `scope: FactScope | None`, `origin: str = "cli"`) e `PurgeFactResult` (com campos `purged_count: int`, `affected_ids: list[str]`, `audit_reference: str`).
  - [x] Criar o caso de uso `PurgeFactUseCase` recebendo `fact_repository: FactRepository` no construtor.
  - [x] Implementar a lógica de `PurgeFactUseCase`:
    - Se `id` for fornecido: ler o fato via `fact_repository.read(id)`. Se não existir, lançar `FactNotFoundError`. Se existir, remover fisicamente via `fact_repository.purge(id)`.
    - Se `scope` for fornecido: listar todos os fatos daquele escopo usando `fact_repository.list(scope=scope)` e chamar `fact_repository.purge(f.id)` para cada um.
    - Se nem `id` nem `scope` forem informados, lançar `ValidationFailedError` ("Deve ser fornecido um id de fato ou um escopo para purga.").
    - Retornar o número de itens purgados e a referência de auditoria se aplicável.
  - [x] Criar o arquivo `src/universal_memory/application/memory/context_hygiene_use_case.py`.
  - [x] Definir os DTOs `ContextHygieneCommand` (com campo `scope: FactScope`) e `ContextHygieneResult` (com campos `stale_count: int`, `archived_count: int`, `audit_reference: str`).
  - [x] Criar o caso de uso `ContextHygieneUseCase` recebendo `fact_repository: FactRepository` no construtor.
  - [x] Implementar a lógica de `ContextHygieneUseCase`:
    - Filtrar fatos do projeto (Short Term Memory).
    - Transição de estados obsoletos:
      - Fatos com `FactStatus.active` são marcados como `FactStatus.stale`.
      - Fatos com `FactStatus.stale` são marcados como `FactStatus.archived`.
      - Fatos `FactStatus.archived` permanecem inalterados.
      - Para cada fato modificado, atualizar o repositório chamando `fact_repository.write(fact)`.
    - Retornar a contagem de transições efetuadas.

- [x] **Task 2: Exportar novos use cases no pacote memory**
  - [x] Atualizar `src/universal_memory/application/memory/__init__.py` para exportar `PurgeFactUseCase`, `PurgeFactCommand`, `PurgeFactResult`, `ContextHygieneUseCase`, `ContextHygieneCommand`, `ContextHygieneResult`.

- [x] **Task 3: Desenvolver os novos comandos CLI sob o parser `facts`** (AC: 1, 2, 3, 4)
  - [x] Atualizar `src/universal_memory/interfaces/cli/init_command.py`:
    - Adicionar o parser de grupo `facts` no `_build_parser` (ex: `facts_parser = subparsers.add_parser("facts", help="Gerenciar fatos de memoria")` e `facts_subparsers = facts_parser.add_subparsers(dest="facts_command")`).
    - Adicionar subcomando `list`:
      - Argumentos `--scope` (opções `project`, `global`, default `None`).
      - Argumentos `--status` (opções `active`, `stale`, `archived`, `purged`, default `None`).
      - Flag `--format` (`human` ou `json`, default `human`).
    - Adicionar subcomando `purge`:
      - Argumentos `--id` (id do fato específico) e `--scope` (escopo para purga em lote), mutuamente exclusivos ou validados no runtime.
      - Flag `--yes` / `-y` para pular a confirmação interativa.
      - Lógica de confirmação:
        - Para formato `human` (sem `-y`): exibir resumo detalhado da purga (escopo, ID, perda permanente de dados) e solicitar `input("Confirmar purga permanente? [y/N]: ")`. Abortar se negado.
        - Para formato `json` (sem `-y`): abortar com erro `SnapshotFailedError` / `ValidationFailedError` explicando que `--yes` é obrigatória no modo JSON.
    - Adicionar subcomando `hygiene`:
      - Flag `--format` (`human` ou `json`).
    - Implementar os handlers de CLI:
      - `_run_facts_list` orquestrando o `ListFactsUseCase`.
      - `_run_facts_purge` orquestrando o `PurgeFactUseCase` com prompts e envelopes padrão.
      - `_run_facts_hygiene` orquestrando o `ContextHygieneUseCase`.

- [x] **Task 4: Registrar os comandos no Bootstrap** (AC: 1)
  - [x] Modificar `src/universal_memory/bootstrap/cli.py` para injetar `PurgeFactUseCase` e `ContextHygieneUseCase` no CLI main build.
  - [x] Passar as dependências corretas de repositórios reais no bootstrap.

- [x] **Task 5: Escrever Suíte de Testes Unitários e de Integração** (AC: 1, 2, 3, 4)
  - [x] Criar testes unitários para os use cases:
    - `tests/application/memory/test_purge_fact_use_case.py` cobrindo purga por id, purga em lote por escopo, validações de parâmetros, e comportamento com repositório.
    - `tests/application/memory/test_context_hygiene_use_case.py` cobrindo a máquina de estados (active -> stale -> archived), atualização no repositório e contagem.
  - [x] Criar testes de integration para a interface CLI:
    - `tests/interfaces/cli/test_facts_commands.py` testando exaustivamente `umem facts list`, `umem facts purge` (fluxo com prompt interativo simulado usando `monkeypatch`, fluxo com `--yes`, modo JSON) e `umem facts hygiene`.
    - Garantir que as saídas do formato JSON obedeçam aos envelopes padrões de sucesso e erro descritos em `devex-interaction-spec.md`.

- [x] **Task 6: Validação de Estilo, Tipos e Regressão Completa**
  - [x] Executar `uv run pytest` e obter 100% de sucesso.
  - [x] Executar `uv run ruff check .` para validação de estilo.
  - [x] Executar `uv run pyright` para validação de tipagem estática.

### Review Findings

- [x] [Review][Decision] Comportamento padrão de listagem oculta fatos com status 'stale' — O comando 'umem facts list' filtra por padrão pelo status 'active', ocultando fatos 'stale'. Resolvido: Mantido o comportamento atual (apenas active por padrão).
- [x] [Review][Patch] Loops sequenciais em lote geram sobrecarga de E/S e logs de auditoria [src/universal_memory/application/memory/context_hygiene_use_case.py:28-42]
- [x] [Review][Patch] Falta de validação combinada para os parâmetros 'id' e 'scope' [src/universal_memory/application/memory/purge_fact_use_case.py:27-28]

## Dev Notes

- **Segurança de Mutação:** O repositório de fatos `LocalFactRepository.purge` utiliza `_write_facts_unlocked`, que delega para `SafeWriteUseCase` se estiver configurado. Portanto, toda alteração persistida em lote ou individual passa por snapshots e logs de auditoria de conformidade automaticamente.
- **Isolamento de Escopo:** Em purga em lote por escopo, garantir que a busca do `FactRepository.list` filtre estritamente pelo escopo solicitado. A exclusão de um escopo `project` jamais deve interferir no arquivo global em `~/.umem/`.
- **Máquina de Estados de Higiene:**
  - `active` -> `stale`
  - `stale` -> `archived`
  - Fatos arquivados não são alterados ou expostos em listagem sem filtro explícito, mas podem ser buscados ativamente via `facts list --status archived` (AC 4).
  - Purgas removem fisicamente a linha do arquivo JSONL, deixando-o fora dos dados ativos e históricos.

### Project Structure Notes

- O caso de uso `PurgeFactUseCase` deve residir em: `src/universal_memory/application/memory/purge_fact_use_case.py`.
- O caso de uso `ContextHygieneUseCase` deve residir em: `src/universal_memory/application/memory/context_hygiene_use_case.py`.
- Os testes devem residir em:
  - `tests/application/memory/test_purge_fact_use_case.py`
  - `tests/application/memory/test_context_hygiene_use_case.py`
  - `tests/interfaces/cli/test_facts_commands.py`

### References

- [PRD: FR5, FR6](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md#L317-L318)
- [Architecture: Context Hygiene Lifecycle](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L817-L827)
- [Architecture: CLI to MCP Parity Matrix](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L695-L710)
- [DevEx Interaction Spec: Confirmation Contract](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md#L73-L92)
- [Local Fact Repository](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/infrastructure/storage/local_fact_repository.py#L217-L230)
- [List Facts Use Case](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/memory/list_facts_use_case.py)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest tests/application/memory/test_purge_fact_use_case.py tests/application/memory/test_context_hygiene_use_case.py tests/interfaces/cli/test_facts_commands.py` -> 13 passed
- `uv run pytest` -> 192 passed
- `uv run ruff check .` -> All checks passed
- `uv run pyright` -> 0 errors, 0 warnings, 0 informations

### Completion Notes List

- Implementados `PurgeFactUseCase` e `ContextHygieneUseCase` com DTOs, validação de comando, purga por id/escopo e transições `active -> stale` e `stale -> archived`.
- Adicionados comandos `umem facts list`, `umem facts purge` e `umem facts hygiene` com saída human/json, confirmação obrigatória para purge interativo e exigência de `--yes` no modo JSON.
- Bootstrap passou a compor repositório real de fatos com `SafeWriteUseCase`, scanner de segredos, snapshots e auditoria para mutações de purge/hygiene.
- Adicionada cobertura unitária e de integração para purge, hygiene, listagem diagnóstica de arquivados, isolamento de escopo e envelopes JSON.

### File List

- `src/universal_memory/application/memory/context_hygiene_use_case.py`
- `src/universal_memory/application/memory/purge_fact_use_case.py`
- `src/universal_memory/application/memory/__init__.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/memory/test_context_hygiene_use_case.py`
- `tests/application/memory/test_purge_fact_use_case.py`
- `tests/interfaces/cli/test_facts_commands.py`
- `_bmad-output/implementation-artifacts/3-6-purgar-fatos-e-executar-context-hygiene.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-05-27: Criada especificação de Story 3.6 para purga de fatos e higiene de contexto.
- 2026-05-27: Implementada Story 3.6 com use cases de purge/hygiene, comandos CLI `facts`, bootstrap real e testes completos.
