# Story 2.1: Implementar Scanner de Segredos

Status: done

## Story

Como um usuário que grava fatos, regras e instruções,  
eu quero que o sistema detecte segredos antes de persistir qualquer dado,  
para que credenciais e variáveis sensíveis não sejam salvas acidentalmente na memória.

## Acceptance Criteria

1. **Dado** testes de segurança com exemplos positivos e negativos de segredos, **Quando** o scanner recebe conteúdo com padrões conhecidos de credenciais, **Então** ele identifica o segredo e retorna um erro tipado `SecretDetectedError`, **E** a operação de persistência não é executada.
2. **Dado** conteúdo com strings longas suspeitas sem padrão explícito, **Quando** o scanner calcula heurística de entropia, **Então** ele bloqueia valores que ultrapassam o limite configurado para segredo genérico, **E** registra metadados suficientes para auditoria sem expor o valor sensível.
3. **Dado** conteúdo legítimo sem segredo, **Quando** o scanner é executado, **Então** ele aprova a continuação do pipeline, **E** não produz falsos positivos para exemplos comuns cobertos pela suíte de testes.

## Tasks / Subtasks

- [x] **Task 1: Escrever testes RED do contrato de scanner** (AC: 1, 2, 3)
  - [x] Criar ou atualizar `tests/domain/test_ports.py` para incluir `SecretScannerPort` como ABC abstrata exportada por `universal_memory.domain.ports`.
  - [x] Definir assinatura tipada mínima do port, por exemplo `scan(content: str, *, origin: str | None = None) -> None`.
  - [x] Garantir que o contrato levanta `SecretDetectedError` para conteúdo bloqueado e retorna `None` para conteúdo aprovado.

- [x] **Task 2: Escrever testes RED da implementação de infraestrutura** (AC: 1, 2, 3)
  - [x] Criar `tests/infrastructure/security/test_entropy_secret_scanner.py`.
  - [x] Cobrir padrões conhecidos: AWS access key, GitHub PAT moderno, token bearer/API key genérico, atribuições `.env` sensíveis (`API_KEY=...`, `SECRET=...`, `TOKEN=...`, `PASSWORD=...`).
  - [x] Cobrir heurística de entropia para tokens longos sem prefixo explícito.
  - [x] Cobrir negativos comuns: UUID v4, caminhos relativos, hashes curtos de commit, texto natural, identificadores de configuração não secretos e exemplos placeholders (`your_api_key_here`, `not-a-secret`).
  - [x] Verificar que mensagens de erro e metadados nunca incluem o valor sensível bruto.

- [x] **Task 3: Implementar `SecretScannerPort` no domínio** (AC: 1)
  - [x] Adicionar `src/universal_memory/domain/ports/secret_scanner_port.py`.
  - [x] Exportar `SecretScannerPort` em `src/universal_memory/domain/ports/__init__.py`.
  - [x] Manter `domain` sem import de `application`, `infrastructure` ou `interfaces`.
  - [x] Reutilizar `SecretDetectedError` já existente em `src/universal_memory/domain/exceptions.py`; não criar erro paralelo.

- [x] **Task 4: Implementar scanner offline sem dependências externas** (AC: 1, 2, 3)
  - [x] Criar `src/universal_memory/infrastructure/security/__init__.py`.
  - [x] Criar `src/universal_memory/infrastructure/security/entropy_secret_scanner.py`.
  - [x] Implementar regex compiladas para padrões conhecidos e nomes de variáveis sensíveis.
  - [x] Implementar cálculo de entropia Shannon com biblioteca padrão (`math`, `collections`) e limiar configurável por construtor.
  - [x] Fazer a classe implementar `SecretScannerPort`.
  - [x] Retornar aprovação silenciosa (`None`) para conteúdo seguro.

- [x] **Task 5: Garantir metadados seguros para auditoria futura** (AC: 2)
  - [x] Incluir no erro apenas informações seguras: tipo de detecção, nome do padrão, posição/faixa aproximada ou contagem, `origin` opcional e dica de recuperação.
  - [x] Não incluir substring detectada, token mascarado reversível, linha completa contendo segredo ou valor original.
  - [x] Se `SecretDetectedError` precisar carregar metadados, evoluir a classe preservando compatibilidade com `tests/domain/test_exceptions.py` e `error.message`.

- [x] **Task 6: Verificação de qualidade e regressão** (AC: 1, 2, 3)
  - [x] Executar `uv run pytest tests/domain/test_ports.py tests/infrastructure/security/test_entropy_secret_scanner.py`.
  - [x] Executar `uv run pytest`.
  - [x] Executar `uv run ruff check .`.
  - [x] Executar `uv run pyright`.

### Review Findings

- [x] [Review][Decision] Risco de Falsos Positivos de Alta Entropia com Payloads Base64 (imagens/binários) — Resolvido: Mantido o comportamento estrito padrão para o MVP por segurança (evitando falsos negativos de segredos em base64).
- [x] [Review][Patch] Risco de Exposição Indireta de Segredos via campo `span` nos Metadados de Erro [src/universal_memory/infrastructure/security/entropy_secret_scanner.py:L74] (Aplicado: adicionado alerta de segurança em docstrings/comentários de SecretDetectedError e SecretScannerPort.scan)

