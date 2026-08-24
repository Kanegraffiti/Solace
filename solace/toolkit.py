"""Stable bridge between Solace and the optional Termux Toolkit."""

from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass
from typing import Callable, List, Optional, Sequence

TOOL_NAME = re.compile(r"^[a-z0-9][a-z0-9-]*$")


class ToolkitUnavailable(RuntimeError):
    """Raised when the Termux Toolkit command cannot be found."""


@dataclass(frozen=True)
class ToolkitResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


class ToolkitClient:
    """Discover and invoke Termux Toolkit through its public ``ttk`` CLI."""

    def __init__(
        self,
        executable: Optional[str] = None,
        *,
        runner: Callable[..., subprocess.CompletedProcess] = subprocess.run,
    ) -> None:
        self.executable = executable or shutil.which("ttk")
        self._runner = runner

    @property
    def available(self) -> bool:
        return bool(self.executable)

    def _call(self, arguments: Sequence[str], *, capture: bool = True) -> ToolkitResult:
        if not self.executable:
            raise ToolkitUnavailable(
                "Termux Toolkit is not installed or 'ttk' is not on PATH."
            )
        completed = self._runner(
            [self.executable, *arguments],
            text=True,
            capture_output=capture,
            check=False,
        )
        return ToolkitResult(
            completed.returncode,
            completed.stdout or "",
            completed.stderr or "",
        )

    def root(self) -> str:
        result = self._call(["root"])
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Could not locate Termux Toolkit.")
        return result.stdout.strip()

    def version(self) -> str:
        result = self._call(["version"])
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Could not read toolkit version.")
        return result.stdout.strip()

    def list_tools(self) -> List[str]:
        result = self._call(["list"])
        if result.returncode:
            raise RuntimeError(result.stderr.strip() or "Could not list toolkit commands.")
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def has(self, tool: str) -> bool:
        if not TOOL_NAME.fullmatch(tool):
            return False
        return self._call(["has", tool]).returncode == 0

    def run(self, tool: str, arguments: Sequence[str] = ()) -> ToolkitResult:
        if not TOOL_NAME.fullmatch(tool):
            raise ValueError(f"Invalid toolkit command name: {tool}")
        if not self.has(tool):
            raise KeyError(f"Toolkit command '{tool}' is not installed.")
        # Inherit the terminal streams so interactive toolkit tools can prompt.
        return self._call(["run", tool, *arguments], capture=False)

    def man(self, arguments: Sequence[str] = ()) -> ToolkitResult:
        # Manuals are also allowed to use the active terminal pager/output.
        return self._call(["man", *arguments], capture=False)
