from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import parse_qs, urlparse

from gaia_cli.steward.issuehygiene.census import (
    COMPLETE,
    INCOMPLETE,
    MISSING,
    STALE,
    bodySha256,
    loadCensus,
    validateCensus,
)
from gaia_cli.steward.issuehygiene.identity import buildGraph, classify, compareVersions
from tests.steward.issuehygiene.e_fakes import realLinkHeader, servedPage
from scripts.steward_issue_census import FetchError, Response, collectCensus, main

FIXTURE = Path(__file__).resolve().parents[2] / "fixtures" / "issuehygiene" / "census-four-families.json"
NOW = "2026-10-21T19:00:00Z"
MAX_AGE = 6 * 3600
UMBRELLA_PARENTS = {1835: 72, 2002: 17, 2020: 4, 1823: 3}
FIXED_NOW = datetime(2026, 10, 21, 19, tzinfo=timezone.utc)


def fixtureDocument() -> dict:
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


def row(number: int, title: str, body: str = "", labels=(), author: str = "mbtiongson1", **extra) -> dict:
    base = {
        "number": number, "title": title, "state": "open", "stateReason": None,
        "labels": list(labels), "author": author, "createdAt": NOW, "updatedAt": NOW,
        "closedAt": None, "comments": 0, "body": body, "bodySha256": bodySha256(body),
        "isPullRequest": False, "mergedAt": None, "headRef": None, "baseRef": None,
    }
    base.update(extra)
    return base


def childBody(parent: int, owner: str, repo: str, slug: str) -> str:
    return (
        f"> Auto-populated by upstream watcher. Umbrella: #{parent}.\n\n"
        f"**Suggested ID:** `{owner}/{slug}`\n"
        f"### Evidence\n\n- **type:** `repo`\n- **url:** https://github.com/{owner}/{repo}/blob/main/skills/{slug}/SKILL.md\n"
    )


def umbrellaBody(skillId: str, newVersion: str, adds: list[str]) -> str:
    payload = {"skillId": skillId, "newVersion": newVersion, "componentAdds": adds, "componentRemoves": []}
    return (
        "## Upstream release detected\n\n<!-- gaia-upstream-payload\n"
        + json.dumps(payload, indent=2)
        + "\n-->\n"
    )


# ---------------------------------------------------------------- census


def test_complete_census_loads_and_reads_back_rows() -> None:
    census = loadCensus(FIXTURE, NOW, MAX_AGE)

    assert census.status.status == COMPLETE
    assert census.status.reasons == ()
    assert len(census.openIssues()) == 115
    assert len(census.openPulls()) == 8
    assert 2091 in census.byNumber()
    assert census.mergedPulls() == []


def test_missing_page_is_incomplete() -> None:
    document = fixtureDocument()
    document["completeness"]["issues"].update(complete=False, pagesFetched=2, expectedPages=3)

    status = validateCensus(document, NOW, MAX_AGE)

    assert status.status == INCOMPLETE
    assert "issues-complete-false" in status.reasons
    assert "issues-pages-mismatch:2/3" in status.reasons


def test_old_census_is_stale_not_incomplete() -> None:
    status = validateCensus(fixtureDocument(), "2026-10-22T19:00:00Z", MAX_AGE)

    assert status.status == STALE
    assert any(reason.startswith("fetchedAt-too-old") for reason in status.reasons)


def test_body_hash_mismatch_is_incomplete() -> None:
    document = fixtureDocument()
    document["issues"][0]["body"] += "\nedited"

    status = validateCensus(document, NOW, MAX_AGE)

    assert status.status == INCOMPLETE
    assert f"issues-body-sha256-mismatch:#{document['issues'][0]['number']}" in status.reasons


def test_row_missing_body_is_incomplete() -> None:
    document = fixtureDocument()
    del document["issues"][3]["body"]

    status = validateCensus(document, NOW, MAX_AGE)

    assert status.status == INCOMPLETE
    assert any(reason.startswith("issues-row-missing-body") for reason in status.reasons)


def test_unknown_schema_is_incomplete_and_bad_input_never_raises() -> None:
    document = fixtureDocument()
    document["schemaVersion"] = "steward-github-census-v0"

    assert validateCensus(document, NOW, MAX_AGE).status == INCOMPLETE
    assert validateCensus("not an object", NOW, MAX_AGE).status == MISSING
    assert validateCensus({"issues": "nope"}, NOW, MAX_AGE).status == INCOMPLETE


def test_missing_and_unparsable_files_are_missing(tmp_path: Path) -> None:
    assert loadCensus(tmp_path / "absent.json", NOW, MAX_AGE).status.status == MISSING

    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    census = loadCensus(broken, NOW, MAX_AGE)

    assert census.status.status == MISSING
    assert census.document is None
    assert census.openIssues() == []


# ---------------------------------------------------------------- identity


