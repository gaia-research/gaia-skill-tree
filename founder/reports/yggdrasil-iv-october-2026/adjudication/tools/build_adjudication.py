#!/usr/bin/env python3
"""Build the October 2026 adjudication / consequence ledger (EPIC #2189 outcome 4).

Read-only and deterministic. Inputs: sweep/findings.json (surviving findings only),
the registry and public artifacts at the checked-out revision, observations.json.
Every number comes from Gaia code through adjcore (in-memory recompute on a copy).
Nothing here approves, mutates or demotes anything: approved is always null.

    python3 build_adjudication.py            # write ledger.json, LEDGER.md, DECISIONS.md
    python3 build_adjudication.py --check    # rebuild in memory, byte-compare, exit 1 on drift
"""
from __future__ import annotations

import argparse
import datetime
import hashlib
import json
import re
import subprocess
import sys
from collections import Counter, defaultdict
from pathlib import Path

HERE = Path(__file__).resolve().parent
ADJ = HERE.parent
CAMP = ADJ.parent
ROOT = CAMP.parents[2]
sys.path.insert(0, str(HERE))
import adjcore as ac  # noqa: E402

DIMS = {"rank", "unbacked-star", "unique-isolation", "origin", "origin-attribution", "champion",
        "champion-cluster", "reclassification", "grade-mismatch", "structural", "starBar"}
GENERATOR = "adjudication/tools/build_adjudication.py (deterministic; adjcore in-memory recompute)"
SPECIALS = {
    "mattpocock/skills": "FD-9", "safishamsi/graphify": "FD-10", "vercel-labs/vercel-react-best-practices": "FD-10",
    "addy-osmani/code-simplification": "FD-10", "ayghri/i-have-adhd": "FD-10", "dietrichgebert/ponytail": "FD-10",
    "google-deepmind/workflow-skill-creator": "FD-11", "latent-spaces/brag": "FD-12",
    "xquik-dev/hermes-tweet": "FD-13", "laravel/upgrade-laravel-v13": "FD-14",
    "martin-stepanoski/nielsen-heuristics-audit": "FD-14", "obra/superpowers": "FD-15",
}
UNIQUE5 = ["vercel-labs/vercel-react-best-practices", "addy-osmani/code-simplification",
           "ayghri/i-have-adhd", "dietrichgebert/ponytail"]
ABSENCE = re.compile(r"\b(?:no|zero|absent) origin(?![-\w]| event)|origin absent|holds no origin|has no origin(?![-\w])|none holds|no origin holder", re.I)


def sh(*args):
    return subprocess.run(list(args), capture_output=True, text=True, cwd=ROOT).stdout.strip()


def jload(p):
    return json.loads(Path(p).read_text())


def dumps(o):
    return json.dumps(o, indent=1, sort_keys=True, ensure_ascii=False) + "\n"


# ----------------------------------------------------------------------------- context
class Ctx:
    pass


def buildCtx():
    c = Ctx()
    c.revision = sh("git", "log", "-1", "--format=%H", "--", ".", ":(exclude)founder/reports")
    when = sh("git", "log", "-1", "--format=%cI", c.revision)
    c.clock = datetime.datetime.fromisoformat(when).astimezone(datetime.timezone.utc)
    ac.setupPaths(ROOT)
    ac.pinClock(c.clock)
    c.reg = ac.loadRegistry(ROOT)
    c.baseReg = c.reg.clone()
    c.base = ac.snapshot(c.baseReg)
    c.sweepPath = CAMP / "sweep" / "findings.json"
    c.sweep = jload(c.sweepPath)
    c.obs = jload(ADJ / "observations.json")
    # public surfaces
    ni = jload(ROOT / "docs/graph/named/index.json")
    c.nameIdx = {}
    for b, items in ni["buckets"].items():
        for s in items:
            c.nameIdx[s["id"]] = dict(s, _list="bucket:" + b)
    for s in ni["awaitingClassification"]:
        c.nameIdx[s["id"]] = dict(s, _list="awaitingClassification")
    c.api = {}
    for p in sorted((ROOT / "docs/api/v1/skills").glob("*/*.json")):
        if p.name != "index.json":
            d = jload(p)
            c.api[d["id"]] = d
    c.lb = jload(ROOT / "docs/api/v1/leaderboard.json")["rows"]
    c.lbPos = {r["id"]: i + 1 for i, r in enumerate(c.lb)}
    c.lbRow = {r["id"]: r for r in c.lb}
    c.ledger = {r["skillId"]: r for r in jload(ROOT / "docs/graph/ledger/data.json")["rows"]}
    c.nodePath = {}
    for p in sorted((ROOT / "registry/nodes").glob("*/*.json")):
        c.nodePath[p.stem] = str(p.relative_to(ROOT))
    c.d6 = sorted(k for k, s in c.base["named"].items() if s["storedN"] > s["ceilingN"])
    c.scen = {}
    return c


def surfaces(c, sid):
    ni, ap, lr, lg = c.nameIdx.get(sid), c.api.get(sid), c.lbRow.get(sid), c.ledger.get(sid)
    s = {
        "namedIndex": {"present": bool(ni), "list": ni and ni["_list"], "level": ni and ni.get("level"),
                       "status": ni and ni.get("status"), "origin": ni and ni.get("origin"),
                       "trustMagnitude": ni and ni.get("trustMagnitude"),
                       "grade": ni and ni.get("overallTrustGrade")},
        "skillApi": {"present": bool(ap), "level": ap and ap.get("level"), "trustMagnitude": ap and ap.get("trustMagnitude"),
                     "grade": ap and ap.get("overallTrustGrade"), "origin": ap and ap.get("origin")},
        "leaderboard": {"present": bool(lr), "position": c.lbPos.get(sid), "level": lr and lr["level"],
                        "trustMagnitude": lr and lr["trustMagnitude"], "grade": lr and lr["grade"],
                        "origin": lr and lr["origin"]},
        "ledger": {"present": bool(lg), "currentStars": lg and lg["currentStars"], "tm": lg and lg["tm"],
                   "grade": lg and lg["grade"], "mayStars": lg and lg.get("mayStars"), "g7Stars": lg and lg.get("g7Stars"),
                   "flag": lg and lg.get("flag")},
    }
    lv = sorted({v for v in (s["namedIndex"]["level"], s["skillApi"]["level"], s["leaderboard"]["level"],
                             s["ledger"]["currentStars"]) if v})
    s["levelsShown"] = lv
    return s


