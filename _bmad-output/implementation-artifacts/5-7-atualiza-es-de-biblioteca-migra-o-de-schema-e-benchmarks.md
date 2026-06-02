# Story 5.7: Atualizacoes de Biblioteca, Migracao de Schema e Benchmarks

Status: done

## Historia

Como um usuario mantendo meu ambiente do `universal-memory` atualizado,
eu quero que a CLI verifique versoes, migre schemas de configuracao com seguranca e atualize os benchmarks locais,
para que eu nao perca meu historico de uso, fatos ou regras customizadas.

**Requirements covered:** FR33.

## Criterios de Aceitacao BDD

1. **Dado** um projeto inicializado com `.umem/` e uma instalacao local do pacote,
   **Quando** o usuario executa `umem update --check`,
   **Entao** a CLI reporta a versao instalada do `universal-memory`, o schema alvo suportado e o status dos artefatos locais verificaveis,
   **E** a operacao e read-only: nao cria, altera, normaliza ou apaga arquivos.

2. **Dado** `umem update --check --format json`,
   **Quando** a verificacao e executada,
   **Entao** stdout contem apenas JSON valido no envelope padrao da DevEx spec,
   **E** `data` contem pelo menos `installed_version`, `target_schema_version`, `project_config_schema_version`, `memory_schema_versions`, `benchmarks_status`, `updates_available`, `migration_required` e `warnings`,
   **E** os nomes de campos permanecem em ingles e `snake_case` independentemente do locale configurado.

3. **Dado** `.umem/config.toml` sem `schema_version` ou com schema anterior suportado,
   **Quando** o usuario executa `umem update --migrate` ou uma atualizacao explicita equivalente,
   **Entao** o sistema migra o config TOML para o schema alvo atual,
   **E** preserva chaves existentes desconhecidas ou customizadas do usuario,
   **E** preserva configuracoes ja existentes como `[hosts] enabled = [...]` e `[preferences] locale = "en"` quando presentes,
   **E** registra snapshot e auditoria antes/depois da mutacao.

4. **Dado** arquivos de memoria existentes em `.umem/memory/*.jsonl` ou `.umem/memory/*.json` contendo fatos, regras, latent skills ou resumos em schema anterior suportado,
   **Quando** a migracao e aplicada,
   **Entao** cada registro valido e migrado para o schema alvo sem alterar `id`, `created_at`, `scope`, `status`, conteudo, tags, metadados ou historico funcional,
   **E** registros customizados com campos extras seguros sao preservados em `metadata` ou mantidos quando o modelo ja aceitar extensoes,
   **E** dados invalidos ou corrompidos nao sao descartados silenciosamente.

5. **Dado** uma falha ao criar snapshot, ao gravar TOML/JSONL ou ao validar a migracao,
   **Quando** `umem update --migrate` e executado,
   **Entao** a operacao aborta antes de substituir o arquivo original,
   **E** retorna erro de dominio acionavel (`SnapshotFailedError`, `ValidationFailedError`, `InvalidConfigError` ou `StorageError`, conforme causa),
   **E** nao deixa arquivo parcial como estado final.

6. **Dado** novos datasets ou definicoes de benchmark disponiveis no pacote local,
   **Quando** o usuario executa `umem update --benchmarks`,
   **Entao** os artefatos locais sob `.umem/benchmarks/` sao atualizados de forma segura,
   **E** o arquivo `.umem/benchmarks/retrieval-results.json` e gerado ou atualizado por execucao do benchmark local existente,
   **E** historico ou resultados customizados do usuario nao sao sobrescritos sem snapshot e auditoria.

7. **Dado** `umem update --benchmarks --format json`,
   **Quando** a atualizacao de benchmark finaliza,
   **Entao** a resposta JSON informa `benchmarks_updated`, `retrieval_results_path`, `query_count`, `fact_count`, `selected_default_strategy`, `p95_latency_ms`, `audit_reference` e `warnings`,
   **E** nao mistura Rich markup, banner ANSI, logs de progresso ou texto humano no stdout.

8. **Dado** ambiente offline apos instalacao local,
   **Quando** `umem update --check`, `umem update --migrate` ou `umem update --benchmarks` sao executados,
   **Entao** o fluxo funciona apenas com metadados e templates locais,
   **E** nenhuma chamada de rede e obrigatoria para cumprir a historia,
   **E** se uma verificacao remota de versao futura for adicionada, ela deve ser opt-in ou degradar para status `unknown` com warning sem falhar a operacao local.

