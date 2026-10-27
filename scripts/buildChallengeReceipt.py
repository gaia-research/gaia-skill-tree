#!/usr/bin/env python3
"""Build and seal the challenge-receipt bundle for ``challenge-receipt-issuer.yml``.

``build`` turns ``evidence/frontier-challenges/<case>/admission-request.json`` into the
receipt archive (``artifact.zip``) the issuer attests; ``seal`` records the environment
approvals observed by the run into ``issuer-approval.json``. Neither step authorizes
anything: authorization is the attested workflow identity plus the authenticated
approval, both verified later by ``gaia_cli.steward.challenge_receipts``.

Admission request (``schemaVersion`` 1)::

    {"schemaVersion": 1, "caseId": "<dir name>", "challengeId": "...",
     "contextDigest": "<64 hex>", "proofSourceSha": "<40|64 hex git commit>",
     "transcriptPath": "<file inside the case directory>",
     "receipt": {<every gaia_cli.challengeDomain.VerificationReceipt field>},
     "notificationRef": "<optional; defaults to receipt.notice_ref>"}

The receipt's ``verifier_id`` must be the GitHub login of the authenticated approver.
Standard library only; run with ``PYTHONPATH=src``.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT / "src") not in sys.path:
    sys.path.insert(0, str(ROOT / "src"))

from gaia_cli.challengeDomain import VerificationReceipt  # noqa: E402
from gaia_cli.steward.challenge_receipts import (  # noqa: E402
    BUNDLE_APPROVAL,
    BUNDLE_ARTIFACT,
    EVIDENCE_ROOT,
    GitHubActionsSource,
    ReceiptUnavailable,
    loadTrustedConfig,
    make_artifact_archive,
    make_receipt_payload,
)

TAG_RE = re.compile(r"^challenge-receipt/([a-z0-9][a-z0-9-]{0,62})-r([1-9][0-9]{0,2})$")
BUILD_FILE = "build.json"


def parseTag(tag: str) -> tuple[str, int]:
    match = TAG_RE.fullmatch(tag)
    if not match:
        raise SystemExit(f"tag {tag!r} must look like challenge-receipt/<case>-r<n>")
    return match.group(1), int(match.group(2))


def loadRequest(root: Path, caseId: str) -> tuple[dict, bytes]:
    caseDir = (root / EVIDENCE_ROOT / caseId).resolve()
    if not caseDir.is_relative_to((root / EVIDENCE_ROOT).resolve()) or not caseDir.is_dir():
        raise SystemExit(f"no challenge case directory for {caseId!r}")
    request = json.loads((caseDir / "admission-request.json").read_text(encoding="utf-8"))
    if request.get("schemaVersion") != 1 or request.get("caseId") != caseId:
        raise SystemExit("admission request must be schemaVersion 1 and name its own case id")
    transcript = (caseDir / request["transcriptPath"]).resolve()
    if not transcript.is_relative_to(caseDir) or not transcript.is_file():
        raise SystemExit("transcriptPath must be a file inside the case directory")
    return request, transcript.read_bytes()


def buildBundle(root: Path, tag: str, out: Path) -> dict:
    caseId, _ = parseTag(tag)
    request, transcript = loadRequest(root, caseId)
    receipt = VerificationReceipt(**request["receipt"])
    payload = make_receipt_payload(
        receipt, challenge_id=request["challengeId"], context_digest=request["contextDigest"],
        raw_transcript=transcript, notification_ref=request.get("notificationRef", receipt.notice_ref),
        source_sha=request["proofSourceSha"])
    archive, payloadDigest = make_artifact_archive(payload)
    out.mkdir(parents=True, exist_ok=True)
    (out / BUNDLE_ARTIFACT).write_bytes(archive)
    build = {
        "tag": tag, "caseId": caseId, "receiptId": receipt.receipt_id,
        "challengeId": request["challengeId"], "artifactSha256": hashlib.sha256(archive).hexdigest(),
        "payloadDigest": payloadDigest, "verifier": receipt.verifier_id,
        "builder": receipt.builder_id, "contributor": receipt.contributor_id,
    }
    (out / BUILD_FILE).write_text(json.dumps(build, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return build


def sealBundle(out: Path, tag: str, approvals: list, *, repository: str, sourceSha: str, runId: int,
               runAttempt: int, actor: str, expectedDigest: str | None) -> dict:
    build = json.loads((out / BUILD_FILE).read_text(encoding="utf-8"))
    archive = (out / BUNDLE_ARTIFACT).read_bytes()
    digest = hashlib.sha256(archive).hexdigest()
    if build["tag"] != tag or build["artifactSha256"] != digest or (expectedDigest and digest != expectedDigest):
        raise SystemExit("receipt archive changed between prepare and issue; refusing to seal")
    config = loadTrustedConfig()
    if repository != config.repository:
        raise SystemExit("workflow repository is not the configured trusted repository")
    items = [{"state": item.get("state"), "user": {"id": item["user"]["id"], "login": item["user"]["login"]},
              "environments": [{"name": env.get("name")} for env in item.get("environments", [])]}
             for item in approvals]
    try:
        approved = GitHubActionsSource()._authenticate_approval(
            {"id": runId, "attempt": runAttempt, "environment": config.environment}, items, config)
    except ReceiptUnavailable as exc:
        raise SystemExit(f"approval refused: {exc}") from exc
    if approved["reviewer"] != build["verifier"]:
        raise SystemExit("receipt verifier_id must be the authenticated approver's GitHub login")
    sealed = {
        "schemaVersion": 1, "kind": "challenge-receipt-issuer-approval", "repository": repository,
        "environment": config.environment, "workflowPath": config.workflow_path, "tag": tag,
        "ref": f"refs/tags/{tag}", "sourceSha": sourceSha, "runId": runId, "runAttempt": runAttempt,
        "caseId": build["caseId"], "receiptId": build["receiptId"], "challengeId": build["challengeId"],
        "artifactSha256": digest, "payloadDigest": build["payloadDigest"], "builder": build["builder"],
        "contributor": build["contributor"], "triggeringActor": actor, "approvals": items,
        "sealedAtUtc": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    (out / BUNDLE_APPROVAL).write_text(json.dumps(sealed, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return sealed


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="package the receipt archive for a tag")
    seal = sub.add_parser("seal", help="seal the observed environment approvals")
    for command in (build, seal):
        command.add_argument("--tag", required=True)
        command.add_argument("--out", type=Path, required=True)
    build.add_argument("--repo-root", type=Path, default=ROOT)
    seal.add_argument("--approvals", type=Path, required=True)
    seal.add_argument("--repository", required=True)
    seal.add_argument("--sha", required=True)
    seal.add_argument("--run-id", type=int, required=True)
    seal.add_argument("--run-attempt", type=int, required=True)
    seal.add_argument("--actor", required=True)
    seal.add_argument("--expected-digest")
    args = parser.parse_args(argv)
    if args.command == "build":
        result = buildBundle(args.repo_root, args.tag, args.out)
        print("### Challenge receipt prepared (not yet issued)\n")
        print(f"- case: `{result['caseId']}`\n- receipt: `{result['receiptId']}`\n"
              f"- challenge: `{result['challengeId']}`\n- verifier (must be you): `{result['verifier']}`\n"
              f"- builder: `{result['builder']}`, contributor: `{result['contributor']}`\n"
              f"- artifact sha256: `{result['artifactSha256']}`\n"
              f"- payload digest: `{result['payloadDigest']}`\n\n"
              "Approve the `challenge-receipt-issuer` environment only if these facts are correct.")
    else:
        sealBundle(args.out, args.tag, json.loads(args.approvals.read_text(encoding="utf-8")),
                   repository=args.repository, sourceSha=args.sha, runId=args.run_id,
                   runAttempt=args.run_attempt, actor=args.actor, expectedDigest=args.expected_digest)
        print(f"sealed {args.out / BUNDLE_APPROVAL}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
