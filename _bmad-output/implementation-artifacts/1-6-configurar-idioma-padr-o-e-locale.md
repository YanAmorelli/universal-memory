# Story 1.6: Configurar Idioma Padrão e Locale

Status: review

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário ou agente inicializando a memória,  
eu quero que o inglês seja o idioma padrão com configuração explícita de locale,  
para que a saída da CLI, instruções geradas e templates de skills sejam consistentes e seguros para automação.

## Acceptance Criteria

1. **Dado** uma configuração limpa sem `.umem/config.toml`, **Quando** `umem init` é executado, **Então** o locale padrão configurado no TOML do projeto é `en`, **E** as saídas humanas padrão de ajuda e inicialização são exibidas em inglês.
2. **Dado** a flag `--format json` ou uma requisição MCP, **Quando** qualquer comando CLI ou ferramenta MCP é executado, **Então** nomes de campos JSON, identificadores de erro, valores estruturados e payloads de ferramenta permanecem estáveis em inglês, **E** não mudam de acordo com o locale configurado para saída humana.
3. **Dado** uma configuração explícita de locale definida como Português (`pt-BR`), **Quando** comandos humanos da CLI são executados, **Então** apenas rótulos, prompts e mensagens voltados a humanos são traduzidos.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes RED para locale padrão e inglês canônico** (AC: 1, 2)
- [x] Atualizar `tests/application/test_setup_project.py` para exigir `.umem/config.toml` com `locale = "en"` ou tabela equivalente clara de locale no projeto.
- [x] Atualizar `tests/interfaces/cli/test_init_command.py` para exigir que `umem init` humano use mensagens em inglês por padrão, incluindo prompt de hosts e help/options quando testável.
- [x] Adicionar teste garantindo que `umem init --format json` continua JSON puro com chaves em inglês e nenhum texto traduzido ou Rich markup.
- [x] Adicionar teste garantindo que erro JSON esperado mantém `ok`, `error`, `code`, `message`, `detail`, `recovery_hint` e `audit_reference` em inglês estável.

- [x] **Task 2: Persistir locale default no config TOML sem quebrar hosts** (AC: 1)
- [x] Atualizar `src/universal_memory/application/onboarding/setup_project.py` para gravar locale default `en` durante `setup_project(...)` junto com `hosts.enabled`.
- [x] Preservar idempotência: reexecutar `umem init` não deve sobrescrever locale manual existente, inclusive `pt-BR`.
- [x] Preservar merge TOML existente em `update_project_config(...)`; não criar parser TOML paralelo.
- [x] Validar que config limpo resultante continua legível com `tomllib` e escrito por `tomli-w`.

- [x] **Task 3: Introduzir overlay mínimo de mensagens humanas** (AC: 1, 3)
- [x] Criar ou atualizar um presenter/catalogo em `src/universal_memory/interfaces/cli/` para resolver mensagens humanas: inglês como string canônica, tradução `pt-BR` como overlay opcional.
- [x] Aplicar o overlay primeiro aos textos humanos diretamente ligados à Story 1.6: `init`, prompts de seleção/configuração de hosts, mensagens de sucesso/no-op e mensagens de erro esperadas usadas pelo CLI.
- [x] Escrever strings novas nativamente em inglês no código; o catálogo `pt-BR` deve mapear inglês literal para português quando locale configurado for `pt-BR`.
- [x] Aceitar `pt-BR` como locale configurado; se o locale for desconhecido, usar `en` sem falhar.

- [x] **Task 4: Proteger automação CLI/MCP contra tradução** (AC: 2)
- [x] Garantir que `--format json` bypassa o catálogo de tradução e não lê/aplica locale para campos estruturados.
- [x] Garantir que envelopes de sucesso/erro JSON em `interfaces/cli/init_command.py` permaneçam em inglês para chaves e códigos.
- [x] Revisar `src/universal_memory/interfaces/mcp/server.py` e `src/universal_memory/bootstrap/mcp.py` para confirmar que payloads MCP não usam presenter humano nem tradução.
- [x] Se necessário, adicionar teste MCP mínimo garantindo que `initialize_project`/status mantém chaves estruturadas em inglês mesmo com `.umem/config.toml` configurado para `pt-BR`.

