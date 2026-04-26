---
stepsCompleted:
  - step-01-init
  - step-02-discovery
  - step-02b-vision
  - step-02c-executive-summary
  - step-03-success
  - step-04-journeys
  - step-05-domain
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

*   **Redução de Fricção:** O usuário consegue iniciar uma tarefa complexa em um novo agente (independente do vendor) e receber uma resposta contextualmente correta sem fornecer preâmbulos ou explicações de contexto prévio.
*   **Adoção por Necessidade:** O produto atinge o "Product-Market Fit" pessoal quando o usuário sente que não consegue trabalhar de forma eficiente sem o "plugin" de memória universal ativo.
*   **Economia de Tokens:** Redução mensurável no volume de tokens gastos em mensagens de sistema (system prompts) repetitivas ao longo de várias sessões.

### Business Success

*   **Agnosticismo de Vendor:** O produto se torna o "padrão de facto" para portabilidade de identidade em fluxos de IA, criando um efeito de rede onde o valor aumenta conforme mais agentes/ferramentas suportam o protocolo.
*   **Eficiência Operacional:** Redução drástica no tempo de onboarding de novas ferramentas ou modelos no fluxo de trabalho do usuário.

### Technical Success

*   **Agnosticismo de Vendor:** O motor de memória e o arquivo `AGENTS.md` devem ser interpretados e aplicados com sucesso em pelo menos dois provedores de LLM diferentes (ex: OpenAI e Anthropic).
*   **Integridade da Configuração:** O motor de adaptação automática deve atualizar o `AGENTS.md` sem corromper instruções existentes ou criar loops de comportamento conflitantes.
*   **Latência de Injeção:** O processo de recuperação de memória e atualização de contexto deve ser quase instantâneo, não adicionando atraso perceptível ao início da sessão.

### Measurable Outcomes

*   Diminuição de 80% nas "mensagens de orientação inicial" em novas sessões após os primeiros 5 fatos salvos na memória universal.
*   Zero edições manuais no arquivo `AGENTS.md` pelo usuário após a ativação do motor de adaptação.

## Product Scope

### MVP - Minimum Viable Product

*   **Core Memory Engine:** Sistema de persistência local (JSON/Markdown) para armazenamento de fatos, preferências e histórico consolidado.
*   **Auto-Adaptation Motor:** Um agente/rotina dedicado que analisa a memória e atualiza o arquivo `AGENTS.md` (instruções globais) para refletir o comportamento do usuário.
*   **On-Demand Skill Creation:** Capacidade de gerar novas skills (ferramentas/scripts) baseadas na necessidade detectada durante o fluxo de trabalho.
*   **Universal Interface:** CLI ou protocolo simples para que qualquer agente possa ler/escrever na memória.

### Growth Features (Post-MVP)

*   **Multi-Machine Sync:** Sincronização em nuvem ou via repositório Git para manter a memória consistente entre diferentes dispositivos.
*   **Session Sharing:** Capacidade de compartilhar "pedaços" de memória ou sessões específicas entre diferentes usuários ou times.
*   **Memory Pruning:** Gestão inteligente de memória para evitar que o contexto fique "poluído" com informações obsoletas.

### Vision (Future)

*   **Autonomous Optimization:** Um agente que atua como "Coach de Fluxo de Trabalho", sugerindo automações e melhorias proativas antes mesmo de o usuário sentir a necessidade.
*   **Ecosystem Integration:** Integração nativa com IDEs e terminais para captura passiva de contexto (sem necessidade de input explícito).

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
    *   **Ação:** No final do ciclo (ou após a 3ª menção), o Agente Adaptador analisa a recorrência: "O usuário expressou preferência por tomllib 3 vezes em 2 sessões differentes. Relevância: Alta."
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

### Journey Requirements Summary

Essas jornadas revelam a necessidade das seguintes capacidades:
*   **Protocolo de Inicialização:** Regra padronizada no `AGENTS.md` para forçar a leitura da memória de curto prazo (Short Term Memory).
*   **Motor de Análise de Relevância:** Lógica de pontuação baseada em recorrência (2-3 vezes) para transformar fatos efêmeros em regras permanentes.
*   **Repositório de Metadados por Repo:** Capacidade de separar o que é "Universal" do que é específico de um projeto/pasta.
*   **Motor de Geração de Código (Skills):** Infraestrutura para que um agente possa escrever, testar e registrar novos scripts/ferramentas no ambiente do usuário.

## Domain-Specific Requirements

### Compliance & Safety (Local MVP)
- **Secret & ENV Guardrails:** O sistema deve implementar um motor de detecção passiva para impedir que chaves de API, credenciais ou variáveis de ambiente sensíveis sejam persistidas na memória (curto ou longo prazo) inadvertidamente.
- **Soberania de Dados:** Por operar localmente, o usuário detém controle total sobre os arquivos de persistência, mas deve haver uma interface clara para purga seletiva de fatos.

### Technical Constraints & Memory Model
- **Arquitetura Dual de Memória:** Separação rígida entre **Short Term Memory** (efêmera, específica por projeto/pasta, focada em tarefas e restrições imediatas) e **Universal Memory** (persistente, global, focada em comportamentos e preferências).
- **Gestão de Contexto (Signal-to-Noise):** A memória de curto prazo deve ser sumarizada e priorizada dinamicamente para garantir que a injeção no buffer de contexto do agente não degrade a performance ou cause overflow de tokens.
- **Cross-Vendor Behavior Sync:** O output final da "memória" não é apenas dado bruto, mas a adaptação ativa do arquivo `AGENTS.MD` (ou equivalente), garantindo que agentes de diferentes provedores (OpenAI, Anthropic, etc.) operem sob as mesmas diretrizes comportamentais do usuário.

### Risk Mitigations
- **Context Hygiene:** Rotinas automáticas para remoção de fatos obsoletos na short-term memory após a conclusão de tarefas, evitando "poluição cognitiva".
- **Encapsulamento de Habilidades:** Transformação de instruções complexas recorrentes em "Skills" formais para reduzir o risco de alucinação ou má interpretação de fatos brutos pelo agente.
