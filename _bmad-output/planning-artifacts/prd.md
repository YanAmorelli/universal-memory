---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
  - step-06-innovation
  - step-07-project-type
  - step-08-scoping
  - step-09-functional
  - step-10-nonfunctional
  - step-11-polish
  - step-12-complete
  - step-e-01-discovery
  - step-e-02-review
  - step-e-03-edit
releaseMode: phased
inputDocuments: []
documentCounts:
  briefCount: 0
  researchCount: 0
  brainstormingCount: 0
  projectDocsCount: 0
classification:
  projectType: Developer Tool / AI Middleware
  domain: AI Infrastructure / Developer Experience (DevEx)
  complexity: Medium-High
  projectContext: greenfield
workflowType: 'prd'
date: '2026-04-25'
lastEdited: '2026-05-19'
editHistory:
  - date: '2026-05-19'
    changes: 'Validation-guided edit: measurable success criteria, post-MVP import/export, developer-tool sections, measurable NFRs, and implementation-leakage cleanup.'
  - date: '2026-05-19'
    changes: 'Added explicit Backup & Recovery requirements and raised runtime baseline to Python 3.12+.'
---

# Product Requirements Document - universal-memory

**Author:** Yan
**Date:** 2026-04-25

<!-- Este documento será construído de forma incremental durante o workflow de criação de PRD -->

## Executive Summary

O **universal-memory** é uma camada de persistência cognitiva agnóstica projetada para eliminar o "imposto de repetição" no fluxo de trabalho com múltiplos agentes de IA. O sistema atua como um "pen drive de identidade", permitindo que o usuário transporte seu contexto, preferências e histórico de interações entre diferentes sessões e modelos sem fricção. O objetivo central é a coesão operacional: em vez de o usuário se adaptar a cada nova sessão, o ecossistema de agentes se adapta automaticamente ao comportamento e às instruções do usuário através de um motor de sincronização de configurações globais (`AGENTS.md`).

### What Makes This Special

*   **Portabilidade de Identidade:** Desacoplamento total de vendors ou produtos específicos, garantindo que o "cérebro" do usuário seja soberano e migrável.
*   **Adaptação Comportamental Ativa:** Não apenas armazena dados, mas traduz interações em instruções de sistema, atualizando automaticamente arquivos de configuração (`AGENTS.md`) para alinhar todos os agentes auxiliares ao modelo mental do usuário.
*   **Eficiência de Contexto e Custo:** Redução drástica na necessidade de re-explicação de tarefas e conceitos, otimizando o consumo de tokens e o tempo de resposta através de uma memória de curto e longo prazo compartilhada.

## Project Classification

*   **Project Type:** Developer Tool / AI Middleware
*   **Domain:** AI Infrastructure / Developer Experience (DevEx)
*   **Complexity:** Medium-High (Automação de configuração e manipulação de arquivos de sistema)
*   **Project Context:** Greenfield (Novo Produto)

## Success Criteria

### User Success

*   **Redução de Fricção:** Após 5 fatos salvos, o usuário inicia uma tarefa complexa em um novo agente suportado com pelo menos 80% menos texto de orientação inicial do que na linha de base manual.
*   **Adoção por Necessidade:** Após 10 sessões com memória ativa, o usuário mantém o uso do universal-memory em pelo menos 2 ferramentas/agentes suportados e considera a ausência da memória um bloqueio operacional relevante.
*   **Economia de Tokens:** O volume médio de tokens gastos em preâmbulos repetitivos cai pelo menos 60% em 10 sessões comparáveis.

### Business Success

*   **Agnosticismo de Vendor:** O MVP opera com pelo menos 2 hosts/agentes de IA diferentes usando a mesma base de memória e instruções consistentes.
*   **Eficiência Operacional:** O tempo de onboarding de uma nova ferramenta suportada cai para menos de 10 minutos, medido do início da configuração até a primeira leitura bem-sucedida de contexto.

### Technical Success

