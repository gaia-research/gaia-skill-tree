import json
import tempfile
import unittest
from dataclasses import replace
from pathlib import Path

from gaia_cli.canonicalTransaction import (
    ApprovalRejected, ApprovalUnavailable, Change, TransactionError,
    apply, assertNoPendingTransaction, canonicalTransactionLock, prepare, rollback,
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

    def test_tampered_journal_fails_closed(self):
        plan = self.plan()
        journal = Path(apply(plan, TestIssuer()))
        doc = json.loads(journal.read_text())
        doc["targets"][0]["after"] = "dGFtcGVyZWQ="
        journal.write_text(json.dumps(doc))
        with self.assertRaisesRegex(TransactionError, "integrity"):
            rollback(self.root, journal, TestIssuer("rollback"))


if __name__ == "__main__":
    unittest.main()
