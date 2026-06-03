# Story 3.4: Montar Resumo de Contexto com Limites de Tokens

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um agente que inicia uma nova sessão,  
eu quero receber um resumo compacto da memória aplicável,  
para que o contexto inicial me ajude sem causar overflow ou ruído no meu prompt.

## Acceptance Criteria

1. **Dado** fatos de projeto, preferências globais e regras ativas,  
   **Quando** o resumo de contexto é montado,  
   **Então** ele prioriza itens por escopo (projeto antes de global), recência (mais recentes primeiro), status (apenas ativos) e relevância (relevância para o escopo),  
   **E** separa claramente as seções `project_summary`, `universal_preferences` e `active_rules`.

2. **Dado** uma configuração de limite de tamanho de caracteres ou tokens (ex: `max_size_chars`),  
   **Quando** o conteúdo recuperado excede esse limite,  
   **Então** o sistema resume ou remove itens de menor prioridade de forma graciosa,  
   **E** preserva a referência (IDs de fatos) aos fatos originais usados para montar o resumo nos metadados ou na auditoria.

3. **Dado** uma leitura ou injeção de contexto solicitada por um agente,  
   **Quando** a operação é executada,  
   **Então** o sistema expõe evidência da última leitura, a origem do resumo (global ou projeto) e registra falhas de injeção por meio do status da entidade ou no log de auditoria,  
   **E** garante que nenhuma informação sensível/segredo detectada pelo `SecretScannerPort` seja exposta no resumo.

## Tasks / Subtasks

- [x] **Task 1: Implementar o Repositório Local de Resumo de Contexto (ContextSummaryRepository)** (AC: 1, 3)
  - [x] Criar a implementação `LocalContextSummaryRepository` em `src/universal_memory/infrastructure/storage/local_context_summary_repository.py`.
  - [x] Implementar leitura e gravação em um arquivo local `.umem/memory/context_summaries.jsonl` (ou similar) seguindo o padrão de persistência do `LocalFactRepository`.
  - [x] Suportar migração de esquemas com o método `migrate`.
  - [x] Criar testes de unidade e integração completos em `tests/infrastructure/storage/test_local_context_summary_repository.py` garantindo isolamento de escrita.

- [x] **Task 2: Projetar e Implementar o Caso de Uso AssembleContextSummaryUseCase** (AC: 1, 2, 3)
  - [x] Criar o arquivo `src/universal_memory/application/memory/assemble_context_summary_use_case.py`.
  - [x] Definir os DTOs `AssembleContextSummaryCommand` e `AssembleContextSummaryResult`. O comando deve aceitar `scope`, `max_size_chars`, e opcionalmente uma chave de identificação do agente ou sessão.
  - [x] Buscar ativamente os fatos usando `FactRepository` e as regras ativas usando `RuleRepository`.
  - [x] Filtrar fatos inativos, obsoletos ou marcados como sensíveis (segredos) utilizando a porta `SecretScannerPort`.
  - [x] Implementar o algoritmo de ordenação e priorização:
    - Priorizar fatos do escopo solicitado (`project` vs `global`).
    - Ordenar por recência (`created_at` decrescente) e opcionalmente por número de ocorrências (`recurrence_count`).
  - [x] Estruturar o resumo de contexto com as chaves bem delimitadas:
    - `project_summary`: Resumo dos fatos específicos do projeto.
    - `universal_preferences`: Preferências globais consolidadas do usuário.
    - `active_rules`: Regras de comportamento ativas relevantes.
  - [x] Implementar o controle de limites de tamanho:
    - Se a soma das seções exceder `max_size_chars`, podar os fatos de menor prioridade.
    - Sumarizar o texto caso a quantidade de caracteres persista acima do limite de segurança.
  - [x] Gerar e persistir um evento de auditoria no `AuditLogRepository` registrando a leitura do contexto com a lista de IDs de fatos incluídos (evidência de última leitura, FR16).
  - [x] Salvar o `ContextSummary` gerado via `ContextSummaryRepository` associado à auditoria gerada.

