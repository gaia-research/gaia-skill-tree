"""Challenge-receipt issuer tests (EPIC #2189).

Everything here is SYNTHETIC unless stated: fake transports, fake attestation verifiers,
synthetic attestation/trusted-root bytes. The only recorded artifact is
``fixtures/gh-attestation-verify-recorded.json`` (real ``gh attestation verify`` output
from a public cli/cli release, used for shape parsing only). Passing here proves the
verification contract; it is not live issuer evidence. No network or ``gh`` call is made.
"""
from __future__ import annotations

import dataclasses
import hashlib
import importlib.util
import io
import json
import os
import re
import shutil
import subprocess
import types
import zipfile
from pathlib import Path

import pytest

from gaia_cli.challengeDomain import VerificationReceipt
from gaia_cli.steward import challenge_receipts as cr
from gaia_cli.steward.challenge_receipts import (
    CommittedAttestedReceiptSource,
    GhAttestationVerifier,
    GitHubActionsSource,
    GitHubVerificationReceiptResolver,
    ReceiptMisconfigured,
    ReceiptUnavailable,
    identityFromGhResult,
    loadTrustedConfig,
    probe_trusted_receipt_source,
)
from tests.steward.receipt_test_ports import SyntheticReceiptPort

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github/workflows/challenge-receipt-issuer.yml"
CONFIG_FILE = ROOT / "src/gaia_cli/data/trust/challenge-receipt-issuer.json"
RECORDED = Path(__file__).parent / "fixtures/gh-attestation-verify-recorded.json"

COMMITTED = loadTrustedConfig(env={})
TAG = "challenge-receipt/case-r1"
REF = f"refs/tags/{TAG}"
RECEIPT_ID = "receipt-17"
CHALLENGE = "challenge-42"
CONTEXT = "b" * 64
PROOF_SHA = "c" * 40
TRANSCRIPT = b'{"cases":3,"result":"passed"}'
RUN_ID = 4242
REVIEWER = {"id": 153011150, "login": "mbtiongson1"}


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def approval(state="approved", user=REVIEWER, env=COMMITTED.environment):
    return {"state": state, "comment": "", "user": dict(user), "environments": [{"id": 1, "name": env}]}


# ---- git, bundle and fake-collaborator builders --------------------------------------------

def git(repo: Path, *args: str) -> str:
    done = subprocess.run(
        ["git", "-c", "user.name=t", "-c", "user.email=t@example.org", "-c", "commit.gpgsign=false",
         "-C", str(repo), *args], capture_output=True, text=True, check=True)
    return done.stdout.strip()


