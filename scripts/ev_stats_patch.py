#!/usr/bin/env python3
"""Deterministic stats-patch script for evidence/verification_process.html.

Replaces the manual, by-eye patching of the stats block and pipeline run
history with a deterministic in-place edit. It:

  * increments the four cumulative stat-card values in the ``.stats-grid``
    block (Unique URLs Audited, Verified Links, Validation Timeout / broken,
    Broken Links) by this run's live/dead URL counts;
  * updates the ``<!-- Last updated: ... -->`` comment above the block;
  * appends (or updates, if the date already exists) a per-run row in the
    Pipeline Run History table.

The stats block is located by the ``<!-- Stats Block -->`` marker. If that
marker is absent the script inserts one immediately above the ``.stats-grid``
div and reports where it placed it.

No CSS, layout, or structural HTML changes are made — only the numeric text
inside existing stat-value divs, the run-history table body, and the
last-updated comment.

Usage:
  python3 scripts/ev_stats_patch.py --date 2026-07-30 \\
      --skills-processed 11 --new-rows 47 --live-urls 53 --dead-urls 0 \\
      [--dry-run]
"""

import argparse
import difflib
import os
import re
import sys

REPOROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HTMLPATH = os.path.join(REPOROOT, "evidence", "verification_process.html")

STATSMARKER = "<!-- Stats Block -->"


