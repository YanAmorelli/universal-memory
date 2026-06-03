# Story 2.2: Criar Snapshot Antes de Mutação

Status: done

## Story

Como um usuário que permite alterações automáticas,  
eu quero que o sistema crie um snapshot local antes de qualquer escrita,  
para que eu possa recuperar o estado anterior se uma alteração automática for indesejada.

## Acceptance Criteria

1. **Dado** uma mutação automática em memória, regra, skill ou arquivo de instrução,  
   **Quando** o pipeline resolve o alvo da escrita,  
   **Então** um snapshot é criado antes da mutação,  
   **E** o manifest registra timestamp, escopo, ação responsável, caminho relativo e hash do conteúdo anterior.

2. **Dado** uma falha ao criar snapshot,  
   **Quando** a mutação é solicitada,  
   **Então** o pipeline aborta antes de escrever qualquer dado,  
   **E** retorna `SnapshotFailedError`.

3. **Dado** múltiplos snapshots no mesmo escopo,  
   **Quando** a política de retenção é aplicada,  
   **Então** pelo menos as 5 versões mais recentes por escopo são preservadas,  
   **E** versões antigas só são removidas após o snapshot novo ser confirmado.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes de contrato e unitários (TDD)** (AC: 1, 2, 3)
  - [x] Criar arquivo de testes de infraestrutura `tests/infrastructure/security/test_local_snapshot_repository.py`.
  - [x] Testar cenário feliz: criar snapshot de um arquivo existente, verificar que a cópia do arquivo é salva no subdiretório de snapshots e os metadados são inseridos no manifest JSON de forma correta.
  - [x] Testar cenário de falha: simular falha de escrita física ou erro de permissão de disco e validar se o repositório aborta lançando `SnapshotFailedError`.
  - [x] Testar cenário de retenção: gerar mais de 5 snapshots para o mesmo escopo (`project` ou `global`) e garantir que apenas os 5 mais recentes são preservados no manifest e que os arquivos físicos associados aos snapshots removidos são limpos do disco.
  - [x] Testar que a remoção das versões antigas só ocorre após o novo snapshot ser totalmente confirmado e escrito no manifest (garantia de transação de backup).

- [x] **Task 2: Implementar `LocalSnapshotRepository` em Infraestrutura** (AC: 1, 3)
  - [x] Criar o arquivo `src/universal_memory/infrastructure/security/local_snapshot_repository.py`.
  - [x] Implementar a classe concreta `LocalSnapshotRepository` herdando de `SnapshotRepository` (definido em `src/universal_memory/domain/ports/snapshot_repository.py`).
  - [x] Configurar a classe para aceitar o diretório base de dados correspondente (e.g. `.umem/` para escopo de projeto e `~/.local/share/umem/` para escopo global; atualizado por BUG-002).
  - [x] Utilizar a estrutura canônica definida para o armazenamento:
    - O arquivo manifest de controle: `.umem/snapshots/manifest.json` (ou o equivalente no caminho global).
    - O diretório físico para as cópias de backup: `.umem/snapshots/files/` (ou correspondente global).
  - [x] Implementar o método `write(self, entity: Snapshot)`:
    - Localizar o arquivo original no caminho absoluto derivado de `relative_path` a partir do diretório raiz.
    - Caso o arquivo exista, ler seu conteúdo binário ou em texto, validar que seu hash SHA-256 bate com o hash informado na entidade `Snapshot`, e salvar a cópia do arquivo em `.umem/snapshots/files/{entity.id}`.
    - Se o arquivo original não existir (por ser uma nova criação de arquivo sem estado anterior), pular a cópia física, mas registrar o metadado no manifest sinalizando a criação inicial.
    - Atualizar o arquivo `.umem/snapshots/manifest.json` adicionando a nova entidade serializada.
    - Executar a política de retenção mantendo apenas os 5 mais recentes por escopo e excluindo os excedentes.
  - [x] Implementar os métodos `read(self, id: str) -> Snapshot` e `list(self, scope: SnapshotScope | None = None, status: SnapshotStatus | None = None) -> list[Snapshot]`:
    - Garantir que as leituras e listagens filtrem corretamente os snapshots registrados no manifest de forma robusta e tipada.

- [x] **Task 3: Exportar o novo repositório em segurança** (AC: 1)
  - [x] Atualizar `src/universal_memory/infrastructure/security/__init__.py` para exportar `LocalSnapshotRepository`.
  - [x] Certificar que todos os imports de domínio são mantidos estritamente limpos (a infraestrutura conhece o domínio, mas o domínio nunca conhece a infraestrutura).

