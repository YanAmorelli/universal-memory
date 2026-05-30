---
stepsCompleted: [1, 2, 3, 4, 5, 6, 7, 8]
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
workflowType: 'architecture'
project_name: 'universal-memory'
user_name: 'Yan'
date: '2026-05-22'
lastStep: 8
status: 'ready-with-minor-gaps'
completedAt: '2026-05-22'
revalidatedAt: '2026-05-22'
patchedAt: '2026-05-22'
lastCorrectionAt: '2026-05-22'
readinessStatus: 'ready-with-minor-gaps'
---

# Architecture Decision Document

_This document builds collaboratively through step-by-step discovery. Sections are appended as we work through each architectural decision together._

## Project Context Analysis

### Requirements Overview

**Functional Requirements:**
28 requisitos funcionais organizados em 8 domínios:
1. **Core Memory Management (FR1–FR6):** Persistência local legível, separação lógica STM/LTM, busca por modos locais, edição manual, purga seletiva, higiene de contexto.
2. **Onboarding & Setup (FR7–FR9):** Seleção de provedores, configuração automática de arquivos de instrução, inicialização por CLI.
3. **CLI (FR10–FR11):** Status de memória, paridade total com API/MCP.
4. **MCP Interface (FR12–FR14):** Servidor MCP nativo (JSON-RPC), leitura e escrita de contexto por agentes externos.
5. **Auto-Adaptation & Sync (FR15–FR17):** Atualização dinâmica de AGENTS.md/CLAUDE.md, injeção de STM com sumarização, controle de overflow de tokens.
6. **Skill Creation Engine (FR18–FR21):** Tracking de latent skills, gatilho de recorrência, geração de estrutura Agent Skills, gestão de skills via CLI.
7. **Security & Safety (FR22–FR24):** Detecção passiva de segredos, bloqueio de persistência, log de auditoria.
8. **Backup & Recovery (FR25–FR28):** Snapshot antes de mutação, bloqueio se snapshot falhar, listagem de snapshots, rollback por escopo.

**Non-Functional Requirements:**
- **Performance:** Consultas de contexto < 150ms p95 (1.000 fatos); inicialização < 200ms p95; benchmark obrigatório texto vs semântica (30 consultas).
- **Security:** 100% bloqueio de padrões de segredo cobertos pela suíte de testes; auditoria consultável em < 2 comandos.
- **Reliability:** Snapshot automático com retenção mínima de 5 versões por escopo; rollback em < 1 minuto via CLI.
- **Integration:** Conformidade MCP 100%; contrato interno de persistência isolado (storage-agnostic); validação em ≥ 2 hosts.
- **Accessibility:** Offline-first total (CLI, MCP, persistência, auditoria, rollback).

**Scale & Complexity:**
- Primary domain: Developer Tool / AI Middleware (CLI + MCP + Local Persistence)
- Complexity level: Medium-High
- Estimated architectural components: ~10 (Memory Engine, Adaptation Motor, Skill Engine, MCP Server, CLI, Secret Scanner, Snapshot Manager, Audit Logger, Context Summarizer, Host Configurator)

### Technical Constraints & Dependencies

- **Runtime:** Python 3.12+
- **Distribution:** PyPI + uvx
- **Storage:** Arquivos locais legíveis por humanos (JSON/Markdown) com metadados estruturados
- **Protocol:** MCP sobre JSON-RPC
- **Offline-first:** Todas as capacidades essenciais sem conectividade
- **Storage abstraction:** Contrato interno isolado para permitir troca futura de backend sem impactar motor de regras, MCP ou CLI
- **Post-MVP readiness:** Modelo de dados deve suportar import/export futuro sem breaking changes

### Cross-Cutting Concerns Identified

1. **Auditoria universal:** Toda mutação automática (memória, regras, skills, arquivos de instrução) gera registro de auditoria consultável.
2. **Snapshot/Rollback:** Pré-condição obrigatória para qualquer escrita automática; falha de snapshot bloqueia a operação.
3. **Detecção de Segredos:** Camada de interceptação transversal que precede qualquer operação de persistência.
4. **Paridade CLI ↔ MCP:** Toda funcionalidade exposta por uma interface deve existir na outra.
5. **Sumarização de Contexto:** Gestão de tamanho de injeção para respeitar limites de tokens do LLM alvo.
6. **Confirmação Humana:** Loop de feedback (Sim/Sempre/Não) antes de promoção de fatos a regras ou criação de skills.

## Starter Template Evaluation

### Technical Preferences Established

- **Package Manager:** uv
- **Linting/Formatting:** Ruff (all-in-one: lint + format + import sort)
- **Type Checking:** Pyright (strict mode, VS Code/Pylance integration)
- **CLI Framework:** Typer + Rich (FastAPI-like DX, output profissional)
- **MCP Framework:** FastMCP 3.x (`fastmcp>=3.3.1,<4`) (experiência existente do usuário; Components, Providers, Transforms)
- **Testing:** pytest + pytest-cov
- **Layout:** src/ com Clean Architecture
- **Distribution:** PyPI (MVP) → Container/Homebrew (post-MVP)

