---
title: 'BUG-004 - Rollback de snapshot de criacao inicial'
type: 'bugfix'
created: '2026-05-30'
status: 'done'
baseline_commit: '49edb1de5384942e4532784f918957e997b7d365'
context:
  - '{project-root}/docs/alpha-sandbox-test-plan.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** `umem rollback` falha quando o snapshot mais recente representa o estado anterior de um arquivo que ainda nao existia, porque o manifesto registra o snapshot mas nao ha backup fisico em `.umem/snapshots/files/<id>`. Isso bloqueia rollback logo apos a primeira mutacao de memoria em um sandbox limpo e deixa o fato ativo.

**Approach:** Tornar o rollback capaz de restaurar corretamente snapshots de criacao inicial, removendo o arquivo alvo quando o snapshot indicar que o estado anterior era ausencia do arquivo. Preservar o caminho normal para snapshots com backup fisico e manter auditoria de sucesso/falha.

## Boundaries & Constraints

**Always:** Preservar verificacao de integridade por SHA-256 para snapshots com backup fisico; manter paths resolvidos dentro de `project_root`; manter rollback atomico e auditado; manter compatibilidade com manifestos existentes quando for seguro distinguir criacao inicial.

**Ask First:** Qualquer migracao de schema do manifesto de snapshots, mudanca no contrato publico CLI/MCP, ou decisao de apagar diretorios vazios alem do arquivo alvo.

**Never:** Ignorar erro de backup fisico ausente para snapshots que deveriam ter copia; relaxar protecao contra path traversal; remover auditoria de falha; corrigir BUG-005 ou BUG-006 neste escopo.

## I/O & Edge-Case Matrix

| Scenario | Input / State | Expected Output / Behavior | Error Handling |
|----------|--------------|---------------------------|----------------|
| Criacao inicial | Arquivo alvo nao existia, safe write criou `.umem/memory/facts.jsonl`, snapshot tem hash de bytes vazios e nao tem backup fisico | Rollback remove o arquivo alvo ou o devolve ao estado ausente, retorna sucesso e registra auditoria `success` | Se o alvo virou diretorio ou escapou do root, falha com erro de dominio e auditoria `failure` |
| Snapshot normal | Arquivo alvo existia antes da mutacao e backup fisico existe | Rollback le backup, valida hash e restaura bytes anteriores | Hash mismatch ou backup ausente continuam falhando sem sobrescrever o alvo |

</frozen-after-approval>

## Code Map

- `src/universal_memory/application/security/safe_write_use_case.py` -- Cria snapshots antes da escrita segura; hoje calcula hash de `b""` quando o alvo nao existe.
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py` -- Persiste manifesto e copia fisica; hoje registra snapshot sem arquivo fisico quando o alvo nao existe.
- `src/universal_memory/application/security/rollback_use_case.py` -- Escolhe o snapshot mais recente e sempre tenta ler backup fisico antes de restaurar.
- `src/universal_memory/domain/entities/snapshot.py` -- Modelo de snapshot; possivel local para representar explicitamente se o arquivo existia antes.
- `tests/application/security/test_rollback_use_case.py` -- Cobertura de rollback de dominio, hash mismatch e arquivo alvo deletado.
- `tests/infrastructure/security/test_local_snapshot_repository.py` -- Cobertura do repositorio local, incluindo snapshot de criacao inicial sem copia fisica.
- `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Registro BUG-004 a atualizar apos correcao e verificacao.

## Tasks & Acceptance

