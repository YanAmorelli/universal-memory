# Acceptance Auditor Review Prompt

Você é o Acceptance Auditor. Revise o diff abaixo em relação à especificação e critérios de aceitação da história. Procure por: violações dos critérios de aceitação, desvios da intenção da especificação, falta de implementação de comportamentos especificados ou contradições entre as restrições da especificação e o código real. Produza apenas findings acionáveis em Markdown.

Para cada finding:
- Título de uma linha
- Qual Critério de Aceitação (AC) ou restrição é violado
- Evidência no diff

## Especificação da História: 2.1: Implementar Scanner de Segredos

### Critérios de Aceitação (Acceptance Criteria)

1. **Dado** testes de segurança com exemplos positivos e negativos de segredos, **Quando** o scanner recebe conteúdo com padrões conhecidos de credenciais, **Então** ele identifica o segredo e retorna um erro tipado `SecretDetectedError`, **E** a operação de persistência não é executada.
2. **Dado** conteúdo com strings longas suspeitas sem padrão explícito, **Quando** o scanner calcula heurística de entropia, **Então** ele bloqueia valores que ultrapassam o limite configurado para segredo genérico, **E** registra metadados suficientes para auditoria sem expor o valor sensível.
3. **Dado** conteúdo legítimo sem segredo, **Quando** o scanner é executado, **Então** ele aprova a continuação do pipeline, **E** não produz falsos positivos para exemplos comuns cobertos pela suíte de testes.

### Requisitos Técnicos & Arquitetura

- Python `>=3.12`; operação totalmente offline.
- Não adicionar dependências externas para secret scanning no MVP. Usar apenas biblioteca padrão para regex e entropia Shannon (`math.log2`).
- `SecretDetectedError` deve ser o erro tipado único para conteúdo bloqueado.
- O scanner deve ser determinístico e testável, com limiares configuráveis por construtor para facilitar testes.
- Não vazar segredo em exceções, logs, fixtures de saída ou metadados de auditoria.
- A heurística de entropia não substitui regex explícita.
- Regra de dependência obrigatória: `interfaces -> application -> domain <- infrastructure`.
  - `SecretScannerPort` deve viver em `src/universal_memory/domain/ports/`.
  - A implementação concreta deve viver em `src/universal_memory/infrastructure/security/`.
  - `domain` não pode conhecer regex, entropia ou detalhes de infraestrutura.
- Testes devem provar que o valor sensível não aparece em `str(error)`, `error.message` ou metadados públicos.

## Diff

Use o mesmo diff do arquivo `review-prompt-blind-hunter-2-1.md`.
