---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
  - step-04-final-validation
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
  - "_bmad-output/planning-artifacts/devex-interaction-spec.md"
---

# universal-memory - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for universal-memory, decomposing the requirements from the PRD, UX Design/DevEx Interaction Spec, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: O sistema deve persistir fatos e preferências do usuário em armazenamento local legível por humanos e compatível com metadados estruturados.

FR2: O sistema deve diferenciar logicamente entre Memória de Curto Prazo, específica por repositório, e Memória de Longo Prazo, global.

FR3: O sistema deve recuperar contexto por modos de busca locais definidos pela arquitetura, com seleção do modo padrão baseada em benchmark de latência, qualidade de resultado, custo operacional e funcionamento offline.

FR4: O usuário deve poder visualizar e editar manualmente os arquivos de persistência diretamente no sistema de arquivos.

FR5: O sistema deve permitir a purga seletiva de fatos específicos ou de bases de memória completas.

FR6: O sistema deve executar rotinas de Context Hygiene para arquivar ou remover fatos de curto prazo obsoletos após a conclusão de tarefas.

FR7: During initial setup, the system must allow the user to select one or more supported runtimes/agents from a registry, including at least Claude Code, OpenCode and Codex/OpenAI-class AGENTS.md hosts, with Cursor and Antigravity represented according to their support tier.

