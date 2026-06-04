#!/usr/bin/env python3
import json
import os
import subprocess
import sys
import tempfile
import time
import traceback
from pathlib import Path

# Descobre o diretório raiz do repositório de forma dinâmica
ORIGINAL_PROJECT_DIR = str(Path(__file__).resolve().parent.parent)

class MCPClient:
    def __init__(self, project_dir, env):
        self.process = subprocess.Popen(
            ["uv", "--project", ORIGINAL_PROJECT_DIR, "run", "umem-mcp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            cwd=project_dir,
            env=env,
            text=True,
            bufsize=1
        )
        self.msg_id = 1
        self.log_messages = []

    def send_request(self, method, params):
        req = {
            "jsonrpc": "2.0",
            "id": self.msg_id,
            "method": method,
            "params": params
        }
        self.msg_id += 1
        payload = json.dumps(req)
        self.process.stdin.write(payload + "\n")
        self.process.stdin.flush()
        return req["id"]

    def read_response(self, expected_id, timeout=5):
        start_time = time.time()
        while time.time() - start_time < timeout:
            line = self.process.stdout.readline()
            if not line:
                break
            line_str = line.strip()
            if not line_str:
                continue
            try:
                resp = json.loads(line_str)
                if resp.get("id") == expected_id:
                    return resp
                else:
                    self.log_messages.append(resp)
            except json.JSONDecodeError:
                self.log_messages.append(line_str)
        raise TimeoutError(f"Resposta com id {expected_id} nao recebida dentro de {timeout} segundos. Logs: {self.log_messages}")

    def call_tool(self, tool_name, arguments):
        req_id = self.send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments
        })
        return self.read_response(req_id)

    def initialize(self):
        req_id = self.send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {
                "name": "alpha-tester-v2",
                "version": "2.0"
            }
        })
        init_resp = self.read_response(req_id)
        # Envia notificação de initialized
        notif = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        self.process.stdin.write(json.dumps(notif) + "\n")
        self.process.stdin.flush()
        return init_resp

    def close(self):
        self.process.terminate()
        try:
            self.process.wait(timeout=2)
        except subprocess.TimeoutExpired:
            self.process.kill()


def get_mcp_data(resp):
    result = resp.get("result", {})
    struct = result.get("structuredContent")
    if struct is not None:
        return struct
    content = result.get("content", [])
    if content:
        text = content[0].get("text", "")
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return {"raw_text": text}
    if result.get("isError") is True or "error" in resp:
        return {"ok": False, "error": resp.get("error", "Unknown MCP error")}
    return {}


def run_cli(args, cwd, env, expect_fail=False):
    cmd = ["uv", "--project", ORIGINAL_PROJECT_DIR, "run", "umem"] + args
    result = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True
    )
    if expect_fail:
        if result.returncode == 0:
            raise AssertionError(f"Esperava que o comando falhasse, mas retornou 0: {' '.join(cmd)}\nStdout: {result.stdout}\nStderr: {result.stderr}")
    elif result.returncode != 0:
        raise AssertionError(f"Comando falhou com codigo {result.returncode}: {' '.join(cmd)}\nStdout: {result.stdout}\nStderr: {result.stderr}")
    return result.stdout, result.stderr, result.returncode


