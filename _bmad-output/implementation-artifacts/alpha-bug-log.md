# Alpha Bug Log

## Objetivo

Este arquivo centraliza os bugs encontrados durante a fase de alpha testing do `universal-memory`.

Uso combinado sugerido:

- registrar novos bugs aqui assim que forem observados;
- investigar bugs ambíguos com `bmad-investigate`;
- corrigir bugs pequenos com `bmad-quick-dev`;
- corrigir bugs ligados a story/sprint com `bmad-dev-story` ou fluxo normal de story.

## Status

- `open`: bug confirmado e ainda nao corrigido
- `investigating`: bug em analise
- `blocked`: depende de decisao ou contexto externo
- `fixed`: correcao aplicada
- `verified`: correcao validada manualmente ou por teste relevante
- `deferred`: bug conhecido, mas adiado

## Severidade

- `high`: bloqueia onboarding, quebra fluxo principal ou compromete confianca basica
- `medium`: nao bloqueia tudo, mas causa falha relevante, UX ruim ou comportamento inconsistente
- `low`: aresta menor, cosmetica ou melhoria de ergonomia

## Template

```md
## BUG-XXX - Titulo curto

- Status: verified
- Severidade: medium
- Superficie: CLI | MCP | Packaging | Docs | Global State | Host Setup
- Encontrado em: 2026-05-29
- Contexto: onde e como apareceu

### Reproducao

1. passo 1
2. passo 2
3. passo 3

### Esperado

- comportamento esperado

### Obtido

- comportamento observado

### Evidencias

- caminhos de arquivo
- output relevante
- auditoria relevante

### Hipotese / Causa Raiz

- preencher quando houver

### Correcao

- preencher quando corrigido

### Verificacao

- testes executados
- validacao manual
```

## Bugs

## BUG-001 - `CLAUDE.md` gerado nao satisfaz o proprio validador de claude_code

- Status: verified
- Severidade: high
- Superficie: Host Setup
- Encontrado em: 2026-05-29
- Contexto: durante smoke test manual em projeto limpo, `umem init` configurou `claude_code`, mas o `umem status` retornou falha para esse host.

### Reproducao

1. criar uma pasta vazia
2. rodar `umem init`
3. aceitar configuracao de `claude_code`
4. rodar `umem status`

### Esperado

- `claude_code` configurado com status `success`
- `CLAUDE.md` gerado em conformidade com a validacao do host

### Obtido

- `claude_code` aparece com status `failure`
- a validacao acusa ausencia de referencia a `universal-memory`, `MCP/FastMCP` ou comandos como `umem context/status`

### Evidencias

- projeto de teste: `/Users/amorelliaoyan/projects/smart-studio/app`
- arquivo: `/Users/amorelliaoyan/projects/smart-studio/app/CLAUDE.md`
- auditoria: `4bba24fd-48e4-4dfd-812f-6e60136e1f70`
- auditoria apos reinstalacao limpa: `996761b9-5258-478c-a979-667fcea58476`
- evento: `host_validation.claude_code`
- metodo: `claude_md_delta_validator`

### Hipotese / Causa Raiz

- o renderer de `CLAUDE.md` gera um bloco minimo sem referencia MCP quando nao ha deltas especificos
- o validador exige essa referencia sempre
- ha inconsistencia entre geracao e validacao

### Correcao

- `CLAUDE.md` gerado para `claude_code` agora inclui uma referencia operacional fixa a `universal-memory`, `umem context`, `umem status` e MCP/FastMCP no bloco UMEM gerenciado.
- Adicionado teste de regressao cobrindo setup de `claude_code` sem deltas seguido de `check=True` com sucesso.

### Verificacao

- `uv run pytest tests/application/test_setup_host.py` -> 15 passed
- smoke em sandbox temporaria: `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem init --hosts claude_code --yes --format json` -> `validation_status: success`
- smoke em sandbox temporaria: `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem status --format json` -> `host_validation.claude_code.status: success`
- `uv run pytest` -> 386 passed

