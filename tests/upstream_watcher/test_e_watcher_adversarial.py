"""Adversarial lane E for the upstream watcher (#2131): scenarios 2, 3, 6, 7, 8 and 13.

The watcher is driven through ``run_batch`` and ``escalate_candidate``. Two fakes are used:
``FakeGh`` (dict-backed, injects races and write failures) and ``ListedRest`` (a ``RestGhRunner``
that also lists the issues it creates, so a later run sees them as GitHub does). Nothing here
reaches the network.
"""

from __future__ import annotations

import pytest

from scripts.upstream_watcher.batch import escalate_candidate, parse_payload, run_batch
from scripts.upstream_watcher.live import GhError, LiveGh, read_live
from upstream_fakes import FakeGh, RestGhRunner, index_from_entries

REPO = "gaia-research/gaia-skill-tree"
GBRAIN_PREFIX = "[upstream] garrytan/gbrain → "
OTHER_PREFIX = "[upstream] other/repo → "
BLOB = "https://github.com/garrytan/gbrain/blob/main/skills/{slug}/SKILL.md"


def finding(version, adds, previous="v0", skill="garrytan/gbrain"):
    return {
        "finding_type": "update",
        "skillId": skill,
        "currentVersion": previous,
        "newVersion": version,
        "releasedAt": "2026-10-21T10:00:00Z",
        "sourceUrl": f"https://github.com/{skill}/releases/tag/{version}",
        "mode": "components",
        "componentAdds": list(adds),
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
    }


def run(gh, findings, apply=True, entries=()):
    index = index_from_entries(list(entries))
    return run_batch(findings, gh, apply=apply, index_loader=lambda: index)


def openUmbrellas(gh, prefix=GBRAIN_PREFIX):
    return [row for row in gh.issues.values() if row["title"].startswith(prefix) and row["state"] == "open"]


class ListedRest(RestGhRunner):
    """A REST stand-in whose created issues show up in later LIST pages, as on GitHub."""

    def __call__(self, args, capture_output=True, text=True, timeout=None):
        result = super().__call__(args, capture_output, text, timeout)
        if args[1:3] == ["issue", "create"] and result.returncode == 0:
            labels = [name for name in args[args.index("--label") + 1].split(",") if name]
            self.issues.append({
                "number": self.next_number, "title": args[args.index("--title") + 1], "state": "open",
                "body": self.writes[-1][2], "labels": [{"name": name} for name in labels],
                "updated_at": "2026-10-21T19:00:00Z",
            })
        return result


class FlakyCreate(FakeGh):
    """Fails the first create whose title starts with ``failTitle``, before anything is stored."""

    def __init__(self, issues=None, failTitle=None):
        super().__init__(issues)
        self.failTitle = failTitle

    def create_issue(self, title, labels, body):
        if self.failTitle and title.startswith(self.failTitle):
            self.failTitle = None
            raise GhError("create failed (fake 502)")
        return super().create_issue(title, labels, body)


class ConcurrentCreator(FakeGh):
    """Another writer creates the umbrella after our LIST snapshot was taken but before our create."""

    def __init__(self, issues=None, racingTitle=None):
        super().__init__(issues)
        self.racingTitle = racingTitle
        self.raced = False

    def list_issues(self, state, since=None, labels=None):
        rows = super().list_issues(state, since, labels)
        if not self.raced and self.racingTitle and state == "open":
            self.raced = True
            self.add({"number": 7000, "title": self.racingTitle, "state": "open",
                      "labels": [{"name": "upstream:release"}], "body": "created by another writer"})
        return rows


# ------------------------------------------------------------------ scenario 2: delayed index, duplicates


def test_a_created_umbrella_is_found_by_the_next_run_from_the_list_and_search_is_never_called() -> None:
    runner = ListedRest([])
    gh = LiveGh(repo=REPO, runner=runner)
    report, code = run(gh, [finding("v1", ["ask-user"])])
    assert code == 0 and report["issuesCreated"] == 1
    writes = len(runner.writes)
    report2, code2 = run(gh, [finding("v1", ["ask-user"])])
    assert code2 == 0
    assert report2["issuesCreated"] == 0 and report2["issuesUpdated"] == 0
    assert len(runner.writes) == writes
    # "gaia-research" contains the substring "search", so match only a search endpoint or segment.
    assert not any(arg.startswith("search") or "/search/" in arg for call in runner.calls for arg in call)


def test_two_identical_findings_in_one_run_never_create_two_umbrellas() -> None:
    gh = FakeGh()
    report, code = run(gh, [finding("v1", ["ask-user"]), finding("v1", ["ask-user"])])
    assert code == 0
    assert len(openUmbrellas(gh)) == 1
    assert [write[0] for write in gh.writes].count("create") == 1


def test_an_umbrella_another_writer_created_mid_run_is_adopted_not_duplicated() -> None:
    gh = ConcurrentCreator(racingTitle=GBRAIN_PREFIX + "v1")
    report, code = run(gh, [finding("v1", ["ask-user"])])
    assert code == 0
    assert len(openUmbrellas(gh)) == 1
    assert [write[0] for write in gh.writes].count("create") == 0  # the racer's umbrella was edited, not recreated
    assert gh.writes and gh.writes[0][0] == "edit"


