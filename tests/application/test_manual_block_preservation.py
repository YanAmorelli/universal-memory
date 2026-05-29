from universal_memory.application.host.setup_host_use_case import ConfigureHostUseCase


def test_merge_managed_block_preserves_user_sections_around_umem_block() -> None:
    use_case = ConfigureHostUseCase.__new__(ConfigureHostUseCase)
    existing = (
        "# Manual heading\n\n"
        "Keep this.\n\n"
        "<!-- UMEM: START -->\n"
        "old generated block\n"
        "<!-- UMEM: END -->\n\n"
        "Tail note.\n"
    )
    managed = "<!-- UMEM: START -->\n" "# Universal Memory Active Policy\n" "<!-- UMEM: END -->\n"

    merged = use_case._merge_managed_block(existing, managed)

    assert merged.startswith("# Manual heading\n\nKeep this.\n\n")
    assert merged.endswith("Tail note.\n")
    assert "old generated block" not in merged
    assert "# Universal Memory Active Policy" in merged