@pytest.fixture
def repo(tmp_path):
    """A real git repo whose commit A carries the issuer workflow; B is a later descendant."""
    root = tmp_path / "repo"
    (root / ".github/workflows").mkdir(parents=True)
    git(root.parent, "init", "-q", str(root))
    workflow = root / COMMITTED.workflow_path
    workflow.write_text("name: synthetic issuer workflow for tests\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "A")
    commitA = git(root, "rev-parse", "HEAD")
    blob = git(root, "rev-parse", f"HEAD:{COMMITTED.workflow_path}")
    (root / "later.txt").write_text("later\n")
    git(root, "add", "-A")
    git(root, "commit", "-q", "-m", "B")
    return types.SimpleNamespace(root=root, sha=commitA, blob=blob)


@pytest.fixture
def cfg(repo):
    return dataclasses.replace(COMMITTED, workflow_blob_sha=repo.blob)


def loadScript():
    spec = importlib.util.spec_from_file_location("buildChallengeReceipt", ROOT / "scripts/buildChallengeReceipt.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def writeRequest(root: Path, *, verifier=REVIEWER["login"], caseId="case"):
    caseDir = root / "evidence/frontier-challenges" / caseId
    caseDir.mkdir(parents=True, exist_ok=True)
    (caseDir / "transcript.json").write_bytes(TRANSCRIPT)
    receipt = VerificationReceipt(
        RECEIPT_ID, CONTEXT, sha(TRANSCRIPT), verifier, "builder-agent", "contributor-x", "passed",
        "reproducible-test", "runner-1", "PASS: 3/3", sha(b"PASS: 3/3"),
        "https://example.org/proof/17", "https://example.org/notices/17", "2026-10-26T12:00:00Z")
    (caseDir / "admission-request.json").write_text(json.dumps({
        "schemaVersion": 1, "caseId": caseId, "challengeId": CHALLENGE, "contextDigest": CONTEXT,
        "proofSourceSha": PROOF_SHA, "transcriptPath": "transcript.json",
        "receipt": dataclasses.asdict(receipt)}))
    return receipt


def makeBundle(tmp_path, repo, *, approvals=None, verifier=REVIEWER["login"], attempt=1, sealOverrides=None):
    """Run the real build + seal script into a bundle dir; attestation files are SYNTHETIC."""
    script = loadScript()
    work = tmp_path / "work"
    writeRequest(work, verifier=verifier)
    out = tmp_path / "out"
    build = script.buildBundle(work, TAG, out)
    sealed = script.sealBundle(
        out, TAG, [approval()] if approvals is None else approvals, repository=COMMITTED.repository,
        sourceSha=repo.sha, runId=RUN_ID, runAttempt=attempt, actor="mbtiongson1",
        expectedDigest=build["artifactSha256"])
    if sealOverrides:
        sealed.update(sealOverrides)
        (out / "issuer-approval.json").write_text(json.dumps(sealed))
    (out / "attestation.jsonl").write_bytes(b'{"synthetic":"sigstore bundle"}\n')
    (out / "trusted_root.jsonl").write_bytes(b'{"synthetic":"trusted root"}\n')
    return out


def bundleFiles(out: Path) -> dict[str, bytes]:
    return {name: (out / name).read_bytes() for name in cr.BUNDLE_LIMITS}


def zipOf(files: dict[str, bytes]) -> bytes:
    stream = io.BytesIO()
    with zipfile.ZipFile(stream, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name, data in files.items():
            bundle.writestr(name, data)
    return stream.getvalue()


class FakeVerifier:
    """SYNTHETIC attestation verifier: reports a chosen identity for whatever bytes it is given."""

    def __init__(self, sha_, **overrides):
        self.sha, self.overrides, self.calls = sha_, overrides, []

    def __call__(self, subject, bundle, trustedRoot, config):
        self.calls.append((Path(subject).name, trustedRoot))
        identity = {"repository": config.repository, "workflowPath": config.workflow_path, "ref": REF,
                    "sourceSha": self.sha, "trigger": "push", "runnerEnvironment": "github-hosted",
                    "runId": RUN_ID, "runAttempt": 1, "subjectSha256": sha(Path(subject).read_bytes())}
        identity.update(self.overrides)
        return identity


class FakeTransport:
    """SYNTHETIC GitHub API: serves canned JSON/bytes keyed by path substring."""

    def __init__(self, responses):
        self.responses, self.requests = responses, []

    def _find(self, path):
        self.requests.append(path)
        for key, value in self.responses.items():
            if key in path:
                if isinstance(value, Exception):
                    raise value
                return value
        raise ReceiptUnavailable(f"no canned response for {path}")

    def getJson(self, path):
        return self._find(path)

    def getBytes(self, path):
        return self._find(path)


def liveTransport(files, sha_, *, listing=None, run=None, approvals=None, zipBytes=None):
    name = f"challenge-receipt-{RECEIPT_ID}"
    baseRun = {"id": RUN_ID, "run_attempt": 1, "path": COMMITTED.workflow_path, "event": "push",
               "head_sha": sha_, "head_branch": TAG, "status": "completed", "conclusion": "success",
               "repository": {"full_name": COMMITTED.repository},
               "head_repository": {"full_name": COMMITTED.repository}}
    baseRun.update(run or {})
    return FakeTransport({
        "actions/artifacts?name=": listing if listing is not None else {
            "total_count": 1, "artifacts": [{"id": 555, "name": name, "expired": False,
                                             "workflow_run": {"id": RUN_ID}}]},
        f"actions/runs/{RUN_ID}/approvals": [approval()] if approvals is None else approvals,
        f"actions/runs/{RUN_ID}": baseRun,
        "actions/artifacts/555/zip": zipBytes if zipBytes is not None else zipOf(files),
    })


def resolveOnline(cfg, repo, files, **transportKw):
    verifier = FakeVerifier(repo.sha)
    source = GitHubActionsSource(transport=liveTransport(files, repo.sha, **transportKw),
                                 verifier=verifier, git=cr.LocalGit(repo.root))
    resolver = GitHubVerificationReceiptResolver(cfg, source)
    return resolver.resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE, expected_proof_source_sha=PROOF_SHA), \
        verifier, source


def commitBundle(repoRoot: Path, out: Path, caseId="case"):
    target = repoRoot / "evidence/frontier-challenges" / caseId / "receipt"
    target.mkdir(parents=True, exist_ok=True)
    for name in cr.BUNDLE_LIMITS:
        (target / name).write_bytes((out / name).read_bytes())
    return target


def resolveOffline(cfg, repo, *, verifier=None, git_=None):
    source = CommittedAttestedReceiptSource(
        repo.root, verifier=verifier or FakeVerifier(repo.sha), git=git_)
    return GitHubVerificationReceiptResolver(cfg, source).resolve(
        RECEIPT_ID, expected_challenge_id=CHALLENGE, expected_proof_source_sha=PROOF_SHA)


# ==== 1. online path ============================================================================

def test_online_path_resolves_and_cross_checks_live_run_artifact_and_approvals(tmp_path, repo, cfg):
    files = bundleFiles(makeBundle(tmp_path, repo))
    receipt, verifier, source = resolveOnline(cfg, repo, files)
    assert receipt.receipt_id == RECEIPT_ID and receipt.verifier_id == "mbtiongson1"
    # online: gh obtains the trusted root itself; the bundle's copy is never trusted
    assert {name: root for name, root in verifier.calls} == {"artifact.zip": None, "issuer-approval.json": None}
    paths = source.transport.requests
    assert any("actions/artifacts?name=challenge-receipt-receipt-17" in path for path in paths)
    assert any(path.endswith(f"actions/runs/{RUN_ID}/approvals") for path in paths)


@pytest.mark.parametrize("kwargs,match", [
    ({"listing": {"total_count": 0, "artifacts": []}}, "absent or ambiguous"),
    ({"listing": {"total_count": 2, "artifacts": [{}, {}]}}, "absent or ambiguous"),
    ({"listing": [1]}, "absent or ambiguous"),
    ({"listing": {"total_count": 1, "artifacts": [{"id": 555, "name": "challenge-receipt-other",
                                                   "workflow_run": {"id": RUN_ID}}]}}, "malformed"),
    ({"listing": {"total_count": 1, "artifacts": [{"id": 555, "name": "challenge-receipt-receipt-17",
                                                   "expired": True, "workflow_run": {"id": RUN_ID}}]}},
     "expired or ambiguous"),
    ({"run": {"conclusion": "failure"}}, "did not complete successfully"),
    ({"run": {"status": "in_progress"}}, "did not complete successfully"),
    ({"run": {"path": ".github/workflows/other.yml"}}, "live workflow run does not match"),
    ({"run": {"event": "workflow_dispatch"}}, "live workflow run does not match"),
    ({"run": {"head_sha": "d" * 40}}, "live workflow run does not match"),
    ({"run": {"head_branch": "challenge-receipt/other-r9"}}, "live workflow run does not match"),
    ({"run": {"run_attempt": 2}}, "live workflow run does not match"),
    ({"run": {"head_repository": {"full_name": "attacker/fork"}}}, "live workflow run does not match"),
    ({"approvals": []}, "no environment approval"),
    ({"approvals": [approval(user={"id": 999, "login": "other"})]}, "configured reviewer roster"),
    ({"approvals": [approval(), approval("rejected")]}, "rejected"),
    ({"approvals": [approval(), approval()]}, "exactly one approved"),
    ({"zipBytes": b"not a zip"}, "invalid receipt bundle"),
])
def test_online_live_state_mismatches_fail_closed(tmp_path, repo, cfg, kwargs, match):
    files = bundleFiles(makeBundle(tmp_path, repo))
    with pytest.raises(ReceiptUnavailable, match=match):
        resolveOnline(cfg, repo, files, **kwargs)


def test_online_transport_failure_is_receipt_unavailable(tmp_path, repo, cfg):
    transport = FakeTransport({"actions/artifacts?name=": ReceiptUnavailable("GitHub API read failed")})
    source = GitHubActionsSource(transport=transport, verifier=FakeVerifier(repo.sha), git=cr.LocalGit(repo.root))
    with pytest.raises(ReceiptUnavailable, match="GitHub API read failed"):
        GitHubVerificationReceiptResolver(cfg, source).resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE)


# ==== 2. offline path ===========================================================================

def test_offline_path_resolves_a_committed_bundle_built_by_the_real_script(tmp_path, repo, cfg):
    out = makeBundle(tmp_path, repo)
    commitBundle(repo.root, out)
    verifier = FakeVerifier(repo.sha)
    receipt = resolveOffline(cfg, repo, verifier=verifier)
    assert receipt.receipt_id == RECEIPT_ID
    # offline: the committed trusted root is what verification runs against
    assert {name: root.name for name, root in verifier.calls} == {
        "artifact.zip": "trusted_root.jsonl", "issuer-approval.json": "trusted_root.jsonl"}
    # and the bound resolver binds challenge id and proof source like any other source
    bound = GitHubVerificationReceiptResolver(
        cfg, CommittedAttestedReceiptSource(repo.root, verifier=verifier)).for_challenge(CHALLENGE, PROOF_SHA)
    assert bound.resolve(RECEIPT_ID) == receipt
    with pytest.raises(ReceiptUnavailable, match="challenge id does not match"):
        GitHubVerificationReceiptResolver(
            cfg, CommittedAttestedReceiptSource(repo.root, verifier=verifier)).for_challenge("other").resolve(RECEIPT_ID)


def test_offline_bundle_structure_failures_fail_closed(tmp_path, repo, cfg):
    out = makeBundle(tmp_path, repo)
    with pytest.raises(ReceiptUnavailable, match="absent or ambiguous"):
        resolveOffline(cfg, repo)  # nothing committed
    target = commitBundle(repo.root, out)
    (target / "trusted_root.jsonl").unlink()
    with pytest.raises(ReceiptUnavailable, match="missing, linked, or oversized"):
        resolveOffline(cfg, repo)
    (target / "trusted_root.jsonl").symlink_to(out / "trusted_root.jsonl")
    with pytest.raises(ReceiptUnavailable, match="missing, linked, or oversized"):
        resolveOffline(cfg, repo)
    (target / "trusted_root.jsonl").unlink()
    (target / "trusted_root.jsonl").write_bytes(b"x" * (cr.BUNDLE_LIMITS["trusted_root.jsonl"] + 1))
    with pytest.raises(ReceiptUnavailable, match="missing, linked, or oversized"):
        resolveOffline(cfg, repo)
    # the same receipt committed under two cases is ambiguous, not "first wins"
    (target / "trusted_root.jsonl").write_bytes((out / "trusted_root.jsonl").read_bytes())
    commitBundle(repo.root, out, caseId="case-dup")
    with pytest.raises(ReceiptUnavailable, match="absent or ambiguous"):
        resolveOffline(cfg, repo)


def test_tampered_committed_bytes_never_resolve(tmp_path, repo, cfg):
    out = makeBundle(tmp_path, repo)
    target = commitBundle(repo.root, out)
    good = bundleFiles(out)
    # a different (valid) receipt archive swapped in: sealed artifact digest no longer matches
    other = (tmp_path / "other")
    writeRequest(other)
    requestFile = other / "evidence/frontier-challenges/case/admission-request.json"
    requestFile.write_text(requestFile.read_text().replace(CHALLENGE, "challenge-other"))
    swapped = loadScript().buildBundle(other, TAG, tmp_path / "other-out")
    assert swapped["artifactSha256"] != sha(good["artifact.zip"])
    (target / "artifact.zip").write_bytes((tmp_path / "other-out/artifact.zip").read_bytes())
    with pytest.raises(ReceiptUnavailable, match="sealed approval does not bind"):
        resolveOffline(cfg, repo)
    # a forged sealed approval: attestation (the verifier) must reject the unattested bytes
    (target / "artifact.zip").write_bytes(good["artifact.zip"])
    forged = json.loads(good["issuer-approval.json"])
    forged["approvals"][0]["user"] = {"id": 999, "login": "forger"}
    (target / "issuer-approval.json").write_text(json.dumps(forged))

    def refuse(subject, bundle, root, config):
        if Path(subject).name == "issuer-approval.json":
            raise ReceiptUnavailable("attestation verification failed: digest not in statement")
        return FakeVerifier(repo.sha)(subject, bundle, root, config)
    with pytest.raises(ReceiptUnavailable, match="attestation verification failed"):
        resolveOffline(cfg, repo, verifier=refuse)


# ==== 3. approval authentication (the Steward plug point) =======================================

AUTH_CASES = [
    ([approval()], 1, None),
    ([], 1, "no environment approval"),
    ("approved", 1, "no environment approval"),
    ([approval(), approval()], 1, "exactly one approved"),
    ([approval("rejected")], 1, "rejected"),
    ([approval(), approval("rejected")], 1, "rejected"),
    ([approval("pending")], 1, "unrecognized state"),
    (["approved"], 1, "malformed"),
    ([approval(user={"id": 999, "login": "other"})], 1, "configured reviewer roster"),
    ([approval(user={"id": True, "login": "x"})], 1, "authenticated reviewer identity"),
    ([approval(user={"id": REVIEWER["id"], "login": ""})], 1, "configured reviewer roster"),
    ([approval(env="another-environment")], 1, "trusted protected environment"),
    ([approval()], 2, "attempt must be 1"),
    ([approval()], True, "attempt must be 1"),
]


@pytest.mark.parametrize("items,attempt,error", AUTH_CASES)
def test_authenticate_approval_rules(items, attempt, error):
    source = GitHubActionsSource(transport=FakeTransport({}))
    run = {"id": RUN_ID, "attempt": attempt, "environment": COMMITTED.environment}
    if error is None:
        assert source._authenticate_approval(run, items, COMMITTED) == {
            "reviewer": "mbtiongson1", "reviewerId": 153011150}
    else:
        with pytest.raises(ReceiptUnavailable, match=error):
            source._authenticate_approval(run, items, COMMITTED)


def test_self_review_is_allowed_but_receipt_verifier_must_be_independent(tmp_path, repo, cfg):
    # the approver is also the tag pusher (single operator): allowed
    assert COMMITTED.prevent_self_review is False
    # ...but a receipt whose builder or contributor is the approver is refused by the resolver
    script = loadScript()
    work = tmp_path / "w"
    writeRequest(work)
    request = json.loads((work / "evidence/frontier-challenges/case/admission-request.json").read_text())
    request["receipt"]["contributor_id"] = REVIEWER["login"]
    (work / "evidence/frontier-challenges/case/admission-request.json").write_text(json.dumps(request))
    out = tmp_path / "o"
    script.buildBundle(work, TAG, out)
    script.sealBundle(out, TAG, [approval()], repository=COMMITTED.repository, sourceSha=repo.sha,
                      runId=RUN_ID, runAttempt=1, actor="mbtiongson1", expectedDigest=None)
    (out / "attestation.jsonl").write_bytes(b"{}\n")
    (out / "trusted_root.jsonl").write_bytes(b"{}\n")
    commitBundle(repo.root, out)
    with pytest.raises(ReceiptUnavailable, match="independent reviewer"):
        resolveOffline(cfg, repo)


def test_steward_can_replace_only_the_approval_decision(tmp_path, repo, cfg):
    calls = []

    class Automated(CommittedAttestedReceiptSource):
        def _authenticate_approval(self, run, items, config):
            calls.append((dict(run), items))
            return {"reviewer": "mbtiongson1", "reviewerId": 153011150}

    commitBundle(repo.root, makeBundle(tmp_path, repo))
    source = Automated(repo.root, verifier=FakeVerifier(repo.sha))
    # a subclass is never on the production allowlist: swapping the plug point needs an explicit decision
    with pytest.raises(ReceiptUnavailable, match="allowlisted authenticated"):
        GitHubVerificationReceiptResolver(cfg, source).resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE)

    class OptIn(GitHubVerificationReceiptResolver):
        AUTHENTICATED_SOURCES = (Automated,)
    assert OptIn(cfg, source).resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE).receipt_id == RECEIPT_ID
    assert calls and calls[0][0] == {"id": RUN_ID, "attempt": 1, "environment": COMMITTED.environment}
    assert "_authenticate_approval" in vars(cr.AuthenticatedApprovalSource)