- [x] **Task 3: Desenvolver a Suíte de Testes de Unidade e Integração do Caso de Uso** (AC: 1, 2, 3)
  - [x] Criar testes de caso de uso em `tests/application/memory/test_assemble_context_summary_use_case.py`.
  - [x] Testar cenários em que o limite de tamanho é estritamente respeitado (verificar remoção graciosa de fatos menos prioritários).
  - [x] Testar a integração do Secret Scanner garantindo que fatos que disparam o scanner sejam ocultados/bloqueados no resumo de injeção.
  - [x] Validar a escrita de eventos de auditoria e geração da evidência contendo os IDs dos fatos consumidos.
  - [x] Testar o comportamento em caso de falha de injeção ou base corrompida.

- [x] **Task 4: Validação Estática e Qualidade**
  - [x] Garantir 100% de passagem nos testes rodando `uv run pytest`.
  - [x] Executar o ruff para verificação de estilo: `uv run ruff check .`.
  - [x] Executar pyright para validação de tipos estritos: `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Crescimento Infinito do Histórico de Resumos de Contexto — O repositório JSONL anexa novos resumos indefinidamente, causando degradação de desempenho. Devemos implementar uma estratégia de retenção (ex: manter últimos 100 itens) ou deixar crescer sem limites?
- [x] [Review][Patch] TOCTOU e Race Condition na Criação e Checagem do Arquivo de Lock [src/universal_memory/infrastructure/storage/local_context_summary_repository.py:41-78]
- [x] [Review][Patch] Inversão de Prioridade e Exclusão Cega de Regras Ativas no Controle de Limites [src/universal_memory/application/memory/assemble_context_summary_use_case.py:227-248]
- [x] [Review][Patch] Mistura de Prioridades entre Escopo e Tags de Alta Prioridade [src/universal_memory/application/memory/assemble_context_summary_use_case.py:269-276]
- [x] [Review][Patch] Violação do Limite de Caracteres em Limites Muito Curtos ou Negativos [src/universal_memory/application/memory/assemble_context_summary_use_case.py:110-137]
- [x] [Review][Patch] Regras Bloqueadas por Contaminação com Segredos Omitidas na Auditoria [src/universal_memory/application/memory/assemble_context_summary_use_case.py:196-216]
- [x] [Review][Patch] Gargalo de Concorrência por Uso de Lock Exclusivo em Leituras [src/universal_memory/infrastructure/storage/local_context_summary_repository.py:85-98]
- [x] [Review][Patch] Exceção de Banco de Dados Corrompido Ocultada como Item Não Encontrado [src/universal_memory/infrastructure/storage/local_context_summary_repository.py:79-83]
- [x] [Review][Patch] Cobertura de Teste Ausente para Cenários de Limite Apertado e Priorização de Regras [tests/application/memory/test_assemble_context_summary_use_case.py:249-274]

## Dev Notes

- **Separador de Conteúdo:** O resumo do contexto injetado no prompt deve ser estruturado em Markdown limpo, usando blocos de código ou marcadores claros para:
  - `# MEMORY CONTEXT SUMMARY`
  - `## Project Summary`
  - `## Universal Preferences`
  - `## Active Rules`
- **Portas a Utilizar:**
  - `FactRepository` para recuperar fatos relevantes.
  - `RuleRepository` para recuperar regras ativas.
  - `SecretScannerPort` para interceptar e bloquear vazamento acidental de chaves de API/segredos.
  - `AuditLogRepository` para gravar o evento de injeção/leitura.
  - `ContextSummaryRepository` para salvar o histórico de resumos gerados.
- **Fatores de Priorização:**
  - Fatos de status `active` devem ser priorizados. Fatos de status `stale`, `archived` ou `purged` devem ser totalmente ignorados.
  - Fatos com tags de alta prioridade (como `preferences` ou `core-behavior`) devem vir primeiro no escopo correspondente.
