"""Synthetic security tests for the lane-A authorization boundary.

No test here claims production authorization: the one successful path replaces
only the private trust hook with an explicitly unit-only verifier stub.
"""
import copy
import hashlib
import json

import pytest

from gaia_cli.curation.authorization import (
    _digest,
    _proposalPacket,
    buildReviewPayload,
    verifyPacketAuthorization,
)


ASSESSMENT = {"receipt": "valid synthetic"}


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


def test_authorization_carriers_do_not_create_digest_cycle(tmp_path):
    original = packet()
    before = buildReviewPayload(original, registryPath=str(tmp_path))
    original["authorizationEnvelope"] = {"reviewPayloadSha256": _digest(before)}
    original["l4Resolution"]["humanReview"] = {"reviewedBy": "fabricated", "reviewedAt": "invented"}
    after = buildReviewPayload(original, registryPath=str(tmp_path))
    assert before == after


@pytest.mark.parametrize("field", ["identity", "source", "definition", "snapshot", "assessment", "route", "manifest"])
def test_every_reviewed_security_input_changes_payload_digest(tmp_path, field):
    row = packet()
    options = {"registryPath": str(tmp_path), "assessments": {row["candidateId"]: {"source": "initial"}}}
    before = buildReviewPayload(row, **options)
    if field == "identity":
        row["l4Resolution"]["named"]["skillName"] = "changed"
    elif field == "source":
        row["source"]["contentSha256"] = "b" * 64
    elif field == "definition":
        row["l4Resolution"]["generic"]["description"] = "Changed full definition."
    elif field == "snapshot":
        row["genericSnapshot"]["generics"].append({"id": "new-generic"})
    elif field == "assessment":
        options["assessments"][row["candidateId"]] = {"source": "changed"}
    elif field == "route":
        options["submissionRoute"] = "existing-intake"
        options["continuation"] = {"batchId": "old", "issue": "42"}
    elif field == "manifest":
        options.update(submissionRoute="manifest", manifestDigest="c" * 64, inventory=[row])
    assert _digest(buildReviewPayload(row, **options)) != _digest(before)


def _reviewAccounting(row):
    from gaia_cli.curation.reconciliation import canonicalJson, sha256

    source = row["source"]
    named = row["l4Resolution"]["named"]
    frozen = {
        "contractVersion": "curation-inventory-v1",
        "candidates": [{
            "candidateId": row["candidateId"],
            "namedIdentity": f"{named['contributor']}/{named['skillName']}",
            "canonicalUrl": source["canonicalUrl"],
            "sourceRevision": source["commitSha"],
            "sourceDigest": source["contentSha256"],
        }],
    }
    frozen["inventoryDigest"] = sha256(canonicalJson(frozen))
    decision = row["decision"]
    proposed = {"decision": decision["value"], "genericId": decision["genericId"]}
    # A real reconciliation report carries positive accounting: the batch is
    # accounted for, no receipt is invalid, nothing claims human approval, and
    # each row states the packet/proposal/assessment digests it observed.
    report = {
        "inventoryDigest": frozen["inventoryDigest"],
        "accounted": True,
        "humanApproved": False,
        "decisions": [{
            "candidateId": row["candidateId"], "outcome": "review-ready",
            "proposedGeneric": proposed,
            "receiptValid": True,
            "packetDigest": sha256(canonicalJson(row)),
            "packetProposalSha256": sha256(canonicalJson(_proposalPacket(row))),
            "assessmentSha256": sha256(canonicalJson(ASSESSMENT)),
        }],
    }
    return {"inventory": frozen, "reconciliation": report}


def test_forged_review_accounting_is_rejected(tmp_path):
    """A report that does not attest a real reconciliation must not be bindable.

    Found by an independent runtime review: the payload builder accepted a report
    whose receipt was marked invalid, whose batch was not accounted for, which
    claimed human approval, and whose digests had been stripped. The production
    verifier still refused it, so this was a latent accounting gap rather than an
    active bypass - but a future verifier that checks only the payload digest
    could otherwise authenticate inconsistent accounting.
    """
    row = packet()
    assessments = {row["candidateId"]: ASSESSMENT}

    notAccounted = copy.deepcopy(_reviewAccounting(row))
    notAccounted["reconciliation"]["accounted"] = False
    with pytest.raises(ValueError, match="fully accounted reconciliation"):
        buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=notAccounted,
                           assessments=assessments)

    claimsApproval = copy.deepcopy(_reviewAccounting(row))
    claimsApproval["reconciliation"]["humanApproved"] = True
    with pytest.raises(ValueError, match="must not claim human approval"):
        buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=claimsApproval,
                           assessments=assessments)

    invalidReceipt = copy.deepcopy(_reviewAccounting(row))
    invalidReceipt["reconciliation"]["decisions"][0]["receiptValid"] = False
    with pytest.raises(ValueError, match="invalid receipt"):
        buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=invalidReceipt,
                           assessments=assessments)

    for key in ("packetDigest", "packetProposalSha256", "assessmentSha256"):
        stripped = copy.deepcopy(_reviewAccounting(row))
        stripped["reconciliation"]["decisions"][0].pop(key, None)
        with pytest.raises(ValueError, match="mismatch|real assessment"):
            buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=stripped,
                               assessments=assessments)

    missingAssessment = copy.deepcopy(_reviewAccounting(row))
    missingAssessment["reconciliation"]["decisions"][0].pop("assessmentSha256", None)
    with pytest.raises(ValueError, match="assessment digest mismatch"):
        buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=missingAssessment,
                           assessments=assessments)

    noAssessmentAtAll = copy.deepcopy(_reviewAccounting(row))
    noAssessmentAtAll["reconciliation"]["decisions"][0].pop("assessmentSha256", None)
    with pytest.raises(ValueError, match="real assessment"):
        buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=noAssessmentAtAll,
                           assessments={})


