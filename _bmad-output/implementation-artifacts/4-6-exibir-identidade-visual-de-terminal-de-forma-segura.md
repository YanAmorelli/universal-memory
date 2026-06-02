# Story 4.6: Exibir Identidade Visual de Terminal de Forma Segura

Status: review

## História

Como usuário executando comandos do `universal-memory` em um terminal humano interativo,
quero ver um splash banner compacto em ANSI/ASCII representando a conexão de um pendrive ao terminal,
para que a ferramenta tenha uma identidade visual reconhecível sem quebrar automações, JSON parseável, CI/CD ou ambientes sem suporte a cor.

## Critérios de Aceitação BDD

1. **Splash exibido somente no onboarding interativo humano**

   **Dado** um terminal humano interativo com `stdout.isatty() == True`
   **E** a execução do comando é em modo humano, sem `--format json`
   **E** o ambiente não indica CI/CD
   **Quando** o usuário inicia o onboarding interativo via CLI, por exemplo `umem init`
   **Então** um splash banner compacto em ANSI/ASCII é exibido no topo da saída de stdout antes do resultado humano do onboarding
   **E** o banner deve representar visualmente, de forma simples, uma conexão USB/pendrive ao terminal
   **E** o banner deve caber com segurança em larguras comuns de terminal, sem depender de largura maior que 80 colunas.

2. **Automação nunca recebe banner nem ANSI em stdout**

   **Dado** a flag `--format json`, modo não interativo ou ambiente de CI/CD
   **Quando** qualquer comando CLI é executado, incluindo `umem init`
   **Então** nenhum splash banner é emitido em stdout
   **E** nenhum escape code ANSI é emitido em stdout por causa do splash
   **E** no caso de `--format json`, stdout continua sendo JSON puro e parseável, sem texto Rich, logs, progress ou banner antes/depois do objeto JSON.

3. **Fallback sem cor respeita `NO_COLOR` e terminais sem cor**

   **Dado** a variável de ambiente `NO_COLOR` definida ou um terminal que não suporta cores
   **E** a execução ainda é interativa e humana
   **Quando** o splash banner é renderizado no `umem init`
   **Então** o sistema exibe uma versão em texto plano, legível, sem escape codes de cor
   **E** o conteúdo ASCII permanece reconhecível sem depender de cor para transmitir a marca.

4. **Escopo restrito ao CLI, sem regressão MCP/paridade**

   **Dado** o servidor MCP e os contratos CLI/MCP já validados na Story 4.5
   **Quando** a identidade visual de terminal é adicionada
   **Então** nenhum payload MCP, JSON-RPC, contrato de paridade CLI/MCP ou saída `--format json` é alterado
   **E** os testes existentes de paridade e conformidade continuam passando.

## Tarefas

- [x] Criar testes primeiro para a política de exibição do splash no CLI `init`.
- [x] Cobrir o caso positivo: `umem init` humano, `stdout.isatty() == True`, sem `--format json`, sem CI, sem `NO_COLOR`, renderiza banner compacto antes do output humano.
- [x] Cobrir supressão por `--format json`: stdout deve continuar começando com `{`, ser parseável por `json.loads`, e não conter marca/bordas/escape codes do splash.
- [x] Cobrir supressão em modo não interativo: quando `stdout.isatty() == False` ou `stdin.isatty() == False`, `umem init` não renderiza splash.
- [x] Cobrir supressão por CI/CD: quando `CI` está definido com valor truthy, `umem init` não renderiza splash.
- [x] Cobrir fallback `NO_COLOR`: com `NO_COLOR` definido e TTY interativo, renderizar versão sem escape ANSI.
- [x] Implementar helper pequeno no adapter CLI para decidir se o splash deve ser exibido, evitando espalhar condicionais no comando.
- [x] Implementar renderização ASCII/ANSI sem dependências externas novas, usando Rich/Console já disponível ou strings ANSI nativas conforme a arquitetura.
- [x] Chamar o splash apenas no fluxo humano de `_run_init`, antes do status spinner ou antes do output final, garantindo que ele não apareça em stderr e não contamine JSON.
- [x] Garantir que `--format json`, MCP e testes de paridade não sejam alterados por esta story.
- [x] Executar testes focados e validação geral mínima antes de marcar a story como concluída.

