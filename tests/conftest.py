import os
import pytest

# Marker assignment criteria:
#   integration: test spawns a subprocess, hits the network, or exercises >1 CLI verb end-to-end
#   slow: any single test consistently >2s wall-clock
#   (unmarked): pure-Python logic against in-memory objects or tmp_path


@pytest.fixture(autouse=True)
def _block_process_replacement(monkeypatch):
    """Block os.execvp and os.execv to prevent tests from replacing the pytest process."""
    def blocked_execvp(*args, **kwargs):
        raise RuntimeError("os.exec* blocked in tests — monkeypatch explicitly to assert exec behavior")

    def blocked_execv(*args, **kwargs):
        raise RuntimeError("os.exec* blocked in tests — monkeypatch explicitly to assert exec behavior")

    monkeypatch.setattr(os, "execvp", blocked_execvp)
    monkeypatch.setattr(os, "execv", blocked_execv)


@pytest.fixture
def isolated_gaia_home(tmp_path, monkeypatch):
    monkeypatch.setenv("GAIA_HOME", str(tmp_path / "gaia-home"))


def pytest_collection_modifyitems(config, items):
    for item in items:
        if "integration" in item.keywords and "isolated_gaia_home" not in item.fixturenames:
            item.fixturenames.append("isolated_gaia_home")
