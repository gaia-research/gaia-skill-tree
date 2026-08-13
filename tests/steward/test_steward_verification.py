"""Steward V1.3 — independent verification of one dispatched Class B patch."""

from __future__ import annotations

import inspect
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path
import shutil

import pytest

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.models import AuthorityClass, DispatchPacket, Observation, RoutingBudget, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.prompt import render_verifier_prompt
from gaia_cli.steward.routing import (
    RoutingError,
    render_dispatch,
    render_verification,
    render_verifier_prompt_for,
)
from gaia_cli.steward.verification import (
    PROOF_TRANSCRIPT_SCHEMA,
    VerificationError,
    evaluate,
    parse_proof_transcript,
    parse_unified_diff,
)


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = datetime(2026, 8, 13, tzinfo=timezone.utc)


def _repo(tmp_path: Path) -> Path:
    policy = tmp_path / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    return tmp_path


class IntegritySensor:
    """One wired Class B finding, plus optional unrelated drift."""

    id = "registry-integrity"

    def __init__(self, *, extra: int = 0) -> None:
        self.extra = extra

    def scan(self, root: Path, observed_at: str) -> list[Observation]:
        result = [
            Observation(
                kind="registry_integrity_failed",
                subject=Subject("repository-surface", "registry-nodes"),
                observed_at=observed_at,
                source=self.id,
                status="drift",
                current_state={"valid": True},
                observed_state={"violations": [{"path": "registry/nodes/a.json", "error": "boom"}]},
            )
        ]
        for number in range(self.extra):
            result.append(
                Observation(
                    kind="cli_contract_drift",
                    subject=Subject("repository-surface", f"surface-{number}"),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"declared": True},
                    observed_state={"missing": number},
                )
            )
        return result


def _controller(sensor: IntegritySensor) -> StewardController:
    return StewardController(sensors=[sensor], clock=lambda: FROZEN)


def _diff(path: str = "scripts/fix.py", *, removed_assert: bool = False) -> str:
    body = "-    assert old_guard()\n" if removed_assert else "-old line\n"
    return (
        f"diff --git a/{path} b/{path}\n"
        "index 1111111..2222222 100644\n"
        f"--- a/{path}\n"
        f"+++ b/{path}\n"
        "@@ -1 +1 @@\n"
        f"{body}"
        "+new line\n"
    )


def _transcript(*, items: int, exit_code: int = 0) -> str:
    return json.dumps(
        {
            "schemaVersion": PROOF_TRANSCRIPT_SCHEMA,
            "entries": [
                {
                    "contractIndex": index,
                    "command": f"python scripts/validate.py # item {index}",
                    "exitCode": exit_code,
                    "output": f"proof output for item {index}",
                }
                for index in range(1, items + 1)
            ],
        }
    )


def _write(root: Path, name: str, text: str) -> Path:
    path = root / name
    path.write_text(text, encoding="utf-8")
    return path


def _packet(**overrides: object) -> DispatchPacket:
    defaults: dict[str, object] = {
        "debt": {"id": "debt:x", "kind": "registry_integrity_failed", "source": "registry-integrity"},
        "evidence": {"debtId": "debt:x"},
        "authority": AuthorityClass.B,
        "rule": "registry-integrity-review",
        "routine": "gaia-registry-integrity-review",
        "objective": "Repair the reported violation.",
        "allowed_paths": ("scripts/**", "tests/**"),
        "allowed_commands": ("python scripts/validate.py",),
        "forbidden_paths": ("registry/**", "founder/**"),
        "stop_conditions": ("scope expands",),
        "proof": ("reproduce the violation", "show a confined diff"),
        "budget": RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0),
        "capability": "Sustained reasoning across a schema and a graph at once.",
    }
    defaults.update(overrides)
    return DispatchPacket.create(**defaults)  # type: ignore[arg-type]