### Review Findings

- [x] [Review][Patch] Splash pode emitir ANSI quando `TERM` esta ausente ou vazio [src/universal_memory/interfaces/cli/init_command.py:884] — resolvido; `TERM` ausente/vazio agora usa splash plain ASCII sem ANSI e ha teste dedicado.

## Contexto / Guardrails do Desenvolvedor

### Fonte funcional da story

- `epics.md` define a Story 4.6 como parte do Epic 4, cobrindo FR30.
- FR30 exige que a experiência de onboarding CLI inclua um elemento compacto de marca terminal para `umem`, implementado como ANSI/ASCII splash art, com fallback sem cor e desabilitado automaticamente para JSON/non-interactive output.
- O PRD reforça a jornada de onboarding multi-runtime: `umem init` mostra arte ASCII/ANSI minimalista simulando conexão de pendrive ao terminal antes do prompt interativo.
- A arquitetura, no patch de 31/05/2026, especifica que o splash deve usar escape ANSI nativo sem dependências externas e ser desabilitado quando stdout é redirecionado, `CI=true`, `--format json` ou `NO_COLOR` estiver presente.

### Estado atual do código relevante

- `src/universal_memory/interfaces/cli/init_command.py` concentra o adapter CLI Typer/Rich e todos os comandos públicos.
- `_run_init(...)` executa seleção de hosts, setup do projeto, configuração de hosts e renderização final do output de `init`.
- `_run_init(...)` já separa o fluxo JSON do fluxo humano: JSON usa `print(json.dumps(...))`; humano usa `_stdout_console().print(...)`.
- `_selected_init_hosts(...)` já evita prompt interativo em JSON, com `--yes`, ou quando `sys.stdin.isatty()` é falso.
- `_stdout_console()` e `_stderr_console()` retornam `Console(file=sys.stdout/stderr, width=200)`. O helper de splash deve considerar `sys.stdout.isatty()` diretamente ou uma abstração testável, porque o `Console` atual fixa largura em 200 e não deve ser usado como evidência única de largura real.
- Não foi encontrada implementação atual de `splash`, `banner`, `NO_COLOR`, `CI` ou política equivalente no CLI.
- `tests/interfaces/cli/test_init_command.py` já cobre `init` humano, JSON puro, seleção interativa de hosts, locale, execução por módulo, idempotência, offline e envelopes de erro.
- `tests/interfaces/test_parity.py` valida matriz CLI/MCP e deve permanecer verde; o splash não deve afetar payloads estruturados.
- `src/universal_memory/interfaces/cli/message_catalog.py` existe com catálogo `pt-BR`, mas a renderização atual de `_format_human_init_output` ainda usa strings hardcoded em português. Isso é uma inconsistência herdada/concorrente de story anterior. Esta story não deve virar uma refatoração ampla de i18n; só corrija strings diretamente tocadas pelo splash se necessário para cumprir English-first.

### Comportamentos a preservar

- `umem init --format json` deve emitir exatamente um JSON parseável em stdout, sem Rich, sem logs, sem banner e sem ANSI.
- Erros esperados em JSON devem continuar usando o envelope atual de `error_payload`/`_print_expected_error`.
- `umem init` continua criando/reutilizando `.umem/` e retornando caminhos relativos conforme testes existentes.
- Modo offline deve permanecer sem acesso de rede.
- A seleção de hosts padrão em JSON/`--yes`/não interativo deve continuar usando `DEFAULT_ENABLED_HOST_IDS`.
- O splash é apresentação de CLI apenas; não cria arquivos, não altera `.umem/config.toml`, não registra auditoria e não passa pelo pipeline de mutação.

