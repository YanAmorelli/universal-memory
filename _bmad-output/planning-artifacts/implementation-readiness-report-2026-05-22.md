---
stepsCompleted:
  - step-01-document-discovery
  - step-02-prd-analysis
  - step-03-epic-coverage-validation
  - step-04-ux-alignment
  - step-05-epic-quality-review
  - step-06-final-assessment
includedFiles:
  prd: _bmad-output/planning-artifacts/prd.md
  prdValidationReport: _bmad-output/planning-artifacts/prd-validation-report.md
  architecture: _bmad-output/planning-artifacts/architecture.md
  epics: _bmad-output/planning-artifacts/epics.md
  ux: null
---

# Implementation Readiness Assessment Report

**Date:** 2026-05-22
**Project:** universal-memory

## Document Inventory

### PRD Files

Whole documents:
- `_bmad-output/planning-artifacts/prd.md` (32365 bytes, modified May 19 19:50:49 2026)
- `_bmad-output/planning-artifacts/prd-validation-report.md` (14201 bytes, modified May 19 19:51:36 2026) - auxiliary validation report

Sharded documents:
- None found

Selected for assessment:
- `_bmad-output/planning-artifacts/prd.md`
- `_bmad-output/planning-artifacts/prd-validation-report.md` as auxiliary context

### Architecture Files

Whole documents:
- `_bmad-output/planning-artifacts/architecture.md` (40499 bytes, modified May 22 15:44:29 2026)

Sharded documents:
- None found

Selected for assessment:
- `_bmad-output/planning-artifacts/architecture.md`

### Epics & Stories Files

Whole documents:
- `_bmad-output/planning-artifacts/epics.md` (52646 bytes, modified May 22 16:59:12 2026)

Sharded documents:
- None found

Selected for assessment:
- `_bmad-output/planning-artifacts/epics.md`

### UX Design Files

Whole documents:
- None found

Sharded documents:
- None found

Selected for assessment:
- None

### Discovery Issues

- No duplicate whole-vs-sharded document formats found.
- Warning: UX design document not found. This may affect assessment completeness if the product has meaningful UI/UX scope.

## PRD Analysis

### Functional Requirements

FR1: O sistema deve persistir fatos e preferências do usuário em armazenamento local legível por humanos e compatível com metadados estruturados.

FR2: O sistema deve diferenciar logicamente entre Memória de Curto Prazo (específica por repositório) e Memória de Longo Prazo (global).

FR3: O sistema deve recuperar contexto por modos de busca locais definidos pela arquitetura, com seleção do modo padrão baseada em benchmark de latência, qualidade de resultado, custo operacional e funcionamento offline.

FR4: O usuário deve poder visualizar e editar manualmente os arquivos de persistência diretamente no sistema de arquivos.

FR5: O sistema deve permitir a purga (deleção) seletiva de fatos específicos ou de bases de memória completas.

FR6: O sistema deve executar rotinas de "Context Hygiene" para arquivar ou remover fatos de curto prazo obsoletos após a conclusão de tarefas.

FR7: Durante a configuração inicial, o sistema deve permitir que o usuário selecione os provedores de agentes suportados (ex: Claude, Gemini, ChatGPT).

FR8: O sistema deve configurar automaticamente os arquivos de instrução dos agentes selecionados (ex: `CLAUDE.md`, `AGENTS.md`) para inicializar o uso da memória universal imediatamente após a instalação.

FR9: O usuário deve poder inicializar o `universal-memory` em um novo projeto/diretório via comando CLI (ex: `umem init`).

FR10: O usuário deve poder consultar o status da memória (tamanho, regras ativas, skills disponíveis) via CLI.

FR11: Toda capacidade exposta pela API/MCP deve ter um comando CLI equivalente para uso manual.

FR12: O sistema deve expor suas capacidades através de um servidor MCP nativo rodando sobre JSON-RPC.

FR13: O sistema deve permitir que agentes externos (ex: Claude Desktop) leiam o contexto atualizado da memória.

FR14: O sistema deve permitir que agentes externos gravem novos fatos e proponham regras na memória via comandos MCP.

FR15: O sistema deve atualizar dinamicamente as instruções contidas nos arquivos dos agentes (`AGENTS.md`, `CLAUDE.md`) conforme novas regras e fatos são consolidados na memória.

FR16: O sistema deve disponibilizar o resumo da Memória de Curto Prazo no contexto inicial dos agentes e expor, via status ou auditoria, evidência de última leitura, origem do resumo e falhas de injeção quando ocorrerem.