## Tarefas

- [x] **Tarefa 1: Definir contrato de update e schema alvo (AC: 1, 2)**
  - [x] Criar DTOs/commands/results em `application` para verificacao, migracao e atualizacao de benchmarks.
  - [x] Definir constante unica para o schema alvo atual, inicialmente `1`, alinhada aos modelos existentes que ja persistem `schema_version` nas entidades.
  - [x] Ler versao instalada via `universal_memory.__version__` ou `importlib.metadata.version("universal-memory")`, sem duplicar parsing de `pyproject.toml` em runtime.
  - [x] Representar `updates_available` como `false` ou `unknown` quando so houver metadados locais; nao inventar integracao remota.

- [x] **Tarefa 2: Implementar `UpdateCheckUseCase` read-only (AC: 1, 2, 8)**
  - [x] Verificar existencia de `.umem/`, `.umem/config.toml`, `.umem/memory/` e `.umem/benchmarks/retrieval-results.json` sem criar arquivos.
  - [x] Ler `schema_version` do config TOML quando existir; tratar ausencia como schema legado suportado.
  - [x] Inspecionar arquivos `.umem/memory/facts.jsonl`, `rules.jsonl`, `latent_skills.jsonl` e `context_summaries.jsonl` quando existirem, computando versoes encontradas sem descartar linhas invalidas.
  - [x] Retornar warnings seguros para arquivos ausentes, config invalido, linhas corruptas ou schemas acima do suportado.

- [x] **Tarefa 3: Implementar migracao segura de config TOML (AC: 3, 5)**
  - [x] Estender `toml_loader.py` ou criar componente dedicado em `infrastructure/config/` para aplicar migracoes TOML preservando chaves desconhecidas.
  - [x] Adicionar `schema_version = 1` ao config do projeto quando ausente, mantendo `[project]`, `[hosts]`, `[preferences]` e quaisquer tabelas customizadas.
  - [x] Usar `SafeWriteUseCase` para escrever `.umem/config.toml` durante `--migrate`; nao usar escrita direta para migracoes automaticas.
  - [x] Validar config apos renderizacao e antes de considerar a migracao concluida.

- [x] **Tarefa 4: Implementar migracao segura dos arquivos de memoria (AC: 4, 5)**
  - [x] Reutilizar hooks `migrate(target_version)` ja existentes nos repositories, ampliando-os para migracoes reais quando necessario.
  - [x] Suportar pelo menos os arquivos atualmente usados pelo codigo: `.umem/memory/facts.jsonl`, `.umem/memory/rules.jsonl`, `.umem/memory/latent_skills.jsonl` e `.umem/memory/context_summaries.jsonl` quando presentes.
  - [x] Tratar a divergencia documental `.json` vs implementacao `.jsonl` explicitamente: a historia deve preservar os arquivos reais `.jsonl` existentes e nao renomear dados do usuario sem requisito adicional.
  - [x] Para linhas invalidas, bloquear a migracao daquele arquivo com erro acionavel ou preservar a linha em quarentena auditada; nao apagar silenciosamente.
  - [x] Garantir snapshot por arquivo antes de qualquer substituicao.

- [x] **Tarefa 5: Integrar atualizacao de benchmarks locais (AC: 6, 7, 8)**
  - [x] Reutilizar `benchmarks/retrieval.py::run_benchmark(project_root=...)` para gerar `.umem/benchmarks/retrieval-results.json`.
  - [x] Se o arquivo de resultados existente tiver conteudo customizado, criar snapshot antes de sobrescrever.
  - [x] Retornar metricas principais do payload ja produzido pelo benchmark: `fact_count`, `query_count`, `selected_default_strategy` e p95 da estrategia selecionada.
  - [x] Manter execucao offline e sem dependencias novas de rede/modelos.

