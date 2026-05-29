# Story 6.1: Registrar Latent Skills por Recorrência

Status: done

## Story

Como um usuário que repete metodologias e instruções,  
eu quero que o sistema registre oportunidades de skill latente,  
para que padrões recorrentes possam virar capacidades reutilizáveis sem eu reexplicar tudo.

## Acceptance Criteria

1. **Dado** uma instrução ou metodologia recorrente detectada por agente ou CLI, **Quando** ela é registrada como latent skill, **Então** o sistema persiste descrição, escopo, origem, contador de recorrência, timestamps, status e metadados, **E** a persistência usa o pipeline seguro de mutação.
2. **Dado** a mesma metodologia aparece novamente, **Quando** o sistema associa a ocorrência a uma latent skill existente, **Então** o contador de recorrência é incrementado, **E** a evidência de origem é preservada sem armazenar segredos.
3. **Dado** uma ocorrência ambígua, **Quando** o sistema não consegue associar com confiança, **Então** ele registra candidato separado ou solicita confirmação em vez de mesclar automaticamente, **E** evita inflar recorrência de skills não relacionadas.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes RED do contrato e repositório de Latent Skills** (AC: 1)
  - [x] Criar ou atualizar testes para garantir que `LatentSkillRepository` é uma interface/port de domínio abstrata válida.
  - [x] Criar `tests/infrastructure/storage/test_local_latent_skill_repository.py`.
  - [x] Cobrir operações CRUD básicas de `LocalLatentSkillRepository`: `read`, `list` com filtros de escopo e status, `write`, `delete` e `migrate`.
  - [x] Cobrir manipulação e persistência no formato JSONL sob `.umem/memory/latent_skills.jsonl` (projeto) e `~/.local/share/universal-memory/memory/latent_skills.jsonl` (global).
  - [x] Cobrir proteção contra concorrência e aquisição de locks (`.latent_skills.jsonl.lock`) seguindo a paridade com `local_fact_repository.py` e `local_rule_repository.py`.

- [x] **Task 2: Escrever testes RED do use case de registro e tracking** (AC: 1, 2, 3)
  - [x] Criar `tests/application/skills/test_track_latent_skill.py`.
  - [x] Testar criação de nova `LatentSkill` a partir de uma instrução inicial (recorrência inicial = 1, status = `proposed`).
  - [x] Testar incremento de recorrência para correspondências de alta confiança (mesmo padrão detectado).
  - [x] Testar criação de candidato separado para ocorrências ambíguas (evitando falsas correspondências).
  - [x] Testar validações de entrada e integração com `SecretScannerPort` (segredos bloqueados).
  - [x] Testar conformidade com o pipeline de mutação obrigatório (verificação de snapshot, escrita atômica e auditoria).

- [x] **Task 3: Implementar `LocalLatentSkillRepository` na infraestrutura** (AC: 1)
  - [x] Criar `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`.
  - [x] Fazer a classe implementar `LatentSkillRepository` e herdar as lógicas de lock e concorrência estabelecidas nas demais classes de storage local.
  - [x] Exportar `LocalLatentSkillRepository` em `src/universal_memory/infrastructure/storage/__init__.py`.

- [x] **Task 4: Implementar o use case de tracking e detecção de recorrência** (AC: 1, 2, 3)
  - [x] Criar diretório `src/universal_memory/application/skills/` se não existir.
  - [x] Criar `src/universal_memory/application/skills/track_latent_skill.py` contendo `TrackLatentSkillUseCase` e seus comandos de entrada/saída.
  - [x] Implementar a lógica de comparação para detecção de duplicidades/recorrências (análise de strings/similaridade das descrições e correspondência de escopo/tags).
  - [x] Integrar o pipeline seguro completo:
    1. Validar a entrada usando o modelo Pydantic do domínio (`LatentSkill`).
    2. Filtrar entrada pelo `SecretScannerPort` (rejeitando se contiver segredos com `SecretDetectedError`).
    3. Criar snapshot com `SnapshotRepository` (abortando em caso de erro com `SnapshotFailedError`).
    4. Gravar no repositório de forma atômica.
    5. Registrar auditoria no `AuditLogRepository` (originando da CLI ou MCP).
    6. Retornar referência de auditoria.