## Dev Notes

- **Escopo desta story:** criar o scanner e seu contrato interno. Não implementar ainda snapshot, escrita atômica, auditoria completa, CLI/MCP ou pipeline de mutação inteiro; isso pertence às histórias 2.2, 2.3 e 2.4.
- **Objetivo de segurança:** bloquear persistência de conteúdo sensível antes de qualquer operação de escrita futura, atendendo FR22 e FR23.
- **Resultado esperado para integração futura:** use cases de mutação poderão receber `SecretScannerPort` via constructor injection e chamar `scan(...)` antes de snapshot/write/audit.

### Technical Requirements

- Python `>=3.12`; operação totalmente offline.
- Não adicionar dependências externas para secret scanning no MVP.
- Usar apenas biblioteca padrão para regex e entropia.
- `SecretDetectedError` deve ser o erro tipado único para conteúdo bloqueado.
- O scanner deve ser determinístico e testável, com limiares configuráveis por construtor para facilitar testes.
- Não vazar segredo em exceções, logs, fixtures de saída ou metadados de auditoria.
- Implementar padrões conhecidos e heurística genérica; a heurística não substitui regex explícita.

### Architecture Compliance

- Regra de dependência obrigatória: `interfaces -> application -> domain <- infrastructure`.
- `SecretScannerPort` deve viver em `src/universal_memory/domain/ports/`.
- A implementação concreta deve viver em `src/universal_memory/infrastructure/security/`.
- `domain` pode definir o port e o erro, mas não pode conhecer regex, entropia ou detalhes de infraestrutura.
- `application` não deve importar `infrastructure`; integração futura deve receber o port por constructor injection.
- Nenhum adapter pode escrever diretamente no storage sem o pipeline seguro futuro.

### Library / Framework Requirements

- Usar `re` para padrões conhecidos.
- Usar `math.log2` para entropia Shannon.
- Não usar pacotes externos como detect-secrets, trufflehog, gitleaks ou chamadas de rede.
- Não alterar versões de `pyproject.toml` nesta story, salvo se os testes existentes exigirem correção já acordada.
- A informação de stack vigente continua a mesma dos artefatos de planejamento: Python 3.12+, Pydantic v2, Typer/Rich, FastMCP e `tomli-w`; esta story não depende dessas libs para executar o scanner.

### File Structure Requirements

- **Arquivos UPDATE esperados:**
  - `src/universal_memory/domain/ports/__init__.py`
  - `tests/domain/test_ports.py`
- **Arquivos UPDATE possíveis, se necessário para metadados seguros:**
  - `src/universal_memory/domain/exceptions.py`
  - `tests/domain/test_exceptions.py`
- **Arquivos NEW esperados:**
  - `src/universal_memory/domain/ports/secret_scanner_port.py`
  - `src/universal_memory/infrastructure/security/__init__.py`
  - `src/universal_memory/infrastructure/security/entropy_secret_scanner.py`
  - `tests/infrastructure/security/test_entropy_secret_scanner.py`

### Testing Requirements

- Seguir TDD: testes RED antes de código de produção.
- Testes positivos devem provar bloqueio para padrões conhecidos e entropia alta.
- Testes negativos devem evitar falsos positivos em conteúdo comum do projeto.
- Testes devem provar que o valor sensível não aparece em `str(error)`, `error.message` ou metadados públicos.
- Testes devem provar que conteúdo seguro retorna `None` e não produz side effects.
- Testes de contrato devem continuar garantindo que ports são ABCs abstratas com assinaturas tipadas.

### Current Code State

- `src/universal_memory/domain/exceptions.py` já define `SecretDetectedError` como subclasse de `UniversalMemoryError`.
- `tests/domain/test_exceptions.py` já garante que erros de domínio preservam `message`; qualquer evolução deve manter essa compatibilidade.
- `src/universal_memory/domain/ports/` já contém repositories e ports de config/layout, mas ainda não contém `SecretScannerPort`.
- `tests/domain/test_ports.py` centraliza expectativas de assinatura dos ports; adicionar o scanner ali mantém o padrão estabelecido no épico 1.
- `src/universal_memory/infrastructure/` hoje só contém `config/`; a pasta `security/` será a localização arquitetural correta para o scanner.

### Previous Story Intelligence

- A Story 1.5 consolidou o padrão de adapters finos e evitou lógica de negócio em interfaces.
- A Story 1.4 endureceu layout/config e reforçou idempotência; não reimplementar filesystem/config para scanner.
- As histórias do Epic 1 estabeleceram que contratos vivem no domínio e implementações com side effects ou detalhes técnicos vivem em infraestrutura.
- O padrão de qualidade vigente é validar com `pytest`, `ruff` e `pyright` antes de mover status de implementação.

