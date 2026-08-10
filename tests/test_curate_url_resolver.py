"""Unit tests for curate GitHub URL resolver scaffolding."""

from __future__ import annotations

import pytest

from gaia_cli.curation import url_resolver


def test_url_resolver_functions_are_callable():
    assert callable(url_resolver.normalize_github_url)
    assert callable(url_resolver.find_skill_files)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/not-github",
        "https://gitlab.com/example/repo",
        "file:///tmp/SKILL.md",
    ],
)
def test_normalize_github_url_non_github_raises(url):
    with pytest.raises(NotImplementedError):
        url_resolver.normalize_github_url(url)


def test_find_skill_files_stub_raises_not_implemented():
    with pytest.raises(NotImplementedError):
        url_resolver.find_skill_files("example/repo")
