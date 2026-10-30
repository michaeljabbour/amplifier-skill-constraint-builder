"""Local tool executor for the pico runtime.

Explicit file-tool path arguments are resolved against project_root. The bash
method intentionally executes trusted caller shell commands with project_root
as cwd; the separate constraint gate must mediate dispatch. It does not contain the command's paths, subprocesses, network
or inherited credentials. A working directory is not an OS sandbox. Deploy an
independent tested boundary before running untrusted commands or checker code.

Dependencies: stdlib only (subprocess, pathlib, os, re).
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path


class LocalToolExecutor:
    """Executes tools within a project_root boundary.

    Explicit file-tool path arguments reject resolved paths outside the root.
    bash(command) is a trusted-code interface with ordinary process privileges;
    setting cwd does not constrain the shell program to that directory.

    Usage::

        executor = LocalToolExecutor("/path/to/project")
        content = executor.read_file("src/main.py")
    """

    def __init__(self, project_root: str) -> None:
        self._project_root = os.path.realpath(project_root)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve(self, path: str) -> str:
        """Resolve *path* and verify it is inside *project_root*.

        Args:
            path: Absolute or relative path.

        Returns:
            The resolved absolute path string.

        Raises:
            PermissionError: If the resolved path is outside project_root.
        """
        if os.path.isabs(path):
            resolved = os.path.realpath(path)
        else:
            resolved = os.path.realpath(os.path.join(self._project_root, path))

        if resolved == self._project_root or resolved.startswith(
            self._project_root + os.sep
        ):
            return resolved

        raise PermissionError(
            f"Path resolves outside project root: {path!r} -> {resolved!r} "
            f"(project_root: {self._project_root!r})"
        )

    # ------------------------------------------------------------------
    # read_file
    # ------------------------------------------------------------------

    def read_file(self, file_path: str) -> str:
        """Read a file's contents.

        Args:
            file_path: Path to read (absolute or relative to project_root).

        Returns:
            File contents as a string.

        Raises:
            PermissionError: Path outside project_root.
            FileNotFoundError: File doesn't exist.
        """
        resolved = self._resolve(file_path)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"File not found: {resolved}")
        with open(resolved) as f:
            return f.read()

    # ------------------------------------------------------------------
    # write_file
    # ------------------------------------------------------------------

    def write_file(self, file_path: str, content: str) -> str:
        """Write content to a file, creating parent directories as needed.

        Args:
            file_path: Path to write (absolute or relative to project_root).
            content: String content to write.

        Returns:
            Confirmation message.

        Raises:
            PermissionError: Path outside project_root.
        """
        resolved = self._resolve(file_path)
        os.makedirs(os.path.dirname(resolved), exist_ok=True)
        with open(resolved, "w") as f:
            f.write(content)
        return f"Wrote {len(content)} bytes to {resolved}"

    # ------------------------------------------------------------------
    # edit_file
    # ------------------------------------------------------------------

    def edit_file(self, file_path: str, old_string: str, new_string: str) -> str:
        """Replace a string in a file (first occurrence only).

        Args:
            file_path: Path to edit.
            old_string: Exact string to find and replace.
            new_string: Replacement string.

        Returns:
            Confirmation message.

        Raises:
            PermissionError: Path outside project_root.
            FileNotFoundError: File doesn't exist.
            ValueError: old_string not found in file.
        """
        resolved = self._resolve(file_path)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"File not found: {resolved}")
        with open(resolved) as f:
            content = f.read()
        if old_string not in content:
            raise ValueError(f"String not found in {resolved}: {old_string!r}")
        new_content = content.replace(old_string, new_string, 1)
        with open(resolved, "w") as f:
            f.write(new_content)
        return f"Replaced in {resolved}"

    # ------------------------------------------------------------------
    # apply_patch
    # ------------------------------------------------------------------

    def apply_patch(self, file_path: str, patch: str) -> str:
        """Apply a unified diff patch to a file.

        Applies a text patch in unified-diff format.  For simple use-cases
        (single-hunk patches) the patch is applied in pure Python without
        requiring the ``patch`` binary.

        Args:
            file_path: Path to patch (absolute or relative to project_root).
            patch: Unified diff string.

        Returns:
            Confirmation message.

        Raises:
            PermissionError: Path outside project_root.
            FileNotFoundError: File doesn't exist.
            ValueError: Patch cannot be applied cleanly.
        """
        resolved = self._resolve(file_path)
        if not os.path.isfile(resolved):
            raise FileNotFoundError(f"File not found: {resolved}")

        # Attempt to apply via subprocess patch(1) if available
        try:
            result = subprocess.run(
                ["patch", "--quiet", resolved],
                input=patch,
                capture_output=True,
                text=True,
                timeout=15,
            )
            if result.returncode == 0:
                return f"Patch applied to {resolved}"
            raise ValueError(f"patch(1) failed: {result.stderr.strip()}")
        except FileNotFoundError:
            raise NotImplementedError(
                "apply_patch requires the 'patch' binary which is not available on this system. "
                "Install it via your package manager (e.g. 'apt-get install patch' or "
                "'brew install patch') to use this tool."
            ) from None

    # ------------------------------------------------------------------
    # bash
    # ------------------------------------------------------------------

    def bash(self, command: str, timeout: int = 30) -> str:
        """Execute a bash command in the project root.

        Uses subprocess.run with shell=True. This is deliberate execution of
        trusted caller code, not a filesystem or credential isolation boundary.

        Args:
            command: Shell command string.
            timeout: Max seconds to wait (default 30).

        Returns:
            Combined stdout + stderr output.

        Raises:
            TimeoutError: Command exceeded timeout.
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=self._project_root,
            )
            output = result.stdout
            if result.stderr:
                output += result.stderr
            return output
        except subprocess.TimeoutExpired:
            raise TimeoutError(f"Command timed out after {timeout}s: {command!r}")

    # ------------------------------------------------------------------
    # grep
    # ------------------------------------------------------------------

    def grep(self, pattern: str, path: str) -> str:
        """Search for a regex pattern in files.

        Uses ripgrep (rg) if available; falls back to a pure-Python
        re-based search when ripgrep is not installed.

        Args:
            pattern: Regex pattern to search for.
            path: Directory or file to search in (relative to project_root).

        Returns:
            Matching lines with file:line prefix, or empty string.

        Raises:
            PermissionError: Path outside project_root.
        """
        resolved = self._resolve(path)

        # Try ripgrep first (fast)
        try:
            result = subprocess.run(
                ["rg", "-n", "--no-heading", pattern, resolved],
                capture_output=True,
                text=True,
                timeout=15,
            )
            return result.stdout
        except FileNotFoundError:
            pass  # ripgrep not installed — Python fallback below
        except subprocess.TimeoutExpired:
            return ""

        # Python re fallback
        regex = re.compile(pattern)
        matches: list[str] = []
        target = Path(resolved)

        if target.is_file():
            files = [target]
        else:
            files = [f for f in target.rglob("*") if f.is_file()]

        for filepath in sorted(files):
            try:
                for lineno, line in enumerate(filepath.read_text().splitlines(), 1):
                    if regex.search(line):
                        rel = (
                            filepath.relative_to(resolved)
                            if target.is_dir()
                            else filepath.name
                        )
                        matches.append(f"{rel}:{lineno}:{line}")
            except (UnicodeDecodeError, PermissionError):
                continue

        return "\n".join(matches)

    # ------------------------------------------------------------------
    # glob
    # ------------------------------------------------------------------

    def glob(self, pattern: str, path: str) -> str:
        """Find files matching a glob pattern using pathlib.glob.

        Args:
            pattern: Glob pattern (e.g., ``**/*.py``).
            path: Base directory to search from.

        Returns:
            Newline-separated list of matching relative paths.

        Raises:
            PermissionError: Path outside project_root.
        """
        resolved = self._resolve(path)
        target = Path(resolved)

        if not target.is_dir():
            return ""

        matches = sorted(
            str(p.relative_to(resolved)) for p in target.glob(pattern) if p.is_file()
        )
        return "\n".join(matches)


# ---------------------------------------------------------------------------
# Tool method name mapping (used by PicoAgent)
# ---------------------------------------------------------------------------

_TOOL_METHOD_MAP: dict[str, str] = {
    "read_file": "read_file",
    "write_file": "write_file",
    "edit_file": "edit_file",
    "apply_patch": "apply_patch",
    "bash": "bash",
    "grep": "grep",
    "glob": "glob",
}
