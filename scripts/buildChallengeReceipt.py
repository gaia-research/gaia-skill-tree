#!/usr/bin/env python3
"""Build the challenge-receipt archive for ``challenge-receipt-issuer.yml`` (``prepare`` job).

Turns ``evidence/frontier-challenges/<case>/admission-request.json`` into ``artifact.zip``.
This is repository code that runs UNPRIVILEGED; it authorizes nothing. The workflow's pinned
inline code re-derives every fact from the archive bytes, shows them to the founder, and is
the only code that runs after approval. Verification happens later in
``gaia_cli.steward.challenge_receipts``.

Admission request (``schemaVersion`` 1)::

    {"schemaVersion": 1, "caseId": "<dir name>", "challengeId": "...",
     "contextDigest": "<64 hex>", "proofSourceSha": "<40|64 hex git commit>",
     "transcriptPath": "<file inside the case directory>",
     "receipt": {<every gaia_cli.challengeDomain.VerificationReceipt field>},
     "notificationRef": "<optional; defaults to receipt.notice_ref>"}

The receipt's ``verifier_id`` must be the GitHub login of the approver. Identifier fields
must match the workflow's allowlist (letters, digits and ``._:/@+-``; no spaces or
backticks). Builder/contributor independence is declared here, not authenticated.
Standard library only; run with ``PYTHONPATH=src``.
"""
from __future__ import annotations

import argparse
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
    BUNDLE_ARTIFACT,
    EVIDENCE_ROOT,
    RECEIPT_ID_RE,
    make_artifact_archive,
    make_receipt_payload,
)

TAG_RE = re.compile(r"^challenge-receipt/([a-z0-9][a-z0-9-]{0,62})-r([1-9][0-9]{0,2})$")
FIELD_RE = re.compile(r"[A-Za-z0-9._:/@+-]{1,200}")
LOGIN_RE = re.compile(r"[A-Za-z0-9-]{1,39}")
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
    if not RECEIPT_ID_RE.fullmatch(receipt.receipt_id) or not LOGIN_RE.fullmatch(receipt.verifier_id):
        raise SystemExit("receipt id or verifier id is outside the workflow allowlist")
    for name in ("challengeId",):
        if not FIELD_RE.fullmatch(str(request.get(name, ""))):
            raise SystemExit(f"{name} is outside the workflow allowlist")
    for value in (receipt.builder_id, receipt.contributor_id, receipt.result):
        if not FIELD_RE.fullmatch(value):
            raise SystemExit("builder, contributor or result is outside the workflow allowlist")
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = parser.add_subparsers(dest="command", required=True)
    build = sub.add_parser("build", help="package the receipt archive for a tag")
    build.add_argument("--tag", required=True)
    build.add_argument("--out", type=Path, required=True)
    build.add_argument("--repo-root", type=Path, default=ROOT)
    args = parser.parse_args(argv)
    result = buildBundle(args.repo_root, args.tag, args.out)
    print(f"built {args.out / BUNDLE_ARTIFACT} for receipt {result['receiptId']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