- [x] **Task 5: Migrar textos existentes em português no escopo tocado sem refatoração ampla** (AC: 1, 3)
- [x] Migrar textos humanos de `init` e prompts diretamente relacionados de português para inglês canônico em `src/universal_memory/interfaces/cli/init_command.py`.
- [x] Não tentar traduzir todo o CLI nesta story; comandos de outros épicos podem continuar com strings legadas se não forem necessários para os ACs, mas não devem ser usados como padrão para código novo.
- [x] Atualizar o conteúdo seedado da skill default `use-universal-memory` para inglês canônico, mantendo comandos e campos estruturados em inglês.
- [x] Preservar nomes de comandos/flags (`init`, `--format json`, `--hosts`, `--yes`) e aliases existentes.

- [x] **Task 6: Verificação de qualidade e regressão** (AC: 1, 2, 3)
- [x] Executar `uv run pytest tests/application/test_setup_project.py tests/interfaces/cli/test_init_command.py`.
- [x] Executar testes MCP relevantes se payload MCP for tocado: `uv run pytest tests/interfaces/mcp/test_server.py`.
- [x] Executar `uv run pytest` completo.
- [x] Executar `uv run ruff check .` e `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Help humano padrao ainda expõe textos em portugues, violando English-first [src/universal_memory/interfaces/cli/init_command.py:237] — resolvido; CLI/help/saidas humanas publicas migradas para ingles canonico por padrao, mantendo overlay explicito `pt-BR`.
- [x] [Review][Patch] Fallback de erro humano usa `pt-BR` quando nenhum locale foi resolvido [src/universal_memory/interfaces/cli/init_command.py:2685] — resolvido; fallback sem locale explicito agora e `en`.
- [x] [Review][Patch] Catalogo de mensagens importa infraestrutura diretamente na camada CLI [src/universal_memory/interfaces/cli/message_catalog.py:3] — resolvido; resolucao de locale movida para bootstrap via `locale_resolver`, mantendo catalogo puro.
- [x] [Review][Patch] Erro de hosts nao suportados nao aplica overlay `pt-BR` no detalhe humano [src/universal_memory/interfaces/cli/init_command.py:991] — resolvido; detalhe humano usa `human_message(...)` e JSON permanece canonico em ingles.

## Dev Notes

- **Escopo desta story:** configurar idioma default e comportamento de locale. Não implementar splash visual (Story 4.6), não implementar update/migração completa de schema (Story 5.7) e não refatorar todo o CLI além do necessário para os ACs.
- **Decisão principal:** inglês é a base canônica do produto. Português é overlay de apresentação humana, não idioma de dados, APIs ou código de erro.
- **Risco principal:** traduzir JSON/MCP ou trocar chaves/códigos quebraria automações e agentes. Trate qualquer tradução em superfície estruturada como regressão.

### Estado Atual Do Código Relevante

- `src/universal_memory/application/onboarding/setup_project.py` grava hoje apenas `hosts.enabled` via `update_project_config(...)`; o TOML esperado nos testes atuais ainda não inclui locale.
- O conteúdo seedado `DEFAULT_UMEM_SKILL_MARKDOWN` e seus triggers estão em português. Esta story deve mudar esse seed para inglês canônico porque FR29 exige templates de skills em inglês por padrão.
- `src/universal_memory/interfaces/cli/init_command.py` já usa Typer/Rich e contém muitas strings humanas em português, inclusive help text, prompts e mensagens de erro. Para esta story, priorize `init`, prompts de hosts e erros esperados cobertos por testes.
- `src/universal_memory/__main__.py` é apenas delegação para `bootstrap.cli.main`; não recriar CLI antigo em `__main__.py`.
- `src/universal_memory/bootstrap/cli.py` compõe dependências concretas. Se o presenter precisar ler config, a leitura deve ser feita sem criar side effects e sem quebrar testes que injetam comandos fake.
- `src/universal_memory/infrastructure/config/toml_loader.py` já implementa `load_config`, `update_project_config`, merge profundo e escrita com `tomli-w`. Reuse isso; não introduza PyYAML ou outro parser.

### Technical Requirements

- Python `>=3.12`; operação offline obrigatória.
- Persistência TOML deve continuar usando `tomllib` para leitura e `tomli-w` para escrita.
- Locale default deve ser `en` para novo projeto. Nome recomendado no config: uma chave simples e explícita como `[preferences] locale = "en"` ou `[project] locale = "en"`. Escolha uma forma e cubra em testes; evite duplicar locale em múltiplas tabelas.
- `pt-BR` deve afetar apenas saída humana. Aceitar também normalização defensiva (`pt_BR` -> `pt-BR`) se simples, mas não expandir para sistema i18n completo.
- JSON CLI deve continuar uma única estrutura parseável em stdout, sem Rich markup, status spinner, prompt, logs ou tradução.
- MCP deve retornar campos semânticos em inglês e não deve consumir presenter humano.

### Architecture Compliance

- Regra de dependência: `interfaces -> application -> domain <- infrastructure`.
- A camada `application` pode definir/propagar o valor de locale no resultado/config, mas não deve formatar mensagens humanas.
- O presenter/catálogo de mensagens pertence à camada `interfaces/cli`; não colocar tradução em `domain` nem em use cases.
- `infrastructure/config` continua responsável por TOML e resolução de paths; não deve conhecer Rich, Typer ou MCP.
- Não usar locale para mudar nomes de comandos, flags, JSON keys, enum values, IDs de runtime, nomes de tools MCP ou códigos de erro.

### Library / Framework Requirements

- Stack vigente do projeto: `typer`, `rich`, `fastmcp`, `pydantic`, `tomli-w`, `pytest`, `ruff`, `pyright`.
- Não adicionar dependência de i18n nesta story; o overlay deve ser tabela/dicionário simples.
- Informação de versão já registrada na arquitetura: `typer>=0.25.1`, `rich>=15.0.0`, `fastmcp>=3.3.1,<4`, `pydantic>=2.13.4,<3`, `tomli-w>=1.2.0`.

### File Structure Requirements

- **Arquivos UPDATE prováveis:**
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/test_setup_project.py`
- `tests/interfaces/cli/test_init_command.py`
- **Arquivos NEW possíveis:**
- `src/universal_memory/interfaces/cli/message_catalog.py` ou equivalente mínimo para overlay humano.
- `tests/interfaces/cli/test_message_catalog.py` se o catálogo tiver lógica própria suficiente para teste isolado.
- **Arquivos que podem ser tocados se necessário:**
- `src/universal_memory/bootstrap/cli.py` para injetar/resolver locale de forma controlada.
- `src/universal_memory/interfaces/mcp/server.py` e `tests/interfaces/mcp/test_server.py` apenas para proteger AC 2 se houver risco real de tradução no MCP.
- `src/universal_memory/infrastructure/config/toml_loader.py` apenas se for necessário helper pequeno de leitura de locale; prefira não alterar se `load_config(...)` já bastar.