# ------------------------------------------------------------------ scenario 3: same component, several releases


def test_a_component_listed_in_three_releases_is_one_row_with_first_and_last_seen_versions() -> None:
    gh = FakeGh()
    for version in ("v1", "v2", "v3"):
        run(gh, [finding(version, ["ask-user"], previous="v0")])
    payload = parse_payload(openUmbrellas(gh)[0]["body"])
    rows = [row for row in payload["candidates"] if row["slug"] == "ask-user"]
    assert len(rows) == 1
    assert rows[0]["firstSeenVersion"] == "v1" and rows[0]["lastSeenVersion"] == "v3"
    assert [write[0] for write in gh.writes].count("create") == 1


def test_a_component_whose_child_was_rejected_stays_rejected_across_later_releases() -> None:
    rejected = {"number": 41, "title": "[intake] garrytan/rejected-one", "state": "closed",
                "labels": [{"name": "upstream:child"}, {"name": "upstream:rejected"}],
                "body": "**Suggested ID:** `garrytan/rejected-one`\n"}
    gh = FakeGh([rejected])
    for version in ("v1", "v2", "v3"):
        report, code = run(gh, [finding(version, ["rejected-one"], previous="v0")])
        assert code == 0
    rows = [row for row in parse_payload(openUmbrellas(gh)[0]["body"])["candidates"] if row["slug"] == "rejected-one"]
    assert len(rows) == 1
    assert rows[0]["status"] == "rejected"
    assert [write[0] for write in gh.writes].count("create") == 1  # no child was created for it


# ------------------------------------------------------------------ scenario 6 and 13: repeated runs


def test_five_reruns_after_an_approval_perform_zero_writes_and_keep_the_approval() -> None:
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    umbrella = openUmbrellas(gh)[0]["number"]
    gh.edit_labels(umbrella, add=("upstream:approved",))
    before = gh.write_count()
    for _ in range(5):
        report, code = run(gh, [finding("v1", ["ask-user"])])
        assert code == 0
        assert report["issuesCreated"] == 0 and report["issuesUpdated"] == 0
    assert gh.write_count() == before
    assert "upstream:approved" in {label["name"] for label in gh.issues[umbrella]["labels"]}


def test_repeated_escalation_of_one_candidate_creates_one_child_and_later_calls_adopt_it() -> None:
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    creates = []
    for _ in range(3):
        result, code = escalate_candidate("garrytan/gbrain:ask-user", gh, apply=True)
        assert code == 0
        creates.append(result)
    children = [row for row in gh.issues.values() if row["title"].startswith("[intake] ")]
    assert len(children) == 1
    assert [write[0] for write in gh.writes].count("create") == 2  # the umbrella and the one child, nothing more


def test_a_rerun_after_a_partial_failure_completes_without_duplicating_what_already_landed() -> None:
    gh = FlakyCreate(failTitle=OTHER_PREFIX)
    first, code1 = run(gh, [finding("v1", ["ask-user"]), finding("v1", ["x-skill"], skill="other/repo")])
    assert code1 == 3
    assert [entry["source"] for entry in first["unknownEvidence"]] == ["github-write"]
    assert len(openUmbrellas(gh)) == 1 and len(openUmbrellas(gh, OTHER_PREFIX)) == 0

    second, code2 = run(gh, [finding("v1", ["ask-user"]), finding("v1", ["x-skill"], skill="other/repo")])
    assert code2 == 0
    assert len(openUmbrellas(gh)) == 1 and len(openUmbrellas(gh, OTHER_PREFIX)) == 1
    assert [write[0] for write in gh.writes].count("create") == 2  # one per umbrella, never one more
    assert second["issuesCreated"] == 1  # only the umbrella that failed before was created on the retry


# ------------------------------------------------------------------ scenario 8: watcher and steward race


def test_a_concurrent_write_between_the_snapshot_and_the_update_is_replanned_not_applied_stale() -> None:
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    umbrella = openUmbrellas(gh)[0]["number"]
    gh.stale_on_get[umbrella] = {"updated_at": "2026-10-21T19:59:00Z", "body": "a human rewrote this body\n"}
    report, code = run(gh, [finding("v2", ["ask-user"], previous="v1")])
    assert code == 0
    edits = [write for write in gh.writes if write[0] == "edit"]
    assert len(edits) == 1  # exactly one write, computed from the re-read snapshot
    assert openUmbrellas(gh)[0]["title"] == GBRAIN_PREFIX + "v2"
    assert len(openUmbrellas(gh)) == 1


def test_a_read_failure_during_the_race_writes_nothing_further_and_is_reported() -> None:
    gh = FakeGh()
    run(gh, [finding("v1", ["ask-user"])])
    gh.fail_get = True
    before = gh.write_count()
    report, code = run(gh, [finding("v2", ["ask-user"], previous="v1")])
    assert code == 3
    assert report["unknownEvidence"]
    assert gh.write_count() == before

