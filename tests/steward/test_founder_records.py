"""`gaia steward founder` lists canonical decision records (ruling steward-founder-command-records)."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
import shutil

from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.desk import _check_record, classify_decision_records, load_decision_records
from gaia_cli.steward.models import Observation
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH
from gaia_cli.steward.routing import render_founder_digest as route_digest


REPO_ROOT = Path(__file__).resolve().parents[2]
FROZEN = datetime(2026, 8, 13, tzinfo=timezone.utc)


class QuietSensor:
    id = "founder-records-fixture"

    def scan(self, root: Path, observed_at: str) -> list[Observation]:
        return []


def _repo(tmp_path: Path) -> Path:
    policy = tmp_path / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    return tmp_path


def _digest(root: Path) -> str:
    controller = StewardController(sensors=[QuietSensor()], clock=lambda: FROZEN)
    return route_digest(root, controller=controller)[1]


def _write_record(root: Path, name: str, **overrides: object) -> None:
    record = {
        "schemaVersion": "steward-decision-v1",
        "id": name,
        "status": "open",
        "decision": f"Should {name} ship?",
        "whyItMatters": "It matters.",
        "evidence": [],
        "recommended": "Yes.",
        "alternative": "No.",
        "unblocks": "The next thing.",
        "links": [],
        **overrides,
    }
    directory = root / "founder" / "steward" / "decisions"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / f"{name}.json").write_text(json.dumps(record), encoding="utf-8")


def test_an_empty_directory_still_says_nothing_requires_a_decision(tmp_path: Path) -> None:
    assert "Nothing requires a decision." in _digest(_repo(tmp_path))


def test_the_digest_lists_open_non_sensor_records(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write_record(root, "ship-gate-advisory")
    text = _digest(root)

    assert "Nothing requires a decision." not in text
    assert "Decisions for you        1" in text
    assert "1 decision(s) require founder judgment" in text
    assert "ship-gate-advisory — decision record" in text
    assert "Should ship-gate-advisory ship?" in text


def test_pending_and_approved_records_are_distinguished(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write_record(root, "still-open")
    _write_record(root, "ruled-not-landed", status="decided", resolution="approved")
    _write_record(root, "ruled-and-landed", status="decided", resolution="approved", landedIn="PR #1")
    _write_record(root, "plain-history", status="decided")
    text = _digest(root)

    assert "Decisions for you        1" in text
    assert "Approved, not yet landed 1" in text
    assert "still-open — decision record" in text
    assert "APPROVED, AWAITING IMPLEMENTATION OR LANDING (1)" in text
    awaiting = text.split("APPROVED, AWAITING IMPLEMENTATION OR LANDING")[1]
    assert "ruled-not-landed" in awaiting
    # Landed and plain-history records are history, not work.
    assert "ruled-and-landed" not in text
    assert "plain-history" not in text
    assert "ruled-not-landed — decision record" not in text


def test_an_approved_record_alone_never_reads_as_an_empty_desk(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write_record(root, "ruled-not-landed", status="decided", resolution="approved")
    text = _digest(root)

    assert "Nothing requires a decision." not in text
    assert "No decision is pending." in text
    assert "Decisions for you        0" in text
    assert "ruled-not-landed" in text


def test_an_unreadable_record_never_reads_as_an_empty_desk(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    directory = root / "founder" / "steward" / "decisions"
    directory.mkdir(parents=True)
    (directory / "broken.json").write_text("{not json", encoding="utf-8")
    text = _digest(root)

    assert "Nothing requires a decision." not in text
    assert "CANNOT BE READ" in text
    assert "founder/steward/decisions/broken.json" in text


def test_landed_in_must_be_a_non_empty_string() -> None:
    base = {
        "schemaVersion": "steward-decision-v1", "id": "x", "status": "decided", "decision": "d",
        "whyItMatters": "w", "evidence": [], "recommended": "r", "alternative": "a",
        "unblocks": "u", "links": [], "resolution": "approved",
    }
    assert _check_record({**base, "landedIn": "PR #1"}) is None
    assert "landedIn" in (_check_record({**base, "landedIn": " "}) or "")


def test_the_repository_decisions_directory_is_classified_exactly_by_its_own_records() -> None:
    """No hard-coded record: the expectation is derived from the files, so a legitimate landing never breaks it."""

    directory = REPO_ROOT / "founder" / "steward" / "decisions"
    documents = [json.loads(path.read_text(encoding="utf-8")) for path in sorted(directory.glob("*.json"))]
    expectedPending = {d["id"] for d in documents if d["status"] == "open"}
    expectedAwaiting = {
        d["id"] for d in documents
        if d["status"] == "decided" and d.get("resolution") == "approved" and "landedIn" not in d
    }

    records = classify_decision_records(load_decision_records(REPO_ROOT))

    assert not records.invalid
    assert {item.decision_id for item in records.pending} == expectedPending
    assert {item.record_id for item in records.awaiting} == expectedAwaiting
    assert records.actionable() == bool(expectedPending or expectedAwaiting)


def test_browser_sink_risk_surfaces_on_founder_desk() -> None:
    from gaia_cli.steward.desk import build_desk
    from gaia_cli.steward.models import AuthorityClass, Debt, Priority, Subject

    debt = Debt(
        id="debt:browser_sink_risk:docs/index.html",
        kind="browser_sink_risk",
        subject=Subject("file", "docs/index.html"),
        source="security-browser",
        current_state={"findingCount": 1},
        observed_state={"findingCount": 1, "findings": [{"line": 42, "pattern": "innerHTML-assignment"}]},
        confidence=0.6,
        priority=Priority(0.8, 0.7, 0.6, 0.8, 0.2, 1.344),
        authority=AuthorityClass.C,
        status="open",
        first_observed_at="2026-11-08T00:00:00Z",
        last_observed_at="2026-11-08T00:00:00Z",
        observation_count=1,
    )

    desk = build_desk(
        open_debts=[debt],
        lane=None,
        founder_queue=None,
        coverage_unknown=(),
        not_evaluated=(),
        decision_records=[],
        ledger_shared=False,
        last_scheduled_run_at=None,
        now="2026-11-08T00:00:00Z",
    )
    assert len(desk.decisions) == 1
    dec = desk.decisions[0]
    assert "unsafe DOM sinks" in dec.decision
    assert "1 sink site(s) across 1 file(s)" in dec.decision  # sites and files are counted separately
    assert "CLAUDE.md frontend human-gating" in dec.why_it_matters
    assert dec.source == "class-c-debt"
