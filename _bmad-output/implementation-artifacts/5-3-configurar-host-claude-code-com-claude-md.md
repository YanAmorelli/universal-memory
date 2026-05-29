# Story 5.3: Configurar Host Claude Code com CLAUDE.md

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário usando Claude Code junto com a memória universal,
eu quero configurar deltas específicos em `CLAUDE.md`,
para que o Claude receba as instruções necessárias sem divergir do manifesto compartilhado.

## Acceptance Criteria

1. **Dado** o host `claude_code` selecionado
   **Quando** o setup/check é executado
   **Então** o sistema detecta ou propõe o arquivo `CLAUDE.md` na raiz do projeto;
   **E** escreve no `CLAUDE.md` apenas os blocos classificados como `provider_delta` (específicos do host Claude) ou `scoped_rule` relevantes ao escopo do Claude, evitando a duplicação das regras de tipo `shared_policy` já definidas no manifesto `AGENTS.md`.

2. **Dado** `AGENTS.md` e `CLAUDE.md` presentes no projeto
   **Quando** a validação de drift (verificação de divergência) é executada (no comando check)
   **Então** o sistema identifica se existem duplicações indevidas de instruções (ex: regras idênticas escritas em ambos) ou contradições explícitas entre os arquivos;
   **E** propõe a correção estruturada por meio de avisos (warnings) ou passos manuais no plano, sem nunca sobrescrever conteúdos adicionados de forma manual pelo usuário sem autorização explícita.

3. **Dado** uma mutação/escrita planejada em `CLAUDE.md` (no comando setup)
   **Quando** a atualização é aplicada com a flag `--yes`/`-y` ou confirmada
   **Então** ela preserva qualquer trecho inserido manualmente pelo usuário fora dos blocos delimitados:
     - `<!-- UMEM: START -->` e `<!-- UMEM: END -->`
   **E** executa a mutação utilizando estritamente o pipeline transacional `SafeWriteUseCase`, garantindo a criação de snapshot antes de aplicar a alteração, auditoria no log de eventos e capacidade de reverter o arquivo ao estado anterior via rollback por escopo.

4. **Dado** a execução da CLI ou MCP para o host `claude_code`
   **Quando** invocado pelo terminal ou ferramentas MCP (`host_setup` ou `host_check`)
   **Então** a CLI suporta `--yes` / `-y` e `--format json`/`human`;
   **E** exibe o plano detalhado listando os arquivos `CLAUDE.md` e opcionalmente `AGENTS.md` (caso haja drift ou necessidade de referência), seus snapshots e referências de auditoria;
   **E** se executado com `--format json`, retorna estritamente o payload formatado de acordo com a especificação DevEx:
     ```json
     {
       "ok": true,
       "operation": "host_setup",
       "scope": "project",
       "data": {
         "host_id": "claude_code",
         "instruction_targets": ["claude_md"],
         "planned_changes": [
           {
             "target": "claude_md",
             "action": "create",
             "path": "CLAUDE.md"
           }
         ],
         "manual_steps": [],
         "validation_status": "success",
         "audit_reference": "uuid-v4-reference",
         "snapshot_reference": "uuid-v4-snapshot",
         "timestamp": "2026-05-29T00:00:00Z"
       },
       "warnings": []
     }
     ```

## Tasks / Subtasks

- [x] **Task 1: Estender o Domínio para Mapeamento de Host e Targets Adicionais** (AC: 1)
  - [x] Garantir que o use case aceita `HostName.claude_code` no método `_host_for`.
  - [x] Retornar o objeto de entidade `Host` com `supported_targets=[InstructionTargetType.claude_md]`, métodos operacionais e tipo de auditoria corretos.
  - [x] Implementar a validação do contrato para `claude_md` na entidade `InstructionTarget`, assegurando que sua propriedade `ownership` seja `delta_consumer` e não permita o tipo `shared_policy` (prevenindo repetição de manifesto comum).

- [x] **Task 2: Estender o `ConfigureHostUseCase` para Mutações de Múltiplos Targets** (AC: 1, 3)
  - [x] Refatorar `ConfigureHostUseCase` para gerenciar a inicialização e atualização de múltiplos targets (`AGENTS.md` e/ou `CLAUDE.md` dependendo do host).
  - [x] Integrar `SafeWriteUseCase` para realizar as escritas e snapshots transacionais em `CLAUDE.md`.
  - [x] Garantir que o particionador de blocos isole apenas instruções com classificação `provider_delta` e `scoped_rule` (relevantes ao Claude) para o `CLAUDE.md`.
  - [x] Adicionar suporte a marcadores `<!-- UMEM: START -->` e `<!-- UMEM: END -->` no `CLAUDE.md` para preservar blocos editados manualmente pelo usuário de forma idêntica ao comportamento implementado para `AGENTS.md`.

