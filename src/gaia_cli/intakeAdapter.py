"""Packet -> intake-YAML adapter (RFC2 Gap B, §3.3).

Reads a review-ready ``discovery-packet-v2`` (RFC1 output, from
``registry-for-review/discovery-packets/``) and produces the intake mapping that
``gaia push --from-file`` consumes (a top-level ``skills:`` list — see
``commands/pushFromFile.py``). This closes the dead end between curation and
``gaia push``: the review-ready packet becomes an intake proposal that opens the
L4 topology-ratification issue.

Mapping (RFC2 §3.3):

- ``decision.value == MAP`` -> the intake references the existing
  ``decision.genericId`` (Axis A satisfied). No new topology is proposed; the
  intake entry carries the generic id and a ``basic`` structural type.
- ``decision.value == NEW_GENERIC`` -> the intake carries
  ``proposal.{name, description, type}``; when ``type == fusion`` it also carries
  ``proposal.prerequisites`` (Axis B) for L4 topology ratification.
- ``suite`` block -> the intake carries ``suiteId`` + ``role`` +
  ``componentCandidateIds`` so the fan-out is reconstructable, and derives
  ``attributionScope`` from ``role`` (``capstone`` -> ``suite-wide``,
  ``component`` -> ``suite-component``, else ``standalone``).

The adapter carries the intake *reference*, never a throwaway star/grade/tier
estimate: Stage-1 minimum-effort evidence (RFC2-A ``stageOneEvidence.py``) is
already written as real rows, so the intake attribution here is provenance, not
a strength claim. TM and rank are derived canonically at appraisal time.
"""

from __future__ import annotations

import json
import os


PACKET_CONTRACT_VERSION = "discovery-packet-v2"


def isDiscoveryPacket(data):
    """Return True when *data* is a discovery-packet-v2 mapping.

    Detection key is the ``contractVersion`` field — an intake YAML never
    carries it (its top level is ``skills:``), so this cleanly disambiguates a
    packet path from a plain intake-YAML path in ``gaia push --from-file``.
    """
    return (
        isinstance(data, dict)
        and data.get("contractVersion") == PACKET_CONTRACT_VERSION
    )


def attributionScopeForRole(role):
    """Derive an ``attributionScope`` from a suite ``role`` (RFC2 §3.3 / locked).

    ``capstone`` -> ``suite-wide`` (a capstone source speaks for the whole
    suite); ``component`` -> ``suite-component``; anything else (no suite) ->
    ``standalone``. A suite-wide source is NOT to be copied as full-strength
    proof across components downstream (enforced in the evidence-seed emitter).
    """
    if role == "capstone":
        return "suite-wide"
    if role == "component":
        return "suite-component"
    return "standalone"


def candidateSlug(candidateId):
    """Kebab-safe skill id for the intake entry.

    Packet ``candidateId`` may be ``contributor/slug``; the intake ``id`` must
    match ``^[a-z][a-z0-9]*(-[a-z0-9]+)*$`` (see ``pushFromFile.SKILL_ID_RE``),
    so ``/`` -> ``-`` and the value is lowercased. The full ``candidateId`` is
    still preserved verbatim on the entry (``candidateId`` key) for provenance.
    """
    return str(candidateId).replace("/", "-").strip().lower()


