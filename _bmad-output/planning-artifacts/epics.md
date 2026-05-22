---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
inputDocuments:
  - "_bmad-output/planning-artifacts/prd.md"
  - "_bmad-output/planning-artifacts/architecture.md"
---

# universal-memory - Epic Breakdown

## Overview

This document provides the complete epic and story breakdown for universal-memory, decomposing the requirements from the PRD, UX Design if it exists, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: O sistema deve persistir fatos e preferências do usuário em armazenamento local legível por humanos e compatível com metadados estruturados.

FR2: O sistema deve diferenciar logicamente entre Memória de Curto Prazo, específica por repositório, e Memória de Longo Prazo, global.

FR3: O sistema deve recuperar contexto por modos de busca locais definidos pela arquitetura, com seleção do modo padrão baseada em benchmark de latência, qualidade de resultado, custo operacional e funcionamento offline.

FR4: O usuário deve poder visualizar e editar manualmente os arquivos de persistência diretamente no sistema de arquivos.

FR5: O sistema deve permitir a purga seletiva de fatos específicos ou de bases de memória completas.

FR6: O sistema deve executar rotinas de Context Hygiene para arquivar ou remover fatos de curto prazo obsoletos após a conclusão de tarefas.

FR7: Durante a configuração inicial, o sistema deve permitir que o usuário selecione os provedores de agentes suportados, como Claude, Gemini e ChatGPT.

FR8: O sistema deve configurar automaticamente os arquivos de instrução dos agentes selecionados, como `CLAUDE.md` e `AGENTS.md`, para inicializar o uso da memória universal imediatamente após a instalação.

FR9: O usuário deve poder inicializar o `universal-memory` em um novo projeto ou diretório via comando CLI, como `umem init`.

FR10: O usuário deve poder consultar o status da memória, incluindo tamanho, regras ativas e skills disponíveis, via CLI.

FR11: Toda capacidade exposta pela API/MCP deve ter um comando CLI equivalente para uso manual.

FR12: O sistema deve expor suas capacidades através de um servidor MCP nativo rodando sobre JSON-RPC.

FR13: O sistema deve permitir que agentes externos, como Claude Desktop, leiam o contexto atualizado da memória.

FR14: O sistema deve permitir que agentes externos gravem novos fatos e proponham regras na memória via comandos MCP.

FR15: O sistema deve atualizar dinamicamente as instruções contidas nos arquivos dos agentes, como `AGENTS.md` e `CLAUDE.md`, conforme novas regras e fatos são consolidados na memória.

FR16: O sistema deve disponibilizar o resumo da Memória de Curto Prazo no contexto inicial dos agentes e expor, via status ou auditoria, evidência de última leitura, origem do resumo e falhas de injeção quando ocorrerem.

FR17: O sistema deve garantir que a injeção de contexto respeite limites de tamanho, usando sumarização para não causar overflow de tokens no LLM.

FR18: O sistema deve rastrear e contabilizar Latent Skills, ou instruções/metodologias recorrentes do usuário.

FR19: O sistema deve solicitar aprovação explícita, com opções Sim/Sempre/Não, ao atingir o gatilho de recorrência para criar uma nova Skill.

FR20: O sistema deve gerar a estrutura de pastas e o arquivo `SKILL.md` seguindo o padrão `agentskills.io`.

FR21: O usuário deve poder listar, ativar, editar e desativar Skills registradas através da CLI.

FR22: O sistema deve escanear passivamente todos os dados recebidos para interceptar chaves de API, credenciais ou variáveis de ambiente sensíveis antes da gravação.

FR23: O sistema deve impedir a persistência de segredos detectados, notificando o usuário sobre a tentativa.

FR24: O sistema deve manter um log de auditoria local de todas as alterações feitas automaticamente nas configurações dos agentes e na criação de novas skills.

FR25: O sistema deve criar snapshot local antes de qualquer alteração automática em memórias, regras, skills ou arquivos de instrução.

FR26: O sistema deve bloquear a alteração automática quando o snapshot prévio falhar.

FR27: O usuário deve poder listar snapshots disponíveis e identificar timestamp, escopo, origem e ação responsável por cada snapshot.

