# Story 3.2: Consultar Contexto Local com Busca Textual

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um agente externo que precisa de contexto antes de agir,  
eu quero consultar fatos relevantes por busca local,  
para que eu consiga recuperar memória útil sem depender de rede ou serviços externos.

## Acceptance Criteria

1. **Dado** uma base local com fatos ativos,  
   **Quando** uma consulta textual é executada,  
   **Então** o sistema retorna fatos relevantes usando busca local por substring, normalização ou regex conforme definido pela arquitetura,  
   **E** os resultados incluem identificador, escopo, trecho ou motivo de correspondência e timestamp relevante.

2. **Dado** fatos arquivados, obsoletos ou purgados,  
   **Quando** a consulta padrão é executada,  
   **Então** o sistema exclui esses fatos dos resultados ativos,  
   **And** permite incluir estados não ativos somente por opção explícita de diagnóstico.

3. **Dado** o ambiente está offline,  
   **Quando** a consulta de contexto é executada,  
   **Então** ela funciona sem conectividade externa,  
   **And** não tenta acessar serviços remotos.

## Tasks / Subtasks

- [x] **Task 1: Definir Port/Interface no Domínio para a Busca Textual** (AC: 1, 2, 3)
  - [x] Analisar `src/universal_memory/domain/ports/fact_repository.py`.
  - [x] Adicionar o método abstrato `search(self, query: str, include_inactive: bool = False) -> list[Fact]` na interface `FactRepository`.
  - [x] Garantir que o design da assinatura de `search` permita filtragem offline e case-insensitive por padrão.

- [x] **Task 2: Escrever testes RED para busca no repositório de infraestrutura `LocalFactRepository`** (AC: 1, 2, 3)
  - [x] Adicionar testes em `tests/infrastructure/storage/test_local_fact_repository.py`.
  - [x] Cobrir busca textual básica (case-insensitive por substring).
  - [x] Cobrir busca que ignora acentos (normalização básica).
  - [x] Cobrir busca por regex básica (se suportado pelo mecanismo padrão).
  - [x] Testar que fatos inativos (`FactStatus.archived`, `FactStatus.stale`, `FactStatus.purged`) são filtrados e excluídos por padrão na busca.
  - [x] Testar que fatos inativos são retornados quando `include_inactive=True`.
  - [x] Testar a ordenação padrão dos resultados baseada em data de criação descendente ou relevância direta.
  - [x] Garantir total isolamento offline dos testes (sem chamadas a APIs externas).

- [x] **Task 3: Implementar o suporte a busca em `LocalFactRepository`** (AC: 1, 2, 3)
  - [x] Implementar o método `search` em `src/universal_memory/infrastructure/storage/local_fact_repository.py`.
  - [x] Adicionar lógica para normalizar textos (remover acentos ou colocar em minúsculo para busca insensível a caixa).
  - [x] Aplicar correspondência por substring simples e, se aplicável, por regex padrão em python (`re`).
  - [x] Filtrar os fatos em memória (carregados a partir do JSONL) conforme o status atual do fato e o parâmetro `include_inactive`.
  - [x] Assegurar que exceções específicas de armazenamento sejam lançadas em caso de corrupção ou erro físico de I/O.

- [x] **Task 4: Escrever testes RED para o Use Case de aplicação `SearchFactsUseCase`** (AC: 1, 2, 3)
  - [x] Criar arquivo de teste `tests/application/memory/test_search_facts_use_case.py` (ou adicionar a `tests/application/memory/test_memory_use_cases.py`).
  - [x] Cobrir `SearchFactsUseCase` recebendo `SearchFactsCommand` com atributos `query` e `include_inactive`.
  - [x] Validar que o Use Case delega os filtros corretos para o `FactRepository` e retorna `SearchFactsResult`.
  - [x] Testar o comportamento com query vazia (deve retornar lista vazia ou todos os fatos conforme regra).

- [x] **Task 5: Implementar o Use Case de aplicação `SearchFactsUseCase`** (AC: 1, 2, 3)
  - [x] Criar o arquivo `src/universal_memory/application/memory/search_facts_use_case.py`.
  - [x] Definir os DTOs `SearchFactsCommand` e `SearchFactsResult`.
  - [x] Implementar `SearchFactsUseCase` com injeção de dependência do `FactRepository`.
  - [x] Registrar e expor os novos objetos no arquivo `src/universal_memory/application/memory/__init__.py`.

- [x] **Task 6: Garantir fechamento em GREEN, linting e tipagem**
  - [x] Executar `uv run pytest` e obter 100% de sucesso.
  - [x] Executar `uv run ruff check .` para validação de linting e formatação.
  - [x] Executar `uv run pyright` para garantir tipagem estática e conformidade estrita de tipos.

## Dev Notes

- **Escopo desta story:** Foco exclusivo nas camadas de domínio, infraestrutura e aplicação para a realização de busca textual offline. Comandos finais CLI e MCP pertencerão às histórias do Épico 4.
- **Offline-First:** Não usar bibliotecas que dependam de conectividade externa. O processamento de substring e normalização deve ser 100% nativo (ex: módulo `re` ou manipulação de strings com `unicodedata`).
- **Resiliência:** Manter o tratamento resiliente de corrupção de linhas do JSONL introduzido na Story 3.1.
- **Normalização:** Utilizar `unicodedata.normalize('NFKD', texto)` para remover acentos e facilitar a correspondência exata.

