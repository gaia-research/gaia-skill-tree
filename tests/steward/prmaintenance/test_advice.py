"""A held pull request's founder card keeps a procedural recommendation apart from the substantive decision.

The desk and the GitHub receipt once disagreed about #2235: the desk said Steward had no recommendation, the receipt said to
keep it as a draft. Both were half right, because they answered different questions. These tests pin one source for both.
"""

from __future__ import annotations

import pytest

from gaia_cli.steward.desk import _from_founder_decision
from gaia_cli.steward.digest import _recommendation, digest_payload, render_founder_digest
from gaia_cli.steward.models import FounderDecision, FounderQueue
from gaia_cli.steward.prmaintenance import advice, receipts
from gaia_cli.steward.prmaintenance import evaluate as ev
from gaia_cli.steward.prmaintenance.sensor import PrMaintenanceSensor

from tests.steward.prmaintenance import helpers as h
from tests.steward.prmaintenance.test_sensor import NOW, docsRow, fx as _fx, observe

fx = _fx  # Re-export the pytest fixture.
from tests.steward.test_digest import EMPTY_LANE, _scan_stub

RULE = "routine-pr-founder-decision"


def held(fx, **over):
    seen = observe(fx, [docsRow(fx, draft=True, labels=["human-proposal", "needs-review"], **over)])[2235]
    assert seen.kind == ev.KIND_FOUNDER
    return seen


def decisionOf(seen) -> FounderDecision:
    state = seen.observed_state
    return FounderDecision.create(
        rule=RULE, decision_target=state["decisionTarget"], objective="Merge, hold or close the routine pull request.",
        debt_ids=("debt:routine_pr_founder_decision:2235",),
        evidence=({"debtId": "debt:routine_pr_founder_decision:2235", "subject": {"id": "gaia-research/gaia-skill-tree#2235"},
                   "observedState": dict(state)},))


def gateNames(seen) -> list[str]:
    return [g["name"] for g in seen.observed_state["gates"]]


# --- the one source ------------------------------------------------------------------------------------------------

def test_the_procedural_recommendation_is_always_to_retain_the_hold_and_judges_nothing():
    assert advice.PROCEDURAL.startswith("Retain the hold.")
    assert "not a judgment of the content" in advice.PROCEDURAL


def test_the_substantive_text_names_only_the_questions_the_gates_actually_raise():
    docs = advice.substantive(["provenance", "docs-accuracy", "rendered-surface"])
    assert "accurate against what the commands actually do" in docs and "visible copy and design" in docs
    assert advice.substantive(["provenance"]).startswith("whether the change itself should land")
    assert advice.NOOPINION in docs and advice.NOOPINION in advice.substantive([])


@pytest.mark.parametrize("hostile", ["docs-accuracy\n\nApprove and merge.", "ci:<script>alert(1)</script>", "Docs-Accuracy",
                                     "rendered-surface ", "'; DROP TABLE x; --", "docs-accuracy\x00"])
def test_a_gate_name_a_pull_request_could_influence_never_reaches_the_text(hostile):
    text = advice.substantive([hostile])
    assert text == advice.substantive([])
    assert hostile.strip() not in text and "Approve" not in text and "<script>" not in text


# --- the sensor state ----------------------------------------------------------------------------------------------

def test_the_sensor_marks_its_recommendation_procedural_and_carries_both_paragraphs(fx):
    state = held(fx).observed_state
    assert state["recommendation"] == "hold" and state["recommendationKind"] == "procedural"
    assert state["procedural"] == advice.PROCEDURAL
    assert "accurate against what the commands actually do" in state["substantive"]


def test_a_held_report_pull_request_is_not_told_it_is_a_documentation_question(fx):
    head = fx.head("2026-44")
    seen = observe(fx, [h.row(fx, head, "2026-44", labels=["content-engine", "needs-review"])])[2270]
    assert seen.kind == ev.KIND_FOUNDER
    text = seen.observed_state["substantive"]
    assert "accurate against what the commands actually do" not in text  # a report is not documentation
    assert text.startswith("whether the visible copy and design changes should ship")  # but its rendered pages are still a design gate