*   **Agnosticismo de Vendor:** O motor de memória e o arquivo `AGENTS.md` deve ser interpretado e aplicado com sucesso em pelo menos dois provedores de LLM diferentes (ex: OpenAI e Anthropic).
*   **Integridade da Configuração:** O motor de adaptação automática deve atualizar o `AGENTS.md` sem corromper instruções existentes ou criar loops de comportamento conflitantes.
*   **Latência de Injeção:** Recuperação de memória e montagem de contexto adicionam menos de 200ms ao início de uma sessão local em 95% das execuções de teste.

### Measurable Outcomes

*   Diminuição de 80% nas "mensagens de orientação inicial" em novas sessões após os primeiros 5 fatos salvos na memória universal.
*   Zero edições manuais no arquivo `AGENTS.md` pelo usuário após a ativação do motor de adaptação.

## Product Scope

### MVP - Minimum Viable Product

*   **Core Memory Engine:** Sistema de persistência local (JSON/Markdown) para armazenamento de fatos, preferências e histórico consolidado.
*   **Auto-Adaptation Motor:** Um agente/rotina dedicado que analisa a memória e atualiza o arquivo `AGENTS.md` (instruções globais) para refletir o comportamento do usuário.
*   **On-Demand Skill Creation:** Capacidade de gerar novas skills (ferramentas/scripts) baseadas na necessidade detectada durante o fluxo de trabalho.
*   **Universal Interface:** CLI ou protocolo simples para que qualquer agente possa ler/escrever na memória.
*   **Backup & Rollback Guardrails:** Proteção local contra perda de dados antes de alterações automáticas em memórias, regras, skills e arquivos de instrução.

### Growth Features (Post-MVP)

*   **Multi-Machine Sync:** Sincronização em nuvem ou via repositório Git para manter a memória consistente entre diferentes dispositivos.
*   **Memory Import/Export:** Ferramentas de importação/exportação de bases de memória para migração manual, backup externo e portabilidade entre ambientes.
*   **Session Sharing:** Capacidade de compartilhar "pedaços" de memória ou sessões específicas entre diferentes usuários ou times.
*   **Memory Pruning:** Gestão inteligente de memória para evitar que o contexto fique "poluído" com informações obsoletas.

### Vision (Future)

*   **Autonomous Optimization:** Um agente que atua como "Coach de Fluxo de Trabalho", sugerindo automações e melhorias proativas antes mesmo de o usuário sentir a necessidade.
*   **Ecosystem Integration:** Integração nativa com IDEs e terminais para captura passiva de contexto (sem necessidade de input explícito).

### Out of Scope for MVP

*   Sincronização multi-máquina automática.
*   Importação/exportação completa de bases de memória.
*   Interfaces web hospedadas para uso fora de ambientes locais.
*   Compartilhamento de memória entre usuários ou times.
*   Otimização autônoma proativa fora dos fluxos explicitamente aprovados pelo usuário.

## User Journeys

### Journey 1: O Engenheiro Multi-Agente (Acesso à Memória de Curto Prazo)
*   **Persona:** Yan, trabalhando em um repositório complexo com múltiplos sub-agentes.
*   **Cenário:** Yan invoca um novo agente especializado em QA para criar testes de integração.
*   **A Jornada:**
    *   **Início:** O agente lê o arquivo `AGENTS.md` global, que contém a diretriz: "Antes de iniciar, consulte a Short Term Memory deste repositório".
    *   **Ação:** O agente executa a ferramenta de leitura de memória e obtém um resumo: "Yan está usando TDD, o módulo X foi refatorado há 10 minutos e a prioridade atual é a cobertura do endpoint /auth".
    *   **Clímax:** Sem que Yan digite nada, o agente responde: "Entendido, Yan. Li a memória do projeto. Vou focar nos testes de integração para o novo endpoint /auth seguindo o padrão TDD que você estabeleceu".
    *   **Resolução:** Yan economiza ~300 tokens de preâmbulo e 5 minutos de explicação. O trabalho flui imediatamente.

