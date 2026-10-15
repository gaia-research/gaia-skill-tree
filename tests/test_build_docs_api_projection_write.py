"""Regression for #2035: ``build_api_projection(check=False)`` must write.

#2034 left the copy/update block after an unconditional ``return True`` in the
check branch, so ``gaia dev docs`` could report API projection drift without
ever updating ``docs/api/v1/``. These tests drive the real function offline
with a stub generator script and a temporary ROOT.
"""

from __future__ import annotations

import importlib.util
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPT = REPO_ROOT / "scripts" / "build_docs.py"

STUB = """
import json, sys
from pathlib import Path
out = Path(sys.argv[sys.argv.index("--out-dir") + 1])
(out / "skills" / "c").mkdir(parents=True, exist_ok=True)
(out / "health.json").write_text(json.dumps({"ok": True, "namedSkillsCount": 2}))
(out / "skills" / "c" / "a.json").write_text(json.dumps({"id": "c/a", "trustMagnitude": 90.0}))
"""


def _load():
    sys.path.insert(0, str(REPO_ROOT / "scripts"))
    sys.path.insert(0, str(REPO_ROOT / "src"))
    spec = importlib.util.spec_from_file_location("build_docs_api_write", SCRIPT)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _setup(tmp_path: Path, monkeypatch):
    bd = _load()
    scripts = tmp_path / "scripts"
    scripts.mkdir()
    (scripts / "buildApiProjection.py").write_text(STUB, encoding="utf-8")
    committed = tmp_path / "docs" / "api" / "v1"
    (committed / "skills" / "c").mkdir(parents=True)
    (committed / "health.json").write_text(json.dumps({"ok": True, "namedSkillsCount": 2}), encoding="utf-8")
    (committed / "skills" / "c" / "a.json").write_text(
        json.dumps({"id": "c/a", "trustMagnitude": 80.0}), encoding="utf-8"
    )
    # Hand-authored file the generator does not emit must survive the round-trip.
    (committed / "openapi.json").write_text('{"openapi": "3.1.0"}', encoding="utf-8")
    monkeypatch.setattr(bd, "ROOT", tmp_path)
    monkeypatch.setattr(bd, "SCRIPTS", scripts)
    return bd, committed


def test_api_projection_write_mode_updates_committed_tree(tmp_path: Path, monkeypatch):
    bd, committed = _setup(tmp_path, monkeypatch)
    changed = bd.build_api_projection(check=False)
    assert changed is True
    data = json.loads((committed / "skills" / "c" / "a.json").read_text(encoding="utf-8"))
    assert data["trustMagnitude"] == 90.0
    assert (committed / "openapi.json").exists()
    # Idempotent: a second write run plans nothing.
    assert bd.build_api_projection(check=False) is False


def test_api_projection_check_mode_does_not_write(tmp_path: Path, monkeypatch):
    bd, committed = _setup(tmp_path, monkeypatch)
    # Ledger routine status unproven -> drift is material and reported.
    monkeypatch.setitem(bd.__dict__, "_TRUST_LEDGER_ROUTINE", False)
    changed = bd.build_api_projection(check=True)
    assert changed is True
    data = json.loads((committed / "skills" / "c" / "a.json").read_text(encoding="utf-8"))
    assert data["trustMagnitude"] == 80.0
