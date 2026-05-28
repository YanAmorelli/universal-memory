# Story 4.1: Estruturar Adapter CLI com Typer e Rich

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário ou agente operando via terminal,
eu quero comandos CLI consistentes sobre os use cases de aplicação,
para que eu possa executar capacidades de memória manualmente ou por automação sem acessar infraestrutura diretamente.

## Acceptance Criteria

1. **Uso de Typer e Rich**:
   - **Dado** a camada de aplicação com use cases disponíveis,
   - **Quando** o adapter CLI é implementado ou migrado,
   - **Então** ele deve utilizar a biblioteca `typer` para declarar comandos, argumentos e opções de linha de comando;
   - **E** deve utilizar a biblioteca `rich` para formatar e colorir toda a saída humana padrão (mensagens de progresso, tabelas descritivas, painéis de informação, e spinners);
   - **E** toda a lógica de negócio deve ser estritamente delegada aos use cases de aplicação compartilhados recebidos via injeção de dependência na inicialização.

2. **Separação de Comandos de Leitura vs Mutações**:
   - **Dado** comandos read-only (`status`, `facts list`, `audit list`, `snapshots list`) e comandos de mutação (`init`, `facts purge`, `facts hygiene`, `rollback`),
   - **Quando** eles são executados via CLI,
   - **Then** comandos read-only nunca devem criar, modificar, deletar ou alterar qualquer arquivo físico local;
   - **And** comandos de mutação devem passar pelo pipeline seguro de escrita definido no Epic 2 (ex: utilizando `SafeWriteUseCase` ou repositórios seguros), gerando snapshots de rollback apropriados e registrando auditoria de escrita.

3. **Suporte de Formato Estruturado (JSON Puro)**:
   - **Dado** a flag global `--format json` (ou `-f json`) no comando principal da CLI,
   - **Quando** o usuário solicita formato JSON para qualquer comando,
   - **Then** a CLI deve imprimir apenas o payload JSON válido correspondente no `stdout`;
   - **And** a saída de sucesso deve seguir estritamente o envelope padronizado em `devex-interaction-spec.md` (chaves: `ok`, `operation`, `scope`, `data`, `warnings`);
   - **And** não deve incluir nenhum Rich markup, cor ANSI, quebra de linha humana, mensagens de depuração ou textos em `stdout` fora do payload JSON puro.