## Arquivos prováveis

- `src/universal_memory/interfaces/cli/init_command.py`
  - Adicionar helper(s) privados como `_should_render_init_splash(...)`, `_render_init_splash(...)` ou equivalente.
  - Chamar a renderização no fluxo humano de `_run_init(...)` somente quando a política permitir.
  - Manter lógica de negócio fora do adapter; o splash é apresentação, então pertence ao adapter CLI.

- `tests/interfaces/cli/test_init_command.py`
  - Adicionar testes focados para exibição/supressão/fallback do splash.
  - Preferir monkeypatch de `sys.stdin.isatty`, `sys.stdout.isatty`, `os.environ`, e captura `capsys`.

- `src/universal_memory/interfaces/cli/message_catalog.py` *(possível, somente se necessário)*
  - Se o banner tiver texto humano além de `umem`/ASCII, manter inglês canônico e, se traduzível, registrar overlay de `pt-BR` sem alterar campos de máquina.
  - Inferência: como o FR29/Architecture Patch 2 estabelece English-first, novos textos humanos devem ser escritos em inglês por padrão. Evidência: `architecture.md` linhas 909-918 e `prd.md` FR29.

## Requisitos técnicos

- Não adicionar dependências novas. `rich` já faz parte do stack (`rich>=15.0.0`) e pode ser usado para estilo humano, mas o fallback sem cor precisa ser determinístico.
- O banner deve ser compacto e ASCII-safe. Use somente caracteres ASCII para evitar problemas em terminais mínimos e para cumprir o requisito ANSI/ASCII.
- A arte deve caber em 80 colunas. Recomendação pragmática: manter cada linha com no máximo 60 caracteres.
- Detecção mínima obrigatória para exibir splash:
  - `output_format != "json"`
  - `sys.stdout.isatty() is True`
  - `sys.stdin.isatty() is True` para o onboarding interativo, pois a história fala de terminal humano interativo e a arquitetura fala em non-interactive automation.
  - variável `CI` ausente ou com valor não truthy.
- Detecção mínima obrigatória para não colorir:
  - `NO_COLOR` presente no ambiente desabilita cor.
  - Terminal/Console sem cor deve cair em texto plano. Se usar Rich, configure estilo para não depender de ANSI quando `NO_COLOR` estiver presente; se usar strings ANSI nativas, não inclua escapes nesse caminho.
- Não usar stderr para o splash. O requisito fala de saída do onboarding; a supressão de JSON se refere a stdout. Manter splash em stdout somente quando permitido evita misturar marca com progress/status.
- Evitar snapshot/auditoria/pipeline de mutação; renderizar banner é read-only e não deve gerar eventos.
- Não alterar MCP. Esta story é sobre terminal visual identity, não sobre JSON-RPC.
- Não alterar `sprint-status.yaml`; o orquestrador fará consolidação.

## Requisitos de teste

- Seguir TDD conforme requisito geral do planejamento: testes antes da implementação.
- Testes unitários/adapter esperados em `tests/interfaces/cli/test_init_command.py`:
  - `test_init_human_interactive_renders_terminal_splash` ou equivalente.
  - `test_init_json_never_renders_terminal_splash_or_ansi` ou equivalente.
  - `test_init_non_interactive_does_not_render_terminal_splash` ou equivalente.
  - `test_init_ci_environment_does_not_render_terminal_splash` ou equivalente.
  - `test_init_no_color_renders_plain_ascii_splash` ou equivalente.
- Asserções sugeridas:
  - Positivo: stdout contém `umem` e algum marcador ASCII estável da arte, por exemplo `USB`, `[]`, `==` ou outro escolhido pelo dev. Evite testes frágeis que dependem de todos os espaços da arte.
  - JSON: `json.loads(captured.out)` funciona; stdout começa com `{`; não contém `\x1b[`; não contém o marcador textual do splash.
  - `NO_COLOR`: stdout contém banner/marca, mas não contém `\x1b[`.
  - CI/não interativo: stdout não contém marcador do splash.
