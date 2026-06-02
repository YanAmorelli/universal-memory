# Especificação Técnica: `umem doctor`

O comando `umem doctor` foi concebido para ser uma ferramenta pré-voo de diagnóstico no **Alpha Tester V2**, projetada para analisar o ambiente local e detectar de forma proativa problemas de configuração, permissões e compatibilidade antes do início do uso do `universal-memory` (CLI e MCP).

---

## 🎯 Objetivos de Negócio & UX

1. **Reduzir Fricção de Onboarding**: Garantir que novos usuários e testadores alpha consigam validar seu ecossistema sem necessitar de depuração manual.
2. **Auto-Diagnóstico Rápido**: Gerar um relatório instantâneo sobre dependências em falta, permissões corrompidas e caminhos inválidos.
3. **Erros Acionáveis**: Cada falha reportada deve vir acompanhada de uma sugestão clara de resolução (ex: "Execute `chmod +w ...`" ou "Instale a versão compatível do Python").

---

## 🛠️ Detalhamento dos Checks

O comando `umem doctor` executará um pipeline seqüencial de verificações de integridade:

### 1. Check do Python (`PythonVersionCheck`)
- **Objetivo**: Garantir que o interpretador executando o universal-memory seja $\ge 3.12$.
- **Ação**: Inspecionar `sys.version_info`.
- **Dica de Recuperação**: "Por favor, configure um ambiente virtual com Python 3.12 ou superior."

### 2. Check de Permissão de Caminhos Canônicos (`PathPermissionsCheck`)
- **Objetivo**: Validar se o usuário possui acesso de leitura e escrita nos diretórios de persistência.
- **Locais a Validar**:
  - Diretório local `.umem/` (se inicializado).
  - Diretório global `$XDG_DATA_HOME/umem/` ou `$HOME/.local/share/umem/`.
  - Arquivo de configuração `$XDG_CONFIG_HOME/umem/config.toml` ou `$HOME/.config/umem/config.toml`.
- **Ação**: Tentar criar e remover um arquivo temporário (`tempfile.TemporaryFile`) nas pastas canônicas correspondentes.
- **Dica de Recuperação**: "Corrija as permissões do sistema de arquivos executando `chmod -R u+rw <path>`."

### 3. Check de Estrutura do Layout (`ProjectLayoutCheck`)
- **Objetivo**: Verificar se a pasta local `.umem/` está em um estado parcial ou corrompido.
- **Ação**: Verificar se todos os caminhos canônicos mínimos existem:
  - `.umem/config.toml` (arquivo)
  - `.umem/memory/` (diretório)
  - `.umem/audit/events.jsonl` (arquivo)
  - `.umem/snapshots/` (diretório)
  - `.umem/skills/` (diretório)
- **Dica de Recuperação**: "A pasta `.umem` está incompleta. Execute `umem init --yes` para reconstruir o layout padrão de forma segura."

### 4. Check de Executáveis e Variáveis no PATH (`PathExecutablesCheck`)
- **Objetivo**: Validar se os executáveis `umem` e `umem-mcp` estão expostos globalmente no terminal ou se a ferramenta `uv` está operacional.
- **Ação**: Executar comandos `which umem` e `which umem-mcp` ou equivalentes multiplataforma.
- **Dica de Recuperação**: "Os scripts de entrada não estão no seu PATH. Certifique-se de ativar o ambiente virtual ou instalar com `pip install --editable .` ou `uv sync`."

### 5. Check de Hosts Configurados (`HostsIntegrationCheck`)
- **Objetivo**: Garantir que os hosts suportados e ativados no `config.toml` (ex: `codex`, `claude_code`) possuam seus respectivos arquivos físicos de instrução configurados e íntegros.
- **Ação**: Executar uma chamada sob os validadores do `HostCheck` (equivalente ao `umem host check <host_id>`).
- **Dica de Recuperação**: "O bloco gerenciado UMEM está ausente ou corrompido no arquivo de configuração do host. Execute `umem host setup <host_id>`."

---

## 📊 Formato da Saída

O comando deve suportar o formato padrão de saída humana (Rich e estilizado) e JSON (envelopado), mantendo a paridade de DX.

### Exemplo de Saída Humana (Terminal)

```text
💎 universal-memory Doctor - Relatório de Integridade
===================================================

[✔] Ambiente Python (3.12.13) ........................................ [OK]
[✔] Permissões do Filesystem (Local & Global) ........................ [OK]
[✘] Estrutura do Layout local (.umem) ................................ [FALHA]
    ↳ Erro: Arquivo '.umem/audit/events.jsonl' ausente.
    ↳ Recuperação: Execute 'umem init --yes' para reconstruir os caminhos.
[✔] Exposição de Executáveis no PATH .................................. [OK]
[✘] Integração de Hosts (codex) ...................................... [FALHA]
    ↳ Erro: Arquivo AGENTS.md não validado (assinatura UMEM inválida).
    ↳ Recuperação: Execute 'umem host setup codex --yes' para reparar.

🩺 Status Final: 2 falhas encontradas. Seu ambiente exige atenção.
```

### Exemplo de Saída JSON (`umem doctor --format json`)

```json
{
  "ok": false,
  "operation": "doctor",
  "scope": "environment",
  "data": {
    "checks": [
      {
        "name": "python_version",
        "status": "success",
        "detail": "Python 3.12.13"
      },
      {
        "name": "filesystem_permissions",
        "status": "success"
      },
      {
        "name": "project_layout",
        "status": "failed",
        "error": "Missing path: .umem/audit/events.jsonl",
        "recovery_hint": "Execute 'umem init --yes' para reconstruir os caminhos."
      },
      {
        "name": "path_executables",
        "status": "success"
      },
      {
        "name": "hosts_integration",
        "status": "failed",
        "error": "AGENTS.md has corrupted UMEM managed block",
        "recovery_hint": "Execute 'umem host setup codex --yes' para reparar."
      }
    ],
    "summary": {
      "total_checks": 5,
      "passed": 3,
      "failed": 2
    }
  },
  "warnings": []
}
```
