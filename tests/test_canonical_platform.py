"""Platform-capability regressions; adapter doubles are NOT native Windows proof."""
import os
from pathlib import Path
import subprocess
import sys

import pytest

from gaia_cli import canonicalTransaction as tx


REPO = Path(__file__).resolve().parents[1]


def test_read_only_native_cli_imports_without_posix_fcntl(tmp_path):
    code = '''
import importlib.abc, sys
class NoFcntl(importlib.abc.MetaPathFinder):
    def find_spec(self, fullname, path=None, target=None):
        if fullname == "fcntl":
            raise ModuleNotFoundError("No module named 'fcntl'", name="fcntl")
sys.meta_path.insert(0, NoFcntl())
from gaia_cli.main import main
sys.argv = ["gaia", "--help"]
main()
'''
    env = dict(os.environ, PYTHONPATH=str(REPO / "src"), PYTHONDONTWRITEBYTECODE="1",
               GAIA_HOME=str(tmp_path / "home"))
    result = subprocess.run([sys.executable, "-c", code], env=env, cwd=tmp_path,
                            text=True, capture_output=True, timeout=20)
    assert result.returncode == 0, result.stderr
    assert "usage:" in result.stdout


class _WindowsLockDouble:
    LK_LOCK, LK_UNLCK = 1, 2

    def __init__(self, *, fail=False):
        self.calls = []
        self.fail = fail

    def locking(self, fd, operation, length):
        assert os.fstat(fd).st_size >= 1
        assert os.lseek(fd, 0, os.SEEK_CUR) == 0
        assert length == 1
        self.calls.append(operation)
        if self.fail:
            raise OSError("fixture lock unavailable")


def test_legacy_windows_lock_backend_keeps_reentrant_cooperative_guard(tmp_path, monkeypatch):
    backend = _WindowsLockDouble()
    monkeypatch.setattr(tx, "fcntl", None)
    monkeypatch.setattr(tx, "msvcrt", backend)
    with tx.canonicalTransactionLock(tmp_path):
        with tx.canonicalTransactionLock(tmp_path):
            pass
    assert backend.calls == [backend.LK_LOCK, backend.LK_UNLCK]


def test_windows_adapter_preserves_ordinary_serializers_and_pending_refusal(tmp_path, monkeypatch):
    import json
    from gaia_cli.commands.dev.helpers import _write_md
    from gaia_cli.treeManager import save_tree

    backend = _WindowsLockDouble()
    monkeypatch.setattr(tx, "fcntl", None)
    monkeypatch.setattr(tx, "msvcrt", backend)
    target = tmp_path / "registry/named/alice/tool.md"
    target.parent.mkdir(parents=True)
    _write_md(target, {"id": "alice/tool"}, "\nfixture body\n")
    save_tree("alice", {"userId": "alice"}, tmp_path)
    assert "alice/tool" in target.read_text()
    assert json.loads((tmp_path / "skill-trees/alice/skill-tree.json").read_bytes())["userId"] == "alice"
    before = target.read_bytes()
    (tmp_path / tx.STATE_DIR / "unknown.pending.json").write_text("unknown pending")
    with pytest.raises(tx.TransactionError, match="pending canonical transaction"):
        _write_md(target, {"id": "changed"}, "changed")
    assert target.read_bytes() == before


def test_failed_windows_lock_never_unlocks_an_unacquired_lock(tmp_path, monkeypatch):
    backend = _WindowsLockDouble(fail=True)
    monkeypatch.setattr(tx, "fcntl", None)
    monkeypatch.setattr(tx, "msvcrt", backend)
    with pytest.raises(tx.TransactionError, match="lock"):
        with tx.canonicalTransactionLock(tmp_path):
            pytest.fail("failed lock yielded permission to write")
    assert backend.calls == [backend.LK_LOCK]


def test_missing_lock_backends_fail_closed_before_metadata_writes(tmp_path, monkeypatch):
    monkeypatch.setattr(tx, "fcntl", None)
    monkeypatch.setattr(tx, "msvcrt", None)
    with pytest.raises(tx.TransactionError, match="lock"):
        with tx.canonicalTransactionLock(tmp_path):
            pytest.fail("unsupported platform yielded permission to write")
    assert not (tmp_path / ".gaia").exists()


@pytest.mark.parametrize("operation", ["apply", "rollback"])
def test_durable_canonical_mutation_is_unavailable_without_posix_capability(tmp_path, monkeypatch, operation):
    target = tmp_path / "registry/named/fixture/tool.md"
    target.parent.mkdir(parents=True)
    target.write_bytes(b"unchanged fixture")
    plan = tx.prepare(tmp_path, "fixture", "platform", [tx.Change("registry/named/fixture/tool.md", b"replacement")])
    monkeypatch.setattr(tx, "fcntl", None)
    monkeypatch.setattr(tx, "msvcrt", _WindowsLockDouble())
    with pytest.raises(tx.TransactionError, match="POSIX"):
        if operation == "apply":
            tx.apply(plan)
        else:
            tx.rollback(tmp_path, tmp_path / tx.STATE_DIR / "unknown.pending.json")
    assert target.read_bytes() == b"unchanged fixture"
    assert not (tmp_path / ".gaia").exists()
