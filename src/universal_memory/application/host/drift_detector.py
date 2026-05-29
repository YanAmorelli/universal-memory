from __future__ import annotations

import re


class InstructionDriftDetector:
    def detect(self, *, agents_content: str, claude_content: str) -> list[str]:
        if not agents_content or not claude_content:
            return []
        agents_lines = _instruction_lines(agents_content)
        claude_lines = _instruction_lines(claude_content)
        warnings: list[str] = []

        agents_by_normalized = {_normalize_line(line): line for line in agents_lines}
        for claude_line in claude_lines:
            normalized = _normalize_line(claude_line)
            if normalized in agents_by_normalized:
                warnings.append(
                    "Instrucao duplicada em AGENTS.md e CLAUDE.md: "
                    f"{agents_by_normalized[normalized]}"
                )

        contradiction_warnings = _detect_always_never_contradictions(
            agents_lines,
            claude_lines,
        )
        warnings.extend(contradiction_warnings)
        return warnings


def _instruction_lines(content: str) -> list[str]:
    lines: list[str] = []
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if not line or "<!--" in line or "-->" in line or line.startswith(("#", ">")):
            continue
        line = re.sub(r"^[-*]\s*", "", line)
        line = re.sub(r"^\([a-z_-]+\)\s*", "", line).strip()
        if line:
            lines.append(line)
    return lines


def _normalize_line(line: str) -> str:
    return re.sub(r"\s+", " ", line).strip().rstrip(".").casefold()


def _detect_always_never_contradictions(
    agents_lines: list[str],
    claude_lines: list[str],
) -> list[str]:
    warnings: list[str] = []
    agents_norms = [_normalize_line(line) for line in agents_lines]
    agents_rules = {}
    for line, norm in zip(agents_lines, agents_norms, strict=True):
        if _rule_polarity(norm):
            body = _rule_body(norm)
            if body:
                agents_rules[body] = (line, norm)

    for claude_line in claude_lines:
        norm = _normalize_line(claude_line)
        claude_polarity = _rule_polarity(norm)
        if claude_polarity is None:
            continue
        body = _rule_body(norm)
        if not body:
            continue
        matched = agents_rules.get(body)
        if matched is None:
            continue
        agents_line, agents_norm = matched
        agents_polarity = _rule_polarity(agents_norm)
        if agents_polarity != claude_polarity:
            warnings.append(
                "Contradicao explicita entre AGENTS.md e CLAUDE.md: "
                f"{agents_line} / {claude_line}"
            )
    return warnings


def _rule_polarity(normalized: str) -> str | None:
    if normalized.startswith(("always ", "sempre ")):
        return "positive"
    if normalized.startswith(("never ", "nunca ")):
        return "negative"
    return None


def _rule_body(normalized: str) -> str:
    for prefix in ("always ", "never ", "sempre ", "nunca "):
        if normalized.startswith(prefix):
            return normalized.removeprefix(prefix)
    return normalized
