---
title: 'BUG-001 - Alinhar CLAUDE.md ao validador claude_code'
type: 'bugfix'
created: '2026-05-29'
status: 'done'
baseline_commit: '727312869dfac8fc3e2da73fec7c80508c6abf4b'
context: []
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `umem init` pode gerar `CLAUDE.md` para `claude_code` que falha no proprio `umem status`, porque o renderer nao inclui referencia aceita pelo validador `claude_md_delta_validator` quando nao ha deltas especificos.

**Approach:** Ajustar o bloco gerenciado padrao de `CLAUDE.md` para sempre documentar como Claude Code deve acessar o contexto `universal-memory`, mantendo o arquivo como consumidor de deltas e sem duplicar politicas compartilhadas.

## Boundaries & Constraints

**Always:** Preservar delimitadores UMEM, preservacao de conteudo manual fora do bloco gerenciado, limite compacto do manifesto e filtragem de `CLAUDE.md` para `provider_delta` e `scoped_rule`.

**Ask First:** Qualquer mudanca na semantica do validador, nos nomes de hosts/targets ou no contrato publico de payload CLI/MCP.

**Never:** Copiar regras compartilhadas inteiras para `CLAUDE.md`, relaxar `_has_mcp_reference`, ou remover a orientacao de ler `AGENTS.md` quando existir.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Setup sem deltas | `ConfigureHostCommand(host_id="claude_code", apply=True)` sem instruction blocks | `CLAUDE.md` contem bloco UMEM com referencia a `universal-memory`/`umem context` e `umem status` retorna `success` | N/A |
| Setup com deltas | `provider_delta` e `scoped_rule` presentes | Deltas continuam renderizados e shared policies seguem excluidas | N/A |

</frozen-after-approval>

## Code Map

- `src/universal_memory/application/host/setup_host_use_case.py` -- Contem renderer de `CLAUDE.md`, validador de leitura e lista de referencias MCP aceitas.
- `tests/application/test_setup_host.py` -- Cobertura de setup/check de hosts, incluindo comportamento de `CLAUDE.md` e validacao `claude_code`.
- `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Registro do BUG-001 a atualizar apos correcao e verificacao.

## Tasks & Acceptance

**Execution:**
- [x] `src/universal_memory/application/host/setup_host_use_case.py` -- Incluir referencia operacional fixa a `universal-memory`/`umem context` no bloco gerenciado de `CLAUDE.md` -- Garante que o arquivo gerado satisfaça o validador sem depender de deltas existentes.
- [x] `tests/application/test_setup_host.py` -- Adicionar teste que aplica setup de `claude_code` sem deltas e em seguida valida com `check=True` -- Reproduz o bug do smoke test e protege contra regressao.
- [x] `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Marcar BUG-001 como corrigido/verificado com comandos executados -- Mantem rastreabilidade alpha.

**Acceptance Criteria:**
- Given um projeto sem `CLAUDE.md`, when `claude_code` setup e check rodam em sequencia, then `validation_status` e `checks["managed_block_has_mcp_reference"]` indicam sucesso.
- Given setup `claude_code` com blocos `shared_policy`, `provider_delta` e `scoped_rule`, when `CLAUDE.md` e gerado, then os deltas suportados aparecem e a shared policy continua ausente.

## Spec Change Log

## Verification

**Commands:**
- `uv run pytest tests/application/test_setup_host.py` -- expected: todos os testes de host setup passam.
- `uv run pytest` -- expected: suite completa passa.
- `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem init --hosts claude_code --yes --format json` em sandbox temporaria -- expected: setup `claude_code` retorna `validation_status: success`.
- `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem status --format json` em sandbox temporaria -- expected: `host_validation.claude_code.status: success`.

## Suggested Review Order

- Renderer inclui referencia MCP sem duplicar politica compartilhada.
  [`setup_host_use_case.py:739`](../../src/universal_memory/application/host/setup_host_use_case.py#L739)

- Regressao reproduz setup sem deltas seguido do proprio validador.
  [`test_setup_host.py:322`](../../tests/application/test_setup_host.py#L322)

- BUG-001 registra correcao e verificacao alpha.
  [`alpha-bug-log.md:78`](alpha-bug-log.md#L78)
