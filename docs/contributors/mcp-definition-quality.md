# MCP definition quality

Universal Memory exposes 38 MCP tools. Their public definitions are part of the
agent-facing API: descriptions explain tool selection and side effects, parameter
schemas explain invocation, and annotations conservatively describe every supported
mode rather than only the default preview.

## Baseline and scope

The public [Glama listing](https://glama.ai/mcp/servers/YanAmorelli/universal-memory)
was checked on 2026-11-04. It still reported server TDQS **C, 2.7/5**, scored on
2026-09-09 18:26 across 38 tools. `track_latent_skill` was **D, 1.8/5** and
`cleanup_skill` was **C, 2.0/5**. These are external baseline measurements, not
scores for this change.

The old local Glama specification covered 37 tools and 111 parameters. The current
`dev` baseline, commit `85a9982`, adds `bootstrap`, retains 111 input properties,
and has no semantic property descriptions or explicit behavior annotations.
This change documents all 38 tools and all 111 properties without changing their
names, types, defaults, validation constraints, output schemas, or use-case behavior.
The older specification is input to this work; its 37-tool release gate is obsolete.

Glama's [methodology](https://glama.ai/mcp/methodology) evaluates purpose, usage,
behavior, parameter semantics, conciseness, and completeness, plus tool-set
coherence and server cohesiveness. Local completeness checks cannot predict a new
grade. Publication and external reindexing are needed for another measurement.

## Behavioral distinctions that definitions must preserve

| Tool or mode | Actual behavior reflected in the definition |
| --- | --- |
| `migrate_project_layout` | Preview leaves source content unchanged. Applying writes shared content and removes migrated/already-shared facts from the legacy facts file; private, global, and conflicting facts stay local. |
| `update_skill` | Omitting `raw_markdown` regenerates the entire SKILL.md from metadata and can discard custom body content, including on an otherwise empty edit. Supply complete edited Markdown to retain it. |
| `share_skill` | Can overwrite existing shared destination files without conflict checking or overwrite confirmation. No preview mode; writes use the snapshot/audit pipeline. |
| `context`, `bootstrap` | Persist generated context summaries and audit events; repeating calls creates records. |
| `host_check` | Leaves the host manifest intact but records validation in the audit log. |
| `track_latent_skill` | Counts another observation on every matched invocation; retries are not idempotent. |
| `cleanup_skill` | `dry_run=true` previews; false removes managed native copies. Canonical content remains. `targets` is currently ignored, including false. No cleanup snapshot is created. |
| `repair_skills` | Removal requires both `remove_orphan_targets=true` and `dry_run=false`. |
| `deactivate_skill` | Changes latent status and may remove native directories or write disabled stubs according to runtime policy. Canonical content remains. Reactivation does not reinstall removed native copies. |
| `activate_skill` | Requires an ignored candidate and an existing valid generated skill file. |
| `create_skill_draft` | Can overwrite an existing unregistered file at the draft path. Omitted/empty triggers default to the skill name in generated Markdown, as in `create_skill`. |
| `recommend_skills` | Evidence thresholds count nonempty entries, including duplicates; distinct summary text is not required. Both values of the compatibility flag `dry_run` remain read-only. |
| `propose_skill` / `generate_skill` | Proposal review/decision and approved latent generation form one flow. |
| `promote_skill_recommendation` | Directly promotes a still-proposed candidate, then marks it active. Do not first approve it through `propose_skill`. `targets` alone does not enable native synchronization. |
| `purge_fact`, `rollback_scope` | Require explicit confirmation. Rollback chooses the latest created snapshot; retrying can select a different recovery point. |
| `initialize_project` | Can configure managed host content and invoke the official skill installer over the network. It is not advertised as a closed-world read. |

Reads may use filesystem lock files. A read-only annotation describes preservation
of user memory/configuration records, not the absence of storage synchronization
primitives. Audit-producing reads are explicitly classified as mutating. Idempotent
hints are false for mutations rather than promising retry safety based on defaults.
Destructive hints include supported overwrite/removal modes even when they are opt-in.

## Verification

`tests/interfaces/mcp/test_definition_quality.py` reads the actual MCP `tools/list`
response through a FastMCP client. It checks:

- The exact 38-tool set and all 111 described input properties.
- All four behavior annotations, including mixed preview/apply operations.
- Input and output schema compatibility against the unmodified `dev` schemas in
  `tests/interfaces/mcp/fixtures/definitions_dev_85a9982.json`, allowing only added
  description metadata. A property named `description` remains an input property.
- Real context-summary/audit persistence, tracking recurrence, and cleanup preview
  versus deletion, legacy fact pruning, and existing shared-file overwrite through
  the MCP adapters and actual application use cases. A sentinel test also verifies
  whole-file regeneration when latent update Markdown is omitted. Tests also verify
  duplicate evidence eligibility, generated trigger defaults, and unregistered draft
  file overwrite.

Run the complete CI checks from [Development](development.md), including the existing
MCP compliance, parity, skill lifecycle, safety, and native-target regression tests.
The fixture must only change with a deliberate, reviewed API change; do not regenerate
it merely to make an unexpected schema difference pass.

## Remaining opportunities

The baseline Glama report also flags overlapping skill lifecycle tools, the 38-tool
selection burden, fact editing, permanent canonical skill deletion, and selecting a
specific rollback snapshot. This metadata change clarifies existing boundaries; it
does not remove tools or implement those capabilities. Consolidation or focused server
profiles need a separate compatibility design. Do not claim an A grade until the
reviewed published commit has been evaluated by Glama.

The lossy metadata-only `update_skill` behavior and unchecked `share_skill` destination
overwrite remain existing application behaviors. The definitions now disclose them;
changing their defaults or adding conflict protection needs a separate functional change
with explicit compatibility tests.