FR8: The system must configure the selected runtimes by writing or updating their supported instruction targets and native skill targets, such as `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, `.cursor/`, `.opencode/` or equivalent runtime-specific paths, with snapshot and audit protection before every mutation, supporting custom maximum overrides (`max_managed_lines` and `max_managed_chars`) to control context buffer sizes.

FR9: O usuário deve poder inicializar o `universal-memory` em um novo projeto ou diretório via comando CLI, como `umem init`.

FR10: O usuário deve poder consultar o status da memória, incluindo tamanho, regras ativas e skills disponíveis, via CLI.

FR11: Toda capacidade exposta pela API/MCP deve ter um comando CLI equivalente para uso manual.

FR12: O sistema deve expor suas capacidades através de um servidor MCP nativo rodando sobre JSON-RPC.

FR13: O sistema deve permitir que agentes externos, como Claude Desktop, leiam o contexto atualizado da memória.

FR14: O sistema deve permitir que agentes externos gravem novos fatos e proponham regras na memória via comandos MCP.

FR15: O sistema deve atualizar dinamicamente as instruções contidas nos arquivos dos agentes, como `AGENTS.md` e `CLAUDE.md`, conforme novas regras e fatos são consolidados na memória, garantindo a preservação de blocos e diretrizes inseridas manualmente pelo usuário fora dos delimitadores de início/fim do UMEM.

FR16: O sistema deve disponibilizar o resumo da Memória de Curto Prazo no contexto inicial dos agentes e expor, via status ou auditoria, evidência de última leitura, origem do resumo e falhas de injeção quando ocorrerem.

FR17: O sistema deve garantir que a injeção de contexto respeite limites de tamanho, usando sumarização para não causar overflow de tokens no LLM.

FR18: O sistema deve rastrear e contabilizar Latent Skills, ou instruções/metodologias recorrentes do usuário.

FR19: O sistema deve solicitar aprovação explícita, com opções Sim/Sempre/Não, ao atingir o gatilho de recorrência para criar uma nova Skill.

FR20: The system must generate a canonical Agent Skill structure with `SKILL.md`, optional `scripts/` and optional `references/`, then install or link it into native skill directories for selected runtimes when supported by that runtime adapter.

FR21: The user must be able to list, activate, edit, disable and inspect both canonical skills and per-runtime installed skill targets through CLI and MCP-equivalent capabilities.

FR22: O sistema deve escanear passivamente todos os dados recebidos para interceptar chaves de API, credenciais ou variáveis de ambiente sensíveis antes da gravação.

FR23: O sistema deve impedir a persistência de segredos detectados, notificando o usuário sobre a tentativa.

FR24: O sistema deve manter um log de auditoria local de todas as alterações feitas automaticamente nas configurações dos agentes e na criação de novas skills.

FR25: O sistema deve criar snapshot local antes de qualquer alteração automática em memórias, regras, skills ou arquivos de instrução.

FR26: O sistema deve bloquear a alteração automática quando o snapshot prévio falhar.

FR27: O usuário deve poder listar snapshots disponíveis e identificar timestamp, escopo, origem e ação responsável por cada snapshot.

FR28: O usuário deve poder reverter a última alteração automática por escopo via CLI.

FR29: The product must use English as the default language for CLI prompts, help text, generated instructions, skill scaffolds and documentation templates, while allowing an explicit locale configuration for other supported languages such as Portuguese.

FR30: The CLI onboarding experience should include a compact terminal brand element for `umem`, implemented as ANSI/ASCII splash art with a no-color fallback and disabled automatically for JSON/non-interactive output.

FR31: The system must allow the user to trigger updates and synchronize local canonical skills from `.umem/skills/` or local package templates to all active native runtime target paths.

FR32: During synchronization, if a native target file has been modified manually and diverges from the canonical source, the system must interactively prompt the user with choices (Keep Local Target / Overwrite with Canonical) and display a warning that overwriting could break the custom agent workflow. Additionally, the system must detect duplications and logical contradiction conflicts (e.g., 'always' vs 'never') between agent instruction files.

FR33: The CLI must support checking for new library versions, migrating local configuration schema safely, and updating local benchmark datasets without losing user history or custom rules.

### NonFunctional Requirements

NFR1: Consultas locais de contexto devem responder em menos de 150ms no percentil 95 em uma base de teste com pelo menos 1.000 fatos, medido por benchmark automatizado em máquina de desenvolvimento.

NFR2: Leitura de memória e montagem do contexto inicial não devem adicionar mais de 200ms no percentil 95 ao início de uma sessão de agente configurado, medido por teste de integração local.

NFR3: Busca textual local e busca semântica devem ser comparadas em pelo menos 30 consultas representativas antes da escolha final da estratégia padrão de recuperação.

NFR4: O sistema deve bloquear 100% dos padrões de segredo cobertos pela suíte de testes de segurança antes da persistência, com exemplos positivos e negativos.

NFR5: Logs de alteração e alertas de interceptação de segredos devem ser consultáveis via CLI em menos de 2 comandos a partir do diretório do projeto.

NFR6: Antes de qualquer alteração automática em arquivos de instrução ou bases de fatos, o sistema deve criar um snapshot local recuperável.

NFR7: O sistema deve manter pelo menos as 5 versões mais recentes por escopo, validado por teste de rollback.

NFR8: O usuário deve conseguir reverter a última alteração automática em menos de 1 minuto usando CLI.

NFR9: O servidor MCP deve passar em 100% da suíte de conformidade definida pela arquitetura, incluindo health check, recuperação de contexto, gravação/proposta de fato, proposta de regra e tratamento de erros JSON-RPC.

NFR10: A lógica de persistência deve isolar operações de leitura, escrita, listagem e versionamento atrás de um contrato interno testável, permitindo troca de backend sem mudanças no motor de regras, MCP ou CLI.

NFR11: O MVP deve validar leitura de contexto em pelo menos 2 hosts/agentes suportados, medido por teste manual documentado ou teste de integração quando o host permitir automação.

NFR12: CLI, motor de persistência e servidor MCP devem executar leitura, gravação, consulta, auditoria e rollback com rede desabilitada.

### Additional Requirements

- A primeira história de implementação deve inicializar o projeto com `uv init --package universal-memory`, fixar Python 3.12+, instalar dependências versionadas e criar o scaffold base.
- O stack runtime deve incluir `typer>=0.25.1`, `rich>=15.0.0`, `fastmcp>=3.3.1,<4`, `pydantic>=2.13.4,<3` e `tomli-w>=1.2.0`.
- O stack de desenvolvimento deve incluir `pytest`, `pytest-cov`, `ruff` e `pyright`.
- A estrutura deve seguir `src/` layout com Clean Architecture e dependências `interfaces -> application -> domain <- infrastructure`.
- `domain` não deve importar de outras camadas; `application` não deve importar de `infrastructure` ou `interfaces`; `interfaces` não deve acessar `infrastructure` diretamente.
- Use cases devem ser síncronos e receber ports via constructor injection.
- CLI Typer/Rich e MCP FastMCP devem ser thin adapters sobre a mesma camada de aplicação.
- Todos os adapters devem traduzir exceções de domínio para o formato apropriado, Rich no CLI e JSON-RPC no MCP.
- Deve existir hierarquia de exceções de domínio tipadas, incluindo `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError` e `StorageError`.
- As exceções de domínio devem mapear para códigos JSON-RPC específicos: `-32010`, `-32020`, `-32602`, `-32040`, `-32050` e `-32060`.
- A persistência deve usar JSON para dados estruturados e Markdown para documentos e arquivos de instrução.
- Todos os JSON persistidos devem usar `snake_case`, UUID v4 como string, timestamps ISO 8601 UTC, enums `lowercase_snake`, booleanos JSON nativos e campos obrigatórios `schema_version`, `id`, `created_at`, `updated_at`, `scope` e `status`.
- O layout persistente por projeto deve usar `.umem/` com `config.toml`, `memory/`, `audit/events.jsonl`, `snapshots/`, `skills/` e `benchmarks/retrieval-results.json`.
- O layout global deve usar `~/.local/share/umem/`.
- Configuração global deve viver em `~/.config/umem/config.toml` e configuração por projeto em `.umem/config.toml`.
- Leitura TOML deve usar `tomllib`; escrita TOML deve usar `tomli-w`.
- Toda mutação automática deve seguir o pipeline obrigatório: validar entrada, escanear segredos, resolver escopo e caminho, criar snapshot, abortar se snapshot falhar, escrever atomicamente via storage port, registrar auditoria e retornar referência de auditoria.
- Nenhum adapter pode bypassar o pipeline de mutação.
- Deve existir matriz de paridade CLI/MCP para `init`, `context`, `remember`, list/purge facts, propose rule, audit list, snapshots list, rollback, host setup/check e skill proposal/list.
- Todo novo use case deve adicionar cobertura CLI e MCP, exceto quando explicitamente marcado como interno.
- As interações CLI/MCP devem seguir `_bmad-output/planning-artifacts/devex-interaction-spec.md` para saída humana, JSON parseável, confirmações seguras, erros acionáveis e paridade semântica.
- Deve existir benchmark `benchmarks/retrieval.py` com 1.000 fatos, 30 consultas representativas, comparação textual versus candidato semântico local/stub, p95 latency, score de qualidade 1-5, compatibilidade offline e complexidade operacional.
- A estratégia padrão de recuperação deve ser justificada em `.umem/benchmarks/retrieval-results.json`.
- Storage ports devem existir in `src/universal_memory/domain/ports/` para fatos, regras, latent skills, snapshots, auditoria e resumos de contexto.
- Testes de contrato devem viver em `tests/contracts/` e validar operações mínimas e hooks de migração dos repositories.
- O MVP deve implementar host adapters para `codex`, `claude_code` e `opencode` como Tier 1, e suportar detectores Tier 2 para `cursor` e `antigravity`.
- `AGENTS.md` deve ser tratado como manifesto compartilhado e alvo de escrita única por ciclo de mutação.
- `CLAUDE.md` deve conter apenas deltas específicos do Claude que não cabem em `AGENTS.md`.
- Host-specific rule directories devem ser alvos separados e não devem duplicar o manifesto compartilhado.
- `AGENTS.md` deve permanecer compacto, com regras operacionais estáveis e ponteiros para documentos especializados, não um dump completo de conhecimento.
- Adapters devem classificar instruções propostas como `shared_policy`, `provider_delta`, `scoped_rule` ou `canonical_doc`.
- Fatos de STM devem suportar estados `active`, `stale`, `archived` e `purged`.
- Context hygiene deve arquivar fatos de projeto obsoletos antes de deletar, salvo quando o usuário solicitar purge.
- Logs de auditoria devem ser JSONL append-only com timestamp, ação, escopo, origem e resultado.
- Snapshots devem usar cópia de arquivo e manifest JSON com timestamp, escopo, ação responsável e hash.
- Secret scanning deve combinar regex para formatos conhecidos e heurística de entropia para segredos genéricos, sem dependências externas no MVP.
- O desenvolvimento deve seguir TDD: cada história deve explicitar os testes esperados antes da implementação, e código de produção só deve ser considerado completo quando os testes automatizados correspondentes estiverem passando.

### UX Design Requirements

Não há UX visual/web/mobile no MVP. A UX relevante é DevEx para CLI, MCP, arquivos locais, confirmações e erros. O contrato canônico de interação está em `_bmad-output/planning-artifacts/devex-interaction-spec.md` e deve ser usado pelas stories de interface como substituto intencional de uma especificação UX visual.

### FR Coverage Map

FR1: Epic 1 - Persistência local legível e estruturada
FR2: Epic 1 - Separação lógica STM/LTM
FR3: Epic 3 - Recuperação de contexto local e benchmark
FR4: Epic 1 - Arquivos legíveis/editáveis manualmente
FR5: Epic 3 - Purga seletiva de fatos
FR6: Epic 3 - Rotinas de Context Hygiene
FR7: Epic 5 - Seleção de múltiplos runtimes
FR8: Epic 5 - Configuração automática de targets nativos
FR9: Epic 1 - Inicialização CLI e scaffold
FR10: Epic 3 - Exibição de status da memória
FR11: Epic 4 - Paridade de comandos CLI/MCP
FR12: Epic 4 - Servidor FastMCP JSON-RPC
FR13: Epic 4 - Leitura externa de contexto
FR14: Epic 4 - Gravação externa e proposta de regras
FR15: Epic 5 - Sincronização dinâmica de instruções dos hosts
FR16: Epic 3 - Resumo STM e injeção com status
FR17: Epic 3 - Sumarização e limites de tokens
FR18: Epic 6 - Rastreamento de Latent Skills
FR19: Epic 6 - Confirmação explícita Sim/Sempre/Não
FR20: Epic 6 - Geração de pasta e estrutura Agent Skill
FR21: Epic 6 - Operações de skills via CLI/MCP
FR22: Epic 2 - Escaneamento passivo de secrets
FR23: Epic 2 - Impedimento de persistência de segredos
FR24: Epic 2 - Registro de auditoria append-only
FR25: Epic 2 - Snapshots locais pré-mutação
FR26: Epic 2 - Fail-safe (bloqueio se snapshot falhar)
FR27: Epic 2 - Listagem e metadados de snapshots
FR28: Epic 2 - Reversão (rollback) por escopo
FR29: Epic 1 - Configuração de idioma (English by default, locale config)
FR30: Epic 4 - Identidade visual (CLI interactive terminal splash banner)
FR31: Epic 6 - Sincronização de skills canônicas para caminhos nativos
FR32: Epic 6 - Alerta interativo de conflito manual (Keep/Overwrite)
FR33: Epic 5 - CLI schema migrations, library check e update de benchmarks

## Epic List

### Epic 1: Fundação Local, Modelos, Contratos e Locale
O usuário consegue inicializar a base local do `universal-memory` com scaffold Python 3.12+, layout `.umem/` e `.local/share/umem/`, modelos de domínio com suporte a `schema_version`, exceções, ports de storage e configuração em TOML (inglês por padrão, suporte a locale de saída) e contratos de persistência testáveis que destravam o trabalho paralelo sem acoplar as camadas.
**FRs covered:** FR1, FR2, FR4, FR9, FR29.

### Epic 2: Pipeline Seguro de Mutação e Auditoria
O usuário pode confiar que qualquer mutação automática passa por validação, secret scanning passivo, snapshot pré-mutação obrigatório, escrita atômica, log de auditoria `jsonl` e rollback por CLI, evitando vazamentos e corrupção de dados.
**FRs covered:** FR22, FR23, FR24, FR25, FR26, FR27, FR28.

### Epic 3: Memória, Busca e Higiene de Contexto
O usuário e agentes externos conseguem gravar, listar, buscar, sumarizar e gerenciar o ciclo de vida (active, stale, archived, purged) de fatos da Short Term Memory (repositório) e Universal Memory (global) locais com limites de tokens, lifecycle de STM e benchmark de latência/qualidade de busca para manter a memória útil e controlada.
**FRs covered:** FR3, FR5, FR6, FR10, FR16, FR17.

### Epic 4: Interfaces e Paridade (CLI e MCP)
Humanos e agentes externos conseguem operar as mesmas capacidades do sistema de forma consistente através do terminal (com visual brand splash ANSI/ASCII seguro) ou servidor FastMCP JSON-RPC, com tratamento uniforme de erros mapeados.
**FRs covered:** FR11, FR12, FR13, FR14, FR30.

### Epic 5: Runtimes, Hosts e Sincronização de Instruções
O usuário consegue selecionar e configurar múltiplos runtimes suportados (Claude Code, OpenCode, Codex, Cursor, Antigravity) usando um model registry declarativo, gerenciar alvos de instrução (`AGENTS.md` compartilhado, `CLAUDE.md` deltas) e atualizar schemas/benchmarks locais de forma segura e transparente.
**FRs covered:** FR7, FR8, FR15, FR33.

### Epic 6: Latent Skills e Gestão de Skills
O usuário consegue transformar instruções recorrentes em Agent Skills canônicas (`SKILL.md`) e instalá-las de forma sincronizada em diretórios nativos de runtimes suportados, com alertas interativos de conflito manual (Keep Local vs Overwrite Canonical).
**FRs covered:** FR18, FR19, FR20, FR21, FR31, FR32.

## Epic 1: Fundação Local, Modelos e Contratos

O usuário consegue inicializar a base local do `universal-memory` com scaffold Python 3.12+, layout `.umem/`, modelos de domínio, exceções, ports e contratos testáveis que destravam o trabalho paralelo sem acoplar as camadas.

### Story 1.1: Inicializar Scaffold Python do Produto

As a desenvolvedor do universal-memory,
I want inicializar o pacote Python com estrutura, dependências e tooling definidos,
So that o projeto tenha uma base reproduzível para desenvolvimento TDD e trabalho paralelo.

**Requirements covered:** FR9.

**Acceptance Criteria:**

**Given** um repositório sem scaffold Python completo
**When** o projeto é inicializado com `uv`
**Then** existem `pyproject.toml`, `uv.lock`, `.python-version`, `src/universal_memory/`, `tests/`, `tests/contracts/` e `benchmarks/`
**And** o runtime é Python 3.12+ e as dependências runtime/dev versionadas estão configuradas

**Given** o scaffold inicial
**When** os comandos de verificação são executados
**Then** `ruff`, `pyright` e `pytest` executam sem falhas sobre a base mínima
**And** há pelo menos um teste inicial que falharia se o pacote não fosse importável

**Given** o scaffold inicial versionado no repositório
**When** uma alteração é enviada para push ou pull request
**Then** um workflow de CI em `.github/workflows/ci.yml` executa `ruff`, `pyright` e `pytest`
**And** o workflow falha quando lint, type check ou testes automatizados falham

### Story 1.2: Definir Modelos de Domínio para Memória

As a agente ou adapter que usa a memória,
I want modelos de domínio validados para fatos, regras, skills latentes, snapshots, auditoria e resumos de contexto,
So that todos os componentes compartilhem contratos consistentes de dados.

**Requirements covered:** FR1, FR2.

**Acceptance Criteria:**

**Given** os testes de domínio escritos primeiro
**When** os modelos Pydantic são implementados
**Then** cada entidade persistível contém `schema_version`, `id`, `created_at`, `updated_at`, `scope` e `status`
**And** campos JSON seguem `snake_case`, UUID v4 string, timestamps ISO 8601 UTC e enums `lowercase_snake`

**Given** entradas inválidas para entidades de domínio
**When** a validação do modelo roda
**Then** dados inválidos são rejeitados com erro tipado e testável
**And** STM suporta estados `active`, `stale`, `archived` e `purged`

### Story 1.3: Definir Exceções e Ports de Domínio

As a desenvolvedor implementando use cases e adapters,
I want exceções e ports de domínio estáveis,
So that infraestrutura, CLI e MCP possam evoluir em paralelo sem acoplamento indevido.

**Requirements covered:** FR1, FR2, FR11, FR12.

**Acceptance Criteria:**

**Given** testes de import boundary e contratos escritos primeiro
**When** os ports de domínio são implementados
**Then** existem ports para fatos, regras, latent skills, snapshots, auditoria e resumos de contexto
**And** os ports expõem operações mínimas de read, list, write, delete/purge quando aplicável e hooks de migração

**Given** erros esperados do domínio
**When** eles são levantados por use cases ou adapters futuros
**Then** existem exceções tipadas como `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError` e `StorageError`
**And** nenhuma camada precisa usar `ValueError` ou `RuntimeError` genéricos para erros de negócio conhecidos

### Story 1.4: Criar Layout Local `.umem/` e Configuração TOML

As a usuário inicializando um projeto,
I want o `universal-memory` criar e reconhecer uma estrutura local legível,
So that eu possa versionar, inspecionar e editar manualmente a memória do projeto.

**Requirements covered:** FR1, FR2, FR4, FR9.

**Acceptance Criteria:**

**Given** testes de inicialização de projeto escritos primeiro
**When** o comando/use case de inicialização roda em um diretório limpo
**Then** a estrutura `.umem/` é criada com `config.toml`, `memory/`, `audit/events.jsonl`, `snapshots/`, `skills/` e `benchmarks/`
**And** os arquivos iniciais são legíveis por humanos e seguros para edição manual

**Given** uma configuração global e uma configuração de projeto
**When** a configuração é carregada
**Then** TOML é lido com `tomllib` e preparado para escrita com `tomli-w`
**And** caminhos globais e locais são resolvidos sem depender de rede

### Story 1.5: Implementar Inicialização CLI Mínima

As a usuário do universal-memory,
I want executar um comando inicial de projeto,
So that eu possa ativar a memória local em um repositório novo com feedback claro.

**Requirements covered:** FR9.

**Acceptance Criteria:**

**Given** testes CLI escritos antes da implementação
**When** o usuário executa `umem init` em um diretório sem `.umem/`
**Then** o comando cria a estrutura local do projeto
**And** retorna uma mensagem humana indicando os caminhos criados
**And** com `--format json`, retorna JSON puro com as chaves `project_path`, `config_path`, `memory_path`, `audit_path`, `snapshots_path`, `created`, `already_initialized` e `audit_reference`
**And** a saída segue `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** um diretório que já contém `.umem/`
**When** o usuário executa `umem init` novamente
**Then** o comando é idempotente e não corrompe arquivos existentes
**And** informa que a memória local já estava inicializada
**And** com `--format json`, retorna `already_initialized: true`, `created: []` e os mesmos caminhos resolvidos da inicialização original

