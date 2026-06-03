# Sprint Change Proposal - universal-memory

**Data:** 2026-05-31
**Usuário:** Yan
**Modo de revisão:** Batch
**Escopo:** Moderate

## 1. Issue Summary

### Trigger

O planejamento atual do `universal-memory` cobre um MVP com memória local, CLI, MCP, `AGENTS.md`, `CLAUDE.md`, criação de Agent Skills e dois hosts MVP (`codex` e `claude_code`). Durante a revisão de direção do produto, surgiram quatro mudanças de produto e arquitetura:

1. Adicionar identidade visual de terminal para o `umem`, usando a metáfora de USB/pendrive conectado ao terminal.
2. Adicionar suporte a inglês e tornar inglês o idioma default do produto.
3. Expandir o onboarding para múltiplos runtimes/agentes, incluindo OpenCode, Antigravity e Cursor, com seleção múltipla semelhante ao fluxo do GSD.
4. Instalar skills nas pastas nativas de cada agente quando o agente consumir skills nativamente, por exemplo `.agents/`, `.claude/`, `.cursor/`, `.opencode/` e equivalentes.

### Problem Statement

O plano atual trata suporte a hosts principalmente como configuração de arquivos de instrução (`AGENTS.md`, `CLAUDE.md`) e validação de leitura de contexto. Esse modelo é insuficiente para agentes modernos que possuem diretórios nativos de skills, regras ou configuração. Além disso, o produto precisa ser internacionalizado desde o MVP, com inglês como idioma default, para reduzir retrabalho em CLI, docs e artefatos gerados. A experiência de onboarding também precisa evoluir de seleção simples de hosts para seleção múltipla de runtimes com paths explícitos e feedback visual reconhecível.

### Evidence

- Exemplo de UX desejada: prompt de terminal com seleção múltipla de runtimes, como `Which runtime(s) would you like to install for?`, listando Claude Code, Antigravity, Cursor, OpenCode e outros.
- Requisito explícito do usuário: skills devem ficar nas pastas nativas do agente para consumo nativo, não apenas em `.umem/skills/`.
- PRD atual FR7-FR8 fala genericamente em Claude, Gemini e ChatGPT, mas não modela paths nativos nem runtime registry.
- Arquitetura atual limita o MVP a `codex` e `claude_code` e trata `.cursor`, `.github/copilot-instructions.md`, `.windsurf`, `.continue` e outros como post-MVP.

### Terminologia de Identidade Visual

O nome técnico mais provável para o desenho de USB no terminal é **ASCII art** quando usa apenas caracteres ASCII, **ANSI art** quando inclui cor/estilo via escape codes, e **FIGlet/TOIlet banner** quando o texto/logo é renderizado por fontes de terminal. Para o `umem`, a proposta é usar um **ANSI/ASCII splash banner** pequeno, não dependente de ferramenta externa, com fallback sem cor.

## 2. Impact Analysis

### Checklist Summary

