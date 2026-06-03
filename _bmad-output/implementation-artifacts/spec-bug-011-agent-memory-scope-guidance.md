---
title: 'BUG-011 - Orientar agentes sobre memoria global vs memoria de projeto'
type: 'bugfix'
created: '2026-05-30'
status: 'done'
route: 'dev-story'
baseline_commit: 'b54f69ae2485b60ef72a56ad69a89a56035901e5'
context:
  - '_bmad-output/planning-artifacts/prd.md'
  - '_bmad-output/planning-artifacts/epics.md'
  - '_bmad-output/planning-artifacts/architecture.md'
  - 'src/universal_memory/application/onboarding/setup_project.py'
  - 'src/universal_memory/application/host/setup_host_use_case.py'
---

# BUG-011: Orientar agentes sobre memoria global vs memoria de projeto

## Intent

**Problem:** O motor ja diferencia memoria global (`--scope global`) e memoria de projeto (`--scope project`), e `umem context --scope project` ja inclui fatos globais relevantes junto com fatos locais. Porem a skill padrao e os blocos de host gerados por `umem init` nao ensinam de forma explicita quando um agente deve gravar em cada escopo. Na pratica, um agente pode salvar preferencias pessoais duraveis no projeto ou deixar de salvar aprendizados relevantes ao final de uma atividade. Alem disso, o `SKILL.md` padrao precisa respeitar o contrato de nomes de Agent Skills: skill name deve conter apenas letras minusculas, numeros e hifens, e deve corresponder ao nome da pasta (`use-universal-memory`).

**Approach:** Atualizar a skill padrao `use-universal-memory` e os blocos UMEM gerenciados de `AGENTS.md`/`CLAUDE.md` para documentar uma politica operacional simples: consultar contexto do projeto no inicio; registrar preferencias pessoais/informacoes duraveis reutilizaveis entre projetos em `--scope global`; registrar decisoes, arquitetura, comandos e contexto especificos do repositorio em `--scope project`; nunca registrar segredos, dumps grandes, dados sensiveis ou fatos incertos.

## Product Context

- O PRD define arquitetura dual de memoria: Short Term Memory especifica por projeto/pasta e Universal Memory global focada em comportamentos e preferencias. [Source: `_bmad-output/planning-artifacts/prd.md`, Technical Constraints & Memory Model]
- FR2 exige diferenciar logicamente memoria de curto prazo por repositorio e memoria de longo prazo global. [Source: `_bmad-output/planning-artifacts/prd.md`, Functional Requirements]
- FR8 exige configurar automaticamente arquivos de instrucao para inicializar o uso da memoria universal apos instalacao. [Source: `_bmad-output/planning-artifacts/prd.md`, Functional Requirements]
- FR13/FR14 exigem que agentes externos leiam contexto atualizado e gravem novos fatos via MCP. [Source: `_bmad-output/planning-artifacts/prd.md`, Functional Requirements]
- O PRD tambem descreve aprendizado por confirmacao ativa no fim da sessao, com o agente perguntando ou registrando aprendizados duraveis aprovados. [Source: `_bmad-output/planning-artifacts/prd.md`, Innovation & Novel Patterns]

## Current Implementation Facts

- `AssembleContextSummaryUseCase` ja inclui fatos `project` e `global` quando o contexto solicitado e `project`; fatos globais aparecem na secao `Universal Preferences`, fatos locais em `Project Summary`. [Source: `src/universal_memory/application/memory/assemble_context_summary_use_case.py`]
- `setup_project.py` cria `.umem/skills/use-universal-memory/SKILL.md`, mas a skill padrao hoje exemplifica apenas `umem remember "..." --scope project --tag <tag>` e deve garantir que o frontmatter `name` seja `use-universal-memory`, nao um titulo humano com espacos/maiusculas. [Source: `src/universal_memory/application/onboarding/setup_project.py`]
- `setup_host_use_case.py` injeta blocos gerenciados em `AGENTS.md` e `CLAUDE.md`, mas os textos atuais apenas mandam consultar `umem context`, `umem status` e a skill; nao explicam a politica global vs project. [Source: `src/universal_memory/application/host/setup_host_use_case.py`]
- Testes existentes ja verificam que a skill padrao e criada, que `AGENTS.md`/`CLAUDE.md` preservam conteudo manual fora do bloco gerenciado, e que os manifestos permanecem compactos. [Source: `tests/application/test_setup_project.py`, `tests/application/test_setup_host.py`]

## Boundaries & Constraints

**Always:**