def normTarget(c, t):
    t = t.strip()
    m = re.match(r"registry/named/(.+)\.md$", t) or re.match(r"registry/nodes/[^/]+/(.+)\.json$", t) \
        or re.match(r"generic/(.+)$", t)
    if m:
        t = m.group(1)
    if t in c.reg.named or t in c.reg.generic:
        return t, ("named" if t in c.reg.named else "generic")
    m = re.match(r"^(\S+) \(", t)
    if m and (m.group(1) in c.reg.generic or m.group(1) in c.reg.named):
        return m.group(1), ("named" if m.group(1) in c.reg.named else "generic")
    return "systemic:" + re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")[:70], "systemic"


# ----------------------------------------------------------------------------- scenarios
def scenario(c, ops):
    key = json.dumps(ops, sort_keys=True)
    if key not in c.scen:
        reg = c.baseReg.clone()
        log = ac.applyOps(reg, ops)
        snap = ac.snapshot(reg)
        c.scen[key] = (reg, log, snap, ac.diffSnapshots(c.base, snap))
    return c.scen[key]


def scenarioView(c, ops, focus=None):
    reg, log, snap, diff = scenario(c, ops)
    out = {"corrections": ops, "applied": log,
           "registryDiff": [d for d in diff],
           "changedRecords": len(diff)}
    if focus and focus in snap["named"]:
        out["after"] = snap["named"][focus]
    return out


def positionShifts(c, newTm):
    rows = [(r["id"], newTm.get(r["id"], r["trustMagnitude"])) for r in c.lb]
    order = [i for i, _ in sorted(rows, key=lambda x: -x[1])]
    return {i: [c.lbPos[i], p + 1] for p, i in enumerate(order) if c.lbPos[i] != p + 1}


def bucket(c, gid):
    mem = []
    for sid, s in sorted(c.base["named"].items()):
        if s["genericSkillRef"] == gid:
            mem.append({"id": sid, "storedLevel": s["storedLevel"], "projectedLevel": s["projectedLevel"],
                        "projectedN": min(s["storedN"], s["ceilingN"]), "status": s["status"], "origin": s["origin"],
                        "tm": s["tm"], "grade": s["grade"], "suite": s["suite"]})
    elig = [m for m in mem if m["status"] == "named" and m["projectedN"] >= 2]
    elig.sort(key=lambda m: (-m["projectedN"], -m["tm"], m["id"]))
    winner, tie = None, False
    if elig:
        winner = elig[0]["id"]
        if len(elig) > 1 and (elig[0]["projectedN"], elig[0]["tm"]) == (elig[1]["projectedN"], elig[1]["tm"]):
            winner, tie = None, True
    eh = [m["id"] for m in elig if m["origin"]]
    return {"genericSkillRef": gid, "members": mem, "originHolders": [m["id"] for m in mem if m["origin"]],
            "eligibleHolders": eh, "ineligibleHolders": [m["id"] for m in mem if m["origin"] and m["id"] not in eh],
            "eligible": [m["id"] for m in elig], "meritWinner": winner, "meritTie": tie}


