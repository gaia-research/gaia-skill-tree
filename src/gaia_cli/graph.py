"""Graph rendering helpers for the Gaia CLI.

The registry source of truth is registry/gaia.json. This module deliberately uses
only the Python standard library so graph viewing remains available in a fresh
clone without Graphviz, Matplotlib, or a browser automation dependency.
"""

from __future__ import annotations

import json
import math
import os
import subprocess
import sys
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from gaia_cli.leveling import level_summary
from gaia_cli.registry import named_skills_index_path, registry_graph_path, registry_nodes_dir

PALETTE = {
    "basic": {"fill": "#38bdf8", "stroke": "#7dd3fc", "label": "Basic"},
    "extra": {"fill": "#a78bfa", "stroke": "#c4b5fd", "label": "Extra"},
    "unique": {"fill": "#7c3aed", "stroke": "#a78bfa", "label": "Unique"},
    "ultimate": {"fill": "#fbbf24", "stroke": "#fde68a", "label": "Ultimate"},
}
TYPE_ORDER = {"basic": 0, "extra": 1, "unique": 2, "ultimate": 3}
RADIUS_BY_TYPE = {"basic": 285, "extra": 170, "unique": 112, "ultimate": 54}
NODE_RADIUS = {"basic": 6, "extra": 10, "unique": 13, "ultimate": 15}


def _registry_root(registry_path: str | os.PathLike[str]) -> Path:
    return Path(registry_path).expanduser().resolve()


def load_graph(registry_path: str | os.PathLike[str] = ".") -> dict[str, Any]:
    graph_path = Path(registry_graph_path(_registry_root(registry_path)))
    if not graph_path.exists():
        raise FileNotFoundError(
            f"Registry graph not found at {graph_path}. "
            "Run gaia init from a gaia-skill-tree clone."
        )
    with graph_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_named_skills(registry_path: str | os.PathLike[str] = ".") -> dict[str, Any]:
    named_path = Path(named_skills_index_path(_registry_root(registry_path)))
    if not named_path.exists():
        return {"buckets": {}}
    with named_path.open("r", encoding="utf-8") as f:
        return json.load(f)


def _stable_angle(skill_id: str, index: int, total: int) -> float:
    # Deterministic jitter prevents same-type nodes from forming a perfectly
    # uniform ring while keeping output stable across machines.
    seed = sum((i + 1) * ord(ch) for i, ch in enumerate(skill_id))
    jitter = ((seed % 997) / 997.0 - 0.5) * (math.tau / max(total, 1)) * 0.35
    return math.tau * index / max(total, 1) + jitter - math.pi / 2


def _named_max_levels(named_buckets: dict[str, Any]) -> dict[str, str]:
    """Map generic skill id -> highest named-variant star (generics are rank-less)."""
    order = ["2★", "3★", "4★", "5★", "6★"]
    out: dict[str, str] = {}
    for ref, entries in (named_buckets or {}).items():
        levels = [e.get("level") for e in entries if e.get("level") in order]
        if levels:
            out[ref] = max(levels, key=order.index)
    return out


def build_render_graph(
    graph: dict[str, Any], width: int = 1280, height: int = 880,
    named_buckets: dict[str, Any] | None = None,
) -> dict[str, Any]:
    skills = graph.get("skills", [])
    named_max = _named_max_levels(named_buckets or {})
    groups: dict[str, list[dict[str, Any]]] = {
        "basic": [],
        "extra": [],
        "unique": [],
        "ultimate": [],
    }
    for skill in skills:
        groups.setdefault(skill.get("type", "basic"), []).append(skill)

    for bucket in groups.values():
        bucket.sort(
            key=lambda s: (str(named_max.get(s.get("id"), "")), str(s.get("name", s.get("id", ""))))
        )

    cx, cy = width / 2, height / 2
    nodes: list[dict[str, Any]] = []
    for skill_type in ("basic", "extra", "unique", "ultimate"):
        bucket = groups.get(skill_type, [])
        radius = RADIUS_BY_TYPE.get(skill_type, 220)
        for i, skill in enumerate(bucket):
            angle = _stable_angle(str(skill.get("id", "")), i, len(bucket))
            local_radius = radius if len(bucket) > 1 else 0
            x = cx + math.cos(angle) * local_radius
            y = cy + math.sin(angle) * local_radius
            star = named_max.get(skill.get("id"))
            level_meta = level_summary(skill)
            nodes.append(
                {
                    "id": skill.get("id"),
                    "label": skill.get("name") or skill.get("id"),
                    "type": skill_type,
                    # Generic refs are rank-less — prefer the top named-variant
                    # star; fall back to any legacy level for back-compat.
                    "level": star or skill.get("level", ""),
                    "effectiveLevel": star or level_meta["effectiveLevel"],
                    "levelMeta": level_meta,
                    "demerits": level_meta["demerits"],
                    "rarity": skill.get("rarity"),
                    "description": skill.get("description", ""),
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "radius": NODE_RADIUS.get(skill_type, 7),
                }
            )

    skill_ids = {node["id"] for node in nodes}
    edges: list[dict[str, Any]] = []
    for skill in skills:
        target = skill.get("id")
        if target not in skill_ids:
            continue
        for source in skill.get("prerequisites", []) or []:
            if source in skill_ids:
                edges.append(
                    {
                        "source": source,
                        "target": target,
                        "type": skill.get("type", "basic"),
                    }
                )

    nodes.sort(
        key=lambda n: (TYPE_ORDER.get(str(n.get("type")), 9), str(n.get("label", "")))
    )
    return {
        "version": graph.get("version"),
        "generatedAt": graph.get("generatedAt"),
        "width": width,
        "height": height,
        "nodes": nodes,
        "edges": edges,
    }


def write_gexf(
    registry_path: str | os.PathLike[str] = ".",
    output: str | os.PathLike[str] | None = None,
) -> Path:
    """Generate GEXF 1.2 from registry/nodes/ and write to output (default: docs/graph/gaia.gexf).

    Uses only xml.etree.ElementTree from the stdlib — no lxml required.
    """
    root = _registry_root(registry_path)
    nodes_dir = registry_nodes_dir(root)

    # Collect skills from nodes directory
    skills: list[dict[str, Any]] = []
    if os.path.isdir(nodes_dir):
        for dirpath, _dirs, files in os.walk(nodes_dir):
            for fname in sorted(files):
                if fname.endswith(".json"):
                    fpath = os.path.join(dirpath, fname)
                    try:
                        with open(fpath, "r", encoding="utf-8") as f:
                            skill = json.load(f)
                        if skill.get("id"):
                            skills.append(skill)
                    except (OSError, json.JSONDecodeError):
                        continue

    # Also fallback to gaia.json skills if nodes dir is empty
    if not skills:
        graph = load_graph(root)
        skills = graph.get("skills", [])

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    # Build XML tree
    ET.register_namespace("", "http://www.gexf.net/1.2draft")
    gexf_el = ET.Element("gexf")
    gexf_el.set("xmlns", "http://www.gexf.net/1.2draft")
    gexf_el.set("version", "1.2")

    meta_el = ET.SubElement(gexf_el, "meta")
    meta_el.set("lastmodifieddate", today)
    ET.SubElement(meta_el, "creator").text = "Gaia"
    ET.SubElement(meta_el, "description").text = "Gaia Skill Registry Graph"

    graph_el = ET.SubElement(gexf_el, "graph")
    graph_el.set("defaultedgetype", "directed")
    graph_el.set("mode", "static")

    # Attribute declarations
    attrs_el = ET.SubElement(graph_el, "attributes")
    attrs_el.set("class", "node")
    for attr_id in ("level", "rarity", "status", "type"):
        attr_el = ET.SubElement(attrs_el, "attribute")
        attr_el.set("id", attr_id)
        attr_el.set("title", attr_id)
        attr_el.set("type", "string")

    # Nodes
    nodes_el = ET.SubElement(graph_el, "nodes")
    skill_ids: set[str] = set()
    for skill in sorted(skills, key=lambda s: str(s.get("id", ""))):
        sid = skill.get("id", "")
        if not sid:
            continue
        skill_ids.add(sid)
        node_el = ET.SubElement(nodes_el, "node")
        node_el.set("id", sid)
        node_el.set("label", skill.get("name") or sid)
        attvalues_el = ET.SubElement(node_el, "attvalues")
        for attr_id in ("level", "rarity", "status", "type"):
            val = skill.get(attr_id, "")
            if val:
                av = ET.SubElement(attvalues_el, "attvalue")
                av.set("for", attr_id)
                av.set("value", str(val))

    # Edges
    edges_el = ET.SubElement(graph_el, "edges")
    edge_idx = 0
    for skill in skills:
        target = skill.get("id", "")
        if target not in skill_ids:
            continue
        for prereq in skill.get("prerequisites", []) or []:
            if prereq in skill_ids:
                edge_el = ET.SubElement(edges_el, "edge")
                edge_el.set("id", str(edge_idx))
                edge_el.set("source", prereq)
                edge_el.set("target", target)
                edge_idx += 1

    # Determine output path
    if output is None:
        out_path = root / "docs" / "graph" / "gaia.gexf"
    else:
        out_path = Path(output)
        if not out_path.is_absolute():
            out_path = root / out_path

    out_path.parent.mkdir(parents=True, exist_ok=True)

    tree = ET.ElementTree(gexf_el)
    ET.indent(tree, space="  ")
    with out_path.open("wb") as f:
        tree.write(f, xml_declaration=True, encoding="UTF-8")

    return out_path