- [x] **Task 5: Verificação de qualidade e conformidade** (AC: 1, 2, 3)
  - [x] Executar a suíte de testes completa: `uv run pytest`.
  - [x] Executar o linter e formatador: `uv run ruff check .` e `uv run ruff format --check .`.
  - [x] Executar a checagem estática de tipos: `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Retorno genérico `object | None` em `LatentSkillRepository.write` e perda de tipagem estática — O contrato de `LatentSkillRepository.write` foi modificado para retornar `object | None`. O caso de uso `TrackLatentSkillUseCase` utiliza duck typing reflexivo (`hasattr` e `getattr`) para extrair referências de auditoria. Isso prejudica a análise estática (mypy) e acopla a camada lógica. Devemos criar uma entidade de retorno ou usar `SafeWriteResult` tipado no domínio/ports?
- [x] [Review][Decision] Crescimento ilimitado do histórico de evidências em `metadata["evidence"]` — Cada incremento de recorrência anexa uma evidência de origem e resumo sem limite máximo (capping). Habilidades com milhares de recorrências inflarão o JSONL e memória, tornando a persistência e leituras lentas de complexidade temporal quadrática. Devemos truncar/limitar (ex. manter as últimas 10 ou 20)?
- [x] [Review][Decision] Bypass silencioso do pipeline seguro caso `safe_write_use_case` seja omitido no repositório — Se `safe_write_use_case` for omitido, o repositório realiza um bypass direto gravando no disco sem validações de segredos, sem snaps e sem trilha de auditoria. Devemos proibir o bypass silencioso em produção e tornar o `safe_write_use_case` obrigatório?
- [x] [Review][Patch] Vulnerabilidade TOCTOU (Time-of-Check to Time-of-Use) na expiração de locks antigos [src/universal_memory/infrastructure/storage/local_latent_skill_repository.py:293-299]
- [x] [Review][Patch] Vazamento de lock obsoleto (stale) sob erro/interrupção de gravação do `lock_id` [src/universal_memory/infrastructure/storage/local_latent_skill_repository.py:92-119]
- [x] [Review][Patch] Mutação dinâmica do repositório em tempo de execução no construtor do usecase [src/universal_memory/application/skills/track_latent_skill.py:47-56]
- [x] [Review][Patch] Descarte de siglas e termos técnicos curtos (comprimento < 3) na regex de tokenização [src/universal_memory/application/skills/track_latent_skill.py:151]
- [x] [Review][Patch] Ação de auditoria incorreta (hardcoded) durante deleção/ignoração da skill [src/universal_memory/infrastructure/storage/local_latent_skill_repository.py:175]
- [x] [Review][Patch] Inconsistência no tratamento de corrupção no JSONL [src/universal_memory/infrastructure/storage/local_latent_skill_repository.py:144]
- [x] [Review][Patch] Poluição de diretório global no Windows usando padrão Unix [src/universal_memory/infrastructure/storage/local_latent_skill_repository.py:59]
- [x] [Review][Patch] Race condition em deleção concorrente antes da obtenção do lock [src/universal_memory/infrastructure/storage/local_latent_skill_repository.py:154-156]
- [x] [Review][Patch] Quebra de duck typing dinâmico se repositório customizado não contiver `global_data_root` [src/universal_memory/application/skills/track_latent_skill.py:51]
- [x] [Review][Defer] Alta concorrência e redundância de locks (listagens e escritas repetidas) [src/universal_memory/application/skills/track_latent_skill.py:83-90] — deferred, pre-existing
- [x] [Review][Defer] Ausência de fluxo interativo de confirmação em ocorrências ambíguas [src/universal_memory/application/skills/track_latent_skill.py:81-90] — deferred, pre-existing

## Dev Notes

- **Escopo desta story:** Criar o repositório de persistência e a lógica do use case que gerencia e contabiliza latent skills no pipeline de mutação seguro. Não implementar nesta história a CLI final de skills, servidor MCP correspondente, nem a geração real de estruturas de pastas físicas com `SKILL.md` (isso pertence às histórias 6.2, 6.3, 6.4 e 6.6).
- **Paridade de Infraestrutura:** Estender a infraestrutura local em JSONL para latent skills, garantindo a mesma maturidade de concorrência e testes de contrato dos fatos/regras locais.
- **Detecção de Segredos:** A interceptação do `SecretScannerPort` deve garantir que nenhuma evidência de origem persistida no metadados da skill contenha credenciais ou segredos em plain text.

### Project Structure Notes

- A nova implementação de domínio/ports e entidades já está devidamente modelada e exportada.
- O novo use case deve viver sob `src/universal_memory/application/skills/` seguindo a estrutura de Clean Architecture definida pela arquitetura.
- A persistência local concreta em JSONL deve ser colocada em `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR18, FR22, FR23, FR24, FR25, FR26)
- `_bmad-output/planning-artifacts/architecture.md` (Persistent Data Layout, Mutation Pipeline, Clean Architecture, Storage Contract)
- `_bmad-output/planning-artifacts/epics.md` (Epic 6, Story 6.1)
- `src/universal_memory/domain/entities/latent_skill.py`
- `src/universal_memory/domain/ports/latent_skill_repository.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py` (Referência para padrão de persistência lock / JSONL)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-29: Story 6.1 resolvida a partir de "epic-6" como primeira história backlog pendente em `sprint-status.yaml`.
- 2026-05-29: Analisados `sprint-status.yaml`, `epics.md`, `architecture.md`, `prd.md`.
- 2026-05-29: Carregadas entidades `LatentSkill` e port `LatentSkillRepository` do domínio.
- 2026-05-29: Analisado `local_fact_repository.py` como padrão de persistência lock e escrita segura JSONL.
- 2026-05-29: Testes RED adicionados para `LocalLatentSkillRepository` e `TrackLatentSkillUseCase`; falhas iniciais confirmaram ausência dos módulos.
- 2026-05-29: Implementados repositório JSONL local/global, export de infraestrutura, pacote `application.skills` e use case de tracking por similaridade/tags.
- 2026-05-29: `uv run pytest` passou com 307 testes.
- 2026-05-29: Checks focados passaram: `ruff check`, `ruff format --check` e `pyright` nos arquivos alterados desta story.
- 2026-05-29: Checks globais permanecem bloqueados por falhas pré-existentes fora do escopo em host/onboarding/CLI.

