#!/usr/bin/env python3
"""Deterministic collector-append script for the Gaia evidence pipeline.

Replaces freehand agent writes to the evidence collector markdown files with a
deterministic, append-only, URL-deduplicated pass. Reads a JSON array of new
evidence rows and appends each to the correct collector file based on its
``evidenceType``.

Routing:
  benchmark-result           -> evidence/collectors/technical/benchmark_results.md
  arxiv, peer-review         -> evidence/collectors/technical/academic_papers.md
  social-signal (blog)       -> evidence/collectors/social/blogs_newsletters.md
  social-signal (youtube)    -> evidence/collectors/social/youtube_showcases.md

Behaviour:
  * Append only. Existing rows are never modified, reordered, or reformatted.
  * Dedup by URL: a row whose URL already appears anywhere in the target file
    is skipped.
  * Each run's appended rows are grouped under a single
    ``<!-- appended: YYYY-MM-DD -->`` comment on its own line.
  * Section numbering continues the file's existing ``## N.`` / ``### N.``
    detailed-section sequence.
  * --dry-run prints what would be appended without writing.

Usage:
  python3 scripts/ev_append.py --input rows.json [--dry-run]

Input JSON schema (array of objects):
  {
    "skillId": "ux-audit",
    "namedSlug": "nextlevelbuilder/ux-audit",
    "evidenceType": "arxiv",
    "url": "https://arxiv.org/abs/2605.03353",
    "title": "SkCC: ...",
    "notes": "First academic citation for the repo",
    "grade": "B",
    "isNew": true
  }
"""

import argparse
import json
import os
import re
import sys

REPOROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

BENCHMARKPATH = os.path.join(
    REPOROOT, "evidence", "collectors", "technical", "benchmark_results.md"
)
ACADEMICPATH = os.path.join(
    REPOROOT, "evidence", "collectors", "technical", "academic_papers.md"
)
BLOGSPATH = os.path.join(
    REPOROOT, "evidence", "collectors", "social", "blogs_newsletters.md"
)
YOUTUBEPATH = os.path.join(
    REPOROOT, "evidence", "collectors", "social", "youtube_showcases.md"
)

# Files that use "### N." detailed section headers vs "## N." headers.
HASHHASHHASH = {BENCHMARKPATH, ACADEMICPATH}


def isyoutube(url):
    """True when the URL points at YouTube."""
    lowered = (url or "").lower()
    return "youtube.com" in lowered or "youtu.be" in lowered


def targetfor(row):
    """Resolve the destination collector file for an evidence row."""
    etype = (row.get("evidenceType") or "").strip().lower()
    if etype == "benchmark-result":
        return BENCHMARKPATH
    if etype in ("arxiv", "peer-review"):
        return ACADEMICPATH
    if etype == "social-signal":
        if isyoutube(row.get("url", "")):
            return YOUTUBEPATH
        return BLOGSPATH
    return None


