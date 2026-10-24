"""#2131 round-2 regression tests for M3: a component tree that is not a usable tree object is unknown
evidence, never an empty or partial diff.

An empty tree list is acceptable only when the response is a real tree object for the tag (it carries
the tree's ``sha``). ``{}``, a response without a ``tree`` key, a non-list ``tree`` and non-object entries
are all unknown evidence.
"""

from __future__ import annotations

import pytest

from scripts.upstream_watcher import liveness
from scripts.upstream_watcher.live import UnknownEvidenceError
from scripts.upstream_watcher.liveness import fetch_component_diff

RESOLVED_SHA = "9f1c2d3e4f5a6b7c8d9e0f1a2b3c4d5e6f7a8b9c"


def diff_of(monkeypatch, response):
    monkeypatch.setattr(liveness, "fetch_json", lambda endpoint, **kwargs: response)
    return fetch_component_diff("mattpocock", "skills", "v1.1.0", "skills", ["mattpocock/caveman"])


@pytest.mark.parametrize(
    "response",
    [
        {},                                             # an empty object is not a tree
        {"truncated": False},                           # no tree key at all
        {"tree": "skills", "truncated": False, "sha": RESOLVED_SHA},   # tree is not a list
        {"tree": None, "truncated": False, "sha": RESOLVED_SHA},
        {"tree": [], "truncated": False},               # an empty list without a resolved tree sha
        {"tree": [], "truncated": False, "sha": ""},
        {"tree": ["skills/caveman/SKILL.md"], "truncated": False, "sha": RESOLVED_SHA},  # entries not objects
        [],                                             # a list is not the tree object
    ],
)
def test_an_unusable_tree_response_is_unknown_evidence_never_an_empty_diff(monkeypatch, response):
    with pytest.raises(UnknownEvidenceError):
        diff_of(monkeypatch, response)


def test_an_empty_tree_for_a_resolved_tag_is_version_only_not_unknown(monkeypatch):
    assert diff_of(monkeypatch, {"tree": [], "truncated": False, "sha": RESOLVED_SHA}) == ([], [])


def test_a_resolved_tree_with_components_still_diffs(monkeypatch):
    response = {
        "tree": [
            {"path": "skills", "type": "tree"},
            {"path": "skills/caveman", "type": "tree"},
            {"path": "skills/caveman/SKILL.md", "type": "blob"},
            {"path": "skills/new-one", "type": "tree"},
            {"path": "skills/new-one/SKILL.md", "type": "blob"},
        ],
        "truncated": False,
        "sha": RESOLVED_SHA,
    }
    assert diff_of(monkeypatch, response) == (["new-one"], [])
