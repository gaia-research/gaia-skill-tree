"""Provenance sidecar ledger writer (RFC3 §3.1, GAP10 + GAP11).

At ingest, ``gaia`` writes ``registry/provenance/<skill-id>.json`` — a ledger
separate from the registry node (NO ``skill.schema.json`` change) that links the
node back to every upstream marker in the pipeline:

    discovery packet -> intake batch -> intake issue -> crawler origin -> evidence seed

``crawlerOrigin`` closes GAP11 by carrying the ``source`` provenance the
discovery packet already captured (``sourceLane``, ``canonicalUrl``,
``contentSha256``), which was previously dropped at ingest.

The ledger also codifies the RFC3 §3.4 status ladder (``discovered ->
review-ready -> intake-open -> evidence-seeded -> in-appraisal -> ingested``,
with ``deferred``/``rejected`` terminal off-ramps). Pre-ingest states have no
node, so the ladder lives here rather than on the node ``status`` enum.

Optionally, the ledger carries a ``timeline[]`` array — the pre-ingest stage
event log (RFC3 §3.2, GAP1 + GAP3). Because discovery/intake stage events have
no node/tree target before ingest, ``gaia dev timeline`` cannot write them; the
ledger's own event log is the sanctioned home. This is NOT a node-timeline
entry, so it is not a fabricated frontmatter entry.

Ungated (writes a sidecar under ``registry/provenance/``, not canonical node
frontmatter) — consistent with ``gaia dev prefill`` / ``gaia dev evidence-seed``.
"""

from __future__ import annotations

import json
import os
from pathlib import Path


# The RFC3 §3.4 status ladder, in pipeline order. Kept in lockstep with the
# enum in provenance.schema.json. deferred/rejected are terminal off-ramps.
STATUS_LADDER = (
    "discovered",
    "review-ready",
    "intake-open",
    "evidence-seeded",
    "in-appraisal",
    "ingested",
)
TERMINAL_STATES = ("deferred", "rejected")
VALID_STATUSES = STATUS_LADDER + TERMINAL_STATES

# Pre-ingest stage timeline actions the ledger event log accepts (RFC3 §3.2).
STAGE_ACTIONS = ("discovered", "intake_opened")

CRAWLER_ORIGIN_KEYS = ("sourceLane", "canonicalUrl", "contentSha256")


def provenanceDir(registryPath) -> Path:
    """Return the registry/provenance directory for a registry root."""
    return Path(registryPath) / "registry" / "provenance"


def provenanceLedgerPath(skillId, registryPath) -> Path:
    """Return the sidecar ledger path for a skill id.

    The skill id may contain a ``/`` (named skills are ``contributor/slug``);
    the ``/`` is preserved as a nested path so a contributor's ledgers group
    together, mirroring the ``registry/named/<contributor>/`` layout.
    """
    return provenanceDir(registryPath) / f"{skillId}.json"


def crawlerOriginFromPacket(packet):
    """Extract the crawlerOrigin block from a discovery packet's source.

    Returns a dict with only the present keys (sourceLane / canonicalUrl /
    contentSha256), or None when the packet carries no usable source. Closes
    GAP11 — the crawler provenance the packet captured is preserved at ingest.
    """
    if not isinstance(packet, dict):
        return None
    source = packet.get("source")
    if not isinstance(source, dict):
        return None
    origin = {}
    for key in CRAWLER_ORIGIN_KEYS:
        value = source.get(key)
        if isinstance(value, str) and value.strip():
            origin[key] = value
    return origin or None


def buildProvenanceLedger(
    skillId,
    *,
    genericSkillRef=None,
    discoveryPacket=None,
    intakeBatch=None,
    intakeIssue=None,
    crawlerOrigin=None,
    evidenceSeed=None,
    ingestedAt=None,
    status="ingested",
    timeline=None,
):
    """Build a provenance-ledger dict (RFC3 §3.1 shape).

    Only ``skillId`` and ``status`` are required; every back-link is optional so
    a ledger can be written even when an upstream marker is unknown. ``status``
    defaults to ``ingested`` (the ladder terminal reached when the ledger is
    written at ingest time).
    """
    if not isinstance(skillId, str) or not skillId.strip():
        raise ValueError("skillId is required and must be a non-empty string.")
    if status not in VALID_STATUSES:
        raise ValueError(
            f"status {status!r} is not on the ladder; expected one of "
            f"{', '.join(VALID_STATUSES)}."
        )

    ledger = {"skillId": skillId, "status": status}
    if genericSkillRef:
        ledger["genericSkillRef"] = genericSkillRef
    if discoveryPacket:
        ledger["discoveryPacket"] = discoveryPacket
    if intakeBatch:
        ledger["intakeBatch"] = intakeBatch
    if intakeIssue:
        ledger["intakeIssue"] = intakeIssue
    if crawlerOrigin:
        ledger["crawlerOrigin"] = {
            key: crawlerOrigin[key]
            for key in CRAWLER_ORIGIN_KEYS
            if key in crawlerOrigin
        }
    if evidenceSeed:
        ledger["evidenceSeed"] = evidenceSeed
    if ingestedAt:
        ledger["ingestedAt"] = ingestedAt
    if timeline:
        ledger["timeline"] = list(timeline)
    return ledger


def _loadProvenanceSchema(registryPath):
    """Load provenance.schema.json from the registry root, or None if absent."""
    schemaPath = (
        Path(registryPath) / "registry" / "schema" / "provenance.schema.json"
    )
    if not schemaPath.exists():
        return None
    try:
        return json.loads(schemaPath.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None


def validateProvenanceLedger(ledger, registryPath):
    """Validate a ledger against provenance.schema.json (CLI Pre-Flight Rule).

    Returns a list of error strings (empty when valid). When jsonschema or the
    schema file is unavailable, falls back to a minimal structural check so the
    invariant is still enforced before writing.
    """
    errors = []
    if not isinstance(ledger, dict):
        return ["ledger must be a JSON object."]
    if not ledger.get("skillId"):
        errors.append("ledger is missing required field 'skillId'.")
    if ledger.get("status") not in VALID_STATUSES:
        errors.append(
            f"ledger status {ledger.get('status')!r} is not on the status ladder."
        )

    schema = _loadProvenanceSchema(registryPath)
    if schema is None:
        return errors
    try:
        import jsonschema
    except ImportError:
        return errors
    try:
        jsonschema.validate(instance=ledger, schema=schema)
    except jsonschema.ValidationError as exc:
        errors.append(f"schema error: {exc.message}")
    return errors


def writeProvenanceLedger(ledger, registryPath):
    """Validate then write a provenance ledger to its sidecar path.

    CLI Pre-Flight Rule: the ledger is validated against provenance.schema.json
    BEFORE it is written; an invalid ledger raises ValueError rather than
    landing a bad state on disk.
    """
    errors = validateProvenanceLedger(ledger, registryPath)
    if errors:
        raise ValueError(
            "provenance ledger failed validation:\n  - "
            + "\n  - ".join(errors)
        )
    path = provenanceLedgerPath(ledger["skillId"], registryPath)
    os.makedirs(path.parent, exist_ok=True)
    path.write_text(
        json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return path
