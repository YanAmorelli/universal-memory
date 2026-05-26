import uuid
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, field_validator

UUID_V4_VERSION = 4


def validate_uuid_v4_string(value: str) -> str:
    try:
        parsed = uuid.UUID(value)
    except ValueError as exc:
        raise ValueError("value must be a valid UUID v4 string") from exc

    if parsed.version != UUID_V4_VERSION:
        raise ValueError("value must be a valid UUID v4 string")
    return value


def validate_utc_datetime(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() != UTC.utcoffset(value):
        raise ValueError("datetime must be timezone-aware UTC")
    return value


class BaseEntity(BaseModel):
    schema_version: Literal[1] = 1
    id: str
    created_at: datetime
    updated_at: datetime

    @field_validator("id")
    @classmethod
    def validate_uuid_v4(cls, value: str) -> str:
        return validate_uuid_v4_string(value)

    @field_validator("created_at", "updated_at")
    @classmethod
    def validate_utc_timestamps(cls, value: datetime) -> datetime:
        return validate_utc_datetime(value)


def format_utc_iso(value: datetime) -> str:
    normalized = value if value.tzinfo is not None else value.replace(tzinfo=UTC)
    return normalized.astimezone(UTC).isoformat().replace("+00:00", "Z")

