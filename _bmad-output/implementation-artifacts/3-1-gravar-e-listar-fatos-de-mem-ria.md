# Story 3.1: Gravar e Listar Fatos de Memória

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário ou agente que trabalha em um projeto,  
eu quero gravar e listar fatos de memória por escopo,  
para que o contexto relevante fique disponível para sessões futuras sem reexplicação.

## Acceptance Criteria

1. **Dado** os repositories e modelos de domínio do Epic 1,  
   **Quando** um fato válido é gravado por use case,  
   **Então** ele é persistido com `schema_version`, `id`, `created_at`, `updated_at`, `scope`, `status`, `source`, `tags` e `metadata`.

2. **Dado** o pipeline seguro de mutação do Epic 2,  
   **Quando** a gravação é executada,  
   **Então** a escrita passa pelo `SafeWriteUseCase` para garantir que o conteúdo passe pelo scanner de segredos, tire snapshot pré-mutação e registre auditoria completa de sucesso ou bloqueio.

3. **Dado** fatos persistidos nos escopos `project` e `global`,  
   **Quando** o usuário lista fatos,  
   **Então** o sistema retorna apenas os fatos compatíveis com o filtro solicitado (escopo e/ou status),  
   **E** preserva a separação lógica entre Short Term Memory (STM) e Universal Memory (LTM).

4. **Dado** que não existem fatos no escopo ou status solicitado,  
   **Quando** a listagem é executada,  
   **Then** o sistema retorna uma lista vazia explícita,  
   **And** não trata a ausência de fatos como um erro.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes RED para o repositório de infraestrutura `LocalFactRepository`** (AC: 1, 3, 4)
  - [x] Criar arquivo de teste `tests/infrastructure/storage/test_local_fact_repository.py`.
  - [x] Cobrir inicialização de `LocalFactRepository` recebendo caminhos para os arquivos locais de armazenamento.
  - [x] Cobrir método `list()` filtrando fatos por `scope` e `status`.
  - [x] Cobrir método `read()` buscando fato por ID e lançando `FactNotFoundError` caso não exista.
  - [x] Cobrir método `write()` adicionando ou atualizando um fato diretamente (para suporte direto na infraestrutura).
  - [x] Cobrir método `delete()` marcando um fato com soft delete (`FactStatus.archived` ou `FactStatus.stale`).
  - [x] Cobrir método `purge()` removendo permanentemente o fato física/estruturalmente.
  - [x] Cobrir comportamento de listagem vazia explícita quando o arquivo não existe ou está vazio.

- [x] **Task 2: Implementar `LocalFactRepository` na camada de infraestrutura** (AC: 1, 3, 4)
  - [x] Criar diretório `src/universal_memory/infrastructure/storage/` se não existir.
  - [x] Criar `src/universal_memory/infrastructure/storage/__init__.py`.
  - [x] Criar `src/universal_memory/infrastructure/storage/local_fact_repository.py` herdando da interface `FactRepository`.
  - [x] Implementar leitura e escrita em `.umem/memory/facts.jsonl` de forma síncrona e resiliente.
  - [x] Tratar corrupção de linhas no parsing usando validação Pydantic de cada linha individualmente.
  - [x] Garantir que o repositório lance exceções específicas de negócio (`FactNotFoundError`, `StorageError`) em vez de erros brutos do sistema operacional.

- [x] **Task 3: Escrever testes RED para os Use Cases de aplicação (`RememberFactUseCase` e `ListFactsUseCase`)** (AC: 1, 2, 3, 4)
  - [x] Criar arquivo de teste `tests/application/memory/test_memory_use_cases.py`.
  - [x] Cobrir `RememberFactUseCase` validando que a gravação orquestra com `SafeWriteUseCase` para persistir as alterações através do pipeline seguro de mutação.
  - [x] Testar bloqueio de fato contendo segredos (credenciais AWS, PAT GitHub, etc.), garantindo que o scanner dispare `SecretDetectedError` e impeça a persistência, enquanto gera auditoria segura de "blocked".
  - [x] Cobrir `ListFactsUseCase` validando o carregamento correto através de `FactRepository` e aplicando os filtros adequadamente.

