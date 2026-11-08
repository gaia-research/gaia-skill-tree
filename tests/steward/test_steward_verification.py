"""Steward V1.3 — independent verification of one dispatched Class B patch."""

from __future__ import annotations

import inspect
import itertools
import json
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path
import shutil
import subprocess

import pytest

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.models import AuthorityClass, DispatchPacket, Observation, RoutingBudget, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.prompt import render_verifier_prompt
from gaia_cli.steward.routing import (
    RoutingError,
    compute_patch_attribution,
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
    path.parent.mkdir(parents=True, exist_ok=True)
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
    _write(root, "scripts/fix.py", "old line\n")
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
    _write(root, "scripts/fix.py", "old line\n")
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
    _write(root, "scripts/fix.py", "old line\n")
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    _result, prompt = render_verifier_prompt_for(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
    )

    import re

    for name in ("claude", "hermes", "codex", "gpt", "gemini", "opus", "sonnet", "sol", "terra", "luna"):
        assert not re.search(rf"\b{name}\b", prompt, flags=re.IGNORECASE), name


def test_independent_review_is_discharged_by_the_process_not_the_builder() -> None:
    packet = _packet(proof=("reproduce the violation", "show a confined diff", "obtain independent review before integration"))
    transcript = parse_proof_transcript(_transcript(items=2), proof_contract_length=3)
    verdict = _evaluate(packet=packet, transcript=transcript)
    # Still pending: the exemption never turns a machine verdict into acceptance.
    assert verdict.verdict == "pending" and verdict.proof_valid and not verdict.decided


def test_the_review_exemption_does_not_cover_any_other_proof_item() -> None:
    packet = _packet(proof=("reproduce the violation", "show a confined diff", "obtain independent review before integration"))
    transcript = parse_proof_transcript(_transcript(items=1), proof_contract_length=3)
    verdict = _evaluate(packet=packet, transcript=transcript)
    assert verdict.verdict == "reject"
    assert "no evidence: 2" in " ".join(verdict.reasons)


# --- Ruling 1 patch attribution tests ----------------------------------------


def test_attribution_evaluates_unrelated_debt_without_escalation() -> None:
    """Under Ruling 1, unrelated concurrent global debt is not charged to the patch."""
    verdict = _evaluate(
        current_open_debt=["debt:x", "unrelated:1"],
        patch_introduced_debt=(),
    )
    assert verdict.verdict == "pending"
    assert verdict.new_debt == ()
    assert verdict.unrelated_new_debt == ("unrelated:1",)
    assert verdict.global_new_debt == ("unrelated:1",)
    assert any("concurrent merge, not charged to patch" in r for r in verdict.reasons)


def test_attribution_evaluates_patch_introduced_debt_with_escalation() -> None:
    """Patch-introduced debt escalates the verdict and is charged to the repair."""
    verdict = _evaluate(
        current_open_debt=["debt:x", "patch:debt", "unrelated:debt"],
        patch_introduced_debt=["patch:debt"],
    )
    assert verdict.verdict == "escalate"
    assert verdict.new_debt == ("patch:debt",)
    assert verdict.unrelated_new_debt == ("unrelated:debt",)
    assert verdict.global_new_debt == ("patch:debt", "unrelated:debt")
    assert any("patch introduced new debt: patch:debt" in r for r in verdict.reasons)
    assert any("concurrent merge, not charged to patch" in r for r in verdict.reasons)


def test_attribution_fails_closed_when_attribution_is_none() -> None:
    """When attribution cannot be computed (None), evaluate fails closed."""
    verdict = _evaluate(
        current_open_debt=["debt:x", "unknown:debt"],
        patch_introduced_debt=None,
    )
    assert verdict.verdict == "escalate"
    assert verdict.new_debt == ("unknown:debt",)
    assert verdict.unrelated_new_debt == ()
    assert verdict.global_new_debt == ("unknown:debt",)
    assert any("attribution could not be computed, failing closed" in r for r in verdict.reasons)


def test_attribution_verdict_to_dict_includes_global_and_unrelated_debt() -> None:
    verdict = _evaluate(
        current_open_debt=["debt:x", "unrelated:1"],
        patch_introduced_debt=(),
    )
    data = verdict.to_dict()
    assert data["newDebt"] == []
    assert data["globalNewDebt"] == ["unrelated:1"]
    assert data["unrelatedNewDebt"] == ["unrelated:1"]


def test_compute_patch_attribution_clean_patch_returns_empty_tuple(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(root, "scripts/fix.py", "old line\n")
    sensor = IntegritySensor()
    controller = _controller(sensor)
    diff = _diff("scripts/fix.py")
    introduced = compute_patch_attribution(
        repo_root=root,
        diff_text=diff,
        target_debt_id="debt:x",
        controller=controller,
    )
    assert introduced == ()


def test_compute_patch_attribution_fails_closed_on_unapplicable_patch(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    sensor = IntegritySensor()
    controller = _controller(sensor)
    diff = _diff("scripts/nonexistent.py")
    introduced = compute_patch_attribution(
        repo_root=root,
        diff_text=diff,
        target_debt_id="debt:x",
        controller=controller,
    )
    assert introduced is None


def test_render_verification_with_clean_patch_does_not_escalate_on_unrelated_debt(tmp_path: Path) -> None:
    """Integration: when the base file exists, diff applies cleanly, and unrelated debt appears."""
    root = _repo(tmp_path)
    _write(root, "scripts/fix.py", "old line\n")
    sensor = IntegritySensor()
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)

    # Unrelated drift appears while builder worked
    sensor.extra = 1
    diff_path = _write(root, "candidate.diff", _diff("scripts/fix.py"))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))

    result, _diff_text, _outputs = render_verification(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller
    )
    assert result.artifact.verdict == "pending"
    assert result.artifact.new_debt == ()
    assert len(result.artifact.unrelated_new_debt) == 1
    assert result.artifact.global_new_debt == result.artifact.unrelated_new_debt