4. **Tratamento de Erros Actionable e Mapeamento Consistente**:
   - **Dado** exceções de domínio conhecidas (ex: `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, `StorageError`),
   - **Quando** elas ocorrem durante a execução de um comando CLI,
   - **Then** o adapter CLI deve capturar a exceção e formatar uma mensagem amigável no Rich (saída humana padrão) com título do erro, detalhe seguro, e hint de recuperação (sem exibir stack traces, a menos que uma opção debug esteja ativada);
   - **And** no formato JSON, deve responder com o envelope de erro padronizado (`ok: false` com as chaves `code`, `message`, `detail`, `recovery_hint`) e retornar um código de saída não-zero apropriado;
   - **And** erros inesperados não classificados devem ser tratados com um erro genérico seguro, sem expor segredos.

5. **Confirmação e Interatividade para Operações Críticas**:
   - **Dado** ações de mutação crítica (como `facts purge`, `facts hygiene` ou `rollback`),
   - **When** executadas pela CLI,
   - **Then** o sistema deve exibir um prompt interativo do Typer solicitando a confirmação do usuário (`Sim`, `Não`), resumindo o impacto esperado (escopo, caminhos afetados e se haverá snapshot);
   - **And** deve aceitar uma flag `--yes` (ou `-y`) para contornar qualquer interação/confirmação humana, o que é fundamental para execução por agentes e CI/CD.

## Tasks / Subtasks

- [x] **Task 1: Instalar e configurar dependências no pyproject.toml** (AC: 1)
  - [x] Validar a presença e versões mínimas de `typer` (>=0.25.1 ou >=0.9.0 conforme compatibilidade) e `rich` (>=15.0.0) no ambiente local.
  - [x] Garantir que o ambiente de desenvolvimento esteja atualizado (`uv sync`).

- [x] **Task 2: Estruturar a composição do Typer App no pacote interfaces/cli** (AC: 1)
  - [x] Criar ou adaptar a raiz do app Typer em `src/universal_memory/interfaces/cli/main.py` ou reestruturar `src/universal_memory/interfaces/cli/init_command.py`.
  - [x] Garantir que o callback principal declare a opção global `--format` (aceitando `"human"` ou `"json"`, com `"human"` sendo o default).
  - [x] Implementar a assinatura de `build_main` para expor uma interface compatível com `bootstrap/cli.py` (recebendo ports e use cases de aplicação e retornando um callable `(argv: Sequence[str] | None) -> int`).
  - [x] Garantir a execução segura por meio da chamada Click interna do Typer (ex: `app(args=list(argv))` ou convertendo os argumentos) para que os testes que chamam `main(["init"])` continuem funcionando sem alterações invasivas nas assinaturas de teste existentes.

- [x] **Task 3: Migrar os comandos da CLI para Typer** (AC: 1, 2, 3)
  - [x] Migrar comando `init` (`umem init`) delegando para o use case de setup do projeto.
  - [x] Migrar comando `status` (`umem status`) delegando para `GetMemoryStatusUseCase`.
  - [x] Migrar subcomando `facts list` (`umem facts list`) com suporte para opções de filtragem `--scope` e `--status`.
  - [x] Migrar subcomando `facts purge` (`umem facts purge`) com suporte para `--id`, `--scope` e a flag global de bypass `--yes` / `-y`.
  - [x] Migrar subcomando `facts hygiene` (`umem facts hygiene`).
  - [x] Migrar subcomando `audit list` (`umem audit list`) com filtro opcional de `--scope`.
  - [x] Migrar subcomando `snapshots list` (`umem snapshots list`) com filtro opcional de `--scope`.
  - [x] Migrar comando `rollback` (`umem rollback`) com opção de `--scope` e flag de bypass `--yes` / `-y`.

- [x] **Task 4: Implementar o Visual Premium Rich (Human Output)** (AC: 1, 2)
  - [x] Criar layouts profissionais e esteticamente agradáveis usando Rich:
    - [x] Tabelas formatadas para listagem de fatos, auditorias e snapshots.
    - [x] Painéis coloridos para erros (vermelho/laranja) e dicas de recuperação.
    - [x] Título moderno ou emojis elegantes nas confirmações de rollback ou purge.
  - [x] Garantir que mensagens humanas padrão informem o resultado das mutações contendo a referência do evento de auditoria gerado.

- [x] **Task 5: Implementar Output JSON Estrito** (AC: 3)
  - [x] Garantir que qualquer impressão em stdout sob a flag `--format json` passe por `json.dumps` do envelope exato.
  - [x] Impedir que qualquer chamada à biblioteca `rich` envie códigos ANSI ou caracteres adicionais para o stdout quando o formato JSON estiver ativo (pode-se redirecionar warnings para stderr se necessário, mas o stdout deve conter apenas JSON puro).

- [x] **Task 6: Consolidar Tratamento de Erros e Confirmações** (AC: 4, 5)
  - [x] Centralizar a tradução de exceções de domínio (`SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError`, `StorageError`) no CLI adapter.
  - [x] Implementar o prompt de confirmação de mutação interativa (usando recursos do Typer ou Rich) com os choices corretos (`Sim` e `Não`).
  - [x] Garantir que ao passar `--yes`, o prompt seja ignorado completamente.

- [x] **Task 7: Testes, Linting e Validação** (AC: 1, 2, 3, 4, 5)
  - [x] Validar a integridade da suíte de testes existente executando `uv run pytest`.
  - [x] Garantir que a migração de argparse para Typer não quebrou nenhum teste de integração ou contrato da CLI.
  - [x] Executar type check com `uv run pyright` e checagem de regras de linting com `uv run ruff check .`.

### Review Findings

- [x] [Review][Patch] Desativação de cores no console do Rich (`color_system=None` e `force_terminal=False`) [src/universal_memory/interfaces/cli/init_command.py:530]
- [x] [Review][Patch] Ausência de spinners e indicação visual de progresso para humanos [src/universal_memory/interfaces/cli/init_command.py]
- [x] [Review][Patch] Uso inadequado de `input()` cru do Python em vez do prompt de confirmação do Typer/Rich [src/universal_memory/interfaces/cli/init_command.py:601]
- [x] [Review][Patch] Ausência de prompt de confirmação e flag `--yes` no comando de mutação crítica `facts hygiene` [src/universal_memory/interfaces/cli/init_command.py:258]
- [x] [Review][Patch] Campo `audit_reference` ausente no envelope JSON de erro [src/universal_memory/interfaces/cli/init_command.py:867]
- [x] [Review][Patch] Ausência de tratamento adequado para exceções de sintaxe/uso da CLI e riscos de traceback [src/universal_memory/interfaces/cli/init_command.py:106]
- [x] [Review][Patch] Ausência de mapeamento e captura de exceções de domínio críticas nos fluxos do CLI [src/universal_memory/interfaces/cli/init_command.py:614]
- [x] [Review][Patch] Fragilidade e acoplamento complexo no cálculo do formato global (`_effective_format`) [src/universal_memory/interfaces/cli/init_command.py]
- [x] [Review][Patch] Assinaturas com retorno `Any` nas funções de formatação de tabelas do Rich [src/universal_memory/interfaces/cli/init_command.py]
- [x] [Review][Patch] Testes unitários com asserção estática frágil em `pyproject.toml` [tests/interfaces/cli/test_typer_rich_adapter.py:13]
- [x] [Review][Patch] Duplicidade e redundância na declaração da opção `--format` / `-f` [src/universal_memory/interfaces/cli/init_command.py]

## Dev Notes

- **Preservação de Compatibilidade em `build_main`**:
  - O arquivo `bootstrap/cli.py` instancia `build_main(...)` e chama o resultado passando os argumentos brutos (`argv`). Para manter essa harmonia sem quebrar a API interna nem os 190+ testes que validam o comportamento da CLI, o adaptador deve embrulhar a chamada do Typer app de forma transparente:
    ```python
    def build_main(
        *,
        layout_port: ProjectLayoutPort,
        config_validation_port: ConfigValidationPort,
        # ... outros comandos / use cases ...
    ):
        # Configurar estado global/estático das dependências que o Typer app usará
        # ...
        def configured_main(argv: Sequence[str] | None = None) -> int:
            if argv is None:
                argv = sys.argv[1:]
            try:
                # O Typer executa dentro da CLI e intercepta exceções do Click
                # Para evitar saídas abruptas, podemos capturar SystemExit
                # ou passar a lista exata para o Typer app
                typer_app(args=list(argv))
                return 0
            except SystemExit as e:
                return e.code
            except Exception as e:
                # Tratamento de erro inesperado fallback
                return 1
        return configured_main
    ```
- **Formatação de Saída Humana (Rich)**:
  - Utilize tabelas elegantes (`rich.table.Table`) com bordas estilizadas para listar dados.
  - Utilize `rich.console.Console` escrevendo diretamente em `sys.stderr` para mensagens auxiliares ou progresso, garantindo que o `stdout` seja limpo para fluxos de pipe ou JSON.
- **Tratamento de Exceções**:
  - Mapear cada erro de domínio para o código JSON apropriado no envelope JSON (por exemplo, `SecretDetectedError` => `validation_failed` ou similar) e para uma saída humana formatada em vermelho/laranja.

### Project Structure Notes

- O adaptador CLI deve residir em `src/universal_memory/interfaces/cli/`.
- Evite criar lógica de negócio no adapter. Toda a validação operacional e persistência real ocorrem nos use cases do domínio e aplicação.

### References

- **DevEx Interaction Specification**: [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- **Arquitetura de Software**: [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md)
- **PRD**: [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

Codex GPT-5

### Debug Log References

- 2026-05-28: Validação de compatibilidade da suíte pytest antes da escrita da história: 194 testes passando com sucesso.
- 2026-05-28: `uv sync` executado com sucesso após autorização para acesso ao cache global do uv.
- 2026-05-28: `uv run pytest` executado com sucesso: 196 testes passando.
- 2026-05-28: `uv run ruff check .` executado com sucesso.
- 2026-05-28: `uv run pyright` executado com sucesso: 0 erros.

### Completion Notes List

- Migrado o adapter CLI de `argparse` para composição `typer.Typer`, preservando a assinatura pública `main(argv)` e a integração de `build_main` com `bootstrap/cli.py`.
- Mantida a delegação de lógica de negócio para use cases injetados, incluindo `init`, `status`, `facts list`, `facts purge`, `facts hygiene`, `audit list`, `snapshots list` e `rollback`.
- Adicionada opção global `--format` / `-f` e mantida compatibilidade com `--format` nos comandos existentes para não quebrar contratos de teste e automação.
- Adicionado uso de Rich para saída humana, com tabelas para fatos, auditoria e snapshots, painéis Rich para erros humanos e consoles separados para `stdout`/`stderr`.
- Preservado JSON puro em `stdout` para `--format json`, incluindo envelopes de sucesso e erro existentes.
- Centralizado o mapeamento de `SecretDetectedError`, `SnapshotFailedError`, `ValidationFailedError`, `FactNotFoundError`, `InvalidConfigError` e `StorageError`.
- Adicionados testes de adapter para garantir exposição de app Typer e dependências runtime diretas de `typer` e `rich`.

### File List

- `pyproject.toml`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/interfaces/cli/test_typer_rich_adapter.py`
- `uv.lock`
- `_bmad-output/implementation-artifacts/4-1-estruturar-adapter-cli-com-typer-e-rich.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`

### Change Log

- 2026-05-28: Implementada migração do adapter CLI para Typer/Rich com compatibilidade dos contratos existentes, testes adicionais e validações completas.