### Git Intelligence Summary

- `44dbe15 feat: implement clean cli init` moveu CLI para composição limpa e manteve inicialização como adapter sobre aplicação.
- `05f7abf feat: harden project init layout and config loading` reforçou ports e adapters de infraestrutura para layout/config.
- `facd129 feat(domain): implementar excecoes e ports de dominio...` estabeleceu o padrão de exceções tipadas e ports abstratos.
- A implementação desta story deve ser incremental: adicionar um port e uma implementação concreta sem refatorar as camadas existentes.

### Latest Technical Information

- Não há dependência externa nova a pesquisar ou versionar nesta story.
- A decisão técnica relevante é usar biblioteca padrão do Python 3.12 para manter o requisito offline-first e zero dependência externa no scanner.
- A heurística de entropia deve ser tratada como sinal auxiliar, não como detector absoluto; os testes negativos são parte obrigatória para controlar falsos positivos.

### Project Structure Notes

- Criar `infrastructure/security/` alinha o código com a árvore prevista em `_bmad-output/planning-artifacts/architecture.md`.
- Não criar `application/security/` ainda, a menos que a implementação precise de um use case interno; o escopo desta story é port + infraestrutura.
- Não tocar em `interfaces/cli/` ou `interfaces/mcp/` nesta story.
- Não usar caminhos absolutos em mensagens, specs, fixtures ou documentação.

### References

- `_bmad-output/planning-artifacts/epics.md` (Epic 2, Story 2.1, FR22, FR23, NFR4)
- `_bmad-output/planning-artifacts/architecture.md` (Security & Guardrails, Clean Architecture, Project Structure, Mutation Pipeline)
- `_bmad-output/planning-artifacts/prd.md` (Secret & ENV Guardrails, Backup & Recovery guardrails)
- `_bmad-output/planning-artifacts/devex-interaction-spec.md` (No secret exposure, actionable errors, relative project paths)
- `_bmad-output/implementation-artifacts/1-5-implementar-inicializa-o-cli-m-nima.md` (padrões recentes de adapter, qualidade e verificação)
- `src/universal_memory/domain/exceptions.py`
- `src/universal_memory/domain/ports/__init__.py`
- `tests/domain/test_ports.py`
- `tests/domain/test_exceptions.py`

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-26: história alvo resolvida a partir de “épico 2” como primeira história backlog do épico: `2-1-implementar-scanner-de-segredos`.
- 2026-05-26: analisados `sprint-status.yaml`, `epics.md`, `architecture.md`, `prd.md` e `devex-interaction-spec.md`.
- 2026-05-26: inspecionados `src/universal_memory/domain/exceptions.py`, `src/universal_memory/domain/ports/`, `tests/domain/test_ports.py`, `tests/domain/test_exceptions.py` e estrutura atual de `infrastructure/`.
- 2026-05-26: não há `project-context.md` no repositório; workflow seguiu com artefatos de planejamento e histórias anteriores.
- 2026-05-26: testes RED adicionados para contrato do `SecretScannerPort` e implementação `EntropySecretScanner`; falharam inicialmente por import ausente.
- 2026-05-26: implementados port de domínio, scanner offline com regex e entropia Shannon, e metadados seguros em `SecretDetectedError`.
- 2026-05-26: validações executadas com sucesso: `uv run pytest tests/domain/test_ports.py tests/infrastructure/security/test_entropy_secret_scanner.py`, `uv run pytest`, `uv run ruff check .`, `uv run pyright`.

### Completion Notes List

- Ultimate context engine analysis completed - comprehensive developer guide created.
- História pronta para dev com escopo delimitado para scanner interno e port de domínio.
- Guardrails incluídos para evitar vazamento de segredo em erros, metadados e testes.
- Arquivos esperados e comandos de verificação definidos.
- `SecretScannerPort` foi adicionado ao domínio com assinatura `scan(content: str, *, origin: str | None = None) -> None`.
- `EntropySecretScanner` bloqueia padrões conhecidos, atribuições sensíveis e tokens de alta entropia sem dependências externas.
- `SecretDetectedError` preserva `message` e agora pode carregar metadados seguros para auditoria futura sem expor valores sensíveis.
- Conteúdo legítimo coberto pelos negativos retorna `None`, incluindo UUID, caminhos relativos, commits curtos, texto natural e placeholders.
- Story validada e movida para `review`.

### File List

- `_bmad-output/implementation-artifacts/2-1-implementar-scanner-de-segredos.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/domain/exceptions.py`
- `src/universal_memory/domain/ports/__init__.py`
- `src/universal_memory/domain/ports/secret_scanner_port.py`
- `src/universal_memory/infrastructure/security/__init__.py`
- `src/universal_memory/infrastructure/security/entropy_secret_scanner.py`
- `tests/domain/test_ports.py`
- `tests/infrastructure/security/test_entropy_secret_scanner.py`

### Change Log

- 2026-05-26: Implementado scanner de segredos offline e contrato de domínio da Story 2.1; status movido para `review`.