| Item | Status | Finding |
| --- | --- | --- |
| 1.1 Triggering story | [N/A] | Não há story de implementação em execução que tenha revelado o problema. A mudança veio de revisão de produto antes da implementação. |
| 1.2 Core problem | [x] | Novo requisito de produto e ajuste arquitetural de host/runtime/skills. |
| 1.3 Evidence | [x] | Screenshot/referência GSD, requisito de pastas nativas e lacunas em PRD/arquitetura/épicos. |
| 2.1 Current epic impact | [x] | Epic 5 e Epic 6 precisam ser ampliados; Epic 1 e Epic 4 recebem impacto secundário. |
| 2.2 Epic-level changes | [x] | Modificar Epic 5, modificar Epic 6, adicionar suporte transversal de i18n/branding. |
| 2.3 Remaining epics | [x] | Epic 1 precisa suportar config de locale/default language; Epic 4 precisa padronizar mensagens em inglês por default. |
| 2.4 Future epics invalidated | [x] | Nenhum épico fica obsoleto; algumas capacidades antes post-MVP devem entrar no MVP ou em uma fase MVP+ explícita. |
| 2.5 Priority/order | [x] | Runtime registry deve preceder setup de hosts e instalação nativa de skills. |
| 3.1 PRD conflicts | [x] | FR7-FR8, escopo MVP, host matrix, CLI examples e NFRs precisam atualização. |
| 3.2 Architecture conflicts | [x] | Host adapters atuais são estreitos; falta Runtime Registry, Native Skill Target e i18n/message catalog. |
| 3.3 UX impact | [x] | Não há UX visual, mas DevEx CLI muda: splash, idioma default, seleção múltipla. |
| 3.4 Other artifacts | [x] | README/docs, devex interaction spec, testes CLI/MCP e sprint status precisarão atualização após aprovação. |
| 4.1 Direct adjustment | [x] Viable | Melhor caminho: ajustar artefatos e stories sem rollback. |
| 4.2 Rollback | [N/A] | Não há implementação consolidada a reverter. |
| 4.3 MVP review | [x] Viable | MVP continua alcançável, mas precisa classificar quais runtimes são Tier 1 vs Tier 2. |
| 4.4 Recommendation | [x] | Hybrid: Direct Adjustment + MVP scope clarification. |

### Epic Impact

**Epic 1: Fundação Local, Modelos e Contratos**

Impacto secundário. Deve adicionar configuração de idioma default (`en`) e idioma de saída opcional. A estrutura `.umem/config.toml` deve persistir seleção de runtimes e locale.

**Epic 4: Paridade CLI e MCP**

Impacto secundário. Mensagens CLI humanas passam a ter inglês como default; JSON permanece independente de idioma nos nomes de campos. MCP deve receber erro/mensagem estável com códigos e `recovery_hint` em inglês por default.

**Epic 5: Hosts e Sincronização de Instruções**

Impacto primário. Deve deixar de ser apenas `codex` + `claude_code` e passar a modelar runtimes/agentes como adapters com paths nativos, capabilities e installation targets.

**Epic 6: Latent Skills e Gestão de Skills**

Impacto primário. `.umem/skills/` permanece como registry/canonical store, mas a instalação/replicação para consumo nativo deve usar targets por runtime, por exemplo `.agents/skills/`, `.claude/skills/`, `.opencode/skills/`, `.cursor/rules/` quando aplicável.

### Artifact Impact

**PRD:** atualizar escopo MVP, FR7-FR8, FR20-FR21, host support matrix, CLI examples, language requirements e onboarding journey.

**Architecture:** adicionar Runtime Registry, Runtime Adapter, Native Skill Installer, Message Catalog/i18n, Terminal Branding Presenter e estratégia de Tiered Runtime Support.

**Epics:** reescrever Epic 5 e ajustar Epic 6; adicionar stories específicas para idioma default, banner CLI e runtime selection.

**UX/DevEx:** atualizar `_bmad-output/planning-artifacts/devex-interaction-spec.md` se existir ou criar/editar uma seção equivalente nos artefatos para cobrir seleção múltipla, fallback não-interativo e saída JSON.

## 3. Recommended Approach

### Selected Path

**Hybrid: Direct Adjustment + MVP Scope Clarification.**

Não há necessidade de rollback. A mudança deve ser incorporada por atualização de PRD, patch arquitetural e reestruturação dos épicos/stories. O ponto crítico é evitar que “suportar muitos agentes” vire promessa de integração profunda para todos no MVP.

### Tiered Runtime Support

Para controlar escopo, recomenda-se classificar runtimes em tiers:

| Tier | Significado | Critério de aceite |
| --- | --- | --- |
| Tier 1 | Suporte MVP completo | Setup, paths nativos, instruções, skill install quando aplicável, validação local e testes. |
| Tier 2 | Suporte MVP básico | Detecta path, instala instruções/skills quando formato é conhecido, validação pode ser manual/documentada. |
| Tier 3 | Catálogo/documentado | Aparece como planejado ou experimental, sem bloquear MVP. |

