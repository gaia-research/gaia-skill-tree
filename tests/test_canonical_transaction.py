import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from gaia_cli.canonicalTransaction import (
    ApprovalRejected, ApprovalUnavailable, Change, TransactionError,
    _hash, apply, assertNoPendingTransaction, canonicalTransactionLock, prepare, rollback,
)


class TestIssuer:
    __test__ = False

    def __init__(self, operation="apply"):
        self.operation = operation

    def verify(self, request):
        return request.operation == self.operation and bool(request.context_digest)


class CanonicalTransactionTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "registry/nodes").mkdir(parents=True)
        (self.root / "registry/named").mkdir(parents=True)
        (self.root / "skill-trees/alice").mkdir(parents=True)
        (self.root / "registry/nodes/a.json").write_bytes(b"old-a")
        (self.root / "registry/named/b.md").write_bytes(b"old-b")

    def tearDown(self):
        self.temp.cleanup()

    def plan(self):
        return prepare(self.root, "approved fixture update", "fixture-plan-1", [
            Change("registry/nodes/a.json", b"new-a"),
            Change("registry/named/b.md", b"new-b"),
        ])

    def test_unavailable_or_rejected_approval_performs_no_writes(self):
        plan = self.plan()
        before = [(self.root / p).read_bytes() for p in ("registry/nodes/a.json", "registry/named/b.md")]
        with self.assertRaises(ApprovalUnavailable):
            apply(plan)
        with self.assertRaises(ApprovalRejected):
            apply(plan, TestIssuer("rollback"))
        self.assertEqual(before, [(self.root / p).read_bytes() for p in ("registry/nodes/a.json", "registry/named/b.md")])
        self.assertFalse((self.root / ".gaia/canonical-transactions").exists())

    def test_plan_is_deterministic_and_cas_checks_all_before_writes(self):
        plan = self.plan()
        self.assertEqual(plan.digest, self.plan().digest)
        (self.root / "registry/named/b.md").write_bytes(b"outside")
        with self.assertRaisesRegex(TransactionError, "CAS conflict"):
            apply(plan, TestIssuer())
        self.assertEqual(b"old-a", (self.root / "registry/nodes/a.json").read_bytes())
        self.assertEqual(b"outside", (self.root / "registry/named/b.md").read_bytes())

    def test_forged_plan_digest_and_replay_are_refused(self):
        plan = self.plan()
        forged = replace(plan, identity="different-plan")
        with self.assertRaisesRegex(TransactionError, "digest is invalid"):
            apply(forged, TestIssuer())
        journal = apply(plan, TestIssuer())
        with self.assertRaisesRegex(TransactionError, "CAS conflict"):
            apply(plan, TestIssuer())
        self.assertEqual(b"new-a", (self.root / "registry/nodes/a.json").read_bytes())
        rollback(self.root, journal, TestIssuer("rollback"))

    def test_containment_blocks_paths_traversal_symlinks_and_nonfiles(self):
        for value in ("registry/nodes/../../outside", "registry/nodes/./a.json", "registry//nodes/a.json", "registry/schema/x.json", "config.json"):
            with self.subTest(value=value), self.assertRaises(TransactionError):
                prepare(self.root, "p", "i", [Change(value, b"x")])
        (self.root / "registry/nodes/link.json").symlink_to(self.root / "registry/nodes/a.json")
        with self.assertRaises(TransactionError):
            prepare(self.root, "p", "i", [Change("registry/nodes/link.json", b"x")])
        (self.root / "registry/nodes/dirlink").symlink_to(self.root / "registry/nodes", target_is_directory=True)
        with self.assertRaises(TransactionError):
            prepare(self.root, "p", "i", [Change("registry/nodes/dirlink/new.json", b"x")])

    def test_apply_and_compare_safe_rollback(self):
        plan = self.plan()
        journal = apply(plan, TestIssuer())
        self.assertEqual(b"new-a", (self.root / "registry/nodes/a.json").read_bytes())
        self.assertEqual(b"new-b", (self.root / "registry/named/b.md").read_bytes())
        rollback(self.root, journal, TestIssuer("rollback"))
        self.assertEqual(b"old-a", (self.root / "registry/nodes/a.json").read_bytes())
        self.assertEqual(b"old-b", (self.root / "registry/named/b.md").read_bytes())
        assertNoPendingTransaction(self.root)

    def test_partial_replace_is_guarded_then_rollback_restores(self):
        plan = self.plan()
        with self.assertRaisesRegex(OSError, "injected"):
            apply(plan, TestIssuer(), fail_after=1)
        with self.assertRaisesRegex(TransactionError, "pending"):
            with canonicalTransactionLock(self.root):
                pass
        journal = next((self.root / ".gaia/canonical-transactions").glob("*.pending.json"))
        rollback(self.root, journal, TestIssuer("rollback"))
        self.assertEqual(b"old-a", (self.root / "registry/nodes/a.json").read_bytes())
        self.assertEqual(b"old-b", (self.root / "registry/named/b.md").read_bytes())
        assertNoPendingTransaction(self.root)

    def test_rollback_refuses_outside_edit_without_clobber(self):
        plan = self.plan()
        journal = apply(plan, TestIssuer())
        (self.root / "registry/named/b.md").write_bytes(b"outside")
        with self.assertRaisesRegex(TransactionError, "outside edit"):
            rollback(self.root, journal, TestIssuer("rollback"))
        self.assertEqual(b"new-a", (self.root / "registry/nodes/a.json").read_bytes())
        self.assertEqual(b"outside", (self.root / "registry/named/b.md").read_bytes())

    def test_rollback_final_receipt_rename_failure_is_recoverable(self):
        from unittest.mock import patch
        from gaia_cli import canonicalTransaction as tx
        journal = apply(self.plan(), TestIssuer())
        original = tx.os.replace

        def failFinalRename(source, target):
            if str(target).endswith(".rolled-back.json"):
                raise OSError("fixture final rename interruption")
            return original(source, target)

        with patch.object(tx.os, "replace", failFinalRename):
            with self.assertRaisesRegex(OSError, "final rename interruption"):
                rollback(self.root, journal, TestIssuer("rollback"))
        pending = next((self.root / tx.STATE_DIR).glob("*.pending.json"))
        self.assertEqual(json.loads(pending.read_bytes())["status"], "rolled-back")
        with self.assertRaisesRegex(TransactionError, "pending"):
            assertNoPendingTransaction(self.root)
        rollback(self.root, pending, TestIssuer("rollback"))
        assertNoPendingTransaction(self.root)
        self.assertEqual(b"old-a", (self.root / "registry/nodes/a.json").read_bytes())
        self.assertEqual(b"old-b", (self.root / "registry/named/b.md").read_bytes())

    def test_tampered_journal_fails_closed(self):
        plan = self.plan()
        journal = Path(apply(plan, TestIssuer()))
        doc = json.loads(journal.read_text())
        doc["targets"][0]["after"] = "dGFtcGVyZWQ="
        journal.write_text(json.dumps(doc))
        with self.assertRaisesRegex(TransactionError, "integrity"):
            rollback(self.root, journal, TestIssuer("rollback"))

    def test_absence_vs_content_domain_separation_and_creation_rollback(self):
        # 1. Direct domain separation check: absence vs content bytes b"<absent>"
        self.assertEqual("<absent>", _hash(None))
        self.assertNotEqual(_hash(None), _hash(b"<absent>"))
        self.assertNotEqual(_hash(None), _hash(b""))

        # 2. Prepare creation while target is genuinely absent
        target_path = "registry/nodes/new.json"
        disk_target = self.root / target_path
        self.assertFalse(disk_target.exists())
        create_plan = prepare(self.root, "create new node", "create-plan-1", [
            Change(target_path, b"created-content"),
        ])
        self.assertIsNone(create_plan.targets[0].before)
        self.assertEqual(b"created-content", create_plan.targets[0].after)

        # 3. Introduce literal b"<absent>" content before apply
        disk_target.write_bytes(b"<absent>")

        # 4. Apply must detect CAS conflict and preserve the file
        with self.assertRaisesRegex(TransactionError, "CAS conflict"):
            apply(create_plan, TestIssuer())
        self.assertEqual(b"<absent>", disk_target.read_bytes())

        # 5. Restore genuine absence and verify successful apply (creation)
        disk_target.unlink()
        self.assertFalse(disk_target.exists())
        journal = apply(create_plan, TestIssuer())
        self.assertEqual(b"created-content", disk_target.read_bytes())

        # 6. Outside edit introducing b"<absent>" refuses rollback and preserves file
        disk_target.write_bytes(b"<absent>")
        with self.assertRaisesRegex(TransactionError, "outside edit"):
            rollback(self.root, journal, TestIssuer("rollback"))
        self.assertEqual(b"<absent>", disk_target.read_bytes())

        # 7. Restore applied content and verify compare-safe rollback deletes the created file
        disk_target.write_bytes(b"created-content")
        rollback(self.root, journal, TestIssuer("rollback"))
        self.assertFalse(disk_target.exists())
        assertNoPendingTransaction(self.root)

        # 8. Deletion detection: if a plan is prepared for an existing file with b"<absent>",
        # deleting the file must trigger a CAS conflict on apply rather than matching absence.
        disk_target.write_bytes(b"<absent>")
        update_plan = prepare(self.root, "update absent-content file", "update-plan-1", [
            Change(target_path, b"updated-content"),
        ])
        self.assertEqual(b"<absent>", update_plan.targets[0].before)
        disk_target.unlink()
        self.assertFalse(disk_target.exists())
        with self.assertRaisesRegex(TransactionError, "CAS conflict"):
            apply(update_plan, TestIssuer())
        self.assertFalse(disk_target.exists())


if __name__ == "__main__":
    unittest.main()