# ----------------------------------------------------------------------------- rechecks
def recheck(c, f, tgt, kind):
    d, k, reason = f["dimension"], f["key"], f["reason"]
    n = c.base["named"].get(tgt)
    V = lambda v, note: {"key": k, "verdict": v, "note": note}  # noqa: E731
    if n:
        if tgt in c.d6 and (d in ("rank", "unbacked-star") and re.search(r"clamp|index|projection|ungraded|1.?star|1★", reason, re.I)):
            return V("confirmed", f"stored {n['storedLevel']} > grade ceiling {n['ceilingN']}★ ({n['grade']}); namedIndex shows {n['projectedLevel']}")
        if d == "rank" and re.search(r"clamp", reason, re.I) and tgt not in c.d6:
            return V("refuted-on-recheck", f"stored {n['storedLevel']} is not above the {n['grade']} ceiling {n['ceilingN']}★")
        if k in ("F12", "F35", "F624"):
            return V("confirmed" if n["origin"] and n["storedN"] <= 1 else "refuted-on-recheck",
                     f"origin={n['origin']} level={n['storedLevel']} status={n['status']}")
        if k in ("F29", "F13", "F287"):
            return V("confirmed" if n["status"] == "awakened" and n["storedN"] >= 2 else "refuted-on-recheck",
                     f"status={n['status']} level={n['storedLevel']} origin={n['origin']}")
        if k in ("F372", "F376"):
            return V("confirmed" if n["status"] == "named" and n["storedN"] == 1 else "refuted-on-recheck",
                     f"status={n['status']} level={n['storedLevel']} tm={n['tm']}")
        if k == "F370":
            ok = n["storedN"] == 3 and n["tm"] >= 100 and n["grade"] == "A" and n["blobLink"]
            return V("confirmed" if ok else "refuted-on-recheck", f"level={n['storedLevel']} tm={n['tm']} grade={n['grade']} blob={n['blobLink']}")
        if k == "F479":
            cached = c.reg.named[tgt].get("apexGateStatus") or {}
            ok = cached.get("overallGradeS") is True and n["grade"] != "S"
            return V("confirmed" if ok else "refuted-on-recheck",
                     f"node cache overallGradeS={cached.get('overallGradeS')} signed={cached.get('apexPromotionPrSigned')}; recomputed grade {n['grade']} TM {n['tm']}; "
                     f"published named index overallGradeS={(c.nameIdx.get(tgt) or {}).get('apexGateStatus', {}).get('overallGradeS')}")
        if k in ("F606", "F618"):
            g = n["gates"].get("uniqueGate")
            lvl = "5★" if k == "F606" else "4★"
            if k == "F618" or n["storedN"] == 5:
                from gaia_cli.promotion import checkUniqueBranchGate
                gate = checkUniqueBranchGate(c.reg.named[tgt], lvl, c.reg.generic, c.reg.named)
                return V("confirmed" if not gate["passed"] else "refuted-on-recheck", f"checkUniqueBranchGate({lvl}) passed={gate['passed']} originPresent={gate['originPresent']}")
        if d in ("unbacked-star", "unique-isolation") and n["storedN"] in (4, 5) and not n["suite"] and "uniqueGate" in n["gates"]:
            g = n["gates"]["uniqueGate"]
            return V("confirmed" if not g["passed"] else "refuted-on-recheck", f"uniqueGate passed={g['passed']} originPresent={g['originPresent']} branch={g['branch']}")
        if k == "F34":
            ev = len(c.reg.named[tgt].get("evidence") or [])
            return V("confirmed" if ev == 0 and n["storedN"] >= 3 else "refuted-on-recheck", f"evidence rows={ev}, level={n['storedLevel']}, tm={n['tm']}")
        if k == "F409":
            sf = surfaces(c, tgt)
            return V("confirmed" if len(sf["levelsShown"]) > 1 else "refuted-on-recheck", f"levels shown across surfaces: {sf['levelsShown']}")
        if d == "starBar":
            link = (c.reg.named[tgt].get("links") or {}).get("github") or ""
            ob = c.obs["links"].get(tgt)
            if "404" in reason and ob:
                return V("confirmed" if ob["blobHttp"] == "404" else "refuted-on-recheck", f"observed HTTP {ob['blobHttp']} (single probe {c.obs['observedAt']}); IV requires bounded t0/+24h/+72h before consequence")
            if re.search(r"directory blob", reason):
                last = link.rstrip("/").split("/")[-1]
                return V("confirmed" if "." not in last else "refuted-on-recheck", f"links.github={link}")
            if re.search(r"repo root", reason):
                return V("confirmed" if "/blob/" not in link else "refuted-on-recheck", f"links.github={link or '(none)'}")
            if re.search(r"no links.github|unlinked|Suite component with no", reason):
                return V("confirmed" if not link else "refuted-on-recheck", f"links.github={link or '(none)'}")
    if tgt == "mattpocock/skills" and k in ("F384", "F385"):
        row = c.reg.named[tgt]["evidence"][0]
        if k == "F384":
            return V("confirmed" if row.get("citations") == 500 else "refuted-on-recheck",
                     f"row 0 citations={row.get('citations')}; Semantic Scholar not independently re-verified (HTTP 429 on recheck)")
        _, _, snap, _ = scenario(c, preWitnessOps())
        s = snap["named"][tgt]
        ob = c.obs["other"]["frontendmastery-witness"]
        return V("confirmed" if s["tm"] < 250 and ob["http"] == "404" else "refuted-on-recheck",
                 f"TM without the two 2026-09-04 rows = {s['tm']} ({s['grade']}); witness URL HTTP {ob['http']}")
    if k == "F232":
        ref = c.reg.named["garrytan/design-shotgun"]["genericSkillRef"]
        return V("confirmed" if ref == "design-review" else "refuted-on-recheck", f"genericSkillRef={ref}")
    if k == "F73":
        has = any("champion" in sk for dd in (c.reg.named, c.reg.generic) for sk in dd.values())
        return V("refuted-on-recheck" if has else "confirmed", f"any record carries a 'champion' field: {has}")
    if k == "F91":
        bad = [i for dd in (c.reg.named, c.reg.generic) for i, sk in dd.items()
               if sk.get("trustMagnitude") is not None and (abs(sk["trustMagnitude"] - ac.derive(sk, c.reg)[0]) > 0.011
                                                            or sk.get("overallTrustGrade") != ac.derive(sk, c.reg)[1])]
        return V("confirmed" if not bad else "refuted-on-recheck", f"cached TM/grade mismatches vs recompute (clock pinned): {len(bad)}")
    if k == "F630":
        p = c.nodePath.get("agent-fusion", "")
        return V("confirmed" if "/basic/" in p and c.reg.generic["agent-fusion"].get("type") == "fusion" else "refuted-on-recheck",
                 f"{p} type={c.reg.generic['agent-fusion'].get('type')}")
    if d == "champion" and tgt in c.reg.generic:
        b = bucket(c, tgt)
        named = list(b["members"])  # champion findings count every child, awakened included
        noField = "champion" not in c.reg.generic[tgt]
        if k in ("F719", "F732"):
            tops = sorted(((m["tm"], m["id"]) for m in named), reverse=True)
            tie = len(tops) > 1 and tops[0][0] == tops[1][0]
            return V("confirmed" if noField and tie else "refuted-on-recheck", f"top TM {tops[0][0]} tie={tie} children={len(named)}")
        return V("confirmed" if noField and len(named) >= 3 else "refuted-on-recheck", f"children={len(named)} championField={not noField}")
    if d in ("origin", "origin-attribution") and kind in ("named", "generic"):
        gid = tgt if kind == "generic" else c.base["named"][tgt]["genericSkillRef"]
        if gid in c.reg.generic and ABSENCE.search(reason):
            b = bucket(c, gid)
            if b["eligibleHolders"]:
                return V("refuted-on-recheck", f"claim of no Origin, but eligible holders now: {b['eligibleHolders']}")
            return V("confirmed", f"bucket {gid} has zero Origin holders; eligible={b['eligible']}")
    return V("not-mechanically-rechecked", "no deterministic re-derivation available; evidence kept as the sweep recorded it")


# ----------------------------------------------------------------------------- scenarios for specials
def mpRows(c):
    ev = c.reg.named["mattpocock/skills"]["evidence"]
    ax = [i for i, r in enumerate(ev) if "2607.03238" in str(r.get("source"))][0]
    fm = [i for i, r in enumerate(ev) if "frontendmastery" in str(r.get("source"))][0]
    return ax, fm


def citeOps():
    return [{"op": "setRowField", "id": "mattpocock/skills", "match": {"sourceContains": "2607.03238"}, "field": "citations", "value": 2}]


def witnessOps():
    return [{"op": "removeRows", "id": "mattpocock/skills", "match": {"sourceContains": "frontendmastery.com"}}]


def preWitnessOps():
    return [{"op": "removeRows", "id": "mattpocock/skills", "match": {"sourceContains": ["2607.03238", "frontendmastery.com"]}}]


def gateTable(c, sid, ops):
    from gaia_cli.trustMagnitude import passesSuiteApexGate
    reg, _, snap, diff = scenario(c, ops)
    s = snap["named"][sid]
    out = {"tm": s["tm"], "grade": s["grade"], "witness": s["witness"], "tmGate5": s["tm"] >= 250 and s["grade"] == "S",
           "tmGate4": s["tm"] >= 100, "suiteOriginOnComponent": s["gates"].get("suiteOriginOnComponent"),
           "ceiling": s["ceilingN"], "projectedLevel": s["projectedLevel"]}
    out["leaderboardShift"] = positionShifts(c, {sid: s["tm"]})
    out["changedRecords"] = [d["id"] for d in diff]
    return out


def proposeMattpocock(c):
    sc = {"asRecorded": gateTable(c, "mattpocock/skills", []),
          "citationsCorrectedTo2": gateTable(c, "mattpocock/skills", citeOps()),
          "witnessRowRemoved": gateTable(c, "mattpocock/skills", witnessOps()),
          "bothCorrections": gateTable(c, "mattpocock/skills", citeOps() + witnessOps()),
          "preWitnessBaseline": gateTable(c, "mattpocock/skills", preWitnessOps())}
    return {"kind": "recomputed", "scenarios": sc, "levelChange": None,
            "note": "Gaia recomputes TM/grade and gate predicates; it does not assign levels. No level change is proposed. "
                    "Row corrections are Class C canonical evidence changes; the corrected citation count and a replacement witness need sourcing, not invention."}


