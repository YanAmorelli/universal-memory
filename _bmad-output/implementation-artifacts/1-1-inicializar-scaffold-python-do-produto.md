# Story 1.1: Inicializar Scaffold Python do Produto

Status: done


<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um desenvolvedor do universal-memory,
eu quero inicializar o pacote Python com estrutura, dependências e tooling definidos,
para que o projeto tenha uma base reproduzível para desenvolvimento TDD e trabalho paralelo.

## Acceptance Criteria

1. **Dado** um repositório sem scaffold Python completo,
   **Quando** o projeto é inicializado com `uv`,
   **Então** existem `pyproject.toml`, `uv.lock`, `.python-version`, `src/universal_memory/`, `tests/`, `tests/contracts/` e `benchmarks/`;
   **E** o runtime é Python 3.12+ e as dependências runtime/dev versionadas estão configuradas.

2. **Dado** o scaffold inicial,
   **Quando** os comandos de verificação são executados,
   **Então** `ruff`, `pyright` e `pytest` executam sem falhas sobre a base mínima;
   **E** há pelo menos um teste inicial que falharia se o pacote não fosse importável.

3. **Dado** o scaffold inicial versionado no repositório,
   **Quando** uma alteração é enviada para push ou pull request,
   **Então** um workflow de CI em `.github/workflows/ci.yml` executa `ruff`, `pyright` e `pytest`;
   **E** o workflow falha quando lint, type check ou testes automatizados falham.

## Tasks / Subtasks

- [x] **Task 1: Configurar Ambiente e Scaffold UV** (AC: 1)
  - [x] Criar ou configurar o arquivo `.python-version` com `3.12` ou superior.
  - [x] Configurar o scaffold básico com `uv init --package` no diretório raiz do projeto.
  - [x] Organizar e criar a raiz do pacote em `src/universal_memory/`.
- [x] **Task 2: Configurar Dependências e Ferramentas em pyproject.toml** (AC: 1, 2)
  - [x] Adicionar dependências de runtime recomendadas: `pydantic>=2.0`, `typer>=0.9.0` (opcional neste passo, mas recomendado), `tomli-w>=1.0.0` (para escrita TOML offline), e `fastmcp>=0.1.0` (para MCP server).
  - [x] Adicionar dependências de desenvolvimento: `pytest>=8.0.0`, `ruff>=0.3.0`, `pyright>=1.1.350`.
  - [x] Configurar a seção `[tool.ruff]` com regras estritas (ex: `select = ["E", "F", "I", "N", "UP", "PL", "RUF"]`).
  - [x] Configurar a seção `[tool.pyright]` definindo o layout de type check (ex: `include = ["src", "tests"]` e `typeCheckingMode = "standard"` ou `"strict"`).
  - [x] Executar `uv sync` para consolidar o lockfile `uv.lock`.
- [x] **Task 3: Estruturar a Árvore de Diretórios Clássica** (AC: 1)
  - [x] Criar os arquivos iniciais do pacote:
    - [x] `src/universal_memory/__init__.py` (expondo a versão do produto e garantindo importabilidade)
    - [x] `src/universal_memory/__main__.py` (entry point mínimo que pode ser executado via `python -m universal_memory`)
  - [x] Criar a estrutura completa de subdiretórios de testes:
    - [x] `tests/conftest.py` (fixtures globais e mocks mínimos de setup)
    - [x] `tests/contracts/` (para testes de conformidade com contratos dos ports)
    - [x] `tests/domain/` (para testes de entidades e exceções pura do domínio)
    - [x] `tests/application/` (para testes dos Use Cases)
    - [x] `tests/infrastructure/` (para testes de adapters de I/O, storage e segurança)
    - [x] `tests/interfaces/` (para testes da CLI e do servidor MCP)
  - [x] Criar o diretório `benchmarks/` e adicionar um arquivo placeholder/estrutura inicial (ex: `benchmarks/__init__.py`).
- [x] **Task 4: Implementar Teste de Importabilidade (Fumaça)** (AC: 2)
  - [x] Criar `tests/test_smoke.py` com pelo menos um teste inicial que verifique se o pacote `universal_memory` pode ser importado corretamente e expõe sua versão.
- [x] **Task 5: Configurar Workflow do GitHub Actions (CI)** (AC: 3)
  - [x] Criar `.github/workflows/ci.yml` configurado para executar a cada push e pull request direcionados à branch principal (`main` ou `dev`).
  - [x] Garantir que o pipeline instale o `uv`, configure o cache de dependências, execute o `ruff check`, `ruff format --check`, `pyright` para tipagem estática e finalmente rode `pytest` para testes unitários.
- [x] **Task 6: Validação Local do Tooling Completo** (AC: 2)
  - [x] Garantir que `uv run ruff check .` e `uv run ruff format --check .` executem sem falhas.
  - [x] Garantir que `uv run pyright` passe sem avisos ou erros.
  - [x] Garantir que `uv run pytest` seja executado com sucesso e todos os testes iniciais passem.

## Dev Notes