**Given** o ambiente está offline
**When** `umem init` é executado
**Then** a inicialização funciona sem conectividade externa

### Story 1.6: Configurar Idioma Padrão e Locale

As a usuário ou agente inicializando a memória,
I want que o inglês seja o idioma padrão com configuração explícita de locale,
So that a saída da CLI, instruções geradas e templates de skills sejam consistentes e seguros para automação.

**Requirements covered:** FR29.

**Acceptance Criteria:**

**Given** uma configuração limpa (sem arquivo config.toml)
**When** `umem init` é executado
**Then** o locale padrão configurado no TOML do projeto é `en`
**And** as saídas humanas padrão de ajuda e inicialização são exibidas em inglês

**Given** a flag `--format json` ou uma requisição MCP
**When** qualquer comando CLI ou ferramenta MCP é executado
**Then** os nomes de campos JSON e identificadores de erro permanecem estáveis em inglês
**And** não mudam de acordo com o locale configurado de saída humana

**Given** uma configuração explícita de locale definida como Português (`pt-BR`)
**When** comandos humanos da CLI são executados
**Then** apenas os rótulos e mensagens voltados a humanos são traduzidos

## Epic 2: Pipeline Seguro de Mutação e Auditoria

O usuário pode confiar que qualquer mutação automática passa por validação, secret scanning, snapshot, escrita atômica, auditoria e rollback, evitando perda de dados ou persistência acidental de segredos.

