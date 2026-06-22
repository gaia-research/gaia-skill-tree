#!/usr/bin/env python3
"""Regenerate marker-owned Gaia documentation sections."""

from __future__ import annotations

import re
import argparse
import filecmp
import json
import subprocess
import sys
import tempfile
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gaia_cli.main import PUBLIC_COMMANDS, get_parser  # noqa: E402

# Stage 1 — bring in the schema-driven CSS-token generator so --check can
# verify docs/css/tokens.css is in sync with registry/gaia.json.meta.
SCRIPTS = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPTS))
from generateCssTokens import build_tokens_css, load_gaia  # noqa: E402


def _read_version() -> str:
    for line in (ROOT / "pyproject.toml").read_text(encoding="utf-8").splitlines():
        if line.startswith("version = "):
            return line.split("=", 1)[1].strip().strip('"')
    return "unknown"


def _replace_region(text: str, start: str, end: str, body: str) -> tuple[str, bool]:
    region = f"{start}\n{body.rstrip()}\n{end}"
    if start not in text or end not in text:
        return text.rstrip() + "\n\n" + region + "\n", True
    before, rest = text.split(start, 1)
    _old, after = rest.split(end, 1)
    updated = before + region + after
    return updated, updated != text


def _strip_ansi(text):
    # This regex identifies the standard ANSI escape sequences
    ansi_escape = re.compile(r'\x1B(?:[@-Z\\-_]|\[[0-?]*[ -/]*[@-~])')
    return ansi_escape.sub('', text)

def _cli_help() -> str:
    parser, _ = get_parser()
    parser.formatter_class = partial(argparse.RawDescriptionHelpFormatter, width=100)
    parser.usage = (
        "%(prog)s [-h] [--registry REGISTRY] [--global] [--version]\n"
        f"            {{{','.join(PUBLIC_COMMANDS)}}}\n"
        "            ..."
    )
    help_text = _strip_ansi(parser.format_help())
    return f"```text\n{help_text}\n```"


def _layout() -> str:
    return """```text
registry/                 curated registry data and public generated catalogs
registry-for-review/      pending skill batch intake records
skill-trees/              per-user skill-tree.json files
generated-output/         ignored local scan and render output
docs/                     docs site
src/gaia_cli/             Python CLI package
packages/cli-npm/         npm wrapper package
packages/mcp/             MCP server package
scripts/                  validation, rendering, docs, and release helpers
tests/                    Python test suite
```"""


def _versions() -> str:
    version = _read_version()
    return f"""Current Gaia CLI version: `{version}`.

```bash
curl -fsSL https://gaia.tiongson.co/install.sh | sh
```

npm wrapper alternative:

```bash
npm install -g @gaia-registry/cli
```"""