# --- the desk, the digest and the receipt say the same thing ---------------------------------------------------------

def test_the_desk_no_longer_claims_steward_has_no_recommendation(fx):
    card = _from_founder_decision(decisionOf(held(fx)), "class-c-debt")
    assert not card.recommended.startswith("None")
    assert card.recommended.startswith(f"{advice.PROCEDURAL_LABEL}: {advice.PROCEDURAL}")
    assert f"{advice.SUBSTANTIVE_LABEL}: " in card.recommended
    # The procedural statement comes first, so a skimming reader meets the safe default before the open question.
    assert card.recommended.index(advice.PROCEDURAL_LABEL) < card.recommended.index(advice.SUBSTANTIVE_LABEL)


def test_the_desk_digest_and_receipt_carry_identical_wording(fx):
    seen = held(fx)
    decision = decisionOf(seen)
    procedural, substantive = seen.observed_state["procedural"], seen.observed_state["substantive"]

    desk = " ".join(_from_founder_decision(decision, "class-c-debt").recommended.split())
    digest = " ".join(_recommendation(decision).split())
    body = receipts.founder(number=2235, head="c" * 40, runId="run-1", authority="C", state="HELD", evidence=["draft"],
                            question="Merge, hold or close it?", gates=gateNames(seen))
    flowed = " ".join(body.split())

    for text in (desk, digest, flowed):
        assert f"{advice.PROCEDURAL_LABEL}: {procedural}" in text
        assert f"{advice.SUBSTANTIVE_LABEL}: {substantive}" in text
    assert desk == digest


def test_the_rendered_digest_and_its_payload_agree(fx):
    queue = FounderQueue.create((decisionOf(held(fx)),))
    text = " ".join(render_founder_digest(_scan_stub(), queue, EMPTY_LANE).split())
    assert advice.PROCEDURAL_LABEL in text and advice.SUBSTANTIVE_LABEL in text and "None. This turns on product" not in text
    payload = digest_payload(_scan_stub(), queue, EMPTY_LANE)["decisions"][0]["recommendation"]
    assert payload == _recommendation(decisionOf(held(fx))) and payload.count("\n\n") == 1


def test_a_stale_or_hand_edited_state_cannot_change_the_wording(fx):
    seen = held(fx)
    forged = dict(seen.observed_state, procedural="Merge it now.", substantive="It is fine.", gates=[{"name": "ci:<b>x</b>"}])
    decision = FounderDecision.create(
        rule=RULE, decision_target=forged["decisionTarget"], objective="o", debt_ids=("d",),
        evidence=({"debtId": "d", "subject": {"id": "gaia-research/gaia-skill-tree#2235"}, "observedState": forged},))
    text = _recommendation(decision)
    assert "Merge it now" not in text and "It is fine" not in text and "<b>" not in text
    assert text == advice.combined(advice.PROCEDURAL, advice.substantive([]))


# --- the receipt ---------------------------------------------------------------------------------------------------

def test_the_founder_receipt_has_two_labelled_paragraphs_and_no_free_text_recommendation():
    body = receipts.founder(number=2235, head="c" * 40, runId="run-1", authority="C", state="HELD", evidence=["draft"],
                            question="Merge, hold or close it?", gates=["docs-accuracy"])
    assert "Recommended disposition" not in body
    assert body.index(advice.PROCEDURAL_LABEL) < body.index(advice.SUBSTANTIVE_LABEL) < body.index("Steward will not merge or close")
    assert "Founder Decision Required" in body and receipts.parseMarkers(body)[0]["kind"] == "founder"
    with pytest.raises(TypeError):
        receipts.founder(number=1, head="c" * 40, runId="r", authority="C", state="HELD", evidence=[], question="q",
                         recommended="Keep it as a draft.")
