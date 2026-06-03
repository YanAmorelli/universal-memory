from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class SafeWriteResult:
    relative_path: str
    audit_reference: str
    snapshot_reference: str
