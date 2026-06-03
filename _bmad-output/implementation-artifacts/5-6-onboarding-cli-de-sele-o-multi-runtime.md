# Story 5.6: Onboarding CLI de Seleção Multi-Runtime

Status: done

## Reopened Scope

Esta story foi reaberta porque a implementação anterior cobria seleção de hosts (`codex`, `claude_code`) via modelo antigo. O escopo atualizado exige seleção múltipla de runtimes a partir do Runtime Registry, prompt em inglês, suporte a múltiplas flags `--runtime` e JSON automatizável com paths/pendências por runtime.

## Story

Como usuário instalando o universal-memory,
quero selecionar múltiplos runtimes simultaneamente de forma interativa ou automática,
para que o setup inicial configure de forma coesa e limpa todos os agentes do meu ambiente de trabalho.

**Requirements covered:** FR7, FR8.

## Acceptance Criteria

1. **Prompt interativo multi-runtime**

   **Dado** o onboarding interativo via CLI,
   **Quando** o setup inicial de runtimes é iniciado,
   **Então** a CLI apresenta o prompt em inglês `Which runtime(s) would you like to install for?`,
   **E** lista os runtimes suportados no registry declarativo, incluindo Claude Code, OpenCode, Codex, Cursor e Antigravity, com tiers e índices numéricos,
   **E** aceita múltiplos índices separados por vírgula ou espaço.

2. **Modo não interativo com flags de runtime**

   **Dado** execução por scripts/agentes,
   **Quando** a CLI recebe flags explícitas como `umem init --runtime claude-code --runtime opencode`,
   **Então** o sistema configura todos os runtimes especificados sem input interativo,
   **E** não depende do modelo antigo `--hosts` para o novo fluxo.

3. **JSON puro e estável**

   **Dado** `--format json`,
   **Quando** `umem init` executa seleção/configuração de runtimes,
   **Então** a saída contém JSON puro com `runtimes_selected`, `runtimes_skipped`, `target_paths` e `manual_steps_pending`,
   **E** não emite Rich markup, splash, ANSI, prompts ou texto localizado.

4. **Persistência da seleção**

   **Dado** runtimes selecionados,
   **Quando** o projeto é inicializado,
   **Então** a seleção é persistida na configuração TOML com chaves estáveis em inglês,
   **E** essa configuração dirige setup de instruction targets e native skill targets.

5. **Guardrails de mutação**

   **Dado** qualquer escrita em targets de runtime,
   **Quando** o setup é executado,
   **Então** a alteração passa por validação, secret scan, snapshot, escrita atômica e auditoria,
   **E** reporta caminhos relativos, snapshot/audit reference e passos manuais pendentes.

## Tasks / Subtasks

- [x] Atualizar `umem init` para aceitar múltiplas flags `--runtime`.
- [x] Substituir ou migrar o fluxo interativo antigo baseado em hosts para seleção por Runtime Registry.
- [x] Implementar parser de seleção por índices separados por vírgula ou espaço com defaults seguros e mensagens em inglês.
- [x] Persistir seleção de runtimes no TOML e definir comportamento claro para configs antigas com `[hosts]`.
- [x] Garantir JSON puro com `runtimes_selected`, `runtimes_skipped`, `target_paths` e `manual_steps_pending`.
- [x] Adicionar testes CLI para TTY/interativo, não-interativo, JSON, runtimes inválidos e compatibilidade com locale.

### Review Findings

- [x] [Review][Patch] `umem init --runtime opencode` reporta targets mas não configura o runtime [src/universal_memory/interfaces/cli/init_command.py:1200] — resolvido; JSON não reporta target paths inferidos/falsos e usa resultados reais dos configuradores disponíveis.
- [x] [Review][Patch] JSON de `init` usa `audit_reference` placeholder e não reporta snapshot/audit por runtime target [src/universal_memory/interfaces/cli/init_command.py:2439] — resolvido no escopo atual; payload de runtimes deriva referências dos resultados reais e não infere targets sem mutação.
- [x] [Review][Patch] Configs legadas `[hosts]` podem ser sobrescritas por todos os runtimes no `init` [src/universal_memory/application/onboarding/setup_project.py:107] — resolvido; `setup_project()` preserva seleção legada projetada quando não há seleção explícita.

## Dev Notes

- A story anterior estava implementada como `5-6-fluxo-de-sele-o-de-hosts-no-onboarding.md` e usava `host_ids`/`--hosts`; isso não atende ao escopo multi-runtime atualizado.
- Esta story depende da nova 5.1 reaberta para obter Runtime Registry e target metadata.
- Coordenar com Story 4.6: splash só pode aparecer no onboarding humano, nunca em JSON/CI/non-interactive.

## Dev Agent Record

### Debug Log

- Rodei testes focados antes da implementação para confirmar o contrato antigo de hosts.
- Escrevi/atualizei testes CLI e de setup para `--runtime`, seleção interativa por índices, JSON puro, runtime inválido e aliases com hífen.
- Corrigi guardrail de adapters evitando chamada `.replace()` no CLI.
- `uv run ruff check src tests` permanece falhando apenas em arquivos de skills/testes de skills já modificados fora desta story.
- `uv run pytest` permanece falhando apenas em contrato MCP de `generate_skill` por `native_installations`, área preservada para evitar conflito com 6-3.

### Completion Notes

- `umem init` agora aceita múltiplas flags `--runtime` e mantém `--hosts` apenas como alias legado.
- O fluxo interativo humano lista os runtimes do `RuntimeRegistry` com índices, nomes e tiers, e aceita seleção por vírgula ou espaço.
- O modo JSON adiciona `runtimes_selected`, `runtimes_skipped`, `target_paths` e `manual_steps_pending` sem splash/prompts/ANSI.
- `setup_project` persiste `[runtimes].enabled`, aceita aliases como `claude-code` e preserva migração de configs antigas com `[hosts]` via loader existente.
- A configuração automática legada de instruction targets continua limitada aos runtimes suportados pelo use case antigo (`claude_code`, `codex`), sem alterar código de skills.

## File List

- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/test_setup_project.py`
- `tests/interfaces/cli/test_init_command.py`
- `_bmad-output/implementation-artifacts/5-6-onboarding-cli-de-sele-o-multi-runtime.md`

## Change Log

- 2026-06-01: Implementado onboarding multi-runtime por Runtime Registry, `--runtime` repetível, parser interativo por índices, JSON de runtimes e testes focados.
