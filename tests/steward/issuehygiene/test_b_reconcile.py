from __future__ import annotations

import json
import random
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gaia_cli.steward.issuehygiene.census import SCHEMA_VERSION as CENSUS_SCHEMA, Census, bodySha256, loadCensus, validateCensus
from gaia_cli.steward.issuehygiene.hygienepolicy import KNOWN_RULE_IDS, HygienePolicy, loadHygienePolicy
from gaia_cli.steward.issuehygiene.reconcile import (
    manifestDigest,
    probeWorkflow,
    questionId,
    reconcile,
    workflowRunnables,
)
from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex

REPO_ROOT = Path(__file__).resolve().parents[3]
FIXTURE = REPO_ROOT / "tests" / "fixtures" / "issuehygiene" / "census-four-families.json"
NOW = datetime(2026, 10, 21, 19, 30, tzinfo=timezone.utc)
FETCHED = "2026-10-21T19:00:00Z"
BOT = "github-actions[bot]"
BLOB = "https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md"


def policyFor(**overrides) -> HygienePolicy:
    raw = {
        "maxClosuresPerRun": 10,
        "maxCensusAgeSeconds": 21600,
        "closedWindowDays": 30,
        "enabledRules": list(KNOWN_RULE_IDS),
        "a5Disabled": [],
        "writesEnabled": True,
    }
    raw.update(overrides)
    return loadHygienePolicy(raw)


def mkRow(number, title, body="", labels=(), author=BOT, updatedAt="2026-10-21T10:00:00Z", isPullRequest=False, mergedAt=None, state="open", stateReason=None):
    return {
        "number": number, "title": title, "state": state, "stateReason": stateReason,
        "labels": list(labels), "author": author, "createdAt": FETCHED, "updatedAt": updatedAt,
        "closedAt": None if state == "open" else FETCHED, "comments": 0, "body": body,
        "bodySha256": bodySha256(body), "isPullRequest": isPullRequest, "mergedAt": mergedAt,
        "headRef": None, "baseRef": None,
    }


def childRow(number, suggested, evidenceUrl, parent=20, labels=("upstream:child",), updatedAt="2026-10-21T10:00:00Z"):
    umbrella = f"> Auto-populated by upstream watcher. Umbrella: #{parent}.\n\n" if parent is not None else ""
    body = (
        f"{umbrella}---\n\n## New skill intake proposal\n\n**Suggested ID:** `{suggested}`\n"
        f"### Evidence\n\n- **type:** `repo`\n- **url:** {evidenceUrl}\n"
    )
    return mkRow(number, f"[intake] {suggested}", body, labels=labels, updatedAt=updatedAt)


def umbrellaRow(number, skillId, version, adds=(), extraBody="", title=None, labels=("upstream:release",)):
    payload = {"skillId": skillId, "newVersion": version, "componentAdds": list(adds), "componentRemoves": []}
    body = "## Upstream release detected\n\n<!-- gaia-upstream-payload\n" + json.dumps(payload, indent=2) + "\n-->\n" + extraBody
    return mkRow(number, title or f"[upstream] {skillId} → {version}", body, labels=labels)


def botRow(number, title, body, labels=("agentic-workflows",)):
    return mkRow(number, title, body, labels=labels)


def censusOf(rows, closed=(), complete=True, fetchedAt=FETCHED):
    issuesDone = {"complete": complete, "pagesFetched": 1, "expectedPages": 1, "itemCount": len(rows), "lastLink": None}
    document = {
        "schemaVersion": CENSUS_SCHEMA, "repo": "gaia-research/gaia-skill-tree", "fetchedAt": fetchedAt,
        "source": "rest",
        "completeness": {"issues": issuesDone, "pulls": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": 0, "lastLink": None}},
        "issues": list(rows), "recentlyClosed": list(closed),
    }
    status = validateCensus(document, NOW, 21600)
    return Census(document, status, "test")


def writeNamed(root: Path, identifier: str, body: str) -> None:
    contributor, slug = identifier.split("/")
    target = root / "registry" / "named" / contributor / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(body, encoding="utf-8")


def skill(identifier, github="", status="named", extra=""):
    contributor = identifier.split("/")[0]
    link = f"links:\n  github: {github}\n" if github else ""
    return f"---\nid: {identifier}\ncontributor: {contributor}\nstatus: {status}\n{link}{extra}---\n\n## Body\n"


def run(census, root: Path, policy=None, workflowDisabled=None):
    return reconcile(census, buildRegistryIndex(root), policy or policyFor(), NOW, workflowDisabled)


def item(manifest, number):
    matches = [entry for entry in manifest["items"] if entry["issue"] == number]
    assert len(matches) == 1
    return matches[0]


# ------------------------------------------------------------------ A1 child-curated

def a1Fixture(tmp_path: Path, registryText: str | None = None, childUrl: str = BLOB, extraRows=()):
    rows = [
        umbrellaRow(20, "obra/superpowers", "v7.0.0"),
        childRow(10, "obra/writing-skills", childUrl),
        *extraRows,
    ]
    if registryText is not None:
        writeNamed(tmp_path, "obra/writing-skills", registryText)
    return censusOf(rows)


def test_a1_positive_closes_child_with_exact_registry_and_equal_link(tmp_path: Path):
    census = a1Fixture(tmp_path, skill("obra/writing-skills", github=BLOB))
    manifest = run(census, tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "A"
    assert child["ruleId"] == "A1-child-curated"
    assert child["state"] == "resolved"
    assert child["proposedTransition"] == {"action": "close", "stateReason": "completed", "duplicateOf": None}
    registryEntries = [entry for entry in child["evidence"] if entry["type"] == "registry"]
    assert len(registryEntries) == 1 and registryEntries[0]["sha256"]


PINNED = BLOB.replace("/main/", "/v6.4.1/")
SHA_PINNED = BLOB.replace("/main/", "/7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd/")
REGISTRY_PATH = "registry/named/obra/writing-skills.md"


def proofOf(child: dict) -> list[tuple[str, str, str]]:
    return [(entry["type"], entry["ref"], entry["detail"]) for entry in child["evidence"]]


def test_a1_negative_url_differs(tmp_path: Path):
    other = BLOB.replace("writing-skills/SKILL.md", "writing-skills/README.md")
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=other)), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert child["state"] == "ambiguous"
    assert "registry-link-differs" in child["notProven"]
    assert "registry-path-differs" in child["notProven"]
    assert "registry-repo-differs" not in child["notProven"]