### Story 2.1: Implementar Scanner de Segredos

As a usuário que grava fatos, regras e instruções,
I want que o sistema detecte segredos antes de persistir qualquer dado,
So that credenciais e variáveis sensíveis não sejam salvas acidentalmente na memória.

**Requirements covered:** FR22, FR23.

**Acceptance Criteria:**

**Given** testes de segurança com exemplos positivos e negativos de segredos
**When** o scanner recebe conteúdo com padrões conhecidos de credenciais
**Then** ele identifica o segredo e retorna um erro tipado `SecretDetectedError`
**And** a operação de persistência não é executada

**Given** conteúdo com strings longas suspeitas sem padrão explícito
**When** o scanner calcula heurística de entropia
**Then** ele bloqueia valores que ultrapassam o limite configurado para segredo genérico
**And** registra metadados suficientes para auditoria sem expor o valor sensível

**Given** conteúdo legítimo sem segredo
**When** o scanner é executado
**Then** ele aprova a continuação do pipeline
**And** não produz falsos positivos para exemplos comuns cobertos pela suíte de testes

### Story 2.2: Criar Snapshot Antes de Mutação

As a usuário que permite alterações automáticas,
I want que o sistema crie snapshot local antes de qualquer escrita,
So that eu possa recuperar o estado anterior se uma alteração automática for indesejada.

**Requirements covered:** FR25, FR26.

**Acceptance Criteria:**

**Given** uma mutação automática em memória, regra, skill ou arquivo de instrução
**When** o pipeline resolve o alvo da escrita
**Then** um snapshot é criado antes da mutação
**And** o manifest registra timestamp, escopo, ação responsável, caminho relativo e hash do conteúdo anterior

**Given** uma falha ao criar snapshot
**When** a mutação é solicitada
**Then** o pipeline aborta antes de escrever qualquer dado
**And** retorna `SnapshotFailedError`

**Given** múltiplos snapshots no mesmo escopo
**When** a política de retenção é aplicada
**Then** pelo menos as 5 versões mais recentes por escopo são preservadas
**And** versões antigas só são removidas após o snapshot novo ser confirmado

### Story 2.3: Implementar Escrita Atômica com Auditoria

As a desenvolvedor implementando use cases de mutação,
I want um pipeline obrigatório de escrita segura,
So that nenhum adapter consiga persistir dados sem validação, scanner, snapshot e auditoria.

**Requirements covered:** FR22, FR23, FR24, FR25, FR26.

**Acceptance Criteria:**

**Given** um use case que altera dados persistidos
**When** a mutação é executada
**Then** o pipeline segue a ordem: validar entrada, escanear segredos, resolver escopo e caminho, criar snapshot, escrever atomicamente e registrar auditoria
**And** o resultado retorna uma referência de auditoria

**Given** um adapter CLI ou MCP
**When** ele executa uma mutação
**Then** ele invoca o use case compartilhado em vez de escrever diretamente no storage
**And** testes impedem bypass do pipeline por adapters

**Given** uma falha durante a escrita atômica
**When** o pipeline captura a exceção
**Then** nenhum arquivo parcial permanece como estado final
**And** um evento de auditoria de falha é registrado quando possível

### Story 2.4: Listar Auditoria e Snapshots

As a usuário auditando alterações automáticas,
I want consultar eventos de auditoria e snapshots disponíveis,
So that eu entenda o que foi alterado, quando, por qual ação e como posso recuperar o estado anterior.

**Requirements covered:** FR24, FR27.

**Acceptance Criteria:**

