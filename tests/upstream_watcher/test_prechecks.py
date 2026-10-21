"""Precheck matrix for upstream batch candidates (#2131): present / alias-suspect / tracked / rejected."""

import pytest

from scripts.upstream_watcher import prechecks as pc

BLOB = "https://github.com/garrytan/gbrain/blob/main/skills/foo/SKILL.md"


def _row(suggested="garrytan/foo", slug="foo", url=BLOB):
    return {"id": f"garrytan/gbrain:{slug}", "slug": slug, "suggestedId": suggested, "evidenceUrl": url}


def _index(entries):
    by_id, by_slug = {}, {}
    for rid, links in entries:
        by_id[rid] = {"links": pc.normalize_blob(links, ignore_ref=True), "status": "named"}
        by_slug.setdefault(pc.slug_key(rid.split("/")[-1]), []).append(rid)
    return {"byId": by_id, "bySlug": by_slug}


def test_normalize_blob_rewrites_tree_and_strips_git_suffix():
    assert pc.normalize_blob("https://github.com/Garry/GBrain.git/tree/main/skills/foo/") == (
        "github.com/garry/gbrain/blob/main/skills/foo"
    )
    assert pc.normalize_blob(BLOB) == "github.com/garrytan/gbrain/blob/main/skills/foo/SKILL.md"
    assert pc.normalize_blob("") == ""
    assert pc.normalize_blob("not a url") == ""


def test_slug_key_ignores_case_hyphens_and_underscores():
    assert pc.slug_key("Test-Driven_Development") == pc.slug_key("testdrivendevelopment")


def test_registry_present_requires_id_and_matching_blob_link():
    idx = _index([("garrytan/foo", BLOB)])
    assert pc.registry_state(_row(), idx) == "present"


def test_registry_present_ignores_ref_pinning():
    pinned = "https://github.com/garrytan/gbrain/blob/0.6.10/skills/foo/SKILL.md"
    assert pc.registry_state(_row(), _index([("garrytan/foo", pinned)])) == "present"


def test_registry_same_id_different_link_is_alias_suspect_not_present():
    idx = _index([("garrytan/foo", "https://github.com/other/repo/blob/main/x/SKILL.md")])
    assert pc.registry_state(_row(), idx) == "alias-suspect"


def test_registry_same_slug_other_handle_is_alias_suspect():
    idx = _index([("addy-osmani/foo", BLOB)])
    assert pc.registry_state(_row(suggested="garrytan/foo"), idx) == "alias-suspect"


def test_registry_normalized_slug_collision_is_alias_suspect():
    idx = _index([("garrytan/test_driven", BLOB)])
    assert pc.registry_state(_row(suggested="garrytan/test-driven", slug="test-driven"), idx) == "alias-suspect"


def test_registry_absent_when_nothing_matches():
    idx = _index([("garrytan/unrelated", BLOB)])
    assert pc.registry_state(_row(), idx) == "absent"


def test_index_children_splits_open_and_rejected():
    body = "**Suggested ID:** `garrytan/foo`\n"
    issues = [
        {"number": 10, "state": "open", "labels": [{"name": "upstream:child"}], "body": body},
        {"number": 11, "state": "closed", "labels": [{"name": "upstream:child"}, {"name": "upstream:rejected"}],
         "body": "**Suggested ID:** `garrytan/bar`\n"},
        {"number": 12, "state": "closed", "labels": [{"name": "upstream:child"}], "body": "**Suggested ID:** `x/y`\n"},
        {"number": 13, "state": "open", "labels": [{"name": "upstream:child"}], "body": body, "pull_request": {}},
    ]
    open_children, rejected = pc.index_children(issues)
    assert open_children == {"garrytan/foo": 10}
    assert rejected == {"garrytan/bar": 11}


@pytest.mark.parametrize(
    "registry_entries, open_children, rejected, expected_status",
    [
        ([("garrytan/foo", BLOB)], {}, {}, "present"),
        ([], {"garrytan/foo": 42}, {}, "tracked"),
        ([], {}, {"garrytan/foo": 7}, "rejected"),
        ([("garrytan/foo", BLOB)], {"garrytan/foo": 42}, {"garrytan/foo": 7}, "rejected"),
        ([("addy-osmani/foo", BLOB)], {}, {}, "new"),
        ([], {}, {}, "new"),
    ],
)
def test_precheck_matrix(registry_entries, open_children, rejected, expected_status):
    result = pc.precheck_row(_row(), _index(registry_entries), open_children, rejected)
    assert result["status"] == expected_status


def test_precheck_reports_tracked_child_number_and_suppression_set():
    result = pc.precheck_row(_row(), _index([]), {"garrytan/foo": 42}, {})
    assert result["precheck"] == {"registry": "absent", "tracked": "child:#42", "priorDisposition": "none"}
    assert result["status"] in pc.SUPPRESSED_STATUSES


def test_load_registry_index_fails_closed_on_missing_directory(tmp_path):
    with pytest.raises(pc.RegistryUnreadable):
        pc.load_registry_index(root=tmp_path / "does-not-exist")


def test_load_registry_index_fails_closed_on_empty_directory(tmp_path):
    with pytest.raises(pc.RegistryUnreadable):
        pc.load_registry_index(root=tmp_path)


def test_load_registry_index_reads_frontmatter(tmp_path):
    (tmp_path / "garrytan").mkdir()
    (tmp_path / "garrytan" / "foo.md").write_text(
        "---\nid: garrytan/foo\nstatus: named\nlinks:\n  github: " + BLOB + "\n---\nbody\n",
        encoding="utf-8",
    )
    idx = pc.load_registry_index(root=tmp_path)
    assert pc.registry_state(_row(), idx) == "present"