def buildIntakeSkill(packet):
    """Build a single intake ``skills[]`` entry from a review-ready packet.

    Returns the entry dict (top-level shape consumed by ``pushFromFile``). Raises
    ValueError when the packet is not review-ready or the decision is not a
    MAP / NEW_GENERIC (only those two reach intake — DEFER/DUPLICATE/NOT_A_SKILL
    never produce an intake entry).
    """
    decision = packet.get("decision") or {}
    value = decision.get("value")

    if value not in ("MAP", "NEW_GENERIC"):
        raise ValueError(
            f"packet decision.value={value!r} is not intake-eligible "
            "(only MAP or NEW_GENERIC produce an intake entry)"
        )

    source = packet.get("source") or {}
    frontmatter = source.get("frontmatter") or {}
    normalized = packet.get("normalized") or {}

    skillId = candidateSlug(packet.get("candidateId", ""))

    # Prefer normalized name/description, then parsed frontmatter, then proposal.
    name = (
        normalized.get("name")
        or frontmatter.get("name")
        or (decision.get("proposal") or {}).get("name")
        or ""
    )
    description = (
        normalized.get("description")
        or frontmatter.get("description")
        or (decision.get("proposal") or {}).get("description")
        or ""
    )

    entry = {
        "id": skillId,
        "candidateId": packet.get("candidateId", ""),
        "name": name,
        "description": description,
    }

    canonicalUrl = source.get("canonicalUrl")
    if canonicalUrl:
        # Attribution reference only — provenance, not a strength claim. The
        # skill_file_url points reviewers at the source; type=attributed because
        # the packet describes an upstream source discovered by the crawl.
        entry["attribution"] = {
            "skill_file_url": canonicalUrl,
            "type": "attributed",
        }
        # The intake validator (pushFromFile) requires >=1 evidence entry. The
        # packet carries no evidence rows — Stage-1 minimum-effort evidence
        # (RFC2-A stageOneEvidence.py) is written as REAL rows separately, and
        # the richer rows arrive post-L4 via the evidence-seed. So we emit one
        # provenance reference to the source repo, NOT a strength estimate.
        #
        # Vocabulary bridge: the intake evidence 'type' enum is DISTINCT from
        # the meta.json / evidence-seed type vocabulary. A discovered source
        # repository maps to the intake enum's 'repo'. Grade 'C' is the neutral
        # unverified-reference floor (the seed carries no authoritative grade;
        # TM/rank are derived at appraisal). This is a reference, not a claim.
        entry["evidence"] = [
            {
                "grade": "C",
                "type": "repo",
                "url": canonicalUrl,
                "notes": "Source reference from discovery packet (unverified; "
                "Stage-1 minimum-effort evidence written separately).",
            }
        ]

    if value == "MAP":
        # Axis A satisfied: reference the existing generic. No new topology.
        genericId = decision.get("genericId")
        if not genericId:
            raise ValueError("MAP packet is missing decision.genericId")
        entry["type"] = "basic"
        entry["prerequisites"] = []
        entry["mapsToGeneric"] = genericId
    else:  # NEW_GENERIC
        proposal = decision.get("proposal") or {}
        proposalType = proposal.get("type", "basic")
        entry["type"] = proposalType
        # Carry the proposal name/description explicitly (topology proposal).
        entry["name"] = entry["name"] or proposal.get("name", "")
        entry["description"] = entry["description"] or proposal.get("description", "")
        if proposalType == "fusion":
            prereqs = list(proposal.get("prerequisites") or [])
            if not prereqs:
                raise ValueError(
                    "NEW_GENERIC fusion proposal is missing prerequisites (Axis B)"
                )
            entry["prerequisites"] = prereqs
        else:
            entry["prerequisites"] = []

    # Suite fan-out (RFC1 suite block) -> intake suite ref + attributionScope.
    suite = packet.get("suite")
    if suite:
        role = suite.get("role")
        suiteBlock = {
            "suiteId": suite.get("suiteId"),
            "role": role,
        }
        if suite.get("componentCandidateIds"):
            suiteBlock["componentCandidateIds"] = list(
                suite["componentCandidateIds"]
            )
        entry["suite"] = suiteBlock
        entry["attributionScope"] = attributionScopeForRole(role)
    else:
        entry["attributionScope"] = attributionScopeForRole(None)

    return entry


def buildIntakeYaml(packets):
    """Build the intake mapping (``{'skills': [...]}``) from packet dict(s).

    Accepts a single packet dict or an iterable of packet dicts (e.g. a suite
    fan-out: component packets + a capstone packet). Only MAP / NEW_GENERIC
    review-ready packets yield entries; others raise via :func:`buildIntakeSkill`.

    Returns a mapping with a top-level ``skills`` list, exactly what
    ``pushFromFile._load_yaml_file`` expects.
    """
    if isinstance(packets, dict):
        packets = [packets]
    skills = [buildIntakeSkill(p) for p in packets]
    return {"skills": skills}


def loadPacketsFromPath(path):
    """Load one or more discovery packets from a path.

    *path* may be a single ``.json`` packet file or a directory of them
    (``registry-for-review/discovery-packets/``). Returns a list of packet
    dicts, sorted by file name for determinism. Non-packet JSON files in a
    directory are skipped; a single non-packet file raises ValueError.
    """
    if os.path.isdir(path):
        packets = []
        for fname in sorted(os.listdir(path)):
            if not fname.endswith(".json"):
                continue
            fpath = os.path.join(path, fname)
            with open(fpath, encoding="utf-8") as f:
                data = json.load(f)
            if isDiscoveryPacket(data):
                packets.append(data)
        return packets

    with open(path, encoding="utf-8") as f:
        data = json.load(f)
    if not isDiscoveryPacket(data):
        raise ValueError(
            f"'{path}' is not a discovery-packet-v2 "
            f"(missing contractVersion=={PACKET_CONTRACT_VERSION!r})"
        )
    return [data]
