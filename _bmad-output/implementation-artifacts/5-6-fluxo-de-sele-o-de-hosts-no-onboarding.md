# Story 5.6: Fluxo de Seleção de Hosts no Onboarding

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário instalando o universal-memory,
Eu quero selecionar quais hosts/agentes configurar durante a inicialização (onboarding),
Para que o setup inicial ative apenas integrações relevantes ao meu fluxo.

**Requirements covered:** FR7, FR8.

## Acceptance Criteria

1. **Dado** hosts suportados pelo MVP (`codex`, `claude_code`)
   **Quando** o onboarding/inicialização do projeto é iniciado (`umem init`)
   **Então** em modo interativo o usuário pode selecionar `codex`, `claude_code` ou ambos (default: ambos)
   **And** o sistema registra a seleção dos hosts habilitados no arquivo de configuração local `.umem/config.toml` (chave `[hosts] enabled = [...]`)
   **And** em modo não interativo (ex: flags `--hosts codex` ou `--yes`) o sistema configura os hosts conforme as opções passadas ou assume todos por padrão.

2. **Dado** qualquer confirmação ou escrita em arquivos de instrução durante o setup de hosts selecionados no onboarding
   **Quando** o processo é executado
   **Then** o sistema mostra claramente o escopo, caminhos relativos dos arquivos afetados, snapshot planejado e evento de auditoria gerado de acordo com as especificações do `_bmad-output/planning-artifacts/devex-interaction-spec.md`.

3. **Dado** um host selecionado pelo usuário durante o onboarding
   **Quando** o setup do projeto é concluído
   **Então** o sistema executa automaticamente a configuração inicial (`ConfigureHostUseCase` com `apply=True`) e validação de leitura do contexto do host (`ConfigureHostUseCase` com `check=True`)
   **And** informa claramente no console quais passos manuais adicionais permanecem necessários (se houver).

4. **Dado** um host não selecionado no onboarding (ex: `codex` selecionado, mas `claude_code` omitido)
   **Quando** o sistema roda a sincronização de regras futura (`SyncInstructionsUseCase`)
   **Então** o sistema não cria nem altera arquivos específicos daquele host omitido (como `CLAUDE.md`)
   **And** mantém a possibilidade de configurar este host posteriormente no futuro via `umem host setup <host_id>` sem necessidade de migrações manuais.

## Tasks / Subtasks

- [x] **Tarefa 1: Suporte a Persistência de Hosts Selecionados no `config.toml` (AC: 1)**
  - [x] Implementar utilitário ou método de persistência em `src/universal_memory/infrastructure/config/toml_loader.py` para atualizar e salvar alterações no `.umem/config.toml` mantendo o padrão TOML do `tomli_w`.
  - [x] Validar a adição de `[hosts]` e campo `enabled = ["codex", "claude_code"]` na entidade e schema de configuração.
  - [x] Atualizar testes em `tests/application/test_setup_project.py` para validar a inicialização do `config.toml` com hosts padrão se nenhuma opção for fornecida.

- [x] **Tarefa 2: Atualizar Caso de Uso `setup_project` e a CLI `umem init` com Opções e Modo Interativo (AC: 1, 3)**
  - [x] Adaptar a assinatura ou estender o caso de uso `setup_project` (ou criar porta especializada) para receber os hosts selecionados.
  - [x] Atualizar o comando `@app.command("init")` em `src/universal_memory/interfaces/cli/init_command.py` para suportar a flag `--hosts` (opção para passar múltiplos hosts, ex: `umem init --hosts codex --hosts claude_code` ou formato similar do Typer).
  - [x] Implementar o modo interativo na CLI durante a execução de `umem init`: se não for passada a flag `--yes` / `-y` e a saída não for JSON, perguntar individualmente ao usuário com confirmações amigáveis:
    - `"Deseja configurar o host 'codex' (suporte a AGENTS.md)? [S/n]"`
    - `"Deseja configurar o host 'claude_code' (suporte a CLAUDE.md)? [S/n]"`
  - [x] Garantir que o resultado do onboarding grave a lista de hosts selecionados na configuração sob a chave `[hosts]` -> `enabled`.

- [x] **Tarefa 3: Integração do Onboarding com a Configuração Automática de Hosts (AC: 2, 3)**
  - [x] Após materializar o layout de diretórios e gravar a configuração de hosts no `init`, se houver hosts selecionados, chamar internamente o `ConfigureHostUseCase` (com `apply=True` e depois `check=True`) para criar e validar os respectivos arquivos de instrução padrão (`AGENTS.md` e/ou `CLAUDE.md`).
  - [x] Assegurar que toda mutação física realizada em `AGENTS.md`/`CLAUDE.md` passe pelo pipeline seguro de escrita (`SafeWriteUseCase`), criando snapshots e gravando no log de auditoria local.
  - [x] Exibir no terminal os logs de progresso e resumos de forma elegante seguindo a especificação `devex-interaction-spec.md` (caminhos, escopos, snapshots criados, logs de auditoria e instruções manuais subsequentes).