FR17: O sistema deve garantir que a injeção de contexto respeite limites de tamanho (sumarização) para não causar overflow de tokens no LLM.

FR18: O sistema deve rastrear e contabilizar "Latent Skills" (instruções/metodologias recorrentes do usuário).

FR19: O sistema deve solicitar aprovação explícita (Sim/Sempre/Não) ao atingir o gatilho de recorrência para criar uma nova Skill.

FR20: O sistema deve gerar a estrutura de pastas e o arquivo `SKILL.md` seguindo o padrão `agentskills.io`.

FR21: O usuário deve poder listar, ativar, editar e desativar Skills registradas através da CLI.

FR22: O sistema deve escanear passivamente todos os dados recebidos para interceptar chaves de API, credenciais ou variáveis de ambiente sensíveis antes da gravação.

FR23: O sistema deve impedir a persistência de segredos detectados, notificando o usuário sobre a tentativa.

FR24: O sistema deve manter um log de auditoria local de todas as alterações feitas automaticamente nas configurações dos agentes e na criação de novas skills.

FR25: O sistema deve criar snapshot local antes de qualquer alteração automática em memórias, regras, skills ou arquivos de instrução.

FR26: O sistema deve bloquear a alteração automática quando o snapshot prévio falhar.

FR27: O usuário deve poder listar snapshots disponíveis e identificar timestamp, escopo, origem e ação responsável por cada snapshot.

FR28: O usuário deve poder reverter a última alteração automática por escopo via CLI.

Total FRs: 28

### Non-Functional Requirements

NFR1: Consultas locais de contexto devem responder em menos de 150ms no percentil 95 em uma base de teste com pelo menos 1.000 fatos, medido por benchmark automatizado em máquina de desenvolvimento.

NFR2: Leitura de memória e montagem do contexto inicial não devem adicionar mais de 200ms no percentil 95 ao início de uma sessão de agente configurado, medido por teste de integração local.

NFR3: Antes da arquitetura final, busca textual local e busca semântica devem ser comparadas em pelo menos 30 consultas representativas, medindo latência, qualidade de resultado em escala 1-5 definida no protocolo de benchmark, custo operacional e funcionamento offline; a estratégia padrão deve ser justificada pelos resultados.

NFR4: O sistema deve bloquear 100% dos padrões de segredo cobertos pela suíte de testes de segurança antes da persistência, medido por testes automatizados com exemplos positivos e negativos.

NFR5: Logs de alteração e alertas de interceptação de segredos devem ser consultáveis via CLI em menos de 2 comandos a partir do diretório do projeto, validado por teste de aceitação.

NFR6: Antes de qualquer alteração automática em arquivos de instrução ou bases de fatos, o sistema deve criar um snapshot local recuperável e manter pelo menos as 5 versões mais recentes por escopo, validado por teste de rollback.

NFR7: O usuário deve conseguir reverter a última alteração automática em menos de 1 minuto usando CLI, medido por teste de aceitação em arquivos de instrução e base de fatos.

NFR8: O servidor deve passar em 100% da suíte de conformidade definida pela arquitetura para o Model Context Protocol, incluindo pelo menos health check, recuperação de contexto, gravação/proposta de fato, proposta de regra e tratamento de erros JSON-RPC.

NFR9: A lógica de persistência deve isolar operações de leitura, escrita, listagem e versionamento atrás de um contrato interno testável; a troca de backend de armazenamento não deve exigir mudanças no motor de regras, MCP ou CLI, validado por testes de contrato.

NFR10: O MVP deve validar leitura de contexto em pelo menos 2 hosts/agentes suportados, medido por teste manual documentado ou teste de integração quando o host permitir automação.

NFR11: CLI, motor de persistência e servidor MCP devem executar leitura, gravação, consulta, auditoria e rollback com rede desabilitada, validado por teste automatizado ou checklist manual reproduzível.

NFR12: O MVP deve suportar Python 3.12+ como runtime local, instalação via PyPI, execução isolada via `uvx`, operação offline para capacidades essenciais, e armazenamento local legível por humanos.

Total NFRs: 12

### Additional Requirements