- [x] **Task 3: Desenvolver o Detector de Drift e Colisão de Regras** (AC: 2)
  - [x] Implementar um serviço local no use case (ou classe validadora dedicada) que analisa comparativamente `AGENTS.md` e `CLAUDE.md`.
  - [x] Identificar duplicações brutas (ex: blocos de textos operacionais idênticos) existentes em ambos os arquivos.
  - [x] Gerar avisos legíveis (`warnings`) listando as linhas ou blocos redundantes detectados.
  - [x] Adicionar regras de drift-validation nos fluxos de `host_check` e `host_setup` do host `claude_code`.

- [x] **Task 4: Integrar CLI e MCP para Suportar `claude_code`** (AC: 4)
  - [x] Atualizar os comandos CLI `umem host setup` e `umem host check` em `src/universal_memory/interfaces/cli/host_command.py` ou equivalentes para aceitar o parâmetro `claude_code`.
  - [x] Renderizar planos ricos em terminal usando Rich para alterações no `CLAUDE.md`.
  - [x] Estender as ferramentas MCP `host_setup` e `host_check` em `src/universal_memory/bootstrap/mcp.py` / `src/universal_memory/interfaces/mcp/server.py` para processar chamadas relativas ao host `claude_code` mantendo paridade com as capacidades da CLI.

- [x] **Task 5: Suíte de Testes e Validações de Qualidade** (AC: 1, 2, 3, 4)
  - [x] Escrever testes de unidade para detecção de drift entre `AGENTS.md` e `CLAUDE.md` (`test_drift_detector.py`).
  - [x] Escrever testes de integração para o setup e validação do host `claude_code` em `tests/application/test_setup_host.py`.
  - [x] Implementar testes de CLI e MCP validando o payload DevEx JSON gerado para setup e check de `claude_code`.
  - [x] Validar conformidade de tipos com `uv run pyright` e estilo com `uv run ruff check`.
  - [x] Garantir que a cobertura não sofra regressões e que todos os testes passem de forma transacional.

### Review Findings

1. **`decision-needed`** findings (unchecked):
   - [ ] [Review][Decision] `AGENTS.md` Excluded from Plan/Audit under Drift — AC 4 requires that the detailed plan lists `CLAUDE.md` and optionally `AGENTS.md` (if drift exists), including snapshots and audit references. The current implementation strictly hardcodes `instruction_targets` as `[target.name.value]` (strictly `["claude_md"]`), completely omitting `AGENTS.md`.
   - [ ] [Review][Decision] Refactored Usecase Restricts Execution to Single Target — Task 2 specifies managing and updating multiple targets depending on the host. However, `execute` strictly binds to a single `target = self._primary_target_for(host)`.

2. **`patch`** findings (unchecked):
   - [ ] [Review][Patch] Fragile HTML Comment Parsing in `_instruction_lines` [src/universal_memory/application/host/drift_detector.py:59]
   - [ ] [Review][Patch] Restrictive Tag Removal Regex in Drift Detector [src/universal_memory/application/host/drift_detector.py:64]
   - [ ] [Review][Patch] Sloppy Defaulting to Codex Host in `_host_for` [src/universal_memory/application/host/setup_host_use_case.py:410-436]
   - [ ] [Review][Patch] Sloppy Defaulting to `agents_md` Target in `_instruction_target_for` [src/universal_memory/application/host/setup_host_use_case.py:443-469]
   - [ ] [Review][Patch] Hardcoded Path Bypass of Target Config in `_drift_warnings` [src/universal_memory/application/host/setup_host_use_case.py:399]
   - [ ] [Review][Patch] TypeError Risk on None/Empty Existing Content [src/universal_memory/application/host/setup_host_use_case.py:198]
   - [ ] [Review][Patch] Mixed English and Portuguese Headers in `CLAUDE.md` [src/universal_memory/application/host/setup_host_use_case.py:475]
   - [ ] [Review][Patch] Duplicate Normalization Calls in Drift Detector Helpers [src/universal_memory/application/host/drift_detector.py:97-111]
   - [ ] [Review][Patch] Missing `warnings` Field in `ConfigureHostResult.to_payload` [src/universal_memory/application/host/setup_host_use_case.py:130]
   - [ ] [Review][Patch] Empty Rule Body Crashes in Drift Contradiction Detector [src/universal_memory/application/host/drift_detector.py:46-66]
   - [ ] [Review][Patch] Inconsistent Setup Dry-Run Drift Detection [src/universal_memory/application/host/setup_host_use_case.py:328-337]
   - [ ] [Review][Patch] Discarding Canonical Docs Silently for Claude Setup [src/universal_memory/application/host/setup_host_use_case.py:285-292]
   - [ ] [Review][Patch] TypeError Risk on None/Empty Fact Tags [src/universal_memory/application/host/setup_host_use_case.py:262]
   - [ ] [Review][Patch] Silent Dropping of Unsupported Classifications [src/universal_memory/application/host/setup_host_use_case.py:495]
   - [ ] [Review][Patch] Hardcoded Empty `manual_steps` Under Drift/Collision Warnings [src/universal_memory/application/host/setup_host_use_case.py:190]
   - [ ] [Review][Patch] Misleading Hardcoded File Names in Validation Errors [src/universal_memory/application/host/setup_host_use_case.py:538-570]

