#!/usr/bin/env python3
"""One-shot migration: make generic skill references rank-less.

Stars now live only on named skills. This migration:

  1. Strips ``level``, ``demerits`` and the dead ``realVariants`` field from every
     generic node under ``registry/nodes/**/*.json``.
  2. Audits GitHub-link evidence: capability-level evidence (Class A / arXiv and
     anything not unambiguously owned by one named implementation) STAYS on the
     generic node, where every named skill in the bucket inherits it. A GitHub
     evidence entry is moved onto a named skill ONLY when exactly one named skill
     in the same ``genericSkillRef`` bucket owns that repository.
  3. Reports everything moved and every ambiguous case (nothing is silently
     dropped).

Idempotent: re-running on already-migrated data is a no-op for the strip step
and will not double-move evidence (dedup by source).

Usage:
    python scripts/migrate_rankless_generics.py [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime
import glob
import json
import os
import re
import sys

import yaml

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NODES_DIR = os.path.join(REPO_ROOT, "registry", "nodes")
NAMED_DIR = os.path.join(REPO_ROOT, "registry", "named")

STRIP_FIELDS = ("level", "demerits", "realVariants")
TODAY = datetime.date.today().isoformat()


def gh_identity(url: str):
    """Normalize a GitHub URL to ``(owner/repo, subpath)`` (or None).

    ``subpath`` is the directory after ``blob/<branch>/`` or ``tree/<branch>/``
    with a trailing ``SKILL.md``/``README.md`` stripped — this disambiguates
    monorepos where many named skills share one repo root (e.g.
    ``science-skills/skills/uv`` vs ``.../skills/science_skills_common``).
    Empty string when the URL is a bare repo root.
    """
    if not url:
        return None
    m = re.search(r"github\.com[:/]+([^/\s]+)/([^/#?\s]+)", url)
    if not m:
        return None
    owner, repo = m.group(1), m.group(2)
    repo = repo[:-4] if repo.endswith(".git") else repo
    base = f"{owner}/{repo}".lower()
    sub = ""
    m2 = re.search(r"(?:blob|tree)/[^/]+/(.+)$", url)
    if m2:
        sub = re.sub(r"/(SKILL|README)\.md$", "", m2.group(1), flags=re.I).strip("/").lower()
    return base, sub


def match_named(bucket_recs: list, repo: str, sub: str):
    """Return (owners, ambiguous) for a GitHub evidence identity within a bucket.

    Prefers an exact subpath match; falls back to repo-root match when the
    evidence (or the named link) carries no subpath.
    """
    candidates = [r for r in bucket_recs if r.get("repo") == repo]
    if not candidates:
        return [], False
    if sub:
        exact = [r for r in candidates if r.get("sub") == sub]
        if len(exact) == 1:
            return exact, False
        if len(exact) > 1:
            return exact, True
        # no subpath match → fall back to repo root
    if len(candidates) == 1:
        return candidates, False
    return candidates, True


def _parse_md(path: str):
    with open(path, "r", encoding="utf-8") as f:
        text = f.read()
    if not text.startswith("---"):
        raise ValueError(f"{path}: no frontmatter")
    _, fm, body = text.split("---", 2)
    return (yaml.safe_load(fm) or {}), body


def _write_md(path: str, meta: dict, body: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        f.write("---\n" + yaml.dump(meta, sort_keys=False, allow_unicode=True) + "---" + body)


def load_named():
    """Return (by_id, bucket) where bucket maps genericSkillRef -> [named record]."""
    by_id = {}
    bucket: dict[str, list] = {}
    for path in sorted(glob.glob(os.path.join(NAMED_DIR, "**", "*.md"), recursive=True)):
        try:
            meta, body = _parse_md(path)
        except (OSError, ValueError) as exc:
            print(f"  WARN: cannot parse {path}: {exc}")
            continue
        rec = {"path": path, "meta": meta, "body": body, "dirty": False}
        nid = meta.get("id")
        ref = meta.get("genericSkillRef")
        ident = gh_identity((meta.get("links") or {}).get("github", ""))
        rec["repo"], rec["sub"] = ident if ident else (None, "")
        if nid:
            by_id[nid] = rec
        if ref:
            bucket.setdefault(ref, []).append(rec)
    return by_id, bucket


def add_named_evidence(rec: dict, ev: dict) -> bool:
    """Append evidence to a named record, dedup by source. Returns True if added."""
    meta = rec["meta"]
    existing = meta.setdefault("evidence", [])
    if any(e.get("source") == ev.get("source") for e in existing):
        return False
    existing.append(ev)
    rec["dirty"] = True
    return True


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Report only; write nothing.")
    args = parser.parse_args()

    by_id, bucket = load_named()

    nodes_stripped = 0
    evidence_moved = 0
    ambiguous = []        # (node_id, source, [candidate named ids])
    unowned_github = []   # (node_id, source) github evidence with no named owner in bucket
    node_writes = []      # (path, data)

    for path in sorted(glob.glob(os.path.join(NODES_DIR, "**", "*.json"), recursive=True)):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        node_id = data.get("id")
        changed = False

        # --- evidence audit ---
        kept_evidence = []
        for ev in data.get("evidence", []) or []:
            ident = gh_identity(ev.get("source", ""))
            if ident is None:
                kept_evidence.append(ev)      # arXiv / Class A / other → stays (inherited)
                continue
            repo, sub = ident
            owners, is_ambiguous = match_named(bucket.get(node_id, []), repo, sub)
            if owners and not is_ambiguous:
                if add_named_evidence(owners[0], ev):
                    evidence_moved += 1
                changed = True               # removed from generic
            elif is_ambiguous:
                ambiguous.append((node_id, ev.get("source"), [o["meta"].get("id") for o in owners]))
                kept_evidence.append(ev)      # leave on generic; report
            else:
                unowned_github.append((node_id, ev.get("source")))
                kept_evidence.append(ev)      # no named owner → stays on generic
        if "evidence" in data and kept_evidence != (data.get("evidence") or []):
            data["evidence"] = kept_evidence
            changed = True

        # --- strip rank fields ---
        for field in STRIP_FIELDS:
            if field in data:
                del data[field]
                changed = True

        if changed:
            data["updatedAt"] = TODAY
            nodes_stripped += 1
            node_writes.append((path, data))

    # --- write ---
    if not args.dry_run:
        for path, data in node_writes:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.write("\n")
        for rec in by_id.values():
            if rec["dirty"]:
                _write_md(rec["path"], rec["meta"], rec["body"])

    # --- report ---
    print("\n=== Rank-less generics migration " + ("(DRY RUN) " if args.dry_run else "") + "===")
    print(f"  Generic nodes updated:       {nodes_stripped}")
    print(f"  GitHub evidence moved→named: {evidence_moved}")
    print(f"  Ambiguous (left on generic): {len(ambiguous)}")
    print(f"  GitHub evidence w/o owner:   {len(unowned_github)} (stays on generic, inherited)")
    if ambiguous:
        print("\n  Ambiguous GitHub evidence (multiple named owners in bucket):")
        for nid, src, cands in ambiguous[:50]:
            print(f"    - {nid}: {src} -> {cands}")
    if unowned_github:
        report = os.path.join(REPO_ROOT, "registry", "_migration")
        if not args.dry_run:
            os.makedirs(report, exist_ok=True)
            with open(os.path.join(report, "unowned-github-evidence.json"), "w", encoding="utf-8") as f:
                json.dump(
                    [{"genericSkillRef": n, "source": s} for n, s in unowned_github],
                    f, indent=2, ensure_ascii=False,
                )
                f.write("\n")
            print(f"\n  Wrote registry/_migration/unowned-github-evidence.json ({len(unowned_github)} entries)")
    print()
    return 0


if __name__ == "__main__":
    sys.exit(main())
