"""Bounded curation walkthroughs required by #2118.

Read-only against the repository: everything happens in temporary directories.
Two walkthroughs:
  1. Small batch  - a 3-candidate batch, honest outcomes, replay-safe identity.
  2. Suite        - six distinct named candidates mapped to ONE generic must stay
                    six rows (lossless identity) and one shared generic.
Neither walkthrough mutates the canonical registry, opens an intake, or claims
human approval: the protected L4 gate is expected to REFUSE.
"""
from __future__ import annotations

import hashlib
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, "src")

from gaia_cli.curation.assessment import buildAssessment  # noqa: E402
from gaia_cli.curation.reconciliation import (  # noqa: E402
    canonicalJson,
    freezeInventory,
    reconcileInventory,
    sha256,
)
from gaia_cli.curation.errors import (  # noqa: E402
    classify_refusals,
    public_detail,
)

RESULTS: list[tuple[str, bool, str]] = []


def check(label: str, ok: bool, code: str = "") -> None:
    """Record a check result and print a bounded, non-sensitive summary.

    ``code`` is a console-safe token (an uppercase identifier). It is the only
    dynamic text this script prints: refusal text, exception renderings and
    payloads are never echoed, because they can carry upstream content. A code
    that is not a safe token is withheld rather than printed.
    """
    RESULTS.append((label, bool(ok), code))
    safe = public_detail(code) if code else ""
    print(f"  [{'PASS' if ok else 'FAIL'}] {label}" + (f" — {safe}" if safe else ""))


def make_registry(root: Path) -> Path:
    """Create a temporary canonical registry root (registry/nodes/<type>/<id>.json)."""
    registry = root / "registry"
    (registry / "nodes" / "basic").mkdir(parents=True)
    (registry / "named").mkdir(parents=True)
    (registry / "nodes" / "basic" / "animation-design.json").write_text(
        json.dumps({
            "id": "animation-design",
            "name": "Animation Design",
            "description": "Designs motion, transitions and animation systems.",
            "type": "basic",
            "prerequisites": [],
        }, indent=2),
        encoding="utf-8",
    )
    return root


def source_for(name: str, description: str) -> str:
    return f"---\nname: {name}\ndescription: {description}\n---\n\n# {name}\n\nBody.\n"


OPTIONS = [{
    "genericId": "animation-design",
    "rationale": "Exact capability match.",
    "similarity": 0.9,
    "matchTier": "strong",
}]


def generic_snapshot(registry_root: Path) -> dict:
    from gaia_cli.prefill import buildGenericSnapshot

    snapshot = buildGenericSnapshot(str(registry_root))
    if snapshot is None:
        raise RuntimeError("fixture registry has no canonical generic nodes")
    # The v2 validator requires the generic kind marker, the canonical content
    # digest and the mapping-options digest to agree with the live catalog.
    snapshot["generics"] = [{**row, "kind": "generic"} for row in snapshot["generics"]]
    snapshot["contentSha256"] = sha256(canonicalJson(snapshot["generics"]))
    snapshot["mappingOptionsSha256"] = sha256(canonicalJson(OPTIONS))
    return snapshot


def build_candidate(index: int, registry: Path, *, named_identity: str) -> dict:
    name = f"motion-skill-{index}"
    description = f"Motion implementation number {index} for the animation suite."
    content = source_for(name, description)
    url = f"https://github.com/suite/motion/blob/main/skills/{index}/SKILL.md"
    return {
        "candidateId": f"suite/motion/{index}",
        "namedIdentity": named_identity,
        "sourceRevision": "a" * 40,
        "freshnessRequired": False,
        "sourceDigest": hashlib.sha256(content.encode("utf-8")).hexdigest(),
        "canonicalUrl": url,
        "packetInput": {
            "candidateId": f"suite/motion/{index}",
            "namedIdentity": named_identity,
            "sourceContent": content,
            "name": name,
            "description": description,
            "packet": {"genericSnapshot": generic_snapshot(registry)},
        },
    }


