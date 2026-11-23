"""Resolve the effective scope of an adapter command without mutation."""

from collections.abc import Callable
from typing import Any


def operation_scope(handler: Callable[..., Any], command: Any) -> str | None:
    scope = getattr(command, "scope", None)
    if scope is not None:
        return getattr(scope, "value", scope)
    owner = getattr(handler, "__self__", None)
    identifier = next(
        (
            getattr(command, key)
            for key in (
                "latent_skill_id",
                "recommendation_id",
                "skill_id_or_name",
                "draft_or_path",
                "id",
            )
            if getattr(command, key, None)
        ),
        None,
    )
    if not identifier:
        return None
    for key in ("repository", "recommendation_repository", "fact_repository"):
        repository = getattr(owner, key, None)
        if repository is None:
            continue
        for entity in repository.list():
            if identifier in (
                entity.id,
                getattr(entity, "name", None),
                getattr(entity, "slug", None),
                getattr(entity, "canonical_path", None),
            ):
                return entity.scope.value
    return None