def _registry_tree() -> str:
    # 1. Get total skills
    graph_path = ROOT / "registry" / "gaia.json"
    if not graph_path.exists():
        return "```text\n(registry not found)\n```"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    total_skills = len(graph.get("skills", []))

    # 2. Read docs/tree.md (should have been updated by build_tree_md)
    tree_path = ROOT / "docs" / "tree.md"
    if not tree_path.exists():
        # Try generated-output if docs/tree.md doesn't exist yet
        tree_path = ROOT / "generated-output" / "tree.md"
        
    if not tree_path.exists():
        return "```text\n(tree not yet generated)\n```"
    
    tree_text = tree_path.read_text(encoding="utf-8")
    
    # Extract from code block
    match = re.search(r'```\n(.*?)\n```', tree_text, re.DOTALL)
    if not match:
        return "```text\n(could not parse tree)\n```"
    
    tree_body = match.group(1)
    lines = tree_body.splitlines()
    
    # Skip header/legend
    content_start = -1
    for i, line in enumerate(lines):
        # Legend starts with ◆ but contains other symbols too. 
        # Real skills have a name/id usually containing a slash or starting with /
        if line.startswith("◆ ") and "/" in line and "[" in line and "★]" in line:
            content_start = i
            break
            
    if content_start == -1:
        return f"```text\n{tree_body}\n```"

    import re as _re

    def _extract_ultimate_block(lines: list, start_idx: int) -> tuple[list, int]:
        """Return (block_lines_up_to_15, next_top_level_idx) for a ◆ block."""
        block = [lines[start_idx]]
        i = start_idx + 1
        while i < len(lines) and not lines[i].startswith("◆ ") and not lines[i].startswith("═"):
            if lines[i].startswith("────"):
                i += 1
                continue
            if len(block) < 15:
                depth = lines[i].count("│") + lines[i].count(" ") // 2
                if depth <= 8:
                    block.append(lines[i])
            i += 1
        while block and not block[-1].strip():
            block.pop()
        return block, i

    def _nested_ultimates(lines: list, idx: int) -> set[str]:
        """Names of any ◆ that appear indented inside the block at idx."""
        found: set[str] = set()
        j = idx + 1
        while j < len(lines) and not lines[j].startswith("◆ ") and not lines[j].startswith("═"):
            m = _re.match(r"^\s+[│ ]*[├└]─ ◆ ([\w/.-]+)", lines[j])
            if m:
                found.add(m.group(1))
            j += 1
        return found

    # Preferred samples, in order. A candidate is skipped if it is already
    # nested (as a sub-◆) inside any previously selected sample.
    PREFERRED_SAMPLES = ["mattpocock/skills", "garrytan/gstack"]

    # Build index: name → line idx for top-level ◆ entries
    ultimate_idx: dict[str, int] = {}
    for i in range(content_start, len(lines)):
        m = _re.match(r"^◆ ([\w/.-]+)", lines[i])
        if m:
            ultimate_idx[m.group(1)] = i

    truncated_lines: list[str] = []
    nested_so_far: set[str] = set()

    for sample_name in PREFERRED_SAMPLES:
        if sample_name in nested_so_far:
            continue  # already represented inside a higher-star tree shown above
        idx = ultimate_idx.get(sample_name)
        if idx is None:
            continue
        block, _ = _extract_ultimate_block(lines, idx)
        truncated_lines.extend(block)
        truncated_lines.append("")
        nested_so_far |= _nested_ultimates(lines, idx)

    # Look for Uniques section
    uniques_start = -1
    for j in range(content_start, len(lines)):
        if "Uniques — " in lines[j]:
            uniques_start = j
            break
            
    if uniques_start != -1:
        if truncated_lines and truncated_lines[-1].strip():
            truncated_lines.append("")
        
        # Add Uniques header and first few items
        truncated_lines.append(lines[uniques_start])
        j = uniques_start + 1
        # Skip potential separators
        while j < len(lines) and lines[j].startswith("═"):
            j += 1
        
        count = 0
        while j < len(lines) and not lines[j].startswith("═") and count < 5:
            if lines[j].strip():
                truncated_lines.append(lines[j])
                count += 1
            j += 1
            
    # Clean up trailing empty lines
    while truncated_lines and not truncated_lines[-1].strip():
        truncated_lines.pop()
        
    final_body = "\n".join(truncated_lines)
    return f"```text\n{final_body}\n\n({total_skills} skills total — see docs/tree.md)\n```"


def build_readme(check: bool) -> bool:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    changed = False
    for start, end, body in (
        ("<!-- gaia:version-start -->", "<!-- gaia:version-end -->", _versions()),
        ("<!-- gaia:registry-start -->", "<!-- gaia:registry-end -->", _registry_tree()),
        ("<!-- gaia:cli-start -->", "<!-- gaia:cli-end -->", _cli_help()),
        ("<!-- gaia:layout-start -->", "<!-- gaia:layout-end -->", _layout()),
    ):
        text, did_change = _replace_region(text, start, end, body)
        if did_change and check:
            print('diff', start, end, body)
        changed = changed or did_change
    if changed and not check:
        path.write_text(text, encoding="utf-8")
    return changed


def build_docs_index(check: bool) -> bool:
    path = ROOT / "docs" / "index.html"
    if not path.exists():
        return False
    graph = json.loads((ROOT / "registry" / "gaia.json").read_text(encoding="utf-8"))
    named = json.loads((ROOT / "registry" / "named-skills.json").read_text(encoding="utf-8"))
    named_count = sum(len(entries) for entries in named.get("buckets", {}).values())
    unique_count = sum(1 for s in graph.get("skills", []) if s.get("type") == "unique")
    body = (
        f"skills={len(graph.get('skills', []))}; namedSkills={named_count}; "
        f"uniqueSkills={unique_count}; version={graph.get('version', 'unknown')}"
    )
    text = path.read_text(encoding="utf-8")
    text, changed = _replace_region(
        text,
        "<!-- gaia:stats-start -->",
        "<!-- gaia:stats-end -->",
        f"<!-- {body} -->",
    )
    if changed and check:
        print('diff', body)
    if changed and not check:
        path.write_text(text, encoding="utf-8")
    return changed


