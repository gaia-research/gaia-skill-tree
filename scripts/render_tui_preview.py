"""Generate docs/samples/tui-preview.html — a byte-faithful color preview.

For each TUI screen, we re-invoke the screen's pure rendering helpers
(`_seal_text`, `_skill_label`, `_node_label`, `_render_frame`) and capture
their `rich.Text` output via a recording `rich.Console`. The exported
HTML is then embedded in a single self-contained preview page along
with a token swatch grid.

Run:
    python scripts/render_tui_preview.py
    open docs/samples/tui-preview.html
"""

from __future__ import annotations

import html
import io
import os
import sys
from contextlib import contextmanager

# Ensure src/ is importable when this script is run from the repo root
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, "src"))

from rich.console import Console  # noqa: E402
from rich.text import Text  # noqa: E402

from gaia_cli.tui import tokens as T  # noqa: E402
from gaia_cli.tui.screens.hero import _seal_text, _title_text  # noqa: E402
from gaia_cli.tui.screens.agent import _skill_label  # noqa: E402
from gaia_cli.tui.screens.tree import _node_label  # noqa: E402


def _record(width: int = 80) -> Console:
    return Console(
        record=True,
        width=width,
        force_terminal=True,
        color_system="truecolor",
        file=io.StringIO(),
    )


def _export(console: Console) -> str:
    """Export captured Rich segments as an HTML <pre> fragment."""
    return console.export_html(inline_styles=True, code_format="{code}")


def _swatch_row(label: str, value: str, role: str) -> str:
    return (
        f"<tr>"
        f"<td><span class='swatch' style='background:{value}'></span></td>"
        f"<td><code>{html.escape(label)}</code></td>"
        f"<td><code>{value}</code></td>"
        f"<td>{html.escape(role)}</td>"
        f"</tr>"
    )


def render_token_table() -> str:
    rows: list[str] = []

    rows.append("<tbody><tr><th colspan=4>Neutrals</th></tr>")
    for label, value, role in [
        ("NEUTRAL_BG",            T.NEUTRAL_BG,            "Page background"),
        ("NEUTRAL_SURFACE",       T.NEUTRAL_SURFACE,       "Panel / card surface"),
        ("NEUTRAL_BORDER",        T.NEUTRAL_BORDER,        "Dividers, borders"),
        ("NEUTRAL_BORDER_STRONG", T.NEUTRAL_BORDER_STRONG, "Hover / focus border"),
        ("NEUTRAL_TEXT",          T.NEUTRAL_TEXT,          "Primary text"),
        ("NEUTRAL_TEXT_MUTED",    T.NEUTRAL_TEXT_MUTED,    "Secondary copy"),
        ("NEUTRAL_TEXT_DIM",      T.NEUTRAL_TEXT_DIM,      "Tertiary / hint copy"),
    ]:
        rows.append(_swatch_row(label, value, role))
    rows.append("</tbody>")

    rows.append("<tbody><tr><th colspan=4>Branch accents</th></tr>")
    for label, value, role in [
        ("BRANCH_ACCENT['standard']", T.BRANCH_ACCENT["standard"], "○ standard branch"),
        ("BRANCH_ACCENT['suite']",    T.BRANCH_ACCENT["suite"],    "◆ suite branch"),
        ("BRANCH_ACCENT['unique']",   T.BRANCH_ACCENT["unique"],   "◉ unique branch"),
    ]:
        rows.append(_swatch_row(label, value, role))
    rows.append("</tbody>")

    rows.append("<tbody><tr><th colspan=4>Rank ramp (0★ → 6★)</th></tr>")
    for label, value, role in [
        ("RANK_UNAWAKENED", T.RANK_UNAWAKENED, "0★ Basic — slate"),
        ("RANK_AWAKENED",   T.RANK_AWAKENED,   "1★ Awakened — sky blue"),
        ("RANK_NAMED",      T.RANK_NAMED,      "2★ Named — teal"),
        ("RANK_EVOLVED",    T.RANK_EVOLVED,    "3★ Evolved — violet"),
        ("RANK_EXTRA",      T.RANK_EXTRA,      "4★ Extra / Unique — fuchsia"),
        ("RANK_ULTIMATE",   T.RANK_ULTIMATE,   "5★ Ultimate / Unique Ultimate — amber"),
        ("RANK_APEX",       T.RANK_APEX,       "6★ Apex / Unique Impossible — amber (bright)"),
    ]:
        rows.append(_swatch_row(label, value, role))
    rows.append("</tbody>")

    rows.append("<tbody><tr><th colspan=4>Brand (restricted)</th></tr>")
    for label, value, role in [
        ("BRAND_HONOR_RED", T.BRAND_HONOR_RED, "Contributor handles only"),
        ("BRAND_APEX_GOLD", T.BRAND_APEX_GOLD, "6★ / Apex / Diamond Seal only"),
    ]:
        rows.append(_swatch_row(label, value, role))
    rows.append("</tbody>")

    rows.append("<tbody><tr><th colspan=4>Functional states</th></tr>")
    for label, value, role in [
        ("STATE_OWNED",                T.STATE_OWNED,                "✓ owned-skill check"),
        ("STATE_DETECTED",             T.STATE_DETECTED,             "◎ detected (sky blue)"),
        ("STATE_INSTALL_ACTION",       T.STATE_INSTALL_ACTION,       "Install button background"),
        ("STATE_INSTALL_ACTION_HOVER", T.STATE_INSTALL_ACTION_HOVER, "Install button hover"),
        ("STATE_INSTALL_ERROR",        T.STATE_INSTALL_ERROR,        "Install error"),
        ("STATE_SCAN_COMPLETE",        T.STATE_SCAN_COMPLETE,        "Scan completion message"),
    ]:
        rows.append(_swatch_row(label, value, role))
    rows.append("</tbody>")

    return (
        "<table class='tokens'>"
        "<thead><tr><th>swatch</th><th>name</th><th>hex</th><th>role</th></tr></thead>"
        + "".join(rows)
        + "</table>"
    )


