# Story 6.3: Gerar Skill Canônica e Instalar em Targets Nativos

Status: ready-for-dev

## Reopened Scope

Esta story foi reaberta porque a implementação anterior cobria a geração da skill canônica em `.umem/skills/`, mas não cobria instalação/sincronização para diretórios nativos de runtimes, detecção de drift manual nem prompt Keep/Overwrite exigidos pelo PRD atualizado.

## Story

Como usuário que aprovou uma nova skill,
quero que o sistema gere a skill canônica e instale-a nos diretórios de skills nativos dos runtimes selecionados,
para que a capacidade seja imediatamente utilizável pelos agentes compatíveis sem perder customizações locais.

**Requirements covered:** FR20, FR31, FR32.

## Acceptance Criteria

1. **Skill canônica preservada como fonte de verdade**

   **Dado** uma skill aprovada,
   **Quando** a geração é executada,
   **Então** o sistema cria ou atualiza a skill canônica sob `.umem/skills/` com `SKILL.md`, `scripts/` e `references/` conforme aplicável,
   **E** essa pasta permanece a fonte de verdade, não os targets nativos.

2. **Instalação em native skill targets**

   **Dado** runtimes selecionados e ativos na configuração,
   **Quando** a skill canônica é gerada ou sincronizada,
   **Então** o sistema instala, copia, renderiza ou linka a skill nos native skill targets declarados pelos adapters,
   **E** cobre pelo menos targets compatíveis para Claude Code, OpenCode e Cursor quando declarados pelo registry.

3. **Metadados e auditoria por target**

   **Dado** uma instalação nativa,
   **Quando** o target é escrito,
   **Então** o sistema registra source skill ID, runtime de destino, path relativo, hash/versão canônica, timestamp e referência de auditoria.

4. **Drift manual protegido**

   **Dado** um arquivo nativo que divergiu da versão canônica instalada,
   **Quando** `umem update --skills` ou sincronização automática roda,
   **Então** o sistema detecta o conflito antes de sobrescrever,
   **E** exibe em inglês o aviso `Warning: Native target has manual changes. Overwriting it might break your current agent workflow. Keep local version or Overwrite with canonical library version? [Keep/Overwrite]`.

5. **Snapshot antes de overwrite**

   **Dado** o usuário escolhe sobrescrever um target nativo com drift,
   **Quando** a escrita é aplicada,
   **Então** o sistema cria snapshot de backup antes de sobrescrever,
   **E** aborta sem escrita se o snapshot falhar.

6. **Desativação não deleta canônico por padrão**

   **Dado** uma skill instalada em runtimes nativos,
   **Quando** a skill é desativada,
   **Então** targets nativos são desabilitados/removidos conforme policy do adapter,
   **E** a skill canônica em `.umem/skills/` não é deletada por padrão.

## Tasks / Subtasks

- [ ] Integrar geração de skill com Runtime Registry e native skill targets.
- [ ] Implementar instalador/sincronizador de skill canônica para targets nativos por runtime.
- [ ] Registrar metadados por instalação nativa, incluindo runtime, path, hash e audit reference.
- [ ] Implementar detecção de drift manual baseada em hash/versão canônica anterior.
- [ ] Implementar prompt Keep/Overwrite em inglês e modo JSON/não-interativo seguro.
- [ ] Garantir snapshot antes de qualquer overwrite de target nativo.
- [ ] Adicionar testes para instalação em `.claude/skills/`, `.opencode/skills/` e `.cursor/rules/` conforme adapters disponíveis.
- [ ] Adicionar testes de drift, Keep, Overwrite, snapshot failure e desativação sem deletar canônico.

## Dev Notes

- A story anterior estava implementada como `6-3-gerar-estrutura-agent-skills.md`; ela continua sendo uma base útil para o canonical store, mas não satisfaz FR31-FR32.
- Esta story depende da 5.1 reaberta para native skill target metadata e da 5.6 para persistência de runtimes ativos.
- Usar o pipeline obrigatório de mutação: validar, secret scan, resolver path/scope, snapshot, atomic write, audit.