def render_svg(render_graph: dict[str, Any]) -> str:
    width = int(render_graph.get("width", 1280))
    height = int(render_graph.get("height", 880))
    nodes = render_graph.get("nodes", [])
    edges = render_graph.get("edges", [])
    node_by_id = {node["id"]: node for node in nodes}

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}" role="img" aria-labelledby="title desc">',
        '<title id="title">Gaia AI Agent Skill Graph</title>',
        '<desc id="desc">Canonical Gaia skill graph rendered from registry/gaia.json, with basic skills on the outer ring, extra skills in the middle ring, and ultimate skills at the core.</desc>',
        "<defs>",
        '<radialGradient id="bg" cx="50%" cy="45%" r="70%"><stop offset="0%" stop-color="#172554"/><stop offset="55%" stop-color="#06111f"/><stop offset="100%" stop-color="#030712"/></radialGradient>',
        '<filter id="glow" x="-50%" y="-50%" width="200%" height="200%"><feGaussianBlur stdDeviation="4" result="blur"/><feMerge><feMergeNode in="blur"/><feMergeNode in="SourceGraphic"/></feMerge></filter>',
        "</defs>",
        f'<rect width="{width}" height="{height}" fill="url(#bg)"/>',
        '<g opacity="0.32" stroke="#334155" stroke-width="1" fill="none">',
        f'<circle cx="{width / 2:.1f}" cy="{height / 2:.1f}" r="{RADIUS_BY_TYPE["basic"]}"/>',
        f'<circle cx="{width / 2:.1f}" cy="{height / 2:.1f}" r="{RADIUS_BY_TYPE["extra"]}"/>',
        f'<circle cx="{width / 2:.1f}" cy="{height / 2:.1f}" r="{RADIUS_BY_TYPE["ultimate"]}"/>',
        "</g>",
        '<g class="edges" fill="none">',
    ]

    for edge in edges:
        source = node_by_id.get(edge.get("source"))
        target = node_by_id.get(edge.get("target"))
        if not source or not target:
            continue
        color = PALETTE.get(str(edge.get("type")), PALETTE["basic"])["fill"]
        lines.append(
            f'<line x1="{source["x"]}" y1="{source["y"]}" x2="{target["x"]}" y2="{target["y"]}" stroke="{color}" stroke-opacity="0.32" stroke-width="1.15"/>'
        )
    lines.append("</g>")

    lines.append('<g class="nodes" filter="url(#glow)">')
    for node in nodes:
        color = PALETTE.get(str(node.get("type")), PALETTE["basic"])
        lines.append(
            f'<circle cx="{node["x"]}" cy="{node["y"]}" r="{node["radius"]}" fill="{color["fill"]}" stroke="{color["stroke"]}" stroke-width="1.6"><title>{escape(str(node.get("label", "")))}</title></circle>'
        )
    lines.append("</g>")

    lines.append(
        '<g class="labels" font-family="Inter, ui-sans-serif, system-ui, sans-serif" text-anchor="middle">'
    )
    for node in nodes:
        typ = str(node.get("type"))
        if (
            typ == "basic"
            and int(sum(ord(c) for c in str(node.get("id", ""))) % 4) != 0
        ):
            continue
        color = PALETTE.get(typ, PALETTE["basic"])["fill"]
        size = 10 if typ == "basic" else 12 if typ == "extra" else 16
        weight = 600 if typ != "ultimate" else 800
        y = float(node["y"]) - float(node["radius"]) - 7
        lines.append(
            f'<text x="{node["x"]}" y="{y:.1f}" fill="{color}" font-size="{size}" font-weight="{weight}" opacity="0.92">{escape(str(node.get("label", "")))}</text>'
        )
    lines.append("</g>")

    legend_x = 44
    legend_y = height - 110
    lines.extend(
        [
            '<g font-family="Inter, ui-sans-serif, system-ui, sans-serif" font-size="14" fill="#cbd5e1">',
            f'<text x="{legend_x}" y="{legend_y - 22}" font-size="20" font-weight="800" fill="#e2e8f0">Gaia Skill Graph</text>',
        ]
    )
    for i, skill_type in enumerate(("basic", "extra", "unique", "ultimate")):
        y = legend_y + i * 28
        color = PALETTE[skill_type]
        count = sum(1 for node in nodes if node.get("type") == skill_type)
        lines.append(
            f'<circle cx="{legend_x + 8}" cy="{y - 5}" r="6" fill="{color["fill"]}"/>'
        )
        lines.append(
            f'<text x="{legend_x + 24}" y="{y}">{color["label"]}: {count}</text>'
        )
    lines.append("</g>")
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _html_json(data: dict[str, Any]) -> str:
    return escape(json.dumps(data, indent=2, ensure_ascii=False), quote=False)


