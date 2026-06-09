import json

def _html_json(data):
    return json.dumps(data, indent=2, ensure_ascii=False).replace("</script>", "<\\/script>")

with open("src/gaia_cli/graph.py", "r") as f:
    content = f.read()

start_marker = "def render_html("
end_marker = "</html>'''"

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx) + len(end_marker)

if start_idx == -1 or end_idx == -1:
    print(f"Could not find render_html bounds")
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
  <script>
    window.GAIA_VERSION = "4.3.12";
    // Point to the local icons sprite downloaded by the CLI
    window.gaiaIconBase = function() {{ return 'assets/icons.svg'; }};
  </script>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="css/styles.css">
  <link rel="stylesheet" href="css/plaque.css">
  <link rel="stylesheet" href="css/alpha-rail.css">
  <style>
    body {{ margin: 0; overflow: hidden; background: #020617; color: #fff; font-family: system-ui, sans-serif; }}
    #hero {{ height: 100vh; width: 100vw; position: relative; z-index: 1; }}
    #hero.hero-graph-fullscreen {{ position: fixed; inset: 0; z-index: 100; }}
    canvas {{ display: block; width: 100%; height: 100%; outline: none; }}
    [data-graph-trigger] {{ display: none; }}
    /* Force visibility of HUD elements which might be hidden by default */
    .graph-search-wrap, .graph-legend, .graph-fullscreen-overlay {{ display: flex !important; }}
  </style>
</head>
<body class="home-page">
  <section id="hero" class="hero-graph-fullscreen">
    <canvas id="canvas3d"></canvas>
    <div class="hero-glass-blur" style="display:none"></div>
    <div class="hero-content" style="display:none"></div>
    <button type="button" data-graph-trigger id="graphTrigger" style="display:none"></button>
  </section>

  <script type="application/json" id="gaia-graph-data">{_html_json(graph)}</script>
  <script type="application/json" id="gaia-named-skills">{_html_json(named_skills)}</script>
  <script type="application/json" id="gaia-user-ctx">{_html_json(user_ctx_data)}</script>

  <script>
    window.document.title = "{_display_title}";
    
    // Mock fetch to serve the embedded JSON data
    const originalFetch = window.fetch;
    window.fetch = async function(resource, options) {{
      const url = typeof resource === 'string' ? resource : resource.url;
      console.log('Mock fetch intercepting:', url);
      
      if (url.includes('ping.json')) {{
        return new Response(JSON.stringify({{ ok: true }}), {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }});
      }}
      if (url.includes('gaia.json')) {{
        const data = document.getElementById('gaia-graph-data').textContent;
        return new Response(data, {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }});
      }}
      if (url.includes('named/index.json') || url.includes('index.json')) {{
        const data = document.getElementById('gaia-named-skills').textContent;
        return new Response(data, {{ status: 200, headers: {{ 'Content-Type': 'application/json' }} }});
      }}
      return originalFetch(resource, options);
    }};
  </script>

  <script src="js/icons.js"></script>
  <script src="js/atlas-helpers.js"></script>
  <script src="js/rank-badge.js"></script>
  <script src="js/plaque.js"></script>
  <script src="js/skill-graph.js"></script>
  <script>
    // Force immediate activation of the fullscreen interactive mode
    window.addEventListener('load', () => {{
      setTimeout(() => {{
        const trigger = document.getElementById('graphTrigger');
        if (trigger) {{
            console.log('Activating graph...');
            trigger.click();
        }}
        // Fallback: search for any element with the attribute
        const anyTrigger = document.querySelector('[data-graph-trigger]');
        if (anyTrigger) anyTrigger.click();
      }}, 500);
    }});
  </script>
</body>
</html>'''"""

with open("src/gaia_cli/graph.py", "w") as f:
    f.write(content[:start_idx] + new_render_html + content[end_idx:])
