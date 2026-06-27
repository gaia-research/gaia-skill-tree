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
            sid = (skill.get("id") or "").lstrip("/")
            angle = _stable_angle(sid, i, len(bucket))
            local_radius = radius if len(bucket) > 1 else 0
            x = cx + math.cos(angle) * local_radius
            y = cy + math.sin(angle) * local_radius
            star = named_max.get(skill.get("id")) or named_max.get(sid)
            level_meta = level_summary(skill)
            nodes.append(
                {
                    "id": sid,
                    "label": skill.get("name") or sid,
                    "type": skill_type,
                    # Generic refs are rank-less — prefer the top named-variant
                    # star; fall back to any legacy level for back-compat.
                    "level": star or skill.get("level", ""),
                    "effectiveLevel": star or level_meta["effectiveLevel"],
                    "levelMeta": level_meta,
                    "demerits": level_meta["demerits"],
                    "description": skill.get("description", ""),
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "radius": NODE_RADIUS.get(skill_type, 7),
                }
            )

    skill_ids = {node["id"] for node in nodes}
    edges: list[dict[str, Any]] = []
    for skill in skills:
        target = (skill.get("id") or "").lstrip("/")
        if target not in skill_ids:
            continue
        for source in skill.get("prerequisites", []) or []:
            source = source.lstrip("/")
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
    skills: list[dict[str, Any]] | None = None,
) -> Path:
    """Generate GEXF 1.2 from registry/nodes/ and write to output (default: docs/graph/gaia.gexf).

    Uses only xml.etree.ElementTree from the stdlib — no lxml required.
    """
    root = _registry_root(registry_path)

    if skills is None:
        nodes_dir = registry_nodes_dir(root)
        # Collect skills from nodes directory
        skills = []
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
    # Enrich graph with semantic positions from registry/layouts_3d.json
    layouts_path = root / "registry" / "layouts_3d.json"
    if layouts_path.exists():
        try:
            with open(layouts_path, "r", encoding="utf-8") as f:
                layout_data = json.load(f)
                layout_nodes = layout_data.get("nodes", {})
                if "meta" in layout_data:
                    graph.setdefault("meta", {}).update({
                        "clusterNames": layout_data["meta"].get("clusterNames", {}),
                        "centroids": layout_data["meta"].get("centroids", [])
                    })
                for skill in graph.get("skills", []):
                    sid = skill.get("id")
                    if sid in layout_nodes:
                        skill["cluster"] = layout_nodes[sid].get("cluster")
                        skill["positions"] = layout_nodes[sid].get("positions")
        except Exception:
            pass
    
            skills = graph.get("skills", [])
    
    skills = skills or []
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
    for attr_id in ("level", "status", "type"):
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
        for attr_id in ("level", "status", "type"):
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


def render_svg(render_graph: dict[str, Any], is_workspace_mode: bool = False) -> str:
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
    if is_workspace_mode:
        # Semi-transparent diagonal watermark text overlay
        lines.append(
            f'<text x="{width / 2:.1f}" y="{height / 2:.1f}" fill="#334155" opacity="0.15" '
            f'font-size="64" font-weight="900" font-family="sans-serif" text-anchor="middle" '
            f'transform="rotate(-30 {width / 2:.1f} {height / 2:.1f})">WORKSPACE ONLY</text>'
        )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _html_json(data: dict[str, Any]) -> str:
    return escape(json.dumps(data, indent=2, ensure_ascii=False), quote=False)


