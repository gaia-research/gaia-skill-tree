"""Read-only evidence discovery for ``trust_evidence_gap`` findings (#2201, ruling 11A).

A named skill whose effective evidence pool is empty (or holds only rows that
score nothing) is not degraded; it is unmeasured. Founder rulings 2026-10-28 and
2026-11-06 say Steward looks for the missing evidence instead of demoting, and
that this looking is bounded and read-only.

This module is the whole routine, and it is deliberately small:

* **It never searches.** Searching is a driver's job (an agent with web access,
  an operator). The driver hands over a *search log*: every search it ran, with
  its results. Steward's code only validates that log, annotates it, and writes
  a receipt. The same stance as ``scripts/steward_collect_*.py``.
* **It records negatives.** A search that found nothing is a first-class record
  (query, channel, date, zero results), because "we looked and found none" is
  the evidence that makes a gap confirmable.
* **It never admits.** A candidate's admissibility is an annotation for a
  Verifier, with reasons. The receipt carries ``admittedEvidence: []`` and
  ``ratingChange: null`` unconditionally, preserves the current level, and the
  search-log schema is strict: a log that tries to carry an admission, a level
  or a trust value is rejected, not ignored.
* **It writes only ignored local state** (``.gaia/steward/discovery/``), never
  ``registry/``. Admitting a discovered row is a separate, governed
  ``gaia dev evidence`` call by an authorized Verifier.

Everything is deterministic given the same log, registry and ``generatedAt``.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Mapping, Sequence
from urllib.parse import urlsplit, urlunsplit

from gaia_cli.steward.models import content_hash, stable_json

DISCOVERY_SCHEMA = "steward-evidence-discovery-v1"
DISCOVERY_RELATIVE_DIR = ".gaia/steward/discovery"
STATE_ROOT = ".gaia/steward"

# Bounds. A routine that can be handed an unbounded log is not a bounded routine.
maxSearches = 12
maxResultsPerSearch = 10
maxTextLength = 500

# The families of source a discovery pass is expected to cover for one skill.
# A pass that skips one still records, as a limitation, that it was not searched.
channelFamilies = ("upstream-repo", "benchmarks", "papers", "releases-usage")
freshWindowDays = 365
agingWindowDays = 1095

_logKeys = {"skillId", "searchedBy", "searches"}
_searchKeys = {"query", "channel", "searchedAt", "results"}
_resultKeys = {"url", "title", "evidenceType", "attribution", "publishedAt", "note"}
_skillId = re.compile(r"[a-z0-9][a-z0-9._-]*/[a-z0-9][a-z0-9._-]*")

# Evidence types whose admission needs more than a URL.
_needsReview = {
    "github-stars-own": "repository stars are not proof of capability by default",
    "self-attestation": "self-attestation is not independent evidence",
    "benchmark-result": "benchmark-result rows are catalog-gated; record a benchmark-source candidate first",
    "social-signal": "social signal needs a verified view floor and creator provenance",
}


class DiscoveryError(ValueError):
    """The search log is not a shape the discovery routine accepts."""


@dataclass(frozen=True)
class DiscoveryTarget:
    skillId: str
    preservedLevel: str
    evidenceBasis: str
    effectiveRowCount: int
    suggestedChannels: tuple[str, ...] = channelFamilies

    def toDict(self) -> dict[str, Any]:
        return {
            "skillId": self.skillId,
            "preservedLevel": self.preservedLevel,
            "evidenceBasis": self.evidenceBasis,
            "effectiveRowCount": self.effectiveRowCount,
            "suggestedChannels": list(self.suggestedChannels),
            "maxSearches": maxSearches,
            "maxResultsPerSearch": maxResultsPerSearch,
        }


def canonicalUrl(url: str) -> str:
    """Normalize a URL for duplicate comparison only (never for storage)."""

    parts = urlsplit(url.strip())
    path = parts.path.rstrip("/")
    return urlunsplit((parts.scheme.lower(), parts.netloc.lower(), path, parts.query, ""))


def _text(value: Any, where: str, *, required: bool = False) -> str | None:
    if value is None:
        if required:
            raise DiscoveryError(f"{where} is required")
        return None
    if not isinstance(value, str) or not value.strip():
        raise DiscoveryError(f"{where} must be a non-empty string")
    if len(value) > maxTextLength:
        raise DiscoveryError(f"{where} exceeds {maxTextLength} characters")
    return value.strip()


def _timestamp(value: Any, where: str) -> str:
    text = _text(value, where, required=True)
    assert text is not None
    try:
        datetime.fromisoformat(text.replace("Z", "+00:00"))
    except ValueError as exc:
        raise DiscoveryError(f"{where} must be an ISO 8601 timestamp") from exc
    return text


def _publishedDate(value: Any, where: str) -> date | None:
    text = _text(value, where)
    if text is None:
        return None
    try:
        return date.fromisoformat(text[:10])
    except ValueError as exc:
        raise DiscoveryError(f"{where} must be an ISO 8601 date") from exc


def _rejectUnknown(mapping: Mapping[str, Any], allowed: set[str], where: str) -> None:
    unknown = sorted(set(mapping) - allowed)
    if unknown:
        # A log that carries an admission, a level or a trust value is refused
        # outright: this routine has no authority to receive one.
        raise DiscoveryError(f"{where} has unsupported field(s) {unknown}; discovery records searches only")


def effectiveEvidenceSnapshot(repoRoot: Path, skillId: str) -> dict[str, Any]:
    """Read-only effective-evidence view of one named skill (own rows plus inherited)."""

    from gaia_cli.registryMaps import buildMergedSkillMap
    from gaia_cli.trustMagnitude import (
        computeOverallTrustGradeFromSkill,
        computeRowArtifactScores,
        computeTrustMagnitude,
    )

    context = buildMergedSkillMap(repoRoot)
    skill = context.get(skillId)
    if skill is None or skill.get("status") != "named":
        raise DiscoveryError(f"named skill not found: {skillId}")
    rows = [
        {
            "source": row.get("source") or row.get("url") or "",
            "type": row.get("type") or "",
            "layer": row.get("_layer") or row.get("layer") or "",
            "score": round(float(score), 3),
        }
        for row, score in computeRowArtifactScores(skill, context)
        if not row.get("_autoDerived")
    ]
    return {
        "level": skill.get("level"),
        "trustMagnitude": round(computeTrustMagnitude(skill, context), 2),
        "trustGrade": computeOverallTrustGradeFromSkill(skill, context),
        "effectiveRows": rows,
    }


def discoveryTargets(repoRoot: Path, observedAt: str) -> tuple[DiscoveryTarget, ...]:
    """The skills with an open evidence gap, from the sensor. Read-only."""

    from gaia_cli.steward.sensors import TrustCalibrationDriftSensor

    targets = []
    for observation in TrustCalibrationDriftSensor().scan(repoRoot, observedAt):
        if observation.kind != "trust_evidence_gap" or observation.status != "drift":
            continue
        state = observation.observed_state
        targets.append(DiscoveryTarget(
            skillId=observation.subject.id,
            preservedLevel=str(state.get("preservedLevel") or observation.current_state.get("level")),
            evidenceBasis=str(state.get("evidenceBasis")),
            effectiveRowCount=int(state.get("effectiveRowCount", 0)),
        ))
    return tuple(sorted(targets, key=lambda item: item.skillId))


def _freshness(published: date | None, today: date) -> dict[str, Any]:
    if published is None:
        return {"class": "unknown", "ageDays": None}
    age = (today - published).days
    if age < 0:
        return {"class": "unknown", "ageDays": age, "note": "published date is in the future"}
    label = "fresh" if age <= freshWindowDays else "aging" if age <= agingWindowDays else "stale"
    return {"class": label, "ageDays": age}


def _admissibility(
    result: Mapping[str, Any],
    *,
    validTypes: Sequence[str],
    duplicateOf: str | None,
) -> dict[str, Any]:
    reasons: list[str] = []
    state = "admissible-candidate"
    url = result["url"]
    if urlsplit(url).scheme not in ("http", "https") or not urlsplit(url).netloc:
        return {"state": "inadmissible", "reasons": ["url is not an http(s) address"]}
    if duplicateOf is not None:
        return {"state": "inadmissible", "reasons": [f"duplicate of {duplicateOf}"]}
    evidenceType = result.get("evidenceType")
    if evidenceType is None:
        state = "needs-review"
        reasons.append("no evidence type proposed")
    elif evidenceType not in validTypes:
        return {"state": "inadmissible", "reasons": [f"unknown evidence type {evidenceType!r}"]}
    elif evidenceType in _needsReview:
        state = "needs-review"
        reasons.append(_needsReview[evidenceType])
    if not result.get("attribution"):
        state = "needs-review" if state != "inadmissible" else state
        reasons.append("no attribution recorded")
    if not reasons:
        reasons.append("typed, attributed, not a duplicate: a Verifier may propose it; Steward admits nothing")
    return {"state": state, "reasons": reasons}


def buildDiscoveryReceipt(
    log: Mapping[str, Any],
    *,
    repoRoot: Path,
    generatedAt: str,
) -> dict[str, Any]:
    """Validate a search log and turn it into an admission-free discovery receipt."""

    from gaia_cli.grading import load_evidence_types

    if not isinstance(log, Mapping):
        raise DiscoveryError("search log must be an object")
    _rejectUnknown(log, _logKeys, "search log")
    skillId = _text(log.get("skillId"), "skillId", required=True)
    assert skillId is not None
    if not _skillId.fullmatch(skillId):
        raise DiscoveryError("skillId must be a named skill id (contributor/skill)")
    searchedBy = _text(log.get("searchedBy"), "searchedBy", required=True)
    generatedTimestamp = _timestamp(generatedAt, "generatedAt")
    today = datetime.fromisoformat(generatedTimestamp.replace("Z", "+00:00")).date()
    searches = log.get("searches")
    if not isinstance(searches, list) or not searches:
        raise DiscoveryError("searches must be a non-empty list: a pass that searched nothing proves nothing")
    if len(searches) > maxSearches:
        raise DiscoveryError(f"at most {maxSearches} searches per receipt; split the pass")

    snapshot = effectiveEvidenceSnapshot(repoRoot, skillId)
    existing = {canonicalUrl(row["source"]): row["source"] for row in snapshot["effectiveRows"] if row["source"]}
    validTypes = load_evidence_types(str(repoRoot))

    seen: dict[str, str] = {}
    records: list[dict[str, Any]] = []
    channelsSearched: set[str] = set()
    for index, search in enumerate(searches):
        where = f"searches[{index}]"
        if not isinstance(search, Mapping):
            raise DiscoveryError(f"{where} must be an object")
        _rejectUnknown(search, _searchKeys, where)
        channel = _text(search.get("channel"), f"{where}.channel", required=True)
        if channel not in channelFamilies:
            raise DiscoveryError(f"{where}.channel must be one of {list(channelFamilies)}")
        channelsSearched.add(channel)
        results = search.get("results")
        if not isinstance(results, list):
            raise DiscoveryError(f"{where}.results must be a list (empty for a negative search)")
        if len(results) > maxResultsPerSearch:
            raise DiscoveryError(f"{where}.results exceeds {maxResultsPerSearch}")
        candidates: list[dict[str, Any]] = []
        for position, result in enumerate(results):
            rwhere = f"{where}.results[{position}]"
            if not isinstance(result, Mapping):
                raise DiscoveryError(f"{rwhere} must be an object")
            _rejectUnknown(result, _resultKeys, rwhere)
            url = _text(result.get("url"), f"{rwhere}.url", required=True)
            assert url is not None
            normalized = canonicalUrl(url)
            duplicateOf = existing.get(normalized) or seen.get(normalized)
            if duplicateOf is None:
                seen[normalized] = url
            parsed = {
                "url": url,
                "title": _text(result.get("title"), f"{rwhere}.title"),
                "evidenceType": _text(result.get("evidenceType"), f"{rwhere}.evidenceType"),
                "attribution": _text(result.get("attribution"), f"{rwhere}.attribution"),
                "note": _text(result.get("note"), f"{rwhere}.note"),
            }
            published = _publishedDate(result.get("publishedAt"), f"{rwhere}.publishedAt")
            candidates.append({
                **{key: value for key, value in parsed.items() if value is not None},
                "publishedAt": published.isoformat() if published else None,
                "freshness": _freshness(published, today),
                "duplicate": {
                    "isDuplicate": duplicateOf is not None,
                    "of": duplicateOf,
                    "scope": (
                        "existing-effective-evidence" if normalized in existing
                        else "earlier-candidate" if duplicateOf is not None else None
                    ),
                },
                "admissibility": _admissibility(parsed, validTypes=validTypes, duplicateOf=duplicateOf),
            })
        records.append({
            "query": _text(search.get("query"), f"{where}.query", required=True),
            "channel": channel,
            "searchedAt": _timestamp(search.get("searchedAt"), f"{where}.searchedAt"),
            "outcome": "positive" if candidates else "negative",
            "resultCount": len(candidates),
            "candidates": candidates,
        })

    states = [item["admissibility"]["state"] for record in records for item in record["candidates"]]
    admissible = states.count("admissible-candidate")
    unresolved = states.count("needs-review")
    notSearched = [family for family in channelFamilies if family not in channelsSearched]
    limitations = [f"channel family not searched: {family}" for family in notSearched]
    receipt: dict[str, Any] = {
        "schemaVersion": DISCOVERY_SCHEMA,
        "readOnly": True,
        "skillId": skillId,
        "generatedAt": generatedTimestamp,
        "searchedBy": searchedBy,
        # Unconditional: this routine has no authority to change either.
        "admittedEvidence": [],
        "ratingChange": None,
        "preservedLevel": snapshot["level"],
        "effectiveEvidence": snapshot,
        "searches": records,
        "coverage": {
            "searchesAttempted": len(records),
            "positive": sum(1 for record in records if record["outcome"] == "positive"),
            "negative": sum(1 for record in records if record["outcome"] == "negative"),
            "admissibleCandidates": admissible,
            "needsReviewCandidates": unresolved,
            "channelsSearched": sorted(channelsSearched),
            "channelsNotSearched": notSearched,
            "limitations": limitations,
        },
        "outcome": (
            "candidates-found" if admissible
            else "candidates-need-review" if unresolved
            else "evidence-gap-confirmed"
        ),
        "nextStep": (
            "A Verifier reviews the admissible candidates and, if they qualify, admits them with "
            "`gaia dev evidence`; the rating is then recomputed. Steward admitted nothing."
            if admissible else
            "No candidate is admissible yet, but some need review (typing, attribution, catalog gating or "
            "independence). The gap is NOT confirmed: a Verifier resolves them first. Steward admitted nothing."
            if unresolved else
            "No admissible or reviewable candidate was found. Keep the current rating and report the gap; a "
            "demotion needs counter-evidence or supersession under #2148, never an empty pool."
        ),
    }
    receipt["receiptId"] = f"discovery-{content_hash({k: v for k, v in receipt.items() if k != 'receiptId'})[:20]}"
    return receipt


def writeDiscoveryReceipt(repoRoot: Path, receipt: Mapping[str, Any]) -> tuple[Path, bool]:
    """Publish a receipt under ignored local Steward state; never under ``registry/``."""

    from gaia_cli.steward.receipts import StateError, ensure_local_state_path

    root = repoRoot.resolve()
    stateRoot = root / STATE_ROOT
    directory = root / DISCOVERY_RELATIVE_DIR
    ensure_local_state_path(root, stateRoot, directory)
    directory.mkdir(parents=True, exist_ok=True)
    slug = re.sub(r"[^a-z0-9]+", "-", str(receipt["skillId"]).lower()).strip("-")[:48]
    path = directory / f"{slug}-{receipt['receiptId']}.json"
    ensure_local_state_path(root, stateRoot, path)
    content = (stable_json(dict(receipt)) + "\n").encode("utf-8")
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        if path.read_bytes() != content:
            raise StateError(f"immutable discovery receipt collision at {path}") from None
        return path, False
    try:
        view = memoryview(content)
        while view:
            written = os.write(descriptor, view)
            view = view[written:]
        os.fsync(descriptor)
    finally:
        os.close(descriptor)
    return path, True


def nowIso() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
