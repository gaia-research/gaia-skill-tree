"""Origin is automatic: the highest-merit named implementation in each bucket.

Founder rulings 2026-10-30 (EPIC #2189, ``founder/reports/yggdrasil-iv-october-2026/CAMPAIGN.md``):
"Origin is highest merit", "Remove manual work on origins, make them
automatic--only exceptions would be frozen contenders. Frozen skills lock the
TM and grade, and they can beat live ones. Highest merit only." and "I have no
rule about origins having a star requirement."

The rule, computed at build time and never stored by hand:

1. **Bucket.** Every named-skill record (``status: named`` or ``awakened``, at
   any star) competes in the bucket of its ``genericSkillRef``. Founder: "It is
   still the origin, it is just not 'named'."
2. **Merit.** Contenders are ordered by ``(published level, Trust Magnitude)``,
   both descending. The published level is the stored level capped by the
   grade ceiling (S→6★, A→4★, B→3★, C→2★, ungraded→1★), exactly as the named
   index publishes it. TM is compared at two decimals, as published. This is
   the merit order META §4.1 already used ("highest-rated named skill, ties
   broken by … Trust Score") and the one ``run_meta_sweep.py`` audited.
3. **No star floor.** A 1★ skill can be Origin. "Named" starts at 2★; Origin
   does not. (Redaction of ≤1★ handles is a separate display rule.)
4. **Frozen contenders** compete with their locked TM and grade
   (:mod:`gaia_cli.frozen`) and can beat live ones.
5. **Ties.** Every contender that shares the top merit key holds Origin
   (founder, 2026-10-30: "origin ties mean two are origin. Very rare edge case
   since tm is a real number."). There is no incumbent rule and no vacancy: a
   bucket with at least one contender always has at least one Origin.

``origin`` in frontmatter is a build-maintained mirror of this result, never an
input. The build rewrites it (except in frozen files). ``gaia dev update-named
--origin`` refuses: "No more manual. Automatic from now on." (2026-10-30).
"""

from __future__ import annotations

from typing import Iterable, Optional

from gaia_cli.redaction import level_num

GRADE_MAX_STARS = {"S": 6, "A": 4, "B": 3, "C": 2, "ungraded": 1}


def publishedLevelNumber(level, grade: Optional[str]) -> int:
    """Stored level capped by the Trust Grade ceiling (the level the index publishes)."""
    return min(level_num(level), GRADE_MAX_STARS.get(grade or "ungraded", 1))


def meritKey(levelNumber: int, tm: float) -> tuple[int, float]:
    """Merit order: published level, then Trust Magnitude (two decimals)."""
    return (int(levelNumber), round(float(tm or 0.0), 2))


def deriveBucketOrigins(contenders: Iterable[dict]) -> frozenset[str]:
    """Return the ids holding Origin among ``contenders`` (empty only when there are none).

    Each contender is ``{"id", "levelNumber", "tm"}``; ``levelNumber`` is already
    the published level. Every contender tied at the top merit key holds Origin.
    """
    pool = [c for c in contenders if c.get("id")]
    if not pool:
        return frozenset()
    keyed = [(meritKey(c.get("levelNumber", 0), c.get("tm", 0.0)), c["id"]) for c in pool]
    best = max(key for key, _ in keyed)
    return frozenset(sid for key, sid in keyed if key == best)


def deriveOrigins(buckets: dict[str, list[dict]]) -> dict[str, frozenset[str]]:
    """Map every bucket to its derived holders. ``buckets`` holds contender dicts."""
    return {ref: deriveBucketOrigins(entries) for ref, entries in buckets.items()}


# ---------------------------------------------------------------------------
# Registry-level derivation (CLI gates, leaderboard, audits)
# ---------------------------------------------------------------------------

CONTENDER_STATUSES = ("named", "awakened")


def _isContender(entry) -> bool:
    """A named-skill record that competes for its bucket's Origin (any star, named or awakened)."""
    return (
        isinstance(entry, dict)
        and bool(entry.get("genericSkillRef"))
        and bool(entry.get("contributor"))
        and entry.get("status", "named") in CONTENDER_STATUSES
    )


def awakenedRecords(registryPath=".") -> dict[str, dict]:
    """Awakened named-skill records, which ``buildMergedSkillMap`` leaves out.

    They compete for Origin ("It is still the origin, it is just not 'named'"),
    so registry-level callers add them to the contender pool with
    :func:`contenderPool`. They are not added to the Trust Magnitude map.
    """
    from pathlib import Path

    from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
    from gaia_cli.registry import named_skills_dir

    out: dict[str, dict] = {}
    namedDir = Path(named_skills_dir(registryPath))
    if not namedDir.exists():
        return out
    for mdFile in namedDir.rglob("*.md"):
        try:
            _f, fmText, _b = split_frontmatter(mdFile.read_text(encoding="utf-8"))
            fm = load_yaml_simple(fmText)
        except (OSError, ValueError):
            continue
        if isinstance(fm, dict) and fm.get("status") == "awakened" and fm.get("id"):
            out[fm["id"]] = fm
    return out