def test_allowlist_contains_exactly_the_two_adapters_and_refuses_ports(cfg):
    assert GitHubVerificationReceiptResolver.AUTHENTICATED_SOURCES == (
        GitHubActionsSource, CommittedAttestedReceiptSource)
    port = SyntheticReceiptPort({}, b"")
    with pytest.raises(ReceiptUnavailable, match="allowlisted authenticated"):
        GitHubVerificationReceiptResolver(cfg, port).resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE)


# ==== 4. pinned workflow and history ============================================================

def test_workflow_blob_mismatch_missing_commit_and_orphaned_commit_fail_closed(tmp_path, repo, cfg):
    commitBundle(repo.root, makeBundle(tmp_path, repo))
    assert resolveOffline(cfg, repo).receipt_id == RECEIPT_ID
    with pytest.raises(ReceiptUnavailable, match="does not match the pinned blob"):
        resolveOffline(dataclasses.replace(cfg, workflow_blob_sha="9" * 40), repo)
    with pytest.raises(ReceiptUnavailable, match="not in local history"):
        resolveOffline(cfg, repo, verifier=FakeVerifier("d" * 40))
    # a commit that exists but is not an ancestor of HEAD (what a squash merge produces)
    git(repo.root, "checkout", "-q", "--orphan", "squashed")
    git(repo.root, "commit", "-q", "-m", "squash")
    with pytest.raises(ReceiptUnavailable, match="not reachable from HEAD"):
        resolveOffline(cfg, repo)


