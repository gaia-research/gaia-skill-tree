import re

with open("src/gaia_cli/graph.py", "r") as f:
    content = f.read()

start_marker = "def render_html("
end_marker = "</script>\n</body>\n</html>\"\"\""

start_idx = content.find(start_marker)
end_idx = content.find(end_marker, start_idx) + len(end_marker)

if start_idx == -1 or end_idx == -1:
    print("Could not find render_html bounds")
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
    _title_text = _title_text or user_ctx_data.get("username", "") or "Gaia Skill Graph"

    # Make sure we add 'meta' object so skill-graph.js doesn't crash if missing
    if "meta" not in graph:
        graph["meta"] = {"levelColors": {}, "levelLabels": {}}

    return f'''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{_title_text} - Gaia Skill Graph</title>
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=EB+Garamond:ital,wght@0,400;0,500;0,600;1,400&family=Bricolage+Grotesque:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&display=swap">
  <link rel="stylesheet" href="https://mbtiongson.github.io/gaia-skill-tree/css/styles.css">
  <link rel="stylesheet" href="https://mbtiongson.github.io/gaia-skill-tree/css/plaque.css">
  <style>
    body {{ margin: 0; overflow: hidden; background: #020617; }}
    .graph-hero {{ height: 100vh; width: 100vw; position: relative; }}
    canvas {{ display: block; width: 100%; height: 100%; outline: none; }}
  </style>
</head>
<body>
  <div class="graph-hero" id="graphHero" data-hero-active="true">
    <canvas id="canvas3d"></canvas>
  </div>

  <script type="application/json" id="gaia-graph-data">{_html_json(graph)}</script>
  <script type="application/json" id="gaia-named-skills">{_html_json(named_skills)}</script>
  <script type="application/json" id="gaia-user-ctx">{_html_json(user_ctx_data)}</script>

  <script>
    // Set global title so the graph HUD can use it if it checks
    window.document.title = "{_title_text} - Gaia Skill Graph";
    
    // Define a fallback method for getCanvasTokens early if styles don't load immediately
    window.getCanvasTokens = function() {{
        return {{
            tier: {{
                basic: {{ rgb: '56,189,248', hex: '#38bdf8' }},
                extra: {{ rgb: '192,132,252', hex: '#c084fc' }},
                unique: {{ rgb: '134,239,172', hex: '#86efac' }},
                ultimate: {{ rgb: '245,158,11', hex: '#f59e0b' }}
            }},
            rank: {{
                '1★': {{ rgb: '56,189,248', hex: '#38bdf8' }},
                '2★': {{ rgb: '99,202,183', hex: '#63cab7' }},
                '3★': {{ rgb: '167,139,250', hex: '#a78bfa' }},
                '4★': {{ rgb: '232,121,249', hex: '#e879f9' }},
                '5★': {{ rgb: '251,191,36', hex: '#fbbf24' }},
                '6★': {{ rgb: '251,191,36', hex: '#fbbf24' }}
            }},
            honorRedRgb: '239,68,68',
            apexGold: '#f59e0b',
            mutedRgb: '148,163,184',
            fontBody: 'system-ui, sans-serif',
            fontMono: 'ui-monospace, monospace',
            fontDisplay: 'serif'
        }};
    }};

    // Mock the window.fetch API so `skill-graph.js` loads the inline JSON instead of making network requests.
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

  <!-- Load the same exact UI scripts as the website -->
  <script src="https://mbtiongson.github.io/gaia-skill-tree/js/icons.js"></script>
  <script src="https://mbtiongson.github.io/gaia-skill-tree/js/skill-graph.js"></script>
  <script>
    // In index.html the graph runs interactively.
    // skill-graph.js attaches to window.setInteractive, let's call it.
    setTimeout(() => {{
      const hero = document.getElementById('graphHero');
      if (hero && hero.classList) {{
          hero.classList.add('graph-hero--active');
      }}
    }}, 100);
  </script>
</body>
</html>'''"""

with open("src/gaia_cli/graph.py", "w") as f:
    f.write(content[:start_idx] + new_render_html + content[end_idx:])
print("Replaced render_html successfully.")
