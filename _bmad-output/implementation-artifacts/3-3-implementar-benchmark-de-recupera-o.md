# Story 3.3: Implementar Benchmark de Recuperação

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um mantenedor do universal-memory,  
eu quero comparar busca textual local com um candidato semântico local ou stub,  
para que a estratégia padrão de recuperação seja justificada por dados de latência, qualidade e simplicidade.

## Acceptance Criteria

1. **Dado** o script `benchmarks/retrieval.py`,  
   **Quando** o benchmark é executado,  
   **Então** ele cria ou usa uma base de pelo menos 1.000 fatos de teste,  
   **E** roda pelo menos 30 consultas representativas derivadas das jornadas e requisitos do PRD.

2. **Dado** duas estratégias comparáveis (busca textual local e candidato semântico local/stub),  
   **Quando** o benchmark finaliza,  
   **Então** ele registra p95 de latência, score de qualidade 1-5, compatibilidade offline e complexidade operacional,  
   **E** salva o resultado em `.umem/benchmarks/retrieval-results.json`.

3. **Dado** os resultados do benchmark,  
   **Quando** a estratégia padrão é selecionada,  
   **Então** a justificativa é registrada junto aos resultados,  
   **E** a escolha não contradiz os limites de 150ms p95 para consulta local.

## Tasks / Subtasks

- [x] **Task 1: Modelar Dados e Preparar Massa de Teste (1.000 fatos)** (AC: 1)
  - [x] Projetar a estrutura de DTO para representar os dados e parâmetros de execução no benchmark.
  - [x] Implementar um gerador sintético dinâmico em `benchmarks/retrieval.py` que crie pelo menos 1.000 instâncias de `Fact` representativas.
  - [x] Incluir variabilidade de escopo (`global` e `project`), tags e conteúdos textuais diversos (incluindo acentuação, variações de caixa e termos comuns do domínio de desenvolvimento de software).
  - [x] Garantir que a geração seja idempotente ou que escreva em um arquivo temporário isolado para não afetar os dados reais de produção.

- [x] **Task 2: Estruturar as 30 Consultas Representativas** (AC: 1)
  - [x] Mapear e escrever pelo menos 30 queries baseadas nas histórias de usuário do PRD (ex: consultas sobre segredos, regras locais, escopo global, termos específicos de arquitetura, etc.).
  - [x] Adicionar para cada query um gabarito ou expectativa de relevância (quais fatos devem ser recuperados) para cálculo do score de qualidade.

- [x] **Task 3: Implementar a Estratégia de Busca Textual Local** (AC: 2, 3)
  - [x] Carregar a base de 1.000 fatos em uma instância de teste de `LocalFactRepository` ou simular o algoritmo de normalização e busca substring/regex offline idêntico.
  - [x] Executar as 30 queries sequencialmente usando a busca textual.
  - [x] Medir com precisão (`time.perf_counter()`) a latência de cada consulta, calculando a média e o percentil 95 (p95).

- [x] **Task 4: Implementar o Candidato/Stub Semântico Local** (AC: 2, 3)
  - [x] Projetar um stub de recuperação semântica local (ou uma busca de cosseno simulada/Mapeamento heurístico leve) para fins de comparação.
  - [x] Documentar no código as premissas operacionais da busca semântica real (carregamento de embeddings local, overhead do modelo, pegada de memória, etc.).
  - [x] Cronometrar as execuções de busca para simular/medir latência e coletar dados comparativos de performance.

- [x] **Task 5: Calcular Métricas de Comparação e Gerar Justificativa** (AC: 2, 3)
  - [x] Avaliar a qualidade das duas estratégias em uma escala de 1 a 5, baseando-se na precisão e revocabilidade dos fatos ideais.
  - [x] Definir a compatibilidade offline (100% offline para busca textual nativa vs limitações/requisitos de stubs semânticos).
  - [x] Quantificar a complexidade operacional (ex: 1 para busca textual nativa sem dependências adicionais, 4 para semântico local que exige PyTorch/SentenceTransformers e downloads de modelos de 500MB+).
  - [x] Selecionar a estratégia padrão com base nas restrições de latência (p95 < 150ms) e simplicidade, escrevendo uma justificativa técnica formal.

- [x] **Task 6: Salvar Relatório de Resultados e Criar Testes de Validação** (AC: 2, 3)
  - [x] Garantir que o script crie e salve os resultados em `.umem/benchmarks/retrieval-results.json` no formato JSON esperado.
  - [x] Escrever testes de contrato ou integração em `tests/infrastructure/test_retrieval_benchmark.py` (ou sob o diretório adequado) para validar a execução do benchmark e o formato da saída JSON.
  - [x] Assegurar 100% de isolamento de rede e ausência de efeitos colaterais na memória persistida real.

