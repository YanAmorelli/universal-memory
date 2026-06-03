# Por que usar universal-memory como MCP + Skills

## Resumo

O `universal-memory` deve combinar duas superfícies complementares:

- **MCP:** a API operacional com autoridade para ler memória, propor mudanças, aplicar guardrails, criar snapshots, auditar eventos e atualizar arquivos de instrução.
- **Skills:** a camada procedural que ensina cada agente quando e como usar o MCP corretamente.

Essa combinação evita que agentes editem arquivos críticos de forma inconsistente, mas ainda permite que eles evoluam o ambiente de trabalho de maneira autônoma, rastreável e reversível.

## Problema

Agentes de IA já conseguem ler e escrever arquivos como `AGENTS.md`, `CLAUDE.md`, `GEMINI.md` e regras específicas de IDEs. Isso é poderoso, mas perigoso quando usado como mecanismo primário de memória e evolução de comportamento.

Sem uma camada de controle, cada agente pode:

- reescrever o mesmo `AGENTS.md` de formas diferentes;
- duplicar conteúdo entre arquivos de providers;
- transformar um manifesto curto em um documento gigante;
- perder contexto sobre o que é regra compartilhada, delta de provider ou documentação canônica;
- alterar instruções sem snapshot, rollback ou auditoria;
- persistir segredos por acidente;
- criar drift entre Codex, Claude Code, Gemini, Cursor, Copilot e outros hosts.

O resultado seria o oposto da proposta do `universal-memory`: em vez de uma memória portátil e coerente, teríamos arquivos locais divergentes e difíceis de confiar.

## Decisão

O fluxo normal deve ser:

```text
Agent
  lê AGENTS.md / CLAUDE.md / GEMINI.md
  aprende o protocolo via Skill
  chama MCP para ler, propor ou gravar memória
  MCP aplica guardrails, snapshot, auditoria e ownership
  MCP atualiza instruction targets quando aprovado
```

Regra central:

```text
Agentes não editam arquivos de instrução diretamente como fluxo normal.
Agentes propõem mudanças via MCP.
MCP decide o target, cria snapshot, escreve atomicamente e audita.
```

## Papel do MCP

O MCP é a superfície de autoridade do sistema.

Ele deve ser responsável por:

- recuperar contexto aplicável ao projeto e ao usuário;
- gravar fatos de memória com validação;
- propor regras a partir de recorrência;
- registrar oportunidades de Skills;
- classificar alterações como `shared_policy`, `provider_delta`, `scoped_rule` ou `canonical_doc`;
- manter ownership de instruction targets como `AGENTS.md`;
- criar snapshots antes de qualquer mutação;
- bloquear escrita quando detectar segredos;
- auditar todas as alterações;
- permitir rollback por escopo;
- expor paridade de capacidades para CLI e hosts MCP.

O MCP é onde ficam as garantias de consistência. Se um agente chama o MCP, o sistema consegue impor as regras arquiteturais independentemente do provider.

## Papel das Skills

Skills não substituem o MCP. Elas ensinam o agente a operar o sistema.

Uma Skill deve explicar:

- quando consultar memória;
- quando propor uma nova regra;
- quando registrar uma skill latente;
- como distinguir fato efêmero, preferência recorrente e regra permanente;
- que arquivos de instrução não devem ser editados diretamente;
- qual ferramenta MCP chamar em cada situação;
- quais sinais exigem confirmação humana;
- como manter `AGENTS.md` curto e apontar para docs especializados.

Skills são portáteis entre hosts porque descrevem comportamento. O MCP é portátil porque expõe capacidades padronizadas.

## Papel dos arquivos de instrução

Arquivos como `AGENTS.md`, `CLAUDE.md` e `GEMINI.md` devem fazer bootstrap do comportamento, não armazenar todo o conhecimento.

O `AGENTS.md` deve ser um manifesto curto e compartilhado:

- regras operacionais estáveis;
- ponteiros para documentação canônica;
- instrução para usar o MCP de memória;
- referência à Skill que define o protocolo de uso.

Provider-specific files devem conter apenas deltas:

- comportamento que aquele provider exige;
- sintaxe ou escopo próprio do host;
- regras que não cabem no manifesto compartilhado.

Rules específicas por provider devem ser usadas para ativação, escopo e granularidade, não para duplicar todo o conteúdo do `AGENTS.md`.

## Por que não usar apenas MCP

MCP sozinho expõe ferramentas, mas não garante que o agente saiba quando usá-las.

Sem Skills, cada host pode interpretar o MCP de forma diferente:

- um agente pode chamar `remember_fact` para algo que deveria ser apenas contexto efêmero;
- outro pode propor regras permanentes cedo demais;
- outro pode ignorar o fluxo de confirmação;
- outro pode editar arquivos diretamente por hábito.

Skills reduzem essa ambiguidade. Elas são o manual operacional que transforma ferramentas em comportamento consistente.

## Por que não usar apenas Skills

Skills sozinhas não conseguem impor guardrails.

Uma Skill pode instruir o agente a criar snapshot, auditar e evitar segredos, mas isso depende da obediência do agente. Para mudanças críticas, precisamos de uma camada que aplique as regras de verdade.

Sem MCP, não há autoridade central para:

- garantir single-writer em `AGENTS.md`;
- bloquear persistência de segredos;
- criar snapshot antes de escrita;
- registrar auditoria consistente;
- executar rollback;
- manter paridade entre CLI e MCP;
- classificar corretamente o destino de uma alteração.

Skills orientam. MCP executa com controle.

## Exemplo de fluxo

1. O agente inicia uma sessão e lê `AGENTS.md`.
2. `AGENTS.md` instrui o agente a usar o `universal-memory` MCP e aponta para a Skill operacional.
3. A Skill orienta: antes de começar uma tarefa, chame `get_context`.
4. O agente chama `get_context` via MCP.
5. Durante a sessão, o usuário repete uma preferência pela terceira vez.
6. A Skill orienta o agente a chamar `propose_rule`, não editar `AGENTS.md`.
7. O MCP classifica a mudança como `shared_policy`.
8. O MCP pede confirmação humana quando necessário.
9. Após aprovação, o MCP cria snapshot, atualiza `AGENTS.md` uma única vez e registra auditoria.
10. Outros hosts que suportam `AGENTS.md` passam a consumir a mesma regra sem duplicação.

## Benefícios

- **Coerência entre hosts:** diferentes agentes usam a mesma memória e seguem o mesmo protocolo.
- **Menos repetição:** regras compartilhadas vivem em um manifesto curto, não em cópias por provider.
- **Segurança:** segredos são bloqueados antes da persistência.
- **Reversibilidade:** toda mutação relevante tem snapshot e rollback.
- **Auditoria:** mudanças de comportamento têm histórico consultável.
- **Portabilidade:** Skills explicam o comportamento; MCP padroniza a capacidade.
- **Controle humano:** preferências recorrentes podem virar regras, mas passam por confirmação quando necessário.

## Princípio final

O `universal-memory` não deve confiar que cada agente editará corretamente os arquivos de instrução.

Ele deve dar aos agentes um caminho melhor:

```text
Skills ensinam o comportamento.
MCP aplica as garantias.
Instruction files fazem bootstrap e apontam para a fonte certa.
```