def _evaluate(**overrides: object):
    packet = overrides.pop("packet", None) or _packet()
    defaults: dict[str, object] = {
        "packet": packet,
        "change_set": parse_unified_diff(_diff()),
        "transcript": parse_proof_transcript(_transcript(items=2), proof_contract_length=2),
        "debt_source": "registry-integrity",
        "sensor_sources": ("registry-integrity",),
        "baseline_open_debt": ["debt:x"],
        "current_open_debt": ["debt:x"],
        "authority_still_class_b": True,
    }
    defaults.update(overrides)
    return evaluate(**defaults)  # type: ignore[arg-type]


# --- diff parsing ------------------------------------------------------------


def test_a_header_cannot_launder_a_write_into_a_forbidden_path() -> None:
    """The bypass that decided how this parser reads a diff.

    ``git apply`` takes the path it writes from the ``---``/``+++`` pair, not
    from ``diff --git``. A parser that trusted the header could be handed one
    naming an allowed path above a body naming a forbidden one: it would count
    the hunk against ``scripts/ok.py``, report ``scopeValid: True``, and the
    patch would write ``registry/nodes/x.json`` — inside the exact scope the
    envelope forbids. The header is corroboration now, and must agree.
    """

    laundered = (
        "diff --git a/scripts/ok.py b/scripts/ok.py\n"
        "--- a/registry/nodes/x.json\n"
        "+++ b/registry/nodes/x.json\n"
        "@@ -1 +1 @@\n-{}\n+{\"owned\": true}\n"
    )
    with pytest.raises(VerificationError, match="the two must agree"):
        parse_unified_diff(laundered)

    # And with no header at all, the body still decides — so the forbidden path
    # is seen, scope-checked, and rejected rather than silently skipped.
    headerless = (
        "--- a/registry/nodes/x.json\n"
        "+++ b/registry/nodes/x.json\n"
        "@@ -1 +1 @@\n-{}\n+{\"owned\": true}\n"
    )
    assert parse_unified_diff(headerless).paths == ("registry/nodes/x.json",)
    verdict = _evaluate(change_set=parse_unified_diff(headerless))
    assert verdict.verdict == "reject"
    assert not verdict.scope_valid


def test_a_removed_line_that_looks_like_a_header_is_content() -> None:
    """Hunks are consumed by their declared length, so content cannot pose.

    Without counting, deleting a line that happens to read ``--- a/somewhere``
    would start a new file section — the same bypass wearing different clothes.
    """

    text = (
        "diff --git a/scripts/one.py b/scripts/one.py\n"
        "--- a/scripts/one.py\n+++ b/scripts/one.py\n"
        "@@ -1,2 +1,2 @@\n"
        "---- a/registry/nodes/x.json\n"
        "-+++ b/registry/nodes/x.json\n"
        "+clean\n"
        "+lines\n"
    )
    change_set = parse_unified_diff(text)
    assert change_set.paths == ("scripts/one.py",)
    assert change_set.changes[0].removed == 2


def test_diff_parsing_reports_paths_counts_and_deletions() -> None:
    text = (
        "diff --git a/scripts/one.py b/scripts/one.py\n"
        "--- a/scripts/one.py\n+++ b/scripts/one.py\n@@ -1 +1,2 @@\n-gone\n+kept\n+added\n"
        "diff --git a/tests/two.py b/tests/two.py\n"
        "deleted file mode 100644\n--- a/tests/two.py\n+++ /dev/null\n@@ -1 +0,0 @@\n-    assert thing()\n"
    )
    change_set = parse_unified_diff(text)
    assert change_set.paths == ("scripts/one.py", "tests/two.py")
    assert change_set.changes[0].added == 2 and change_set.changes[0].removed == 1
    assert change_set.deleted_guard_files == ("tests/two.py",)
    assert change_set.guard_signal_removed == 1


