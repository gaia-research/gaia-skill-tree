"""Deterministically rebuild findings.json / ledger.json / COVERAGE.md from the sweep workflow journal.

Replays the workflow script's own merge, dedupe, grouping and survival rule over the
recorded agent results, so nothing is transcribed by a model.
"""
import json, sys, collections, glob, os
from pathlib import Path

journal, outDir = Path(sys.argv[1]), Path(sys.argv[2])
rows = [json.loads(l) for l in journal.open() if l.strip()]
label = {r["key"]: r.get("label") for r in rows if r["type"] == "started"}
byLabel = {}
for r in rows:
    if r["type"] == "result":
        byLabel[label.get(r["key"])] = r["result"]

DIMS = ["star-bar", "liveness", "origin-attribution", "unbacked-star", "brand-coupled", "heavy-deps",
        "installability", "placeholder-bodies", "testuser-timelines", "champion-cluster", "unique-isolation",
        "grade-mismatch", "product-attribution"]
batches = sorted({l.split(":", 1)[1] for l in byLabel if l and l.startswith("appraise")},
                 key=lambda n: (0 if n.startswith("named") else 1, n))
allF = []
for d in DIMS:
    s = byLabel.get(f"survey:{d}")
    if s:
        for f in s["findings"]:
            allF.append({**f, "source": f"survey:{s['dimension']}"})
appraise = {}
for b in batches:
    r = byLabel.get(f"appraise-retry:{b}") or byLabel.get(f"appraise:{b}")
    appraise[b] = r
    for f in (r or {}).get("findings", []):
        allF.append({**f, "source": f"appraise:{b}"})
fuse = byLabel.get("fuse") or {"candidates": []}
for c in fuse["candidates"]:
    allF.append({"target": c["proposedGenericId"], "dimension": "semantic-fusion", "priority": "P3", "reason": c["rationale"],
                 "suggestedAction": f"fuse {','.join(c['prerequisites'])}", "metaRef": "§6.2", "sources": c["exampleNamed"], "source": "fuse"})
prop = byLabel.get("propose") or {"proposals": []}
for p in prop["proposals"]:
    allF.append({"target": p["id"], "dimension": "new-generic", "priority": "P3", "reason": p["reasoning"],
                 "suggestedAction": f"add {p['type']} {p['id']}: {p['description']}", "metaRef": "§1", "sources": p["prerequisites"], "source": "propose"})
seen = {}
for f in allF:
    k = f"{f['target']}::{f['dimension']}::{(f.get('reason') or '')[:60]}"
    if k not in seen:
        seen[k] = {**f, "key": f"F{len(seen) + 1}"}
deduped = list(seen.values())
byDim = {}
for f in deduped:
    byDim.setdefault(f["dimension"], []).append(f)
groups = []
for dim, fs in byDim.items():
    for i in range(0, len(fs), 5):
        groups.append((dim, fs[i:i + 5]))
verified, missingVotes = [], 0
for gi, (dim, items) in enumerate(groups):
    votes = [byLabel.get(f"verify:{dim}:{gi}:L{li}") for li in (1, 2, 3)]
    missingVotes += sum(v is None for v in votes)
    for f in items:
        vs = [x for v in votes if v for x in v.get("verdicts", []) if x.get("key") == f["key"]]
        upheld = sum(1 for v in vs if not v["refuted"])
        verified.append({**f, "votes": len(vs), "upheld": upheld, "survives": upheld >= 2,
                         "verdictReasons": [("UPHELD: " if not v["refuted"] else "REFUTED: ") + v["reason"] for v in vs]})

# per-record ledger
shards = {}
for p in sorted(glob.glob(str(outDir / "batches" / "*.ledger.json"))):
    for rec in json.load(open(p)):
        shards[(rec.get("kind"), rec.get("path"))] = rec
prepass = json.load(open(outDir / "prepass.json"))
surv = [f for f in verified if f["survives"]]
def matches(f, rec):
    t = str(f["target"]); rid = str(rec.get("id") or ""); path = rec["path"]
    return t in (rid, path) or (rec["kind"] == "named" and t == rid.split("/")[-1] and False) or t == Path(path).stem and rec["kind"] == "generic"
ledger, attached = [], set()
for pre in prepass["records"]:
    rec = shards.get((pre["kind"], pre["path"]), {})
    keys = [f["key"] for f in verified if matches(f, pre)]
    sk = [f["key"] for f in surv if matches(f, pre)]
    attached.update(sk)
    disp = "blocked" if rec.get("disposition") == "blocked" else ("change-proposed" if sk else "reviewed-no-change")
    ledger.append({"id": pre.get("id"), "kind": pre["kind"], "path": pre["path"],
                   "reviewer": rec.get("reviewer"), "method": rec.get("method"), "checks": rec.get("checks"),
                   "evidenceRowsReviewed": rec.get("evidenceRowsReviewed"), "auditorDisposition": rec.get("disposition"),
                   "proposalType": rec.get("proposalType"), "findingSummary": rec.get("findingSummary"),
                   "evidenceRefs": rec.get("evidenceRefs"), "prepass": {k: pre.get(k) for k in ("level", "computedTm", "computedGrade", "status", "gateViolations") if k in pre},
                   "findingKeys": keys, "survivingFindingKeys": sk, "finalDisposition": disp, "inShard": bool(rec)})
unattached = [f["key"] for f in surv if f["key"] not in attached]
counts = {
    "records": len(ledger), "named": sum(r["kind"] == "named" for r in ledger), "generic": sum(r["kind"] == "generic" for r in ledger),
    "missingFromShards": sum(not r["inShard"] for r in ledger),
    "finalDisposition": dict(collections.Counter(r["finalDisposition"] for r in ledger)),
    "auditorDisposition": dict(collections.Counter(r["auditorDisposition"] for r in ledger)),
    "findingsRaw": len(allF), "findingsDeduped": len(deduped), "findingsSurviving": len(surv),
    "survivingByPriority": dict(sorted(collections.Counter(f["priority"] for f in surv).items())),
    "survivingByDimension": dict(collections.Counter(f["dimension"] for f in surv).most_common()),
    "verifyGroups": len(groups), "verifyVotesMissing": missingVotes, "unattachedSurvivingFindings": len(unattached),
    "evidenceRowsReviewed": sum(r["evidenceRowsReviewed"] or 0 for r in ledger),
}
header = {"registryRevision": prepass["registryRevision"], "snapshot": "provisional-2026-10-28", "cutoff": "2026-10-31T23:59:59Z", "mode": "read-only",
          "generator": "sweep/tools/rebuild_from_journal.py (deterministic replay of workflow wf_fb1ee3fb-d06)"}
(outDir / "findings.json").write_text(json.dumps({**header, "counts": counts, "unattachedSurvivingFindingKeys": unattached, "findings": verified}, indent=1, ensure_ascii=False))
(outDir / "ledger.json").write_text(json.dumps({**header, "counts": counts, "records": ledger}, indent=1, ensure_ascii=False))
surveyMeta = [{"dimension": d, **({k: byLabel[f'survey:{d}'][k] for k in ('checkedCount', 'method')} if byLabel.get(f'survey:{d}') else {"missing": True}),
               "findings": len(byLabel.get(f'survey:{d}', {}).get('findings', []))} for d in DIMS]
json.dump({"counts": counts, "survey": surveyMeta, "fusionCandidates": len(fuse["candidates"]), "newGenericProposals": len(prop["proposals"])},
          open(outDir / "tools" / "summary.json", "w"), indent=1)
print(json.dumps(counts, indent=1)); print(json.dumps(surveyMeta, indent=0)[:3000])