- Executar validação mínima:
  - `uv run pytest tests/interfaces/cli/test_init_command.py`
  - `uv run pytest tests/interfaces/test_parity.py`
  - `uv run pytest tests/interfaces/mcp/test_compliance.py`
  - Se tempo permitir, `uv run pytest`.
  - `uv run ruff check .` e `uv run pyright` se o código Python for alterado.

## Inteligência da história anterior

Story anterior relevante: `4-5-validar-conformidade-mcp-e-contratos-de-interface.md`, status `done`.

Lições e guardrails aplicáveis:

- A Story 4.5 ampliou a suíte offline de conformidade MCP e a paridade CLI vs MCP. Qualquer alteração nesta story deve manter esses testes verdes.
- A conformidade MCP valida ferramentas públicas, envelopes de sucesso, erros de domínio, erros inesperados e confirmações obrigatórias para mutações destrutivas. O splash não deve criar qualquer novo requisito MCP.
- A paridade CLI vs MCP foi ampliada para `init` e valida recursivamente chaves, tipos e valores escalares em payloads estruturados. Portanto, `--format json` de `init` não pode ganhar campos, prefixos, banners ou logs.
- A Story 4.5 corrigiu paths relativos no JSON de `init`; não reintroduzir `Path.cwd()` absoluto em payloads JSON.
- Arquivos tocados pela Story 4.5 e relevantes para esta story: `src/universal_memory/interfaces/cli/init_command.py`, `src/universal_memory/interfaces/mcp/server.py`, `tests/interfaces/mcp/test_compliance.py`, `tests/interfaces/test_parity.py`. Esta story provavelmente só deve tocar o primeiro e testes CLI.
- Review anterior apontou problemas de path relativo e exceções de filesystem no adapter CLI. Ao adicionar helpers de terminal, tratar acesso a ambiente/TTY de forma simples e robusta, sem deixar exceções de detecção de terminal quebrar o comando.

## Riscos / Edge Cases

- **Contaminação de JSON:** maior risco da story. Qualquer impressão antes/depois do JSON quebra automação e testes.
- **TTY em testes:** `capsys` pode fazer `sys.stdout.isatty()` retornar falso. Testes do caso positivo devem monkeypatchar explicitamente `sys.stdout.isatty` e `sys.stdin.isatty`.
- **CI variável:** algumas ferramentas definem `CI` como `true`, `1` ou outro valor não vazio. Implementar política simples: qualquer `CI` presente e não vazio desabilita splash. Se decidir tratar `CI=false` como falso, documentar no teste.
- **`NO_COLOR`:** a presença da variável, mesmo vazia, convencionalmente desabilita cor. Não exigir valor truthy para `NO_COLOR`.
- **Terminal sem cor:** se usar Rich, ele pode decidir suporte de cor baseado em ambiente. Não escreva teste dependente do terminal real; teste `NO_COLOR` como caminho determinístico.
- **Largura de terminal:** a arquitetura pede segurança para larguras comuns. Não usar arte larga nem depender de `Console.width` atual de 200.
- **i18n concorrente:** há inconsistência atual entre testes English-first e strings portuguesas hardcoded em `init_command.py`. Não ampliar escopo para refatorar todas as mensagens; se adicionar texto, use inglês canônico.
- **Ordem do output humano:** o AC pede banner no topo. Se houver spinner/status em stderr antes do stdout, isso não deve afetar stdout, mas visualmente pode aparecer antes em alguns terminais. Preferir renderizar o splash antes do status spinner para cumprir a intenção.

## Checklist de validação

