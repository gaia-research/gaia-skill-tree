import io
import json
import os
import shutil
import sys
import threading
import zipfile
from pathlib import Path

import pytest

from challenge_case_support import (
    BUILDKWARGS, CASE, SyntheticVerifiedResolver, addCase, makeCase, stubReceiptDir, tamper,
)
from test_challenge_domain import opened
from gaia_cli import challengeAdmission as admission
from gaia_cli.challengeAdmission import HoldReason, Outcome
from gaia_cli.challengeDomain import VerificationReceipt, draft_challenge_id, draft_context_digest
from gaia_cli.steward.challenge_receipts import GitHubVerificationReceiptResolver, ReceiptUnavailable


def built(tmp_path, **overrides):
    root, directory = makeCase(tmp_path)
    document = admission.buildRequest(root, CASE, **{**BUILDKWARGS, **overrides})
    return root, directory, document


def events(directory):
    return [json.loads(line) for line in (directory / "events.jsonl").read_text().splitlines()]


def test_public_draft_helpers_match_open_challenge():
    challenge, _ = opened()
    draft = {"subject_id": challenge.subject_id, "claim_id": challenge.claim_id, "claim": challenge.claim,
             "behavior_id": challenge.behavior_id, "contributor_id": challenge.contributor_id,
             "contributor_notice_ref": challenge.contributor_notice_ref, "pinned_version": challenge.pinned_version,
             "pinned_sha": challenge.pinned_sha, "environment": challenge.environment,
             "test_version": challenge.test_version, "baseline": challenge.baseline, "comparator": challenge.comparator,
             "material_to_origin": challenge.material_to_origin, "created_at_utc": challenge.created_at_utc,
             "linked_challenge_id": challenge.linked_challenge_id}
    assert draft_challenge_id(draft) == challenge.challenge_id
    assert len(draft_context_digest(draft)) == 64


def test_build_request_binds_the_bundle_and_revalidates(tmp_path):
    root, directory, document = built(tmp_path)
    report = admission.inspectBundle(root, CASE)
    assert report.ok, report.errors
    assert document["challengeId"] == draft_challenge_id(document["draft"])
    assert document["receipt"]["context_digest"] == draft_context_digest(document["draft"])
    assert document["receipt"]["receipt_id"] == f"{CASE}-r1" and document["receipt"]["result"] == "verified"
    assert document["bundle"]["bundleDigest"] == report.digests["bundle"]
    transcript = json.loads((directory / "transcript.json").read_text())
    assert transcript["bundleDigest"] == report.digests["bundle"] and transcript["subject"]["genericSkillId"]
    [event] = events(directory)
    assert event["type"] == "admission-request-built" and event["prev"] == admission.GENESIS


def test_build_request_is_pinned_and_refuses_overwrite_or_bad_actors(tmp_path):
    root, directory, _ = built(tmp_path)
    with pytest.raises(admission.AdmissionError, match="already exists"):
        admission.buildRequest(root, CASE, **BUILDKWARGS)
    root2, _ = makeCase(tmp_path / "b")
    with pytest.raises(admission.AdmissionError, match="differ"):
        admission.buildRequest(root2, CASE, **{**BUILDKWARGS, "builder": "founder-login"})
    with pytest.raises(admission.AdmissionError, match="GitHub login"):
        admission.buildRequest(root2, CASE, **{**BUILDKWARGS, "verifier": "not a login"})
    assert not (root2 / "evidence/frontier-challenges" / CASE / "admission-request.json").exists()


def test_build_request_refuses_a_bundle_that_does_not_recommend_admission(tmp_path):
    root, directory = makeCase(tmp_path, positive=False)
    with pytest.raises(admission.AdmissionError, match="nothing to bind"):
        admission.buildRequest(root, CASE, **BUILDKWARGS)
    assert not (directory / "admission-request.json").exists()


def test_request_goes_stale_when_the_bundle_changes(tmp_path):
    root, directory, _ = built(tmp_path)
    tamper(directory)
    assert not admission.inspectBundle(root, CASE).ok


def test_admit_without_issuer_receipt_records_held_never_admitted(tmp_path):
    root, directory, _ = built(tmp_path)
    event = admission.admit(root, CASE, actor="tester", online=False)
    assert (event["outcome"], event["reason"]) == ("held", "trusted-issuer-unavailable")
    assert event["recordedStateIsNotAuthority"] is True
    assert "admitted" not in {e.get("outcome") for e in events(directory)}