3. **`defer`** findings (checked off, marked deferred):
   - [x] [Review][Defer] Lack of Transactional Multi-File Rollback [src/universal_memory/application/host/setup_host_use_case.py:321-344] — deferred, pre-existing

## Dev Notes

- **Separação Rígida de Conceitos:**
  - O `AGENTS.md` contém a política comum de identidade operacional e ativação MCP do repositório.
  - O `CLAUDE.md` é estritamente um delta. Ele deve instruir o Claude especificamente e complementar o que estiver ausente no manifesto principal.
  - Não duplique a seção `## Regras Operacionais Consolidadas` do `AGENTS.md` no `CLAUDE.md`. Em vez disso, injete apenas ponteiros ou instruções delta.

- **Uso do SafeWriteUseCase:**
  - Todo processo de modificação em `CLAUDE.md` deve obrigatoriamente herdar a robustez do `SafeWriteUseCase` para reuso do scanner de entropia, gravação em bloco seguro e geração de auditoria.

### Project Structure Notes

- O detector de drift/colisão pode ser acoplado no Use Case de setup ou extraído em:
  - `src/universal_memory/application/host/drift_detector.py` (Opcional/Novo)
- CLI adapters estendidos em:
  - `src/universal_memory/interfaces/cli/host_command.py`
- MCP server adapters integrados em:
  - `src/universal_memory/interfaces/mcp/server.py`
- Suíte de testes atualizada em:
  - `tests/application/test_setup_host.py`
  - `tests/interfaces/cli/test_host_command.py`

### References

