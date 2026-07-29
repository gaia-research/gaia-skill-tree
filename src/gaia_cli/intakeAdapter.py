"""Packet -> intake-YAML adapter (RFC2 Gap B, §3.3).

Reads a review-ready ``discovery-packet-v2`` (RFC1 output, from
``registry-for-review/discovery-packets/``) and produces the intake mapping that
``gaia push --from-file`` consumes (a top-level ``skills:`` list — see
``commands/pushFromFile.py``). This closes the dead end between curation and
``gaia push``: the review-ready packet becomes an intake proposal that opens the
L4 topology-ratification issue.

Mapping (RFC2 §3.3):

- The adapter runs only after the human appends ``l4Resolution``. That block is
  the authoritative vendor-neutral generic identity, exact named identity, and
  upstream ``blob/.../SKILL.md`` provenance; none is inferred from discovery.
- ``decision.value == MAP`` -> the ratified generic id must match both the
  decision and frozen generic snapshot (Axis A satisfied).
- ``decision.value == NEW_GENERIC`` -> the ratified generic identity replaces
  the vendor/candidate slug and carries any fusion prerequisites (Axis B).
- ``suite`` block -> the intake carries ``suiteId`` + ``role`` +
  ``componentCandidateIds`` so the fan-out is reconstructable, and derives
  ``attributionScope`` from ``role`` (``capstone`` -> ``suite-wide``,
  ``component`` -> ``suite-component``, else ``standalone``).

The adapter carries the intake *reference*, never a throwaway star/grade/tier
estimate: Stage-1 minimum-effort evidence (RFC2-A ``stageOneEvidence.py``) is
already written as real rows, so the intake attribution here is provenance, not
a strength claim. It emits a packet digest receipt for packet→batch→issue
traceability. TM and rank are derived canonically at appraisal time.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from urllib.parse import urlparse


PACKET_CONTRACT_VERSION = "discovery-packet-v2"
HANDOFF_CONTRACT_VERSION = "curation-handoff-v1"
SKILL_ID_RE = re.compile(r"^[a-z][a-z0-9]*(-[a-z0-9]+)*$")


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
    """Legacy helper retained for callers that normalize candidate locators."""
    return str(candidateId).replace("/", "-").strip().lower()


def _canonicalDigest(value):
    encoded = json.dumps(value, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _packetDigest(packet):
    return _canonicalDigest(packet)


def _isExactSkillBlob(url):
    """Accept only a GitHub blob URL whose final path segment is SKILL.md."""
    try:
        parsed = urlparse(url)
    except Exception:
        return False
    return (
        parsed.scheme == "https"
        and parsed.netloc.lower() in ("github.com", "www.github.com")
        and "/blob/" in parsed.path
        and parsed.path.rstrip("/").endswith("/SKILL.md")
    )


def validateL4Resolution(packet):
    """Validate the explicit human-ratified packet -> intake handoff.

    Discovery fields are never reinterpreted here. The resolution must name the
    vendor-neutral generic, the canonical named implementation, and the exact
    upstream SKILL.md blob. The packet's embedded frozen generic snapshot is
    digest-checked; MAP resolutions must select the same existing generic.
    """
    errors = []
    if packet.get("lifecycle", [])[-1:] != ["review-ready"]:
        errors.append("packet lifecycle must end at review-ready")

    resolution = packet.get("l4Resolution")
    if not isinstance(resolution, dict) or resolution.get("status") != "approved":
        return ["explicit l4Resolution.status=approved is required"]

    generic = resolution.get("generic")
    named = resolution.get("named")
    if not isinstance(generic, dict):
        errors.append("l4Resolution.generic is required")
        generic = {}
    if not isinstance(named, dict):
        errors.append("l4Resolution.named is required")
        named = {}

    genericId = generic.get("id", "")
    if not SKILL_ID_RE.fullmatch(genericId):
        errors.append("l4Resolution.generic.id must be a vendor-neutral kebab-case id")
    if not str(generic.get("name", "")).strip():
        errors.append("l4Resolution.generic.name is required")
    if len(str(generic.get("description", "")).strip()) < 10:
        errors.append("l4Resolution.generic.description must be at least 10 characters")
    genericType = generic.get("type")
    prerequisites = generic.get("prerequisites")
    if genericType not in ("basic", "fusion"):
        errors.append("l4Resolution.generic.type must be basic or fusion")
    elif genericType == "basic" and prerequisites not in ([], None):
        errors.append("a basic l4Resolution.generic must have no prerequisites")
    elif genericType == "fusion" and (
        not isinstance(prerequisites, list)
        or not prerequisites
        or any(not SKILL_ID_RE.fullmatch(str(item)) for item in prerequisites)
    ):
        errors.append("a fusion l4Resolution.generic requires kebab-case prerequisites")

    contributor = named.get("contributor", "")
    skillName = named.get("skillName", "")
    if not str(contributor).strip() or "/" in str(contributor):
        errors.append("l4Resolution.named.contributor is required")
    if not SKILL_ID_RE.fullmatch(str(skillName)):
        errors.append("l4Resolution.named.skillName must be kebab-case")
    if not _isExactSkillBlob(resolution.get("skillFileUrl", "")):
        errors.append("l4Resolution.skillFileUrl must be an exact GitHub blob URL ending in SKILL.md")

    snapshot = packet.get("genericSnapshot")
    options = packet.get("mappingOptions")
    if not isinstance(snapshot, dict) or not isinstance(snapshot.get("generics"), list):
        errors.append("a frozen genericSnapshot is required")
    else:
        if snapshot.get("command") != "gaia dev list --generic --json":
            errors.append("genericSnapshot.command is not canonical")
        if snapshot.get("contentSha256") != _canonicalDigest(snapshot["generics"]):
            errors.append("genericSnapshot.contentSha256 does not match its frozen generics")
        if snapshot.get("mappingOptionsSha256") != _canonicalDigest(options or []):
            errors.append("genericSnapshot.mappingOptionsSha256 does not match mappingOptions")

    decision = packet.get("decision") or {}
    if decision.get("value") == "MAP":
        optionIds = {
            row.get("genericId") for row in (options or []) if isinstance(row, dict)
        }
        if decision.get("genericId") not in optionIds:
            errors.append("MAP decision.genericId is absent from mappingOptions")
        if genericId != decision.get("genericId"):
            errors.append("MAP l4Resolution.generic.id must match decision.genericId")
        snapshotIds = {
            row.get("id") for row in (snapshot or {}).get("generics", [])
            if isinstance(row, dict) and row.get("kind") == "generic"
        }
        if genericId not in snapshotIds:
            errors.append("MAP l4Resolution.generic.id is absent from the frozen snapshot")
    elif decision.get("value") != "NEW_GENERIC":
        errors.append("only MAP or NEW_GENERIC packets are intake-eligible")
    return errors


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

    resolutionErrors = validateL4Resolution(packet)
    if resolutionErrors:
        raise ValueError("invalid post-L4 handoff: " + "; ".join(resolutionErrors))

    resolution = packet["l4Resolution"]
    generic = resolution["generic"]
    named = resolution["named"]
    skillFileUrl = resolution["skillFileUrl"]

    entry = {
        "id": generic["id"],
        "candidateId": packet.get("candidateId", ""),
        "name": generic["name"],
        "description": generic["description"],
    }

    if skillFileUrl:
        # Attribution reference only — provenance, not a strength claim. The
        # skill_file_url points reviewers at the source; type=attributed because
        # the packet describes an upstream source discovered by the crawl.
        entry["attribution"] = {
            "skill_file_url": skillFileUrl,
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
                "url": skillFileUrl,
                "notes": "Source reference from discovery packet (unverified; "
                "Stage-1 minimum-effort evidence written separately).",
            }
        ]

    if value == "MAP":
        # Axis A satisfied: reference the existing generic. No new topology.
        genericId = decision.get("genericId")
        if not genericId:
            raise ValueError("MAP packet is missing decision.genericId")
        entry["type"] = generic["type"]
        entry["prerequisites"] = list(generic.get("prerequisites") or [])
        entry["mapsToGeneric"] = genericId
    else:  # NEW_GENERIC
        entry["type"] = generic["type"]
        entry["prerequisites"] = list(generic.get("prerequisites") or [])

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

    entry["named"] = {
        "contributor": named["contributor"],
        "skill_name": named["skillName"],
        "links_github": skillFileUrl,
    }

    return entry


def buildIntakeYaml(packets, packetPath=None):
    """Build the intake mapping (``{'skills': [...]}``) from packet dict(s).

    Accepts a single packet dict or an iterable of packet dicts (e.g. a suite
    fan-out: component packets + a capstone packet). Only MAP / NEW_GENERIC
    review-ready packets yield entries; others raise via :func:`buildIntakeSkill`.

    Returns a mapping with a top-level ``skills`` list, exactly what
    ``pushFromFile._load_yaml_file`` expects.
    """
    if isinstance(packets, dict):
        packets = [packets]
    packets = list(packets)
    skills = [buildIntakeSkill(p) for p in packets]
    refs = []
    for packet in packets:
        ref = {
            "candidateId": packet.get("candidateId", ""),
            "packetContentSha256": _packetDigest(packet),
            "sourceContentSha256": (packet.get("source") or {}).get("contentSha256"),
        }
        if packetPath and len(packets) == 1:
            ref["packetPath"] = packetPath
        refs.append({key: value for key, value in ref.items() if value})
    return {
        "skills": skills,
        "curationHandoff": {
            "contractVersion": HANDOFF_CONTRACT_VERSION,
            "packetRefs": refs,
        },
    }


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
