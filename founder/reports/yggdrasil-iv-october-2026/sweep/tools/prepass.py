"""Deterministic October sweep pre-pass: every named file + generic node, computed TM/grade vs recorded level."""
import json, sys, re, subprocess
from pathlib import Path
root = Path(sys.argv[1]); out = Path(sys.argv[2])
sys.path.insert(0, str(root / "scripts")); sys.path.insert(0, str(root / "src"))
import trust_appraise as ta
gm, nm = ta._load_registry_maps(root)
rev = subprocess.run(["git","-C",str(root),"rev-parse","HEAD"],capture_output=True,text=True).stdout.strip()
indexed = set()
nb = json.loads((root/"registry/named-skills.json").read_text())
for bucket, entries in nb["buckets"].items():
    for e in entries: indexed.add(e.get("id"))
STARS = {"1★":1,"2★":2,"3★":3,"4★":4,"5★":5,"6★":6}
records = []
for p in sorted((root/"registry/named").rglob("*.md")):
    rel = p.relative_to(root).as_posix()
    text = p.read_text(encoding="utf-8")
    m = ta.FRONTMATTER_RE.match(text)
    fm = (ta.yaml.safe_load(m.group(1)) or {}) if m else {}
    sid = fm.get("id") if isinstance(fm, dict) else None
    rec = {"kind":"named","path":rel,"id":sid,"indexed": sid in indexed}
    if not sid:
        rec["prepassError"] = "no frontmatter id"; records.append(rec); continue
    try:
        a = ta.appraise_skill(sid if "/" in sid else f"{p.parent.name}/{p.stem}", gm, nm)
    except Exception as exc:
        a = {"error": repr(exc)}
    lvl = fm.get("level"); links = fm.get("links") or {}
    gh = links.get("github") if isinstance(links, dict) else None
    tm = a.get("tm"); n = STARS.get(str(lvl))
    gates = []
    if n and n >= 4 and (tm is None or tm < 100): gates.append("4★ requires TM≥100 (META §1.1)")
    if n and n >= 5 and (tm is None or tm < 250): gates.append("5★ requires TM≥250 S-grade (META §1.1)")
    if n and n >= 5 and a.get("grade") != "S": gates.append("5★ requires Overall Trust Grade S")
    if n and n >= 3 and not fm.get("suiteComponents") and not (gh and "/blob/" in str(gh)): gates.append("3★+ star bar: links.github blob URL (META §2.4)")
    rec.update({"contributor": fm.get("contributor"), "name": fm.get("name"), "status": fm.get("status"),
        "level": lvl, "genericSkillRef": fm.get("genericSkillRef"), "origin": fm.get("origin"),
        "suiteComponents": fm.get("suiteComponents"), "installable": fm.get("installable"),
        "linksGithub": gh, "evidenceRows": len(fm.get("evidence") or []),
        "computedTm": tm, "computedGrade": a.get("grade"), "tmStatus": a.get("totalStatus"),
        "appraiseError": a.get("error"), "gateViolations": gates})
    records.append(rec)
for p in sorted((root/"registry/nodes").rglob("*.json")):
    d = json.loads(p.read_text(encoding="utf-8"))
    sid = d.get("id")
    try: a = ta.appraise_skill(sid, gm, nm)
    except Exception as exc: a = {"error": repr(exc)}
    records.append({"kind":"generic","path":p.relative_to(root).as_posix(),"id":sid,"type":d.get("type"),
        "name": d.get("name"), "prerequisites": d.get("prerequisites"), "evidenceRows": len(d.get("evidence") or []),
        "computedTm": a.get("tm"), "computedGrade": a.get("grade"), "appraiseError": a.get("error")})
out.write_text(json.dumps({"registryRevision": rev, "records": records}, indent=1, ensure_ascii=False))
named=[r for r in records if r["kind"]=="named"]; gen=[r for r in records if r["kind"]=="generic"]
print("named files", len(named), "indexed", sum(r["indexed"] for r in named), "generic", len(gen))
print("gate violations", sum(1 for r in named if r.get("gateViolations")), "errors", sum(1 for r in records if r.get("appraiseError") or r.get("prepassError")))
print("evidence rows", sum(r.get("evidenceRows",0) for r in records))
