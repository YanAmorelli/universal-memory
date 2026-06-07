# Safety And Recovery

Universal Memory is designed to let agents make useful persistent changes
without silently corrupting local context or leaking secrets.

## Safe Mutation Pipeline

Automatic mutations should follow this sequence:

1. validate input;
2. scan for secrets;
3. resolve scope and target path;
4. create a snapshot;
5. abort if snapshot creation fails;
6. write atomically;
7. record an audit event;
8. return an audit reference.

Adapters should not bypass this pipeline.

## Secret Scanning

Facts and skill updates are scanned before persistence. Known secret patterns
and high-entropy strings are blocked before they are written.

## Snapshots

List snapshots:

```bash
umem snapshots list --scope project
```

Snapshots are created before automatic writes to memory, skills, rules, or
instruction targets.

## Audit Events

Inspect audit history:

```bash
umem audit list --scope project
```

Audit events are append-only JSONL records with action, scope, origin, result,
and timestamps.

## Rollback

Rollback the latest automatic change for a scope:

```bash
umem rollback --scope project
```

Use `--yes` only when automation should skip confirmation.