### Primary Technology Domain

Developer Tool / AI Middleware — CLI Tool + MCP Server (Python 3.12+)

### Starter Options Considered

| Opção | Avaliação | Decisão |
| :--- | :--- | :--- |
| `uv init --package` | Scaffolding oficial, minimal, src/ layout | ✅ Selecionado como base |
| Cookiecutter/Copier templates | Opiniados, genéricos, não cobrem MCP | ❌ Overhead desnecessário |

### Selected Starter: `uv init --package` + Clean Architecture Manual

**Rationale for Selection:**
Projeto com requisitos específicos (CLI + MCP dual-interface, Clean Arch, múltiplos subsistemas)
que nenhum template genérico cobre. O scaffolding mínimo do `uv` dá controle total sobre a
estrutura de camadas sem carregar decisões indesejadas.

**Initialization Command:**

```bash
uv init --package universal-memory
cd universal-memory
uv add "typer>=0.25.1" "rich>=15.0.0" "fastmcp>=3.3.1,<4" "pydantic>=2.13.4,<3" "tomli-w>=1.2.0"
uv add --dev pytest pytest-cov ruff pyright
```

**Architectural Decisions Provided by Starter:**

**Language & Runtime:**
Python 3.12+ com type hints obrigatórios (Pyright strict mode)

**CLI Framework:**
Typer + Rich para interface de terminal profissional com saída colorida, tabelas e spinners

**MCP Framework:**
FastMCP 3.x (`fastmcp>=3.3.1,<4`) — Components, Providers, Transforms. Hot reload em dev, auto-threading, authorization granular

**Build Tooling:**
uv (build, lock, run, publish) + Hatchling como build-backend

**Testing Framework:**
pytest + pytest-cov para cobertura integrada ao fluxo de testes

**Code Organization:**
src/ layout com Clean Architecture — separação clara entre domínio, aplicação, infraestrutura e interfaces (CLI/MCP)

**Development Experience:**
- `uv run` para execução no ambiente correto sem ativação manual de venv
- `ruff check . && ruff format .` para lint/format unificado
- `pyright` para type checking estrito
- `uv tool install . --editable` para desenvolvimento local do CLI

**Note:** Project initialization using this command should be the first implementation story.

## Core Architectural Decisions

### Decision Priority Analysis

**Critical Decisions (Block Implementation):**
- Formato de persistência dual (JSON + Markdown)
- Validação com Pydantic v2
- Paridade CLI ↔ MCP via camada de aplicação unificada (Use Cases)
- Exceções de domínio tipadas
- Configuração em TOML

**Important Decisions (Shape Architecture):**
- Detecção de segredos via regex + heurística de entropia
- Snapshot via cópia + manifest JSON
- Auditoria em JSONL (append-only)
- Busca textual como estratégia padrão de recuperação

**Deferred Decisions (Post-MVP):**
- Busca semântica com embeddings locais (interface abstrata pronta)
- Structured logging (structlog)
- Container/Homebrew distribution

### Data Architecture

**Formato de Persistência:** Dual — JSON para dados estruturados (fatos, regras, auditoria,
snapshots, latent skills) + Markdown para documentos (skills, arquivos de instrução).
Rationale: combina "metadados estruturados para automação" com "legível por humanos".

**Validação de Dados:** Pydantic v2 como modelo de domínio e contrato.
Rationale: padrão do ecossistema FastAPI/FastMCP; validação + serialização unificadas.

**Busca/Recuperação:** Busca textual local (substring/regex em JSON) como hipótese padrão MVP.
Interface abstrata (contrato/port) para permitir implementação semântica futura.
O padrão final de recuperação só pode ser confirmado após o benchmark obrigatório com 30 consultas representativas.
Rationale: manter zero dependência e offline-first como hipótese inicial, mas validar latência, qualidade e custo operacional antes de congelar a estratégia.

### Security & Guardrails

**Detecção de Segredos:** Regex patterns para formatos conhecidos (AWS keys, Bearer tokens,
GitHub PATs, etc.) + heurística de entropia para segredos genéricos.
Zero dependências externas, extensível via configuração.
Rationale: cobertura ampla sem deps pesadas; atende FR22-FR23.

**Snapshot/Backup:** Cópia de arquivo + manifest JSON com metadados (timestamp, escopo,
ação responsável, hash do arquivo). Retenção: 5 últimas versões por escopo.
Falha no snapshot bloqueia a operação de mutação.
Rationale: simples, auditável, sem deps; atende FR25-FR28.

**Log de Auditoria:** JSONL (append-only). Cada linha é um evento JSON independente
com timestamp, ação, escopo, origem e resultado.
Consultável via CLI ou `grep`/`jq` direto.
Rationale: append-only natural para auditoria; atende "consultável em < 2 comandos".

### API & Communication Patterns

**Paridade CLI ↔ MCP:** Camada de Aplicação unificada (Use Cases / Application Services).
CLI (Typer) e MCP (FastMCP) são thin adapters na camada de interface.
Cada adapter formata I/O do seu jeito, mas delega para os mesmos use cases.
Rationale: paridade garantida por design; DRY; testabilidade; Clean Architecture natural.