def _apply_cache_busting(text: str, version: str) -> str:
    # 1. Inject or update Cache-Control meta tags inside <head>
    cache_meta = (
        '\n  <meta http-equiv="Cache-Control" content="no-cache, no-store, must-revalidate">\n'
        '  <meta http-equiv="Pragma" content="no-cache">\n'
        '  <meta http-equiv="Expires" content="0">'
    )
    if 'http-equiv="Cache-Control"' not in text:
        text = text.replace("<head>", f"<head>{cache_meta}", 1)

    # 2. Inject or update window.GAIA_VERSION in <head>
    version_script = f'\n  <script>window.GAIA_VERSION = "{version}";</script>'
    if 'window.GAIA_VERSION = ' in text:
        text = re.sub(
            r'<script>\s*window\.GAIA_VERSION\s*=\s*"[^"]*";\s*</script>',
            f'<script>window.GAIA_VERSION = "{version}";</script>',
            text
        )
    else:
        text = text.replace("<head>", f"<head>{version_script}", 1)

    # 3. Append version query parameters (?v={version}) to local CSS and JS imports.
    # Matches: relative paths (../css/foo.css, css/foo.css) AND same-directory files
    # (styles.css, leaderboard.css) — but never absolute URLs (http://, https://).
    text = re.sub(
        r'href="((?!https?://)(?:(?:\.\./)*)(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+\.css)(?:\?v=[^"]*)?"',
        fr'href="\1?v={version}"',
        text
    )
    text = re.sub(
        r'src="((?!https?://)(?:(?:\.\./)*)(?:[a-zA-Z0-9_\-\.]+/)*[a-zA-Z0-9_\-\.]+\.js)(?:\?v=[^"]*)?"',
        fr'src="\1?v={version}"',
        text
    )

    # 4. Update the human-readable footer version literal ("v3.x.x ·").
    text = re.sub(r'\bv\d+\.\d+\.\d+(?=\s+·)', f'v{version}', text)

    return text


def build_html_cache_busting(check: bool) -> bool:
    version = _read_version()
    changed = False
    for filename in (
        "index.html",
        "about.html",
        "codex.html",
        "meta.html",
        "privacy.html",
        "starless.html",
        "badges/index.html",
        "named/index.html",
        "named/report.html",
        "share/index.html",
        "trust/index.html",
        "trust/ledger/index.html",
        "codex/trust-methodology.html",
        "u/index.html",
    ):
        path = ROOT / "docs" / filename
        if not path.exists():
            continue
        original_text = path.read_text(encoding="utf-8")
        updated_text = _apply_cache_busting(original_text, version)
        if original_text != updated_text:
            changed = True
            if check:
                print(f"diff docs/{filename} (cache busting / version stale)")
            else:
                path.write_text(updated_text, encoding="utf-8")
    return changed


def build_wiki_sync(check: bool) -> bool:
    """Run sync_wiki.py against ../gaia-wiki if that directory exists.

    In --check mode the script is called with --check and any reported drift
    contributes to the overall drift signal (but does NOT cause `gaia docs build
    --check` to fail — wiki drift is advisory only, since CI handles the push
    separately via WIKI_PAT).

    In write mode the wiki pages are updated on disk but NOT pushed; CI runs
    sync_wiki.py --push after cloning the wiki with credentials.
    """
    script = SCRIPTS / "sync_wiki.py"
    if not script.exists():
        return False
    wiki_dir = ROOT.parent / "gaia-wiki"
    if not wiki_dir.exists():
        # No local wiki clone — skip silently (not an error for local devs)
        return False
    args_extra = ["--check"] if check else []
    rc, output = _run_script(script, ["--wiki-dir", str(wiki_dir), *args_extra])
    if output.strip():
        print(output.rstrip())
    # Wiki drift is advisory — never fail the build over it
    return False


def build_css_tokens(check: bool) -> bool:
    """Regenerate docs/css/tokens.css from registry/gaia.json. Returns True if drift."""
    gaia_path = ROOT / "registry" / "gaia.json"
    out_path = ROOT / "docs" / "css" / "tokens.css"
    if not gaia_path.exists():
        return False
    gaia = load_gaia(gaia_path)
    rendered = build_tokens_css(gaia)
    if not out_path.exists():
        if check:
            print(f"diff docs/css/tokens.css (missing)")
            return True
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(rendered, encoding="utf-8")
        return True
    current = out_path.read_text(encoding="utf-8")
    if current == rendered:
        return False
    if check:
        print("diff docs/css/tokens.css")
        return True
    out_path.write_text(rendered, encoding="utf-8")
    return True