- [x] **Tarefa 6: Expor CLI `umem update` (AC: 1, 2, 3, 6, 7, 8)**
  - [x] Adicionar subcomando ou comando Typer `umem update` em `interfaces/cli/init_command.py` preservando os comandos existentes de `skills update`.
  - [x] Suportar flags `--check`, `--migrate`, `--benchmarks`, `--format json` e `--yes` quando confirmacao humana for necessaria.
  - [x] Definir comportamento seguro quando nenhuma flag for passada: preferir `--check` read-only ou retornar ajuda acionavel, sem migrar implicitamente.
  - [x] Em saida humana, seguir `devex-interaction-spec.md`: resultado, escopo, caminhos relativos, referencias de auditoria para mutacoes e proxima acao util.
  - [x] Em JSON, usar envelope padrao `{ "ok": true, "operation": "update...", "scope": "project", "data": ..., "warnings": [] }`.

- [x] **Tarefa 7: Composicao/bootstrap (AC: todos)**
  - [x] Instanciar use cases de update em `src/universal_memory/bootstrap/cli.py` com `SafeWriteUseCase`, repositories e benchmark runner necessarios.
  - [x] Evitar import de `infrastructure` dentro de `domain`; se algum use case em `application` precisar de I/O concreto, introduzir port simples ou manter a composicao no bootstrap.
  - [x] Nao expor MCP nesta historia a menos que a matriz de paridade do projeto ja exija update como capacidade publica; se nao expor MCP, documentar como excecao temporaria por FR33 ser explicitamente CLI.

- [x] **Tarefa 8: Testes automatizados e validacao (AC: todos)**
  - [x] Criar testes de application para check read-only, migracao de config, migracao de JSONL e falhas de snapshot/storage.
  - [x] Criar testes CLI para `umem update --check`, `--migrate`, `--benchmarks` e combinacoes com `--format json`.
  - [x] Criar teste garantindo que `--check` nao altera mtimes/conteudo dos arquivos locais.
- [x] Criar teste garantindo preservacao de fatos/regras/custom fields ao migrar fixture legado.
- [x] Atualizar ou adicionar testes de benchmark para validar integracao por CLI sem rede.
- [x] Rodar `uv run pytest`, `uv run ruff check .` e `uv run pyright` antes de marcar done.

### Review Findings

- [x] [Review][Patch] `umem update --check/--migrate` ignora arquivos de memória `.json` [src/universal_memory/application/update/update_use_cases.py:27] — resolvido; `.json` legados são detectados, migrados com snapshot/auditoria e validados.
- [x] [Review][Patch] Migração JSONL pode marcar registros inválidos como schema alvo sem validar o modelo resultante [src/universal_memory/application/update/update_use_cases.py:427] — resolvido; registros migrados são validados contra modelos reais de domínio antes da escrita.
- [x] [Review][Patch] Testes de `umem update` não protegem requisito offline contra uso de rede [tests/interfaces/cli/test_update_command.py:13] — resolvido; testes bloqueiam uso de socket/rede nos fluxos de update.
- [x] [Review][Patch] Migracao de config com `schema_version = 0` preserva o schema antigo em vez de migrar para o alvo [src/universal_memory/application/update/update_use_cases.py:328] — resolvido; merge corrigido e teste com schema legado explicito adicionado.
- [x] [Review][Patch] Migracao pode deixar projeto parcialmente migrado se uma escrita posterior falhar [src/universal_memory/application/update/update_use_cases.py:281] — resolvido; migracao prepara snapshots antes do primeiro commit e aplica rollback reverso dos writes ja commitados quando commit posterior falha.
- [x] [Review][Patch] Testes nao cobrem schema anterior explicito nem schema invalido [tests/application/test_update_use_cases.py:80] — resolvido; adicionada cobertura para schema legado explicito, tipo invalido string, boolean em config/check e boolean em JSONL.

## Contexto/Guardrails do Desenvolvedor

