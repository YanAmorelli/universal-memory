---
title: 'BUG-003: Actionable empty skills message'
type: 'bugfix'
created: '2026-05-29'
status: 'done'
route: 'one-shot'
---

# BUG-003: Actionable Empty Skills Message

## Intent

**Problem:** `umem skills list` without registered skills suggested `umem skills propose <latent_skill_id>`, but a user on a clean onboarding flow does not yet have a `latent_skill_id` to provide.

**Approach:** Replace the default recommendation with guidance that explains how latent skills emerge and indicates an executable next command (`umem remember "..."`) without requiring a non-existent ID.

## Suggested Review Order

- [Default message](../../src/universal_memory/application/skills/list_skills.py) -- confirm that the empty state does not suggest `skills propose` directly and does not promise an ID that the listing does not display.
- [Use case test](../../tests/application/skills/test_list_skills.py) -- verify payload contract for the empty list.
- [CLI test](../../tests/interfaces/cli/test_skills_list.py) -- verify human output with an actionable next step and regression against `umem skills propose` in the empty state.
- [Bug log](alpha-bug-log.md) -- check status, fix, and verification command registered for BUG-003.
