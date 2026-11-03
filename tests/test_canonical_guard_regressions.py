"""Disposable regressions for the P3 cooperative guard and readable journals."""
from pathlib import Path

import pytest

from gaia_cli import canonicalTransaction as tx
from gaia_cli.commands.dev.helpers import _write_md
from gaia_cli.treeManager import save_tree


@pytest.mark.parametrize("owner", ["registry", "skill-trees"])
@pytest.mark.parametrize("area", ["named", "tree"])
def test_reserved_looking_owner_cannot_select_a_different_transaction_root(tmp_path, owner, area):
    root = tmp_path / "repo"
    if area == "named":
        target = root / "registry" / "named" / owner / "tool.md"
        writer = lambda: _write_md(target, {"id": f"{owner}/tool"}, "replacement")
    else:
        target = root / "skill-trees" / owner / "skill-tree.json"
        writer = lambda: save_tree(owner, {"userId": owner}, root)
    target.parent.mkdir(parents=True)
    original = b"unchanged disposable fixture\n"
    target.write_bytes(original)
    state = root / tx.STATE_DIR
    state.mkdir(parents=True)
    pending = state / "unknown.pending.json"
    pending.write_bytes(b"unknown pending records must block, not disappear")

    with pytest.raises(tx.TransactionError, match="pending canonical transaction"):
        writer()

    assert target.read_bytes() == original
    assert pending.read_bytes() == b"unknown pending records must block, not disappear"
    assert not (root / "registry/named/.gaia").exists()
    assert not (root / "skill-trees/.gaia").exists()


class _DisposableFixtureApproval:
    """Test-only trusted-port replacement, never a production issuer."""

    def verify(self, request):
        return True


def test_writer_refuses_a_journal_its_reader_cannot_recover_before_replacing_targets(tmp_path):
    target = tmp_path / "registry/named/fixture/tool.md"
    target.parent.mkdir(parents=True)
    original = b"original disposable fixture\n"
    target.write_bytes(original)
    plan = tx.prepare(tmp_path, "fixture", "x" * (tx.MAX_PAYLOAD_BYTES * 2),
                      [tx.Change("registry/named/fixture/tool.md", b"replacement\n")])

    with pytest.raises(tx.TransactionError, match="journal|bound"):
        tx.apply(plan, _DisposableFixtureApproval())

    assert target.read_bytes() == original
    assert not list((tmp_path / tx.STATE_DIR).glob("*.json"))


def test_full_supported_payload_remains_readable_and_reversible(tmp_path):
    target = tmp_path / "registry/named/fixture/tool.md"
    target.parent.mkdir(parents=True)
    original = b"a" * (tx.MAX_PAYLOAD_BYTES // 2)
    target.write_bytes(original)
    after = b"b" * (tx.MAX_PAYLOAD_BYTES // 2)
    plan = tx.prepare(tmp_path, "fixture", "full-supported-payload",
                      [tx.Change("registry/named/fixture/tool.md", after)])
    issuer = _DisposableFixtureApproval()

    journal = Path(tx.apply(plan, issuer))
    assert journal.stat().st_size <= tx.MAX_JOURNAL_BYTES
    _, recovered = tx._read_journal(journal, tmp_path.resolve())
    assert recovered == plan
    tx.rollback(tmp_path, journal, issuer)
    assert target.read_bytes() == original
