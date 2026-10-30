"""Regression: ``gaia dev docs`` must leave docs/graph/installability/index.json current in ONE run.

The installability projection reads the Class S mirror
``docs/graph/named/index.json`` (``installability._load_current_index``), which the
``docs-named-index`` step rewrites from ``registry/named-skills.json``. The
projection step used to run BEFORE that mirror was refreshed, so after a registry
change a single ``gaia dev docs`` projected the previous registry and the artifact
only converged on a second run (it looked as if only a direct ``build_docs.py``
invocation rewrote it). ``gaia dev docs`` is a thin wrapper over the same script.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "build_docs.py"


def _load():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    spec = importlib.util.spec_from_file_location("build_docs_stage_order", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _recordedStages(monkeypatch, argv):
    bd = _load()
    calls: list[str] = []
    for name in [n for n in dir(bd) if n.startswith("build_") and callable(getattr(bd, n))]:
        monkeypatch.setattr(bd, name, lambda check, _name=name: calls.append(_name) or False)
    monkeypatch.setattr(bd, "ROOT", REPO_ROOT)
    bd.main(argv)
    return calls


@pytest.mark.parametrize("argv", [[], ["--check"]])
def test_installability_runs_after_docs_named_index(monkeypatch, argv):
    calls = _recordedStages(monkeypatch, argv)
    assert "build_installability_projection" in calls
    assert calls.index("build_docs_named_index") < calls.index("build_installability_projection")


def test_installability_reads_the_docs_named_index_mirror():
    # The ordering above is only required while this dependency holds; if the
    # projection stops reading the mirror this test should be revisited.
    source = (REPO_ROOT / "scripts" / "installability.py").read_text(encoding="utf-8")
    assert '"docs" / "graph" / "named" / "index.json"' in source


def test_dev_docs_runs_the_same_script_as_build_docs(monkeypatch):
    from gaia_cli import impl

    seen: list[list[str]] = []
    monkeypatch.setattr(impl.subprocess, "call", lambda cmd: seen.append(cmd) or 0)
    with pytest.raises(SystemExit) as exit_info:
        impl.docs_command(SimpleNamespace(registry=str(REPO_ROOT), check=False))
    assert exit_info.value.code == 0
    assert Path(seen[0][1]).resolve() == SCRIPT.resolve()
    assert "--check" not in seen[0]