def test_hold_reasons_are_a_closed_enum():
    assert set(admission.REASONS) == {item.value for item in HoldReason}


def test_unverifiable_receipt_is_held_not_admitted(tmp_path):
    root, _, _ = built(tmp_path)

    class Failing:
        def for_challenge(self, challengeId):
            raise ReceiptUnavailable("attestation did not verify")
    event = admission.admit(root, CASE, resolver=Failing(), online=False)
    assert (event["outcome"], event["reason"]) == ("held", "receipt-unverifiable")


def test_a_resolver_returning_a_mismatched_receipt_is_rejected_not_admitted(tmp_path):
    root, directory, _ = built(tmp_path)
    resolver = SyntheticVerifiedResolver(directory)
    resolver.receipt = VerificationReceipt(**{**resolver.receipt.__dict__, "context_digest": "f" * 64})
    event = admission.admit(root, CASE, resolver=resolver, online=False)
    assert (event["outcome"], event["reason"]) == ("held", "challenge-rejected")


def test_admitted_only_when_a_receipt_resolves_and_binds_the_bundle(tmp_path):
    root, directory, document = built(tmp_path)
    event = admission.admit(root, CASE, resolver=SyntheticVerifiedResolver(directory), online=False)
    assert event["outcome"] == "admitted" and event["challengeId"] == document["challengeId"]
    again = admission.attemptAdmission(admission.inspectBundle(root, CASE), root, online=False)
    assert again.outcome is Outcome.HELD and again.challenge is None  # the recorded event proved nothing


def test_attested_transcript_must_equal_the_bundle_transcript(tmp_path):
    """Reviewer attack a4: evidence tampered after issuance, then the unattested request re-bound."""
    root, directory, document = built(tmp_path)
    attested = SyntheticVerifiedResolver(directory)  # what the issuer signed
    tamper(directory)
    for name in ("admission-request.json", "transcript.json", "events.jsonl"):
        (directory / name).unlink()
    rebuilt = admission.buildRequest(root, CASE, **BUILDKWARGS)
    assert rebuilt["bundle"]["bundleDigest"] != document["bundle"]["bundleDigest"]
    outcome = admission.attemptAdmission(admission.inspectBundle(root, CASE), root, resolver=attested)
    assert outcome.outcome is Outcome.HELD and outcome.reason is HoldReason.BUNDLE_NOT_BOUND


def test_generic_reference_comes_from_the_bound_transcript_and_lead_edits_are_rejected(tmp_path):
    """Reviewer attack a3."""
    root, directory, _ = built(tmp_path)
    outcome = admission.attemptAdmission(admission.inspectBundle(root, CASE), root,
                                         resolver=SyntheticVerifiedResolver(directory))
    assert outcome.genericRef == json.loads((directory / "transcript.json").read_text())["subject"]["genericSkillId"]
    lead = json.loads((directory / "lead.json").read_text())
    lead["target"]["genericSkillId"] = "totally-forged-generic"
    (directory / "lead.json").write_text(json.dumps(lead, indent=2, sort_keys=True) + "\n")
    assert not admission.inspectBundle(root, CASE).ok


def test_receipt_id_must_be_the_cases_own(tmp_path):
    """Reviewer attack a2/a1: a request that borrows another case's receipt id, or a cloned case."""
    root, directory, _ = built(tmp_path)
    clone = root / admission.EVIDENCE / "replay-copy"
    shutil.copytree(directory, clone)
    assert any("name its own case id" in e for e in admission.inspectBundle(root, "replay-copy").errors)
    path = directory / "admission-request.json"
    request = json.loads(path.read_text())
    request["receipt"]["receipt_id"] = "case-a-r1"
    path.write_text(json.dumps(request, indent=2, sort_keys=True) + "\n")
    assert any(f"receipt id must be {CASE}-r" in e for e in admission.inspectBundle(root, CASE).errors)


def test_resolver_sees_only_its_own_case_and_passes_the_proof_sha(tmp_path):
    root, directory, document = built(tmp_path)
    seen = {}

    class Recorder(GitHubVerificationReceiptResolver):
        def resolve(self, receipt_id, *, expected_challenge_id, expected_proof_source_sha=None):
            seen.update(receipt=receipt_id, challenge=expected_challenge_id, proof=expected_proof_source_sha)
            return VerificationReceipt(**document["receipt"])
    case = admission.CaseResolver(Recorder(None), CASE, f"{CASE}-r1", document["proofSourceSha"])
    case.for_challenge(document["challengeId"]).resolve(f"{CASE}-r1")
    assert seen == {"receipt": f"{CASE}-r1", "challenge": document["challengeId"], "proof": document["proofSourceSha"]}
    with pytest.raises(ReceiptUnavailable, match="own receipt"):
        case.for_challenge(document["challengeId"]).resolve("another-case-r1")


