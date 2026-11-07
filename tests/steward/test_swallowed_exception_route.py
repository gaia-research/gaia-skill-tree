"""Tests for the swallowed_exception Class B dispatch route.

Verifies:
- POLICY.yaml loads cleanly with the swallowed-exception-repair dispatch rule.
- Mechanical verification (prove_exception_edit in exceptionproof.py) accepts valid edits
  (narrowing, diagnostic logging, and best-effort marker) and rejects out-of-envelope edits
  (modifying try body, changing return values, replacing continue/break, adding raise,
  modifying code outside try-except, syntax errors).
- Route eligibility in routing.py enforces pairing, .py subject in scripts/ or src/gaia_cli/,
  uncapped findings, and findingCount > 0.
- Verification evaluation in verification.py rejects multi-file diffs, forbidden paths,
  and diffs violating exception proof while allowing valid repairs.
"""

from __future__ import annotations

import difflib
import json
from pathlib import Path

import pytest

from gaia_cli.steward.exceptionproof import prove_exception_edit
from gaia_cli.steward.models import (
    AuthorityClass,
    Debt,
    DispatchPacket,
    Priority,
    RoutingBudget,
    Subject,
)
from gaia_cli.steward.policy import (
    SWALLOWED_EXCEPTION_DEBT_KIND,
    SWALLOWED_EXCEPTION_RULE_ID,
    StewardPolicy,
)
from gaia_cli.steward.routing import RoutingError, _assert_route_eligible, _assert_route_ratified
from gaia_cli.steward.verification import (
    PROOF_TRANSCRIPT_SCHEMA,
    evaluate,
    parse_proof_transcript,
    parse_unified_diff,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
RULE_ID = "swallowed-exception-repair"
DEBT_KIND = "swallowed_exception"


def _live_policy() -> StewardPolicy:
    return StewardPolicy.load(REPO_ROOT)


def _live_rule():
    rule = _live_policy().dispatch_rules.get(RULE_ID)
    assert rule is not None
    return rule


def _make_debt(
    subject_path: str = "src/gaia_cli/handler.py",
    kind: str = DEBT_KIND,
    finding_count: int = 1,
    findings_capped: bool = False,
    findings: list[dict[str, Any]] | None = None,
) -> Debt:
    actual_findings = (
        findings
        if findings is not None
        else [{"line": 10, "handler": "except Exception", "body": "pass"}] * finding_count
    )
    return Debt(
        id=f"debt:{kind}:{subject_path}",
        kind=kind,
        subject=Subject("source-file", subject_path),
        source="error-handling",
        current_state={"swallowedExceptions": 0},
        observed_state={
            "path": subject_path,
            "findingCount": len(actual_findings) if findings is not None else finding_count,
            "findings": actual_findings,
            "findingsCapped": findings_capped,
        },
        confidence=0.8,
        priority=Priority(0.8, 0.7, 0.6, 0.8, 0.2, 1.344),
        authority=AuthorityClass.B,
        status="open",
        first_observed_at="2026-11-08T00:00:00Z",
        last_observed_at="2026-11-08T00:00:00Z",
        observation_count=1,
    )


def _make_packet(subject_path: str = "src/gaia_cli/handler.py") -> DispatchPacket:
    rule = _live_rule()
    debt = _make_debt(subject_path)
    return DispatchPacket.create(
        debt=debt.to_dict(),
        evidence=dict(debt.observed_state),
        authority=AuthorityClass.B,
        rule=rule.id,
        routine=rule.routine,
        objective=rule.objective,
        allowed_paths=rule.allowed_paths,
        allowed_commands=rule.allowed_commands,
        forbidden_paths=rule.forbidden_paths,
        stop_conditions=rule.stop_conditions,
        proof=rule.proof,
        budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0),
        capability=rule.capability,
    )


def _make_transcript(packet: DispatchPacket):
    entries = [
        {"contractIndex": i, "command": f"cmd-{i}", "exitCode": 0, "output": "ok"}
        for i in range(1, len(packet.proof) + 1)
    ]
    return parse_proof_transcript(
        json.dumps({"schemaVersion": PROOF_TRANSCRIPT_SCHEMA, "entries": entries}),
        proof_contract_length=len(packet.proof),
    )


