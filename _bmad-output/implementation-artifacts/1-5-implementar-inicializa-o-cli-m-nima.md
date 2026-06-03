# Story 1.5: Implementar Inicialização CLI Mínima

Status: done

## Story

Como um usuário do universal-memory,  
eu quero executar um comando inicial de projeto,  
para que eu possa ativar a memória local em um repositório novo com feedback claro.

## Acceptance Criteria

1. **Dado** testes CLI escritos antes da implementação, **Quando** o usuário executa `umem init` em um diretório sem `.umem/`, **Então** o comando cria a estrutura local do projeto, **E** retorna mensagem humana com caminhos criados, **E** com `--format json` retorna JSON puro contendo `project_path`, `config_path`, `memory_path`, `audit_path`, `snapshots_path`, `created`, `already_initialized` e `audit_reference`, **E** segue `devex-interaction-spec.md`.
2. **Dado** diretório já inicializado com `.umem/`, **Quando** o usuário executa `umem init` novamente, **Então** o comando é idempotente e não corrompe arquivos existentes, **E** informa que a memória já estava inicializada, **E** com `--format json` retorna `already_initialized: true`, `created: []` e os mesmos caminhos resolvidos.
3. **Dado** ambiente offline, **Quando** `umem init` é executado, **Então** a inicialização funciona sem conectividade externa.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes RED para CLI mínima** (AC: 1, 2, 3)
- [x] Criar `tests/interfaces/cli/test_init_command.py` cobrindo:
- [x] Execução de `init` em diretório limpo com saída humana contendo estado e próximos passos.
- [x] Execução de `init --format json` com JSON puro parseável e chaves obrigatórias.
- [x] Reexecução idempotente (`already_initialized: true`, `created: []`, sem corrupção).
- [x] Execução offline (sem qualquer dependência de rede; falha se houver tentativa de acesso externo).
- [x] Erros esperados com envelope/semântica consistente para CLI.
- [x] Confirmar fase RED antes de implementar adapter CLI.

- [x] **Task 2: Implementar adapter CLI mínimo para `umem init`** (AC: 1, 2, 3)
- [x] Evoluir `src/universal_memory/__main__.py` para expor comando `init` com parser de argumentos mínimo.
- [x] Suportar `--format json` com JSON puro em stdout, sem texto adicional.
- [x] Integrar com `setup_project` existente via adapters de config/layout já implementados.
- [x] Incluir `audit_reference` no payload de resposta com placeholder estável e explícito (`"not-implemented-yet"`), mantendo contrato sem inventar auditoria prematura.
- [x] Garantir código de saída `0` em sucesso e não-zero em erro esperado.

- [x] **Task 3: Padronizar saída e tratamento de erro para contrato DevEx** (AC: 1, 2)
- [x] Saída humana: indicar se criou ou reutilizou `.umem/`, listar caminhos relativos, sugerir próximo comando.
- [x] Saída JSON: manter formato determinístico e campos obrigatórios da spec.
- [x] Mapear exceções de domínio (`InvalidConfigError`, `StorageError`, `ValidationFailedError`) para mensagem acionável no CLI.
- [x] Não misturar lógica de negócio no adapter; apenas orquestração de I/O e formatação.