**Given** eventos existentes em `.umem/audit/events.jsonl`
**When** o usuário consulta auditoria por use case ou CLI
**Then** o sistema lista timestamp, ação, escopo, origem, resultado e referência do snapshot quando existir
**And** a consulta pode ser feita em menos de 2 comandos a partir do diretório do projeto
**And** com `--format json`, retorna JSON puro com `events[]` contendo `timestamp`, `action`, `scope`, `origin`, `result`, `snapshot_reference` e `audit_reference`
**And** a saída segue `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** snapshots existentes em `.umem/snapshots/`
**When** o usuário lista snapshots
**Then** o sistema mostra timestamp, escopo, origem, ação responsável, caminho relativo e hash
**And** a saída humana é legível e a saída estruturada é adequada para automação futura
**And** com `--format json`, retorna JSON puro com `snapshots[]` contendo `timestamp`, `scope`, `origin`, `action`, `relative_path`, `hash` e `manifest_path`

**Given** não há eventos ou snapshots
**When** o usuário executa as consultas
**Then** o sistema retorna estado vazio de forma explícita
**And** não trata ausência de dados como erro
**And** com `--format json`, retorna listas vazias em `events` ou `snapshots`, sem texto Rich misturado

### Story 2.5: Reverter Última Mutação por Escopo

As a usuário recuperando uma alteração automática,
I want reverter a última mutação por escopo,
So that eu possa restaurar rapidamente memórias, regras, skills ou arquivos de instrução.

**Requirements covered:** FR28.

**Acceptance Criteria:**

**Given** snapshots válidos para um escopo
**When** o usuário solicita rollback desse escopo
**Then** o sistema restaura o conteúdo do snapshot mais recente aplicável
**And** registra um novo evento de auditoria para o rollback

**Given** não existe snapshot para o escopo solicitado
**When** o rollback é executado
**Then** o sistema retorna erro tipado e mensagem clara
**And** nenhum arquivo é alterado

**Given** um snapshot corrompido ou com hash incompatível
**When** o rollback tenta restaurá-lo
**Then** a operação é bloqueada
**And** o evento de falha preserva evidência suficiente para investigação sem expor segredos

**Given** o ambiente está offline
**When** o usuário executa rollback por escopo
**Then** a reversão funciona sem conectividade externa
**And** completa em menos de 1 minuto em um projeto local de teste

## Epic 3: Memória, Busca e Higiene de Contexto

O usuário e agentes conseguem gravar, listar, recuperar, sumarizar e limpar contexto local com benchmark de busca, limites de tokens e lifecycle de STM para manter a memória útil e controlada.

### Story 3.1: Gravar e Listar Fatos de Memória

As a usuário ou agente que trabalha em um projeto,
I want gravar e listar fatos de memória por escopo,
So that o contexto relevante fique disponível para sessões futuras sem reexplicação.

**Requirements covered:** FR1, FR2.

**Acceptance Criteria:**

**Given** os repositories e modelos de domínio do Epic 1
**When** um fato válido é gravado por use case
**Then** ele é persistido com `schema_version`, `id`, `created_at`, `updated_at`, `scope`, `status`, `source`, `tags` e `metadata`
**And** a gravação passa pelo pipeline seguro de mutação do Epic 2 antes da escrita
**And** se Story 3.1 for implementada antes do pipeline completo, deve usar uma porta/stub de mutation pipeline com o mesmo contrato e substituir o stub antes de marcar a história como concluída

**Given** fatos de escopo `project` e `global`
**When** o usuário lista fatos
**Then** o sistema retorna apenas os fatos compatíveis com o filtro solicitado
**And** preserva separação lógica entre Short Term Memory e Universal Memory

**Given** não existem fatos no escopo solicitado
**When** a listagem é executada
**Then** o sistema retorna uma lista vazia explícita
**And** não trata a ausência de fatos como erro

### Story 3.2: Consultar Contexto Local com Busca Textual

As a agente externo que precisa de contexto antes de agir,
I want consultar fatos relevantes por busca local,
So that eu consiga recuperar memória útil sem depender de rede ou serviços externos.

**Requirements covered:** FR3, FR16.

**Acceptance Criteria:**

**Given** uma base local com fatos ativos
**When** uma consulta textual é executada
**Then** o sistema retorna fatos relevantes usando busca local por substring, normalização ou regex conforme definido pela arquitetura
**And** os resultados incluem identificador, escopo, trecho ou motivo de correspondência e timestamp relevante

**Given** fatos arquivados, obsoletos ou purgados
**When** a consulta padrão é executada
**Then** o sistema exclui esses fatos dos resultados ativos
**And** permite incluir estados não ativos somente por opção explícita de diagnóstico

**Given** o ambiente está offline
**When** a consulta de contexto é executada
**Then** ela funciona sem conectividade externa
**And** não tenta acessar serviços remotos

### Story 3.3: Implementar Benchmark de Recuperação

As a mantenedor do universal-memory,
I want comparar busca textual local com um candidato semântico local ou stub,
So that a estratégia padrão de recuperação seja justificada por dados de latência, qualidade e simplicidade.

**Requirements covered:** FR3.

**Acceptance Criteria:**

**Given** o script `benchmarks/retrieval.py`
**When** o benchmark é executado
**Then** ele cria ou usa uma base de pelo menos 1.000 fatos de teste
**And** roda pelo menos 30 consultas representativas derivadas das jornadas e requisitos do PRD

**Given** duas estratégias comparáveis
**When** o benchmark finaliza
**Then** ele registra p95 de latência, score de qualidade 1-5, compatibilidade offline e complexidade operacional
**And** salva o resultado em `.umem/benchmarks/retrieval-results.json`

**Given** os resultados do benchmark
**When** a estratégia padrão é selecionada
**Then** a justificativa é registrada junto aos resultados
**And** a escolha não contradiz os limites de 150ms p95 para consulta local

### Story 3.4: Montar Resumo de Contexto com Limites de Tokens

As a agente que inicia uma nova sessão,
I want receber um resumo compacto da memória aplicável,
So that o contexto inicial ajude sem causar overflow ou ruído no prompt.

**Requirements covered:** FR16, FR17.

**Acceptance Criteria:**

**Given** fatos de projeto, preferências globais e regras ativas
**When** o resumo de contexto é montado
**Then** ele prioriza itens por escopo, recência, status e relevância
**And** separa claramente `project_summary`, `universal_preferences` e `active_rules`

**Given** uma configuração de limite de tamanho
**When** o conteúdo recuperado excede o limite
**Then** o sistema sumariza ou corta itens de menor prioridade
**And** preserva referência aos fatos usados para montar o resumo

**Given** uma leitura de contexto por agente
**When** a operação completa ou falha
**Then** o sistema expõe evidência de última leitura, origem do resumo e falhas de injeção por status ou auditoria
**And** não expõe segredos ou conteúdo bloqueado pelo scanner

### Story 3.5: Exibir Status da Memória

As a usuário verificando a saúde da memória local,
I want consultar status, tamanho e atividade da base,
So that eu saiba se o projeto está configurado e quais dados estão ativos.

**Requirements covered:** FR10, FR16.

**Acceptance Criteria:**

**Given** uma base `.umem/` inicializada
**When** o status é consultado por use case ou CLI
**Then** o sistema mostra contagem de fatos por escopo e status, regras ativas, skills registradas, tamanho aproximado da base e último health check conhecido
**And** a saída humana é clara para leitura no terminal
**And** com `--format json`, retorna JSON puro com `initialized`, `project_path`, `fact_counts`, `active_rules_count`, `registered_skills_count`, `approximate_size_bytes`, `last_health_check` e `host_validation`
**And** a saída segue `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** o diretório atual não possui `.umem/`
**When** o status é consultado
**Then** o sistema retorna uma mensagem acionável indicando que o projeto não foi inicializado
**And** não cria arquivos automaticamente durante uma consulta read-only
**And** com `--format json`, retorna `initialized: false`, `project_path` e `recommended_action`

**Given** o ambiente está offline
**When** o status é consultado
**Then** a operação funciona apenas com dados locais
**And** não depende de hosts externos

### Story 3.6: Purgar Fatos e Executar Context Hygiene

As a usuário mantendo a memória limpa,
I want arquivar, purgar e higienizar fatos de curto prazo,
So that contexto obsoleto não degrade decisões futuras dos agentes.

**Requirements covered:** FR5, FR6.

**Acceptance Criteria:**

**Given** fatos de Short Term Memory com estados `active`, `stale`, `archived` e `purged`
**When** a higiene de contexto é executada após conclusão de tarefa ou comando explícito
**Then** fatos obsoletos de projeto são marcados como `stale` ou `archived` antes de exclusão
**And** a purga definitiva só ocorre quando o usuário solicita purge explicitamente

**Given** um fato específico selecionado para purga
**When** o usuário confirma a remoção
**Then** o fato deixa de aparecer em consultas e listagens padrão
**And** a alteração passa pelo pipeline seguro de mutação e registra auditoria

**Given** uma base inteira selecionada para purga
**When** a operação é executada
**Then** o sistema aplica escopo corretamente e evita remover dados globais quando o usuário solicitou apenas escopo de projeto
**And** retorna resumo dos itens afetados

**Given** fatos arquivados anteriormente
**When** o usuário executa consulta diagnóstica
**Then** o sistema consegue listar itens arquivados com metadados de lifecycle
**And** mantém fatos purgados fora dos resultados ativos

## Epic 4: Paridade CLI e MCP

Humanos e agentes conseguem operar as mesmas capacidades por CLI e MCP, com adapters finos, matriz de paridade, tratamento consistente de erros e validação JSON-RPC.

### Story 4.1: Estruturar Adapter CLI com Typer e Rich

As a usuário ou agente operando via terminal,
I want comandos CLI consistentes sobre os use cases de aplicação,
So that eu possa executar capacidades de memória manualmente ou por automação sem acessar infraestrutura diretamente.

**Requirements covered:** FR11.

**Acceptance Criteria:**