FR28: O usuário deve poder reverter a última alteração automática por escopo via CLI.

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
- O layout global deve usar `~/.local/share/universal-memory/`.
- Configuração global deve viver em `~/.config/universal-memory/config.toml` e configuração por projeto em `.umem/config.toml`.
- Leitura TOML deve usar `tomllib`; escrita TOML deve usar `tomli-w`.
- Toda mutação automática deve seguir o pipeline obrigatório: validar entrada, escanear segredos, resolver escopo e caminho, criar snapshot, abortar se snapshot falhar, escrever atomicamente via storage port, registrar auditoria e retornar referência de auditoria.
- Nenhum adapter pode bypassar o pipeline de mutação.
- Deve existir matriz de paridade CLI/MCP para `init`, `context`, `remember`, list/purge facts, propose rule, audit list, snapshots list, rollback, host setup/check e skill proposal/list.
- Todo novo use case deve adicionar cobertura CLI e MCP, exceto quando explicitamente marcado como interno.
- Deve existir benchmark `benchmarks/retrieval.py` com 1.000 fatos, 30 consultas representativas, comparação textual versus candidato semântico local/stub, p95 latency, score de qualidade 1-5, compatibilidade offline e complexidade operacional.
- A estratégia padrão de recuperação deve ser justificada em `.umem/benchmarks/retrieval-results.json`.
- Storage ports devem existir em `src/universal_memory/domain/ports/` para fatos, regras, latent skills, snapshots, auditoria e resumos de contexto.
- Testes de contrato devem viver em `tests/contracts/` e validar operações mínimas e hooks de migração dos repositories.
- O MVP deve implementar host adapters para `codex` e `claude_code`.
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

Nenhum documento de UX Design foi encontrado em `_bmad-output/planning-artifacts`. Não há UX-DRs extraídos nesta etapa.

### FR Coverage Map

FR1: Epic 1 - persistência local legível e estruturada.

FR2: Epic 1 - separação STM/LTM nos modelos e layout de dados.

FR3: Epic 3 - recuperação local e benchmark de estratégia de busca.

FR4: Epic 1 - arquivos editáveis manualmente e formato humano.

FR5: Epic 3 - purga seletiva de fatos e bases.

FR6: Epic 3 - context hygiene e lifecycle de STM.

FR7: Epic 5 - seleção e configuração de hosts/provedores.

FR8: Epic 5 - configuração automática de arquivos de instrução.

FR9: Epic 1 - inicialização por CLI e scaffold local.

FR10: Epic 3 - status da memória via use case e CLI.

FR11: Epic 4 - paridade CLI/MCP para capacidades expostas.

FR12: Epic 4 - servidor MCP nativo sobre JSON-RPC.

FR13: Epic 4 - leitura de contexto por agentes externos.

FR14: Epic 4 - escrita de fatos e proposta de regras via MCP.

FR15: Epic 5 - atualização dinâmica de instruções dos agentes.

FR16: Epic 3 - resumo STM, evidência de leitura e falhas de injeção.

FR17: Epic 3 - sumarização e limites de tokens.

FR18: Epic 6 - tracking e contagem de latent skills.

FR19: Epic 6 - aprovação explícita Sim/Sempre/Não.

FR20: Epic 6 - geração de estrutura Agent Skills com `SKILL.md`.

FR21: Epic 6 - gestão de skills via CLI.

FR22: Epic 2 - scanner passivo de segredos.

FR23: Epic 2 - bloqueio de persistência de segredos.

FR24: Epic 2 - log de auditoria local.

FR25: Epic 2 - snapshot local antes de mutação.

FR26: Epic 2 - bloqueio quando snapshot falhar.

FR27: Epic 2 - listagem de snapshots.

FR28: Epic 2 - rollback por escopo.

## Epic List

### Epic 1: Fundação Local, Modelos e Contratos

O usuário consegue inicializar a base local do `universal-memory` com scaffold Python 3.12+, layout `.umem/`, modelos de domínio, exceções, ports e contratos testáveis que destravam o trabalho paralelo sem acoplar as camadas.

**FRs covered:** FR1, FR2, FR4, FR9.

**Implementation notes:** Este épico deve criar a fundação mínima compartilhada, incluindo testes de contrato e estrutura para TDD nas histórias seguintes.

### Epic 2: Pipeline Seguro de Mutação e Auditoria

O usuário pode confiar que qualquer mutação automática passa por validação, secret scanning, snapshot, escrita atômica, auditoria e rollback, evitando perda de dados ou persistência acidental de segredos.

