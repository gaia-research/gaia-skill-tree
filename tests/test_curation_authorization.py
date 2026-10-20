"""Synthetic security tests for the lane-A authorization boundary.

No test here claims production authorization: the one successful path replaces
only the private trust hook with an explicitly unit-only verifier stub.
"""
import copy
import hashlib
import json

from gaia_cli.curation.authorization import (
    _digest,
    buildReviewPayload,
    verifyPacketAuthorization,
)


def packet(candidate="upstream/tool"):
    return {
        "contractVersion": "discovery-packet-v2",
        "candidateId": candidate,
        "source": {
            "canonicalUrl": "https://github.com/upstream/tool/blob/abc123/SKILL.md",
            "commitSha": "abc123", "contentSha256": "a" * 64,
        },
        "decision": {"value": "MAP", "genericId": "generic-a"},
        "genericSnapshot": {"generics": [{"id": "generic-a", "kind": "generic"}]},
        "suite": {"role": "component", "componentCandidateIds": [candidate]},
        "l4Resolution": {
            "generic": {"id": "generic-a", "name": "Generic A", "description": "A generic ability.",
                        "type": "fusion", "prerequisites": ["generic-b"]},
            "named": {"contributor": "Owner", "skillName": "exact-name"},
            "skillFileUrl": "https://github.com/upstream/tool/blob/abc123/SKILL.md",
        },
    }


def test_payload_binds_all_manifest_packets_exact_digest_and_context(tmp_path):
    rows = [packet(), packet("upstream/second")]
    rawManifest = b'{"contractVersion":"discovery-packet-manifest-v1","packetPaths":["a","b"]}\n'
    manifestDigest = hashlib.sha256(rawManifest).hexdigest()
    payload = buildReviewPayload(rows, registryPath=str(tmp_path), submissionRoute="manifest",
                                 manifestDigest=manifestDigest, inventory=rows,
                                 assessments={"upstream/tool": {"assessment": "A"},
                                             "upstream/second": {"assessment": "B"}})
    assert payload["manifestSha256"] == manifestDigest
    assert [row["candidateId"] for row in payload["inventory"]] == ["upstream/tool", "upstream/second"]
    assert payload["inventory"][0]["namedIdentity"] == {"contributor": "Owner", "skillName": "exact-name"}
    assert payload["inventory"][0]["generic"]["prerequisites"] == ["generic-b"]
    assert payload["inventory"][0]["source"]["revision"] == "abc123"
    assert payload["inventory"][0]["assessmentSha256"] == _digest({"assessment": "A"})


def test_manifest_rejects_leaf_only_or_missing_exact_manifest_hash(tmp_path):
    row = packet()
    assert verifyPacketAuthorization(row, registryPath=str(tmp_path), submissionRoute="manifest",
                                     inventory=[row])
    assert verifyPacketAuthorization(row, registryPath=str(tmp_path), submissionRoute="manifest",
                                     manifestDigest="0" * 64, inventory=[row, packet("upstream/second")])


def test_forged_user_metadata_never_authenticates(tmp_path):
    row = packet()
    row["l4Resolution"]["humanReview"] = {
        "reviewedBy": "maintainer", "approvalRef": "issue#123", "attestation": "approved",
        "acknowledgeHumanReview": True,
    }
    forged = {"reviewPayloadSha256": "0" * 64, "reviewer": "maintainer", "approved": True}
    errors = verifyPacketAuthorization(row, registryPath=str(tmp_path), envelope=forged)
    assert any("does not bind" in error for error in errors)


def test_altered_reviewed_payload_is_rejected_even_with_old_envelope(tmp_path):
    row = packet()
    payload = buildReviewPayload(row, registryPath=str(tmp_path))
    envelope = {"reviewPayloadSha256": _digest(payload), "runId": 42, "reviewer": "maintainer"}
    altered = copy.deepcopy(row)
    altered["l4Resolution"]["generic"]["prerequisites"] = ["different"]
    errors = verifyPacketAuthorization(altered, registryPath=str(tmp_path), envelope=envelope)
    assert any("does not bind" in error for error in errors)


def test_mocked_authenticated_success_is_unit_only_and_rejects_revocation(tmp_path, monkeypatch):
    row = packet()
    payload = buildReviewPayload(row, registryPath=str(tmp_path))
    envelope = {"reviewPayloadSha256": _digest(payload), "runId": 42, "attempt": 1,
                "reviewer": "maintainer", "caller": "agent", "artifactBytes": "synthetic"}

    def unitOnlyMockVerifier(computed, supplied, *, registryPath):
        assert supplied["reviewPayloadSha256"] == _digest(computed)
        assert supplied["reviewer"] != supplied["caller"]
        return []  # UNIT-ONLY: no GitHub, protected environment, or real human approval.

    monkeypatch.setattr("gaia_cli.curation.authorization._verifyTrustedEnvelope", unitOnlyMockVerifier)
    assert verifyPacketAuthorization(row, registryPath=str(tmp_path), envelope=envelope) == []

    def revokedMockVerifier(computed, supplied, *, registryPath):
        return ["authorization was revoked or is stale"]

    monkeypatch.setattr("gaia_cli.curation.authorization._verifyTrustedEnvelope", revokedMockVerifier)
    assert verifyPacketAuthorization(row, registryPath=str(tmp_path), envelope=envelope) == [
        "authorization was revoked or is stale"
    ]


def test_unconfigured_production_trust_seam_fails_closed(tmp_path):
    errors = verifyPacketAuthorization(packet(), registryPath=str(tmp_path))
    assert errors == ["independent protected human authorization is not configured; L4 remains pending"]
