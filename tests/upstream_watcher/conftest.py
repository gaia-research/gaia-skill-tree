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
