# Architecture

Universal Memory is a Python 3.12+ developer tool and AI middleware project. It
uses a Clean Architecture layout with thin CLI and MCP adapters over shared
application use cases.

## Layers

```text
interfaces -> application -> domain <- infrastructure
```

Guidelines:

- `domain` owns entities, ports, and domain exceptions.
- `application` owns use cases and receives ports by constructor injection.
- `infrastructure` implements storage, security, and configuration ports.
- `interfaces` translates CLI and MCP input/output only.

## Persistence

The product uses human-readable local storage:

- JSON or JSONL for structured data such as facts, rules, latent skills,
  snapshots, and audit events;
- Markdown for instruction files, skills, and documentation.

Project memory uses `.umem/`. Global memory uses the configured user-level
storage root.

## Interfaces

The CLI is canonical. MCP is equivalent and delegates to the same use cases.
New public capabilities should be exposed through both surfaces unless there is
an explicit documented exclusion.

## Cross-Cutting Guarantees

- secret scanning before persistence;
- snapshots before automatic writes;
- rollback by scope;
- append-only audit events;
- local-first operation;
- parseable JSON for automation;
- host-specific instruction deltas instead of duplicated shared policy.

## Retrieval

Text search is the default MVP strategy. The architecture keeps retrieval behind
ports so future semantic search can be evaluated without changing the interface
contract.
