"""Regression coverage for legacy child identity and closed finding coverage."""

from __future__ import annotations

import json

import pytest

from scripts.upstream_watcher import evidence, prechecks


def child(number: int, source: str, state: str = "open", rejected: bool = False) -> dict:
    labels = ["upstream:child"] + (["upstream:rejected"] if rejected else [])
    return {
        "number": number,
        "state": state,
        "labels": labels,
        "body": (
            f"**Suggested ID:** `alice/foo`\n\n### Evidence\n\n- **url:** {source}\n"
        ),
    }


def row(source: str) -> dict:
    return {
        "id": "suite-a/repo:foo",
        "slug": "foo",
        "suggestedId": "alice/foo",
        "evidenceUrl": source,
    }


def test_open_child_with_same_suggested_id_but_different_source_is_not_adopted():
    children, rejected = prechecks.index_children([
        child(11, "https://github.com/suite-a/repo/blob/main/skills/foo/SKILL.md")
    ])

    result = prechecks.precheck_row(
        row("https://github.com/suite-b/repo/blob/main/skills/foo/SKILL.md"), {"byId": {}, "bySlug": {}}, children, rejected
    )

    assert result["status"] == "new"
    assert result["precheck"]["tracked"] == "none"


def test_same_candidate_rejection_survives_equivalent_blob_refs():
    children, rejected = prechecks.index_children([
        child(12, "https://github.com/suite-a/repo/tree/v1/skills/foo/SKILL.md", "closed", True)
    ])

    result = prechecks.precheck_row(
        row("https://github.com/SUITE-A/REPO/blob/main/skills/foo/SKILL.md"), {"byId": {}, "bySlug": {}}, children, rejected
    )

    assert result["status"] == "rejected"
    assert result["precheck"]["priorDisposition"] == "rejected:#12"


def test_child_with_ambiguous_source_fails_closed():
    children, rejected = prechecks.index_children([child(13, "not-a-github-blob-url")])
    with pytest.raises(prechecks.AmbiguousChildIdentity):
        prechecks.precheck_row(
            row("https://github.com/suite-a/repo/blob/main/skills/foo/SKILL.md"),
            {"byId": {}, "bySlug": {}},
            children,
            rejected,
        )


def finding(**changes):
    data = {
        "finding_type": "update",
        "skillId": "suite-a/repo",
        "newVersion": "v1",
        "sourceUrl": "https://github.com/suite-a/repo/releases/tag/v1",
        "componentAdds": ["foo"],
        "componentRemoves": [],
        "linkLiveness": [],
        "nameDrift": [],
    }
    return {**data, **changes}


def closed_payload(recorded: dict) -> dict:
    payload = {
        "skillId": recorded["skillId"],
        "newVersion": recorded["newVersion"],
        "sourceUrl": recorded["sourceUrl"],
        "componentAdds": recorded["componentAdds"],
        "componentRemoves": recorded["componentRemoves"],
        "linkLiveness": recorded["linkLiveness"],
        "nameDrift": recorded["nameDrift"],
    }
    return {
        "number": 9,
        "title": "[upstream] suite-a/repo → v1",
        "state": "closed",
        "body": "<!-- gaia-upstream-payload\n" + json.dumps(payload) + "\n-->",
    }


@pytest.mark.parametrize(
    "change",
    [
        {"componentRemoves": ["old"]},
        {"linkLiveness": [{"skillId": "alice/foo", "url": "https://github.com/suite-a/repo/blob/main/skills/foo/SKILL.md", "status": 404}]},
        {"nameDrift": [{"skillId": "alice/foo", "registrySlug": "foo", "sanitizedName": "bar"}]},
    ],
)
def test_new_actionable_content_is_not_covered_by_closed_payload(change):
    baseline = finding()
    verdict = evidence.classify(finding(**change), "release", [closed_payload(baseline)])

    assert verdict.state == "new"


def test_subset_of_closed_actionable_content_remains_processed():
    recorded = finding(componentRemoves=["old"], nameDrift=[{"skillId": "alice/foo"}])
    current = finding()

    assert evidence.classify(current, "release", [closed_payload(recorded)]).state == "processed"