- Fonte primaria desta historia: `epics.md` atual da worktree principal, linhas da Story 5.7, cobrindo FR33: check de versoes, migracao segura de schema e atualizacao de benchmarks sem perda de historico/regras.
- O PRD define FR33 como capacidade CLI e reforca offline-first, preservacao de dados locais e ausencia de perda de historico/custom rules.
- A arquitetura define Clean Architecture: `interfaces -> application -> domain <- infrastructure`; `domain` nao importa outras camadas e `application` nao deve importar `infrastructure` diretamente.
- A arquitetura tambem define pipeline obrigatorio de mutacao: validar entrada, escanear segredos, resolver escopo/path, criar snapshot, abortar se snapshot falhar, escrever atomicamente via storage port, auditar e retornar referencia de auditoria.
- A DevEx spec exige que comandos read-only nao causem side effects e que `--format json` produza JSON puro, sem Rich markup, logs ou banner.
- A historia deve preservar ingles como base canonica para prompts/help/JSON fields. Esta especificacao esta em PT-BR, mas o codigo e as mensagens de produto devem seguir a decisao English-first.
- Nao atualizar `_bmad-output/implementation-artifacts/sprint-status.yaml`; a consolidacao e responsabilidade do orquestrador.

## Arquivos Provaveis

- `src/universal_memory/interfaces/cli/init_command.py`: adicionar `umem update` geral sem quebrar `umem skills update` existente.
- `src/universal_memory/bootstrap/cli.py`: compor novos use cases e dependencias.
- `src/universal_memory/__init__.py`: fonte atual de `__version__`; evitar duplicar versao.
- `src/universal_memory/infrastructure/config/toml_loader.py`: leitura/escrita TOML existente; hoje `update_project_config()` pode escrever direto quando sem `write_options`, mas migracoes automaticas devem usar `SafeWriteUseCase`.
- `src/universal_memory/infrastructure/config/project_layout.py`: layout atual inclui `.umem/benchmarks/retrieval-results.json`; a historia deve preservar esse caminho.
- `src/universal_memory/application/onboarding/setup_project.py`: hoje materializa defaults de hosts e locale; migracao deve preservar essas chaves.
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`: usa `.umem/memory/facts.jsonl`; `migrate()` hoje so aceita target 1 sem transformar.
- `src/universal_memory/infrastructure/storage/local_rule_repository.py`: usa `.umem/memory/rules.jsonl`; `migrate()` hoje so aceita target 1 sem transformar.
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`: usa `.umem/memory/latent_skills.jsonl`; `migrate()` hoje so aceita target 1 sem transformar.
- `src/universal_memory/infrastructure/storage/local_context_summary_repository.py`: provavel participante da migracao de resumos.
- `benchmarks/retrieval.py`: benchmark existente com `run_benchmark(project_root=...)` e output `.umem/benchmarks/retrieval-results.json`.
- `tests/interfaces/cli/test_init_command.py` ou novo `tests/interfaces/cli/test_update_command.py`: cobertura CLI.
- `tests/infrastructure/test_retrieval_benchmark.py`: pode ser expandido para integracao `umem update --benchmarks`.
- `tests/infrastructure/config/test_toml_loader.py`: cobertura de preservacao TOML/migracao.

## Requisitos Tecnicos

- O schema alvo inicial deve ser `1`, salvo se o dev encontrar evidencia de outro valor no codigo atual.
- A verificacao de versao deve funcionar offline. Nao adicionar chamada remota obrigatoria para PyPI/GitHub nesta historia.
- A migracao deve ser idempotente: rodar `umem update --migrate` duas vezes nao deve duplicar dados, reordenar desnecessariamente arquivos ou criar novas alteracoes quando nada mudou.
- Mutacoes de config, memoria e benchmarks devem passar por `SafeWriteUseCase` ou por um port equivalente que preserve snapshot, secret scan, escrita atomica e auditoria.
- Read-only `--check` nao deve chamar `ensure_project_layout()`, `run_benchmark()` ou qualquer metodo de escrita.
- Ao lidar com `.json` vs `.jsonl`, priorizar o estado real do codigo atual (`*.jsonl`) e documentar warnings para arquivos legados ou inesperados. Nao fazer rename destrutivo sem requisito explicito.
- Ao renderizar TOML, preservar semanticamente chaves desconhecidas. Comentarios podem nao sobreviver ao `tomli_w`; se isso for inevitavel, declarar warning em output humano/JSON antes da migracao.
- Erros devem usar excecoes de dominio ja existentes quando possivel: `InvalidConfigError`, `ValidationFailedError`, `SnapshotFailedError`, `StorageError`.
- O comando `umem update` geral nao deve conflitar com o namespace `umem skills update` ja implementado.

## Requisitos de Teste