- Preservar Clean Architecture: alteracoes de texto/template ficam em application/onboarding e application/host; nao adicionar logica de negocio aos adapters CLI/MCP.
- Manter `AGENTS.md` compacto; usar regras operacionais curtas e ponteiro para a skill para detalhes.
- Preservar delimitadores `<!-- UMEM: START -->` e `<!-- UMEM: END -->` e a preservacao de conteudo manual fora do bloco gerenciado.
- Preservar a semantica atual de `umem context --scope project`: inclui memoria de projeto e preferencias globais.
- Proteger contra persistencia de segredos: manter orientacao explicita para nao registrar credenciais, tokens, dumps de env, dados sensiveis ou informacao incerta.

**Ask First:**

- Qualquer mudanca no contrato publico dos comandos `umem remember`, `umem context`, MCP tools ou nomes de escopo.
- Qualquer tentativa de criar automacao nova que grave memoria sem acao explicita do agente/usuario.
- Qualquer mudanca que transforme `AGENTS.md` em dump completo de memoria ou replique todo o conteudo da skill.

**Never:**

- Nao adicionar novo storage, novo schema ou novo comando CLI para esta correcao.
- Nao duplicar toda a politica detalhada em `CLAUDE.md`; ele deve continuar sendo delta especifico e apontar para `AGENTS.md`/skill.
- Nao relaxar validadores de host para aceitar manifestos sem referencia operacional a `universal-memory`.

## User Story

As a agente configurado pelo universal-memory,
I want instrucoes claras para escolher entre memoria global e memoria de projeto,
so that preferencias duraveis do usuario sejam reutilizadas entre projetos e aprendizados especificos do repositorio nao poluam a memoria universal.

## Acceptance Criteria

1. Given um projeto inicializado com `umem init`, when `.umem/skills/use-universal-memory/SKILL.md` e gerado, then a skill explica explicitamente que `--scope global` deve ser usado para preferencias pessoais, estilo de comunicacao, informacoes duraveis do usuario, habitos recorrentes e comportamentos que devem valer entre projetos.
2. Given um projeto inicializado com `umem init`, when `.umem/skills/use-universal-memory/SKILL.md` e gerado, then a skill explica explicitamente que `--scope project` deve ser usado para decisoes, arquitetura, comandos, restricoes, tarefas, bugs, dominio e aprendizados especificos do repositorio atual.
3. Given a skill padrao, when um agente le a secao de procedimento, then ela orienta consultar `umem context --scope project` no inicio de uma sessao relevante e revisar aprendizados duraveis durante ou ao final de uma atividade.
4. Given a skill padrao, when ela mostra exemplos de gravacao, then existem exemplos para `umem remember ... --scope global --tag preference` e `umem remember ... --scope project --tag architecture` ou tags equivalentes.
5. Given a skill padrao, when ela descreve guardrails, then ela proibe gravar segredos, credenciais, dados pessoais sensiveis, dumps grandes, logs brutos, informacao incerta e passos transitorios.
6. Given a skill padrao, when `.umem/skills/use-universal-memory/SKILL.md` e gerado, then o frontmatter contem `name: "use-universal-memory"`, usando apenas letras minusculas, numeros e hifens, e o nome corresponde exatamente a pasta `use-universal-memory`.
7. Given `umem host setup codex --yes`, when `AGENTS.md` e gerado ou atualizado, then o bloco UMEM gerenciado inclui orientacao compacta para consultar `umem context --scope project` e escolher `--scope global` vs `--scope project` ao registrar aprendizados, sem virar dump de memoria.
8. Given `umem host setup claude_code --yes`, when `CLAUDE.md` e gerado ou atualizado, then o bloco UMEM gerenciado continua compacto, preserva a orientacao para ler `AGENTS.md` e aponta para a skill como fonte da politica global/local.
9. Given arquivos `AGENTS.md` ou `CLAUDE.md` com conteudo manual fora do bloco UMEM, when host setup roda novamente, then o conteudo manual continua preservado e apenas o bloco gerenciado e substituido.
10. Given testes automatizados, when a suite relevante roda, then ha cobertura protegendo os textos essenciais de escopo na skill padrao, `AGENTS.md`, `CLAUDE.md` e o contrato de nome da skill.

## Tasks & Subtasks

- [x] Atualizar skill padrao em `src/universal_memory/application/onboarding/setup_project.py` (AC: 1, 2, 3, 4, 5, 6)
  - [x] Adicionar secao curta explicando `Memoria Global` vs `Memoria De Projeto`.
  - [x] Atualizar procedimento para consultar contexto no inicio e revisar aprendizados durante/final da atividade.
  - [x] Adicionar exemplos concretos de `umem remember` para `--scope global` e `--scope project`.
  - [x] Garantir que o frontmatter do `SKILL.md` use `name: "use-universal-memory"`, correspondendo ao nome da pasta e obedecendo ao padrao lowercase/hyphen.
  - [x] Manter texto ASCII-only se possivel, seguindo o estilo atual sem acentos nos templates Python existentes.
