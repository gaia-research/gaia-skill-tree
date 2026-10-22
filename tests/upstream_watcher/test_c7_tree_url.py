"""#2131 round-3 verifier FAIL, D11: a tag is percent-encoded in the git tree URL.

A tag containing '#' (or another URL-unsafe character) used to cut the URL before ?recursive=1. The tree
then came back non-recursive, so nested components looked removed. The tag is now encoded whole.
"""

from __future__ import annotations

import pytest

from scripts.upstream_watcher import liveness
from scripts.upstream_watcher.liveness import fetch_component_diff

RESOLVED = {"tree": [{"path": "skills/caveman/SKILL.md", "type": "blob"}], "truncated": False, "sha": "a" * 40}


def captured_url(monkeypatch, tag):
    seen = []

    def fake(url, **kwargs):
        seen.append(url)
        return RESOLVED

    monkeypatch.setattr(liveness, "fetch_json", fake)
    fetch_component_diff("mattpocock", "skills", tag, "skills", [])
    return seen[0]


@pytest.mark.parametrize("tag, encoded", [
    ("v1.1.0", "v1.1.0"),
    ("v1#2", "v1%232"),
    ("release/1.0", "release%2F1.0"),
    ("v1?x=y", "v1%3Fx%3Dy"),
    ("v 1", "v%201"),
])
def test_the_tag_is_percent_encoded_and_recursive_survives(monkeypatch, tag, encoded):
    url = captured_url(monkeypatch, tag)
    assert url == f"https://api.github.com/repos/mattpocock/skills/git/trees/{encoded}?recursive=1"
    assert url.count("#") == 0 and url.endswith("?recursive=1")


def test_a_hash_in_the_tag_does_not_drop_nested_components(monkeypatch):
    """With the tag unencoded the URL lost recursive=1 and a nested component came back as a removal."""
    nested = {
        "tree": [
            {"path": "skills/engineering", "type": "tree"},
            {"path": "skills/engineering/caveman", "type": "tree"},
            {"path": "skills/engineering/caveman/SKILL.md", "type": "blob"},
        ],
        "truncated": False,
        "sha": "b" * 40,
    }
    monkeypatch.setattr(liveness, "fetch_json", lambda url, **kwargs: nested)
    adds, removes = fetch_component_diff("mattpocock", "skills", "v1#2", "skills", ["mattpocock/caveman"])
    assert (adds, removes) == ([], [])
