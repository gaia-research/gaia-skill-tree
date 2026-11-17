"""Scoped records, canonical adoption and closure tests for repository envelopes."""
import copy

import pytest

from scripts.upstream_watcher import envelope as wire
from scripts.upstream_watcher.approval import PayloadError
from scripts.upstream_watcher import repository_batch as rb
from scripts.upstream_watcher import records
from upstream_fakes import FakeGh
from test_repository_envelope import authority, finding, issue, payloads, run, legacy_issue, no_network  # noqa: F401


def large_findings(version="v1"):
    return [finding(name, version, [f"candidate-{i:03d}" for i in range(120)]) for name in ("owner/a", "owner/b")]


def test_records_round_trip_each_scoped_row_and_repeat_is_zero_writes():
    gh = FakeGh()
    report, code = run(gh, large_findings(), apply=True)
    assert code == 0, report
    row = report["repositories"][0]
    assert row["wirePayload"]["candidateRecords"]["rows"] == 240
    assert report["retainedCandidates"] == 240
    number = row["umbrella"]
    expanded = wire.read(gh.issues[number]["body"], authority(), title_text=gh.issues[number]["title"],
                         comments=gh.list_comments(number))
    assert expanded == row["payload"]
    assert [len(f["candidates"]) for f in expanded["findings"]] == [120, 120]
    scoped = records.read_rows(gh.list_comments(number), row["wirePayload"]["candidateRecords"])
    assert len({r["id"] for r in scoped}) == 240
    assert len({r["candidateId"] for r in scoped}) == 120
    assert {r["namedSkillId"] for r in scoped} == {"owner/a", "owner/b"}
    gh.writes.clear()
    again, code = run(gh, large_findings(), apply=True)
    assert code == 0 and gh.writes == []
    assert again["repositories"][0]["outcome"] == "noop"


def test_sibling_digest_is_independent_of_repository_record_generation():
    gh = FakeGh()
    report, code = run(gh, large_findings(), apply=True)
    before = report["repositories"][0]
    b = copy.deepcopy(before["payload"]["findings"][1])
    report, code = run(gh, [large_findings("v2")[0]], apply=True)
    assert code == 0, report
    after = report["repositories"][0]
    assert after["payload"]["findings"][1] == b
    assert after["wirePayload"]["candidateRecords"]["sha256"] != before["wirePayload"]["candidateRecords"]["sha256"]
    selected, digest = wire.select(gh.issues[after["umbrella"]]["body"], authority(),
        identifier=b["skillId"], digest=b["payloadSha256"], source=b["sourceUrl"],
        comments=gh.list_comments(after["umbrella"]))
    assert selected == b and digest == b["payloadSha256"]
    assert len(gh.comments[after["umbrella"]]) == 5  # only the complete current generation remains


@pytest.mark.parametrize("damage", ["missing", "edited", "duplicate", "foreign-scope"])
def test_invalid_record_generation_stops_before_mutation(damage):
    gh = FakeGh()
    report, code = run(gh, large_findings(), apply=True)
    number = report["repositories"][0]["umbrella"]
    if damage == "missing":
        gh.comments[number].pop()
    elif damage == "edited":
        gh.comments[number][0]["body"] += "edited"
    elif damage == "duplicate":
        duplicate = copy.deepcopy(gh.comments[number][0])
        duplicate["id"] += 1000
        gh.comments[number].append(duplicate)
    else:
        # A perfectly sealed generation still cannot move A's rows into B's scope.
        payload = report["repositories"][0]["wirePayload"]
        scoped = records.read_rows(gh.comments[number], payload["candidateRecords"])
        scoped[0]["namedSkillId"] = "owner/b"
        generation = records.rows_digest(scoped)
        payload["candidateRecords"]["sha256"] = generation
        payload = wire.seal(payload)
        gh.issues[number]["body"] = wire.render(payload)
        gh.comments[number] = [{"id": 1000 + i, "user": {"login": records.WATCHER_LOGIN, "type": "Bot"},
            "body": records.render_chunk(generation, i, 5, chunk)}
            for i, chunk in enumerate(records.chunk_rows(scoped), 1)]
    before = copy.deepcopy(gh.issues)
    gh.writes.clear()
    report, code = run(gh, large_findings("v2"), apply=True)
    assert code == 3 and report["unknownEvidence"] and not report["knownLegacyHolds"]
    assert gh.writes == [] and gh.issues == before


