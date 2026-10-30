"""Native hook must enforce the same typed result contract as the portable gate."""
import asyncio
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(__file__)),
                              "modules", "hooks-harness"))
from amplifier_module_hooks_harness import _make_handler


class TruthinessMustNotRun:
    def __bool__(self):
        raise AssertionError("Checker decisions must never be coerced to bool")


def invoke(checker, signature, strict):
    handler = _make_handler(checker, signature, strict, "/fictional/project")
    return asyncio.run(handler("tool:pre", {"tool_name": "read_file", "parameters": {}}))


@pytest.mark.parametrize("signature", ["is_legal_action", "validate_action"])
@pytest.mark.parametrize("strict", [True, False])
@pytest.mark.parametrize("value", [
    ("False", "denied"), ("True", ""), (1, ""), (0, ""), (1.0, ""),
    (None, ""), (TruthinessMustNotRun(), ""), [True, ""], (True,),
    (True, "", "extra"), True, None, (True, None), (False, 123),
], ids=["string-false", "string-true", "int-one", "int-zero", "float-one",
        "none-decision", "object-decision", "list-pair", "short-tuple",
        "long-tuple", "bare-bool", "bare-none", "none-reason", "numeric-reason"])
def test_malformed_checker_result_is_hard_denied(value, strict, signature):
    result = invoke(lambda *args: value, signature, strict)
    assert result.action == "deny"
    assert "invalid result; expected (bool, reason)" in result.reason
    assert "invalid result" in result.context_injection


@pytest.mark.parametrize("signature", ["is_legal_action", "validate_action"])
@pytest.mark.parametrize("strict", [True, False])
def test_literal_true_remains_legal(strict, signature):
    assert invoke(lambda *args: (True, ""), signature, strict).action == "continue"


@pytest.mark.parametrize("signature", ["is_legal_action", "validate_action"])
@pytest.mark.parametrize("strict", [True, False])
def test_literal_false_preserves_policy_reason_and_warn_mode(strict, signature):
    result = invoke(lambda *args: (False, "Protected resource is outside this task"),
                    signature, strict)
    assert result.action == ("deny" if strict else "inject_context")
    assert "Protected resource is outside this task" in result.context_injection


@pytest.mark.parametrize("signature", ["is_legal_action", "validate_action"])
@pytest.mark.parametrize("strict", [True, False])
def test_checker_exception_is_hard_denied(strict, signature):
    def broken(*args):
        raise ValueError("Fictional policy configuration is unavailable")
    result = invoke(broken, signature, strict)
    assert result.action == "deny"
    assert "Fictional policy configuration is unavailable" in result.reason