@pytest.mark.parametrize(
    "text, message",
    [
        ("diff --git a/one b/two\n@@ -1 +1 @@\n-a\n+b\n", "renames"),
        ('diff --git "a/one two" "b/one two"\n', "quoted"),
        ("diff --git a//etc/passwd b//etc/passwd\n", "unsafe"),
        ("diff --git a/one\n", "unparseable"),
        ("+++ stray content\n+line\n", "no matching old-file line"),
        ("@@ -1 +1 @@\n-a\n+b\n", "hunk belongs to no file"),
        ("--- a/x\n+++ b/x\n@@ -1,3 +1 @@\n-a\n", "ends inside an unfinished hunk"),
        ("--- a/x\n+++ b/x\n@@ -1 +1 @@\n-a\n+b\nstray\n", "outside any hunk"),
        ("--- /dev/null\n+++ /dev/null\n", "/dev/null on both sides"),
        ("--- a/x\n+++ b/y\n@@ -1 +1 @@\n-a\n+b\n", "rewrites"),
        ("", "touches no files"),
        (
            "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -0,0 +1 @@\n+a\n"
            "diff --git a/x b/x\n--- a/x\n+++ b/x\n@@ -0,0 +1 @@\n+b\n",
            "same path twice",
        ),
        (
            "diff --git a/one b/one\nrename from one\nrename to two\n",
            "renames are not verifiable",
        ),
    ],
)
def test_diff_parsing_fails_closed_on_anything_it_cannot_attribute(text: str, message: str) -> None:
    with pytest.raises(VerificationError, match=message):
        parse_unified_diff(text)


def test_diff_parsing_refuses_an_oversized_document() -> None:
    with pytest.raises(VerificationError, match="2 MiB"):
        parse_unified_diff("diff --git a/x b/x\n" + "+padding\n" * 400_000)


# --- proof transcript --------------------------------------------------------


def test_proof_transcript_reports_coverage_and_failures() -> None:
    transcript = parse_proof_transcript(_transcript(items=2), proof_contract_length=2)
    assert transcript.covered() == {1, 2}
    assert transcript.failures() == ()
    failing = parse_proof_transcript(_transcript(items=2, exit_code=1), proof_contract_length=2)
    assert len(failing.failures()) == 2


@pytest.mark.parametrize(
    "payload, message",
    [
        ('{"schemaVersion": "wrong", "entries": []}', "schemaVersion"),
        (f'{{"schemaVersion": "{PROOF_TRANSCRIPT_SCHEMA}", "entries": []}}', "non-empty list"),
        (
            f'{{"schemaVersion": "{PROOF_TRANSCRIPT_SCHEMA}", "entries": '
            '[{"contractIndex": 9, "command": "x", "exitCode": 0}]}',
            "outside the packet",
        ),
        (
            f'{{"schemaVersion": "{PROOF_TRANSCRIPT_SCHEMA}", "entries": '
            '[{"contractIndex": true, "command": "x", "exitCode": 0}]}',
            "contractIndex must be an integer",
        ),
        (
            f'{{"schemaVersion": "{PROOF_TRANSCRIPT_SCHEMA}", "entries": '
            '[{"contractIndex": 1, "command": "x", "exitCode": true}]}',
            "exitCode must be an integer",
        ),
        ("not json", "invalid proof transcript JSON"),
    ],
)
def test_proof_transcript_fails_closed(payload: str, message: str) -> None:
    with pytest.raises(VerificationError, match=message):
        parse_proof_transcript(payload, proof_contract_length=2)


# --- the verdict matrix ------------------------------------------------------


def test_a_clean_candidate_stays_pending_and_is_never_accepted() -> None:
    verdict = _evaluate()
    assert verdict.verdict == "pending"
    assert not verdict.decided
    assert verdict.scope_valid and verdict.proof_valid and verdict.finding_confirmed
    assert "independent judgment" in " ".join(verdict.reasons)


