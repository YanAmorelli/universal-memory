# Plano de Alpha Testing e Publicacao Inicial no PyPI

## Objetivo

Este documento define um plano pragmatico para levar o `universal-memory` do estado atual de desenvolvimento concluido para uma primeira fase de uso real com **alpha testers** e, depois disso, para uma publicacao inicial como pacote Python versionado, preferencialmente `0.1.0a1`.

Premissa central:

- concluir as stories funcionais nao significa automaticamente que o projeto esta pronto para PyPI publico;
- existe uma fase de **hardening** entre "feature complete" e "alpha distribuivel";
- o melhor proximo passo e validar o produto em ambientes reais, com pouca escala e muita observabilidade.

## Estado atual

As stories `6.5` e `6.6` foram concluidas. O projeto agora deve ser tratado como:

- **funcionalmente completo para o MVP**;
- **suficiente para testes reais controlados**;
- **ainda sujeito a bugs de integracao, UX e edge cases de ambiente**.

Isso e um bom ponto para:

- iniciar um programa pequeno de alpha testers;
- validar instalacao em ambiente limpo;
- validar uso real de CLI e MCP;
- coletar bugs e atritos antes de qualquer promessa de estabilidade.

Em outras palavras: o foco agora nao e mais desenvolvimento de feature principal, e sim **validacao de instalacao, onboarding, UX, packaging e robustez operacional**.

## Definicao de fases

### Fase 1: Pre-alpha interno

Objetivo:

- consolidar o estado feature complete do MVP;
- estabilizar o fluxo principal;
- corrigir regresses obvias;
- validar packaging local.

Saida esperada:

- instalacao local funcionando em `venv` limpa;
- smoke tests manuais repetiveis;
- README e docs minimos para onboarding.

Status sugerido agora:

- **em andamento imediato**.

### Fase 2: Alpha privado

Objetivo:

- disponibilizar o pacote para um grupo pequeno de testers;
- exercitar cenarios reais em maquinas e projetos diferentes;
- medir friccao de onboarding, ergonomia do CLI e robustez do MCP.

Saida esperada:

- lista priorizada de bugs;
- ajustes de DX e mensagens de erro;
- confianca minima para uma release publica inicial.

### Fase 3: Publicacao inicial no PyPI

Objetivo:

- publicar uma versao claramente rotulada como alpha;
- permitir instalacao padronizada por `pip`;
- manter escopo e expectativa controlados.

Saida esperada:

- release `0.1.0a1` ou similar;
- instrucoes claras de instalacao e feedback;
- changelog minimo e known issues.

## O que precisa existir antes do alpha

### 1. Fechamento funcional do MVP

Checklist:

- stories `6.5` e `6.6` concluidas;
- testes atualizados para CLI e MCP;
- paridade minima entre superficies mantida;
- fluxos de leitura e mutacao principais funcionando.

Leitura pratica do estado atual:

- este bloco deve ser considerado **atendido**;
- qualquer falha encontrada daqui em diante deve ser tratada como bug de hardening, nao como lacuna de escopo do MVP.

### 2. Packaging local valido

Checklist:

- `pyproject.toml` consistente para build;
- nome do projeto validado;
- scripts de entrada funcionando apos instalacao;
- build local do pacote testado;
- wheel e sdist gerados sem erro.

Comandos sugeridos:

```bash
uv build
python -m venv .venv-alpha
source .venv-alpha/bin/activate
pip install dist/*.whl
umem --help
umem-mcp --help
```

### 3. Documentacao minima para tester

Checklist:

- README com descricao realista do status do projeto;
- secao "como instalar";
- secao "como iniciar um projeto";
- secao "como reportar bug";
- aviso explicito de que a versao e alpha.

### 4. Validacao em ambiente limpo

Checklist:

- testar em um diretorio novo, sem estado previo;
- testar em um projeto ja existente;
- testar sem arquivos de host configurados;
- testar com pelo menos um host configurado;
- validar mensagens de erro quando o setup estiver incompleto.

## Checklist tecnico para release pre-alpha

Antes de distribuir para testers, executar:

- `uv run pytest`
- `uv run ruff check .`
- `uv run ruff format --check .`
- `uv run pyright`
- `uv build`

E tambem validar manualmente:

- `pip install` do wheel em `venv` limpa;
- `umem --help`;
- `umem init`;
- `umem status`;
- pelo menos um fluxo de escrita com auditoria/snapshot;
- pelo menos um fluxo de skills;
- inicializacao do MCP.

Se tudo acima passar, o projeto ja esta em condicao de entrar no primeiro ciclo de alpha privado.

## Checklist de smoke test para alpha tester

### Ambiente

- criar uma `venv` limpa;
- instalar o pacote por wheel ou TestPyPI;
- testar em macOS ou Linux primeiro;
- evitar depender de ambiente ja customizado na primeira rodada.

### Fluxo 1: Onboarding basico

Passos:

1. criar uma pasta vazia;
2. rodar `umem init`;
3. verificar criacao de `.umem/`;
4. rodar `umem status`;
5. verificar se a resposta faz sentido para projeto recem iniciado.

O que observar:

- clareza da mensagem inicial;
- caminhos criados;
- sugestoes de proximo passo;
- se algo exige conhecimento implicito demais.

### Fluxo 2: Memoria basica

Passos:

1. registrar fatos;
2. listar fatos;
3. montar contexto;
4. purgar ou arquivar conforme o fluxo disponivel.

O que observar:

- consistencia entre saida humana e JSON;
- clareza de `scope`;
- mensagens de erro;
- comportamento em dados vazios.

### Fluxo 3: Skills

Passos:

1. registrar ou propor skill;
2. listar skills;
3. inspecionar detalhes;
4. gerar ou ativar a skill conforme as stories finais implementadas.
5. desativar, reativar e atualizar uma skill por CLI.
6. repetir pelo menos uma mutacao equivalente por MCP.

O que observar:

- caminhos relativos corretos;
- metadados coerentes;
- leitura de `SKILL.md`;
- paridade entre CLI e MCP nas mutacoes de skill;
- comportamento em nomes ambiguos, colisoes e arquivos parcialmente manuais.

### Fluxo 4: Seguranca e reversibilidade

Passos:

1. executar uma mutacao que gere snapshot;
2. consultar auditoria;
3. listar snapshots;
4. testar rollback em cenario controlado.

O que observar:

- se snapshot realmente aparece;
- se auditoria e util para diagnostico;
- se rollback e compreensivel;
- se ha risco de mutacao silenciosa demais.

### Fluxo 5: MCP

Passos:

1. subir o servidor MCP;
2. conectar com um host suportado;
3. chamar ferramentas de leitura;
4. chamar pelo menos uma ferramenta de mutacao com confirmacao, se aplicavel.

O que observar:

- paridade com a CLI;
- envelopes estruturados;
- mapeamento de erros;
- comportamento em ambientes com pouca configuracao.

## Como reportar bugs durante o alpha

Cada bug deveria registrar, no minimo:

- versao instalada;
- sistema operacional;
- comando executado;
- saida obtida;
- saida esperada;
- se havia projeto inicializado ou nao;
- se o fluxo era CLI ou MCP;
- arquivos relevantes ou estado minimo para reproduzir.

Formato sugerido:

```text
Titulo: breve descricao do problema
Versao: 0.1.0a1
OS: macOS / Linux
Superficie: CLI / MCP
Comando: umem ...
Esperado: ...
Obtido: ...
Passos para reproduzir: ...
Observacoes: ...
```

## Criterios para publicar `0.1.0a1`

Eu recomendaria publicar a primeira alpha apenas quando todos os itens abaixo forem verdadeiros:

- MVP funcional concluido;
- testes automatizados principais passando;
- build do pacote funcionando localmente;
- instalacao limpa validada fora do ambiente de desenvolvimento;
- README suficiente para onboarding sem ajuda oral;
- pelo menos um ciclo de smoke test manual completo executado;
- problemas conhecidos documentados;
- expectativa de alpha explicitamente comunicada.

## O que ainda nao significa estabilidade

Mesmo com `0.1.0a1`, ainda e esperado encontrar:

- bugs de filesystem;
- diferencas entre hosts MCP;
- arestas de UX em mensagens e prompts;
- fluxos nao ideais para repositorios ja existentes;
- casos de borda em paths, encoding, YAML/frontmatter e arquivos manuais.

Por isso, a release inicial deve comunicar claramente:

- que a versao e experimental;
- que o schema/contratos ainda podem evoluir;
- que feedback de instalacao e onboarding e tao importante quanto bug funcional.

## Recomendacao pratica de execucao

Ordem sugerida:

1. rodar suite completa de validacao;
2. ajustar `README.md` para onboarding de alpha;
3. testar `uv build` e instalacao em `venv` limpa;
4. executar um smoke test manual completo em pasta nova;
5. validar um fluxo real de CLI e um fluxo real de MCP;
6. publicar primeiro no TestPyPI ou distribuir wheel localmente;
7. executar um ciclo curto de alpha privado;
8. corrigir bugs de onboarding, packaging e ambiente;
9. publicar `0.1.0a1` no PyPI.

## Proximo passo imediato

Se o objetivo e comecar agora, a sequencia mais objetiva e:

1. rodar `uv run pytest`, `uv run ruff check .`, `uv run ruff format --check .` e `uv run pyright`;
2. rodar `uv build`;
3. instalar o wheel em uma `venv` limpa;
4. executar o smoke test de onboarding basico;
5. executar um fluxo de memoria;
6. executar um fluxo de skills;
7. subir o MCP e validar pelo menos uma leitura e uma mutacao.

Ao fim desse ciclo, ja deve ser possivel abrir uma primeira lista real de bugs e decidir se o pacote esta pronto para distribuicao alpha privada.

## Minha avaliacao honesta

Sim, faz sentido ficar confiante no projeto, mas com confianca calibrada.

O que inspira confianca:

- arquitetura com separacao razoavel entre dominio, CLI e MCP;
- preocupacao com contratos de saida;
- auditoria, snapshot e rollback como fundamentos;
- cobertura de testes evoluindo junto com as stories.

O que ainda exige cautela:

- comportamento em ambientes reais fora da maquina de desenvolvimento;
- atrito de onboarding;
- empacotamento e distribuicao;
- integracao com hosts reais e seus edge cases.

Em resumo:

- **sim, eu colocaria esse projeto em alpha privada**;
- **nao, eu ainda nao trataria como estavel**;
- **sim, o proximo passo natural e preparar instalacao limpa e validacao real de uso**.