**Estratégia de Erro:** Hierarquia de exceções de domínio tipadas.
Base: `UniversalMemoryError`. Especializações: `FactNotFoundError`,
`SecretDetectedError`, `SnapshotFailedError`, `InvalidConfigError`, etc.
CLI traduz para mensagens Rich coloridas; MCP traduz para JSON-RPC error codes.
Rationale: expressivo, idiomático em Python, cada interface traduz independentemente.

**Gestão de Configuração:** TOML.
Global: `~/.config/umem/config.toml`
Por projeto: `<projeto>/.umem/config.toml`
Leitura nativa com `tomllib` (Python 3.12+); escrita com `tomli-w`.
Rationale: padrão do ecossistema Python moderno, suporta comentários, legível.

### Infrastructure & Deployment

**CI/CD:** GitHub Actions — workflow de lint (ruff) + type check (pyright) +
test (pytest --cov) + publish to PyPI. Detalhamento na fase de implementação.

**Logging da Aplicação:** `logging` stdlib para MVP.
Interface preparada para migração futura para `structlog` se necessário.
Rationale: zero deps, single-user local, logs simples são suficientes.

### Decision Impact Analysis

**Implementation Sequence:**
1. Modelos de domínio (Pydantic v2) — base para tudo
2. Contrato de persistência (ports/interfaces)
3. Implementação de storage (JSON + MD adapters)
4. Use Cases (camada de aplicação)
5. CLI adapter (Typer + Rich)
6. MCP adapter (FastMCP 3.x)
7. Secret scanner (cross-cutting)
8. Snapshot manager (cross-cutting)
9. Audit logger (cross-cutting, JSONL)
10. Host configurator (AGENTS.md, CLAUDE.md)

**Cross-Component Dependencies:**
- Secret Scanner intercepta todas as operações de escrita (Memory Engine, Skill Engine)
- Snapshot Manager é pré-condição de todas as mutações automáticas
- Audit Logger registra ações de todos os componentes
- Use Cases são compartilhados entre CLI e MCP (paridade por design)
- Pydantic models são compartilhados entre domínio, persistência e interfaces

## Implementation Patterns & Consistency Rules

### Contexto Operacional

**O CLI do universal-memory é operado primariamente por agentes de IA em contexto conversacional (tool-use / `run_command`), não por humanos em terminal separado.**
- **Implicações:** MCP é a interface primária; `--format json` é crucial para parsing programático; Rich output é usado quando o agente exibe resultados no chat.

### Naming Patterns

**Código Python:**
- Módulos/arquivos: `snake_case` (ex: `memory_engine.py`)
- Classes: `PascalCase` (ex: `FactRepository`)
- Funções/métodos: `snake_case` (ex: `save_fact()`)
- Variáveis: `snake_case` (ex: `fact_id`)
- Constantes: `UPPER_SNAKE_CASE` (ex: `MAX_RETENTION_COUNT`)
- Tipos/TypeAlias: `PascalCase` (ex: `FactScope`)
- Módulos privados: Prefixo `_` (ex: `_internal.py`)
- Interfaces/Ports (ABC): Prefixo com conceito, sufixo `Port` ou `Repository` (ex: `FactRepository`, `SearchPort`)

**Dados JSON (Persistência):**
- Campos JSON: `snake_case` (ex: `"created_at"`)
- IDs: UUID v4 como string
- Timestamps: ISO 8601 UTC (ex: `"2026-05-22T15:00:00Z"`)
- Enums em JSON: `lowercase_snake` (ex: `"project"`)
- Booleans: `true`/`false` (nunca 1/0)

**CLI:**
- Comandos: `kebab-case` (ex: `umem host setup`)
- Flags: `--kebab-case` (ex: `--format json`)
- Variáveis de ambiente: `UPPER_SNAKE` com prefixo `UMEM_` (ex: `UMEM_CONFIG_PATH`)

### Structure Patterns

**Clean Architecture — Camadas e Regra de Dependência:**
- `interfaces` → `application` → `domain` ← `infrastructure`
- `domain` **não importa nada** de outras camadas.
- `application` importa de `domain`, **nunca** de `infrastructure` ou `interfaces`.
- `infrastructure` implementa os `ports` definidos em `domain`.
- `interfaces` usa `application` (use cases), **nunca** acessa `infrastructure` diretamente.

**Organização de Testes:**
- Diretório `tests/` na raiz, espelhando a estrutura `src/`.
- Nomenclatura: `test_<módulo>.py`.
- Fixtures: `tests/conftest.py` na raiz e por subpasta.

### Format Patterns

**Respostas CLI:**
- Humano (default): Rich panels, tabelas, cores.
- Máquina (`--format json`): JSON puro, uma linha por objeto.

**Respostas MCP (JSON-RPC):**
- Sucesso: `{"result": {"facts": [...], "summary": "..."}}`
- Erro: `{"error": {"code": -32000, "message": "SecretDetectedError", "data": {"detail": "..."}}}`