def _patch(path: str, before: str, after: str) -> str:
    return "".join(
        difflib.unified_diff(
            before.splitlines(keepends=True),
            after.splitlines(keepends=True),
            fromfile=f"a/{path}",
            tofile=f"b/{path}",
            n=3,
        )
    )


# --- 1. Policy loading tests ------------------------------------------------


def test_policy_loads_cleanly_with_swallowed_exception_rule() -> None:
    policy = _live_policy()
    rule = policy.dispatch_rules.get(RULE_ID)
    assert rule is not None
    assert rule.id == RULE_ID
    assert rule.debt_kind == DEBT_KIND
    assert rule.authority is AuthorityClass.B
    assert rule.routine == "error-handling-steward"
    assert "scripts/**" in rule.allowed_paths
    assert "src/gaia_cli/**" in rule.allowed_paths

    for forbidden in (
        ".agents/skills/**",
        ".claude/skills/**",
        ".gaia/steward/**",
        ".github/**",
        "docs/**",
        "founder/**",
        "registry/**",
        "skill-trees/**",
    ):
        assert forbidden in rule.forbidden_paths

    assert (REPO_ROOT / rule.prompt_guide).is_file()
    decision_file = REPO_ROOT / "founder/steward/decisions/steward-swallowed-exception-route.json"
    assert decision_file.is_file()
    data = json.loads(decision_file.read_text(encoding="utf-8"))
    assert data["status"] == "decided"
    assert data["resolution"] == "approved"
    # Route is ratified under Founder Ruling 4
    _assert_route_ratified(rule, REPO_ROOT)


# --- 2. prove_exception_edit positive tests ----------------------------------


def test_prove_exception_edit_accepts_narrowing() -> None:
    before = """\
import json

def process():
    try:
        data = load_file()
    except Exception:
        pass
    return data
"""
    after = """\
import json

def process():
    try:
        data = load_file()
    except (OSError, json.JSONDecodeError):
        pass
    return data
"""
    violations = prove_exception_edit(before, after)
    assert violations == [], violations


def test_prove_exception_edit_accepts_bare_except_narrowing() -> None:
    before = """\
def process():
    try:
        data = load_file()
    except:
        pass
"""
    after = """\
def process():
    try:
        data = load_file()
    except OSError:
        pass
"""
    violations = prove_exception_edit(before, after)
    assert violations == [], violations


def test_prove_exception_edit_accepts_best_effort_comment() -> None:
    before = """\
def process():
    try:
        data = load_file()
    except Exception:
        pass
"""
    after = """\
def process():
    try:
        data = load_file()
    except Exception:  # steward: best-effort: intentional ignore
        pass
"""
    violations = prove_exception_edit(before, after)
    assert violations == [], violations


def test_prove_exception_edit_accepts_diagnostic_logging_before_pass() -> None:
    before = """\
import logging

logger = logging.getLogger(__name__)

def process():
    try:
        data = load_file()
    except Exception:
        pass
"""
    after = """\
import logging

logger = logging.getLogger(__name__)

def process():
    try:
        data = load_file()
    except Exception:
        logger.debug("ignored", exc_info=True)
        pass
"""
    violations = prove_exception_edit(before, after)
    assert violations == [], violations


def test_prove_exception_edit_accepts_logging_before_continue() -> None:
    before = """\
import logging

log = logging.getLogger(__name__)

for item in items:
    try:
        work(item)
    except Exception:
        continue
"""
    after = """\
import logging

log = logging.getLogger(__name__)

for item in items:
    try:
        work(item)
    except OSError:
        log.warning("failed item")
        continue
"""
    violations = prove_exception_edit(before, after)
    assert violations == [], violations


def test_prove_exception_edit_accepts_logging_before_return() -> None:
    before = """\
import logging

logger = logging.getLogger(__name__)

def fetch():
    try:
        return get_val()
    except Exception:
        return None
"""
    after = """\
import logging

logger = logging.getLogger(__name__)

def fetch():
    try:
        return get_val()
    except (KeyError, ValueError):
        logger.info("value missing")
        return None
"""
    violations = prove_exception_edit(before, after)
    assert violations == [], violations


