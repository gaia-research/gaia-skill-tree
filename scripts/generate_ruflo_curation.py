#!/usr/bin/env python3
"""Generate docs/ruflo-curation.html from generated-output/ruflo-skills-raw.json.

The output is a static HTML curation brief for the ruvnet/ruflo meta-curation sprint.
It includes: full skill tree, per-skill mapping table, fusion plan, Queen Seraphina callout,
and a gaia-curate action checklist.

Usage:
    python scripts/generate_ruflo_curation.py [--raw PATH] [--out PATH]

Exit codes:
    0 — Success
    1 — Fatal error
"""

from __future__ import annotations

import argparse
import html
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RAW_DEFAULT = ROOT / "generated-output" / "ruflo-skills-raw.json"
OUT_DEFAULT = ROOT / "docs" / "ruflo-curation.html"

LEVEL_LABEL = {
    "2★": "Named",
    "3★": "Evolved",
    "4★": "Hardened",
    "5★": "Transcendent",
    "6★": "Apex",
}

TYPE_SYMBOL = {
    "basic":   ("○", "#38bdf8"),
    "extra":   ("◇", "#c084fc"),
    "unique":  ("◉", "#7c3aed"),
    "ultimate":("◆", "#f59e0b"),
}

SUITE_ORDER = [
    "flow-nexus", "agentdb", "github", "hive-mind",
    "reasoningbank", "swarm", "v3", "standalone",
]

SUITE_LABELS = {
    "flow-nexus":   "Flow Nexus Suite",
    "agentdb":      "AgentDB Suite",
    "github":       "GitHub Suite",
    "hive-mind":    "Hive Mind Suite",
    "reasoningbank":"ReasoningBank Suite",
    "swarm":        "Swarm Skills → V3",
    "v3":           "V3 Suite",
    "standalone":   "Standalone Skills",
}

SUITE_NOTES = {
    "flow-nexus": "4★ extra fusion. Queen Seraphina AI assistant lives inside <code>flow-nexus-platform</code> — not a standalone skill.",
    "agentdb":    "5★ ultimate fusion. QUIC/HNSW perf claims (150×–12,500× faster) serve as Class B evidence.",
    "github":     "Individual skills are <code>origin: false</code> variants. Only the 4★ fusion is novel to ruvnet.",
    "hive-mind":  "Single skill → <strong>Unique (◉)</strong>. Byzantine consensus + queen-led hierarchy is distinct from <code>multi-agent-debate</code>. No prereqs.",
    "reasoningbank": "3★ extra fusion. Adaptive learning loop on top of vector memory.",
    "swarm":      "No suite fusion. Both skills folded as prerequisites into <code>v3-swarm-coordination</code>.",
    "v3":         "4★ extra fusion. Time-bounded sprint — tagged <code>v3-sprint, modernization</code>. Absorbs swarm skills as prereqs.",
    "standalone": "No suite fusion. Each skill mapped individually to Gaia canon.",
}


def _esc(s: str) -> str:
    return html.escape(str(s))


def _level_badge(level: str | None) -> str:
    if not level:
        return ""
    label = LEVEL_LABEL.get(level, level)
    return f'<span class="level-badge">{_esc(level)} {_esc(label)}</span>'


def _type_chip(t: str | None) -> str:
    if not t:
        return ""
    sym, color = TYPE_SYMBOL.get(t, ("?", "#888"))
    return f'<span class="type-chip" style="color:{color}">{sym} {_esc(t)}</span>'


def _status_chip(is_new: bool, existing_canon: str | None) -> str:
    if not is_new and existing_canon:
        return f'<span class="chip chip-exists">✅ maps to <code>{_esc(existing_canon)}</code></span>'
    return '<span class="chip chip-new">🔨 new canon needed</span>'


def _origin_chip(origin: bool) -> str:
    if origin:
        return '<span class="chip chip-origin">origin ★</span>'
    return '<span class="chip chip-variant">variant</span>'