## BUG-003 - Mensagem de `umem skills list` sem skills sugere comando pouco acionavel

- Status: verified
- Severidade: low
- Superficie: CLI
- Encontrado em: 2026-05-29
- Contexto: durante smoke test em projeto limpo, `umem skills list` retornou estado vazio com uma sugestao que exige um `latent_skill_id` que o usuario ainda nao tem.

### Reproducao

1. criar projeto limpo
2. rodar `umem init`
3. rodar `umem skills list`

### Esperado

- mensagem orientar um proximo passo executavel por um usuario sem skills registradas
- exemplo: explicar como latent skills surgem ou sugerir um fluxo anterior que gere/proponha uma candidata

### Obtido

- `Nenhuma skill registrada.`
- `Execute `umem skills propose <latent_skill_id>` para revisar uma skill candidata.`

### Evidencias

- projeto de teste: `/Users/amorelliaoyan/projects/smart-studio/app`
- comando: `umem skills list`

### Hipotese / Causa Raiz

- a mensagem assume que ja existe uma latent skill candidata conhecida, mas no onboarding limpo nao existe ID disponivel para o usuario

### Correcao

- A recomendacao padrao do estado vazio de `umem skills list` agora explica que latent skills aparecem quando o `universal-memory` registra padroes recorrentes.
- A mensagem sugere um proximo passo executavel sem exigir ID inexistente: continuar registrando memoria com `umem remember "..."` e rodar `umem skills list` novamente para acompanhar as skills quando uma candidata aparecer.
- Testes de application e CLI foram atualizados para proteger contra a reintroducao da sugestao direta de `umem skills propose <latent_skill_id>` no estado vazio.

### Verificacao

- `uv run pytest tests/application/skills/test_list_skills.py tests/interfaces/cli/test_skills_list.py` -> 10 passed

## BUG-002 - Estrategia de armazenamento global usa caminhos diferentes por tipo de dado

- Status: verified
- Severidade: medium
- Superficie: Global State
- Encontrado em: 2026-05-29
- Contexto: ao inspecionar o estado global no macOS, ficou evidente que config, facts/rules e latent skills usam raizes globais diferentes.

### Reproducao

1. inspecionar o codigo dos repositórios locais e do loader de config
2. comparar os caminhos globais usados por config, facts, rules e skills

### Esperado

- estrategia global consistente e previsivel para todos os tipos de armazenamento

### Obtido

- config global em `~/.config/universal-memory/config.toml`
- facts e rules globais em `~/.umem/`
- latent skills globais em `~/.local/share/universal-memory/`

### Evidencias