- [x] **Tarefa 4: Adaptar `SyncInstructionsUseCase` para Respeitar Hosts Habilitados (AC: 4)**
  - [x] Modificar `SyncInstructionsUseCase` em `src/universal_memory/application/host/sync_instructions_use_case.py` para ler a configuração do projeto (.umem/config.toml) via `load_config`.
  - [x] Se o comando `SyncInstructionsCommand` receber a lista padrão ou vazia de `host_ids`, filtrar dinamicamente para sincronizar apenas os hosts que estão ativamente listados como habilitados/selecionados no arquivo de configuração do projeto.
  - [x] Se um host específico for requisitado explicitamente na linha de comando mas não estiver habilitado no onboarding, emitir um warning ou permitir a sincronização temporária sob demanda sem erros de bloqueio estrutural.

- [x] **Tarefa 5: Escrever Testes Abrangentes (AC: 1, 2, 3, 4)**
  - [x] Adicionar testes unitários em `tests/application/host/test_sync_instructions.py` garantindo que a sincronização seja ignorada de forma transparente para hosts desabilitados na configuração.
  - [x] Adicionar testes de integração em `tests/interfaces/cli/` (ou expandir `test_setup_project.py` / criar novo `test_onboarding.py`) simulando o fluxo de `umem init` com e sem interatividade, validando a gravação do arquivo `.umem/config.toml` e a geração automática dos arquivos de instruções dos hosts selecionados.

### Review Findings

- [x] [Review][Decision] Ausência de prompt de confirmação/visualização de impacto no onboarding — Resolvido: adotada Opção B (prompt inicial de escolha do host é a confirmação; logs de progresso finais seguem devex-spec de forma limpa).
- [x] [Review][Decision] Sincronização sob demanda permitida para hosts desabilitados (inconsistência de estado) — Resolvido: adotada Opção C (habilitar auto-ativamento transparente do host no config.toml ao sincronizar sob demanda com aviso).
- [ ] [Review][Patch] Mascaramento da recusa de seleção de todos os hosts (lista vazia) no onboarding interativo [src/universal_memory/application/onboarding/setup_project.py:27-32]
- [ ] [Review][Patch] Omissão dos dados de resultados dos hosts na saída JSON do comando umem init [src/universal_memory/interfaces/cli/init_command.py:690]
- [ ] [Review][Patch] Falha silenciosa de setup automatizado de hosts se dependências de injeção forem nulas [src/universal_memory/interfaces/cli/init_command.py:754]
- [ ] [Review][Patch] Falha com AttributeError se a chave hosts na configuração for um valor não-tabela [src/universal_memory/application/host/sync_instructions_use_case.py:358]
- [ ] [Review][Patch] Lógica frágil de comparação de hosts default em _host_ids_for_command [src/universal_memory/application/host/sync_instructions_use_case.py:343]
- [ ] [Review][Patch] Sensibilidade a maiúsculas e espaços em branco nos IDs de hosts fornecidos pelo CLI [src/universal_memory/interfaces/cli/init_command.py:737]
- [ ] [Review][Patch] Duplo I/O e escrita insegura (não atômica) em update_project_config [src/universal_memory/infrastructure/config/toml_loader.py:168]
- [ ] [Review][Patch] Uso de inspeção de assinatura em tempo de execução (signature) frágil [src/universal_memory/interfaces/cli/init_command.py:311]
- [ ] [Review][Patch] Assinatura preguiçosa Callable[..., SetupProjectResult] prejudica tipagem estática [src/universal_memory/interfaces/cli/init_command.py:214]
- [ ] [Review][Patch] Escrita no arquivo de configuração TOML antes da validação [src/universal_memory/application/onboarding/setup_project.py:30]
- [ ] [Review][Patch] Falta de captura de exceções de leitura de config em _enabled_hosts_from_config [src/universal_memory/application/host/sync_instructions_use_case.py:350]
- [ ] [Review][Patch] Falta de tratamento de interrupções de teclado nos prompts do CLI [src/universal_memory/interfaces/cli/init_command.py:656]
- [ ] [Review][Patch] Ausência de tratamento de exceções individuais no setup sequencial de hosts [src/universal_memory/interfaces/cli/init_command.py:756]
- [x] [Review][Defer] Violação de camadas da Clean Architecture (caso de uso importando infraestrutura) [src/universal_memory/application/host/sync_instructions_use_case.py:27] — deferred, pre-existing
- [x] [Review][Defer] Dependência acoplada do relógio do sistema (datetime.now(UTC)) [src/universal_memory/application/host/sync_instructions_use_case.py:63] — deferred, pre-existing
- [x] [Review][Defer] Validação de hosts suportados no caso de uso em vez de camada de validação dedicada [src/universal_memory/application/host/sync_instructions_use_case.py:360] — deferred, pre-existing
- [x] [Review][Defer] Ausência de teste e especificidade no comportamento de mesclagem de listas de _deep_merge [src/universal_memory/infrastructure/config/toml_loader.py:174] — deferred, pre-existing