# ─────────────────────────────────────────────────────────────────────────────
# Stage 4 — extend --check to drive the full asset pipeline so any drift between
# the schema (registry/gaia.json + registry/named/*.md) and the committed docs/
# assets surfaces in one place. Each helper below regenerates into a tempdir
# and diffs the output against the committed copy.
#
# Stage 7 will add: ! grep -RnE 'levels?\\.sort\\(.*a\\s*-\\s*b|sortBy.*level.*asc' docs/js/ scripts/ | grep -v 'data-pattern.*journey'
# (directional lint guard — Ascension Cycle remains exempt). Don't add the
# actual lint here; Stage 7 owns the CI wiring.
# ─────────────────────────────────────────────────────────────────────────────


# Volatile release timestamps embedded in generated artifacts. assemble_gaia.py
# stamps registry/gaia.json's `generatedAt` with wall-clock now() on every build,
# and that date cascades into named-skills.json and docs/tree.md. Auto-Sync
# re-stamps it on every main merge, so a feature branch built on a later calendar
# day shows a date-only diff that is NOT real content drift. In --check mode we
# normalize these timestamps away so the integrity gate flags genuine changes
# only; write mode keeps the byte-exact comparison so Auto-Sync still freshens
# the committed date on main.
_VOLATILE_DATE_PATTERNS = (
    # JSON: "generatedAt": "2026-06-13" | "...T..Z" → value blanked
    (re.compile(r'("generatedAt"\s*:\s*)"[^"]*"'), r'\1"<normalized>"'),
    # docs/tree.md provenance lines, both forms:
    #   "GAIA SKILL TREE … · generated 2026-06-13"   (banner header)
    #   "Generated from gaia.json on 2026-06-13. …"  (footer)
    (re.compile(r'([Gg]enerated(?: from gaia\.json on)?\s+)'
                r'\d{4}-\d{2}-\d{2}(?:[T ][\d:.]+Z?)?'),
     r'\1<normalized>'),
)


def _normalize_dates(text: str) -> str:
    for pattern, repl in _VOLATILE_DATE_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def _equal_ignoring_dates(a: Path, b: Path) -> bool:
    """Compare two text files ignoring volatile release timestamps.

    Falls back to a byte comparison if either file is not valid UTF-8.
    """
    try:
        return _normalize_dates(a.read_text(encoding="utf-8")) == _normalize_dates(
            b.read_text(encoding="utf-8")
        )
    except (OSError, UnicodeDecodeError):
        return filecmp.cmp(a, b, shallow=False)


def _diff_tree(reference: Path, candidate: Path) -> list[str]:
    """Return a list of relative path diffs between two directory trees.

    A path appears in the list if it's present in only one side or if the file
    bytes differ. Empty list → trees match.
    """
    drifts: list[str] = []

    def _walk(rel: Path) -> None:
        ref = reference / rel if rel.parts else reference
        cand = candidate / rel if rel.parts else candidate
        ref_names = {p.name for p in ref.iterdir()} if ref.is_dir() else set()
        cand_names = {p.name for p in cand.iterdir()} if cand.is_dir() else set()
        for name in sorted(ref_names | cand_names):
            sub = rel / name
            ref_path = reference / sub
            cand_path = candidate / sub
            if ref_path.is_dir() or cand_path.is_dir():
                if not (ref_path.is_dir() and cand_path.is_dir()):
                    drifts.append(str(sub))
                    continue
                _walk(sub)
                continue
            if not ref_path.exists() or not cand_path.exists():
                drifts.append(str(sub))
                continue
            if sub.name == "registry.json":
                if not _equal_ignoring_dates(ref_path, cand_path):
                    drifts.append(str(sub))
            elif not filecmp.cmp(ref_path, cand_path, shallow=False):
                drifts.append(str(sub))

    if not reference.exists() or not candidate.exists():
        return ["<tree missing>"]
    _walk(Path())
    return drifts


