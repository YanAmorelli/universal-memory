---
title: 'BUG-003: Mensagem vazia de skills acionavel'
type: 'bugfix'
created: '2026-05-29'
status: 'done'
route: 'one-shot'
---

# BUG-003: Mensagem vazia de skills acionavel

## Intent

**Problem:** `umem skills list` sem skills registradas sugeria `umem skills propose <latent_skill_id>`, mas um usuario em onboarding limpo ainda nao tem um `latent_skill_id` para informar.

**Approach:** Trocar a recomendacao padrao por uma orientacao que explica como latent skills surgem e indica um proximo comando executavel (`umem remember "..."`) sem exigir ID inexistente.

## Suggested Review Order

- [Mensagem padrao](../../src/universal_memory/application/skills/list_skills.py) -- confirmar que o estado vazio nao sugere `skills propose` diretamente e nao promete ID que a listagem nao exibe.
- [Teste de use case](../../tests/application/skills/test_list_skills.py) -- verificar contrato de payload para lista vazia.
- [Teste de CLI](../../tests/interfaces/cli/test_skills_list.py) -- verificar output humano com proximo passo acionavel e regressao contra `umem skills propose` no estado vazio.
- [Bug log](alpha-bug-log.md) -- conferir status, correcao e comando de verificacao registrado para BUG-003.