- [x] **Task 7: Executar Validação Estática e Qualidade Geral**
  - [x] Rodar a suíte inteira via `uv run pytest` garantindo que todos os testes passem.
  - [x] Validar a aderência aos padrões de formatação e linting usando `uv run ruff check .`.
  - [x] Validar tipagem estrita com `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Viés artificial no cálculo do Score de Qualidade no Benchmark — A estratégia `local_text` retorna os 10 itens mais recentes (ordenação por `created_at` descendente), excluindo o fato ideal esperado (que é o mais antigo). Já a estratégia `semantic_stub` ordena por `id` crescente como desempate, o que mantém o fato ideal no topo e infla artificialmente o seu score. Precisamos decidir como equilibrar essa comparação.
- [x] [Review][Patch] Vazamento de variável no loop do caso de uso de busca [src/universal_memory/application/memory/search_facts_use_case.py:67]
- [x] [Review][Patch] Normalização inadequada de query regex corrompendo padrões [src/universal_memory/infrastructure/storage/local_fact_repository.py:152]
- [x] [Review][Patch] Falta de tratamento de OSError ao gravar relatório do benchmark [benchmarks/retrieval.py:326]
- [x] [Review][Patch] Ausência de suporte a buscas regex no mock de busca textual do benchmark [benchmarks/retrieval.py:159]
- [x] [Review][Patch] Risco de IndexError no cálculo de percentil p95 com lista vazia [benchmarks/retrieval.py:183]
- [x] [Review][Patch] Risco de StatisticsError no cálculo do score de qualidade com lista vazia [benchmarks/retrieval.py:189]
- [x] [Review][Patch] Risco de TypeError na normalização de texto do benchmark com conteúdo nulo [benchmarks/retrieval.py:64]
- [x] [Review][Defer] Duplicação da constante MIN_REGEX_QUERY_LENGTH [vários arquivos] — deferred, pre-existing
- [x] [Review][Defer] Duplicação de lógica de normalização de texto [vários arquivos] — deferred, pre-existing
- [x] [Review][Defer] Silenciamento de exceções re.error no repositório de fatos [src/universal_memory/infrastructure/storage/local_fact_repository.py:165] — deferred, pre-existing
- [x] [Review][Defer] Vulnerabilidade potencial a ReDoS em buscas regex [src/universal_memory/infrastructure/storage/local_fact_repository.py] — deferred, pre-existing

## Dev Notes

- **Localização dos Resultados:** O arquivo de resultados final deve ser salvo exatamente em `.umem/benchmarks/retrieval-results.json`. Crie a pasta `benchmarks` dentro do diretório de dados local se ela não existir.
- **Estratégia Padrão Selecionada:** Como a busca textual nativa opera em memória local lendo JSONL de forma extremamente eficiente (< 5ms), a justificativa deve documentar que ela satisfaz com folga o limite de 150ms p95, dispensando dependências complexas (SentenceTransformers, PyTorch) que violariam o princípio de "boring technology" e simplicidade de instalação do CLI.
- **Métricas de Qualidade (1-5):**
  - 5: Excelente (traz todos os resultados esperados com ruído zero).
  - 3: Aceitável (traz os resultados esperados, mas com correspondências parciais ou algum ruído).
  - 1: Ruim (erros de correspondência ou perda de fatos cruciais).

### Project Structure Notes

- O arquivo `benchmarks/retrieval.py` deve ser um script executável que pode ser chamado diretamente via linha de comando (ex: `python benchmarks/retrieval.py` ou através de `uv run`).
- Certifique-se de que qualquer importação de submódulos (`universal_memory.*`) utilize imports absolutos baseados na raiz do pacote.

### References

- `_bmad-output/planning-artifacts/prd.md` (FR3, Latência de Recuperação, Benchmark de Recuperação)
- `_bmad-output/planning-artifacts/architecture.md` (Retrieval Benchmark Protocol, Performance, Structure Mapping)
- `src/universal_memory/domain/ports/fact_repository.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`

## Dev Agent Record

### Agent Model Used

Gemini 3.5 Flash (High)

### Debug Log References

- `uv run pytest tests/infrastructure/test_retrieval_benchmark.py` - RED inicial falhou por ausência do módulo `benchmarks.retrieval`; GREEN passou após implementação.
- `uv run python benchmarks/retrieval.py` - gerou `.umem/benchmarks/retrieval-results.json` com 1.000 fatos e 30 queries.
- `uv run pytest` - 155 passed.
- `uv run ruff check .` - passed.
- `uv run pyright` - 0 errors, 0 warnings.

### Completion Notes List

- Implementado `benchmarks/retrieval.py` com DTOs de consulta, métricas e configuração de estratégia.
- Gerador sintético cria 1.000 fatos `Fact` em memória, com escopos `global`/`project`, tags, acentuação, variações de caixa e termos do domínio.
- Adicionadas 30 queries representativas com IDs esperados para cálculo de qualidade.
- Implementadas estratégias `local_text` e `semantic_stub`, com medição via `time.perf_counter()`, média, p95, score 1-5, compatibilidade offline e complexidade operacional.
- Resultado salvo em `.umem/benchmarks/retrieval-results.json`; a estratégia padrão registrada é `local_text`, justificada por p95 abaixo de 150ms e menor complexidade.
- Adicionados testes de contrato do benchmark e ajustes pequenos de lint na busca textual existente para permitir `ruff check .` global.

### File List

- `.umem/benchmarks/retrieval-results.json`
- `_bmad-output/implementation-artifacts/3-3-implementar-benchmark-de-recupera-o.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `benchmarks/retrieval.py`
- `src/universal_memory/application/memory/search_facts_use_case.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `tests/application/memory/test_memory_use_cases.py`
- `tests/infrastructure/storage/test_local_fact_repository.py`
- `tests/infrastructure/test_retrieval_benchmark.py`

### Change Log

- 2026-05-27: Implementado benchmark de recuperação local com relatório JSON, testes de contrato e validações completas.
