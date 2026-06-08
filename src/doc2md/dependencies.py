"""Dependency checking and on-demand installation for doc2md."""

from __future__ import annotations

import importlib.util
import subprocess
import sys
import tempfile
from collections.abc import Callable, Iterable
from pathlib import Path

from .models import MANUAL_INSTALL_COMMAND, Dependency


class DependencyManager:
    """Checks and optionally installs pip dependencies without blocking the GUI."""

    def __init__(self, dependencies: list[Dependency]) -> None:
        self.dependencies = dependencies

    def is_installed(self, dependency: Dependency) -> bool:
        return importlib.util.find_spec(dependency.import_name) is not None

    def get_missing_dependencies(self) -> list[Dependency]:
        return [dependency for dependency in self.dependencies if not self.is_installed(dependency)]

    def get_status_lines(self) -> list[str]:
        lines: list[str] = []
        for dependency in self.dependencies:
            state = "installed" if self.is_installed(dependency) else "missing"
            lines.append(
                f"Dependency status: {dependency.display_name} is {state} "
                f"({dependency.required_for})."
            )
        return lines

    @staticmethod
    def format_dependency_list(dependencies: Iterable[Dependency]) -> str:
        return "\n".join(
            f"- {dependency.display_name} ({dependency.package_name}) for {dependency.required_for}"
            for dependency in dependencies
        )

    def install_missing_dependencies(
        self,
        dependencies: Iterable[Dependency],
        log_callback: Callable[[str], None],
    ) -> tuple[bool, str, list[Dependency]]:
        failures: list[str] = []

        for dependency in dependencies:
            command = [sys.executable, "-m", "pip", "install", dependency.package_name]
            log_callback(
                f"Installing dependency: {dependency.display_name} with command: "
                f"{' '.join(command)}"
            )

            with tempfile.NamedTemporaryFile("w", delete=False, encoding="utf-8", suffix=".log") as temp_file:
                temp_log_path = Path(temp_file.name)

            try:
                with temp_log_path.open("w", encoding="utf-8", errors="replace") as handle:
                    subprocess.check_call(command, stdout=handle, stderr=handle)
                log_callback(f"Dependency installed successfully: {dependency.display_name}")
            except subprocess.CalledProcessError as exc:
                details = temp_log_path.read_text(encoding="utf-8", errors="replace").strip()
                failure_message = self._build_install_failure_message(
                    dependency=dependency,
                    return_code=exc.returncode,
                    details=details,
                )
                failures.append(failure_message)
                log_callback(failure_message)
            except Exception as exc:
                failure_message = (
                    f"Unexpected error while installing {dependency.display_name}: {exc}\n"
                    f"You can install dependencies manually with:\n{MANUAL_INSTALL_COMMAND}"
                )
                failures.append(failure_message)
                log_callback(failure_message)
            finally:
                try:
                    temp_log_path.unlink(missing_ok=True)
                except OSError:
                    pass

        remaining_missing = self.get_missing_dependencies()
        if remaining_missing:
            message = (
                "Dependency installation finished with missing packages still present.\n"
                f"Remaining missing dependencies:\n{self.format_dependency_list(remaining_missing)}\n\n"
                f"Manual installation command:\n{MANUAL_INSTALL_COMMAND}"
            )
            if failures:
                message = f"{message}\n\nDetailed failures were written to the log."
            return False, message, remaining_missing

        return True, "All requested dependencies are installed and ready to use.", []

    @staticmethod
    def _build_install_failure_message(dependency: Dependency, return_code: int, details: str) -> str:
        lines = [
            f"Failed to install {dependency.display_name} ({dependency.package_name}).",
            f"pip exited with code {return_code}.",
        ]

        lower_details = details.lower()
        if "permission denied" in lower_details or "access is denied" in lower_details:
            lines.append(
                "Permission-related failure detected. Try running inside a virtual environment, "
                "or install manually with:"
            )
            lines.append(MANUAL_INSTALL_COMMAND)
        else:
            lines.append("You can install dependencies manually with:")
            lines.append(MANUAL_INSTALL_COMMAND)

        if details:
            lines.append("pip details:")
            lines.append(details)

        return "\n".join(lines)