def render_html(
    graph: dict[str, Any],
    named_skills: dict[str, Any] | None = None,
    *,
    user_ctx: dict[str, Any] | None = None,
) -> str:
    named_skills = named_skills or {"buckets": {}}
    # Build the user context JSON script tag (empty dict when no user)
    user_ctx_data: dict[str, Any] = user_ctx if user_ctx is not None else {}
    user_ctx_tag = f'<script type="application/json" id="gaia-user-ctx">{_html_json(user_ctx_data)}</script>'
    # Title text for h1 — use username when available
    _username = user_ctx.get("username", "") if user_ctx else ""
    _title_text = f"{_username}'s Skill Graph" if _username else "Gaia Skill Graph"
    return f"""<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Gaia Skill Graph</title>
<style>
  :root {{
    color-scheme: dark;
    --bg: #020617;
    --panel: rgba(15, 23, 42, .82);
    --panel-border: rgba(148, 163, 184, .22);
    --text: #e2e8f0;
    --muted: #94a3b8;
    --basic: #38bdf8;
    --extra: #c084fc;
    --ultimate: #f59e0b;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; min-height: 100%; background: var(--bg); color: var(--text); font-family: Inter, ui-sans-serif, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; }}
  body {{ overflow: hidden; }}
  .shell {{ position: fixed; inset: 0; }}
  #gaiaGraphCanvas {{ display: block; width: 100%; height: 100%; }}
  .title-panel {{
    position: fixed; top: 16px; left: 16px; z-index: 2;
    background: var(--panel); border: 1px solid var(--panel-border); border-radius: 8px;
    box-shadow: 0 18px 50px rgba(0, 0, 0, .28); backdrop-filter: blur(16px);
    padding: 10px 12px; pointer-events: auto; display: flex; align-items: center; gap: 10px; flex-wrap: wrap;
  }}
  h1 {{ margin: 0; font-size: 15px; line-height: 1.15; letter-spacing: 0; }}
  .meta {{ color: var(--muted); font-size: 12px; }}
  #resetView {{
    height: 36px; border: 1px solid rgba(148, 163, 184, .28); border-radius: 7px;
    background: rgba(15, 23, 42, .72); color: var(--text); padding: 0 11px; cursor: pointer;
  }}
  .skill-tooltip{{
    position:absolute;pointer-events:none;display:none;z-index:10;
    background:rgba(3,7,18,.9);border:1px solid rgba(148,163,184,.22);
    border-radius:.6rem;padding:.6rem .85rem;min-width:148px;max-width:230px;
    backdrop-filter:blur(8px);
  }}
  .skill-tooltip-name{{font-weight:800;font-size:1rem;line-height:1.2;margin-bottom:.38rem}}
  .skill-tooltip-row{{display:flex;align-items:center;gap:.4rem .5rem;flex-wrap:wrap}}
  .skill-tooltip-badge{{
    font-size:.65rem;font-weight:800;letter-spacing:.06em;
    padding:.14rem .42rem;border-radius:999px;border:1px solid currentColor;
    opacity:.85;
  }}
  .skill-tooltip-type-basic{{color:#38bdf8}}
  .skill-tooltip-type-extra{{color:#c084fc}}
  .skill-tooltip-type-ultimate{{color:#f59e0b}}
  .graph-search-wrap{{position:absolute;top:.75rem;right:.75rem;z-index:10}}
  .graph-search{{
    background:rgba(3,7,18,.15);border:1px solid rgba(148,163,184,.15);
    border-radius:999px;padding:.28rem .72rem;font-size:.74rem;
    color:#e2e8f0;outline:none;width:130px;font-family:inherit;
    transition:background .2s,border-color .2s,width .2s;
  }}
  .graph-search::placeholder{{color:rgba(148,163,184,.38)}}
  .graph-search:hover,.graph-search:focus{{
    background:rgba(3,7,18,.72);border-color:rgba(148,163,184,.5);width:175px;
  }}
  .graph-legend{{
    position:absolute;top:50%;right:.75rem;transform:translateY(-50%);z-index:10;
    display:flex;flex-direction:column;gap:.55rem;
    background:rgba(3,7,18,.78);border:none;
    border-radius:.6rem;padding:.5rem .65rem;backdrop-filter:blur(8px);
    max-height:calc(100% - 3.5rem);overflow-y:auto;user-select:none;
  }}
  .graph-legend-section{{display:flex;flex-direction:column;gap:.18rem}}
  .graph-legend-heading{{
    font-size:.6rem;font-weight:700;letter-spacing:.1em;text-transform:uppercase;
    color:#64748b;margin-bottom:.1rem;
  }}
  .graph-legend-item{{
    display:flex;align-items:center;gap:.38rem;
    font-size:.7rem;font-weight:600;color:#94a3b8;
    padding:.18rem .38rem;border-radius:4px;cursor:pointer;
    transition:background .15s,color .15s;
  }}
  .graph-legend-item:hover{{background:rgba(255,255,255,.06);color:#e2e8f0}}
  .graph-legend-item.active{{background:rgba(56,189,248,.12);color:#e2e8f0;box-shadow:inset 0 0 0 1px rgba(56,189,248,.3)}}
  .graph-legend-swatch{{border-radius:50%;flex-shrink:0}}
  .graph-legend-ranks{{display:flex;flex-wrap:wrap;gap:.28rem;padding:.1rem 0}}
  .graph-legend-rank-pill{{
    display:inline-flex;align-items:center;justify-content:center;
    width:22px;height:22px;border-radius:50%;
    font-size:.6rem;font-weight:700;cursor:pointer;
    transition:transform .15s,box-shadow .15s;
  }}
  .graph-legend-rank-pill:hover{{transform:scale(1.18);box-shadow:0 0 8px currentColor}}
  .graph-legend-rank-pill.active{{transform:scale(1.18);box-shadow:0 0 10px currentColor,inset 0 0 0 1.5px currentColor}}
  .graph-label-toggle{{
    position:absolute;right:1rem;bottom:1rem;z-index:2;
    color:#94a3b8;font-size:.72rem;font-weight:700;background:rgba(3,7,18,.68);
    border:1px solid rgba(148,163,184,.18);border-radius:999px;padding:.3rem .7rem;
    cursor:pointer;transition:border-color .2s,color .2s,background .2s;font-family:inherit;
  }}
  .graph-label-toggle:hover{{border-color:rgba(56,189,248,.5);color:#e2e8f0}}
  .graph-label-toggle.active{{background:rgba(56,189,248,.12);border-color:rgba(56,189,248,.45);color:#e2e8f0}}
  .graph-redpill{{
    position:absolute;bottom:3.4rem;right:.75rem;z-index:10;
    color:#f87171;font-size:.72rem;font-weight:700;background:rgba(3,7,18,.68);
    border:1px solid rgba(239,68,68,.45);border-radius:999px;padding:.3rem .78rem;
    cursor:pointer;transition:all .2s;font-family:inherit;white-space:nowrap;
  }}
  .graph-redpill:hover{{border-color:rgba(239,68,68,.75);color:#fca5a5;background:rgba(239,68,68,.08)}}
  .graph-redpill.active{{
    background:rgba(239,68,68,.18);border-color:rgba(239,68,68,.7);
    color:#fca5a5;box-shadow:0 0 14px rgba(239,68,68,.35);
  }}
  @media (max-width:700px){{
    .graph-legend{{top:auto;bottom:2.8rem;right:.5rem;transform:none;padding:.4rem .5rem;font-size:.65rem}}
  }}
</style>
</head>
<body>
<main class="shell" id="graphShell">
  <canvas id="gaiaGraphCanvas"></canvas>
</main>
<div class="title-panel">
  <h1>{_title_text}</h1>
  <div class="meta" id="graphMeta">Loading…</div>
  <button id="resetView" type="button">Reset</button>
</div>
<script type="application/json" id="gaia-graph-data">{_html_json(graph)}</script>
<script type="application/json" id="gaia-named-skills">{_html_json(named_skills)}</script>
{user_ctx_tag}
<script>
(() => {{
  const graph = JSON.parse(document.getElementById('gaia-graph-data').textContent);
  const namedIndex = JSON.parse(document.getElementById('gaia-named-skills').textContent);
  const canvas = document.getElementById('gaiaGraphCanvas');
  const ctx = canvas.getContext('2d');
  const meta = document.getElementById('graphMeta');
  const resetView = document.getElementById('resetView');

  const PALETTE = {{
    basic:    {{ rgb:'56,189,248',   hex:'#38bdf8' }},
    extra:    {{ rgb:'192,132,252',  hex:'#c084fc' }},
    ultimate: {{ rgb:'245,158,11',   hex:'#f59e0b' }},
  }};
  const RANK_META = {{
    '1★':  {{ name:'Awakened',       hex:'#38bdf8', bg:'rgba(56,189,248,.12)' }},
    '2★': {{ name:'Named',          hex:'#63cab7', bg:'rgba(99,202,183,.12)' }},
    '3★':{{ name:'Evolved',        hex:'#a78bfa', bg:'rgba(167,139,250,.12)' }},
    '4★': {{ name:'Hardened',       hex:'#e879f9', bg:'rgba(232,121,249,.12)' }},
    '5★':  {{ name:'Transcendent',   hex:'#fbbf24', bg:'rgba(251,191,36,.12)' }},
    '6★': {{ name:'Apex', hex:'#fbbf24', bg:'rgba(251,191,36,.20)' }},
  }};
   const SCALE = 1.25;

  // Parse user context (may be empty {{}} when no user is logged in)
  const userCtxEl = document.getElementById('gaia-user-ctx');
  const userCtx = userCtxEl ? JSON.parse(userCtxEl.textContent) : {{}};
  const ownedIds = new Set(Array.isArray(userCtx.owned_ids) ? userCtx.owned_ids : []);
  const userNamedMap = (userCtx.named_map && typeof userCtx.named_map === 'object') ? userCtx.named_map : {{}};

  const namedMap = {{}}, titleMap = {{}};
  Object.entries(namedIndex.buckets || {{}}).forEach(([skillId, entries]) => {{
    if (!Array.isArray(entries) || !entries.length) return;
    const origin = entries.find(e => e.origin) || entries[0];
    if (origin?.id) namedMap[skillId] = origin.id;
    if (origin?.title) titleMap[skillId] = origin.title;
  }});

  function normalizeSkills(graph) {{
    const TYPE_ALIASES = {{ atomic: 'basic', composite: 'extra', legendary: 'ultimate' }};
    const skills = (graph && graph.skills) ? graph.skills : [];
    return skills.map(skill => ({{
      id: skill.id,
      name: skill.name || skill.id,
      type: TYPE_ALIASES[skill.type] || skill.type || 'basic',
      level: skill.level || '',
      rarity: skill.rarity || '',
      description: skill.description || '',
      prerequisites: Array.isArray(skill.prerequisites) ? skill.prerequisites : [],
      named: namedMap[skill.id] || '',
      namedTitle: titleMap[skill.id] || '',
    }})).filter(skill => skill.id);
  }}

  function stableHash(str) {{
    let h = 2166136261;
    for (let i = 0; i < str.length; i += 1) {{
      h ^= str.charCodeAt(i);
      h = Math.imul(h, 16777619);
    }}
    return Math.abs(h >>> 0);
  }}

  // 2D ring layout: concentric circles by skill type, matching build_render_graph logic
  function ringPoint(radius, skillId, index, count) {{
    const seed = stableHash(skillId);
    const jitter = ((seed % 997) / 997.0 - 0.5) * (2 * Math.PI / Math.max(count, 1)) * 0.35;
    const angle = 2 * Math.PI * index / Math.max(count, 1) + jitter - Math.PI / 2;
    const r = count > 1 ? radius : 0;
    return {{
      x: Math.cos(angle) * r,
      y: Math.sin(angle) * r,
      phase: (seed % 628) / 100,
    }};
  }}

  function buildPositions(skills) {{
    const TYPE_ORDER = ['basic', 'extra', 'unique', 'ultimate'];
    const RADII = {{ basic: 285, extra: 170, unique: 112, ultimate: 54 }};
    const groups = {{ basic:[], extra:[], unique:[], ultimate:[] }};
    skills.forEach(skill => {{
      const bucket = groups[skill.type] || groups.basic;
      if (!groups[skill.type]) groups[skill.type] = bucket;
      bucket.push(skill);
    }});
    TYPE_ORDER.forEach(type => {{
      if (groups[type]) {{
        groups[type].sort((a, b) => {{
          const la = String(a.level || ''), lb = String(b.level || '');
          return la !== lb ? la.localeCompare(lb) : (a.name || a.id).localeCompare(b.name || b.id);
        }});
      }}
    }});
    const positions = {{}};
    Object.entries(groups).forEach(([type, group]) => {{
      const radius = RADII[type] || RADII.basic;
      group.forEach((skill, index) => {{
        positions[skill.id] = ringPoint(radius, skill.id, index, group.length);
      }});
    }});
    return positions;
  }}

  const skills = normalizeSkills(graph);
  const positions = buildPositions(skills);

  // project: apply pan+zoom and map ring coords to screen space
  function project(p) {{
    const z = state.zoom;
    return {{
      sx: state.width / 2 + p.x * z + state.panX,
      sy: state.height / 2 + p.y * z + state.panY,
      scale: z,
    }};
  }}

  const state = {{
    skills,
    positions,
    stars: [],
    width: 0,
    height: 0,
    t: 0,
    zoom: 1,
    panX: 0,
    panY: 0,
    dragging: false,
    dragLastX: 0,
    dragLastY: 0,
    dragStartX: 0,
    dragStartY: 0,
    dragMoved: false,
    hoveredId: null,
    focusedId: null,
    potentialClickId: null,
    projectedNodes: {{}},
    nodeAlphas: {{}},
    searchText: '',
    legendFilterType: null,
    legendFilterRank: null,
    legendHoverType: null,
    legendHoverRank: null,
    legendEl: null,
    showTitles: false,
    redPillActive: false,
    namedMap,
    titleMap,
    tooltipEl: null,
    searchInputEl: null,
    redPillEl: null,
    labelToggleEl: null,
  }};
  function drawNode(sx, sy, r, color, alpha) {{
    const grad = ctx.createRadialGradient(sx, sy, 0, sx, sy, r * 3.9);
    grad.addColorStop(0, `rgba(${{color.rgb}},${{Math.min(alpha * 0.68, 1).toFixed(2)}})`);
    grad.addColorStop(0.42, `rgba(${{color.rgb}},${{Math.min(alpha * 0.24, 1).toFixed(2)}})`);
    grad.addColorStop(1, `rgba(${{color.rgb}},0)`);
    ctx.beginPath(); ctx.arc(sx, sy, r * 3.9, 0, Math.PI * 2); ctx.fillStyle = grad; ctx.fill();
    ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2); ctx.fillStyle = `rgba(${{color.rgb}},${{Math.min(alpha * 1.18, 1).toFixed(2)}})`; ctx.fill();
    ctx.beginPath(); ctx.arc(sx - r * 0.28, sy - r * 0.28, r * 0.32, 0, Math.PI * 2); ctx.fillStyle = `rgba(255,255,255,${{(alpha * 0.65).toFixed(2)}})`; ctx.fill();
  }}
  function drawNodeNamed(sx, sy, r, alpha) {{
    const glow = ctx.createRadialGradient(sx, sy, 0, sx, sy, r * 4.2);
    glow.addColorStop(0,   `rgba(239,68,68,${{Math.min(alpha * 0.7, 1).toFixed(2)}})`);
    glow.addColorStop(0.4, `rgba(239,68,68,${{Math.min(alpha * 0.25, 1).toFixed(2)}})`);
    glow.addColorStop(1,   'rgba(239,68,68,0)');
    ctx.beginPath(); ctx.arc(sx, sy, r * 4.2, 0, Math.PI * 2); ctx.fillStyle = glow; ctx.fill();
    ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(239,68,68,${{Math.min(alpha * 1.2, 1).toFixed(2)}})`; ctx.fill();
    ctx.beginPath(); ctx.arc(sx - r * 0.28, sy - r * 0.28, r * 0.32, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255,255,255,${{(alpha * 0.65).toFixed(2)}})`; ctx.fill();
  }}
  function drawNodeVI(sx, sy, r, alpha, t, p) {{
    const hue = (t * 45) % 360;
    const glowPulse = 0.7 + 0.3 * Math.sin(t * 1.8 + (p.phase || 0));
    const glowR = r * (4.8 + glowPulse);
    const glow = ctx.createRadialGradient(sx, sy, r * 0.5, sx, sy, glowR);
    glow.addColorStop(0,    `hsla(${{hue}},100%,72%,${{(alpha * 0.55).toFixed(2)}})`);
    glow.addColorStop(0.35, `hsla(${{(hue + 90) % 360}},100%,65%,${{(alpha * 0.32).toFixed(2)}})`);
    glow.addColorStop(0.65, `hsla(45,100%,58%,${{(alpha * 0.18).toFixed(2)}})`);
    glow.addColorStop(1,    'hsla(45,100%,50%,0)');
    ctx.beginPath(); ctx.arc(sx, sy, glowR, 0, Math.PI * 2); ctx.fillStyle = glow; ctx.fill();
    const coreGrad = ctx.createRadialGradient(sx - r * 0.25, sy - r * 0.25, 0, sx, sy, r * 1.05);
    coreGrad.addColorStop(0,    `hsla(${{(hue + 200) % 360}},100%,88%,${{Math.min(alpha * 1.1, 1).toFixed(2)}})`);
    coreGrad.addColorStop(0.45, `hsla(${{hue}},100%,68%,${{Math.min(alpha * 1.1, 1).toFixed(2)}})`);
    coreGrad.addColorStop(0.8,  `hsla(${{(hue + 60) % 360}},90%,55%,${{alpha.toFixed(2)}})`);
    coreGrad.addColorStop(1,    `hsla(45,100%,45%,${{alpha.toFixed(2)}})`);
    ctx.beginPath(); ctx.arc(sx, sy, r, 0, Math.PI * 2); ctx.fillStyle = coreGrad; ctx.fill();
    for (let i = 0; i < 6; i++) {{
      const angle = (Math.PI * 2 * i / 6) + t * 0.4;
      const dist = r * (1.65 + 0.35 * Math.sin(t * 2.1 + i));
      const sAlpha = alpha * (0.5 + 0.5 * Math.sin(t * 3.0 + i * 1.05));
      ctx.beginPath();
      ctx.arc(sx + Math.cos(angle) * dist, sy + Math.sin(angle) * dist, r * 0.2, 0, Math.PI * 2);
      ctx.fillStyle = `hsla(${{(hue + i * 60) % 360}},100%,82%,${{sAlpha.toFixed(2)}})`; ctx.fill();
    }}
    ctx.beginPath(); ctx.arc(sx - r * 0.28, sy - r * 0.28, r * 0.32, 0, Math.PI * 2);
    ctx.fillStyle = `rgba(255,255,255,${{(alpha * 0.85).toFixed(2)}})`; ctx.fill();
  }}

  function shouldLabel(skill) {{
    if (state.redPillActive && state.namedMap[skill.id]) return true;
    if (state.showTitles) return true;
    return skill.type === 'ultimate';
  }}

  function getNeighborSet(nodeId) {{
    const set = new Set([nodeId]);
    const skill = state.skills.find(s => s.id === nodeId);
    if (skill) {{
      skill.prerequisites.forEach(pid => set.add(pid));
      state.skills.forEach(s => {{
        if (s.prerequisites.includes(nodeId)) set.add(s.id);
      }});
    }}
    return set;
  }}

  function fitBoundingBoxForFocusedNode() {{
    if (!state.focusedId) return;
    const ids = Array.from(getNeighborSet(state.focusedId));
    const points = ids.map(id => state.positions[id]).filter(Boolean);
    if (!points.length) return;

    let minX = Infinity, maxX = -Infinity, minY = Infinity, maxY = -Infinity;
    points.forEach(p => {{
      minX = Math.min(minX, p.x); maxX = Math.max(maxX, p.x);
      minY = Math.min(minY, p.y); maxY = Math.max(maxY, p.y);
    }});

    const minSize = 80;
    const contentW = Math.max(maxX - minX, minSize);
    const contentH = Math.max(maxY - minY, minSize);
    const targetZoom = Math.max(0.3, Math.min(3.0, Math.min(
      state.width * 0.88 / contentW,
      state.height * 0.88 / contentH
    )));
    state.zoom = targetZoom;
    state.panX = -((minX + maxX) / 2) * targetZoom;
    state.panY = -((minY + maxY) / 2) * targetZoom;
  }}

  function resize() {{
    const dpr = Math.min(window.devicePixelRatio || 1, 2);
    state.width = canvas.parentElement.clientWidth;
    state.height = canvas.parentElement.clientHeight;
    canvas.width = Math.floor(state.width * dpr);
    canvas.height = Math.floor(state.height * dpr);
    canvas.style.width = state.width + 'px';
    canvas.style.height = state.height + 'px';
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    // Static 2D stars scattered around the canvas background
    state.stars = Array.from({{ length: 260 }}, (_, i) => {{
      const seed = i * 7919 + 97;
      const angle = (seed % 6283) / 1000;
      const r = 200 + (seed % 380);
      return {{
        x: Math.cos(angle) * r,
        y: Math.sin(angle) * r,
        size: 0.4 + (seed % 13) / 10,
        alpha: 0.22 + (seed % 55) / 100,
      }};
    }});
  }}

  function draw() {{
    state.t += 0.006;
    ctx.clearRect(0, 0, state.width, state.height);
    state.projectedNodes = {{}};

    const highlightRoot = state.focusedId !== null ? state.focusedId : state.hoveredId;
    const isHighlighting = Boolean(highlightRoot);
    const neighborSet = highlightRoot ? getNeighborSet(highlightRoot) : new Set();
    const isSearchActive = Boolean(state.searchText);
    const searchQuery = isSearchActive ? state.searchText.toLowerCase() : '';
    const legendHovering = Boolean(state.legendHoverType || state.legendHoverRank);
    const legendFiltering = Boolean(state.legendFilterType || state.legendFilterRank);
    const hasUserCtx = ownedIds.size > 0;

    state.skills.forEach(skill => {{
      let targetVis;
      if (isHighlighting) {{
        targetVis = skill.id === highlightRoot ? 1.0 : neighborSet.has(skill.id) ? 0.88 : 0.12;
      }} else if (legendHovering) {{
        const mt = !state.legendHoverType || skill.type === state.legendHoverType;
        const mr = !state.legendHoverRank || skill.level === state.legendHoverRank;
        targetVis = (mt && mr) ? 1.0 : 0.12;
      }} else if (legendFiltering) {{
        const mt = !state.legendFilterType || skill.type === state.legendFilterType;
        const mr = !state.legendFilterRank || skill.level === state.legendFilterRank;
        const matchesLegend = mt && mr;
        if (isSearchActive) {{
          const matchesSearch = (skill.name || skill.id).toLowerCase().includes(searchQuery);
          targetVis = (matchesLegend && matchesSearch) ? 1.0 : 0.12;
        }} else {{
          targetVis = matchesLegend ? 1.0 : 0.12;
        }}
      }} else if (isSearchActive) {{
        targetVis = (skill.name || skill.id).toLowerCase().includes(searchQuery) ? 1.0 : 0.12;
      }} else if (hasUserCtx) {{
        // When user context present: dim unowned nodes to 35%, owned stay full
        targetVis = ownedIds.has(skill.id) ? 1.0 : 0.35;
      }} else {{
        targetVis = 1.0;
      }}
      if (state.redPillActive && !state.namedMap[skill.id]) targetVis = Math.min(targetVis, 0.07);
      if (state.nodeAlphas[skill.id] === undefined) state.nodeAlphas[skill.id] = targetVis;
      state.nodeAlphas[skill.id] += (targetVis - state.nodeAlphas[skill.id]) * 0.15;
    }});

    // Draw background stars (2D, static)
    state.stars.forEach(star => {{
      const pr = project(star);
      ctx.beginPath();
      ctx.arc(pr.sx, pr.sy, star.size * 1.55, 0, Math.PI * 2);
      ctx.fillStyle = `rgba(255,255,255,${{star.alpha.toFixed(2)}})`; ctx.fill();
    }});

    // Draw edges
    state.skills.forEach(skill => {{
      const p0 = state.positions[skill.id]; if (!p0) return;
      skill.prerequisites.forEach(pid => {{
        const pp = state.positions[pid]; if (!pp) return;
        const pa = project(p0), pb = project(pp);
        const col = PALETTE[skill.type] || PALETTE.basic;
        const isNeighborEdge = isHighlighting && neighborSet.has(skill.id) && neighborSet.has(pid);
        const fromVis = state.nodeAlphas[skill.id] ?? 1.0;
        const toVis   = state.nodeAlphas[pid]       ?? 1.0;
        const edgeVis = (fromVis + toVis) / 2;
        const baseEdgeAlpha = isNeighborEdge ? 0.72 : 0.31;
        ctx.beginPath(); ctx.moveTo(pa.sx, pa.sy); ctx.lineTo(pb.sx, pb.sy);
        ctx.strokeStyle = `rgba(${{col.rgb}},${{(baseEdgeAlpha * edgeVis).toFixed(2)}})`;
        ctx.lineWidth = isNeighborEdge ? (skill.type === 'ultimate' ? 2.2 : 1.4) : (skill.type === 'ultimate' ? 1.55 : 0.92);
        ctx.stroke();
      }});
    }});

    // Draw nodes
    state.skills.forEach(skill => {{
      const p = state.positions[skill.id]; if (!p) return;
      const pr = project(p);
      state.projectedNodes[skill.id] = pr;
      const pulse = 0.84 + 0.16 * Math.sin(state.t * 2.2 + p.phase);
      const col = PALETTE[skill.type] || PALETTE.basic;
      const baseR = skill.type === 'ultimate' ? 12.5 : skill.type === 'extra' ? 6.9 : skill.type === 'unique' ? 10 : 3.5;
      const vis = state.nodeAlphas[skill.id] ?? 1.0;
      const owned = hasUserCtx && ownedIds.has(skill.id);
      if (skill.level === '6★') {{
        drawNodeVI(pr.sx, pr.sy, baseR * pr.scale * pulse, vis, state.t, p);
      }} else if (state.redPillActive && state.namedMap[skill.id]) {{
        drawNodeNamed(pr.sx, pr.sy, baseR * pr.scale * pulse, vis);
      }} else if (owned) {{
        // Owned node: full saturation + soft glow
        ctx.save();
        ctx.shadowBlur = 12;
        ctx.shadowColor = col.hex;
        drawNode(pr.sx, pr.sy, baseR * pr.scale * pulse, col, vis);
        ctx.restore();
      }} else {{
        drawNode(pr.sx, pr.sy, baseR * pr.scale * pulse, col, vis);
      }}
    }});

    if (state.focusedId) {{
      const skill = state.skills.find(s => s.id === state.focusedId);
      const pr = state.projectedNodes[state.focusedId];
      if (skill && pr) {{
        const p0 = state.positions[skill.id];
        const pulse = 0.84 + 0.16 * Math.sin(state.t * 2.2 + (p0 ? p0.phase : 0));
        const baseR = skill.type === 'ultimate' ? 12.5 : skill.type === 'extra' ? 6.9 : skill.type === 'unique' ? 10 : 3.5;
        const r = baseR * pr.scale * pulse + 5;
        ctx.beginPath();
        ctx.arc(pr.sx, pr.sy, r, 0, Math.PI * 2);
        ctx.strokeStyle = '#fff';
        ctx.lineWidth = 2.5;
        ctx.stroke();
      }}
    }}

    const labelNodes = state.skills.filter(skill => shouldLabel(skill));
    function drawLabel(skill, highlighted) {{
      const p = state.positions[skill.id]; if (!p) return;
      const pr = project(p);
      const vis = state.nodeAlphas[skill.id] ?? 1.0;
      const labelAlpha = highlighted ? 1.0 : Math.max(0.22, vis) * 0.9;
      if (labelAlpha < 0.04) return;
      // Label color: user's named_map > red-pill namedMap > palette
      const userNamed = userNamedMap[skill.id];
      const col = userNamed
        ? {{ rgb:'56,189,248' }}
        : (state.redPillActive && state.namedMap[skill.id])
          ? {{ rgb:'239,68,68' }}
          : (PALETTE[skill.type] || PALETTE.basic);
      const size = skill.type === 'ultimate' ? 13 : skill.type === 'extra' ? 10 : 8;
      ctx.font = `bold ${{Math.max(6, Math.round(size * pr.scale * 1.16))}}px Inter,system-ui,sans-serif`;
      ctx.fillStyle = `rgba(${{col.rgb}},${{labelAlpha.toFixed(2)}})`; ctx.textAlign = 'center';
      // Label text priority: user's named_map (strip contributor prefix) > red-pill namedMap > showTitles > skill id
      let labelText;
      if (userNamed) {{
        // Strip "contributor/" prefix for own skills
        labelText = userNamed.includes('/') ? userNamed.split('/').slice(1).join('/') : userNamed;
      }} else if (state.redPillActive && state.namedMap && state.namedMap[skill.id]) {{
        labelText = state.namedMap[skill.id];
      }} else if (state.showTitles) {{
        labelText = (state.titleMap && state.titleMap[skill.id]) || skill.name;
      }} else {{
        labelText = '/' + skill.id;
      }}
      ctx.fillText(labelText, pr.sx, pr.sy + 18 * pr.scale);
    }}
    labelNodes.forEach(skill => {{
      const vis = state.nodeAlphas[skill.id] ?? 1.0;
      if (vis <= 0.95) drawLabel(skill, false);
    }});
    labelNodes.forEach(skill => {{
      const vis = state.nodeAlphas[skill.id] ?? 1.0;
      if (vis > 0.95) drawLabel(skill, true);
    }});

    if (state.tooltipEl) {{
      const pr = state.projectedNodes[state.hoveredId];
      if (state.hoveredId && pr) {{
        if (state.hoveredId !== state.lastHoveredId) {{
          const skill = state.skills.find(s => s.id === state.hoveredId);
          const col = PALETTE[skill.type] || PALETTE.basic;
          const typeClass = `skill-tooltip-type-${{skill.type}}`;
          const rm = skill.level ? RANK_META[skill.level] : null;
          const rankPill = rm
            ? `<span style="display:inline-block;padding:.12rem .42rem;border-radius:999px;font-size:.62rem;font-weight:700;background:${{rm.bg}};color:${{rm.hex}}">${{skill.level}}</span>`
            : '';
          state.tooltipEl.innerHTML =
            `<div class="skill-tooltip-name" style="color:rgba(${{col.rgb}},1)">${{skill.name}}</div>` +
            `<div style="color:#64748b;font-size:.68rem;font-weight:500;margin-bottom:.3rem;font-family:monospace">${{skill.id}}</div>` +
            `<div class="skill-tooltip-row"><span class="skill-tooltip-badge ${{typeClass}}">${{skill.type.toUpperCase()}}</span>${{rankPill}}</div>` +
            `<div style="color:#94a3b8;font-size:.72rem;margin-top:.18rem;line-height:1.35">${{skill.description || ''}}</div>`;
          state.lastHoveredId = state.hoveredId;
        }}
        let tx = pr.sx + 18, ty = pr.sy - 34;
        tx = Math.min(tx, state.width - 240); ty = Math.max(ty, 8);
        state.tooltipEl.style.left = tx + 'px';
        state.tooltipEl.style.top  = ty + 'px';
        state.tooltipEl.style.display = 'block';
      }} else {{
        state.tooltipEl.style.display = 'none';
        state.lastHoveredId = null;
      }}
    }}

    state.frame = requestAnimationFrame(draw);
  }}

  function initDOM() {{
    const tip = document.createElement('div');
    tip.className = 'skill-tooltip';
    canvas.parentElement.appendChild(tip);
    state.tooltipEl = tip;

    const searchWrap = document.createElement('div');
    searchWrap.className = 'graph-search-wrap';
    const searchInput = document.createElement('input');
    searchInput.type = 'text';
    searchInput.className = 'graph-search';
    searchInput.placeholder = 'Search skills…';
    searchInput.setAttribute('aria-label', 'Filter skill graph');
    searchInput.addEventListener('input', () => {{ state.searchText = searchInput.value.trim(); }});
    searchInput.addEventListener('mousedown', e => e.stopPropagation());
    searchWrap.appendChild(searchInput);
    canvas.parentElement.appendChild(searchWrap);
    state.searchInputEl = searchInput;

    const legend = document.createElement('div');
    legend.className = 'graph-legend';
    legend.innerHTML =
      '<div class="graph-legend-section"><div class="graph-legend-heading">Type</div>' +
      '<div class="graph-legend-item" data-legend-type="basic"><span class="graph-legend-swatch" style="background:#38bdf8;width:7px;height:7px"></span>Basic</div>' +
      '<div class="graph-legend-item" data-legend-type="extra"><span class="graph-legend-swatch" style="background:#c084fc;width:10px;height:10px"></span>Extra</div>' +
      '<div class="graph-legend-item" data-legend-type="ultimate"><span class="graph-legend-swatch" style="background:#f59e0b;width:14px;height:14px"></span>Ultimate</div>' +
      '</div><div class="graph-legend-section"><div class="graph-legend-heading">Rank</div>' +
      '<div class="graph-legend-ranks">' +
      '<span class="graph-legend-rank-pill" data-legend-rank="1★"  style="background:rgba(56,189,248,.12);color:#38bdf8">1★</span>' +
      '<span class="graph-legend-rank-pill" data-legend-rank="2★" style="background:rgba(99,202,183,.12);color:#63cab7">2★</span>' +
      '<span class="graph-legend-rank-pill" data-legend-rank="3★"style="background:rgba(167,139,250,.12);color:#a78bfa">3★</span>' +
      '<span class="graph-legend-rank-pill" data-legend-rank="4★" style="background:rgba(232,121,249,.12);color:#e879f9">4★</span>' +
      '<span class="graph-legend-rank-pill" data-legend-rank="5★"  style="background:rgba(251,191,36,.12);color:#fbbf24">5★</span>' +
      '<span class="graph-legend-rank-pill" data-legend-rank="6★" style="background:rgba(251,191,36,.20);color:#fbbf24">6★</span>' +
      '</div></div>';
    legend.addEventListener('mousedown', e => e.stopPropagation());
    legend.querySelectorAll('.graph-legend-item[data-legend-type]').forEach(item => {{
      item.addEventListener('mouseenter', () => {{ state.legendHoverType = item.dataset.legendType; }});
      item.addEventListener('mouseleave', () => {{ state.legendHoverType = null; }});
      item.addEventListener('click', () => {{
        const val = state.legendFilterType === item.dataset.legendType ? null : item.dataset.legendType;
        state.legendFilterType = val;
        legend.querySelectorAll('[data-legend-type]').forEach(el => el.classList.remove('active'));
        if (val) item.classList.add('active');
      }});
    }});
    legend.querySelectorAll('.graph-legend-rank-pill').forEach(pill => {{
      pill.addEventListener('mouseenter', () => {{ state.legendHoverRank = pill.dataset.legendRank; }});
      pill.addEventListener('mouseleave', () => {{ state.legendHoverRank = null; }});
      pill.addEventListener('click', () => {{
        const val = state.legendFilterRank === pill.dataset.legendRank ? null : pill.dataset.legendRank;
        state.legendFilterRank = val;
        legend.querySelectorAll('.graph-legend-rank-pill').forEach(el => el.classList.remove('active'));
        if (val) pill.classList.add('active');
      }});
    }});
    canvas.parentElement.appendChild(legend);
    state.legendEl = legend;

    const redPill = document.createElement('button');
    redPill.type = 'button';
    redPill.className = 'graph-redpill';
    redPill.textContent = 'Named Skills';
    redPill.title = 'Highlight Named skills (2★+) with contributor attribution and red glow';
    redPill.addEventListener('mousedown', e => e.stopPropagation());
    redPill.addEventListener('click', () => {{
      state.redPillActive = !state.redPillActive;
      redPill.classList.toggle('active', state.redPillActive);
    }});
    canvas.parentElement.appendChild(redPill);
    state.redPillEl = redPill;

    const labelToggle = document.createElement('button');
    labelToggle.type = 'button';
    labelToggle.className = 'graph-label-toggle';
    labelToggle.textContent = 'Show Title';
    labelToggle.addEventListener('mousedown', e => e.stopPropagation());
    labelToggle.addEventListener('click', () => {{
      state.showTitles = !state.showTitles;
      labelToggle.classList.toggle('active', state.showTitles);
    }});
    canvas.parentElement.appendChild(labelToggle);
    state.labelToggleEl = labelToggle;
  }}

  function resetFilters() {{
    state.legendFilterType = null;
    state.legendFilterRank = null;
    state.legendHoverType = null;
    state.legendHoverRank = null;
    state.showTitles = false;
    state.searchText = '';
    state.redPillActive = false;
    if (state.redPillEl) state.redPillEl.classList.remove('active');
    if (state.legendEl) {{
      state.legendEl.querySelectorAll('.active').forEach(el => el.classList.remove('active'));
    }}
    if (state.searchInputEl) state.searchInputEl.value = '';
    if (state.labelToggleEl) state.labelToggleEl.classList.remove('active');
  }}

  // Performance optimization: Cache canvas bounds to prevent layout thrashing
  // on high-frequency mousemove events. Invalidate on scroll/resize/mousedown.
  let _lastRect = null;
  window.addEventListener('resize', () => {{ _lastRect = null; }});
  window.addEventListener('scroll', () => {{ _lastRect = null; }}, {{ passive: true }});

  function handlePointerMove(event) {{
    if (!_lastRect) _lastRect = canvas.getBoundingClientRect();
    const rect = _lastRect;
    if (state.dragging) {{
      // 2D pan: translate the canvas view
      state.panX += (event.clientX - state.dragLastX);
      state.panY += (event.clientY - state.dragLastY);
      state.dragLastX = event.clientX;
      state.dragLastY = event.clientY;
      if (Math.hypot(event.clientX - state.dragStartX, event.clientY - state.dragStartY) > 5) state.dragMoved = true;
      state.hoveredId = null;
      return;
    }}

    const mxScreen = event.clientX - rect.left;
    const myScreen = event.clientY - rect.top;
    let closest = null, closestDist = 22;
    Object.entries(state.projectedNodes).forEach(([id, pr]) => {{
      const d = Math.hypot(pr.sx - mxScreen, pr.sy - myScreen);
      if (d < closestDist) {{ closestDist = d; closest = id; }}
    }});
    state.hoveredId = closest;
    canvas.style.cursor = closest ? 'pointer' : 'default';
  }}

  function handleMouseDown(event) {{
    event.preventDefault();
    _lastRect = canvas.getBoundingClientRect();
    state.potentialClickId = state.hoveredId;
    state.dragging = true;
    state.dragMoved = false;
    state.dragStartX = event.clientX;
    state.dragStartY = event.clientY;
    state.dragLastX = event.clientX;
    state.dragLastY = event.clientY;
    canvas.style.cursor = 'grabbing';
    state.hoveredId = null;
  }}

  function handleMouseUp() {{
    if (!state.dragging) return;
    const wasDrag = state.dragMoved;
    state.dragging = false;
    state.dragMoved = false;
    if (!wasDrag) {{
      if (state.potentialClickId) {{
        state.focusedId = state.potentialClickId;
        fitBoundingBoxForFocusedNode();
      }} else {{
        state.focusedId = null;
        state.panX = 0;
        state.panY = 0;
      }}
    }}
    state.potentialClickId = null;
    canvas.style.cursor = state.hoveredId ? 'pointer' : 'default';
  }}

  function handleWheel(event) {{
    event.preventDefault();
    state.zoom = Math.max(0.3, Math.min(3.0, state.zoom * (1 - event.deltaY * 0.001)));
  }}

  resize();
  initDOM();
  meta.textContent = `${{skills.length}} skills, ${{skills.reduce((sum, s) => sum + s.prerequisites.length, 0)}} prerequisites, version ${{graph.version || 'unknown'}}`;
  resetView.addEventListener('click', resetFilters);
  canvas.addEventListener('mousemove', handlePointerMove);
  canvas.addEventListener('mousedown', handleMouseDown);
  window.addEventListener('mouseup', handleMouseUp);
  canvas.addEventListener('wheel', handleWheel, {{ passive: false }});
  window.addEventListener('resize', resize);
  draw();
}})();
</script>
</body>
</html>"""