def test_prove_exception_edit_accepts_logging_before_break() -> None:
    before = """\
import logging

logger = logging.getLogger(__name__)

while True:
    try:
        step()
    except Exception:
        break
"""
    after = """\
import logging

logger = logging.getLogger(__name__)

while True:
    try:
        step()
    except StopIteration:
        logger.debug("stopped")
        break
"""
    violations = prove_exception_edit(before, after)
    assert violations == [], violations


# --- 3. prove_exception_edit negative tests ----------------------------------


def test_prove_exception_edit_rejects_modifying_try_body() -> None:
    before = """\
try:
    x = 1
except Exception:
    pass
"""
    after = """\
try:
    x = 2
except OSError:
    pass
"""
    violations = prove_exception_edit(before, after)
    assert violations, "expected violation for try body edit"
    assert any("try block body was modified" in v for v in violations)


def test_prove_exception_edit_rejects_changing_continue_to_pass() -> None:
    before = """\
for item in items:
    try:
        work(item)
    except Exception:
        continue
"""
    after = """\
for item in items:
    try:
        work(item)
    except OSError:
        pass
"""
    violations = prove_exception_edit(before, after)
    assert violations
    assert any("continue statement was removed or replaced" in v for v in violations)


def test_prove_exception_edit_rejects_changing_continue_to_break() -> None:
    before = """\
for item in items:
    try:
        work(item)
    except Exception:
        continue
"""
    after = """\
for item in items:
    try:
        work(item)
    except OSError:
        break
"""
    violations = prove_exception_edit(before, after)
    assert violations
    assert any("continue statement was removed or replaced" in v for v in violations)


def test_prove_exception_edit_rejects_changing_return_value() -> None:
    before = """\
def compute():
    try:
        return calculate()
    except Exception:
        return None
"""
    after = """\
def compute():
    try:
        return calculate()
    except OSError:
        return {}
"""
    violations = prove_exception_edit(before, after)
    assert violations
    assert any("return value modified" in v for v in violations)


def test_prove_exception_edit_rejects_adding_raise() -> None:
    before = """\
try:
    do_something()
except Exception:
    pass
"""
    after = """\
try:
    do_something()
except OSError:
    raise
"""
    violations = prove_exception_edit(before, after)
    assert violations
    assert any("new raise statement introduced" in v for v in violations)


def test_prove_exception_edit_rejects_editing_code_outside_try_except() -> None:
    before = """\
a = 1
try:
    do_something()
except Exception:
    pass
"""
    after = """\
a = 999
try:
    do_something()
except OSError:
    pass
"""
    violations = prove_exception_edit(before, after)
    assert violations
    assert any("AST value mismatch" in v or "mismatch" in v for v in violations)


def test_prove_exception_edit_rejects_syntax_error_in_after_code() -> None:
    before = """\
try:
    do_something()
except Exception:
    pass
"""
    after = """\
try:
    do_something()
except (OSError:
    pass
"""
    violations = prove_exception_edit(before, after)
    assert violations
    assert any("after_code failed to parse" in v for v in violations)


def test_prove_exception_edit_rejects_syntax_error_in_before_code() -> None:
    before = "def bad(:"
    after = "def bad(): pass"
    violations = prove_exception_edit(before, after)
    assert violations
    assert any("before_code failed to parse" in v for v in violations)


def test_prove_exception_edit_rejects_widening_exception_type() -> None:
    before = """\
try:
    do_something()
except Exception:
    pass
"""
    after = """\
try:
    do_something()
except BaseException:
    pass
"""
    violations = prove_exception_edit(before, after)
    assert violations
    assert any("exception type was not narrowed" in v for v in violations)


def test_prove_exception_edit_rejects_disallowed_statement_in_body() -> None:
    before = """\
try:
    do_something()
except Exception:
    pass
"""
    after = """\
try:
    do_something()
except OSError:
    x = 42
    pass
"""
    violations = prove_exception_edit(before, after)
    assert violations
    assert any("disallowed statement in except handler body" in v for v in violations)


# --- 4. Route eligibility tests in routing.py --------------------------------


def test_route_eligible_for_valid_subject_scripts() -> None:
    rule = _live_rule()
    debt = _make_debt("scripts/environment/smoke.py", findings=[{"line": 86, "handler": "except Exception", "body": "pass"}])
    # Must not raise
    _assert_route_eligible(rule, debt, repo_root=REPO_ROOT)