def test_attribution_evaluates_patch_introduced_debt_when_global_delta_is_empty() -> None:
    """When global delta is empty, patch-introduced debt still escalates."""
    verdict = _evaluate(
        baseline_open_debt=["debt:x"],
        current_open_debt=["debt:x"],
        patch_introduced_debt=["patch:new"],
    )
    assert verdict.verdict == "escalate"
    assert verdict.new_debt == ("patch:new",)
    assert verdict.global_new_debt == ()
    assert verdict.unrelated_new_debt == ()
    assert any("patch introduced new debt: patch:new" in r for r in verdict.reasons)


def test_attribution_evaluates_patch_introduced_debt_already_in_baseline() -> None:
    """A patch introducing a debt that was in dispatch baseline is still charged to the patch."""
    verdict = _evaluate(
        baseline_open_debt=["debt:x", "baseline:existing"],
        current_open_debt=["debt:x", "baseline:existing"],
        patch_introduced_debt=["baseline:existing"],
    )
    assert verdict.verdict == "escalate"
    assert verdict.new_debt == ("baseline:existing",)
    assert verdict.global_new_debt == ()
    assert verdict.unrelated_new_debt == ()
    assert any("patch introduced new debt: baseline:existing" in r for r in verdict.reasons)


def test_real_git_repo_with_worktrees_and_concurrent_merge(tmp_path: Path) -> None:
    """In a real git repo, patch attribution uses git worktrees and isolates concurrent merge debt."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Steward"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "steward@example.com"], cwd=root, check=True)

    # Copy policy into repo
    policy_dst = root / POLICY_RELATIVE_PATH
    policy_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy_dst)

    # Create target file
    _write(root, "scripts/fix.py", "old line\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=root, check=True)

    # Base commit at dispatch time
    rev_base = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True
    ).stdout.strip()

    sensor = IntegritySensor()
    controller = _controller(sensor)
    scan = controller.scan(root)
    debt_id = scan.open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)

    # Concurrent merge commit on main branch that introduces an unrelated debt
    _write(root, "scripts/concurrent.py", "# concurrent change\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "Concurrent merge commit"], cwd=root, check=True)
    sensor.extra = 1  # Unrelated drift appears globally

    # Candidate patch was cut against base_commit
    diff_path = _write(root, "candidate.diff", _diff("scripts/fix.py"))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))

    result, _diff_text, _outputs = render_verification(
        root,
        debt_id,
        diff_path=diff_path,
        proof_path=proof_path,
        controller=controller,
    )
    assert dispatch.artifact.head_commit == rev_base
    assert result.artifact.verdict == "pending"
    assert result.artifact.new_debt == ()
    assert len(result.artifact.unrelated_new_debt) == 1
    assert result.artifact.global_new_debt == result.artifact.unrelated_new_debt
    assert any("concurrent merge, not charged to patch" in r for r in result.artifact.reasons)


def test_git_dispatch_without_recorded_base_fails_closed_even_with_caller_base(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import gaia_cli.steward.routing as routing

    root = _repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test Steward"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "steward@example.com"], cwd=root, check=True)
    _write(root, "scripts/fix.py", "old line\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    base = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=root, text=True).strip()
    controller = _controller(IntegritySensor())
    debt_id = controller.scan(root).open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)
    diff_path = _write(root, "candidate.diff", _diff("scripts/fix.py"))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    original = routing._dispatch_receipt_for

    def legacy_receipt(*args, **kwargs):
        receipt = original(*args, **kwargs)
        receipt = dict(receipt)
        receipt["artifact"] = dict(receipt["artifact"])
        for field in ("headCommit", "gitHead"):
            receipt.pop(field, None)
            receipt["artifact"].pop(field, None)
        return receipt

    monkeypatch.setattr(routing, "_dispatch_receipt_for", legacy_receipt)
    result, _, _ = render_verification(
        root, debt_id, diff_path=diff_path, proof_path=proof_path,
        controller=controller, base_commit=base,
    )
    assert result.artifact.attribution_failed is True
    assert result.artifact.verdict == "escalate"


def test_supplied_base_must_match_dispatch_receipt(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.name", "Test Steward"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "steward@example.com"], cwd=root, check=True)
    _write(root, "scripts/fix.py", "old line\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-qm", "initial"], cwd=root, check=True)
    controller = _controller(IntegritySensor())
    debt_id = controller.scan(root).open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)
    diff_path = _write(root, "candidate.diff", _diff("scripts/fix.py"))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    with pytest.raises(RoutingError, match="supplied base_commit does not match authenticated dispatch receipt base"):
        render_verification(root, debt_id, diff_path=diff_path, proof_path=proof_path,
                            controller=controller, base_commit="different-base")


def test_git_attribution_requires_explicit_baseline(tmp_path: Path) -> None:
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    assert compute_patch_attribution(tmp_path, "", "debt:x", _controller(IntegritySensor())) is None


@pytest.mark.parametrize("field", ["not_evaluated", "partial_coverage"])
@pytest.mark.parametrize("incomplete_scan", [0, 1])
def test_incomplete_scratch_coverage_fails_closed(
    tmp_path: Path, field: str, incomplete_scan: int, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    _write(root, "scripts/fix.py", "old line\n")
    controller = _controller(IntegritySensor())
    original_scan = controller.scan
    calls = 0

    def scan(path: Path):
        nonlocal calls
        result = original_scan(path)
        if calls == incomplete_scan:
            result = replace(result, receipt=replace(result.receipt, **{field: ({"sensor": "missing"},)}))
        calls += 1
        return result

    monkeypatch.setattr(controller, "scan", scan)
    assert compute_patch_attribution(root, _diff("scripts/fix.py"), "debt:x", controller) is None
    assert calls == 2


def test_missing_specific_dispatch_never_falls_back(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    controller = _controller(IntegritySensor())
    debt_id = controller.scan(root).open_debts[0].id
    render_dispatch(root, debt_id, controller=controller)
    render_dispatch(root, debt_id, controller=controller)
    with pytest.raises(RoutingError, match="no dispatch receipt found for dispatch missing"):
        render_verification(root, debt_id, diff_path=root / "none", proof_path=root / "none",
                            controller=controller, dispatch_id="missing")


def test_unknown_sensor_coverage_on_scratch_scan_fails_closed(tmp_path: Path) -> None:
    """When a sensor fails during scratch scan, attribution fails closed (returns None)."""
    root = _repo(tmp_path)
    _write(root, "scripts/fix.py", "old line\n")

    class FaultySensor:
        id = "faulty-sensor"

        def scan(self, path: Path, observed_at: str) -> list[Observation]:
            raise RuntimeError("sensor failure during scratch scan")

    controller = StewardController(sensors=[IntegritySensor(), FaultySensor()], clock=lambda: FROZEN)
    diff = _diff("scripts/fix.py")
    introduced = compute_patch_attribution(
        repo_root=root,
        diff_text=diff,
        target_debt_id="debt:x",
        controller=controller,
    )
    assert introduced is None


def test_worktree_creation_failure_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """If git worktree creation fails, attribution does not fall back to copying; it fails closed."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Steward"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "steward@example.com"], cwd=root, check=True)

    policy_dst = root / POLICY_RELATIVE_PATH
    policy_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy_dst)

    _write(root, "scripts/fix.py", "old line\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=root, check=True)

    sensor = IntegritySensor()
    controller = _controller(sensor)
    diff = _diff("scripts/fix.py")

    base_commit = subprocess.run(["git", "rev-parse", "HEAD"], cwd=root, check=True, capture_output=True, text=True).stdout.strip()
    orig_run = subprocess.run
    worktree_attempted = False

    def mock_run(cmd, *args, **kwargs):
        nonlocal worktree_attempted
        if isinstance(cmd, list) and len(cmd) >= 3 and cmd[:3] == ["git", "worktree", "add"]:
            worktree_attempted = True
            return subprocess.CompletedProcess(cmd, returncode=1, stdout="", stderr="fatal: mock failure")
        return orig_run(cmd, *args, **kwargs)

    monkeypatch.setattr(subprocess, "run", mock_run)

    introduced = compute_patch_attribution(
        repo_root=root,
        diff_text=diff,
        target_debt_id="debt:x",
        controller=controller,
        base_commit=base_commit,
    )
    assert worktree_attempted
    assert introduced is None


def test_attribution_failed_true_escalates_even_with_empty_global_new_debt() -> None:
    """If attribution_failed is True, evaluate fails closed (escalates) even if global_new_debt is empty."""
    verdict = _evaluate(
        baseline_open_debt=["debt:x"],
        current_open_debt=["debt:x"],
        attribution_failed=True,
    )
    assert verdict.verdict == "escalate"
    assert verdict.attribution_failed is True
    assert verdict.global_new_debt == ()
    assert any("patch attribution failed; failing closed on safety gate" in r for r in verdict.reasons)


def test_compute_patch_attribution_unresolvable_base_commit_in_git_repo_fails_closed(tmp_path: Path) -> None:
    """In a git repo, if base commit cannot be resolved, attribution fails closed (returns None)."""
    root = tmp_path / "repo"
    root.mkdir()
    subprocess.run(["git", "init", "-b", "main"], cwd=root, check=True, capture_output=True)
    subprocess.run(["git", "config", "user.name", "Test Steward"], cwd=root, check=True)
    subprocess.run(["git", "config", "user.email", "steward@example.com"], cwd=root, check=True)

    policy_dst = root / POLICY_RELATIVE_PATH
    policy_dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy_dst)

    _write(root, "scripts/fix.py", "old line\n")
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=root, check=True)

    sensor = IntegritySensor()
    controller = _controller(sensor)
    diff = _diff("scripts/fix.py")

    introduced = compute_patch_attribution(
        repo_root=root,
        diff_text=diff,
        target_debt_id="debt:x",
        controller=controller,
        base_commit="nonexistent_commit_hash_123456",
    )
    assert introduced is None


