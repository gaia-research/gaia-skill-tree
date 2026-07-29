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

import hashlib
import json
import sys
from pathlib import Path

from gaia_cli.provenance import (
    appendStageEvent,
    buildProvenanceLedger,
    crawlerOriginFromPacket,
    writeProvenanceLedger,
)


def provenanceCommand(args):
    """Entry point for ``gaia dev provenance``."""
    skillId = args.skill_id.lstrip("/")
    registryPath = args.registry

    # RFC3 §3.2 — pre-ingest stage event. gaia dev timeline cannot target a
    # skill that has no node/tree yet, so the stage event lands on the ledger's
    # own timeline event log (not a node-timeline entry).
    stageEvent = getattr(args, "stage_event", None)
    if stageEvent:
        try:
            path = appendStageEvent(
                skillId,
                stageEvent,
                getattr(args, "notes", None),
                registryPath,
                timestamp=getattr(args, "timestamp", None),
            )
        except ValueError as exc:
            print(f"ERROR: {exc}", file=sys.stderr)
            return 1
        print(f"Appended '{stageEvent}' stage event for '{skillId}' -> {path}")
        return 0

    crawlerOrigin = None
    discoveryPacketSha256 = None
    intakeBatchId = None
    discoveryPacket = getattr(args, "discovery_packet", None)
    fromPacket = getattr(args, "from_packet", None)
    if fromPacket:
        packetPath = Path(fromPacket)
        try:
            packet = json.loads(packetPath.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"ERROR: could not read --from-packet {fromPacket}: {exc}", file=sys.stderr)
            return 1
        canonicalPacket = json.dumps(packet, sort_keys=True, separators=(",", ":")).encode("utf-8")
        discoveryPacketSha256 = hashlib.sha256(canonicalPacket).hexdigest()
        crawlerOrigin = crawlerOriginFromPacket(packet)
        if crawlerOrigin is None:
            print(
                f"Warning: --from-packet {fromPacket} carried no source block; "
                "crawlerOrigin left empty.",
                file=sys.stderr,
            )
        if not discoveryPacket:
            discoveryPacket = fromPacket

    intakeBatch = getattr(args, "intake_batch", None)
    if intakeBatch:
        try:
            intakeBatchId = json.loads(Path(intakeBatch).read_text(encoding="utf-8")).get("batchId")
        except (OSError, json.JSONDecodeError):
            intakeBatchId = None

    try:
        ledger = buildProvenanceLedger(
            skillId,
            genericSkillRef=getattr(args, "generic_ref", None),
            discoveryPacket=discoveryPacket,
            discoveryPacketSha256=discoveryPacketSha256,
            intakeBatch=intakeBatch,
            intakeBatchId=intakeBatchId,
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