def test_route_eligible_for_valid_subject_gaia_cli() -> None:
    rule = _live_rule()
    debt = _make_debt("src/gaia_cli/treeManager.py", findings=[{"line": 170, "handler": "except Exception", "body": "pass"}])
    # Must not raise
    _assert_route_eligible(rule, debt, repo_root=REPO_ROOT)


def test_route_ineligible_for_non_python_subject() -> None:
    rule = _live_rule()
    debt = _make_debt("scripts/cleanup.sh")
    with pytest.raises(RoutingError, match="must be a .py file in scripts/ or src/gaia_cli/"):
        _assert_route_eligible(rule, debt)


def test_route_ineligible_for_subject_outside_allowed_roots() -> None:
    rule = _live_rule()
    debt = _make_debt("docs/conf.py")
    with pytest.raises(RoutingError, match="must be a .py file in scripts/ or src/gaia_cli/"):
        _assert_route_eligible(rule, debt)


def test_route_ineligible_when_rule_and_kind_unpaired() -> None:
    rule = _live_rule()
    debt = _make_debt("src/gaia_cli/handler.py", kind="unused_import")
    with pytest.raises(RoutingError, match="must be paired"):
        _assert_route_eligible(rule, debt)


def test_route_ineligible_when_findings_capped() -> None:
    rule = _live_rule()
    debt = _make_debt("src/gaia_cli/handler.py", findings_capped=True)
    with pytest.raises(RoutingError, match="findings must not be capped and must have findingCount > 0"):
        _assert_route_eligible(rule, debt)


def test_route_ineligible_when_finding_count_zero() -> None:
    rule = _live_rule()
    debt = _make_debt("src/gaia_cli/handler.py", finding_count=0)
    with pytest.raises(RoutingError, match="findings must not be capped and must have findingCount > 0"):
        _assert_route_eligible(rule, debt)


# --- 5. Scope and verification checks in verification.py ---------------------


def test_verification_rejects_diff_with_multiple_files() -> None:
    before = "try:\n    pass\nexcept Exception:\n    pass\n"
    after = "try:\n    pass\nexcept OSError:\n    pass\n"
    diff1 = _patch("src/gaia_cli/a.py", before, after)
    diff2 = _patch("src/gaia_cli/b.py", before, after)
    multi_diff = diff1 + diff2

    packet = _make_packet("src/gaia_cli/a.py")
    change_set = parse_unified_diff(multi_diff)
    transcript = _make_transcript(packet)

    verdict = evaluate(
        packet=packet,
        change_set=change_set,
        transcript=transcript,
        debt_source="error-handling",
        sensor_sources=["error-handling"],
        baseline_open_debt=[],
        current_open_debt=[],
        authority_still_class_b=True,
    )
    assert not verdict.scope_valid
    assert verdict.verdict == "reject"
    assert any("must touch exactly one file" in r for r in verdict.reasons)


def test_verification_rejects_diff_with_forbidden_paths() -> None:
    before = "try:\n    pass\nexcept Exception:\n    pass\n"
    after = "try:\n    pass\nexcept OSError:\n    pass\n"
    diff = _patch(".github/workflows/ci.yml", before, after)

    packet = _make_packet(".github/workflows/ci.yml")
    change_set = parse_unified_diff(diff)
    transcript = _make_transcript(packet)

    verdict = evaluate(
        packet=packet,
        change_set=change_set,
        transcript=transcript,
        debt_source="error-handling",
        sensor_sources=["error-handling"],
        baseline_open_debt=[],
        current_open_debt=[],
        authority_still_class_b=True,
    )
    assert not verdict.scope_valid
    assert verdict.verdict == "reject"
    assert any("forbiddenPaths" in r for r in verdict.reasons)


def test_verification_accepts_valid_exception_patch() -> None:
    path = "src/gaia_cli/handler.py"
    before = """\
def run():
    try:
        execute()
    except Exception:
        pass
"""
    after = """\
def run():
    try:
        execute()
    except (OSError, RuntimeError):
        pass
"""
    diff = _patch(path, before, after)
    packet = _make_packet(path)
    change_set = parse_unified_diff(diff)
    transcript = _make_transcript(packet)

    verdict = evaluate(
        packet=packet,
        change_set=change_set,
        transcript=transcript,
        debt_source="error-handling",
        sensor_sources=["error-handling"],
        baseline_open_debt=[],
        current_open_debt=[],
        authority_still_class_b=True,
        exception_baseline={path: before},
    )
    assert verdict.scope_valid, verdict.reasons
    assert verdict.verdict == "pending"


