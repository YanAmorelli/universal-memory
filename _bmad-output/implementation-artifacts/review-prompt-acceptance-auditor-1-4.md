# Acceptance Auditor Review Prompt

Você é um Acceptance Auditor. Revise este diff contra a spec e o contexto disponível. Verifique:
- violações dos acceptance criteria
- desvios da intenção da story
- comportamento especificado mas não implementado
- contradições entre constraints da spec e o código

Saída: lista Markdown. Cada finding deve conter:
- título de uma linha
- AC ou constraint violado
- evidência objetiva no diff
- impacto concreto

## Spec

Arquivo: `_bmad-output/implementation-artifacts/1-4-criar-layout-local-umem-e-configura-o-toml.md`

Pontos críticos da spec:
- criar `.umem/config.toml`, `.umem/memory/`, `.umem/audit/events.jsonl`, `.umem/snapshots/`, `.umem/skills/` e `.umem/benchmarks/`
- arquivos iniciais legíveis por humanos e seguros para edição manual
- carregar configuração global e de projeto com `tomllib`
- preparar escrita com `tomli-w`
- resolver caminhos globais e locais offline
- erros conhecidos de TOML inválido devem virar `InvalidConfigError`
- quando fizer sentido para output/diagnóstico, caminhos retornados devem ser relativos
- `application/` depende apenas de `domain/`; filesystem e TOML ficam em `infrastructure/config/`
- o use case deve permanecer síncrono
- não antecipar CLI nem MCP

## Contexto adicional

- Nenhum `project-context.md` encontrado
- Nenhum `CLAUDE.md` encontrado
- Exceções atuais do domínio em `src/universal_memory/domain/exceptions.py`
- Reexports atuais do domínio em `src/universal_memory/domain/__init__.py`

## Diff

Use o mesmo diff do arquivo `review-prompt-blind-hunter-1-4.md`.
