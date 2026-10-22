"""Original audit attacks, independently constructed synthetic fixtures.

No human approval is manufactured. These are negative production-boundary tests;
passing cannot establish a real protected approval ceremony.
"""
import copy
import hashlib
import json

import pytest

from gaia_cli.commands.pushFromFile import _load_yaml_file
from gaia_cli.intakeAdapter import validateL4Resolution


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()


def forgedPacket():
    generics = [{"id": key, "kind": "generic", "name": key.title(),
                 "description": "Synthetic generic capability for security regression.",
                 "type": "basic", "prerequisites": []}
                for key in ("animation-design", "ui-audit")]
    options = [{"genericId": "ui-audit", "rationale": "Retrieval recall only.",
                "similarity": 0.8, "matchTier": "strong"}]
    url = "https://github.com/synthetic/audit/blob/" + "1" * 40 + "/skills/motion/SKILL.md"
    selected = {key: value for key, value in generics[0].items() if key != "kind"}
    return {"contractVersion": "discovery-packet-v2", "candidateId": "synthetic/motion",
        "lifecycle": ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"],
        "artifactGate": "valid-skill", "source": {"canonicalUrl": url,
            "hostRepository": "https://github.com/synthetic/audit", "sourceLane": "source-repository",
            "fetchedAt": "2026-01-01T00:00:00Z", "contentSha256": "a" * 64,
            "frontmatter": {"name": "motion", "description": "Synthetic animation skill."}},
        "normalized": {"name": "motion", "description": "Synthetic animation skill."},
        "exactDedupe": {"matched": False}, "mappingOptions": options, "flags": [],
        "genericSnapshot": {"command": "gaia dev list --generic --json", "capturedAt": "2026-01-01T00:00:00Z",
            "generics": generics, "contentSha256": digest(generics), "mappingOptionsSha256": digest(options)},
        "decision": {"value": "MAP", "reasonCode": "L4_RATIFIED_MAP", "genericId": "animation-design"},
        "l4Resolution": {"status": "approved", "generic": selected,
            "named": {"contributor": "synthetic", "skillName": "motion"}, "skillFileUrl": url,
            "humanReview": {"humanOverride": True, "reviewedBy": "invented-human",
                "approvalRef": "invented-reference", "reviewedAt": "invented-time",
                "rationale": "Invented rationale", "assessmentPath": "/nonexistent-audit-assessment.json",
                "assessmentReceiptDigest": "b" * 64, "attestation": "Fabricated local attestation"}}}


@pytest.mark.parametrize("mutation", ["identity", "approval-reference", "timestamp", "outside-top-k", "source", "generic-definition"])
def test_audit_forgery_rejected_at_trusted_adapter(mutation):
    packet = forgedPacket()
    if mutation == "identity":
        packet["l4Resolution"]["named"]["skillName"] = "changed-after-approval"
    elif mutation == "approval-reference":
        packet["l4Resolution"]["humanReview"]["approvalRef"] = "https://github.com/gaia-research/gaia-skill-tree/issues/123"
    elif mutation == "timestamp":
        packet["l4Resolution"]["humanReview"]["reviewedAt"] = "2026-10-20T12:00:00Z"
    elif mutation == "source":
        packet["source"]["contentSha256"] = "c" * 64
    elif mutation == "generic-definition":
        packet["l4Resolution"]["generic"]["description"] = "Changed after purported approval."
    assert validateL4Resolution(packet, requireHumanReview=True,
                                trustedGenerics=packet["genericSnapshot"]["generics"])


def test_empty_digest_matched_assessment_does_not_grant_authority(tmp_path):
    packet = forgedPacket()
    assessment = tmp_path / "empty.json"
    assessment.write_text("{}")
    packet["l4Resolution"]["humanReview"].update(assessmentPath=str(assessment), assessmentReceiptDigest=digest({}))
    assert validateL4Resolution(packet, requireHumanReview=True,
                                trustedGenerics=packet["genericSnapshot"]["generics"])


@pytest.mark.parametrize("manifest", [False, True])
def test_forged_packet_cannot_submit_on_either_route(tmp_path, monkeypatch, manifest):
    monkeypatch.chdir(tmp_path)
    packet = forgedPacket()
    directory = tmp_path / "registry-for-review/discovery-packets"
    directory.mkdir(parents=True)
    path = directory / "forged.json"
    path.write_text(json.dumps(packet))
    monkeypatch.setattr("gaia_cli.prefill.buildGenericSnapshot", lambda root: {"generics": packet["genericSnapshot"]["generics"]})
    if manifest:
        path = tmp_path / "manifest.json"
        path.write_text(json.dumps({"contractVersion": "discovery-packet-manifest-v1",
                                   "packetPaths": ["registry-for-review/discovery-packets/forged.json"]}))
    data, error = _load_yaml_file(str(path))
    assert data is None and error
    assert not list((tmp_path / "registry-for-review").glob("skill-batches/*"))
