"""Tests for the pico runtime (runtime/pico/runtime.py).

All LLM calls are mocked — these tests verify the constraint gate logic,
retry loop, and conversation management, not the LLM itself.
"""

from __future__ import annotations

import asyncio
import os
import sys
from unittest.mock import MagicMock
from types import ModuleType

import pytest


@pytest.fixture(autouse=True)
def mocked_optional_litellm(monkeypatch):
    """Unit tests mock the SDK surface; they never require or call a provider."""
    module = ModuleType("litellm")
    async def refuse_unmocked_completion(**kwargs):
        raise AssertionError("A runtime unit test attempted an unmocked completion")
    module.acompletion = refuse_unmocked_completion
    monkeypatch.setitem(sys.modules, "litellm", module)

# Add runtime/pico to path (pico tier replaced the flat runtime files)
_RUNTIME_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "runtime"
)
sys.path.insert(0, os.path.join(_RUNTIME_DIR, "pico"))
sys.path.insert(0, _RUNTIME_DIR)

FIXTURES_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")


# ---------------------------------------------------------------------------
# Mock litellm response helpers
# ---------------------------------------------------------------------------


def _make_tool_call_choice(tool_name, parameters, call_id="call_001"):
    """Build a mock litellm choice that proposes a tool call."""
    tc = MagicMock()
    tc.id = call_id
    tc.type = "function"
    tc.function.name = tool_name
    tc.function.arguments = (
        parameters if isinstance(parameters, str) else str(parameters)
    )
    choice = MagicMock()
    choice.message.content = None
    choice.message.tool_calls = [tc]
    response = MagicMock()
    response.choices = [choice]
    return response


def _make_text_choice(text):
    """Build a mock litellm choice that is plain text (no tool call)."""
    choice = MagicMock()
    choice.message.content = text
    choice.message.tool_calls = None
    response = MagicMock()
    response.choices = [choice]
    return response


# ---------------------------------------------------------------------------
# Tests: constraint gate
# ---------------------------------------------------------------------------


class TestConstraintGate:
    """Test the constraint gate that checks actions before dispatch."""

    def test_gate_blocks_illegal_action(self, tmp_path):
        from gate import ConstraintGate  # type: ignore[import]

        gate = ConstraintGate(
            constraints_path=os.path.join(FIXTURES_DIR, "constraints_simple.py")
        )
        is_legal, reason = gate.check("bash", {"command": "rm -rf /"})
        assert is_legal is False
        assert "rm" in reason.lower()

    def test_gate_passes_legal_action(self, tmp_path):
        from gate import ConstraintGate  # type: ignore[import]

        gate = ConstraintGate(
            constraints_path=os.path.join(FIXTURES_DIR, "constraints_simple.py")
        )
        is_legal, reason = gate.check("read_file", {"file_path": "src/main.py"})
        assert is_legal is True
        assert reason == ""

    def test_gate_exception_treated_as_deny(self):
        from gate import ConstraintGate  # type: ignore[import]

        gate = ConstraintGate(
            constraints_path=os.path.join(FIXTURES_DIR, "constraints_simple.py")
        )
        # None tool_name will cause a TypeError which is caught and returned as deny
        is_legal, reason = gate.check(None, None)
        assert is_legal is False


# ---------------------------------------------------------------------------
# Tests: PicoAgent
# ---------------------------------------------------------------------------


class TestPicoAgent:
    """Test the async PicoAgent loop with mocked litellm."""

    def _make_agent(self, tmp_path):
        from gate import ConstraintGate  # type: ignore[import]
        from runtime import PicoAgent  # type: ignore[import]
        from tools import LocalToolExecutor  # type: ignore[import]

        (tmp_path / "file.txt").write_text("test")
        gate = ConstraintGate(
            constraints_path=os.path.join(FIXTURES_DIR, "constraints_simple.py"),
            project_root=str(tmp_path),
        )
        executor = LocalToolExecutor(str(tmp_path))
        return PicoAgent(
            gate=gate,
            executor=executor,
            system_prompt="You are a test agent.",
            model="mock",
            max_retries=3,
        )

    def test_retry_on_illegal_action(self, tmp_path):
        """Agent retries when constraint gate blocks an action."""
        from unittest.mock import patch

        agent = self._make_agent(tmp_path)

        call_count = 0
        illegal = _make_tool_call_choice("bash", '{"command": "rm -rf /"}')
        legal = _make_text_choice("I'll use a different approach.")

        async def mock_acompletion(**kwargs):
            nonlocal call_count
            call_count += 1
            return illegal if call_count == 1 else legal

        with patch("litellm.acompletion", side_effect=mock_acompletion):
            result = asyncio.run(agent.process_turn("Do something dangerous"))

        assert call_count == 2  # retried once
        assert "different approach" in result.lower()

    def test_max_retries_exhaustion(self, tmp_path):
        """Agent gives up after max_retries consecutive rejections."""
        from unittest.mock import patch

        agent = self._make_agent(tmp_path)
        agent.max_retries = 2
        illegal = _make_tool_call_choice("bash", '{"command": "rm -rf /"}')

        async def mock_acompletion(**kwargs):
            return illegal

        with patch("litellm.acompletion", side_effect=mock_acompletion):
            result = asyncio.run(agent.process_turn("Do something dangerous"))

        assert "max retries" in result.lower() or "exhausted" in result.lower()

    def test_legal_tool_call_dispatches_and_returns(self, tmp_path):
        """Legal tool call is dispatched to executor and result returned to LLM."""
        import json
        from unittest.mock import patch

        (tmp_path / "hello.txt").write_text("Hello from test!")
        agent = self._make_agent(tmp_path)

        call_count = 0
        tool_resp = _make_tool_call_choice(
            "read_file", json.dumps({"file_path": str(tmp_path / "hello.txt")})
        )
        final_resp = _make_text_choice("The file says: Hello from test!")

        async def mock_acompletion(**kwargs):
            nonlocal call_count
            call_count += 1
            return tool_resp if call_count == 1 else final_resp

        with patch("litellm.acompletion", side_effect=mock_acompletion):
            result = asyncio.run(agent.process_turn("Read hello.txt"))

        assert "Hello from test" in result

    def test_conversation_history_accumulates(self, tmp_path):
        """Each turn adds to conversation history."""
        from unittest.mock import patch

        agent = self._make_agent(tmp_path)

        call_count = 0

        async def mock_acompletion(**kwargs):
            nonlocal call_count
            call_count += 1
            return _make_text_choice(
                f"Response (history has {len(kwargs['messages'])} messages)"
            )

        with patch("litellm.acompletion", side_effect=mock_acompletion):
            asyncio.run(agent.process_turn("First message"))
            asyncio.run(agent.process_turn("Second message"))

        # system + user1 + assistant1 + user2 + assistant2 = 5
        assert len(agent.messages) == 5