# --- Legacy dispatch receipts: runner-recorded, authenticated baseline (#2371) ---


def _git(root: Path, *args: str) -> str:
    return subprocess.run(["git", *args], cwd=root, check=True, capture_output=True, text=True).stdout.strip()


def _blob(root: Path, text: str) -> str:
    return subprocess.run(
        ["git", "hash-object", "--stdin"], cwd=root, input=text, check=True, capture_output=True, text=True
    ).stdout.strip()


def _real_diff(root: Path, path: str = "scripts/fix.py", old: str = "old line\n", new: str = "new line\n") -> str:
    return (
        f"diff --git a/{path} b/{path}\n"
        f"index {_blob(root, old)[:12]}..{_blob(root, new)[:12]} 100644\n"
        f"--- a/{path}\n+++ b/{path}\n@@ -1 +1 @@\n-{old}+{new}"
    )


def _legacy_repo(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    """A git repo whose dispatch receipt predates headCommit (the legacy campaign format)."""
    from gaia_cli.steward import routing

    root = _repo(tmp_path)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "Test Steward")
    _git(root, "config", "user.email", "steward@example.com")
    _write(root, "scripts/fix.py", "old line\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "initial")
    base = _git(root, "rev-parse", "HEAD")
    controller = _controller(IntegritySensor())
    debt_id = controller.scan(root).open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)
    original = routing._dispatch_receipt_for

    def legacy_receipt(*args, **kwargs):
        receipt = dict(original(*args, **kwargs))
        receipt["artifact"] = dict(receipt["artifact"])
        for field in ("headCommit", "gitHead"):
            receipt.pop(field, None)
            receipt["artifact"].pop(field, None)
        return receipt

    monkeypatch.setattr(routing, "_dispatch_receipt_for", legacy_receipt)
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    return root, base, controller, debt_id, proof_path


