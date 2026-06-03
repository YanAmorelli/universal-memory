# AI Coding Agents - Diretrizes de Instruções Customizadas

Os arquivos de instrução e de regras a nível de projeto funcionam como uma camada de documentação padronizada voltada para inteligências artificiais (comumente denominados "README para IAs"). O propósito fundamental desses arquivos é garantir a persistência de regras de estilo, stacks de tecnologia, arquitetura de software e comandos operacionais (como testes, linters e builds) de forma automatizada, mitigando a necessidade de reinjeção manual de contexto a cada nova sessão de desenvolvimento.

Abaixo apresenta-se o mapeamento técnico das especificações, nomenclaturas padronizadas e compatibilidades dos assistentes de codificação por IA mais adotados no ambiente corporativo atual.

---

## 📊 Tabela Comparativa de Agentes e Instruções

| Provedor / Desenvolvedor | Nome do Agente / CLI | Arquivo de Instrução Principal | Formato & Recursos Especiais |
| :--- | :--- | :--- | :--- |
| **Anthropic** | Claude Code | `CLAUDE.md` | Markdown simples. Suporta escopo dinâmico e localização por subdiretórios. |
| **Anysphere** | Cursor | `.cursorrules`<br>`.cursor/rules/*.mdc` | Markdown para escopo global ou formato `.mdc` (YAML frontmatter + Markdown) com escopo por regras de glob. |
| **Microsoft / GitHub**| GitHub Copilot | `.github/copilot-instructions.md` | Markdown. Localizado no diretório padrão de configurações do repositório. |
| **Codeium** | Windsurf | `.windsurfrules` | Markdown. Suporta também a modularização de regras no diretório `.windsurf/rules/`. |
| **Comunidade (Open)** | Cline / Roo Code | `.clinerules` ou `.clinerules/` | Markdown. O formato de pasta `.clinerules/` viabiliza a segmentação lógica de diretrizes (ex: frontend, testes). |
| **Continue.dev** | Continue | `.continue/rules/*.md` | Markdown de estrutura modular armazenado em `.continue/rules/` e parametrizações globais em `.continue/config.yaml`. |
| **Paul Gauthier** | Aider | `CONVENTIONS.md` | Markdown. Carregado de forma automatizada mediante configuração no parâmetro `read` do arquivo `.aider.conf.yml`. |
| **OpenAI** | **Codex** | `AGENTS.md`<br>`AGENTS.override.md` | Markdown com suporte a comportamento em cascata (herança de diretórios). Permite controle de segurança por arquivos `.rules`. |
| **OpenSource** | **OpenCode** | `AGENTS.md`<br>`.opencode/commands/` | Markdown para prompt de sistema. Suporta injeção de comandos customizados a partir de `.opencode/commands/`. |
| **Open Standard** | Cross-Tool Standard | `AGENTS.md` | Proposta neutra de código aberto voltada para a interoperabilidade de regras entre múltiplos agentes de mercado. |
| **Google** | **Antigravity** | `AGENTS.md` ou `GEMINI.md`<br>`.agents/rules/` | Suporta o padrão neutro `AGENTS.md`, parametrizações exclusivas via `GEMINI.md` e regras estruturadas na pasta `.agents/rules/`. |

---

## 🔍 Detalhamento Técnico das Plataformas

### 1. Anthropic — Claude Code (`CLAUDE.md`)
O **Claude Code** (CLI desenvolvida pela Anthropic) utiliza a convenção do arquivo **`CLAUDE.md`** localizado na raiz ou em subpastas do workspace.
*   **Mecanismo de Escopo:** O agente realiza buscas recursivas ascendentes. Caso o desenvolvimento ocorra dentro de uma pasta específica que possua um arquivo `CLAUDE.md` próprio, tais instruções serão priorizadas e aplicadas de forma localizada.
*   **Conteúdo Recomendado:** Definição objetiva de comandos de build, execução de testes, padrões de linting e regras estritas de arquitetura.

### 2. Anysphere — Cursor (`.cursorrules` & `.mdc`)
O editor **Cursor** gerencia diretrizes através do arquivo clássico **`.cursorrules`** e, mais recentemente, de forma modularizada com a extensão **`.mdc`** na pasta **`.cursor/rules/`**.
*   **Recursos Avançados (.mdc):** Associa metadados em formato YAML (frontmatter) para definir regras de ativação baseadas em correspondência de padrões de arquivos (globs) e gatilhos de comportamento.
*   **Vantagem Operacional:** Reduz a sobrecarga de processamento no contexto do modelo de linguagem (LLM) ao carregar estritamente as regras aplicáveis ao escopo do arquivo sob edição.

### 3. Microsoft / GitHub — Copilot (`.github/copilot-instructions.md`)
O **GitHub Copilot** centraliza o contexto em um arquivo markdown padronizado para controle de versão.
*   **Mecanismo:** Armazenado na pasta `.github/`, o conteúdo é automaticamente injetado como instruções de sistema (system prompt) nas interações realizadas via painel de chat ou geração inline de código.

### 4. Codeium — Windsurf (`.windsurfrules`)
A IDE **Windsurf** opera com mapeamento de regras locais para alinhar a geração de código às preferências de engenharia estabelecidas.
*   **Mecanismo:** Armazenado como `.windsurfrules` na raiz ou modularizado no diretório `.windsurf/rules/`.