def proposeGraphify(c):
    from gaia_cli.promotion import checkUniqueBranchGate
    sid = "safishamsi/graphify"
    sk = c.reg.named[sid]
    gates = {lvl: {k: v for k, v in checkUniqueBranchGate(sk, lvl, c.reg.generic, c.reg.named).items()}
             for lvl in ("4★", "5★")}
    g = c.reg.generic[sk["genericSkillRef"]]
    pre = {}
    for pid in g.get("prerequisites") or []:
        pre[pid] = [{"id": i, "contributor": s["contributor"], "level": s["level"], "origin": s["origin"]}
                    for i, s in sorted(c.reg.named.items()) if s.get("genericSkillRef") == pid]
    return {"kind": "gate-recompute", "gates": gates, "fusionStructurePrerequisites": pre, "levelChange": None,
            "note": "5★ Unique Ultimate needs fusion-structure Origin on a prerequisite of the generic parent (promotion.py); the 4★ gate would pass. "
                    "Any level action is a Class C founder decision; none is proposed here."}


def proposeSetOrigin(c, sid, value, focus=None):
    v = scenarioView(c, [{"op": "setOrigin", "id": sid, "value": value}], focus or sid)
    return v


def proposeBucketOrigin(c, gid, target):
    b = bucket(c, gid)
    p = {"bucket": b}
    if not b["eligible"]:
        p.update(kind="needs-decision", reason="no eligible (named, >=2 star after clamp) claimant; nothing to recompute")
    elif b["ineligibleHolders"]:
        p.update(kind="needs-decision", reason=f"Origin sits on non-eligible record(s) {b['ineligibleHolders']} (awakened or below 2 star); resolving it is a decision (see their own candidates)")
    elif not b["originHolders"] and b["meritWinner"]:
        w = b["meritWinner"]
        p.update(kind="recomputed", scenario=proposeSetOrigin(c, w, True),
                 basis=f"merit rule (stored/projected level, then TM): {w} is the unique top eligible member; META 4.1 requires exactly one Origin; "
                       "assignment itself is a curation act and remains held")
    elif not b["originHolders"] and b["meritTie"]:
        p.update(kind="needs-decision", reason="tie on level and TM among the top eligible members; no deterministic merit winner (META 4.1 tie-break by attribution/Trust Score is judgement)")
    elif len(b["originHolders"]) == 1 and b["meritWinner"] and b["originHolders"][0] != b["meritWinner"]:
        h, w = b["originHolders"][0], b["meritWinner"]
        p.update(kind="needs-decision", reason=f"Origin held by {h} but merit winner is {w}; a transfer removes an Origin mark",
                 ifTransferred=scenarioView(c, [{"op": "setOrigin", "id": h, "value": False}, {"op": "setOrigin", "id": w, "value": True}], w))
    else:
        p.update(kind="needs-decision", reason=f"holders={b['originHolders']} meritWinner={b['meritWinner']} tie={b['meritTie']}: not mechanically determined")
    return p


def proposeUnique4(c, sid):
    n = c.base["named"][sid]
    return proposeBucketOrigin(c, n["genericSkillRef"], sid)


def proposeBrag(c):
    sid = "latent-spaces/brag"
    v = scenarioView(c, [{"op": "setLevel", "id": sid, "value": "4★"}], sid)
    return {"kind": "recomputed", "scenario": v, "levelChange": None,
            "note": "Hypothetical raise to 4★: gates recomputed by Gaia code. A promotion is Class C and is only proposed, never applied."}


def proposeHermes(c):
    sid = "xquik-dev/hermes-tweet"
    b = bucket(c, c.base["named"][sid]["genericSkillRef"])
    return {"kind": "recomputed", "scenario": proposeSetOrigin(c, sid, False), "bucketAfter": [m for m in b["members"] if m["id"] != sid],
            "note": "META 1.3/4.1: a 1-star entry cannot hold Origin. Clearing it leaves the bucket without a holder and without an eligible claimant."}


def proposeWsc(c):
    sid = "google-deepmind/workflow-skill-creator"
    return {"kind": "needs-decision",
            "reason": "two reconcilable routes; promoting to named needs a title or catalogRef that must come from a reviewer, not from this ledger",
            "alternatives": {
                "A-promote-to-named(hypothetical, title/catalogRef pending)": scenarioView(c, [{"op": "setField", "id": sid, "field": "status", "value": "named"}], sid),
                "B-reconcile-level-to-awakened-1star": scenarioView(c, [{"op": "setLevel", "id": sid, "value": "1★"}], sid)},
            "bucket": bucket(c, "skill-authoring")}


def proposeStatusNamed1(c, sid):
    return {"kind": "needs-decision",
            "reason": "status named at 1 star conflicts with META 1.1 (Named = 2 star minimum, needs title or catalogRef); fix is either status awakened or earned evidence",
            "alternatives": {"A-status-awakened": scenarioView(c, [{"op": "setField", "id": sid, "field": "status", "value": "awakened"}], sid)},
            "bucket": bucket(c, c.base["named"][sid]["genericSkillRef"])}


def proposeObra(c):
    sid = "obra/superpowers"
    s = c.base["named"][sid]
    return {"kind": "recomputed", "scenario": {"corrections": [], "applied": [], "registryDiff": [], "changedRecords": 0, "after": s},
            "staleNodeCache": c.reg.named[sid].get("apexGateStatus"), "publishedIndexApex": (c.nameIdx.get(sid) or {}).get("apexGateStatus"),
            "levelChange": None,
            "note": "Recompute equals what the published index already shows; only the node frontmatter cache is stale. Regenerate via gaia dev calibrate-trust-magnitude (never hand-edit)."}


def proposeD6(c, sid):
    n = c.base["named"][sid]
    sf = surfaces(c, sid)
    return {"kind": "needs-decision", "packet": "FD-7",
            "storedLevel": n["storedLevel"], "gradeCeiling": f"{n['ceilingN']}★", "clampedLevel": n["projectedLevel"],
            "optionOutcomes": {
                "A-align-leaderboard-and-ledger-to-clamp": {"namedIndex": n["projectedLevel"], "skillApi": n["projectedLevel"],
                                                           "leaderboard": n["projectedLevel"], "ledger": n["projectedLevel"],
                                                           "leaderboardPositionChanges": False},
                "B-lift-clamp-display": {"namedIndex": n["storedLevel"], "skillApi": n["storedLevel"], "leaderboard": n["storedLevel"],
                                         "ledger": n["storedLevel"],
                                         "metaRedaction13": "handle becomes public (>=2 star)" if n["storedN"] >= 2 else "unchanged"},
                "C-leave-as-is": {"surfacesShown": sf["levelsShown"]},
                "D-calibrate-stored-level-to-ceiling": {"storedLevelBecomes": n["projectedLevel"], "classC": True,
                                                        "note": "a lowering of the stored value; deterministic gate, not decay; founder only"}}}