- [x] Atualizar renderer de `AGENTS.md` em `src/universal_memory/application/host/setup_host_use_case.py` (AC: 7, 9)
  - [x] Inserir orientacao compacta sobre escolher escopo ao registrar aprendizados.
  - [x] Manter manifest block abaixo dos limites de `max_lines` e `max_chars` existentes.
  - [x] Nao adicionar dumps de fatos, IDs ou conteudo dinamico de memoria ao manifesto.
- [x] Atualizar renderer de `CLAUDE.md` em `src/universal_memory/application/host/setup_host_use_case.py` (AC: 8, 9)
  - [x] Preservar o papel de `CLAUDE.md` como delta especifico.
  - [x] Apontar para `AGENTS.md` e para `.umem/skills/use-universal-memory/SKILL.md` como fontes da politica de memoria.
- [x] Atualizar testes de onboarding e host setup (AC: 1-10)
  - [x] `tests/application/test_setup_project.py`: verificar que a skill criada contem `name: "use-universal-memory"`, nao contem `name: "Use Universal Memory"`, contem `--scope global`, `--scope project`, exemplos de `umem remember`, e guardrails de nao salvar segredos/dados sensiveis.
  - [x] `tests/application/test_setup_host.py`: verificar que `AGENTS.md` gerado contem orientacao compacta de escopo e que `CLAUDE.md` referencia a politica sem duplicar regras compartilhadas.
  - [x] Se necessario, ajustar testes CLI de `init` apenas se snapshots de texto humano forem afetados.
- [x] Verificar comportamento em sandbox (AC: 1-10)
  - [x] Rodar `uv run pytest tests/application/test_setup_project.py tests/application/test_setup_host.py`.
  - [x] Rodar `uv run pytest` se os testes focais passarem.
  - [x] Em sandbox limpo, rodar `uv run umem init --yes --hosts codex --hosts claude_code --format json` e inspecionar `.umem/skills/use-universal-memory/SKILL.md`, `AGENTS.md` e `CLAUDE.md`.

## Dev Notes

### Code Map

- `src/universal_memory/application/onboarding/setup_project.py` -- define `DEFAULT_UMEM_SKILL_MARKDOWN`; principal fonte da skill instalada por `umem init`.
- `src/universal_memory/application/host/setup_host_use_case.py` -- define `_render_managed_block` para `AGENTS.md` e `_render_claude_managed_block` para `CLAUDE.md`.
- `tests/application/test_setup_project.py` -- cobre criacao da skill padrao e paths canonicos do layout.
- `tests/application/test_setup_host.py` -- cobre renderizacao, validacao, preservacao manual, compactacao e bloqueio de dumps nos arquivos de host.
- `tests/interfaces/cli/test_init_command.py` -- cobre fluxo CLI `init` com hosts; provavelmente nao precisa de grande alteracao, mas pode falhar se alguma expectativa textual mudar.

### Existing Behavior To Preserve

- `umem context --scope project` deve continuar montando `Project Summary`, `Universal Preferences` e `Active Rules`; nao alterar `AssembleContextSummaryUseCase` nesta story.
- `umem remember` ja aceita `--scope project` e `--scope global`; nao alterar contrato CLI/MCP.
- `AGENTS.md` deve permanecer manifesto compartilhado compacto e ponteiro para documentos/skills, nao base de conhecimento completa.
- `CLAUDE.md` deve continuar contendo deltas especificos de Claude Code e referencia operacional para `universal-memory`, nao uma copia de `AGENTS.md`.
- Mutacoes de host continuam passando por `SafeWriteUseCase`, snapshot e auditoria; nao bypassar pipeline.

### Suggested Text Semantics

Use conteudo equivalente a:

```text
Use `--scope global` para preferencias pessoais, estilo de comunicacao, informacoes duraveis sobre o usuario, habitos recorrentes e comportamentos que devem valer entre projetos.

Use `--scope project` para decisoes, arquitetura, comandos, restricoes, tarefas, bugs, dominio e aprendizados especificos do repositorio atual.

Ao iniciar trabalho relevante, rode `umem context --scope project`. Durante ou ao final da atividade, registre apenas fatos curtos, verificaveis e nao sensiveis que serao uteis depois.
```

Exemplos aceitaveis:

```bash
umem remember "Preferir respostas objetivas em portugues." --scope global --tag preference
umem remember "Este projeto usa Firestore backend-only via Firebase Admin/ADC." --scope project --tag architecture
```