- Product scope MVP: Core Memory Engine, Auto-Adaptation Motor, On-Demand Skill Creation, Universal Interface, Backup & Rollback Guardrails.
- Post-MVP exclusions: sincronização multi-máquina automática, importação/exportação completa, interfaces web hospedadas, compartilhamento entre usuários/times e otimização autônoma fora de fluxos explicitamente aprovados.
- Data model constraint: separação rígida entre Short Term Memory por projeto/pasta e Universal Memory global.
- Host interoperability: suporte mínimo a dois hosts/agentes diferentes com mesma base de memória e comportamento consistente.
- MCP/API operations: recuperação de contexto, captura/proposta de fatos, proposta de regras, proposta de skills e health check.
- CLI command surface: init, remember, context, rules propose, host setup, status/diagnostics, audit review, snapshot listing e rollback.
- Safety constraints: confirmação humana para promoção de fatos a regras quando aplicável; bloqueio de segredos; snapshots obrigatórios antes de mutação; falha de snapshot bloqueia alteração.
- Skill engine constraint: adoção do padrão Agent Skills com `SKILL.md`, `scripts/` e `references/`, incluindo rastreamento de latent skills e aprovação explícita.

### PRD Completeness Assessment

O PRD está substancialmente completo para alimentar validação de implementação: contém visão, escopo, jornadas, MVP, exclusões, FRs numerados, NFRs mensuráveis e requisitos técnicos de CLI/MCP/persistência/segurança/rollback. Pontos que exigem atenção na validação cruzada: ausência de artefato UX separado, necessidade de rastrear cobertura de todos os 28 FRs nas epics/stories, e verificar se os NFRs mensuráveis aparecem como critérios testáveis nas histórias.

## Epic Coverage Validation

### Epic FR Coverage Extracted

FR1: Covered in Epic 1 and Story 1.2/1.4/3.1.

FR2: Covered in Epic 1 and Story 1.2/1.4/3.1.

FR3: Covered in Epic 3 and Story 3.2/3.3.

FR4: Covered in Epic 1 and Story 1.4.

FR5: Covered in Epic 3 and Story 3.6.

FR6: Covered in Epic 3 and Story 3.6.

FR7: Covered in Epic 5 and Story 5.1/5.4/5.6.

FR8: Covered in Epic 5 and Story 5.1/5.2/5.3/5.4/5.6.

FR9: Covered in Epic 1 and Story 1.1/1.4/1.5.

FR10: Covered in Epic 3 and Story 3.5.

FR11: Covered in Epic 4 and Story 4.1/4.3.

FR12: Covered in Epic 4 and Story 4.2/4.3/4.4/4.5.

FR13: Covered in Epic 4 and Story 4.2/4.3/4.5.

FR14: Covered in Epic 4 and Story 4.3/4.4/4.5.

FR15: Covered in Epic 5 and Story 5.1/5.2/5.3/5.5.

FR16: Covered in Epic 3 and Story 3.2/3.4/3.5.

FR17: Covered in Epic 3 and Story 3.4.

FR18: Covered in Epic 6 and Story 6.1/6.6.

FR19: Covered in Epic 6 and Story 6.2/6.6.

FR20: Covered in Epic 6 and Story 6.3/6.6.

FR21: Covered in Epic 6 and Story 6.4/6.5/6.6.

FR22: Covered in Epic 2 and Story 2.1/2.3.

FR23: Covered in Epic 2 and Story 2.1/2.3.

FR24: Covered in Epic 2 and Story 2.3/2.4.

FR25: Covered in Epic 2 and Story 2.2/2.3.

FR26: Covered in Epic 2 and Story 2.2/2.3.

FR27: Covered in Epic 2 and Story 2.4.

FR28: Covered in Epic 2 and Story 2.5.

Total FRs in epics: 28

### Coverage Matrix

