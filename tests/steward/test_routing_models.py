from __future__ import annotations

import re
from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.models import (
    AuthorityClass,
    DispatchPacket,
    FounderDecision,
    FounderQueue,
    RoutingBudget,
    normalize_decision_target,
)
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, PolicyError, StewardPolicy
from gaia_cli.steward.prompt import render_tree_keeper_prompt


REPO_ROOT = Path(__file__).resolve().parents[2]


def _policy_copy(tmp_path: Path, mutate) -> Path:
    data = yaml.safe_load((REPO_ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    mutate(data)
    destination = tmp_path / POLICY_RELATIVE_PATH
    destination.parent.mkdir(parents=True)
    destination.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")
    return tmp_path


def _packet() -> DispatchPacket:
    return DispatchPacket.create(
        debt={"id": "debt:registry", "kind": "registry_integrity_failed"},
        evidence={"violations": [{"path": "registry/nodes/x.json", "error": "invalid"}]},
        authority=AuthorityClass.B,
        rule="registry-integrity-review",
        routine="gaia-registry-integrity-review",
        objective="Reproduce and report the bounded integrity failure.",
        allowed_paths=("registry/nodes/**", "scripts/**", "tests/**"),
        allowed_commands=("python scripts/validate.py",),
        forbidden_paths=("founder/**", ".github/**"),
        stop_conditions=("proof is incomplete",),
        proof=("reproduce the violation",),
        budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0),
    )


def test_checked_in_routing_policy_is_exact_and_does_not_change_authority() -> None:
    policy = StewardPolicy.load(REPO_ROOT)

    dispatch = policy.dispatch_rule_for("registry_integrity_failed")
    founder = policy.founder_rule_for("generic_mapping")
    assert dispatch is not None and dispatch.authority is AuthorityClass.B
    assert founder is not None and founder.authority is AuthorityClass.C
    assert founder.decision_target_field == "decisionTarget"
    assert policy.dispatch_rule_for("sensor_coverage_unknown") is None
    assert policy.max_dispatches_per_run == 1
    assert policy.routing_budget.to_dict() == {
        "modelCalls": 0,
        "maxTokens": 0,
        "maxMinutes": 0,
    }
    assert policy.authority_for("registry_integrity_failed") is AuthorityClass.B
    assert policy.authority_for("generic_mapping") is AuthorityClass.C


@pytest.mark.parametrize(
    "mutate,match",
    [
        (
            lambda data: data["routing"]["dispatchRules"].update(
                {"coverage-review": data["routing"]["dispatchRules"]["registry-integrity-review"]}
            ),
            "multiple dispatch rules are configured",
        ),
        (
            lambda data: data["routing"]["dispatchRules"]["registry-integrity-review"].update(
                {"authority": "A"}
            ),
            "must route Class B debt",
        ),
        (
            # Class C work belongs to the founder queue; a dispatch rule may
            # never quietly hand a governance decision to an agent.
            lambda data: data["routing"]["dispatchRules"]["registry-integrity-review"].update(
                {"debtKind": "generic_mapping"}
            ),
            "must route Class B debt",
        ),
        (
            lambda data: data["routing"]["dispatchRules"]["registry-integrity-review"].update(
                {"promptGuide": "docs/agents/whatever.md"}
            ),
            "promptGuide must be a markdown routine",
        ),
        (
            lambda data: data["routing"]["dispatchRules"].clear(),
            "at least one dispatch rule",
        ),
        (
            lambda data: data["routing"]["founderRules"]["generic-mapping-decision"].update(
                {"decisionTargetField": "subject"}
            ),
            "require decisionTarget",
        ),
        (
            lambda data: data["routing"]["budget"].update({"modelCalls": 1}),
            "must be zero",
        ),
    ],
)
def test_routing_policy_fails_closed_on_broadened_or_malformed_rules(
    tmp_path: Path,
    mutate,
    match: str,
) -> None:
    root = _policy_copy(tmp_path, mutate)

    with pytest.raises(PolicyError, match=match):
        StewardPolicy.load(root)


def test_dispatch_packet_semantic_id_survives_evidence_refresh() -> None:
    first = _packet()
    refreshed = DispatchPacket.create(
        debt={"id": "debt:registry", "kind": "registry_integrity_failed", "lastObservedAt": "later"},
        evidence={"violations": [{"path": "registry/nodes/x.json", "error": "different fresh evidence"}]},
        authority=AuthorityClass.B,
        rule="registry-integrity-review",
        routine="gaia-registry-integrity-review",
        objective="Reproduce and report the bounded integrity failure.",
        allowed_paths=("registry/nodes/**", "scripts/**", "tests/**"),
        allowed_commands=("python scripts/validate.py",),
        forbidden_paths=("founder/**", ".github/**"),
        stop_conditions=("proof is incomplete",),
        proof=("reproduce the violation",),
        budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0),
    )

    assert first.dispatch_id == refreshed.dispatch_id
    assert first.packet_hash != refreshed.packet_hash
    assert first.to_dict()["budget"] == {
        "modelCalls": 0,
        "maxTokens": 0,
        "maxMinutes": 0,
    }
    with pytest.raises(ValueError, match="must be zero"):
        RoutingBudget(model_calls=1, max_tokens=0, max_minutes=0)


