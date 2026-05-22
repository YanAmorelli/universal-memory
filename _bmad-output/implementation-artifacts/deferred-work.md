# Deferred Work

## Deferred from: code review (2026-05-22) (of 1-3-definir-exce-es-e-ports-de-dom-nio.md)

- **Dados Estruturados Específicos em Exceções de Domínio** (`src/universal_memory/domain/exceptions.py`): As exceções customizadas de domínio carecem de dados estruturados específicos da falha (como o ID da entidade que falhou) e passam essas informações como strings simples. Isso deve ser melhorado futuramente à medida que os use cases específicos demandarem análises de log e tratamento estruturado.