| FR Number | PRD Requirement | Epic Coverage | Status |
| --------- | --------------- | ------------- | ------ |
| FR1 | Persistir fatos e preferências em armazenamento local legível por humanos e com metadados estruturados. | Epic 1, Stories 1.2/1.4; Epic 3, Story 3.1 | Covered |
| FR2 | Diferenciar STM por repositório e LTM global. | Epic 1, Stories 1.2/1.4; Epic 3, Story 3.1 | Covered |
| FR3 | Recuperar contexto por modos de busca locais com seleção baseada em benchmark. | Epic 3, Stories 3.2/3.3 | Covered |
| FR4 | Permitir visualização e edição manual dos arquivos de persistência. | Epic 1, Story 1.4 | Covered |
| FR5 | Permitir purga seletiva de fatos ou bases. | Epic 3, Story 3.6 | Covered |
| FR6 | Executar context hygiene para arquivar/remover fatos obsoletos. | Epic 3, Story 3.6 | Covered |
| FR7 | Permitir seleção de provedores/agentes suportados na configuração inicial. | Epic 5, Stories 5.1/5.4/5.6 | Covered |
| FR8 | Configurar automaticamente arquivos de instrução dos agentes selecionados. | Epic 5, Stories 5.1/5.2/5.3/5.4/5.6 | Covered |
| FR9 | Inicializar projeto via CLI. | Epic 1, Stories 1.1/1.4/1.5 | Covered |
| FR10 | Consultar status da memória via CLI. | Epic 3, Story 3.5 | Covered |
| FR11 | Toda capacidade MCP/API deve ter comando CLI equivalente. | Epic 4, Stories 4.1/4.3 | Covered |
| FR12 | Expor capacidades por servidor MCP JSON-RPC. | Epic 4, Stories 4.2/4.3/4.4/4.5 | Covered |
| FR13 | Permitir leitura de contexto por agentes externos. | Epic 4, Stories 4.2/4.3/4.5 | Covered |
| FR14 | Permitir escrita de fatos e proposta de regras via MCP. | Epic 4, Stories 4.3/4.4/4.5 | Covered |
| FR15 | Atualizar dinamicamente instruções dos agentes conforme regras/fatos consolidados. | Epic 5, Stories 5.1/5.2/5.3/5.5 | Covered |
| FR16 | Disponibilizar resumo STM e evidência de leitura/falhas. | Epic 3, Stories 3.2/3.4/3.5 | Covered |
| FR17 | Respeitar limites de contexto via sumarização. | Epic 3, Story 3.4 | Covered |
| FR18 | Rastrear e contabilizar latent skills. | Epic 6, Stories 6.1/6.6 | Covered |
| FR19 | Solicitar aprovação Sim/Sempre/Não para criar skill. | Epic 6, Stories 6.2/6.6 | Covered |
| FR20 | Gerar estrutura Agent Skills com `SKILL.md`. | Epic 6, Stories 6.3/6.6 | Covered |
| FR21 | Listar, ativar, editar e desativar skills via CLI. | Epic 6, Stories 6.4/6.5/6.6 | Covered |
| FR22 | Escanear dados para interceptar segredos antes da gravação. | Epic 2, Stories 2.1/2.3 | Covered |
| FR23 | Impedir persistência de segredos detectados e notificar usuário. | Epic 2, Stories 2.1/2.3 | Covered |
| FR24 | Manter log de auditoria local de alterações automáticas. | Epic 2, Stories 2.3/2.4 | Covered |
| FR25 | Criar snapshot antes de alteração automática. | Epic 2, Stories 2.2/2.3 | Covered |
| FR26 | Bloquear alteração automática se snapshot falhar. | Epic 2, Stories 2.2/2.3 | Covered |
| FR27 | Listar snapshots com timestamp, escopo, origem e ação. | Epic 2, Story 2.4 | Covered |
| FR28 | Reverter última alteração automática por escopo via CLI. | Epic 2, Story 2.5 | Covered |

### Missing Requirements

No missing FR coverage found. All 28 PRD FRs have declared epic coverage and at least one corresponding story path.

### Coverage Statistics

- Total PRD FRs: 28
- FRs covered in epics: 28
- Coverage percentage: 100%
- FRs in epics but not in PRD: none found

## UX Alignment Assessment

### UX Document Status

Not Found.

Searches performed:
- `_bmad-output/planning-artifacts/*ux*.md`
- `_bmad-output/planning-artifacts/*ux*/index.md`
- UI/UX-related terms across PRD, Architecture, and Epics

The epics document explicitly records: "Nenhum documento de UX Design foi encontrado em `_bmad-output/planning-artifacts`. Não há UX-DRs extraídos nesta etapa."

### UX/UI Implied Assessment

UX is implied, but not as a web/mobile or visual product surface for the MVP. The MVP is a developer tool / AI middleware with CLI, MCP, local files, host setup, audit/snapshot inspection, confirmation flows, and human-readable terminal output.

Relevant implied UX surfaces:
- CLI command flow: `init`, `context`, `remember`, status, audit list, snapshots list, rollback, host setup/check, skill proposal/list.
- Terminal output: Rich human output, JSON structured output, clear errors.
- Confirmation flows: rule promotion, skill creation, host instruction mutation, purge/rollback.
- File-level UX: human-readable JSON/Markdown/TOML persistence and safe manual inspection/editing.

### Alignment Issues