def test_founder_decisions_normalize_explicit_targets_and_sort_queue() -> None:
    first = FounderDecision.create(
        rule="generic-mapping-decision",
        decision_target=" Context Compression ",
        objective="Decide the canonical mapping.",
        debt_ids=("debt:z",),
        evidence=({"debtId": "debt:z", "source": "fixture"},),
    )
    second = FounderDecision.create(
        rule="generic-mapping-decision",
        decision_target="agent-routing",
        objective="Decide the canonical mapping.",
        debt_ids=("debt:a",),
        evidence=({"debtId": "debt:a", "source": "fixture"},),
    )

    queue = FounderQueue.create((first, second))
    repeated = FounderQueue.create((second, first))

    assert normalize_decision_target(" Context Compression ") == "context-compression"
    assert [item.decision_target for item in queue.decisions] == [
        "agent-routing",
        "context-compression",
    ]
    assert queue == repeated
    assert queue.queue_hash == repeated.queue_hash
    grown = FounderDecision.create(
        rule="generic-mapping-decision",
        decision_target="context-compression",
        objective="Decide the canonical mapping.",
        debt_ids=("debt:z", "debt:new"),
        evidence=(
            {"debtId": "debt:z", "source": "fixture"},
            {"debtId": "debt:new", "source": "fixture"},
        ),
    )
    assert grown.decision_id == first.decision_id
    assert FounderQueue.create((grown,)).queue_id == FounderQueue.create((first,)).queue_id
    with pytest.raises(ValueError, match="decisionTarget"):
        normalize_decision_target("ambiguous target?")


# --- V1.2: Tree Keeper prompt rendering ---------------------------------------


def test_checked_in_dispatch_rules_point_at_a_real_routine_document() -> None:
    """A policy rule's human contract must exist, not just validate."""

    policy = StewardPolicy.load(REPO_ROOT)

    assert policy.dispatch_rules
    for rule in policy.dispatch_rules.values():
        assert (REPO_ROOT / rule.prompt_guide).is_file(), rule.prompt_guide


def test_tree_keeper_prompt_carries_the_whole_envelope_and_names_no_harness() -> None:
    packet = _packet()

    prompt = render_tree_keeper_prompt(
        packet,
        prompt_guide="founder/steward/routines/registry-integrity-review.md",
        receipt={"runId": "steward-fixture-run"},
    )

    # Everything that bounds the work must survive the projection.
    assert packet.dispatch_id in prompt
    assert packet.objective in prompt
    assert "Class B" in prompt
    assert "founder/steward/routines/registry-integrity-review.md" in prompt
    assert "steward-fixture-run" in prompt
    for value in packet.allowed_paths + packet.allowed_commands + packet.forbidden_paths:
        assert value in prompt
    for value in packet.stop_conditions + packet.proof:
        assert value in prompt
    assert "registry/nodes/x.json" in prompt

    # The prompt is a contract, not a routing decision: naming a harness or a
    # model here would let the paste target change what the work is.
    lowered = prompt.lower()
    for harness in ("claude", "hermes", "codex", "opus", "sonnet", "gpt", "luna", "terra", "sol"):
        assert re.search(rf"\b{harness}\b", lowered) is None, harness


def test_tree_keeper_prompt_is_deterministic_and_declares_a_zero_budget() -> None:
    packet = _packet()

    first = render_tree_keeper_prompt(packet, prompt_guide="founder/steward/routines/x.md")
    second = render_tree_keeper_prompt(packet, prompt_guide="founder/steward/routines/x.md")

    assert first == second
    assert first.endswith("\n")
    assert "Model calls granted by Steward: **0**" in first
    assert "unrecorded" in first