def write_graph_artifact(
    registry_path: str | os.PathLike[str] = ".",
    output: str | os.PathLike[str] | None = None,
    fmt: str = "html",
    *,
    user_ctx: dict[str, Any] | None = None,
    custom: bool = False,
) -> Path:
    root = _registry_root(registry_path)
    graph = load_graph(root)
    if custom:
        custom_state_path = Path.cwd() / ".gaia" / "custom_state.json"
        custom_skills = []
        if custom_state_path.exists():
            try:
                with open(custom_state_path, "r", encoding="utf-8") as f:
                    custom_state = json.load(f)
                    custom_skills = custom_state.get("customSkills", [])
            except Exception:
                pass
        else:
            from gaia_cli.scanner import scan_skill_mds
            local_skills = scan_skill_mds(global_search=False)
            custom_skills = [{
                "id": sk["id"],
                "name": sk.get("name", sk["id"]),
                "description": sk.get("description", ""),
                "mapped_to": sk["id"],
                "prerequisites": sk.get("prerequisites", [])
            } for sk in local_skills]
        
        canon_skills = {sk["id"]: sk for sk in graph.get("skills", [])}
        scanned_nodes = set()
        if user_ctx:
            scanned_nodes.update(user_ctx.get("owned_ids", []))

        for csk in custom_skills:
            cid = csk["id"]
            mapped_to = csk.get("mapped_to")
            
            node_id = mapped_to if mapped_to else cid
            scanned_nodes.add(node_id)
            
            if mapped_to and mapped_to in canon_skills and mapped_to != cid:
                target = canon_skills[mapped_to]
                # Merge prereqs, avoiding duplicates
                merged_prereqs = list(set(target.get("prerequisites", []) + csk.get("prerequisites", [])))
                target["name"] = csk["name"]
                target["description"] = csk["description"]
                target["prerequisites"] = merged_prereqs
            elif cid in canon_skills:
                canon_skills[cid]["name"] = csk["name"]
                canon_skills[cid]["description"] = csk["description"]
                canon_skills[cid]["prerequisites"] = list(set(canon_skills[cid].get("prerequisites", []) + csk.get("prerequisites", [])))
            else:
                canon_skills[cid] = {
                    "id": cid,
                    "name": csk["name"],
                    "description": csk["description"],
                    "type": "basic",
                    "level": "0★",
                    "prerequisites": csk.get("prerequisites", []),
                }
        
        display_ids = set()
        queue = list(scanned_nodes)
        visited = set()
        while queue:
            curr = queue.pop(0)
            if curr in visited:
                continue
            visited.add(curr)
            display_ids.add(curr)
            for prereq in canon_skills.get(curr, {}).get("prerequisites", []):
                queue.append(prereq)

        graph["skills"] = [sk for sk in canon_skills.values() if sk["id"] in display_ids]
        graph["version"] = "local-custom"
    named_buckets = load_named_skills(root).get("buckets", {})
    render_graph = build_render_graph(graph, named_buckets=named_buckets)
    fmt = fmt.lower()
    if output is None:
        if custom:
            local_dir = Path(".gaia")
            if fmt == "html":
                output = local_dir / "render" / "gaia.html"
            elif fmt == "svg":
                output = local_dir / "gaia.svg"
            else:
                output = local_dir / "render" / "latest.json"
        else:
            from gaia_cli.registry import registry_dir
            reg_dir = Path(registry_dir(root))
            if fmt == "html":
                output = reg_dir / "render" / "gaia.html"
            elif fmt == "svg":
                output = reg_dir / "gaia.svg"
            else:
                output = reg_dir / "render" / "latest.json"
    out_path = Path(output)
    if not out_path.is_absolute():
        if custom:
            out_path = Path.cwd() / out_path
        else:
            out_path = root / out_path
    out_path.parent.mkdir(parents=True, exist_ok=True)

    if fmt == "html":
        out_path.write_text(
            render_html(graph, load_named_skills(root), user_ctx=user_ctx),
            encoding="utf-8",
        )
    elif fmt == "svg":
        out_path.write_text(render_svg(render_graph), encoding="utf-8")
    elif fmt == "json":
        out_path.write_text(json.dumps(render_graph, indent=2) + "\n", encoding="utf-8")
    else:
        raise ValueError(f"Unsupported graph format: {fmt}")
    return out_path