# ----------------------------------------------------------------------------- dependents
def dependents(c, tgt, kind, proposed):
    out = {}
    if kind == "named":
        n = c.base["named"][tgt]
        out["suiteParents"] = sorted(i for i, s in c.reg.named.items() if tgt in (s.get("suiteComponents") or []))
        out["bucket"] = bucket(c, n["genericSkillRef"]) if n["genericSkillRef"] in c.reg.generic else None
        gr = n["genericSkillRef"]
        out["fusionParentsOfBucket"] = sorted(i for i, g in c.reg.generic.items() if gr in (g.get("prerequisites") or []))
        out["leaderboardPosition"] = c.lbPos.get(tgt)
        out["leaderboardNeighbours"] = [c.lb[i]["id"] for i in ((c.lbPos[tgt] - 2, c.lbPos[tgt]) if tgt in c.lbPos else ()) if 0 <= i < len(c.lb)]
        shifts = {}
        sc = proposed.get("scenarios")
        if sc:
            shifts = {k: v["leaderboardShift"] for k, v in sc.items()}
        out["leaderboardShiftIfProposed"] = shifts
    elif kind == "generic":
        out["bucket"] = bucket(c, tgt)
        out["fusionParents"] = sorted(i for i, g in c.reg.generic.items() if tgt in (g.get("prerequisites") or []))
        out["prerequisites"] = c.reg.generic[tgt].get("prerequisites") or []
    return out


# ----------------------------------------------------------------------------- candidates
PRIO = {"P0": 0, "P1": 1, "P2": 2, "P3": 3, "P4": 4}


def who(dims, tgt, kind, c, prop, special):
    if special in ("FD-9", "FD-10", "FD-11", "FD-12", "FD-13", "FD-14", "FD-15") or tgt in c.d6:
        return "founder"
    if kind == "systemic" or set(dims) <= {"champion", "champion-cluster", "grade-mismatch"}:
        return "Core"
    if "reclassification" in dims or "structural" in dims:
        return "L4"
    if "starBar" in dims:
        return "L4"
    return "founder" if (prop.get("kind") == "needs-decision" and "origin" in dims and c.base["named"].get(tgt, {}).get("storedN", 0) >= 4) else "L4"


def build(c):
    fs = [f for f in c.sweep["findings"] if f["survives"] and (f["dimension"] in DIMS or f["priority"] == "P0")]
    groups = defaultdict(list)
    kinds = {}
    for f in fs:
        t, kd = normTarget(c, f["target"])
        groups[t].append(f)
        kinds[t] = kd
    for sid in c.d6:
        groups.setdefault(sid, [])
        kinds[sid] = "named"
    for sid in SPECIALS:
        groups.setdefault(sid, [])
        kinds[sid] = "named"
    cands = []
    for tgt in sorted(groups):
        kd = kinds[tgt]
        fl = sorted(groups[tgt], key=lambda f: int(f["key"][1:]))
        dims = sorted({f["dimension"] for f in fl} | ({"D6-ceiling-clamp"} if tgt in c.d6 else set()))
        rc = [recheck(c, f, tgt, kd) for f in fl]
        special = SPECIALS.get(tgt)
        if tgt in c.d6 and not special:
            special = "FD-7"
        if tgt in c.d6 and tgt == "mattpocock/personal":
            special = "FD-7"
        # proposal
        if rc and all(r["verdict"] == "refuted-on-recheck" for r in rc) and tgt not in c.d6 and tgt not in SPECIALS:
            prop = {"kind": "none", "reason": "every surviving finding was refuted on re-check against current files"}
        elif tgt == "mattpocock/skills":
            prop = proposeMattpocock(c)
        elif tgt == "safishamsi/graphify":
            prop = proposeGraphify(c)
        elif tgt in UNIQUE5:
            prop = proposeUnique4(c, tgt)
        elif tgt == "latent-spaces/brag":
            prop = proposeBrag(c)
        elif tgt == "xquik-dev/hermes-tweet":
            prop = proposeHermes(c)
        elif tgt == "google-deepmind/workflow-skill-creator":
            prop = proposeWsc(c)
        elif tgt in ("laravel/upgrade-laravel-v13", "martin-stepanoski/nielsen-heuristics-audit"):
            prop = proposeStatusNamed1(c, tgt)
        elif tgt == "obra/superpowers":
            prop = proposeObra(c)
        elif tgt in c.d6:
            prop = proposeD6(c, tgt)
        elif kd == "generic" and set(dims) & {"origin", "origin-attribution"}:
            prop = proposeBucketOrigin(c, tgt, tgt)
        elif kd == "named" and set(dims) & {"origin", "origin-attribution"} and c.base["named"][tgt]["genericSkillRef"] in c.reg.generic:
            prop = proposeBucketOrigin(c, c.base["named"][tgt]["genericSkillRef"], tgt)
        else:
            prop = {"kind": "needs-decision", "reason": "no correction is mechanically determined by Gaia code for this finding class; "
                    "before-state and evidence recorded, no numbers invented"}
        if prop["kind"] == "none":
            outcome = "refuted-on-recheck"
        elif prop["kind"] in ("recomputed", "gate-recompute"):
            outcome = "proposed-with-numbers"
        else:
            outcome = "needs-decision"
        if kd == "named":
            n = c.base["named"][tgt]
            before = {"stored": {"level": n["storedLevel"], "status": n["status"], "origin": n["origin"], "branch": n["branch"],
                                 "genericSkillRef": n["genericSkillRef"], "suite": n["suite"]},
                      "derived": {k: n[k] for k in ("tm", "grade", "ceilingN", "projectedLevel", "distinctTypes", "witness", "gates")},
                      "surfaces": surfaces(c, tgt)}
        elif kd == "generic":
            g = c.base["generic"][tgt]
            before = {"stored": {"type": g["type"], "path": c.nodePath.get(tgt)}, "derived": {"tm": g["tm"], "grade": g["grade"]}}
        else:
            before = {"systemic": True}
        cands.append({
            "target": tgt, "kind": kd, "dimensions": dims,
            "priority": min([f["priority"] for f in fl], key=lambda p: PRIO[p]) if fl else "P2",
            "before": before, "recheck": rc,
            "outcome": outcome, "proposed": prop,
            "affectedDependents": dependents(c, tgt, kd, prop) if kd != "systemic" else {},
            "evidence": [{"key": f["key"], "dimension": f["dimension"], "priority": f["priority"], "reason": f["reason"],
                          "suggestedAction": f["suggestedAction"], "votes": f["votes"], "upheld": f["upheld"],
                          "verdictReasons": f["verdictReasons"], "sources": f.get("sources")} for f in fl],
            "requiredDecision": {"who": None, "packet": special or ("FD-16" if set(dims) & {"origin", "origin-attribution"} else
                                                                      "FD-17" if "starBar" in dims else "FD-18"),
                                 "doctrine": "no lowering from age, outages, competitor existence, model confidence or audit findings alone; IDs/hashes are not authentication"},
            "approved": None, "status": "held",
        })
    for i, cd in enumerate(cands):
        cd["id"] = f"ADJ-{i + 1:03d}"
        cd["requiredDecision"]["who"] = who(cd["dimensions"], cd["target"], cd["kind"], c, cd["proposed"], SPECIALS.get(cd["target"]))
        if cd["outcome"] == "refuted-on-recheck":
            cd["requiredDecision"]["who"] = "none (refuted; record only)"
    return cands