def test_local_git_rejects_non_sha_arguments_and_missing_git():
    sentinel = cr.LocalGit(Path("."), runner=lambda *a, **k: pytest.fail("git must not run"))
    assert sentinel.blobShaAt("--upload-pack=x", "p") is None
    assert sentinel.isAncestor("HEAD~1") is False

    def noGit(*args, **kwargs):
        raise FileNotFoundError("git")
    with pytest.raises(ReceiptUnavailable, match="git is required"):
        cr.LocalGit(Path("."), runner=noGit).blobShaAt("a" * 40, "p")


# ==== 5. attestation identity ===================================================================

@pytest.mark.parametrize("override,match", [
    ({"repository": "attacker/repo"}, "not the trusted issuer workflow"),
    ({"workflowPath": ".github/workflows/other.yml"}, "not the trusted issuer workflow"),
    ({"ref": "refs/heads/main"}, "outside the trusted challenge-receipt tag namespace"),
    ({"ref": "refs/tags/release/v1"}, "outside the trusted challenge-receipt tag namespace"),
    ({"trigger": "workflow_dispatch"}, "push-triggered GitHub-hosted"),
    ({"runnerEnvironment": "self-hosted"}, "push-triggered GitHub-hosted"),
    ({"runAttempt": 2}, "not attempt 1"),
    ({"runId": 0}, "not attempt 1"),
    ({"sourceSha": "nothex"}, "source commit is invalid"),
    ({"runId": 7}, "sealed approval does not bind"),
    ({"ref": "refs/tags/challenge-receipt/other-r1"}, "sealed approval does not bind"),
    ({"subjectSha256": "0" * 64}, "does not cover the exact bundle file bytes"),
])
def test_attestation_identity_mismatches_fail_closed(tmp_path, repo, cfg, override, match):
    commitBundle(repo.root, makeBundle(tmp_path, repo))
    with pytest.raises(ReceiptUnavailable, match=match):
        resolveOffline(cfg, repo, verifier=FakeVerifier(repo.sha, **override))


