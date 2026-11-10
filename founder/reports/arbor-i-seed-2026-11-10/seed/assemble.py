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
    python founder/reports/arbor-i-seed-2026-11-10/seed/assemble.py --list-digests

Attribution follows the founder ruling of 2026-11-11: the owner of the canonical
skill is the primary attribution and the drafting agent is the supporting
author. The owner comes from each canonical record's `contributor` field, as
recorded in `seed.json`. An edge whose two endpoints have different owners needs
its own attribution wording and is refused here.
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


def claimAuthority(seed: dict, entry: dict, lines: str) -> dict:
    template = seed["authority"]
    return {
        "actor": template["claimActor"].format(
            owner=entry["owner"], supportingAuthor=template["supportingAuthor"]
        ),
        "basis": template["basis"].format(
            lead=template["basisLead"]["claim"].format(sources=sourceLine(entry), lines=lines)
        ),
    }


def edgeAuthority(seed: dict, fromEntry: dict, toEntry: dict, lines: str) -> dict:
    if fromEntry["owner"] != toEntry["owner"]:
        raise SeedError(
            "an edge between skills with different owners needs its own attribution wording"
        )
    template = seed["authority"]
    sources = "from: " + sourceLine(fromEntry) + "; to: " + sourceLine(toEntry)
    return {
        "actor": template["edgeActor"].format(
            owners=fromEntry["owner"], supportingAuthor=template["supportingAuthor"]
        ),
        "basis": template["basis"].format(
            lead=template["basisLead"]["edge"].format(sources=sources, lines=lines)
        ),
    }


def buildRecords(seed: dict, declaredAt: str | None) -> dict[str, dict]:
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
                    "authority": claimAuthority(seed, entry, claim["lines"]),
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
                    "authority": edgeAuthority(seed, fromEntry, toEntry, claim["lines"]),
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
    parser.add_argument(
        "--list-digests",
        action="store_true",
        help="print the store-relative source path of every seed record, for removal before a re-issue",
    )
    parser.add_argument("--declared-at")
    parser.add_argument("--out", default=str(HERE / "records"))
    args = parser.parse_args()

    seed = json.loads((HERE / "seed.json").read_text(encoding="utf-8"))
    try:
        records = buildRecords(seed, args.declared_at)
    except SeedError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    if args.list_digests:
        for _relative, record in sorted(records.items()):
            print(f"{SOURCE_DIRECTORIES[record['schema']]}/{contentDigest(record)}.json")
        return 0

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
