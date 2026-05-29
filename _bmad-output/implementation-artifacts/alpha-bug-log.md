# Alpha Bug Log

## Objetivo

Este arquivo centraliza os bugs encontrados durante a fase de alpha testing do `universal-memory`.

Uso combinado sugerido:

- registrar novos bugs aqui assim que forem observados;
- investigar bugs ambíguos com `bmad-investigate`;
- corrigir bugs pequenos com `bmad-quick-dev`;
- corrigir bugs ligados a story/sprint com `bmad-dev-story` ou fluxo normal de story.

## Status

- `open`: bug confirmado e ainda nao corrigido
- `investigating`: bug em analise
- `blocked`: depende de decisao ou contexto externo
- `fixed`: correcao aplicada
- `verified`: correcao validada manualmente ou por teste relevante
- `deferred`: bug conhecido, mas adiado

## Severidade

- `high`: bloqueia onboarding, quebra fluxo principal ou compromete confianca basica
- `medium`: nao bloqueia tudo, mas causa falha relevante, UX ruim ou comportamento inconsistente
- `low`: aresta menor, cosmetica ou melhoria de ergonomia

## Template

```md
## BUG-XXX - Titulo curto

- Status: verified
- Severidade: medium
- Superficie: CLI | MCP | Packaging | Docs | Global State | Host Setup
- Encontrado em: 2026-05-29
- Contexto: onde e como apareceu

### Reproducao

1. passo 1
2. passo 2
3. passo 3

### Esperado

- comportamento esperado

### Obtido

- comportamento observado

### Evidencias

- caminhos de arquivo
- output relevante
- auditoria relevante

### Hipotese / Causa Raiz

- preencher quando houver

### Correcao

- preencher quando corrigido

### Verificacao

- testes executados
- validacao manual
```

## Bugs

## BUG-001 - `CLAUDE.md` gerado nao satisfaz o proprio validador de claude_code

- Status: verified
- Severidade: high
- Superficie: Host Setup
- Encontrado em: 2026-05-29
- Contexto: durante smoke test manual em projeto limpo, `umem init` configurou `claude_code`, mas o `umem status` retornou falha para esse host.

### Reproducao

1. criar uma pasta vazia
2. rodar `umem init`
3. aceitar configuracao de `claude_code`
4. rodar `umem status`

### Esperado

- `claude_code` configurado com status `success`
- `CLAUDE.md` gerado em conformidade com a validacao do host

### Obtido

- `claude_code` aparece com status `failure`
- a validacao acusa ausencia de referencia a `universal-memory`, `MCP/FastMCP` ou comandos como `umem context/status`

### Evidencias

- projeto de teste: `/Users/amorelliaoyan/projects/smart-studio/app`
- arquivo: `/Users/amorelliaoyan/projects/smart-studio/app/CLAUDE.md`
- auditoria: `4bba24fd-48e4-4dfd-812f-6e60136e1f70`
- auditoria apos reinstalacao limpa: `996761b9-5258-478c-a979-667fcea58476`
- evento: `host_validation.claude_code`
- metodo: `claude_md_delta_validator`

### Hipotese / Causa Raiz

- o renderer de `CLAUDE.md` gera um bloco minimo sem referencia MCP quando nao ha deltas especificos
- o validador exige essa referencia sempre
- ha inconsistencia entre geracao e validacao

### Correcao

- `CLAUDE.md` gerado para `claude_code` agora inclui uma referencia operacional fixa a `universal-memory`, `umem context`, `umem status` e MCP/FastMCP no bloco UMEM gerenciado.
- Adicionado teste de regressao cobrindo setup de `claude_code` sem deltas seguido de `check=True` com sucesso.

### Verificacao

- `uv run pytest tests/application/test_setup_host.py` -> 15 passed
- smoke em sandbox temporaria: `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem init --hosts claude_code --yes --format json` -> `validation_status: success`
- smoke em sandbox temporaria: `uv --project /Users/amorelliaoyan/projects/personal/lab/universal-memory run umem status --format json` -> `host_validation.claude_code.status: success`
- `uv run pytest` -> 386 passed

## BUG-003 - Mensagem de `umem skills list` sem skills sugere comando pouco acionavel

- Status: verified
- Severidade: low
- Superficie: CLI
- Encontrado em: 2026-05-29
- Contexto: durante smoke test em projeto limpo, `umem skills list` retornou estado vazio com uma sugestao que exige um `latent_skill_id` que o usuario ainda nao tem.

### Reproducao

1. criar projeto limpo
2. rodar `umem init`
3. rodar `umem skills list`

### Esperado

- mensagem orientar um proximo passo executavel por um usuario sem skills registradas
- exemplo: explicar como latent skills surgem ou sugerir um fluxo anterior que gere/proponha uma candidata

### Obtido

- `Nenhuma skill registrada.`
- `Execute `umem skills propose <latent_skill_id>` para revisar uma skill candidata.`

### Evidencias

- projeto de teste: `/Users/amorelliaoyan/projects/smart-studio/app`
- comando: `umem skills list`

### Hipotese / Causa Raiz

- a mensagem assume que ja existe uma latent skill candidata conhecida, mas no onboarding limpo nao existe ID disponivel para o usuario

### Correcao

- A recomendacao padrao do estado vazio de `umem skills list` agora explica que latent skills aparecem quando o `universal-memory` registra padroes recorrentes.
- A mensagem sugere um proximo passo executavel sem exigir ID inexistente: continuar registrando memoria com `umem remember "..."` e rodar `umem skills list` novamente para acompanhar as skills quando uma candidata aparecer.
- Testes de application e CLI foram atualizados para proteger contra a reintroducao da sugestao direta de `umem skills propose <latent_skill_id>` no estado vazio.

### Verificacao

- `uv run pytest tests/application/skills/test_list_skills.py tests/interfaces/cli/test_skills_list.py` -> 10 passed

## BUG-002 - Estrategia de armazenamento global usa caminhos diferentes por tipo de dado

- Status: open
- Severidade: medium
- Superficie: Global State
- Encontrado em: 2026-05-29
- Contexto: ao inspecionar o estado global no macOS, ficou evidente que config, facts/rules e latent skills usam raizes globais diferentes.

### Reproducao

1. inspecionar o codigo dos repositórios locais e do loader de config
2. comparar os caminhos globais usados por config, facts, rules e skills

### Esperado

- estrategia global consistente e previsivel para todos os tipos de armazenamento

### Obtido

- config global em `~/.config/universal-memory/config.toml`
- facts e rules globais em `~/.umem/`
- latent skills globais em `~/.local/share/universal-memory/`

### Evidencias

- `src/universal_memory/infrastructure/config/toml_loader.py`
- `src/universal_memory/infrastructure/storage/local_fact_repository.py`
- `src/universal_memory/infrastructure/storage/local_rule_repository.py`
- `src/universal_memory/infrastructure/storage/local_latent_skill_repository.py`

### Hipotese / Causa Raiz

- a evolucao incremental do projeto deixou convencoes globais diferentes entre subsistemas

### Correcao

- pendente

### Verificacao

- pendente
