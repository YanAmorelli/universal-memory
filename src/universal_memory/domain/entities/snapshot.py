from datetime import datetime
from enum import StrEnum
from pathlib import PurePosixPath

from pydantic import Field, field_validator

from universal_memory.domain.entities.base import BaseEntity, validate_utc_datetime


class SnapshotScope(StrEnum):
    global_ = "global"
    project = "project"


class SnapshotStatus(StrEnum):
    created = "created"
    restored = "restored"
    failed = "failed"


class Snapshot(BaseEntity):
    timestamp: datetime
    scope: SnapshotScope
    origin: str = "unknown"
    action: str
    relative_path: str
    hash: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    previous_file_existed: bool = True
    status: SnapshotStatus

    @field_validator("timestamp")
    @classmethod
    def validate_timestamp_utc(cls, value: datetime) -> datetime:
        return validate_utc_datetime(value)

    @field_validator("relative_path")
    @classmethod
    def validate_relative_path(cls, value: str) -> str:
        path = PurePosixPath(value)
        if not value or path.is_absolute() or ".." in path.parts:
            raise ValueError("relative_path must be relative and must not contain traversal")
        return value