### Journey 2: O Curador de Instruções (Adaptação por Recorrência)
*   **Persona:** O "Agente Adaptador" (rotina de fundo).
*   **Cenário:** Durante o dia, Yan menciona em diferentes chats que prefere usar `tomllib` em vez de `pyyaml` para arquivos de configuração.
*   **A Jornada:**
    *   **Início:** O motor de memória universal registra essas menções como "fatos latentes".
    *   **Ação:** No final do ciclo (ou após a 3ª menção), o Agente Adaptador analisa a recorrência: "O usuário expressou preferência por tomllib 3 vezes em 2 sessões diferentes. Relevância: Alta."
    *   **Clímax:** O agente propõe ou executa uma atualização no `AGENTS.md`: "Adicionada regra: Preferir sempre tomllib para parsing de arquivos TOML".
    *   **Resolução:** Yan não precisa mais lembrar de avisar aos agentes sobre sua biblioteca preferida; o ambiente "aprendeu" o comportamento.

### Journey 3: O Criador de Skills (Expansão de Capacidade)
*   **Persona:** Yan, instruindo o sistema sobre uma nova metodologia (ex: SDD - Spec Driven Development).
*   **Cenário:** Yan explica detalhadamente como quer que as especificações sejam geradas antes do código.
*   **A Jornada:**
    *   **Início:** O sistema detecta uma instrução metodológica complexa e repetitiva.
    *   **Ação:** O Agente de Adaptação identifica que essa lógica pode ser encapsulada em uma ferramenta reutilizável para diminuir a carga cognitiva.
    *   **Clímax:** O sistema gera o boilerplate e a lógica de uma nova skill `generate-sdd-spec` e a registra no sistema.
    *   **Resolução:** Na próxima vez, Yan apenas diz "crie a spec SDD para o módulo Y", invocando a skill em vez de re-explicar a metodologia.

### Journey 4: O Integrador de Novo Agente (Portabilidade entre Vendors)
*   **Persona:** Yan, avaliando uma nova ferramenta de IA no fluxo de desenvolvimento.
*   **Cenário:** Yan quer usar a mesma memória e diretrizes comportamentais em um agente diferente sem reconstruir contexto manualmente.
*   **A Jornada:**
    *   **Início:** Yan executa o fluxo de configuração para um novo host/agente suportado.
    *   **Ação:** O sistema aplica as instruções de inicialização, conecta o agente ao servidor MCP e valida uma leitura de contexto.
    *   **Clímax:** O novo agente responde com as mesmas preferências, restrições e memória de projeto já usadas nos agentes anteriores.
    *   **Resolução:** Yan confirma que a identidade operacional foi portada em menos de 10 minutos, sem reescrever prompts longos.

### Journey Requirements Summary

Essas jornadas revelam a necessidade das seguintes capacidades:
*   **Protocolo de Inicialização:** Regra padronizada no `AGENTS.md` para forçar a leitura da memória de curto prazo (Short Term Memory).
*   **Motor de Análise de Relevância:** Lógica de pontuação baseada em recorrência (2-3 vezes) para transformar fatos efêmeros em regras permanentes.
*   **Repositório de Metadados por Repo:** Capacidade de separar o que é "Universal" do que é específico de um projeto/pasta.
*   **Motor de Geração de Código (Skills):** Infraestrutura para que um agente possa escrever, testar e registrar novos scripts/ferramentas no ambiente do usuário.
*   **Fluxo de Integração de Host:** Procedimento repetível para configurar um novo agente, validar leitura de memória e confirmar consistência de comportamento.

## Domain-Specific Requirements

### Compliance & Safety (Local MVP)
- **Secret & ENV Guardrails:** O sistema deve implementar um motor de detecção passiva para impedir que chaves de API, credenciais ou variáveis de ambiente sensíveis sejam persistidas na memória (curto ou longo prazo) inadvertidamente.
- **Soberania de Dados:** Por operar localmente, o usuário detém controle total sobre os arquivos de persistência, mas deve haver uma interface clara para purga seletiva de fatos.