- **Estrutura Unificada de Diretórios e Boundaries:**
  - Deve-se seguir estritamente o layout estrutural descrito na arquitetura em [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L335-L398).
  - É proibido importar dependências de `infrastructure/` ou `interfaces/` dentro de `domain/` ou `application/`.
  - As interfaces (`cli` e `mcp`) e a infraestrutura (`storage`, `security`) devem ser desacopladas da lógica de negócios central por meio de ports em `domain/ports/`.
- **Gestão de Dependências com `uv`:**
  - Evite usar qualquer outra ferramenta que não seja o `uv`. A velocidade de resolução e execução local é fundamental para a performance do ciclo DevEx local.
  - Lembre-se de rodar `uv sync` sempre que o arquivo `pyproject.toml` for alterado para garantir que `uv.lock` permaneça consistentemente atualizado.
- **Diretrizes de Tipagem e Estilo:**
  - O linter `ruff` e o validador `pyright` não são opcionais; eles atuam como guardiões da saúde e legibilidade do código no repositório. O CI deve rejeitar qualquer código que falhe nesses passos.

### Project Structure Notes

- O projeto deve ser configurado utilizando o layout clássico do Python `src/` para evitar problemas com importações de pacotes locais não instalados durante a execução da CLI e MCP.
- O diretório `benchmarks/` deve ser mantido no mesmo nível de `src/` e `tests/` para facilitar execuções isoladas sem acoplamento com o runtime do pacote principal.

### References

- **Arquitetura de Software**: [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L335-L398)
- **Especificação de Interação DevEx**: [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- **PRD Completo**: [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash

### Debug Log References

- 2026-05-22: RED confirmado com `uv run --with pytest pytest tests/test_smoke.py`; falha esperada por `ModuleNotFoundError: No module named 'universal_memory'`.
- 2026-05-22: GREEN/validação final com `uv run ruff check .`, `uv run ruff format --check .`, `uv run pyright`, `uv run pytest` e `uv run python -m universal_memory`.

### Completion Notes List

- Scaffold Python inicial criado com `uv init --package`, runtime `>=3.12`, layout `src/`, `.python-version` e `uv.lock`.
- Dependências runtime e dev configuradas em `pyproject.toml`, incluindo `pydantic`, `typer`, `tomli-w`, `fastmcp`, `pytest`, `ruff` e `pyright`.
- Estrutura inicial de pacote, testes, contratos e benchmarks criada conforme arquitetura da story.
- Teste de fumaça garante importabilidade do pacote e exposição de `__version__`.
- CI configurado para push e pull request em `main` e `dev`, executando `ruff`, `pyright` e `pytest`.

### File List

- `.github/workflows/ci.yml`
- `.python-version`
- `benchmarks/__init__.py`
- `pyproject.toml`
- `src/universal_memory/__init__.py`
- `src/universal_memory/__main__.py`
- `tests/application/.gitkeep`
- `tests/conftest.py`
- `tests/contracts/.gitkeep`
- `tests/domain/.gitkeep`
- `tests/infrastructure/.gitkeep`
- `tests/interfaces/.gitkeep`
- `tests/test_smoke.py`
- `uv.lock`

### Change Log

- 2026-05-22: Inicializado scaffold Python do produto, tooling local, smoke test e CI; story movida para revisão.


### Review Findings

- [x] [Review][Decision] [Resolved: Dynamic] Versão do pacote duplicada e estática — A versão "0.1.0" está declarada em pyproject.toml e src/universal_memory/__init__.py.
- [x] [Review][Decision] [Resolved: Kept Unbounded] Dependências sem limite superior (Unbounded) — Pydantic, Typer, Tomli-w e Fastmcp estão declaradas sem limite superior no pyproject.toml.
- [x] [Review][Decision] [Resolved: Standard Checking] Pyright em modo strict nos testes — O Pyright está configurado com strict type checking sobre a pasta tests/, o que pode gerar atritos excessivos.
- [x] [Review][Decision] [Resolved: Extended] Conjunto de linters do Ruff restrito — Ruff seleciona apenas as regras ["E", "F", "I", "N", "UP", "PL", "RUF"]. Poderíamos estender para bandit (S) e bugbear (B).
- [x] [Review][Patch] Criar arquivos .gitkeep para subdiretórios de testes [tests/:1]
- [x] [Review][Patch] Adicionar licença e metadados de empacotamento no pyproject.toml [pyproject.toml:1]
- [x] [Review][Patch] Definir permissões de privilégio mínimo no CI [ci.yml:1]
- [x] [Review][Patch] Incluir benchmarks no escopo do Pyright [pyproject.toml:38]
- [x] [Review][Patch] Melhorar assertiva e escopo do teste de fumaça [tests/test_smoke.py:5]
- [x] [Review][Defer] Tratar BrokenPipeError na execução CLI [src/universal_memory/__main__.py:1] — deferred, pre-existing
- [x] [Review][Defer] Matriz de testes para múltiplas versões de Python no CI [.github/workflows/ci.yml:1] — deferred, pre-existing
- [x] [Review][Defer] Adicionar cobertura de testes com pytest-cov no CI [.github/workflows/ci.yml:1] — deferred, pre-existing


