import copy
import hashlib
import json
import threading
import time

import pytest

from gaia_cli.curation import fanout
from gaia_cli.curation.assessment import buildAssessment
from gaia_cli.curation.fanout import reconcileFanout, runFanout, shardFor
from gaia_cli.curation.reconciliation import canonicalJson, freezeInventory, reconcileInventory, sha256
from gaia_cli.prefill import buildGenericSnapshot

GENERIC = {
    "id": "animation-design",
    "name": "Animation Design",
    "description": "Designing motion and animation behavior in interfaces.",
    "type": "basic",
    "prerequisites": [],
}
OPTIONS = [{
    "genericId": GENERIC["id"],
    "rationale": "Exact capability match.",
    "similarity": 0.9,
    "matchTier": "strong",
}]
SOURCE_TEMPLATE = "---\nname: {name}\ndescription: {description}\n---\n\nSynthetic test skill body.\n"


@pytest.fixture
def registry(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    node = tmp_path / "registry" / "nodes" / "basic" / f"{GENERIC['id']}.json"
    node.parent.mkdir(parents=True)
    node.write_text(json.dumps(GENERIC), encoding="utf-8")
    return tmp_path


def _generic_snapshot(registry):
    snapshot = buildGenericSnapshot(registry)
    assert snapshot is not None
    snapshot["mappingOptionsSha256"] = sha256(canonicalJson(OPTIONS))
    return snapshot


def _source(index):
    name = f"Animation Skill {index}"
    description = f"A complete animation capability for deterministic test candidate {index}."
    content = SOURCE_TEMPLATE.format(name=name, description=description)
    return content, name, description


def inventory(registry, count=12, *, revision=True):
    snapshot = _generic_snapshot(registry)
    entries = []
    for index in range(count):
        cid = f"candidate-{index:02d}"
        source_content, name, description = _source(index)
        entries.append({
            "candidateId": cid,
            "namedIdentity": f"author/animation-{index:02d}",
            "sourceRevision": f"revision-{index}" if revision else None,
            "freshnessRequired": not revision,
            "sourceDigest": sha256(source_content.encode("utf-8")),
            "canonicalUrl": f"https://example.test/{index}/SKILL.md",
            "packetInput": {
                "sourceContent": source_content,
                "name": name,
                "description": description,
                "packet": {"genericSnapshot": copy.deepcopy(snapshot)},
            },
        })
    return freezeInventory(entries)


def packet(row, *, decision="MAP", identity=None, source_digest=None,
           revision=None, proposal=None, normalized=None, frontmatter=None,
           generic_snapshot=None):
    source_content = row["packetInput"]["sourceContent"]
    frozen_frontmatter = row["packetInput"]["frontmatter"]
    source = {
        "canonicalUrl": row["canonicalUrl"],
        "hostRepository": "https://example.test/repo",
        "sourceLane": "source-repository",
        "fetchedAt": "2026-01-01T00:00:00Z",
        "commitSha": row["sourceRevision"] if revision is None else revision,
        "contentSha256": row["sourceDigest"] if source_digest is None else source_digest,
        "frontmatter": copy.deepcopy(frozen_frontmatter if frontmatter is None else frontmatter),
    }
    if row["sourceRevision"] is None:
        source.pop("commitSha")
        source["revision"] = None
    decision_value = {
        "MAP": {"value": "MAP", "reasonCode": "MAP_EXISTING_GENERIC", "genericId": GENERIC["id"]},
        "NEW_GENERIC": {
            "value": "NEW_GENERIC", "reasonCode": "NEW_GENERIC_PROPOSAL",
            "proposal": proposal or {"name": "Motion", "description": "A precise motion capability definition.", "type": "basic"},
        },
        "DEFER": {"value": "DEFER", "reasonCode": "SOURCE_UNAVAILABLE"},
        "NOT_A_SKILL": {"value": "NOT_A_SKILL", "reasonCode": "NOT_A_SKILL"},
        "DUPLICATE": {"value": "DUPLICATE", "reasonCode": "EXACT_DUPLICATE"},
    }[decision]
    lifecycle = {
        "MAP": ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"],
        "NEW_GENERIC": ["discovered", "fetched", "parsed", "normalized", "deduped", "mapped", "review-ready"],
        "DEFER": ["discovered", "deferred"],
        "NOT_A_SKILL": ["discovered", "fetched", "rejected"],
        "DUPLICATE": ["discovered", "fetched", "parsed", "normalized", "deduped", "rejected"],
    }[decision]
    exact_dedupe = {"matched": False, "matchedCandidateId": None, "matchedCanonicalUrl": None}
    if decision == "DUPLICATE":
        exact_dedupe = {"matched": True, "matchedCandidateId": "known-target",
                        "matchedCanonicalUrl": row["canonicalUrl"]}
    packet_snapshot = copy.deepcopy(generic_snapshot or row["packetInput"]["packet"]["genericSnapshot"])
    if decision == "NEW_GENERIC":
        packet_snapshot["mappingOptionsSha256"] = sha256(canonicalJson([]))
    result = {
        "contractVersion": "discovery-packet-v2",
        "candidateId": row["candidateId"],
        "namedIdentity": identity or row["namedIdentity"],
        "lifecycle": lifecycle,
        "source": source,
        "normalized": copy.deepcopy(row["packetInput"]["normalized"] if normalized is None else normalized),
        "exactDedupe": exact_dedupe,
        "mappingOptions": copy.deepcopy(OPTIONS if decision == "MAP" else []),
        "genericSnapshot": packet_snapshot,
        "decision": decision_value,
        "flags": [],
    }
    return result


def receipt(row, registry, outcome="review-ready", *, packet_value=None,
            proposed=None, attempt=1, **extra):
    if packet_value is None:
        decision = {"review-ready": "MAP", "deferred": "DEFER", "rejected": "NOT_A_SKILL",
                    "proven-duplicate": "DUPLICATE"}[outcome]
        packet_value = packet(row, decision=decision)
    data = canonicalJson(packet_value)
    assessment = None if outcome == "deferred" else buildAssessment(packet_value, registryPath=registry)
    try:
        proposed_generic = proposed or _proposal_for(packet_value)
    except (KeyError, TypeError):
        proposed_generic = proposed or {"decision": "MAP", "genericId": GENERIC["id"]}
    result = {
        "candidateId": row["candidateId"], "taskId": row["taskId"],
        "attempt": attempt, "inputDigest": row["inputDigest"],
        "outputDigest": sha256(data), "packetHash": sha256(data),
        "packetBytes": data,
        "proposedGeneric": proposed_generic,
        "outcome": outcome,
    }
    if assessment is not None:
        assessment_bytes = canonicalJson(assessment)
        result["assessment"] = assessment
        result["assessmentSha256"] = sha256(assessment_bytes)
    return {**result, **extra}


def _proposal_for(packet_value):
    decision = packet_value["decision"]
    value = decision["value"]
    if value == "MAP":
        return {"decision": value, "genericId": decision["genericId"]}
    if value == "NEW_GENERIC":
        return {"decision": value, "proposal": decision["proposal"]}
    return {"decision": value}


def test_conserves_named_rows_with_shared_generic_and_retains_provenance(registry):
    frozen = inventory(registry)
    report = reconcileInventory(frozen, [receipt(row, registry) for row in frozen["candidates"]])
    assert report["accounted"] and report["counts"]["review-ready"] == 12
    assert len({row["namedIdentity"] for row in report["decisions"]}) == 12
    assert all(row["packetDigest"] == row["outputDigest"] for row in report["decisions"])
    assert all(row["taskId"] and row["attempt"] == 1 and row["proposedGeneric"] for row in report["decisions"])
    assert report["humanApproved"] is False


def test_freeze_detaches_input_and_requires_valid_identity_and_source(registry):
    content, name, description = _source(0)
    candidate = {
        "candidateId": "c", "namedIdentity": "owner/my-skill", "sourceRevision": "rev",
        "sourceDigest": sha256(content.encode()), "canonicalUrl": "https://example.test/SKILL.md",
        "packetInput": {"sourceContent": content, "name": name, "description": description,
                        "packet": {"genericSnapshot": _generic_snapshot(registry)}},
    }
    frozen = freezeInventory([candidate])
    candidate["packetInput"]["name"] = "changed"
    assert frozen["candidates"][0]["packetInput"]["normalized"] == {"name": name, "description": description}
    for identity in ("Owner/name", "owner/Bad", "owner/name/extra", "owner/"):
        with pytest.raises(ValueError, match="identity"):
            freezeInventory([{**candidate, "namedIdentity": identity}])


def test_freeze_rejects_duplicate_named_identity_and_source_digest_mismatch(registry):
    first = inventory(registry, 1)["candidates"][0]
    second = copy.deepcopy(first)
    second["candidateId"] = "candidate-other"
    with pytest.raises(ValueError, match="duplicate namedIdentity"):
        freezeInventory([first, second])
    original = _source(1)[0]
    with pytest.raises(ValueError, match="sourceContent does not match"):
        freezeInventory([{
            "candidateId": "mismatch", "namedIdentity": "owner/mismatch", "sourceRevision": "rev",
            "sourceDigest": sha256(original.encode()), "canonicalUrl": "https://example.test/SKILL.md",
            "packetInput": {"sourceContent": original + "altered\n"},
        }])


def test_unresolved_revision_requires_freshness_and_is_not_invented(registry):
    frozen = inventory(registry, 1, revision=False)
    row = frozen["candidates"][0]
    assert row["sourceRevision"] is None and row["freshnessRequired"] is True
    assert reconcileInventory(frozen, [receipt(row, registry)])["decisions"][0]["outcome"] == "review-ready"
    candidate = copy.deepcopy(row)
    candidate["freshnessRequired"] = False
    with pytest.raises(ValueError, match="freshnessRequired"):
        freezeInventory([candidate])


def test_packet_identity_source_revision_digest_and_proposal_are_bound(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    attacks = [
        packet(row, identity="other/identity"),
        packet(row, source_digest="f" * 64),
        packet(row, revision="other-revision"),
    ]
    for forged in attacks:
        decision = reconcileInventory(frozen, [receipt(row, registry, packet_value=forged)])["decisions"][0]
        assert decision["outcome"] == "deferred" and decision["reason"]
    forged = receipt(row, registry, proposed={"decision": "MAP", "genericId": "other-generic"})
    assert reconcileInventory(frozen, [forged])["decisions"][0]["outcome"] == "deferred"


def test_packet_normalized_text_or_frontmatter_cannot_differ_from_frozen_source(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    altered_text = packet(row, normalized={"name": "Forged", "description": "Forged source text."})
    altered_frontmatter = packet(row, frontmatter={"name": "Forged", "description": "Forged source text."})
    for value in (altered_text, altered_frontmatter):
        decision = reconcileInventory(frozen, [receipt(row, registry, packet_value=value)])["decisions"][0]
        assert decision["outcome"] == "deferred"
        assert "frozen source" in decision["reason"]


def test_rejects_incomplete_or_untrusted_snapshot_and_does_not_require_human_review(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    incomplete = {"contractVersion": "discovery-packet-v2", "candidateId": row["candidateId"]}
    result = reconcileInventory(frozen, [receipt(row, registry, packet_value=incomplete)])
    assert result["decisions"][0]["outcome"] == "deferred"
    assert reconcileInventory(frozen, [receipt(row, registry)])["counts"]["review-ready"] == 1


def test_outcome_must_match_actual_packet_decision(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    mismatched = receipt(row, registry, outcome="deferred", packet_value=packet(row, decision="MAP"), reason="misstated")
    result = reconcileInventory(frozen, [mismatched])
    assert result["decisions"][0]["outcome"] == "deferred"
    assert "outcome does not match" in result["decisions"][0]["reason"]


def test_review_ready_requires_real_valid_assessment_and_matching_digest(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    missing = receipt(row, registry)
    missing.pop("assessment")
    missing.pop("assessmentSha256")
    result = reconcileInventory(frozen, [missing])
    assert result["decisions"][0]["outcome"] == "deferred"
    assert result["decisions"][0]["reason"]

    invalid = receipt(row, registry)
    invalid["assessment"] = {"contractVersion": "curation-assessment-v1", "authority": "advisory"}
    invalid["assessmentSha256"] = sha256(canonicalJson(invalid["assessment"]))
    result = reconcileInventory(frozen, [invalid])
    assert result["decisions"][0]["outcome"] == "deferred"
    assert "invalid assessment" in result["decisions"][0]["reason"]

    swapped = receipt(row, registry)
    other = inventory(registry, 2)["candidates"][1]
    swapped["assessment"] = buildAssessment(packet(other), registryPath=registry)
    swapped["assessmentSha256"] = sha256(canonicalJson(swapped["assessment"]))
    result = reconcileInventory(frozen, [swapped])
    assert result["decisions"][0]["outcome"] == "deferred"


def test_report_digests_describe_content_not_artifact_bytes(registry, tmp_path):
    """A pretty-printed artifact has different bytes but identical content.

    The reconciliation report attests to CONTENT, so its digests must be the
    canonical content digests. The artifact (file-bytes) digest is the receipt's
    identity. If the report carried file bytes instead, an authorization
    payload built from the same packet would compare different digests and
    reject a perfectly legitimate batch.
    """
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    value = packet(row)
    assessment = buildAssessment(value, registryPath=registry)

    # Write the artifacts exactly as production writes them: indented JSON.
    packetPath = tmp_path / "registry-for-review" / "discovery-packets" / "tool.json"
    packetPath.parent.mkdir(parents=True, exist_ok=True)
    packetPath.write_text(json.dumps(value, indent=2), encoding="utf-8")
    assessmentPath = tmp_path / "generated-output" / "curation" / "tool.assessment.json"
    assessmentPath.parent.mkdir(parents=True, exist_ok=True)
    assessmentPath.write_text(json.dumps(assessment, indent=2), encoding="utf-8")
    assert packetPath.read_bytes() != canonicalJson(value)
    assert assessmentPath.read_bytes() != canonicalJson(assessment)

    receipt = {
        "candidateId": row["candidateId"], "taskId": row["taskId"], "attempt": 1,
        "inputDigest": row["inputDigest"],
        "outputDigest": sha256(packetPath.read_bytes()),
        "packetHash": sha256(packetPath.read_bytes()),
        "packetPath": "registry-for-review/discovery-packets/tool.json",
        "assessmentPath": "generated-output/curation/tool.assessment.json",
        "assessmentSha256": sha256(assessmentPath.read_bytes()),
        "proposedGeneric": {"decision": "MAP", "genericId": "animation-design"},
        "outcome": "review-ready",
    }
    report = reconcileInventory(frozen, [receipt], packetRoot=str(tmp_path))
    decision = report["decisions"][0]
    assert decision["outcome"] == "review-ready", decision.get("reason")
    # The report carries the canonical CONTENT digests...
    assert decision["packetDigest"] == sha256(canonicalJson(value))
    assert decision["assessmentSha256"] == sha256(canonicalJson(assessment))
    # ...and separately the ARTIFACT digests that identify the files.
    assert decision["packetArtifactSha256"] == sha256(packetPath.read_bytes())
    assert decision["assessmentArtifactSha256"] == sha256(assessmentPath.read_bytes())


def test_packet_identity_resolves_by_one_rule_everywhere(registry):
    """A packet may bind its named identity in either place; both must agree.

    Reconciliation and the authorization payload builder previously used
    different rules, so a legitimate packet could pass reconciliation and then
    be rejected as an identity mismatch when bound into a payload.
    """
    from gaia_cli.curation.reconciliation import packetNamedIdentity

    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    identity = row["namedIdentity"]

    explicit = {"namedIdentity": identity}
    assert packetNamedIdentity(explicit) == identity

    fromResolution = {"l4Resolution": {"named": {"contributor": identity.split("/")[0],
                                                 "skillName": identity.split("/")[1]}}}
    assert packetNamedIdentity(fromResolution) == identity

    # Both places present and agreeing is fine.
    both = {**explicit, **fromResolution}
    assert packetNamedIdentity(both) == identity

    # Both present and DISAGREEING is an identity change hidden in the packet.
    conflicting = {"namedIdentity": identity,
                   "l4Resolution": {"named": {"contributor": "someone-else", "skillName": "other"}}}
    assert packetNamedIdentity(conflicting) == identity

    # A MAPPING-form top-level binding is an unsupported form and must not be
    # able to assert an identity the consistency check does not compare.
    mappingForm = {"namedIdentity": {"contributor": "forged", "slug": "spoofed"},
                   "l4Resolution": {"named": {"contributor": "test-contributor", "skillName": "legit"}}}
    assert packetNamedIdentity(mappingForm) is None
    conflictingPacket = packet(row)
    conflictingPacket["namedIdentity"] = identity
    conflictingPacket["l4Resolution"] = conflicting["l4Resolution"]
    result = reconcileInventory(frozen, [receipt(row, registry, packet_value=conflictingPacket)])
    assert result["decisions"][0]["outcome"] == "deferred"
    assert "identity" in result["decisions"][0]["reason"]

    # A named block that expresses the identity two ways and disagrees with
    # itself asserts no identity at all.
    from gaia_cli.curation.reconciliation import identityFromNamedBlock

    selfContradicting = {"contributor": "test-contributor", "skillName": "legit",
                         "namedIdentity": "someone-else/other"}
    assert identityFromNamedBlock(selfContradicting) is None
    assert identityFromNamedBlock({"contributor": "owner", "skillName": "exact-name"}) == "owner/exact-name"
    assert identityFromNamedBlock({"namedIdentity": "owner/exact-name"}) == "owner/exact-name"

    # The same attack in mapping form must be refused too.
    mappingPacket = packet(row)
    mappingPacket["namedIdentity"] = {"contributor": "forged", "slug": "spoofed"}
    mappingResult = reconcileInventory(frozen, [receipt(row, registry, packet_value=mappingPacket)])
    assert mappingResult["decisions"][0]["outcome"] == "deferred"
    assert "identity" in mappingResult["decisions"][0]["reason"]


def test_exact_duplicate_requires_different_surviving_target_and_source_proof(registry):
    ordinary = inventory(registry, 2)
    first, old_target = ordinary["candidates"]
    target_candidate = {
        "candidateId": old_target["candidateId"],
        "namedIdentity": old_target["namedIdentity"],
        "sourceRevision": first["sourceRevision"],
        "sourceDigest": first["sourceDigest"],
        "canonicalUrl": first["canonicalUrl"],
        "packetInput": {
            "sourceContent": first["packetInput"]["sourceContent"],
            "packet": copy.deepcopy(first["packetInput"]["packet"]),
        },
    }
    frozen = freezeInventory([{
        "candidateId": first["candidateId"], "namedIdentity": first["namedIdentity"],
        "sourceRevision": first["sourceRevision"], "sourceDigest": first["sourceDigest"],
        "canonicalUrl": first["canonicalUrl"], "packetInput": copy.deepcopy(first["packetInput"]),
    }, target_candidate])
    first, target = frozen["candidates"]
    self_proof = {"targetNamedIdentity": first["namedIdentity"], "canonicalUrl": first["canonicalUrl"]}
    assert reconcileInventory(frozen, [receipt(first, registry, "proven-duplicate", duplicateProof=self_proof)])["decisions"][0]["outcome"] == "deferred"
    unknown = {"targetNamedIdentity": "author/not-present", "canonicalUrl": first["canonicalUrl"]}
    assert reconcileInventory(frozen, [receipt(first, registry, "proven-duplicate", duplicateProof=unknown)])["decisions"][0]["outcome"] == "deferred"
    valid = {"targetNamedIdentity": target["namedIdentity"], "canonicalUrl": first["canonicalUrl"]}
    target_deferred = receipt(target, registry, "deferred", reason="source unavailable")
    duplicate = receipt(first, registry, "proven-duplicate", duplicateProof=valid)
    decisions = reconcileInventory(frozen, [duplicate, target_deferred])["decisions"]
    assert [item["outcome"] for item in decisions] == ["deferred", "deferred"]
    assert "target" in decisions[0]["reason"]
    surviving = receipt(target, registry)
    proven = reconcileInventory(frozen, [duplicate, surviving])
    assert proven["decisions"][0]["outcome"] == "proven-duplicate"
    assert proven["decisions"][0]["duplicateProof"] == valid


def test_unknown_receipts_and_competing_attempts_are_reported_order_independently(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    first, second = receipt(row, registry), receipt(row, registry, attempt=2)
    unknown = receipt({**row, "candidateId": "unknown"}, registry)
    one = reconcileInventory(frozen, [first, second, unknown])
    two = reconcileInventory(frozen, [unknown, second, first])
    assert one == two
    assert one["unknownReceipts"][0]["reason"] == "receipt references unknown candidate"
    assert one["decisions"][0]["outcome"] == "deferred"
    assert "multiple attempts" in one["decisions"][0]["reason"]


def test_conflicting_generic_definitions_defer_all_regardless_order(registry):
    frozen = inventory(registry, 2)
    proposals = [
        {"name": "Motion", "description": "A precise motion capability definition.", "type": "basic"},
        {"name": "Motion", "description": "A different motion capability definition.", "type": "basic"},
    ]
    receipts = []
    for row, proposal in zip(frozen["candidates"], proposals):
        value = packet(row, decision="NEW_GENERIC", proposal=proposal)
        receipts.append(receipt(row, registry, proposed={"decision": "NEW_GENERIC", "proposal": proposal}, packet_value=value))
    one = reconcileInventory(frozen, receipts)
    two = reconcileInventory(frozen, reversed(receipts))
    assert one == two
    assert [row["outcome"] for row in one["decisions"]] == ["deferred", "deferred"]
    assert all("conflicting full definitions" in row["reason"] for row in one["decisions"])


def test_missing_receipts_are_deferred_without_loss(registry):
    report = reconcileInventory(inventory(registry), [])
    assert report["accounted"] and report["counts"]["deferred"] == 12
    assert all(row["reason"] for row in report["decisions"])


def test_deferred_requires_reason_but_not_assessment(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    empty_reason = receipt(row, registry, "deferred", reason="  ")
    result = reconcileInventory(frozen, [empty_reason])
    assert result["decisions"][0]["outcome"] == "deferred"
    assert "explicit reason" in result["decisions"][0]["reason"]
    valid = receipt(row, registry, "deferred", reason="Upstream source could not be fetched.")
    assert "assessment" not in valid and "assessmentSha256" not in valid
    report = reconcileInventory(frozen, [valid])
    assert report["decisions"][0]["receiptValid"] is True
    assert report["decisions"][0]["outcome"] == "deferred"


def test_fanout_retries_worker_exceptions_and_is_completion_order_independent(registry):
    frozen = inventory(registry, 4)
    calls = {}

    def worker(row, attempt):
        cid = row["candidateId"]
        calls[cid] = calls.get(cid, 0) + 1
        if cid.endswith("02") and attempt == 1:
            raise RuntimeError("transient")
        return receipt(row, registry, attempt=attempt)

    result = runFanout(frozen, worker, maxWorkers=3, maxAttempts=2, packetRoot=str(registry))
    assert len(result["receipts"]) == 4 and calls["candidate-02"] == 2
    assert reconcileInventory(frozen, result["receipts"], packetRoot=str(registry))["counts"]["review-ready"] == 4
    assert result["attemptBudget"] == 8 and result["budgetUnit"] == "candidate-tasks"


def test_attempt_one_then_two_rejects_worker_receipt_claiming_attempt_one_again(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    calls = []

    def worker(task, attempt):
        calls.append(attempt)
        if attempt == 1:
            raise RuntimeError("retry this worker exception")
        return receipt(task, registry, attempt=1)

    result = runFanout(frozen, worker, maxAttempts=2, packetRoot=str(registry))
    assert calls == [1, 2]
    assert result["receipts"] == []
    assert "binding mismatch" in result["errors"][row["candidateId"]]


def test_deterministically_invalid_receipt_is_not_retried_and_errors_reconcile(registry):
    frozen = inventory(registry, 1)
    calls = []

    def worker(row, attempt):
        calls.append(attempt)
        return receipt(row, registry, packet_value={"contractVersion": "discovery-packet-v2", "candidateId": row["candidateId"]}, attempt=attempt)

    result = runFanout(frozen, worker, maxAttempts=4, packetRoot=str(registry))
    assert calls == [1]
    assert reconcileFanout(frozen, result, packetRoot=str(registry))["decisions"][0]["reason"]


def test_budget_counts_candidate_tasks_and_missing_worker_errors_survive(registry):
    frozen = inventory(registry, 12)
    result = runFanout(frozen, lambda row, attempt: receipt(row, registry, attempt=attempt), maxTasks=5, maxAttempts=3, packetRoot=str(registry))
    assert len(result["receipts"]) == 5
    assert result["attemptBudget"] == 15
    report = reconcileFanout(frozen, result, packetRoot=str(registry))
    assert report["counts"]["deferred"] == 7
    assert all("budget exhausted" in row["reason"] for row in report["decisions"] if row["outcome"] == "deferred")
    missing = runFanout(inventory(registry, 2), None)
    assert all(row["reason"] == "worker unavailable" for row in reconcileFanout(inventory(registry, 2), missing)["decisions"])


def test_prior_deferred_receipt_is_retained_by_default_and_reopened_on_request(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    prior = receipt(row, registry, "deferred", reason="temporary source failure")
    # A plain DEFER has no assessment: it asserts no reviewed decision, so
    # Fanout must retain it rather than demanding artifacts that cannot
    # truthfully exist for a candidate whose source could not be fetched.
    assert "assessment" not in prior and "assessmentBytes" not in prior
    seen = []

    def worker(task, attempt):
        seen.append((task["candidateId"], attempt))
        return receipt(task, registry, attempt=attempt)

    retained = runFanout(frozen, worker, priorReceipts=[prior], packetRoot=str(registry))
    assert retained["receipts"][0]["outcome"] == "deferred"
    assert retained["dispatched"] == 0 and seen == []
    reopened = runFanout(frozen, worker, priorReceipts=[prior], retryDeferred=True, packetRoot=str(registry))
    assert seen == [(row["candidateId"], 1)]
    assert reconcileInventory(frozen, reopened["receipts"], packetRoot=str(registry))["counts"]["review-ready"] == 1


def test_prior_receipt_attempts_and_receipt_order_conflict_are_deterministic(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    one, two = receipt(row, registry), receipt(row, registry, attempt=2)
    assert reconcileInventory(frozen, [one, two]) == reconcileInventory(frozen, [two, one])

    def worker(task, attempt):
        return receipt(task, registry, attempt=attempt)

    first_order = runFanout(frozen, worker, priorReceipts=[one, two], packetRoot=str(registry))
    reversed_order = runFanout(frozen, worker, priorReceipts=[two, one], packetRoot=str(registry))
    assert first_order == reversed_order
    assert first_order["receipts"] == [one, two]
    assert first_order["dispatched"] == 0
    assert "conflicting receipts" in first_order["priorReceiptErrors"][row["candidateId"]]
    report = reconcileFanout(frozen, first_order, packetRoot=str(registry))
    decision = report["decisions"][0]
    assert decision["outcome"] == "deferred" and decision["receiptValid"] is False
    assert "conflicting receipts" in decision["reason"]


def test_single_valid_prior_receipt_is_retained_and_suppresses_dispatch(registry):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    prior = receipt(row, registry)
    calls = []

    def worker(task, attempt):
        calls.append(task["candidateId"])
        return receipt(task, registry, attempt=attempt)

    result = runFanout(frozen, worker, priorReceipts=[prior], packetRoot=str(registry))
    assert result["receipts"] == [prior]
    assert result["dispatched"] == 0 and calls == []
    assert reconcileFanout(frozen, result, packetRoot=str(registry))["decisions"][0]["outcome"] == "review-ready"


def test_unknown_prior_receipt_remains_visible_in_final_report(registry):
    frozen = inventory(registry, 1)
    unknown_row = {**frozen["candidates"][0], "candidateId": "unknown-candidate"}
    unknown = receipt(unknown_row, registry)
    result = runFanout(frozen, None, priorReceipts=[unknown], packetRoot=str(registry))
    report = reconcileFanout(frozen, result, packetRoot=str(registry))
    assert report["unknownReceipts"] == [{"candidateId": "unknown-candidate", "reason": "receipt references unknown candidate"}]
    assert report["decisions"][0]["outcome"] == "deferred"


def test_timeout_late_worker_cannot_change_reconciled_snapshot(registry, monkeypatch):
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    late = []
    started = threading.Event()
    gate = threading.Event()
    completed = threading.Event()
    clock_started = threading.Event()
    real_monotonic = time.monotonic
    clock_origin = []
    real_executor = fanout.concurrent.futures.ThreadPoolExecutor

    class WorkerEntryExecutor(real_executor):
        def submit(self, *args, **kwargs):
            future = super().submit(*args, **kwargs)
            assert started.wait(5), "worker did not enter before submit returned"
            return future

    monkeypatch.setattr(fanout.concurrent.futures, "ThreadPoolExecutor", WorkerEntryExecutor)

    class WorkerStartClock:
        @staticmethod
        def monotonic():
            # Exclude executor scheduling from the timeout interval, then use
            # real elapsed time once the worker is actually in flight.
            if not clock_started.is_set():
                return 0.0
            return real_monotonic() - clock_origin[0]

    monkeypatch.setattr(fanout, "time", WorkerStartClock)

    def worker(task, attempt):
        started.set()
        clock_origin.append(real_monotonic())
        clock_started.set()
        gate.wait()
        late_receipt = receipt(row, registry, attempt=attempt)
        late_path = registry / "late-worker-packet.json"
        late_path.write_bytes(late_receipt.pop("packetBytes"))
        late_receipt["packetPath"] = "late-worker-packet.json"
        late.append(late_receipt)
        completed.set()
        return late_receipt

    try:
        result = runFanout(frozen, worker, timeoutSeconds=0.02, packetRoot=str(registry))
        assert started.is_set(), "the worker must have entered before checking timeout protection"
        assert "timeout" in result["errors"][row["candidateId"]]
        before = reconcileFanout(frozen, result, packetRoot=str(registry))
        before_bytes = canonicalJson(before)
        assert before["decisions"][0]["outcome"] == "deferred"
    finally:
        gate.set()

    assert completed.wait(5), "the released late worker must finish"
    late_path = registry / "late-worker-packet.json"
    assert late_path.is_file(), "the late worker's packet artifact must be written"
    assert late[0]["packetPath"] == "late-worker-packet.json"
    assert canonicalJson(reconcileFanout(frozen, result, packetRoot=str(registry))) == before_bytes

    # Reconcile the completed late artifact directly: validity and SHA checks
    # do not need a second executor run or a startup-time assumption.
    accepted = reconcileFanout(frozen, {"receipts": [late[0]]}, packetRoot=str(registry))
    assert accepted["decisions"][0]["outcome"] == "review-ready"
    assert accepted["decisions"][0]["receiptValid"] is True

    corrupt = dict(late[0], outputDigest="0" * 64)
    rejected = reconcileFanout(frozen, {"receipts": [corrupt]}, packetRoot=str(registry))
    assert rejected["decisions"][0]["outcome"] == "deferred"
    assert "hash" in rejected["decisions"][0]["reason"]


def test_timeout_is_one_wall_clock_budget_for_the_whole_run(registry):
    frozen = inventory(registry, 2)
    calls = []

    def worker(row, attempt):
        calls.append(row["candidateId"])
        time.sleep(0.12)
        return receipt(row, registry, attempt=attempt)

    result = runFanout(frozen, worker, maxWorkers=1, timeoutSeconds=0.18, packetRoot=str(registry))
    assert len(calls) == 2
    assert len(result["receipts"]) == 1
    assert len(result["errors"]) == 1
    assert "timeout" in next(iter(result["errors"].values()))


def test_inventory_digest_detects_mutation(registry):
    frozen = inventory(registry, 1)
    frozen["candidates"][0]["namedIdentity"] = "changed/name"
    with pytest.raises(ValueError, match="inventory digest"):
        reconcileInventory(frozen, [])


def test_stable_sharding_and_safe_packet_path(registry, tmp_path):
    ids = [f"candidate-{index}" for index in range(20)]
    assert {cid: shardFor(cid, 7) for cid in ids} == {cid: shardFor(cid, 7) for cid in reversed(ids)}
    frozen = inventory(registry, 1)
    row = frozen["candidates"][0]
    outside = tmp_path / "escape.json"
    outside.write_bytes(canonicalJson(packet(row)))
    bad = receipt(row, registry)
    bad.pop("packetBytes")
    bad["packetPath"] = "../escape.json"
    result = reconcileInventory(frozen, [bad], packetRoot=str(registry))
    assert result["decisions"][0]["outcome"] == "deferred"
    assert "safe relative path" in result["decisions"][0]["reason"]
