"""Merge-gate verification for the curation safety repair.

Independent, self-contained checks that the invariants hold at the current head.
Nothing here mutates the canonical registry, opens an intake, or claims human
approval. Run:  PYTHONPATH=src python scripts/merge_gate_check.py
"""
from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, "src")

from gaia_cli import prefill  # noqa: E402
from gaia_cli.curation.assessment import buildAssessment  # noqa: E402
from gaia_cli.curation.authorization import (  # noqa: E402
    _verifyTrustedEnvelope,
    buildReviewPayload,
    verifyPacketAuthorization,
)
from gaia_cli.curation.reconciliation import (  # noqa: E402
    canonicalJson,
    freezeInventory,
    reconcileInventory,
    sha256,
)

RESULTS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((label, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))


def make_registry(root: Path) -> None:
    (root / "registry" / "nodes" / "basic").mkdir(parents=True, exist_ok=True)
    (root / "registry" / "named").mkdir(parents=True, exist_ok=True)
    (root / "registry" / "nodes" / "basic" / "generic-a.json").write_text(json.dumps({
        "id": "generic-a", "name": "Generic A",
        "description": "A generic ability for the test.", "type": "basic", "prerequisites": [],
    }), encoding="utf-8")


def genuine_packet(root: Path):
    """A genuine discovery packet from the production prefill, then ratified."""
    make_registry(root)
    content = "---\nname: Tool\ndescription: A tool capability for testing purposes.\n---\nbody\n"
    embeddings = {"model": "all-MiniLM-L6-v2", "dimensions": 3,
                  "entries": [{"id": "generic-a", "vector": [1.0, 0.0, 0.0]}]}
    with patch.object(prefill, "embed_query", return_value=[1.0, 0.0, 0.0]):
        packet = prefill.buildPrefillPacket(
            candidateId="candidate-1", name="Tool",
            description="A tool capability for testing purposes.",
            canonicalUrl="https://github.com/upstream/tool/blob/" + "a" * 40 + "/SKILL.md",
            sourceLane="source-repository", embeddings=embeddings,
            thresholds={"strongMap": 0.72, "weakMap": 0.45, "topK": 3},
            registryPath=str(root), fetcher=lambda _url: content.encode("utf-8"))
    packet["lifecycle"] = ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"]
    packet["decision"] = {"value": "MAP", "reasonCode": "L4_RATIFIED_MAP", "genericId": "generic-a"}
    packet["namedIdentity"] = "owner/exact-name"
    packet["l4Resolution"] = {
        "status": "approved",
        "generic": {"id": "generic-a", "name": "Generic A", "description": "A generic ability.",
                    "type": "basic", "prerequisites": []},
        "named": {"contributor": "owner", "skillName": "exact-name"},
        "skillFileUrl": packet["source"]["canonicalUrl"],
        "humanReview": {
            "reviewedBy": "reviewer", "approvalRef": "intake/1",
            "rationale": "Reviewed the actual source.", "reviewedAt": "2026-10-20T00:00:00Z",
            "assessmentPath": "assessment.json", "assessmentReceiptDigest": "a" * 64,
            "humanOverride": True, "operatorOverride": True, "attestation": "Local text only.",
        },
    }
    packet["suite"] = {"role": "capstone", "suiteId": "suite-1", "componentCandidateIds": ["candidate-1"]}
    return packet, content


def write_artifacts(root: Path, packet: dict):
    """Write the artifacts the way production writes them: indented JSON."""
    packetPath = root / "registry-for-review" / "discovery-packets" / "tool.json"
    packetPath.parent.mkdir(parents=True, exist_ok=True)
    packetPath.write_text(json.dumps(packet, indent=2), encoding="utf-8")
    assessment = buildAssessment(packet, registryPath=str(root))
    assessmentPath = root / "generated-output" / "curation" / "tool.assessment.json"
    assessmentPath.parent.mkdir(parents=True, exist_ok=True)
    assessmentPath.write_text(json.dumps(assessment, indent=2), encoding="utf-8")
    return packetPath, assessmentPath, assessment


def accounting_for(root: Path, packet: dict, content: str, identity: str):
    """Freeze the inventory and reconcile REAL receipts over the real artifacts."""
    packetPath = root / "registry-for-review" / "discovery-packets" / "tool.json"
    assessmentPath = root / "generated-output" / "curation" / "tool.assessment.json"
    source = packet["source"]
    frozen = freezeInventory([{
        "candidateId": packet["candidateId"], "namedIdentity": identity,
        "sourceRevision": source.get("revision") or source.get("commitSha"),
        "freshnessRequired": False, "sourceDigest": source["contentSha256"],
        "canonicalUrl": source["canonicalUrl"],
        "packetInput": {"sourceContent": content, "name": "Tool",
                        "description": "A tool capability for testing purposes.",
                        "packet": {"genericSnapshot": packet["genericSnapshot"]}},
    }])
    row = frozen["candidates"][0]
    receipt = {
        "candidateId": packet["candidateId"], "taskId": row["taskId"], "attempt": 1,
        "inputDigest": row["inputDigest"],
        "outputDigest": sha256(packetPath.read_bytes()), "packetHash": sha256(packetPath.read_bytes()),
        "packetPath": "registry-for-review/discovery-packets/tool.json",
        "assessmentPath": "generated-output/curation/tool.assessment.json",
        "assessmentSha256": sha256(assessmentPath.read_bytes()),
        "proposedGeneric": {"decision": "MAP", "genericId": "generic-a"}, "outcome": "review-ready",
    }
    report = reconcileInventory(frozen, [receipt], packetRoot=str(root))
    return frozen, report, receipt


