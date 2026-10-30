"""Amplifier Hook Module: Generic Constraint Enforcement.

Dynamically loads ANY constraints.py and enforces it via Amplifier's tool:pre hook.
Supports two constraint function signatures with auto-detection:
  - is_legal_action(tool_name: str, parameters: dict) -> (bool, str)
  - validate_action(state: dict, action: dict) -> (bool, str)

Usage in behavior.yaml:
    hooks:
      - module: hooks-harness
        config:
          constraints_path: ./constraints.py
          strict: true  # deny on violation (false = warn via inject_context)
"""

from __future__ import annotations

import importlib.util
import os
from dataclasses import dataclass
from typing import Any, Callable

# ---------------------------------------------------------------------------
# HookResult: use amplifier_core's if available, otherwise define our own
# compatible dataclass (for testing without amplifier installed).
# ---------------------------------------------------------------------------
try:
    from amplifier_core.models import HookResult  # type: ignore[import]
except ImportError:

    @dataclass
    class HookResult:
        """Minimal HookResult compatible with Amplifier's hook protocol."""

        action: str = "continue"
        reason: str = ""
        context_injection: str = ""
        context_injection_role: str = "system"
        ephemeral: bool = True
        user_message: str = ""
        user_message_level: str = "info"


__all__ = ["mount"]
__version__ = "0.1.0"


# ---------------------------------------------------------------------------
# Dynamic constraint loading
# ---------------------------------------------------------------------------


def _load_constraints_module(constraints_path: str) -> Any:
    """Load a constraints.py file as a Python module via importlib.

    Args:
        constraints_path: Absolute or relative path to the constraints.py file.

    Returns:
        The loaded module object.

    Raises:
        FileNotFoundError: If the file doesn't exist.
    """
    path = os.path.abspath(constraints_path)
    if not os.path.isfile(path):
        raise FileNotFoundError(f"Constraints file not found: {path}")

    spec = importlib.util.spec_from_file_location("_harness_constraints", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"Could not load spec for constraints file: {path}")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)  # type: ignore[union-attr]
    return module


def _detect_signature(
    module: Any,
) -> tuple[str, Callable]:
    """Auto-detect which constraint function signature the module exports.

    Checks for (in order of preference):
      1. is_legal_action(tool_name, parameters) -> (bool, str)
      2. validate_action(state, action) -> (bool, str)

    Args:
        module: The loaded constraints module.

    Returns:
        Tuple of (signature_name, callable).

    Raises:
        ValueError: If neither function is found.
    """
    if hasattr(module, "is_legal_action") and callable(module.is_legal_action):
        return "is_legal_action", module.is_legal_action
    if hasattr(module, "validate_action") and callable(module.validate_action):
        return "validate_action", module.validate_action
    raise ValueError(
        f"Constraints module exports neither 'is_legal_action' nor "
        f"'validate_action'. Found: {[n for n in dir(module) if not n.startswith('_')]}"
    )


# ---------------------------------------------------------------------------
# Hook handler factory
# ---------------------------------------------------------------------------


def _make_handler(
    constraint_fn: Callable,
    signature_name: str,
    strict: bool,
    project_root: str,
) -> Callable:
    """Build the async tool:pre handler that enforces constraints.

    Args:
        constraint_fn: The is_legal_action or validate_action callable.
        signature_name: "is_legal_action" or "validate_action".
        strict: If True, deny on violation. If False, inject_context (warn).
        project_root: The project root directory for context.

    Returns:
        An async handler function compatible with Amplifier's hook protocol.
    """

    async def handler(event: str, data: dict[str, Any]) -> HookResult:
        # Only act on tool:pre events
        if event != "tool:pre":
            return HookResult(action="continue")

        tool_name = data.get("tool_name")
        parameters = data.get("parameters") or {}

        check_failed = False
        try:
            if tool_name is None:
                raise ValueError("tool_name is None — invalid tool call")
            if signature_name == "is_legal_action":
                result = constraint_fn(tool_name, parameters)
            else:
                # validate_action(state, action) signature
                state = {"project_root": project_root}
                action = {"tool_name": tool_name, "parameters": parameters}
                result = constraint_fn(state, action)
            if (not isinstance(result, tuple) or len(result) != 2
                    or type(result[0]) is not bool or not isinstance(result[1], str)):
                raise TypeError(
                    "Constraint returned an invalid result; expected (bool, reason)"
                )
            is_legal, reason = result
        except Exception as exc:
            # A broken checker is a hard deny even in advisory/warn mode.
            check_failed = True
            is_legal = False
            reason = f"Constraint check raised an exception: {exc}"

        if is_legal:
            return HookResult(action="continue")

        # Build context injection for agent self-correction
        injection = (
            f"<constraint-violation>\n"
            f"Your proposed {tool_name!r} call was rejected.\n"
            f"Reason: {reason}\n"
            f"Please retry with a modified approach that satisfies the constraint.\n"
            f"</constraint-violation>"
        )

        if strict or check_failed:
            return HookResult(
                action="deny",
                reason=f"Constraint violation: {reason}",
                context_injection=injection,
                context_injection_role="system",
                ephemeral=True,
            )
        else:
            return HookResult(
                action="inject_context",
                context_injection=injection,
                context_injection_role="system",
                ephemeral=True,
                user_message=f"⚠️ Constraint warning: {reason}",
                user_message_level="warning",
            )

    return handler


# ---------------------------------------------------------------------------
# Module entry point
# ---------------------------------------------------------------------------


async def mount(
    coordinator: Any,
    config: dict[str, Any],
) -> Callable[[], None] | None:
    """Mount the constraint enforcement hook module.

    Called by Amplifier kernel during session initialization.
    Loads the constraints.py specified in config and registers a tool:pre handler.

    Args:
        coordinator: The Amplifier ModuleCoordinator.
        config: Module configuration from behavior.yaml. Expected keys:
            - constraints_path (str): Path to the constraints.py file.
            - strict (bool, default True): Deny on violation vs warn.

    Returns:
        Cleanup function to unregister hooks on shutdown.

    Raises:
        FileNotFoundError: If constraints_path doesn't exist.
        ValueError: If constraints.py exports neither function.
    """
    constraints_path = config.get("constraints_path", "constraints.py")
    strict = config.get("strict", True)

    # Resolve project_root from coordinator capability, fall back to config
    project_root = None
    if hasattr(coordinator, "get_capability"):
        project_root = coordinator.get_capability("session.working_dir")
    if not project_root:
        project_root = config.get("project_root", os.getcwd())

    # Load and detect
    module = _load_constraints_module(constraints_path)
    signature_name, constraint_fn = _detect_signature(module)

    # Build and register handler
    handler = _make_handler(constraint_fn, signature_name, strict, project_root)

    handlers = []
    handlers.append(
        coordinator.hooks.register(
            event="tool:pre",
            handler=handler,
            priority=5,  # High priority — enforce before other hooks
            name="harness-constraint-enforcement",
        )
    )

    def cleanup() -> None:
        for unregister in handlers:
            unregister()

    return cleanup