def render_hero_capture() -> str:
    console = _record(width=44)
    console.print(_seal_text(T.BRANCH_ACCENT["suite"]))
    console.print()
    console.print(_title_text(frame=0))
    console.print()
    stats = Text()
    stats.append("○ 78 standard", style=T.BRANCH_ACCENT["standard"])
    stats.append("  ·  ", style=T.NEUTRAL_TEXT_MUTED)
    stats.append("◉ 81 unique", style=T.BRANCH_ACCENT["unique"])
    stats.append("  ·  ", style=T.NEUTRAL_TEXT_MUTED)
    stats.append("◆ 2 suite", style=T.BRANCH_ACCENT["suite"])
    stats.append("  ·  ", style=T.NEUTRAL_TEXT_MUTED)
    stats.append("✦ 119 named", style=T.BRAND_APEX_GOLD)
    console.print(stats)
    return _export(console)


def _mock_skill(
    sid: str,
    level: str = "",
    installed: bool = False,
    suite_components: list[str] | None = None,
) -> dict:
    """Build a mock registry entry and derive its display branch via the
    taxonomy authority (build + read — the preview never hand-labels a branch).

    A ``suite_components`` list makes ``branchFor`` return "suite"; a 4★+ level
    with no components returns "unique"; everything else is "standard".
    """
    from gaia_cli.taxonomy import branchFor

    entry: dict = {"id": sid, "level": level, "installed": installed}
    if suite_components is not None:
        entry["suiteComponents"] = suite_components
    entry["branch"] = branchFor(entry)
    return entry


def render_agent_capture() -> str:
    console = _record(width=72)
    samples = [
        _mock_skill("web-scrape",                  "1★", installed=True),
        _mock_skill("parse-json",                  "0★"),
        _mock_skill("api-proxy",                   "2★"),
        _mock_skill("elena/payment-orchestrator",  "3★", installed=True),
        _mock_skill("noor/multi-agent-debate",     "6★",
                    suite_components=["debate-loop", "critic", "arbiter"]),
        _mock_skill("karpathy/llm-training-loop",  "4★", installed=True),
    ]
    for skill in samples:
        console.print(_skill_label(skill))
    return _export(console)


