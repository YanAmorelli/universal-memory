# Story 5.2: Configurar Host Codex com AGENTS.md

Status: done

<!-- Note: Validation is optional. Run validate-create-story for quality check before dev-story. -->

## Story

Como um usuário usando Codex em um projeto,
eu quero configurar `AGENTS.md` como manifesto compartilhado compacto,
para que o agente leia regras operacionais e ponteiros para memória sem carregar conhecimento excessivo.

## Acceptance Criteria

1. **Dado** um projeto inicializado com `.umem/`
   **Quando** o usuário executa setup/check do host `codex`
   **Então** o sistema detecta ou propõe o arquivo `AGENTS.md` na raiz do projeto;
   **E** classifica cada instrução proposta como `shared_policy` (regras operacionais estáveis), `provider_delta` (específica de host), `scoped_rule` (regras locais) ou `canonical_doc` (docs de projeto);
   **E** regras de tipo `canonical_doc` devem ser salvas na pasta `docs/` e apenas referenciadas no `AGENTS.md` de forma compacta (ponteiros).

2. **Dado** um `AGENTS.md` existente contendo conteúdo editado manualmente pelo usuário fora dos blocos autogerenciados,
   **Quando** o sistema precisa atualizá-lo para injetar novas regras ou atualizar o bootstrap da memória,
   **Then** o motor preserva as seções manuais não gerenciadas utilizando delimitadores claros de comentários HTML:
     - `<!-- UMEM: START -->` e `<!-- UMEM: END -->` (ou equivalentes estruturados);
   **And** qualquer mutação de escrita no arquivo passa estritamente pelo pipeline seguro de escrita (`SafeWriteUseCase`), gerando snapshot, auditoria e rollback.

3. **Dado** o manifesto `AGENTS.md` gerado ou atualizado pelo setup/check do host `codex`,
   **When** a validação do host é executada,
   **Then** o validador garante que o arquivo `AGENTS.md` permanece abaixo do limite compacto de tamanho (ex: tamanho máximo recomendado em bytes ou linhas configurável);
   **And** garante que não virou um dump de conhecimento massivo do projeto (rejeita dumps brutos de fatos/memórias, exigindo que fatos longos fiquem em `docs/` ou sejam recuperados dinamicamente via MCP);
   **And** retorna o status de validação adequado com timestamp e auditoria.

4. **Dado** a execução da CLI ou MCP para setup/check do host `codex`,
   **When** invocado via terminal ou ferramenta MCP,
   **Then** a CLI aceita a flag de confirmação interativa `--yes` / `-y`;
   **And** exibe o plano detalhado de alterações, o caminho relativo do arquivo, o snapshot planejado e o tipo de evento de auditoria antes da aplicação;
   **And** no formato `--format json`, retorna estritamente o payload formatado:
     ```json
     {
       "ok": true,
       "operation": "host_setup",
       "scope": "project",
       "data": {
         "host_id": "codex",
         "instruction_targets": ["agents_md"],
         "planned_changes": [
           {
             "target": "agents_md",
             "action": "create",
             "path": "AGENTS.md"
           }
         ],
         "manual_steps": [],
         "validation_status": "success",
         "audit_reference": "uuid-v4-reference"
       },
       "warnings": []
     }
     ```

## Tasks / Subtasks

- [x] **Task 1: Implementar o Serviço/Port de Domínio para Classificação e Particionamento de Instruções** (AC: 1, 3)
  - [x] Implementar a lógica que classifica blocos de regras em `shared_policy`, `provider_delta`, `scoped_rule` ou `canonical_doc`.
  - [x] Garantir que conteúdos longos (`canonical_doc`) sejam separados para gravação na pasta `docs/` e referenciados no manifesto principal por meio de ponteiros/links relativos (ex: `[README.md](file:///docs/readme.md)`).
  - [x] Validar que o manifesto final resultante em `AGENTS.md` permanece estritamente compacto (limite configurável, e.g., máximo de 100 linhas ou 4000 caracteres no bloco autogerenciado).

- [x] **Task 2: Implementar o Use Case de Host Setup & Check** (AC: 1, 2, 3)
  - [x] Criar o use case `ConfigureHostUseCase` (ou `SetupHostUseCase`) em `src/universal_memory/application/host/setup_host_use_case.py`.
  - [x] Integrar o `SafeWriteUseCase` existente para todas as mutações no arquivo `AGENTS.md`.
  - [x] Implementar lógica de preservação de seções manuais no `AGENTS.md` caso o arquivo já exista:
    - Procurar por delimitadores estruturados: `<!-- UMEM: START -->` e `<!-- UMEM: END -->`.
    - Preservar intactos quaisquer dados/comentários adicionados pelo usuário antes e depois destes marcadores.
    - Se os marcadores não existirem, acrescentá-los de forma limpa ao final do arquivo ou inicializar um novo `AGENTS.md`.
  - [x] Implementar a verificação/validação associada ao host `codex` (garantir presença do manifesto, integridade da instrução bootstrap de memória, validação do endpoint MCP e tamanho compacto).

