"""Deterministic core for the October 2026 adjudication ledger.

Read-only. Every number comes from Gaia code (trustMagnitude, promotion,
taxonomy); this module only loads the registry into memory, applies hypothetical
corrections to an in-memory COPY, and recomputes. Nothing is written to registry/.
"""
from __future__ import annotations

import copy
import json
import re
import subprocess
import sys
from pathlib import Path

STARS = {"1★": 1, "2★": 2, "3★": 3, "4★": 4, "5★": 5, "6★": 6}
# Mirrors scripts/generateNamedIndex.py GRADE_MAX_STARS (#1729). Kept in sync by
# selfcheck(): the projected level must equal the published named index level.
GRADE_MAX_STARS = {"S": 6, "A": 4, "B": 3, "C": 2, "ungraded": 1}


def setupPaths(root: Path):
    sys.path.insert(0, str(root / "scripts"))
    sys.path.insert(0, str(root / "src"))


def pinClock(when):
    """Pin Gaia's wall clock (freshness decay, source-tenure predicate) to ``when`` so
    every recompute is a pure function of the registry bytes. Without this the
    ledger would change daily."""
    import gaia_cli.trustMagnitude as tmod
    tmod._utcNow = lambda: when


def lvl(s):
    return STARS.get(str(s), 0)


def star(n):
    return f"{n}★"


class Registry:
    """In-memory registry maps. ``clone()`` deep-copies so corrections never leak."""

    def __init__(self, generic, named):
        self.generic = generic
        self.named = named

    def clone(self):
        return Registry(copy.deepcopy(self.generic), copy.deepcopy(self.named))


def loadRegistry(root: Path) -> Registry:
    import trust_appraise as ta
    gm, nm = ta._load_registry_maps(root)
    return Registry(gm, nm)


def derive(sk, reg: Registry):
    """TM / grade for one skill dict, exactly as scripts/trust_appraise.appraise_skill."""
    from gaia_cli.trustMagnitude import (
        computeTrustMagnitude, computeOverallTrustGrade,
        _countDistinctEvidenceTypes, _hasEligibleIndependentWitness,
    )
    mm = {**reg.generic, **reg.named}
    tm = computeTrustMagnitude(sk, mm, reg.named)
    types = _countDistinctEvidenceTypes(sk, mm)
    wit = _hasEligibleIndependentWitness(sk, mm)
    grade = computeOverallTrustGrade(tm, types, wit)
    return round(tm, 2), grade, types, bool(wit)


def refreshCaches(reg: Registry):
    """Mirror generateNamedIndex: stamp computed TM/grade onto the in-memory maps so
    apex predicates (which read cached overallTrustGrade) see fresh values."""
    for d in (reg.generic, reg.named):
        for k, sk in d.items():
            tm, g, _t, _w = derive(sk, reg)
            sk["trustMagnitude"] = tm
            sk["overallTrustGrade"] = g


def _originModule():
    """Origin is automatic (founder rulings 2026-10-30): read it from gaia_cli.origin.

    Requires a Gaia checkout that carries src/gaia_cli/origin.py (dev/yggdrasil-iv
    after the "Origin is automatic" PR). The stored frontmatter flag is never read.
    """
    try:
        import gaia_cli.origin as origin
    except ImportError as exc:  # pragma: no cover - old checkout
        raise RuntimeError(
            "gaia_cli.origin is missing: merge dev/yggdrasil-iv (Origin is automatic) first. "
            "adjcore no longer reads the stored origin flag."
        ) from exc
    return origin


def _pool(reg: Registry):
    return {**reg.generic, **reg.named}


def holdsOrigin(sid, reg: Registry):
    """True when ``sid`` holds its bucket's derived Origin (highest merit; ties all hold)."""
    sk = reg.named.get(sid) or {}
    ref = sk.get("genericSkillRef")
    return bool(ref) and sid in _originModule().bucketHolders(ref, _pool(reg))


def holdsSuiteOrigin(sk, reg: Registry):
    """META 4.2: the proposer holds the derived Origin on >=1 suiteComponent."""
    return _originModule().contributorHoldsOriginIn(sk.get("contributor"), sk.get("suiteComponents") or [], _pool(reg))


def namedState(sid, reg: Registry, withApex=True):
    """Full derived state of one named skill: TM, grade, ceiling, gates."""
    from gaia_cli.promotion import checkUniqueBranchGate
    from gaia_cli.trustMagnitude import passesSuiteApexGate
    from gaia_cli.taxonomy import branchFor
    sk = reg.named[sid]
    tm, grade, types, wit = derive(sk, reg)
    n = lvl(sk.get("level"))
    ceil = GRADE_MAX_STARS.get(grade, 1)
    st = {
        "id": sid, "storedLevel": sk.get("level"), "storedN": n, "tm": tm, "grade": grade,
        "distinctTypes": types, "witness": wit, "ceilingN": ceil,
        "projectedLevel": star(min(n, ceil)) if n else sk.get("level"),
        "origin": holdsOrigin(sid, reg), "status": sk.get("status"),
        "genericSkillRef": sk.get("genericSkillRef"),
        "suite": bool(sk.get("suiteComponents")),
        "branch": branchFor(sk),
    }
    gh = (sk.get("links") or {}).get("github")
    st["blobLink"] = bool(gh and "/blob/" in str(gh))
    gates = {}
    if n >= 4:
        gates["tmGate"] = tm >= 100 if n == 4 else (tm >= 250 and grade == "S")
        if not sk.get("suiteComponents") and n in (4, 5):
            g = checkUniqueBranchGate(sk, star(n), reg.generic, reg.named)
            gates["uniqueGate"] = {k: g[k] for k in ("passed", "originPresent", "tmThresholdMet", "branch")}
        if sk.get("suiteComponents"):
            if n == 5:
                gates["suiteOriginOnComponent"] = holdsSuiteOrigin(sk, reg)
            if withApex and n >= 4:
                mm = {**reg.generic, **reg.named}
                ap = passesSuiteApexGate(sk, {"genericSkillMap": reg.generic, "namedSkillMap": reg.named})
                gates["apex"] = {k: v for k, v in ap.items() if v is not None}
                gates["apex"]["all"] = all(gates["apex"].values())
    if n >= 3 and not sk.get("suiteComponents"):
        gates["starBarBlob"] = st["blobLink"]
    st["gates"] = gates
    return st