- [x] **Task 4: Implementar Use Cases de Memória na camada de aplicação** (AC: 1, 2, 3, 4)
  - [x] Criar diretório `src/universal_memory/application/memory/`.
  - [x] Criar `src/universal_memory/application/memory/__init__.py`.
  - [x] Criar `src/universal_memory/application/memory/remember_fact_use_case.py` com o comando estruturado e fluxo seguro de mutação.
  - [x] Criar `src/universal_memory/application/memory/list_facts_use_case.py` expondo a listagem e filtros seguros.
  - [x] Garantir acoplamento correto com `SafeWriteUseCase` injetado pelo construtor (Dependency Injection).

- [x] **Task 5: Integrar os novos Use Cases no Bootstrap do sistema**
  - [x] Atualizar `src/universal_memory/bootstrap/cli.py` se necessário para mapear e preparar a injeção do repositório local e dos novos use cases na CLI futura.

- [x] **Task 6: Fechar em GREEN com verificação de qualidade e regressão**
  - [x] Executar `uv run pytest` e validar que 100% dos testes passam sem erros.
  - [x] Executar `uv run ruff check .` para validação de estilo e regras.
  - [x] Executar `uv run pyright` para validação estática de tipagem estrita.

### Review Findings

- [x] [Review][Decision] Separation of Universal Memory (LTM) Global Storage Path — Resolvido: Fatos de escopo global salvos em `~/.umem/memory/facts.jsonl` (home do usuário) e fatos locais do projeto em `.umem/memory/facts.jsonl` (diretório local).
- [x] [Review][Patch] Race Condition in RememberFactUseCase (Read-Modify-Write unprotected) [src/universal_memory/application/memory/remember_fact_use_case.py:47-70]
- [x] [Review][Patch] TOCTOU and Lock Stealing in Lock Mechanism [src/universal_memory/infrastructure/storage/local_fact_repository.py:40-73]
- [x] [Review][Patch] Direct Repository Modifying Methods Bypass SafeWriteUseCase [src/universal_memory/infrastructure/storage/local_fact_repository.py:87]
- [x] [Review][Patch] Concurrent Soft Delete Race Condition [src/universal_memory/infrastructure/storage/local_fact_repository.py:98-103]
- [x] [Review][Patch] Silent Permanent Data Loss on JSONL Line Corruption [src/universal_memory/infrastructure/storage/local_fact_repository.py:129-137]
- [x] [Review][Patch] Indiscriminate DateTime Suffix Normalization Corrupts User Content [src/universal_memory/application/memory/remember_fact_use_case.py:81-89]
- [x] [Review][Patch] Leaky Abstractions and Hardcoded Storage Paths in Use Cases [src/universal_memory/application/memory/remember_fact_use_case.py:78]
- [x] [Review][Patch] Duplicated Serializer and Normalizer Rules [src/universal_memory/application/memory/remember_fact_use_case.py:78]

## Dev Notes

- **Escopo desta story:** Foco exclusivo na camada de domínio, infraestrutura e use cases de aplicação para gravar e listar fatos de memória. A interface do usuário final (Typer CLI commands como `umem remember` ou `umem facts list` e FastMCP tools equivalentes) pertencerá às histórias do Épico 4.
- **Pipeline Seguro do Épico 2:** O pipeline de escrita segura `SafeWriteUseCase` já está implementado e deve ser obrigatoriamente utilizado. Ele já lida com:
  - Scanner de segredos offline via `SecretScannerPort` (lanca `SecretDetectedError`).
  - Snapshots automáticos de rollback via `SnapshotRepository`.
  - Escrita atômica em arquivos com substituição atômica de arquivo temporário.
  - Log auditável local via `AuditLogRepository`.