- No dedicated UX artifact exists for CLI interaction design, command taxonomy, prompt wording, confirmation flows, or error-message standards.
- This is not a blocker for implementation readiness because the architecture and epics already specify CLI/MCP adapters, Rich output, JSON output, error mapping, and parity checks.
- The missing UX artifact does leave a quality risk for user-facing CLI polish and onboarding consistency unless early stories treat CLI messages and confirmation prompts as acceptance-testable outputs.

### Warnings

- Warning: No UX document found. Since the MVP is primarily CLI/MCP and local developer workflow, not visual UI, this should be treated as a moderate documentation gap rather than a release blocker.
- Recommendation: Include concrete CLI output expectations, confirmation wording, and structured-output examples in relevant implementation stories, especially Stories 1.5, 2.4, 2.5, 3.5, 4.1, 5.6, 6.2, and 6.4.

## Epic Quality Review

### Critical Violations

No critical violations found.

Rationale:
- No uncovered FRs.
- No forward dependency requiring Epic N+1 for Epic N to be meaningful.
- No story appears epic-sized or impossible to complete as a standalone implementation task.
- Acceptance criteria are consistently expressed in BDD-style Given/When/Then blocks.

### Major Issues

#### MQ1: Epic 1 Contains Technical-Milestone Stories

Affected areas:
- Epic 1: "Fundação Local, Modelos e Contratos"
- Story 1.2: "Definir Modelos de Domínio para Memória"
- Story 1.3: "Definir Exceções e Ports de Domínio"

Issue:
Epic 1 has a user-facing outcome at the epic level, but Stories 1.2 and 1.3 read primarily as implementation substrate rather than independently valuable user stories. They are valid engineering work, but they violate the best-practice preference that stories deliver visible user or operator value.

Impact:
Implementation can proceed, but sprint planning should avoid treating these as isolated "done" product slices unless their value is framed as enabling validated persistence contracts and preventing adapter drift.

Recommendation:
Reframe Story 1.2 around "agents and adapters can exchange validated memory records safely" and Story 1.3 around "CLI/MCP implementers can rely on stable domain errors and storage contracts." Keep the technical ACs, but make the user/operator value explicit.

#### MQ2: CI/CD Pipeline Is Present in Architecture but Missing from Epics

Evidence:
- `architecture.md` references GitHub Actions for lint, type check, and tests.
- `epics.md` Story 1.1 requires local `ruff`, `pyright`, and `pytest`, but no story or AC establishes CI execution.

Issue:
Greenfield readiness guidance expects development environment and CI/CD setup early. The local tooling is covered; CI/CD is not traceably planned.

Impact:
This is not a product FR gap, but it is an implementation-readiness gap because automated quality gates may be delayed or omitted.

Recommendation:
Add an AC to Story 1.1 or a small Story 1.6 requiring GitHub Actions to run `ruff`, `pyright`, and `pytest` on push/PR. Prefer adding to Story 1.1 if the repo is still in initial scaffold phase.

### Minor Concerns

#### MC1: "When Available" Dependency Wording Can Blur Sequencing

Affected examples:
- Story 3.1 says memory writes respect the secure mutation pipeline "quando ele estiver disponível."
- Epic 3 notes it can integrate Epic 2 "assim que ele estiver disponível."

Issue:
This wording is acceptable for parallel planning, but it can weaken story readiness if Story 3.1 is selected before the mutation pipeline contract is implemented or stubbed.

Recommendation:
In sprint planning, split Story 3.1 into a read/list/write slice that uses the current storage contract and a follow-up integration task if Epic 2 is not complete. If Epic 2 is complete first, no change is needed.

#### MC2: CLI UX Expectations Are Testable but Not Concrete Enough in Early Stories

Affected examples:
- Story 1.5: "retorna uma mensagem humana indicando os caminhos criados"
- Story 2.4: "saída humana é legível"
- Story 3.5: "saída humana é clara"

Issue:
The ACs are testable at a high level but leave exact output shape to implementation. This is manageable, but it may produce inconsistent CLI UX across stories.

Recommendation:
During story creation, include expected output fields and JSON keys for each CLI command. Human wording can remain flexible, but structured output should be explicit.

### Best Practices Compliance Checklist

