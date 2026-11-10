#!/usr/bin/env python3
"""Assemble import-ready Arbor source records from the Arbor I seed manifest.

This is a campaign-local authoring aid, not a new Arbor contract. It reads
`seed.json` (the reviewable authoring source), pins every skill to the exact
bytes of its canonical record in this checkout, and writes
`gaia.arbor-expert-declaration/v1` and `gaia.arbor-edge-declaration/v1` records
under `records/`. Admission still goes through `gaia dev arbor import`; this
script never writes into `registry/arbor/`.

    python founder/reports/arbor-i-seed-2026-11-10/seed/assemble.py            # write records/
    python founder/reports/arbor-i-seed-2026-11-10/seed/assemble.py --check    # records == store?

Re-issue under a different authority (the PR #2036 pattern: same claims, a
human adopter as the named authority) with `--authority-actor`,
`--authority-basis` and `--declared-at`. Claim text is never altered by those
flags, so a re-issue differs from the seed only in `authority` and
`declaredAt`.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[3]
sys.path.insert(0, str(ROOT / "src"))

from gaia_cli.arbor import (  # noqa: E402
    DECLARATION_SCHEMA,
    EDGE_DECLARATION_SCHEMA,
    SOURCE_DIRECTORIES,
    canonicalBytes,
    canonicalSkillPath,
    contentDigest,
    validateRecord,
)


class SeedError(RuntimeError):
    pass


def currentPin(skillId: str) -> str:
    return hashlib.sha256(canonicalSkillPath(skillId, ROOT).read_bytes()).hexdigest()


def pinned(seed: dict, skillId: str) -> dict:
    """Return the endpoint pin, refusing a manifest that drifted from canon."""

    entry = seed["skills"].get(skillId)
    if entry is None:
        raise SeedError(f"{skillId} is used by the seed but has no skills entry")
    actual = currentPin(skillId)
    if entry["canonicalSha256"] != actual:
        raise SeedError(
            f"{skillId}: canonical record changed since the seed was written "
            f"(seed {entry['canonicalSha256'][:12]}, checkout {actual[:12]}). "
            "Re-read the record and the upstream source, then update the seed."
        )
    return {"id": skillId, "contentSha256": actual}


def sourceLine(entry: dict) -> str:
    upstream = entry.get("upstream")
    if upstream is None:
        return "No upstream instruction file was read for this endpoint."
    return (
        f"{upstream['repo']}@{upstream['commit']}:{upstream['path']} "
        f"(sha256 {upstream['sha256']}; the canonical record links ref "
        f"'{upstream['linkRef']}')"
    )


def authorityFor(seed: dict, sources: list[str], lines: str, override: dict | None) -> dict:
    if override is not None:
        return override
    template = seed["authority"]
    basis = template["basis"].format(sources="; ".join(sources), lines=lines)
    return {"actor": template["actor"], "basis": basis}


def buildRecords(seed: dict, override: dict | None, declaredAt: str | None) -> dict[str, dict]:
    declaredAt = declaredAt or seed["declaredAt"]
    records: dict[str, dict] = {}
    for skillId, entry in sorted(seed["skills"].items()):
        claims = entry.get("claims") or []
        if not claims:
            continue
        record = {
            "schema": DECLARATION_SCHEMA,
            "declarationId": entry["declarationId"],
            "declaredAt": declaredAt,
            "skill": pinned(seed, skillId),
            "claims": [
                {
                    "id": claim["id"],
                    "facet": claim["facet"],
                    "conditions": claim["conditions"],
                    "rationale": claim["rationale"],
                    "authority": authorityFor(
                        seed, [sourceLine(entry)], claim["lines"], override
                    ),
                }
                for claim in claims
            ],
        }
        validateRecord(record, ROOT)
        records[f"declarations/{skillId.replace('/', '__')}.json"] = record

    for edge in seed["edges"]:
        fromEntry = seed["skills"][edge["from"]]
        toEntry = seed["skills"][edge["to"]]
        record = {
            "schema": EDGE_DECLARATION_SCHEMA,
            "declarationId": edge["declarationId"],
            "declaredAt": declaredAt,
            "pair": {"from": pinned(seed, edge["from"]), "to": pinned(seed, edge["to"])},
            "claims": [
                {
                    "id": claim["id"],
                    "relation": claim["relation"],
                    "conditions": claim["conditions"],
                    "rationale": claim["rationale"],
                    "authority": authorityFor(
                        seed,
                        [
                            "from: " + sourceLine(fromEntry),
                            "to: " + sourceLine(toEntry),
                        ],
                        claim["lines"],
                        override,
                    ),
                }
                for claim in edge["claims"]
            ],
        }
        validateRecord(record, ROOT)
        records[f"edge-declarations/{edge['declarationId']}.json"] = record
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--check", action="store_true", help="verify records/ and the store match the seed")
    parser.add_argument("--authority-actor")
    parser.add_argument("--authority-basis")
    parser.add_argument("--declared-at")
    parser.add_argument("--out", default=str(HERE / "records"))
    args = parser.parse_args()

    if bool(args.authority_actor) != bool(args.authority_basis):
        parser.error("--authority-actor and --authority-basis must be given together")
    override = (
        {"actor": args.authority_actor, "basis": args.authority_basis}
        if args.authority_actor
        else None
    )

    seed = json.loads((HERE / "seed.json").read_text(encoding="utf-8"))
    try:
        records = buildRecords(seed, override, args.declared_at)
    except SeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    out = Path(args.out)
    failures = 0
    for relative, record in sorted(records.items()):
        path = out / relative
        text = json.dumps(record, indent=2, sort_keys=True, ensure_ascii=False) + "\n"
        digest = contentDigest(record)
        stored = (
            ROOT / "registry" / "arbor" / "sources"
            / SOURCE_DIRECTORIES[record["schema"]] / f"{digest}.json"
        )
        if args.check:
            onDisk = path.read_text(encoding="utf-8") if path.is_file() else None
            inStore = stored.is_file() and stored.read_bytes() == canonicalBytes(record) + b"\n"
            state = "ok" if (onDisk == text and inStore) else "MISMATCH"
            failures += state != "ok"
            print(f"{state:8} {digest[:12]} {relative}"
                  f"{'' if onDisk == text else ' [records/ differs]'}"
                  f"{'' if inStore else ' [not in store]'}")
        else:
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(text, encoding="utf-8")
            print(f"wrote    {digest[:12]} {relative}")
    return 1 if failures else 0


if __name__ == "__main__":
    raise SystemExit(main())