**Execution:**
- [x] `src/universal_memory/domain/entities/snapshot.py` e produtores/consumidores relacionados -- Representar de forma segura quando o arquivo existia antes do snapshot, preferindo uma alteracao minima e compativel com manifestos atuais -- Evita confundir arquivo vazio com arquivo inexistente.
- [x] `src/universal_memory/application/security/rollback_use_case.py` -- Restaurar snapshots de criacao inicial removendo o arquivo alvo quando apropriado; manter leitura e hash do backup para snapshots normais -- Corrige o BUG-004 sem relaxar integridade.
- [x] `src/universal_memory/infrastructure/security/local_snapshot_repository.py` -- Persistir/carregar qualquer metadado novo necessario sem quebrar manifestos existentes -- Mantem snapshots locais utilizaveis.
- [x] `tests/application/security/test_rollback_use_case.py` e/ou `tests/infrastructure/security/test_local_snapshot_repository.py` -- Adicionar regressao para safe write de arquivo inexistente seguido de rollback -- Garante que o caso do alpha nao volte a falhar.
- [x] `_bmad-output/implementation-artifacts/alpha-bug-log.md` -- Atualizar BUG-004 com correcao e comandos executados -- Mantem rastreabilidade alpha.

**Acceptance Criteria:**
- Given um projeto limpo onde `umem remember "Fato antes do rollback." --scope project` criou o primeiro arquivo de facts, when `umem rollback --scope project --yes` executa, then o rollback retorna sucesso e o arquivo volta ao estado anterior ausente ou vazio sem o fato ativo.
- Given um snapshot com backup fisico valido, when rollback executa, then o conteudo anterior e restaurado somente depois de validar o hash SHA-256.
- Given um snapshot normal cujo backup fisico esta ausente ou corrompido, when rollback executa, then a operacao falha e nao sobrescreve nem remove o alvo.

## Spec Change Log

## Verification

**Commands:**
- `uv run pytest tests/application/security/test_rollback_use_case.py tests/infrastructure/security/test_local_snapshot_repository.py tests/interfaces/cli/test_rollback_command.py tests/interfaces/mcp/test_server.py::test_real_mcp_rollback_removes_file_created_by_first_remember` -- passed: 27 passed.
- Smoke CLI em sandbox isolado com `umem init`, `umem remember "Fato antes do rollback." --scope project`, `umem rollback --scope project --yes --format json`, e `test ! -e .umem/memory/facts.jsonl` -- passed: rollback `ok=true` e arquivo removido.
- `uv run pytest` -- passed: 395 passed.

## Suggested Review Order

**Rollback Sem Backup Fisico**

- Entrada principal distingue snapshot normal, novo ausente e legado seguro.
  [`rollback_use_case.py:64`](../../src/universal_memory/application/security/rollback_use_case.py#L64)

- Remocao exige hash vazio para nao apagar snapshot inconsistente.
  [`rollback_use_case.py:117`](../../src/universal_memory/application/security/rollback_use_case.py#L117)

- Compatibilidade legado fica limitada a campo ausente com hash vazio.
  [`rollback_use_case.py:126`](../../src/universal_memory/application/security/rollback_use_case.py#L126)

**Snapshot Metadata**

- Snapshot carrega a semantica de existencia anterior com default compativel.
  [`snapshot.py:28`](../../src/universal_memory/domain/entities/snapshot.py#L28)

- Safe write captura existencia antes de registrar o snapshot.
  [`safe_write_use_case.py:65`](../../src/universal_memory/application/security/safe_write_use_case.py#L65)

- Snapshot persistido recebe o metadado junto do hash anterior.
  [`safe_write_use_case.py:168`](../../src/universal_memory/application/security/safe_write_use_case.py#L168)

**Regressoes**

- Testes cobrem novo snapshot, legado sem campo e hash invalido.
  [`test_rollback_use_case.py:234`](../../tests/application/security/test_rollback_use_case.py#L234)

- Reproducao CLI alpha valida primeira mutacao seguida de rollback.
  [`test_rollback_command.py:93`](../../tests/interfaces/cli/test_rollback_command.py#L93)

- Reproducao MCP valida initialize, remember e rollback_scope reais.
  [`test_server.py:205`](../../tests/interfaces/mcp/test_server.py#L205)