def readfile(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def ensuremarker(text):
    """Ensure the '<!-- Stats Block -->' marker precedes the .stats-grid div.

    Returns (text, added) where ``added`` is True when a marker was inserted.
    """
    if STATSMARKER in text:
        return text, False
    pattern = re.compile(r'(?m)^([ \t]*)<div class="stats-grid">')
    match = pattern.search(text)
    if not match:
        raise SystemExit(
            "Could not find a .stats-grid div to anchor the stats block marker."
        )
    indent = match.group(1)
    insertion = f"{indent}{STATSMARKER}\n"
    start = match.start()
    text = text[:start] + insertion + text[start:]
    return text, True


def patchstatcards(text, liveurls, deadurls):
    """Increment the four cumulative stat-card values by this run's counts.

    Card order in the .stats-grid block:
      1. Unique URLs Audited      += (live + dead)
      2. Verified Links (200 OK)  += live
      3. Validation Timeout       (unchanged — timeouts aren't a CLI input)
      4. Broken Links (404)       += dead
    """
    gridmatch = re.search(
        r'(<div class="stats-grid">)(.*?)(</div>\s*</div>)',
        text,
        flags=re.DOTALL,
    )
    if not gridmatch:
        # Fall back to matching just the grid open/close at the same depth.
        gridmatch = re.search(
            r'(<div class="stats-grid">)(.*?)(\n\s*</div>)',
            text,
            flags=re.DOTALL,
        )
    if not gridmatch:
        raise SystemExit("Could not locate the .stats-grid block to patch.")

    block = gridmatch.group(0)
    values = re.findall(r'<div class="stat-value">(\d+)</div>', block)
    if len(values) < 4:
        raise SystemExit(
            f"Expected at least 4 stat-value entries, found {len(values)}."
        )

    current = [int(value) for value in values[:4]]
    deltas = [liveurls + deadurls, liveurls, 0, deadurls]
    updated = [current[index] + deltas[index] for index in range(4)]

    newblock = block
    for index in range(4):
        oldsnippet = f'<div class="stat-value">{current[index]}</div>'
        newsnippet = f'<div class="stat-value">{updated[index]}</div>'
        # Replace one occurrence at a time, left to right.
        newblock = newblock.replace(oldsnippet, newsnippet, 1)

    text = text[: gridmatch.start()] + newblock + text[gridmatch.end():]
    return text, current, updated


def patchlastupdated(text, date, skillsprocessed, liveurls):
    """Update or insert the '<!-- Last updated: ... -->' comment."""
    comment = (
        f"<!-- Last updated: {date} (intake seed pipeline, "
        f"{skillsprocessed} skills, {liveurls} URLs) -->"
    )
    pattern = re.compile(r"<!-- Last updated:.*?-->")
    if pattern.search(text):
        return pattern.sub(comment, text, count=1)
    # Insert directly after the stats-block marker.
    return text.replace(STATSMARKER, f"{STATSMARKER}\n    {comment}", 1)


def buildrunrow(date, description, skills, urls, dead):
    """Render one Pipeline Run History <tr>, matching existing row styling."""
    return (
        '          <tr>\n'
        '            <td style="padding: 0.35rem 0.75rem 0.35rem 0; '
        f'color: var(--muted);">{date}</td>\n'
        '            <td style="padding: 0.35rem 0.75rem; '
        f'color: var(--text);">{description}</td>\n'
        '            <td style="padding: 0.35rem 0 0.35rem 0.75rem; '
        f'text-align: right; color: var(--text);">{skills}</td>\n'
        '            <td style="padding: 0.35rem 0 0.35rem 0.75rem; '
        f'text-align: right; color: var(--text);">{urls}</td>\n'
        '            <td style="padding: 0.35rem 0 0.35rem 0.75rem; '
        f'text-align: right; color: var(--tier-basic);">{dead}</td>\n'
        '          </tr>'
    )


def patchrunhistory(text, date, description, skills, urls, dead):
    """Append a run-history row, or leave the table unchanged if the date row
    already exists (idempotent)."""
    tbodymatch = re.search(
        r"(<tbody>)(.*?)(</tbody>)", text, flags=re.DOTALL
    )
    if not tbodymatch:
        raise SystemExit("Could not locate the run-history <tbody>.")
    body = tbodymatch.group(2)
    if re.search(
        r">%s<" % re.escape(date), body
    ):
        # A row for this date already exists — idempotent no-op.
        return text, False
    row = buildrunrow(date, description, skills, urls, dead)
    newbody = body.rstrip("\n") + "\n" + row + "\n        "
    newtbody = tbodymatch.group(1) + newbody + tbodymatch.group(3)
    text = text[: tbodymatch.start()] + newtbody + text[tbodymatch.end():]
    return text, True


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--date", required=True, help="Run date, YYYY-MM-DD.")
    parser.add_argument(
        "--skills-processed", type=int, required=True, dest="skillsprocessed"
    )
    parser.add_argument("--new-rows", type=int, required=True, dest="newrows")
    parser.add_argument("--live-urls", type=int, required=True, dest="liveurls")
    parser.add_argument("--dead-urls", type=int, required=True, dest="deadurls")
    parser.add_argument(
        "--description",
        default=None,
        help="Run-history description. Defaults to a standard intake summary.",
    )
    parser.add_argument(
        "--dry-run", action="store_true", dest="dryrun",
        help="Print a unified diff without writing.",
    )
    args = parser.parse_args(argv)

    original = readfile(HTMLPATH)
    text = original

    text, markeradded = ensuremarker(text)
    if markeradded:
        print(
            f"NOTE: inserted '{STATSMARKER}' above the .stats-grid div "
            "(no marker was present)."
        )

    text = patchlastupdated(text, args.date, args.skillsprocessed, args.liveurls)
    text, cardsbefore, cardsafter = patchstatcards(
        text, args.liveurls, args.deadurls
    )

    description = args.description or (
        f"Intake seed pipeline — {args.skillsprocessed} skills, "
        f"{args.newrows} new evidence rows"
    )
    text, rowadded = patchrunhistory(
        text,
        args.date,
        description,
        args.skillsprocessed,
        args.liveurls,
        args.deadurls,
    )

    print("=== stat-card values ===")
    labels = [
        "Unique URLs Audited",
        "Verified Links (200 OK)",
        "Validation Timeout",
        "Broken Links (404)",
    ]
    for index in range(4):
        print(
            f"  {labels[index]}: {cardsbefore[index]} -> {cardsafter[index]}"
        )
    print(
        f"=== run-history row ({args.date}): "
        f"{'added' if rowadded else 'already present (no-op)'} ==="
    )

    if args.dryrun:
        diff = difflib.unified_diff(
            original.splitlines(keepends=True),
            text.splitlines(keepends=True),
            fromfile="verification_process.html (before)",
            tofile="verification_process.html (after)",
        )
        sys.stdout.writelines(diff)
        print("\n(dry-run — no file written)")
        return 0

    if text != original:
        with open(HTMLPATH, "w", encoding="utf-8") as handle:
            handle.write(text)
        print(f"Wrote {os.path.relpath(HTMLPATH, REPOROOT)}")
    else:
        print("No changes needed (file already up to date).")
    return 0


if __name__ == "__main__":
    sys.exit(main())
