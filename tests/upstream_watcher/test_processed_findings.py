"""Closed history is evidence of processed findings (PR #2133, hardening pass).

A finding is identified by its evidence: the suite (case-insensitive), the version it proposes and the candidate ids it
adds. A closed umbrella's payload records that finding. So:

- the same finding after closure, on every later daily scan, is processed: nothing is created;
- a new version, or a new candidate, is a genuinely new finding: a new open issue is created;
- a closed issue that names the finding but cannot prove it (no payload, a tampered payload, a payload that
  contradicts its own title) is ambiguous: nothing is created and the run exits 3.

Nothing here closes or reopens an issue. Closure classification is unchanged.
"""

from __future__ import annotations

import json

import pytest
from upstream_fakes import FakeGh, index_from_entries

from scripts.upstream_watcher import evidence
from scripts.upstream_watcher.batch import build_payload, run_batch

SUITE = "garrytan/gbrain"
PREFIX = "[upstream] garrytan/gbrain → "
ADDS = ["ask-user", "briefing"]
INDEX = index_from_entries([])


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


def run(gh, findings=None):
    return run_batch(findings or [finding("v1")], gh, apply=True, index_loader=lambda: INDEX)


def close(gh, number, label="upstream:rejected"):
    if label:
        gh.edit_labels(number, add=[label])
    gh.issues[number]["state"] = "closed"


def umbrellas(gh):
    return sorted(number for number, row in gh.issues.items() if row["title"].startswith(PREFIX))


def writes_since(gh, mark):
    return gh.writes[mark:]


# --- repeated daily scans and new findings after closure --------------------------------------------------------


@pytest.mark.parametrize("label", ["upstream:rejected", None])
def test_repeated_daily_scans_after_closure_create_nothing(label):
    gh = FakeGh()
    run(gh)
    close(gh, 5000, label=label)
    mark = gh.write_count()

    for _day in range(7):
        report, code = run(gh)
        assert code == 0, report
    assert writes_since(gh, mark) == []
    assert umbrellas(gh) == [5000]


def test_a_new_candidate_after_closure_is_a_genuinely_new_finding_and_creates():
    gh = FakeGh()
    run(gh, [finding("v1")])
    close(gh, 5000)
    mark = gh.write_count()

    report, code = run(gh, [finding("v1", adds=ADDS + ["extra-skill"])])

    assert code == 0, report
    assert [w[0] for w in writes_since(gh, mark)] == ["create"]
    assert umbrellas(gh) == [5000, 5001]
    assert gh.issues[5000]["state"] == "closed", "the closed issue is never touched"


def test_a_candidate_subset_of_a_closed_finding_is_still_processed():
    gh = FakeGh()
    run(gh, [finding("v1", adds=ADDS)])
    close(gh, 5000)
    mark = gh.write_count()

    report, code = run(gh, [finding("v1", adds=["ask-user"])])

    assert code == 0, report
    assert writes_since(gh, mark) == []


# --- ambiguous evidence fails closed --------------------------------------------------------------------------


def closed_then(mutate):
    gh = FakeGh()
    run(gh)
    close(gh, 5000)
    mutate(gh.issues[5000])
    return gh


def test_a_closed_issue_for_this_version_without_a_payload_blocks_the_suite_with_zero_writes():
    gh = closed_then(lambda row: row.update(body="hand edited: the payload block was removed"))
    mark = gh.write_count()

    report, code = run(gh)

    assert code == 3
    assert writes_since(gh, mark) == []
    assert report["unknownEvidence"][0]["source"] == "github-identity"
    assert report["unknownEvidence"][0]["suite"] == SUITE


def test_a_tampered_payload_for_this_version_blocks_the_suite_with_zero_writes():
    def tamper(row):
        body = row["body"]
        tampered = body.replace('"newVersion": "v1"', '"newVersion": "v9"')
        assert tampered != body, "the payload's version must be present to tamper with it"
        row["body"] = tampered

    gh = closed_then(tamper)
    mark = gh.write_count()

    report, code = run(gh)

    assert code == 3
    assert writes_since(gh, mark) == []
    assert report["unknownEvidence"][0]["source"] == "github-identity"


def test_an_unrelated_headless_closed_issue_for_another_version_does_not_block_a_new_version():
    gh = FakeGh()
    gh.add({"number": 4990, "title": PREFIX + "v0", "state": "closed", "body": "no payload",
            "labels": ["upstream:release"]})

    report, code = run(gh, [finding("v1")])

    assert code == 0, report
    assert [w[0] for w in gh.writes] == ["create"]


# --- stable identity: suite case, not titles alone ------------------------------------------------------------


def test_the_suite_identity_is_case_insensitive_so_a_recorded_finding_is_still_processed():
    gh = FakeGh()
    run(gh, [finding("v1", skill="Garrytan/GBrain")])
    close(gh, 5000)
    mark = gh.write_count()

    report, code = run(gh, [finding("v1", skill="garrytan/gbrain")])

    assert code == 0, report
    assert writes_since(gh, mark) == []


# --- the classifier itself -------------------------------------------------------------------------------------


def closed_issue(number, finding_record, kind="release", state="closed", title=None, body=None):
    if kind == "bootstrap":
        payload = {"skillId": finding_record["skillId"], "newVersion": finding_record["newVersion"],
                   "componentAdds": [], "sourceUrl": finding_record.get("sourceUrl", "")}
        title = title or f"[upstream:bootstrap] {finding_record['skillId']} → baseline at {finding_record['newVersion']}"
    else:
        payload = build_payload(finding_record, [], None)
        title = title or f"[upstream] garrytan/gbrain → {finding_record['newVersion']}"
    body = body if body is not None else (
        "<!-- gaia-upstream-payload\n" + json.dumps(payload, indent=2) + "\n-->"
    )
    return {"number": number, "title": title, "state": state, "body": body, "labels": [{"name": "upstream:release"}]}


def test_no_closed_history_is_a_new_finding():
    assert evidence.classify(finding("v1"), "release", []).state == "new"


def test_a_closed_finding_that_records_every_candidate_is_processed():
    recorded = closed_issue(7, finding("v1"))
    verdict = evidence.classify(finding("v1"), "release", [recorded])
    assert verdict == evidence.Verdict("processed", (7,))


def test_a_candidate_the_closed_finding_did_not_record_is_new():
    recorded = closed_issue(7, finding("v1", adds=ADDS))
    assert evidence.classify(finding("v1", adds=ADDS + ["extra"]), "release", [recorded]).state == "new"


def test_an_open_issue_is_never_evidence_of_a_processed_finding():
    recorded = closed_issue(7, finding("v1"))
    recorded["state"] = "open"
    assert evidence.classify(finding("v1"), "release", [recorded]).state == "new"


def test_a_bootstrap_is_processed_by_its_closed_baseline_for_the_same_version():
    baseline = {"skillId": "garrytan/gbrain", "newVersion": "v1", "sourceUrl": ""}
    recorded = closed_issue(9, baseline, kind="bootstrap")
    verdict = evidence.classify(baseline, "bootstrap", [recorded])
    assert verdict == evidence.Verdict("processed", (9,))
    assert evidence.classify({**baseline, "newVersion": "v2"}, "bootstrap", [recorded]).state == "new"


def test_a_bootstrap_with_no_payload_for_its_version_is_ambiguous():
    baseline = {"skillId": "garrytan/gbrain", "newVersion": "v1", "sourceUrl": ""}
    headless = closed_issue(9, baseline, kind="bootstrap", body="no payload")
    assert evidence.classify(baseline, "bootstrap", [headless]) == evidence.Verdict("ambiguous", (), (9,))