| Area | Assessment |
| ---- | ---------- |
| Epic delivers user value | Mostly compliant; Epic 1 needs stronger user-value framing for technical stories |
| Epic independence | Compliant; no forward epic dependency found |
| Story sizing | Compliant; stories are implementable slices |
| No forward dependencies | Mostly compliant; minor wording risk in Epic 3 |
| Database/entity timing | Not applicable as database tables are not used; file/model creation is incremental |
| Clear acceptance criteria | Mostly compliant; BDD structure is consistent |
| Traceability to FRs | Compliant; all stories list FR coverage |
| Starter template requirement | Compliant; architecture selects `uv init --package`, covered by Story 1.1 |
| Greenfield setup | Partially compliant; local tooling covered, CI/CD missing |

### Overall Epic Quality Assessment

The epic plan is implementation-ready with minor-to-major documentation fixes. The strongest qualities are complete FR traceability, consistent BDD acceptance criteria, no clear forward dependency breakage, and a coherent ordering from foundation to safety, memory, interfaces, hosts, and skills. The main weakness is that early foundation work is still phrased as technical construction rather than user/operator value, and CI/CD is not represented despite being an architecture decision.

## Summary and Recommendations

### Overall Readiness Status

READY

The planning artifacts are ready to move into implementation, with non-blocking remediation recommended before or during sprint planning. There are no critical blockers: PRD, architecture, and epics exist; no duplicate document formats were found; all 28 PRD FRs are covered by epics/stories; and story acceptance criteria are consistently testable.

### Critical Issues Requiring Immediate Action

None.

### Issues Requiring Attention

1. Missing UX document for CLI/user interaction details.
   - Severity: Warning / moderate documentation gap.
   - Action: Capture CLI output shape, confirmation prompts, and structured JSON examples in story files as they are created.

2. Technical-story framing in Epic 1.
   - Severity: Major planning quality issue, not a blocker.
   - Action: Reframe Stories 1.2 and 1.3 around operator/developer outcomes while preserving the technical ACs.

3. CI/CD gap.
   - Severity: Major implementation readiness issue.
   - Action: Add CI setup to Story 1.1 or create a small Story 1.6 for GitHub Actions running `ruff`, `pyright`, and `pytest`.

4. Ambiguous "when available" dependency wording around the secure mutation pipeline.
   - Severity: Minor sequencing risk.
   - Action: During sprint planning, ensure Epic 3 stories either run after Epic 2 contracts exist or explicitly use temporary storage-contract stubs.

5. CLI UX acceptance criteria are sometimes broad.
   - Severity: Minor consistency risk.
   - Action: Add expected output fields and JSON keys when creating implementation-ready story files.

### Recommended Next Steps

1. Patch `epics.md` before sprint planning to add CI/CD coverage and improve the value framing of Stories 1.2 and 1.3.

2. Proceed to Sprint Planning (`bmad-sprint-planning`) after the small planning patch, or proceed immediately if you accept the documented risks.

3. When creating the first implementation story, include exact verification commands and expected local checks: `ruff`, `pyright`, `pytest`, and CI if added.

4. Treat missing UX documentation as a CLI design checklist, not a separate full UX workflow, unless the product scope changes to include visual/web UI.

### Final Note

This assessment identified 5 issues across 3 categories: UX/documentation, epic/story quality, and implementation operations. None are critical blockers. The artifacts support implementation, but addressing the CI/CD and story-framing fixes before sprint planning will reduce downstream churn.

**Assessor:** Codex via BMad Implementation Readiness workflow
**Completed:** 2026-05-22

## Post-Assessment Corrections

**Date:** 2026-05-22

Three non-blocking findings were corrected in `_bmad-output/planning-artifacts/epics.md` after the initial assessment:

1. CI/CD gap resolved.
   - Story 1.1 now requires `.github/workflows/ci.yml` to run `ruff`, `pyright`, and `pytest` on push or pull request.

2. Secure mutation pipeline sequencing clarified.
   - Story 3.1 now requires writes to pass through the Epic 2 mutation pipeline before persistence.
   - If Story 3.1 is implemented before the full pipeline, it must use a contract-compatible mutation pipeline port/stub and replace it before the story is marked complete.

3. CLI/JSON output expectations made concrete.
   - Story 1.5 now specifies JSON keys for `umem init`.
   - Story 2.4 now specifies JSON shapes for audit and snapshot listing.
   - Story 3.5 now specifies JSON keys for memory status.
   - Story 6.4 now specifies JSON shapes for skill listing and detail views.

Remaining known issues:
- UX remains intentionally handled as CLI interaction design inside stories, not as a separate visual UX artifact.
- Story 1.2 and Story 1.3 still retain technical framing unless separately refactored.
