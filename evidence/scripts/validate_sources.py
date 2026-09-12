#!/usr/bin/env python3
"""URL-health validator for the Gaia evidence data lake (#1786).

Coexistence shim: the evidence lake is type-first (`evidence/by-type/*.md`),
with legacy `evidence/tier_*.md` files kept only for compatibility. This
script previously globbed *only* `tier_*.md` — contradicting the type-first
contract and validating nothing an intake or a fresh curation run actually
produced under `evidence/by-type/`. It also took no path/manifest argument,
so it could never target a specific intake's candidate rows; only a bare
positional sample-size limit was supported.

Three ways to gather URLs to check:
  1. Default: scan both evidence/by-type/*.md and evidence/tier_*.md.
  2. --urls <file>: a plain text file, one URL per line (blank/`#` lines skipped).
  3. --manifest <path>: a JSON or YAML file — a bare list of URL strings, a
     list of {"url": ...} objects, or an object with a urls/candidates/
     entries/rows list of either shape.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import subprocess
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
LAKE_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))

URL_PATTERN = re.compile(r'\[.*?\]\((https?://.*?)\)')


def _lake_source_files(lake_dir: str) -> list[str]:
    """Every markdown file the type-first lake and its legacy coexistence
    tiers can hold, relative to `lake_dir`."""
    files: list[str] = []
    by_type_dir = os.path.join(lake_dir, "by-type")
    if os.path.isdir(by_type_dir):
        for fname in sorted(os.listdir(by_type_dir)):
            if fname.endswith(".md"):
                files.append(os.path.join("by-type", fname))
    for fname in sorted(os.listdir(lake_dir)):
        if fname.endswith(".md") and fname.startswith("tier_"):
            files.append(fname)
    return files


def collect_urls_from_lake(lake_dir: str) -> dict[str, list[tuple[str, int, str]]]:
    """Scan the lake for `[label](url)` occurrences.

    Returns {url: [(relative_file, line_num, skill_id), ...]}.
    """
    url_occurrences: dict[str, list[tuple[str, int, str]]] = {}
    for relpath in _lake_source_files(lake_dir):
        fpath = os.path.join(lake_dir, relpath)
        with open(fpath, "r", encoding="utf-8") as f:
            current_skill = "Unknown"
            for line_num, line in enumerate(f, 1):
                if line.startswith("## Skill:"):
                    m = re.match(r'## Skill:\s*`(.*?)`', line)
                    if m:
                        current_skill = m.group(1)
                for url in URL_PATTERN.findall(line):
                    url = url.strip()
                    url_occurrences.setdefault(url, []).append((relpath, line_num, current_skill))
    return url_occurrences


def collect_urls_from_file(path: str) -> dict[str, list[tuple[str, int, str]]]:
    """Plain text file, one URL per line. Blank lines and `#`-comments skipped."""
    url_occurrences: dict[str, list[tuple[str, int, str]]] = {}
    with open(path, encoding="utf-8") as f:
        for line_num, line in enumerate(f, 1):
            url = line.strip()
            if not url or url.startswith("#"):
                continue
            url_occurrences.setdefault(url, []).append((os.path.basename(path), line_num, "-"))
    return url_occurrences


def _load_manifest_entries(path: str) -> list[Any]:
    with open(path, encoding="utf-8") as f:
        text = f.read().strip()
    if not text:
        return []
    if path.lower().endswith((".yaml", ".yml")):
        import yaml as _yaml
        loaded = _yaml.safe_load(text)
    else:
        loaded = json.loads(text)
    if isinstance(loaded, dict):
        for key in ("urls", "candidates", "entries", "rows"):
            if isinstance(loaded.get(key), list):
                return loaded[key]
        return [loaded]
    if isinstance(loaded, list):
        return loaded
    raise ValueError("manifest must be a JSON/YAML object, array, or {urls|candidates|entries|rows: [...]}")


def collect_urls_from_manifest(path: str) -> dict[str, list[tuple[str, int, str]]]:
    """A candidate manifest (JSON or YAML) — see module docstring for shapes."""
    url_occurrences: dict[str, list[tuple[str, int, str]]] = {}
    for i, entry in enumerate(_load_manifest_entries(path), 1):
        if isinstance(entry, str):
            url, skill_id = entry, "-"
        elif isinstance(entry, dict):
            url = entry.get("url") or entry.get("source")
            skill_id = entry.get("id") or entry.get("skillId") or "-"
        else:
            continue
        if not url:
            continue
        url_occurrences.setdefault(url.strip(), []).append((os.path.basename(path), i, skill_id))
    return url_occurrences


def validate_url(url: str) -> tuple[str, dict[str, Any]]:
    try:
        cmd = ["firecrawl", "scrape", url, "--json"]
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=45)
        if proc.returncode != 0:
            return url, {"status": "error", "message": f"CLI error (exit code {proc.returncode}): {proc.stderr.strip()[:150]}"}

        output = proc.stdout.strip()
        json_start = output.find('{')
        if json_start == -1:
            return url, {"status": "error", "message": f"No JSON in output: {output[:150]}"}

        try:
            data = json.loads(output[json_start:])
        except json.JSONDecodeError as je:
            return url, {"status": "error", "message": f"JSON decode error: {str(je)} output: {output[:100]}"}

        status_code = data.get("statusCode", 200)
        error = data.get("error")

        if status_code == 404 or error == "Not Found":
            return url, {"status": "broken", "statusCode": status_code, "error": error or "Not Found"}
        return url, {"status": "ok", "statusCode": status_code}

    except Exception as e:
        return url, {"status": "error", "message": str(e)}


def write_report(report_path: str, unique_urls: list[str], url_occurrences: dict, results: dict) -> None:
    os.makedirs(os.path.dirname(report_path) or ".", exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write("# Data Lake Source Validation Report\n\n")
        f.write(f"Validated {len(unique_urls)} URLs using Firecrawl.\n\n")

        f.write("## Broken Links\n\n")
        f.write("| Skill ID | File | Line | URL | Status |\n")
        f.write("| --- | --- | --- | --- | --- |\n")
        broken_count = 0
        for url, res in sorted(results.items()):
            if res["status"] == "broken":
                broken_count += 1
                for fname, line_num, skill_id in url_occurrences[url]:
                    f.write(f"| `{skill_id}` | `{fname}` | {line_num} | {url} | {res.get('statusCode')} {res.get('error')} |\n")
        f.write(f"\nTotal broken links: {broken_count}\n\n")

        f.write("## Validation Errors (CLI/API Issues)\n\n")
        f.write("| URL | Error Message |\n")
        f.write("| --- | --- |\n")
        err_count = 0
        for url, res in sorted(results.items()):
            if res["status"] == "error":
                err_count += 1
                f.write(f"| {url} | {res.get('message')} |\n")
        f.write(f"\nTotal validation errors: {err_count}\n\n")

        f.write("## Valid Links\n\n")
        f.write("| URL | Status |\n")
        f.write("| --- | --- |\n")
        for url, res in sorted(results.items()):
            if res["status"] == "ok":
                f.write(f"| {url} | {res.get('statusCode')} |\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--urls", help="Plain text file, one URL per line, to validate instead of scanning the lake.")
    parser.add_argument("--manifest", help="JSON or YAML candidate manifest to validate instead of scanning the lake.")
    parser.add_argument("--limit", type=int, default=None, help="Validate only the first N URLs (deterministic sample for a quick test).")
    parser.add_argument("--report", default=None, help="Path to write the validation report (default: <lake>/data_lake_validation_report.md).")
    parser.add_argument("legacy_limit", nargs="?", default=None, help=argparse.SUPPRESS)  # back-compat: bare positional int limit
    args = parser.parse_args(argv)

    if args.urls and args.manifest:
        parser.error("--urls and --manifest are mutually exclusive")

    if args.urls:
        print(f"Validating URLs from {args.urls}...")
        url_occurrences = collect_urls_from_file(args.urls)
    elif args.manifest:
        print(f"Validating URLs from manifest {args.manifest}...")
        url_occurrences = collect_urls_from_manifest(args.manifest)
    else:
        print(f"Scanning evidence lake at {LAKE_DIR} (by-type/ + legacy tier_*.md)...")
        url_occurrences = collect_urls_from_lake(LAKE_DIR)

    limit = args.limit
    if limit is None and args.legacy_limit is not None:
        try:
            limit = int(args.legacy_limit)
        except ValueError:
            pass

    unique_urls = sorted(url_occurrences.keys())
    print(f"Total unique URLs found: {len(unique_urls)}")
    if limit is not None:
        print(f"Limiting validation to first {limit} URLs for testing.")
        unique_urls = unique_urls[:limit]

    results: dict[str, dict[str, Any]] = {}
    print("Starting validation using Firecrawl (concurrency=2)...")
    completed = 0
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = {executor.submit(validate_url, url): url for url in unique_urls}
        for future in as_completed(futures):
            url = futures[future]
            try:
                url, res = future.result()
                results[url] = res
                completed += 1
                if res["status"] == "broken":
                    print(f"[{completed}/{len(unique_urls)}] ❌ BROKEN: {url} -> {res.get('statusCode')} {res.get('error')}")
                elif res["status"] == "error":
                    print(f"[{completed}/{len(unique_urls)}] ⚠ ERROR: {url} -> {res.get('message')}")
                else:
                    print(f"[{completed}/{len(unique_urls)}] ✓ OK: {url}")
            except Exception as e:
                completed += 1
                print(f"[{completed}/{len(unique_urls)}] \U0001f4a5 EXCEPTION: {url} -> {str(e)}")

    report_path = args.report or os.path.join(LAKE_DIR, "data_lake_validation_report.md")
    write_report(report_path, unique_urls, url_occurrences, results)
    print(f"\nValidation complete. Report written to {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