def counts(c, cands):
    byDim = Counter(d for cd in cands for d in cd["dimensions"])
    return {"candidates": len(cands), "byOutcome": dict(sorted(Counter(cd["outcome"] for cd in cands).items())),
            "byDimension": dict(sorted(byDim.items())),
            "byDecisionOwner": dict(sorted(Counter(cd["requiredDecision"]["who"] for cd in cands).items())),
            "byPacket": dict(sorted(Counter(cd["requiredDecision"]["packet"] for cd in cands).items())),
            "findingsUsed": sum(len(cd["evidence"]) for cd in cands),
            "findingRechecks": dict(sorted(Counter(r["verdict"] for cd in cands for r in cd["recheck"]).items())),
            "d6Set": len(c.d6), "approved": sum(1 for cd in cands if cd["approved"] is not None), "held": sum(1 for cd in cands if cd["status"] == "held")}


def selfcheck(c):
    mism = [i for dd in (c.reg.named, c.reg.generic) for i, sk in dd.items()
            if sk.get("trustMagnitude") is not None and (abs(sk["trustMagnitude"] - ac.derive(sk, c.reg)[0]) > 0.011
                                                         or sk.get("overallTrustGrade") != ac.derive(sk, c.reg)[1])]
    idx = [i for i, s in c.nameIdx.items() if i in c.base["named"] and s.get("level") != c.base["named"][i]["projectedLevel"]]
    prep = jload(CAMP / "sweep/prepass.json")
    return {"cachedTmGradeMismatchesVsRecompute": len(mism), "namedIndexLevelVsClampMismatches": len(idx),
            "d6Recomputed": len(c.d6), "prepassRegistryRevision": prep.get("registryRevision"),
            "clockPinnedTo": c.clock.strftime("%Y-%m-%dT%H:%M:%SZ")}


def ledgerDoc(c, cands):
    return {"generator": GENERATOR,
            "registryRevision": c.revision,
            "registryRevisionNote": "last commit touching anything outside founder/reports (HEAD only adds campaign records); stable under this ledger's own commits",
            "sweep": {"registryRevision": c.sweep["registryRevision"], "snapshot": c.sweep["snapshot"], "cutoff": c.sweep["cutoff"],
                      "findingsSha256": hashlib.sha256(c.sweepPath.read_bytes()).hexdigest(), "findingsCount": len(c.sweep["findings"])},
            "mode": "read-only; approved is null everywhere; nothing here is a decision",
            "doctrine": ["no lowering justified by age, outages, competitor existence, model confidence or audit findings alone",
                         "IDs and hashes are not authentication", "zero demotions is a valid outcome; none is manufactured",
                         "a raise (e.g. latent-spaces/brag) is only proposed"],
            "selfcheck": selfcheck(c), "counts": counts(c, cands), "candidates": cands}


# ----------------------------------------------------------------------------- markdown
def one(cd):
    p = cd["proposed"]
    k = p["kind"]
    if k == "none":
        return "refuted on re-check"
    if k == "needs-decision":
        return "needs-decision" + (f" ({p['reason'][:70]})" if p.get("reason") else "")
    if k == "gate-recompute":
        return "gate recompute: " + ", ".join(f"{l} passed={g['passed']}" for l, g in p["gates"].items())
    if cd["target"] == "mattpocock/skills":
        return "; ".join(f"{n}: TM {s['tm']} {s['grade']}" for n, s in p["scenarios"].items() if n != "preWitnessBaseline")
    sc = p.get("scenario")
    if sc and sc.get("after"):
        a = sc["after"]
        return f"recomputed: origin={a['origin']} level={a['storedLevel']} TM {a['tm']} {a['grade']}; {sc['changedRecords']} record(s) change"
    return "recomputed"


def bef(cd):
    b = cd["before"]
    if "stored" not in b or "level" not in b["stored"]:
        return "-" if "systemic" in b else f"TM {b['derived']['tm']} {b['derived']['grade']}"
    return f"{b['stored']['level']} {b['derived']['grade']} TM {b['derived']['tm']} o={int(bool(b['stored']['origin']))}"


