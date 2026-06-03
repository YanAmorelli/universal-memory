---
title: 'BUG-002 - Unificar armazenamento global XDG em umem'
type: 'bugfix'
created: '2026-05-29'
status: 'done'
baseline_commit: '7a0709071768113cf0cbb9ed078b81e19769227e'
context:
  - '{project-root}/_bmad-output/planning-artifacts/architecture.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** O armazenamento global usa raizes diferentes: config em `~/.config/universal-memory/config.toml`, facts/rules em `~/.umem/` e latent skills em `~/.local/share/universal-memory/`. Isso torna o estado global dificil de prever, inspecionar e documentar durante alpha testing.

**Approach:** Padronizar o estado global em caminhos XDG com nome curto `umem`: config global em `~/.config/umem/config.toml` e dados globais em `~/.local/share/umem/memory/*`. Manter o armazenamento por projeto em `<projeto>/.umem/` inalterado.

## Boundaries & Constraints

**Always:** Preservar `global_home` como ponto de injeção para testes; manter escopo de projeto em `.umem`; manter SafeWrite, snapshot e auditoria funcionando para writes globais; atualizar testes que codificam caminhos antigos.

**Ask First:** Qualquer migração/leitura de caminhos legados (`~/.umem`, `~/.config/universal-memory`, `~/.local/share/universal-memory`), mudança de nomes publicos de comandos, ou alteração no contrato de payload CLI/MCP.

**Never:** Adicionar compatibilidade retroativa sem aprovação humana; mover storage de projeto para XDG; relaxar validações de escrita segura para acomodar a mudança de caminho.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Config global padrao | `load_config(project_root=...)` sem `global_config_path`, com `HOME=/tmp/home` | `global_config_path` resolve para `/tmp/home/.config/umem/config.toml` | Config ausente continua retornando `{}` |
| Facts/rules globais | Repositorios com `global_home=/tmp/home` gravam entidades de escopo global | JSONL global fica em `/tmp/home/.local/share/umem/memory/facts.jsonl` e `rules.jsonl` | Falhas de I/O continuam mapeadas para `StorageError` |
| Latent skills globais | `LocalLatentSkillRepository` grava `LatentSkillScope.global_` | JSONL global fica em `/tmp/home/.local/share/umem/memory/latent_skills.jsonl` | SafeWrite global usa a raiz XDG correta para snapshot/auditoria |
| Escopo de projeto | Qualquer repositorio grava entidade de escopo project | Arquivos permanecem em `<projeto>/.umem/memory/*` | Sem regressao de path local |

</frozen-after-approval>

## Code Map

- `src/universal_memory/infrastructure/config/toml_loader.py` -- Define o caminho default da config global e resolve caminhos relativos da config.
- `src/universal_memory/infrastructure/storage/local_fact_repository.py` -- Define raiz global de facts e SafeWrite global atualmente baseado em `global_home/.umem`.
- `src/universal_memory/infrastructure/storage/local_rule_repository.py` -- Define raiz global de rules e SafeWrite global atualmente baseado em `global_home/.umem`.
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py` -- Ja usa XDG para dados globais, mas com nome `universal-memory` em vez de `umem`.
- `tests/infrastructure/config/test_toml_loader.py` -- Protege o caminho default da config global.
- `tests/infrastructure/storage/test_local_fact_repository.py` -- Deve cobrir o novo caminho global de facts.
- `tests/infrastructure/storage/test_local_rule_repository.py` -- Deve cobrir o novo caminho global de rules.
- `tests/infrastructure/storage/test_local_latent_skill_repository.py` -- Contem expectativa atual para `.local/share/universal-memory`.
- `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Registro alpha do BUG-002 a atualizar apos correcao e verificacao.

## Tasks & Acceptance