**FRs covered:** FR22, FR23, FR24, FR25, FR26, FR27, FR28.

**Implementation notes:** Pode avançar em paralelo com Epic 3 após os ports/modelos básicos do Epic 1. Cada comportamento de segurança deve ser orientado por testes automatizados antes da implementação.

### Epic 3: Memória, Busca e Higiene de Contexto

O usuário e agentes conseguem gravar, listar, recuperar, sumarizar e limpar contexto local com benchmark de busca, limites de tokens e lifecycle de STM para manter a memória útil e controlada.

**FRs covered:** FR3, FR5, FR6, FR10, FR16, FR17.

**Implementation notes:** Pode começar após a fundação de modelos/ports do Epic 1 e integrar o pipeline seguro do Epic 2 assim que ele estiver disponível.

### Epic 4: Paridade CLI e MCP

Humanos e agentes conseguem operar as mesmas capacidades por CLI e MCP, com adapters finos, matriz de paridade, tratamento consistente de erros e validação JSON-RPC.

**FRs covered:** FR11, FR12, FR13, FR14.

**Implementation notes:** Pode evoluir por fatias assim que houver use cases reais dos Epics 1-3. Cada capacidade nova deve ter cobertura equivalente de CLI e MCP, salvo exceção explícita.

### Epic 5: Hosts e Sincronização de Instruções

O usuário consegue configurar hosts suportados, validar leitura de contexto e manter `AGENTS.md` e `CLAUDE.md` sincronizados sem duplicação, drift ou ownership ambíguo.

**FRs covered:** FR7, FR8, FR15.

**Implementation notes:** Deve depender do pipeline seguro do Epic 2 antes de escrever arquivos de instrução e da base de interfaces do Epic 4 para validação operacional.

### Epic 6: Latent Skills e Gestão de Skills

O usuário consegue transformar metodologias recorrentes em Agent Skills formais, com tracking de recorrência, aprovação explícita e gestão por CLI.

**FRs covered:** FR18, FR19, FR20, FR21.

**Implementation notes:** Deve reaproveitar persistência, auditoria e CLI já estabilizadas. Histórias deste épico devem testar geração de estrutura, aprovação e registry antes de consolidar a implementação.

## Epic 1: Fundação Local, Modelos e Contratos

O usuário consegue inicializar a base local do `universal-memory` com scaffold Python 3.12+, layout `.umem/`, modelos de domínio, exceções, ports e contratos testáveis que destravam o trabalho paralelo sem acoplar as camadas.

### Story 1.1: Inicializar Scaffold Python do Produto

As a desenvolvedor do universal-memory,
I want inicializar o pacote Python com estrutura, dependências e tooling definidos,
So that o projeto tenha uma base reproduzível para desenvolvimento TDD e trabalho paralelo.

**Acceptance Criteria:**

**Given** um repositório sem scaffold Python completo
**When** o projeto é inicializado com `uv`
**Then** existem `pyproject.toml`, `uv.lock`, `.python-version`, `src/universal_memory/`, `tests/`, `tests/contracts/` e `benchmarks/`
**And** o runtime é Python 3.12+ e as dependências runtime/dev versionadas estão configuradas

**Given** o scaffold inicial
**When** os comandos de verificação são executados
**Then** `ruff`, `pyright` e `pytest` executam sem falhas sobre a base mínima
**And** há pelo menos um teste inicial que falharia se o pacote não fosse importável

### Story 1.2: Definir Modelos de Domínio para Memória

As a agente ou adapter que usa a memória,
I want modelos de domínio validados para fatos, regras, skills latentes, snapshots, auditoria e resumos de contexto,
So that todos os componentes compartilhem contratos consistentes de dados.

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

**Acceptance Criteria:**

**Given** testes CLI escritos antes da implementação
**When** o usuário executa `umem init` em um diretório sem `.umem/`
**Then** o comando cria a estrutura local do projeto
**And** retorna uma mensagem humana indicando os caminhos criados

**Given** um diretório que já contém `.umem/`
**When** o usuário executa `umem init` novamente
**Then** o comando é idempotente e não corrompe arquivos existentes
**And** informa que a memória local já estava inicializada

**Given** o ambiente está offline
**When** `umem init` é executado
**Then** a inicialização funciona sem conectividade externa