### Technical Constraints & Memory Model
- **Arquitetura Dual de Memória:** Separação rígida entre **Short Term Memory** (efêmera, específica por projeto/pasta, focada em tarefas e restrições imediatas) e **Universal Memory** (persistente, global, focada em comportamentos e preferências).
- **Gestão de Contexto (Signal-to-Noise):** A memória de curto prazo deve ser sumarizada e priorizada dinamicamente para garantir que a injeção no buffer de contexto do agente não degrade a performance ou cause overflow de tokens.
- **Cross-Vendor Behavior Sync:** O output final da "memória" não é apenas dado bruto, mas a adaptação ativa do arquivo `AGENTS.MD` (ou equivalente), garantindo que agentes de diferentes provedores (OpenAI, Anthropic, etc.) operem sob as mesmas diretrizes comportamentais do usuário.
- **Gate de Estratégia de Recuperação:** A arquitetura deve comparar busca textual local e busca semântica antes de selecionar o padrão de recuperação, usando benchmarks de latência, qualidade de resultado, custo operacional e simplicidade offline.

### Risk Mitigations
- **Context Hygiene:** Rotinas automáticas para remoção de fatos obsoletos na short-term memory após a conclusão de tarefas, evitando "poluição cognitiva".
- **Encapsulamento de Habilidades:** Transformação de instruções complexas recorrentes em "Skills" formais para reduzir o risco de alucinação ou má interpretação de fatos brutos pelo agente.

## Innovation & Novel Patterns

### Detected Innovation Areas
- **Consolidação de Padrões Fragmentados:** O sistema não apenas cria novas capacidades, mas orquestra padrões de mercado existentes (RAG, perfis, system prompts) em uma solução coesa e agnóstico de vendor.
- **Adaptação Comportamental "Invisível":** A métrica de sucesso é o silêncio — a redução da necessidade de o usuário explicar premissas e preferências repetitivas.
- **Aprendizado por Confirmação Ativa:** Introdução de um loop de feedback no final da sessão onde o agente pergunta: "Eu aprendi [X], posso salvar?". O usuário controla a evolução do seu próprio "agente universal" com opções de "Sim", "Sempre" ou "Não".

### Validation Approach
- **Métrica de Repetição:** Monitoramento da frequência de mensagens de correção ou orientação do usuário sobre os mesmos temas em sessões subsequentes.
- **Token Efficiency:** Medição da redução do tamanho do prompt de sistema necessário para atingir o mesmo nível de precisão operacional após a injeção de memória.

### Risk Mitigation
- **Feedback Loop Humano:** Todo fato promovido a "regra" passa por uma confirmação opcional mas recomendada, mitigando a deriva comportamental indesejada (alucinação de preferência).
- **Testes de Regressão de Comportamento:** Verificação contínua se novas regras injetadas não entram em conflito com diretrizes pré-existentes no `AGENTS.md`.

## Developer Tool Specific Requirements

### Language & Runtime Support
- **Primary Runtime:** O MVP deve suportar Python 3.12+ como runtime de execução local.
- **Package Support:** O MVP deve publicar instalação via PyPI e execução isolada via `uvx`.
- **Host Support Matrix:** O MVP deve documentar, para cada host/agente suportado, o arquivo de instruções usado, o método de conexão MCP e o status de leitura/escrita de memória.
- **Offline Operation:** Todas as capacidades essenciais do MVP devem funcionar sem conectividade externa após instalação e configuração local.

### Runtime & Host Support Matrix
| Surface | MVP Support Target | Acceptance Criteria |
| --- | --- | --- |
| Python runtime | Python 3.12+ | `universal-memory --version` executa com sucesso em ambiente Python 3.12 limpo. |
| Package install | PyPI e `uvx` | Instalação via `pip install universal-memory` e execução via `uvx universal-memory --help` documentadas e verificadas. |
| Host 1 | Host baseado em `AGENTS.md` | Host lê contexto de projeto via MCP e respeita instrução de consulta de memória. |
| Host 2 | Host baseado em arquivo de instruções equivalente, como `CLAUDE.md` | Host lê a mesma base de memória e preserva comportamento consistente com o Host 1. |
| Offline mode | CLI, MCP, persistência, auditoria e rollback | Fluxo de leitura, escrita, auditoria e rollback passa com rede desabilitada após instalação local. |