def render_html(
    graph: dict[str, Any],
    named_skills: dict[str, Any] | None = None,
    *,
    user_ctx: dict[str, Any] | None = None,
    icons_svg: str | None = None,
    is_workspace_mode: bool = False,
) -> str:
    named_skills = named_skills or {"buckets": {}}
    user_ctx_data: dict[str, Any] = user_ctx if user_ctx is not None else {}
    _title_text = user_ctx_data.get("title", "") if user_ctx_data else ""
    _username = user_ctx_data.get("username", "unknown")
    _title_text = _title_text or _username
    _display_title = f"{_title_text} - Gaia Skill Graph" if _title_text else "Gaia Skill Graph"

    if "meta" not in graph:
        graph["meta"] = {"levelColors": {}, "levelLabels": {}}

    watermark_style = ""
    watermark_html = ""
    if is_workspace_mode:
        watermark_style = """
    .workspace-watermark {
      position: fixed;
      top: 1.5rem;
      right: 1.5rem;
      z-index: 9999;
      background: rgba(15, 23, 42, 0.85);
      backdrop-filter: blur(8px);
      -webkit-backdrop-filter: blur(8px);
      border: 1px solid rgba(245, 158, 11, 0.3);
      padding: 0.5rem 1rem;
      border-radius: 9999px;
      font-size: 0.75rem;
      font-weight: 700;
      letter-spacing: 0.05em;
      text-transform: uppercase;
      color: #f8fafc;
      pointer-events: none;
      box-shadow: 0 4px 20px rgba(0, 0, 0, 0.6);
      display: flex;
      align-items: center;
      gap: 6px;
    }
    .workspace-watermark::before {
      content: "";
      display: inline-block;
      width: 8px;
      height: 8px;
      background: #f59e0b;
      border-radius: 50%;
    }
"""
        watermark_html = '<div class="workspace-watermark">Workspace Mode</div>'

    return f'''<!DOCTYPE html>
<html lang="en" data-graph-mode="local" data-graph-handle="{_username}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_display_title}</title>
  <script>
    window.GAIA_VERSION = "4.3.12";
    // Point icon base to a path that we will intercept in fetch
    window.gaiaIconBase = function() {{ return 'assets/icons.svg'; }};
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="https://gaia.tiongson.co/css/styles.css">
  <link rel="stylesheet" href="https://gaia.tiongson.co/css/plaque.css">
  <link rel="stylesheet" href="https://gaia.tiongson.co/css/alpha-rail.css">
  <style>
    body {{ margin: 0; overflow: hidden; background: #020617; color: #fff; font-family: system-ui, sans-serif; }}
    #hero {{ height: 100vh; width: 100vw; position: relative; z-index: 1; }}
    #hero.hero-graph-fullscreen {{ position: fixed; inset: 0; z-index: 100; }}
    canvas {{ display: block; width: 100%; height: 100%; outline: none; }}
    [data-graph-trigger] {{ display: none; }}
    .graph-search-wrap, .graph-legend, .graph-fullscreen-overlay {{ display: flex !important; }}
    {watermark_style}
  </style>
</head>
<body class="home-page">
  <section id="hero" class="hero-graph-fullscreen">
    <canvas id="canvas3d"></canvas>
    <div class="hero-glass-blur" style="display:none"></div>
    <div class="hero-content" style="display:none"></div>
    <button type="button" data-graph-trigger id="graphTrigger" style="display:none"></button>
  </section>
  {watermark_html}

  <script type="application/json" id="gaia-graph-data">{_html_json(graph)}</script>
  <script type="application/json" id="gaia-named-skills">{_html_json(named_skills)}</script>
  <script type="application/json" id="gaia-user-ctx">{_html_json(user_ctx_data)}</script>

  <script>
    window.document.title = "{_display_title}";
    
    const originalFetch = window.fetch;
    window.fetch = async function(resource, options) {{
      const url = typeof resource === 'string' ? resource : resource.url;
      
      if (url.includes('icons.svg')) {{
          {f"return new Response({json.dumps(icons_svg)}, {{ status: 200, headers: {{ 'Content-Type': 'image/svg+xml' }} }});" if icons_svg else "return originalFetch('https://gaia.tiongson.co/assets/icons.svg', options);"}
      }}
      
      if (url.includes('ping.json') || url.includes('gaia.json') || url.includes('index.json')) {{
          let data = '{{}}';
          if (url.includes('ping.json')) data = '{{ "ok": true }}';
          else if (url.includes('gaia.json')) data = document.getElementById('gaia-graph-data').textContent;
          else if (url.includes('index.json')) data = document.getElementById('gaia-named-skills').textContent;
          
          return new Response(data, {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }});
      }}
      return originalFetch(resource, options);
    }};
  </script>

  <script src="https://gaia.tiongson.co/js/icons.js"></script>
  <script src="https://gaia.tiongson.co/js/atlas-helpers.js"></script>
  <script src="https://gaia.tiongson.co/js/rank-badge.js"></script>
  <script src="https://gaia.tiongson.co/js/plaque.js"></script>
  <script src="https://gaia.tiongson.co/js/skill-graph.js"></script>
  <script>
    window.addEventListener('load', () => {{
      setTimeout(() => {{
        const trigger = document.getElementById('graphTrigger');
        if (trigger) trigger.click();
      }}, 500);
    }});
  </script>
</body>
</html>'''