**Given** a camada de aplicação com use cases disponíveis
**When** o adapter CLI é implementado
**Then** ele usa Typer para comandos e Rich para saída humana
**And** delega a lógica de negócio aos use cases compartilhados

**Given** comandos read-only e comandos de mutação
**When** eles são executados pela CLI
**Then** comandos read-only não criam ou alteram arquivos
**And** comandos de mutação passam pelo pipeline seguro definido no Epic 2

**Given** uma flag de saída estruturada
**When** o usuário solicita formato JSON
**Then** a CLI retorna JSON puro adequado para parsing programático
**And** não mistura Rich markup ou texto humano no payload estruturado
**And** a saída humana, saída JSON, confirmações e erros seguem `_bmad-output/planning-artifacts/devex-interaction-spec.md`

### Story 4.2: Implementar Servidor MCP Base com FastMCP

As a agente externo compatível com MCP,
I want acessar o universal-memory por um servidor MCP nativo,
So that eu consiga ler contexto e invocar capacidades sem depender da CLI.

**Requirements covered:** FR12, FR13.

**Acceptance Criteria:**

**Given** o pacote Python inicializado
**When** o servidor MCP é executado
**Then** ele registra ferramentas ou recursos base via FastMCP
**And** expõe pelo menos health check e leitura de contexto inicial

**Given** uma chamada MCP válida
**When** ela invoca uma capacidade implementada
**Then** o adapter MCP delega ao mesmo use case usado pela CLI
**And** não acessa repositories ou infraestrutura diretamente
**And** respostas MCP preservam os campos semânticos definidos em `_bmad-output/planning-artifacts/devex-interaction-spec.md` para a capacidade equivalente

**Given** o ambiente está offline
**When** o servidor MCP executa capacidades locais
**Then** ele funciona sem conectividade externa
**And** falhas de host externo não impedem operações locais da memória

### Story 4.3: Implementar Matriz de Paridade CLI/MCP

As a mantenedor do produto,
I want garantir que capacidades expostas em uma interface existam na outra,
So that humanos e agentes tenham acesso consistente ao mesmo comportamento.

**Requirements covered:** FR11, FR12, FR13, FR14.

**Acceptance Criteria:**

**Given** a matriz de paridade da arquitetura
**When** uma capacidade pública é implementada
**Then** existem entrada CLI e entrada MCP equivalentes para `init`, `context`, `remember`, list/purge facts, propose rule, audit list, snapshots list, rollback, host setup/check e skill proposal/list
**And** exceções internas são documentadas explicitamente

**Given** testes de paridade
**When** a suíte roda
**Then** ela falha se um use case público estiver exposto somente em CLI ou somente em MCP sem justificativa
**And** valida que ambos retornam dados semanticamente equivalentes
**And** valida aderência aos contratos de interação de `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** uma nova capacidade futura
**When** ela é registrada como pública
**Then** o checklist de implementação exige cobertura nas duas interfaces
**And** o contrato de resposta compartilhado é atualizado antes da entrega

### Story 4.4: Mapear Erros de Domínio para CLI e JSON-RPC

As a usuário ou agente consumidor da interface,
I want receber erros consistentes e acionáveis,
So that eu consiga entender falhas sem depender de detalhes internos.

**Requirements covered:** FR12, FR14.

**Acceptance Criteria:**

**Given** exceções de domínio conhecidas
**When** elas chegam ao adapter CLI
**Then** a CLI renderiza mensagem Rich clara e encerra com status não-zero
**And** não imprime stack trace por padrão para erro de negócio esperado
**And** a mensagem inclui detalhe seguro e hint de recuperação conforme `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** exceções de domínio conhecidas
**When** elas chegam ao adapter MCP
**Then** o MCP retorna JSON-RPC error com códigos mapeados: `SecretDetectedError` `-32010`, `SnapshotFailedError` `-32020`, `ValidationFailedError` `-32602`, `FactNotFoundError` `-32040`, `InvalidConfigError` `-32050` e `StorageError` `-32060`
**And** inclui `data.detail` seguro para automação
**And** inclui `data.recovery_hint` quando houver ação segura recomendada

**Given** erro inesperado não classificado
**When** ele ocorre em qualquer adapter
**Then** o sistema retorna erro genérico seguro
**And** registra auditoria ou log diagnóstico sem expor segredos

### Story 4.5: Validar Conformidade MCP e Contratos de Interface

As a mantenedor garantindo integração com hosts MCP,
I want uma suíte de validação para o servidor MCP e contratos de interface,
So that mudanças futuras não quebrem leitura, escrita e tratamento de erros por agentes externos.

**Requirements covered:** FR12, FR13, FR14.

**Acceptance Criteria:**

**Given** o servidor MCP com capacidades públicas
**When** a suíte de conformidade roda
**Then** ela valida health check, recuperação de contexto, gravação/proposta de fato, proposta de regra e tratamento de erros JSON-RPC
**And** todos os casos passam sem rede externa

**Given** respostas CLI e MCP para a mesma capacidade
**When** testes de contrato comparam os resultados
**Then** os campos essenciais são equivalentes mesmo que a formatação humana seja diferente
**And** diferenças de adapter ficam restritas à camada de apresentação

**Given** uma falha de validação MCP
**When** o teste reporta o erro
**Then** a mensagem aponta a capacidade e o contrato quebrado
**And** a falha bloqueia a história até correção

### Story 4.6: Exibir Identidade Visual de Terminal de Forma Segura

As a usuário executando comandos no terminal de forma interativa,
I want ver um splash banner em ANSI/ASCII representando um pendrive conectado ao terminal,
So that a ferramenta tenha uma identidade visual reconhecível sem quebrar a automação.

**Requirements covered:** FR30.

**Acceptance Criteria:**

**Given** um terminal TTY interativo humano (stdout.isatty() == True)
**When** o usuário inicia o onboarding interativo via CLI (ex: `umem init`)
**Then** um splash banner em ANSI/ASCII compacto ilustrando uma conexão USB/pendrive é exibido no topo
**And** o tamanho do banner é seguro para larguras comuns de terminal

**Given** a flag `--format json`, modo não-interativo ou ambiente de CI/CD
**When** qualquer comando CLI é executado
**Then** nenhum splash banner ou escape code ANSI é emitido na saída padrão

**Given** a variável de ambiente `NO_COLOR` definida ou terminal que não suporta cores
**When** o splash banner é renderizado no modo interativo
**Then** o sistema exibe o banner em texto plano (sem escape codes de cores) de forma legível

## Epic 5: Runtimes, Hosts e Sincronização de Instruções

O usuário consegue selecionar e configurar múltiplos runtimes suportados (Claude Code, OpenCode, Codex, Cursor, Antigravity) usando um model registry declarativo, gerenciar alvos de instrução (`AGENTS.md` compartilhado, `CLAUDE.md` deltas) e atualizar schemas/benchmarks locais de forma segura e transparente.

### Story 5.1: Modelar Registro de Runtimes e Alvos

As a mantenedor configurando integrações de agentes,
I want um modelo declarativo de registro de runtimes e alvos (instruction e native skill targets),
So that cada runtime tenha caminhos, capabilities e tiers de suporte bem definidos.

**Requirements covered:** FR7, FR8, FR15.

**Acceptance Criteria:**

**Given** um registry declarativo de runtimes
**When** os adaptadores e modelos Pydantic são definidos no domínio
**Then** cada runtime declara explicitamente: `runtime_id`, display name, support tier (Tier 1 ou 2), paths padrão (globais e de projeto), alvos de instrução e alvos de skills nativas
**And** o registry inclui suporte a Claude Code, OpenCode e Codex/OpenAI como Tier 1, e Cursor e Antigravity como Tier 2