### Project Structure Notes

- A alteração na interface `FactRepository` exige que quaisquer stubs de teste (como `RecordingFactRepository` em `test_memory_use_cases.py`) também implementem o método `search` para não quebrar a suíte de testes existente.
- A estrutura de pastas segue estritamente os padrões de Arquitetura Limpa estabelecidos.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR3, FR16, NFR3)
- `_bmad-output/planning-artifacts/architecture.md` (Data Architecture, Core Memory Management)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (Output Contract, Error Contract)
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/domain/entities/fact.py`
- `src/universal_memory/application/memory/list_facts_use_case.py`

## Dev Agent Record

### Agent Model Used

Codex GPT-5

### Debug Log References

- `uv run pytest tests/domain/test_ports.py -q` falhou inicialmente até `FactRepository.search` ser adicionado.
- `uv run pytest tests/infrastructure/storage/test_local_fact_repository.py -q` falhou inicialmente até `LocalFactRepository.search` ser implementado e o teste de ordenação com inativos ficar determinístico.
- `uv run pytest tests/application/memory/test_memory_use_cases.py -q` falhou inicialmente até `SearchFactsUseCase` ser criado e exportado.
- `uv run pytest` passou com 151 testes.
- `uv run ruff check .` passou.
- `uv run pyright` passou com 0 erros.

### Completion Notes List

- Adicionado `FactRepository.search(query, include_inactive=False)` como contrato abstrato para busca textual offline.
- Implementado `LocalFactRepository.search` com normalização via `unicodedata.normalize("NFKD", ...)`, busca case-insensitive, fallback por regex Python nativo, filtro de fatos ativos por padrão e ordenação descendente por `created_at`.
- Adicionado `SearchFactsUseCase`, `SearchFactsCommand` e `SearchFactsResult`, com query em branco retornando lista vazia sem chamar o repositório.
- Atualizados stubs/testes para cobrir substring, acentos, regex, filtros de inativos, inclusão diagnóstica de inativos, ordenação e delegação do use case.
- Ajustado o contrato de retorno de `FactRepository.write` para `object | None`, preservando o retorno opcional usado pelo pipeline de escrita segura e deixando `pyright` verde.

### File List

- `_bmad-output/implementation-artifacts/3-2-consultar-contexto-local-com-busca-textual.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/memory/__init__.py`
- `src/universal_memory/application/memory/remember_fact_use_case.py`
- `src/universal_memory/application/memory/search_facts_use_case.py`
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `tests/application/memory/test_memory_use_cases.py`
- `tests/domain/test_ports.py`
- `tests/infrastructure/storage/test_local_fact_repository.py`

### Change Log

- 2026-05-27: Implementada busca textual local offline para fatos, use case de aplicação, testes de domínio/aplicação/infraestrutura e validações `pytest`, `ruff` e `pyright`.

### Review Findings

- [x] [Review][Decision] Unescaped Regex Search & ReDoS Vulnerability in LocalFactRepository — The search implementation falls back to `re.search` using raw, unescaped user query. This can cause accidental regex matches (e.g. 'C+' matching 'C') and exposes a Regular Expression Denial of Service (ReDoS) vulnerability. Accent stripping before regex compilation also corrupts regex syntax.
- [x] [Review][Decision] Acceptance Criteria Violation: Lack of Match Snippet or Motive in Search Results — Acceptance Criterion 1 requires results to include 'identificador, escopo, trecho ou motivo de correspondência e timestamp relevante'. However, SearchFactsResult only returns a list of Fact entities directly, with no snippet or motive metadata.
- [x] [Review][Patch] Fragile Hardcoded Path.home() as Fallback in RememberFactUseCase [src/universal_memory/application/memory/remember_fact_use_case.py:44]
- [x] [Review][Patch] Dead Code and Fragile Unused References in RememberFactUseCase [src/universal_memory/application/memory/remember_fact_use_case.py:73]
- [x] [Review][Patch] Inconsistent Sorting Semantics Between List, Search, and Mock Repository [src/universal_memory/infrastructure/storage/local_fact_repository.py:145]
- [x] [Review][Patch] LSP Violation: Mock RecordingFactRepository.search Lacks Normalization and Regex Support [tests/application/memory/test_memory_use_cases.py:98]
- [x] [Review][Patch] Inefficient Full-Scan and Suboptimal Filtering in LocalFactRepository.search [src/universal_memory/infrastructure/storage/local_fact_repository.py:138]
- [x] [Review][Patch] Robustness Gaps: Potential AttributeErrors and TypeErrors on None/Malformed inputs in Repository Search [src/universal_memory/application/memory/search_facts_use_case.py:23]
- [x] [Review][Defer] Weak Domain Port Typing for write() and Abundant cast(Any, ...) Workarounds [src/universal_memory/domain/ports/fact_repository.py:50] — deferred, pre-existing
- [x] [Review][Defer] Clean Architecture Violation: Dynamic Runtime State and Injection on Repository Port [src/universal_memory/application/memory/remember_fact_use_case.py:40] — deferred, pre-existing
- [x] [Review][Defer] Skills para Agentes para explicar capacidades UMEM ao modelo — deferred, new requirement
