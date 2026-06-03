# Story 1.4: Criar Layout Local `.umem/` e Configuração TOML

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário inicializando um projeto,
eu quero que o `universal-memory` crie e reconheça uma estrutura local legível,
para que eu possa versionar, inspecionar e editar manualmente a memória do projeto.

## Acceptance Criteria

1. **Dado** testes de inicialização de projeto escritos primeiro,
   **Quando** o comando/use case de inicialização roda em um diretório limpo,
   **Então** a estrutura `.umem/` é criada com `config.toml`, `memory/`, `audit/events.jsonl`, `snapshots/`, `skills/` e `benchmarks/`;
   **E** os arquivos iniciais são legíveis por humanos e seguros para edição manual.

2. **Dado** uma configuração global e uma configuração de projeto,
   **Quando** a configuração é carregada,
   **Então** TOML é lido com `tomllib` e preparado para escrita com `tomli-w`;
   **E** caminhos globais e locais são resolvidos sem depender de rede.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes RED para layout local e carregamento de config** (AC: 1, 2)
  - [x] Criar `tests/application/test_setup_project.py` cobrindo a inicialização em diretório limpo e a idempotência básica do fluxo de setup sem CLI.
  - [x] Criar `tests/infrastructure/test_project_layout.py` validando a criação da árvore `.umem/` canônica e dos arquivos iniciais legíveis por humanos.
  - [x] Criar `tests/infrastructure/config/test_toml_loader.py` validando leitura com `tomllib`, serialização com `tomli-w` e merge/resolução entre config global e config de projeto.
  - [x] Confirmar a fase RED com falhas por ausência das implementações de `application/onboarding/` e `infrastructure/config/`.

- [x] **Task 2: Implementar o modelo de configuração e o layout persistente local** (AC: 1, 2)
  - [x] Criar `src/universal_memory/infrastructure/config/__init__.py`.
  - [x] Criar `src/universal_memory/infrastructure/config/project_layout.py` com helpers explícitos para materializar e reconhecer `.umem/`.
  - [x] Criar `src/universal_memory/infrastructure/config/toml_loader.py` com leitura usando `tomllib` e escrita preparada via `tomli-w`, sem dependência de rede.
  - [x] Definir valores iniciais legíveis para:
    - [x] `.umem/config.toml`
    - [x] `.umem/audit/events.jsonl`
    - [x] `.umem/benchmarks/retrieval-results.json`
  - [x] Garantir que a árvore criada siga exatamente o layout canônico da arquitetura:
    - [x] `.umem/config.toml`
    - [x] `.umem/memory/`
    - [x] `.umem/audit/events.jsonl`
    - [x] `.umem/snapshots/`
    - [x] `.umem/skills/`
    - [x] `.umem/benchmarks/`

- [x] **Task 3: Implementar o use case de onboarding sem acoplar a CLI** (AC: 1, 2)
  - [x] Criar `src/universal_memory/application/__init__.py` caso ainda não exista.
  - [x] Criar `src/universal_memory/application/onboarding/__init__.py`.
  - [x] Criar `src/universal_memory/application/onboarding/setup_project.py` para orquestrar a inicialização do projeto e retornar um resultado estruturado para consumo futuro pela CLI e MCP.
  - [x] Garantir que o use case permaneça síncrono e que qualquer I/O de filesystem/TOML fique encapsulado em `infrastructure/config/`.
  - [x] Não introduzir adapter CLI nesta story; `src/universal_memory/__main__.py` deve continuar mínimo até a Story 1.5.

- [x] **Task 4: Validar reconhecimento e resolução de configuração global + projeto** (AC: 2)
  - [x] Cobrir o caminho global `~/.config/umem/config.toml` apenas como entrada de leitura/resolução nesta story (atualizado por BUG-002).
  - [x] Garantir que a configuração de projeto viva em `.umem/config.toml`.
  - [x] Garantir que caminhos de projeto retornados sejam relativos quando fizer sentido para output/diagnóstico e absolutos apenas internamente quando necessário para I/O.
  - [x] Garantir que cenários inválidos de TOML resultem em `InvalidConfigError`, sem uso de `ValueError`/`RuntimeError` para erros conhecidos.

- [x] **Task 5: Fechar GREEN com suíte, tipagem e verificação de regressão** (AC: 1, 2)
  - [x] Executar `uv run pytest tests/application/test_setup_project.py tests/infrastructure/test_project_layout.py tests/infrastructure/config/test_toml_loader.py`.
  - [x] Executar `uv run pytest` para validar ausência de regressões nas stories 1.1–1.3.
  - [x] Executar `uv run ruff check .` e `uv run pyright`.

## Dev Notes

- **Objetivo real desta story:**
  - Esta história fecha o gap entre o scaffold já existente e o layout persistente canônico descrito na arquitetura.
  - O foco aqui é preparar a fundação local do produto e o carregamento de configuração; a superfície CLI humana fica para a Story 1.5.

