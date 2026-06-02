# Story 5.1: Modelar Registro de Runtimes e Alvos

Status: ready-for-dev

## Reopened Scope

Esta story foi reaberta porque a implementação anterior cobria apenas o modelo antigo de hosts (`codex`, `claude_code`) e instruction targets. O PRD, arquitetura e épicos foram atualizados em 2026-05-31 para exigir Runtime Registry declarativo, tiers de suporte, targets nativos de instruções e targets nativos de skills.

## Story

Como mantenedor configurando integrações de agentes,
quero um modelo declarativo de registro de runtimes e alvos,
para que cada runtime tenha caminhos, capabilities, tiers de suporte, instruction targets e native skill targets bem definidos.

**Requirements covered:** FR7, FR8, FR15.

## Acceptance Criteria

1. **Modelo declarativo de runtime registry**

   **Dado** um registry declarativo de runtimes,
   **Quando** os adaptadores e modelos Pydantic são definidos,
   **Então** cada runtime declara explicitamente `runtime_id`, display name, support tier, paths padrão globais e de projeto, instruction targets, native skill targets, método/configuração MCP, estratégia de validação, comportamento de mutação/rollback e limitações conhecidas.

2. **Cobertura mínima de runtimes do MVP atualizado**

   **Dado** os requisitos atualizados de multi-runtime,
   **Quando** o registry é carregado,
   **Então** ele inclui Claude Code, OpenCode e Codex/OpenAI-class como Tier 1,
   **E** inclui Cursor e Antigravity como Tier 2,
   **E** mantém IDs estáveis em inglês/snake_case para config, CLI JSON e MCP.

3. **Ownership de targets compartilhados**

   **Dado** o target compartilhado `agents_md`,
   **Quando** múltiplos runtimes consumirem `AGENTS.md`,
   **Então** apenas o target de escrita único do `AGENTS.md` pode escrever no manifesto compartilhado,
   **E** runtimes consumidores apenas referenciam ou validam leitura sem duplicar ou sobrescrever o arquivo independentemente.

4. **Targets nativos de skills**

   **Dado** runtimes que consomem skills ou regras nativamente,
   **Quando** o registry declara capabilities do runtime,
   **Então** cada native skill target declara path, formato, estratégia de instalação, estratégia de drift e política de rollback.

5. **Compatibilidade com o código existente**

   **Dado** projetos já inicializados com `[hosts] enabled = [...]`,
   **Quando** a nova configuração de runtimes for carregada,
   **Então** a implementação deve definir uma decisão explícita de migração ou substituição para a chave antiga,
   **E** não deve manter dois modelos concorrentes sem contrato claro.

## Tasks / Subtasks

- [ ] Criar ou atualizar modelos de domínio para `RuntimeAdapter`, `RuntimeRegistry`, `RuntimeTarget`, `InstructionTarget` e `NativeSkillTarget`.
- [ ] Implementar registry declarativo incluindo `claude_code`, `opencode`, `codex`, `cursor` e `antigravity` com tiers corretos.
- [ ] Atualizar o código que hoje usa `HostName`/`host_ids` para consumir runtime IDs ou registrar uma migração controlada.
- [ ] Garantir single-writer ownership para `AGENTS.md` no novo modelo.
- [ ] Adicionar testes de domínio/config para tiers, paths, targets, native skill targets e IDs estáveis.
- [ ] Atualizar documentação interna da story com qualquer decisão de migração de `[hosts]` para `[runtimes]`.

## Dev Notes

- A story anterior estava implementada como `5-1-modelar-hosts-e-alvos-de-instru-o.md` e foi reaberta porque não cobre OpenCode, Cursor, Antigravity, native skill targets nem Runtime Registry.
- Fontes de verdade: `_bmad-output/planning-artifacts/epics.md` Story 5.1, `_bmad-output/planning-artifacts/architecture.md` Architecture Patch 2, `_bmad-output/planning-artifacts/prd.md` FR7-FR8.
- Não alterar `sprint-status.yaml` para `review` sem implementação e verificação da nova cobertura.