def test_unresolved_unpolled_sibling_survives_a_new_repository_batch():
    payload = wire.build("owner/repo", payloads(), authority())
    gh = FakeGh([issue(payload, state="closed")])
    report, code = run(gh, [finding("owner/a", "v2", adds=())])
    assert code == 0
    a, b = report["repositories"][0]["payload"]["findings"]
    assert (a["skillId"], b["skillId"]) == ("owner/a", "owner/b")
    assert a["candidates"][0]["carriedFrom"] == b["candidates"][0]["carriedFrom"] == "#10"
    assert b["newVersion"] == "v1" and a["newVersion"] == "v2"
    assert report["retainedCandidates"] == 2


def test_create_race_adopts_lowest_canonical_without_duplicate_issue():
    class RacingGh(FakeGh):
        def __init__(self):
            super().__init__()
            self.opens = 0
        def list_issues(self, state, since=None, labels=None):
            if state == "open":
                self.opens += 1
                if self.opens == 2:
                    self.add(issue(wire.build("owner/repo", payloads(), authority()), 7))
            return super().list_issues(state, since, labels)
    gh = RacingGh()
    report, code = run(gh, apply=True)
    assert code == 0 and gh.writes == []
    assert report["repositories"][0]["umbrella"] == 7
    assert report["repositories"][0]["outcome"] == "noop"


def test_legacy_target_introduced_in_race_is_a_hold_not_an_overwrite_or_parallel_create():
    class RacingLegacy(FakeGh):
        def __init__(self):
            super().__init__()
            self.opens = 0
        def list_issues(self, state, since=None, labels=None):
            if state == "open":
                self.opens += 1
                if self.opens == 2:
                    self.add(legacy_issue())
            return super().list_issues(state, since, labels)
    gh = RacingLegacy()
    report, code = run(gh, apply=True)
    assert code == 0 and not report["writeReadiness"] and gh.writes == []
    assert report["knownLegacyHolds"][0]["issue"] == 42


def test_closed_before_update_is_replanned_and_closed_body_never_changes():
    payload = wire.build("owner/repo", payloads(), authority())
    class ClosingGh(FakeGh):
        def __init__(self):
            super().__init__([issue(payload)])
            self.gets = 0
        def get_issue(self, number):
            self.gets += 1
            if self.gets == 3:
                self.issues[number]["state"] = "closed"
            return super().get_issue(number)
    gh = ClosingGh()
    old_body = gh.issues[10]["body"]
    report, code = run(gh, [finding("owner/a", "v2")], apply=True)
    assert code == 0, report
    assert gh.issues[10]["body"] == old_body and gh.issues[10]["state"] == "closed"
    assert not any(w[0] != "create" and w[1] == 10 for w in gh.writes)
    assert len([i for i in gh.issues.values() if i["state"] == "open"]) == 1


def test_raw_reference_hash_has_one_framing_only():
    import hashlib
    old = legacy_issue()
    raw = old["body"]
    plan = wire.migration_plan(old, rb.batch.parse_payload(raw), authority(), {}, {})
    assert plan["bodyHashScheme"] == "raw_api_utf8"
    assert plan["bodySha256"] == hashlib.sha256(raw.encode()).hexdigest()
    assert plan["bodySha256"] != hashlib.sha256((raw + "\n").encode()).hexdigest()
    assert wire.verify_migration_reference(plan, old)
    for replacement in (raw + "\n", raw.replace("\n", "\r\n"), raw.rstrip("\n")):
        if replacement != raw:
            with pytest.raises(PayloadError):
                wire.verify_migration_reference(plan, {**old, "body": replacement})


def test_approval_cannot_freeze_a_sibling_suite_root_even_if_nested_in_selected_suite():
    metadata = authority()
    metadata["owner/a"]["suiteComponents"] = ["owner/b"]
    metadata["owner/b"]["suiteComponents"] = ["owner/component"]
    a = payloads()[0]
    a["componentRemoves"] = ["owner/b"]
    with pytest.raises(PayloadError, match="suite root"):
        wire.build("owner/repo", [wire.seal(a)], metadata)
