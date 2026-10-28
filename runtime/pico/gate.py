"""Constraint gate for pico runtime.

Loads a constraints.py module and checks tool actions before dispatch.
Supports both is_legal_action(tool_name, params) and
validate_action(state, action) harness signatures with auto-detection.
"""

from __future__ import annotations

import importlib.util
import os


class ConstraintViolation(Exception):
    """Raised when a tool call is denied by the constraint gate."""

    def __init__(self, tool_name: str, reason: str) -> None:
        self.tool_name = tool_name
        self.reason = reason
        super().__init__(f"ConstraintViolation: {tool_name} — {reason}")


class ConstraintGate:
    """Loads a constraints.py and checks tool actions before dispatch.

    Supports both is_legal_action(tool_name, params) and
    validate_action(state, action) signatures with auto-detection.

    Binds a project_root so downstream tools receive a consistent boundary.
    """

    def __init__(
        self,
        constraints_path: str,
        project_root: str | None = None,
    ) -> None:
        """Initialise the gate.

        Args:
            constraints_path: Path to a constraints.py module.
            project_root: Optional project root to bind; defaults to cwd.

        Raises:
            FileNotFoundError: If constraints_path does not exist.
            ValueError: If the module exports neither supported function.
        """
        path = os.path.abspath(constraints_path)
        if not os.path.isfile(path):
            raise FileNotFoundError(f"Constraints file not found: {path}")

        self.project_root = os.path.realpath(project_root or os.getcwd())

        spec = importlib.util.spec_from_file_location("_pico_constraints", path)
        if spec is None or spec.loader is None:
            raise ValueError(f"Could not load constraints module: {path}")
        self._module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(self._module)  # type: ignore[union-attr]

        # Auto-detect signature: is_legal_action takes priority
        if hasattr(self._module, "is_legal_action"):
            self._signature = "is_legal_action"
            self._fn = self._module.is_legal_action
        elif hasattr(self._module, "validate_action"):
            self._signature = "validate_action"
            self._fn = self._module.validate_action
        else:
            raise ValueError(
                "Constraints module exports neither 'is_legal_action' nor 'validate_action'"
            )

    def check(self, tool_name: str | None, parameters: dict | None) -> tuple[bool, str]:
        """Check whether a tool action is permitted.

        Args:
            tool_name: Name of the tool being called.
            parameters: Tool parameters dict (may be None or empty).

        Returns:
            ``(True, "")`` if the action is legal.
            ``(False, reason)`` if the action is denied.
        """
        try:
            if not isinstance(tool_name, str):
                raise TypeError(
                    f"tool_name must be a string, got {type(tool_name).__name__}"
                )
            safe_params = parameters if parameters is not None else {}
            if self._signature == "is_legal_action":
                result = self._fn(tool_name, safe_params)
            else:
                state = {"project_root": self.project_root}
                action = {"tool_name": tool_name, "parameters": safe_params}
                result = self._fn(state, action)
            if (not isinstance(result, tuple) or len(result) != 2
                    or type(result[0]) is not bool or not isinstance(result[1], str)):
                return False, "Constraint returned an invalid result; expected (bool, reason)"
            return result
        except Exception as exc:
            return False, f"Constraint check error: {exc}"