def _run_script(script: Path, args: list[str]) -> tuple[int, str]:
    """Run a helper script and return (returncode, stdout+stderr)."""
    proc = subprocess.run(
        [sys.executable, str(script), *args],
        cwd=ROOT,
        capture_output=True,
        text=True,
    )
    return proc.returncode, proc.stdout + proc.stderr


def build_named_index(check: bool) -> bool:
    """Run generateNamedIndex.py and compare against registry/named-skills.json."""
    script = SCRIPTS / "generateNamedIndex.py"
    if not script.exists():
        return False
    committed = ROOT / "registry" / "named-skills.json"
    with tempfile.TemporaryDirectory() as tmp:
        out_path = Path(tmp) / "named-skills.json"
        rc, output = _run_script(script, ["--out", str(out_path)])
        if rc != 0:
            if check:
                print(f"diff registry/named-skills.json (regen failed: rc={rc})")
                print(output)
            raise RuntimeError(f"named-skills.json regen failed: rc={rc}")
        if not committed.exists():
            if check:
                print("diff registry/named-skills.json (missing committed file)")
            return True
        if check:
            if _equal_ignoring_dates(committed, out_path):
                return False
            print("diff registry/named-skills.json")
            return True
        if filecmp.cmp(committed, out_path, shallow=False):
            return False
        committed.write_bytes(out_path.read_bytes())
        return True


def build_docs_named_index(check: bool) -> bool:
    """Mirror registry/named-skills.json → docs/graph/named/index.json (sync step)."""
    src = ROOT / "registry" / "named-skills.json"
    dst = ROOT / "docs" / "graph" / "named" / "index.json"
    if not src.exists():
        return False
    if dst.exists() and filecmp.cmp(src, dst, shallow=False):
        return False
    if check:
        print("diff docs/graph/named/index.json")
        return True
    dst.parent.mkdir(parents=True, exist_ok=True)
    dst.write_bytes(src.read_bytes())
    return True


def build_profile_pages(check: bool) -> bool:
    """Run generateProfilePages.py to a tempdir and diff against docs/u/."""
    script = SCRIPTS / "generateProfilePages.py"
    if not script.exists():
        return False
    committed = ROOT / "docs" / "u"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "u"
        rc, output = _run_script(script, ["--out-dir", str(out_dir)])
        if rc != 0:
            if check:
                print(f"diff docs/u/ (regen failed: rc={rc})")
                print(output)
            raise RuntimeError(f"docs/u/ regen failed: rc={rc}")
        # The contributors directory page (u/index.html) has cache-busting
        # meta/version applied by build_html_cache_busting() in write mode, which
        # runs *after* this step. generateProfilePages.py strips the no-cache meta
        # tags, so the raw generated page never matches the post-processed committed
        # file. Apply the same transform here so --check compares like-for-like
        # instead of reporting perpetual drift on u/index.html.
        gen_index = out_dir / "index.html"
        if gen_index.exists():
            version = _read_version()
            gen_index.write_text(
                _apply_cache_busting(gen_index.read_text(encoding="utf-8"), version),
                encoding="utf-8",
            )
        if not committed.exists():
            if check:
                print("diff docs/u/ (missing)")
            else:
                import shutil
                shutil.copytree(out_dir, committed)
            return True
        drifts = _diff_tree(committed, out_dir)
        if not drifts:
            return False
        if check:
            for d in drifts:
                print(f"diff docs/u/{d}")
        else:
            import shutil
            shutil.rmtree(committed)
            shutil.copytree(out_dir, committed)
        return True


def build_badges(check: bool) -> bool:
    """Run generateBadges.py to a tempdir and diff against docs/badges/."""
    script = SCRIPTS / "generateBadges.py"
    if not script.exists():
        return False
    committed = ROOT / "docs" / "badges"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "badges"
        rc, output = _run_script(script, ["--out-dir", str(out_dir)])
        if rc != 0:
            if check:
                print(f"diff docs/badges/ (regen failed: rc={rc})")
                print(output)
            raise RuntimeError(f"docs/badges/ regen failed: rc={rc}")
        # Preserve hand-authored docs/badges/index.html across regeneration
        # by copying it into the candidate tree before diffing.
        sampler = committed / "index.html"
        if sampler.exists():
            (out_dir / "index.html").write_bytes(sampler.read_bytes())
        if not committed.exists():
            if check:
                print("diff docs/badges/ (missing)")
            else:
                import shutil
                shutil.copytree(out_dir, committed)
            return True
        drifts = _diff_tree(committed, out_dir)
        if not drifts:
            return False
        if check:
            for d in drifts:
                print(f"diff docs/badges/{d}")
        else:
            import shutil
            shutil.rmtree(committed)
            shutil.copytree(out_dir, committed)
        return True