**Given** o target compartilhado `agents_md`
**When** múltiplos runtimes suportam e consomem `AGENTS.md`
**Then** apenas o target de escrita único do `AGENTS.md` é autorizado a escrever no manifesto compartilhado
**And** adaptadores de runtimes consumidores apenas referenciam e validam a leitura do manifesto compartilhado, sem duplicar o arquivo ou sobrescrevê-lo de forma independente

**Given** um target específico de runtime como `CLAUDE.md` (`claude_md`)
**When** regras ou deltas específicos do runtime precisam ser aplicados
**Then** eles são salvos sob o arquivo do runtime sem duplicar as regras gerais compactas contidas em `AGENTS.md`

### Story 5.2: Configurar Host Codex com `AGENTS.md`

As a usuário usando Codex em um projeto,
I want configurar `AGENTS.md` como manifesto compartilhado compacto,
So that o agente leia regras operacionais e ponteiros para memória sem carregar conhecimento excessivo.

**Requirements covered:** FR8, FR15.

**Acceptance Criteria:**

**Given** um projeto inicializado com `.umem/`
**When** o usuário executa setup/check do host `codex`
**Then** o sistema detecta ou propõe o arquivo `AGENTS.md`
**And** classifica cada instrução proposta como `shared_policy`, `provider_delta`, `scoped_rule` ou `canonical_doc`

**Given** um `AGENTS.md` existente
**When** o sistema precisa atualizá-lo
**Then** preserva conteúdo manual não gerenciado sempre que possível
**And** a alteração passa pelo pipeline seguro de mutação com snapshot, auditoria e rollback

**Given** o manifesto gerado ou atualizado
**When** a validação do host roda
**Then** `AGENTS.md` permanece compacto, com regras operacionais estáveis e ponteiros para docs ou memória
**And** não vira um dump completo de conhecimento do projeto

### Story 5.3: Configurar Host Claude Code com `CLAUDE.md`

As a usuário usando Claude Code junto com a memória universal,
I want configurar deltas específicos em `CLAUDE.md`,
So that Claude receba instruções necessárias sem divergir do manifesto compartilhado.

**Requirements covered:** FR8, FR15.

**Acceptance Criteria:**

**Given** o host `claude_code` selecionado
**When** o setup/check é executado
**Then** o sistema detecta ou propõe `CLAUDE.md`
**And** escreve apenas deltas específicos que não cabem em `AGENTS.md`

**Given** `AGENTS.md` e `CLAUDE.md` presentes
**When** a validação de drift roda
**Then** o sistema identifica duplicações indevidas ou contradições entre os arquivos
**And** propõe correção sem sobrescrever conteúdo manual sem confirmação

**Given** uma atualização em `CLAUDE.md`
**When** a mutação é aplicada
**Then** ela usa snapshot, escrita atômica e auditoria
**And** o rollback por escopo consegue restaurar o estado anterior do arquivo

### Story 5.4: Validar Leitura de Contexto por Host

As a usuário integrando um novo agente,
I want verificar que o host consegue ler contexto da memória,
So that eu saiba que a identidade operacional foi portada corretamente.

**Requirements covered:** FR7, FR8.

**Acceptance Criteria:**

**Given** um host configurado
**When** o check de leitura é executado
**Then** o sistema valida que o host possui instrução para consultar a memória e que o MCP está configurado ou documentado para o host
**And** registra resultado de sucesso, falha ou pendência manual

**Given** uma validação bem-sucedida
**When** o usuário consulta status da memória
**Then** o último resultado de validação do host aparece com timestamp, host, método e referência de auditoria quando aplicável
**And** a evidência ajuda a cumprir o requisito de pelo menos 2 hosts suportados no MVP

**Given** uma falha de validação
**When** o sistema reporta o problema
**Then** a mensagem indica se a falha é de arquivo de instrução, configuração MCP, permissão de escrita ou leitura de contexto
**And** não tenta corrigir automaticamente sem confirmação quando houver risco de sobrescrever conteúdo

### Story 5.5: Sincronizar Regras Consolidadas para Instruções

As a usuário que aprova novas regras de comportamento,
I want sincronizar regras consolidadas para arquivos de instrução suportados,
So that agentes diferentes operem com diretrizes consistentes.

**Requirements covered:** FR15.

**Acceptance Criteria:**

**Given** uma regra aprovada para promoção
**When** a sincronização de instruções roda
**Then** o sistema decide se a regra pertence a `shared_policy`, `provider_delta`, `scoped_rule` ou `canonical_doc`
**And** atualiza apenas os targets correspondentes

**Given** múltiplos runtimes configurados
**When** uma regra compartilhada é sincronizada
**Then** `AGENTS.md` é escrito uma única vez por ciclo de mutação
**And** runtimes que consomem `AGENTS.md` não produzem cópias divergentes

**Given** uma regra que aponta para conteúdo detalhado
**When** ela é sincronizada
**Then** o arquivo de instrução inclui ponteiro compacto para a fonte canônica
**And** o conteúdo longo permanece em docs ou memória, conforme classificado

### Story 5.6: Onboarding CLI de Seleção Multi-Runtime

As a usuário instalando o universal-memory,
I want selecionar múltiplos runtimes simultaneamente de forma interativa ou automática,
So that o setup inicial configure de forma coesa e limpa todos os agentes do meu ambiente de trabalho.

**Requirements covered:** FR7, FR8.

**Acceptance Criteria:**

**Given** o onboarding interativo via CLI
**When** o setup inicial de runtimes é iniciado
**Then** a CLI apresenta o prompt destacado em inglês: `Which runtime(s) would you like to install for?`
**And** lista os runtimes suportados no registry declarativo (Claude Code, OpenCode, Codex, Cursor, Antigravity) com seus respectivos tiers e índices numéricos
**And** aceita a seleção de múltiplos índices (separados por vírgula ou espaço) com defaults seguros visíveis

**Given** a execução no modo não-interativo (scripts/agentes)
**When** a CLI recebe opções explícitas de runtime (ex: `umem init --runtime claude-code --runtime opencode`)
**Then** o sistema executa o setup para todos os runtimes especificados sem exigir input do usuário
**And** com `--format json`, retorna JSON puro contendo `runtimes_selected`, `runtimes_skipped`, `target_paths` e `manual_steps_pending` de forma automatizável

**Given** qualquer confirmação ou plano de alteração de arquivos de runtime
**When** o setup é executado
**Then** as informações mostradas seguem rigorosamente as diretrizes de escopo, caminhos relativos e snapshots do `_bmad-output/planning-artifacts/devex-interaction-spec.md`

### Story 5.7: Atualizações de Biblioteca, Migração de Schema e Benchmarks

As a usuário mantendo meu ambiente do universal-memory atualizado,
I want que a CLI verifique versões, migre schemas de configuração com segurança e atualize os benchmarks locais,
So that eu não perca meu histórico de uso, fatos ou regras customizadas.

**Requirements covered:** FR33.

**Acceptance Criteria:**

**Given** um comando de verificação de atualização (ex: `umem update --check`)
**When** executado via CLI
**Then** o sistema verifica a versão atual da biblioteca local e reporta status

**Given** uma alteração de versão da biblioteca com modificações no schema da configuração TOML
**When** a CLI inicializa ou atualiza o ambiente
**Then** o sistema migra de forma automática e segura os arquivos `.umem/config.toml` e `.umem/memory/*.json`
**And** não corrompe ou deleta dados de fatos salvos, histórico de auditoria ou regras customizadas pelo usuário

**Given** novos datasets ou atualizações nas definições de testes locais
**When** a atualização do benchmarks é executada
**Then** os novos datasets de benchmarks locais sob `.umem/benchmarks/` são atualizados