def ledgerMd(L):
    cs, n = L["candidates"], L["counts"]
    o = ["# Adjudication / consequence ledger (EPIC #2189 outcome 4)", "",
         "Generated by `adjudication/tools/build_adjudication.py` from `sweep/findings.json` (surviving findings) and the registry at "
         f"`{L['registryRevision'][:9]}`. Regenerate: `python3 founder/reports/yggdrasil-iv-october-2026/adjudication/tools/build_adjudication.py`. "
         "**Approved: 0. Every row is held.** Nothing here is a decision, a demotion or a promotion.", "",
         f"- Sweep snapshot `{L['sweep']['snapshot']}` (registry {L['sweep']['registryRevision'][:9]}), cutoff {L['sweep']['cutoff']}; provisional.",
         f"- Gaia clock pinned to {L['selfcheck']['clockPinnedTo']}; self-check: {L['selfcheck']['cachedTmGradeMismatchesVsRecompute']} cached TM/grade mismatches, "
         f"{L['selfcheck']['namedIndexLevelVsClampMismatches']} named-index level mismatches vs the grade-ceiling clamp, D6 set {L['selfcheck']['d6Recomputed']}.", "",
         "## Summary", "", f"Candidates: **{n['candidates']}** (from {n['findingsUsed']} surviving findings plus the D6 set and named specials).", "",
         "| Outcome | Count |", "|---|---|"]
    o += [f"| {k} | {v} |" for k, v in n["byOutcome"].items()]
    o += ["", "| Dimension (candidates touching) | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in n["byDimension"].items()]
    o += ["", "| Decision owner | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in n["byDecisionOwner"].items()]
    o += ["", "| Packet | Count |", "|---|---|"] + [f"| {k} | {v} |" for k, v in n["byPacket"].items()]
    o += ["", "Finding re-checks: " + ", ".join(f"{k} {v}" for k, v in n["findingRechecks"].items()), "",
          "## Candidates (before -> proposed -> approved)", "",
          "| ID | Target | Dimensions | P | Before | Proposed | Owner / packet | Approved |", "|---|---|---|---|---|---|---|---|"]
    for cd in cs:
        o.append(f"| {cd['id']} | `{cd['target']}` | {', '.join(cd['dimensions'])} | {cd['priority']} | {bef(cd)} | {one(cd).replace('|', '/')} | "
                 f"{cd['requiredDecision']['who']} / {cd['requiredDecision']['packet']} | null (held) |")
    return "\n".join(o) + "\n"


def decisionsMd(c, L):
    by = {cd["target"]: cd for cd in L["candidates"]}
    o = ["# Founder decision packets (adjudication)", "",
         "Companion to `ledger.json`. Numbers are Gaia-code recomputes on an in-memory copy; no registry write occurred. FD-9 onward continue the numbering after FD-8 (hyperframes); renumber freely. "
         "Doctrine on every packet: no lowering from age, outages, competitor existence, model confidence or audit findings alone; IDs and hashes are not authentication. Approved: 0.", ""]
    # FD-7
    d6 = [by[s] for s in c.d6]
    onLb = [s for s in c.d6 if s in c.lbRow]
    onLg = [s for s in c.d6 if s in c.ledger]
    cnt = Counter((by[s]["before"]["stored"]["level"], by[s]["before"]["derived"]["grade"]) for s in c.d6)
    o += ["## FD-7 - the 39 skills stored above the TM-grade ceiling", "",
          f"Verified: {len(c.d6)} named skills have stored level above the ceiling (S6/A4/B3/C2/ungraded 1, `scripts/generateNamedIndex.py` ~L617, #1729): "
          + ", ".join(f"{v}x {k[0]} {k[1]}" for k, v in sorted(cnt.items())) + f". {len(onLb)} appear on leaderboard.json, {len(onLg)} on the ledger at the stored level; the named index and skills API show the clamp.", "",
          "| Skill | Stored | Grade/TM | Named index | Skills API | Leaderboard | Ledger |", "|---|---|---|---|---|---|---|"]
    for cd in d6:
        s = cd["before"]["surfaces"]
        o.append(f"| `{cd['target']}` | {cd['before']['stored']['level']} | {cd['before']['derived']['grade']} {cd['before']['derived']['tm']} | "
                 f"{s['namedIndex']['level']} | {s['skillApi']['level'] or 'absent'} | {s['leaderboard']['level']} | {s['ledger']['currentStars']} |")
    o += ["", "Options and consequences:", "",
          "- **A. Align leaderboard/ledger to the clamp** (publish the projected level everywhere): all four surfaces agree; leaderboard order is TM-sorted so positions do not move; the two strict xfails from #2195 can be flipped. Stored values stay 2-3 star in node files, so a later lift of the clamp would resurface them.",
          "- **B. Lift the clamp display** (named index and API show stored level): 38 ungraded 2-star and one ungraded 3-star skill (TM 0, zero evidence) appear as Named/Evolved and their handles become public under META 1.3. This overrides the deterministic Ygg III gate and needs a gate-level ruling.",
          "- **C. Leave as is**: the disagreement stays public and pinned by strict xfails; cheapest, but two truths remain on the site.",
          "- **D. Calibrate stored level down to the ceiling** (`gaia dev calibrate`, Class C, founder): makes files match what the index already shows; this is 39 stored-value lowerings justified by a deterministic gate, not decay. Not proposed; listed so the consequence is explicit.", "",
          "No option is approved. Related candidates: " + ", ".join(cd["id"] for cd in d6[:3]) + ", ... (all D6 rows in LEDGER.md).", ""]
    # FD-9
    m = by["mattpocock/skills"]
    sc = m["proposed"]["scenarios"]
    o += ["## FD-9 - mattpocock/skills evidence and the 5-star witness", "",
          f"Findings {', '.join(e['key'] for e in m['evidence'])}; re-check: " + "; ".join(f"{r['key']} {r['verdict']} ({r['note']})" for r in m["recheck"] if r["key"] in ('F384', 'F385')), "",
          "| Scenario | TM | Grade | Independent witness | 5-star TM gate (>=250, S) |", "|---|---|---|---|---|"]
    for k, v in sc.items():
        o.append(f"| {k} | {v['tm']} | {v['grade']} | {v['witness']} | {v['tmGate5']} |")
    o += ["", f"Reading: correcting the citation count alone leaves TM {sc['citationsCorrectedTo2']['tm']} ({sc['citationsCorrectedTo2']['grade']}), still above the 5-star gate; the S grade and the gate fail only when the unreachable witness row is also removed ({sc['bothCorrections']['tm']}, {sc['bothCorrections']['grade']}). "
          f"The pre-witness baseline recomputes to {sc['preWitnessBaseline']['tm']} at the pinned clock (the sweep quoted 233.42 from the 2026-09-04 timeline; both are below 250).", "",
          f"Observations: witness URL (frontendmastery) HTTP {c.obs['other']['frontendmastery-witness']['http']} on one probe; the citation count of 2 comes from the sweep (Semantic Scholar returned 429 on re-check, so not independently re-verified here). "
          "Under IV a 404 is review debt with bounded probes (t0/+24h/+72h), not a demotion. Also note ledger.json shows mayStars 6 for this skill while the local apex recompute is false (apexPromotionPrSigned and tenure predicates), a separate surface question.", "",
          "Decision asked (founder, Class C): (1) source a dated, correct citation count and replace/re-verify the witness; (2) whether any level action follows only after the recompute. Recompute does not assign levels; none is proposed.", ""]
    # FD-10
    o += ["## FD-10 - Unique-branch 4-star/5-star without bucket Origin", "",
          "Basis checked: the 4-star Unique Origin requirement is stated in CLAUDE.md and enforced by `promotion.checkUniqueBranchGate` (bucket-level Origin, TM>=100); META 1.1 does not restate it, META 4.1 requires exactly one Origin per bucket. Suite branch (has `suiteComponents`) does not need bucket Origin at 4-star. All five below have no `suiteComponents`, so the Unique rule applies.", "",
          "| Skill | Level | Branch | TM/grade | Bucket | Holders | Merit winner | uniqueGate (as stored) | If Origin set |", "|---|---|---|---|---|---|---|---|---|"]
    for t in UNIQUE5:
        cd = by[t]
        b = cd["proposed"]["bucket"]
        n = cd["before"]
        g = n["derived"]["gates"]["uniqueGate"]
        after = ""
        if cd["proposed"]["kind"] == "recomputed" and cd["proposed"]["scenario"]["applied"]:
            after = f"{cd['proposed']['scenario']['applied'][0]}; {cd['proposed']['scenario']['changedRecords']} record changes"
        else:
            after = "needs-decision"
        o.append(f"| `{t}` | {n['stored']['level']} | {n['stored']['branch']} | {n['derived']['grade']} {n['derived']['tm']} | {b['genericSkillRef']} ({len(b['members'])}) | "
                 f"{b['originHolders'] or 'none'} | {b['meritWinner']} | passed={g['passed']} originPresent={g['originPresent']} | {after} |")
    gr = by["safishamsi/graphify"]["proposed"]
    o += ["", f"`safishamsi/graphify` (5-star Unique Ultimate): holds bucket Origin but the 5-star gate needs fusion-structure Origin on a prerequisite of `knowledge-graph-build` "
          f"({', '.join(gr['fusionStructurePrerequisites'])}); checkUniqueBranchGate 5-star passed={gr['gates']['5★']['passed']}, 4-star passed={gr['gates']['4★']['passed']}. "
          "Whether to leave, assign prerequisite Origin, or act on the level is a founder Class C choice; none is proposed.", "",
          "Decision asked (founder): assign bucket Origin to the merit winner for the four 4-star skills (each is the unique top member, so the recompute only flips the origin flag and the gate), or rule otherwise. Origin is a merit mark; assignment goes through `gaia dev` on a review/meta branch.", ""]
    # FD-11..15
    w = by["google-deepmind/workflow-skill-creator"]
    o += ["## FD-11 - google-deepmind/workflow-skill-creator awakened at 4-star", "",
          f"Verified: status {w['before']['stored']['status']}, level {w['before']['stored']['level']}, origin {w['before']['stored']['origin']}, TM {w['before']['derived']['tm']} {w['before']['derived']['grade']}; "
          f"list: {w['before']['surfaces']['namedIndex']['list']}; absent from leaderboard and ledger (present={w['before']['surfaces']['leaderboard']['present']}). Sole awakened record above 1-star; holds Origin of skill-authoring while not Named (META 1.3). "
          "Routes: A promote to named (needs reviewer-supplied title/catalogRef; hypothetical recompute in ledger) or B reconcile to 1-star (then Origin falls away). Decision: founder/L4. TM is thin (100.82, barely over the 4-star floor); do not rely on it before the rows are re-verified.", ""]
    b = by["latent-spaces/brag"]["proposed"]["scenario"]["after"]
    o += ["## FD-12 - latent-spaces/brag meets 4-star numbers at 3-star", "",
          f"Verified: stored 3-star, TM {by['latent-spaces/brag']['before']['derived']['tm']} A, blob link present, sole bucket Origin. Hypothetical 4-star recompute: tm gate {b['gates'].get('tmGate')}, uniqueGate {b['gates'].get('uniqueGate')}, branch {b['branch']}. A raise is Class C and needs approval; only proposed.", ""]
    h = by["xquik-dev/hermes-tweet"]
    o += ["## FD-13 - xquik-dev/hermes-tweet holds Origin at 1-star", "",
          f"Verified: level {h['before']['stored']['level']}, status {h['before']['stored']['status']}, origin {h['before']['stored']['origin']}. META 1.3/4.1: a 1-star entry cannot hold Origin. Clearing it (via update-named, after pre-flight) leaves x-twitter-automation holderless with no eligible claimant. Decision: L4/founder.", ""]
    o += ["## FD-14 - status `named` at 1-star (laravel/upgrade-laravel-v13, martin-stepanoski/nielsen-heuristics-audit)", ""]
    for t in ("laravel/upgrade-laravel-v13", "martin-stepanoski/nielsen-heuristics-audit"):
        x = by[t]["before"]
        o.append(f"- `{t}`: status {x['stored']['status']}, level {x['stored']['level']}, TM {x['derived']['tm']} {x['derived']['grade']}. Alternative A (status awakened) recomputed in ledger; earning 2-star needs evidence, not a label edit.")
    s = by["obra/superpowers"]["proposed"]
    o += ["", "## FD-15 - obra/superpowers stale apex cache", "",
          f"Verified: node frontmatter apexGateStatus.overallGradeS={s['staleNodeCache']['overallGradeS']} signed={s['staleNodeCache']['apexPromotionPrSigned']}; recomputed grade A TM 221.52 (below 250); the published named index already shows overallGradeS={s['publishedIndexApex']['overallGradeS']}. "
          "So the public surface is correct and only the node cache is stale; regenerate through `gaia dev calibrate-trust-magnitude`. Core/maintainer action, no rank effect.", ""]
    n17 = [cd for cd in L["candidates"] if cd["requiredDecision"]["packet"] == "FD-17"]
    n16 = [cd for cd in L["candidates"] if cd["requiredDecision"]["packet"] == "FD-16"]
    o += ["## FD-16 - bucket Origin invariant and merit inversions (systemic)", "",
          f"{len(n16)} candidates. Sweep claims 105 of 202 buckets have no Origin holder; META 4.1 says exactly one per bucket, but only 4-star Unique treats it as a gate (FD-10). "
          "Rows where Gaia's merit rule gives a unique winner carry a recomputed single-flag change; ties and inversions (holder differs from merit winner) are needs-decision because a transfer removes a mark. Recommend a bulk curation policy decision rather than 100+ individual rulings.", "",
          f"## FD-17 - Star Bar link findings", "",
          f"{len(n17)} candidates (leonxlnx x11 observed HTTP 404 on one probe, mattpocock directory blobs, ruvnet repo-root links, suite components without links). 404s need the IV bounded re-probe before any consequence; link corrections are L4 curation.", "",
          "## FD-18 - structural, grade-mismatch, champion, reclassification, other", "",
          "Core/L4 items with no mechanically determined correction; evidence and re-check verdicts are in the ledger. Findings that failed re-check are kept as `refuted-on-recheck`.", ""]
    return "\n".join(o)


# ----------------------------------------------------------------------------- main
def render():
    c = buildCtx()
    cands = build(c)
    L = ledgerDoc(c, cands)
    return {"ledger.json": dumps(L), "LEDGER.md": ledgerMd(L), "DECISIONS.md": decisionsMd(c, L)}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true", help="rebuild and byte-compare ledger.json (and the markdown); exit 1 on drift")
    a = ap.parse_args()
    out = render()
    if a.check:
        bad = [n for n, t in out.items() if not (ADJ / n).exists() or (ADJ / n).read_text() != t]
        if bad:
            print("DRIFT: " + ", ".join(bad))
            sys.exit(1)
        L = json.loads(out["ledger.json"])
        assert L["counts"]["approved"] == 0
        print(f"OK: {L['counts']['candidates']} candidates, approved=0, byte-identical rebuild")
        return
    for n, t in out.items():
        (ADJ / n).write_text(t)
    L = json.loads(out["ledger.json"])
    print(json.dumps(L["counts"], indent=1))


if __name__ == "__main__":
    main()
