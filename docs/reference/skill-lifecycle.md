# Skill Lifecycle

Universal Memory tracks recurring procedures as latent skills, then allows the
user or agent workflow to promote them into canonical Agent Skills.

## Lifecycle

1. Track a recurring workflow.
2. List latent skills.
3. Inspect details.
4. Propose a skill decision.
5. Generate a canonical skill.
6. Activate, deactivate, or update the skill.
7. Synchronize active skills into native runtime targets.

## CLI Commands

```bash
umem skills track --name "Review Protocol" --description "Recurring review workflow"
umem skills list
umem skills detail <skill-id-or-name>
umem skills propose <latent-skill-id>
umem skills generate <latent-skill-id>
umem skills activate <latent-skill-id>
umem skills deactivate <latent-skill-id>
umem skills update <latent-skill-id> --name "Updated Skill"
umem update --skills
```

## File Shape

Generated skills use a canonical structure:

```text
.umem/skills/<skill-slug>/
  SKILL.md
  references/
  scripts/
```

`references/` and `scripts/` are optional, but useful for durable supporting
material and helper automation.

## Safety

Skill mutations should create snapshots and audit events. Native runtime sync
should warn before overwriting manually changed target files.