- **Contexto já estabelecido pelas stories anteriores:**
  - A Story 1.1 já criou o scaffold Python, `pyproject.toml`, `uv.lock`, `src/`, `tests/` e `benchmarks/`.
  - A Story 1.2 já consolidou os modelos de domínio Pydantic com `schema_version`, UUID v4, timestamps UTC e enums de escopo/status.
  - A Story 1.3 já consolidou `InvalidConfigError`, `StorageError` e os ports de storage do domínio, então esta story deve reutilizar essas peças em vez de criar novos erros ad hoc.

- **Guardrails de arquitetura que o dev deve seguir:**
  - Respeitar o layout `src/` e as fronteiras da Clean Architecture em `_bmad-output/planning-artifacts/architecture.md`.
  - `application/` depende apenas de `domain/`; lógica de filesystem e TOML deve ficar em `infrastructure/config/`.
  - O use case deve ser síncrono.
  - Nenhuma parte desta story deve depender de rede.
  - Não antecipar a CLI Typer/Rich nem o servidor FastMCP nesta entrega.

- **Layout canônico obrigatório para esta story:**
  - `.umem/config.toml`
  - `.umem/memory/`
  - `.umem/audit/events.jsonl`
  - `.umem/snapshots/`
  - `.umem/skills/`
  - `.umem/benchmarks/`
  - A arquitetura detalha arquivos futuros dentro de `memory/` e `benchmarks/`, mas esta story precisa ao menos deixar a estrutura reconhecível e estável para as histórias seguintes.

- **Formato e comportamento de configuração:**
  - Ler TOML com `tomllib` e escrever/preparar TOML com `tomli-w`.
  - Configuração global: `~/.config/umem/config.toml` (atualizado por BUG-002).
  - Configuração por projeto: `.umem/config.toml`.
  - O fluxo deve resolver ambas localmente, offline, e tratar config inválida com `InvalidConfigError`.

- **Estado atual do código que importa para a implementação:**
  - `src/universal_memory/__main__.py` ainda imprime apenas uma string fixa; não use esta story para transformar isso em CLI completa.
  - `src/universal_memory/domain/entities/` e `src/universal_memory/domain/ports/` já existem e devem continuar sendo a base tipada para as próximas camadas.
  - Ainda não existem `src/universal_memory/application/` nem `src/universal_memory/infrastructure/config/`; esta story é o ponto certo para introduzi-los.
  - `pyproject.toml` já contém `pydantic`, `tomli-w`, `typer` e `fastmcp`, mas com pisos mais soltos do que os pisos arquiteturais. Se algum ajuste nesse arquivo for estritamente necessário para a story, preserve o escopo mínimo e não misture refactor amplo de dependências.

- **Aprendizados úteis das stories anteriores:**
  - O projeto já usa TDD explícito e validação RED/GREEN nas stories completas.
  - Os testes existentes já rodam com `uv run pytest`, `ruff` e `pyright`; mantenha o mesmo padrão.
  - Os artefatos existentes privilegiam nomes de arquivos previsíveis e responsabilidades pequenas por módulo.

- **Informação técnica atual verificada externamente em 2026-05-24:**
  - `fastmcp` 3.3.1 está publicado no PyPI e continua compatível com Python 3.12+, alinhado à decisão arquitetural de usar a linha 3.x.
  - `pydantic` 2.13.4 está publicado no PyPI e confirma a linha v2 assumida pela arquitetura.
  - `typer` 0.25.1, `rich` 15.0.0 e `tomli-w` 1.2.0 estão publicados no PyPI; isso reforça os pisos definidos nos artefatos de planejamento.
  - Inferência: esta story não precisa atualizar dependências sozinha, mas o dev não deve introduzir APIs incompatíveis com essas versões-alvo.

### Project Structure Notes

- Módulos novos esperados nesta story:
  - `src/universal_memory/application/__init__.py`
  - `src/universal_memory/application/onboarding/__init__.py`
  - `src/universal_memory/application/onboarding/setup_project.py`
  - `src/universal_memory/infrastructure/config/__init__.py`
  - `src/universal_memory/infrastructure/config/project_layout.py`
  - `src/universal_memory/infrastructure/config/toml_loader.py`
- Testes novos esperados nesta story:
  - `tests/application/test_setup_project.py`
  - `tests/infrastructure/test_project_layout.py`
  - `tests/infrastructure/config/test_toml_loader.py`
- Arquivos existentes que podem ser tocados apenas se necessário:
  - `pyproject.toml`
  - `src/universal_memory/domain/__init__.py`
  - `src/universal_memory/__main__.py`
- Preserve a evolução incremental: não criar ainda `interfaces/cli/` nem `interfaces/mcp/`.

### References