def open_path(path: Path) -> None:
    uri = path.resolve().as_uri()
    try:
        opened = webbrowser.open(uri)
    except Exception:
        opened = False
    if opened:
        return
    if sys.platform == "darwin":
        subprocess.run(["open", str(path.resolve())], check=False)
    elif os.name == "nt":
        os.startfile(str(path.resolve()))  # type: ignore[attr-defined]
    else:
        subprocess.run(["xdg-open", str(path.resolve())], check=False)


def graph_command(args: Any) -> None:
    fmt = getattr(args, "format", "html") or "html"
    output = getattr(args, "output", None)
    registry_path = getattr(args, "registry", ".")

    # Build local user context if a username is configured
    user_ctx: dict[str, Any] | None = None
    try:
        from gaia_cli import scanner
        from gaia_cli.localContext import LocalContext
        from gaia_cli.treeManager import detect_source_repo

        config = scanner.load_config()
        username = (config or {}).get("gaiaUser") or (config or {}).get("username") or ""
        
        repo_title = ""
        try:
            repo_title = detect_source_repo(config) if config else ""
        except Exception:
            pass

        if username or repo_title:
            ctx = LocalContext.load(str(registry_path), username or "unknown", include_scan=False)
            user_ctx = {
                "username": ctx.username,
                "owned_ids": list(ctx.owned_ids),
                "named_map": ctx.named_map,
                "title": repo_title or username,
            }
    except Exception:
        pass  # Degrade gracefully to canon mode

    try:
        canon = getattr(args, "canon", False)
        custom = getattr(args, "custom", False) or (not canon)
        out_path = write_graph_artifact(registry_path, output=output, fmt=fmt, user_ctx=user_ctx, custom=custom)
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return
    print(f"  saved {out_path}")

    # Regenerate the GEXF from current node data
    if fmt == "html":
        try:
            if custom:
                write_gexf(registry_path, output=Path.cwd() / ".gaia" / "gaia.gexf")
            else:
                write_gexf(registry_path)
        except Exception:
            pass  # GEXF regen is best-effort

    if getattr(args, "open", True):
        open_path(out_path)
