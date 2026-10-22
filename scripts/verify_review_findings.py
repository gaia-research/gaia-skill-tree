"""Independent verification probes for the three P2 findings of the runtime review.

Run from the remediation worktree:  PYTHONPATH=src python scripts/verify_review_findings.py

Each probe reproduces the reviewer's original reproduction and asserts the NEW
behaviour. Nothing here mutates the canonical registry or the network.
"""
from __future__ import annotations

import copy
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

RESULTS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, detail: str = "") -> None:
    RESULTS.append((label, bool(ok), detail))
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" — {detail}" if detail else ""))


def probe_symlinked_output_directory() -> None:
    print("\n=== Finding 1: symlinked output directory escapes the registry root ===")
    from gaia_cli.prefill import writeAssessmentReceipt, writePacket

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        outside = Path(tmp) / "outside"
        outside.mkdir()
        (root / "registry-for-review").mkdir(parents=True)
        # The discovery-packets directory is a symlink pointing OUTSIDE the root.
        (root / "registry-for-review" / "discovery-packets").symlink_to(outside, target_is_directory=True)

        packet = {"contractVersion": "discovery-packet-v2", "candidateId": "synthetic/a-b"}
        escaped = False
        try:
            writePacket(packet, str(root))
        except Exception:
            escaped = True
        wrote_outside = any(outside.iterdir()) if outside.exists() else False
        check("writePacket refuses a symlinked output directory", escaped,
              "raised" if escaped else "no error raised")
        check("writePacket wrote NOTHING outside the registry root", not wrote_outside,
              f"outside contains: {[p.name for p in outside.iterdir()] if outside.exists() else []}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        outside = Path(tmp) / "outside"
        outside.mkdir()
        # The assessment-receipt output directory is a symlink pointing OUTSIDE.
        (root / "generated-output").mkdir(parents=True)
        (root / "generated-output" / "curation").symlink_to(outside, target_is_directory=True)
        packet = {"contractVersion": "discovery-packet-v2", "candidateId": "synthetic/a-b"}
        escaped_assessment = False
        try:
            writeAssessmentReceipt(packet, {"advisory": True}, str(root))
        except Exception:
            escaped_assessment = True
        check("writeAssessmentReceipt refuses a symlinked output directory", escaped_assessment,
              "raised" if escaped_assessment else "no error raised")
        check("writeAssessmentReceipt wrote NOTHING outside the registry root",
              not any(outside.iterdir()) if outside.exists() else True,
              f"outside contains: {[p.name for p in outside.iterdir()] if outside.exists() else []}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        outside = Path(tmp) / "outside"
        outside.mkdir()
        (root / "registry-for-review").mkdir(parents=True)
        (root / "registry-for-review" / "discovery-packets").mkdir()
        from gaia_cli.prefill import safeCandidateSlug

        slug = safeCandidateSlug("synthetic/a-b")
        leaf = root / "registry-for-review" / "discovery-packets" / f"{slug}.json"
        leaf.symlink_to(outside / "target.json")
        refused = False
        try:
            from gaia_cli.prefill import writePacket

            writePacket({"contractVersion": "discovery-packet-v2", "candidateId": "synthetic/a-b"}, str(root))
        except Exception:
            refused = True
        check("a symlinked LEAF file is still refused", refused,
              "raised" if refused else "no error raised")
        check("the symlinked leaf target was not written through",
              not (outside / "target.json").exists(),
              f"outside contains: {[p.name for p in outside.iterdir()]}")

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp) / "repo"
        (root / "registry-for-review" / "discovery-packets").mkdir(parents=True)
        from gaia_cli.prefill import writePacket

        path = writePacket({"contractVersion": "discovery-packet-v2", "candidateId": "synthetic/ok"}, str(root))
        check("a normal (non-symlinked) write still succeeds inside the root",
              Path(path).is_file() and str(Path(path).resolve()).startswith(str(root.resolve())),
              str(path))


def probe_fanout_conflict_loss() -> None:
    print("\n=== Finding 2: FAN-OUT resume dropped conflicting prior receipts ===")
    from gaia_cli.curation.fanout import runFanout
    from gaia_cli.curation.reconciliation import freezeInventory, reconcileInventory, sha256, canonicalJson

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        (root / "registry" / "nodes" / "basic").mkdir(parents=True)
        (root / "registry" / "named").mkdir(parents=True)
        (root / "registry" / "nodes" / "basic" / "animation-design.json").write_text(json.dumps({
            "id": "animation-design", "name": "Animation Design",
            "description": "Designs motion and animation behavior in interfaces.",
            "type": "basic", "prerequisites": [],
        }), encoding="utf-8")
        from gaia_cli.curation.assessment import buildAssessment
        from gaia_cli.prefill import buildGenericSnapshot

        snapshot = buildGenericSnapshot(str(root))
        snapshot["generics"] = [{**row, "kind": "generic"} for row in snapshot["generics"]]
        options = [{"genericId": "animation-design", "rationale": "Exact capability match.",
                    "similarity": 0.9, "matchTier": "strong"}]
        snapshot["contentSha256"] = sha256(canonicalJson(snapshot["generics"]))
        snapshot["mappingOptionsSha256"] = sha256(canonicalJson(options))
        content = "---\nname: Motion\ndescription: A motion capability for testing purposes.\n---\nbody\n"
        row = {
            "candidateId": "candidate-00", "namedIdentity": "author/motion",
            "sourceRevision": "rev-0", "freshnessRequired": False,
            "sourceDigest": sha256(content.encode()),
            "canonicalUrl": "https://example.test/0/SKILL.md",
            "packetInput": {"sourceContent": content, "name": "Motion",
                            "description": "A motion capability for testing purposes.",
                            "packet": {"genericSnapshot": snapshot}},
        }
        frozen = freezeInventory([row])
        frozen_row = frozen["candidates"][0]

        def packet_value():
            return {
                "contractVersion": "discovery-packet-v2", "candidateId": frozen_row["candidateId"],
                "namedIdentity": frozen_row["namedIdentity"],
                "lifecycle": ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"],
                "source": {"canonicalUrl": frozen_row["canonicalUrl"], "hostRepository": "https://example.test",
                           "sourceLane": "source-repository", "fetchedAt": "2026-10-20T00:00:00+00:00",
                           "commitSha": frozen_row["sourceRevision"], "contentSha256": frozen_row["sourceDigest"],
                           "frontmatter": {"name": "Motion", "description": "A motion capability for testing purposes."}},
                "normalized": {"name": "Motion", "description": "A motion capability for testing purposes."},
                "exactDedupe": {"matched": False, "checked": True},
                "mappingOptions": options, "genericSnapshot": snapshot,
                "decision": {"value": "MAP", "reasonCode": "MAP_EXISTING_GENERIC", "genericId": "animation-design"},
                "flags": [],
            }

        def receipt(attempt: int):
            value = packet_value()
            assessment = buildAssessment(value, registryPath=str(root))
            data = canonicalJson(value)
            return {
                "candidateId": frozen_row["candidateId"], "taskId": frozen_row["taskId"], "attempt": attempt,
                "inputDigest": frozen_row["inputDigest"], "outputDigest": sha256(data),
                "packetHash": sha256(data), "packetBytes": data, "assessment": assessment,
                "assessmentSha256": sha256(canonicalJson(assessment)),
                "proposedGeneric": {"decision": "MAP", "genericId": "animation-design"},
                "outcome": "review-ready",
            }

        prior = [receipt(1), receipt(2)]
        direct = reconcileInventory(frozen, prior, packetRoot=str(root))
        direct_outcome = direct["decisions"][0]["outcome"]
        check("direct reconciliation treats two receipts for one candidate as a conflict",
              direct_outcome == "deferred" and "conflict" in direct["decisions"][0]["reason"],
              direct["decisions"][0]["reason"])

        def worker(task, attempt):
            return receipt(attempt)

        result = runFanout(frozen, worker, priorReceipts=prior, packetRoot=str(root))
        final = reconcileInventory(frozen, result["receipts"], packetRoot=str(root))
        outcome = final["decisions"][0]["outcome"]
        check("FAN-OUT resume does NOT silently upgrade a conflicted candidate to review-ready",
              outcome != "review-ready", f"outcome={outcome} reason={final['decisions'][0]['reason']}")
        check("the conflict is surfaced as an explicit diagnostic",
              bool(result.get("priorReceiptErrors")),
              json.dumps(result.get("priorReceiptErrors", {}))[:140])


def probe_row_to_packet_binding() -> None:
    print("\n=== Finding 3: review accounting did not bind each row to its packet ===")
    from gaia_cli.curation.authorization import buildReviewPayload
    from gaia_cli.curation.reconciliation import canonicalJson, freezeInventory, sha256

    # The assessment must be a REAL receipt: validateAssessment recomputes every
    # field against the current catalog and semantic inputs.
    from gaia_cli.curation.assessment import buildAssessment

    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        # Build a GENUINE discovery packet with the production prefill so the
        # packet satisfies the real v2 contract instead of a hand-rolled shape.
        from unittest.mock import patch

        from gaia_cli import prefill

        registry_node = root / "registry" / "nodes" / "basic" / "generic-a.json"
        registry_node.parent.mkdir(parents=True, exist_ok=True)
        registry_node.write_text(json.dumps({
            "id": "generic-a", "name": "Generic A",
            "description": "A generic ability for the test.", "type": "basic",
            "prerequisites": [],
        }), encoding="utf-8")
        (root / "registry" / "named").mkdir(parents=True, exist_ok=True)
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
        # The prefill path defers; model the ratified MAP decision for review.
        packet["lifecycle"] = ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"]
        packet["decision"] = {"value": "MAP", "reasonCode": "L4_RATIFIED_MAP", "genericId": "generic-a"}
        packet["namedIdentity"] = "owner/exact-name"
        packet["l4Resolution"] = {
            "status": "approved",
            "generic": {"id": "generic-a", "name": "Generic A",
                        "description": "A generic ability.", "type": "fusion",
                        "prerequisites": ["generic-b"]},
            "named": {"contributor": "owner", "skillName": "exact-name"},
            "skillFileUrl": packet["source"]["canonicalUrl"],
        }
        # The v2 validator requires a complete humanReview block when an
        # l4Resolution is present, and a well-formed suite block.
        packet["l4Resolution"]["humanReview"] = {
            "reviewedBy": "reviewer", "approvalRef": "intake/1",
            "rationale": "Reviewed the actual source.", "reviewedAt": "2026-10-20T00:00:00Z",
            "assessmentPath": "assessment.json",
            "assessmentReceiptDigest": "a" * 64,
            "humanOverride": True, "operatorOverride": True,
            "attestation": "Local text only.",
        }
        packet["suite"] = {"role": "capstone", "suiteId": "suite-1",
                           "componentCandidateIds": ["candidate-1"]}
        content_digest = hashlib.sha256(content.encode("utf-8")).hexdigest()
        packet_url = packet["source"]["canonicalUrl"]
        packet_revision = packet["source"].get("revision") or packet["source"].get("commitSha")
        packet_digest = packet["source"]["contentSha256"]

        def frozen_row(named_identity, url, revision, digest):
            envelope = freezeInventory([{
                "candidateId": "candidate-1", "namedIdentity": named_identity,
                "sourceRevision": revision, "freshnessRequired": False,
                "sourceDigest": digest, "canonicalUrl": url,
                "packetInput": {"sourceContent": content, "name": "Tool",
                                "description": "A tool capability for testing purposes.",
                                "packet": {"genericSnapshot": packet["genericSnapshot"]}},
            }])
            return envelope

        def report_for(envelope, named_identity, packet):
            """Build a GENUINE receipt-backed reconciliation, not a hand-made report.

            The payload builder recomputes the reconciliation from the receipts
            and requires the claimed report to agree, so a forged report cannot
            be bound into an authorization payload.
            """
            from gaia_cli.curation.authorization import _proposalPacket
            from gaia_cli.curation.reconciliation import reconcileInventory

            row = envelope["candidates"][0]
            data = canonicalJson(packet)
            assessment = buildAssessment(packet, registryPath=str(root))
            receipt = {
                "candidateId": row["candidateId"], "taskId": row["taskId"], "attempt": 1,
                "inputDigest": row["inputDigest"], "outputDigest": sha256(data),
                "packetHash": sha256(data), "packetBytes": data,
                "assessment": assessment, "assessmentSha256": sha256(canonicalJson(assessment)),
                "proposedGeneric": {"decision": "MAP", "genericId": "generic-a"},
                "outcome": "review-ready",
            }
            report = reconcileInventory(envelope, [receipt], packetRoot=str(root))
            return report, [receipt], assessment

        # Mismatched: the frozen row's named identity and source differ from the packet.
        mismatched = frozen_row("owner/inventory-name",
                                "https://github.com/upstream/other/blob/def456/SKILL.md",
                                "def456", packet_digest)
        rejected = False
        detail = ""
        try:
            report, receipts, assessment = report_for(mismatched, "owner/inventory-name", packet)
            buildReviewPayload([packet], registryPath=str(root), submissionRoute="manifest",
                               manifestDigest="c" * 64, inventory=[packet],
                               assessments={"candidate-1": assessment},
                               reviewInventory={"inventory": mismatched,
                                                "reconciliation": report,
                                                "receipts": receipts})
        except Exception as exc:
            rejected = True
            detail = f"{type(exc).__name__}: {exc}"
        check("a frozen row whose named identity/source differ from its packet is REJECTED",
              rejected, detail[:150])

        # Consistent: the frozen row matches the packet exactly.
        consistent = frozen_row("owner/exact-name", packet_url, packet_revision, packet_digest)
        built = False
        detail = ""  # Reset: the positive control must not print the negative case's error.
        try:
            report, receipts, assessment = report_for(consistent, "owner/exact-name", packet)
            buildReviewPayload([packet], registryPath=str(root), submissionRoute="manifest",
                               manifestDigest="c" * 64, inventory=[packet],
                               assessments={"candidate-1": assessment},
                               reviewInventory={"inventory": consistent,
                                                "reconciliation": report,
                                                "receipts": receipts})
            built = True
        except Exception as exc:
            detail = f"{type(exc).__name__}: {exc}"
        check("a self-consistent review inventory still builds a payload (positive control)", built,
              detail[:150] if not built else "payload built from genuine receipts")

        # A report is only evidence when it can be recomputed from the receipts
        # it claims to come from. A hand-forged "review-ready" row must not bind.
        forged = copy.deepcopy(report)
        forged["decisions"][0]["outcome"] = "review-ready"
        forged["decisions"][0]["receiptValid"] = True
        forged_rejected = False
        forged_detail = ""
        try:
            buildReviewPayload([packet], registryPath=str(root), submissionRoute="manifest",
                               manifestDigest="c" * 64, inventory=[packet],
                               assessments={"candidate-1": assessment},
                               reviewInventory={"inventory": consistent,
                                                "reconciliation": forged,
                                                "receipts": []})
        except Exception as exc:
            forged_rejected = True
            forged_detail = f"{type(exc).__name__}: {exc}"
        check("a forged review-ready report with no receipts is REJECTED",
              forged_rejected, forged_detail[:150])


def main() -> int:
    print("Independent verification of runtime-review findings")
    probe_symlinked_output_directory()
    probe_fanout_conflict_loss()
    probe_row_to_packet_binding()
    failed = [label for label, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
        return 1
    print("All three reviewed findings are closed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