Proposta inicial:

| Runtime | Tier recomendado | Path alvo inicial |
| --- | --- | --- |
| Claude Code | Tier 1 | `~/.claude/`, `.claude/`, `CLAUDE.md` conforme escopo |
| OpenCode | Tier 1 | `~/.config/opencode/`, `.opencode/`, `AGENTS.md` conforme suporte |
| Cursor | Tier 2 | `~/.cursor/`, `.cursor/rules/` |
| Antigravity | Tier 2 | `~/.gemini/antigravity/` ou path confirmado por runtime adapter |
| Codex | Tier 1 ou renomear para OpenAI/Codex | `AGENTS.md`, path de config aplicável |
| Gemini | Tier 2 | `~/.gemini/`, `GEMINI.md` quando aplicável |

### Effort Estimate

**Medium.** A maior parte é modelagem e CLI/onboarding; integração profunda por runtime deve ser incremental.

### Risk Level

**Medium.** Risco principal é prometer compatibilidade nativa sem contratos estáveis de cada agente. Mitigação: registry declarativo, tiers e testes por adapter.

### Timeline Impact

Adiciona trabalho antes de concluir Epic 5 e Epic 6. Não bloqueia Epic 1-3, exceto locale básico e estrutura de config.

## 4. Detailed Change Proposals

### PRD Changes

#### Product Scope / MVP

OLD:

```md
* **Auto-Adaptation Motor:** Um agente/rotina dedicado que analisa a memória e atualiza o arquivo `AGENTS.md` (instruções globais) para refletir o comportamento do usuário.
* **On-Demand Skill Creation:** Capacidade de gerar novas skills (ferramentas/scripts) baseadas na necessidade detectada durante o fluxo de trabalho.
```

NEW:

```md
* **Auto-Adaptation Motor:** Um agente/rotina dedicado que analisa a memória e atualiza manifests compartilhados e arquivos nativos de runtimes suportados para refletir o comportamento do usuário sem drift.
* **On-Demand Skill Creation and Native Skill Installation:** Capacidade de gerar Agent Skills canônicas e instalá-las em diretórios nativos de agentes suportados quando o runtime consumir skills nativamente.
* **Multi-Runtime Onboarding:** Fluxo CLI para seleção múltipla de runtimes/agentes, com inglês como idioma default e feedback visual de terminal.
```

Rationale: amplia o MVP para refletir que a unidade de integração é runtime/adapter, não apenas arquivo de instrução.

#### FR7-FR8

OLD:

```md
- **FR7:** Durante a configuração inicial, o sistema deve permitir que o usuário selecione os provedores de agentes suportados (ex: Claude, Gemini, ChatGPT).
- **FR8:** O sistema deve configurar automaticamente os arquivos de instrução dos agentes selecionados (ex: `CLAUDE.md`, `AGENTS.md`) para inicializar o uso da memória universal imediatamente após a instalação.
```

NEW:

```md
- **FR7:** During initial setup, the system must allow the user to select one or more supported runtimes/agents from a registry, including at least Claude Code, OpenCode and Codex/OpenAI-class AGENTS.md hosts, with Cursor and Antigravity represented according to their support tier.
- **FR8:** The system must configure the selected runtimes by writing or updating their supported instruction targets and native skill targets, such as `AGENTS.md`, `CLAUDE.md`, `.agents/`, `.claude/`, `.cursor/`, `.opencode/` or equivalent runtime-specific paths, with snapshot and audit protection before every mutation.
```

Rationale: torna o requisito testável e compatível com instalação nativa.

#### New Language Requirement

NEW:

```md
- **FR29:** The product must use English as the default language for CLI prompts, help text, generated instructions, skill scaffolds and documentation templates, while allowing an explicit locale configuration for other supported languages such as Portuguese.
```