def test_verification_rejects_patch_that_modifies_try_body() -> None:
    path = "src/gaia_cli/handler.py"
    before = """\
def run():
    try:
        execute()
    except Exception:
        pass
"""
    after = """\
def run():
    try:
        execute_changed()
    except OSError:
        pass
"""
    diff = _patch(path, before, after)
    packet = _make_packet(path)
    change_set = parse_unified_diff(diff)
    transcript = _make_transcript(packet)

    verdict = evaluate(
        packet=packet,
        change_set=change_set,
        transcript=transcript,
        debt_source="error-handling",
        sensor_sources=["error-handling"],
        baseline_open_debt=[],
        current_open_debt=[],
        authority_still_class_b=True,
        exception_baseline={path: before},
    )
    assert not verdict.scope_valid
    assert verdict.verdict == "reject"
    assert any("try block body was modified" in r for r in verdict.reasons)


def test_prove_exception_edit_rejects_best_effort_in_escalated_security_context() -> None:
    # 1. authz.py fail-open context
    before_authz = """\
def _registry_has_any_verifier(reg):
    try:
        index = json.load(f)
    except Exception:
        pass
    return False
"""
    after_authz = """\
def _registry_has_any_verifier(reg):
    try:
        index = json.load(f)
    except Exception:  # steward: best-effort: fallback to bootstrap
        pass
    return False
"""
    violations = prove_exception_edit(before_authz, after_authz, filename="src/gaia_cli/authz.py")
    assert any("feeds authorization" in v for v in violations)

    # 2. jev.py _recordSpend context
    before_spend = """\
def _recordSpend(amount):
    try:
        write_ledger(amount)
    except Exception:
        pass
"""
    after_spend = """\
def _recordSpend(amount):
    try:
        write_ledger(amount)
    except Exception:  # steward: best-effort: ignore budget write error
        pass
"""
    violations = prove_exception_edit(before_spend, after_spend, filename="src/gaia_cli/jev.py")
    assert any("budget/spend recording" in v for v in violations)

    # 3. install.py load_manifest context
    before_manifest = """\
def load_manifest():
    try:
        return json.load(f)
    except Exception:
        pass
    return {}
"""
    after_manifest = """\
def load_manifest():
    try:
        return json.load(f)
    except Exception:  # steward: best-effort: empty fallback
        pass
    return {}
"""
    violations = prove_exception_edit(before_manifest, after_manifest, filename="src/gaia_cli/install.py")
    assert any("file overwrite" in v for v in violations)


def test_assert_route_eligible_rejects_escalated_security_file() -> None:
    rule = _live_rule()
    debt = _make_debt(subject_path="src/gaia_cli/authz.py")
    with pytest.raises(RoutingError, match="feeds authorization, budget/spend, or overwrite decisions"):
        _assert_route_eligible(rule, debt)


def test_verification_rejects_diff_touching_different_subject_file() -> None:
    path_a = "src/gaia_cli/handler.py"
    path_b = "src/gaia_cli/other.py"
    before = "try:\n    execute()\nexcept Exception:\n    pass\n"
    after = "try:\n    execute()\nexcept OSError:\n    pass\n"

    diff = _patch(path_b, before, after)
    packet = _make_packet(path_a)
    change_set = parse_unified_diff(diff)
    transcript = _make_transcript(packet)

    verdict = evaluate(
        packet=packet,
        change_set=change_set,
        transcript=transcript,
        debt_source="error-handling",
        sensor_sources=["error-handling"],
        baseline_open_debt=[],
        current_open_debt=[],
        authority_still_class_b=True,
        exception_baseline={path_b: before},
    )
    assert not verdict.scope_valid
    assert verdict.verdict == "reject"
    assert any("diff touches src/gaia_cli/other.py but debt subject is src/gaia_cli/handler.py" in r for r in verdict.reasons)


def test_prove_exception_edit_rejects_unsafe_diagnostic_call() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception:
        pass
"""
    # Unsafe call with side-effect argument
    after_unsafe_arg = """\
