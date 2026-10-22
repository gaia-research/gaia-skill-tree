"""Shared fixtures for the upstream watcher tests.

The watcher retries transient GitHub reads with a backoff (C9, H-B). A test that exercises a transient failure
must not wait out the real delays, so every test in this folder runs with the retry sleep replaced by a no-op.
A test that asserts the backoff replaces it again with its own recorder (monkeypatch applies in order).
"""

import pytest


@pytest.fixture(autouse=True)
def _no_retry_sleep(monkeypatch):
    from scripts.upstream_watcher import live

    monkeypatch.setattr(live, "RETRY_SLEEP", lambda seconds: None, raising=False)


@pytest.fixture(autouse=True)
def _hermetic_github(monkeypatch):
    """Keep every test off the real ``gh`` CLI and off the caller's GitHub credentials.

    ``watcher.main`` builds ``LiveGh()`` for its batch pass. Left unpatched, that shells out to ``gh api``:
    with no token gh exits 4 (unknown evidence), with a token it calls live GitHub. Either way the outcome
    depended on the environment, so the default is a fake GitHub surface with no issues and no token in the
    environment. A test that needs a specific GitHub surface still patches ``watcher.LiveGh`` itself, which
    overrides this default because it runs later.
    """
    from scripts.upstream_watcher import watcher

    from upstream_fakes import FakeGh

    monkeypatch.delenv("GH_TOKEN", raising=False)
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    monkeypatch.setattr(watcher, "LiveGh", lambda *args, **kwargs: FakeGh())