def build_og_cards(check: bool) -> bool:
    """Run generateOgCards.py to a tempdir and diff SVG outputs against docs/og/."""
    script = SCRIPTS / "generateOgCards.py"
    if not script.exists():
        return False
    committed = ROOT / "docs" / "og"
    with tempfile.TemporaryDirectory() as tmp:
        out_dir = Path(tmp) / "og"
        rc, output = _run_script(script, ["--out-dir", str(out_dir)])
        if rc != 0:
            if check:
                print(f"diff docs/og/ (regen failed: rc={rc})")
                print(output)
            raise RuntimeError(f"docs/og/ regen failed: rc={rc}")
        if not committed.exists():
            if check:
                print("diff docs/og/ (missing)")
            else:
                import shutil
                shutil.copytree(out_dir, committed)
            return True

        # Compare only SVG files — PNGs are optional (cairosvg may be absent
        # in CI) and the SVG is the canonical artifact.
        drifts = []
        committed_svgs = {p.relative_to(committed) for p in committed.rglob("*.svg")}
        candidate_svgs = {p.relative_to(out_dir) for p in out_dir.rglob("*.svg")}
        for rel in sorted(committed_svgs | candidate_svgs):
            c = committed / rel
            n = out_dir / rel
            if not c.exists() or not n.exists():
                drifts.append(str(rel))
            elif not filecmp.cmp(c, n, shallow=False):
                drifts.append(str(rel))
        if not drifts:
            return False
        if check:
            for d in drifts:
                print(f"diff docs/og/{d}")
        else:
            import shutil
            # Non-destructive merge: update SVGs, preserve PNGs
            # 1. Copy all candidate SVGs into committed dir
            for svg_rel in candidate_svgs:
                src = out_dir / svg_rel
                dst = committed / svg_rel
                dst.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(src, dst)
            # 2. Remove committed SVGs that are no longer generated
            for svg_rel in committed_svgs - candidate_svgs:
                stale = committed / svg_rel
                if stale.exists():
                    stale.unlink()
            # 3. Remove empty handle directories
            for handle_dir in committed.iterdir():
                if handle_dir.is_dir() and not any(handle_dir.iterdir()):
                    handle_dir.rmdir()
        return True



def build_tree_md(check: bool) -> bool:
    """Run generateProjections.py and compare generated-output/tree.md against docs/tree.md."""
    script = SCRIPTS / "generateProjections.py"
    if not script.exists():
        return False
    
    rc, output = _run_script(script, [])
    if rc != 0:
        if check:
            print(f"diff docs/tree.md (regen failed: rc={rc})")
            print(output)
        raise RuntimeError(f"docs/tree.md regen failed: rc={rc}")

    generated = ROOT / "generated-output" / "tree.md"
    committed = ROOT / "docs" / "tree.md"
    
    if not generated.exists():
        if check:
            print("diff docs/tree.md (regen did not produce output)")
        return True
        
    if not committed.exists():
        if check:
            print("diff docs/tree.md (missing committed file)")
        return True
        
    if check:
        if _equal_ignoring_dates(committed, generated):
            return False
        print("diff docs/tree.md")
        return True

    if filecmp.cmp(committed, generated, shallow=False):
        return False
    committed.write_bytes(generated.read_bytes())
    return True



def build_ruflo_curation(check: bool) -> bool:
    """Verify docs/audits/ruflo-curation.html exists (regenerate with generate_ruflo_curation.py)."""
    path = ROOT / "docs" / "audits" / "ruflo-curation.html"
    if not path.exists():
        if check:
            print("diff docs/audits/ruflo-curation.html (missing — run: python scripts/generate_ruflo_curation.py)")
        return True
    return False


def build_assembly(check: bool) -> bool:
    """Run assemble_gaia.py."""
    script = SCRIPTS / "assemble_gaia.py"
    if not script.exists():
        return False
    rc, output = _run_script(script, [])
    if rc != 0:
        if check:
            print(f"diff registry/gaia.json (assembly failed: rc={rc})")
            print(output)
        raise RuntimeError(f"assembly failed: rc={rc}")
    return False

