"""Offline rehearsal parity oracle over actual builder output, never an approver.

Reuses canonical generators to derive expected content from the copied source.
This intentionally costs extra offline work; it makes a stale successful-looking
file, a page beyond page one, and historical/taxonomy corruption detectable.
"""
from __future__ import annotations

import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile


def _json(path):
    return json.loads(path.read_text(encoding="utf-8"))


def _equal(actual, expected):
    if actual.suffix == ".json":
        same = _json(actual) == _json(expected)
    else:
        same = actual.read_bytes() == expected.read_bytes()
    if not same:
        raise ValueError("cross-surface semantic mismatch: " + str(actual))


def _tree(actual, expected, suffix=None):
    files = {p.relative_to(expected) for p in expected.rglob("*") if p.is_file() and (not suffix or p.suffix == suffix)}
    actual_files = {p.relative_to(actual) for p in actual.rglob("*") if p.is_file() and (not suffix or p.suffix == suffix)}
    if files != actual_files:
        raise ValueError("cross-surface coverage mismatch: " + str(actual))
    for rel in sorted(files):
        _equal(actual / rel, expected / rel)


def check_semantic_parity(root: Path):
    # Execute this module in the target scratch runtime, not the caller's
    # imports (which may point at another worktree).
    env = {**os.environ, "PYTHONPATH": os.pathsep.join((str(root), str(root / "src"), str(root / "scripts"))),
           "GAIA_PUBLICATION_CONTEXT": str(root / "publication-context.json"), "PYTHONHASHSEED": "0"}
    proc = subprocess.run([sys.executable, str(root / "scripts/publication_parity.py"), "--root", str(root)],
                          cwd=root, env=env, capture_output=True, text=True)
    if proc.returncode:
        raise ValueError("cross-surface semantic mismatch: " + (proc.stdout + proc.stderr)[-3000:])


def _check(root):
    from publication_context import compare_ledger_api, record_execution
    import buildApiProjection as api
    import generateProfilePages as profiles
    import generateBadges as badges
    import build_docs as builder
    import syncDocsGraphAssets as sync
    named = _json(root / "registry/named-skills.json")
    if named != _json(root / "docs/graph/named/index.json"):
        raise ValueError("named/graph mirror differs")
    entries = [s for bucket in named["buckets"].values() for s in bucket]
    entries += named.get("awaitingClassification", [])
    # An absent issuer is not an empty verified challenge collection. Do not
    # turn booleans/actor names into a public proceeding.
    for entry in entries:
        if any(key in entry for key in ("verifiedChallenges", "originContested", "challengeStatus")):
            raise ValueError("live verified challenge projection unavailable")
    with tempfile.TemporaryDirectory(prefix="publication-parity-") as tmp:
        target = Path(tmp)
        def run(script, args):
            result = subprocess.run([sys.executable, str(root / "scripts" / script), *map(str, args)],
                                    cwd=root, capture_output=True, text=True)
            record_execution(Path(script), list(map(str, args)), result.returncode, result.stdout + result.stderr)
        # Recompute from Markdown/engine/catalog at pinned time. These compare
        # current Origin AND historical named timeline, not snapshot tags.
        run("generateNamedIndex.py", ["--out", target / "named.json"])
        _equal(root / "registry/named-skills.json", target / "named.json")
        run("generateLeaderboardData.py", ["--out", target / "ledger.json"])
        _equal(root / "docs/graph/ledger/data.json", target / "ledger.json")
        api.run(target / "api")
        # Hand-authored API subtrees have independent owners; all endpoints
        # actually emitted by buildApiProjection are compared, including page N.
        for path in sorted((target / "api").rglob("*.json")):
            _equal(root / "docs/api/v1" / path.relative_to(target / "api"), path)
        expected_api = {p.relative_to(target / "api") for p in (target / "api").rglob("*.json")}
        actual_api = {p.relative_to(root / "docs/api/v1") for p in (root / "docs/api/v1").rglob("*.json")
                      if p.relative_to(root / "docs/api/v1").parts[0] not in ("openapi.json", "trending", "benchmarks", "reports")}
        if actual_api != expected_api:
            raise ValueError("API missing/extra endpoint")
        pages = [_json(p) for p in sorted((target / "api/skills").glob("*.json"))]
        api_rows = [row for page in pages for row in page["skills"]]
        ledger = _json(root / "docs/graph/ledger/data.json")
        if {r["skillId"] for r in ledger["rows"]} != {r["id"] for r in api_rows}:
            raise ValueError("ledger/API coverage differs")
        problems = compare_ledger_api(ledger, {"skills": api_rows})
        by_id = {r["id"]: r for r in entries}
        for row in ledger["rows"]:
            entry = by_id[row["skillId"]]
            if row["origin"] != bool(entry.get("origin")) or row["grade"] != entry.get("overallTrustGrade"):
                problems.append(row["skillId"] + ": Origin/grade differs")
        if problems:
            raise ValueError("; ".join(problems[:20]))
        # Full rendered profile expectations include real owner-tree historical
        # awards and current named standing. Only unrelated JSON-LD is stripped.
        profiles.generate_pages(root / "registry/named-skills.json", target / "u")
        def normalize(text):
            text = re.sub(r'\s*<script type="application/ld\+json"[^>]*>.*?</script>', '', text, flags=re.S)
            return builder._apply_cache_busting(text, builder._read_version()).strip()
        expected_profiles = {p.relative_to(target / "u") for p in (target / "u").rglob("*.html")}
        actual_profiles = {p.relative_to(root / "docs/u") for p in (root / "docs/u").rglob("*.html")}
        if expected_profiles != actual_profiles:
            raise ValueError("profile missing/extra page")
        for rel in sorted(expected_profiles):
            if normalize((root / "docs/u" / rel).read_text()) != normalize((target / "u" / rel).read_text()):
                raise ValueError("profile current/history/Origin mismatch: " + str(rel))
        run("generateBadges.py", ["--out-dir", target / "badges"])
        _equal(root / "docs/badges/registry.json", target / "badges/registry.json")
        _tree(root / "docs/badges/_assets", target / "badges/_assets", ".svg")
        run("generateOgCards.py", ["--out-dir", target / "og"])
        _tree(root / "docs/og", target / "og", ".svg")
        # Re-sync the graph into an isolated tiny reference tree. No source
        # data or inspected output is overwritten by the parity oracle.
        import shutil
        graph_ref = target / "graph-reference"
        for rel in ("registry/gaia.json", "registry/gaia.gexf", "registry/named-skills.json", "registry/schema/meta.json", "generated-output/layouts.json", "generated-output/tree.md"):
            src = root / rel
            if src.exists():
                dst = graph_ref / rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(src, dst)
        sync.sync_docs_graph_assets(graph_ref)
        for rel in ("docs/graph/gaia.json", "docs/graph/gaia.gexf", "docs/graph/named/index.json"):
            _equal(root / rel, graph_ref / rel)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    _check(args.root)