def render_skill_row(skill: dict) -> str:
    name = skill["id"]
    canon = skill.get("canon_mapping") or "—"
    is_new = skill.get("canon_is_new", False)
    ctype = skill.get("canon_type")
    origin = skill.get("origin", False)
    status_html = _status_chip(is_new, None if is_new else canon)
    type_html = _type_chip(ctype) if is_new else ""
    origin_html = _origin_chip(origin)
    fetch_ok = skill.get("fetch_status") == "ok"
    fetch_icon = "✓" if fetch_ok else "⚠"
    fetch_class = "fetch-ok" if fetch_ok else "fetch-miss"
    return (
        f'<tr>'
        f'<td class="skill-name"><code>{_esc(name)}</code>'
        f' <span class="{fetch_class}">{fetch_icon}</span></td>'
        f'<td><code>{_esc(canon)}</code></td>'
        f'<td>{status_html} {type_html}</td>'
        f'<td>{origin_html}</td>'
        f'</tr>'
    )


def render_suite_section(suite_id: str, skills: list[dict], fusions: dict) -> str:
    label = SUITE_LABELS.get(suite_id, suite_id)
    note = SUITE_NOTES.get(suite_id, "")
    fusion = fusions.get(suite_id, {})
    fusion_html = ""
    if fusion.get("named_id"):
        sym, color = TYPE_SYMBOL.get(fusion.get("type", ""), ("?", "#888"))
        fusion_html = f"""
        <div class="fusion-card">
          <span class="fusion-icon" style="color:{color}">{sym}</span>
          <div class="fusion-info">
            <strong>Suite Fusion:</strong>
            <code>{_esc(fusion["named_id"])}</code>
            {_level_badge(fusion.get("level"))}
            {_type_chip(fusion.get("type"))}
            {"<span class='chip chip-origin'>origin ★</span>" if fusion.get("origin") else ""}
            <br><small>canon node: <code>{_esc(fusion.get("canon_id",""))}</code></small>
          </div>
        </div>"""

    rows = "\n".join(render_skill_row(s) for s in skills)

    return f"""
    <section class="suite-section" id="suite-{_esc(suite_id)}">
      <h2>{_esc(label)} <span class="skill-count">({len(skills)})</span></h2>
      <p class="suite-note">{note}</p>
      {fusion_html}
      <table class="skill-table">
        <thead>
          <tr>
            <th>Ruflo Skill</th>
            <th>Gaia Canon Node</th>
            <th>Status</th>
            <th>Origin</th>
          </tr>
        </thead>
        <tbody>
          {rows}
        </tbody>
      </table>
    </section>"""


def render_capstone(capstone: dict) -> str:
    prereqs = capstone.get("prerequisites", [])
    prereq_list = "".join(f"<li><code>{_esc(p)}</code></li>" for p in prereqs)
    return f"""
    <section class="suite-section capstone-section" id="capstone">
      <h2>◆ Capstone: <code>ruvnet/ruflo</code> <span class="level-badge">6★ Apex</span></h2>
      <p class="suite-note">
        The master ultimate combining all 6 suite fusions.
        Qualifies via the Grandmaster Path: 34k+ stars (passes 10k threshold) + AgentDB 5★ ultimate.
        A Class A evidence source must be confirmed during the <code>/gaia-curate</code> sweep.
      </p>
      <div class="capstone-prereqs">
        <strong>Prerequisites ({len(prereqs)}):</strong>
        <ul>{prereq_list}</ul>
      </div>
    </section>"""


def render_queen_seraphina() -> str:
    return """
    <aside class="callout callout-seraphina">
      <h3>👑 Queen Seraphina</h3>
      <p>
        Queen Seraphina is the AI assistant embedded in the <code>flow-nexus-platform</code> skill's
        "System Utilities" section. She provides multi-turn conversation support with tool execution
        capabilities for architecture design and code deployment tasks.
      </p>
      <p>
        <strong>She is not a standalone skill.</strong> Document her as a notable feature in the body of
        <code>registry/named/ruvnet/flow-nexus-platform.md</code>, under a "Queen Seraphina" heading.
      </p>
    </aside>"""