### Installation & Environment
- **Multi-Package Manager Support:** O sistema deve estar disponível via PyPI (`pip install universal-memory`) e suportar execução direta/isolada via `uvx` para Python 3.12+.
- **Local Persistence Layer:** Armazenamento baseado em arquivos legíveis por humanos, com metadados estruturados para automação, auditoria e controle via Git opcional.

### CLI Command Surface
- **Project Initialization:** Comando para inicializar universal-memory em um diretório de projeto e registrar a memória de curto prazo local.
- **Memory Read/Write:** Comandos para gravar fatos, listar fatos ativos, consultar contexto e purgar fatos selecionados.
- **Status & Diagnostics:** Comando para exibir tamanho da base, hosts configurados, regras ativas, skills registradas e último resultado de health check.
- **Host Setup:** Comando para configurar ou verificar integração com arquivos de instrução de agentes suportados.
- **Audit Review:** Comando para listar alterações automáticas feitas em instruções, fatos e skills.

### Communication & Interoperability
- **MCP Protocol Implementation:** A API principal deve seguir o padrão **Model Context Protocol (MCP)** sobre JSON-RPC, permitindo integração plug-and-play com Claude Desktop e outros hosts MCP.
- **CLI/API Parity:** Toda funcionalidade exposta pelo servidor de memória deve ser invocável via comandos CLI equivalentes para automação e uso manual.

### MCP/API Surface
- **Context Retrieval:** Operação MCP para recuperar resumo de memória de curto prazo, preferências universais e regras ativas aplicáveis ao projeto atual.
- **Fact Capture:** Operação MCP para propor ou gravar novos fatos com classificação de escopo, origem e expiração.
- **Rule Proposal:** Operação MCP para propor promoção de fatos recorrentes para regras persistentes, exigindo confirmação quando aplicável.
- **Skill Proposal:** Operação MCP para registrar uma oportunidade de skill latente e consultar o contador de recorrência associado.
- **Health Check:** Operação MCP para verificar disponibilidade da base local, permissões de escrita, versão do servidor e hosts configurados.

### Output Formats & Config Schema
- **Human-Readable Storage:** Arquivos persistidos devem ser legíveis e editáveis por humanos.
- **Structured Metadata:** Fatos, regras, skills latentes e eventos de auditoria devem conter metadados mínimos de escopo, origem, timestamp e status.
- **CLI Output Modes:** Comandos devem suportar saída humana por padrão e saída estruturada para automação.
- **Config Schema:** Configurações locais devem declarar caminhos de memória, hosts habilitados, política de confirmação e limites de contexto.

### Usage Examples
- **Novo Projeto:** `umem init --project .` registra a memória de curto prazo do repositório atual e retorna os caminhos de configuração criados ou detectados.
- **Salvar Fato:** `umem remember --scope project "Priorizar TDD para endpoints de autenticação"` grava um fato local e retorna identificador, escopo e origem.
- **Consultar Contexto:** `umem context --format json` retorna resumo de memória aplicável ao diretório atual, incluindo fatos de projeto, preferências universais e regras ativas.
- **Nova Regra:** `umem rules propose --from-recurrence` lista preferências recorrentes candidatas à promoção e exige resposta explícita: `yes`, `always` ou `no`.
- **Novo Host:** `umem host setup --host <host-id>` detecta arquivo de instruções suportado, propõe alteração, cria snapshot e executa health check de leitura de contexto.
- **MCP Context Retrieval:** Um host MCP invoca a operação de recuperação de contexto e recebe resposta estruturada com `project_summary`, `universal_preferences`, `active_rules` e `audit_reference`.