def test_a1_negative_draft_status(tmp_path: Path):
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=BLOB, status="draft")), tmp_path)
    assert item(manifest, 10)["authority"] == "B"
    assert "registry-draft" in item(manifest, 10)["notProven"]


def test_a1_positive_ref_only_tag_vs_main_is_a1_with_ref_differs(tmp_path: Path):
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=PINNED)), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "A"
    assert child["ruleId"] == "A1-child-curated"
    assert child["state"] == "resolved"
    assert child["notProven"] == []
    assert child["proposedTransition"] == {"action": "close", "stateReason": "completed", "duplicateOf": None}
    proof = proofOf(child)
    assert ("registry", REGISTRY_PATH, "ref-differs: registry=v6.4.1 intake=main") in proof
    assert ("registry", PINNED, f"links.github of {REGISTRY_PATH}") in proof
    assert ("issue", "#10", f"evidence {BLOB}") in proof


def test_a1_positive_ref_only_commit_sha_vs_main_is_a1_with_ref_differs(tmp_path: Path):
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=SHA_PINNED)), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "A"
    assert child["ruleId"] == "A1-child-curated"
    assert ("registry", REGISTRY_PATH, "ref-differs: registry=7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd intake=main") in proofOf(child)


def test_a1_positive_exact_link_adds_no_second_registry_url(tmp_path: Path):
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=BLOB)), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "A"
    assert [entry for entry in proofOf(child) if entry[0] == "registry"] == [("registry", REGISTRY_PATH, "links.github equals the evidence URL")]


@pytest.mark.parametrize("spelling", [
    BLOB.replace("/blob/", "/tree/"),
    BLOB + "/",
    BLOB + "?plain=1",
])
def test_a1_positive_tree_trailing_slash_and_query_fold_to_the_same_file(tmp_path: Path, spelling: str):
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=spelling)), tmp_path)
    assert item(manifest, 10)["authority"] == "A"
    assert item(manifest, 10)["notProven"] == []


def test_a1_positive_fork_link_closes_when_declared_upstream_repo_and_path_match(tmp_path: Path):
    extra = "upstream:\n  repo: obra/superpowers\n  version: v6.4.1\n"
    fork = "https://github.com/garrytan/gstack/blob/main/skills/writing-skills/SKILL.md"
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=fork, extra=extra)), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "A"
    assert ("registry", REGISTRY_PATH, "upstream repo and path match the evidence URL") in proofOf(child)


@pytest.mark.parametrize("registryUrl", [
    BLOB.replace("obra/superpowers", "obra/other-repo"),
    BLOB.replace("obra/superpowers", "obra/other-repo").replace("/main/", "/v6.4.1/"),
])
def test_a1_negative_different_repo_is_never_a_even_when_ref_is_ignored(tmp_path: Path, registryUrl: str):
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=registryUrl)), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert child["ruleId"] is None
    assert "registry-repo-differs" in child["notProven"]
    assert "registry-path-differs" not in child["notProven"]


def test_a1_negative_different_file_name_is_not_the_same_file(tmp_path: Path):
    rootSkill = "https://github.com/obra/superpowers/blob/main/SKILL.md"
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=rootSkill)), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert "registry-path-differs" in child["notProven"]


def test_a1_negative_different_path_stays_b_even_with_a_pinned_ref(tmp_path: Path):
    readme = PINNED.replace("writing-skills/SKILL.md", "writing-skills/README.md")
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=readme)), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert "registry-path-differs" in child["notProven"]


# ------------------------------------------------------------------ A1 ref/path split trust

SLASH_BRANCH = "https://github.com/obra/superpowers/blob/feature/x/skills/writing-skills/SKILL.md"
SLASH_AT_MAIN = "https://github.com/obra/superpowers/blob/main/x/skills/writing-skills/SKILL.md"
RELEASE_BRANCH = "https://github.com/obra/superpowers/blob/release/x/skills/writing-skills/SKILL.md"