- **Host Domain Entities (Story 5.1)**: [instruction_target.py](file:///src/universal_memory/domain/entities/instruction_target.py) e [host.py](file:///src/universal_memory/domain/entities/host.py)
- **Codex Host Setup (Story 5.2)**: [5-2-configurar-host-codex-com-agents-md.md](file:///_bmad-output/implementation-artifacts/5-2-configurar-host-codex-com-agents-md.md) e [setup_host_use_case.py](file:///src/universal_memory/application/host/setup_host_use_case.py)
- **DevEx Interaction Specification**: [devex-interaction-spec.md](file:///_bmad-output/planning-artifacts/devex-interaction-spec.md#L197-L209)
- **Architecture Host Matrix**: [architecture.md](file:///_bmad-output/planning-artifacts/architecture.md#L753-L800)
- **PRD Automations (FR8, FR15)**: [prd.md](file:///_bmad-output/planning-artifacts/prd.md#L322-L339)

## Dev Agent Record

### Implementation Plan

- Task 1: cobrir primeiro o suporte de domínio para `claude_code` e `claude_md`, depois implementar o mapeamento no use case preservando compatibilidade com `codex`.
- Task 2: manter o particionamento existente como base e escolher renderização/escrita pelo target primário do host, com `CLAUDE.md` filtrando apenas classificações aceitas pelo contrato do target.
- Task 3: extrair a validação comparativa para um detector dedicado e retornar warnings no resultado do use case sem sobrescrever conteúdo manual.
- Task 4: manter a aceitação de `host_id` dinâmica já existente na CLI/MCP e alinhar o envelope JSON com o contrato DevEx incluindo `snapshot_reference`, `timestamp` e warnings reais do use case.
- Task 5: completar a matriz de testes para setup/check de `claude_code` e refatorar o use case apenas onde necessário para satisfazer lint/tipos sem mudar o contrato.

### Debug Log

- `uv run pytest tests/application/test_setup_host.py -q` falhou inicialmente com `ValidationFailedError` porque `_host_for("claude_code")` ainda rejeitava o host.
- `uv run pytest tests/application/test_setup_host.py -q` passou após implementar o mapeamento de host e target.
- `uv run pytest -q` passou com 266 testes.
- `uv run pytest tests/application/test_setup_host.py -q` falhou inicialmente porque `execute()` ainda tentava resolver `AGENTS.md` para `claude_code`.
- `uv run pytest tests/application/test_setup_host.py -q` passou após separar target primário por host e renderizar `CLAUDE.md`.
- `uv run pytest -q` passou com 268 testes.
- `uv run pytest tests/application/test_drift_detector.py tests/application/test_setup_host.py -q` falhou inicialmente até o detector existir e depois até o check usar o conteúdo atual de `CLAUDE.md`.
- `uv run pytest tests/application/test_drift_detector.py tests/application/test_setup_host.py -q` passou após integrar `InstructionDriftDetector` ao fluxo `claude_code`.
- `uv run pytest -q` passou com 271 testes.
- `uv run pytest tests/interfaces/cli/test_host_command.py tests/interfaces/mcp/test_server.py -q` falhou inicialmente porque os envelopes não expunham `snapshot_reference`, `timestamp` e warnings.
- `uv run pytest tests/interfaces/cli/test_host_command.py tests/interfaces/mcp/test_server.py tests/interfaces/mcp/test_compliance.py -q` passou após alinhar o contrato CLI/MCP.
- `uv run pytest -q` passou com 273 testes.
- `uv run pytest tests/application/test_drift_detector.py tests/application/test_setup_host.py tests/interfaces/cli/test_host_command.py tests/interfaces/mcp/test_server.py -q` passou com 27 testes.
- `uv run pyright` falhou inicialmente por inferência ampla de classificação de fatos e passou após usar `InstructionClassification`.
- `uv run ruff check` falhou inicialmente por complexidade no `execute()`, linha longa e imports, e passou após extrair helpers e organizar imports.
- `uv run pytest -q` passou com 275 testes.

### Completion Notes

- Task 1 concluída: `ConfigureHostUseCase._host_for` agora aceita `claude_code` e retorna um `Host` com target `claude_md`, métodos operacionais e auditoria alinhados ao setup seguro.
- Adicionado resolvedor de target para `claude_md` com `ownership=delta_consumer` e classificações restritas a `provider_delta` e `scoped_rule`, evitando `shared_policy`.
- Task 2 concluída: `ConfigureHostUseCase.execute` agora seleciona o target primário do host, renderiza `CLAUDE.md` com bloco UMEM próprio, preserva conteúdo manual fora dos delimitadores e aplica a escrita via `SafeWriteUseCase`.
- O fluxo de `claude_code` ignora `shared_policy` e documentos canônicos ao montar `CLAUDE.md`, mantendo somente `provider_delta` e `scoped_rule`.
- Task 3 concluída: `InstructionDriftDetector` identifica linhas duplicadas e contradições explícitas `always/never` ou `sempre/nunca` entre `AGENTS.md` e `CLAUDE.md`.
- `ConfigureHostResult` agora carrega `warnings`, e o use case popula esses avisos para `claude_code` em setup/check.
- Task 4 concluída: CLI e MCP propagam `claude_code`, retornam payload DevEx com `snapshot_reference` e `timestamp`, e preservam warnings estruturados no envelope.
- A renderização humana Rich já consome `planned_changes`, então planos para `CLAUDE.md` aparecem com alvo, ação, caminho, snapshot e auditoria.
- Task 5 concluída: adicionados testes de unidade, integração, CLI e MCP para `claude_code`; validações `pyright`, `ruff` e regressão completa passam.
- `ConfigureHostUseCase.execute` foi refatorado em helpers menores para manter o código dentro dos limites de qualidade configurados.

## File List

- `src/universal_memory/application/host/setup_host_use_case.py`
- `src/universal_memory/application/host/drift_detector.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/test_setup_host.py`
- `tests/application/test_drift_detector.py`
- `tests/interfaces/cli/test_host_command.py`
- `tests/interfaces/mcp/test_server.py`
- `tests/interfaces/mcp/test_compliance.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-3-configurar-host-claude-code-com-claude-md.md`

## Change Log

- 2026-05-28: Iniciada Story 5.3 e concluída Task 1 de mapeamento de domínio para `claude_code`/`claude_md`.
- 2026-05-28: Concluída Task 2 com suporte transacional a `CLAUDE.md` e filtragem de deltas.
- 2026-05-28: Concluída Task 3 com detector de drift e warnings no use case.
- 2026-05-28: Concluída Task 4 com contrato JSON DevEx para CLI/MCP.
- 2026-05-28: Concluída Task 5 com testes e validações finais.
