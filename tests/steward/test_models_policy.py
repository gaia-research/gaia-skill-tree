from __future__ import annotations

from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.models import AuthorityClass, Observation, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, PolicyError, StewardPolicy


REPO_ROOT = Path(__file__).resolve().parents[2]


def test_semantic_debt_id_is_stable_across_observation_runs() -> None:
    first = Observation(
        kind="bundled_schema_mirror_drift",
        subject=Subject(type="repository-surface", id="registry-schema"),
        observed_at="2026-08-09T00:00:00Z",
        source="bundled-schema-mirror",
        status="drift",
        current_state={"digest": "a"},
        observed_state={"digest": "b"},
    )
    later = Observation(
        kind=first.kind,
        subject=first.subject,
        observed_at="2026-08-10T00:00:00Z",
        source=first.source,
        status="drift",
        current_state={"digest": "different-current-bytes"},
        observed_state={"digest": "different-observed-bytes"},
    )

    assert first.debt_id == later.debt_id
    assert first.debt_id.startswith("debt:bundled_schema_mirror_drift:registry-schema:")


def test_checked_in_policy_classifies_a_b_and_c() -> None:
    policy = StewardPolicy.load(REPO_ROOT)

    assert policy.authority_for("bundled_schema_mirror_drift") is AuthorityClass.A
    assert policy.authority_for("cli_contract_drift") is AuthorityClass.B
    assert policy.authority_for("generic_mapping") is AuthorityClass.C
    assert policy.priority_for("generic_mapping", confidence=1.0).score > 0


def test_policy_rejects_unclassified_debt_kind() -> None:
    policy = StewardPolicy.load(REPO_ROOT)

    with pytest.raises(PolicyError, match="not classified"):
        policy.authority_for("invented_kind")


def test_policy_rejects_write_scope_outside_local_steward_state(tmp_path: Path) -> None:
    data = yaml.safe_load((REPO_ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8"))
    data["allowedWrites"] = ["registry/**"]
    policy_path = tmp_path / POLICY_RELATIVE_PATH
    policy_path.parent.mkdir(parents=True)
    policy_path.write_text(yaml.safe_dump(data, sort_keys=False), encoding="utf-8")

    with pytest.raises(PolicyError, match="allowedWrites"):
        StewardPolicy.load(tmp_path)
