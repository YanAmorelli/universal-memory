# Story 1.3: Definir Exceções e Ports de Domínio

Status: done

## Story

Como um desenvolvedor implementando use cases e adapters,
eu quero exceções e ports de domínio estáveis,
para que infraestrutura, CLI e MCP possam evoluir em paralelo sem acoplamento indevido.

## Acceptance Criteria

1. **Dado** testes de import boundary e contratos de ports escritos primeiro (TDD),
   **Quando** os ports de domínio são implementados sob `domain/ports/`,
   **Então** existem portas abstratas (ABCs) para fatos, regras, latent skills, snapshots, auditoria e resumos de contexto.
   **E** tentar instanciar qualquer um desses ports diretamente resulta em um erro de tipo (`TypeError`).
   **E** cada port expõe as assinaturas abstratas para as operações mínimas de leitura, listagem, escrita, exclusão/purga (onde aplicável) e hooks de migração.

2. **Dado** erros esperados e cenários excepcionais de negócio no domínio,
   **Quando** eles são simulados nos testes ou levantados por futuros use cases,
   **Então** o sistema expõe exceções tipadas de domínio:
     - `SecretDetectedError` (Erro ao detectar segredos/API keys em fatos ou regras; Código JSON-RPC: `-32010`)
     - `SnapshotFailedError` (Falha na integridade ou criação/restauração do snapshot; Código JSON-RPC: `-32020`)
     - `ValidationFailedError` (Falha de validação lógica na camada de negócio; Código JSON-RPC: `-32602`)
     - `FactNotFoundError` (Fato solicitado por ID não encontrado; Código JSON-RPC: `-32040`)
     - `InvalidConfigError` (Configuração TOML global ou local inválida ou ausente; Código JSON-RPC: `-32050`)
     - `StorageError` (Falha física ou corrupção no layout de persistência `.umem/`; Código JSON-RPC: `-32060`)
   **E** todas as exceções herdam de uma classe base comum do domínio (`UniversalMemoryError` ou similar) e aceitam mensagens detalhadas de erro.
   **E** nenhuma lógica interna de negócio ou port precisa usar exceções genéricas como `ValueError` ou `RuntimeError` para cenários conhecidos.

## Tasks / Subtasks

- [x] **Task 1: Escrever os Testes de Contrato e Exceções Primeiro (TDD - RED Phase)** (AC: 1, 2)
  - [x] Criar o arquivo de teste `tests/domain/test_exceptions.py` validando que todas as exceções de domínio necessárias herdam de uma exceção base e carregam as propriedades corretas.
  - [x] Criar o arquivo de teste `tests/domain/test_ports.py` para garantir que os ports abstratos não podem ser instanciados e expõem as assinaturas com assinaturas de tipo e type hints compatíveis com o Pyright.
  - [x] Validar a fase RED garantindo que esses testes falham por falta dos arquivos de produção.

- [x] **Task 2: Implementar Exceções do Domínio** (AC: 2)
  - [x] Criar `src/universal_memory/domain/exceptions.py`.
  - [x] Definir a exceção base `UniversalMemoryError` herdando de `Exception`.
  - [x] Implementar `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError` e `StorageError` herdando de `UniversalMemoryError`.

- [x] **Task 3: Implementar Ports de Armazenamento e Persistência** (AC: 1)
  - [x] Criar o diretório `src/universal_memory/domain/ports/`.
  - [x] Criar o arquivo `src/universal_memory/domain/ports/__init__.py` para exportar de forma limpa todas as interfaces abstratas.
  - [x] Implementar os seguintes ports abstratos utilizando `abc.ABC` e `abc.abstractmethod`:
    - [x] `FactRepository` em `fact_repository.py` com métodos: `read`, `list`, `write`, `delete`, `purge` e `migrate`.
    - [x] `RuleRepository` em `rule_repository.py` com métodos: `read`, `list`, `write`, `delete` e `migrate`.
    - [x] `LatentSkillRepository` em `latent_skill_repository.py` com métodos: `read`, `list`, `write`, `delete` e `migrate`.
    - [x] `SnapshotRepository` em `snapshot_repository.py` com métodos: `read`, `list`, `write` e `migrate`.
    - [x] `AuditLogRepository` em `audit_log_repository.py` com métodos: `read`, `list`, `write` e `migrate`.
    - [x] `ContextSummaryRepository` em `context_summary_repository.py` com métodos: `read`, `list`, `write` e `migrate`.

- [x] **Task 4: Exportar Exceções e Ports na Raiz do Módulo Domain** (AC: 1, 2)
  - [x] Atualizar `src/universal_memory/domain/__init__.py` para exportar todas as exceções e ports definidos, facilitando o acesso para camadas externas (`application` e `infrastructure`).

- [x] **Task 5: Validar a Suíte Completa de Testes e Tipagem Estática (GREEN Phase)** (AC: 1, 2)
  - [x] Executar os testes unitários de domínio e garantir 100% de cobertura verde.
  - [x] Executar o linter `ruff check .` e o analisador `pyright` garantindo tipagem estática infalível e livre de avisos.

### Review Findings