### 5. Cline / Roo Code (`.clinerules`)
Os agentes autônomos **Cline** e **Roo Code** executam a leitura de instruções estruturadas em formato de arquivo ou pasta.
*   **Modularidade:** Admite o uso de uma pasta `.clinerules/` para a divisão de regras complexas (ex: `01-architecture.md`, `02-database.md`).
*   **Interoperabilidade:** O agente possui lógica de fallback para detectar e respeitar configurações de outras IDEs (como `.cursorrules`) na ausência de diretrizes específicas.

### 6. Continue.dev — Continue (`.continue/rules/*.md`)
O assistente **Continue** processa regras de projeto de forma granular.
*   **Mecanismo:** Leitura de arquivos `.md` dispostos na pasta `.continue/rules/` da raiz do repositório, integrada às configurações gerais de ambiente declaradas no arquivo principal `config.yaml`.

### 7. Aider (`CONVENTIONS.md`)
O **Aider** adota uma abordagem de documentação explícita de convenções.
*   **Mecanismo:** O arquivo **`CONVENTIONS.md`** descreve os padrões de projeto. O carregamento é parametrizado via linha de comando (`--read CONVENTIONS.md`) ou pela declaração expressa no arquivo de configuração do ambiente local, o `.aider.conf.yml`.

### 8. OpenAI — Codex (`AGENTS.md` & `AGENTS.override.md`)
A plataforma **Codex** opera com um ecossistema focado na rastreabilidade e controle de execução.
*   **Comportamento em Cascata:** Realiza buscas a partir do diretório do usuário (`~/.codex/AGENTS.md`) até o diretório atual do arquivo em edição, concatenando as regras encontradas para formar a árvore final de instruções de sistema.
*   **AGENTS.override.md:** Recurso projetado para interromper a herança de diretórios superiores e impor regras exclusivas para pastas ou branches específicas (ex: períodos de congelamento de produção ou incidentes técnicos).
*   **Controle de Segurança (`.rules`):** Suporta a declaração de regras de sandboxing na pasta `rules/` para gerenciar permissões de execução de comandos de terminal de forma automatizada.

### 9. OpenCode (`AGENTS.md` & `.opencode/`)
O **OpenCode** estruturou um ecossistema com foco em extensibilidade do terminal.
*   **AGENTS.md:** Atua como prompt de sistema do agente, podendo ser inicializado ou atualizado de maneira automatizada através do comando `/init` na interface de linha de comando.
*   **Customização de Ações:** O diretório `.opencode/commands/` e `.opencode/skills/` armazena scripts e markdowns que adicionam comandos operacionais reaproveitáveis ao terminal do agente.

### 10. Padrão Neutro Comunitário (`AGENTS.md`)
Visando conter a fragmentação de formatos de configuração, a iniciativa comunitária de código aberto propõe a adoção do **`AGENTS.md`**.
*   **Objetivo:** Um padrão único e agnóstico de ferramenta, permitindo que múltiplos agentes distintos operem sob as mesmas diretrizes em repositórios compartilhados.

---

## 🛸 Google Antigravity (Arquitetura e Integração)

A plataforma de desenvolvimento **Google Antigravity** adota uma arquitetura estruturada para garantir alta compatibilidade com padrões abertos e eficiência na injeção de contexto. 

Diferente de suposições iniciais sobre a existência de arquivos específicos do tipo `antigravitycli.md`, a arquitetura utiliza convenções consolidadas e neutras para otimizar o desempenho do modelo:

1.  **`AGENTS.md` (Compatibilidade Cruzada):** Leitura nativa do arquivo `AGENTS.md` na raiz do workspace. Havendo este arquivo configurado, o contexto é automaticamente incorporado ao prompt do sistema do agente.
2.  **`GEMINI.md` ou `~/.gemini/GEMINI.md` (Especificidade):** Diretrizes específicas e configurações voltadas aos recursos exclusivos dos modelos Gemini e do ambiente integrado de desenvolvimento. A busca prioritária ocorre na raiz do repositório ou no escopo global do usuário em `~/.gemini/GEMINI.md`.
3.  **Habilidades e Workflows (`.agents/`):** Utilização da estrutura interna do diretório `.agents/` no repositório para o mapeamento de habilidades personalizadas (`.agents/skills/`) e rotinas sequenciais de automação (`.agents/workflows/`).

---

## 💡 Melhores Práticas para Elaboração de Diretrizes

Para mitigar a sobrecarga de tokens e maximizar a assertividade operacional dos agentes de desenvolvimento:
1.  **Declaração da Stack:** Especificar de forma sucinta as linguagens, frameworks e bibliotecas principais adotadas.
2.  **Diretrizes de Qualidade:** Indicar restrições arquiteturais explícitas (ex: "preferir composição à herança", "exigir validação de dados na camada de transporte").
3.  **Comandos de Validação:** Listar os comandos exatos de terminal recomendados para compilação, linting e execução de baterias de testes.
4.  **Políticas de Fluxo:** Estabelecer parâmetros de comportamento esperados (ex: "sempre validar alterações através da suíte de testes antes de considerar a tarefa concluída").

---

> [!NOTE]
> Para a criação ou configuração de um arquivo de instruções unificado (como `AGENTS.md` ou `GEMINI.md`) para o repositório `universal-memory`, recomenda-se a estruturação de um modelo sob medida com as melhores práticas da arquitetura do projeto.