def test_all_96_real_children_classify_with_slug_evidence_and_parent() -> None:
    census = loadCensus(FIXTURE, NOW, MAX_AGE)
    children = [classify(item) for item in census.openIssues() if "upstream:child" in item["labels"]]

    assert len(children) == 96
    for identity in children:
        assert identity.kind == "child", identity
        assert identity.slug, identity
        assert identity.evidenceUrl and identity.evidenceUrl.startswith("https://github.com/"), identity
        assert identity.parent in UMBRELLA_PARENTS, identity
        assert identity.key.startswith("upstream-candidate:"), identity

    graph = buildGraph(census.openIssues() + census.openPulls(), census.rows("recentlyClosed"))
    assert {parent: len(numbers) for parent, numbers in graph.children.items()} == UMBRELLA_PARENTS
    assert graph.orphans == ()
    assert graph.duplicates == {}


def test_umbrella_and_bootstrap_payloads_parse() -> None:
    census = loadCensus(FIXTURE, NOW, MAX_AGE)
    byNumber = census.byNumber()

    umbrella = classify(byNumber[1835])
    assert umbrella.kind == "umbrella"
    assert umbrella.key == "upstream-release:garrytan/gbrain@v0.60.340.0"
    assert umbrella.suite == "upstream-suite:garrytan/gbrain"
    assert umbrella.version == "v0.60.340.0"
    assert umbrella.payload and umbrella.payload["mode"] == "components"
    assert umbrella.payloadReason is None

    bootstrap = classify(byNumber[2091])
    assert bootstrap.kind == "bootstrap"
    assert bootstrap.key == "upstream-bootstrap:leonxlnx/taste-skill"
    assert bootstrap.payload["mode"] == "bootstrap"


def test_title_payload_suite_mismatch_is_recorded_and_payload_wins() -> None:
    identity = classify(row(2002, "[upstream] addyosmani/agent-skills → 0.6.13", umbrellaBody("addy-osmani/agent-skills", "0.6.13", []), labels=["upstream:release"], author="github-actions[bot]"))

    assert identity.suite == "upstream-suite:addy-osmani/agent-skills"
    assert any(reason.startswith("title-payload-suite-mismatch") for reason in identity.reasons)


def test_malformed_payload_is_reported_not_raised() -> None:
    body = "## Upstream release detected\n\n<!-- gaia-upstream-payload\n{\"skillId\": \"o/r\", \n-->\n"
    identity = classify(row(3001, "[upstream] o/r → v1.0.0", body, labels=["upstream:release"], author="github-actions[bot]"))

    assert identity.kind == "umbrella"
    assert identity.payload is None
    assert identity.payloadReason.startswith("malformed:")
    assert identity.version == "v1.0.0"
    assert identity.key == "upstream-release:o/r@v1.0.0"


def test_unterminated_payload_block_is_malformed() -> None:
    body = "<!-- gaia-upstream-payload\n{\"skillId\": \"o/r\"}\n"
    identity = classify(row(3002, "[upstream] o/r → v1", body, labels=["upstream:release"], author="github-actions[bot]"))

    assert identity.payloadReason == "malformed:unterminated-block"


def test_orphan_child_is_reported_not_attached() -> None:
    orphan = row(4001, "[intake] alice/orphan", childBody(9999, "alice", "tools", "orphan"), labels=["upstream:child"])
    graph = buildGraph([orphan])

    assert graph.orphans == (4001,)
    assert graph.items[4001].parent == 9999
    assert "parent-not-open" in graph.items[4001].reasons
    assert graph.children == {}


def test_duplicate_candidate_keys_are_grouped() -> None:
    first = row(5001, "[intake] alice/shared", childBody(7000, "alice", "tools", "shared"), labels=["upstream:child"])
    second = row(5002, "[intake] alice/shared", childBody(7000, "alice", "tools", "shared"), labels=["upstream:child"])
    umbrella = row(7000, "[upstream] alice/tools → v1.0.0", umbrellaBody("alice/tools", "v1.0.0", ["shared"]), labels=["upstream:release"])

    graph = buildGraph([first, second, umbrella])

    assert graph.duplicates == {"upstream-candidate:alice/tools:shared": (5001, 5002)}
    assert graph.orphans == ()


def test_umbrella_versions_order_semver_tolerant() -> None:
    versions = ["v7.0.0", "0.6.13", "v0.60.340.0", "v0.9.0", "1.0.0", "1.0.0-rc1"]
    rows = [
        row(8000 + index, f"[upstream] alice/tools → {version}", umbrellaBody("alice/tools", version, []), labels=["upstream:release"])
        for index, version in enumerate(versions)
    ]
    graph = buildGraph(rows)
    ordered = [graph.items[number].version for number in graph.suites["upstream-suite:alice/tools"]]

    assert ordered == ["0.6.13", "v0.9.0", "v0.60.340.0", "1.0.0-rc1", "1.0.0", "v7.0.0"]
    assert compareVersions("v0.60.340.0", "0.6.13") == 1
    assert compareVersions("0.6", "0.6.0") == 0
    assert compareVersions("v7.0.0", "7.0.0.1") == -1


