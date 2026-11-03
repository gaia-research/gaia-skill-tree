"""Fixed runner for protocol c1-graphify-vs-graft-callers-v1. Reviewed code; reads no packet strings.

Extracts src/gaia_cli at the pinned revision into a scratch dir, runs Graphify (native/challenger)
and Graft (target/incumbent) on identical bytes, parses caller sets, scores them against the
reviewed ground-truth fixture and applies the pre-registered decision rule.
"""
from __future__ import annotations
import argparse, hashlib, json, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[4]
PRECISION_MARGIN = 0.05
RECALL_MARGIN = 0.2
MIN_TARGETS = 3


def sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def norm_path(p: str) -> str:
    p = p.split("gaia_cli/", 1)[1] if "gaia_cli/" in p else p
    return p[len("tree/"):] if p.startswith("tree/") else p


def norm_name(label: str, is_file: bool = False) -> str:
    label = label.strip()
    if is_file or label.endswith(".py") or label == "<module>":
        return "<module>"
    label = label.rstrip("()").lstrip(".")
    return label.split(".")[-1]


def run(cmd, cwd, env=None):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env)


def graphify_callers(tree_root: Path, work: Path, names: dict) -> dict:
    shutil.copytree(tree_root, work / "gx" / "tree")
    r = run(["graphify", "update", "tree"], work / "gx")
    if r.returncode != 0:
        raise RuntimeError("graphify update failed: " + r.stderr[-400:] + r.stdout[-400:])
    g = json.loads((work / "gx" / "tree" / "graphify-out" / "graph.json").read_text())
    nodes = {n["id"]: n for n in g["nodes"]}
    out = {}
    for name, defining in names.items():
        targets = [n for n in g["nodes"] if n.get("label") == f"{name}()" and norm_path(n.get("source_file", "")) == defining]
        found = set()
        for t in targets:
            for e in g["links"]:
                if e.get("relation") == "calls" and e["target"] == t["id"]:
                    s = nodes.get(e["source"], {})
                    is_file = s.get("label", "").endswith(".py")
                    found.add((norm_path(s.get("source_file") or e.get("source_file", "")), norm_name(s.get("label", ""), is_file)))
        out[name] = {"targetNodes": len(targets), "callers": sorted(found)}
    return out


CALL = re.compile(r"^\s*calls\s+←\s+(\S+)\s+\((.+?):L\d+-L\d+\)\s*$")


def graft_callers(tree_root: Path, work: Path, names: dict) -> dict:
    gx = work / "gf"
    shutil.copytree(tree_root, gx / "tree")
    r = run(["graft", "--dir", str(work / "gg"), "build", "--only-dir", "tree", "--no-gitignore", "--no-ignore", "."], gx)
    if r.returncode != 0:
        raise RuntimeError("graft build failed: " + r.stderr[-400:] + r.stdout[-400:])
    out = {}
    for name in names:
        r = run(["graft", "--dir", str(work / "gg"), "callers", name, "."], gx)
        found, raw = set(), r.stdout
        for line in raw.splitlines():
            m = CALL.match(line)
            if m:
                found.add((norm_path(m.group(2)), norm_name(m.group(1))))
        out[name] = {"exit": r.returncode, "callers": sorted(found), "rawDigest": sha(raw.encode())}
    return out


def score(gt: dict, got: dict) -> dict:
    per, tp_all, pred_all = {}, 0, 0
    for name, truth in gt.items():
        truth_set = {tuple(c) for c in truth}
        pred = {tuple(c) for c in got[name]["callers"]}
        tp = len(truth_set & pred)
        per[name] = {"groundTruth": len(truth_set), "predicted": len(pred), "truePositives": tp,
                     "recall": round(tp / len(truth_set), 4), "precision": round(tp / len(pred), 4) if pred else None,
                     "missed": sorted(truth_set - pred), "extra": sorted(pred - truth_set)}
        tp_all += tp; pred_all += len(pred)
    return {"perTarget": per, "microPrecision": round(tp_all / pred_all, 4) if pred_all else 0.0, "totalPredicted": pred_all, "totalTruePositives": tp_all}