def test_two_subjects_signed_by_different_runs_are_refused(tmp_path, repo, cfg):
    commitBundle(repo.root, makeBundle(tmp_path, repo))
    inner = FakeVerifier(repo.sha)

    def split(subject, bundle, root, config):
        identity = inner(subject, bundle, root, config)
        if Path(subject).name == "issuer-approval.json":
            identity["runId"] = RUN_ID + 1
        return identity
    with pytest.raises(ReceiptUnavailable, match="not signed by the same run"):
        resolveOffline(cfg, repo, verifier=split)


def test_sealed_binding_fields_are_enforced(tmp_path, repo, cfg):
    for index, (overrides, match) in enumerate([
        ({"environment": "elsewhere"}, "sealed approval does not bind"),
        ({"repository": "attacker/repo"}, "sealed approval does not bind"),
        ({"receiptId": "receipt-99"}, "absent or ambiguous"),
        ({"sourceSha": "d" * 40}, "sealed approval does not bind"),
        ({"payloadDigest": "xyz"}, "payload digest is invalid"),
        ({"approvals": [approval(user={"id": 1, "login": "x"})]}, "configured reviewer roster"),
        ({"challengeId": "challenge-other"}, "sealed approval challenge id differs"),
    ]):
        out = makeBundle(tmp_path / f"b{index}", repo, sealOverrides=overrides)
        shutil.rmtree(repo.root / "evidence", ignore_errors=True)
        commitBundle(repo.root, out)
        with pytest.raises(ReceiptUnavailable, match=match):
            resolveOffline(cfg, repo)


# ==== 6. gh output parsing and the default verifier =============================================

def recorded():
    return json.loads(RECORDED.read_text())["result"]