@pytest.mark.parametrize(
    "overrides, expected, marker",
    [
        ({"change_set": parse_unified_diff(_diff("docs/site.html"))}, "reject", "outside allowedPaths"),
        ({"change_set": parse_unified_diff(_diff("registry/nodes/a.json"))}, "reject", "forbiddenPaths"),
        (
            {"transcript": parse_proof_transcript(_transcript(items=1), proof_contract_length=2)},
            "reject",
            "no evidence",
        ),
        (
            {"transcript": parse_proof_transcript(_transcript(items=2, exit_code=2), proof_contract_length=2)},
            "reject",
            "exited non-zero",
        ),
        ({"debt_source": "a-helpful-agent"}, "reject", "asserted, not observed"),
        ({"authority_still_class_b": False}, "escalate", "no longer classified Class B"),
        (
            {"change_set": parse_unified_diff(_diff("tests/guard.py", removed_assert=True))},
            "escalate",
            "guard assertions",
        ),
        ({"current_open_debt": ["debt:x", "debt:y"]}, "escalate", "new debt appeared"),
    ],
)
def test_each_disqualifying_fact_reaches_its_own_verdict(
    overrides: dict[str, object], expected: str, marker: str
) -> None:
    verdict = _evaluate(**overrides)
    assert verdict.verdict == expected
    assert any(marker in reason for reason in verdict.reasons), verdict.reasons


def test_a_deleted_guard_file_escalates() -> None:
    text = (
        "diff --git a/tests/steward/test_repairs.py b/tests/steward/test_repairs.py\n"
        "deleted file mode 100644\n--- a/tests/steward/test_repairs.py\n+++ /dev/null\n"
        "@@ -1,2 +0,0 @@\n-def test_thing():\n-    assert True\n"
    )
    verdict = _evaluate(change_set=parse_unified_diff(text))
    assert verdict.verdict == "escalate"
    assert verdict.guards_weakened


def test_machinery_can_never_accept_under_any_combination_of_facts() -> None:
    """The load-bearing invariant of V1.3.

    Steward decides what work exists and whether it stayed inside its envelope.
    It does not decide that work is good. If any combination of mechanical facts
    could produce ``accept``, autonomous Class B integration would rest on a
    check that never looked at whether the patch does anything.
    """

    matrix = itertools.product([True, False], repeat=6)
    seen: set[str] = set()
    for scope, proof, finding, authority, guards, new_debt in matrix:
        if guards:
            diff_text = _diff("tests/g.py" if scope else "docs/x.html", removed_assert=True)
        else:
            diff_text = _diff("scripts/fix.py" if scope else "docs/x.html")
        verdict = _evaluate(
            change_set=parse_unified_diff(diff_text),
            transcript=parse_proof_transcript(
                _transcript(items=2, exit_code=0 if proof else 1), proof_contract_length=2
            ),
            debt_source="registry-integrity" if finding else "an-agent",
            authority_still_class_b=authority,
            current_open_debt=["debt:x", *(["debt:new"] if new_debt else [])],
        )
        assert verdict.verdict != "accept"
        assert verdict.verdict in {"reject", "escalate", "pending"}
        seen.add(verdict.verdict)

    # The matrix must actually exercise all three outcomes, or the assertion
    # above would pass on a matrix that never reached a decision at all.
    assert seen == {"reject", "escalate", "pending"}


# --- the routing transaction -------------------------------------------------


def test_verification_runs_against_the_dispatched_envelope_not_a_re_derived_one(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(IntegritySensor())
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)
    packet = dispatch.artifact

    diff_path = _write(root, "candidate.diff", _diff("scripts/fix.py"))
    proof_path = _write(root, "proof.json", _transcript(items=len(packet.proof)))

    # Narrow the policy's Class B envelope *after* dispatch. The builder was
    # commissioned under the old one and must be judged against it.
    policy_path = root / POLICY_RELATIVE_PATH
    policy_path.write_text(
        policy_path.read_text(encoding="utf-8").replace("      - scripts/**\n", ""),
        encoding="utf-8",
    )

    result, _diff_text, _outputs = render_verification(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
    )
    assert result.artifact.verdict == "pending"
    assert result.artifact.scope_valid
    assert result.receipt.action == "verify"
    assert result.receipt.to_dict()["result"]["status"] == "verdict:pending"
    assert result.receipt_path.is_file()