def contenderPool(registryPath, mergedMap: dict) -> dict:
    """``mergedMap`` plus the awakened records: every Origin contender in the registry."""
    return {**awakenedRecords(registryPath), **(mergedMap or {})}


def contenderMerit(entry: dict, mergedMap: dict, frozen: set[str], level=None) -> tuple[int, float]:
    """Return ``(published level, TM)`` for one contender, honouring the frozen lock."""
    from gaia_cli.frozen import frozenLock

    lock = frozenLock(entry) if entry.get("id") in frozen else None
    if lock is not None:
        tm, grade = lock
    else:
        from gaia_cli.trustMagnitude import computeOverallTrustGradeFromSkill, computeTrustMagnitude

        tm = float(computeTrustMagnitude(entry, mergedMap))
        grade = computeOverallTrustGradeFromSkill(entry, mergedMap) or "ungraded"
    return publishedLevelNumber(level if level is not None else entry.get("level"), grade), tm


def _trustMap(pool: dict) -> dict:
    """The Trust Magnitude map: the pool without awakened records (as buildMergedSkillMap)."""
    return {k: v for k, v in (pool or {}).items() if not (isinstance(v, dict) and v.get("status") == "awakened")}


def bucketContenders(bucketRef: str, pool: dict) -> list[dict]:
    return [e for e in (pool or {}).values() if _isContender(e) and e.get("genericSkillRef") == bucketRef]


def _frozenIn(pool: dict) -> set[str]:
    from gaia_cli.frozen import frozenIds

    return frozenIds(e for e in (pool or {}).values() if _isContender(e) or (isinstance(e, dict) and e.get("contributor")))


def bucketHolders(bucketRef: str, pool: dict, overrides: Optional[dict] = None,
                  frozen: Optional[set[str]] = None) -> frozenset[str]:
    """Derive the Origin holder(s) of ``bucketRef`` from a contender pool.

    ``pool`` is a merged registry map (ideally :func:`contenderPool`, so awakened
    records compete). ``overrides`` maps a skill id to a hypothetical level, so a
    gate can ask who would hold Origin if the candidate sat at its target level.
    """
    overrides = overrides or {}
    frozen = _frozenIn(pool) if frozen is None else frozen
    tmMap = _trustMap(pool)
    contenders = []
    for entry in bucketContenders(bucketRef, pool):
        levelNumber, tm = contenderMerit(entry, tmMap, frozen, overrides.get(entry.get("id")))
        contenders.append({"id": entry["id"], "levelNumber": levelNumber, "tm": tm})
    return deriveBucketOrigins(contenders)


def holdsBucketOrigin(named: dict, pool: Optional[dict] = None, level=None) -> bool:
    """True when ``named`` is (or, at ``level``, would be) its bucket's Origin.

    With no ``pool`` the skill is judged as the only contender in its bucket.
    """
    ref = named.get("genericSkillRef")
    sid = named.get("id")
    if not ref or not sid:
        return False
    pool = dict(pool or {})
    pool[sid] = {**pool.get(sid, {}), **named, "status": "named"}
    overrides = {sid: level} if level is not None else None
    return sid in bucketHolders(ref, pool, overrides)


def contributorHoldsOriginIn(contributor: Optional[str], nodeIds, pool: dict) -> bool:
    """True when ``contributor`` holds the derived Origin on >=1 of ``nodeIds``.

    A named id (``owner/slug``) counts when it belongs to ``contributor`` and is
    its bucket's Origin. A generic id counts when one of the bucket's Origins
    belongs to ``contributor``. Used by the Suite 5★ Ultimate gate (META §4.2).
    """
    if not contributor or not nodeIds or not pool:
        return False
    frozen = _frozenIn(pool)
    for nodeId in nodeIds:
        node = pool.get(nodeId) or {}
        if _isContender(node):
            if node.get("contributor") == contributor and nodeId in bucketHolders(node["genericSkillRef"], pool, frozen=frozen):
                return True
            continue
        if any((pool.get(h) or {}).get("contributor") == contributor for h in bucketHolders(nodeId, pool, frozen=frozen)):
            return True
    return False


def registryOrigins(pool: dict) -> dict[str, frozenset[str]]:
    """Derive every bucket's holder(s) from a contender pool (see :func:`contenderPool`)."""
    frozen = _frozenIn(pool)
    refs = sorted({e["genericSkillRef"] for e in (pool or {}).values() if _isContender(e)})
    return {ref: bucketHolders(ref, pool, frozen=frozen) for ref in refs}