- [x] **Task 3: Integrar CLI para os Comandos `umem host setup` e `umem host check`** (AC: 4)
  - [x] Criar ou atualizar os comandos CLI correspondentes no arquivo `src/universal_memory/interfaces/cli/host_command.py` ou diretamente no `init_command.py`.
  - [x] Expor opções comuns: `--yes` / `-y` (para bypassar confirmações em setup) e `--format json`/`human`.
  - [x] Exibir de forma rica (Rich Panels/Tables) o plano detalhado antes da mutação de escrita no terminal.
  - [x] Formatar o output JSON exatamente conforme o envelope de sucesso/erro padrão da especificação DevEx.

- [x] **Task 4: Expor as Ferramentas MCP Equivalentes** (AC: 4)
  - [x] Registrar as ferramentas MCP em `src/universal_memory/bootstrap/mcp.py` / `src/universal_memory/interfaces/mcp/`:
    - `host_setup(host_id: str, force: bool = False)`
    - `host_check(host_id: str)`
  - [x] Mapear as chamadas dos métodos MCP de forma idêntica ao Use Case central, mantendo conformidade e mesma estrutura de campos JSON que a CLI.

- [x] **Task 5: Suíte Completa de Testes Unitários e Integração** (AC: 1, 2, 3, 4)
  - [x] Criar testes unitários para o parser de preservação de blocos manuais (`test_manual_block_preservation.py`).
  - [x] Criar testes de integração para o `ConfigureHostUseCase` simulando setup em repositórios novos e brownfield.
  - [x] Escrever testes de conformidade para o comando CLI (`umem host setup` e `umem host check`) validando o formato human-rich e JSON de retorno.
  - [x] Validar a tipagem estática com `uv run pyright` e o estilo do código com `uv run ruff check`.
  - [x] Assegurar 100% de cobertura nos cenários críticos de rollback e snapshot decorrentes de mutações de host.

### Review Findings

- [x] [Review][Decision] Instruções e blocos propostos não são injetáveis/passados via CLI ou MCP — A CLI e o MCP chamam o use case de setup/check sem passar nenhum `instruction_blocks`, resultando em uma lista vazia e impedindo o fluxo de classificação de regras reais no uso normal.
- [x] [Review][Decision] Inexistência de parametrização para limites compactos na CLI e MCP — Os limites compactos (`max_managed_lines` e `max_managed_chars`) não são expostos como parâmetros na CLI ou nas ferramentas MCP, impedindo que os usuários configurem esses limites conforme exigido pelo AC 3.
- [x] [Review][Patch] Substituição silenciosa de referências de snapshot/auditoria e falta de transacionalidade no loop de escrita [src/universal_memory/application/host/setup_host_use_case.py:179-202]
- [x] [Review][Patch] Vulnerabilidade de Traversal de Caminho no Windows e falta de validação preventiva no plano [src/universal_memory/application/host/setup_host_use_case.py:365]
- [x] [Review][Patch] Colisão de caminhos/slugs de documentos canônicos com títulos idênticos ou parecidos [src/universal_memory/application/host/setup_host_use_case.py:143]
- [x] [Review][Patch] Caminhos de ponteiros não utilizam o prefixo de protocolo `file:///` [src/universal_memory/application/host/setup_host_use_case.py:121]
- [x] [Review][Patch] Remoção de acentuação gráfica em textos propostos no bloco UMEM [src/universal_memory/application/host/setup_host_use_case.py:263-286]
- [x] [Review][Patch] Delimitadores UMEM incompletos barram execução e bloqueiam auto-correção [src/universal_memory/application/host/setup_host_use_case.py:307]
- [x] [Review][Patch] Incompatibilidade com quebras de linha Windows (CRLF) [src/universal_memory/application/host/setup_host_use_case.py:298]
- [x] [Review][Patch] Quebra de formatação Markdown em blocos multilinha [src/universal_memory/application/host/setup_host_use_case.py:276]
- [x] [Review][Patch] Validação obstrutiva de conteúdo existente [src/universal_memory/application/host/setup_host_use_case.py:148]
- [x] [Review][Patch] Presença de delimitadores UMEM no conteúdo dos blocos [src/universal_memory/application/host/setup_host_use_case.py:323]
- [x] [Review][Patch] Dependência de `datetime.now(UTC)` em versões antigas do Python [src/universal_memory/application/host/setup_host_use_case.py:222]
- [x] [Review][Patch] Falsos positivos com termos de dump de memória [src/universal_memory/application/host/setup_host_use_case.py:319]
- [x] [Review][Patch] Ausência de verificação de Symlinks direcionando fora do projeto [src/universal_memory/application/host/setup_host_use_case.py:256]
- [x] [Review][Patch] Omissão de `snapshot_reference` e `timestamp` no Payload de retorno [src/universal_memory/application/host/setup_host_use_case.py:91]

## Dev Notes

- **Reutilização Obrigatória de Componentes Existentes:**
  - **NÃO** tente escrever arquivos usando `Path.write_text` diretamente. Você **DEVE** utilizar o `SafeWriteUseCase` importado de `universal_memory.application.security` para aplicar mutações no `AGENTS.md`. Ele garante validação de segredos (entropy scanning), geração de UUIDs para snapshots, e gravação atômica com auditoria nativa no repositório.
  - Utilize os modelos de entidade do domínio (`Host`, `HostName`, `InstructionTarget` e `InstructionTargetType`) criados na Story 5.1 para validar as invariantes do host `codex`.