### Migration & Onboarding
- **Existing Instructions:** O onboarding deve detectar arquivos de instrução existentes e propor alterações sem sobrescrever conteúdo manual sem confirmação.
- **Manual Memory Workflows:** O onboarding deve permitir registrar memórias iniciais a partir de notas locais aprovadas pelo usuário.
- **Rollback Path:** Toda alteração automática em arquivos de instrução deve ter caminho de reversão documentado e auditável.
- **Post-MVP Portability:** Importação/exportação completa de bases de memória fica fora do MVP, mas o modelo de dados deve evitar decisões que impeçam essa capacidade futura.

### Backup & Recovery
- **Snapshot Before Mutation:** Toda alteração automática em memórias, regras, skills ou arquivos de instrução deve criar um snapshot local antes da escrita.
- **Rollback by Scope:** O usuário deve conseguir reverter a última alteração por escopo: projeto, memória universal, regra, skill ou arquivo de instrução.
- **Backup Inspection:** O usuário deve conseguir listar snapshots disponíveis, ver origem da alteração, timestamp, escopo afetado e comando/ação responsável.
- **Retention Policy:** O MVP deve manter uma política local mínima de retenção que proteja contra perda acidental sem exigir sincronização externa.
- **Failure Behavior:** Se o snapshot falhar, a alteração automática não deve prosseguir.

### Skill Creation Engine (Agent Skills Standard)
- **Padrão de Skills:** O sistema deve adotar o padrão **Agent Skills** (conforme agentskills.io), utilizando a estrutura de pastas com `SKILL.md` (instruções), `scripts/` (código executável) e `references/` (contexto).
- **Fluxo de Geração Proativa:**
  1. **Detecção:** O agente identifica quando uma metodologia ou fluxo procedimental está sendo explicado.
  2. **Interpolação de Contexto:** O agente consulta a memória (curto e longo prazo) para consolidar instruções relacionadas ao tema.
  3. **Proposta:** O agente pergunta ao usuário se deseja criar uma Skill formal para encapsular esse conhecimento.
  4. **Aprovação:** Se aprovado, o sistema gera a estrutura de pastas e o arquivo `SKILL.md` seguindo o padrão.
- **Latent Skill Tracking:** Caso o usuário esteja "com pressa", o agente deve registrar um fato de memória resumido com um contador de recorrência. Quando o padrão se repetir *N* vezes, o sistema re-propõe a criação da Skill com base no histórico acumulado.
- **Skill Registry:** Interface para o desenvolvedor listar, testar e versionar as habilidades aprendidas pelo sistema.

## Project Scoping & Phased Development

### MVP Strategy & Philosophy
**MVP Approach:** Focado na resolução imediata do "imposto de repetição" através de persistência local, interface MCP e motor de adaptação comportamental passiva. O objetivo é validar o valor da "invisibilidade" e da economia de tokens em fluxos DevEx.

### MVP Feature Set (Phase 1)
**Core User Journeys Supported:**
- Acesso à Memória de Curto Prazo (Short Term Memory) para injeção imediata de contexto em novas sessões.
- Adaptação por Recorrência: Transformação de fatos latentes em regras no `AGENTS.md` (via aprovação do usuário).
- Criação Proativa de Skills: Detecção e encapsulamento de metodologias no padrão `Agent Skills`.

**Must-Have Capabilities:**
- Servidor MCP (JSON-RPC) para integração nativa.
- CLI para gestão de memória e injeção manual.
- Motor de persistência local legível por humanos e compatível com metadados estruturados.
- Guardrails de segurança para Secrets e ENVs.
- Mecanismo de confirmação de regras (Sim/Sempre/Não).
- Fluxo de configuração de host para pelo menos dois agentes/ferramentas suportados.
- Snapshots locais e rollback para alterações automáticas.

### Post-MVP Features
**Phase 2 (Growth):**
- **Multi-Machine Sync:** Sincronização via Git ou repositório centralizado.
- **Cloud Gateway:** Possibilitar o uso da memória em interfaces web (ChatGPT, Gemini.com) via serviço de armazenamento em nuvem.
- **Memory Import/Export:** Importação/exportação completa de bases de memória para migração manual, backup externo e portabilidade entre ambientes.
- **Session Sharing:** Compartilhamento de contextos específicos entre times.

