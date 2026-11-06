#!/usr/bin/env python3
"""Prefill credential disposition records for humans and verifiers (#2283).

``draft <debtId>`` rescans the checkout and emits one record skeleton per live
finding of that debt, with path, line, pattern, fingerprint and the file sha256
filled in. It never sets policy, disposition, evidence, author, verifiedBy or
verifiedAt: those are a human's judgement and an independent verifier's
attestation. A skeleton is inert, because the Steward consumer rejects any record
with an empty field, so drafting cannot resolve or exempt anything.

    python scripts/steward_credential_disposition.py draft <debtId>
    python scripts/steward_credential_disposition.py draft <debtId> --write

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
    for observation in scan.observations:
        if observation.debt_id != debtId:
            continue
        rel = observation.subject.id
        data = (root / rel).read_bytes()
        findings = SecretScanSensor._findings(rel, data.decode("utf-8", errors="replace"), _SecretTally())
        sha = records.fileSha256(data)
        return [
            {
                "schemaVersion": records.RECORDSCHEMA,
                "debtId": debtId,
                "path": rel,
                "line": item["line"],
                "pattern": item["pattern"],
                "fingerprint": item["fingerprint"],
                "occurrence": index,
                "fileSha256": sha,
                "policy": "",
                "disposition": "",
                "evidence": "",
                "author": "",
                "verifiedBy": "",
                "verifiedAt": "",
                "founderRuling": records.RULINGID,
            }
            for item, index in zip(findings, records.occurrences(findings))
        ]
    raise LookupError(f"no credential finding currently produces {debtId}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    commands = parser.add_subparsers(dest="command", required=True)
    draft = commands.add_parser("draft", help="prefill record skeletons for one debt id")
    draft.add_argument("debtId")
    draft.add_argument("--root", type=Path, default=REPOROOT)
    draft.add_argument("--write", action="store_true", help="write one file per finding instead of printing")
    args = parser.parse_args(argv)
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
        out = target / records.recordName(
            skeleton["debtId"], skeleton["line"], skeleton["fingerprint"], skeleton["occurrence"]
        )
        if out.exists():
            print(f"refusing to overwrite {out.relative_to(root)}", file=sys.stderr)
            return 1
        out.write_text(json.dumps(skeleton, indent=2) + "\n", encoding="utf-8")
        print(out.relative_to(root).as_posix())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