- `src/universal_memory/infrastructure/config/toml_loader.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `src/universal_memory/infrastructure/storage/local_rule_repository.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`

### Hipotese / Causa Raiz

- a evolucao incremental do projeto deixou convencoes globais diferentes entre subsistemas

### Correcao

- Config global padrao movida para `~/.config/umem/config.toml`.
- Facts, rules e latent skills globais agora usam `~/.local/share/umem/memory/`.
- Escritas globais via SafeWrite para facts/rules agora usam a raiz XDG de dados, preservando `.umem/memory/*` apenas para escopo de projeto.
- Testes de regressao cobrem os caminhos globais XDG com nome `umem`.

### Verificacao

- `uv run pytest tests/infrastructure/config/test_toml_loader.py tests/infrastructure/storage/test_local_fact_repository.py tests/infrastructure/storage/test_local_rule_repository.py tests/infrastructure/storage/test_local_latent_skill_repository.py tests/interfaces/cli/test_skills_propose.py` -> 44 passed
- `uv run pytest tests/infrastructure/security/test_local_audit_log_repository.py::test_concurrent_writes_preserve_all_jsonl_events` -> 1 passed apos falha concorrente transiente na primeira suite completa
- `uv run pytest` -> 390 passed

## BUG-004 - Rollback falha quando o snapshot representa arquivo inexistente antes da mutacao

- Status: verified
- Severidade: high
- Superficie: CLI | MCP | Snapshots | Rollback
- Encontrado em: 2026-05-29
- Contexto: durante execucao do plano `docs/alpha-sandbox-test-plan.md`, rollback em sandbox recem-inicializado falhou apos criar o primeiro fato do projeto.

### Reproducao

1. criar sandbox limpo com `HOME`, `XDG_CONFIG_HOME` e `XDG_DATA_HOME` isolados
2. rodar `uv run --project <repo> umem init --yes --format json`
3. rodar `uv run --project <repo> umem remember "Fato antes do rollback." --scope project --format json`
4. rodar `uv run --project <repo> umem rollback --scope project --yes --format json`

### Esperado

- rollback usa o snapshot mais recente
- `.umem/memory/facts.jsonl` volta ao estado anterior esperado
- evento de rollback aparece no audit log com sucesso

### Obtido

- rollback retorna erro de armazenamento
- mensagem: `Snapshot backup file not found: <snapshot-id>`
- arquivo de memoria continua com o fato ativo
- audit log registra `rollback` com `result=failure`

### Evidencias

- sandbox observado: `/tmp/umem-rollback.0RhTdN/project`
- erro CLI: `Snapshot backup file not found: cdedaf37-f300-4cf9-a4ed-a94d38092a39`
- manifest registra snapshot `write_fact` para `.umem/memory/facts.jsonl`
- diretorio `.umem/snapshots/files/` estava vazio no caso em que o arquivo nao existia antes da primeira escrita
- mesmo sintoma apareceu via MCP em `rollback_scope(scope="project", confirm=true)`: `Snapshot backup file not found: 27f1cf91-3c5f-44e5-870f-43cb271f7c27`

### Hipotese / Causa Raiz

- `SafeWriteUseCase` cria snapshot com hash de `previous_bytes=b""` quando o arquivo alvo ainda nao existe
- `LocalSnapshotRepository._copy_current_file()` retorna `None` quando o arquivo fonte nao existe e nao cria backup fisico vazio em `.umem/snapshots/files/<snapshot-id>`
- `RollbackUseCase` sempre chama `snapshot_repository.get_content(snapshot.id)`, entao snapshots sem arquivo fisico nao sao restauraveis

### Correcao

- `Snapshot` agora registra `previous_file_existed`, permitindo distinguir estado anterior ausente de arquivo existente vazio.
- `SafeWriteUseCase` preenche esse metadado antes de criar o snapshot.
- `RollbackUseCase` remove o arquivo alvo quando o snapshot representa ausencia anterior; snapshots normais continuam exigindo backup fisico e validacao SHA-256.
- Rollback valida hash vazio antes de remover arquivo criado e trata snapshots legados sem `previous_file_existed` quando o backup fisico esta ausente e o hash e de conteudo vazio.
- Testes de application, infraestrutura, CLI e MCP cobrem rollback apos primeira mutacao em sandbox limpo, manifesto legado e rejeicao de hash inconsistente.

### Verificacao

- `uv run pytest tests/application/security/test_rollback_use_case.py tests/infrastructure/security/test_local_snapshot_repository.py tests/interfaces/cli/test_rollback_command.py tests/interfaces/mcp/test_server.py::test_real_mcp_rollback_removes_file_created_by_first_remember` -> 27 passed
- smoke CLI em sandbox isolado: `umem init`, `umem remember "Fato antes do rollback." --scope project`, `umem rollback --scope project --yes --format json`, seguido de `test ! -e .umem/memory/facts.jsonl` -> rollback `ok=true`
- teste MCP real com `initialize_project`, `remember_fact` e `rollback_scope(scope="project", confirm=true)` -> rollback `ok=true` e arquivo removido
- `uv run pytest` -> 395 passed

## BUG-005 - Erros MCP nao preservam envelope uniforme com `operation`, `scope` e `warnings`

- Status: open
- Severidade: medium
- Superficie: MCP
- Encontrado em: 2026-05-29
- Contexto: durante teste black-box MCP via `stdio` com cliente FastMCP real, erros controlados retornaram payload parcial diferente do envelope exigido pelo plano.

### Reproducao

1. subir `umem-mcp` via cliente MCP em sandbox limpo
2. inicializar projeto com `initialize_project`
3. criar/listar um fato para obter `id`
4. chamar `purge_fact(id=<id>, confirm=false)`

### Esperado

- toda resposta MCP segue envelope com `ok`, `operation`, `scope`, `data`, `warnings`
- erros destrutivos sem confirmacao retornam erro controlado mantendo metadados de operacao e escopo

### Obtido

- erro retorna apenas `ok=false` e `error`
- faltam `operation`, `scope` e `warnings`
- mesmo padrao apareceu em erros de `rollback_scope`, `activate_skill` e `update_skill`

### Evidencias

- sandbox observado: `/tmp/umem-mcp.TgpvXe/project`
- chamada: `purge_fact(id=<id>, confirm=false)`
- payload observado: chaves `error`, `ok`
- erro: `Validation failed.`, detalhe `Purging facts is destructive and requires explicit confirmation. Please call this tool with confirm=True.`
- sandbox adicional: `/tmp/umem-mcp2.pDb3Xp/project`
- `rollback_scope` com falha tambem retornou apenas `error`, `ok`

### Hipotese / Causa Raiz

- tratamento de excecoes MCP monta envelope de erro JSON-RPC sem preencher os campos comuns usados no envelope de sucesso
- contrato de erro MCP nao esta alinhado ao contrato documentado no plano alpha

### Correcao

- preencher quando corrigido

### Verificacao

- reexecutar a secao 8 de `docs/alpha-sandbox-test-plan.md`
- validar que respostas de erro incluem pelo menos `ok`, `operation`, `scope`, `warnings` e `error`

## BUG-006 - MCP permite mutacao antes de inicializacao e deixa layout `.umem` parcial

- Status: open
- Severidade: high
- Superficie: MCP | Onboarding | Storage
- Encontrado em: 2026-05-29
- Contexto: durante teste MCP black-box, uma chamada invalida de `initialize_project` seguida de mutacao (`remember_fact`) criou parte do layout `.umem`; depois `initialize_project` nao conseguiu reparar o estado parcial.

### Reproducao

1. criar sandbox limpo para MCP
2. chamar `initialize_project` com argumentos invalidos, por exemplo `yes` e `hosts`
3. chamar `remember_fact(content="MCP grava fatos corretamente", scope="project", tags=["mcp"])`
4. chamar `initialize_project` novamente sem argumentos

### Esperado

- mutacoes antes de inicializacao sao bloqueadas com erro controlado sem criar layout parcial, ou
- `initialize_project` repara/completa um layout parcial criado por operacoes anteriores

### Obtido

- `remember_fact` executa e cria estado parcial
- chamada posterior de `initialize_project {}` falha com `storage_error`
- detalhe: `Project layout '.umem' is partial or corrupted; missing canonical paths: .umem/config.toml, .umem/skills, .umem/benchmarks, .umem/benchmarks/retrieval-results.json`

### Evidencias

- sandbox observado: `/tmp/umem-mcp.TgpvXe/project`
- `initialize_project` com argumentos `yes` e `hosts` falhou por argumentos inesperados
- `remember_fact` em seguida retornou `ok=true`
- `initialize_project {}` depois retornou erro de layout parcial/corrompido
- em sandbox MCP limpo, `initialize_project {}` funcionou corretamente, isolando o problema ao estado parcial criado antes do init

### Hipotese / Causa Raiz

- tools MCP de mutacao nao exigem projeto inicializado antes de escrever em `.umem`
- validacao/reparo de layout no onboarding trata layout parcial como corrupcao fatal em vez de completar caminhos canonicos ausentes

### Correcao

- preencher quando corrigido

### Verificacao

- repetir o fluxo acima e confirmar que nenhuma mutacao pre-init cria `.umem` parcial, ou que `initialize_project` repara o layout
- reexecutar a secao MCP do plano alpha em sandbox limpo e em sandbox com tentativa pre-init invalida