def test_legacy_receipt_uses_authenticated_runner_baseline(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root, base, controller, debt_id, proof_path = _legacy_repo(tmp_path, monkeypatch)
    # The branch moved on after dispatch: the recorded head is history, not the tip.
    _write(root, "scripts/other.py", "later\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "later merge")
    diff_path = _write(root, "candidate.diff", _real_diff(root))
    result, _, _ = render_verification(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller,
        runner_baseline={"commit": base, "branchRef": "refs/heads/main"},
    )
    verdict = result.artifact
    assert verdict.attribution_failed is False
    assert verdict.verdict == "pending"
    assert any("runner-recorded integration head" in r and base in r for r in verdict.reasons)


@pytest.mark.parametrize("case", ["not-ancestor", "preimage-mismatch", "no-index", "abbrev", "unknown", "no-branch"])
def test_legacy_runner_baseline_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, case: str) -> None:
    root, base, controller, debt_id, proof_path = _legacy_repo(tmp_path, monkeypatch)
    commit, branch_ref, diff = base, "refs/heads/main", _real_diff(root)
    if case == "not-ancestor":
        # Same tree and before-images, but a commit that never landed on the branch.
        commit = _git(root, "commit-tree", f"{base}^{{tree}}", "-p", base, "-m", "off-branch")
    elif case == "preimage-mismatch":
        diff = _real_diff(root, old="something else\n")
    elif case == "no-index":
        diff = "--- a/scripts/fix.py\n+++ b/scripts/fix.py\n@@ -1 +1 @@\n-old line\n+new line\n"
    elif case == "abbrev":
        commit = base[:12]
    elif case == "unknown":
        commit = "unknown"
    else:
        branch_ref = "refs/remotes/origin/missing"
    diff_path = _write(root, "candidate.diff", diff)
    result, _, _ = render_verification(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller,
        runner_baseline={"commit": commit, "branchRef": branch_ref},
    )
    assert result.artifact.attribution_failed is True
    assert result.artifact.verdict == "escalate"
    assert any(r.startswith("runner baseline rejected: ") for r in result.artifact.reasons)


def test_receipt_head_commit_outranks_runner_baseline(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "Test Steward")
    _git(root, "config", "user.email", "steward@example.com")
    _write(root, "scripts/fix.py", "old line\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "initial")
    controller = _controller(IntegritySensor())
    debt_id = controller.scan(root).open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)
    diff_path = _write(root, "candidate.diff", _real_diff(root))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    result, _, _ = render_verification(
        root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller,
        runner_baseline={"commit": "0" * 40, "branchRef": "refs/heads/nope"},
    )
    assert result.artifact.attribution_failed is False
    assert not any("runner baseline" in r for r in result.artifact.reasons)


def test_diff_preimages_parsing() -> None:
    from gaia_cli.steward.routing import _diff_preimages

    new = "diff --git a/n.py b/n.py\nnew file mode 100644\nindex 0000000..abcdef1\n--- /dev/null\n+++ b/n.py\n@@ -0,0 +1 @@\n+x\n"
    rename = (
        "diff --git a/o.py b/p.py\nsimilarity index 90%\nrename from o.py\nrename to p.py\n"
        "index abcdef1..1234567 100644\n--- a/o.py\n+++ b/p.py\n@@ -1 +1 @@\n-a\n+b\n"
    )
    assert _diff_preimages(new) == [("n.py", "0000000", True)]
    assert _diff_preimages(rename) == [("o.py", "abcdef1", False)]
    assert _diff_preimages("diff --git a/m b/m\nold mode 100644\nnew mode 100755\n") is None
    assert _diff_preimages("diff --git a/s b/s\nindex abc..def 100644\n--- a/s\n+++ b/s\n") is None
    assert _diff_preimages('diff --git "a/q x" "b/q x"\nindex abcdef1..1234567\n--- "a/q x"\n+++ "b/q x"\n') is None
    assert _diff_preimages("diff --git a/z b/z\nindex 0000000..abcdef1\n--- a/z\n+++ b/z\n") is None
    assert _diff_preimages("") is None


def test_runner_baseline_rejects_created_file_that_exists(tmp_path: Path) -> None:
    from gaia_cli.steward.routing import authenticate_runner_baseline

    root = tmp_path
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "T")
    _git(root, "config", "user.email", "t@example.com")
    _write(root, "n.py", "x\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "i")
    head = _git(root, "rev-parse", "HEAD")
    diff = "diff --git a/n.py b/n.py\nnew file mode 100644\nindex 0000000..abcdef1\n--- /dev/null\n+++ b/n.py\n@@ -0,0 +1 @@\n+x\n"
    commit, reason = authenticate_runner_baseline(root, head, "refs/heads/main", diff)
    assert commit is None and "already exists" in reason
    ok, _ = authenticate_runner_baseline(root, head, "refs/heads/main", diff.replace("n.py", "m.py"))
    assert ok == head


def _hashed_dispatch(tmp_path: Path):
    from gaia_cli.steward import routing

    root = _repo(tmp_path)
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.name", "Test Steward")
    _git(root, "config", "user.email", "steward@example.com")
    _write(root, "scripts/fix.py", "old line\n")
    _git(root, "add", ".")
    _git(root, "commit", "-qm", "initial")
    base = _git(root, "rev-parse", "HEAD")
    controller = _controller(IntegritySensor())
    debt_id = controller.scan(root).open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)
    policy = routing.StewardPolicy.load(root)
    directory = root / policy.state_directory / policy.receipts_directory
    receipt_path = directory / f"{routing._dispatch_receipt_for(directory, debt_id)['runId']}.json"
    diff_path = _write(root, "candidate.diff", _real_diff(root))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    return root, base, controller, debt_id, receipt_path, diff_path, proof_path