- **Formato do Arquivo de Fatos:** Os fatos devem ser gravados em `.umem/memory/facts.jsonl` sob a forma de JSON Lines (um JSON válido por linha) representando cada instância de `Fact` serializada.

### Project Structure Notes

- A criação do diretório `infrastructure/storage/` e arquivo `local_fact_repository.py` segue as diretrizes da arquitetura limpa acordadas em `architecture.md`.
- Os Use Cases devem viver em `application/memory/` e respeitar a barreira de dependência (sem importar nada de `infrastructure` ou `interfaces`).

### References

- `_bmad-output/planning-artifacts/prd.md` (FR1, FR2, FR22, FR23, FR25)
- `_bmad-output/planning-artifacts/architecture.md` (Core Memory Management, Clean Architecture, Structure Mapping, Mutation Pipeline)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (remember fact, list facts, error mappings)
- `src/universal_memory/application/security/safe_write_use_case.py`
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/domain/entities/fact.py`

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash

### Debug Log References

- 2026-05-26: Inicializada a criação da Story 3.1 com análise aprofundada dos épicos, arquitetura e especificações de interação.
- 2026-05-26: Identificados os padrões vigentes do Épico 2 para auditorias e snapshots locais seguros.
- 2026-05-26: Estruturada a modelagem de tarefas com TDD e isolamento estrito de camadas.
- 2026-05-26: Criados testes RED para `LocalFactRepository`; falha inicial confirmou ausência do pacote `infrastructure.storage`.
- 2026-05-26: Implementado `LocalFactRepository` com JSONL, filtros, soft delete, purge, skip resiliente de linhas inválidas e erros tipados.
- 2026-05-26: Criados testes RED para `RememberFactUseCase` e `ListFactsUseCase`; falha inicial confirmou ausência do pacote `application.memory`.
- 2026-05-26: Implementados use cases de memória com DI de `FactRepository` e `SafeWriteUseCase`, mantendo comandos CLI finais fora do escopo desta story.
- 2026-05-26: Validações finais executadas: `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

### Completion Notes List

- Story context created for offline local fact storage.
- SafeWriteUseCase integrated as a mandatory dependency for the fact modification flow to satisfy security auditing requirements.
- JSON Lines formats and exceptions mapped securely.
- Implementado `LocalFactRepository` para `.umem/memory/facts.jsonl`, com leitura/listagem vazia explícita, filtros por `scope` e `status`, `read`, `write`, `delete` lógico via `archived`, `purge` físico e tratamento de corrupção por linha.
- Implementados `RememberFactUseCase` e `ListFactsUseCase`; gravação de fatos cria `Fact` completo e persiste o conteúdo por `SafeWriteUseCase`, garantindo scanner, snapshot e auditoria de sucesso ou bloqueio.
- O bootstrap da CLI não foi alterado porque a story limita a entrega às camadas de domínio/infra/aplicação; comandos `umem remember` e `umem facts list` estão explicitamente reservados para o Épico 4.
- Testes adicionados/atualizados cobrem infraestrutura, use cases, bloqueio por segredo, filtros e listagem vazia.
- Verificações finais passaram: `uv run pytest` (143 passed), `uv run ruff check .`, `uv run pyright`.

### File List

- `_bmad-output/implementation-artifacts/3-1-gravar-e-listar-fatos-de-mem-ria.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/memory/__init__.py`
- `src/universal_memory/application/memory/list_facts_use_case.py`
- `src/universal_memory/application/memory/remember_fact_use_case.py`
- `src/universal_memory/infrastructure/storage/__init__.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `tests/application/memory/test_memory_use_cases.py`
- `tests/infrastructure/storage/test_local_fact_repository.py`

### Change Log

- 2026-05-26: Implementada Story 3.1 com repositório local de fatos, use cases de memória e cobertura automatizada completa.