def test_verification_refuses_work_that_was_never_dispatched(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(IntegritySensor())
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    diff_path = _write(root, "candidate.diff", _diff())
    proof_path = _write(root, "proof.json", _transcript(items=2))

    with pytest.raises(RoutingError, match="no dispatch receipt exists"):
        render_verification(
            root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
        )


def test_new_unrelated_debt_since_dispatch_escalates(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = IntegritySensor()
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)

    sensor.extra = 1  # unrelated drift appears while the builder was working
    diff_path = _write(root, "candidate.diff", _diff())
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    result, _diff_text, _outputs = render_verification(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
    )
    assert result.artifact.verdict == "escalate"
    assert result.artifact.new_debt


def test_a_dispatch_receipt_edited_after_publication_is_not_evidence(tmp_path: Path) -> None:
    """Widening the envelope in local state must not widen what was authorized.

    ``dispatchId`` deliberately covers only the *semantic* identity of the work
    — debt, authority, rule — so a re-render on refreshed evidence keeps one
    identity. That leaves the envelope itself uncovered, so the receipt has to
    be checked against its own content hash instead.
    """

    root = _repo(tmp_path)
    controller = _controller(IntegritySensor())
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)

    receipt_path = dispatch.receipt_path
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    data["artifact"]["allowedPaths"] = ["docs/**", "registry/**"]
    receipt_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    diff_path = _write(root, "candidate.diff", _diff("registry/nodes/a.json"))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    with pytest.raises(RoutingError, match="no longer matches its own content hash"):
        render_verification(
            root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
        )


def test_a_tampered_packet_identity_is_rejected_on_restore() -> None:
    data = _packet().to_dict()
    data["rule"] = "some-other-rule"
    with pytest.raises(ValueError, match="identity does not match"):
        DispatchPacket.from_dict(data)


# --- the verifier prompt -----------------------------------------------------


def test_prompt_is_refused_once_machinery_has_already_decided(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(IntegritySensor())
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)
    diff_path = _write(root, "candidate.diff", _diff("docs/leak.html"))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))

    with pytest.raises(VerificationError, match="already reached 'reject'"):
        render_verifier_prompt_for(
            root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
        )


def test_prompt_carries_the_envelope_the_diff_and_the_proof(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(IntegritySensor())
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)
    diff_path = _write(root, "candidate.diff", _diff("scripts/fix.py"))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))

    _result, prompt = render_verifier_prompt_for(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
    )
    assert "independent verifier" in prompt
    assert "scripts/fix.py" in prompt
    assert "proof output for item 1" in prompt
    assert "accept | reject | escalate" in prompt
    assert "registry/**" in prompt  # the forbidden scope travels with the prompt
    assert "founder/steward/routines/registry-integrity-review.md" in prompt


def test_the_verifier_prompt_cannot_be_handed_builder_narrative() -> None:
    """Independence is structural, not a matter of prompt etiquette.

    A verifier that reads the builder's account of the work is verifying the
    account, not the change. The renderer therefore accepts no free-text field
    the builder controls: it takes the packet, the machine verdict, the routine
    contract, the diff, and captured command output — nothing else.
    """

    parameters = set(inspect.signature(render_verifier_prompt).parameters)
    assert parameters == {
        "packet",
        "verdict",
        "prompt_guide",
        "diff_text",
        "proof_outputs",
        "receipt",
    }


def test_a_harness_is_never_named_in_the_verifier_prompt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(IntegritySensor())
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)
    diff_path = _write(root, "candidate.diff", _diff("scripts/fix.py"))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    _result, prompt = render_verifier_prompt_for(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
    )

    import re

    for name in ("claude", "hermes", "codex", "gpt", "gemini", "opus", "sonnet", "sol", "terra", "luna"):
        assert not re.search(rf"\b{name}\b", prompt, flags=re.IGNORECASE), name