def build_packet(row: dict, *, generic_id: str = "animation-design", duplicate_of: dict | None = None) -> dict:
    snapshot = row["packetInput"]["packet"]["genericSnapshot"]
    lifecycle = (["discovered", "fetched", "parsed", "normalized", "deduped", "rejected"]
                 if duplicate_of else
                 ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"])
    return {
        "contractVersion": "discovery-packet-v2",
        "candidateId": row["candidateId"],
        "namedIdentity": row["namedIdentity"],
        "lifecycle": lifecycle,
        "source": {
            "canonicalUrl": row["canonicalUrl"],
            "hostRepository": "https://github.com/suite/motion",
            "sourceLane": "source-repository",
            "fetchedAt": "2026-10-20T00:00:00+00:00",
            "commitSha": row["sourceRevision"],
            "contentSha256": row["sourceDigest"],
            "frontmatter": {"name": row["packetInput"]["name"], "description": row["packetInput"]["description"]},
        },
        "normalized": {"name": row["packetInput"]["name"], "description": row["packetInput"]["description"]},
        "exactDedupe": ({"matched": True, "checked": True,
                         "matchedCandidateId": duplicate_of["candidateId"],
                         "matchedCanonicalUrl": duplicate_of["canonicalUrl"],
                         "contentSha256": duplicate_of["sourceDigest"],
                         "namedIdentity": duplicate_of["namedIdentity"]}
                        if duplicate_of else
                        {"matched": False, "checked": True, "matchedCandidateId": None,
                         "matchedCanonicalUrl": None, "namedIdentity": None}),
        "mappingOptions": [dict(OPTIONS[0], genericId=generic_id)],
        "genericSnapshot": snapshot,
        "decision": ({"value": "DUPLICATE", "reasonCode": "EXACT_DUPLICATE"}
                    if duplicate_of else
                    {"value": "MAP", "reasonCode": "MAP_EXISTING_GENERIC", "genericId": generic_id}),
        "flags": [],
    }


def build_receipt(row: dict, registry: Path, packet_value: dict) -> dict:
    assessment = buildAssessment(packet_value, registryPath=str(registry))
    data = canonicalJson(packet_value)
    return {
        "candidateId": row["candidateId"],
        "taskId": row["taskId"],
        "attempt": 1,
        "inputDigest": row["inputDigest"],
        "outputDigest": sha256(data),
        "packetHash": sha256(data),
        "packetBytes": data,
        "assessment": assessment,
        "assessmentSha256": sha256(canonicalJson(assessment)),
        "proposedGeneric": ({"decision": "DUPLICATE"}
                          if packet_value["decision"]["value"] == "DUPLICATE" else
                          {"decision": "MAP", "genericId": "animation-design"}),
        "outcome": ("proven-duplicate" if packet_value["decision"]["value"] == "DUPLICATE"
                    else "review-ready"),
    }


def walkthrough_small_batch() -> None:
    print("\n=== Walkthrough 1: small batch (3 candidates) ===")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        registry = make_registry(root)
        candidates = [build_candidate(i, registry, named_identity=f"suite/motion-{i}") for i in range(3)]
        frozen = freezeInventory(candidates)
        rows = {row["candidateId"]: row for row in frozen["candidates"]}
        receipts = [build_receipt(rows[c["candidateId"]], registry, build_packet(rows[c["candidateId"]]))
                    for c in candidates]
        report = reconcileInventory(frozen, receipts, packetRoot=str(registry))

        check("every expected candidate is accounted for exactly once",
              report["accounted"] and len(report["decisions"]) == 3,
              "DECISIONS_EXPECTED_3")
        check("all three are review-ready with no loss",
              report["counts"]["review-ready"] == 3, "REVIEW_READY_COUNT_3")
        check("reconciliation never claims human approval", report["humanApproved"] is False)
        check("each row keeps its own exact named identity",
              {d["namedIdentity"] for d in report["decisions"]} ==
              {"suite/motion-0", "suite/motion-1", "suite/motion-2"})
        check("reconciliation is order-independent",
              reconcileInventory(frozen, list(reversed(receipts)), packetRoot=str(registry)) == report)

        # Replay: the same content must yield the same identity, not a new one.
        from gaia_cli.curation.submission import contentKey

        body = {"batchId": "content-demo", "userId": "curator", "sourceRepo": "suite/motion"}
        check("identical content derives an identical submission key",
              contentKey(body) == contentKey(dict(body)))
        check("changed content derives a different submission key",
              contentKey(body) != contentKey({**body, "userId": "someone-else"}))

        # The protected L4 gate must REFUSE locally authored approval.
        from gaia_cli.intakeAdapter import validateL4Resolution

        # A complete, realistic ratified packet: valid artifact gate, real
        # assessment receipt, real decision, and a locally authored review block.
        # Only the INDEPENDENT human ceremony is missing, so the refusal must
        # come from the authorization seam itself.
        packet = build_packet(rows["suite/motion/0"])
        packet["artifactGate"] = "valid-skill"
        packet["decision"] = {"value": "MAP", "reasonCode": "L4_RATIFIED_MAP",
                              "genericId": "animation-design"}
        assessment = buildAssessment(packet, registryPath=str(registry))
        assessment_path = registry / "generated-output" / "curation" / "walkthrough.assessment.json"
        assessment_path.parent.mkdir(parents=True, exist_ok=True)
        assessment_path.write_text(json.dumps(assessment, indent=2), encoding="utf-8")
        packet["l4Resolution"] = {
            "status": "approved",
            "generic": {"id": "animation-design", "name": "Animation Design",
                        "description": "Designs motion, transitions and animation systems.",
                        "type": "basic", "prerequisites": []},
            "named": {"contributor": "suite", "skillName": "motion-0"},
            "skillFileUrl": rows["suite/motion/0"]["canonicalUrl"],
            "humanReview": {"humanOverride": True, "reviewedBy": "curator",
                            "approvalRef": "https://github.com/gaia-research/gaia-skill-tree/issues/1",
                            "reviewedAt": "2026-10-20T00:00:00Z", "rationale": "looks right",
                            "attestation": "I approve this",
                            "assessmentPath": str(assessment_path),
                            "assessmentReceiptDigest": sha256(canonicalJson(assessment))},
        }
        errors = validateL4Resolution(packet, requireHumanReview=True,
                                      trustedGenerics=generic_snapshot(registry)["generics"])
        # The refusal must come from the AUTHORIZATION seam, not from an earlier
        # structural check, otherwise this proves nothing about human authority.
        check("locally authored humanReview does NOT authorize",
              any("protected human authorization is not configured" in error for error in errors),
              classify_refusals(errors))
        check("the refusal is the independent-authorization gate, not a shape error",
              errors == ["independent protected human authorization is not configured; L4 remains pending"],
              classify_refusals(errors))


def walkthrough_suite() -> None:
    print("\n=== Walkthrough 2: suite — six named candidates, ONE generic ===")
    with tempfile.TemporaryDirectory() as tmp:
        root = Path(tmp)
        registry = make_registry(root)
        candidates = [build_candidate(i, registry, named_identity=f"suite/motion-{i}") for i in range(6)]
        frozen = freezeInventory(candidates)
        rows = {row["candidateId"]: row for row in frozen["candidates"]}
        receipts = [build_receipt(rows[c["candidateId"]], registry, build_packet(rows[c["candidateId"]]))
                    for c in candidates]
        report = reconcileInventory(frozen, receipts, packetRoot=str(registry))

        check("six distinct named candidates stay six rows", len(report["decisions"]) == 6,
              "DECISIONS_EXPECTED_6")
        check("all six are review-ready", report["counts"]["review-ready"] == 6, "REVIEW_READY_COUNT_6")
        check("six distinct named identities survive",
              len({d["namedIdentity"] for d in report["decisions"]}) == 6)
        check("they share exactly one generic",
              {d["proposedGeneric"]["genericId"] for d in report["decisions"]} == {"animation-design"})
        check("a shared generic never collapses rows", report["accounted"] is True)

        # A shared generic must NOT be mistaken for an exact duplicate.
        forged = dict(receipts[0])
        forged["outcome"] = "proven-duplicate"
        forged["duplicateProof"] = {"targetNamedIdentity": rows["suite/motion/1"]["namedIdentity"],
                                    "canonicalUrl": rows["suite/motion/0"]["canonicalUrl"]}
        forged_report = reconcileInventory(frozen, [forged] + receipts[1:], packetRoot=str(registry))
        check("a shared generic is not an exact duplicate",
              forged_report["decisions"][0]["outcome"] == "deferred",
              "OUTCOME_DEFERRED")

        # An exact duplicate must name a different surviving target with the
        # same source proof.
        dup_rows = [build_candidate(i, registry, named_identity=f"suite/motion-{i}") for i in range(2)]
        # A genuine exact duplicate: same source bytes and URL, different identity.
        dup_rows[1]["sourceDigest"] = dup_rows[0]["sourceDigest"]
        dup_rows[1]["packetInput"]["sourceContent"] = dup_rows[0]["packetInput"]["sourceContent"]
        dup_rows[1]["packetInput"]["name"] = dup_rows[0]["packetInput"]["name"]
        dup_rows[1]["packetInput"]["description"] = dup_rows[0]["packetInput"]["description"]
        dup_rows[1]["canonicalUrl"] = dup_rows[0]["canonicalUrl"]
        dup_frozen = freezeInventory(dup_rows)
        dup_map = {r["candidateId"]: r for r in dup_frozen["candidates"]}
        first = dup_map["suite/motion/0"]
        second = dup_map["suite/motion/1"]
        first_receipt = build_receipt(first, registry, build_packet(first))
        duplicate_packet = build_packet(second, duplicate_of=first)
        second_receipt = build_receipt(second, registry, duplicate_packet)
        second_receipt["outcome"] = "proven-duplicate"
        second_receipt["duplicateProof"] = {"targetNamedIdentity": first["namedIdentity"],
                                            "canonicalUrl": first["canonicalUrl"]}
        dup_report = reconcileInventory(dup_frozen, [first_receipt, second_receipt], packetRoot=str(registry))
        by_id = {d["candidateId"]: d for d in dup_report["decisions"]}
        check("a genuine exact duplicate with a surviving target is proven",
              by_id["suite/motion/1"]["outcome"] == "proven-duplicate",
              "OUTCOME_PROVEN_DUPLICATE")
        check("its surviving target remains review-ready",
              by_id["suite/motion/0"]["outcome"] == "review-ready")


def main() -> int:
    print("Curation walkthroughs (#2118 bounded verification)")
    walkthrough_small_batch()
    walkthrough_suite()
    failed = [label for label, ok, _ in RESULTS if not ok]
    print(f"\n{len(RESULTS) - len(failed)}/{len(RESULTS)} checks passed")
    if failed:
        print("FAILED: " + "; ".join(failed))
        return 1
    print("All bounded walkthrough checks passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
