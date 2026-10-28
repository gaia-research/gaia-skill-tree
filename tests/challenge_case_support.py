"""Visibly SYNTHETIC case bundles and a SYNTHETIC receipt resolver for challenge tests.

Everything here lives under ``tests/`` and writes only into pytest tmp dirs. Nothing in
``docs/`` may ever carry these ids (``test_challenge_projection.py`` guards that).
The synthetic resolver stands in for a verified issuer receipt; the production resolver
never accepts it.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

from gaia_cli import frontier
from gaia_cli.challengeDomain import VerificationReceipt
from gaia_cli.frontier import build_experiment_receipt, receipt_digest
from test_frontier_meta_verification import RECEIPT_RUN, VERIFIER_RUN, sha, verifierNative
from test_frontier_protocol import committedBundle

REPO = Path(__file__).resolve().parent.parent
LEADFILE = REPO / "examples/frontier/git-log-L-graft.challenger-lead-v1.json"
CASE = "synthetic-case"
SYNTHETICTOKENS = ("synthetic-case", "synthetic-verification-0001", "SYNTHETIC separate run")


def makeCase(tmp_path, caseId=CASE, *, positive=True):
    """Write a complete, internally consistent SYNTHETIC bundle; return ``(root, caseDir)``."""
    root, request, art = committedBundle(tmp_path, caseId)
    art = f"evidence/frontier-challenges/{caseId}/artifacts"
    receipt = build_experiment_receipt(
        root=root, request=request, protocol=request["protocol"]["path"],
        execution_path=f"{art}/native.json", target_path=f"{art}/target.txt", result="supported",
        artifact_root=art, run_id=RECEIPT_RUN, recorded_at="2026-10-28T01:02:03Z")
    reexec = []
    if positive:
        raw = b"SYNTHETIC verifier re-execution of target\n"
        (root / art / "verifier-target.txt").write_bytes(raw)
        reexec = [verifierNative(root, request, receipt, art),
                  {"label": "target", "contentDigest": sha(raw), "path": f"{art}/verifier-target.txt"}]
    record = {
        "schemaVersion": "frontier-meta-verification-v1", "verificationId": "synthetic-verification-0001",
        "campaignId": receipt["campaignId"], "requestId": receipt["requestId"],
        "receiptDigest": receipt_digest(receipt), "receiptRunId": receipt["experimentRunId"],
        "verifierRunId": VERIFIER_RUN, "outcome": "substantiated" if positive else "inconclusive",
        "recommend": ({"action": "request-admission-review", "rationale": "Synthetic: re-execution matched the receipt."}
                      if positive else {"action": "hold", "rationale": "Synthetic: evidence is not conclusive."}),
        "counterevidence": {"searched": "Synthetic: searched the protocol's own limitations and vendor notes.", "items": []},
        "reexecution": {"performed": positive, "artifacts": reexec, "notes": "Synthetic re-run in a separate session."},
        "independence": "declared-unauthenticated",
        "declaredSession": {"harness": "synthetic", "model": "synthetic", "note": "declared, not authenticated"},
        "limitations": ["Synthetic unit fixture; no real verification occurred."],
        "recordedAtUTC": "2026-10-28T02:00:00Z",
    }
    assert frontier.validate_meta_verification(record, receipt, request, repo_root=root, artifact_root=art) == []
    directory = root / "evidence/frontier-challenges" / caseId
    for name, value in (("lead.json", json.loads(LEADFILE.read_text())), ("request.json", request),
                        ("receipt.json", receipt), ("meta-verification.json", record)):
        (directory / name).write_text(json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return root, directory


BUILDKWARGS = dict(verifier="founder-login", builder="builder-bot", noticeRef="https://example.org/notices/synthetic-1",
                   verifiedAt="2026-10-28T03:00:00Z")


class SyntheticBound:
    def __init__(self, receipts, challengeId):
        self.receipts, self.challenge_id = receipts, challengeId

    def resolve(self, receiptId):
        return self.receipts[receiptId]  # KeyError for any receipt this port does not hold


class SyntheticVerifiedResolver:
    """SYNTHETIC stand-in for verified issuer receipts of one or more cases. Never the production resolver."""

    SYNTHETIC_TEST_ONLY = True

    def __init__(self, *directories):
        self.receipts = {}
        for directory in directories:
            data = json.loads((Path(directory) / "admission-request.json").read_text())
            self.receipts[data["receipt"]["receipt_id"]] = VerificationReceipt(**data["receipt"])

    @property
    def receipt(self):  # single-case convenience
        return next(iter(self.receipts.values()))

    @receipt.setter
    def receipt(self, value):
        self.receipts = {value.receipt_id: value}

    def for_challenge(self, challengeId):
        return SyntheticBound(self.receipts, challengeId)


def tamper(directory, name="meta-verification.json"):
    path = Path(directory) / name
    data = json.loads(path.read_text())
    data = copy.deepcopy(data)
    data["limitations"] = data["limitations"] + ["tampered after the fact"]
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def addCase(root, scratch, caseId, **kwargs):
    """Add a second built SYNTHETIC case to ``root`` (built from an identical lead, so ids can collide)."""
    import shutil
    from gaia_cli import challengeAdmission as admission
    _, source = makeCase(scratch, caseId)
    shutil.copytree(source, Path(root) / admission.EVIDENCE / caseId)
    return admission.buildRequest(root, caseId, **{**BUILDKWARGS, **kwargs})


def stubReceiptDir(directory):
    """Dummy receipt/ files so a case LOOKS like it claims an issuer receipt (never verifies)."""
    target = Path(directory) / "receipt"
    target.mkdir()
    for name in ("artifact.zip", "issuer-approval.json", "attestation.jsonl"):
        (target / name).write_bytes(b"{}")
    return target


def corrupt(directory, name="meta-verification.json"):
    """An edit that no longer validates (an outcome that cannot carry that recommendation)."""
    path = Path(directory) / name
    data = json.loads(path.read_text())
    data["outcome"] = "contradicted"
    path.write_text(json.dumps(data, indent=2, sort_keys=True) + "\n", encoding="utf-8")
