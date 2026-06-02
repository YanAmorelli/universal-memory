# Story 5.7: Atualizacoes de Biblioteca, Migracao de Schema e Benchmarks

Status: ready-for-dev

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

- [ ] **Tarefa 1: Definir contrato de update e schema alvo (AC: 1, 2)**
  - [ ] Criar DTOs/commands/results em `application` para verificacao, migracao e atualizacao de benchmarks.
  - [ ] Definir constante unica para o schema alvo atual, inicialmente `1`, alinhada aos modelos existentes que ja persistem `schema_version` nas entidades.
  - [ ] Ler versao instalada via `universal_memory.__version__` ou `importlib.metadata.version("universal-memory")`, sem duplicar parsing de `pyproject.toml` em runtime.
  - [ ] Representar `updates_available` como `false` ou `unknown` quando so houver metadados locais; nao inventar integracao remota.

- [ ] **Tarefa 2: Implementar `UpdateCheckUseCase` read-only (AC: 1, 2, 8)**
  - [ ] Verificar existencia de `.umem/`, `.umem/config.toml`, `.umem/memory/` e `.umem/benchmarks/retrieval-results.json` sem criar arquivos.
  - [ ] Ler `schema_version` do config TOML quando existir; tratar ausencia como schema legado suportado.
  - [ ] Inspecionar arquivos `.umem/memory/facts.jsonl`, `rules.jsonl`, `latent_skills.jsonl` e `context_summaries.jsonl` quando existirem, computando versoes encontradas sem descartar linhas invalidas.
  - [ ] Retornar warnings seguros para arquivos ausentes, config invalido, linhas corruptas ou schemas acima do suportado.

- [ ] **Tarefa 3: Implementar migracao segura de config TOML (AC: 3, 5)**
  - [ ] Estender `toml_loader.py` ou criar componente dedicado em `infrastructure/config/` para aplicar migracoes TOML preservando chaves desconhecidas.
  - [ ] Adicionar `schema_version = 1` ao config do projeto quando ausente, mantendo `[project]`, `[hosts]`, `[preferences]` e quaisquer tabelas customizadas.
  - [ ] Usar `SafeWriteUseCase` para escrever `.umem/config.toml` durante `--migrate`; nao usar escrita direta para migracoes automaticas.
  - [ ] Validar config apos renderizacao e antes de considerar a migracao concluida.

- [ ] **Tarefa 4: Implementar migracao segura dos arquivos de memoria (AC: 4, 5)**
  - [ ] Reutilizar hooks `migrate(target_version)` ja existentes nos repositories, ampliando-os para migracoes reais quando necessario.
  - [ ] Suportar pelo menos os arquivos atualmente usados pelo codigo: `.umem/memory/facts.jsonl`, `.umem/memory/rules.jsonl`, `.umem/memory/latent_skills.jsonl` e `.umem/memory/context_summaries.jsonl` quando presentes.
  - [ ] Tratar a divergencia documental `.json` vs implementacao `.jsonl` explicitamente: a historia deve preservar os arquivos reais `.jsonl` existentes e nao renomear dados do usuario sem requisito adicional.
  - [ ] Para linhas invalidas, bloquear a migracao daquele arquivo com erro acionavel ou preservar a linha em quarentena auditada; nao apagar silenciosamente.
  - [ ] Garantir snapshot por arquivo antes de qualquer substituicao.

- [ ] **Tarefa 5: Integrar atualizacao de benchmarks locais (AC: 6, 7, 8)**
  - [ ] Reutilizar `benchmarks/retrieval.py::run_benchmark(project_root=...)` para gerar `.umem/benchmarks/retrieval-results.json`.
  - [ ] Se o arquivo de resultados existente tiver conteudo customizado, criar snapshot antes de sobrescrever.
  - [ ] Retornar metricas principais do payload ja produzido pelo benchmark: `fact_count`, `query_count`, `selected_default_strategy` e p95 da estrategia selecionada.
  - [ ] Manter execucao offline e sem dependencias novas de rede/modelos.

- [ ] **Tarefa 6: Expor CLI `umem update` (AC: 1, 2, 3, 6, 7, 8)**
  - [ ] Adicionar subcomando ou comando Typer `umem update` em `interfaces/cli/init_command.py` preservando os comandos existentes de `skills update`.
  - [ ] Suportar flags `--check`, `--migrate`, `--benchmarks`, `--format json` e `--yes` quando confirmacao humana for necessaria.
  - [ ] Definir comportamento seguro quando nenhuma flag for passada: preferir `--check` read-only ou retornar ajuda acionavel, sem migrar implicitamente.
  - [ ] Em saida humana, seguir `devex-interaction-spec.md`: resultado, escopo, caminhos relativos, referencias de auditoria para mutacoes e proxima acao util.
  - [ ] Em JSON, usar envelope padrao `{ "ok": true, "operation": "update...", "scope": "project", "data": ..., "warnings": [] }`.

- [ ] **Tarefa 7: Composicao/bootstrap (AC: todos)**
  - [ ] Instanciar use cases de update em `src/universal_memory/bootstrap/cli.py` com `SafeWriteUseCase`, repositories e benchmark runner necessarios.
  - [ ] Evitar import de `infrastructure` dentro de `domain`; se algum use case em `application` precisar de I/O concreto, introduzir port simples ou manter a composicao no bootstrap.
  - [ ] Nao expor MCP nesta historia a menos que a matriz de paridade do projeto ja exija update como capacidade publica; se nao expor MCP, documentar como excecao temporaria por FR33 ser explicitamente CLI.

- [ ] **Tarefa 8: Testes automatizados e validacao (AC: todos)**
  - [ ] Criar testes de application para check read-only, migracao de config, migracao de JSONL e falhas de snapshot/storage.
  - [ ] Criar testes CLI para `umem update --check`, `--migrate`, `--benchmarks` e combinacoes com `--format json`.
  - [ ] Criar teste garantindo que `--check` nao altera mtimes/conteudo dos arquivos locais.
  - [ ] Criar teste garantindo preservacao de fatos/regras/custom fields ao migrar fixture legado.
  - [ ] Atualizar ou adicionar testes de benchmark para validar integracao por CLI sem rede.
  - [ ] Rodar `uv run pytest`, `uv run ruff check .` e `uv run pyright` antes de marcar done.

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

- A historia anterior relevante existe como `5-6-fluxo-de-sele-o-de-hosts-no-onboarding.md`, nao como `5-6-onboarding-cli-de-sele-o-multi-runtime.md`. Essa divergencia deve ser considerada ao referenciar sprint status e artefatos.
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

- [ ] `umem update --check` existe, e read-only e retorna versao/schema/status local.
- [ ] `umem update --check --format json` retorna JSON puro com campos obrigatorios.
- [ ] `umem update --migrate` adiciona/atualiza schema alvo com snapshot, auditoria e preservacao de dados.
- [ ] Migracao de `.umem/config.toml` preserva `[hosts]`, `[preferences]` e tabelas customizadas.
- [ ] Migracao de memoria preserva fatos, regras, latent skills e resumos existentes sem perda silenciosa.
- [ ] Falhas de snapshot/storage/validacao abortam sem corromper arquivos.
- [ ] `umem update --benchmarks` reutiliza `benchmarks/retrieval.py` e atualiza `.umem/benchmarks/retrieval-results.json` com snapshot/auditoria quando sobrescreve.
- [ ] Todos os fluxos funcionam offline.
- [ ] O comando nao altera `sprint-status.yaml` nem artefatos BMad fora desta historia.
- [ ] `uv run pytest`, `uv run ruff check .` e `uv run pyright` passam.
