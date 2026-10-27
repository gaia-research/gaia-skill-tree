import hashlib
import io
import struct
import zipfile

import pytest

from gaia_cli.challengeDomain import VerificationReceipt
from tests.steward.receipt_test_ports import SyntheticReceiptPort, SyntheticTestResolver
from gaia_cli.steward.challenge_receipts import (
    AuthenticatedApprovalSource,
    GitHubActionsSource,
    GitHubVerificationReceiptResolver,
    ReceiptUnavailable,
    TrustedReceiptConfig,
    make_artifact_archive,
    make_receipt_payload,
    probe_trusted_receipt_source,
    trusted_config_from_environment,
)


WORKFLOW_SHA = "a" * 64
CONTEXT = "b" * 64
PROOF_SOURCE_SHA = "c" * 64
TRANSCRIPT = b'{"cases":3,"result":"passed"}'


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
        "receipt-17", CONTEXT, sha(TRANSCRIPT), "maintainer", "builder", "contributor",
        "passed", "reproducible-test", "runner-1", "PASS: 3/3", sha(b"PASS: 3/3"),
        "https://example.org/proof/17", "https://example.org/notices/17",
        "2026-10-26T12:00:00Z",
    )


def good_fixture(**source_changes):
    rec = receipt()
    payload = make_receipt_payload(
        rec, challenge_id="challenge-42", context_digest=CONTEXT,
        raw_transcript=TRANSCRIPT,
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
    return SyntheticReceiptPort(source, archive)


CH = dict(expected_challenge_id="challenge-42")


def resolve(fixture, receipt_id="receipt-17", cfg=None, **kw):
    return SyntheticTestResolver(cfg or config(), fixture).resolve(receipt_id, **{**CH, **kw})


def sha(data):
    return hashlib.sha256(data).hexdigest()


def test_synthetic_transport_fixture_resolves_but_is_not_live_proof():
    resolver = SyntheticTestResolver(config(), good_fixture())
    resolved = resolver.resolve("receipt-17", **CH)
    assert resolved == receipt()
    assert isinstance(resolver.source, SyntheticReceiptPort)
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
    resolver = SyntheticTestResolver(config(), good_fixture(**changes))
    with pytest.raises(ReceiptUnavailable, match=match):
        resolver.resolve("receipt-17", **CH)


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
        SyntheticTestResolver(config(), SyntheticReceiptPort(source, archive)).resolve("receipt-17", **CH)


def test_transcript_notification_contributor_and_result_bindings_are_checked():
    fixture = good_fixture()
    source = dict(fixture.document)
    payload = {
        "schemaVersion": 1, "receipt": receipt().__dict__, "challengeId": "challenge-42",
        "contextDigest": CONTEXT, "transcript": '{"cases":3,"result":"passed"}',
        "transcriptBytesSha256": sha(TRANSCRIPT),
        "notificationRef": "https://example.org/notices/other", "proofSourceSha": PROOF_SOURCE_SHA,
    }
    archive, digest = make_artifact_archive(payload)
    source.update(archive=archive, payloadDigest=digest)
    with pytest.raises(ReceiptUnavailable, match="notification"):
        SyntheticTestResolver(config(), SyntheticReceiptPort(source, archive)).resolve("receipt-17", **CH)
    for changes in ({"contributor": "another"}, {"builder": "another"}):
        with pytest.raises(ReceiptUnavailable, match="actor identities"):
            SyntheticTestResolver(config(), good_fixture(**changes)).resolve("receipt-17", **CH)


def test_invalid_receipt_ids_config_and_live_api_unavailability_are_explicit():
    with pytest.raises(ReceiptUnavailable, match="not configured"):
        GitHubVerificationReceiptResolver().resolve("receipt-17", **CH)
    with pytest.raises(ReceiptUnavailable, match="invalid"):
        SyntheticTestResolver(config(), good_fixture()).resolve("../receipt", **CH)


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
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w") as zf:
        zf.writestr("verification-receipt.json", b"{}")
        zf.writestr("extra.json", b"{}")
    source = dict(good_fixture().document)
    source.update(archive=stream.getvalue(), payloadDigest="0" * 64)
    with pytest.raises(ReceiptUnavailable, match="exactly the expected"):
        SyntheticTestResolver(config(), SyntheticReceiptPort(source, stream.getvalue())).resolve("receipt-17", **CH)


def test_raw_transcript_and_notification_are_in_full_artifact_payload():
    value = receipt()
    payload = make_receipt_payload(
        value, challenge_id="challenge-42", context_digest=CONTEXT,
        raw_transcript=TRANSCRIPT, notification_ref=value.notice_ref,
        source_sha=PROOF_SOURCE_SHA,
    )
    assert payload["transcript"] == TRANSCRIPT.decode()
    assert payload["transcriptBytesSha256"]
    assert payload["contextDigest"] == value.context_digest
    assert payload["notificationRef"] == value.notice_ref
    assert payload["challengeId"] == "challenge-42"
    with pytest.raises(ValueError, match="notification reference"):
        make_receipt_payload(value, challenge_id="challenge-42", context_digest=CONTEXT,
                             raw_transcript=b"x", notification_ref="https://example.org/other",
                             source_sha=PROOF_SOURCE_SHA)


# ---- Repair 2026-10-28 regressions -------------------------------------------------

def rebuilt(rec=None, transcript=TRANSCRIPT, challenge_id="challenge-42", source_sha=PROOF_SOURCE_SHA,
            check=True, **source_changes):
    """Fixture whose artifact packages ``rec``/``transcript`` (bypassing producer checks)."""
    rec = rec or receipt()
    payload = make_receipt_payload(receipt(), challenge_id=challenge_id, context_digest=CONTEXT,
                                   raw_transcript=TRANSCRIPT, notification_ref=rec.notice_ref,
                                   source_sha=source_sha)
    payload["receipt"] = rec.__dict__
    payload["transcript"] = transcript.decode()
    payload["transcriptBytesSha256"] = sha(transcript)
    archive, digest = make_artifact_archive(payload)
    fixture = good_fixture(archive=archive, payloadDigest=digest, **source_changes)
    return fixture


def test_git_commit_sha_accepts_40_and_64_hex_but_digests_stay_64():
    assert config(workflow_sha="a" * 40).workflow_sha == "a" * 40
    assert config(workflow_sha="a" * 64)
    for bad in ("a" * 39, "a" * 41, "A" * 40, "sha256:" + "a" * 40, "a" * 63):
        with pytest.raises(ValueError, match="pinned source SHA"):
            config(workflow_sha=bad)
    rec = receipt()
    p = make_receipt_payload(rec, challenge_id="c", context_digest=CONTEXT, raw_transcript=TRANSCRIPT,
                             notification_ref=rec.notice_ref, source_sha="b" * 40)
    assert p["proofSourceSha"] == "b" * 40
    with pytest.raises(ValueError, match="context digest|SHA-256"):
        make_receipt_payload(rec, challenge_id="c", context_digest="b" * 40, raw_transcript=TRANSCRIPT,
                             notification_ref=rec.notice_ref, source_sha="b" * 40)
    # a 40-hex workflow SHA end-to-end resolves
    cfg = config(workflow_sha="a" * 40)
    assert resolve(good_fixture(workflowSha="a" * 40), cfg=cfg) == receipt()


def test_receipt_digests_are_bound_to_transcript_and_output():
    rec = receipt()
    for field, match in (("transcript_digest", "transcript digest"), ("output_digest", "output digest")):
        forged = VerificationReceipt(**{**rec.__dict__, field: "d" * 64})
        with pytest.raises(ValueError, match=match):
            make_receipt_payload(forged, challenge_id="c", context_digest=CONTEXT, raw_transcript=TRANSCRIPT,
                                 notification_ref=rec.notice_ref, source_sha=PROOF_SOURCE_SHA)
        # a hostile packager skips the producer: resolver must refuse independently
        with pytest.raises(ReceiptUnavailable, match=match):
            resolve(rebuilt(forged))
    # substituting a different transcript while the receipt still claims the old digest
    with pytest.raises(ReceiptUnavailable, match="transcript digest"):
        resolve(rebuilt(transcript=b'{"cases":3,"result":"substituted"}'))


def test_production_resolver_refuses_synthetic_and_duck_typed_sources():
    assert GitHubVerificationReceiptResolver.AUTHENTICATED_SOURCES == (GitHubActionsSource,)
    port = good_fixture()
    with pytest.raises(ReceiptUnavailable, match="allowlisted authenticated"):
        GitHubVerificationReceiptResolver(config(), port).resolve("receipt-17", **CH)

    class Duck:
        def fetch(self, *args):
            return port.document
    with pytest.raises(ReceiptUnavailable, match="allowlisted authenticated"):
        GitHubVerificationReceiptResolver(config(), Duck()).resolve("receipt-17", **CH)

    class Sub(AuthenticatedApprovalSource):
        def fetch(self, *args):
            return port.document
    with pytest.raises(ReceiptUnavailable, match="allowlisted authenticated"):
        GitHubVerificationReceiptResolver(config(), Sub()).resolve("receipt-17", **CH)
    # the test resolver's opt-in does not extend to other subclasses either
    with pytest.raises(ReceiptUnavailable, match="allowlisted authenticated"):
        SyntheticTestResolver(config(), Sub()).resolve("receipt-17", **CH)
    # default production source is the unavailable GitHub adapter
    with pytest.raises(ReceiptUnavailable, match="cannot currently prove|authentication"):
        GitHubVerificationReceiptResolver(config()).resolve("receipt-17", **CH)
    assert not hasattr(GitHubActionsSource, "_get")


class _Raw(AuthenticatedApprovalSource):
    def __init__(self, value):
        self.value = value

    def fetch(self, *args):
        return self.value


class _RawResolver(GitHubVerificationReceiptResolver):
    AUTHENTICATED_SOURCES = (_Raw,)


def _corrupt_deflate(archive):
    data = bytearray(archive)
    start = 30 + len("verification-receipt.json")
    for k in range(start + 2, start + 12):
        data[k] ^= 0xFF
    return bytes(data)


@pytest.mark.parametrize("mutate", [
    lambda d: None,
    lambda d: [],
    lambda d: {**d, "archive": _corrupt_deflate(d["archive"])},
    lambda d: {**d, "archive": bytearray(d["archive"])},
    lambda d: {**d, "requiredReviewers": [["x"]]},
    lambda d: {**d, "reviewer": 5},
    lambda d: {**d, "payloadDigest": 7},
    lambda d: {**d, "runId": True},
])
def test_malformed_source_shapes_raise_only_receipt_unavailable(mutate):
    document = mutate(dict(good_fixture().document))
    with pytest.raises(ReceiptUnavailable):
        _RawResolver(config(), _Raw(document)).resolve("receipt-17", **CH)


def test_corrupt_deflate_stream_is_receipt_unavailable_not_zlib_error():
    document = dict(good_fixture().document)
    document["archive"] = _corrupt_deflate(document["archive"])
    with pytest.raises(ReceiptUnavailable, match="invalid receipt artifact archive"):
        resolve(SyntheticReceiptPort(document, document["archive"]))


def test_large_repetitive_transcript_round_trips_and_absolute_cap_is_the_defense():
    rec = receipt()
    big = b"A" * 1_900_000
    vr = VerificationReceipt(**{**rec.__dict__, "transcript_digest": sha(big)})
    payload = make_receipt_payload(vr, challenge_id="challenge-42", context_digest=CONTEXT,
                                   raw_transcript=big, notification_ref=rec.notice_ref,
                                   source_sha=PROOF_SOURCE_SHA)
    archive, digest = make_artifact_archive(payload)
    assert len(big) > len(archive) * 100  # would have tripped the old 100x ratio bound
    got = resolve(good_fixture(archive=archive, payloadDigest=digest))
    assert got == vr
    # oversized uncompressed member (tiny archive) is refused by the absolute cap
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("verification-receipt.json", b" " * (5 * 1024 * 1024))
    with pytest.raises(ReceiptUnavailable, match="oversized"):
        resolve(good_fixture(archive=stream.getvalue(), payloadDigest=sha(b" " * (5 * 1024 * 1024))))


def test_lying_size_header_cannot_inflate_past_the_cap():
    payload = b'{"schemaVersion":1}' + b" " * 3_000_000
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("verification-receipt.json", payload)
    raw = bytearray(stream.getvalue())
    for sig, off in ((b"PK\x03\x04", 22), (b"PK\x01\x02", 24)):
        pos = raw.find(sig)
        while pos >= 0:
            raw[pos + off:pos + off + 4] = struct.pack("<I", 100)
            pos = raw.find(sig, pos + 4)
    with pytest.raises(ReceiptUnavailable):
        resolve(good_fixture(archive=bytes(raw), payloadDigest=sha(payload)))


def test_expected_challenge_and_proof_source_must_match():
    fixture = good_fixture()
    assert resolve(fixture, expected_proof_source_sha=PROOF_SOURCE_SHA) == receipt()
    with pytest.raises(ReceiptUnavailable, match="challenge id does not match"):
        resolve(fixture, expected_challenge_id="challenge-other")
    with pytest.raises(ReceiptUnavailable, match="proof source SHA does not match"):
        resolve(fixture, expected_proof_source_sha="9" * 64)
    with pytest.raises(ReceiptUnavailable, match="proof source SHA is invalid"):
        resolve(fixture, expected_proof_source_sha="nothex")
    for bad in ("", "  ", None):
        with pytest.raises(ReceiptUnavailable, match="expected challenge id"):
            resolve(fixture, expected_challenge_id=bad)
    with pytest.raises(TypeError):  # challenge context is a required keyword
        SyntheticTestResolver(config(), fixture).resolve("receipt-17")
    # the bound adapter satisfies the one-argument VerificationReceiptResolver protocol
    bound = SyntheticTestResolver(config(), fixture).for_challenge("challenge-42", PROOF_SOURCE_SHA)
    assert bound.resolve("receipt-17") == receipt()
    with pytest.raises(ReceiptUnavailable, match="challenge id does not match"):
        SyntheticTestResolver(config(), fixture).for_challenge("challenge-x").resolve("receipt-17")


def _bomb_archive(size, header_size):
    """Deflate ``size`` bytes, then patch local+central uncompressed sizes to ``header_size``."""
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("verification-receipt.json", b" " * size)
    raw = bytearray(stream.getvalue())
    for sig, off in ((b"PK\x03\x04", 22), (b"PK\x01\x02", 24)):
        pos = raw.find(sig)
        while pos >= 0:
            raw[pos + off:pos + off + 4] = struct.pack("<I", header_size)
            pos = raw.find(sig, pos + 4)
    return bytes(raw)


@pytest.mark.parametrize("header_size", [100, 4 * 1024 * 1024])
def test_lying_header_decompression_bomb_is_bounded_not_inflated(header_size):
    import tracemalloc
    payload_size = 96 * 1024 * 1024
    archive = _bomb_archive(payload_size, header_size)
    assert len(archive) < 1024 * 1024
    tracemalloc.start()
    try:
        with pytest.raises(ReceiptUnavailable):
            resolve(good_fixture(archive=archive, payloadDigest="0" * 64))
        _, peak = tracemalloc.get_traced_memory()
    finally:
        tracemalloc.stop()
    assert peak < 16 * 1024 * 1024, f"peak {peak} bytes: payload was inflated past the cap"


def test_bounded_read_stops_at_cap_plus_one(monkeypatch):
    from gaia_cli.steward import challenge_receipts as module
    read = {"bytes": 0}
    real = zipfile.ZipExtFile.read

    def counting(self, n=-1):
        data = real(self, n)
        read["bytes"] += len(data)
        return data
    monkeypatch.setattr(zipfile.ZipExtFile, "read", counting)
    archive = _bomb_archive(64 * 1024 * 1024, 4 * 1024 * 1024)
    with pytest.raises(ReceiptUnavailable):
        resolve(good_fixture(archive=archive, payloadDigest="0" * 64))
    assert read["bytes"] <= module.MAX_PAYLOAD_BYTES + 1
