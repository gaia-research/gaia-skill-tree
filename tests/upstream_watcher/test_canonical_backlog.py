"""Canonical backlog issue per suite (founder correction, PR #2133).

Rules under test:

1. At most one OPEN canonical umbrella per suite. New findings update that open issue in place.
2. When no OPEN canonical umbrella exists, a new one is created, even if closed ones exist for the suite.
3. The watcher never edits, comments on, relabels or reopens a closed issue. Closed issues are preserved.
4. Several open exact matches: the lowest-numbered is canonical, the rest are reported as duplicates for Steward
   and left untouched. Nothing is created beside them.
5. Identity is the suite parsed from the title, case-insensitive. A title that names the suite but does not parse
   is ambiguous: no write, exit 3.
6. Unchanged findings against the open canonical issue cause no writes.
7. A concurrent run that opens the canonical issue between the first read and the create is adopted, not duplicated.

Nothing here reaches GitHub. ``FakeGh`` records every write as (kind, number, ...).
"""

from __future__ import annotations

from pathlib import Path

import yaml
from upstream_fakes import FakeGh, index_from_entries

from scripts.upstream_watcher.batch import run_batch
from scripts.upstream_watcher.live import canonical_umbrellas, suite_key, umbrella_suite

REPO_ROOT = Path(__file__).resolve().parents[2]
SUITE = "garrytan/gbrain"
PREFIX = "[upstream] garrytan/gbrain → "
INDEX = index_from_entries([])
ADDS = ["ask-user", "briefing"]


def finding(version, adds=ADDS, skill=SUITE):
    return {
        "finding_type": "update",
        "skillId": skill,
        "currentVersion": "v0",
        "newVersion": version,
        "releasedAt": "2026-10-21T10:00:00Z",
        "sourceUrl": f"https://github.com/{skill}/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
    }


def run(gh, findings=None, apply=True):
    return run_batch(findings or [finding("v1")], gh, apply=apply, index_loader=lambda: INDEX)


def umbrellas(gh, prefix=PREFIX):
    return sorted(number for number, row in gh.issues.items() if row["title"].startswith(prefix))


def close(gh, number, label="upstream:rejected", state_reason=None):
    if label:
        gh.edit_labels(number, add=[label])
    gh.issues[number]["state"] = "closed"
    if state_reason:
        gh.issues[number]["state_reason"] = state_reason


def writes_since(gh, mark):
    return gh.writes[mark:]


def touched(writes, number):
    return [w for w in writes if w[1] == number]


# --- identity: parsed, exact, case-insensitive --------------------------------------------------------------


def test_identity_is_the_parsed_suite_not_a_substring():
    assert umbrella_suite("[upstream] garrytan/gbrain → v1") == "garrytan/gbrain"
    assert umbrella_suite("[upstream] garrytan/gbrain-extra → v1") == "garrytan/gbrain-extra"
    assert umbrella_suite("Garrytan/GBrain notes") is None
    assert suite_key(" Garrytan/GBrain ") == "garrytan/gbrain"


def test_canonical_is_the_lowest_exact_match_and_the_rest_are_duplicates():
    issues = [
        {"number": 5003, "title": PREFIX + "v0", "state": "open", "labels": [{"name": "upstream:release"}]},
        {"number": 5000, "title": PREFIX + "v0", "state": "open", "labels": [{"name": "upstream:release"}]},
        {"number": 5001, "title": "[upstream] garrytan/gbrain-extra → v0", "state": "open",
         "labels": [{"name": "upstream:release"}]},
    ]
    found = canonical_umbrellas(issues, "Garrytan/GBrain")
    assert found.canonical["number"] == 5000
    assert [row["number"] for row in found.duplicates] == [5003]
    assert found.ambiguous == []


# --- open-issue reuse and multi-day updates to one suite ----------------------------------------------------


