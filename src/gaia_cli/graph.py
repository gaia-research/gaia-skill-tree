"""Graph rendering helpers for the Gaia CLI.

The registry source of truth is registry/gaia.json. This module deliberately uses
only the Python standard library so graph viewing remains available in a fresh
clone without Graphviz, Matplotlib, or a browser automation dependency.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import webbrowser
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from typing import Any

from gaia_cli.registry import named_skills_index_path, registry_graph_path, registry_nodes_dir


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


def resolve_enriched_graph_path(root: Path, custom: str | os.PathLike[str] | None = None) -> Path | None:
    """Locate the enriched 3D World Tree graph, if one is available locally.

    The lean registry/gaia.json lacks the branch/namedMaxLevel/cluster/rank
    fields the site's 3D renderer needs for a non-degraded view. Those are baked
    into docs/graph/gaia.json at release time. This picks the enriched copy when
    present, in priority order:

      (a) an explicit path passed by the caller,
      (b) .gaia/registry/graph/gaia.json  (written by `gaia fetch`),
      (c) <root>/docs/graph/gaia.json     (a repo checkout).

    Returns the first existing path, or None if no enriched graph is found (the
    caller then falls back to the lean registry/gaia.json).
    """
    if custom is not None:
        p = Path(custom)
        if p.exists():
            return p
    candidates = [
        Path.cwd() / ".gaia" / "registry" / "graph" / "gaia.json",
        root / "docs" / "graph" / "gaia.json",
    ]
    for cand in candidates:
        if cand.exists():
            return cand
    return None


def load_enriched_graph(path: Path) -> dict[str, Any]:
    """Load an enriched graph JSON from `path`."""
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


_ENRICHED_WARNED = False


def _warn_enriched_missing_once() -> None:
    """Print a one-time stderr hint when no enriched 3D graph is found locally."""
    global _ENRICHED_WARNED
    if _ENRICHED_WARNED:
        return
    _ENRICHED_WARNED = True
    print(
        "Note: run 'gaia fetch' for the full 3D skill-tree view "
        "(enriched graph not found locally).",
        file=sys.stderr,
    )


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
    ET.SubElement(meta_el, "description").text = "Gaia Skill Tree Graph"

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

    # Read the version dynamically from the embedded graph rather than hardcoding
    # (decorative surfaces must never carry a stale baked-in version — see #807).
    _graph_version = escape(str(graph.get("version", "")), quote=True)

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
    window.GAIA_VERSION = "{_graph_version}";
    // Point icon base to a path that we will intercept in fetch
    window.gaiaIconBase = function() {{ return 'assets/icons.svg'; }};
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="https://gaiaskilltree.com/css/styles.css">
  <link rel="stylesheet" href="https://gaiaskilltree.com/css/plaque.css">
  <link rel="stylesheet" href="https://gaiaskilltree.com/css/alpha-rail.css">
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
          {f"return new Response({json.dumps(icons_svg)}, {{ status: 200, headers: {{ 'Content-Type': 'image/svg+xml' }} }});" if icons_svg else "return originalFetch('https://gaiaskilltree.com/assets/icons.svg', options);"}
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

  <script src="https://gaiaskilltree.com/js/icons.js"></script>
  <script src="https://gaiaskilltree.com/js/atlas-helpers.js"></script>
  <script src="https://gaiaskilltree.com/js/rank-badge.js"></script>
  <script src="https://gaiaskilltree.com/js/plaque.js"></script>
  <script src="https://gaiaskilltree.com/js/skill-graph.js"></script>
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
    enriched_path = resolve_enriched_graph_path(root)
    if enriched_path is not None:
        graph = load_enriched_graph(enriched_path)
    else:
        graph = load_graph(root)
        # Degrade gracefully: the lean registry/gaia.json renders the 3D tree
        # all-grey/collapsed. Hint the user (once) toward the enriched view.
        _warn_enriched_missing_once()
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
                    # Mark uncanonized local skills so the frontend (PR 3c) can
                    # render them green-starless. Canon skills never carry this.
                    "custom": True,
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

    fmt = fmt.lower()
    if output is None:
        if custom:
            local_dir = Path(".gaia")
            if fmt == "html":
                output = local_dir / "render" / "gaia.html"
            else:
                output = local_dir / "render" / "latest.json"
        else:
            from gaia_cli.registry import registry_dir
            reg_dir = Path(registry_dir(root))
            if fmt == "html":
                output = reg_dir / "render" / "gaia.html"
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
    elif fmt == "json":
        # Emit the same enriched DAG the HTML path embeds (skills[] with
        # type/branch/namedMaxLevel/… + prerequisite edges), NOT an x/y ring
        # render graph — `gaia graph` is a thin data-pump for the 3D World Tree.
        out_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
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