def build_gexf(check: bool) -> bool:
    """Run exportGexf.py."""
    script = SCRIPTS / "exportGexf.py"
    if not script.exists():
        return False
    rc, output = _run_script(script, [])
    if rc != 0:
        raise RuntimeError(f"exportGexf.py failed: rc={rc}")
    return False

def build_svg(check: bool) -> bool:
    """Run renderGraphSvg.py."""
    script = SCRIPTS / "renderGraphSvg.py"
    if not script.exists():
        return False
    rc, output = _run_script(script, ["--format", "svg"])
    if rc != 0:
        raise RuntimeError(f"renderGraphSvg.py failed: rc={rc}")
    return False

def build_docs_graph_assets(check: bool) -> bool:
    """Run syncDocsGraphAssets.py."""
    script = SCRIPTS / "syncDocsGraphAssets.py"
    if not script.exists():
        return False
    rc, output = _run_script(script, [])
    if rc != 0:
        raise RuntimeError(f"syncDocsGraphAssets.py failed: rc={rc}")
    return False

def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build generated Gaia docs regions.")
    parser.add_argument("--check", action="store_true", help="Fail if generated docs are stale")
    args = parser.parse_args(argv)

    # Track steps that may have failed (subscript errors return True = "stale"
    # but swallow the root cause). We surface warnings so they aren't silent.
    warnings: list[str] = []

    def _run_step(name: str, func, check: bool) -> bool:
        try:
            return func(check)
        except Exception as exc:
            warnings.append(f"{name}: {exc}")
            return False

    # Stage 0 — Core Graph Assembly
    assembly_changed = _run_step("assembly", build_assembly, args.check)

    # Stage 4 — full asset pipeline. Each step regenerates into a tempdir and
    # diffs against the committed copy. CSS tokens are already covered above;
    # syncDocsGraphAssets fans out gaia.json / tree.md / named-index — the
    # named-index drift specifically is the one most likely to land out of sync.
    named_index_changed = _run_step("named-index", build_named_index, args.check)
    docs_named_changed = _run_step("docs-named-index", build_docs_named_index, args.check)
    profiles_changed = _run_step("profiles", build_profile_pages, args.check)
    badges_changed = _run_step("badges", build_badges, args.check)
    og_changed = _run_step("og-cards", build_og_cards, args.check)
    tree_changed = _run_step("tree-md", build_tree_md, args.check)
    ruflo_curation_changed = _run_step("ruflo-curation", build_ruflo_curation, args.check)
    
    # Extra artifacts
    gexf_changed = _run_step("gexf", build_gexf, args.check)
    svg_changed = _run_step("svg", build_svg, args.check)
    sync_assets_changed = _run_step("docs-graph-assets", build_docs_graph_assets, args.check)

    # Local sections (README + index.html stats + tokens.css).
    # README depends on tree.md (build_tree_md)
    readme_changed = _run_step("readme", build_readme, args.check)
    docs_index_changed = _run_step("docs-index", build_docs_index, args.check)
    html_cache_busted = _run_step("html-cache-busting", build_html_cache_busting, args.check)
    css_tokens_changed = _run_step("css-tokens", build_css_tokens, args.check)

    # Wiki sync — updates ../gaia-wiki pages from README marker regions.
    # Advisory only: drift is reported but never blocks the build.
    build_wiki_sync(args.check)

    if warnings:
        print(f"\nWarning: {len(warnings)} build step(s) encountered errors:", file=sys.stderr)
        for w in warnings:
            print(f"  • {w}", file=sys.stderr)

    changed = (
        assembly_changed
        or readme_changed
        or docs_index_changed
        or html_cache_busted
        or css_tokens_changed
        or named_index_changed
        or docs_named_changed
        or profiles_changed
        or badges_changed
        or og_changed
        or tree_changed
        or ruflo_curation_changed
        or gexf_changed
        or svg_changed
        or sync_assets_changed
    )
    if args.check:
        if changed or warnings:
            if warnings:
                print("\nError: Documentation build encountered errors in --check mode.", file=sys.stderr)
            print("Generated documentation is stale. Run `gaia docs build --check` locally.")
            print("If it reports drift, run `gaia docs build` and commit the updated files.")
            print("Validation checks can be run with `gaia validate`.")
            return 1
        print("Documentation is up to date.")
        return 0
    else:
        if warnings:
            print("\nDocumentation build completed with warnings/errors.", file=sys.stderr)
            return 0
        print("Documentation is up to date." if not changed else "Documentation regenerated.")
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
