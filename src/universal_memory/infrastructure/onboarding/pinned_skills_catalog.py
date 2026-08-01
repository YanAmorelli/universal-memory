from __future__ import annotations

from dataclasses import dataclass
from types import MappingProxyType

from universal_memory.application.skills.official_skill_distribution import (
    OFFICIAL_SKILLS_CLI_PACKAGE,
)


@dataclass(frozen=True, slots=True)
class PinnedSkillsAgent:
    display_name: str
    project_skills_directory: str

    @property
    def instruction_target(self) -> str:
        return f"{self.project_skills_directory}/universal-memory/SKILL.md"


# Reviewed against the agent catalog shipped by the exact package pin below. Updating the
# package and this table is one atomic compatibility change.
PINNED_SKILLS_CATALOG_PACKAGE = "skills@1.5.20"
if PINNED_SKILLS_CATALOG_PACKAGE != OFFICIAL_SKILLS_CLI_PACKAGE:
    raise RuntimeError("The external agent catalog and skills CLI pin must be updated together.")

PINNED_SKILLS_AGENTS = MappingProxyType(
    {
        "adal": PinnedSkillsAgent("AdaL", ".adal/skills"),
        "aider-desk": PinnedSkillsAgent("AiderDesk", ".aider-desk/skills"),
        "amp": PinnedSkillsAgent("Amp", ".agents/skills"),
        "antigravity": PinnedSkillsAgent("Antigravity", ".agents/skills"),
        "antigravity-cli": PinnedSkillsAgent("Antigravity CLI", ".agents/skills"),
        "astrbot": PinnedSkillsAgent("AstrBot", "data/skills"),
        "augment": PinnedSkillsAgent("Augment", ".augment/skills"),
        "autohand-code": PinnedSkillsAgent("Autohand Code CLI", ".autohand/skills"),
        "bob": PinnedSkillsAgent("IBM Bob", ".bob/skills"),
        "claude-code": PinnedSkillsAgent("Claude Code", ".claude/skills"),
        "cline": PinnedSkillsAgent("Cline", ".agents/skills"),
        "codearts-agent": PinnedSkillsAgent("CodeArts Agent", ".codeartsdoer/skills"),
        "codebuddy": PinnedSkillsAgent("CodeBuddy", ".codebuddy/skills"),
        "codemaker": PinnedSkillsAgent("Codemaker", ".codemaker/skills"),
        "codestudio": PinnedSkillsAgent("Code Studio", ".codestudio/skills"),
        "codex": PinnedSkillsAgent("Codex", ".agents/skills"),
        "command-code": PinnedSkillsAgent("Command Code", ".commandcode/skills"),
        "continue": PinnedSkillsAgent("Continue", ".continue/skills"),
        "cortex": PinnedSkillsAgent("Cortex Code", ".cortex/skills"),
        "crush": PinnedSkillsAgent("Crush", ".crush/skills"),
        "cursor": PinnedSkillsAgent("Cursor", ".agents/skills"),
        "deepagents": PinnedSkillsAgent("Deep Agents", ".agents/skills"),
        "devin": PinnedSkillsAgent("Devin for Terminal", ".devin/skills"),
        "dexto": PinnedSkillsAgent("Dexto", ".agents/skills"),
        "droid": PinnedSkillsAgent("Droid", ".factory/skills"),
        "eve": PinnedSkillsAgent("Eve", "agent/skills"),
        "firebender": PinnedSkillsAgent("Firebender", ".agents/skills"),
        "forgecode": PinnedSkillsAgent("ForgeCode", ".forge/skills"),
        "gemini-cli": PinnedSkillsAgent("Gemini CLI", ".agents/skills"),
        "github-copilot": PinnedSkillsAgent("GitHub Copilot", ".agents/skills"),
        "goose": PinnedSkillsAgent("Goose", ".goose/skills"),
        "grok": PinnedSkillsAgent("Grok Build", ".grok/skills"),
        "hermes-agent": PinnedSkillsAgent("Hermes Agent", ".hermes/skills"),
        "iflow-cli": PinnedSkillsAgent("iFlow CLI", ".iflow/skills"),
        "inference-sh": PinnedSkillsAgent("inference.sh", ".inferencesh/skills"),
        "jazz": PinnedSkillsAgent("Jazz", ".jazz/skills"),
        "junie": PinnedSkillsAgent("Junie", ".junie/skills"),
        "kilo": PinnedSkillsAgent("Kilo Code", ".kilocode/skills"),
        "kimchi": PinnedSkillsAgent("Kimchi", ".kimchi/skills"),
        "kimi-code-cli": PinnedSkillsAgent("Kimi Code CLI", ".agents/skills"),
        "kiro-cli": PinnedSkillsAgent("Kiro CLI", ".kiro/skills"),
        "kode": PinnedSkillsAgent("Kode", ".kode/skills"),
        "lingma": PinnedSkillsAgent("Lingma", ".lingma/skills"),
        "loaf": PinnedSkillsAgent("Loaf", ".agents/skills"),
        "mcpjam": PinnedSkillsAgent("MCPJam", ".mcpjam/skills"),
        "mistral-vibe": PinnedSkillsAgent("Mistral Vibe", ".vibe/skills"),
        "moxby": PinnedSkillsAgent("Moxby", ".moxby/skills"),
        "mux": PinnedSkillsAgent("Mux", ".mux/skills"),
        "neovate": PinnedSkillsAgent("Neovate", ".neovate/skills"),
        "ona": PinnedSkillsAgent("Ona", ".ona/skills"),
        "openclaw": PinnedSkillsAgent("OpenClaw", "skills"),
        "opencode": PinnedSkillsAgent("OpenCode", ".agents/skills"),
        "openhands": PinnedSkillsAgent("OpenHands", ".openhands/skills"),
        "pi": PinnedSkillsAgent("Pi", ".pi/skills"),
        "pochi": PinnedSkillsAgent("Pochi", ".pochi/skills"),
        "promptscript": PinnedSkillsAgent("PromptScript", ".agents/skills"),
        "qoder": PinnedSkillsAgent("Qoder", ".qoder/skills"),
        "qoder-cn": PinnedSkillsAgent("Qoder CN", ".qoder/skills"),
        "qwen-code": PinnedSkillsAgent("Qwen Code", ".qwen/skills"),
        "reasonix": PinnedSkillsAgent("Reasonix", ".reasonix/skills"),
        "replit": PinnedSkillsAgent("Replit", ".agents/skills"),
        "roo": PinnedSkillsAgent("Roo Code", ".roo/skills"),
        "rovodev": PinnedSkillsAgent("Rovo Dev", ".rovodev/skills"),
        "tabnine-cli": PinnedSkillsAgent("Tabnine CLI", ".tabnine/agent/skills"),
        "terramind": PinnedSkillsAgent("Terramind", ".terramind/skills"),
        "tinycloud": PinnedSkillsAgent("Tinycloud", ".tinycloud/skills"),
        "trae": PinnedSkillsAgent("Trae", ".trae/skills"),
        "trae-cn": PinnedSkillsAgent("Trae CN", ".trae/skills"),
        "universal": PinnedSkillsAgent("Universal", ".agents/skills"),
        "warp": PinnedSkillsAgent("Warp", ".agents/skills"),
        "windsurf": PinnedSkillsAgent("Windsurf", ".windsurf/skills"),
        "zcode": PinnedSkillsAgent("ZCode", ".zcode/skills"),
        "zed": PinnedSkillsAgent("Zed", ".agents/skills"),
        "zencoder": PinnedSkillsAgent("Zencoder", ".zencoder/skills"),
        "zenflow": PinnedSkillsAgent("Zenflow", ".zencoder/skills"),
    }
)