@pytest.mark.parametrize("field", ["headCommit", "gitHead"])
@pytest.mark.parametrize("same_value", [True, False])
def test_top_level_receipt_head_is_unauthenticated_and_refused(tmp_path: Path, field: str, same_value: bool) -> None:
    """Top-level fields sit outside the receipt digest: their presence fails closed, never steers the base."""
    root, base, controller, debt_id, receipt_path, diff_path, proof_path = _hashed_dispatch(tmp_path)
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    data[field] = base if same_value else "f" * 40
    receipt_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RoutingError, match=f"top-level {field}"):
        render_verification(root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller,
                            runner_baseline={"commit": "unknown", "branchRef": "refs/heads/nope"})


def test_edited_artifact_head_breaks_receipt_digest(tmp_path: Path) -> None:
    root, _base, controller, debt_id, receipt_path, diff_path, proof_path = _hashed_dispatch(tmp_path)
    data = json.loads(receipt_path.read_text(encoding="utf-8"))
    data["artifact"]["headCommit"] = "f" * 40
    receipt_path.write_text(json.dumps(data), encoding="utf-8")
    with pytest.raises(RoutingError, match="no longer matches its own content"):
        render_verification(root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller)


@pytest.mark.parametrize("artifact_patch", [{"gitHead": "f" * 40}, {"headCommit": "abc1234"}])
def test_artifact_head_must_be_one_full_commit_field(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, artifact_patch: dict[str, str]
) -> None:
    """Even inside the hashed artifact, only a full-sha headCommit names a base."""
    from gaia_cli.steward import routing

    root, _base, controller, debt_id, _receipt_path, diff_path, proof_path = _hashed_dispatch(tmp_path)
    original = routing._dispatch_receipt_for

    def patched(*args, **kwargs):
        receipt = dict(original(*args, **kwargs))
        receipt["artifact"] = {**receipt["artifact"], **artifact_patch}
        return receipt

    monkeypatch.setattr(routing, "_dispatch_receipt_for", patched)
    with pytest.raises(RoutingError, match="gitHead|not a full commit id"):
        render_verification(root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller)


