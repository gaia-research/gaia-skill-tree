import os
import pytest


@pytest.fixture(autouse=True)
def _block_process_replacement(monkeypatch):
    """Block os.execvp and os.execv to prevent tests from replacing the pytest process."""
    def blocked_execvp(*args, **kwargs):
        raise RuntimeError("os.exec* blocked in tests — monkeypatch explicitly to assert exec behavior")

    def blocked_execv(*args, **kwargs):
        raise RuntimeError("os.exec* blocked in tests — monkeypatch explicitly to assert exec behavior")

    monkeypatch.setattr(os, "execvp", blocked_execvp)
    monkeypatch.setattr(os, "execv", blocked_execv)


@pytest.fixture(autouse=True)
def isolated_gaia_home(tmp_path, monkeypatch):
    monkeypatch.setenv("GAIA_HOME", str(tmp_path / "gaia-home"))