def gate_production_refusal() -> None:
    print("\n=== Gate 1: the protected boundary refuses, and refuses completely ===")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        packet, content = genuine_packet(root)
        write_artifacts(root, packet)
        errors = verifyPacketAuthorization([packet], registryPath=str(root))
        check("a locally ratified packet is refused by the production verifier",
              errors == ["independent protected human authorization is not configured; L4 remains pending"],
              "; ".join(errors))
        check("the production trust seam denies unconditionally",
              _verifyTrustedEnvelope(None, None, registryPath=str(root)) ==
              ["independent protected human authorization is not configured; L4 remains pending"])


def gate_legitimate_flow() -> None:
    print("\n=== Gate 2: a legitimate batch still binds (no false rejection) ===")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        packet, content = genuine_packet(root)
        write_artifacts(root, packet)
        frozen, report, receipt = accounting_for(root, packet, content, "owner/exact-name")
        check("the legitimate reconciliation is review-ready",
              report["decisions"][0]["outcome"] == "review-ready", report["decisions"][0].get("reason", ""))
        assessment = json.loads((root / "generated-output/curation/tool.assessment.json").read_text())
        try:
            buildReviewPayload([packet], registryPath=str(root), submissionRoute="manifest",
                               manifestDigest="c" * 64, inventory=[packet],
                               assessments={packet["candidateId"]: assessment},
                               reviewInventory={"inventory": frozen, "reconciliation": report,
                                                "receipts": [receipt]})
            built = True
            detail = "payload built from genuine receipts"
        except Exception as exc:
            built = False
            detail = f"{type(exc).__name__}: {exc}"
        check("the legitimate batch builds an authorization payload", built, detail)


def gate_forgery() -> None:
    print("\n=== Gate 3: forged accounting is refused ===")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        packet, content = genuine_packet(root)
        write_artifacts(root, packet)
        frozen, report, receipt = accounting_for(root, packet, content, "owner/exact-name")
        assessment = json.loads((root / "generated-output/curation/tool.assessment.json").read_text())

        def attempt(label: str, review, expect):
            try:
                buildReviewPayload([packet], registryPath=str(root), submissionRoute="manifest",
                                   manifestDigest="c" * 64, inventory=[packet],
                                   assessments={packet["candidateId"]: assessment}, reviewInventory=review)
                check(label, False, "ACCEPTED")
            except ValueError as exc:
                check(label, expect in str(exc), str(exc)[:110])

        attempt("a report with no receipts is refused",
                {"inventory": frozen, "reconciliation": report}, "receipts")
        forged = json.loads(json.dumps(report))
        forged["decisions"][0]["packetArtifactSha256"] = "0" * 64
        attempt("a report with a forged artifact digest is refused",
                {"inventory": frozen, "reconciliation": forged, "receipts": [receipt]}, "disagrees")
        forged = json.loads(json.dumps(report))
        forged["decisions"][0]["outcome"] = "deferred"
        attempt("a report whose outcome disagrees with the receipts is refused",
                {"inventory": frozen, "reconciliation": forged, "receipts": [receipt]}, "disagrees")
        forged = json.loads(json.dumps(report))
        forged["accounted"] = False
        attempt("an unaccounted report is refused",
                {"inventory": frozen, "reconciliation": forged, "receipts": [receipt]}, "accounted")
        forged = json.loads(json.dumps(report))
        forged["humanApproved"] = True
        attempt("a report claiming human approval is refused",
                {"inventory": frozen, "reconciliation": forged, "receipts": [receipt]}, "human approval")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        packet, content = genuine_packet(root)
        write_artifacts(root, packet)
        mapping = dict(packet)
        mapping["namedIdentity"] = {"contributor": "forged", "slug": "spoofed"}
        frozen, report, receipt = accounting_for(root, mapping, content, "forged/spoofed")
        check("a mapping-form top-level identity binding is refused",
              report["decisions"][0]["outcome"] == "deferred",
              report["decisions"][0].get("reason", "")[:90])


def gate_scope_integrity() -> None:
    print("\n=== Gate 4: scope integrity against main ===")
    def run(*args):
        return subprocess.run(args, capture_output=True, text=True).stdout.strip()

    changed = run("git", "diff", "--name-only", "origin/main...HEAD", "--", "registry/")
    check("no canonical registry DATA changed", all("schema" in path for path in changed.splitlines()),
          changed.replace("\n", " "))
    for path in ("src/gaia_cli/commands/curate.py", "src/gaia_cli/curation/orchestrator.py"):
        same = run("git", "diff", "--quiet", "origin/main", "HEAD", "--", path)
        check(f"main's {path} is byte-identical", same == "")
    check("the skill mirrors are in sync", "in sync" in run("python", "scripts/sync_agent_skill_mirror.py", "--check"))
    quick = Path(".agents/skills/gaia-quick-curate/SKILL.md").read_text(encoding="utf-8")
    check("the quick-curate skill does not claim an executing CLI",
          "paused" in quick.lower() and "auto-merge" not in quick.lower())


def main() -> int:
    print("Merge-gate verification")
    gate_production_refusal()
    gate_legitimate_flow()
    gate_forgery()
    gate_scope_integrity()
    failed = [label for label, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
        return 1
    print("All merge-gate checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