def test_committed_lookup_is_private_to_the_case(tmp_path):
    root, directory, _ = built(tmp_path)
    addCase(root, tmp_path / "b", "case-b")
    for caseId in (CASE, "case-b"):
        stubReceiptDir(root / admission.EVIDENCE / caseId)
    report = admission.inspectBundle(root, CASE)
    resolver = admission.committedResolver(Path(root), report)
    scratch = resolver.keepalive.name
    assert [p.name for p in (Path(scratch) / admission.EVIDENCE).iterdir()] == [CASE]


def test_event_log_is_an_append_only_hash_chain(tmp_path):
    root, directory, _ = built(tmp_path)
    admission.admit(root, CASE, online=False)
    admission.admit(root, CASE, online=False)
    assert [e["seq"] for e in events(directory)] == [1, 2, 3]
    assert admission.readEvents(directory / "events.jsonl")[1] == []
    path = directory / "events.jsonl"
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0].replace("admission-request-built", "admission-attempt")] + lines[1:]) + "\n")
    assert admission.readEvents(path)[1]
    report = admission.inspectBundle(root, CASE)
    assert report.ok and report.eventErrors  # evidence intact, log not
    outcome = admission.attemptAdmission(report, root, resolver=SyntheticVerifiedResolver(directory))
    assert outcome.outcome is Outcome.HELD and outcome.reason is HoldReason.EVENT_LOG_BROKEN
    with pytest.raises(admission.AdmissionError, match="broken event log"):
        admission.admit(root, CASE, online=False)
    with pytest.raises(admission.AdmissionError, match="broken event log"):
        admission.appendEvent(directory, "admission-attempt", {})


def test_concurrent_appends_keep_one_chain(tmp_path):
    root, directory, _ = built(tmp_path)
    workers = [threading.Thread(target=admission.appendEvent, args=(directory, "note", {"n": i})) for i in range(12)]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    log, errors = admission.readEvents(directory / "events.jsonl")
    assert errors == [] and [e["seq"] for e in log] == list(range(1, 14))


# --- reviewer attack a6: symlinks ------------------------------------------------------

def test_symlinked_outputs_are_never_written_through(tmp_path):
    root, directory = makeCase(tmp_path)
    victim = tmp_path / "outside" / "victim.txt"
    victim.parent.mkdir()
    os.symlink(victim, directory / "transcript.json")
    with pytest.raises(admission.AdmissionError):
        admission.buildRequest(root, CASE, **BUILDKWARGS)
    assert not victim.exists()
    os.unlink(directory / "transcript.json")
    os.symlink(victim, directory / "admission-request.json")
    with pytest.raises(admission.AdmissionError):
        admission.buildRequest(root, CASE, **BUILDKWARGS)
    assert not victim.exists()


def test_symlinked_event_log_is_refused(tmp_path):
    root, directory, _ = built(tmp_path)
    (directory / "events.jsonl").unlink()
    victim = tmp_path / "outside-events.txt"
    os.symlink(victim, directory / "events.jsonl")
    with pytest.raises(admission.AdmissionError):
        admission.appendEvent(directory, "note", {})
    with pytest.raises(admission.AdmissionError):
        admission.admit(root, CASE, online=False)
    assert not victim.exists()


def test_symlinked_path_component_is_refused(tmp_path):
    root, directory = makeCase(tmp_path)
    moved = tmp_path / "moved-ledger"
    shutil.move(str(root / "evidence/frontier-challenges"), moved)
    os.symlink(moved, root / "evidence/frontier-challenges")
    with pytest.raises(admission.AdmissionError, match="symlink"):
        admission.inspectBundle(root, CASE)


# --- fetch-receipt and live admission --------------------------------------------------

class FakeTransport:
    def __init__(self, data):
        self.data, self.paths = data, []

    def getBytes(self, path):
        self.paths.append(path)
        return self.data


class FakeSource:
    def __init__(self, data):
        self.transport = FakeTransport(data)

    def fetch(self, receiptId, config):
        return {"artifactId": 77, "receiptId": receiptId}


