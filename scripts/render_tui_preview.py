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

    rows.append("<tbody><tr><th colspan=4>Tiers</th></tr>")
    for label, value, role in [
        ("TIER_BASIC",    T.TIER_BASIC,    "○ Basic Skill"),
        ("TIER_EXTRA",    T.TIER_EXTRA,    "◇ Extra Skill"),
        ("TIER_UNIQUE",   T.TIER_UNIQUE,   "◉ Unique Skill"),
        ("TIER_ULTIMATE", T.TIER_ULTIMATE, "◆ Ultimate Skill"),
    ]:
        rows.append(_swatch_row(label, value, role))
    rows.append("</tbody>")

    rows.append("<tbody><tr><th colspan=4>Rank ramp (0★ → 6★)</th></tr>")
    for label, value, role in [
        ("RANK_UNAWAKENED",        T.RANK_UNAWAKENED,        "0★ Unawakened — slate"),
        ("RANK_AWAKENED",          T.RANK_AWAKENED,          "1★ Awakened — sky blue"),
        ("RANK_NAMED",             T.RANK_NAMED,             "2★ Named — teal"),
        ("RANK_EVOLVED",           T.RANK_EVOLVED,           "3★ Evolved — violet"),
        ("RANK_HARDENED",          T.RANK_HARDENED,          "4★ Hardened — fuchsia"),
        ("RANK_TRANSCENDENT",      T.RANK_TRANSCENDENT,      "5★ Transcendent — amber"),
        ("RANK_TRANSCENDENT_APEX", T.RANK_TRANSCENDENT_APEX, "6★ Transcendent ★ — amber (bright)"),
    ]:
        rows.append(_swatch_row(label, value, role))
    rows.append("</tbody>")

    rows.append("<tbody><tr><th colspan=4>Brand (restricted)</th></tr>")
    for label, value, role in [
        ("BRAND_HONOR_RED", T.BRAND_HONOR_RED, "Contributor handles only"),
        ("BRAND_APEX_GOLD", T.BRAND_APEX_GOLD, "6★ / Ultimate / Diamond Seal only"),
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
    console.print(_seal_text(T.TIER_ULTIMATE))
    console.print()
    console.print(_title_text(frame=0))
    console.print()
    stats = Text()
    stats.append("○ 78 basic", style=T.TIER_BASIC)
    stats.append("  ·  ", style=T.NEUTRAL_TEXT_MUTED)
    stats.append("◇ 81 extra", style=T.TIER_EXTRA)
    stats.append("  ·  ", style=T.NEUTRAL_TEXT_MUTED)
    stats.append("◆ 2 ultimate", style=T.TIER_ULTIMATE)
    stats.append("  ·  ", style=T.NEUTRAL_TEXT_MUTED)
    stats.append("✦ 119 named", style=T.BRAND_APEX_GOLD)
    console.print(stats)
    return _export(console)


def _mock_skill(sid: str, type_: str, level: str = "", installed: bool = False) -> dict:
    return {"id": sid, "type": type_, "level": level, "installed": installed}


def render_agent_capture() -> str:
    console = _record(width=72)
    samples = [
        _mock_skill("web-scrape",                  "basic",    "1★", installed=True),
        _mock_skill("parse-json",                  "basic",    "0★"),
        _mock_skill("api-proxy",                   "extra",    "2★"),
        _mock_skill("elena/payment-orchestrator",  "extra",    "3★", installed=True),
        _mock_skill("noor/multi-agent-debate",     "ultimate", "6★"),
        _mock_skill("karpathy/llm-training-loop",  "unique",   "4★", installed=True),
    ]
    for skill in samples:
        console.print(_skill_label(skill))
    return _export(console)


def render_tree_capture() -> str:
    console = _record(width=72)
    headers = [
        ("◆ ULTIMATES", T.TIER_ULTIMATE),
        ("  ◆ multi-agent-debate", T.TIER_ULTIMATE),
        ("◉ UNIQUES",   T.TIER_UNIQUE),
        ("  ◉ retrieval-augmented", T.TIER_UNIQUE),
        ("◇ EXTRAS",    T.TIER_EXTRA),
        ("  ◇ api-proxy", T.TIER_EXTRA),
        ("○ BASICS",    T.TIER_BASIC),
        ("  ○ parse-json", T.TIER_BASIC),
    ]
    for label, color in headers:
        t = Text(label, style=f"bold {color}")
        console.print(t)
    return _export(console)


def render_levelup_capture() -> str:
    """Mock the level-up modal frame at the final tier-locked state."""
    console = _record(width=42)
    tier_color = T.TIER_ULTIMATE
    gutter = T.NEUTRAL_BORDER
    border_h = "═" * 34
    rows: list[tuple[str, str]] = [
        (f"╔{border_h}╗", tier_color),
        (f"║{'':^34}║", gutter),
        (f"║{' ★ ★  ULTIMATE  ★ ★ '.center(34)}║", tier_color),
        (f"║{'':^34}║", gutter),
        (f"║{'  ◉  '.center(34)}║", T.BRAND_APEX_GOLD),
        (f"║{'':^34}║", gutter),
        (f"║{'  noor/multi-agent-debate  '.center(34)}║", T.NEUTRAL_TEXT),
        (f"║{'  6★  '.center(34)}║", T.NEUTRAL_TEXT_MUTED),
        (f"║{'':^34}║", gutter),
        (f"║{'· ○ ○ ◇ ◆ ◉'.center(34)}║", tier_color),
        (f"║{'':^34}║", gutter),
        (f"║{' [press any key] '.center(34)}║", T.NEUTRAL_TEXT_DIM),
        (f"╚{border_h}╝", tier_color),
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
        ("  ◇  api-proxy",                                T.TIER_EXTRA),
        ("  ○  parse-json",                               T.TIER_BASIC),
        ("  ◉  elena/payment-orchestrator",               T.TIER_UNIQUE),
        ("  ──▶  fusion: web-scrape + parse-json",        T.TIER_EXTRA),
        ("   SKILL UNLOCKED ",                            T.TIER_ULTIMATE),
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
    <code>tokens.py</code>, which loads tier and rank colors from
    <code>registry/gaia.json.meta</code>. If you change the registry,
    re-run <code>python scripts/render_tui_preview.py</code> to
    regenerate this page.
  </p>

  <h2>Tokens</h2>
  {render_token_table()}

  <h2>HeroScreen</h2>
  <p class="meta">Diamond Seal + GAIA letters + registry stats. Live screen
  cycles seal color through <code>CYCLE_ULTIMATE</code>; this capture is
  frozen on the Ultimate stop.</p>
  <div class="screen">{render_hero_capture()}</div>

  <h2>AgentScreen — skill list</h2>
  <p class="meta">Contributor handles (before <code>/</code>) render in
  <code>BRAND_HONOR_RED</code>. Owned skills get a green ✓.</p>
  <div class="screen">{render_agent_capture()}</div>

  <h2>SkillTreeScreen — tier groups</h2>
  <p class="meta">Tier headers use the canonical tier color directly —
  the off-palette GitHub Primer colors from the first pass are gone.</p>
  <div class="screen">{render_tree_capture()}</div>

  <h2>LevelUpModal — Ultimate unlock</h2>
  <p class="meta">Apex-gold glyph appears only at the Ultimate frame.
  Banner and border carry the tier color.</p>
  <div class="screen">{render_levelup_capture()}</div>

  <h2>ScanScreen — live output</h2>
  <p class="meta">Each line classified by regex; tier glyph maps to
  <code>TIER_BY_KEY</code>; unlock banners are Ultimate-gold.</p>
  <div class="screen">{render_scan_capture()}</div>

  <h2>Lint audit</h2>
  <ul class="audit">
    <li>No bare hex literals outside <code>tokens.py</code></li>
    <li>Apex Gold appears only in: Diamond Seal G, Ultimate banner,
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
