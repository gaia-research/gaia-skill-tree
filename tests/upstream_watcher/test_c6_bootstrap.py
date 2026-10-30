"""#2131 round-2 regression tests for the bootstrap path: H3 (rejection memory), L4 (update failure is
unknown evidence), M4 (no "automatically approved" claim) and the approval reset on a bootstrap
whose version moves while a human holds upstream:approved.

Canonical-issue ruling (founder correction, PR #2133): a closed upstream:bootstrap never blocks a new one. When
    no baseline for the suite is open, a new one is created, and the closed issue is never edited, commented on or
    reopened. An open list that fails is unknown evidence (exit 3, zero writes).
"""

from __future__ import annotations

import json
import subprocess

import pytest

from scripts.upstream_watcher import issuer, watcher
from scripts.upstream_watcher.issuer import render_bootstrap_body
from scripts.upstream_watcher.batch import new_report
from scripts.upstream_watcher.issuer import IdempotencyLookupError, UmbrellaWriteError, create_issues
from upstream_fakes import RestGhRunner

SUITE = "firecrawl/firecrawl-skills"
TITLE_V211 = f"[upstream:bootstrap] {SUITE} → baseline at v2.11.0"
TITLE_V210 = f"[upstream:bootstrap] {SUITE} → baseline at v2.10.0"

BOOTSTRAP = {
    "finding_type": "bootstrap",
    "skillId": SUITE,
    "newVersion": "v2.11.0",
    "releasedAt": "2026-10-21T00:00:00Z",
    "sourceUrl": "https://github.com/firecrawl/firecrawl/releases/tag/v2.11.0",
    "mode": "bootstrap",
    "componentAdds": [],
    "componentRemoves": [],
    "linkLiveness": [],
    "nameDrift": [],
}


def bootstrap_issue(number, title, state, labels, body=""):
    return {
        "number": number, "title": title, "state": state, "body": body, "updated_at": "2026-10-01T00:00:00Z",
        "labels": [{"name": name} for name in labels],
    }


def world_for(monkeypatch, issues, fail_pages=()):
    world = RestGhRunner(issues, fail_pages=fail_pages)
    monkeypatch.setattr(subprocess, "run", world)
    return world


def created_titles(world):
    return [title for kind, title, *_rest in world.writes if kind == "create"]


# ---------------------------------------------------------------------------
# Canonical issue: a closed baseline never blocks the next one, and is never touched
# ---------------------------------------------------------------------------


def test_a_closed_and_rejected_bootstrap_for_the_same_version_is_processed_and_not_recreated(monkeypatch):
    rejected = bootstrap_issue(1700, TITLE_V211, "closed", ["upstream:bootstrap", "upstream:rejected"],
                               body=render_bootstrap_body(BOOTSTRAP))
    world = world_for(monkeypatch, [rejected])

    summaries = create_issues([BOOTSTRAP], apply=True)

    assert world.writes == [], "the closed baseline records this finding: nothing is created or edited"
    assert summaries[0]["skipped"] is True and summaries[0]["covering"] == [1700]


def test_a_bootstrap_closed_as_completed_for_the_same_version_is_processed_and_not_recreated(monkeypatch):
    completed = bootstrap_issue(1701, TITLE_V211, "closed", ["upstream:bootstrap"],
                                body=render_bootstrap_body(BOOTSTRAP))
    world = world_for(monkeypatch, [completed])

    create_issues([BOOTSTRAP], apply=True)

    assert world.writes == []


def test_a_closed_bootstrap_for_this_version_with_no_payload_fails_closed_with_zero_writes(monkeypatch):
    headless = bootstrap_issue(1703, TITLE_V211, "closed", ["upstream:bootstrap"], body="")
    world = world_for(monkeypatch, [headless])

    with pytest.raises(IdempotencyLookupError):
        create_issues([BOOTSTRAP], apply=True)

    assert world.writes == [], "a closed baseline that cannot prove its finding is ambiguous: no create"


def test_a_closed_bootstrap_for_an_older_version_does_not_suppress_the_new_version(monkeypatch):
    older = bootstrap_issue(1702, TITLE_V210, "closed", ["upstream:bootstrap", "upstream:rejected"])
    world = world_for(monkeypatch, [older])

    create_issues([BOOTSTRAP], apply=True)

    assert created_titles(world) == [TITLE_V211]