def decide(chal: dict, inc: dict) -> dict:
    names = list(chal["perTarget"])
    wins = [n for n in names if chal["perTarget"][n]["recall"] >= inc["perTarget"][n]["recall"] + RECALL_MARGIN]
    prec_ok = chal["microPrecision"] >= inc["microPrecision"] - PRECISION_MARGIN
    inc_ge_all = all(inc["perTarget"][n]["recall"] >= chal["perTarget"][n]["recall"] for n in names) and inc["microPrecision"] >= chal["microPrecision"]
    if len(wins) >= MIN_TARGETS and prec_ok:
        result = "supported"
    elif inc_ge_all:
        result = "contradicted"
    else:
        result = "inconclusive"
    return {"result": result, "recallWinTargets": wins, "precisionWithinMargin": prec_ok, "incumbentAtLeastChallengerOnAll": inc_ge_all}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--request", required=True)
    ap.add_argument("--native-out", required=True)
    ap.add_argument("--target-out", required=True)
    ap.add_argument("--score-out", required=True)
    a = ap.parse_args()
    request = json.loads(Path(a.request).read_text())
    proto = ROOT / request["protocol"]["path"]
    fixture_path = ROOT / request["fixture"]["path"]
    fixture = json.loads(fixture_path.read_bytes())
    rev = fixture["pinnedRevision"]
    gt = fixture["groundTruth"]
    defining = {k: v["definedIn"] for k, v in fixture["targets"].items()}
    versions = {"graphify": run(["graphify", "--version"], ROOT).stdout.strip(), "graft": run(["graft", "--version"], ROOT).stdout.strip()}
    with tempfile.TemporaryDirectory(prefix="gaia-c1-") as td:
        work = Path(td)
        tree = work / "extract"; tree.mkdir()
        arc = subprocess.run(["git", "-C", str(ROOT), "archive", rev, "src/gaia_cli"], capture_output=True, check=True)
        subprocess.run(["tar", "-x", "-C", str(tree), "--exclude=src/gaia_cli/data"], input=arc.stdout, check=True)
        gcode = tree / "src" / "gaia_cli"
        chal_raw = graphify_callers(gcode, work, defining)
        inc_raw = graft_callers(gcode, work, defining)
    chal, inc = score(gt, chal_raw), score(gt, inc_raw)
    decision = decide(chal, inc)
    common = {"experiment": "c1-graphify-vs-graft-callers-v1", "requestId": request["requestId"], "fixtureDigest": request["fixture"]["contentDigest"],
              "protocolDigest": request["protocol"]["contentDigest"], "executionCheck": "passed", "pinnedRevision": rev}
    out_native = json.dumps(chal_raw, sort_keys=True, indent=1)
    native = {**common, "graphifyVersion": f"graphify {versions['graphify'].split()[-1]}", "executedVersion": versions["graphify"].split()[-1],
              "output": out_native, "outputDigest": sha(out_native.encode()), "result": decision["result"]}
    target = {**common, "graftVersion": versions["graft"], "output": json.dumps(inc_raw, sort_keys=True, indent=1)}
    scoring = {"incumbent": "graft", "challenger": "graphify", "challengerScore": chal, "incumbentScore": inc, "decision": decision, "versions": versions}
    for path, doc in ((a.native_out, native), (a.target_out, target), (a.score_out, scoring)):
        with open(path, "x", encoding="utf-8") as f:
            f.write(json.dumps(doc, indent=1, sort_keys=True) + "\n")
    print(json.dumps({"versions": versions, "decision": decision, "graphifyMicroPrecision": chal["microPrecision"], "graftMicroPrecision": inc["microPrecision"]}, indent=1))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