def zipOf(names=("artifact.zip", "issuer-approval.json", "attestation.jsonl")):
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in names:
            bundle.writestr(name, b"{}")
    return stream.getvalue()


def test_fetch_receipt_writes_the_committed_files_after_offline_reverification(tmp_path):
    root, directory, _ = built(tmp_path)
    source = FakeSource(zipOf())
    event = admission.fetchReceipt(root, CASE, source=source, resolver=SyntheticVerifiedResolver(directory))
    assert event["type"] == "receipt-fetched"
    assert sorted(p.name for p in (directory / "receipt").iterdir()) == ["artifact.zip", "attestation.jsonl", "issuer-approval.json"]
    assert source.transport.paths == ["repos/gaia-research/gaia-skill-tree/actions/artifacts/77/zip"]
    with pytest.raises(admission.AdmissionError, match="already exists"):
        admission.fetchReceipt(root, CASE, source=source, resolver=SyntheticVerifiedResolver(directory))


def test_fetch_receipt_rolls_back_when_the_files_do_not_verify(tmp_path):
    root, directory, _ = built(tmp_path)

    class Failing:
        def for_challenge(self, challengeId):
            raise ReceiptUnavailable("attestation did not verify")
    with pytest.raises(admission.AdmissionError, match="does not verify offline"):
        admission.fetchReceipt(root, CASE, source=FakeSource(zipOf()), resolver=Failing())
    assert not (directory / "receipt").exists()
    with pytest.raises(admission.AdmissionError, match="not retrievable"):
        admission.fetchReceipt(root, CASE, source=FakeSource(zipOf(("artifact.zip",))))


def test_live_success_without_committed_receipt_is_not_admitted(tmp_path, monkeypatch):
    root, directory, document = built(tmp_path)
    monkeypatch.setattr(admission, "liveResolver", lambda rootPath, report: admission.CaseResolver(
        SyntheticVerifiedResolver(directory), CASE, f"{CASE}-r1", document["proofSourceSha"]))
    event = admission.admit(root, CASE, online=True)
    assert event["outcome"] == "live-verified-uncommitted"
    assert admission.attemptAdmission(admission.inspectBundle(root, CASE), root, online=False).outcome is Outcome.HELD


def test_hold_reasons_without_a_request_or_recommendation(tmp_path):
    root, directory = makeCase(tmp_path)
    assert admission.admit(root, CASE, online=False)["reason"] == "admission-request-missing"
    root2, _ = makeCase(tmp_path / "n", positive=False)
    assert admission.admit(root2, CASE, online=False)["reason"] == "not-recommended-for-admission"


def test_pinned_config_ignores_environment_overrides(monkeypatch):
    """Reviewer attack a7: GAIA_RECEIPT_* must not weaken the pins used for admission."""
    from gaia_cli.steward.challenge_receipts import CONFIG_ENV
    monkeypatch.setenv(CONFIG_ENV["requiredReviewerIds"], "999")
    monkeypatch.setenv(CONFIG_ENV["workflowBlobSha"], "a" * 40)
    config = admission.pinnedConfig()
    assert config.required_reviewer_ids == (153011150,) and config.workflow_blob_sha != "a" * 40


def test_cli_wiring_and_operator_gate(tmp_path, monkeypatch, capsys):
    from gaia_cli.main import main
    root, directory = makeCase(tmp_path, positive=False)
    monkeypatch.setenv("GAIA_OPERATOR_OVERRIDE", "1")
    argv = ["gaia", "--registry", str(root), "dev", "challenge", "build-request", "--case", CASE,
            "--verifier", "founder-login", "--builder", "builder-bot", "--notice-ref", "https://example.org/n/1",
            "--repo-root", str(root)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as refused:
        main()
    assert refused.value.code == 1
    assert "nothing to bind" in capsys.readouterr().err
    monkeypatch.delenv("GAIA_OPERATOR_OVERRIDE")
    monkeypatch.setattr("gaia_cli.authz.authorization_status",
                        lambda *a, **k: {"authorized": False, "via": "denied", "reason": "denied for test"})
    for verb in (["admit", "--case", CASE], ["fetch-receipt", CASE]):
        monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(root), "dev", "challenge", *verb])
        with pytest.raises(SystemExit) as exc:
            main()
        assert exc.value.code == 1
    assert not (directory / "events.jsonl").exists()
