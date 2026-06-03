# Story 6.6: Expor Gestão de Skills por CLI e MCP

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário ou agente consumidor,
eu quero propor, listar e gerenciar as skills (incluindo ativação, desativação e atualização segura) por meio de interfaces unificadas de CLI e MCP,
para que automações e hosts possam interagir com o ciclo de vida das skills sem duplicação de lógica operacional ou de segurança.

## Acceptance Criteria

1. **Dado** os use cases de latent skills e registry já implementados (`ActivateSkillUseCase`, `DeactivateSkillUseCase`, `UpdateSkillUseCase`), **Quando** a interface CLI é acionada, **Então** o sistema expõe os comandos:
   - `umem skills activate <latent_skill_id>`
   - `umem skills deactivate <latent_skill_id>`
   - `umem skills update <latent_skill_id> [opções...]`
   **E** estes comandos executam os respectivos use cases de aplicação utilizando a origem consistente `"cli"`.

2. **Dado** os comandos de mutação CLI (`activate`, `deactivate`, `update`), **Quando** executados com sucesso no formato Rich padrão, **Então** eles criam snapshots, registram eventos no log de auditoria e imprimem uma saída legível por humanos detalhando o escopo alterado, caminhos relativos afetados e a referência de auditoria (`audit_reference`), em plena conformidade com `devex-interaction-spec.md`.

3. **Dado** o comando CLI `umem skills update <latent_skill_id>`, **Quando** o usuário deseja alterar metadados de forma granular, **Então** o CLI aceita as opções:
   - `--name <texto>` para atualizar o nome
   - `--description <texto>` para atualizar a descrição
   - `--trigger <texto>` (suportando múltiplas declarações, ex: `--trigger "trigger A" --trigger "trigger B"`) para atualizar gatilhos
   - `--file <caminho>` para passar um arquivo markdown físico como novo conteúdo da skill
   **E** o CLI passa as informações limpas ao `UpdateSkillCommand`.

4. **Dado** a execução com `--format json`, **Quando** qualquer comando de mutação CLI (`activate`, `deactivate`, `update`) é chamado, **Então** ele retorna estritamente uma saída JSON compatível com o envelope de sucesso padrão definido no `devex-interaction-spec.md` contendo `ok: true`, `operation`, `scope` e `data` contendo a skill atualizada, caminhos de arquivo, e o `audit_reference` gerado.

5. **Dado** o servidor MCP, **Quando** ele é iniciado, **Então** ele expõe as ferramentas:
   - `activate_skill(latent_skill_id: str)`
   - `deactivate_skill(latent_skill_id: str)`
   - `update_skill(latent_skill_id: str, name: str | None, description: str | None, triggers: list[str] | None, raw_markdown: str | None)`
   **E** estas ferramentas delegam para os mesmos use cases, utilizando `"mcp"` como origem e respeitando os mesmos contratos e envelopes de retorno JSON.

6. **Dado** a suíte de testes de paridade, **Quando** ela executa para gerenciamento de skills, **Então** valida que:
   - CLI com `--format json` e MCP retornam estruturas equivalentes.
   - Tratamentos de erros (`ValidationFailedError`, `SecretDetectedError`, `StorageError`) são mapeados corretamente para seus códigos JSON-RPC e envelopes correspondentes sem vazamento de dados sensíveis ou segredos.
   - Nenhuma mutação de skill contorna o pipeline seguro.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes unitários e de integração (RED) para as novas rotas CLI e MCP** (AC: 1, 2, 3, 4, 5, 6)
  - [x] Criar/atualizar testes de CLI em `tests/interfaces/cli/test_skills.py` para cobrir os comandos `activate`, `deactivate` e `update` (cenários de sucesso Rich/JSON e cenários de erro esperados).
  - [x] Criar/atualizar testes de MCP em `tests/interfaces/mcp/test_skills.py` para cobrir as ferramentas `activate_skill`, `deactivate_skill` e `update_skill`.
  - [x] Criar/atualizar testes de paridade em `tests/interfaces/test_parity.py` para verificar que as respostas JSON do CLI e MCP são semântica e estruturalmente equivalentes para todas as operações de mutação de skills.
  - [x] Garantir que erros de domínio (`ValidationFailedError`, `SecretDetectedError`, `StorageError`) se comportem de forma idêntica e segura em ambas as suítes de testes.