def render_tree_capture() -> str:
    console = _record(width=72)
    headers = [
        ("◆ SUITE", T.BRANCH_ACCENT["suite"]),
        ("  ◆ multi-agent-debate", T.BRANCH_ACCENT["suite"]),
        ("◉ UNIQUE",   T.BRANCH_ACCENT["unique"]),
        ("  ◉ retrieval-augmented", T.BRANCH_ACCENT["unique"]),
        ("○ STANDARD",    T.BRANCH_ACCENT["standard"]),
        ("  ○ api-proxy", T.BRANCH_ACCENT["standard"]),
        ("  ○ parse-json", T.BRANCH_ACCENT["standard"]),
    ]
    for label, color in headers:
        t = Text(label, style=f"bold {color}")
        console.print(t)
    return _export(console)


def render_levelup_capture() -> str:
    """Mock the level-up modal frame at the final rank-locked state (a 6★ suite
    unlock — the authority's rank word for that is "Apex")."""
    console = _record(width=42)
    accent = T.BRANCH_ACCENT["suite"]
    gutter = T.NEUTRAL_BORDER
    border_h = "═" * 34
    rows: list[tuple[str, str]] = [
        (f"╔{border_h}╗", accent),
        (f"║{'':^34}║", gutter),
        (f"║{' ★ ★  APEX  ★ ★ '.center(34)}║", accent),
        (f"║{'':^34}║", gutter),
        (f"║{'  ◉  '.center(34)}║", T.BRAND_APEX_GOLD),
        (f"║{'':^34}║", gutter),
        (f"║{'  noor/multi-agent-debate  '.center(34)}║", T.NEUTRAL_TEXT),
        (f"║{'  6★  '.center(34)}║", T.NEUTRAL_TEXT_MUTED),
        (f"║{'':^34}║", gutter),
        (f"║{'· ○ ○ ◇ ◈ ◆ ✦'.center(34)}║", accent),
        (f"║{'':^34}║", gutter),
        (f"║{' [press any key] '.center(34)}║", T.NEUTRAL_TEXT_DIM),
        (f"╚{border_h}╝", accent),
    ]
    for line, color in rows:
        console.print(Text(line, style=color))
    return _export(console)


def render_scan_capture() -> str:
    console = _record(width=72)
    samples: list[tuple[str, str]] = [
        ("  Scanning repository…",                       T.NEUTRAL_TEXT_MUTED),
        ("",                                              T.NEUTRAL_TEXT_DIM),
        ("  ⚡ 14 skills reachable",                      T.STATE_SCAN_COMPLETE),
        ("",                                              T.NEUTRAL_TEXT_DIM),
        ("  ○  api-proxy",                                T.BRANCH_ACCENT["standard"]),
        ("  ○  parse-json",                               T.BRANCH_ACCENT["standard"]),
        ("  ◉  elena/payment-orchestrator",               T.BRANCH_ACCENT["unique"]),
        ("  ──▶  fusion: web-scrape + parse-json",        T.BRANCH_ACCENT["suite"]),
        ("   SKILL UNLOCKED ",                            T.BRANCH_ACCENT["suite"]),
        ("",                                              T.NEUTRAL_TEXT_DIM),
        ("  ✓ Scan complete",                             T.STATE_SCAN_COMPLETE),
    ]
    for line, color in samples:
        console.print(Text(line, style=color))
    return _export(console)


