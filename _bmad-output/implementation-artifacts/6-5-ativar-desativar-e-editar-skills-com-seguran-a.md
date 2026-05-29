# Story 6.5: Ativar, Desativar e Editar Skills com Segurança

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário ajustando skills existentes,
eu quero ativar, desativar e editar as skills registradas com guardrails,
para que eu controle quais capacidades estão disponíveis no sistema sem perder o histórico das metodologias formalizadas.

## Acceptance Criteria

1. **Dado** uma skill com status ativa (`status: active`), **Quando** o usuário solicita a sua desativação, **Então** o status da skill no repositório (`LatentSkillRepository`) muda para `ignored`, **E** a alteração gera um registro de auditoria (`AuditEventScope`) com a ação `deactivate_skill` e origem informada, **E** os arquivos físicos correspondentes (como `SKILL.md`) **não** são excluídos do sistema de arquivos para preservar o histórico e permitir reativação.
2. **Dado** uma skill desativada (`status: ignored`), **Quando** o usuário solicita a sua activation, **Então** o status da skill no repositório muda de volta para `active` se, e somente se, o arquivo físico obrigatório `SKILL.md` correspondente ainda existir no caminho esperado, **E** a transição de status gera um registro de auditoria com a ação `activate_skill` e origem informada, **E** se o arquivo `SKILL.md` estiver ausente ou corrompido (frontmatter inválido), o sistema reporta um erro claro (`ValidationFailedError`) e mantém o status original inalterado.
3. **Dado** uma edição de metadados ou de conteúdo da skill, **Quando** a alteração é aplicada, **Então** o sistema executa a escrita no disco de forma transacional e cria um snapshot de backup antes da gravação através de `SafeWriteUseCase`, **E** valida o novo conteúdo preventivamente contra vazamento de credenciais ou chaves sensíveis com o `SecretScannerPort`, **E** mantém o histórico de rollback por escopo disponível para a alteração executada.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes unitários e de integração (RED) para os Use Cases de Ativação, Desativação e Edição** (AC: 1, 2, 3)
  - [x] Criar o arquivo de testes `tests/application/skills/test_update_skill.py`.
  - [x] Escrever casos de teste para a desativação: verificar a mudança de status da entidade no repositório para `ignored`, garantir que o arquivo `SKILL.md` não foi apagado física ou logicamente e verificar a gravação do log de auditoria com a ação `deactivate_skill`.
  - [x] Escrever casos de teste para a ativação com sucesso: simular skill no status `ignored`, garantir que o arquivo `SKILL.md` físico correspondente existe e está íntegro e verificar a transição para `active` com o log de auditoria `activate_skill`.
  - [x] Escrever casos de teste para a ativação com erro: simular skill no status `ignored` mas com arquivo `SKILL.md` ausente ou com frontmatter corrompido, validando o lançamento de `ValidationFailedError` e garantindo que o status permaneceu `ignored`.
  - [x] Escrever casos de teste para a edição de metadados e conteúdo: injetar dublês de teste para `SafeWriteUseCase` e verificar que snapshots são acionados preventivamente, segredos sensíveis são escaneados com rejeição por `SecretDetectedError` e rollback está operacional caso haja uma falha durante o processo.

- [x] **Task 2: Implementar use cases `ActivateSkillUseCase`, `DeactivateSkillUseCase` e `UpdateSkillUseCase`** (AC: 1, 2, 3)
  - [x] Criar o arquivo `src/universal_memory/application/skills/update_skill.py`.
  - [x] Definir os comandos e resultados correspondentes para cada caso de uso:
    - `ActivateSkillCommand`, `ActivateSkillResult`
    - `DeactivateSkillCommand`, `DeactivateSkillResult`
    - `UpdateSkillCommand`, `UpdateSkillResult` (campos para editar de forma granular metadados como nome, triggers, etc., ou aceitar o raw markdown completo do arquivo `SKILL.md` atualizado).
  - [x] Implementar `DeactivateSkillUseCase`:
    - Ler a latent skill do repositório (`LatentSkillRepository.read`). Se o status não for `active`, levantar `ValidationFailedError`.
    - Atualizar o status para `ignored` na entidade `LatentSkill` e chamar `repository.write`. (O repositório já lidará com a auditoria padrão do registro).
  - [x] Implementar `ActivateSkillUseCase`:
    - Ler a latent skill do repositório. Se o status não for `ignored`, levantar `ValidationFailedError`.
    - Resolver o caminho físico esperado do arquivo `SKILL.md` (ex: `.umem/skills/<slug>/SKILL.md` para local ou `skills/<slug>/SKILL.md` para global).
    - Verificar se o arquivo físico existe no filesystem. Se não existir, lançar `ValidationFailedError` explicativo indicando o caminho ausente.
    - Se existir, efetuar a validação rápida da integridade do frontmatter markdown para garantir que continua mapeável para a entidade. Se for corrompido ou inválido, lançar `ValidationFailedError`.
    - Atualizar o status da entidade para `active` e salvar no repositório.
  - [x] Implementar `UpdateSkillUseCase`:
    - Ler a latent skill do repositório por ID.
    - Se a chamada for para atualizar metadados granulares (como alterar triggers ou descrição), reconstruir a entidade `LatentSkill` e regenerar o conteúdo markdown do `SKILL.md` correspondente usando o template padrão, salvando via `SafeWriteUseCase` (que cria snapshots e roda o scanner).
    - Se a chamada for para salvar um raw markdown completo (edição direta de arquivo pelo usuário), efetuar o parse do frontmatter YAML do novo markdown para extrair campos como `name`, `description`, `triggers` e atualizar os dados da entidade `LatentSkill`.
    - Gravar o conteúdo markdown atualizado em `SKILL.md` usando o `SafeWriteUseCase` correspondente ao escopo da skill.
    - Gravar a entidade `LatentSkill` atualizada no repositório `LatentSkillRepository.write`.
    - Tratar erros transacionais: reverter escritas na base de dados (`latent_skills.jsonl`) se a escrita no disco do `SKILL.md` falhar ou vice-versa, mantendo estado consistente.
  - [x] Registrar e exportar os novos use cases e DTOs no arquivo de bootstrap CLI/MCP e em `src/universal_memory/application/skills/__init__.py`.