def readfile(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def urlpresent(text, url):
    """True when the exact URL string already appears in the file text."""
    if not url:
        return False
    return url in text


def nextsectionnumber(text):
    """Highest existing '## N.' / '### N.' section number, plus one."""
    numbers = [int(match) for match in re.findall(r"(?m)^#{2,3}\s+(\d+)\.", text)]
    if not numbers:
        return 1
    return max(numbers) + 1


def displaylabel(row):
    """Human label for a section header — namedSlug, else skillId."""
    return row.get("namedSlug") or row.get("skillId") or "unknown"


def renderbenchmark(number, row):
    label = displaylabel(row)
    lines = [f"### {number}. `{label}`"]
    lines.append(f"* **Benchmark URL:** [{row.get('title', row['url'])}]({row['url']})")
    if row.get("title"):
        lines.append(f"* **Benchmark:** {row['title']}")
    if row.get("grade"):
        lines.append(f"* **Grade:** {row['grade']}")
    if row.get("notes"):
        lines.append(f"* **Setup Description:** {row['notes']}")
    return "\n".join(lines)


def renderacademic(number, row):
    label = displaylabel(row)
    lines = [f"### {number}. `{label}`"]
    if row.get("title"):
        lines.append(f"* **Paper Title:** {row['title']}")
    lines.append(f"* **Publication URL:** [{row['url']}]({row['url']})")
    if row.get("evidenceType"):
        lines.append(f"* **Evidence Type:** {row['evidenceType']}")
    if row.get("grade"):
        lines.append(f"* **Grade:** {row['grade']}")
    if row.get("notes"):
        lines.append(f"* **Summary & Relevance:** {row['notes']}")
    return "\n".join(lines)


def renderblog(number, row):
    label = displaylabel(row)
    title = row.get("title") or row["url"]
    lines = [f"## {number}. `{label}` — {title}"]
    lines.append(f"*   **Article URL:** [{row['url']}]({row['url']})")
    if row.get("grade"):
        lines.append(f"*   **Grade:** {row['grade']}")
    if row.get("notes"):
        lines.append(f"*   **Description:** {row['notes']}")
    return "\n".join(lines)


def renderyoutube(number, row):
    label = displaylabel(row)
    title = row.get("title") or row["url"]
    lines = [f"## {number}. `{label}` — {title}"]
    lines.append(f"*   **Video Title:** [{title}]({row['url']})")
    lines.append(f"*   **Video URL:** `{row['url']}`")
    if row.get("grade"):
        lines.append(f"*   **Grade:** {row['grade']}")
    if row.get("notes"):
        lines.append(f"*   **Description:** {row['notes']}")
    return "\n".join(lines)


RENDERERS = {
    BENCHMARKPATH: renderbenchmark,
    ACADEMICPATH: renderacademic,
    BLOGSPATH: renderblog,
    YOUTUBEPATH: renderyoutube,
}


def buildblock(path, existingtext, rows, datestamp):
    """Render the appended block (date-stamp + numbered sections) for one file.

    Returns (blocktext, appendedcount). Section numbering starts from the
    file's current highest section number and advances per rendered row.
    """
    renderer = RENDERERS[path]
    number = nextsectionnumber(existingtext)
    chunks = []
    for row in rows:
        chunks.append(renderer(number, row))
        number += 1
    if not chunks:
        return "", 0
    body = "\n\n---\n\n".join(chunks)
    block = f"\n---\n\n<!-- appended: {datestamp} -->\n\n{body}\n"
    return block, len(chunks)


def loadrows(inputpath):
    with open(inputpath, "r", encoding="utf-8") as handle:
        data = json.load(handle)
    if not isinstance(data, list):
        raise ValueError("Input JSON must be an array of evidence rows.")
    return data


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, help="Path to rows JSON file.")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        dest="dryrun",
        help="Print what would be appended without writing.",
    )
    parser.add_argument(
        "--date",
        default=None,
        help="Date stamp (YYYY-MM-DD) for the appended block. "
        "Defaults to today (UTC).",
    )
    args = parser.parse_args(argv)

    if args.date:
        datestamp = args.date
    else:
        import datetime

        datestamp = datetime.datetime.utcnow().strftime("%Y-%m-%d")

    rows = loadrows(args.input)

    # Group rows by target file, dedup by URL against the file's current text.
    buckets = {}
    skipped = {}
    unrouted = []
    filetexts = {}
    seenurls = {}

    for row in rows:
        url = (row.get("url") or "").strip()
        path = targetfor(row)
        if path is None:
            unrouted.append(row)
            continue
        if path not in filetexts:
            filetexts[path] = readfile(path)
            skipped[path] = 0
            buckets[path] = []
            seenurls[path] = set()
        # Dedup against both existing file content and rows already queued
        # this run (guards against duplicate URLs within the input itself).
        if urlpresent(filetexts[path], url) or url in seenurls[path]:
            skipped[path] += 1
            continue
        seenurls[path].add(url)
        buckets[path].append(row)

    summary = []
    for path in sorted(buckets):
        block, count = buildblock(path, filetexts[path], buckets[path], datestamp)
        rel = os.path.relpath(path, REPOROOT)
        summary.append((rel, count, skipped.get(path, 0)))
        if count == 0:
            continue
        if args.dryrun:
            print(f"--- would append to {rel} ---")
            print(block)
        else:
            with open(path, "a", encoding="utf-8") as handle:
                handle.write(block)

    # Report files touched only by dedup skips (no new rows).
    for path in sorted(skipped):
        if path not in buckets or not buckets[path]:
            rel = os.path.relpath(path, REPOROOT)
            if not any(entry[0] == rel for entry in summary):
                summary.append((rel, 0, skipped[path]))

    print("\n=== ev_append summary%s ===" % (" (dry-run)" if args.dryrun else ""))
    for rel, count, skip in sorted(summary):
        print(f"  {rel}: {count} appended, {skip} skipped (duplicate URL)")
    if unrouted:
        print(f"  UNROUTED (unknown evidenceType): {len(unrouted)} row(s)")
        for row in unrouted:
            print(
                f"    - {row.get('skillId', '?')} / "
                f"{row.get('evidenceType', '?')} / {row.get('url', '?')}"
            )
    if not summary and not unrouted:
        print("  (no rows in input)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