def run():
    try:
        do_work()
    except Exception:
        logger.warning(delete_data())
        pass
"""
    violations = prove_exception_edit(before, after_unsafe_arg, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)

    # Calling unapproved target (e.g. attacker.write)
    after_unapproved_target = """\
def run():
    try:
        do_work()
    except Exception:
        attacker.write("leak")
        pass
"""
    violations = prove_exception_edit(before, after_unapproved_target, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_statement_removal_in_handler() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception:
        cleanup()
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except OSError:
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("existing statements in except handler were reordered, removed, or modified" in v for v in violations)


def test_prove_exception_edit_rejects_binding_renaming() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception as e:
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except OSError as other:
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("variable binding changed" in v for v in violations)


def test_prove_exception_edit_rejects_attribute_lookup_in_diagnostic() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except Exception:
        logger.warning(obj.attr)
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_binary_op_in_diagnostic() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception as e:
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except Exception as e:
        logger.warning("err: " + str(e))
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_fstring_in_diagnostic() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception as e:
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except Exception as e:
        logger.warning(f"err: {e}")
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_assert_route_eligible_rejects_real_jev_line_838() -> None:
    rule = _live_rule()
    debt = _make_debt(
        subject_path="src/gaia_cli/jev.py",
        finding_count=1,
        findings=[{"line": 838, "handler": "except Exception", "body": "pass"}],
    )
    with pytest.raises(RoutingError, match="feeds authorization, budget/spend, or overwrite decisions"):
        _assert_route_eligible(rule, debt, repo_root=REPO_ROOT)


def test_assert_route_eligible_rejects_real_install_line_68() -> None:
    rule = _live_rule()
    debt = _make_debt(
        subject_path="src/gaia_cli/install.py",
        finding_count=1,
        findings=[{"line": 68, "handler": "except Exception", "body": "pass"}],
    )
    with pytest.raises(RoutingError, match="feeds authorization, budget/spend, or overwrite decisions"):
        _assert_route_eligible(rule, debt, repo_root=REPO_ROOT)


def test_prove_exception_edit_rejects_side_effect_in_narrowed_type() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except execute_side_effect():
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("exception type was not narrowed" in v for v in violations)


def test_prove_exception_edit_rejects_unbound_name_in_diagnostic() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception as e:
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except Exception as e:
        logger.warning(unbound_var)
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_arbitrary_stderr_target() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except Exception:
        custom_obj.stderr.write("msg")
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_diff_outside_except_handler() -> None:
    before = """\
# Top level comment
def run():
    # Inside func
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
# Modified top level comment
def run():
    # Inside func
    try:
        do_work()
    except OSError:
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("outside any except handler" in v for v in violations)


def test_prove_exception_edit_rejects_narrowing_in_escalated_security_context() -> None:
    before = """\
def _registry_has_any_verifier(reg):
    try:
        index = json.load(f)
    except Exception:
        pass
    return False
"""
    after = """\
def _registry_has_any_verifier(reg):
    try:
        index = json.load(f)
    except (OSError, json.JSONDecodeError):
        pass
    return False
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/authz.py")
    assert any("feeds authorization, budget/spend recording, file overwrite" in v for v in violations)


@pytest.mark.parametrize(
    "path, line",
    [
        ("src/gaia_cli/commands/dev/helpers.py", 726),
        ("src/gaia_cli/commands/dev/helpers.py", 1424),
        ("src/gaia_cli/commands/dev/helpers.py", 1445),
        ("src/gaia_cli/commands/dev/calibrate.py", 113),
        ("src/gaia_cli/commands/dev/calibrate.py", 161),
        ("src/gaia_cli/commands/dev/timeline.py", 21),
        ("src/gaia_cli/commands/dev/timeline.py", 43),
        ("src/gaia_cli/impl.py", 1023),
        ("src/gaia_cli/impl.py", 1024),
        ("src/gaia_cli/impl.py", 1689),
        ("src/gaia_cli/impl.py", 1691),
    ],
)
def test_assert_route_eligible_rejects_all_escalated_locations(path: str, line: int) -> None:
    rule = _live_rule()
    debt = _make_debt(
        subject_path=path,
        finding_count=1,
        findings=[{"line": line, "handler": "except Exception", "body": "pass"}],
    )
    with pytest.raises(RoutingError, match="feeds authorization|escalated security|wraps custom_state"):
        _assert_route_eligible(rule, debt, repo_root=REPO_ROOT)


def test_prove_exception_edit_rejects_unbound_logger_target() -> None:
    # No logger = ... or import logging at module level
    before = """\
