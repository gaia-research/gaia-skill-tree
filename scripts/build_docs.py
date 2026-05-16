#!/usr/bin/env python3
"""Regenerate marker-owned Gaia documentation sections."""

from __future__ import annotations

import re
import argparse
import json
import sys
from functools import partial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from gaia_cli.main import PUBLIC_COMMANDS, get_parser  # noqa: E402

# Stage 1 — bring in the schema-driven CSS-token generator so --check can
# verify docs/css/tokens.css is in sync with registry/gaia.json.meta.
sys.path.insert(0, str(Path(__file__).resolve().parent))
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


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Build generated Gaia docs regions.")
    parser.add_argument("--check", action="store_true", help="Fail if generated docs are stale")
    args = parser.parse_args(argv)

    readme_changed = build_readme(args.check)
    docs_index_changed = build_docs_index(args.check)
    css_tokens_changed = build_css_tokens(args.check)
    changed = readme_changed or docs_index_changed or css_tokens_changed
    if args.check and changed:
        print("Generated documentation is stale. Run `python scripts/build_docs.py --check` locally.")
        print("If it reports drift, run `python scripts/build_docs.py` and commit the updated files.")
        print("CSS tokens specifically can be refreshed with `python scripts/generateCssTokens.py`.")
        return 1
    print("Documentation is up to date." if not changed else "Documentation regenerated.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
