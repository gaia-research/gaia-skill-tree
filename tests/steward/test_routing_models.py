from __future__ import annotations

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
            "exactly registry-integrity-review",
        ),
        (
            lambda data: data["routing"]["dispatchRules"]["registry-integrity-review"].update(
                {"authority": "A"}
            ),
            "only Class B",
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


def test_dispatch_packet_id_hash_and_zero_budget_are_stable() -> None:
    first = _packet()
    second = _packet()

    assert first == second
    assert first.dispatch_id == second.dispatch_id
    assert first.packet_hash == second.packet_hash
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
    with pytest.raises(ValueError, match="decisionTarget"):
        normalize_decision_target("ambiguous target?")