def run():
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except Exception:
        logger.warning("unbound logger")
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_missing_error_or_custom_attribute() -> None:
    before = """\
def run():
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
def run():
    try:
        do_work()
    except MissingError:
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("exception type was not narrowed" in v for v in violations)


def test_prove_exception_edit_accepts_repair_in_file_with_unchanged_escalated_handler() -> None:
    # Mixed file: handler 1 is unchanged at line 68 (load_manifest in install.py),
    # handler 2 is repaired at line 649 (normal handler narrowed to OSError).
    before = """\
def load_manifest():
    try:
        data = read_json()
    except Exception:
        pass

def download_skill():
    try:
        fetch_remote()
    except Exception:
        pass
"""
    after = """\
def load_manifest():
    try:
        data = read_json()
    except Exception:
        pass

def download_skill():
    try:
        fetch_remote()
    except OSError:
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/install.py")
    assert violations == [], violations


def test_assert_route_eligible_accepts_eligible_line_in_mixed_file() -> None:
    rule = _live_rule()
    debt = _make_debt(
        subject_path="src/gaia_cli/install.py",
        finding_count=1,
        findings=[{"line": 649, "handler": "except Exception", "body": "pass"}],
    )
    # Line 649 in install.py is eligible (not escalated)! Must not raise.
    _assert_route_eligible(rule, debt, repo_root=REPO_ROOT)


def test_prove_exception_edit_rejects_fake_logger_assignment() -> None:
    # logger = None is not a trusted logging.Logger
    before = """\
logger = None

def run():
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
logger = None

def run():
    try:
        do_work()
    except Exception:
        logger.warning("fake logger")
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_shadowed_builtin_exception() -> None:
    # OSError is shadowed by local parameter
    before = """\
def run(OSError):
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
def run(OSError):
    try:
        do_work()
    except OSError:
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("exception type was not narrowed" in v for v in violations)


def test_prove_exception_edit_rejects_shadowed_logger_in_func() -> None:
    # logger is shadowed by local parameter in run(logger)
    before = """\
import logging
logger = logging.getLogger(__name__)

def run(logger):
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
import logging
logger = logging.getLogger(__name__)

def run(logger):
    try:
        do_work()
    except Exception:
        logger.warning("shadowed logger")
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_fake_logging_module_import() -> None:
    # import malicious as logging -> logging is not genuine
    before = """\
import malicious as logging
logger = logging.getLogger(__name__)

def run():
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
import malicious as logging
logger = logging.getLogger(__name__)

def run():
    try:
        do_work()
    except Exception:
        logger.warning("fake logging module")
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_custom_getLogger_function() -> None:
    # custom def getLogger shadows getLogger
    before = """\
def getLogger(name):
    return None

logger = getLogger(__name__)

def run():
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
def getLogger(name):
    return None

logger = getLogger(__name__)

def run():
    try:
        do_work()
    except Exception:
        logger.warning("custom getLogger")
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_reassigned_logger() -> None:
    # logger is reassigned later in module
    before = """\
import logging
logger = logging.getLogger(__name__)
logger = "not a logger"

def run():
    try:
        do_work()
    except Exception:
        pass
"""
    after = """\
import logging
logger = logging.getLogger(__name__)
logger = "not a logger"

def run():
    try:
        do_work()
    except Exception:
        logger.warning("reassigned logger")
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/handler.py")
    assert any("disallowed statement" in v or "except handler edit must narrow" in v for v in violations)


def test_prove_exception_edit_rejects_custom_state_in_impl_try_block() -> None:
    # Try block touches custom_state_path in impl.py
    before = """\
def scan_command():
    try:
        data = read_json(custom_state_path)
    except Exception:
        pass
"""
    after = """\
def scan_command():
    try:
        data = read_json(custom_state_path)
    except OSError:
        pass
"""
    violations = prove_exception_edit(before, after, filename="src/gaia_cli/impl.py")
    assert any("feeds authorization, budget/spend recording, file overwrite" in v for v in violations)