### Testing Requirements

- Estratégia TDD: RED -> GREEN -> REFACTOR.
- Testar novo projeto: `.umem/config.toml` contém locale default `en` e hosts continuam persistidos.
- Testar idempotência: locale manual `pt-BR` não é sobrescrito para `en` quando `umem init` roda novamente.
- Testar saída humana default do `init` em inglês: não deve depender de português como `criada`, `Deseja configurar`, `Operacao cancelada` nos testes desta superfície.
- Testar saída humana com locale `pt-BR`: apenas mensagens/prompt humanos selecionados aparecem traduzidos; payload JSON equivalente continua inglês.
- Testar `--format json`: `json.loads(captured.out)` passa, `captured.err == ""`, chaves/códigos em inglês e sem texto traduzido ao redor.
- Testar MCP se tocado: resposta estruturada mantém keys em inglês quando config local define `pt-BR`.

### Previous Story Intelligence (1.5)

- Story 1.5 implementou `umem init`, saída humana/JSON, idempotência e offline-first.
- Review da Story 1.5 corrigiu acesso direto do CLI à infraestrutura e envelope JSON fora da spec; não reintroduzir esses problemas.
- O CLI evoluiu após a Story 1.5 para Typer/Rich em `interfaces/cli/init_command.py`; não seguir a nota antiga de implementar CLI mínima com `argparse`.
- Testes existentes ainda assertam strings em português (`criada`, prompts `Deseja configurar...`). Eles devem mudar para inglês canônico nesta story.
- `audit_reference` ainda pode ser placeholder estável onde a auditoria real não estiver implementada; não inventar auditoria nova para locale.

### Git Intelligence Summary