**Estrutura de Fato Canônica:**
```json
{
  "id": "uuid-v4",
  "content": "conteúdo",
  "scope": "project",
  "source": "user_explicit",
  "created_at": "ISO-8601-UTC",
  "updated_at": "ISO-8601-UTC",
  "status": "active",
  "recurrence_count": 0,
  "tags": ["tag1"],
  "metadata": {}
}
```

### Process Patterns

**Error Handling:**
- Exceção de domínio (`UniversalMemoryError` e derivadas) capturada pelo adapter.
- CLI: Imprime erro com Rich e faz `sys.exit(1)`.
- MCP: Levanta `McpError` formatado.

**Logging:**
- Módulo-level logger (`logger = logging.getLogger(__name__)`).
- Níveis: DEBUG (interno), INFO (operações), WARNING (recuperáveis), ERROR (falhas críticas).

**Injeção de Dependência:**
- Use Cases recebem ports via construtor (Constructor Injection).

### Enforcement Guidelines

**Todos os Agentes de IA DEVEM:**
1. **NUNCA** importar de `infrastructure` ou `interfaces` dentro de `domain` ou `application`.
2. **SEMPRE** usar a hierarquia de exceções de domínio — nunca levantar `ValueError`/`RuntimeError` genéricos.
3. **SEMPRE** adicionar type hints em toda assinatura de função pública.
4. **SEMPRE** escrever teste correspondente em `tests/` para qualquer novo use case ou adapter.
5. **NUNCA** persistir dados sem passar pelo secret scanner.
6. **SEMPRE** usar `snake_case` para campos JSON e nomes de arquivo.
7. **SEMPRE** documentar use cases com docstring que descreve o que faz, não como faz.
8. **NUNCA** colocar lógica de negócio nos adapters (CLI/MCP) — eles apenas formatam I/O.

## Project Structure & Boundaries

### Complete Project Directory Structure

```text
universal-memory/
├── pyproject.toml              # Dependências (uv), metadados, scripts (entry points)
├── uv.lock                     # Lockfile gerenciado pelo uv
├── fastmcp.json                # Configuração declarativa do FastMCP (se aplicável)
├── README.md
├── LICENSE
├── .github/
│   └── workflows/
│       └── ci.yml              # Roda ruff, pyright, pytest
├── tests/
│   ├── conftest.py             # Fixtures globais do pytest
│   ├── contracts/              # Testes de contrato para ports de storage e interfaces
│   ├── domain/
│   ├── application/
│   ├── infrastructure/
│   └── interfaces/
├── benchmarks/
│   └── retrieval.py            # Benchmark textual vs candidato semântico local
└── src/
    └── universal_memory/
        ├── __init__.py
        ├── __main__.py         # Permite rodar `python -m universal_memory`
        │
        ├── domain/             # Sem dependências externas.
        │   ├── __init__.py
        │   ├── exceptions.py   # UniversalMemoryError, SecretDetectedError, etc.
        │   ├── entities/       # Pydantic models (Fact, Rule, Snapshot, AuditEvent)
        │   └── ports/          # ABCs: FactRepository, SecretScannerPort, SnapshotPort...
        │
        ├── application/        # Use Cases. Depende apenas do domain/.
        │   ├── __init__.py
        │   ├── memory/         # save_fact.py, get_context.py, purge_fact.py
        │   ├── adaptation/     # promote_rule.py, sync_agents_md.py
        │   ├── skills/         # track_latent_skill.py, generate_skill_scaffold.py
        │   └── onboarding/     # setup_project.py, configure_host.py
        │
        ├── infrastructure/     # Implementações. Depende do domain/ (para os ports).
        │   ├── __init__.py
        │   ├── storage/        # local_json_repo.py, markdown_repo.py
        │   ├── search/         # text_search.py
        │   ├── security/       # entropy_secret_scanner.py, snapshot_manager.py
        │   ├── audit/          # jsonl_audit_logger.py
        │   └── config/         # toml_loader.py, env_config.py
        │
        └── interfaces/         # Portas de entrada. Dependem do application/.
            ├── __init__.py
            ├── cli/            # Typer app
            │   ├── __init__.py
            │   ├── main.py     # Setup do app Typer, configuração de logging
            │   ├── commands/   # memory.py, host.py, rules.py, audit.py
            │   └── presenters/ # Formatação com Rich
            │
            └── mcp/            # FastMCP server
                ├── __init__.py
                ├── server.py   # Instanciação do FastMCP, registro de rotas
                ├── tools/      # Funções @mcp.tool (chamam os use cases)
                ├── resources/  # @mcp.resource (ex: ler contexto atual)
                └── prompts/    # @mcp.prompt (templates de prompt)
```

### Architectural Boundaries