def render_action_checklist(data: dict) -> str:
    missing = data.get("missing", [])
    new_canon_count = sum(1 for s in data["skills"] if s.get("canon_is_new"))
    existing_map_count = sum(1 for s in data["skills"] if not s.get("canon_is_new") and s.get("canon_mapping"))
    return f"""
    <section class="checklist-section" id="action-checklist">
      <h2>Action Checklist</h2>

      <h3>Phase 0 — Research Artifact (current branch: <code>claude/ruflo-skill-research-ar9JG</code>)</h3>
      <ul>
        <li>✅ <code>scripts/fetch_ruflo_skills.py</code> created — fetches 39 SKILL.md files</li>
        <li>✅ <code>scripts/generate_ruflo_curation.py</code> created — renders this document</li>
        <li>✅ <code>docs/ruflo-curation.html</code> generated</li>
        {"<li>⚠ Missing skills: " + ", ".join(f"<code>{_esc(m)}</code>" for m in missing) + "</li>" if missing else ""}
      </ul>

      <h3>Phase 1 — Canon Branch: <code>review/meta/ruflo-canon</code></h3>
      <ul>
        <li>Add <strong>{new_canon_count}</strong> new generic nodes to <code>registry/gaia.json</code> and <code>registry/nodes/</code></li>
        <li>Order: basic nodes → extra nodes → unique (<code>hive-mind-coordination</code>) → ultimates (<code>agent-memory-platform</code>, <code>ruflo</code>)</li>
        <li>Run <code>python scripts/validate.py</code></li>
        <li>Run <code>python scripts/generateProjections.py</code></li>
        <li>Bump version lockstep: <code>pyproject.toml</code>, both <code>package.json</code>, <code>registry/gaia.json</code></li>
      </ul>

      <h3>Phase 2 — Named Branch: <code>review/meta/ruflo-named</code></h3>
      <ul>
        <li>Add <strong>38 new</strong> named <code>.md</code> files under <code>registry/named/ruvnet/</code> (plus update existing <code>flow-nexus-swarm.md</code>)</li>
        <li>Add <strong>6 fusion</strong> named <code>.md</code> files (one per suite with a fusion)</li>
        <li>Add <strong>1 capstone</strong>: <code>registry/named/ruvnet/ruflo.md</code></li>
        <li>Run <code>python scripts/generateNamedIndex.py</code></li>
        <li>Run <code>python scripts/generateProfilePages.py</code></li>
        <li>Existing mappings ({existing_map_count} skills map to existing canon — set <code>origin: false</code> where appropriate)</li>
      </ul>

      <h3>Phase 3 — Evidence Sweep: <code>review/meta/ruflo-evidence</code></h3>
      <ul>
        <li>Dispatch 4 parallel <code>/gaia-curate</code> agents:</li>
        <li><strong>Agent 1:</strong> Evidence collection (Class A/B sources for 47 entries)</li>
        <li><strong>Agent 2:</strong> Demotion review (check if ruflo displaces existing named skills)</li>
        <li><strong>Agent 3:</strong> Mapping verification (confirm ruflo→gaia node mappings)</li>
        <li><strong>Agent 4:</strong> Variant detection (find other contributors fitting new ruflo-created canons)</li>
        <li>Run <code>python scripts/verify_evidence.py</code> after sweep</li>
        <li>Confirm 6★ claim via Grandmaster Path in <code>registry/schema/meta.json</code></li>
      </ul>
    </section>"""


def render_stats(data: dict) -> str:
    total = data.get("total", 0)
    ok = data.get("fetched_ok", 0)
    new_canon = sum(1 for s in data["skills"] if s.get("canon_is_new"))
    fused = sum(1 for f in data.get("fusions", {}).values() if f.get("named_id"))
    return f"""
    <div class="stats-row">
      <div class="stat-card"><span class="stat-num">{total}</span><span class="stat-label">Total Skills</span></div>
      <div class="stat-card"><span class="stat-num">{ok}</span><span class="stat-label">SKILL.md Fetched</span></div>
      <div class="stat-card"><span class="stat-num">{new_canon}</span><span class="stat-label">New Canon Nodes</span></div>
      <div class="stat-card"><span class="stat-num">{fused}</span><span class="stat-label">Suite Fusions</span></div>
      <div class="stat-card"><span class="stat-num">1</span><span class="stat-label">Capstone (6★)</span></div>
    </div>"""


