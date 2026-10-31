"""Challenge-receipt issuer tests (EPIC #2189).

Everything here is SYNTHETIC unless stated: fake transports, fake attestation verifiers,
synthetic attestation bytes. The only recorded artifact is
``fixtures/gh-attestation-verify-recorded.json`` (real ``gh attestation verify`` output
from a public cli/cli release, used for shape parsing only). Passing here proves the
verification contract; it is not live issuer evidence. No network or ``gh`` call is made.
The workflow's inline (pinned) Python is extracted from the committed YAML and executed, so
the sealing logic that actually runs after approval is the logic under test.
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
import sys
import types
import warnings
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
TRUSTED_ROOT = ROOT / "src/gaia_cli/data/trust/sigstore-trusted-root.jsonl"
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
    (root / COMMITTED.workflow_path).write_text("name: synthetic issuer workflow for tests\n")
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


def writeRequest(root: Path, *, verifier=REVIEWER["login"], contributor="contributor-x", challengeId=CHALLENGE,
                 caseId="case"):
    caseDir = root / "evidence/frontier-challenges" / caseId
    caseDir.mkdir(parents=True, exist_ok=True)
    (caseDir / "transcript.json").write_bytes(TRANSCRIPT)
    receipt = VerificationReceipt(
        RECEIPT_ID, CONTEXT, sha(TRANSCRIPT), verifier, "builder-agent", contributor, "passed",
        "reproducible-test", "runner-1", "PASS: 3/3", sha(b"PASS: 3/3"),
        "https://example.org/proof/17", "https://example.org/notices/17", "2026-10-26T12:00:00Z")
    (caseDir / "admission-request.json").write_text(json.dumps({
        "schemaVersion": 1, "caseId": caseId, "challengeId": challengeId, "contextDigest": CONTEXT,
        "proofSourceSha": PROOF_SHA, "transcriptPath": "transcript.json",
        "receipt": dataclasses.asdict(receipt)}))
    return receipt


# ---- the workflow's pinned inline code, extracted and executed -------------------------------

def workflowSteps(job):
    import yaml
    return yaml.safe_load(WORKFLOW.read_text())["jobs"][job]["steps"]


def inlineBody(job, stepPrefix):
    run = next(step["run"] for step in workflowSteps(job) if step.get("name", "").startswith(stepPrefix))
    return run.split("python3 -I - <<'PY'\n", 1)[1].rsplit("\nPY", 1)[0]


def runInline(body, cwd, env):
    # same interpreter flags as the workflow's `python3 -I -` (isolated: no cwd/env on sys.path)
    return subprocess.run([sys.executable, "-I", "-"], input=body, cwd=cwd, capture_output=True, text=True,
                          env={"PATH": os.environ["PATH"], **env})


def prepareEnv(run: Path, tag=TAG, actor="mbtiongson1"):
    return {"GITHUB_REF_NAME": tag, "TRIGGERING_ACTOR": actor, "GITHUB_OUTPUT": str(run / "output.txt"),
            "GITHUB_STEP_SUMMARY": str(run / "summary.md")}


def sealEnv(run: Path, digest, tag=TAG, shaValue="0" * 40, **over):
    env = {"GITHUB_REF_NAME": tag, "GITHUB_REF_TYPE": "tag", "GITHUB_REF": f"refs/tags/{tag}",
           "GITHUB_RUN_ATTEMPT": "1", "GITHUB_RUN_ID": str(RUN_ID), "GITHUB_SHA": shaValue,
           "GITHUB_REPOSITORY": COMMITTED.repository, "REPOSITORY_ID": str(COMMITTED.repository_id),
           "OWNER_ID": str(COMMITTED.repository_owner_id), "ENVIRONMENT_NAME": COMMITTED.environment,
           "REVIEWER_ID": str(REVIEWER["id"]), "EXPECTED_DIGEST": digest, "RECEIPT_ID": RECEIPT_ID,
           "TRIGGERING_ACTOR": "mbtiongson1", "GITHUB_STEP_SUMMARY": str(run / "summary.md")}
    env.update(over)
    return env


def buildArchive(tmp_path, *, verifier=REVIEWER["login"], contributor="contributor-x", challengeId=CHALLENGE):
    """Real build script into <tmp>/run/out; returns (run dir, build record)."""
    work, run = tmp_path / "work", tmp_path / "run"
    writeRequest(work, verifier=verifier, contributor=contributor, challengeId=challengeId)
    run.mkdir()
    return run, loadScript().buildBundle(work, TAG, run / "out")


def makeBundle(tmp_path, repo, *, approvals=None, verifier=REVIEWER["login"], contributor="contributor-x",
               sealOverrides=None, envOver=None):
    """Real build script, then the PINNED inline sealing code; attestation bytes are SYNTHETIC."""
    run, build = buildArchive(tmp_path, verifier=verifier, contributor=contributor)
    (run / "approvals.json").write_text(json.dumps([approval()] if approvals is None else approvals))
    proc = runInline(inlineBody("issue", "Verify the facts"), run,
                     sealEnv(run, build["artifactSha256"], shaValue=repo.sha, **(envOver or {})))
    assert proc.returncode == 0, proc.stderr
    out = run / "out"
    if sealOverrides:
        sealed = json.loads((out / "issuer-approval.json").read_text())
        sealed.update(sealOverrides)
        (out / "issuer-approval.json").write_text(json.dumps(sealed))
    (out / "attestation.jsonl").write_bytes(b'{"synthetic":"sigstore bundle"}\n')
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
        self.calls.append((Path(subject).name, Path(trustedRoot).read_bytes() if trustedRoot else None))
        identity = {"repository": config.repository, "workflowPath": config.workflow_path, "ref": REF,
                    "sourceSha": self.sha, "trigger": "push", "runnerEnvironment": "github-hosted",
                    "runId": RUN_ID, "runAttempt": 1, "repositoryId": config.repository_id,
                    "ownerId": config.repository_owner_id, "subjectSha256": sha(Path(subject).read_bytes())}
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


def resolveOffline(cfg, repo, *, verifier=None, git_=None, trustedRoot=TRUSTED_ROOT):
    source = CommittedAttestedReceiptSource(
        repo.root, verifier=verifier or FakeVerifier(repo.sha), git=git_, trustedRoot=trustedRoot)
    return GitHubVerificationReceiptResolver(cfg, source).resolve(
        RECEIPT_ID, expected_challenge_id=CHALLENGE, expected_proof_source_sha=PROOF_SHA)


# ==== 1. online path ============================================================================

def test_online_path_resolves_and_cross_checks_live_run_artifact_and_approvals(tmp_path, repo, cfg):
    files = bundleFiles(makeBundle(tmp_path, repo))
    receipt, verifier, source = resolveOnline(cfg, repo, files)
    assert receipt.receipt_id == RECEIPT_ID and receipt.verifier_id == "mbtiongson1"
    # both subjects verified against the packaged, pinned root
    assert {name: root for name, root in verifier.calls} == {
        "artifact.zip": TRUSTED_ROOT.read_bytes(), "issuer-approval.json": TRUSTED_ROOT.read_bytes()}
    paths = source.transport.requests
    assert any("actions/artifacts?name=challenge-receipt-receipt-17" in path for path in paths)
    assert any(path.endswith(f"actions/runs/{RUN_ID}/approvals") for path in paths)


@pytest.mark.parametrize("kwargs,match", [
    ({"listing": {"total_count": 0, "artifacts": []}}, "absent or ambiguous"),
    ({"listing": {"total_count": 1, "artifacts": [{}]}}, "malformed"),
    ({"listing": {"total_count": 21, "artifacts": [{}] * 21}}, "absent or ambiguous"),
    ({"listing": [1]}, "absent or ambiguous"),
    ({"listing": {"total_count": 1, "artifacts": [{"id": 555, "name": "challenge-receipt-other",
                                                   "workflow_run": {"id": RUN_ID}}]}}, "malformed"),
    ({"listing": {"total_count": 1, "artifacts": [{"id": 555, "name": "challenge-receipt-receipt-17",
                                                   "expired": True, "workflow_run": {"id": RUN_ID}}]}},
     "expired or ambiguous"),
    ({"run": {"conclusion": "failure"}}, "did not complete successfully"),
    ({"run": {"status": "in_progress"}}, "did not complete successfully"),
    ({"run": {"path": ".github/workflows/other.yml"}}, "0 of 1 same-named"),
    ({"run": {"event": "workflow_dispatch"}}, "0 of 1 same-named"),
    ({"run": {"head_sha": "d" * 40}}, "live workflow run does not match"),
    ({"run": {"head_branch": "main"}}, "0 of 1 same-named"),
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


def test_online_transport_failure_is_receipt_unavailable(repo, cfg):
    transport = FakeTransport({"actions/artifacts?name=": ReceiptUnavailable("GitHub API read failed")})
    source = GitHubActionsSource(transport=transport, verifier=FakeVerifier(repo.sha), git=cr.LocalGit(repo.root))
    with pytest.raises(ReceiptUnavailable, match="GitHub API read failed"):
        GitHubVerificationReceiptResolver(cfg, source).resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE)


def squatterArtifact(runId):
    return {"id": 900 + runId, "name": "challenge-receipt-receipt-17", "expired": False,
            "workflow_run": {"id": runId}}


def test_same_named_artifacts_from_other_workflows_cannot_deny_or_hijack(tmp_path, repo, cfg):
    files = bundleFiles(makeBundle(tmp_path, repo))
    genuine = {"id": 555, "name": "challenge-receipt-receipt-17", "expired": False, "workflow_run": {"id": RUN_ID}}
    listing = {"total_count": 3, "artifacts": [squatterArtifact(901), genuine, squatterArtifact(902)]}
    transport = liveTransport(files, repo.sha, listing=listing)
    foreign = {"id": 901, "path": ".github/workflows/evil.yml", "event": "push", "head_branch": TAG}
    transport.responses = {**{f"actions/runs/{rid}": {**foreign, "id": rid} for rid in (901, 902)},
                           **transport.responses}
    # a squatter run on a branch push of the right file name is also ignored
    transport.responses["actions/runs/902"] = {**foreign, "id": 902, "path": COMMITTED.workflow_path,
                                               "head_branch": "main"}
    source = GitHubActionsSource(transport=transport, verifier=FakeVerifier(repo.sha), git=cr.LocalGit(repo.root))
    receipt = GitHubVerificationReceiptResolver(cfg, source).resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE)
    assert receipt.receipt_id == RECEIPT_ID
    # only squatters: nothing from the issuer workflow, fail closed with a count in the message
    only = {"total_count": 1, "artifacts": [squatterArtifact(901)]}
    transport = liveTransport(files, repo.sha, listing=only)
    transport.responses = {"actions/runs/901": {**foreign, "id": 901}, **transport.responses}
    source = GitHubActionsSource(transport=transport, verifier=FakeVerifier(repo.sha), git=cr.LocalGit(repo.root))
    with pytest.raises(ReceiptUnavailable, match="0 of 1 same-named"):
        GitHubVerificationReceiptResolver(cfg, source).resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE)


def test_two_fully_verifying_artifacts_are_ambiguous_but_a_branch_squatter_is_not(tmp_path, repo, cfg):
    files = bundleFiles(makeBundle(tmp_path, repo))
    genuine = {"id": 555, "name": "challenge-receipt-receipt-17", "expired": False, "workflow_run": {"id": RUN_ID}}
    twin = {**genuine, "id": 556}
    transport = liveTransport(files, repo.sha, listing={"total_count": 2, "artifacts": [genuine, twin]})
    transport.responses["actions/artifacts/556/zip"] = zipOf(files)
    source = GitHubActionsSource(transport=transport, verifier=FakeVerifier(repo.sha), git=cr.LocalGit(repo.root))
    with pytest.raises(ReceiptUnavailable, match="2 same-named artifacts fully verify"):
        GitHubVerificationReceiptResolver(cfg, source).resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE)
    # A BRANCH named challenge-receipt/x running a same-path workflow passes the structural filter
    # (its head_branch has the tag-like prefix) but can never verify, so it cannot force "ambiguous".
    for squatPath in (COMMITTED.workflow_path, COMMITTED.workflow_path + "@refs/heads/challenge-receipt/x"):
        squatter = {"id": 777, "name": "challenge-receipt-receipt-17", "expired": False, "workflow_run": {"id": 700}}
        listing = {"total_count": 2, "artifacts": [squatter, genuine]}
        transport = liveTransport(files, repo.sha, listing=listing)
        transport.responses = {
            "actions/runs/700/approvals": [approval()],
            "actions/runs/700": {"id": 700, "path": squatPath, "event": "push", "run_attempt": 1,
                                 "head_branch": "challenge-receipt/x", "head_sha": repo.sha, "status": "completed",
                                 "conclusion": "success", "repository": {"full_name": COMMITTED.repository},
                                 "head_repository": {"full_name": COMMITTED.repository}},
            "actions/artifacts/777/zip": b"attacker junk that is not a bundle",
            **transport.responses}
        source = GitHubActionsSource(transport=transport, verifier=FakeVerifier(repo.sha),
                                     git=cr.LocalGit(repo.root))
        assert GitHubVerificationReceiptResolver(cfg, source).resolve(
            RECEIPT_ID, expected_challenge_id=CHALLENGE).receipt_id == RECEIPT_ID
        if "@" in squatPath:  # an explicit non-tag ref in `path` is dropped before any download
            assert not any("artifacts/777/zip" in request for request in transport.requests)
    # a squatter whose junk is the ONLY same-named artifact fails closed with the real reason
    transport = liveTransport(files, repo.sha, listing={"total_count": 1, "artifacts": [squatter]})
    transport.responses = {"actions/artifacts?name=": {"total_count": 1, "artifacts": [squatter]},
                           "actions/runs/700/approvals": [approval()],
                           "actions/runs/700": {"id": 700, "path": COMMITTED.workflow_path, "event": "push",
                                                "head_branch": "challenge-receipt/x"},
                           "actions/artifacts/777/zip": b"junk"}
    source = GitHubActionsSource(transport=transport, verifier=FakeVerifier(repo.sha), git=cr.LocalGit(repo.root))
    with pytest.raises(ReceiptUnavailable, match="invalid receipt bundle"):
        GitHubVerificationReceiptResolver(cfg, source).resolve(RECEIPT_ID, expected_challenge_id=CHALLENGE)


# ==== 2. offline path ===========================================================================

def test_offline_path_resolves_a_committed_bundle_built_by_the_real_script(tmp_path, repo, cfg):
    out = makeBundle(tmp_path, repo)
    commitBundle(repo.root, out)
    verifier = FakeVerifier(repo.sha)
    receipt = resolveOffline(cfg, repo, verifier=verifier)
    assert receipt.receipt_id == RECEIPT_ID
    assert [root for _, root in verifier.calls] == [TRUSTED_ROOT.read_bytes()] * 2
    bound = GitHubVerificationReceiptResolver(
        cfg, CommittedAttestedReceiptSource(repo.root, verifier=verifier)).for_challenge(CHALLENGE, PROOF_SHA)
    assert bound.resolve(RECEIPT_ID) == receipt
    with pytest.raises(ReceiptUnavailable, match="challenge id does not match"):
        GitHubVerificationReceiptResolver(
            cfg, CommittedAttestedReceiptSource(repo.root, verifier=verifier)).for_challenge("other").resolve(RECEIPT_ID)


def test_offline_bundle_structure_failures_fail_closed(tmp_path, repo, cfg):
    out = makeBundle(tmp_path, repo)
    with pytest.raises(ReceiptUnavailable, match="absent"):
        resolveOffline(cfg, repo)  # nothing committed
    target = commitBundle(repo.root, out)
    (target / "attestation.jsonl").unlink()
    with pytest.raises(ReceiptUnavailable, match="missing, linked, or oversized"):
        resolveOffline(cfg, repo)
    (target / "attestation.jsonl").symlink_to(out / "attestation.jsonl")
    with pytest.raises(ReceiptUnavailable, match="missing, linked, or oversized"):
        resolveOffline(cfg, repo)
    (target / "attestation.jsonl").unlink()
    (target / "attestation.jsonl").write_bytes(b"x" * (cr.BUNDLE_LIMITS["attestation.jsonl"] + 1))
    with pytest.raises(ReceiptUnavailable, match="missing, linked, or oversized"):
        resolveOffline(cfg, repo)


def test_duplicate_receipt_id_across_cases_fails_closed_and_names_the_cases(tmp_path, repo, cfg):
    out = makeBundle(tmp_path, repo)
    commitBundle(repo.root, out)
    commitBundle(repo.root, out, caseId="case-dup")
    with pytest.raises(ReceiptUnavailable, match="ambiguous: receipt id 'receipt-17' is sealed in case, case-dup"):
        resolveOffline(cfg, repo)


def test_tampered_committed_bytes_never_resolve(tmp_path, repo, cfg):
    out = makeBundle(tmp_path, repo)
    target = commitBundle(repo.root, out)
    good = bundleFiles(out)
    # a different (valid) receipt archive swapped in: sealed artifact digest no longer matches
    other = tmp_path / "other"
    writeRequest(other, challengeId="challenge-other")
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


# ==== 3. trusted root pinning (a bundle never supplies its own root) =============================

def test_shipped_trusted_root_matches_the_committed_pin():
    assert sha(TRUSTED_ROOT.read_bytes()) == COMMITTED.trusted_root_sha256, (
        "sigstore-trusted-root.jsonl changed: re-pin trustedRootSha256 in challenge-receipt-issuer.json")
    assert "data/trust/*.jsonl" in (ROOT / "pyproject.toml").read_text()


def test_tampered_trusted_root_is_refused_before_any_verification(tmp_path, repo, cfg):
    commitBundle(repo.root, makeBundle(tmp_path, repo))
    tampered = tmp_path / "tampered-root.jsonl"
    tampered.write_bytes(TRUSTED_ROOT.read_bytes() + b'{"attacker":"supplied root"}\n')
    verifier = FakeVerifier(repo.sha)
    with pytest.raises(ReceiptUnavailable, match="does not match the pinned sha256"):
        resolveOffline(cfg, repo, verifier=verifier, trustedRoot=tampered)
    assert verifier.calls == []  # never reached the attestation verifier
    with pytest.raises(ReceiptUnavailable, match="unreadable"):
        resolveOffline(cfg, repo, trustedRoot=tmp_path / "absent.jsonl")
    # a re-pinned config does not help an attacker who cannot change the committed pin
    with pytest.raises(ReceiptUnavailable, match="does not match the pinned sha256"):
        resolveOffline(dataclasses.replace(cfg, trusted_root_sha256="0" * 64), repo)


def test_a_root_shipped_inside_the_committed_bundle_is_ignored(tmp_path, repo, cfg):
    target = commitBundle(repo.root, makeBundle(tmp_path, repo))
    (target / "trusted_root.jsonl").write_bytes(b'{"attacker":"root"}\n')
    verifier = FakeVerifier(repo.sha)
    assert resolveOffline(cfg, repo, verifier=verifier).receipt_id == RECEIPT_ID
    assert all(root == TRUSTED_ROOT.read_bytes() for _, root in verifier.calls)
    # and an online artifact carrying an extra trusted_root.jsonl is not an acceptable bundle
    files = {**bundleFiles(target), "trusted_root.jsonl": b'{"attacker":"root"}\n'}
    with pytest.raises(ReceiptUnavailable, match="exactly the three"):
        resolveOnline(cfg, repo, files)


# ==== 4. approval authentication (the Steward plug point) =======================================

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


def test_self_review_is_allowed_but_receipt_verifier_must_differ_from_declared_actors(tmp_path, repo, cfg):
    assert COMMITTED.prevent_self_review is False  # the approver is also the tag pusher
    commitBundle(repo.root, makeBundle(tmp_path, repo, contributor=REVIEWER["login"]))
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


# ==== 5. pinned workflow and history ============================================================

def test_workflow_blob_mismatch_missing_commit_and_orphaned_commit_fail_closed(tmp_path, repo, cfg):
    commitBundle(repo.root, makeBundle(tmp_path, repo))
    assert resolveOffline(cfg, repo).receipt_id == RECEIPT_ID
    with pytest.raises(ReceiptUnavailable, match="does not match the pinned blob"):
        resolveOffline(dataclasses.replace(cfg, workflow_blob_sha="9" * 40), repo)
    with pytest.raises(ReceiptUnavailable, match="not in local history"):
        resolveOffline(cfg, repo, verifier=FakeVerifier("d" * 40))
    git(repo.root, "checkout", "-q", "--orphan", "squashed")  # what a squash merge produces
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


# ==== 6. attestation identity ===================================================================

@pytest.mark.parametrize("override,match", [
    ({"repository": "attacker/repo"}, "not the trusted issuer workflow"),
    ({"workflowPath": ".github/workflows/other.yml"}, "not the trusted issuer workflow"),
    ({"repositoryId": 1}, "not the trusted issuer workflow"),
    ({"ownerId": 1}, "not the trusted issuer workflow"),
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


@pytest.mark.parametrize("index,overrides,match", [
    (0, {"environment": "elsewhere"}, "sealed approval does not bind"),
    (1, {"repository": "attacker/repo"}, "sealed approval does not bind"),
    (2, {"repositoryId": 5}, "sealed approval does not bind"),
    (3, {"ownerId": 5}, "sealed approval does not bind"),
    (4, {"receiptId": "receipt-99"}, "absent"),
    (5, {"sourceSha": "d" * 40}, "sealed approval does not bind"),
    (6, {"payloadDigest": "xyz"}, "payload digest is invalid"),
    (7, {"approvals": [approval(user={"id": 1, "login": "x"})]}, "configured reviewer roster"),
    (8, {"challengeId": "challenge-other"}, "sealed approval challenge id differs"),
])
def test_sealed_binding_fields_are_enforced(tmp_path, repo, cfg, index, overrides, match):
    commitBundle(repo.root, makeBundle(tmp_path / f"b{index}", repo, sealOverrides=overrides))
    with pytest.raises(ReceiptUnavailable, match=match):
        resolveOffline(cfg, repo)


# ==== 7. gh output parsing and the default verifier =============================================

def recorded():
    return json.loads(RECORDED.read_text())["result"]


def test_identity_is_extracted_from_recorded_gh_output():
    subject = recorded()[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"]
    identity = identityFromGhResult(json.dumps(recorded()), subject)
    assert identity == {
        "repository": "cli/cli", "workflowPath": ".github/workflows/deployment.yml",
        "ref": "refs/heads/trunk", "sourceSha": "63837fb778d6a39f02be0ce76ff89f2bc8d74bdc",
        "trigger": "workflow_dispatch", "runnerEnvironment": "github-hosted",
        "runId": 40384165451, "runAttempt": 1, "repositoryId": 212613049, "ownerId": 59704711,
        "subjectSha256": subject}


def mutated(path, value):
    data = recorded()
    node = data[0]["verificationResult"]
    keys = path.split(".")
    for key in keys[:-1]:
        node = node[key]
    node[keys[-1]] = value
    return json.dumps(data)


@pytest.mark.parametrize("text,match", [
    ("not json", "not JSON"),
    ("[]", "no verified attestation"),
    ('{"a": 1}', "no verified attestation"),
    ("[{}]", "unexpected shape"),
    (mutated("statement.predicateType", "https://example.org/other"), "exact subject digest"),
    (mutated("signature.certificate.issuer", "https://evil.example"), "OIDC"),
    (mutated("signature.certificate.buildSignerURI",
             "https://github.com/other/repo/.github/workflows/x.yml@refs/heads/trunk"), "signer is not a workflow"),
    (mutated("signature.certificate.buildSignerDigest", "d" * 40), "internally inconsistent"),
    (mutated("signature.certificate.runInvocationURI", "https://example.org/runs/1"), "internally inconsistent"),
    (mutated("signature.certificate.buildTrigger", "push"), "internally inconsistent"),
    (mutated("signature.certificate.sourceRepositoryIdentifier", "not-a-number"), "unexpected shape"),
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
    data = recorded()
    data[0]["verificationResult"]["statement"]["subject"][0]["digest"]["sha256"] = sha(b"payload")
    data[0]["verificationResult"]["signature"]["certificate"].update({
        "sourceRepositoryURI": f"https://github.com/{COMMITTED.repository}",
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


class FakePipe:
    def __init__(self, data):
        self.stream = io.BytesIO(data)
        self.reads = 0

    def read(self, n):
        self.reads += 1
        return self.stream.read(n)

    def close(self):
        pass


class FakeProc:
    def __init__(self, stdout=b"", code=0, stderrText=b"", errors=None):
        self.stdout = FakePipe(stdout)
        self.code, self.killed = code, False
        if errors is not None and stderrText:
            errors.write(stderrText)

    def kill(self):
        self.killed = True

    def wait(self):
        return self.code


def fakePopen(stdout=b"", code=0, stderrText=b""):
    holder = {}

    def make(command, **kwargs):
        proc = FakeProc(stdout, code, stderrText, kwargs.get("stderr"))
        holder["proc"], holder["command"], holder["env"] = proc, command, kwargs.get("env")
        return proc
    make.holder = holder
    return make


def test_gh_api_transport_reads_json_and_bytes():
    popen = fakePopen(b'{"ok": true}')
    transport = cr.GhApiTransport("tok", popen=popen)
    assert transport.getJson("repos/o/r/actions/runs/1") == {"ok": True}
    assert popen.holder["command"] == ["gh", "api", "repos/o/r/actions/runs/1"]
    assert popen.holder["env"]["GH_TOKEN"] == "tok"
    assert cr.GhApiTransport(popen=fakePopen(b"zipbytes")).getBytes("x") == b"zipbytes"


def test_gh_api_transport_fails_closed_and_enforces_size_while_streaming():
    with pytest.raises(ReceiptUnavailable, match="HTTP 404"):
        cr.GhApiTransport(popen=fakePopen(b"", 1, b"HTTP 404")).getJson("p")
    with pytest.raises(ReceiptUnavailable, match="non-JSON"):
        cr.GhApiTransport(popen=fakePopen(b"<html>")).getJson("p")

    def missing(*a, **k):
        raise FileNotFoundError("gh")
    with pytest.raises(ReceiptUnavailable, match="gh CLI is required"):
        cr.GhApiTransport(popen=missing).getJson("p")
    huge = fakePopen(b"0" * (cr.MAX_BUNDLE_ZIP_BYTES + 70000))
    with pytest.raises(ReceiptUnavailable, match="size limit"):
        cr.GhApiTransport(popen=huge).getBytes("p")
    proc = huge.holder["proc"]
    assert proc.killed is True
    # it stopped reading shortly after the cap instead of buffering the whole response
    assert proc.stdout.reads <= cr.MAX_BUNDLE_ZIP_BYTES // 65536 + 2


# ==== 8. bundle bounds ==========================================================================

def goodFiles():
    return {name: b"{}" for name in cr.BUNDLE_LIMITS}


@pytest.mark.parametrize("build,match", [
    (lambda: b"not a zip", "invalid receipt bundle"),
    (lambda: zipOf({**goodFiles(), "extra.txt": b"x"}), "exactly the three"),
    (lambda: zipOf({k: v for k, v in goodFiles().items() if k != "artifact.zip"}), "exactly the three"),
    (lambda: zipOf({**goodFiles(), "attestation.jsonl": b"x" * (cr.BUNDLE_LIMITS["attestation.jsonl"] + 1)}),
     "unsafe bundle member|size cap"),
    (lambda: b"x" * (cr.MAX_BUNDLE_ZIP_BYTES + 1), "absent or too large"),
])
def test_bundle_zip_is_bounded_and_exact(build, match):
    with pytest.raises(ReceiptUnavailable, match=match):
        cr._readBundleZip(build())
    assert set(cr._readBundleZip(zipOf(goodFiles()))) == set(cr.BUNDLE_LIMITS)


# ==== 9. configuration and probe ================================================================

def test_committed_config_loads_the_founder_issuer_and_ships_in_the_wheel():
    assert COMMITTED.required_reviewer_ids == (153011150,)
    assert COMMITTED.prevent_self_review is False
    assert (COMMITTED.repository_id, COMMITTED.repository_owner_id) == (1221716703, 297590332)
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
        "(receipts already issued at older commits verify only while that older blob stays pinned; "
        "re-issue them if the pin moves)")


COMPLETE_ENV = {
    "GAIA_RECEIPT_REPOSITORY": "o/r", "GAIA_RECEIPT_WORKFLOW_PATH": ".github/workflows/x.yml",
    "GAIA_RECEIPT_TRIGGER_REF_PREFIX": "refs/tags/x/", "GAIA_RECEIPT_WORKFLOW_BLOB_SHA": "a" * 40,
    "GAIA_RECEIPT_ENVIRONMENT": "e", "GAIA_RECEIPT_REQUIRED_REVIEWER_IDS": "1",
    "GAIA_RECEIPT_REPOSITORY_ID": "11", "GAIA_RECEIPT_REPOSITORY_OWNER_ID": "12",
    "GAIA_RECEIPT_TRUSTED_ROOT_SHA256": "b" * 64}


def test_environment_overrides_replace_fields_loudly_and_neither_source_means_not_configured(tmp_path):
    env = {"GAIA_RECEIPT_ENVIRONMENT": "other-env", "GAIA_RECEIPT_REQUIRED_REVIEWER_IDS": "5, 6",
           "GAIA_RECEIPT_PREVENT_SELF_REVIEW": "true", "GAIA_RECEIPT_WORKFLOW_BLOB_SHA": "a" * 40,
           "GAIA_RECEIPT_TRUSTED_ROOT_SHA256": "c" * 64}
    with pytest.warns(RuntimeWarning, match="NOT in force") as caught:
        config = loadTrustedConfig(env)
    message = str(caught[0].message)
    for name in ("GAIA_RECEIPT_WORKFLOW_BLOB_SHA", "GAIA_RECEIPT_REQUIRED_REVIEWER_IDS",
                 "GAIA_RECEIPT_TRUSTED_ROOT_SHA256", "GAIA_RECEIPT_ENVIRONMENT"):
        assert name in message
    assert (config.environment, config.required_reviewer_ids, config.prevent_self_review) == (
        "other-env", (5, 6), True)
    assert config.repository == COMMITTED.repository  # untouched fields come from the committed file
    with warnings.catch_warnings():
        warnings.simplefilter("error")  # an override equal to the committed pin is not a change
        loadTrustedConfig({"GAIA_RECEIPT_ENVIRONMENT": COMMITTED.environment})
    with pytest.raises(ReceiptUnavailable, match="not configured") as error:
        loadTrustedConfig({}, path=tmp_path / "absent.json")
    assert not isinstance(error.value, ReceiptMisconfigured)
    assert cr.trusted_config_from_environment(COMPLETE_ENV).prevent_self_review is False


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
    (None, {**COMPLETE_ENV, "GAIA_RECEIPT_REPOSITORY_ID": "0"}, "invalid"),
    (None, {**COMPLETE_ENV, "GAIA_RECEIPT_TRUSTED_ROOT_SHA256": "short"}, "invalid"),
])
def test_bad_configuration_is_misconfigured_not_silently_defaulted(tmp_path, content, env, match):
    path = None
    if content is not None:
        path = tmp_path / "config.json"
        path.write_text(content)
    with pytest.raises(ReceiptMisconfigured, match=match):
        loadTrustedConfig(env, path=path)


def test_probe_reports_each_status_truthfully_and_available_is_never_admitted(tmp_path):
    def runner(ok):
        return lambda c, **k: subprocess.CompletedProcess(c, 0 if ok else 1, "tok\n", "")
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
    badRoot = probe_trusted_receipt_source(COMMITTED, which=found, runner=runner(True),
                                           trustedRoot=tmp_path / "absent.jsonl")
    assert badRoot["status"] == "misconfigured" and "trusted root" in badRoot["reason"]
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
    overridden = probe_trusted_receipt_source(
        env={"GAIA_RECEIPT_ENVIRONMENT": COMMITTED.environment}, configPath=CONFIG_FILE, which=found,
        runner=runner(True))
    assert overridden["envOverrides"] == ["GAIA_RECEIPT_ENVIRONMENT"]
    for report in (absent, drift, badRoot, offline, live, tokened):
        assert report["admitted"] is False, "a readiness probe must never claim admission"
        assert report["status"] in {"not-configured", "misconfigured", "offline-only", "available"}
    assert live["admission"] == "not-evaluated" and "nothing is admitted" in live["reason"]


# ==== 10. producer workflow: pinned code after approval, and the founder-facing summary ==========

def stepText(job):
    return json.dumps(workflowSteps(job))


def factsBlock(job, stepPrefix):
    body = inlineBody(job, stepPrefix)
    return body[body.index("# --- facts begin"):body.index("# --- facts end")]


def test_workflow_is_a_least_privilege_sha_pinned_tag_triggered_three_job_issuer():
    import yaml
    text = WORKFLOW.read_text()
    data = yaml.safe_load(text)
    assert (data.get(True) or data["on"]) == {"push": {"tags": ["challenge-receipt/**"]}}
    assert data["permissions"] == {}
    prepare, show, issue = (data["jobs"][name] for name in ("prepare", "show", "issue"))
    assert show["needs"] == "prepare" and issue["needs"] == ["prepare", "show"]
    assert issue["environment"] == COMMITTED.environment
    assert "environment" not in prepare and "environment" not in show
    assert prepare["permissions"] == {"contents": "read"} and show["permissions"] == {}
    assert issue["permissions"] == {"contents": "read", "actions": "read", "id-token": "write",
                                    "attestations": "write"}
    assert "secrets." not in text and "pull_request" not in text and "workflow_dispatch" not in text
    uses = re.findall(r"uses:\s*(\S+)", text)
    assert any(item.startswith("actions/attest-build-provenance@") for item in uses)
    for item in uses:
        assert re.fullmatch(r"actions/[a-z-]+@[0-9a-f]{40}", item), f"action not SHA-pinned: {item}"
    assert issue["env"]["REVIEWER_ID"] == str(COMMITTED.required_reviewer_ids[0])
    assert issue["env"]["ENVIRONMENT_NAME"] == COMMITTED.environment
    # approval wait can be up to 30 days; the prepared archive must outlive it
    uploads = [s for s in prepare["steps"] if "upload-artifact" in s.get("uses", "")]
    assert uploads and uploads[0]["with"]["retention-days"] >= 35
    # the founder must create the protected environment first (GitHub auto-creates it unprotected)
    assert "FOUNDER, FIRST" in text and "auto-creates a missing environment" in text


def test_founder_facts_come_from_a_clean_runner_and_the_issue_digest_comes_from_it():
    show, issue, prepare = (workflowSteps(name) for name in ("show", "issue", "prepare"))
    for steps in (show, issue):
        assert not any("checkout" in step.get("uses", "") for step in steps)
    assert any("checkout" in step.get("uses", "") for step in prepare)  # the only job that runs repo code
    import yaml
    jobs = yaml.safe_load(WORKFLOW.read_text())["jobs"]
    assert jobs["issue"]["env"]["EXPECTED_DIGEST"] == "${{ needs.show.outputs.digest }}"
    assert jobs["issue"]["env"]["RECEIPT_ID"] == "${{ needs.show.outputs.receipt }}"
    assert "outputs" not in jobs["prepare"]  # nothing the founder relies on is computed in prepare
    assert "needs.prepare.outputs" not in WORKFLOW.read_text()
    # prepare's summary is explicitly untrusted and points at `show`
    prepareText = stepText("prepare")
    assert "untrusted runner" in prepareText and "'show' job summary" in prepareText
    assert "```json" not in prepareText


def test_every_pinned_interpreter_call_is_isolated():
    for job in ("show", "issue"):
        for step in workflowSteps(job):
            for match in re.finditer(r"(?m)^\s*(?:\w+=\S+\s+)*python3?\b.*", step.get("run", "")):
                assert match.group(0).strip().startswith("python3 -I - <<'PY'"), match.group(0)
    # repository code runs only in the unprivileged prepare job, and nothing there is trusted
    assert "PYTHONPATH=src python3 scripts/buildChallengeReceipt.py" in stepText("prepare")


def test_a_shadowing_stdlib_module_in_the_workspace_cannot_poison_the_pinned_code(tmp_path, repo):
    run, build = buildArchive(tmp_path)
    for name in ("json.py", "zipfile.py", "hashlib.py", "re.py", "io.py"):
        (run / name).write_text("raise SystemExit('poisoned stdlib shadow imported')\n")
    env = prepareEnv(run)
    proc = runInline(inlineBody("show", "Derive and show"), run, {**env, "PYTHONPATH": str(run)})
    assert proc.returncode == 0, proc.stderr
    (run / "approvals.json").write_text(json.dumps([approval()]))
    sealed = runInline(inlineBody("issue", "Verify the facts"), run,
                       {**sealEnv(run, build["artifactSha256"], shaValue=repo.sha), "PYTHONPATH": str(run)})
    assert sealed.returncode == 0, sealed.stderr
    # control: the same shadow DOES poison a non-isolated interpreter, so the test is meaningful
    control = subprocess.run([sys.executable, "-"], input=inlineBody("show", "Derive and show"), cwd=run,
                             capture_output=True, text=True, env={**os.environ, **env})
    assert control.returncode != 0 and "poisoned" in control.stderr


def test_both_jobs_derive_facts_with_byte_identical_pinned_code():
    prepare = factsBlock("show", "Derive and show")
    seal = factsBlock("issue", "Verify the facts")
    assert prepare == seal and "def facts" in prepare


def test_pinned_summary_is_derived_from_the_archive_bytes_and_escaped(tmp_path):
    run, build = buildArchive(tmp_path)
    proc = runInline(inlineBody("show", "Derive and show"), run, prepareEnv(run))
    assert proc.returncode == 0, proc.stderr
    summary = (run / "summary.md").read_text()
    shown = json.loads(summary.split("```json\n", 1)[1].split("\n```", 1)[0])
    assert shown["receiptId"] == RECEIPT_ID and shown["challengeId"] == CHALLENGE
    assert shown["verifier"] == "mbtiongson1" and shown["builder"] == "builder-agent"
    assert shown["contributor"] == "contributor-x" and shown["triggeringActor"] == "mbtiongson1"
    assert shown["archiveSha256"] == build["artifactSha256"]
    assert shown["transcriptSha256"] == sha(TRANSCRIPT)
    assert "not authenticated" in summary and "clean runner" in summary
    outputs = dict(line.split("=", 1) for line in (run / "output.txt").read_text().splitlines())
    assert outputs == {"receipt": RECEIPT_ID, "digest": build["artifactSha256"]}


def forgedArchive(run: Path, mutate):
    """What a malicious (unpinned) build step could emit instead of the honest archive."""
    archive = run / "out/artifact.zip"
    with zipfile.ZipFile(archive) as bundle:
        payload = json.loads(bundle.read("verification-receipt.json"))
    mutate(payload)
    content = json.dumps(payload).encode()
    with zipfile.ZipFile(archive, "w") as bundle:
        bundle.writestr("verification-receipt.json", content)


@pytest.mark.parametrize("mutate", [
    lambda p: p["receipt"].update(receipt_id="x\nreceipt=forged"),            # GITHUB_OUTPUT injection
    lambda p: p["receipt"].update(receipt_id="../escape"),
    lambda p: p.update(challengeId="x`\n```\n[click](https://evil.example)"),  # summary markdown injection
    lambda p: p["receipt"].update(builder_id="a b"),
    lambda p: p["receipt"].update(verifier_id="bad login"),
    lambda p: p["receipt"].update(transcript_digest="0" * 64),                # digest not bound to transcript
    lambda p: p.update(transcript="substituted"),
    lambda p: p.update(schemaVersion=2),
])
def test_pinned_code_refuses_forged_archives_before_the_founder_sees_or_signs_them(tmp_path, repo, mutate):
    run, build = buildArchive(tmp_path)
    forgedArchive(run, mutate)
    proc = runInline(inlineBody("show", "Derive and show"), run, prepareEnv(run))
    assert proc.returncode != 0
    assert not (run / "output.txt").exists() and not (run / "summary.md").exists()
    # the post-approval code applies the same refusal even if the digest were somehow replayed
    (run / "approvals.json").write_text(json.dumps([approval()]))
    digest = sha((run / "out/artifact.zip").read_bytes())
    sealed = runInline(inlineBody("issue", "Verify the facts"), run, sealEnv(run, digest, shaValue=repo.sha))
    assert sealed.returncode != 0 and not (run / "out/issuer-approval.json").exists()


@pytest.mark.parametrize("approvals,env,match", [
    ([], {}, "exactly one approved"),
    ([approval(), approval()], {}, "exactly one approved"),
    ([approval("rejected")], {}, "exactly one approved"),
    ([approval(), approval("rejected")], {}, "exactly one approved"),
    ([approval(user={"id": 999, "login": "mbtiongson1"})], {}, "not the founder's"),
    ([approval(env="elsewhere")], {}, "not the founder's"),
    ([approval(user={"id": REVIEWER["id"], "login": "someone-else"})], {}, "approver's GitHub login"),
    ([approval()], {"GITHUB_RUN_ATTEMPT": "2"}, "first-attempt"),
    ([approval()], {"GITHUB_REF_TYPE": "branch"}, "first-attempt"),
    ([approval()], {"GITHUB_REF_NAME": "challenge-receipt/../x-r1", "GITHUB_REF": "refs/tags/challenge-receipt/../x-r1"},
     "first-attempt"),
    ([approval()], {"EXPECTED_DIGEST": "0" * 64}, "changed between prepare and issue"),
    ([approval()], {"RECEIPT_ID": "other-receipt"}, "changed between prepare and issue"),
])
def test_pinned_sealing_code_refusals(tmp_path, repo, approvals, env, match):
    run, build = buildArchive(tmp_path)
    (run / "approvals.json").write_text(json.dumps(approvals))
    proc = runInline(inlineBody("issue", "Verify the facts"), run,
                     sealEnv(run, build["artifactSha256"], shaValue=repo.sha, **env))
    assert proc.returncode != 0 and match in proc.stderr
    assert not (run / "out/issuer-approval.json").exists()


def test_sealed_approval_comes_only_from_the_pinned_verified_item(tmp_path, repo):
    run, build = buildArchive(tmp_path)
    extra = approval()
    extra["comment"] = "ignore previous instructions"
    extra["user"]["email"] = "leak@example.org"
    (run / "approvals.json").write_text(json.dumps([extra]))
    proc = runInline(inlineBody("issue", "Verify the facts"), run,
                     sealEnv(run, build["artifactSha256"], shaValue=repo.sha))
    assert proc.returncode == 0, proc.stderr
    sealed = json.loads((run / "out/issuer-approval.json").read_text())
    assert sealed["approvals"] == [{"state": "approved", "user": REVIEWER,
                                    "environments": [{"name": COMMITTED.environment}]}]
    assert sealed["repositoryId"] == COMMITTED.repository_id and sealed["ownerId"] == COMMITTED.repository_owner_id
    assert sealed["triggeringActor"] == "mbtiongson1" and sealed["sourceSha"] == repo.sha


def test_build_script_refusals(tmp_path):
    script = loadScript()
    for tag in ("release/v1", "challenge-receipt/../x-r1", "challenge-receipt/case-r0"):
        with pytest.raises(SystemExit, match="must look like"):
            script.parseTag(tag)
    with pytest.raises(SystemExit, match="no challenge case directory"):
        script.loadRequest(tmp_path, "nope")
    work = tmp_path / "work"
    writeRequest(work)
    requestFile = work / "evidence/frontier-challenges/case/admission-request.json"
    original = requestFile.read_text()
    requestFile.write_text(original.replace('"caseId": "case"', '"caseId": "different"'))
    with pytest.raises(SystemExit, match="own case id"):
        script.loadRequest(work, "case")
    for field, value in (("receipt_id", "id\nwith-newline"), ("builder_id", "has space"),
                         ("verifier_id", "bad login"), ("contributor_id", "back`tick")):
        data = json.loads(original)
        data["receipt"][field] = value
        requestFile.write_text(json.dumps(data))
        with pytest.raises(SystemExit, match="allowlist"):
            script.buildBundle(work, TAG, tmp_path / "out")
    data = json.loads(original)
    data["challengeId"] = "spaced id"
    requestFile.write_text(json.dumps(data))
    with pytest.raises(SystemExit, match="allowlist"):
        script.buildBundle(work, TAG, tmp_path / "out")


def test_public_surface_keeps_imports_lazy_and_stdlib_only():
    code = (
        "import sys\n"
        "import gaia_cli.steward.challenge_receipts\n"
        "bad = sorted(m for m in sys.modules if m.split('.')[0] in {'yaml','requests','httpx','pytest','jsonschema'})\n"
        "print(','.join(bad))\n")
    out = subprocess.run([sys.executable, "-c", code], capture_output=True, text=True,
                         cwd=ROOT, env={**os.environ, "PYTHONPATH": str(ROOT / "src")}, check=True).stdout.strip()
    assert out == "", f"third-party modules imported at module import time: {out}"