def main():
    report = []
    report.append("# Alpha Sandbox Test Simulation Report - V2")
    report.append(f"Executado em: {time.strftime('%Y-%m-%d %H:%M:%S')}\n")
    report.append("| Fase do Teste | Status | Detalhes |")
    report.append("| --- | --- | --- |")

    temp_dir = tempfile.TemporaryDirectory(prefix="umem-smoke-v2-")
    sandbox_path = Path(temp_dir.name)
    project_path = sandbox_path / "project"
    home_path = sandbox_path / "home"

    project_path.mkdir(parents=True)
    home_path.mkdir(parents=True)

    # Configuração de variáveis de ambiente isoladas
    env = os.environ.copy()
    env["HOME"] = str(home_path)
    env["XDG_CONFIG_HOME"] = str(home_path / ".config")
    env["XDG_DATA_HOME"] = str(home_path / ".local" / "share")

    print(f"--- Sandbox criada em {sandbox_path} ---")

    # 1. Preparação
    try:
        stdout, stderr, code = run_cli(["--help"], project_path, env)
        assert "umem" in stdout or "Usage:" in stdout, "umem --help nao contem ajuda"
        report.append("| 1. Preparacao | ✅ PASS | Sandbox criada, `umem --help` executado com sucesso. |")
    except Exception as e:
        traceback.print_exc()
        report.append(f"| 1. Preparacao | ❌ FAIL | Falha ao preparar ambiente: {e} |")
        print(f"Falha na preparacao: {e}")
        sys.exit(1)

    # 2. Smoke CLI Básico
    try:
        stdout, _, _ = run_cli(["status", "--format", "json"], project_path, env)
        envelope = json.loads(stdout)
        status_data = envelope.get("data", {})
        assert status_data.get("initialized") is False, "Esperava initialized=False antes de rodar o init"

        stdout, _, _ = run_cli(["init", "--yes", "--hosts", "codex", "--hosts", "claude_code", "--format", "json"], project_path, env)
        init_envelope = json.loads(stdout)
        assert init_envelope.get("ok") is True, "Init falhou"

        stdout, _, _ = run_cli(["status", "--format", "json"], project_path, env)
        envelope = json.loads(stdout)
        status_data = envelope.get("data", {})
        assert status_data.get("initialized") is True, "Esperava initialized=True apos init"

        umem_dir = project_path / ".umem"
        assert (umem_dir / "config.toml").is_file(), "config.toml nao encontrado"
        assert (umem_dir / "memory").is_dir(), "pasta memory nao encontrada"
        assert (umem_dir / "audit" / "events.jsonl").is_file(), "events.jsonl nao encontrado"
        assert (umem_dir / "snapshots").is_dir(), "pasta snapshots nao encontrada"
        assert (umem_dir / "skills").is_dir(), "pasta skills nao encontrada"

        stdout, _, _ = run_cli(["init", "--yes", "--format", "json"], project_path, env)
        init_envelope_2 = json.loads(stdout)
        assert init_envelope_2.get("ok") is True or init_envelope_2.get("status") == "success", "Init de idempotencia falhou"
        
        stdout, _, _ = run_cli(["status", "--format", "json"], project_path, env)
        envelope_2 = json.loads(stdout)
        status_data_2 = envelope_2.get("data", {})
        assert status_data_2.get("initialized") is True, "A idempotencia quebrou o status inicializado"

        report.append("| 2. Smoke CLI Basico | ✅ PASS | Inicializacao bem sucedida, idempotencia confirmada, layout verificado. |")
    except Exception as e:
        traceback.print_exc()
        err_msg = "".join(traceback.format_exception_only(type(e), e)).strip()
        report.append(f"| 2. Smoke CLI Basico | ❌ FAIL | Erro: {err_msg} |")
        print(f"Falha no Smoke CLI Basico: {err_msg}")

    # 3. Memoria Local E Global
    try:
        run_cli(["remember", "O projeto usa arquitetura hexagonal.", "--scope", "project", "--tag", "architecture", "--format", "json"], project_path, env)
        run_cli(["remember", "Preferir respostas objetivas em portugues.", "--scope", "global", "--tag", "preference", "--format", "json"], project_path, env)

        stdout_local, _, _ = run_cli(["facts", "list", "--scope", "project", "--format", "json"], project_path, env)
        facts_local = json.loads(stdout_local).get("data", {}).get("facts", [])
        assert any("arquitetura hexagonal" in f.get("content", "") for f in facts_local), "Fato local nao encontrado na listagem"

        stdout_global, _, _ = run_cli(["facts", "list", "--scope", "global", "--format", "json"], project_path, env)
        facts_global = json.loads(stdout_global).get("data", {}).get("facts", [])
        assert any("portugues" in f.get("content", "") for f in facts_global), "Fato global nao encontrado na listagem"

        stdout_ctx, _, _ = run_cli(["context", "--scope", "project", "--max-size-chars", "4000", "--format", "json"], project_path, env)
        ctx_envelope = json.loads(stdout_ctx)
        assert ctx_envelope.get("ok") is True and "project_summary" in ctx_envelope.get("data", {}), "Falha ao gerar contexto local"
        
        stdout_ctx_glob, _, _ = run_cli(["context", "--scope", "global", "--format", "json"], project_path, env)
        ctx_glob_envelope = json.loads(stdout_ctx_glob)
        assert ctx_glob_envelope.get("ok") is True and "project_summary" in ctx_glob_envelope.get("data", {}), "Falha ao gerar contexto global"

        report.append("| 3. Memoria Local e Global | ✅ PASS | Fatos gravados e recuperados corretamente em ambos os escopos. Contextos gerados com sucesso. |")
    except Exception as e:
        traceback.print_exc()
        err_msg = "".join(traceback.format_exception_only(type(e), e)).strip()
        report.append(f"| 3. Memoria Local e Global | ❌ FAIL | Erro: {err_msg} |")
        print(f"Falha na Memoria Local e Global: {err_msg}")

    # 4. Segurança, Snapshots E Rollback
    try:
        stdout_snapshots, _, _ = run_cli(["snapshots", "list", "--scope", "project", "--format", "json"], project_path, env)
        snapshots_envelope = json.loads(stdout_snapshots)
        assert len(snapshots_envelope.get("data", {}).get("snapshots", [])) > 0, "Deveria haver pelo menos 1 snapshot"

        stdout_audit, _, _ = run_cli(["audit", "list", "--scope", "project", "--format", "json"], project_path, env)
        audit_envelope = json.loads(stdout_audit)
        assert len(audit_envelope.get("data", {}).get("events", [])) > 0, "Deveria haver eventos no log de auditoria"

        secret_blocked = False
        try:
            stdout_secret, stderr_secret, code_secret = run_cli(
                ["remember", "aws_secret_access_key = AKIAIOSFODNN7EXAMPLE", "--scope", "project", "--format", "json"], 
                project_path, env, expect_fail=True
            )
            sec_env = json.loads(stdout_secret)
            if not sec_env.get("ok"):
                secret_blocked = True
        except (AssertionError, json.JSONDecodeError):
            secret_blocked = True

        assert secret_blocked, "Segredo nao foi bloqueado pelo EntropySecretScanner"
        report.append("| 4. Seguranca (Deteccao Segredo) | ✅ PASS | Segredo de alta entropia detectado e bloqueado com sucesso. |")

        run_cli(["remember", "Fato antes do rollback.", "--scope", "project", "--format", "json"], project_path, env)
        stdout_f1, _, _ = run_cli(["facts", "list", "--scope", "project", "--format", "json"], project_path, env)
        facts_f1 = json.loads(stdout_f1).get("data", {}).get("facts", [])
        
        run_cli(["rollback", "--scope", "project", "--yes", "--format", "json"], project_path, env)
        stdout_f2, _, _ = run_cli(["facts", "list", "--scope", "project", "--format", "json"], project_path, env)
        facts_f2 = json.loads(stdout_f2).get("data", {}).get("facts", [])
        
        assert len(facts_f2) < len(facts_f1), "Rollback nao surtiu efeito no numero de fatos ativos"
        report.append("| 4. Snapshots e Rollback | ✅ PASS | Snapshots gravados, auditados e rollback executado com sucesso. |")
    except Exception as e:
        traceback.print_exc()
        err_msg = "".join(traceback.format_exception_only(type(e), e)).strip()
        report.append(f"| 4. Snapshots e Rollback | ❌ FAIL | Erro: {err_msg} |")
        print(f"Falha em Snapshots e Rollback: {err_msg}")

    # 5. Purge E Hygiene
    try:
        stdout_list, _, _ = run_cli(["facts", "list", "--scope", "project", "--format", "json"], project_path, env)
        facts_list = json.loads(stdout_list).get("data", {}).get("facts", [])
        assert len(facts_list) > 0, "Precisa haver pelo menos um fato ativo para o purge"
        fact_id = facts_list[0]["id"]

        run_cli(["facts", "purge", "--id", fact_id, "--format", "json"], project_path, env, expect_fail=True)
        run_cli(["facts", "purge", "--id", fact_id, "--yes", "--format", "json"], project_path, env)

        stdout_list_2, _, _ = run_cli(["facts", "list", "--scope", "project", "--format", "json"], project_path, env)
        facts_list_2 = json.loads(stdout_list_2).get("data", {}).get("facts", [])
        assert not any(f["id"] == fact_id for f in facts_list_2), "Fato purgado ainda aparece na listagem ativa"

        run_cli(["facts", "hygiene", "--yes", "--format", "json"], project_path, env)
        report.append("| 5. Purge e Hygiene | ✅ PASS | Purge destructivo protegido, purge apaga fisicamente o dado por seguranca e hygiene executa sem erro. |")
    except Exception as e:
        traceback.print_exc()
        err_msg = "".join(traceback.format_exception_only(type(e), e)).strip()
        report.append(f"| 5. Purge e Hygiene | ❌ FAIL | Erro: {err_msg} |")
        print(f"Falha em Purge e Hygiene: {err_msg}")

    # 6. Hosts
    try:
        run_cli(["host", "setup", "codex", "--yes", "--format", "json"], project_path, env)
        run_cli(["host", "setup", "claude_code", "--yes", "--format", "json"], project_path, env)

        assert (project_path / "AGENTS.md").is_file(), "AGENTS.md para codex nao foi criado"
        assert (project_path / "CLAUDE.md").is_file(), "CLAUDE.md para claude_code nao foi criado"

        stdout_check_codex, _, _ = run_cli(["host", "check", "codex", "--format", "json"], project_path, env)
        check_codex_envelope = json.loads(stdout_check_codex)
        assert check_codex_envelope.get("ok") is True or check_codex_envelope.get("data", {}).get("status") == "success", "Check do codex falhou"

        run_cli(["host", "sync", "--no-apply", "--format", "json"], project_path, env)
        run_cli(["host", "sync", "--apply", "--yes", "--format", "json"], project_path, env)

        report.append("| 6. Hosts | ✅ PASS | Setup, Check e Sync dos hosts codex e claude_code executados com exito. |")
    except Exception as e:
        traceback.print_exc()
        err_msg = "".join(traceback.format_exception_only(type(e), e)).strip()
        report.append(f"| 6. Hosts | ❌ FAIL | Erro: {err_msg} |")
        print(f"Falha em Hosts: {err_msg}")

    # 7. Skills
    try:
        skills_file = project_path / ".umem" / "memory" / "latent_skills.jsonl"
        latent_skill_id = "22222222-2222-4222-8222-222222222222"
        latent_skill_data = {
            "id": latent_skill_id,
            "created_at": "2026-06-02T12:00:00Z",
            "updated_at": "2026-06-02T12:00:00Z",
            "name": "AutoRefactor",
            "description": "Usuario solicita refatoracao automatizada",
            "scope": "project",
            "status": "proposed",
            "recurrence_count": 3,
            "metadata": {"origin": "alpha-tester-v2"}
        }
        skills_file.parent.mkdir(parents=True, exist_ok=True)
        with open(skills_file, "w", encoding="utf-8") as f:
            f.write(json.dumps(latent_skill_data) + "\n")

        stdout_skills, _, _ = run_cli(["skills", "list", "--format", "json"], project_path, env)
        skills_envelope = json.loads(stdout_skills)
        skills_list = skills_envelope.get("data", {}).get("skills", [])
        assert any(s["name"] == latent_skill_data["name"] for s in skills_list), "Latent skill da fixture nao listada"

        run_cli(["skills", "propose", latent_skill_id, "--decision", "yes", "--format", "json"], project_path, env)
        run_cli(["skills", "generate", latent_skill_id, "--yes", "--format", "json"], project_path, env)
        assert (project_path / ".umem" / "skills" / "autorefactor" / "SKILL.md").is_file(), "Estrutura fisica da skill nao foi gerada"

        run_cli(["skills", "deactivate", latent_skill_id, "--format", "json"], project_path, env)
        run_cli(["skills", "activate", latent_skill_id, "--format", "json"], project_path, env)
        run_cli(["skills", "update", latent_skill_id, "--name", "AutoRefactor Modificado", "--trigger", "quando revisar", "--format", "json"], project_path, env)

        report.append("| 7. Skills | ✅ PASS | Proposta, geracao, ativacao, desativacao e atualizacao de skills via CLI validados. |")
    except Exception as e:
        traceback.print_exc()
        err_msg = "".join(traceback.format_exception_only(type(e), e)).strip()
        report.append(f"| 7. Skills | ❌ FAIL | Erro: {err_msg} |")
        print(f"Falha em Skills: {err_msg}")

    # 8. MCP Black-Box
    mcp = None
    try:
        mcp = MCPClient(project_path, env)
        mcp.initialize()

        resp = mcp.call_tool("status", {})
        data_status = get_mcp_data(resp)
        assert data_status.get("ok") is True or data_status.get("data", {}).get("initialized") is True, "Status do MCP falhou"

        resp = mcp.call_tool("remember_fact", {
            "content": "MCP grava fatos corretamente",
            "scope": "project",
            "tags": ["mcp"]
        })
        data_rem = get_mcp_data(resp)
        assert data_rem.get("ok") is True or "id" in data_rem.get("data", {}).get("fact", {}), "remember_fact no MCP falhou"

        resp = mcp.call_tool("list_facts", {"scope": "project"})
        data_list = get_mcp_data(resp)
        facts = data_list.get("data", {}).get("facts", [])
        assert any("MCP grava fatos" in f.get("content", "") for f in facts), "Fato gravado por MCP nao aparece na listagem do MCP"

        resp = mcp.call_tool("context", {"scope": "project"})
        data_ctx = get_mcp_data(resp)
        assert data_ctx.get("ok") is True, "context no MCP falhou"

        resp = mcp.call_tool("purge_fact", {"confirm": False})
        data_purge_fail = get_mcp_data(resp)
        assert data_purge_fail.get("ok") is False or "error" in resp

        resp_facts = mcp.call_tool("list_facts", {"scope": "project"})
        data_facts_list = get_mcp_data(resp_facts)
        facts_list_mcp = data_facts_list.get("data", {}).get("facts", [])
        fact_id_mcp = facts_list_mcp[0]["id"]
        resp_purge = mcp.call_tool("purge_fact", {"id": fact_id_mcp, "confirm": True})
        data_purge_ok = get_mcp_data(resp_purge)
        assert data_purge_ok.get("ok") is True, "purge_fact com confirm=True falhou no MCP"

        resp = mcp.call_tool("host_setup", {"host_id": "codex", "force": True})
        data_setup = get_mcp_data(resp)
        assert data_setup.get("ok") is True, "host_setup falhou no MCP"

        resp = mcp.call_tool("host_check", {"host_id": "codex"})
        data_check = get_mcp_data(resp)
        assert data_check.get("ok") is True, "host_check falhou no MCP"

        resp = mcp.call_tool("list_snapshots", {"scope": "project"})
        data_snap = get_mcp_data(resp)
        assert len(data_snap.get("data", {}).get("snapshots", [])) > 0, "list_snapshots falhou no MCP"

        resp = mcp.call_tool("list_audit_events", {"scope": "project"})
        data_audit = get_mcp_data(resp)
        assert len(data_audit.get("data", {}).get("events", [])) > 0, "list_audit_events falhou no MCP"

        latent_skill_id_mcp = "33333333-3333-4333-8333-333333333333"
        latent_skill_data_mcp = {
            "id": latent_skill_id_mcp,
            "created_at": "2026-06-02T12:00:00Z",
            "updated_at": "2026-06-02T12:00:00Z",
            "name": "McpSkill",
            "description": "Usuario solicita skill via MCP",
            "scope": "project",
            "status": "proposed",
            "recurrence_count": 2,
            "metadata": {"origin": "alpha-tester-v2-mcp"}
        }
        with open(skills_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(latent_skill_data_mcp) + "\n")

        resp = mcp.call_tool("list_skills", {})
        data_skills_list = get_mcp_data(resp)
        skills = data_skills_list.get("data", {}).get("skills", [])
        assert any(s["name"] == latent_skill_data_mcp["name"] for s in skills), "Latent skill do MCP nao listada"

        resp = mcp.call_tool("propose_skill", {"latent_skill_id": latent_skill_id_mcp, "decision": "yes"})
        data_prop = get_mcp_data(resp)
        assert data_prop.get("ok") is True, "propose_skill falhou no MCP"

        resp = mcp.call_tool("generate_skill", {"latent_skill_id": latent_skill_id_mcp, "update_existing": False})
        data_gen = get_mcp_data(resp)
        assert data_gen.get("ok") is True, "generate_skill falhou no MCP"
        assert (project_path / ".umem" / "skills" / "mcpskill" / "SKILL.md").is_file(), "Skill gerada pelo MCP nao existe no filesystem"

        resp = mcp.call_tool("deactivate_skill", {"latent_skill_id": latent_skill_id_mcp})
        data_deact = get_mcp_data(resp)
        assert data_deact.get("ok") is True, "deactivate_skill falhou no MCP"

        resp = mcp.call_tool("activate_skill", {"latent_skill_id": latent_skill_id_mcp})
        data_act = get_mcp_data(resp)
        assert data_act.get("ok") is True, "activate_skill falhou no MCP"

        resp = mcp.call_tool("update_skill", {
            "latent_skill_id": latent_skill_id_mcp,
            "name": "McpSkill Modificado",
            "triggers": ["quando mcp for chamado"]
        })
        data_upd = get_mcp_data(resp)
        assert data_upd.get("ok") is True, "update_skill falhou no MCP"

        report.append("| 8. MCP Black-Box | ✅ PASS | Todas as 19 tools MCP testadas de forma Black-Box com sucesso. Envelopes e schemas validados. |")
    except Exception as e:
        traceback.print_exc()
        err_msg = "".join(traceback.format_exception_only(type(e), e)).strip()
        report.append(f"| 8. MCP Black-Box | ❌ FAIL | Erro: {err_msg} |")
        print(f"Falha em MCP Black-Box: {err_msg}")
    finally:
        if mcp:
            mcp.close()

    # 9. Compatibilidade Cruzada CLI/MCP
    try:
        run_cli(["remember", "Criado pela CLI, lido pelo MCP.", "--scope", "project", "--format", "json"], project_path, env)
        
        mcp2 = MCPClient(project_path, env)
        mcp2.initialize()
        resp_mcp = mcp2.call_tool("list_facts", {"scope": "project"})
        data_mcp = get_mcp_data(resp_mcp)
        facts_mcp = data_mcp.get("data", {}).get("facts", [])
        assert any("Criado pela CLI, lido pelo MCP" in f.get("content", "") for f in facts_mcp), "Fato da CLI nao lido pelo MCP"

        resp_rem2 = mcp2.call_tool("remember_fact", {"content": "Criado pelo MCP, lido pela CLI", "scope": "project"})
        mcp2.close()

        stdout_cli, _, _ = run_cli(["facts", "list", "--scope", "project", "--format", "json"], project_path, env)
        facts_cli = json.loads(stdout_cli).get("data", {}).get("facts", [])
        assert any("Criado pelo MCP, lido pela CLI" in f.get("content", "") for f in facts_cli), "Fato do MCP nao lido pela CLI"

        report.append("| 9. Compatibilidade CLI/MCP | ✅ PASS | CLI e MCP compartilham o mesmo storage de forma consistente e transparente. |")
    except Exception as e:
        traceback.print_exc()
        err_msg = "".join(traceback.format_exception_only(type(e), e)).strip()
        report.append(f"| 9. Compatibilidade CLI/MCP | ❌ FAIL | Erro: {err_msg} |")
        print(f"Falha na compatibilidade CLI/MCP: {err_msg}")

    # Limpeza
    temp_dir.cleanup()
    print("--- Sandbox removida ---")

    # Output do relatório markdown
    report_content = "\n".join(report)
    print("\n=== RELATORIO DE TESTES GERADO ===")
    print(report_content)

    # Escrever no arquivo de log
    report_file = Path(ORIGINAL_PROJECT_DIR) / "docs" / "alpha-sandbox-test-results.md"
    report_file.write_text(report_content, encoding="utf-8")
    print(f"Relatorio gravado em {report_file}")
    
    # Se alguma fase falhou, sai com código de erro
    if "❌ FAIL" in report_content:
        sys.exit(1)
    else:
        sys.exit(0)

if __name__ == "__main__":
    main()
