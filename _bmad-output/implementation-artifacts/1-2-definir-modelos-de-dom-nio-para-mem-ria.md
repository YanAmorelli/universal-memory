# Story 1.2: Definir Modelos de Domínio para Memória

Status: done

## Story

Como um agente ou adapter que usa a memória,
eu quero modelos de domínio validados para fatos, regras, skills latentes, snapshots, auditoria e resumos de contexto,
para que todos os componentes compartilhem contratos consistentes de dados.

## Acceptance Criteria

1. **Dado** que os testes de domínio são escritos primeiro (TDD),
   **Quando** os modelos Pydantic v2 são implementados,
   **Então** cada entidade persistível contém obrigatoriamente os atributos `schema_version` (inteiro), `id` (UUID v4 como string), `created_at` (timestamp ISO 8601 UTC), `updated_at` (timestamp ISO 8601 UTC), `scope` (enum) e `status` (enum ou string).
   **E** todos os campos serializados em JSON seguem o padrão `snake_case`, as chaves de enums utilizam `lowercase_snake` e booleanos são representados de forma nativa JSON (`true`/`false`).

2. **Dado** entradas inválidas para as entidades de domínio (como IDs que não são UUIDs válidos, timestamps corrompidos ou tipos incompatíveis),
   **Quando** a validação do modelo Pydantic é executada,
   **Então** os dados inválidos são sumariamente rejeitados com erros de validação tipados e testáveis (`pydantic.ValidationError`).

3. **Dado** o ciclo de ciclo de vida de Short Term Memory (STM),
   **Quando** o status de um Fato é avaliado,
   **Então** o sistema suporta explicitamente os estados: `active`, `stale`, `archived` e `purged`.

4. **Dado** a necessidade de consistência nos dados de auditoria, snapshots e resumos de contexto,
   **Quando** as entidades correspondentes são instanciadas,
   **Então** o modelo de Auditoria (`AuditEvent`) contém `timestamp`, `action`, `scope`, `origin`, `result`, `snapshot_reference` e `audit_reference`.
   **E** o modelo de Snapshot contém `timestamp`, `scope`, `action` (responsável), `relative_path` e `hash` (SHA-256 do arquivo anterior).
   **E** o modelo de Resumo de Contexto (`ContextSummary`) diferencia claramente `project_summary`, `universal_preferences` e `active_rules`, além de conter a `audit_reference` correspondente.

## Tasks / Subtasks

- [x] **Task 1: Escrever os Testes de Domínio Primeiro (TDD)** (AC: 1, 2, 3, 4)
  - [x] Criar o arquivo `tests/domain/test_entities.py`.
  - [x] Implementar casos de teste de validação positiva (entradas perfeitas) para todas as entidades: `Fact`, `Rule`, `LatentSkill`, `Snapshot`, `AuditEvent` e `ContextSummary`.
  - [x] Implementar casos de teste de validação negativa (tipos errados, formatos de UUID corrompidos, escopos inválidos, etc.) garantindo que `pydantic.ValidationError` seja levantado.
  - [x] Implementar casos de teste específicos para o ciclo de vida dos estados do fato (`active`, `stale`, `archived`, `purged`).

- [x] **Task 2: Definir Enums de Domínio e Tipagem Estruturada** (AC: 1, 3)
  - [x] Criar o arquivo `src/universal_memory/domain/entities/__init__.py` para facilitar exportações limpas.
  - [x] Definir o enum `FactScope` (`global` ou `project`) em `src/universal_memory/domain/entities/fact.py`.
  - [x] Definir o enum `FactStatus` (`active`, `stale`, `archived`, `purged`) em `src/universal_memory/domain/entities/fact.py`.
  - [x] Definir outros enums necessários para controle de auditoria, status de snapshots e escopos de regras.

- [x] **Task 3: Implementar Entidades Pydantic v2 do Domínio** (AC: 1, 2, 3, 4)
  - [x] Implementar `Fact` com validações robustas (UUIDv4 para `id`, ISO 8601 UTC para `created_at` / `updated_at`, `recurrence_count` inicializado em 0 por padrão, `tags` como lista de strings, `metadata` como dicionário genérico).
  - [x] Implementar `Rule` para representação de regras de prompts consolidadas e regras ativas de comportamento.
  - [x] Implementar `LatentSkill` para tracking de recorrência de metodologias do usuário.
  - [x] Implementar `Snapshot` (com metadados do manifest: timestamp, escopo, ação, caminho relativo, hash SHA-256).
  - [x] Implementar `AuditEvent` para logs estruturados append-only (JSONL).
  - [x] Implementar `ContextSummary` segregando `project_summary`, `universal_preferences` e `active_rules`.
  - [x] Configurar todos os modelos com `model_config = ConfigDict(populate_by_name=True, alias_generator=to_camel)` ou garantir que a serialização nativa use estritamente `snake_case` e configure adequadamente aliases se necessário (embora a persistência exija `snake_case` nativo direto em disco).

- [x] **Task 4: Exportar Entidades na Raiz do Módulo Domain** (AC: 1)
  - [x] Atualizar `src/universal_memory/domain/__init__.py` para expor de forma limpa todas as entidades criadas e exceções associadas (se houver).