- **Formato da Seção Autogerenciada no AGENTS.md:**
  - O bootstrap de memória obrigatório no `AGENTS.md` deve conter um ponteiro claro instando o agente leitor a consultar o servidor MCP do universal-memory ou as rotinas locais. Exemplo de instrução bootstrap:
    ```markdown
    <!-- UMEM: START -->
    # Universal Memory Active Policy
    > [!IMPORTANT]
    > Antes de iniciar qualquer tarefa de codificação, consulte a Short Term Memory deste repositório executando a CLI `umem context` ou usando as ferramentas MCP correspondentes.
    
    ## Regras Operacionais Consolidadas:
    - [Regras ativas da memória injetadas aqui de forma compacta]
    
    ## Ponteiros Canônicos:
    - Diretrizes adicionais em [docs/PROJECT_GUIDES.md](file:///docs/PROJECT_GUIDES.md)
    <!-- UMEM: END -->
    ```

- **Mapeamento de Erros e Segurança:**
  - Se um segredo for detectado no manifesto `AGENTS.md` durante o processo de setup, o sistema deve levantar um `SecretDetectedError` e abortar a operação, garantindo que nenhum segredo seja gravado no manifesto público.

### Project Structure Notes

- O use case de aplicação deve ser alocado em:
  - `src/universal_memory/application/host/setup_host_use_case.py` (Novo)
- A lógica de CLI e as extensões Typer devem ir em:
  - `src/universal_memory/interfaces/cli/host_command.py` (Novo)
  - E registradas no arquivo de bootstrap do console `src/universal_memory/bootstrap/cli.py`.
- O adapter MCP e o registro de ferramentas devem ser estendidos em:
  - `src/universal_memory/bootstrap/mcp.py`
- Os testes automatizados da Story devem ser inseridos em:
  - `tests/application/test_setup_host.py`
  - `tests/interfaces/test_host_cli.py`

### References

- **Host Domain Entities (Story 5.1)**: [instruction_target.py](file:///src/universal_memory/domain/entities/instruction_target.py) e [host.py](file:///src/universal_memory/domain/entities/host.py)
- **DevEx Interaction Specification**: [devex-interaction-spec.md](file:///_bmad-output/planning-artifacts/devex-interaction-spec.md#L197-L209)
- **Architecture Instruction Strategy**: [architecture.md](file:///_bmad-output/planning-artifacts/architecture.md#L753-L827)
- **PRD Automations (FR8, FR15)**: [prd.md](file:///_bmad-output/planning-artifacts/prd.md#L322-L339)

## Dev Agent Record

### Agent Model Used

GPT-5 Codex

### Debug Log References

- 2026-05-28: `uv run pytest tests/application/test_setup_host.py tests/interfaces/cli/test_host_command.py`
- 2026-05-28: `uv run pytest tests/interfaces/mcp/test_server.py tests/application/test_setup_host.py tests/interfaces/cli/test_host_command.py`
- 2026-05-28: `uv run ruff check`
- 2026-05-28: `uv run pyright`
- 2026-05-28: `uv run pytest`

### Completion Notes List

- Implementado `ConfigureHostUseCase` para host `codex`, incluindo particionamento de instruções, geração/preservação do bloco autogerenciado `UMEM`, ponteiros relativos para documentos canônicos em `docs/`, validação de compacidade e bloqueio de dumps brutos de memória.
- Todas as mutações de `AGENTS.md` e documentos canônicos passam por `SafeWriteUseCase`, gerando snapshot/auditoria e respeitando o scanner de segredos.
- Integrados comandos `umem host setup` e `umem host check` com `--yes`/`-y`, saída human com plano e saída JSON no contrato DevEx.
- Expostas ferramentas MCP `host_setup` e `host_check` com o mesmo use case e contrato de payload da CLI.
- Validações concluídas: `uv run ruff check`, `uv run pyright`, `uv run pytest` (`264 passed`).

### File List

- `src/universal_memory/application/host/__init__.py`
- `src/universal_memory/application/host/setup_host_use_case.py`
- `src/universal_memory/bootstrap/cli.py`
- `src/universal_memory/bootstrap/mcp.py`
- `src/universal_memory/interfaces/cli/init_command.py`
- `src/universal_memory/interfaces/mcp/server.py`
- `tests/application/test_setup_host.py`
- `tests/application/test_manual_block_preservation.py`
- `tests/interfaces/cli/test_host_command.py`
- `tests/interfaces/mcp/test_compliance.py`
- `tests/interfaces/mcp/test_server.py`
- `_bmad-output/implementation-artifacts/sprint-status.yaml`
- `_bmad-output/implementation-artifacts/5-2-configurar-host-codex-com-agents-md.md`

### Change Log

- 2026-05-28: Implementada configuração/check do host Codex com AGENTS.md, CLI, MCP, validações e testes automatizados.