- Teste RED inicial deve demonstrar ausencia de `umem update --check` ou ausencia dos campos obrigatorios.
- Testar JSON puro com `json.loads(stdout)` e stderr sem Rich/progresso inesperado para `--format json`.
- Testar que `umem update --check` em projeto inicializado nao altera conteudo nem mtimes de `.umem/config.toml`, `.umem/memory/*.jsonl` e `.umem/benchmarks/retrieval-results.json`.
- Testar migracao de config sem `schema_version`, com `[hosts] enabled = ["codex"]`, `[preferences] locale = "pt_BR"` e tabela customizada; resultado deve preservar dados e adicionar schema alvo.
- Testar migracao de fixture JSONL legado com pelo menos um fato e uma regra; `id`, `created_at`, `scope`, `status`, `content`/campos equivalentes e metadata devem permanecer intactos.
- Testar falha de snapshot: migracao deve abortar e arquivo original deve permanecer byte-a-byte igual.
- Testar arquivo de memoria com linha JSON invalida: nao pode ser descartado silenciosamente; esperar erro ou mecanismo explicito de quarentena auditada.
- Testar `umem update --benchmarks` cria/atualiza `.umem/benchmarks/retrieval-results.json` com pelo menos 1.000 fatos sinteticos, 30 queries e estrategia default registrada.
- Testar offline por construcao: monkeypatch ou fixture que falhe se `socket`/rede for usado, ou assert de ausencia de chamada remota quando aplicavel.
- Rodar suite completa e checks: `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

## Inteligencia da Historia Anterior

- A historia anterior relevante foi reaberta como `5-6-onboarding-cli-de-sele-o-multi-runtime.md` para alinhar o sprint status ao escopo multi-runtime atualizado.
- A Story 5.6 foi marcada `done`, mas seu escopo implementado usa `hosts` e cobre principalmente `codex` e `claude_code`, enquanto o `epics.md` atualizado fala em multi-runtime com Claude Code, OpenCode, Codex, Cursor e Antigravity. Nao expandir suporte de runtime nesta historia alem do necessario para FR33.
- A Story 5.6 registrou pendencias de review abertas que podem impactar esta historia, especialmente escrita insegura/duplo I/O em `update_project_config()`, escrita de config antes da validacao, fragilidade de hosts em config e falta de tratamento de excecoes. Ao tocar esses pontos, corrija de forma local e testada sem alterar comportamento nao relacionado.
- O onboarding ja grava `[hosts] enabled = [...]` e default de locale; a migracao de schema precisa preservar esses dados para nao quebrar sincronizacao futura de instrucoes.
- O arquivo de resultados de benchmark ja existe no layout e o benchmark da Story 3.3 esta `done`; esta historia deve reutilizar, nao reimplementar do zero.

## Riscos / Edge Cases

- **Perda de dados por normalizacao TOML:** `tomli_w` pode remover comentarios ou reordenar formatacao. Mitigar preservando semantica, usando snapshot e exibindo warning quando relevante.
- **Divergencia documental `.json` vs codigo `.jsonl`:** PRD/epics mencionam `.umem/memory/*.json`, mas repositories atuais usam `.jsonl`. Tratar como inferencia baseada no codigo: preservar `.jsonl` real e nao renomear automaticamente.
- **Schema futuro maior que suportado:** se um arquivo local tiver `schema_version` maior que o alvo, nao tentar downgrade; retornar warning/erro seguro.
- **Linha corrompida em JSONL:** nao descartar; bloquear migracao ou quarentenar com auditoria explicita.
- **Benchmark sobrescrevendo resultado customizado:** criar snapshot antes de atualizar `retrieval-results.json`.
- **Comando update remoto:** FR33 fala em checking library versions, mas os documentos tambem exigem offline-first. Para esta historia, check deve ser local; qualquer rede deve ser post-MVP ou opt-in.
- **Conflito com `skills update`:** manter namespace claro para nao quebrar fluxos de skills ja implementados.
- **Arquivos globais:** FR33 cita config/schema local. Se o dev decidir incluir `~/.config/umem/config.toml` ou `~/.local/share/umem`, marcar como extensao inferida e garantir testes isolados; nao e obrigatorio salvo evidencia adicional.

## Checklist de Validacao

- [x] `umem update --check` existe, e read-only e retorna versao/schema/status local.
- [x] `umem update --check --format json` retorna JSON puro com campos obrigatorios.
- [x] `umem update --migrate` adiciona/atualiza schema alvo com snapshot, auditoria e preservacao de dados.
- [x] Migracao de `.umem/config.toml` preserva `[hosts]`, `[preferences]` e tabelas customizadas.
- [x] Migracao de memoria preserva fatos, regras, latent skills e resumos existentes sem perda silenciosa.
- [x] Falhas de snapshot/storage/validacao abortam sem corromper arquivos.
- [x] `umem update --benchmarks` reutiliza `benchmarks/retrieval.py` e atualiza `.umem/benchmarks/retrieval-results.json` com snapshot/auditoria quando sobrescreve.
- [x] Todos os fluxos funcionam offline.
- [x] O comando nao altera `sprint-status.yaml` nem artefatos BMad fora desta historia.
- [x] `uv run pytest`, `uv run ruff check .` e `uv run pyright` passam.

## Dev Agent Record

### Implementation Plan

- Criar contrato `application.update` com comandos/resultados para check, migrate e benchmarks, mantendo schema alvo unico `TARGET_SCHEMA_VERSION = 1` e versao instalada via `universal_memory.__version__`.
- Implementar `UpdateCheckUseCase` estritamente read-only, sem `ensure_project_layout`, sem benchmark e sem escrita.
- Implementar `UpdateMigrateUseCase` com pre-validacao de config/memoria antes de qualquer escrita e mutacoes via `SafeWriteUseCase` para snapshot, atomic write e auditoria.
- Implementar `UpdateBenchmarksUseCase` gerando payload offline em diretorio temporario e gravando `.umem/benchmarks/retrieval-results.json` apenas via `SafeWriteUseCase`.
- Expor `umem update` na CLI com JSON puro, saida humana, confirmacao `--yes` para mutacoes e default seguro para `--check`.
- Compor use cases no bootstrap da CLI sem expor MCP nesta historia; excecao temporaria: FR33 e explicitamente CLI.

### Debug Log

- Teste RED inicial falhou por ausencia de `universal_memory.application.update`, confirmando lacuna da story.
- Primeira suite focada revelou asserts de TOML acoplados a formatacao de `tomli_w`; testes foram ajustados para validacao semantica.
- `uv run pytest` completo inicialmente revelou regressao no subprocesso `python -m universal_memory init` causada por import top-level de `benchmarks`; corrigido com import lazy.
- Verificacao manual fora do repo revelou que `benchmarks.retrieval` nao era resolvido em instalacao/editable fora do cwd; adicionado pacote `src/benchmarks` com runner offline empacotado equivalente.
- `sprint-status.yaml` nao foi lido nem alterado, conforme guardrail do usuario.

### Completion Notes

- `umem update --check` implementado como leitura local offline com campos JSON obrigatorios, warnings seguros e `updates_available=false`.
- `umem update --migrate` migra config TOML e JSONL de memoria para schema 1, preservando chaves/tabelas customizadas e campos extras seguros em `metadata`.
- Linhas JSONL invalidas bloqueiam migracao com `StorageError`, sem descarte silencioso.
- Mutacoes de config, memoria e benchmarks usam `SafeWriteUseCase`, criando snapshot e auditoria antes da substituicao.
- `umem update --benchmarks` executa benchmark offline, retorna metricas principais e grava resultados via pipeline seguro.
- O comando geral `umem update` nao conflita com `umem skills update`; sem flags, faz `--check` read-only.

### Validation Results

- `uv run pytest` - passou, 406 passed.
- `uv run ruff check .` - passou, All checks passed.
- `uv run pyright` - passou, 0 errors, 0 warnings.

## File List

- `src/benchmarks/__init__.py`
- `src/benchmarks/retrieval.py`
- `src/universal_memory/application/update/__init__.py`
- `src/universal_memory/application/update/update_use_cases.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/test_update_use_cases.py`
- `tests/interfaces/cli/test_update_command.py`
- `_bmad-output/implementation-artifacts/5-7-atualiza-es-de-biblioteca-migra-o-de-schema-e-benchmarks.md`

## Change Log

- 2026-06-01: Implementado comando `umem update` com `--check`, `--migrate`, `--benchmarks`, JSON puro, schema alvo 1, migracao segura, benchmark offline empacotado e cobertura automatizada.