def write_graph_artifact(
    registry_path: str | os.PathLike[str] = ".",
    output: str | os.PathLike[str] | None = None,
    fmt: str = "html",
    *,
    user_ctx: dict[str, Any] | None = None,
    custom: bool = False,
    known_only: bool = True,
    is_workspace: bool = False,
) -> tuple[Path, dict[str, Any]]:
    root = _registry_root(registry_path)
    graph = load_graph(root)
    named_buckets = load_named_skills(root).get("buckets", {})

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
        scanned_nodes: set[str] = set()
        if user_ctx:
            scanned_nodes.update(user_ctx.get("owned_ids", []))

        # Reverse map: named skill ID -> canonical skill ID
        named_to_canon: dict[str, str] = {}
        for canon_id, entries in named_buckets.items():
            for entry in entries:
                nid = entry.get("id")
                if nid:
                    named_to_canon[nid] = canon_id

        for csk in custom_skills:
            cid = csk["id"]
            mapped_to = csk.get("mapped_to")

            node_id = mapped_to if mapped_to else cid
            # Resolve named skill IDs (e.g. "mbtiongson1/graphify-triage") to their
            # canonical counterpart so prerequisites are inherited from the registry.
            canon_node_id = named_to_canon.get(node_id, node_id)
            scanned_nodes.add(canon_node_id)

            if canon_node_id in canon_skills and canon_node_id != cid:
                target = canon_skills[canon_node_id]
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

        if known_only:
            display_ids = scanned_nodes & set(canon_skills.keys())
        else:
            display_ids = set()
            queue = list(scanned_nodes)
            visited: set[str] = set()
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
        icons_svg: str | None = None
        icons_path = root / "docs" / "assets" / "icons.svg"
        if icons_path.exists():
            try:
                icons_svg = icons_path.read_text(encoding="utf-8")
            except OSError:
                pass
        out_path.write_text(
            render_html(graph, load_named_skills(root), user_ctx=user_ctx, icons_svg=icons_svg, is_workspace_mode=is_workspace),
            encoding="utf-8",
        )
    elif fmt == "svg":
        out_path.write_text(render_svg(render_graph, is_workspace_mode=is_workspace), encoding="utf-8")
    elif fmt == "json":
        out_path.write_text(json.dumps(render_graph, indent=2) + "\n", encoding="utf-8")
    else:
        raise ValueError(f"Unsupported graph format: {fmt}")
    return out_path, graph


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
    is_workspace = False
    try:
        from gaia_cli import scanner
        from gaia_cli.localContext import LocalContext
        from gaia_cli.push import detect_source_repo

        config = scanner.load_config()
        username = (config or {}).get("gaiaUser") or (config or {}).get("username") or ""
        
        if config and config.get("workspaceMode"):
            is_workspace = True

        repo_title = ""
        try:
            repo_title = detect_source_repo(config) if config else ""
        except NonPublicRepoError:
            is_workspace = True
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
        known_only = not getattr(args, "show_all", False)
        out_path, filtered_graph = write_graph_artifact(
            registry_path,
            output=output,
            fmt=fmt,
            user_ctx=user_ctx,
            custom=custom,
            known_only=known_only,
            is_workspace=is_workspace,
        )
    except FileNotFoundError as exc:
        print(str(exc), file=sys.stderr)
        return
    print(f"  saved {out_path}")

    if known_only and custom:
        displayed_ids = {sk["id"] for sk in filtered_graph.get("skills", [])}
        has_hidden = any(
            p not in displayed_ids
            for sk in filtered_graph.get("skills", [])
            for p in sk.get("prerequisites", [])
        )
        if has_hidden:
            print("  tip: use -a / --all to include unowned prerequisites in the graph")

    # Regenerate the GEXF from current node data
    if fmt == "html":
        try:
            if custom:
                write_gexf(registry_path, output=Path.cwd() / ".gaia" / "gaia.gexf", skills=filtered_graph.get("skills"))
            else:
                write_gexf(registry_path, skills=filtered_graph.get("skills"))
        except Exception:
            pass  # GEXF regen is best-effort

    if getattr(args, "open", True):
        open_path(out_path)
