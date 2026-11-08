#!/usr/bin/env python3
"""Prefill credential disposition records for humans and verifiers (#2283).

``draft <debtId>`` rescans the checkout and emits one record skeleton per live
finding of that debt, with path, line (informational), pattern, fingerprint,
occurrence and the stable-source-context hash prefilled. The debt id may be
the file's ``credential_leak`` or ``credential_review`` debt; records always
carry the stable ``credential_leak`` id. It never sets policy, disposition,
evidence or author (a builder's judgement), nor verifiedBy, verifiedAt or
verificationReceipt (an independent verifier's attestation, stamped by the
lead's integrate step from a recorded agent.verify outcome). A skeleton is inert, because the Steward
consumer rejects any record with an empty field, so drafting cannot resolve or
exempt anything.

    python scripts/steward_credential_disposition.py draft <debtId>
    python scripts/steward_credential_disposition.py draft <debtId> --write
    python scripts/steward_credential_disposition.py hash <record.json>

``hash`` prints the reviewed-content sha256 a verification receipt must list for
a record (the record without verifiedBy, verifiedAt and verificationReceipt).

Default output is a JSON array on stdout. ``--write`` creates one file per
finding under founder/steward/security-dispositions/ and refuses to overwrite.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPOROOT = Path(__file__).resolve().parents[1]
if str(REPOROOT / "src") not in sys.path:
    sys.path.insert(0, str(REPOROOT / "src"))

from gaia_cli.steward import credentialDispositions as records  # noqa: E402
from gaia_cli.steward.sensors_security import SecretScanSensor, _SecretTally  # noqa: E402


def draftRecords(root: Path, debtId: str, observedAt: str = "1970-01-01T00:00:00Z") -> list[dict]:
    """Return skeletons for every current finding of ``debtId``; raise LookupError if none."""

    scan = SecretScanSensor().scan_detailed(root, observedAt)
    subject = next(
        (
            item.subject.id
            for item in scan.observations
            if item.debt_id == debtId or records.reviewDebtId(item.subject.id) == debtId
        ),
        None,
    )
    leak = next(
        (item for item in scan.observations if item.subject.id == subject and item.kind == "credential_leak"),
        None,
    )
    if subject is None or leak is None:
        raise LookupError(f"no credential finding currently produces {debtId}")
    data = (root / subject).read_bytes()
    located = SecretScanSensor._locate(subject, data.decode("utf-8", errors="replace"), _SecretTally())
    findings = [item.finding for item in located]
    return [
        {
            "schemaVersion": records.RECORDSCHEMA,
            "debtId": leak.debt_id,
            "path": subject,
            "line": item.finding["line"],
            "pattern": item.finding["pattern"],
            "fingerprint": item.finding["fingerprint"],
            "occurrence": index,
            "contextSha256": item.contextHash,
            "policy": "",
            "disposition": "",
            "evidence": "",
            "author": "",
            "verifiedBy": "",
            "verifiedAt": "",
            "verificationReceipt": "",
            "founderRuling": records.RULINGID,
        }
        for item, index in zip(located, records.occurrences(findings))
    ]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    draft = commands.add_parser("draft", help="prefill record skeletons for one debt id")
    draft.add_argument("debtId")
    draft.add_argument("--root", type=Path, default=REPOROOT)
    draft.add_argument("--write", action="store_true", help="write one file per finding instead of printing")
    digest = commands.add_parser("hash", help="print the reviewed-content sha256 of one record file")
    digest.add_argument("record", type=Path)
    args = parser.parse_args(argv)
    if args.command == "hash":
        try:
            print(records.contentSha256(json.loads(args.record.read_text(encoding="utf-8"))))
        except (OSError, ValueError, AttributeError) as exc:
            print(f"cannot hash {args.record}: {exc}", file=sys.stderr)
            return 1
        return 0
    root = args.root.resolve()
    try:
        skeletons = draftRecords(root, args.debtId)
    except LookupError as exc:
        print(str(exc), file=sys.stderr)
        return 1
    if not args.write:
        print(json.dumps(skeletons, indent=2))
        return 0
    target = root / records.RECORDDIR
    target.mkdir(parents=True, exist_ok=True)
    for skeleton in skeletons:
        out = target / records.recordName(skeleton["debtId"], skeleton["fingerprint"], skeleton["occurrence"])
        if out.exists():
            print(f"refusing to overwrite {out.relative_to(root)}", file=sys.stderr)
            return 1
        out.write_text(json.dumps(skeleton, indent=2) + "\n", encoding="utf-8")
        print(out.relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
