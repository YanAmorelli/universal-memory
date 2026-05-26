import math
import re
from collections import Counter
from re import Pattern
from typing import ClassVar

from universal_memory.domain.exceptions import SecretDetectedError
from universal_memory.domain.ports import SecretScannerPort


class EntropySecretScanner(SecretScannerPort):
    _KNOWN_PATTERNS: tuple[tuple[str, Pattern[str]], ...] = (
        ("aws_access_key", re.compile(r"\b(?:A3T|AKIA|ASIA|AGPA|AIDA)[A-Z0-9]{16}\b")),
        ("github_pat", re.compile(r"\bgh[pousr]_[A-Za-z0-9_]{36,255}\b")),
        ("bearer_token", re.compile(r"\bBearer\s+([A-Za-z0-9._~+/=-]{20,})\b", re.IGNORECASE)),
        (
            "sensitive_assignment",
            re.compile(
                r"\b(?:API_KEY|SECRET|TOKEN|PASSWORD)\b\s*=\s*['\"]?([^\s'\"#]{10,})",
                re.IGNORECASE,
            ),
        ),
    )
    _CANDIDATE_PATTERN = re.compile(r"\b[A-Za-z0-9._~+/=-]{20,}\b")
    _UUID_PATTERN = re.compile(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-"
        r"[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"
    )
    _PLACEHOLDER_VALUES: ClassVar[set[str]] = {
        "changeme",
        "example",
        "not-a-secret",
        "placeholder",
        "your_api_key_here",
    }

    def __init__(self, entropy_threshold: float = 4.5, min_token_length: int = 28) -> None:
        self.entropy_threshold = entropy_threshold
        self.min_token_length = min_token_length

    def scan(self, content: str, *, origin: str | None = None) -> None:
        for pattern_name, pattern in self._KNOWN_PATTERNS:
            match = pattern.search(content)
            if match is None:
                continue

            if pattern_name == "sensitive_assignment" and self._is_placeholder(match.group(1)):
                continue

            raise self._error(
                detection_type="pattern",
                pattern=pattern_name,
                span=(match.start(), match.end()),
                origin=origin,
            )

        for match in self._CANDIDATE_PATTERN.finditer(content):
            token = match.group(0)
            if len(token) < self.min_token_length or self._is_common_non_secret(token):
                continue

            entropy = self._shannon_entropy(token)
            if entropy <= self.entropy_threshold:
                continue

            raise self._error(
                detection_type="entropy",
                pattern="generic_high_entropy",
                span=(match.start(), match.end()),
                origin=origin,
                entropy=entropy,
            )

    def _error(
        self,
        *,
        detection_type: str,
        pattern: str,
        span: tuple[int, int],
        origin: str | None,
        entropy: float | None = None,
    ) -> SecretDetectedError:
        metadata: dict[str, object] = {
            "detection_type": detection_type,
            "pattern": pattern,
            "span": span,
            "hint": "Remove the sensitive value before persisting this content.",
        }
        if origin is not None:
            metadata["origin"] = origin
        if entropy is not None:
            metadata["entropy"] = round(entropy, 3)

        return SecretDetectedError("Secret detected; persistence was blocked.", metadata)

    def _is_common_non_secret(self, token: str) -> bool:
        normalized = token.lower()
        return (
            self._UUID_PATTERN.fullmatch(token) is not None
            or self._is_placeholder(token)
            or "/" in token
            or normalized.endswith((".md", ".toml", ".yaml", ".yml", ".json"))
        )

    def _is_placeholder(self, value: str) -> bool:
        normalized = value.strip("'\"").lower()
        return normalized in self._PLACEHOLDER_VALUES or "placeholder" in normalized

    def _shannon_entropy(self, value: str) -> float:
        counts = Counter(value)
        length = len(value)
        return -sum((count / length) * math.log2(count / length) for count in counts.values())