**Phase 3 (Vision):**
- **Autonomous Optimization:** IA que sugere melhorias proativas no workflow antes do usuário pedir.
- **Native IDE Integration:** Captura passiva de contexto direto do VS Code/JetBrains sem necessidade de comandos explícitos.

### Risk Mitigation Strategy
- **Technical Risks:** Injeção de contexto assíncrona para evitar degradação de performance; separação rígida entre memórias para evitar poluição do buffer de tokens.
- **Market Risks:** Foco total no protocolo aberto MCP para garantir interoperabilidade imediata e evitar lock-in de ecossistema.
- **Resource Risks:** Início 100% local para simplificar a infraestrutura e focar na qualidade do motor de adaptação.

## Functional Requirements

### 1. Core Memory Management (Gestão de Memória)
- **FR1:** O sistema deve persistir fatos e preferências do usuário em armazenamento local legível por humanos e compatível com metadados estruturados.
- **FR2:** O sistema deve diferenciar logicamente entre Memória de Curto Prazo (específica por repositório) e Memória de Longo Prazo (global).
- **FR3:** O sistema deve recuperar contexto por modos de busca locais definidos pela arquitetura, com seleção do modo padrão baseada em benchmark de latência, qualidade de resultado, custo operacional e funcionamento offline.
- **FR4:** O usuário deve poder visualizar e editar manualmente os arquivos de persistência diretamente no sistema de arquivos.
- **FR5:** O sistema deve permitir a purga (deleção) seletiva de fatos específicos ou de bases de memória completas.
- **FR6:** O sistema deve executar rotinas de "Context Hygiene" para arquivar ou remover fatos de curto prazo obsoletos após a conclusão de tarefas.

### 2. Onboarding & Setup (Instalação e Ativação)
- **FR7:** Durante a configuração inicial, o sistema deve permitir que o usuário selecione os provedores de agentes suportados (ex: Claude, Gemini, ChatGPT).
- **FR8:** O sistema deve configurar automaticamente os arquivos de instrução dos agentes selecionados (ex: `CLAUDE.md`, `AGENTS.md`) para inicializar o uso da memória universal imediatamente após a instalação.
- **FR9:** O usuário deve poder inicializar o `universal-memory` em um novo projeto/diretório via comando CLI (ex: `umem init`).

### 3. Command Line Interface (CLI)
- **FR10:** O usuário deve poder consultar o status da memória (tamanho, regras ativas, skills disponíveis) via CLI.
- **FR11:** Toda capacidade exposta pela API/MCP deve ter um comando CLI equivalente para uso manual.

### 4. Model Context Protocol (MCP) Interface
- **FR12:** O sistema deve expor suas capacidades através de um servidor MCP nativo rodando sobre JSON-RPC.
- **FR13:** O sistema deve permitir que agentes externos (ex: Claude Desktop) leiam o contexto atualizado da memória.
- **FR14:** O sistema deve permitir que agentes externos gravem novos fatos e proponham regras na memória via comandos MCP.

### 5. Auto-Adaptation & Synchronization (Sincronização Ativa)
- **FR15:** O sistema deve atualizar dinamicamente as instruções contidas nos arquivos dos agentes (`AGENTS.md`, `CLAUDE.md`) conforme novas regras e fatos são consolidados na memória.
- **FR16:** O sistema deve disponibilizar o resumo da Memória de Curto Prazo no contexto inicial dos agentes e expor, via status ou auditoria, evidência de última leitura, origem do resumo e falhas de injeção quando ocorrerem.
- **FR17:** O sistema deve garantir que a injeção de contexto respeite limites de tamanho (sumarização) para não causar overflow de tokens no LLM.