- [x] [Review][Decision] Protocol Leak (JSON-RPC) in Domain Layer — As exceções de domínio customizadas definem diretamente `json_rpc_code` como um atributo de classe. Embora isso esteja mapeado nas referências da Story 1.3, definir códigos de protocolo de transporte diretamente no domínio viola a separação de conceitos da Clean Architecture. O ideal seria que a camada externa de MCP fizesse essa tradução, mantendo as exceções puras.
- [x] [Review][Patch] Genéricos `str` em vez de Enums de Domínio Específicos nos Ports [src/universal_memory/domain/ports/]
- [x] [Review][Patch] Parâmetro `status` inadequado em AuditLog e ContextSummary [src/universal_memory/domain/ports/audit_log_repository.py]
- [x] [Review][Patch] Uso Redundante de `raise NotImplementedError` em Métodos Abstratos [src/universal_memory/domain/ports/]
- [x] [Review][Patch] Ausência de Documentação nos Métodos `read` (Tratamento de Não Encontrado) [src/universal_memory/domain/ports/]
- [x] [Review][Patch] Falta de Docstrings explicando `delete` e `purge` [src/universal_memory/domain/ports/fact_repository.py]
- [x] [Review][Patch] Fragilidade e Erros de Robustez nos Testes de Assinatura (`test_ports.py`) [tests/domain/test_ports.py]
- [x] [Review][Patch] Inconsistência de Idioma nos Testes de Exceção [tests/domain/test_exceptions.py]
- [x] [Review][Defer] Dados Estruturados Específicos em Exceções de Domínio [src/universal_memory/domain/exceptions.py] — deferred, pre-existing

## Dev Notes

- **Conformidade com a Clean Architecture:**
  - Os ports representam as fronteiras (boundaries) do nosso sistema. Elas definem contratos e assinaturas que a camada de infraestrutura (`infrastructure/`) implementará.
  - A camada de domínio não depende de banco de dados, arquivos TOML, serializadores JSON ou FastMCP diretamente. Seus ports devem conter apenas tipos nativos e as entidades de domínio definidas na Story 1.2.
- **Tipagem Estrita com ABCs:**
  - Use `abc.ABC` e o decorador `abc.abstractmethod` para todos os métodos dos ports.
  - Use type hints completos em todas as assinaturas (ex: `Optional`, `list`, `Union` de `typing`, ou os tipos nativos se rodando em Python 3.12+).
- **Assinaturas sugeridas para os métodos de repositório:**
  - `read(id: str) -> Entity`: Retorna a entidade correspondente ou lança `FactNotFoundError` (ou exceção correlata de não encontrado).
  - `list(...) -> list[Entity]`: Retorna a lista de entidades encontradas que combinam com os filtros informados (ex: `scope`, `status`).
  - `write(entity: Entity) -> None`: Grava ou atualiza a entidade de forma atômica no armazenamento físico.
  - `delete(id: str) -> None`: Remove logicamente ou marca como indisponível/inativo (onde aplicável).
  - `purge(id: str) -> None` (específico de fatos): Remove de forma definitiva e irrecuperável do armazenamento físico.
  - `migrate(target_version: int) -> None`: Hook responsável por efetuar migrações estruturais de dados quando o `schema_version` mudar.

### Project Structure Notes

- A árvore de arquivos esperada para a camada de domínio após essa história deve ser:
  ```
  src/universal_memory/domain/
  ├── __init__.py
  ├── entities/
  │   ├── __init__.py
  │   ├── base.py
  │   ├── fact.py
  │   ├── rule.py
  │   ├── latent_skill.py
  │   ├── snapshot.py
  │   ├── audit_event.py
  │   └── context_summary.py
  ├── exceptions.py
  └── ports/
      ├── __init__.py
      ├── fact_repository.py
      ├── rule_repository.py
      ├── latent_skill_repository.py
      ├── snapshot_repository.py
      ├── audit_log_repository.py
      └── context_summary_repository.py
  ```

### References

- **Persistent Data Layout & Storage Contract:** [architecture.md#L725-L737](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L725-L737)
- **MCP Error Mapping Spec:** [architecture.md#L738-L752](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L738-L752)
- **Quality & Boundaries:** [architecture.md#L400-L415](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L400-L415)

## Dev Agent Record

### Agent Model Used

Antigravity (Gemini 3.5 Pro / Advanced Agentic Coding)

### Debug Log References

- 2026-05-22: RED confirmado com `uv run pytest tests/domain/test_exceptions.py tests/domain/test_ports.py`, falhando por ausência de `universal_memory.domain.exceptions` e `universal_memory.domain.ports`.
- 2026-05-22: GREEN confirmado com `uv run pytest`.
- 2026-05-22: Qualidade confirmada com `uv run ruff check .` e `uv run pyright`.

### Completion Notes List

- Implementadas exceções de domínio tipadas com `UniversalMemoryError` como base comum, mensagem detalhada e códigos JSON-RPC por cenário conhecido.
- Implementados ports abstratos para fatos, regras, latent skills, snapshots, auditoria e resumos de contexto com `abc.ABC`, métodos abstratos e assinaturas tipadas.
- Exportadas exceções e interfaces de ports em `universal_memory.domain` para consumo por camadas externas.

### File List

- `_bmad-output/implementation-artifacts/1-3-definir-exce-es-e-ports-de-dom-nio.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/domain/__init__.py`
- `src/universal_memory/domain/exceptions.py`
- `src/universal_memory/domain/ports/__init__.py`
- `src/universal_memory/domain/ports/audit_log_repository.py`
- `src/universal_memory/domain/ports/context_summary_repository.py`
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/domain/ports/latent_skill_repository.py`
- `src/universal_memory/domain/ports/rule_repository.py`
- `src/universal_memory/domain/ports/snapshot_repository.py`
- `tests/domain/test_exceptions.py`
- `tests/domain/test_ports.py`

### Change Log

- 2026-05-22: História inicializada e detalhada com sucesso. Pronta para desenvolvimento TDD (RED/GREEN).
- 2026-05-22: Implementadas exceções e ports de domínio com testes de contrato, suíte completa, Ruff e Pyright verdes.