def render_html(data: dict) -> str:
    fetched_at = data.get("fetched_at", "unknown")

    # Group skills by suite
    skills_by_suite: dict[str, list[dict]] = {s: [] for s in SUITE_ORDER}
    for skill in data.get("skills", []):
        suite = skill.get("suite", "standalone")
        if suite in skills_by_suite:
            skills_by_suite[suite].append(skill)
        else:
            skills_by_suite.setdefault("standalone", []).append(skill)

    suite_sections = "\n".join(
        render_suite_section(suite_id, skills_by_suite[suite_id], data.get("fusions", {}))
        for suite_id in SUITE_ORDER
    )

    stats_html = render_stats(data)
    capstone_html = render_capstone(data.get("capstone", {}))
    seraphina_html = render_queen_seraphina()
    checklist_html = render_action_checklist(data)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>Ruflo Meta-Curation Brief — Gaia Registry</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  <style>
    :root {{
      --bg: #0a0a0f;
      --surface: #13131a;
      --border: #23232e;
      --text: #e8e6e1;
      --muted: #888;
      --accent: #f59e0b;
      --blue: #38bdf8;
      --purple: #c084fc;
      --violet: #7c3aed;
      --green: #4ade80;
      --red: #f87171;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      font-family: 'Bricolage Grotesque', sans-serif;
      background: var(--bg);
      color: var(--text);
      line-height: 1.6;
      padding: 2rem;
    }}
    a {{ color: var(--blue); }}
    h1 {{ font-family: 'EB Garamond', serif; font-size: 2.2rem; margin-bottom: .25rem; }}
    h2 {{ font-family: 'EB Garamond', serif; font-size: 1.5rem; margin: 2rem 0 .75rem; border-bottom: 1px solid var(--border); padding-bottom: .4rem; }}
    h3 {{ font-size: 1rem; margin: 1.25rem 0 .5rem; color: var(--accent); }}
    p {{ margin: .5rem 0; }}
    code {{ font-family: 'JetBrains Mono', monospace; font-size: .82em; background: var(--surface); border: 1px solid var(--border); border-radius: 3px; padding: 0 4px; }}
    ul {{ padding-left: 1.5rem; }}
    li {{ margin: .25rem 0; }}
    header {{ margin-bottom: 2rem; border-bottom: 1px solid var(--border); padding-bottom: 1.5rem; }}
    .meta {{ color: var(--muted); font-size: .85rem; margin-top: .5rem; }}
    .stats-row {{ display: flex; gap: 1rem; flex-wrap: wrap; margin: 1.5rem 0; }}
    .stat-card {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: .75rem 1.25rem; text-align: center; min-width: 120px; }}
    .stat-num {{ display: block; font-size: 1.8rem; font-weight: 700; color: var(--accent); font-family: 'JetBrains Mono', monospace; }}
    .stat-label {{ font-size: .75rem; color: var(--muted); text-transform: uppercase; letter-spacing: .05em; }}
    .suite-section {{ margin: 2.5rem 0; }}
    .skill-count {{ font-size: .85rem; color: var(--muted); font-family: 'JetBrains Mono', monospace; }}
    .suite-note {{ color: var(--muted); font-size: .9rem; margin-bottom: 1rem; }}
    .fusion-card {{ background: var(--surface); border: 1px solid var(--accent); border-radius: 8px; padding: .75rem 1rem; margin-bottom: 1rem; display: flex; align-items: flex-start; gap: .75rem; }}
    .fusion-icon {{ font-size: 1.5rem; line-height: 1; flex-shrink: 0; }}
    .fusion-info {{ flex: 1; }}
    .skill-table {{ width: 100%; border-collapse: collapse; font-size: .88rem; }}
    .skill-table th {{ text-align: left; padding: .5rem .75rem; background: var(--surface); border-bottom: 2px solid var(--border); color: var(--muted); text-transform: uppercase; font-size: .75rem; letter-spacing: .06em; font-family: 'JetBrains Mono', monospace; }}
    .skill-table td {{ padding: .45rem .75rem; border-bottom: 1px solid var(--border); vertical-align: middle; }}
    .skill-table tr:hover td {{ background: var(--surface); }}
    .skill-name {{ font-family: 'JetBrains Mono', monospace; }}
    .level-badge {{ background: color-mix(in srgb, var(--accent) 15%, transparent); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 40%, transparent); border-radius: 4px; padding: 1px 6px; font-size: .78rem; font-family: 'JetBrains Mono', monospace; white-space: nowrap; }}
    .type-chip {{ font-size: .82rem; font-weight: 600; }}
    .chip {{ display: inline-block; border-radius: 4px; padding: 1px 7px; font-size: .75rem; margin: 1px; }}
    .chip-exists {{ background: color-mix(in srgb, var(--green) 12%, transparent); color: var(--green); border: 1px solid color-mix(in srgb, var(--green) 35%, transparent); }}
    .chip-new {{ background: color-mix(in srgb, var(--purple) 12%, transparent); color: var(--purple); border: 1px solid color-mix(in srgb, var(--purple) 35%, transparent); }}
    .chip-origin {{ background: color-mix(in srgb, var(--accent) 12%, transparent); color: var(--accent); border: 1px solid color-mix(in srgb, var(--accent) 35%, transparent); }}
    .chip-variant {{ background: color-mix(in srgb, var(--muted) 12%, transparent); color: var(--muted); border: 1px solid color-mix(in srgb, var(--muted) 35%, transparent); }}
    .fetch-ok {{ color: var(--green); font-size: .75rem; }}
    .fetch-miss {{ color: var(--red); font-size: .75rem; }}
    .callout {{ border-radius: 8px; padding: 1.25rem 1.5rem; margin: 2rem 0; }}
    .callout-seraphina {{ background: color-mix(in srgb, var(--violet) 10%, transparent); border: 1px solid color-mix(in srgb, var(--violet) 40%, transparent); }}
    .callout h3 {{ color: var(--purple); margin-top: 0; }}
    .capstone-section {{ border: 1px solid var(--accent); border-radius: 8px; padding: 1.5rem; background: color-mix(in srgb, var(--accent) 5%, transparent); }}
    .capstone-prereqs {{ margin-top: .75rem; }}
    .capstone-prereqs ul {{ margin-top: .4rem; columns: 2; }}
    .checklist-section {{ margin-top: 2.5rem; }}
    nav.toc {{ background: var(--surface); border: 1px solid var(--border); border-radius: 8px; padding: 1rem 1.5rem; margin-bottom: 2rem; }}
    nav.toc ul {{ list-style: none; padding: 0; display: flex; flex-wrap: wrap; gap: .5rem 1.5rem; }}
    nav.toc a {{ color: var(--muted); font-size: .85rem; text-decoration: none; }}
    nav.toc a:hover {{ color: var(--text); }}
  </style>