Rationale: evita retrofit de i18n depois que CLI, docs e templates estiverem espalhados.

#### New Branding Requirement

NEW:

```md
- **FR30:** The CLI onboarding experience should include a compact terminal brand element for `umem`, implemented as ANSI/ASCII splash art with a no-color fallback and disabled automatically for JSON/non-interactive output.
```

Rationale: melhora reconhecimento do produto sem quebrar automação.

#### FR20-FR21

OLD:

```md
- **FR20:** O sistema deve gerar a estrutura de pastas e o arquivo `SKILL.md` seguindo o padrão `agentskills.io`.
- **FR21:** O usuário deve poder listar, ativar, editar e desativar Skills registradas através da CLI.
```

NEW:

```md
- **FR20:** The system must generate a canonical Agent Skill structure with `SKILL.md`, optional `scripts/` and optional `references/`, then install or link it into native skill directories for selected runtimes when supported by that runtime adapter.
- **FR21:** The user must be able to list, activate, edit, disable and inspect both canonical skills and per-runtime installed skill targets through CLI and MCP-equivalent capabilities.
```

Rationale: separa skill canônica de instalações específicas por runtime.

### Architecture Changes

#### Add Runtime Registry

NEW section:

```md
### Runtime Registry and Adapter Model

The system must model each supported agent/runtime through a declarative runtime adapter.

Each adapter declares:
- `runtime_id`
- display name
- support tier
- default global paths
- default project paths
- instruction targets
- native skill targets
- MCP configuration method
- validation strategy
- mutation/rollback behavior
- known limitations

Runtime selection is stored in global or project TOML config and drives onboarding, instruction sync and native skill installation.
```

Rationale: evita lógica hardcoded e permite adicionar agentes sem redesenhar o fluxo.

#### Add Native Skill Installation Strategy

NEW section:

```md
### Canonical Skills vs Native Skill Targets

`.umem/skills/` remains the canonical registry and source of truth for generated skills.

Runtime-specific directories are installation targets, not the canonical source. The installer may copy, render, link or generate runtime-specific wrappers depending on adapter support.

Every native skill installation must pass through the mutation pipeline: validate, secret scan, snapshot, atomic write, audit.
```

Rationale: evita drift e mantém rollback/auditoria centralizados.

#### Add i18n / Message Catalog

NEW section:

```md
### Language Defaults and Message Catalog

English is the default product language for CLI, generated files, templates and documentation scaffolds.

Human-facing strings should be routed through a minimal message catalog or presenter layer. JSON field names, domain enums and config keys remain stable English identifiers regardless of locale.

`--format json`, MCP responses and non-interactive output must never include localized labels in machine-readable field names.
```

Rationale: mantém automação estável e permite português sem quebrar contratos.

#### Add Terminal Branding Presenter

NEW section:

```md
### Terminal Branding Presenter

The CLI may render a compact ANSI/ASCII `umem` splash during interactive onboarding.

Rules:
- render only for TTY interactive human output
- disable for `--format json`, `NO_COLOR`, CI and non-interactive mode
- keep width safe for common terminals
- avoid external runtime dependencies for the MVP
```

Rationale: identidade visual sem risco para scripts/agentes.

### Epic Changes

#### Epic 1 Add Story

NEW Story 1.6: Configure Language Defaults

```md
As a user or agent initializing umem,
I want English to be the default language with explicit locale configuration,
So that CLI output, generated instructions and skill templates are consistent and automation-safe.

Acceptance Criteria:
- Given a clean config, when `umem init` runs, then default locale is `en` unless explicitly overridden.
- Given `--format json`, when any command runs, then JSON field names remain stable English identifiers independent of locale.
- Given a supported locale override such as Portuguese, when human output is rendered, then only human-facing labels are localized.
```

#### Epic 4 Add Story

NEW Story 4.6: Render Terminal Branding Safely