### 6. Skill Creation Engine (Padrão Agent Skills)
- **FR18:** O sistema deve rastrear e contabilizar "Latent Skills" (instruções/metodologias recorrentes do usuário).
- **FR19:** O sistema deve solicitar aprovação explícita (Sim/Sempre/Não) ao atingir o gatilho de recorrência para criar uma nova Skill.
- **FR20:** O sistema deve gerar a estrutura de pastas e o arquivo `SKILL.md` seguindo o padrão `agentskills.io`.
- **FR21:** O usuário deve poder listar, ativar, editar e desativar Skills registradas através da CLI.

### 7. Security & Safety Guardrails
- **FR22:** O sistema deve escanear passivamente todos os dados recebidos para interceptar chaves de API, credenciais ou variáveis de ambiente sensíveis antes da gravação.
- **FR23:** O sistema deve impedir a persistência de segredos detectados, notificando o usuário sobre a tentativa.
- **FR24:** O sistema deve manter um log de auditoria local de todas as alterações feitas automaticamente nas configurações dos agentes e na criação de novas skills.

### 8. Backup & Recovery Guardrails
- **FR25:** O sistema deve criar snapshot local antes de qualquer alteração automática em memórias, regras, skills ou arquivos de instrução.
- **FR26:** O sistema deve bloquear a alteração automática quando o snapshot prévio falhar.
- **FR27:** O usuário deve poder listar snapshots disponíveis e identificar timestamp, escopo, origem e ação responsável por cada snapshot.
- **FR28:** O usuário deve poder reverter a última alteração automática por escopo via CLI.

## Non-Functional Requirements

### Performance
- **Latência de Recuperação:** Consultas locais de contexto devem responder em menos de 150ms no percentil 95 em uma base de teste com pelo menos 1.000 fatos, medido por benchmark automatizado em máquina de desenvolvimento.
- **Impacto de Inicialização:** Leitura de memória e montagem do contexto inicial não devem adicionar mais de 200ms no percentil 95 ao início de uma sessão de agente configurado, medido por teste de integração local.
- **Benchmark de Recuperação:** Antes da arquitetura final, busca textual local e busca semântica devem ser comparadas em pelo menos 30 consultas representativas, medindo latência, qualidade de resultado em escala 1-5 definida no protocolo de benchmark, custo operacional e funcionamento offline; a estratégia padrão deve ser justificada pelos resultados.

### Security
- **Detecção de Segredos:** O sistema deve bloquear 100% dos padrões de segredo cobertos pela suíte de testes de segurança antes da persistência, medido por testes automatizados com exemplos positivos e negativos.
- **Auditoria de Acesso:** Logs de alteração e alertas de interceptação de segredos devem ser consultáveis via CLI em menos de 2 comandos a partir do diretório do projeto, validado por teste de aceitação.

### Reliability (Confiabilidade)
- **Estratégia de Backup Local:** Antes de qualquer alteração automática em arquivos de instrução ou bases de fatos, o sistema deve criar um snapshot local recuperável e manter pelo menos as 5 versões mais recentes por escopo, validado por teste de rollback.
- **Rollback:** O usuário deve conseguir reverter a última alteração automática em menos de 1 minuto usando CLI, medido por teste de aceitação em arquivos de instrução e base de fatos.

### Integration
- **MCP Compliance:** O servidor deve passar em 100% da suíte de conformidade definida pela arquitetura para o Model Context Protocol, incluindo pelo menos health check, recuperação de contexto, gravação/proposta de fato, proposta de regra e tratamento de erros JSON-RPC.
- **Prontidão para Storage Alternativo:** A lógica de persistência deve isolar operações de leitura, escrita, listagem e versionamento atrás de um contrato interno testável; a troca de backend de armazenamento não deve exigir mudanças no motor de regras, MCP ou CLI, validado por testes de contrato.
- **Host Compatibility:** O MVP deve validar leitura de contexto em pelo menos 2 hosts/agentes suportados, medido por teste manual documentado ou teste de integração quando o host permitir automação.

### Accessibility (Disponibilidade)
- **Offline-First:** CLI, motor de persistência e servidor MCP devem executar leitura, gravação, consulta, auditoria e rollback com rede desabilitada, validado por teste automatizado ou checklist manual reproduzível.