- [x] Story implementada com mudança restrita ao adapter CLI/testes relevantes.
- [x] Banner aparece somente em `umem init` humano interativo permitido.
- [x] Banner não aparece em `--format json` e JSON continua parseável.
- [x] Banner não aparece em CI/CD.
- [x] Banner não aparece em modo não interativo/redirecionado.
- [x] `NO_COLOR` remove todos os ANSI escapes do splash e mantém arte legível.
- [x] Nenhum comportamento MCP foi alterado.
- [x] Testes de paridade CLI/MCP continuam passando.
- [x] Não foram adicionadas dependências novas.
- [x] Não houve alteração em `sprint-status.yaml`.
- [x] Dev Agent Record deve registrar comandos executados, resultados e qualquer divergência residual.

## Referências

- `_bmad-output/planning-artifacts/epics.md` linhas 796-818: definição da Story 4.6 e ACs originais.
- `_bmad-output/planning-artifacts/prd.md` linhas 153-160 e 385-388: jornada de onboarding e FR30.
- `_bmad-output/planning-artifacts/architecture.md` linhas 1008-1019: arquitetura do splash, supressão por JSON/CI/redirecionamento/NO_COLOR e onboarding.
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` linhas 35-44: contrato de JSON puro sem Rich/logs/prosa.
- `_bmad-output/implementation-artifacts/4-5-validar-conformidade-mcp-e-contratos-de-interface.md`: aprendizados sobre paridade e conformidade.

## Completion Note

Ultimate context engine analysis completed - comprehensive developer guide created.

## Dev Agent Record

### Implementation Plan

- Adicionar testes de adapter CLI para política do splash antes da implementação.
- Manter o splash restrito ao `init` humano interativo, com helper privado para centralizar `format`, TTY e CI.
- Renderizar arte ASCII compacta com ANSI nativo apenas quando cor for permitida, preservando fallback texto plano com `NO_COLOR`.
- Validar que JSON, paridade CLI/MCP e conformidade MCP continuam sem alterações de contrato.

### Debug Log

- `uv run pytest tests/interfaces/cli/test_init_command.py` após adicionar testes: falhou inicialmente como esperado por ausência do splash; ajustes nos testes isolaram dependências de host e mantiveram falhas focadas em `USB` ausente.
- `uv run pytest tests/interfaces/cli/test_init_command.py`: 18 passed.
- `uv run pytest tests/interfaces/test_parity.py`: 16 passed.
- `uv run pytest tests/interfaces/mcp/test_compliance.py`: 4 passed.
- `uv run ruff check .`: falhou inicialmente por linhas longas; formatação ajustada.
- `uv run ruff check .`: All checks passed.
- `uv run pyright`: 0 errors, 0 warnings, 0 informations.
- `uv run pytest`: 403 passed.
- `uv run pytest tests/interfaces/test_parity.py`: 16 passed.
- `uv run pytest tests/interfaces/mcp/test_compliance.py`: 4 passed.

### Completion Notes

- Implementado splash compacto ASCII/ANSI para `umem init` somente quando `output_format != "json"`, `stdin` e `stdout` são TTY e `CI` não está definido com valor truthy.
- Implementado fallback sem cor quando `NO_COLOR` está presente ou `TERM=dumb`, mantendo a marca e o marcador ASCII `USB` legíveis.
- Splash é escrito apenas em stdout no fluxo humano de `_run_init`, antes da seleção de hosts, spinner e output final.
- JSON de `init`, payloads MCP e contratos de paridade não foram alterados.
- Nenhuma dependência nova foi adicionada.
- `_bmad-output/implementation-artifacts/sprint-status.yaml` não foi alterado, conforme guardrail do usuário.

## File List

- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/interfaces/cli/test_init_command.py`
- `_bmad-output/implementation-artifacts/4-6-exibir-identidade-visual-de-terminal-de-forma-segura.md`

## Change Log

- 2026-06-01: Adicionado splash seguro do `umem init` para terminais humanos interativos, com supressão em JSON, CI e modo não interativo, mais fallback `NO_COLOR`.
- 2026-06-01: Adicionados testes focados de política do splash e executada validação completa da story.
