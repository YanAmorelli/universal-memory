import inspect
from abc import ABC
from collections.abc import Callable
from typing import get_type_hints

import pytest

from universal_memory.domain.entities import (
    AuditEvent,
    AuditEventScope,
    ContextSummary,
    ContextSummaryScope,
    Fact,
    FactScope,
    FactStatus,
    LatentSkill,
    LatentSkillScope,
    LatentSkillStatus,
    Rule,
    RuleScope,
    RuleStatus,
    Snapshot,
    SnapshotScope,
    SnapshotStatus,
)
from universal_memory.domain.ports import (
    AuditLogRepository,
    ContextSummaryRepository,
    FactRepository,
    LatentSkillRepository,
    RuleRepository,
    SnapshotRepository,
)

PortType = type[ABC]
type MethodExpectations = dict[str, tuple[object, dict[str, object]]]


EXPECTED_METHODS: dict[PortType, MethodExpectations] = {
    FactRepository: {
        "read": (Fact, {"id": str}),
        "list": (list[Fact], {"scope": FactScope | None, "status": FactStatus | None}),
        "write": (type(None), {"entity": Fact}),
        "delete": (type(None), {"id": str}),
        "purge": (type(None), {"id": str}),
        "migrate": (type(None), {"target_version": int}),
    },
    RuleRepository: {
        "read": (Rule, {"id": str}),
        "list": (list[Rule], {"scope": RuleScope | None, "status": RuleStatus | None}),
        "write": (type(None), {"entity": Rule}),
        "delete": (type(None), {"id": str}),
        "migrate": (type(None), {"target_version": int}),
    },
    LatentSkillRepository: {
        "read": (LatentSkill, {"id": str}),
        "list": (
            list[LatentSkill],
            {"scope": LatentSkillScope | None, "status": LatentSkillStatus | None},
        ),
        "write": (type(None), {"entity": LatentSkill}),
        "delete": (type(None), {"id": str}),
        "migrate": (type(None), {"target_version": int}),
    },
    SnapshotRepository: {
        "read": (Snapshot, {"id": str}),
        "list": (list[Snapshot], {"scope": SnapshotScope | None, "status": SnapshotStatus | None}),
        "write": (type(None), {"entity": Snapshot}),
        "migrate": (type(None), {"target_version": int}),
    },
    AuditLogRepository: {
        "read": (AuditEvent, {"id": str}),
        "list": (list[AuditEvent], {"scope": AuditEventScope | None}),
        "write": (type(None), {"entity": AuditEvent}),
        "migrate": (type(None), {"target_version": int}),
    },
    ContextSummaryRepository: {
        "read": (ContextSummary, {"id": str}),
        "list": (list[ContextSummary], {"scope": ContextSummaryScope | None}),
        "write": (type(None), {"entity": ContextSummary}),
        "migrate": (type(None), {"target_version": int}),
    },
}


@pytest.mark.parametrize("port_type", EXPECTED_METHODS)
def test_ports_are_abstract_and_not_directly_instantiable(port_type: PortType) -> None:
    assert inspect.isabstract(port_type)

    with pytest.raises(TypeError):
        port_type()


@pytest.mark.parametrize(("port_type", "methods"), EXPECTED_METHODS.items())
def test_ports_expose_abstract_methods_with_typed_signatures(
    port_type: PortType, methods: MethodExpectations
) -> None:
    assert port_type.__abstractmethods__ == frozenset(methods)

    for method_name, (expected_return, expected_parameters) in methods.items():
        method = getattr(port_type, method_name)
        assert isinstance(method, Callable)
        assert inspect.getattr_static(method, "__isabstractmethod__") is True

        signature = inspect.signature(method)
        hints = get_type_hints(method)

        assert "return" in hints, f"Method '{method_name}' lacks return type annotation"
        assert hints["return"] == expected_return
        assert next(iter(signature.parameters)) == "self"

        for parameter_name, expected_type in expected_parameters.items():
            assert parameter_name in signature.parameters, (
                f"Missing parameter '{parameter_name}' in method '{method_name}'"
            )
            assert parameter_name in hints, (
                f"Missing type hint for parameter '{parameter_name}' in method '{method_name}'"
            )
            parameter = signature.parameters[parameter_name]
            assert parameter.kind is inspect.Parameter.POSITIONAL_OR_KEYWORD
            assert hints[parameter_name] == expected_type

        optional_filters = {"scope", "status"} & set(expected_parameters)
        for parameter_name in optional_filters:
            assert signature.parameters[parameter_name].default is None
