# Story 5.1: Modelar Hosts e Alvos de Instrução

Status: done


<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como mantenedor configurando integrações de agentes,
quero um modelo explícito de hosts e instruction targets no domínio,
para que cada arquivo de instrução tenha ownership (propriedade) claro e não ocorra escrita duplicada ou drift de comportamento.

## Acceptance Criteria

1. **Modelagem de Hosts com Validação Robusta**:
   - **Dado** os hosts MVP `codex` e `claude_code`,
   - **Quando** os modelos de configuração de host são definidos no domínio,
   - **Então** cada host deve declarar explicitamente:
     - Os `instruction targets` suportados.
     - O método de configuração MCP (`mcp_config_method`).
     - A estratégia de validação de leitura (`read_validation_method`).
     - A estratégia de validação de escrita (`write_validation_method`).
     - O comportamento de reversão (`rollback_behavior`).
     - O tipo de evento de auditoria gerado (`audit_event_type`).
   - **E** os modelos devem ser validados de forma estrita com Pydantic v2 (herdando de `BaseEntity`).

2. **Garantia de Single-Writer Ownership para AGENTS.md**:
   - **Dado** o target compartilhado `agents_md` configurado como proprietário único de `AGENTS.md`,
   - **Quando** múltiplos hosts (como `codex` ou hosts futuros) declararem suporte ao `AGENTS.md`,
   - **Então** apenas o target `agents_md` é autorizado a escrever no arquivo compartilhado.
   - **E** os hosts consumidores devem referenciar o mesmo manifesto compartilhado de forma read-only em vez de gerar cópias próprias ou drifts.

3. **Isolamento de Deltas de Provedor em CLAUDE.md**:
   - **Dado** um target de instrução específico de provedor como `claude_md` (que escreve em `CLAUDE.md`),
   - **Quando** uma instrução de comportamento específica de provedor não couber no manifesto compartilhado `AGENTS.md`,
   - **Então** o modelo deve permitir classificá-la como um delta específico do provedor (`provider_delta`).
   - **E** a serialização do delta não deve duplicar nem copiar o conteúdo completo de `AGENTS.md`.

## Tasks / Subtasks

- [x] **Task 1: Implementar os Enums e Entidade InstructionTarget no Domínio** (AC: 2, 3)
  - [x] Criar `InstructionTargetType` como `StrEnum` com os valores `agents_md` e `claude_md` (e suporte expansível).
  - [x] Criar `InstructionClassification` como `StrEnum` contendo as classes canônicas de regras: `shared_policy`, `provider_delta`, `scoped_rule` e `canonical_doc`.
  - [x] Criar `InstructionTargetOwnership` como `StrEnum` representando `single_writer` e `delta_consumer`.
  - [x] Criar a entidade de domínio `InstructionTarget` herdando de `BaseEntity` em `src/universal_memory/domain/entities/instruction_target.py` contendo:
    - `name`: `InstructionTargetType`
    - `relative_path`: `str` (caminho seguro do arquivo, e.g. `AGENTS.md`, `CLAUDE.md`)
    - `ownership`: `InstructionTargetOwnership`
    - `supported_classifications`: `list[InstructionClassification]`
    - `metadata`: `dict[str, Any]`

- [x] **Task 2: Implementar a Entidade Host no Domínio** (AC: 1)
  - [x] Criar `HostName` como `StrEnum` representando os hosts do MVP: `codex` e `claude_code`.
  - [x] Criar a entidade de domínio `Host` herdando de `BaseEntity` em `src/universal_memory/domain/entities/host.py` contendo:
    - `name`: `HostName`
    - `supported_targets`: `list[InstructionTargetType]` (ou referências diretas de targets)
    - `mcp_config_method`: `str` (e.g. método de injeção ou setup MCP)
    - `read_validation_method`: `str`
    - `write_validation_method`: `str`
    - `rollback_behavior`: `str`
    - `audit_event_type`: `str` (deve se alinhar às ações de auditoria de mutação de instrução)
    - `metadata`: `dict[str, Any]`

- [x] **Task 3: Exportar Novas Entidades e Registrar Exportadores** (AC: 1, 2, 3)
  - [x] Atualizar `src/universal_memory/domain/entities/__init__.py` para exportar todos os enums e entidades de `host.py` e `instruction_target.py`.
  - [x] Garantir que o `__all__` inclua as novas classes expostas.

- [x] **Task 4: Implementar Suíte de Testes Unitários de Domínio** (AC: 1, 2, 3)
  - [x] Criar o arquivo de testes `tests/domain/test_host.py` e/ou expandir `tests/domain/test_entities.py` para validar:
    - Criação de instâncias válidas de `InstructionTarget` e `Host` utilizando payloads de dados corretos.
    - Rejeição de UUIDs v4 mal formatados para o campo `id` herdado.
    - Validação de que os timestamps `created_at` e `updated_at` exigem fuso horário consciente UTC.
    - Validação das constraints e limites de enums (por exemplo, falha ao inicializar com hosts não suportados fora do MVP).
  - [x] Assegurar conformidade rodando os comandos `uv run pytest` e `uv run ruff check` na pasta.

### Review Findings