def test_a_new_finding_updates_the_open_canonical_issue_in_place_and_creates_nothing():
    gh = FakeGh()
    run(gh)
    mark = gh.write_count()

    report, code = run(gh, [finding("v2")])

    assert code == 0, report
    assert sorted(w[0] for w in writes_since(gh, mark)) == ["comment", "edit"]
    assert umbrellas(gh) == [5000]
    assert gh.issues[5000]["title"] == PREFIX + "v2"
    assert report["issuesCreated"] == 0 and report["issuesUpdated"] == 1


def test_multi_day_updates_to_one_suite_reuse_one_issue_and_repeats_write_nothing():
    gh = FakeGh()
    run(gh, [finding("v1")])
    run(gh, [finding("v2")])
    mark = gh.write_count()
    run(gh, [finding("v2")])
    assert gh.write_count() == mark, "the same finding on a later day writes nothing"
    run(gh, [finding("v3")])

    assert umbrellas(gh) == [5000]
    assert gh.issues[5000]["title"] == PREFIX + "v3"
    assert not [w for w in gh.writes if w[0] == "create"][1:], "one create only, on day one"


def test_repeated_daily_runs_with_unchanged_findings_write_nothing_after_the_first():
    gh = FakeGh()
    run(gh)
    mark = gh.write_count()
    for _day in range(5):
        report, code = run(gh)
        assert code == 0, report
    assert gh.write_count() == mark
    assert umbrellas(gh) == [5000]


# --- closed issues: preserved, never edited, a new one opens when none is open -------------------------------


def test_a_closed_canonical_issue_is_replaced_by_a_new_one_and_left_untouched():
    gh = FakeGh()
    run(gh)
    close(gh, 5000)
    mark = gh.write_count()

    report, code = run(gh)

    assert code == 0, report
    assert [w[0] for w in writes_since(gh, mark)] == ["create"]
    assert umbrellas(gh) == [5000, 5001]
    assert gh.issues[5000]["state"] == "closed", "the closed issue is not reopened"
    assert touched(writes_since(gh, mark), 5000) == [], "the closed issue gets no edit, comment or label"


def test_multiple_historical_closures_each_stay_closed_and_the_newest_open_one_carries_forward():
    gh = FakeGh()
    run(gh)
    close(gh, 5000)
    run(gh)
    close(gh, 5001, label="upstream:rejected")
    run(gh)
    close(gh, 5002, label=None, state_reason="completed")
    mark = gh.write_count()

    report, code = run(gh)

    assert code == 0, report
    assert umbrellas(gh) == [5000, 5001, 5002, 5003]
    for number in (5000, 5001, 5002):
        assert gh.issues[number]["state"] == "closed"
        assert touched(writes_since(gh, mark), number) == []
    assert [w[0] for w in writes_since(gh, mark)] == ["create"]


# --- duplicates: canonical updated, duplicates reported and untouched ----------------------------------------


def test_duplicate_open_umbrellas_are_reported_for_steward_and_never_written():
    gh = FakeGh()
    gh.add({"number": 5000, "title": PREFIX + "v0", "state": "open", "body": "",
            "labels": ["upstream:release"]})
    gh.add({"number": 5003, "title": PREFIX + "v0", "state": "open", "body": "",
            "labels": ["upstream:release"]})
    mark = gh.write_count()

    report, code = run(gh)

    assert code == 0, report
    assert not [w for w in writes_since(gh, mark) if w[0] == "create"], "no third issue beside the duplicates"
    assert touched(writes_since(gh, mark), 5003) == [], "the duplicate is never edited, commented on or closed"
    assert gh.issues[5003]["state"] == "open"
    assert gh.issues[5000]["title"] == PREFIX + "v1", "the canonical (lowest) issue receives the update"
    assert report["duplicateOpenUmbrellas"] == [
        {"suite": SUITE, "canonical": 5000, "duplicates": [{"number": 5003, "title": PREFIX + "v0"}]}
    ]


# --- ambiguous identity: fail closed --------------------------------------------------------------------------