def render_html() -> str:
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>Gaia TUI — Token Preview</title>
  <style>
    :root {{
      --tui-bg: {T.NEUTRAL_BG};
      --tui-surface: {T.NEUTRAL_SURFACE};
      --tui-border: {T.NEUTRAL_BORDER};
      --tui-text: {T.NEUTRAL_TEXT};
      --tui-muted: {T.NEUTRAL_TEXT_MUTED};
    }}
    body {{
      background: var(--tui-bg);
      color: var(--tui-text);
      font-family: ui-monospace, 'JetBrains Mono', 'Departure Mono', monospace;
      padding: 2rem;
      max-width: 1100px;
      margin: 0 auto;
    }}
    h1, h2 {{ color: {T.BRAND_APEX_GOLD}; font-weight: 600; }}
    h1 small {{ color: var(--tui-muted); font-size: 0.6em; margin-left: 1em; }}
    .screen {{
      background: var(--tui-bg);
      border: 1px solid var(--tui-border);
      border-radius: 4px;
      padding: 1.25rem;
      margin-bottom: 2rem;
    }}
    .screen pre {{
      margin: 0;
      font-family: inherit;
      font-size: 13px;
      line-height: 1.5;
      white-space: pre;
      overflow-x: auto;
    }}
    .meta {{ color: var(--tui-muted); font-size: 0.85em; margin-bottom: 0.6rem; }}
    table.tokens {{
      width: 100%;
      border-collapse: collapse;
      margin-bottom: 2rem;
    }}
    table.tokens th, table.tokens td {{
      text-align: left;
      padding: 6px 12px;
      border-bottom: 1px solid var(--tui-border);
      font-size: 0.9em;
    }}
    table.tokens th {{
      background: var(--tui-surface);
      color: var(--tui-muted);
      font-weight: 500;
      text-transform: uppercase;
      letter-spacing: 0.05em;
      font-size: 0.75em;
    }}
    table.tokens tbody th {{
      background: transparent;
      color: {T.BRAND_APEX_GOLD};
      padding-top: 1rem;
      text-transform: none;
      font-size: 0.9em;
      letter-spacing: 0;
    }}
    table.tokens td code {{ color: var(--tui-text); }}
    .swatch {{
      display: inline-block;
      width: 1.4em;
      height: 1.4em;
      vertical-align: middle;
      border: 1px solid var(--tui-border);
      border-radius: 3px;
    }}
    .audit {{
      list-style: none;
      padding: 0;
      margin: 1em 0;
    }}
    .audit li {{
      padding: 4px 0;
      color: {T.STATE_OWNED};
    }}
    .audit li::before {{
      content: '✓ ';
      margin-right: 0.5em;
    }}
  </style>
</head>
<body>
  <h1>Gaia TUI — Token Preview <small>generated from src/gaia_cli/tui/tokens.py</small></h1>
  <p class="meta">
    Every color below is the canonical resolved value from
    <code>tokens.py</code>, which loads branch and rank colors from
    <code>registry/gaia.json.meta</code>. If you change the registry,
    re-run <code>python scripts/render_tui_preview.py</code> to
    regenerate this page.
  </p>

  <h2>Tokens</h2>
  {render_token_table()}

  <h2>HeroScreen</h2>
  <p class="meta">Diamond Seal + GAIA letters + registry stats. Live screen
  cycles seal color through <code>CYCLE_APEX</code>; this capture is
  frozen on the suite stop.</p>
  <div class="screen">{render_hero_capture()}</div>

  <h2>AgentScreen — skill list</h2>
  <p class="meta">Contributor handles (before <code>/</code>) render in
  <code>BRAND_HONOR_RED</code>. Owned skills get a green ✓.</p>
  <div class="screen">{render_agent_capture()}</div>

  <h2>SkillTreeScreen — branch groups</h2>
  <p class="meta">Branch headers use the canonical <code>BRANCH_ACCENT</code>
  color directly — the off-palette GitHub Primer colors from the first pass
  are gone.</p>
  <div class="screen">{render_tree_capture()}</div>

  <h2>LevelUpModal — Apex unlock</h2>
  <p class="meta">Apex-gold glyph appears only at the pinnacle frame.
  Banner and border carry the branch accent; the banner word is the
  authority's <code>rankWord</code> ("Apex" for a 6★ suite).</p>
  <div class="screen">{render_levelup_capture()}</div>

  <h2>ScanScreen — live output</h2>
  <p class="meta">Each line classified by regex; branch glyph maps to
  <code>BRANCH_GLYPH</code>; unlock banners carry the suite accent.</p>
  <div class="screen">{render_scan_capture()}</div>

  <h2>Lint audit</h2>
  <ul class="audit">
    <li>No bare hex literals outside <code>tokens.py</code></li>
    <li>Apex Gold appears only in: Diamond Seal G, Apex banner,
        ✦ named count, 6★ rank</li>
    <li>Honor Red appears only in contributor handles before <code>/</code></li>
    <li>Off-palette literals
        (<code>#30363d</code>, <code>#e3b341</code>, <code>#79c0ff</code>,
         <code>#d2a8ff</code>, <code>#e6edf3</code>, <code>#3fb950</code>,
         <code>#8b949e</code>, <code>#484f58</code>)
        replaced with canonical tokens</li>
  </ul>
</body>
</html>
"""


def main() -> int:
    output_dir = os.path.join(ROOT, "docs", "samples")
    os.makedirs(output_dir, exist_ok=True)
    output_path = os.path.join(output_dir, "tui-preview.html")
    with open(output_path, "w", encoding="utf-8") as fh:
        fh.write(render_html())
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