**Execution:**
- [x] `src/universal_memory/infrastructure/config/toml_loader.py` -- Trocar o default de config global para `Path.home() / ".config" / "umem" / "config.toml"` -- Alinha config ao nome XDG decidido.
- [x] `src/universal_memory/infrastructure/storage/local_fact_repository.py` -- Trocar raiz global para `global_home/.local/share/umem` e ajustar SafeWrite global para essa raiz -- Centraliza facts globais no mesmo data dir XDG.
- [x] `src/universal_memory/infrastructure/storage/local_rule_repository.py` -- Trocar raiz global para `global_home/.local/share/umem` e ajustar SafeWrite global para essa raiz -- Centraliza rules globais no mesmo data dir XDG.
- [x] `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py` -- Trocar o nome do app no data dir global de `universal-memory` para `umem`, inclusive Windows -- Mantem latent skills no mesmo padrao nominal.
- [x] `tests/infrastructure/config/test_toml_loader.py`, `tests/infrastructure/storage/test_local_fact_repository.py`, `tests/infrastructure/storage/test_local_rule_repository.py`, `tests/infrastructure/storage/test_local_latent_skill_repository.py` -- Atualizar/adicionar testes dos caminhos globais -- Previne regressao para as tres raizes antigas.
- [x] `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Marcar BUG-002 como corrigido/verificado com resumo e comandos executados -- Mantem rastreabilidade alpha.

**Acceptance Criteria:**
- Given um `HOME` isolado, when a config global default e carregada, then o caminho usado e `~/.config/umem/config.toml`.
- Given repositorios de facts, rules e latent skills com `global_home` isolado, when entidades globais sao gravadas, then todos os JSONL globais ficam sob `~/.local/share/umem/memory/`.
- Given entidades de escopo project, when repositorios gravam dados, then os caminhos de projeto permanecem sob `<projeto>/.umem/memory/`.
- Given a suite de storage/config relevante, when os testes rodam, then nao ha expectativa restante para `~/.umem`, `~/.config/universal-memory` ou `~/.local/share/universal-memory` como caminho global default.

## Spec Change Log

## Verification

**Commands:**
- `uv run pytest tests/infrastructure/config/test_toml_loader.py tests/infrastructure/storage/test_local_fact_repository.py tests/infrastructure/storage/test_local_rule_repository.py tests/infrastructure/storage/test_local_latent_skill_repository.py` -- expected: testes de caminhos globais passam.
- `uv run pytest tests/interfaces/cli/test_skills_propose.py` -- expected: output humano de proposta global usa `~/.config/umem/config.toml`.
- `uv run pytest` -- expected: suite completa passa sem regressao em CLI/MCP/storage.

## Suggested Review Order

**Global Path Contract**

- Entrada principal da decisão XDG para config global.
  [`toml_loader.py:49`](../../src/universal_memory/infrastructure/config/toml_loader.py#L49)

- Facts globais usam data root XDG e SafeWrite global isolado.
  [`local_fact_repository.py:60`](../../src/universal_memory/infrastructure/storage/local_fact_repository.py#L60)

- Rules globais espelham a mesma estratégia de facts.
  [`local_rule_repository.py:58`](../../src/universal_memory/infrastructure/storage/local_rule_repository.py#L58)

- Latent skills mantem XDG, agora com nome `umem`.
  [`local_latent_skill_repository.py:65`](../../src/universal_memory/infrastructure/storage/local_latent_skill_repository.py#L65)

**SafeWrite And Audit**

- Escritas globais de facts usam `memory/facts.jsonl` sob a raiz XDG.
  [`local_fact_repository.py:327`](../../src/universal_memory/infrastructure/storage/local_fact_repository.py#L327)

- SafeWrite global de rules cria snapshot e auditoria na raiz XDG.
  [`local_rule_repository.py:65`](../../src/universal_memory/infrastructure/storage/local_rule_repository.py#L65)

- Mensagem humana de proposta global aponta para a config nova.
  [`init_command.py:2373`](../../src/universal_memory/interfaces/cli/init_command.py#L2373)

**Regression Coverage**

- Config default protege `~/.config/umem/config.toml`.
  [`test_toml_loader.py:55`](../../tests/infrastructure/config/test_toml_loader.py#L55)

- Facts globais validam JSONL, audit e snapshots no XDG.
  [`test_local_fact_repository.py:70`](../../tests/infrastructure/storage/test_local_fact_repository.py#L70)

- Rules globais cobrem projeto e global separadamente.
  [`test_local_rule_repository.py:30`](../../tests/infrastructure/storage/test_local_rule_repository.py#L30)

- Latent skills validam dados, audit e snapshots globais.
  [`test_local_latent_skill_repository.py:133`](../../tests/infrastructure/storage/test_local_latent_skill_repository.py#L133)

- CLI protege contra regressao para `universal-memory/config.toml`.
  [`test_skills_propose.py:68`](../../tests/interfaces/cli/test_skills_propose.py#L68)