- [x] **Task 4: Verificação de qualidade e regressão** (AC: 1, 2, 3)
- [x] Executar `uv run pytest tests/interfaces/cli/test_init_command.py`.
- [x] Executar `uv run pytest` completo para regressões das stories 1.1-1.4.
- [x] Executar `uv run ruff check .` e `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Remover acesso direto do CLI à infraestrutura [`src/universal_memory/__main__.py:13`]
- [x] [Review][Patch] JSON de sucesso não segue o envelope DevEx [`src/universal_memory/__main__.py:59`]
- [x] [Review][Patch] Erros de filesystem fora das exceções de domínio podem vazar traceback [`src/universal_memory/__main__.py:49`]
- [x] [Review][Patch] Testes não exercitam execução real do CLI instalado ou como processo [`tests/interfaces/cli/test_init_command.py:7`]

## Dev Notes

- **Escopo desta story:** CLI mínima de inicialização (`umem init`) sobre use case já existente de onboarding, sem antecipar adapter CLI completo do Epic 4.
- **Objetivo de arquitetura:** manter `application` sem dependência de `infrastructure`/`interfaces`; CLI como adapter fino.
- **Contrato funcional central:** iniciar `.umem/` local e entregar feedback humano + resposta JSON parseável para agentes.

### Technical Requirements

- Python `>=3.12`; operação offline obrigatória.
- Reutilizar `setup_project(...)` de `application/onboarding/setup_project.py`.
- Reutilizar `LocalProjectLayoutPort` e `LocalConfigValidationPort` de `infrastructure/config/adapters.py`.
- Não criar novos modelos de domínio para esta história; apenas compor resposta de CLI.
- `--format json` deve imprimir **somente JSON** válido.

### Architecture Compliance

- Regra de dependência: `interfaces -> application -> domain <- infrastructure`.
- Não mover regras de negócio para `__main__.py`; usar `setup_project` para orquestração de inicialização.
- Preservar comportamento idempotente já existente no layout/config da Story 1.4.
- Não introduzir MCP, scanner de segredos, snapshot pipeline ou rollback nesta story.

### Library / Framework Requirements

- Implementar CLI mínima com biblioteca padrão (`argparse`) nesta story para menor superfície de risco.
- Manter compatibilidade com stack já declarada no projeto (`typer`, `fastmcp`, `pydantic`, `tomli-w`) sem acoplamento prematuro.
- Informação recente já registrada na Story 1.4 (data: 2026-05-24): `typer 0.25.1`, `rich 15.0.0`, `pydantic 2.13.4`, `tomli-w 1.2.0`, `fastmcp 3.3.1`.
- Inferência: a Story 1.5 não deve forçar upgrade de dependências; foco é contrato de inicialização CLI.

### File Structure Requirements

- **Arquivos UPDATE obrigatórios:**
- `src/universal_memory/__main__.py`
- **Arquivos NEW esperados:**
- `tests/interfaces/cli/test_init_command.py`
- **Arquivos que podem ser tocados se estritamente necessário:**
- `src/universal_memory/__init__.py` (apenas metadados/versão, se requerido por testes)
- `pyproject.toml` (somente se entrypoint/execução exigir ajuste mínimo)

### Testing Requirements

- Estratégia TDD: RED -> GREEN -> REFACTOR.
- Cobrir sucesso (novo projeto), idempotência (projeto já inicializado), formato JSON e offline-first.
- Validar parseabilidade JSON com `json.loads` no teste.
- Validar que caminhos retornados são relativos no payload/saída humana (`.`, `.umem/...`) para aderência DevEx.
- Garantir ausência de regressões nas suítes já existentes de domínio/aplicação/infra.

### Previous Story Intelligence (1.4)

- `setup_project` já retorna `created`, `already_initialized`, `created_paths` e `existing_paths`; aproveitar diretamente.
- Layout `.umem/` e validação TOML já foram endurecidos; CLI não deve reimplementar lógica de filesystem/config.
- Review anterior corrigiu violações de fronteira de camada; evitar novamente acoplamento direto de `application` com `infrastructure`.
- Padrão de qualidade vigente: executar `pytest`, `ruff`, `pyright` antes de fechar.

### Git Intelligence Summary

- Commit mais recente: `feat: harden project init layout and config loading` reforça robustez e idempotência do setup.
- Histórico recente consolidou base de domínio e contratos (`exceptions`, `ports`) para uso por interfaces.
- A story atual deve preservar incrementalidade: adicionar superfície CLI mínima sem refatoração ampla.

### Project Structure Notes

- Estrutura atual já contém `application/onboarding` e `infrastructure/config`; falta somente entrada CLI funcional.
- `src/universal_memory/__main__.py` hoje imprime string fixa; esse arquivo é o ponto de evolução natural para `umem init`.
- Não criar `interfaces/cli/` completo nesta story; isso pertence ao Epic 4.

### References

- `_bmad-output/planning-artifacts/epics.md` (Story 1.5 / ACs)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (`umem init`, JSON puro, chaves obrigatórias)
- `_bmad-output/planning-artifacts/architecture.md` (Clean Architecture, patterns CLI/MCP, dependências)
- `_bmad-output/planning-artifacts/prd.md` (FR9 e contrato offline-first)
- `_bmad-output/implementation-artifacts/1-4-criar-layout-local-umem-e-configura-o-toml.md` (learnings e guardrails)
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/infrastructure/config/adapters.py`
- `src/universal_memory/__main__.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-24: descoberta automática da próxima story em backlog via `sprint-status.yaml`.
- 2026-05-24: análise de `epics.md`, `architecture.md`, `prd.md`, `devex-interaction-spec.md` e learnings da story 1.4.
- 2026-05-24: revisão de estado de código atual (`__main__.py`, `setup_project.py`, adapters de config/layout).
- 2026-05-24: fase RED confirmada com `uv run pytest tests/interfaces/cli/test_init_command.py` falhando por `TypeError: main() takes 0 positional arguments but 1 was given`.
- 2026-05-24: fase GREEN da suíte CLI confirmada com `uv run pytest tests/interfaces/cli/test_init_command.py` (5 passed).
- 2026-05-24: entrypoint `umem` validado em diretório temporário com o projeto local como fonte.
- 2026-05-24: contrato de saída e erro revalidado com `uv run pytest tests/interfaces/cli/test_init_command.py` (5 passed).
- 2026-05-24: regressão completa validada com `uv run pytest` (60 passed).
- 2026-05-24: qualidade validada com `uv run ruff check .` e `uv run pyright` (sem erros).

### Completion Notes List

- Story contextualizada com tarefas TDD e guardrails de arquitetura para implementação segura.
- Critérios de saída humana e JSON definidos para aderência ao contrato DevEx.
- Escopo delimitado para evitar antecipação indevida do adapter CLI completo do Epic 4.
- Testes CLI RED/GREEN adicionados cobrindo inicialização limpa, JSON puro, idempotência, offline-first e envelope de erro esperado.
- Adapter CLI mínimo implementado com `argparse`, comando `init`, alias `umem`, composição via `setup_project` e placeholder de auditoria estável.
- Saídas humana e JSON padronizadas para caminhos relativos e erros esperados mapeados para envelope CLI acionável.
- Verificação final de regressão e qualidade concluída com 60 testes passando, `ruff` limpo e `pyright` sem erros.

### File List

- `_bmad-output/implementation-artifacts/1-5-implementar-inicializa-o-cli-m-nima.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `pyproject.toml`
- `src/universal_memory/__main__.py`
- `tests/interfaces/cli/test_init_command.py`

### Change Log

- 2026-05-24: Implementado `umem init` mínimo com saída humana, JSON puro, idempotência e envelope de erro esperado.
- 2026-05-24: Adicionada suíte CLI TDD para inicialização, idempotência, offline-first e erros esperados.
- 2026-05-24: Story movida para `review` após validação completa (`pytest`, `ruff`, `pyright`).
