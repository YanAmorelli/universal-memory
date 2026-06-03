import universal_memory


def test_package_imports_and_exposes_version() -> None:
    assert hasattr(universal_memory, "__version__")
    assert isinstance(universal_memory.__version__, str)
    assert universal_memory.__version__ != ""
