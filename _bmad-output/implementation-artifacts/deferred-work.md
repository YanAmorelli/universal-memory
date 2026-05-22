# Deferred Work

This file tracks work deferred from development sprint reviews.

## Deferred from: code review (2026-05-22) (1-1-inicializar-scaffold-python-do-produto.md)

- **Tratar BrokenPipeError na execução CLI** (`src/universal_memory/__main__.py`): Tratar possível BrokenPipeError quando a saída padrão (stdout) for fechada ou redirecionada no ponto de entrada executável do pacote Python.
- **Matriz de testes para múltiplas versões de Python no CI** (`.github/workflows/ci.yml`): Adicionar testes automatizados sobre uma matriz de versões de suporte ativo (ex: Python 3.12 e 3.13) em vez de focar exclusivamente no Python 3.12.
- **Adicionar cobertura de testes com pytest-cov no CI** (`.github/workflows/ci.yml`): Integrar relatórios e métricas de cobertura de código no processo de CI para rejeitar commits com baixa cobertura ou sem testes apropriados.