</head>
<body>

  <header>
    <h1>Ruflo Meta-Curation Brief</h1>
    <p>Curation plan for all <strong>ruvnet/ruflo</strong> skills → Gaia registry</p>
    <p class="meta">
      Source: <a href="https://github.com/ruvnet/ruflo">github.com/ruvnet/ruflo</a> ·
      Contributor: <strong>ruvnet</strong> ·
      Fetched: {_esc(fetched_at)} ·
      Branch: <code>claude/ruflo-skill-research-ar9JG</code>
    </p>
  </header>

  <nav class="toc">
    <ul>
      <li><a href="#suite-flow-nexus">Flow Nexus</a></li>
      <li><a href="#suite-agentdb">AgentDB</a></li>
      <li><a href="#suite-github">GitHub</a></li>
      <li><a href="#suite-hive-mind">Hive Mind</a></li>
      <li><a href="#suite-reasoningbank">ReasoningBank</a></li>
      <li><a href="#suite-swarm">Swarm → V3</a></li>
      <li><a href="#suite-v3">V3</a></li>
      <li><a href="#suite-standalone">Standalone</a></li>
      <li><a href="#capstone">Capstone ◆</a></li>
      <li><a href="#queen-seraphina">Queen Seraphina</a></li>
      <li><a href="#action-checklist">Checklist</a></li>
    </ul>
  </nav>

  {stats_html}

  {suite_sections}

  {capstone_html}

  <div id="queen-seraphina">
    {seraphina_html}
  </div>

  {checklist_html}

  <footer style="margin-top:3rem; padding-top:1rem; border-top:1px solid var(--border); color:var(--muted); font-size:.8rem;">
    Generated by <code>scripts/generate_ruflo_curation.py</code> · Gaia Skill Registry
  </footer>

</body>
</html>"""


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Generate docs/ruflo-curation.html.")
    parser.add_argument("--raw", default=str(RAW_DEFAULT), help="Path to ruflo-skills-raw.json")
    parser.add_argument("--out", default=str(OUT_DEFAULT), help="Output HTML path")
    args = parser.parse_args(argv)

    raw_path = Path(args.raw)
    if not raw_path.exists():
        print(f"ERROR: {raw_path} not found. Run scripts/fetch_ruflo_skills.py first.", file=sys.stderr)
        return 1

    data = json.loads(raw_path.read_text(encoding="utf-8"))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(render_html(data), encoding="utf-8")
    print(f"Wrote {out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
