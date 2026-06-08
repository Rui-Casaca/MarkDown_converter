"""Unit tests for :mod:`doc2md.dependencies`."""

from __future__ import annotations

from doc2md.dependencies import DependencyManager
from doc2md.models import Dependency

INSTALLED = Dependency(
    display_name="pathlib",
    import_name="pathlib",
    package_name="pathlib",
    required_for="standard library",
)
MISSING = Dependency(
    display_name="Made Up Package",
    import_name="doc2md_nonexistent_module_xyz",
    package_name="doc2md-nonexistent",
    required_for="testing",
)


class TestIsInstalled:
    def test_installed_module(self) -> None:
        manager = DependencyManager([INSTALLED])
        assert manager.is_installed(INSTALLED) is True

    def test_missing_module(self) -> None:
        manager = DependencyManager([MISSING])
        assert manager.is_installed(MISSING) is False


class TestGetMissingDependencies:
    def test_only_returns_missing(self) -> None:
        manager = DependencyManager([INSTALLED, MISSING])
        assert manager.get_missing_dependencies() == [MISSING]

    def test_empty_when_all_present(self) -> None:
        manager = DependencyManager([INSTALLED])
        assert manager.get_missing_dependencies() == []


class TestFormatDependencyList:
    def test_formats_each_entry(self) -> None:
        result = DependencyManager.format_dependency_list([MISSING])
        assert result == "- Made Up Package (doc2md-nonexistent) for testing"

    def test_empty_iterable(self) -> None:
        assert DependencyManager.format_dependency_list([]) == ""


class TestGetStatusLines:
    def test_reports_states(self) -> None:
        manager = DependencyManager([INSTALLED, MISSING])
        lines = manager.get_status_lines()
        assert "pathlib is installed" in lines[0]
        assert "Made Up Package is missing" in lines[1]