## Epic 6: Latent Skills e Gestão de Skills

O usuário consegue transformar metodologias recorrentes em Agent Skills formais, com tracking de recorrência, aprovação explícita e gestão por CLI.

### Story 6.1: Registrar Latent Skills por Recorrência

As a usuário que repete metodologias e instruções,
I want que o sistema registre oportunidades de skill latente,
So that padrões recorrentes possam virar capacidades reutilizáveis sem eu reexplicar tudo.

**Requirements covered:** FR18.

**Acceptance Criteria:**

**Given** uma instrução ou metodologia recorrente detectada por agente ou CLI
**When** ela é registrada como latent skill
**Then** o sistema persiste descrição, escopo, origem, contador de recorrência, timestamps, status e metadados
**And** a persistência usa o pipeline seguro de mutação

**Given** a mesma metodologia aparece novamente
**When** o sistema associa a ocorrência a uma latent skill existente
**Then** o contador de recorrência é incrementado
**And** a evidência de origem é preservada sem armazenar segredos

**Given** uma ocorrência ambígua
**When** o sistema não consegue associar com confiança
**Then** ele registra candidato separado ou solicita confirmação em vez de mesclar automaticamente
**And** evita inflar recorrência de skills não relacionadas

### Story 6.2: Propor Criação de Skill com Aprovação Explícita

As a usuário controlando a evolução do sistema,
I want aprovar ou recusar a criação de uma skill quando uma recorrência for detectada,
So that o sistema aprenda sem automatizar decisões comportamentais sensíveis.

**Requirements covered:** FR19.

**Acceptance Criteria:**

**Given** uma latent skill atinge o gatilho de recorrência configurado
**When** a proposta é apresentada ao usuário
**Then** o sistema oferece opções explícitas `Sim`, `Sempre` e `Não`
**And** explica o nome sugerido, propósito, escopo e evidências resumidas da recorrência
**And** a confirmação segue o padrão de decisão e segurança de `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** o usuário escolhe `Sim`
**When** a proposta é aceita
**Then** o sistema cria uma solicitação de geração de skill para aquela ocorrência
**And** mantém futuras ocorrências sujeitas a nova confirmação

**Given** o usuário escolhe `Sempre`
**When** a proposta é aceita
**Then** o sistema registra preferência para aprovar automaticamente propostas equivalentes dentro do escopo configurado
**And** a decisão é auditável e reversível

**Given** o usuário escolhe `Não`
**When** a proposta é recusada
**Then** o sistema marca a latent skill como recusada ou reduz sua prioridade
**And** não cria arquivos de skill

### Story 6.3: Gerar Skill Canônica e Instalar em Targets Nativos

As a usuário que aprovou uma nova skill,
I want que o sistema gere a skill canônica e instale-a nos diretórios de skills nativos dos runtimes selecionados,
So that a capacidade seja imediatamente utilizável pelos agentes compatíveis.

**Requirements covered:** FR20, FR31, FR32.

**Acceptance Criteria:**

**Given** uma skill aprovada
**When** a geração é executada
**Then** o sistema cria a skill canônica sob `.umem/skills/` com `SKILL.md`, `scripts/` e `references/` seguindo a especificação

**Given** runtimes selecionados e ativos na configuração (ex: `claude_code`, `opencode`)
**When** a skill canônica é gerada ou atualizada
**Then** o sistema instala ou cria links simbólicos para a skill nos diretórios nativos correspondentes (ex: `.claude/skills/`, `.opencode/skills/`, `.cursor/rules/`)
**And** cada instalação nativa registra timestamp, runtime de destino, path relativo e referência de auditoria

**Given** uma sincronização ou escrita em arquivo de target nativo que foi editado manualmente pelo usuário (divergindo da versão canônica)
**When** o comando `umem update --skills` ou sincronização automática roda
**Then** o sistema detecta o conflito e exibe um prompt de aviso interativo destacado em inglês: `Warning: Native target has manual changes. Overwriting it might break your current agent workflow. Keep local version or Overwrite with canonical library version? [Keep/Overwrite]`
**And** cria um snapshot de backup da skill modificada antes de qualquer sobrescrita

### Story 6.4: Registrar e Listar Skills

As a usuário gerenciando capacidades aprendidas,
I want listar e inspecionar skills registradas,
So that eu saiba quais metodologias foram formalizadas e estão disponíveis.

**Requirements covered:** FR21.

**Acceptance Criteria:**

**Given** skills registradas na base local ou global
**When** o usuário lista skills via use case ou CLI
**Then** o sistema mostra nome, escopo, status, caminho relativo, data de criação, última atualização e origem
**And** diferencia skills ativas, desativadas e candidatas
**And** com `--format json`, retorna JSON puro com `skills[]` contendo `name`, `scope`, `status`, `relative_path`, `created_at`, `updated_at`, `origin` e `audit_reference`
**And** a saída segue `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** nenhuma skill registrada
**When** a listagem é executada
**Then** o sistema retorna estado vazio explícito
**And** sugere comando ou fluxo de proposta sem criar artefatos automaticamente
**And** com `--format json`, retorna `skills: []` e `recommended_action`

**Given** uma skill específica
**When** o usuário solicita detalhes
**Then** o sistema mostra metadados, caminho relativo, gatilhos de uso e referência de auditoria
**And** não carrega arquivos grandes de `references/` sem pedido explícito
**And** com `--format json`, retorna `name`, `scope`, `status`, `relative_path`, `triggers`, `audit_reference` e `references_loaded: false` por padrão

### Story 6.5: Ativar, Desativar e Editar Skills com Segurança

As a usuário ajustando skills existentes,
I want ativar, desativar e editar skills registradas com guardrails,
So that eu controle quais capacidades estão disponíveis sem perder histórico.

**Requirements covered:** FR21.

**Acceptance Criteria:**

**Given** uma skill ativa
**When** o usuário solicita desativação
**Then** o status da skill muda para desativada
**And** a alteração é auditada e não remove arquivos por padrão

**Given** uma skill desativada
**When** o usuário solicita ativação
**Then** o status volta para ativa se os arquivos obrigatórios ainda existirem
**And** o sistema reporta erro claro se `SKILL.md` estiver ausente ou inválido

**Given** uma edição de metadados ou conteúdo da skill
**When** a alteração é aplicada
**Then** o sistema cria snapshot antes da escrita
**And** mantém rollback por escopo disponível para a alteração

### Story 6.6: Expor Gestão de Skills por CLI e MCP

As a usuário ou agente consumidor,
I want propor, listar e gerenciar skills por CLI e MCP,
So that automações e hosts possam usar o mesmo fluxo sem duplicação de lógica.

**Requirements covered:** FR18, FR19, FR20, FR21.

**Acceptance Criteria:**

**Given** use cases de latent skills e registry implementados
**When** a interface CLI é exposta
**Then** existem comandos para propor skill, listar skills, ver detalhes, ativar, desativar e atualizar metadados permitidos
**And** comandos de mutação passam pelo pipeline seguro

**Given** o servidor MCP implementado
**When** ferramentas MCP de skills são expostas
**Then** existem capacidades equivalentes para propor e listar skills conforme matriz de paridade
**And** capacidades de mutação usam os mesmos use cases da CLI

**Given** testes de paridade CLI/MCP
**When** eles rodam para gestão de skills
**Then** validam equivalência semântica das respostas
**And** falham se uma capacidade pública de skills existir em apenas uma interface sem justificativa
**And** validam os contratos de confirmação, erro e saída definidos em `_bmad-output/planning-artifacts/devex-interaction-spec.md`
