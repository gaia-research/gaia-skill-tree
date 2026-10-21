"""Regression tests for M3 and M10 (#2131 verifier FAIL) in scripts/upstream_watcher/issuer.py.

M3: a bootstrap issue is never created with upstream:approved, and the watcher never
    dispatches upstream-approve.yml for one. The bootstrap protocol needs a human to
    apply the label after reading the proposed baseline.
M10: in legacy fanout, a failed umbrella create writes no child intakes and stops the
    run with a raised error (the watcher maps it to exit 3). A child is never created
    under an umbrella number of "?".
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from scripts.upstream_watcher import issuer
from scripts.upstream_watcher.issuer import UmbrellaWriteError, create_issues


def _no_existing_issues(labels=issuer.IDEMPOTENCY_LABELS):
    return {label: [] for label in labels}


BOOTSTRAP = {
    "finding_type": "bootstrap",
    "skillId": "firecrawl/firecrawl-skills",
    "newVersion": "v2.11.0",
    "sourceUrl": "https://github.com/firecrawl/firecrawl/releases/tag/v2.11.0",
}

UPDATE = {
    "finding_type": "update",
    "skillId": "garrytan/gbrain",
    "currentVersion": "v1",
    "newVersion": "v2",
    "releasedAt": "2026-10-21T00:00:00Z",
    "sourceUrl": "https://github.com/garrytan/gbrain/releases/tag/v2",
    "mode": "components",
    "componentAdds": ["ask-user"],
    "componentRemoves": [],
    "linkLiveness": [],
    "nameDrift": [],
}


# ---------------------------------------------------------------------------
# M3: bootstrap is human-approved, never auto-approved or dispatched
# ---------------------------------------------------------------------------


def test_new_bootstrap_is_created_without_upstream_approved():
    created = []

    def fake_create(title, labels, body, dry_run, verbose=False):
        created.append((title, list(labels)))
        return 1568

    with patch.object(issuer, "_open_snapshot", return_value=_no_existing_issues()), patch.object(
        issuer, "_create_issue", side_effect=fake_create
    ), patch.object(issuer.subprocess, "run") as run:
        create_issues([BOOTSTRAP], apply=True)

    assert created and all("upstream:approved" not in labels for _title, labels in created)
    assert created[0][1] == ["upstream:bootstrap"]
    assert not any("workflow" in call.args[0] for call in run.call_args_list)


def test_existing_bootstrap_update_does_not_dispatch_approve():
    existing_title = "[upstream:bootstrap] firecrawl/firecrawl-skills → baseline at v2.10.0"
    snapshot = _no_existing_issues()
    snapshot["upstream:bootstrap"] = [{"number": 1755, "title": existing_title}]

    with patch.object(issuer, "_open_snapshot", return_value=snapshot), patch.object(
        issuer, "_update_issue", return_value=True
    ), patch.object(issuer.subprocess, "run") as run:
        summaries = create_issues([BOOTSTRAP], apply=True)

    assert not any("workflow" in call.args[0] for call in run.call_args_list)
    assert summaries[0]["issue"] == 1755


def test_bootstrap_dry_run_writes_nothing_and_dispatches_nothing():
    with patch.object(issuer, "_open_snapshot", return_value=_no_existing_issues()), patch.object(
        issuer, "_create_issue", return_value=None
    ) as create:
        create_issues([BOOTSTRAP], apply=False)
    assert create.call_args.kwargs["dry_run"] is True


# ---------------------------------------------------------------------------
# M10: legacy fanout fails closed when the umbrella cannot be created
# ---------------------------------------------------------------------------


def test_fanout_umbrella_create_failure_creates_no_children():
    created_titles = []

    def fake_create(title, labels, body, dry_run, verbose=False):
        created_titles.append(title)
        if title.startswith("[upstream] "):
            return None  # the umbrella create failed (gh error)
        return 9001

    with patch.object(issuer, "_open_snapshot", return_value=_no_existing_issues()), patch.object(
        issuer, "_create_issue", side_effect=fake_create
    ), patch.object(issuer, "_edit_umbrella_body") as edit:
        with pytest.raises(UmbrellaWriteError):
            create_issues([UPDATE], apply=True)

    assert not any(title.startswith("[intake]") for title in created_titles), created_titles
    edit.assert_not_called()


def test_fanout_umbrella_create_failure_is_reported_as_exit_3(tmp_path, monkeypatch):
    from scripts.upstream_watcher import watcher

    monkeypatch.setattr(watcher, "_build_registry_map", lambda root=None: {})
    monkeypatch.setattr(watcher, "_poll_suite", lambda fm, registry_map, verbose: UPDATE)
    monkeypatch.setattr(watcher, "iter_suite_skills", lambda root=None: iter([(None, {"id": "garrytan/gbrain"})]))

    def fail_create(*args, **kwargs):
        raise UmbrellaWriteError("umbrella create failed (fake)")

    monkeypatch.setattr(watcher, "create_issues", fail_create)
    report_path = tmp_path / "report.json"
    code = watcher.main(["--child-mode", "fanout", "--apply", "--report", str(report_path)])
    assert code == 3
    import json

    report = json.loads(report_path.read_text(encoding="utf-8"))
    assert report["unknownEvidence"][0]["source"] == "github-write"


def test_fanout_dry_run_does_not_raise_for_a_missing_umbrella_number():
    """Dry run has no issue numbers by design. The fail-closed rule applies to real writes only."""
    with patch.object(issuer, "_open_snapshot", return_value=_no_existing_issues()):
        summaries = create_issues([UPDATE], apply=False)
    assert summaries[0]["umbrella"] is None