**API & Component Boundaries:**
- **I/O Boundary (`interfaces/`):** Recebe input bruto (CLI/MCP), mapeia para DTOs/Entities, invoca Use Cases, e formata o output. Captura exceções de domínio e traduz para erros específicos do cliente (Rich UI ou JSON-RPC erro).
- **Application Boundary (`application/`):** Contém os Use Cases (a lógica de negócio). Orquestra as regras, mas não sabe se foi chamado via CLI ou MCP, nem como os dados são salvos (fala com `infrastructure/` via `ports/`).
- **Domain Boundary (`domain/`):** O núcleo do sistema. Pydantic models e ABCs puros. Zero dependências externas (apenas bibliotecas padrão Python e Pydantic).
- **Infrastructure Boundary (`infrastructure/`):** Onde os side-effects acontecem. I/O de disco, chamadas de OS, Regex. Implementa os ABCs definidos em `domain/ports/`.

**Cross-Cutting Concerns:**
- **Security & Audit:** Os use cases em `application/` devem instanciar e invocar o `SecretScannerPort` e `SnapshotPort` antes de persistir, e o `AuditLoggerPort` após o sucesso/falha.

### Requirements to Structure Mapping

**Epic/Feature Mapping:**
- **Core Memory Management:** `application/memory/`, `domain/entities/fact.py`, `infrastructure/storage/local_json_repo.py`
- **Onboarding & Setup:** `application/onboarding/`, `infrastructure/config/host_configurator.py`
- **CLI:** `interfaces/cli/commands/`
- **MCP Interface:** `interfaces/mcp/tools/`, `interfaces/mcp/resources/`
- **Auto-Adaptation:** `application/adaptation/`, `domain/entities/rule.py`
- **Skill Engine:** `application/skills/`, `infrastructure/storage/markdown_repo.py`
- **Security & Guardrails:** `infrastructure/security/`
- **Backup & Recovery:** `infrastructure/security/snapshot_manager.py`

## Architecture Validation Results

### Coherence Validation ✅

**Decision Compatibility:**
Alta compatibilidade. `uv` gerencia perfeitamente o build backend do Hatchling exigido por padrões modernos. `Typer` e `FastMCP` compartilham o mesmo ecossistema mental (`Pydantic`), facilitando a passagem de modelos do domínio para as interfaces sem fricção.

**Pattern Consistency:**
A decisão de manter lógica de negócio estritamente em `application/` (Use Cases) garante que as diferenças de I/O (assíncrono no MCP vs síncrono no Typer CLI) sejam tratadas exclusivamente na camada de adaptadores, preservando os padrões.

**Structure Alignment:**
A estrutura `src/` com Clean Architecture reflete exatamente a separação de responsabilidades decidida no Passo 4, isolando side-effects de infraestrutura (arquivos, scanner) da lógica.

### Requirements Coverage Validation ✅

**Epic/Feature Coverage:**
Todos os 8 domínios funcionais do PRD possuem mapeamento direto na árvore de diretórios (ex: Core Memory → `application/memory`; Security → `infrastructure/security`).

**Functional Requirements Coverage:**
FR1 a FR28 cobertos estruturalmente. Destaque para o Secret Scanner (FR22-23) e Snapshot Manager (FR25-28), que foram elevados a "Cross-Cutting Concerns" a serem injetados nos Use Cases, garantindo execução obrigatória.

**Non-Functional Requirements Coverage:**
- Performance (< 150ms): Suportada pela hipótese de busca textual e repositório JSON local sem network overhead; deve ser comprovada pelo benchmark de 30 consultas antes da estratégia final.
- Offline-first: Adoção exclusiva de bibliotecas locais e persistência em FS.

### Implementation Readiness Validation ✅

**Decision Completeness:**
Tecnologias, pacotes e versões fixados. Regras de nomenclatura claras para Python e JSON. Estrutura de exceções definida.

**Structure Completeness:**
Árvore de diretórios completa, indo da raiz do repositório até a granularidade de arquivos de interfaces abstratas (`ports/`).

**Pattern Completeness:**
Diretrizes explícitas sobre injeção de dependência e tratamento de erros (Rich vs JSON-RPC).

### Gap Analysis Results

**Important Gaps:**
- **Modelo de concorrência (Typer sync vs FastMCP async):** Para evitar complexidade e dado que I/O local é rápido, Use Cases devem ser síncronos. FastMCP lidará com isso via threadpool automático.

**Nice-to-Have Gaps:**
- **Versionamento de Schema:** Inserir `"schema_version": 1` nas entidades base Pydantic para prever migrações futuras sem quebrar a deserialização (Post-MVP portability).

### Architecture Completeness Checklist

**Requirements Analysis**
- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**
- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**
- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**
- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** SUPERSEDED BY REVALIDATION PATCH

**Confidence Level:** HIGH - A estrutura é sólida, os pacotes são modernos (Python 3.12+, uv, FastMCP) e o escopo foi adequadamente delimitado para um MVP local.

**Key Strengths:**
- Adoção de Clean Architecture garante que a complexidade de ter duas interfaces (CLI e MCP) não corrompa a lógica de negócio.
- Foco em offline-first real sem bancos de dados pesados.
- Padrões rigorosos para garantir que agentes de IA possam ler e entender o código.

**Areas for Future Enhancement:**
- Migração do motor de busca textual para busca semântica em base vetorial local.
- Distribuição via Homebrew.
- Sincronização multi-máquina nativa (fase 2).

