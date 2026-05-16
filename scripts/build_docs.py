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

Python install:

```bash
pip install gaia-cli
```

npm wrapper alternative:

```bash
npm install -g @gaia-registry/cli
```"""


def build_readme(check: bool) -> bool:
    path = ROOT / "README.md"
    text = path.read_text(encoding="utf-8")
    changed = False
    for start, end, body in (
        ("<!-- gaia:version-start -->", "<!-- gaia:version-end -->", _versions()),
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
            if not filecmp.cmp(ref_path, cand_path, shallow=False):
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
            return True
        if not committed.exists():
            if check:
                print("diff registry/named-skills.json (missing committed file)")
            return True
        if filecmp.cmp(committed, out_path, shallow=False):
            return False
        if check:
            print("diff registry/named-skills.json")
        else:
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
            return True
        if not committed.exists():
            if check:
                print("diff docs/u/ (missing)")
            return True
        drifts = _diff_tree(committed, out_dir)
        if not drifts:
            return False
        if check:
            for d in drifts:
                print(f"diff docs/u/{d}")
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
            return True
        if not committed.exists():
            if check:
                print("diff docs/og/ (missing)")
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
        return True


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build generated Gaia docs regions.")
    parser.add_argument("--check", action="store_true", help="Fail if generated docs are stale")
    args = parser.parse_args(argv)

    # Local sections (README + index.html stats + tokens.css).
    readme_changed = build_readme(args.check)
    docs_index_changed = build_docs_index(args.check)
    css_tokens_changed = build_css_tokens(args.check)

    # Stage 4 — full asset pipeline. Each step regenerates into a tempdir and
    # diffs against the committed copy. CSS tokens are already covered above;
    # syncDocsGraphAssets fans out gaia.json / tree.md / named-index — the
    # named-index drift specifically is the one most likely to land out of sync.
    named_index_changed = build_named_index(args.check)
    docs_named_changed = build_docs_named_index(args.check)
    profiles_changed = build_profile_pages(args.check)
    og_changed = build_og_cards(args.check)

    changed = (
        readme_changed
        or docs_index_changed
        or css_tokens_changed
        or named_index_changed
        or docs_named_changed
        or profiles_changed
        or og_changed
    )
    if args.check and changed:
        print("Generated documentation is stale. Run `python scripts/build_docs.py --check` locally.")
        print("If it reports drift, run `python scripts/build_docs.py` and commit the updated files.")
        print("CSS tokens specifically can be refreshed with `python scripts/generateCssTokens.py`.")
        print("Named index can be refreshed with `python scripts/generateNamedIndex.py`.")
        print("Docs assets can be re-synced with `python scripts/syncDocsGraphAssets.py`.")
        return 1
    print("Documentation is up to date." if not changed else "Documentation regenerated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