### Completion Notes List

- Análise de contexto e arquitetura concluída - guia compreensivo de implementação criado.
- História configurada como pronta para desenvolvimento com escopo e tarefas detalhados.
- Integração obrigatória do pipeline seguro de mutação explicitada na tarefa do use case.
- Guardrails definidos para prevenção de vazamento de segredos nos metadados de Latent Skills.
- Implementado `LocalLatentSkillRepository` com JSONL por escopo, lock `.jsonl.lock`, skip seguro de linhas corruptas em leitura diagnóstica, rejeição de corrupção durante escrita e integração opcional com `SafeWriteUseCase`.
- Implementado `TrackLatentSkillUseCase` com criação de candidato `proposed`, incremento de recorrência para matches de alta confiança, preservação de evidência sanitizada e criação separada para ocorrência ambígua.
- Atualizado contrato de `LatentSkillRepository.write` para permitir retorno de referência do pipeline seguro, alinhado a `FactRepository.write`.
- Bloqueio de conclusão: `uv run ruff check .`, `uv run ruff format --check .` e `uv run pyright` falham em arquivos fora da story; status mantido como `in-progress`.

### File List

- `src/universal_memory/application/skills/__init__.py`
- `src/universal_memory/application/skills/track_latent_skill.py`
- `src/universal_memory/domain/ports/latent_skill_repository.py`
- `src/universal_memory/infrastructure/storage/__init__.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`
- `tests/application/skills/test_track_latent_skill.py`
- `tests/domain/test_ports.py`
- `tests/infrastructure/storage/test_local_latent_skill_repository.py`

### Change Log

- 2026-05-29: Added latent skill local repository, tracking use case, domain port return contract alignment, and regression tests.
- 2026-05-29: Story remains `in-progress` because global Ruff/Pyright checks fail outside story scope.