### Implementation Handoff

**AI Agent Guidelines:**
- Follow all architectural decisions exactly as documented
- Use implementation patterns consistently across all components
- Respect project structure and boundaries
- Refer to this document for all architectural questions

**First Implementation Priority:**
Inicializar o projeto base (`uv init --package universal-memory`), configurar o `.python-version` para `3.12`, instalar as dependências base versionadas (`typer`, `rich`, `fastmcp`, `pydantic`, `tomli-w`) e as deps de dev (`pytest`, `pytest-cov`, `ruff`, `pyright`), e montar o esqueleto básico de diretórios de acordo com a `Complete Project Directory Structure`.

## Architecture Revalidation Results

### Coherence Validation

**Decision Compatibility:**
Parcial. Clean Architecture + Typer + FastMCP + Pydantic v2 é coerente, mas há inconsistência operacional: o comando inicial instala `typer`, `rich` e `fastmcp`, enquanto a arquitetura depende também de `pydantic` e `tomli-w`.

**Pattern Consistency:**
Boa, com ressalva. A regra CLI/MCP como adapters finos sobre use cases compartilhados é sólida. Falta, porém, uma matriz explícita de paridade CLI ↔ MCP para impedir drift entre interfaces.

**Structure Alignment:**
Parcial. A árvore suporta os domínios principais, mas ainda não define layout de dados em disco, política de merge de config global/projeto, nem contratos concretos de mutation pipeline.

### Requirements Coverage Validation

**Epic/Feature Coverage:**
Parcial. Os 8 domínios do PRD têm pastas mapeadas, mas alguns requisitos têm apenas cobertura nominal.

**Functional Requirements Coverage:**
Parcial. Gaps principais: FR3 benchmark obrigatório, FR6 context hygiene, FR7 seleção de hosts, FR16 evidência de última leitura/falhas, FR18-FR21 registry/validação de skills.

**Non-Functional Requirements Coverage:**
Parcial. Performance e MCP compliance são objetivos declarados, mas faltam protocolo de benchmark, suíte de conformidade MCP e testes de contrato de storage.

### Implementation Readiness Validation

**Decision Completeness:**
Parcial. Stack e camadas estão claras, mas versões/pacotes não estão totalmente fixados.

**Structure Completeness:**
Parcial. Falta layout canônico de arquivos de memória, snapshots, auditoria, config e skills geradas.

**Pattern Completeness:**
Parcial. Falta especificar fluxo transacional obrigatório: secret scan -> snapshot -> write -> audit -> rollback/failure event.

### Gap Analysis Results

**Critical Gaps:**

- Benchmark textual vs semântico exigido pelo PRD ainda não foi definido nem executado antes da escolha final de recuperação textual.
- Dependências iniciais incompletas: `pydantic` e `tomli-w` são decisões arquiteturais, mas não aparecem no comando base.
- Layout persistente de dados não está especificado, apesar de ser central para edição manual, auditoria, rollback e portabilidade.

**Important Gaps:**

- Falta matriz CLI ↔ MCP por capacidade.
- Falta contrato de storage com operações mínimas e testes de contrato.
- Falta host support matrix arquitetural para `AGENTS.md`, `CLAUDE.md` e equivalentes.
- Falta modelo de lifecycle para STM/context hygiene.
- Falta schema/versionamento obrigatório nas entidades, não apenas como nice-to-have.
- Falta política de error codes MCP/JSON-RPC por exceção de domínio.

**Nice-to-Have Gaps:**

- Registrar decisão explícita sobre sync/async nos use cases e adapters.
- Separar `snapshot_manager.py` de `security/` se o domínio de backup crescer.

### Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**

- [ ] Critical decisions documented with versions
- [ ] Technology stack fully specified
- [x] Integration patterns defined
- [ ] Performance considerations addressed

**Implementation Patterns**

- [x] Naming conventions established
- [x] Structure patterns defined
- [ ] Communication patterns specified
- [ ] Process patterns documented

**Project Structure**

- [ ] Complete directory structure defined
- [x] Component boundaries established
- [ ] Integration points mapped
- [ ] Requirements to structure mapping complete

### Architecture Readiness Assessment

**Overall Status:** SUPERSEDED BY ARCHITECTURE PATCH

**Confidence Level:** medium

**Key Strengths:**

- Clean Architecture é a escolha correta para manter CLI e MCP consistentes.
- Offline-first, arquivos locais e auditoria append-only combinam bem com o PRD.
- Guardrails de secret scanning e snapshot foram corretamente tratados como cross-cutting concerns.

**Areas for Future Enhancement:**

- Adicionar um Architecture Patch antes de criar épicos/stories.
- Transformar gaps críticos em decisões explícitas: data layout, benchmark protocol, dependency list, mutation pipeline e parity matrix.

### Implementation Handoff

**First Implementation Priority:**
Atualizar este documento com um patch de arquitetura antes do scaffold inicial.

## Architecture Patch - Revalidation Fixes

### Technology Stack Corrections

**Runtime:** Python 3.12+.