- [x] **Task 5: Validar a Suíte Completa de Testes locais** (AC: 1, 2, 4)
  - [x] Executar `uv run pytest tests/domain/` e verificar cobertura completa (100% verde nos testes de entidades).
  - [x] Executar `uv run ruff check .` e `uv run pyright` para garantir conformidade estrita com as regras de qualidade e tipagem estática.

### Review Findings

- [x] [Review][Patch] Validar timestamps como UTC em todas as entidades persistíveis [`src/universal_memory/domain/entities/base.py`:8]
- [x] [Review][Patch] Exigir `schema_version` canônico igual a 1 [`src/universal_memory/domain/entities/base.py`:6]
- [x] [Review][Patch] Validar `Snapshot.relative_path` como caminho relativo seguro [`src/universal_memory/domain/entities/snapshot.py`:18]
- [x] [Review][Patch] Validar `Snapshot.hash` como digest SHA-256 [`src/universal_memory/domain/entities/snapshot.py`:19]
- [x] [Review][Patch] Validar referências de snapshot/auditoria em vez de aceitar placeholders livres [`src/universal_memory/domain/entities/audit_event.py`:15]
- [x] [Review][Patch] Impedir `recurrence_count` negativo em fatos e latent skills [`src/universal_memory/domain/entities/fact.py`:21]
- [x] [Review][Patch] Exportar todos os enums públicos de escopo nos módulos `domain` e `domain.entities` [`src/universal_memory/domain/entities/__init__.py`:3]
- [x] [Review][Patch] Corrigir falhas declaradas em `ruff check` e `pyright` [`tests/domain/test_entities.py`:104]

## Dev Notes

- **Padrão de Arquitetura Limpa (Boundaries):**
  - As entidades de domínio residem na camada mais interna (`domain/entities/`). Elas NÃO podem importar nada de `application/`, `infrastructure/` ou `interfaces/`.
  - Use Pydantic v2 nativo sem dependências de frameworks adicionais.
- **Padrões de Persistência JSON:**
  - Em conformidade com a arquitetura descrita em `architecture.md`, as entidades persistíveis em disco (Facts, Rules, Snapshots, AuditEvents, LatentSkills) devem sempre carregar metadados canônicos: `"schema_version": 1`.
  - Certifique-se de que os timestamps usem UTC absoluto (ex: `datetime.now(timezone.utc)` ou serialização com terminação `Z`).
- **Prevenção contra Alucinações de Tipagem:**
  - Garanta tipagem estrita com Pyright. Use type-hints completos (ex: `str`, `int`, `list[str]`, `dict[str, Any]`, `datetime`).
  - No Pydantic v2, prefira o uso de `pydantic.Field` para especificar valores padrões (`default_factory=uuid4` ou `default_factory=lambda: datetime.now(timezone.utc)`).

### Project Structure Notes

- As entidades devem ser criadas dentro do layout `src/universal_memory/domain/entities/`.
- Estrutura esperada de arquivos:
  - `src/universal_memory/domain/entities/__init__.py`
  - `src/universal_memory/domain/entities/fact.py`
  - `src/universal_memory/domain/entities/rule.py`
  - `src/universal_memory/domain/entities/latent_skill.py`
  - `src/universal_memory/domain/entities/snapshot.py`
  - `src/universal_memory/domain/entities/audit_event.py`
  - `src/universal_memory/domain/entities/context_summary.py`

### References

- **Arquitetura - Persistent Data Layout:** [architecture.md#L652-L679](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L652-L679)
- **Arquitetura - Naming Patterns:** [architecture.md#L245-L268](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L245-L268)
- **PRD - Functional Requirements:** [prd.md#L312-L318](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md#L312-L318)

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 3.5 Pro / Advanced Agentic Coding)

### Debug Log References

### Completion Notes List

- Todos os modelos de domínio (Fact, Rule, LatentSkill, Snapshot, AuditEvent, ContextSummary) foram implementados com Pydantic v2 e validações fortes de UUID v4 e fuso horário.
- A suíte de testes unitários escrita previamente (tests/domain/test_entities.py) foi mantida intacta e está totalmente compatível com as classes criadas.
- O isolamento completo da camada de domínio foi estritamente mantido (Clean Architecture).

### File List

- `src/universal_memory/domain/entities/base.py`
- `src/universal_memory/domain/entities/fact.py`
- `src/universal_memory/domain/entities/rule.py`
- `src/universal_memory/domain/entities/latent_skill.py`
- `src/universal_memory/domain/entities/snapshot.py`
- `src/universal_memory/domain/entities/audit_event.py`
- `src/universal_memory/domain/entities/context_summary.py`
- `src/universal_memory/domain/entities/__init__.py`
- `src/universal_memory/domain/__init__.py`

### Change Log

- 2026-05-22: História inicializada e desenhada com sucesso; pronta para início de desenvolvimento TDD.
- 2026-05-22: Implementação concluída das entidades de domínio e conformidade TDD garantida.
