import os
import json
import sys
import subprocess
from pathlib import Path

from gaia_cli.registry import registry_nodes_dir
from gaia_cli.commands.dev.helpers import _is_generated, _parse_named_frontmatter


def meta_audit_command(args):
    """Registry linter for maintenance issues."""
    registry_path = args.registry
    nodes_dir = Path(registry_nodes_dir(registry_path))
    threshold = getattr(args, "level", 0)

    issues = []

    for p in nodes_dir.glob("**/*.json"):
        with open(p, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
            except json.JSONDecodeError:
                continue

            skill_id = data.get("id")
            level_str = data.get("level") or "0★"
            try:
                level = int(level_str[0])
            except (ValueError, IndexError):
                issues.append(f"[P0] {skill_id}: Malformed level {level_str!r}")
                continue

            if threshold and level < threshold:
                continue

            evidence = data.get("evidence", [])
            best_class = "D"
            if evidence:
                classes = [e.get("class", "C") for e in evidence]
                if "A" in classes:
                    best_class = "A"
                elif "B" in classes:
                    best_class = "B"
                elif "C" in classes:
                    best_class = "C"

            # Evidence Floor Checks (from GEMINI.md)
            # 2★ needs Tier C
            if level >= 2 and not evidence:
                issues.append(
                    f"[P1] {skill_id}: Level {level_str} but has NO evidence."
                )

            # 3★ needs Tier B
            if level == 3 and best_class == "C":
                issues.append(
                    f"[P1] {skill_id}: Level {level_str} but only has Class C evidence (needs B)."
                )

            # 4★+ needs Tier B/A
            if level >= 4 and best_class not in ["A", "B"]:
                issues.append(
                    f"[P0] {skill_id}: Level {level_str} but only has Class {best_class} evidence (needs A/B)."
                )

            # Orphan check
            if (
                not data.get("prerequisites")
                and data.get("type") != "basic"
                and data.get("type") != "unique"
            ):
                issues.append(
                    f"[P2] {skill_id}: Orphaned {data.get('type')} skill (no prerequisites)."
                )

            # Missing description
            if not data.get("description") or len(data.get("description")) < 10:
                issues.append(f"[P3] {skill_id}: Missing or too short description.")

    if not issues:
        print("✅ No registry maintenance issues found.")
    else:
        print(f"Found {len(issues)} potential issues:")
        for issue in sorted(issues):
            print(f"  {issue}")


def meta_diff_command(args):
    """Show substantive registry additions in a branch vs main, stripping generated noise."""
    ref = getattr(args, "ref", None)
    base = getattr(args, "base", "origin/main")

    if ref:
        compare_ref = (
            ref if ref.startswith(("origin/", "HEAD", "refs/")) else f"origin/{ref}"
        )
    else:
        r = subprocess.run(
            ["git", "rev-parse", "--abbrev-ref", "HEAD"],
            capture_output=True,
            text=True,
        )
        current = r.stdout.strip()
        if not current or current in ("HEAD", "main"):
            print("Error: specify a branch, e.g.  gaia dev diff review/meta/my-branch")
            sys.exit(1)
        compare_ref = current

    print(f"\n  Comparing {base}...{compare_ref}\n")

    def _git_json(git_ref, path):
        r = subprocess.run(
            ["git", "show", f"{git_ref}:{path}"],
            capture_output=True,
            text=True,
        )
        if r.returncode != 0:
            return None
        try:
            return json.loads(r.stdout)
        except json.JSONDecodeError:
            return None

    def _git_text(git_ref, path):
        r = subprocess.run(
            ["git", "show", f"{git_ref}:{path}"],
            capture_output=True,
            text=True,
        )
        return r.stdout if r.returncode == 0 else ""

    # Gather changed files, separate generated noise from substantive paths
    r = subprocess.run(
        ["git", "diff", "--name-status", f"{base}...{compare_ref}"],
        capture_output=True,
        text=True,
    )
    if r.returncode != 0:
        print(f"Error running git diff: {r.stderr.strip()}")
        sys.exit(1)

    skipped = 0
    substantive = []
    for line in r.stdout.splitlines():
        parts = line.split("\t", 1)
        if len(parts) != 2:
            continue
        status, path = parts[0].rstrip(), parts[1]
        if _is_generated(path):
            skipped += 1
        else:
            substantive.append((status, path))

    # Diff registry/gaia.json as structured JSON (most reliable approach)
    base_graph = _git_json(base, "registry/gaia.json") or {"skills": [], "edges": []}
    branch_graph = _git_json(compare_ref, "registry/gaia.json") or {
        "skills": [],
        "edges": [],
    }

    base_ids = {s["id"] for s in base_graph.get("skills", [])}
    branch_ids = {s["id"] for s in branch_graph.get("skills", [])}

    new_skill_ids = branch_ids - base_ids
    removed_skill_ids = base_ids - branch_ids
    new_skills = sorted(
        [s for s in branch_graph.get("skills", []) if s["id"] in new_skill_ids],
        key=lambda s: s["id"],
    )

    def _edge_key(e):
        return (e["sourceSkillId"], e["targetSkillId"], e.get("edgeType", ""))

    base_edges = {_edge_key(e) for e in base_graph.get("edges", [])}
    branch_edges = {_edge_key(e) for e in branch_graph.get("edges", [])}
    new_edges = sorted(branch_edges - base_edges)
    removed_edges = sorted(base_edges - branch_edges)

    base_version = base_graph.get("version", "?")
    branch_version = branch_graph.get("version", "?")

    # Categorise substantive paths
    new_named = sorted(
        (s, p) for s, p in substantive if s == "A" and p.startswith("registry/named/")
    )
    mod_named = sorted(
        (s, p) for s, p in substantive if s == "M" and p.startswith("registry/named/")
    )
    version_paths = [(s, p) for s, p in substantive if p in {
        "pyproject.toml",
        "packages/cli-npm/package.json",
        "packages/mcp/package.json",
        "registry/gaia.json",
        "docs/graph/gaia.json",
    }]
    other = [
        (s, p)
        for s, p in substantive
        if not p.startswith("registry/named/")
        and not p.startswith("registry/nodes/")
        and p not in {
            "pyproject.toml",
            "packages/cli-npm/package.json",
            "packages/mcp/package.json",
            "registry/gaia.json",
            "docs/graph/gaia.json",
        }
        and p != "registry/gaia.json"
    ]

    W = 68

    # ── New generic skills ────────────────────────────────────────────
    if new_skills:
        print(f"  ── NEW GENERIC SKILLS ({len(new_skills)}) {'─' * max(0, W - 24)}")
        for s in new_skills:
            stype = s.get("type", "?")
            level = s.get("level", "?")
            status = s.get("status", "?")
            desc = s.get("description", "")
            if len(desc) > 65:
                desc = desc[:62] + "..."
            prereqs = s.get("prerequisites", [])
            evidence = s.get("evidence", [])
            ev_str = (
                f"{len(evidence)}× ({', '.join(e['class'] for e in evidence)})"
                if evidence
                else "none"
            )
            print(f"  + {s['id']}  [{stype} · {level} · {status}]")
            print(f'    "{desc}"')
            if prereqs:
                print(f"    Prerequisites: {', '.join(prereqs)}")
            print(f"    Evidence: {ev_str}")
        print()

    # ── Removed generic skills (danger) ──────────────────────────────
    if removed_skill_ids:
        print(
            f"  ── ⛔  REMOVED SKILLS ({len(removed_skill_ids)}) {'─' * max(0, W - 24)}"
        )
        for sid in sorted(removed_skill_ids):
            print(f"  - {sid}")
        print()

    # ── New named skill files ─────────────────────────────────────────
    if new_named:
        print(f"  ── NEW NAMED SKILLS ({len(new_named)}) {'─' * max(0, W - 22)}")
        for _, path in new_named:
            content = _git_text(compare_ref, path)
            meta = _parse_named_frontmatter(content)
            skill_id = meta.get(
                "id", path.replace("registry/named/", "").replace(".md", "")
            )
            generic = meta.get("genericSkillRef", "—")
            level = meta.get("level", "?")
            print(f"  + {skill_id}  → {generic}  [{level}]")
        print()

    if mod_named:
        print(f"  ── MODIFIED NAMED SKILLS ({len(mod_named)}) {'─' * max(0, W - 27)}")
        for _, path in mod_named:
            print(f"  ~ {path.replace('registry/named/', '')}")
        print()

    # ── New edges ────────────────────────────────────────────────────
    if new_edges:
        print(f"  ── NEW EDGES ({len(new_edges)}) {'─' * max(0, W - 15)}")
        for src, tgt, etype in new_edges:
            print(f"  + {src} → {tgt}  ({etype})")
        print()

    if removed_edges:
        print(f"  ── ⛔  REMOVED EDGES ({len(removed_edges)}) {'─' * max(0, W - 23)}")
        for src, tgt, etype in removed_edges:
            print(f"  - {src} → {tgt}  ({etype})")
        print()

    # ── Version bump ─────────────────────────────────────────────────
    if base_version != branch_version:
        print(f"  ── VERSION BUMP {'─' * max(0, W - 17)}")
        print(f"  {base_version} → {branch_version}  (will conflict if main has moved)")
        print()

    # ── Other substantive changes ─────────────────────────────────────
    if other:
        print(f"  ── OTHER CHANGES ({len(other)}) {'─' * max(0, W - 19)}")
        for status, path in other:
            label = {"A": "new", "M": "mod", "D": "del"}.get(status, status)
            print(f"  {label}  {path}")
        print()

    # ── Quality flags ─────────────────────────────────────────────────
    flags = []
    for sid in sorted(removed_skill_ids):
        flags.append(("⛔", f"{sid} — skill removed (verify intentional!)"))

    for _, path in new_named:
        content = _git_text(compare_ref, path)
        meta = _parse_named_frontmatter(content)
        skill_id = meta.get(
            "id", path.replace("registry/named/", "").replace(".md", "")
        )
        if "Add installation instructions here" in content:
            flags.append(("⚠", f"{skill_id} — empty ## Installation body"))
        if not meta.get("genericSkillRef"):
            flags.append(("⚠", f"{skill_id} — missing genericSkillRef"))

    for s in new_skills:
        ev = s.get("evidence", [])
        if not ev:
            flags.append(("⚠", f"{s['id']} — no evidence attached"))
        elif all(e["class"] == "C" for e in ev):
            flags.append(("⚠", f"{s['id']} — only Class C evidence"))

    if flags:
        print(f"  ── QUALITY FLAGS {'─' * max(0, W - 18)}")
        for icon, msg in flags:
            print(f"  {icon}  {msg}")
        print()

    # ── Summary ───────────────────────────────────────────────────────
    if (
        not new_skills
        and not removed_skill_ids
        and not new_named
        and not new_edges
        and not other
    ):
        print(
            "  No substantive changes — branch is all generated noise or already merged."
        )

    print(f"  Skipped {skipped} generated files (SVG, HTML, GEXF, timestamps).")
    print()