def test_an_open_title_that_names_the_suite_but_does_not_parse_blocks_the_suite_with_zero_writes():
    gh = FakeGh()
    gh.add({"number": 5000, "title": "[upstream] garrytan/gbrain v1 (hand-typed)", "state": "open", "body": "",
            "labels": ["upstream:release"]})
    mark = gh.write_count()

    report, code = run(gh)

    assert code == 3, "an ambiguous identity is unknown evidence, not a silent skip"
    assert writes_since(gh, mark) == [], "no create, edit or comment"
    assert report["unknownEvidence"][0]["source"] == "github-identity"
    assert report["unknownEvidence"][0]["suite"] == SUITE


def test_an_ambiguous_title_for_another_suite_does_not_block_this_one():
    gh = FakeGh()
    gh.add({"number": 5000, "title": "[upstream] garrytan/gbrain-extra v1 (hand-typed)", "state": "open",
            "body": "", "labels": ["upstream:release"]})

    report, code = run(gh)

    assert code == 0, report
    assert [w[0] for w in gh.writes] == ["create"], "a sibling's unparseable title does not block this suite"
    assert umbrellas(gh) == [5001]


# --- cross-suite isolation ------------------------------------------------------------------------------------


def test_a_suite_with_a_longer_name_is_isolated_from_its_prefix_sibling():
    gh = FakeGh()
    run(gh, [finding("v1", skill="garrytan/gbrain-extra")])
    mark = gh.write_count()

    report, code = run(gh, [finding("v1")])

    assert code == 0, report
    assert [w[0] for w in writes_since(gh, mark)] == ["create"], "the sibling suite's issue is not reused"
    assert gh.issues[5000]["title"] == "[upstream] garrytan/gbrain-extra → v1"


def test_case_differences_in_the_owner_repo_name_refer_to_the_same_suite():
    gh = FakeGh()
    run(gh, [finding("v1", skill="Garrytan/GBrain")])
    mark = gh.write_count()

    report, code = run(gh, [finding("v2")])

    assert code == 0, report
    assert umbrellas(gh, "[upstream] ") == [5000], "one suite, one issue, whatever the case"
    assert sorted(w[0] for w in writes_since(gh, mark)) == ["comment", "edit"]


# --- concurrency: a create that a concurrent run beat us to is adopted ----------------------------------------


class ConcurrentOpen(FakeGh):
    """A concurrent run opens the canonical umbrella after this run's first open read and before its create."""

    def __init__(self, rival):
        super().__init__()
        self.rival = rival
        self.injected = False

    def list_issues(self, state, since=None, labels=None):
        rows = super().list_issues(state, since, labels)
        if state == "open" and not self.injected:
            self.injected = True
            self.add(self.rival)
        return rows


def test_a_create_raced_by_a_concurrent_run_is_adopted_and_never_duplicated():
    rival = {"number": 5900, "title": PREFIX + "v1", "state": "open", "body": "",
             "labels": ["upstream:release"]}
    gh = ConcurrentOpen(rival)

    report, code = run(gh)

    assert code == 0, report
    assert not [w for w in gh.writes if w[0] == "create"], "the rival is adopted, nothing is created"
    assert umbrellas(gh) == [5900]


# --- the daily schedule and the concurrency group stay configured ---------------------------------------------


def test_the_daily_schedule_and_the_serialising_concurrency_group_are_configured():
    workflow = yaml.safe_load((REPO_ROOT / ".github" / "workflows" / "upstream-watcher.yml").read_text(encoding="utf-8"))
    schedules = workflow.get(True, workflow.get("on"))["schedule"]
    assert [entry["cron"] for entry in schedules] == ["0 6 * * *"]
    concurrency = workflow["concurrency"]
    group = concurrency if isinstance(concurrency, str) else concurrency["group"]
    assert group == "upstream-watcher"
    assert not (isinstance(concurrency, dict) and concurrency.get("cancel-in-progress") is True), \
        "a second run queues behind the first; it never cancels it mid-write"