## Dev Notes

- **Aproveitamento de Componentes Existentes:** Use a função `load_config` de `toml_loader.py` para ler as configurações e estenda-a ou implemente a escrita segura das chaves usando `tomli_w.dumps()`.
- **Pipeline Seguro de Mutação:** Qualquer escrita física em arquivos como `AGENTS.md` ou `CLAUDE.md` durante a inicialização deve usar estritamente o `SafeWriteUseCase` para garantir conformidade com auditoria local e geração automática de snapshots de rollback.
- **Formato TOML:** Certifique-se de que a escrita TOML siga as convenções do projeto (snake_case, UTF-8).
- **Paridade CLI/MCP:** Durante a execução da ferramenta MCP ou CLI com `--format json`, desabilitar interações humanas interativas (`input()`) e adotar defaults seguros (habilitando todos os hosts suportados caso nenhuma restrição explícita tenha sido imposta).

### Project Structure Notes

- O arquivo de configuração local é `.umem/config.toml`. O arquivo global padrão (opcional) lives em `~/.config/universal-memory/config.toml`.
- O layout gerado na inicialização deve preservar a conformidade descrita em `project_layout.py`.

### References

- [Architecture Guidelines: Host Support Matrix](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#Host%20Support%20Matrix)
- [Architecture Guidelines: Rules and Manifest Strategy](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/architecture.md#Rules%20and%20Manifest%20Strategy)
- [Acceptance Criteria: Epic 5 Story 5.6](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/epics.md#Story%205.6)
- [DevEx CLI & Mutation Specifications](file:///Users/amorelliaoyan/projects/personal/lab/universal-memory/_bmad-output/planning-artifacts/devex-interaction-spec.md)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- `uv run pytest tests/infrastructure/config/test_toml_loader.py tests/application/test_setup_project.py tests/interfaces/cli/test_init_command.py tests/application/host/test_sync_instructions.py` -> 28 passed.
- `uv run ruff check .` -> All checks passed.
- `uv run pytest` -> 293 passed.

### Implementation Plan

- Estender a persistência TOML existente com escrita de configuração local preservando o estilo `tomli_w`.
- Fazer o onboarding persistir hosts padrão ou selecionados e expor seleção por `umem init --hosts` e prompt interativo.
- Reutilizar os handlers de host já compostos para executar `ConfigureHostCommand(apply=True)` e depois `check=True`.
- Fazer `SyncInstructionsUseCase` ler `.umem/config.toml` e filtrar apenas hosts habilitados quando o comando usa a seleção padrão.

### Completion Notes List

- Implementado `update_project_config()` e persistência de `[hosts] enabled = [...]` durante `setup_project`.
- `umem init` agora aceita `--hosts` repetível, respeita `--yes`/JSON como modo não interativo e usa prompts individuais em terminal interativo.
- O onboarding chama setup e check dos hosts selecionados quando os handlers estão disponíveis; a escrita física continua passando pelo `ConfigureHostUseCase` e `SafeWriteUseCase`.
- `SyncInstructionsUseCase` passa a respeitar hosts habilitados para sincronização padrão e permite sincronização sob demanda de host omitido com warning.
- Testes cobrem persistência TOML, setup com hosts padrão/selecionados, fluxo CLI JSON/interativo e sync com host desabilitado.

### File List

- `_bmad-output/implementation-artifacts/5-6-fluxo-de-sele-o-de-hosts-no-onboarding.md`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `src/universal_memory/application/host/setup_host_use_case.py`
- `src/universal_memory/application/host/sync_instructions_use_case.py`
- `src/universal_memory/application/onboarding/setup_project.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/infrastructure/config/toml_loader.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `tests/application/host/test_sync_instructions.py`
- `tests/application/test_setup_project.py`
- `tests/infrastructure/config/test_toml_loader.py`
- `tests/interfaces/cli/test_host_sync.py`
- `tests/interfaces/cli/test_init_command.py`

### Change Log

- 2026-05-29: Implementado fluxo de seleção de hosts no onboarding e filtro de sincronização por hosts habilitados.
