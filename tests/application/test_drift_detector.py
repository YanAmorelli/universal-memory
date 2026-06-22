from universal_memory.application.host.drift_detector import InstructionDriftDetector


def test_drift_detector_warns_about_duplicate_instruction_lines() -> None:
    warnings = InstructionDriftDetector().detect(
        agents_content="""
<!-- UMEM: START -->
- (shared_policy) Use relative paths in specs, code and docs.
<!-- UMEM: END -->
""",
        claude_content="""
<!-- UMEM: START -->
- (provider_delta) Use relative paths in specs, code and docs.
<!-- UMEM: END -->
""",
    )

    assert warnings == [
        "Duplicate instruction in AGENTS.md and CLAUDE.md: "
        "Use relative paths in specs, code and docs."
    ]


def test_drift_detector_warns_about_explicit_always_never_contradictions() -> None:
    warnings = InstructionDriftDetector().detect(
        agents_content="""
<!-- UMEM: START -->
- (shared_policy) Always run tests before review.
<!-- UMEM: END -->
""",
        claude_content="""
<!-- UMEM: START -->
- (provider_delta) Never run tests before review.
<!-- UMEM: END -->
""",
    )

    assert warnings == [
        "Explicit contradiction between AGENTS.md and CLAUDE.md: "
        "Always run tests before review. / Never run tests before review."
    ]