def test_a1_negative_slash_branch_in_evidence_is_ref_split_ambiguous(tmp_path: Path):
    # The evidence splits as ref "feature" with path "x/skills/...". The registry splits as ref "main"
    # with that same path. Ignoring the ref would call them one file, but "feature/x" may be the branch.
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=SLASH_AT_MAIN), childUrl=SLASH_BRANCH), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert child["ruleId"] is None
    assert child["state"] == "ambiguous"
    assert child["proposedTransition"]["action"] == "keep"
    assert "ref-split-ambiguous" in child["notProven"]
    assert "registry-path-differs" not in child["notProven"]
    assert "registry-link-differs" not in child["notProven"]
    assert ("registry", SLASH_AT_MAIN, f"ref split ambiguous against evidence {SLASH_BRANCH}") in proofOf(child)
    assert ("issue", "#10", f"evidence {SLASH_BRANCH}") in proofOf(child)


@pytest.mark.parametrize("registryUrl, childUrl", [
    (SLASH_AT_MAIN, SLASH_BRANCH),
    (SLASH_BRANCH, SLASH_AT_MAIN),
    (RELEASE_BRANCH, SLASH_BRANCH),
])
def test_a1_negative_slash_branch_on_either_side_is_ref_split_ambiguous(tmp_path: Path, registryUrl: str, childUrl: str):
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=registryUrl), childUrl=childUrl), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert child["state"] == "ambiguous"
    assert "ref-split-ambiguous" in child["notProven"]


@pytest.mark.parametrize("spelling", [
    SLASH_BRANCH,
    SLASH_BRANCH.replace("/blob/", "/tree/"),
    SLASH_BRANCH + "/",
])
def test_a1_positive_identical_slash_ref_urls_still_prove_the_same_file(tmp_path: Path, spelling: str):
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=spelling), childUrl=SLASH_BRANCH), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "A"
    assert child["ruleId"] == "A1-child-curated"
    assert child["notProven"] == []
    assert ("registry", REGISTRY_PATH, "links.github equals the evidence URL") in proofOf(child)


@pytest.mark.parametrize("registryRef, evidenceRef", [
    ("v6.4.1", "main"),
    ("7a2a6917367e6dd7ce22f4c321c4a852dcf58dfd", "main"),
    ("0.6.10", "v0.51.6.0"),
    ("HEAD", "master"),
    ("2.0.0-rc.1", "1.0.0+build.5"),
])
def test_a1_positive_simple_refs_on_both_sides_stay_a(tmp_path: Path, registryRef: str, evidenceRef: str):
    registry = BLOB.replace("/main/", f"/{registryRef}/")
    childUrl = BLOB.replace("/main/", f"/{evidenceRef}/")
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=registry), childUrl=childUrl), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "A"
    assert child["ruleId"] == "A1-child-curated"
    assert child["notProven"] == []


def test_a1_negative_non_simple_ref_without_a_slash_is_ambiguous(tmp_path: Path):
    registry = BLOB.replace("/main/", "/release-1.2/")
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=registry)), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert "ref-split-ambiguous" in child["notProven"]
    assert "registry-repo-differs" not in child["notProven"]


def test_a1_negative_ref_only_difference_is_not_proof_when_draft(tmp_path: Path):
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=PINNED, status="draft")), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert "registry-draft" in child["notProven"]
    assert "registry-link-differs" not in child["notProven"]


def test_a1_negative_ref_only_alias_handle_is_never_a(tmp_path: Path):
    rows = [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "addyosmani/writing-skills", BLOB)]
    writeNamed(tmp_path, "addy-osmani/writing-skills", skill("addy-osmani/writing-skills", github=PINNED))
    manifest = run(censusOf(rows), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "C"
    assert child["ruleId"] is None
    assert "no-exact-registry-record" in child["notProven"]


def test_a1_positive_via_upstream_repo_and_path_when_ref_differs(tmp_path: Path):
    pinned = BLOB.replace("/main/", "/v6.4.1/")
    extra = "upstream:\n  repo: obra/superpowers\n  version: v6.4.1\n"
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=pinned, extra=extra)), tmp_path)
    assert item(manifest, 10)["authority"] == "A"


def test_a1_negative_upstream_repo_differs(tmp_path: Path):
    pinned = BLOB.replace("/main/", "/v6.4.1/")
    extra = "upstream:\n  repo: obra/other\n  version: v6.4.1\n"
    manifest = run(a1Fixture(tmp_path, skill("obra/writing-skills", github=pinned, extra=extra)), tmp_path)
    assert item(manifest, 10)["authority"] == "B"
    assert "registry-repo-differs" in item(manifest, 10)["notProven"]


def test_a1_negative_contributor_field_disagrees_with_path_is_unreadable(tmp_path: Path):
    text = skill("obra/writing-skills", github=BLOB).replace("contributor: obra", "contributor: someone")
    writeNamed(tmp_path, "obra/writing-skills", text)
    manifest = run(censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB)]), tmp_path)
    assert item(manifest, 10)["state"] == "not-evaluated"
    assert item(manifest, 10)["authority"] == "none"