- [x] [Review][Defer] Missing access mode classification (read-only vs write) for Host targets — deferred, resolved: Adiado para a camada de casos de uso (camada de aplicação) nas próximas stories.
- [x] [Review][Defer] Missing Instruction Entity and Serialization Validation — deferred, resolved: Adiado para as próximas stories (5.2/5.3), mantendo o escopo de 5.1 na infraestrutura básica de hosts e targets.
- [x] [Review][Defer] Lack of relationship validation between Host and InstructionTarget ownership — deferred, resolved: Adiado para a validação na camada de aplicação/serviço onde os repositórios estarão acessíveis.
- [x] [Review][Patch] Whitespace values in operational methods allowed and not stripped [src/universal_memory/domain/entities/host.py:88-99]
- [x] [Review][Patch] Platform-dependent directory traversal validation on Windows [src/universal_memory/domain/entities/instruction_target.py:141-147]
- [x] [Review][Patch] Hardcoded target-specific validations violate the Open-Closed Principle [src/universal_memory/domain/entities/instruction_target.py:149-165]
- [x] [Review][Patch] Lists permit duplicate entries in target and classification fields [src/universal_memory/domain/entities/host.py:80]
- [x] [Review][Patch] Loose string types for operational method fields [src/universal_memory/domain/entities/host.py:81-85]
- [x] [Review][Patch] Boilerplate manual blank-string validation [src/universal_memory/domain/entities/host.py:88-99]
- [x] [Review][Defer] Untyped escape hatch in metadata field [src/universal_memory/domain/entities/host.py:86] — deferred, pre-existing

## Dev Notes

- **Conformidade com a Base do Domínio**: Ambas as entidades `InstructionTarget` e `Host` devem herdar de `BaseEntity` para herdar o rastreamento canônico de `schema_version`, `id` (UUID v4), `created_at` e `updated_at`.
- **Validação Pydantic v2**: Utilizar a estrutura padrão adotada pelas demais entidades do projeto (ex: `Rule`, `Fact`), tirando proveito das validações automáticas do Pydantic para types e strings UUID v4 declarados.
- **Single-Writer Constraint**: Os instruction targets e hosts no domínio devem modelar e reforçar logicamente a restrição de que `AGENTS.md` tem propriedade exclusiva de escrita vinculada a `agents_md`. Outros adaptadores que referenciam o mesmo target operam de forma read-only.
- **Conexão de Auditoria**: O campo `audit_event_type` mapeado na modelagem de `Host` será utilizado pelas futuras stories de configuração do host para criar registros persistentes de auditoria (`AuditEvent`) a cada alteração ou check de leitura/escrita.

### Project Structure Notes

- As novas entidades de domínio serão alocadas na camada core:
  - `src/universal_memory/domain/entities/instruction_target.py` (Nova)
  - `src/universal_memory/domain/entities/host.py` (Nova)
  - `src/universal_memory/domain/entities/__init__.py` (Modificar)
- Os testes unitários associados devem ser inseridos em:
  - `tests/domain/test_host.py` (Nova)

### References

- [epics.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/epics.md#L810-L834) - Requisitos operacionais detalhados da Story 5.1.
- [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L753-L827) - Host Support Matrix e estratégias de regras de targets no universal-memory.
- [devex-interaction-spec.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md) - Especificação de retorno de erros de validação da camada de domínio.

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- `uv run pytest tests/domain/test_host.py` — 7 passed
- `uv run pytest` — 237 passed
- `uv run pytest tests/domain/test_host.py` — 14 passed
- `uv run pytest` — 244 passed
- `uv run pytest tests/domain/test_host.py` — 15 passed
- `uv run pytest` — 245 passed
- `uv run pytest tests/domain/test_host.py` — 17 passed
- `uv run ruff check` — All checks passed
- `uv run pytest` — 247 passed

### Implementation Plan

- Implementar `InstructionTarget` como entidade Pydantic v2 estrita, herdando de `BaseEntity`.
- Reforçar no domínio que `agents_md` escreve somente `AGENTS.md` com ownership `single_writer`.
- Reforçar no domínio que `claude_md` escreve somente `CLAUDE.md` como `delta_consumer` sem `shared_policy`.
- Implementar `Host` com enum explícito dos hosts MVP, lista obrigatória de targets e validação de campos operacionais não vazios.
- Exportar as novas entidades e enums no pacote `universal_memory.domain.entities` mantendo o padrão de `__all__` existente.
- Completar a suíte unitária de domínio cobrindo entidades válidas, invariantes de ownership, enum boundaries, UUID v4, timestamps UTC e exports públicos.

### Completion Notes List

- Implementados `InstructionTargetType`, `InstructionClassification`, `InstructionTargetOwnership` e `InstructionTarget`.
- Adicionadas validações de caminho relativo seguro, ownership single-writer de `AGENTS.md` e isolamento de delta para `CLAUDE.md`.
- Criados testes unitários de domínio para criação válida, UUID inválido, timestamps UTC, caminho inseguro e contratos de ownership/delta.
- Implementados `HostName` e `Host` com suporte explícito a `codex` e `claude_code`, incluindo métodos MCP, validações de leitura/escrita, rollback e tipo de auditoria.
- Expandidos testes unitários para hosts válidos, host fora do MVP, UUID inválido, timestamps UTC, lista vazia de targets e métodos operacionais em branco.
- Exportados `Host`, `HostName`, `InstructionTarget`, `InstructionTargetType`, `InstructionClassification` e `InstructionTargetOwnership` em `domain.entities`.
- Suíte de testes de domínio consolidada em `tests/domain/test_host.py` com 17 cenários cobrindo todos os ACs da story.
- Validação final concluída com `uv run pytest` e `uv run ruff check`.

### File List

- `src/universal_memory/domain/entities/instruction_target.py`
- `src/universal_memory/domain/entities/host.py`
- `src/universal_memory/domain/entities/__init__.py`
- `tests/domain/test_host.py`