```md
As a user running interactive onboarding,
I want a compact umem terminal splash using ANSI/ASCII art,
So that the product has recognizable identity without breaking automation.

Acceptance Criteria:
- Given an interactive TTY, when onboarding starts, then a compact umem USB/terminal splash may be shown.
- Given `--format json`, CI, `NO_COLOR` or non-interactive output, when the command runs, then no splash or ANSI escape codes are emitted.
- Given narrow terminal width, when the splash is rendered, then it falls back to plain text.
```

#### Epic 5 Rewrite Summary

OLD:

```md
O usuário consegue configurar hosts suportados, validar leitura de contexto e manter `AGENTS.md` e `CLAUDE.md` sincronizados sem duplicação, drift ou ownership ambíguo.
```

NEW:

```md
O usuário consegue selecionar múltiplos runtimes/agentes suportados, configurar seus instruction targets e native skill targets, validar leitura de contexto e manter manifests compartilhados e arquivos nativos sincronizados sem duplicação, drift ou ownership ambíguo.
```

#### Epic 5 Story Changes

Story 5.1 should become **Model Runtime Registry and Targets**.

Key AC additions:

- Runtime adapters declare support tier, global paths, project paths, instruction targets and native skill targets.
- Registry includes at least Claude Code, OpenCode and Codex/OpenAI-class AGENTS.md support.
- Cursor and Antigravity are represented as Tier 2 unless validated to Tier 1.

Story 5.6 should become **Multi-Runtime Selection Onboarding**.

Key AC additions:

- Interactive prompt asks: `Which runtime(s) would you like to install for?`
- User can select multiple runtimes via comma-separated or space-separated indices.
- Defaults are safe and visible.
- Non-interactive mode accepts explicit flags such as `--runtime claude-code --runtime opencode`.
- JSON output reports selected runtimes, skipped runtimes, target paths and pending manual steps.

#### Epic 6 Story Changes

Story 6.3 should become **Generate Canonical Skill and Install Native Targets**.

Key AC additions:

- Canonical skill is generated under `.umem/skills/` or configured global canonical store.
- Runtime-specific targets are installed only for selected runtimes that support native skills.
- Each installed target records source skill ID, target runtime, path and audit reference.
- Deactivation disables/removes installed targets according to adapter policy without deleting canonical skill by default.

## 5. Implementation Handoff

### Scope Classification

**Moderate.** This is not a full strategic reset, but it requires coordinated updates to PRD, architecture and epics before implementation.

### Recommended Handoff

1. Product Manager / PRD edit: update PRD requirements, scope, language defaults and runtime support matrix.
2. Architect: patch architecture with Runtime Registry, Native Skill Installer, i18n/presenter rules and terminal branding rules.
3. PO/Planning: update Epic 5 and Epic 6 stories, add language/branding stories and update acceptance criteria.
4. Developer agent: implement only after the above artifacts are approved.

### Implementation Sequencing

1. Add language default and config support early in Epic 1.
2. Add CLI branding presenter in Epic 4 after base CLI exists.
3. Implement Runtime Registry before any concrete runtime adapter.
4. Implement Tier 1 adapters first.
5. Implement native skill installation after canonical skill generation is stable.

### Success Criteria

- `umem init` defaults to English human output.
- Interactive onboarding supports multiple runtime selection.
- Non-interactive onboarding supports explicit runtime flags and JSON output.
- Runtime registry lists Claude Code, OpenCode, Codex/OpenAI-class AGENTS.md support, Cursor and Antigravity with support tiers.
- Canonical skills can be installed into native target directories for selected runtimes with snapshot, audit and rollback.
- Terminal splash never appears in JSON, CI or non-interactive output.

## 6. Recommendation

Approve this proposal, then run the next BMad steps in this order:

1. `bmad-edit-prd` to update the PRD.
2. `bmad-create-architecture` or an architecture patch workflow to update architecture decisions.
3. `bmad-create-epics-and-stories` to update the epic/story breakdown.
4. `bmad-create-story` for the first implementation-ready story after the artifacts are aligned.