# --- Path validation before any apply (#2371) --------------------------------------


def _outside_layout(tmp_path: Path):
    root = _repo(tmp_path / "root")
    _write(root, "scripts/fix.py", "old line\n")
    scratch = tmp_path / "scratch"
    outside = tmp_path / "outside.txt"
    outside.write_text("unchanged\n", encoding="utf-8")
    return root, scratch, outside


OUT_OF_SCOPE_DIFFS = {
    "dotdot": "diff --git a/../../outside.txt b/../../outside.txt\n--- a/../../outside.txt\n+++ b/../../outside.txt\n"
              "@@ -1 +1 @@\n-unchanged\n+changed\n",
    "unified-dotdot": "--- a/../../outside.txt\n+++ b/../../outside.txt\n@@ -1 +1 @@\n-unchanged\n+changed\n",
    "absolute": "--- /tmp/outside.txt\n+++ /tmp/outside.txt\n@@ -1 +1 @@\n-unchanged\n+changed\n",
    "git-dir": "diff --git a/.git/config b/.git/config\n--- a/.git/config\n+++ b/.git/config\n@@ -1 +1 @@\n-a\n+b\n",
    "rename": "diff --git a/scripts/fix.py b/x\nsimilarity index 100%\nrename from scripts/fix.py\nrename to ../outside.txt\n",
    "quoted": 'diff --git "a/x y" "b/x y"\n--- "a/x y"\n+++ "b/x y"\n@@ -1 +1 @@\n-a\n+b\n',
    "backslash": "--- a/..\\outside.txt\n+++ b/..\\outside.txt\n@@ -1 +1 @@\n-unchanged\n+changed\n",
}


