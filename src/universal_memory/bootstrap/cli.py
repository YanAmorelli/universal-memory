from collections.abc import Sequence

from universal_memory.infrastructure.config import (
    LocalConfigValidationPort,
    LocalProjectLayoutPort,
)
from universal_memory.interfaces.cli import build_main

_main = build_main(
    layout_port=LocalProjectLayoutPort(),
    config_validation_port=LocalConfigValidationPort(),
)


def main(argv: Sequence[str] | None = None) -> int:
    return _main(argv)
