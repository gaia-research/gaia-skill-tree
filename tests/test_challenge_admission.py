import json
import sys

import pytest

from challenge_case_support import BUILDKWARGS, CASE, SyntheticVerifiedResolver, makeCase, tamper
from test_challenge_domain import opened
from gaia_cli import challengeAdmission as admission
from gaia_cli.challengeDomain import draft_challenge_id, draft_context_digest
from gaia_cli.steward.challenge_receipts import ReceiptUnavailable


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
    assert document["receipt"]["verifier_id"] == "founder-login" and document["receipt"]["result"] == "verified"
    assert document["bundle"]["bundleDigest"] == report.digests["bundle"]
    assert (directory / "transcript.json").is_file()
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
    report = admission.inspectBundle(root, CASE)
    assert not report.ok


def test_admit_without_issuer_receipt_records_held_never_admitted(tmp_path):
    root, directory, _ = built(tmp_path)
    event = admission.admit(root, CASE, actor="tester", online=False)
    assert (event["outcome"], event["reason"]) == ("held", "trusted-issuer-unavailable")
    assert event["recordedStateIsNotAuthority"] is True
    assert "admitted" not in {e.get("outcome") for e in events(directory)}


@pytest.mark.parametrize("failure", [
    ReceiptUnavailable("committed receipt bundle is absent (exactly one is required)"),
    ReceiptUnavailable("attestation did not verify"),
])
def test_unverifiable_receipts_hold_with_distinct_reasons(tmp_path, failure):
    root, _, _ = built(tmp_path)

    class Failing:
        def for_challenge(self, challengeId):
            raise failure
    event = admission.admit(root, CASE, resolver=Failing(), online=False)
    assert event["outcome"] == "held"
    assert event["reason"] == ("trusted-issuer-unavailable" if "absent" in str(failure) else "receipt-unverifiable")


def test_a_resolver_returning_a_mismatched_receipt_is_rejected_not_admitted(tmp_path):
    root, directory, _ = built(tmp_path)
    resolver = SyntheticVerifiedResolver(directory)
    resolver.receipt = type(resolver.receipt)(**{**resolver.receipt.__dict__, "context_digest": "f" * 64})
    event = admission.admit(root, CASE, resolver=resolver, online=False)
    assert (event["outcome"], event["reason"]) == ("held", "challenge-rejected")


def test_admitted_only_when_a_receipt_resolves_and_the_event_is_not_authority(tmp_path):
    root, directory, document = built(tmp_path)
    event = admission.admit(root, CASE, resolver=SyntheticVerifiedResolver(directory), online=False)
    assert event["outcome"] == "admitted" and event["challengeId"] == document["challengeId"]
    assert event["recordedStateIsNotAuthority"] is True
    # The same bundle without that receipt is still held: the recorded event proves nothing.
    again = admission.attemptAdmission(admission.inspectBundle(root, CASE), root, online=False)
    assert again.outcome == "held" and again.challenge is None


def test_hold_reasons_without_a_request_or_recommendation(tmp_path):
    root, directory = makeCase(tmp_path)
    assert admission.admit(root, CASE, online=False)["reason"] == "admission-request-missing"
    root2, _ = makeCase(tmp_path / "n", positive=False)
    assert admission.admit(root2, CASE, online=False)["reason"] == "not-recommended-for-admission"


def test_event_log_is_an_append_only_hash_chain(tmp_path):
    root, directory, _ = built(tmp_path)
    admission.admit(root, CASE, online=False)
    admission.admit(root, CASE, online=False)
    log = events(directory)
    assert [e["seq"] for e in log] == [1, 2, 3]
    assert admission.readEvents(directory / "events.jsonl")[1] == []
    path = directory / "events.jsonl"
    lines = path.read_text().splitlines()
    path.write_text("\n".join([lines[0].replace("admission-request-built", "admission-attempt")] + lines[1:]) + "\n")
    assert admission.readEvents(path)[1]
    with pytest.raises(admission.AdmissionError, match="append-only chain"):
        admission.admit(root, CASE, online=False)
    with pytest.raises(admission.AdmissionError, match="broken event log"):
        admission.appendEvent(directory, "admission-attempt", {})
    assert admission.inspectBundle(root, CASE).ok is False


def test_cli_wiring_and_operator_gate(tmp_path, monkeypatch, capsys):
    from gaia_cli.main import main
    root, directory = makeCase(tmp_path, positive=False)
    monkeypatch.setenv("GAIA_OPERATOR_OVERRIDE", "1")
    argv = ["gaia", "--registry", str(root), "dev", "challenge", "build-request", "--case", CASE,
            "--verifier", "founder-login", "--builder", "builder-bot", "--notice-ref", "https://example.org/n/1", "--repo-root", str(root)]
    monkeypatch.setattr(sys, "argv", argv)
    with pytest.raises(SystemExit) as refused:
        main()
    assert refused.value.code == 1
    assert "nothing to bind" in capsys.readouterr().err
    monkeypatch.delenv("GAIA_OPERATOR_OVERRIDE")
    monkeypatch.setattr("gaia_cli.authz.authorization_status",
                        lambda *a, **k: {"authorized": False, "via": "denied", "reason": "denied for test"})
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(root), "dev", "challenge", "admit", "--case", CASE])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 1
    assert not (directory / "events.jsonl").exists()