- [x] **Task 3: Verificação final de qualidade e conformidade** (AC: 1, 2, 3)
  - [x] Executar a suíte de testes completa do repositório: `uv run pytest`.
  - [x] Executar a checagem de estilo e formatação: `uv run ruff check .` e `uv run ruff format --check .`.
  - [x] Executar a checagem de tipos estáticos: `uv run pyright`.

### Review Findings

- [x] [Review][Patch] Preservar a origem informada nos eventos de auditoria de ativação e desativação [src/universal_memory/infrastructure/storage/local_latent_skill_repository.py:249]
- [x] [Review][Patch] Corrigir rename de skill para manter o caminho de `SKILL.md` consistente com o slug atual [src/universal_memory/application/skills/update_skill.py:179]
- [x] [Review][Patch] Proteger rollback de arquivo para não mascarar a falha original nem deixar estado divergente [src/universal_memory/application/skills/update_skill.py:194]
- [x] [Review][Patch] Sincronizar remoção ou limpeza de `triggers` ao atualizar via markdown bruto [src/universal_memory/application/skills/update_skill.py:224]
- [x] [Review][Patch] Aceitar `SKILL.md` válido com BOM ou CRLF ao validar frontmatter [src/universal_memory/application/skills/update_skill.py:294]

## Dev Notes

- **Separação de Camadas (Clean Architecture)**:
  - Respeitar estritamente a barreira arquitetural. Toda a lógica de verificação de arquivos e parse de frontmatter markdown deve residir na camada de aplicação (`application/skills/update_skill.py`). Os adaptadores CLI/MCP apenas interagem com DTOs.
  - As interfaces e entrega CLI e MCP para estas operações não fazem parte desta story, devendo ser expostas apenas na Story 6.6.
- **Snapshots e Escrita Segura**:
  - A edição de conteúdo físico markdown deve invocar obrigatoriamente o `SafeWriteUseCase` correspondente ao escopo (`global` ou `project`).
  - O repositório `LatentSkillRepository` herda em seu construtor o `safe_write_use_case`, garantindo que atualizações na base de dados de latent skills também gerem snapshots locais e log de auditoria automatizados.
- **Tratamento de Exceções**:
  - Lançar `ValidationFailedError` para quaisquer falhas de transição de status inválidas ou arquivo físico de skill ausente.
  - Lançar `SecretDetectedError` se o scanner passivo encontrar chaves privadas ou credenciais sensíveis no conteúdo markdown sendo salvo.

### Project Structure Notes

- O arquivo do caso de uso de edição/toggle deve residir em `src/universal_memory/application/skills/update_skill.py`.
- O registro dos novos use cases deve ser feito em `src/universal_memory/application/skills/__init__.py`.
- Testes unitários/integração de aplicação devem residir em `tests/application/skills/test_update_skill.py`.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR21, FR22, FR23, FR24, FR25, FR26) - [prd.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md)
- `_bmad-output/planning-artifacts/architecture.md` (Skill Engine, CLI to MCP Parity Matrix) - [architecture.md](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md)
- `src/universal_memory/domain/entities/latent_skill.py` - [latent_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/entities/latent_skill.py)
- `src/universal_memory/application/skills/generate_skill.py` - [generate_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/skills/generate_skill.py)
- `src/universal_memory/application/skills/propose_skill.py` - [propose_skill.py](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/application/skills/propose_skill.py)

## Dev Agent Record

### Agent Model Used

Codex GPT-5

### Debug Log References

- `uv run pytest tests/application/skills/test_update_skill.py` - 10 passed
- `uv run pytest` - 360 passed
- `uv run ruff check .` - passed
- `uv run ruff format --check .` - passed
- `uv run pyright` - 0 errors

### Completion Notes List

- Implementados `ActivateSkillUseCase`, `DeactivateSkillUseCase` e `UpdateSkillUseCase` em `src/universal_memory/application/skills/update_skill.py`.
- Desativação e ativação validam transições de status e usam auditoria específica `deactivate_skill` e `activate_skill` no repositório local.
- Ativação valida existência e frontmatter mínimo de `SKILL.md` antes de alterar o status da latent skill.
- Edição granular e por markdown bruto grava `SKILL.md` via `SafeWriteUseCase`, aciona scanner/snapshot/auditoria e restaura o arquivo anterior se a escrita do repositório falhar.
- DTOs e use cases exportados em `src/universal_memory/application/skills/__init__.py`; bootstrap CLI/MCP constrói as novas dependências sem expor comandos de interface nesta story.

### File List

- `_bmad-output/implementation-artifacts/6-5-ativar-desativar-e-editar-skills-com-seguran-a.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/application/skills/update_skill.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`
- `tests/application/skills/test_list_skills.py`
- `tests/application/skills/test_update_skill.py`

### Change Log

- 2026-05-29: Implementados use cases de ativação, desativação e edição segura de skills; adicionados testes e validações completas; história movida para review.