- **Preservação de Referência:** O modelo de `ContextSummary` possui o campo `audit_reference`. Este UUID deve ser exatamente o mesmo ID do evento de auditoria gerado durante a montagem do resumo de contexto. Desta forma, a rastreabilidade (FR16) é 100% mantida.

### Project Structure Notes

- A classe do caso de uso deve residir exatamente em: `src/universal_memory/application/memory/assemble_context_summary_use_case.py`.
- O repositório concreto deve residir exatamente em: `src/universal_memory/infrastructure/storage/local_context_summary_repository.py`.
- Nomes de classes e métodos devem seguir exatamente a nomenclatura em inglês estabelecida nas portas e entidades do domínio.

### References

- [PRD: FR16, FR17](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/prd.md#L336-L337)
- [Architecture Storage Contract](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#L734)
- [Context Summary Entity](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/entities/context_summary.py)
- [Context Summary Port](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/src/universal_memory/domain/ports/context_summary_repository.py)

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- 2026-05-27T19:18:08Z: Task 1 red-green-refactor concluida. Teste focado inicial falhou por ausencia de `LocalContextSummaryRepository`; apos implementacao, `uv run pytest tests/infrastructure/storage/test_local_context_summary_repository.py` passou com 9 testes.
- 2026-05-27T19:18:08Z: Regressao completa apos Task 1: `uv run pytest` passou com 164 testes.
- 2026-05-27T19:21:27Z: Task 2 red-green-refactor concluida. Teste focado inicial falhou por ausencia dos DTOs/caso de uso; apos implementacao, `uv run pytest tests/application/memory/test_assemble_context_summary_use_case.py` passou com 5 testes.
- 2026-05-27T19:21:27Z: Regressao completa apos Task 2: `uv run pytest` passou com 169 testes.
- 2026-05-27T19:22:07Z: Task 3 validada com `uv run pytest tests/application/memory/test_assemble_context_summary_use_case.py` (5 passed) e regressao completa `uv run pytest` (169 passed).
- 2026-05-27T19:23:38Z: Task 4 validada com `uv run pytest` (169 passed), `uv run ruff check .` (passed) e `uv run pyright` (0 errors).

### Completion Notes List

- Implementado `LocalContextSummaryRepository` com persistencia JSONL em `.umem/memory/context_summaries.jsonl`, lock local, escrita atomica, leitura tolerante a linhas corrompidas e bloqueio de escrita quando o arquivo esta corrompido.
- Exportado o repositorio em `src/universal_memory/infrastructure/storage/__init__.py` e adicionada suite de testes de unidade/integracao com isolamento em `tmp_path`.
- Implementado `AssembleContextSummaryUseCase` com DTOs, montagem Markdown, priorizacao por escopo/tags/recorrencia/recencia, poda por `max_size_chars`, filtro via `SecretScannerPort`, persistencia de `ContextSummary` e evento de auditoria com IDs de fatos incluidos.
- Suite do caso de uso cobre limite estrito, poda de fatos de menor prioridade, bloqueio de segredos, evidencia de auditoria, origem do resumo e falha de persistencia/base corrompida.
- Validacao estatica e regressao completa executadas com sucesso para a historia.

### File List

- `_bmad-output/implementation-artifacts/3-4-montar-resumo-de-contexto-com-limites-de-tokens.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/infrastructure/storage/__init__.py`
- `src/universal_memory/infrastructure/storage/local_context_summary_repository.py`
- `src/universal_memory/application/memory/__init__.py`
- `src/universal_memory/application/memory/assemble_context_summary_use_case.py`
- `tests/application/memory/test_assemble_context_summary_use_case.py`
- `tests/infrastructure/storage/test_local_context_summary_repository.py`

### Change Log

- 2026-05-27T19:24:25Z: Implementada montagem de resumo de contexto com persistencia local, auditoria, poda por limite, filtro de segredos e testes completos.
