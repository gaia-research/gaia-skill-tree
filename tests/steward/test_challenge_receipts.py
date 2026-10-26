import pytest

from gaia_cli.challengeDomain import VerificationReceipt
from gaia_cli.steward.challenge_receipts import (
    GitHubActionsSource,
    GitHubVerificationReceiptResolver,
    ReceiptUnavailable,
    SyntheticSourceFixture,
    TrustedReceiptConfig,
    make_artifact_archive,
    make_receipt_payload,
    probe_trusted_receipt_source,
    trusted_config_from_environment,
)


WORKFLOW_SHA = "a" * 64
CONTEXT = "b" * 64
PROOF_SOURCE_SHA = "c" * 64


def config(**overrides):
    values = dict(
        repository="gaia-research/gaia-skill-tree",
        workflow_path=".github/workflows/challenge-receipt.yml",
        workflow_ref="refs/heads/dev/yggdrasil-iv-challenge-receipts",
        workflow_sha=WORKFLOW_SHA,
        environment="challenge-receipt-review",
        required_reviewers=("maintainer",),
        prevent_self_review=True,
    )
    values.update(overrides)
    return TrustedReceiptConfig(**values)


def receipt():
    return VerificationReceipt(
        "receipt-17", CONTEXT, "d" * 64, "maintainer", "builder", "contributor",
        "passed", "reproducible-test", "runner-1", "PASS: 3/3", "e" * 64,
        "https://example.org/proof/17", "https://example.org/notices/17",
        "2026-10-26T12:00:00Z",
    )


def good_fixture(**source_changes):
    rec = receipt()
    payload = make_receipt_payload(
        rec, challenge_id="challenge-42", context_digest=CONTEXT,
        raw_transcript=b'{"cases":3,"result":"passed"}',
        notification_ref=rec.notice_ref, source_sha=PROOF_SOURCE_SHA,
    )
    archive, digest = make_artifact_archive(payload)
    source = {
        "repository": "gaia-research/gaia-skill-tree",
        "workflowPath": ".github/workflows/challenge-receipt.yml",
        "workflowRef": "refs/heads/dev/yggdrasil-iv-challenge-receipts",
        "workflowSha": WORKFLOW_SHA,
        "environment": "challenge-receipt-review",
        "runId": 111, "runAttempt": 2, "runStatus": "completed", "runConclusion": "success",
        "artifactId": 555, "artifactName": "challenge-receipt-111-2-receipt-17",
        "artifactExpired": False, "artifactRunId": 111, "artifactAttempt": 2,
        "artifactCount": 1, "builder": "builder", "contributor": "contributor",
        "reviewer": "maintainer", "requiredReviewers": ["maintainer"],
        "preventSelfReview": True, "approvalHistoryVerified": True,
        "payloadDigest": digest, "archive": archive,
    }
    source.update(source_changes)
    return SyntheticSourceFixture(source, archive)


def test_synthetic_transport_fixture_resolves_but_is_not_live_proof():
    resolver = GitHubVerificationReceiptResolver(config(), good_fixture())
    resolved = resolver.resolve("receipt-17")
    assert resolved == receipt()
    assert isinstance(resolver.source, SyntheticSourceFixture)
    # This success checks the validation contract only; SyntheticSourceFixture
    # is explicitly not an authenticated GitHub source adapter.


@pytest.mark.parametrize("changes,match", [
    ({"repository": "attacker/repo"}, "workflow source"),
    ({"workflowPath": ".github/workflows/other.yml"}, "workflow source"),
    ({"workflowRef": "refs/heads/untrusted"}, "workflow source"),
    ({"workflowSha": "f" * 64}, "workflow source"),
    ({"environment": "unprotected"}, "workflow source"),
    ({"runAttempt": 3}, "artifact is not uniquely"),
    ({"artifactRunId": 112}, "artifact is not uniquely"),
    ({"artifactAttempt": 1}, "artifact is not uniquely"),
    ({"artifactCount": 2}, "expired or ambiguous"),
    ({"artifactExpired": True}, "expired or ambiguous"),
    ({"runConclusion": "failure"}, "did not complete"),
    ({"runStatus": "in_progress"}, "did not complete"),
    ({"reviewer": "builder"}, "independent reviewer"),
    ({"reviewer": "outsider"}, "configured reviewer roster"),
    ({"builder": "maintainer"}, "independent reviewer"),
    ({"contributor": "maintainer"}, "independent reviewer"),
    ({"requiredReviewers": ["other"]}, "approval history/configuration"),
    ({"preventSelfReview": False}, "approval history/configuration"),
    ({"approvalHistoryVerified": False}, "approval history/configuration"),
    ({"payloadDigest": "0" * 64}, "payload digest mismatch"),
])
def test_provenance_mismatches_fail_closed(changes, match):
    resolver = GitHubVerificationReceiptResolver(config(), good_fixture(**changes))
    with pytest.raises(ReceiptUnavailable, match=match):
        resolver.resolve("receipt-17")