def test_a_failed_open_bootstrap_list_is_unknown_evidence_with_zero_writes(monkeypatch):
    world = world_for(monkeypatch, [], fail_pages=[("open", "", 1)])

    with pytest.raises(IdempotencyLookupError):
        create_issues([BOOTSTRAP], apply=True)

    assert world.writes == []


def test_a_failed_closed_bootstrap_history_read_is_unknown_evidence_with_zero_writes(monkeypatch):
    world = world_for(monkeypatch, [], fail_pages=[("closed", "upstream:bootstrap", 1)])

    with pytest.raises(IdempotencyLookupError):
        create_issues([BOOTSTRAP], apply=True)

    assert world.writes == [], "closed history is the evidence: without it the baseline cannot be classified"


def test_batch_mode_open_bootstrap_list_failure_exits_3_with_zero_writes(monkeypatch, tmp_path):
    world = world_for(monkeypatch, [], fail_pages=[("open", "", 1)])
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: iter([(None, {"id": SUITE})]))
    monkeypatch.setattr(watcher, "_poll_suite", lambda fm, registry_map, verbose: BOOTSTRAP)
    monkeypatch.setattr(watcher, "run_batch", lambda *a, **k: (new_report(), 0))
    report_path = tmp_path / "report.json"

    code = watcher.main(["--apply", "--report", str(report_path)])

    assert code == 3
    assert world.writes == []
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unknownEvidence"][0]["source"] == "github-list"


# ---------------------------------------------------------------------------
# L4: a failed bootstrap update is unknown evidence (exit 3)
# ---------------------------------------------------------------------------


def test_a_failed_bootstrap_update_raises_so_the_run_exits_3(monkeypatch):
    world_for(monkeypatch, [bootstrap_issue(1755, TITLE_V210, "open", ["upstream:bootstrap"])])
    monkeypatch.setattr(issuer, "_update_issue", lambda *args, **kwargs: False)

    with pytest.raises(UmbrellaWriteError):
        create_issues([BOOTSTRAP], apply=True)


def test_batch_mode_failed_bootstrap_update_exits_3_and_reports_it(monkeypatch, tmp_path):
    world_for(monkeypatch, [bootstrap_issue(1755, TITLE_V210, "open", ["upstream:bootstrap"])])
    monkeypatch.setattr(watcher, "_build_registry_map", lambda: {})
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda: iter([(None, {"id": SUITE})]))
    monkeypatch.setattr(watcher, "_poll_suite", lambda fm, registry_map, verbose: BOOTSTRAP)
    monkeypatch.setattr(watcher, "run_batch", lambda *a, **k: (new_report(), 0))
    monkeypatch.setattr(issuer, "_update_issue", lambda *args, **kwargs: False)
    report_path = tmp_path / "report.json"

    code = watcher.main(["--apply", "--report", str(report_path)])

    assert code == 3
    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unknownEvidence"], "the failed bootstrap write must be reported as unknown evidence"


def test_a_bootstrap_whose_version_moves_while_approved_loses_the_approval(monkeypatch):
    world = world_for(monkeypatch, [bootstrap_issue(1755, TITLE_V210, "open",
                                                    ["upstream:bootstrap", "upstream:approved"])])

    create_issues([BOOTSTRAP], apply=True)

    edits = [call for call in world.calls if call[1:3] == ["issue", "edit"]]
    assert edits, world.calls
    assert "--remove-label" in edits[0] and "upstream:approved" in edits[0]
    assert "--add-label" in edits[0] and "upstream:needs-info" in edits[0]


# ---------------------------------------------------------------------------
# M4: the bootstrap body does not claim it is auto-approved
# ---------------------------------------------------------------------------


def test_the_bootstrap_body_never_claims_auto_approval_and_says_a_human_applies_the_label():
    from scripts.upstream_watcher.issuer import render_bootstrap_body

    body = render_bootstrap_body(BOOTSTRAP)

    assert "automatically" not in body.lower()
    assert "auto-approved" not in body.lower()
    reviewer = body.split("### Reviewer actions", 1)[1]
    assert "`upstream:approved`" in reviewer
    assert "human" in reviewer.lower()
    assert "watcher never" in reviewer.lower()