def test_a1_negative_alias_only_is_never_a(tmp_path: Path):
    rows = [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "addyosmani/writing-skills", BLOB)]
    writeNamed(tmp_path, "addy-osmani/writing-skills", skill("addy-osmani/writing-skills", github=BLOB))
    manifest = run(censusOf(rows), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "C"
    assert child["state"] == "awaiting-founder"
    assert child["authority"] != "A"


def test_a1_negative_unknown_suggested_id_or_evidence_url(tmp_path: Path):
    rows = [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", "_unknown")]
    manifest = run(censusOf(rows), tmp_path)
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert "evidence-repo-unknown" in child["unknowns"]


def test_a1_negative_rule_disabled_downgrades_to_b(tmp_path: Path):
    census = a1Fixture(tmp_path, skill("obra/writing-skills", github=BLOB))
    manifest = run(census, tmp_path, policyFor(enabledRules=[rule for rule in KNOWN_RULE_IDS if rule != "A1-child-curated"]))
    child = item(manifest, 10)
    assert child["authority"] == "B"
    assert child["ruleId"] is None
    assert "rule-disabled:A1-child-curated" in child["notProven"]
    assert child["state"] == "resolved"


def test_a1_negative_unreadable_registry_file_is_not_evaluated(tmp_path: Path):
    writeNamed(tmp_path, "obra/writing-skills", "no frontmatter at all\n")
    manifest = run(a1Fixture(tmp_path, None), tmp_path)
    child = item(manifest, 10)
    assert child["state"] == "not-evaluated"
    assert child["authority"] == "none"
    assert 10 in manifest["coverage"]["notEvaluated"]
    assert any("registry-unreadable" in entry for entry in manifest["coverage"]["unknown"])


def test_a1_negative_unreadable_same_slug_other_handle_is_not_evaluated(tmp_path: Path):
    writeNamed(tmp_path, "garrytan/writing-skills", "broken\n")
    manifest = run(a1Fixture(tmp_path, None), tmp_path)
    assert item(manifest, 10)["state"] == "not-evaluated"


# ------------------------------------------------------------------ A2 umbrella-synced

def suiteRegistry(tmp_path: Path, version="v7.0.0", frozen=False, repo="obra/superpowers"):
    extra = f"installable: false\n" if frozen else ""
    writeNamed(tmp_path, "obra/superpowers", skill("obra/superpowers", extra=f"{extra}upstream:\n  repo: {repo}\n  version: {version}\n"))


def test_a2_positive_registry_version_matches_and_no_open_children(tmp_path: Path):
    suiteRegistry(tmp_path)
    manifest = run(censusOf([umbrellaRow(30, "obra/superpowers", "v7.0.0")]), tmp_path)
    umbrella = item(manifest, 30)
    assert umbrella["authority"] == "A"
    assert umbrella["ruleId"] == "A2-umbrella-synced"
    assert umbrella["proposedTransition"]["stateReason"] == "completed"


def test_a2_negative_version_mismatch(tmp_path: Path):
    suiteRegistry(tmp_path, version="v6.9.0")
    manifest = run(censusOf([umbrellaRow(30, "obra/superpowers", "v7.0.0")]), tmp_path)
    assert item(manifest, 30)["authority"] == "B"
    assert "registry-version-differs" in item(manifest, 30)["notProven"]


def test_a2_negative_frozen_suite(tmp_path: Path):
    suiteRegistry(tmp_path, frozen=True)
    manifest = run(censusOf([umbrellaRow(30, "obra/superpowers", "v7.0.0")]), tmp_path)
    assert item(manifest, 30)["authority"] == "B"
    assert "suite-frozen" in item(manifest, 30)["notProven"]


def test_a2_negative_no_suite_record(tmp_path: Path):
    manifest = run(censusOf([umbrellaRow(30, "obra/superpowers", "v7.0.0")]), tmp_path)
    assert item(manifest, 30)["authority"] == "B"
    assert "suite-record-missing" in item(manifest, 30)["notProven"]


def test_a2_negative_open_children_block(tmp_path: Path):
    suiteRegistry(tmp_path)
    rows = [umbrellaRow(30, "obra/superpowers", "v7.0.0"), childRow(31, "obra/foo", BLOB.replace("writing-skills", "foo"), parent=30)]
    manifest = run(censusOf(rows), tmp_path)
    umbrella = item(manifest, 30)
    assert umbrella["authority"] == "B"
    assert umbrella["dependencies"] == [31]


def test_a2_positive_via_merged_sync_pr_when_registry_lags(tmp_path: Path):
    suiteRegistry(tmp_path, version="v6.9.0")
    pr = mkRow(77, "[upstream sync] obra/superpowers v7.0.0", "", author=BOT, isPullRequest=True, mergedAt=FETCHED, state="closed")
    manifest = run(censusOf([umbrellaRow(30, "obra/superpowers", "v7.0.0")], closed=[pr]), tmp_path)
    umbrella = item(manifest, 30)
    assert umbrella["authority"] == "A"
    assert any(entry["type"] == "pr" and entry["ref"] == "#77" for entry in umbrella["evidence"])


def test_a2_negative_title_payload_mismatch_is_c_not_a(tmp_path: Path):
    suiteRegistry(tmp_path)
    row = umbrellaRow(33, "addy-osmani/agent-skills", "v7.0.0", title="[upstream] addyosmani/agent-skills → 0.6.13")
    manifest = run(censusOf([row]), tmp_path)
    umbrella = item(manifest, 33)
    assert umbrella["authority"] == "C"
    assert any(question for question in manifest["founderQuestions"] if 33 in question["affected"])


def test_a2_negative_unknown_payload_stays_b(tmp_path: Path):
    suiteRegistry(tmp_path)
    row = mkRow(34, "[upstream] obra/superpowers → v7.0.0", "no payload here", labels=("upstream:release",))
    manifest = run(censusOf([row]), tmp_path)
    umbrella = item(manifest, 34)
    assert umbrella["authority"] == "B"
    assert "payload-absent" in umbrella["unknowns"]


# ------------------------------------------------------------------ A3 umbrella-superseded

def supersedeRows(olderAdds=("foo",), newerAdds=("foo",), newerVersion="v7.0.0", listFoo=True):
    listing = "- `+ foo` (child intake: _pending_)\n" if listFoo else ""
    return [
        umbrellaRow(30, "obra/superpowers", "v6.0.0", adds=olderAdds),
        childRow(31, "obra/foo", BLOB.replace("writing-skills", "foo"), parent=30),
        umbrellaRow(40, "obra/superpowers", newerVersion, adds=newerAdds, extraBody=listing),
    ]


def test_a3_positive_superseded_umbrella_with_listed_children(tmp_path: Path):
    manifest = run(censusOf(supersedeRows()), tmp_path)
    older = item(manifest, 30)
    assert older["authority"] == "A"
    assert older["ruleId"] == "A3-umbrella-superseded"
    assert older["state"] == "superseded"
    assert older["canonical"] == 40
    assert older["proposedTransition"]["stateReason"] == "not_planned"


def test_a3_negative_child_not_listed_in_newer(tmp_path: Path):
    manifest = run(censusOf(supersedeRows(listFoo=False)), tmp_path)
    older = item(manifest, 30)
    assert older["authority"] == "B"
    assert "not-listed-in-superseder:31" in older["notProven"]


def test_a3_negative_newer_lacks_component_add(tmp_path: Path):
    manifest = run(censusOf(supersedeRows(newerAdds=("bar",))), tmp_path)
    assert item(manifest, 30)["authority"] == "B"
    assert "superseder-lacks-adds:foo" in item(manifest, 30)["notProven"]


def test_a3_negative_superseder_not_newer(tmp_path: Path):
    manifest = run(censusOf(supersedeRows(newerVersion="v6.0.0")), tmp_path)
    assert item(manifest, 30)["authority"] == "B"
    assert "superseder-not-newer" in item(manifest, 30)["notProven"]


def test_a3_negative_unknown_version_blocks(tmp_path: Path):
    rows = supersedeRows(newerVersion="vNEXT")
    manifest = run(censusOf(rows), tmp_path)
    assert item(manifest, 30)["authority"] == "B"


def test_a3_negative_superseder_rule_disabled(tmp_path: Path):
    manifest = run(censusOf(supersedeRows()), tmp_path, policyFor(enabledRules=[rule for rule in KNOWN_RULE_IDS if rule != "A3-umbrella-superseded"]))
    assert item(manifest, 30)["authority"] == "B"
    assert item(manifest, 30)["ruleId"] is None


# ------------------------------------------------------------------ A4 duplicate-child

def dupRows(second=BLOB, labelsSecond=("upstream:child",)):
    return [
        umbrellaRow(60, "obra/superpowers", "v7.0.0"),
        childRow(50, "obra/dup", BLOB.replace("writing-skills", "dup"), parent=60),
        childRow(51, "obra/dup", second.replace("writing-skills", "dup"), parent=60, labels=labelsSecond),
    ]


def test_a4_positive_later_duplicate_of_lower_numbered_canonical(tmp_path: Path):
    manifest = run(censusOf(dupRows()), tmp_path)
    duplicate = item(manifest, 51)
    assert duplicate["authority"] == "A"
    assert duplicate["ruleId"] == "A4-duplicate-child"
    assert duplicate["proposedTransition"] == {"action": "close", "stateReason": "duplicate", "duplicateOf": 50}
    assert item(manifest, 50)["authority"] == "B"


def test_a4_negative_evidence_url_differs(tmp_path: Path):
    manifest = run(censusOf(dupRows(second=BLOB.replace("/main/", "/v1/"))), tmp_path)
    assert item(manifest, 51)["authority"] == "B"
    assert "evidence-url-differs-from-canonical" in item(manifest, 51)["notProven"]


def test_a4_negative_rule_disabled(tmp_path: Path):
    manifest = run(censusOf(dupRows()), tmp_path, policyFor(enabledRules=[rule for rule in KNOWN_RULE_IDS if rule != "A4-duplicate-child"]))
    assert item(manifest, 51)["authority"] == "B"


def test_a4_positive_identical_slash_ref_evidence_still_duplicates(tmp_path: Path):
    # A4 compares full blob URLs with the ref included, so a slash-containing ref needs no split check.
    slash = SLASH_BRANCH.replace("writing-skills", "dup")
    rows = [
        umbrellaRow(60, "obra/superpowers", "v7.0.0"),
        childRow(50, "obra/dup", slash, parent=60),
        childRow(51, "obra/dup", slash, parent=60),
    ]
    manifest = run(censusOf(rows), tmp_path)
    duplicate = item(manifest, 51)
    assert duplicate["authority"] == "A"
    assert duplicate["ruleId"] == "A4-duplicate-child"


# ------------------------------------------------------------------ A5 bot-report superseded

COPILOT_BODY = "### What happened\n\n[View run](https://github.com/x/y/actions/runs/1) · [Workflow source](https://github.com/x/y/blob/main/.github/workflows/steward-build-copilot.md)\n"


def bot5Census(title="[aw] Steward Build Copilot: hit billing error", labels=("agentic-workflows",), body=COPILOT_BODY):
    return censusOf([botRow(2127, title, body, labels=labels)])


def a5Proof(proven=True):
    return {"steward-build-copilot.lock.yml": {"path": "steward-build-copilot.lock.yml", "sha256": "ab" * 32, "proven": proven, "reasons": ["every-job-gated-false"] if proven else ["job-may-run"]}}


A5_POLICY = dict(a5Disabled=[".github/workflows/steward-build-copilot.lock.yml"])


def test_a5_positive_when_workflow_listed_and_proven_disabled(tmp_path: Path):
    manifest = run(bot5Census(), tmp_path, policyFor(**A5_POLICY), a5Proof())
    bot = item(manifest, 2127)
    assert bot["authority"] == "A"
    assert bot["ruleId"] == "A5-botreport-superseded"
    assert any(entry["type"] == "workflow" for entry in bot["evidence"])


def test_a5_negative_not_listed_in_policy(tmp_path: Path):
    manifest = run(bot5Census(), tmp_path, policyFor(), a5Proof())
    assert item(manifest, 2127)["authority"] == "C"


def test_a5_negative_not_proven_disabled(tmp_path: Path):
    manifest = run(bot5Census(), tmp_path, policyFor(**A5_POLICY), a5Proof(proven=False))
    assert item(manifest, 2127)["authority"] == "C"


def test_a5_negative_detection_runs_tracker_and_security_markers(tmp_path: Path):
    tracker = run(bot5Census(title="[aw] Detection Runs", body=COPILOT_BODY), tmp_path, policyFor(**A5_POLICY), a5Proof())
    assert item(tracker, 2127)["authority"] == "C"
    secured = run(bot5Census(labels=("agentic-workflows", "security")), tmp_path, policyFor(**A5_POLICY), a5Proof())
    assert item(secured, 2127)["authority"] == "C"
    threat = run(bot5Census(body=COPILOT_BODY + "\nDetects potential security threats\n"), tmp_path, policyFor(**A5_POLICY), a5Proof())
    assert item(threat, 2127)["authority"] == "C"


def test_a5_negative_no_workflow_reference(tmp_path: Path):
    manifest = run(bot5Census(body="billing failed, no link"), tmp_path, policyFor(**A5_POLICY), a5Proof())
    assert item(manifest, 2127)["authority"] == "C"
    assert "no-workflow-reference" in item(manifest, 2127)["notProven"]


def test_gh_aw_pair_compresses_to_one_question(tmp_path: Path):
    rows = [
        botRow(2126, "[aw] Detection Runs", "tracker body with security threats"),
        botRow(2127, "[aw] Steward Build Copilot: billing", COPILOT_BODY),
    ]
    manifest = run(censusOf(rows), tmp_path)
    questions = [question for question in manifest["founderQuestions"] if "gh-aw" in question["question"]]
    assert len(questions) == 1
    assert questions[0]["affected"] == [2126, 2127]
    assert questions[0]["recommendation"] is None
    assert questions[0]["basis"] == "no basis for an opinion"
    assert questions[0]["id"] == questionId(questions[0]["question"])
    assert questions[0]["id"].startswith("Q-") and len(questions[0]["id"]) == 10


# ------------------------------------------------------------------ labels and gates

def test_skip_child_gate_umbrella_with_open_children_is_c_and_label_never_closes(tmp_path: Path):
    rows = [
        umbrellaRow(70, "garrytan/gbrain", "v0.60.0", labels=("upstream:release", "upstream:approved", "skip-child-gate")),
        childRow(71, "garrytan/x", BLOB.replace("writing-skills", "x"), parent=70),
    ]
    manifest = run(censusOf(rows), tmp_path)
    umbrella = item(manifest, 70)
    assert umbrella["authority"] == "C"
    assert umbrella["state"] == "awaiting-founder"
    assert umbrella["proposedTransition"]["action"] == "keep"
    question = next(q for q in manifest["founderQuestions"] if 70 in q["affected"])
    assert question["options"] == ["accept", "reject", "defer"]


def test_approved_label_alone_does_not_make_child_closable(tmp_path: Path):
    rows = [umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB, labels=("upstream:child", "upstream:approved", "skip-child-gate"))]
    manifest = run(censusOf(rows), tmp_path)
    assert item(manifest, 10)["authority"] == "B"


def test_title_payload_mismatch_produces_one_question_per_distinct_question(tmp_path: Path):
    rows = [
        umbrellaRow(33, "addy-osmani/agent-skills", "v1", title="[upstream] addyosmani/agent-skills → v1"),
        umbrellaRow(34, "addy-osmani/agent-skills", "v2", title="[upstream] addyosmani/agent-skills → v2"),
    ]
    manifest = run(censusOf(rows), tmp_path)
    questions = [q for q in manifest["founderQuestions"] if "title names suite" in q["question"]]
    assert len(questions) == 1
    assert questions[0]["affected"] == [33, 34]


def test_alias_questions_group_by_handle_pair(tmp_path: Path):
    writeNamed(tmp_path, "addy-osmani/one", skill("addy-osmani/one", github=BLOB.replace("writing-skills", "one")))
    writeNamed(tmp_path, "addy-osmani/two", skill("addy-osmani/two", github=BLOB.replace("writing-skills", "two")))
    rows = [
        umbrellaRow(20, "obra/superpowers", "v7.0.0"),
        childRow(10, "addyosmani/one", BLOB.replace("writing-skills", "one")),
        childRow(11, "addyosmani/two", BLOB.replace("writing-skills", "two")),
    ]
    manifest = run(censusOf(rows), tmp_path)
    handle = [q for q in manifest["founderQuestions"] if "handle" in q["question"]]
    assert len(handle) == 1
    assert handle[0]["affected"] == [10, 11]
    assert handle[0]["recommendation"] == "same-skill"


# ------------------------------------------------------------------ census gating

def test_incomplete_census_makes_every_item_not_evaluated(tmp_path: Path):
    census = censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0"), childRow(10, "obra/writing-skills", BLOB)], complete=False)
    manifest = run(census, tmp_path)
    assert manifest["censusStatus"] == "incomplete"
    assert all(entry["state"] == "not-evaluated" and entry["authority"] == "none" for entry in manifest["items"])
    assert manifest["coverage"]["unknown"]
    assert manifest["coverage"]["notEvaluated"] == [10, 20]
    assert manifest["founderQuestions"] == [] and manifest["batches"] == []


def test_stale_census_is_not_evaluated(tmp_path: Path):
    stale = censusOf([umbrellaRow(20, "obra/superpowers", "v7.0.0")], fetchedAt="2026-10-01T00:00:00Z")
    manifest = run(stale, tmp_path)
    assert manifest["censusStatus"] == "stale"
    assert manifest["items"][0]["state"] == "not-evaluated"


def test_missing_census_has_no_items(tmp_path: Path):
    from gaia_cli.steward.issuehygiene.census import CensusStatus, MISSING

    manifest = reconcile(Census(None, CensusStatus(MISSING, ("file-missing",)), "x"), buildRegistryIndex(tmp_path), policyFor(), NOW)
    assert manifest["items"] == []
    assert manifest["censusStatus"] == "missing"
    assert manifest["coverage"]["unknown"]


def test_writes_disabled_still_reports_authority_for_dry_run(tmp_path: Path):
    suite = tmp_path
    writeNamed(suite, "obra/superpowers", skill("obra/superpowers", extra="upstream:\n  repo: obra/superpowers\n  version: v7.0.0\n"))
    manifest = run(censusOf([umbrellaRow(30, "obra/superpowers", "v7.0.0")]), suite, policyFor(writesEnabled=False))
    assert item(manifest, 30)["authority"] == "A"
    assert manifest["policy"]["writesEnabled"] is False


# ------------------------------------------------------------------ batches, untracked, bootstrap

def test_batches_group_b_children_per_suite_and_orphans_go_unbatched(tmp_path: Path):
    rows = [
        umbrellaRow(20, "obra/superpowers", "v7.0.0"),
        childRow(10, "obra/foo", BLOB.replace("writing-skills", "foo"), parent=20),
        childRow(11, "obra/bar", BLOB.replace("writing-skills", "bar"), parent=999),
        mkRow(900, "human issue", "hello"),
    ]
    manifest = run(censusOf(rows), tmp_path)
    assert manifest["batches"][0]["suite"] == "obra/superpowers"
    assert manifest["batches"][0]["umbrella"] == 20
    assert manifest["batches"][0]["classB"] == ["upstream-candidate:obra/superpowers:foo"]
    assert manifest["batches"][-1] == {"suite": None, "umbrella": None, "classB": ["upstream-candidate:obra/superpowers:bar"], "size": 1}
    assert item(manifest, 900)["kind"] == "untracked"
    assert item(manifest, 900)["authority"] == "none"
    assert item(manifest, 900)["state"] == "actionable"


def test_bootstrap_is_never_authorized_for_closure(tmp_path: Path):
    row = mkRow(2091, "[upstream:bootstrap] leonxlnx/taste-skill → baseline at v2.1.4", "<!-- gaia-upstream-payload\n{\"skillId\": \"leonxlnx/taste-skill\", \"newVersion\": \"v2.1.4\"}\n-->", labels=("upstream:bootstrap", "upstream:approved"))
    writeNamed(tmp_path, "leonxlnx/taste-skill", skill("leonxlnx/taste-skill", extra="upstream:\n  repo: leonxlnx/taste-skill\n  version: v2.1.4\n"))
    manifest = run(censusOf([row]), tmp_path)
    assert item(manifest, 2091)["kind"] == "bootstrap"
    assert item(manifest, 2091)["authority"] == "none"


# ------------------------------------------------------------------ determinism and digest

def test_same_inputs_give_byte_identical_manifest(tmp_path: Path):
    rows = supersedeRows() + dupRows()[1:]
    first = json.dumps(run(censusOf(rows), tmp_path), sort_keys=True)
    second = json.dumps(run(censusOf(rows), tmp_path), sort_keys=True)
    assert first == second


def test_shuffled_census_order_gives_same_manifest(tmp_path: Path):
    rows = supersedeRows() + dupRows()
    base = run(censusOf(rows), tmp_path)
    shuffled = list(rows)
    random.Random(7).shuffle(shuffled)
    again = run(censusOf(shuffled), tmp_path)
    assert json.dumps(base, sort_keys=True) == json.dumps(again, sort_keys=True)
    assert base["manifestSha256"] == again["manifestSha256"]


def test_manifest_digest_covers_everything_but_itself(tmp_path: Path):
    manifest = run(censusOf(supersedeRows()), tmp_path)
    assert manifest["manifestSha256"] == manifestDigest(manifest)
    tampered = dict(manifest, stats=dict(manifest["stats"], classA=99))
    assert manifestDigest(tampered) != manifest["manifestSha256"]


def test_manifest_has_no_wall_clock_fields(tmp_path: Path):
    manifest = run(censusOf(supersedeRows()), tmp_path)
    assert manifest["censusFetchedAt"] == FETCHED
    assert "generatedAt" not in json.dumps(manifest)


# ------------------------------------------------------------------ workflow probe

def test_probe_workflow_proves_only_literal_false_gates(tmp_path: Path):
    workflows = tmp_path / ".github" / "workflows"
    workflows.mkdir(parents=True)
    (workflows / "gated.lock.yml").write_text("on: schedule\njobs:\n  a:\n    if: ${{ false }}\n    runs-on: x\n", encoding="utf-8")
    (workflows / "live.lock.yml").write_text("on: push\njobs:\n  a:\n    runs-on: x\n", encoding="utf-8")
    assert probeWorkflow(tmp_path, "gated.lock.yml")["proven"] is True
    assert probeWorkflow(tmp_path, "live.lock.yml")["proven"] is False
    assert probeWorkflow(tmp_path, "missing.lock.yml")["reasons"] == ["file-missing"]
    assert probeWorkflow(tmp_path, "../escape.yml")["proven"] is False


def test_workflow_runnables_maps_md_to_lock_yml():
    body = "see .github/workflows/steward-build-copilot.md and .github/workflows/steward-verify.lock.yml"
    assert workflowRunnables(body) == ["steward-build-copilot.lock.yml", "steward-verify.lock.yml"]


# ------------------------------------------------------------------ fixture and live registry cross-check

# Live cross-check after the 2026-10-21 ruling (A1 ignores the git ref). Sixteen children were
# blocked only by a ref (registry pins a tag or commit, intake points at main). 1995 was already A
# through upstream.repo. 1984 differs by repo and path. The other 22 differ only by path
# (registry plugin/skills/<name>/SKILL.md, intake skills/<name>/SKILL.md) and stay B.
LIVE_A1_CHILDREN = {1981, 1994, 1995, 2003, 2004, 2005, 2006, 2007, 2009, 2010, 2011, 2012, 2016, 2017, 2018, 2022, 2024}
LIVE_PATH_ONLY_CHILDREN = {
    1923, 1924, 1927, 1928, 1934, 1937, 1940, 1941, 1948, 1950, 1953,
    1955, 1960, 1963, 1965, 1967, 1972, 1975, 1980, 1983, 1989, 1991,
}
LIVE_REPO_AND_PATH_CHILDREN = {1984}


def test_fixture_census_reconciles_to_known_counts():
    census = loadCensus(FIXTURE, now=NOW, maxAgeSeconds=21600)
    manifest = reconcile(census, buildRegistryIndex(REPO_ROOT), policyFor(), NOW)
    assert manifest["censusStatus"] == "complete"
    stats = manifest["stats"]
    assert stats["openIssues"] == 115
    assert stats["upstreamChildOpen"] == 96
    assert stats["umbrellaOpen"] == 6
    assert stats["botOpen"] == 2
    assert stats["classA"] == 17
    assert stats["classB"] == 80
    assert stats["classC"] == 7
    assert stats["notEvaluated"] == 0
    children = {entry["issue"]: entry for entry in manifest["items"] if entry["kind"] == "child"}
    assert {number for number, entry in children.items() if entry["authority"] == "A"} == LIVE_A1_CHILDREN
    assert all(children[number]["ruleId"] == "A1-child-curated" for number in LIVE_A1_CHILDREN)
    assert not any("ref-split-ambiguous" in entry["notProven"] for entry in manifest["items"])
    for number in LIVE_PATH_ONLY_CHILDREN:
        assert children[number]["authority"] == "B"
        assert "registry-path-differs" in children[number]["notProven"]
        assert "registry-repo-differs" not in children[number]["notProven"]
    for number in LIVE_REPO_AND_PATH_CHILDREN:
        assert children[number]["authority"] == "B"
        assert {"registry-repo-differs", "registry-path-differs"} <= set(children[number]["notProven"])
    questions = {tuple(q["affected"]) for q in manifest["founderQuestions"]}
    assert (2126, 2127) in questions
    assert (1835,) in questions and (1823,) in questions


def test_workflow_probes_cover_policy_entries_and_open_gh_aw_reports(tmp_path: Path):
    from gaia_cli.steward.issuehygiene.reconcile import workflowProbesFor

    workflows = tmp_path / '.github' / 'workflows'
    workflows.mkdir(parents=True)
    (workflows / 'steward-build-copilot.lock.yml').write_text("on: push\njobs:\n  a:\n    if: ${{ false }}\n", encoding='utf-8')
    census = censusOf([botRow(2127, '[aw] Steward Build Copilot: billing', COPILOT_BODY)])
    probes = workflowProbesFor(tmp_path, census, policyFor(**A5_POLICY))
    assert set(probes) == {'steward-build-copilot.lock.yml'}
    assert probes['steward-build-copilot.lock.yml']['proven'] is True