- [x] **Task 4: Validação de Qualidade e Ausência de Regressões** (AC: 1, 2, 3)
  - [x] Executar os testes criados: `uv run pytest tests/infrastructure/security/test_local_snapshot_repository.py`.
  - [x] Executar toda a suíte de testes do projeto para garantir zero quebras de regressão: `uv run pytest`.
  - [x] Validar conformidade de formatação e estática usando `uv run ruff check .` e `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Condição de Corrida Concorrente (Race Condition) no manifesto sem File Locking — Tanto a leitura `_load_snapshots()` quanto a escrita `_write_manifest()` acessam o arquivo `manifest.json` compartilhado sem qualquer mecanismo de trava de arquivo (como `fcntl`). Se múltiplos processos tentarem gravar um snapshot concorrentemente, haverá sobreposição de dados, levando a perda de registros de snapshots e acúmulo de cópias físicas órfãs.
- [x] [Review][Patch] Vazamento de arquivos temporários (`.tmp`) de cópias e manifesto em caso de falha física de escrita [src/universal_memory/infrastructure/security/local_snapshot_repository.py:84]
- [x] [Review][Patch] Propagação de `StorageError` em vez de `SnapshotFailedError` e falha em cascata em caso de manifesto corrompido [src/universal_memory/infrastructure/security/local_snapshot_repository.py:83]
- [x] [Review][Patch] Inconsistência de estado do pipeline se a exclusão pós-confirmação física dos snapshots antigos falhar [src/universal_memory/infrastructure/security/local_snapshot_repository.py:93]
- [x] [Review][Patch] Vulnerabilidade de Path Traversal na leitura de arquivos de origem fora do `project_root` [src/universal_memory/infrastructure/security/local_snapshot_repository.py:108]
- [x] [Review][Patch] Omissão de validação de `schema_version` ao carregar o manifesto [src/universal_memory/infrastructure/security/local_snapshot_repository.py:104]
- [x] [Review][Patch] Risco de `TypeError` na ordenação por comparação cronológica entre Datetimes Naive e Aware [src/universal_memory/infrastructure/security/local_snapshot_repository.py:81]
- [x] [Review][Patch] Política de retenção limitada apenas ao escopo de mutação alterado e expiração retroativa [src/universal_memory/infrastructure/security/local_snapshot_repository.py:151]

## Dev Notes

- **Escopo desta story:** Criar o repositório de snapshots e sua infraestrutura concreta (`LocalSnapshotRepository`). Não é escopo desta história integrar isso no pipeline geral de mutação (Story 2.3) ou criar os comandos CLI de listagem (Story 2.4); apenas os contratos e o repositório local robusto devem ser implementados e testados exaustivamente.
- **Padrão de escrita atômica do manifest:** A gravação em `.umem/snapshots/manifest.json` deve ser robusta. Recomenda-se realizar escrita atômica (gravar em arquivo temporário adjacente e renomear) para evitar corrupção do manifest em caso de interrupção ou falha no meio do processo.
- **Garantia de UTC:** Todos os timestamps e datetime devem usar timezone-aware UTC (`datetime.now(UTC)` ou similar), respeitando os validadores existentes no modelo `Snapshot` e `BaseEntity`.

### Project Structure Notes

- O repositório concreto deve ser criado em `src/universal_memory/infrastructure/security/local_snapshot_repository.py`, em simetria ao scanner de segredos (`entropy_secret_scanner.py`).
- O port `SnapshotRepository` já está definido em `src/universal_memory/domain/ports/snapshot_repository.py` e os testes em `tests/domain/test_ports.py` já garantem a conformidade da sua assinatura. Não modifique as assinaturas abstratas do port nem da entidade para evitar regressões nos testes que já passaram.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 2, Story 2.2, FR25, FR26)
- `_bmad-output/planning-artifacts/architecture.md` (Backup & Recovery, Persistent Data Layout, Mutation Pipeline)
- `_bmad-output/planning-artifacts/prd.md` (Backup & Recovery guardrails)
- `src/universal_memory/domain/entities/snapshot.py`
- `src/universal_memory/domain/ports/snapshot_repository.py`
- `tests/domain/test_ports.py`
- `_bmad-output/implementation-artifacts/2-1-implementar-scanner-de-segredos.md` (Learn-from reference)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-26: História alvo identificada como `2-2-criar-snapshot-antes-de-muta-o` a partir de `sprint-status.yaml` como a primeira história pendente (backlog).
- 2026-05-26: Analisados `epics.md`, `architecture.md`, `prd.md`, `snapshot.py` e `snapshot_repository.py` para garantir conformidade técnica absoluta.
- 2026-05-26: Detalhada a especificação dos arquivos a serem alterados e criados, bem como os passos de TDD e Tref.
- 2026-05-26: Story iniciada via `bmad-dev-story`; `sprint-status.yaml` e story movidos para `in-progress`.
- 2026-05-26: Testes RED criados em `tests/infrastructure/security/test_local_snapshot_repository.py`; falharam inicialmente por ausência de `LocalSnapshotRepository`.
- 2026-05-26: Implementado `LocalSnapshotRepository` com cópia física, manifest JSON, escrita atômica, leitura/listagem e retenção por escopo.
- 2026-05-26: Validações executadas com sucesso: `uv run pytest tests/infrastructure/security/test_local_snapshot_repository.py`, `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- `LocalSnapshotRepository` implementado em infraestrutura, herdando de `SnapshotRepository`.
- Snapshots existentes são copiados para `.umem/snapshots/files/{id}` após validação do hash SHA-256 informado pela entidade.
- Manifest `.umem/snapshots/manifest.json` é gravado com substituição atômica e contém snapshots serializados pelo modelo de domínio.
- Arquivos novos sem estado anterior são registrados no manifest sem cópia física.
- Retenção mantém as 5 versões mais recentes por escopo e só remove arquivos antigos depois que o novo manifest foi confirmado.
- Falhas de cópia, hash mismatch e problemas de persistência abortam a operação com `SnapshotFailedError` antes de registrar o snapshot.
- Story validada e movida para `review`.

### File List

- `_bmad-output/implementation-artifacts/2-2-criar-snapshot-antes-de-muta-o.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/infrastructure/security/__init__.py`
- `src/universal_memory/infrastructure/security/local_snapshot_repository.py`
- `tests/infrastructure/security/test_local_snapshot_repository.py`

### Change Log

- 2026-05-26: Implementado repositório local de snapshots da Story 2.2; status movido para `review`.