- [x] **Task 2: Implementar os comandos CLI de mutação na interface Typer** (AC: 1, 2, 3, 4)
  - [x] Atualizar `src/universal_memory/interfaces/cli/init_command.py` para expor os novos comandos no subgrupo `skills_app`:
    - Adicionar `@skills_app.command("activate")` e seu respectivo helper runner `_run_skills_activate`.
    - Adicionar `@skills_app.command("deactivate")` e seu respectivo helper runner `_run_skills_deactivate`.
    - Adicionar `@skills_app.command("update")` e seu respectivo helper runner `_run_skills_update` com suporte a `--name`, `--description`, `--trigger` (acumulável) e `--file` (com leitura de conteúdo seguro).
  - [x] Mapear as respostas Rich formatando retornos elegantes contendo escopo, caminho relativo da skill no filesystem e IDs de auditoria.
  - [x] Mapear o retorno JSON puro com o envelope padrão do `devex-interaction-spec.md` ao usar `--format json`.
  - [x] Mapear erros de domínio e exceções capturadas nos runners para os retornos amigáveis de CLI.

- [x] **Task 3: Expor as ferramentas equivalentes de skills no servidor MCP** (AC: 5, 6)
  - [x] Atualizar `src/universal_memory/interfaces/mcp/server.py`:
    - Adicionar `@server.tool(name="activate_skill")`.
    - Adicionar `@server.tool(name="deactivate_skill")`.
    - Adicionar `@server.tool(name="update_skill")` aceitando parâmetros opcionais (`name`, `description`, `triggers`, `raw_markdown`).
  - [x] Delegar a execução destas ferramentas para os mesmos `ActivateSkillUseCase`, `DeactivateSkillUseCase` e `UpdateSkillUseCase` injetados.
  - [x] Garantir que os retornos usem o envelope de sucesso padrão MCP e que os erros de domínio sejam devidamente traduzidos para códigos JSON-RPC usando a tabela de conformidade (ex: `SecretDetectedError` -> `-32010`, `ValidationFailedError` -> `-32602`).

- [x] **Task 4: Conectar e bootar dependências nas fábricas CLI e MCP** (AC: 1, 5)
  - [x] Atualizar `src/universal_memory/bootstrap/cli.py` para injetar os use cases `_activate_skill_use_case`, `_deactivate_skill_use_case` e `_update_skill_use_case` na fábrica `build_main`.
  - [x] Atualizar a assinatura e chamadas de `build_main` em `src/universal_memory/interfaces/cli/init_command.py` para receber os novos handlers de comandos de mutação de skills.
  - [x] Atualizar `src/universal_memory/bootstrap/mcp.py` para injetar os novos use cases no `MCPUseCases` e no construtor do servidor MCP.
  - [x] Atualizar a assinatura e propriedades de `MCPUseCases` em `src/universal_memory/interfaces/mcp/server.py` para incluir os novos use cases.

