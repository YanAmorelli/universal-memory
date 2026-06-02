# Story 5.1: Modelar Registro de Runtimes e Alvos

Status: done

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

- [x] Criar ou atualizar modelos de domínio para `RuntimeAdapter`, `RuntimeRegistry`, `RuntimeTarget`, `InstructionTarget` e `NativeSkillTarget`.
- [x] Implementar registry declarativo incluindo `claude_code`, `opencode`, `codex`, `cursor` e `antigravity` com tiers corretos.
- [x] Atualizar o código que hoje usa `HostName`/`host_ids` para consumir runtime IDs ou registrar uma migração controlada.
- [x] Garantir single-writer ownership para `AGENTS.md` no novo modelo.
- [x] Adicionar testes de domínio/config para tiers, paths, targets, native skill targets e IDs estáveis.
- [x] Atualizar documentação interna da story com qualquer decisão de migração de `[hosts]` para `[runtimes]`.

### Review Findings

- [x] [Review][Patch] `sync_instructions` quebra após `umem init` padrão com Runtime Registry completo [src/universal_memory/application/host/sync_instructions_use_case.py:366] — resolvido; sync legado filtra runtimes não suportados e opera apenas nos hosts sincronizáveis.
- [x] [Review][Patch] Cursor/Antigravity burlam validação Pydantic com `InstructionTarget.model_construct()` [src/universal_memory/domain/entities/runtime.py:341] — resolvido; targets genéricos agora usam `RuntimeInstructionTarget` validado.
- [x] [Review][Patch] Testes de native skill targets não cobrem Antigravity apesar do registry declarar target [tests/application/skills/test_generate_skill.py:270] — resolvido; cobertura inclui target nativo de Antigravity.

## Dev Notes

- A story anterior estava implementada como `5-1-modelar-hosts-e-alvos-de-instru-o.md` e foi reaberta porque não cobre OpenCode, Cursor, Antigravity, native skill targets nem Runtime Registry.
- Fontes de verdade: `_bmad-output/planning-artifacts/epics.md` Story 5.1, `_bmad-output/planning-artifacts/architecture.md` Architecture Patch 2, `_bmad-output/planning-artifacts/prd.md` FR7-FR8.
- Não alterar `sprint-status.yaml` para `review` sem implementação e verificação da nova cobertura.

## Dev Agent Record

### Debug Log

- 2026-06-01: Testes RED adicionados para Runtime Registry, tiers, native skill targets, single-writer de `AGENTS.md` e migração `[hosts]` -> `[runtimes]`.
- 2026-06-01: `uv run pytest tests/domain/test_host.py tests/application/test_setup_project.py tests/infrastructure/config/test_toml_loader.py` falhou inicialmente por ausência de `universal_memory.domain.entities.runtime`, confirmando RED.
- 2026-06-01: Ajustado contrato para permitir consumidores read-only de `AGENTS.md` via target de runtime, mantendo `InstructionTarget` legado validando writer real.
- 2026-06-01: `uv run ruff check src tests` e `uv run pytest` passaram.

### Completion Notes

- Criado modelo de domínio `runtime.py` com `RuntimeId`, `RuntimeSupportTier`, `RuntimeTarget`, `NativeSkillTarget`, `RuntimeInstructionTarget`, `RuntimeAdapter`, `RuntimeRegistry` e `default_runtime_registry()`.
- Registry declarativo inclui `claude_code`, `opencode`, `codex`, `cursor` e `antigravity`; Claude Code/OpenCode/Codex como Tier 1; Cursor/Antigravity como Tier 2.
- Ownership de `AGENTS.md`: `codex` é o único writer `single_writer`; `opencode` referencia `AGENTS.md` como consumidor read-only no modelo de runtime.
- Decisão de migração: `[runtimes] enabled = [...]` é a chave canônica nova; `[hosts] enabled = [...]` permanece apenas como entrada legada. `load_config()` projeta `[hosts]` para `[runtimes]` quando a chave nova não existe, `setup_project()` grava `[runtimes]`, `sync_instructions` lê/escreve `[runtimes]`, e `update --migrate` materializa `[runtimes]` preservando `[hosts]` legado.
- Mantida compatibilidade operacional de CLI/use cases existentes que ainda expõem nomes `host_id`/`--hosts`, tratando esses valores como IDs estáveis de runtime até uma renomeação pública posterior.

## File List

- `src/universal_memory/domain/entities/runtime.py`
- `src/universal_memory/domain/entities/__init__.py`
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/application/host/sync_instructions_use_case.py`
- `src/universal_memory/application/update/update_use_cases.py`
- `src/universal_memory/infrastructure/config/toml_loader.py`
- `tests/domain/test_host.py`
- `tests/application/test_setup_project.py`
- `tests/application/test_update_use_cases.py`
- `tests/infrastructure/config/test_toml_loader.py`
- `tests/interfaces/cli/test_init_command.py`
- `tests/interfaces/cli/test_update_command.py`
- `_bmad-output/implementation-artifacts/5-1-modelar-registro-de-runtimes-e-alvos.md`

## Change Log

- 2026-06-01: Implementado Runtime Registry declarativo, migração controlada `[hosts]` -> `[runtimes]`, single-writer de `AGENTS.md` e testes de domínio/config/update/CLI relacionados.