- Commit recente `d24dd2d docs(bmad): update PRD and architecture with 2026-05-31 Sprint Change Proposal` introduziu FR29 e a arquitetura English-first/localization overlay.
- Commits recentes também adicionaram guidance de memória, skills e MCP; por isso a story deve preservar payloads estruturados e não quebrar ferramentas existentes.
- O sprint planning revelou esta story como backlog adicionada após as primeiras stories de Epic 1, então ela deve adaptar código existente em vez de assumir scaffold inicial.

### Project Structure Notes

- O projeto já contém estrutura completa de Clean Architecture e várias interfaces. Story 1.6 é uma alteração transversal pequena, mas deve ficar concentrada em onboarding/config e CLI presenter.
- Evite criar abstrações genéricas de i18n além do necessário. Um catálogo de overlay simples é suficiente para AC 3.
- Não mover `DEFAULT_UMEM_SKILL_MARKDOWN` para fora se isso aumentar escopo; traduzir o conteúdo seedado no próprio arquivo é aceitável.

### References

- `_bmad-output/planning-artifacts/epics.md` (Story 1.6 / FR29 / Epic 1)
- `_bmad-output/planning-artifacts/prd.md` (FR29, Language & Visual Identity Guardrails, Journey 4)
- `_bmad-output/planning-artifacts/architecture.md` (Architecture Patch 2, English-First & Localization Overlay)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (JSON puro, human output, error envelope, MCP parity)
- `_bmad-output/implementation-artifacts/1-5-implementar-inicializa-o-cli-m-nima.md` (learnings e regressões a evitar)
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/infrastructure/config/toml_loader.py`
- `tests/application/test_setup_project.py`
- `tests/interfaces/cli/test_init_command.py`

## Dev Agent Record

### Agent Model Used

openai/gpt-5.5

### Debug Log References

- 2026-06-01: descoberta automática da próxima story em backlog via `sprint-status.yaml`.
- 2026-06-01: análise de `epics.md`, `architecture.md`, `prd.md`, `devex-interaction-spec.md` e Story 1.5.
- 2026-06-01: inspeção de código atual confirmou CLI Typer/Rich em `interfaces/cli/init_command.py`, composição em `bootstrap/cli.py` e config TOML em `infrastructure/config/toml_loader.py`.
- 2026-06-02: testes RED adicionados para locale default `en`, preservação de `pt-BR`, saída humana `init` English-first, JSON puro e erro JSON em inglês.
- 2026-06-02: implementação adicionou `[preferences] locale = "en"`, catálogo humano mínimo `pt-BR`, seed default skill em inglês e envelopes JSON/MCP com recovery hints em inglês.
- 2026-06-02: validações executadas: `uv run pytest tests/application/test_setup_project.py tests/interfaces/cli/test_init_command.py`, `uv run pytest tests/interfaces/mcp/test_server.py tests/interfaces/test_errors.py`, `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

### Completion Notes List

- Story contextualizada como guia de implementação pronto para dev.
- Guardrails adicionados para impedir tradução de JSON/MCP e regressões de automação.
- Escopo delimitado para locale e inglês canônico, sem antecipar splash visual ou migração completa de schema.
- Implementado locale padrão `[preferences] locale = "en"` no config TOML de novos projetos, preservando locale manual existente como `pt-BR`.
- Introduzido catálogo mínimo de mensagens humanas no CLI com inglês canônico e overlay `pt-BR` apenas para saída humana de `init`/hosts/erros esperados.
- Mantidos payloads CLI JSON e MCP em inglês estável; erro JSON agora usa mensagem e `recovery_hint` em inglês.
- Skill default `use-universal-memory` seedada em inglês canônico, com comandos e campos estruturados preservados.
- Suíte completa validada com 399 testes passando, Ruff sem erros e Pyright sem erros.

### File List

- `_bmad-output/implementation-artifacts/1-6-configurar-idioma-padr-o-e-locale.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/cli/message_catalog.py`
- `src/universal_memory/interfaces/errors.py`
- `tests/application/test_setup_project.py`
- `tests/interfaces/cli/test_init_command.py`

### Change Log

- 2026-06-01: Story criada com status `ready-for-dev`.
- 2026-06-02: Implementado locale padrão English-first com overlay humano `pt-BR`, proteção JSON/MCP e testes de regressão; status atualizado para `review`.