def test_identity_is_extracted_from_recorded_gh_output():
    subject = recorded()[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"]
    identity = identityFromGhResult(json.dumps(recorded()), subject)
    assert identity == {
        "repository": "cli/cli", "workflowPath": ".github/workflows/deployment.yml",
        "ref": "refs/heads/trunk", "sourceSha": "63837fb778d6a39f02be0ce76ff89f2bc8d74bdc",
        "trigger": "workflow_dispatch", "runnerEnvironment": "github-hosted",
        "runId": 40384165451, "runAttempt": 1, "subjectSha256": subject}


def mutated(path, value):
    data = recorded()
    node = data[0]["verificationResult"]
    keys = path.split(".")
    for key in keys[:-1]:
        node = node[int(key)] if key.isdigit() else node[key]
    node[keys[-1]] = value
    return json.dumps(data)


@pytest.mark.parametrize("text,match", [
    ("not json", "not JSON"),
    ("[]", "no verified attestation"),
    ('{"a": 1}', "no verified attestation"),
    ("[{}]", "unexpected shape"),
    (mutated("statement.predicateType", "https://example.org/other"), "exact subject digest"),
    (mutated("signature.certificate.issuer", "https://evil.example"), "OIDC"),
    (mutated("signature.certificate.buildSignerURI", "https://github.com/other/repo/.github/workflows/x.yml@refs/heads/trunk"),
     "signer is not a workflow"),
    (mutated("signature.certificate.buildSignerDigest", "d" * 40), "internally inconsistent"),
    (mutated("signature.certificate.runInvocationURI", "https://example.org/runs/1"), "internally inconsistent"),
    (mutated("signature.certificate.buildTrigger", "push"), "internally inconsistent"),
])
def test_malformed_or_inconsistent_gh_output_is_refused(text, match):
    subject = recorded()[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"]
    with pytest.raises(ReceiptUnavailable, match=match):
        identityFromGhResult(text, subject)


def test_gh_output_must_name_the_exact_subject_and_attestations_must_agree():
    with pytest.raises(ReceiptUnavailable, match="exact subject digest"):
        identityFromGhResult(json.dumps(recorded()), "0" * 64)
    subject = recorded()[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"]
    two = recorded() + recorded()
    two[1]["verificationResult"]["signature"]["certificate"]["runInvocationURI"] = \
        "https://github.com/cli/cli/actions/runs/1/attempts/1"
    with pytest.raises(ReceiptUnavailable, match="disagree"):
        identityFromGhResult(json.dumps(two), subject)


def test_default_verifier_builds_an_offline_capable_gh_command(tmp_path):
    subject = tmp_path / "artifact.zip"
    subject.write_bytes(b"payload")
    digest = sha(b"payload")
    data = recorded()
    data[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = digest
    cert = data[0]["verificationResult"]["signature"]["certificate"]
    cert.update({"sourceRepositoryURI": f"https://github.com/{COMMITTED.repository}",
                 "buildSignerURI": f"https://github.com/{COMMITTED.repository}/{COMMITTED.workflow_path}@{REF}",
                 "sourceRepositoryRef": REF, "buildTrigger": "push", "githubWorkflowTrigger": "push",
                 "runInvocationURI": f"https://github.com/{COMMITTED.repository}/actions/runs/9/attempts/1"})
    seen = []

    def runner(command, **kwargs):
        seen.append(command)
        return subprocess.CompletedProcess(command, 0, json.dumps(data), "")
    verifier = GhAttestationVerifier("gh", runner=runner)
    identity = verifier(subject, tmp_path / "attestation.jsonl", tmp_path / "trusted_root.jsonl", COMMITTED)
    assert identity["runId"] == 9 and identity["workflowPath"] == COMMITTED.workflow_path
    command = seen[0]
    assert command[:3] == ["gh", "attestation", "verify"]
    for flag in ("--bundle", "--custom-trusted-root", "--deny-self-hosted-runners"):
        assert flag in command
    assert command[command.index("--signer-workflow") + 1] == f"{COMMITTED.repository}/{COMMITTED.workflow_path}"
    assert command[command.index("--repo") + 1] == COMMITTED.repository
    verifier(subject, tmp_path / "attestation.jsonl", None, COMMITTED)
    assert "--custom-trusted-root" not in seen[1]


def test_default_verifier_fails_closed_on_gh_failure_or_absence(tmp_path):
    subject = tmp_path / "f"
    subject.write_bytes(b"x")
    bad = GhAttestationVerifier("gh", runner=lambda c, **k: subprocess.CompletedProcess(c, 1, "", "no matching attestation"))
    with pytest.raises(ReceiptUnavailable, match="no matching attestation"):
        bad(subject, subject, None, COMMITTED)

    def missing(*args, **kwargs):
        raise FileNotFoundError("gh")
    with pytest.raises(ReceiptUnavailable, match="gh CLI is required"):
        GhAttestationVerifier("gh", runner=missing)(subject, subject, None, COMMITTED)


def test_gh_api_transport_reads_json_bytes_and_fails_closed():
    calls = []

    def runner(command, **kwargs):
        calls.append((command, kwargs["env"].get("GH_TOKEN")))
        return subprocess.CompletedProcess(command, 0, b'{"ok": true}', b"")
    transport = cr.GhApiTransport("tok", runner=runner)
    assert transport.getJson("repos/o/r/actions/runs/1") == {"ok": True}
    assert calls[0] == (["gh", "api", "repos/o/r/actions/runs/1"], "tok")
    assert transport.getBytes("x") == b'{"ok": true}'
    for result, match in [(subprocess.CompletedProcess([], 1, b"", b"HTTP 404"), "HTTP 404"),
                          (subprocess.CompletedProcess([], 0, b"<html>", b""), "non-JSON")]:
        with pytest.raises(ReceiptUnavailable, match=match):
            cr.GhApiTransport(runner=lambda *a, **k: result).getJson("p")
    big = subprocess.CompletedProcess([], 0, b"0" * (cr.MAX_BUNDLE_ZIP_BYTES + 1), b"")
    with pytest.raises(ReceiptUnavailable, match="size limit"):
        cr.GhApiTransport(runner=lambda *a, **k: big).getBytes("p")


# ==== 7. bundle bounds ==========================================================================

def goodFiles():
    return {name: b"{}" for name in cr.BUNDLE_LIMITS}


@pytest.mark.parametrize("build,match", [
    (lambda: b"not a zip", "invalid receipt bundle"),
    (lambda: zipOf({**goodFiles(), "extra.txt": b"x"}), "exactly the four"),
    (lambda: zipOf({k: v for k, v in goodFiles().items() if k != "artifact.zip"}), "exactly the four"),
    (lambda: zipOf({**goodFiles(), "attestation.jsonl": b"x" * (cr.BUNDLE_LIMITS["attestation.jsonl"] + 1)}),
     "unsafe bundle member|size cap"),
    (lambda: b"x" * (cr.MAX_BUNDLE_ZIP_BYTES + 1), "absent or too large"),
])
def test_bundle_zip_is_bounded_and_exact(build, match):
    with pytest.raises(ReceiptUnavailable, match=match):
        cr._readBundleZip(build())
    assert set(cr._readBundleZip(zipOf(goodFiles()))) == set(cr.BUNDLE_LIMITS)


# ==== 8. configuration and probe ================================================================

def test_committed_config_loads_the_founder_issuer_and_ships_in_the_wheel():
    assert COMMITTED.required_reviewer_ids == (153011150,)
    assert COMMITTED.prevent_self_review is False
    assert COMMITTED.environment == "challenge-receipt-issuer"
    assert COMMITTED.trigger_ref_prefix == "refs/tags/challenge-receipt/"
    assert COMMITTED.workflow_path == ".github/workflows/challenge-receipt-issuer.yml"
    assert cr.DEFAULT_CONFIG_PATH == CONFIG_FILE
    assert "data/trust/*.json" in (ROOT / "pyproject.toml").read_text()


def test_committed_config_pin_equals_the_blob_of_the_committed_workflow():
    actual = subprocess.run(["git", "hash-object", "--", str(WORKFLOW)], capture_output=True, text=True,
                            check=True, cwd=ROOT).stdout.strip()
    assert COMMITTED.workflow_blob_sha == actual, (
        f"challenge-receipt-issuer.yml changed: re-pin workflowBlobSha in {CONFIG_FILE.name} to {actual} "
        "(previously issued receipts attested at older commits keep verifying only while that "
        "older blob stays pinned; re-issue them if the pin moves)")


def test_environment_overrides_replace_fields_and_neither_source_means_not_configured(tmp_path):
    env = {"GAIA_RECEIPT_ENVIRONMENT": "other-env", "GAIA_RECEIPT_REQUIRED_REVIEWER_IDS": "5, 6",
           "GAIA_RECEIPT_PREVENT_SELF_REVIEW": "true"}
    config = loadTrustedConfig(env)
    assert (config.environment, config.required_reviewer_ids, config.prevent_self_review) == (
        "other-env", (5, 6), True)
    assert config.repository == COMMITTED.repository  # untouched fields come from the committed file
    with pytest.raises(ReceiptUnavailable, match="not configured") as error:
        loadTrustedConfig({}, path=tmp_path / "absent.json")
    assert not isinstance(error.value, ReceiptMisconfigured)
    assert cr.trusted_config_from_environment(COMPLETE_ENV).prevent_self_review is False


COMPLETE_ENV = {
    "GAIA_RECEIPT_REPOSITORY": "o/r", "GAIA_RECEIPT_WORKFLOW_PATH": ".github/workflows/x.yml",
    "GAIA_RECEIPT_TRIGGER_REF_PREFIX": "refs/tags/x/", "GAIA_RECEIPT_WORKFLOW_BLOB_SHA": "a" * 40,
    "GAIA_RECEIPT_ENVIRONMENT": "e", "GAIA_RECEIPT_REQUIRED_REVIEWER_IDS": "1"}


@pytest.mark.parametrize("content,env,match", [
    ("{not json", {}, "unreadable"),
    ('["list"]', {}, "schemaVersion 1"),
    ('{"schemaVersion": 2}', {}, "schemaVersion 1"),
    (json.dumps({"schemaVersion": 1, "surprise": 1}), {}, "unknown keys"),
    (json.dumps({"schemaVersion": 1, "repository": "o/r"}), {}, "incomplete"),
    (None, {"GAIA_RECEIPT_ENVIRONMENT": "e"}, "incomplete"),
    (None, {"GAIA_RECEIPT_REQUIRED_REVIEWER_IDS": "abc"}, "override is invalid"),
    (None, {"GAIA_RECEIPT_PREVENT_SELF_REVIEW": "maybe"}, "override is invalid"),
    (None, {**COMPLETE_ENV, "GAIA_RECEIPT_WORKFLOW_BLOB_SHA": "short"}, "invalid"),
    (None, {**COMPLETE_ENV, "GAIA_RECEIPT_TRIGGER_REF_PREFIX": "refs/heads/"}, "invalid"),
    (None, {**COMPLETE_ENV, "GAIA_RECEIPT_REQUIRED_REVIEWER_IDS": "0"}, "invalid"),
])
def test_bad_configuration_is_misconfigured_not_silently_defaulted(tmp_path, content, env, match):
    path = None
    if content is not None:
        path = tmp_path / "config.json"
        path.write_text(content)
    with pytest.raises(ReceiptMisconfigured, match=match):
        loadTrustedConfig(env, path=path)


def test_probe_reports_each_status_truthfully_and_never_claims_admission(tmp_path):
    runner = lambda ok: (lambda c, **k: subprocess.CompletedProcess(c, 0 if ok else 1, "tok\n", ""))
    found = lambda path: "/usr/bin/gh"
    common = dict(env={}, configPath=CONFIG_FILE)
    absent = probe_trusted_receipt_source(env={}, configPath=tmp_path / "none.json")
    assert (absent["status"], absent["available"]) == ("not-configured", False)
    broken = tmp_path / "broken.json"
    broken.write_text("{nope")
    assert probe_trusted_receipt_source(env={}, configPath=broken)["status"] == "misconfigured"
    drift = probe_trusted_receipt_source(
        dataclasses.replace(COMMITTED, workflow_blob_sha="9" * 40), repoRoot=ROOT, which=found, runner=runner(True))
    assert drift["status"] == "misconfigured" and "pinned workflow blob" in drift["reason"]
    missingFile = probe_trusted_receipt_source(COMMITTED, repoRoot=tmp_path, which=found, runner=runner(True))
    assert missingFile["status"] == "misconfigured" and "missing from the checkout" in missingFile["reason"]
    noGh = probe_trusted_receipt_source(COMMITTED, which=lambda p: None, runner=runner(True))
    assert noGh["status"] == "misconfigured" and "gh CLI not found" in noGh["reason"]
    offline = probe_trusted_receipt_source(**common, repoRoot=ROOT, which=found, runner=lambda c, **k: (
        subprocess.CompletedProcess(c, 0, COMMITTED.workflow_blob_sha + "\n", "") if "hash-object" in c
        else subprocess.CompletedProcess(c, 1, "", "not logged in")))
    assert (offline["status"], offline["available"]) == ("offline-only", False)
    live = probe_trusted_receipt_source(**common, repoRoot=ROOT, which=found, runner=lambda c, **k: (
        subprocess.CompletedProcess(c, 0, COMMITTED.workflow_blob_sha + "\n", "")))
    assert (live["status"], live["available"]) == ("available", True)
    tokened = probe_trusted_receipt_source(COMMITTED, env={"GH_TOKEN": "x"}, which=found, runner=runner(False))
    assert tokened["status"] == "available"
    for report in (absent, drift, offline, live):
        assert "admitted" not in json.dumps(report).lower()
        assert report["status"] in {"not-configured", "misconfigured", "offline-only", "available"}


# ==== 9. producer workflow and build script =====================================================

def test_workflow_is_a_least_privilege_sha_pinned_tag_triggered_two_job_issuer():
    text = WORKFLOW.read_text()
    import yaml
    data = yaml.safe_load(text)
    triggers = data.get(True) or data["on"]
    assert triggers == {"push": {"tags": ["challenge-receipt/**"]}}
    assert data["permissions"] == {}
    prepare, issue = data["jobs"]["prepare"], data["jobs"]["issue"]
    assert issue["needs"] == "prepare" and issue["environment"] == COMMITTED.environment
    assert "environment" not in prepare
    assert prepare["permissions"] == {"contents": "read"}
    assert issue["permissions"] == {"contents": "read", "actions": "read", "id-token": "write",
                                    "attestations": "write"}
    assert "secrets." not in text and "pull_request" not in text and "workflow_dispatch" not in text
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert any(item.startswith("actions/attest-build-provenance@") for item in uses)
    for item in uses:
        assert re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", item), f"action not SHA-pinned: {item}"
    assert issue["env"]["REVIEWER_ID"] == str(COMMITTED.required_reviewer_ids[0])
    assert issue["env"]["ENVIRONMENT_NAME"] == COMMITTED.environment
    assert "buildChallengeReceipt.py" in text and (ROOT / "scripts/buildChallengeReceipt.py").is_file()
    assert "GITHUB_RUN_ATTEMPT" in text and "/approvals" in text


def test_build_and_seal_script_refusals(tmp_path, repo):
    script = loadScript()
    with pytest.raises(SystemExit, match="must look like"):
        script.parseTag("release/v1")
    with pytest.raises(SystemExit, match="must look like"):
        script.parseTag("challenge-receipt/../x-r1")
    out = makeBundle(tmp_path, repo)
    build = json.loads((out / "build.json").read_text())

    def seal(**kw):
        args = dict(approvals=[approval()], repository=COMMITTED.repository, sourceSha=repo.sha, runId=RUN_ID,
                    runAttempt=1, actor="a", expectedDigest=build["artifactSha256"])
        args.update(kw)
        return script.sealBundle(out, TAG, args.pop("approvals"), **args)
    seal()
    with pytest.raises(SystemExit, match="changed between prepare and issue"):
        seal(expectedDigest="0" * 64)
    with pytest.raises(SystemExit, match="approval refused"):
        seal(approvals=[approval(), approval("rejected")])
    with pytest.raises(SystemExit, match="approval refused"):
        seal(runAttempt=2)
    with pytest.raises(SystemExit, match="configured trusted repository"):
        seal(repository="attacker/repo")
    mismatched = tmp_path / "mm"
    writeRequest(mismatched / "work", verifier="someone-else")
    mmOut = mismatched / "out"
    script.buildBundle(mismatched / "work", TAG, mmOut)
    with pytest.raises(SystemExit, match="authenticated approver"):
        script.sealBundle(mmOut, TAG, [approval()], repository=COMMITTED.repository, sourceSha=repo.sha,
                          runId=RUN_ID, runAttempt=1, actor="a", expectedDigest=None)
    with pytest.raises(SystemExit, match="no challenge case directory"):
        script.loadRequest(tmp_path / "work", "nope")
    with pytest.raises(SystemExit, match="own case id"):
        request = tmp_path / "work/evidence/frontier-challenges/case/admission-request.json"
        data = json.loads(request.read_text())
        data["caseId"] = "different"
        request.write_text(json.dumps(data))
        script.loadRequest(tmp_path / "work", "case")


def test_public_surface_keeps_imports_lazy_and_stdlib_only():
    code = (
        "import sys\n"
        "import gaia_cli.steward.challenge_receipts\n"
        "bad = sorted(m for m in sys.modules if m.split('.')[0] in {'yaml','requests','httpx','pytest','jsonschema'})\n"
        "print(','.join(bad))\n")
    out = subprocess.run([os.environ.get("PYTHON", "python3"), "-c", code], capture_output=True, text=True,
                         cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, check=True).stdout.strip()
    assert out == "", f"third-party modules imported at module import time: {out}"
