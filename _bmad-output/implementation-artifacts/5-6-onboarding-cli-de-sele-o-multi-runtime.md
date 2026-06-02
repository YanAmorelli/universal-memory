# Story 5.6: Onboarding CLI de Seleção Multi-Runtime

Status: ready-for-dev

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

- [ ] Atualizar `umem init` para aceitar múltiplas flags `--runtime`.
- [ ] Substituir ou migrar o fluxo interativo antigo baseado em hosts para seleção por Runtime Registry.
- [ ] Implementar parser de seleção por índices separados por vírgula ou espaço com defaults seguros e mensagens em inglês.
- [ ] Persistir seleção de runtimes no TOML e definir comportamento claro para configs antigas com `[hosts]`.
- [ ] Garantir JSON puro com `runtimes_selected`, `runtimes_skipped`, `target_paths` e `manual_steps_pending`.
- [ ] Adicionar testes CLI para TTY/interativo, não-interativo, JSON, runtimes inválidos e compatibilidade com locale.

## Dev Notes

- A story anterior estava implementada como `5-6-fluxo-de-sele-o-de-hosts-no-onboarding.md` e usava `host_ids`/`--hosts`; isso não atende ao escopo multi-runtime atualizado.
- Esta story depende da nova 5.1 reaberta para obter Runtime Registry e target metadata.
- Coordenar com Story 4.6: splash só pode aparecer no onboarding humano, nunca em JSON/CI/non-interactive.
