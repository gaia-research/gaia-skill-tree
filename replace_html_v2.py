import json
from html import escape

def _html_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False).replace("</script>", "<\\/script>")

with open("src/gaia_cli/graph.py", "r") as f:
    content = f.read()

start_marker = "def render_html("
end_marker = "</html>'''"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx) + len(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Could not find render_html bounds (start: {start_idx}, end: {end_idx})")
    exit(1)

new_render_html = """def render_html(
    graph: dict[str, Any],
    named_skills: dict[str, Any] | None = None,
    *,
    user_ctx: dict[str, Any] | None = None,
) -> str:
    named_skills = named_skills or {"buckets": {}}
    user_ctx_data: dict[str, Any] = user_ctx if user_ctx is not None else {}
    _title_text = user_ctx_data.get("title", "") if user_ctx_data else ""
    _username = user_ctx_data.get("username", "unknown")
    _title_text = _title_text or _username
    _display_title = f"{_title_text} - Gaia Skill Graph" if _title_text else "Gaia Skill Graph"

    # Make sure we add 'meta' object so skill-graph.js doesn't crash if missing
    if "meta" not in graph:
        graph["meta"] = {"levelColors": {}, "levelLabels": {}}

    return f'''<!DOCTYPE html>
<html lang="en" data-graph-mode="local" data-graph-handle="{_username}">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_display_title}</title>
  <script>window.GAIA_VERSION = "4.3.12";</script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="https://mbtiongson.github.io/gaia-skill-tree/css/styles.css">
  <link rel="stylesheet" href="https://mbtiongson.github.io/gaia-skill-tree/css/plaque.css">
  <style>
    body {{ margin: 0; overflow: hidden; background: #020617; }}
    #hero {{ height: 100vh; width: 100vw; position: relative; }}
    canvas {{ display: block; width: 100%; height: 100%; outline: none; }}
    [data-graph-trigger] {{ display: none; }}
  </style>
</head>
<body class="home-page">
  <section id="hero">
    <canvas id="canvas3d"></canvas>
    <div class="hero-glass-blur"></div>
    <div class="hero-content"></div>
    <button type="button" data-graph-trigger id="graphTrigger"></button>
  </section>

  <script type="application/json" id="gaia-graph-data">{_html_json(graph)}</script>
  <script type="application/json" id="gaia-named-skills">{_html_json(named_skills)}</script>
  <script type="application/json" id="gaia-user-ctx">{_html_json(user_ctx_data)}</script>

  <script>
    window.document.title = "{_display_title}";
    
    // Mock fetch
    const originalFetch = window.fetch;
    window.fetch = async function(resource, options) {{
      const url = typeof resource === 'string' ? resource : resource.url;
      if (url.includes('graph/ping.json')) {{
        return new Response(JSON.stringify({{ ok: true }}), {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }});
      }}
      if (url.includes('graph/gaia.json')) {{
        const data = document.getElementById('gaia-graph-data').textContent;
        return new Response(data, {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }});
      }}
      if (url.includes('named/index.json')) {{
        const data = document.getElementById('gaia-named-skills').textContent;
        return new Response(data, {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }});
      }}
      return originalFetch(resource, options);
    }};
  </script>

  <script src="https://mbtiongson.github.io/gaia-skill-tree/js/icons.js"></script>
  <script src="https://mbtiongson.github.io/gaia-skill-tree/js/skill-graph.js"></script>
  <script>
    // Activate interactive mode
    setTimeout(() => {{
      const trigger = document.getElementById('graphTrigger');
      if (trigger) trigger.click();
    }}, 500);
  </script>
</body>
</html>'''"""

with open("src/gaia_cli/graph.py", "w") as f:
    f.write(content[:start_idx] + new_render_html + content[end_idx:])