- [x] **Task 5: Rodar testes e validações de qualidade finais (GREEN)** (AC: 6)
  - [x] Executar toda a suíte de testes de integração e regressão: `uv run pytest`.
  - [x] Validar formatação e linting: `uv run ruff check .` e `uv run ruff format --check .`.
  - [x] Validar tipagem estática: `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Validar conflito entre `--file` e campos explícitos no update de skill [src/universal_memory/application/skills/update_skill.py:227]
- [x] [Review][Patch] `update_skill` falha para skills válidas materializadas em slug não canônico [src/universal_memory/application/skills/update_skill.py:179]
- [x] [Review][Patch] CLI reporta caminho afetado incorreto para mutações de skill global [src/universal_memory/interfaces/cli/init_command.py:2501]
- [x] [Review][Patch] Skill inexistente vaza como `storage_error` em vez de erro de validação/not-found [src/universal_memory/interfaces/cli/init_command.py:1775]
- [x] [Review][Patch] MCP `update_skill` não normaliza entradas como a CLI [src/universal_memory/interfaces/mcp/server.py:525]

## Dev Notes

- **Clean Architecture & Separação de Camadas**:
  - Os adaptadores de CLI (`init_command.py`) e MCP (`server.py`) devem apenas traduzir a entrada do usuário/host para DTOs de comando correspondentes (`ActivateSkillCommand`, `DeactivateSkillCommand`, `UpdateSkillCommand`) e enviar para os use cases da aplicação.
  - Nenhuma lógica de validação de arquivos ou checagem de frontmatter deve ser reimplementada no adaptador de CLI ou MCP. Isso já está devidamente encapsulado nos use cases de aplicação (`update_skill.py`).

- **Paridade Estrutural JSON (CLI vs MCP)**:
  - De acordo com o `devex-interaction-spec.md`, a saída JSON de `--format json` na CLI e o retorno JSON das ferramentas MCP devem compartilhar as mesmas chaves semânticas e envelopamento de sucesso/erro.
  - O envelope padrão de sucesso deve ser respeitado:
    ```json
    {
      "ok": true,
      "operation": "skills.activate",
      "scope": "project",
      "data": {
        "latent_skill": {
          "id": "6-6-expor-gest-o-de-skills-por-cli-e-mcp",
          "name": "Expor Gestão de Skills por CLI e MCP",
          "status": "active",
          "scope": "project"
        },
        "skill_file": "skills/6-6-expor-gest-o-de-skills-por-cli-e-mcp/SKILL.md",
        "audit_reference": "evt_abc123",
        "snapshot_reference": "snp_xyz789"
      },
      "warnings": []
    }
    ```

- **Leitura do Arquivo de Update (`--file`)**:
  - Ao usar `umem skills update <latent_skill_id> --file <caminho>`, o CLI deve carregar o conteúdo físico do arquivo markdown informado usando codificação UTF-8 e passá-lo como `raw_markdown` para o `UpdateSkillCommand`.
  - Caso o arquivo não exista no caminho informado na CLI, lançar um erro CLI amigável explicativo de validação.

### Project Structure Notes

- Interfaces de CLI residem em `src/universal_memory/interfaces/cli/init_command.py`.
- Interfaces de MCP residem em `src/universal_memory/interfaces/mcp/server.py`.
- Os bootrappers principais que unem tudo residem em `src/universal_memory/bootstrap/cli.py` e `src/universal_memory/bootstrap/mcp.py`.
- Testes devem estar sob `tests/interfaces/cli/test_skills.py`, `tests/interfaces/mcp/test_skills.py` e `tests/interfaces/test_parity.py`.

### References

- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (Output & Error Contracts, MCP Parity) - [devex-interaction-spec.md](file:///{project-root}/_bmad-output/planning-artifacts/devex-interaction-spec.md)
- `_bmad-output/planning-artifacts/prd.md` (FR11, FR12, FR18, FR21) - [prd.md](file:///{project-root}/_bmad-output/planning-artifacts/prd.md)
- `src/universal_memory/application/skills/update_skill.py` - [update_skill.py](file:///{project-root}/src/universal_memory/application/skills/update_skill.py)

## Dev Notes (Customizations / Past Learnings)

- **Preservação de estado**: De acordo com a história anterior (6.5), as operações de desativação (`deactivate_skill`) apenas alteram o status da latent skill para `ignored` no repositório, garantindo que o arquivo físico `SKILL.md` permaneça intacto para não perder histórico.
- **Validação de reativação**: A reativação (`activate_skill`) exige que o arquivo físico `SKILL.md` esteja no disco e tenha frontmatter legível/válido antes de retornar o status para `active`.

## Dev Agent Record

### Agent Model Used

Codex GPT-5

### Debug Log References

- `uv run pytest tests/interfaces/cli/test_skills.py tests/interfaces/mcp/test_skills.py` confirmou o ciclo RED/GREEN das rotas novas.
- `uv sync` foi necessário para resolver o ambiente MCP depois de o sandbox bloquear acesso ao cache do uv.
- `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run pyright` executados com sucesso.

### Completion Notes List

- Implementados os comandos CLI `skills activate`, `skills deactivate` e `skills update`, todos delegando para os use cases de aplicação com origem `cli`.
- Implementadas as ferramentas MCP `activate_skill`, `deactivate_skill` e `update_skill`, todas delegando para os mesmos use cases com origem `mcp`.
- Padronizados envelopes JSON de mutação de skills, saída humana com caminhos relativos, snapshot e auditoria, e mapeamento seguro de erros de domínio.
- Adicionados testes de CLI, MCP, paridade e compliance cobrindo sucesso, erros esperados e equivalência estrutural.

### File List

- `_bmad-output/implementation-artifacts/6-6-expor-gest-o-de-skills-por-cli-e-mcp.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/skills/update_skill.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/__init__.py`
- `tests/interfaces/__init__.py`
- `tests/interfaces/cli/__init__.py`
- `tests/interfaces/cli/test_skills.py`
- `tests/interfaces/mcp/__init__.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_skills.py`
- `tests/interfaces/test_parity.py`

### Change Log

- 2026-05-29: Expostas mutações de skills por CLI e MCP com paridade JSON, testes e validações finais.