def test_gh_aw_bot_reports_are_botreports_and_other_bot_issues_are_untracked() -> None:
    census = loadCensus(FIXTURE, NOW, MAX_AGE)
    byNumber = census.byNumber()

    for number in (2126, 2127):
        identity = classify(byNumber[number])
        assert identity.kind == "botreport"
        assert identity.family == "gh-aw"
        assert identity.key.startswith("bot-report:gh-aw:")

    plain = classify(row(6001, "Nightly bot note", author="github-actions[bot]"))
    assert plain.kind == "untracked"
    assert plain.key == "issue:6001"


def test_human_issue_is_untracked() -> None:
    identity = classify(loadCensus(FIXTURE, NOW, MAX_AGE).byNumber()[2130])
    assert identity.kind == "untracked"
    assert identity.key == "issue:2130"


# ---------------------------------------------------------------- collector


def fakeListing(pages: list[list[dict]], failPage: int | None = None, status: int = 200):
    """Fake GitHub: open pages are served in order with the live cursor Link shape; closed listing is empty and complete."""
    total = len(pages)

    def fetch(url: str) -> Response:
        if "actions/workflows" in url:
            return Response(200, {}, json.dumps({"total_count": 0, "workflows": []}))
        if "state=closed" in url:
            return Response(200, {}, "[]")
        number = servedPage(parse_qs(urlparse(url).query))
        if failPage == number:
            if status == 200:
                raise FetchError("rate-limited")
            return Response(status, {}, "{}")
        if number > total:
            return Response(200, {}, "[]")
        link = realLinkHeader("open", 100, number, total)
        return Response(200, {"link": link} if link else {}, json.dumps(pages[number - 1]))

    return fetch


def sampleRows(count: int, start: int) -> list[dict]:
    return [
        {"number": start + index, "title": f"t{start + index}", "state": "open", "labels": [],
         "user": {"login": "alice"}, "body": "b", "created_at": NOW, "updated_at": NOW}
        for index in range(count)
    ]


def test_collector_follows_three_pages_to_a_complete_census(tmp_path: Path) -> None:
    pages = [sampleRows(2, 1), sampleRows(2, 3), sampleRows(1, 5)]
    out = tmp_path / "inputs" / "github-issues.json"

    code = main(["--repo", "o/r", "--out", str(out), "--now", NOW], fetch=fakeListing(pages))

    assert code == 0
    census = loadCensus(out, NOW, MAX_AGE)
    assert census.status.status == COMPLETE
    assert len(census.openIssues()) == 5
    # Pages are summed over the open listing (3) and the closed listing (1).
    assert census.document["completeness"]["issues"]["pagesFetched"] == 4
    assert census.document["completeness"]["issues"]["expectedPages"] == 4


def test_collector_fails_closed_on_a_failing_page(tmp_path: Path) -> None:
    pages = [sampleRows(2, 1), sampleRows(2, 3), sampleRows(1, 5)]
    out = tmp_path / "github-issues.json"

    code = main(["--repo", "o/r", "--out", str(out), "--now", NOW], fetch=fakeListing(pages, failPage=2, status=502))

    assert code != 0
    census = loadCensus(out, NOW, MAX_AGE)
    assert census.status.status == INCOMPLETE
    assert census.document["completeness"]["issues"]["complete"] is False
    assert "http-502" in census.document["completeness"]["issues"]["reason"]


def test_collector_reports_rate_limit_without_a_complete_file(tmp_path: Path) -> None:
    pages = [sampleRows(2, 1), sampleRows(2, 3)]
    document = collectCensus("o/r", FIXED_NOW, fakeListing(pages, failPage=2))

    assert document["completeness"]["issues"]["complete"] is False
    assert document["completeness"]["issues"]["reason"] == "rate-limited"
    assert document["completeness"]["issues"]["pagesFetched"] == 1


def test_collector_refuses_to_claim_completeness_on_short_pagination(tmp_path: Path) -> None:
    def short(url: str) -> Response:
        if "state=closed" in url:
            return Response(200, {}, "[]")
        return Response(200, {"link": '<https://api.github.com/x?page=3>; rel="last"'}, json.dumps(sampleRows(2, 1)))

    document = collectCensus("o/r", FIXED_NOW, short)

    assert document["completeness"]["issues"]["complete"] is False
    assert document["completeness"]["issues"]["reason"].startswith("pagination-short")


def test_census_file_written_by_collector_is_valid_schema(tmp_path: Path) -> None:
    pages = [sampleRows(1, 1)]
    out = tmp_path / "github-issues.json"
    main(["--repo", "o/r", "--out", str(out), "--now", NOW], fetch=fakeListing(pages))
    document = json.loads(out.read_text(encoding="utf-8"))

    assert document["schemaVersion"] == "steward-github-census-v1"
    assert document["issues"][0]["bodySha256"] == bodySha256("b")