def genericState(gid, reg: Registry):
    sk = reg.generic[gid]
    tm, grade, types, wit = derive(sk, reg)
    return {"id": gid, "tm": tm, "grade": grade, "type": sk.get("type")}


def snapshot(reg: Registry):
    """Derived state for every record (cheap: whole registry recomputes in <1s)."""
    refreshCaches(reg)
    out = {"named": {}, "generic": {}}
    for sid in sorted(reg.named):
        out["named"][sid] = namedState(sid, reg)
    for gid in sorted(reg.generic):
        out["generic"][gid] = genericState(gid, reg)
    return out


def diffSnapshots(a, b):
    """List the records whose derived state differs, with a field-level diff."""
    changes = []
    for kind in ("named", "generic"):
        for rid, sa in a[kind].items():
            sb = b[kind].get(rid)
            if sb is None:
                changes.append({"kind": kind, "id": rid, "removed": True})
                continue
            d = {}
            for k in sorted(set(sa) | set(sb)):
                if sa.get(k) != sb.get(k):
                    d[k] = [sa.get(k), sb.get(k)]
            if d:
                changes.append({"kind": kind, "id": rid, "changed": d})
    return changes


# ---------------------------------------------------------------- correction ops

def rowMatches(row, match):
    t = row.get("type")
    if "type" in match:
        types = match["type"] if isinstance(match["type"], list) else [match["type"]]
        if t not in types:
            return False
    if "sourceContains" in match:
        subs = match["sourceContains"] if isinstance(match["sourceContains"], list) else [match["sourceContains"]]
        src = str(row.get("source") or "")
        if not any(s in src for s in subs):
            return False
    if "notesContains" in match and match["notesContains"] not in str(row.get("notes") or ""):
        return False
    if "index" in match and match["index"] != row.get("_i"):
        return False
    return True


def applyOps(reg: Registry, ops):
    """Apply hypothetical corrections to ``reg`` (a clone). Returns a list of
    human-readable effects, e.g. which rows were removed. Raises KeyError if an
    op targets something absent (so a stale spec is loud, not silent)."""
    from gaia_cli.trustMagnitude import EVIDENCE_TYPE_LAYER_CONTRACT
    log = []
    for op in ops:
        kind = op["op"]
        if kind in ("removeRows", "setRowField"):
            pool = reg.generic if op.get("layer") == "generic" else reg.named
            sk = pool[op["id"]]
            ev = sk.get("evidence") or []
            hit = [r for r in ev if rowMatches(r, op["match"])]
            if not hit:
                raise KeyError(f"no row matches {op}")
            if kind == "removeRows":
                keep = [r for r in ev if not rowMatches(r, op["match"])]
                sk["evidence"] = keep
                log.append(f"removed {len(hit)} row(s) from {op['id']}: " +
                           "; ".join(f"{r.get('type')}@{str(r.get('source'))[-60:]}" for r in hit))
            else:
                for r in hit:
                    r[op["field"]] = op["value"]
                log.append(f"set {op['field']}={op['value']} on {len(hit)} row(s) of {op['id']}")
        elif kind == "setOrigin":
            raise ValueError(
                "setOrigin is retired: Origin is automatic (highest merit per bucket, founder "
                "rulings 2026-10-30). Change the merit inputs (rows, level) instead."
            )
        elif kind == "setField":
            pool = reg.generic if op.get("layer") == "generic" else reg.named
            pool[op["id"]][op["field"]] = op["value"]
            log.append(f"{op['field']} of {op['id']} -> {op['value']}")
        elif kind == "setLevel":
            reg.named[op["id"]]["level"] = op["value"]
            log.append(f"level of {op['id']} -> {op['value']}")
        elif kind == "setGenericRef":
            if op["value"] not in reg.generic:
                raise KeyError(f"generic {op['value']} absent")
            reg.named[op["id"]]["genericSkillRef"] = op["value"]
            log.append(f"genericSkillRef of {op['id']} -> {op['value']}")
        elif kind == "removeSuiteComponents":
            sk = reg.named[op["id"]]
            before = list(sk.get("suiteComponents") or [])
            gone = [c for c in op["components"] if c in before]
            sk["suiteComponents"] = [c for c in before if c not in op["components"]]
            log.append(f"suiteComponents of {op['id']}: removed {gone}")
        elif kind == "engineDropGenericNamedOnly":
            n = 0
            for g in reg.generic.values():
                keep = []
                for r in g.get("evidence") or []:
                    c = EVIDENCE_TYPE_LAYER_CONTRACT.get(r.get("type") or "", {})
                    if c.get("inheritMultiplier") is None and r.get("type") in (
                            "repo-own", "github-stars-own", "self-attestation"):
                        n += 1
                        continue
                    keep.append(r)
                g["evidence"] = keep
            log.append(f"engine-fix simulation: ignore {n} named-only-type rows inherited from generic nodes")
        else:
            raise ValueError(kind)
    return log


def gitOut(root, *args):
    return subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True).stdout.strip()