**Runtime dependencies:**

- `typer>=0.25.1`
- `rich>=15.0.0`
- `fastmcp>=3.3.1,<4`
- `pydantic>=2.13.4,<3`
- `tomli-w>=1.2.0`

**Initialization Command:**

```bash
uv init --package universal-memory
cd universal-memory
uv add "typer>=0.25.1" "rich>=15.0.0" "fastmcp>=3.3.1,<4" "pydantic>=2.13.4,<3" "tomli-w>=1.2.0"
uv add --dev pytest pytest-cov ruff pyright
```

### Persistent Data Layout

**Global data root:** `~/.local/share/umem/`

**Project data root:** `.umem/`

Canonical structure:

```text
.umem/
├── config.toml
├── memory/
│   ├── facts.json
│   ├── rules.json
│   ├── latent_skills.json
│   └── context_summaries.json
├── audit/
│   └── events.jsonl
├── snapshots/
│   ├── manifest.json
│   └── files/
├── skills/
└── benchmarks/
    └── retrieval-results.json
```

All persisted JSON entities must include `schema_version`, `id`, `created_at`, `updated_at`, `scope`, and `status`.

### Mutation Pipeline

Every automatic mutation must follow this order:

1. Validate input with Pydantic.
2. Run secret scanner.
3. Resolve target scope and storage path.
4. Create snapshot.
5. If snapshot fails, abort mutation.
6. Write data atomically through storage port.
7. Append audit event.
8. Return CLI/MCP result with audit reference.

No adapter may bypass this pipeline.

### CLI to MCP Parity Matrix

| Capability | CLI | MCP |
| --- | --- | --- |
| initialize project memory | `umem init` | `initialize_project` |
| get context | `umem context` | `get_context` |
| remember fact | `umem remember` | `remember_fact` |
| list facts | `umem facts list` | `list_facts` |
| purge fact | `umem facts purge` | `purge_fact` |
| propose rule | `umem rules propose` | `propose_rule` |
| list audit events | `umem audit list` | `list_audit_events` |
| list snapshots | `umem snapshots list` | `list_snapshots` |
| rollback scope | `umem rollback` | `rollback_scope` |
| host setup/check | `umem host setup/check` | `check_host` |
| skill proposal/list | `umem skills propose/list` | `propose_skill`, `list_skills` |

Every new use case must add both CLI and MCP coverage unless explicitly marked internal.

### Retrieval Benchmark Protocol

Before textual retrieval is final, implement `benchmarks/retrieval.py`.

Minimum benchmark:

- 1,000 synthetic or fixture facts.
- 30 representative queries from PRD journeys.
- Compare local substring/regex against a semantic retrieval stub or documented local semantic candidate.
- Record p95 latency, quality score 1-5, offline compatibility, operational complexity.
- Default retrieval strategy must be justified in `benchmarks/retrieval-results.json`.

### Storage Contract

Define storage ports in `src/universal_memory/domain/ports/`:

- `FactRepository`
- `RuleRepository`
- `LatentSkillRepository`
- `SnapshotRepository`
- `AuditLogRepository`
- `ContextSummaryRepository`

Each repository must support read, list, write, delete/purge where applicable, and schema migration hooks. Contract tests live under `tests/contracts/`.

### MCP Error Mapping

Map domain exceptions to JSON-RPC errors:

| Domain exception | JSON-RPC code |
| --- | --- |
| `SecretDetectedError` | `-32010` |
| `SnapshotFailedError` | `-32020` |
| `ValidationFailedError` | `-32602` |
| `FactNotFoundError` | `-32040` |
| `InvalidConfigError` | `-32050` |
| `StorageError` | `-32060` |

CLI renders the same errors through Rich and exits with non-zero status.

### Host Support Matrix

MVP host adapters:

- `codex`: validates and consumes the shared `AGENTS.md` target.
- `claude_code`: validates and consumes the `CLAUDE.md` target.

Instruction targets:

- `agents_md`: writes `AGENTS.md` exactly once as the shared cross-tool instruction manifest.
- `claude_md`: writes `CLAUDE.md` only for Claude-specific instructions that cannot be represented in `AGENTS.md`.
- Host-specific rules directories are separate targets and must not duplicate the full shared manifest.

Each host adapter must define supported instruction targets, MCP configuration method, read validation, write validation, rollback behavior, and audit event type.

### Instruction Target Ownership

`AGENTS.md` is a shared standard followed partially by multiple tools. It is not owned by a single host adapter.

The system must enforce single-writer ownership for shared instruction files:

- `AGENTS.md` is owned by the `agents_md` instruction target and updated once per mutation cycle.
- Hosts that support `AGENTS.md` reference the same file instead of generating their own copy.
- Host-specific adapters may validate whether their provider reads `AGENTS.md`, but they must not rewrite it independently.
- Provider-specific files store only deltas that are impossible or inappropriate in the shared manifest.

`AGENTS.md` must remain a compact routing and policy manifest, not a full knowledge dump. It should point agents to specialized documents or rules when the provider supports that pattern.

Recommended layout:

