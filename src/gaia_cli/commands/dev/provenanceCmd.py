"""`gaia dev provenance <skill-id>` — write the RFC3 §3.1 provenance sidecar.

Writes ``registry/provenance/<skill-id>.json`` at ingest, back-linking the
registry node to its discovery packet, intake batch, intake issue, crawler
origin, and evidence seed. Closes GAP10 (no back-link node -> upstream markers)
and GAP11 (crawler provenance dropped).

Ungated (writes a sidecar under ``registry/provenance/``, not canonical node
frontmatter) — consistent with ``gaia dev prefill`` / ``gaia dev evidence-seed``.

``--from-packet`` reads a discovery packet and lifts its ``source`` block into
``crawlerOrigin`` (and, when unset, its path into ``discoveryPacket``), so the
crawler provenance the packet captured is preserved automatically.
"""

import json
import sys
from pathlib import Path

from gaia_cli.provenance import (
    buildProvenanceLedger,
    crawlerOriginFromPacket,
    writeProvenanceLedger,
)


def provenanceCommand(args):
    """Entry point for ``gaia dev provenance``."""
    skillId = args.skill_id.lstrip("/")
    registryPath = args.registry

    crawlerOrigin = None
    discoveryPacket = getattr(args, "discovery_packet", None)
    fromPacket = getattr(args, "from_packet", None)
    if fromPacket:
        packetPath = Path(fromPacket)
        try:
            packet = json.loads(packetPath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: could not read --from-packet {fromPacket}: {exc}", file=sys.stderr)
            return 1
        crawlerOrigin = crawlerOriginFromPacket(packet)
        if crawlerOrigin is None:
            print(
                f"Warning: --from-packet {fromPacket} carried no source block; "
                "crawlerOrigin left empty.",
                file=sys.stderr,
            )
        if not discoveryPacket:
            discoveryPacket = fromPacket

    try:
        ledger = buildProvenanceLedger(
            skillId,
            genericSkillRef=getattr(args, "generic_ref", None),
            discoveryPacket=discoveryPacket,
            intakeBatch=getattr(args, "intake_batch", None),
            intakeIssue=getattr(args, "intake_issue", None),
            crawlerOrigin=crawlerOrigin,
            evidenceSeed=getattr(args, "evidence_seed", None),
            ingestedAt=getattr(args, "ingested_at", None),
            status=getattr(args, "status", "ingested"),
        )
        path = writeProvenanceLedger(ledger, registryPath)
    except ValueError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    print(f"Wrote provenance ledger for '{skillId}' -> {path}")
    return 0