def test_actor_claims_in_artifact_cannot_override_source_actors():
    fixture = good_fixture()
    source = dict(fixture.document)
    payload = {
        "schemaVersion": 1,
        "receipt": {**receipt().__dict__, "verifier_id": "forged-reviewer"},
        "challengeId": "challenge-42", "contextDigest": CONTEXT,
        "transcript": '{"cases":3,"result":"passed"}',
        "transcriptBytesSha256": "f" * 64,
        "notificationRef": receipt().notice_ref,
        "proofSourceSha": PROOF_SOURCE_SHA,
    }
    archive, digest = make_artifact_archive(payload)
    source.update(archive=archive, payloadDigest=digest)
    with pytest.raises(ReceiptUnavailable, match="transcript digest mismatch|actor identities"):
        GitHubVerificationReceiptResolver(config(), SyntheticSourceFixture(source, archive)).resolve("receipt-17")


def test_transcript_notification_contributor_and_result_bindings_are_checked():
    fixture = good_fixture()
    source = dict(fixture.document)
    payload = {
        "schemaVersion": 1, "receipt": receipt().__dict__, "challengeId": "challenge-42",
        "contextDigest": CONTEXT, "transcript": '{"cases":3,"result":"passed"}',
        "transcriptBytesSha256": __import__("hashlib").sha256(b'{"cases":3,"result":"passed"}').hexdigest(),
        "notificationRef": "https://example.org/notices/other", "proofSourceSha": PROOF_SOURCE_SHA,
    }
    archive, digest = make_artifact_archive(payload)
    source.update(archive=archive, payloadDigest=digest)
    with pytest.raises(ReceiptUnavailable, match="notification"):
        GitHubVerificationReceiptResolver(config(), SyntheticSourceFixture(source, archive)).resolve("receipt-17")
    for changes in ({"contributor": "another"}, {"builder": "another"}):
        with pytest.raises(ReceiptUnavailable, match="actor identities"):
            GitHubVerificationReceiptResolver(config(), good_fixture(**changes)).resolve("receipt-17")


def test_invalid_receipt_ids_config_and_live_api_unavailability_are_explicit():
    with pytest.raises(ReceiptUnavailable, match="not configured"):
        GitHubVerificationReceiptResolver().resolve("receipt-17")
    with pytest.raises(ReceiptUnavailable, match="invalid"):
        GitHubVerificationReceiptResolver(config(), good_fixture()).resolve("../receipt")


def test_environment_config_missing_protected_settings_refuses():
    with pytest.raises(ReceiptUnavailable, match="not configured"):
        trusted_config_from_environment({})
    with pytest.raises(ValueError, match="prevent-self-review"):
        config(prevent_self_review=False)
    assert probe_trusted_receipt_source()["status"] == "not-configured"


def test_live_github_adapter_does_not_claim_unavailable_approval_history():
    with pytest.raises(ReceiptUnavailable, match="cannot currently prove completed protected-environment"):
        GitHubActionsSource(token="fake-token").fetch("receipt-17", config())
    probe = probe_trusted_receipt_source(config())
    assert probe["status"] == "unavailable"
    assert probe["available"] is False


def test_artifact_archive_rejects_duplicate_members_and_wrong_digest():
    import io
    import zipfile

    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as zf:
        zf.writestr("verification-receipt.json", b"{}")
        zf.writestr("extra.json", b"{}")
    source = dict(good_fixture().document)
    source.update(archive=stream.getvalue(), payloadDigest="0" * 64)
    with pytest.raises(ReceiptUnavailable, match="exactly the expected"):
        GitHubVerificationReceiptResolver(config(), SyntheticSourceFixture(source, stream.getvalue())).resolve("receipt-17")


def test_raw_transcript_and_notification_are_in_full_artifact_payload():
    value = receipt()
    payload = make_receipt_payload(
        value, challenge_id="challenge-42", context_digest=CONTEXT,
        raw_transcript=b"exact raw transcript", notification_ref=value.notice_ref,
        source_sha=PROOF_SOURCE_SHA,
    )
    assert payload["transcript"] == "exact raw transcript"
    assert payload["transcriptBytesSha256"]
    assert payload["contextDigest"] == value.context_digest
    assert payload["notificationRef"] == value.notice_ref
    assert payload["challengeId"] == "challenge-42"
    with pytest.raises(ValueError, match="notification reference"):
        make_receipt_payload(value, challenge_id="challenge-42", context_digest=CONTEXT,
                             raw_transcript=b"x", notification_ref="https://example.org/other",
                             source_sha=PROOF_SOURCE_SHA)