### Test Guidance

- Prefira assertions por substrings essenciais em vez de snapshots completos de Markdown.
- Teste os contratos de intencao: presenca de `--scope global`, `--scope project`, `preference`, `architecture`, `segredos`/`credenciais`, e mencao a revisar aprendizados no fim da atividade.
- Para `AGENTS.md`, verificar que a orientacao aparece dentro dos delimitadores UMEM e que a validacao compacta continua passando.
- Para `CLAUDE.md`, verificar que a referencia a `AGENTS.md`, `umem context`, `umem status` e `.umem/skills/use-universal-memory/SKILL.md` permanece.

## Verification

**Commands:**

- `uv run pytest tests/application/test_setup_project.py tests/application/test_setup_host.py` -- expected: testes focais passam.
- `uv run pytest tests/interfaces/cli/test_init_command.py` -- expected: fluxo CLI init continua passando se afetado por texto/host setup.
- `uv run pytest` -- expected: suite completa passa.
- `uv run ruff check .` -- expected: sem lint errors.
- `uv run ruff format --check .` -- expected: sem alteracoes pendentes.
- `uv run pyright` -- expected: sem erros de tipo.

**Manual Alpha Smoke:**

```bash
SANDBOX="$(mktemp -d /tmp/umem-scope-guidance.XXXXXX)"
PROJECT="$SANDBOX/project"
HOME_SANDBOX="$SANDBOX/home"
mkdir -p "$PROJECT" "$HOME_SANDBOX"
cd "$PROJECT"
HOME="$HOME_SANDBOX" XDG_CONFIG_HOME="$HOME/.config" XDG_DATA_HOME="$HOME/.local/share" \
  uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem init --yes --hosts codex --hosts claude_code --format json
```

Expected inspection:

- `.umem/skills/use-universal-memory/SKILL.md` explains global vs project scope.
- `.umem/skills/use-universal-memory/SKILL.md` uses `name: "use-universal-memory"`; it must not use `name: "Use Universal Memory"`.
- `AGENTS.md` includes compact scope guidance inside the UMEM managed block.
- `CLAUDE.md` remains compact and points to `AGENTS.md`/skill.

## Suggested Review Order

- Skill template first: `src/universal_memory/application/onboarding/setup_project.py`.
- Host block renderers second: `src/universal_memory/application/host/setup_host_use_case.py`.
- Regression tests third: `tests/application/test_setup_project.py` and `tests/application/test_setup_host.py`.
- Optional CLI init regression last: `tests/interfaces/cli/test_init_command.py`.

## Completion Notes

- Status is `done`.
- Implemented alpha hardening only; no new product feature, schema migration, or CLI/MCP contract change.
- Code review found one registry/frontmatter identity mismatch; resolved by making the seeded latent skill name `use-universal-memory`.
- Verification passed: focal tests, CLI init tests, full pytest suite, ruff check, ruff format check, pyright, and sandbox init smoke.
- Sprint status was not updated because all planned sprint stories are already `done`; this spec follows the existing `spec-bug-*` artifact pattern.

## Suggested Review Order

**Default Skill Identity And Policy**

- Start here: canonical slug, frontmatter, and scope guidance are defined together.
  [`setup_project.py:11`](../../src/universal_memory/application/onboarding/setup_project.py#L11)

- Procedure now loads project context and reviews durable learnings.
  [`setup_project.py:34`](../../src/universal_memory/application/onboarding/setup_project.py#L34)

- Scope examples and guardrails protect global/project memory separation.
  [`setup_project.py:42`](../../src/universal_memory/application/onboarding/setup_project.py#L42)

- Seeded registry entry now matches the skill folder and frontmatter.
  [`setup_project.py:169`](../../src/universal_memory/application/onboarding/setup_project.py#L169)

**Host Instruction Blocks**

- `AGENTS.md` remains compact while teaching context lookup and scope choice.
  [`setup_host_use_case.py:704`](../../src/universal_memory/application/host/setup_host_use_case.py#L704)

- `CLAUDE.md` stays a delta and points to shared policy sources.
  [`setup_host_use_case.py:738`](../../src/universal_memory/application/host/setup_host_use_case.py#L738)

**Regression Coverage**

- Onboarding test protects frontmatter, registry name, examples, and guardrails.
  [`test_setup_project.py:14`](../../tests/application/test_setup_project.py#L14)

- Host setup test protects compact `AGENTS.md` scope guidance.
  [`test_setup_host.py:175`](../../tests/application/test_setup_host.py#L175)

- Claude setup test protects delta behavior and policy pointers.
  [`test_setup_host.py:327`](../../tests/application/test_setup_host.py#L327)