def test_review_inventory_binds_exact_named_identity_and_source(tmp_path):
    row = packet()
    accounting = _reviewAccounting(row)
    assert buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=accounting,
                                assessments={row["candidateId"]: ASSESSMENT})

    badIdentity = copy.deepcopy(accounting)
    badIdentity["inventory"]["candidates"][0]["namedIdentity"] = "Owner/inventory-name"
    from gaia_cli.curation.reconciliation import canonicalJson, sha256
    frozen = badIdentity["inventory"]
    unsigned = {key: val for key, val in frozen.items() if key != "inventoryDigest"}
    frozen["inventoryDigest"] = sha256(canonicalJson(unsigned))
    badIdentity["reconciliation"]["inventoryDigest"] = frozen["inventoryDigest"]
    with pytest.raises(ValueError, match="named identity mismatch"):
        buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=badIdentity,
                                assessments={row["candidateId"]: ASSESSMENT})

    for field, value in (("sourceDigest", "b" * 64), ("sourceRevision", "different"),
                         ("canonicalUrl", "https://github.com/other/tool/blob/abc/SKILL.md")):
        badSource = copy.deepcopy(accounting)
        badSource["inventory"]["candidates"][0][field] = value
        frozen = badSource["inventory"]
        from gaia_cli.curation.reconciliation import canonicalJson, sha256
        unsigned = {key: val for key, val in frozen.items() if key != "inventoryDigest"}
        frozen["inventoryDigest"] = sha256(canonicalJson(unsigned))
        badSource["reconciliation"]["inventoryDigest"] = frozen["inventoryDigest"]
        with pytest.raises(ValueError, match="source provenance mismatch"):
            buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=badSource,
                                assessments={row["candidateId"]: ASSESSMENT})


def test_review_report_must_match_packet_decision_and_packet_digest(tmp_path):
    row = packet()
    for key, value in (("proposedGeneric", {"decision": "MAP", "genericId": "generic-other"}),
                       ("outcome", "deferred")):
        accounting = _reviewAccounting(row)
        accounting["reconciliation"]["decisions"][0][key] = value
        with pytest.raises(ValueError, match="reconciliation decision disagrees"):
            buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=accounting,
                                assessments={row["candidateId"]: ASSESSMENT})

    accounting = _reviewAccounting(row)
    accounting["reconciliation"]["decisions"][0]["packetDigest"] = "0" * 64
    with pytest.raises(ValueError, match="packet digest mismatch"):
        buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=accounting,
                                assessments={row["candidateId"]: ASSESSMENT})


def test_report_binds_assessment_digest_and_outside_top_k_mapping_is_allowed(tmp_path):
    row = packet()
    row["decision"]["genericId"] = "outside-top-k"
    row["l4Resolution"]["generic"]["id"] = "outside-top-k"
    assessment = {"receipt": "valid synthetic"}
    accounting = _reviewAccounting(row)
    accounting["reconciliation"]["decisions"][0]["assessmentSha256"] = _digest({"receipt": "wrong"})
    with pytest.raises(ValueError, match="assessment digest mismatch"):
        buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=accounting,
                           assessments={row["candidateId"]: assessment})
    accounting["reconciliation"]["decisions"][0]["assessmentSha256"] = _digest(assessment)
    payload = buildReviewPayload(row, registryPath=str(tmp_path), reviewInventory=accounting,
                                 assessments={row["candidateId"]: assessment})
    assert payload["inventory"][0]["generic"]["id"] == "outside-top-k"


def test_unconfigured_production_trust_seam_fails_closed(tmp_path):
    errors = verifyPacketAuthorization(packet(), registryPath=str(tmp_path))
    assert errors == ["independent protected human authorization is not configured; L4 remains pending"]