```text
AGENTS.md                         # Shared compact manifest, single writer
CLAUDE.md                         # Claude-specific deltas only
GEMINI.md                         # Gemini-specific deltas only, post-MVP
.cursor/rules/*.mdc               # Cursor scoped rules, post-MVP
.github/copilot-instructions.md   # Copilot-specific entrypoint, post-MVP
.windsurf/rules/                  # Windsurf scoped rules, post-MVP
.continue/rules/*.md              # Continue scoped rules, post-MVP
.clinerules/                      # Cline/Roo scoped rules, post-MVP
CONVENTIONS.md                    # Aider-readable convention doc, post-MVP
```

Provider-specific targets must prefer references to shared docs over repeated content. If a provider cannot follow references reliably, the adapter may generate a small provider-specific summary, but the summary must be derived from canonical shared content and audited as a generated delta.

### Rules and Manifest Strategy

The architecture distinguishes three layers:

1. Canonical knowledge lives in project docs and memory records.
2. `AGENTS.md` is the shared manifest that gives stable, concise operating rules and pointers.
3. Provider-specific rule files express activation, scoping, or syntax required by a specific host.

This prevents two failure modes:

- A giant `AGENTS.md` that consumes too much context and becomes hard to maintain.
- Repetitive host files that drift from one another and contradict the shared policy.

Adapters must classify every proposed instruction update as one of:

- `shared_policy`: belongs in `AGENTS.md`.
- `provider_delta`: belongs in a provider-specific file.
- `scoped_rule`: belongs in a host rules directory with activation metadata.
- `canonical_doc`: belongs in project documentation and should only be linked from instruction files.

### Context Hygiene Lifecycle

STM facts must support lifecycle states:

- `active`
- `stale`
- `archived`
- `purged`

Context hygiene runs after task completion or explicit CLI/MCP command and must archive stale project-scoped facts before deletion unless user requests purge.

### Updated Readiness

This patch resolves the critical revalidation gaps. Architecture can return to `READY WITH MINOR GAPS` after this content is saved and the validation section is updated.

## Architecture Revalidation Closure

### Corrections Applied

As revisões do patch foram incorporadas às seções operacionais da arquitetura:

- O comando de inicialização agora instala `pydantic` e `tomli-w` com versões compatíveis.
- A decisão de recuperação textual foi rebaixada de escolha final para hipótese padrão condicionada ao benchmark obrigatório.
- A estrutura de projeto agora inclui `tests/contracts/` e `benchmarks/retrieval.py`.
- O handoff inicial agora exige dependências versionadas e o benchmark antes de congelar a estratégia de busca.

### Residual Gap Analysis

**Critical Gaps:** Nenhum gap crítico permanece aberto depois do patch.

**Important Gaps:**

- O benchmark textual vs candidato semântico ainda precisa ser implementado e registrado em `.umem/benchmarks/retrieval-results.json` durante as primeiras histórias.
- A suíte de conformidade MCP precisa ser materializada como testes de integração quando os adapters MCP forem criados.
- Os contratos de storage precisam ser validados em `tests/contracts/` assim que os ports forem implementados.

**Nice-to-Have Gaps:**

- Separar `snapshot_manager.py` de `infrastructure/security/` se backup/rollback crescer além de uma responsabilidade transversal simples.
- Documentar um candidato semântico local específico após o primeiro benchmark, caso a busca textual não alcance qualidade suficiente.

### Updated Architecture Completeness Checklist

**Requirements Analysis**

- [x] Project context thoroughly analyzed
- [x] Scale and complexity assessed
- [x] Technical constraints identified
- [x] Cross-cutting concerns mapped

**Architectural Decisions**

- [x] Critical decisions documented with versions
- [x] Technology stack fully specified
- [x] Integration patterns defined
- [x] Performance considerations addressed

**Implementation Patterns**

- [x] Naming conventions established
- [x] Structure patterns defined
- [x] Communication patterns specified
- [x] Process patterns documented

**Project Structure**

- [x] Complete directory structure defined
- [x] Component boundaries established
- [x] Integration points mapped
- [x] Requirements to structure mapping complete

### Updated Architecture Readiness Assessment

**Overall Status:** READY WITH MINOR GAPS

**Confidence Level:** high

**Rationale:**
As decisões bloqueantes estão documentadas com versões, layout persistente, pipeline de mutação, matriz CLI/MCP, contrato de storage, mapeamento de erros MCP e estratégia de ownership de arquivos de instrução. Os gaps restantes são itens de execução das histórias iniciais, não bloqueadores de arquitetura.

### Corrected Implementation Handoff

**First Implementation Priority:**
Inicializar o scaffold com `uv init --package universal-memory`, fixar Python 3.12+, instalar as dependências versionadas, criar os diretórios `src/`, `tests/contracts/`, `benchmarks/` e implementar primeiro os modelos/ports que sustentam storage, auditoria, snapshot, secret scanning e benchmark de recuperação.

**Next Planning Step:**
Prosseguir para criação ou atualização de épicos e histórias usando esta arquitetura corrigida como fonte de verdade.
