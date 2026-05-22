---
stepsCompleted:
  - step-01-validate-prerequisites
  - step-02-design-epics
  - step-03-create-stories
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
- As interações CLI/MCP devem seguir `_bmad-output/planning-artifacts/devex-interaction-spec.md` para saída humana, JSON parseável, confirmações seguras, erros acionáveis e paridade semântica.
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

Não há UX visual/web/mobile no MVP. A UX relevante é DevEx para CLI, MCP, arquivos locais, confirmações e erros. O contrato canônico de interação está em `_bmad-output/planning-artifacts/devex-interaction-spec.md` e deve ser usado pelas stories de interface como substituto intencional de uma especificação UX visual.

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

## Epic 5: Hosts e Sincronização de Instruções

O usuário consegue configurar hosts suportados, validar leitura de contexto e manter `AGENTS.md` e `CLAUDE.md` sincronizados sem duplicação, drift ou ownership ambíguo.

### Story 5.1: Modelar Hosts e Alvos de Instrução

As a mantenedor configurando integrações de agentes,
I want um modelo explícito de hosts e instruction targets,
So that cada arquivo de instrução tenha ownership claro e não haja escrita duplicada.

**Requirements covered:** FR7, FR8, FR15.

**Acceptance Criteria:**

**Given** os hosts MVP `codex` e `claude_code`
**When** os modelos de configuração de host são definidos
**Then** cada host declara instruction targets suportados, método de configuração MCP, validação de leitura, validação de escrita, rollback e tipo de evento de auditoria
**And** os modelos são validados com Pydantic ou contrato equivalente do domínio

**Given** o target compartilhado `agents_md`
**When** múltiplos hosts suportam `AGENTS.md`
**Then** apenas o target `agents_md` é autorizado a escrever no arquivo compartilhado
**And** hosts consumidores referenciam o mesmo manifesto em vez de gerar cópias próprias

**Given** um target específico como `claude_md`
**When** uma instrução não cabe no manifesto compartilhado
**Then** ela pode ser classificada como delta específico do provider
**And** não duplica o conteúdo completo de `AGENTS.md`

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

**Given** múltiplos hosts configurados
**When** uma regra compartilhada é sincronizada
**Then** `AGENTS.md` é escrito uma única vez por ciclo de mutação
**And** hosts que consomem `AGENTS.md` não produzem cópias divergentes

**Given** uma regra que aponta para conteúdo detalhado
**When** ela é sincronizada
**Then** o arquivo de instrução inclui ponteiro compacto para a fonte canônica
**And** o conteúdo longo permanece em docs ou memória, conforme classificado

### Story 5.6: Fluxo de Seleção de Hosts no Onboarding

As a usuário instalando o universal-memory,
I want selecionar quais hosts/agentes configurar,
So that o setup inicial ative apenas integrações relevantes ao meu fluxo.

**Requirements covered:** FR7, FR8.

**Acceptance Criteria:**

**Given** hosts suportados pelo MVP
**When** o onboarding de host é iniciado
**Then** o usuário pode selecionar `codex`, `claude_code` ou ambos
**And** o sistema registra a seleção em configuração local ou global apropriada
**And** qualquer confirmação de escrita em arquivos de instrução mostra escopo, caminhos relativos, snapshot planejado e evento de auditoria conforme `_bmad-output/planning-artifacts/devex-interaction-spec.md`

**Given** um host selecionado
**When** o setup é concluído
**Then** o sistema executa ou agenda validação de leitura de contexto
**And** informa claramente quais passos manuais permanecem, se houver

**Given** um host não selecionado
**When** o sistema sincroniza regras futuras
**Then** ele não cria nem altera arquivos específicos desse host
**And** mantém possibilidade de configuração posterior sem migração manual

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

### Story 6.3: Gerar Estrutura Agent Skills

As a usuário que aprovou uma nova skill,
I want que o sistema gere a estrutura padrão de Agent Skills,
So that a metodologia recorrente vire um artefato reutilizável por agentes.

**Requirements covered:** FR20.

**Acceptance Criteria:**

**Given** uma proposta de skill aprovada
**When** a geração é executada
**Then** o sistema cria uma pasta de skill com `SKILL.md`
**And** inclui diretórios opcionais `scripts/` e `references/` somente quando necessários ao escopo aprovado

**Given** o conteúdo consolidado da latent skill
**When** `SKILL.md` é gerado
**Then** ele contém nome, descrição, gatilhos de uso e instruções operacionais claras
**And** usa caminhos relativos em specs, código e docs conforme regra do projeto

**Given** já existe uma skill com nome conflitante
**When** a geração é solicitada
**Then** o sistema propõe nome alternativo ou atualização controlada
**And** não sobrescreve conteúdo existente sem confirmação e snapshot

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