@pytest.mark.parametrize("name", sorted(OUT_OF_SCOPE_DIFFS))
def test_out_of_scope_paths_are_refused_before_any_scratch_exists(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    from gaia_cli.steward import routing

    root, scratch, outside = _outside_layout(tmp_path)
    created: list[str] = []
    monkeypatch.setattr(routing.tempfile, "mkdtemp", lambda **kw: created.append("x") or str(scratch))
    result = compute_patch_attribution(root, OUT_OF_SCOPE_DIFFS[name], "debt:x", _controller(IntegritySensor()))
    assert result is None
    assert created == []  # path validation ran before any filesystem action
    assert outside.read_text(encoding="utf-8") == "unchanged\n"


def test_apply_refuses_outside_paths_even_past_validation(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Second line: without --unsafe-paths, git apply itself keeps writes inside the scratch tree."""
    from gaia_cli.steward import routing

    root, scratch, outside = _outside_layout(tmp_path)
    scratch.mkdir()
    monkeypatch.setattr(routing.tempfile, "mkdtemp", lambda **kw: str(scratch))
    monkeypatch.setattr(routing, "_diff_paths_safe", lambda text: True)
    result = compute_patch_attribution(root, OUT_OF_SCOPE_DIFFS["dotdot"], "debt:x", _controller(IntegritySensor()))
    assert result is None
    assert outside.read_text(encoding="utf-8") == "unchanged\n"


def test_removed_line_that_looks_like_a_header_is_content() -> None:
    from gaia_cli.steward.routing import _diff_paths_safe

    diff = "--- a/docs/a.sql\n+++ b/docs/a.sql\n@@ -1,2 +1 @@\n--- ../../x\n keep\n"
    assert _diff_paths_safe(diff) is True
    after = diff + "--- a/../../x\n+++ b/../../x\n@@ -1 +1 @@\n-a\n+b\n"
    assert _diff_paths_safe(after) is False  # the next file's header is validated again


def test_out_of_scope_change_set_is_never_attributed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Scope is decided first; an out-of-scope change set never reaches any apply."""
    from gaia_cli.steward import routing

    root = _repo(tmp_path)
    _write(root, "scripts/fix.py", "old line\n")
    _write(root, "registry/nodes/a.json", "{}\n")
    controller = _controller(IntegritySensor())
    debt_id = controller.scan(root).open_debts[0].id
    dispatch = render_dispatch(root, debt_id, controller=controller)

    def never(*args, **kwargs):
        pytest.fail("attribution must not run on an out-of-scope change set")

    monkeypatch.setattr(routing, "compute_patch_attribution", never)
    diff_path = _write(root, "candidate.diff", _diff("registry/nodes/a.json"))
    proof_path = _write(root, "proof.json", _transcript(items=len(dispatch.artifact.proof)))
    result, _, _ = render_verification(root, debt_id, diff_path=diff_path, proof_path=proof_path, controller=controller)
    assert result.artifact.verdict == "reject"
    assert result.artifact.scope_valid is False
    assert "patch attribution not run: the change set is out of scope" in result.artifact.reasons
    assert (root / "registry/nodes/a.json").read_text(encoding="utf-8") == "{}\n"