- Estrutura e fronteiras: `_bmad-output/planning-artifacts/architecture.md` (Project Structure & Boundaries)
- Layout persistente canônico e contrato de mutação: `_bmad-output/planning-artifacts/architecture.md` (Project data root / Canonical structure / Mutation Pipeline)
- Requisitos funcionais e NFRs do MVP: `_bmad-output/planning-artifacts/prd.md`
- Story source e dependências entre histórias: `_bmad-output/planning-artifacts/epics.md`
- Contrato DevEx para paths relativos e outputs parseáveis: `_bmad-output/planning-artifacts/devex-interaction-spec.md`
- Aprendizados prévios:
  - `_bmad-output/implementation-artifacts/1-1-inicializar-scaffold-python-do-produto.md`
  - `_bmad-output/implementation-artifacts/1-2-definir-modelos-de-dom-nio-para-mem-ria.md`
  - `_bmad-output/implementation-artifacts/1-3-definir-exce-es-e-ports-de-dom-nio.md`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-24: Story criada a partir de `epics.md`, `architecture.md`, `prd.md`, `devex-interaction-spec.md` e learnings das stories 1.1–1.3.
- 2026-05-24: Verificação externa de versões-alvo no PyPI para `fastmcp`, `pydantic`, `typer`, `rich` e `tomli-w`.
- 2026-05-24: Fase RED confirmada com `ModuleNotFoundError` para `universal_memory.application` e `universal_memory.infrastructure` ao rodar a suíte alvo antes da implementação.
- 2026-05-24: Validações GREEN concluídas com `uv run pytest`, `uv run ruff check .` e `uv run pyright`.

### Completion Notes List

- Story contextualizada para implementação TDD do layout local `.umem/` e carregamento TOML offline.
- Guardrails adicionados para evitar mistura prematura com CLI/MCP e para preservar as fronteiras da arquitetura.
- Implementado `ensure_project_layout` com árvore canônica `.umem/`, arquivos iniciais legíveis e reconhecimento idempotente do projeto.
- Implementado `load_config` com leitura offline via `tomllib`, serialização via `tomli-w`, merge profundo global + projeto e erro tipado `InvalidConfigError`.
- Implementado `setup_project` como use case síncrono com retorno estruturado para futura integração com CLI e MCP.
- Adicionados testes de aplicação e infraestrutura cobrindo RED/GREEN, idempotência, merge de configuração e TOML inválido.

### File List

- `_bmad-output/implementation-artifacts/1-4-criar-layout-local-umem-e-configura-o-toml.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/__init__.py`
- `src/universal_memory/application/onboarding/__init__.py`
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/infrastructure/__init__.py`
- `src/universal_memory/infrastructure/config/__init__.py`
- `src/universal_memory/infrastructure/config/project_layout.py`
- `src/universal_memory/infrastructure/config/toml_loader.py`
- `tests/application/test_setup_project.py`
- `tests/infrastructure/config/test_toml_loader.py`
- `tests/infrastructure/test_project_layout.py`

### Change Log

- 2026-05-24: Story criada e enriquecida com contexto de arquitetura, dependências entre stories, tarefas TDD e guardrails de implementação.
- 2026-05-24: Layout local `.umem/`, loader TOML offline e use case de onboarding implementados com cobertura de testes e validações completas.

### Review Findings

- [x] [Review][Patch] Rompimento da fronteira da camada de aplicação [`src/universal_memory/application/onboarding/setup_project.py:4`] — resolvido via ports de domínio e adapters locais, removendo acoplamento direto de `application/` com `infrastructure/`.
- [x] [Review][Patch] Estado parcial ou corrompido de `.umem/` deve falhar explicitamente [`src/universal_memory/infrastructure/config/project_layout.py:47`] — resolvido com validação explícita e erro determinístico para árvore parcial/corrompida.
- [x] [Review][Patch] Colisão arquivo-diretório é aceita como layout válido [`src/universal_memory/infrastructure/config/project_layout.py:47`] — resolvido com checagem de tipo esperada para cada caminho canônico.
- [x] [Review][Patch] Leitura de TOML deixa erros reais de filesystem escaparem sem normalização [`src/universal_memory/infrastructure/config/toml_loader.py:55`] — resolvido com normalização para `StorageError`/`InvalidConfigError`.
- [x] [Review][Patch] O loader não resolve caminhos configurados, só faz merge de strings [`src/universal_memory/infrastructure/config/toml_loader.py:27`] — resolvido com `resolved_paths` retornando caminhos absolutos calculados offline.
- [x] [Review][Patch] `merged` compartilha referências mutáveis com `global_data` e `project_data` [`src/universal_memory/infrastructure/config/toml_loader.py:70`] — resolvido com merge por cópia profunda.
- [x] [Review][Patch] O rastreamento do layout não representa integralmente a estrutura canônica de `benchmarks/` [`src/universal_memory/infrastructure/config/project_layout.py:4`] — resolvido incluindo `benchmarks/` no layout canônico e no rastreamento retornado.
- [x] [Review][Defer] Estratégia de auto-reparo resiliente para estados específicos de `.umem/` [`src/universal_memory/infrastructure/config/project_layout.py:47`] — deferred, futura evolução desejável após definir regras explícitas para quais corrupções parciais podem ser reparadas com segurança.
