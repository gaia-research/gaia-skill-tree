#!/usr/bin/env python3
"""
check_html_sinks.py — fast pre-CodeQL guard for unsafe HTML sinks

Flags the exact string-building-into-an-HTML-sink pattern that produced 6 of
the 8 CodeQL "DOM text reinterpreted as HTML" alerts on PR #1185. This is a
cheap, dataflow-free grep guard: it runs in well under a second and gives
authors instant feedback in review, BEFORE the slower CodeQL scan lands.

  It is deliberately NOT a replacement for CodeQL. CodeQL does real source->sink
  taint tracking across functions; this guard only pattern-matches the sink
  line itself. The two are belt-and-suspenders: this catches the common,
  unambiguous cases fast; CodeQL remains the backstop for cross-function flows.

==============================================================================
POSTURE: WARN-ONLY by default (see HARD_FAIL).

The repo has ~260 pre-existing `.innerHTML =` assignments across 20+ files;
most are safe (clearing to '', static literals) but ~14 interpolate runtime
values. Hard-failing all of them on day one would red-build staging for work
outside this guard's introducing PR. So the guard ships WARN-ONLY: it surfaces
the dangerous class and offers an audited-suppression marker, acting as a
ratchet. Flip HARD_FAIL=True once the interpolating sites are driven to zero
(each either converted to a DOM API or annotated with an OK marker below).
==============================================================================

WHAT IT FLAGS  (the unambiguously-dangerous sink patterns)
  - `x.innerHTML  = `...${expr}...`` — template literal with interpolation.
  - `x.outerHTML  = `...${expr}...``
  - `x.innerHTML  = '...' + expr`    — string concatenation into the sink.
  - `el.insertAdjacentHTML(pos, `...${expr}...`)` / concatenation form.
  - `document.write(` / `document.writeln(` with interpolation/concatenation.

WHAT IT DELIBERATELY DOES NOT FLAG  (safe or needs-dataflow)
  - `x.innerHTML = ''` / `= ""`            — clearing a node (always safe).
  - `x.innerHTML = '<static markup>'`      — a single string literal with no
    concatenation and no `${}` (author-controlled constant markup).
  - `x.innerHTML = someVar;`               — a bare identifier. Whether `someVar`
    is tainted is a DATAFLOW question this guard can't answer; that's CodeQL's
    job. Flagging it here would be pure false-positive noise.
  - reads: `const h = x.innerHTML;`        — only assignments to the sink match.
  - comment / prose lines.

SUPPRESSION  (for reviewed-safe interpolations)
  Append a trailing marker on the offending line:

      el.innerHTML = `<use href="${ICON_BASE}#copy"/>`;  // gaia-html-sink-ok: ICON_BASE is a build-time constant

  The reason after the colon is REQUIRED (a bare marker is rejected) so every
  suppression carries an in-code justification the next reader can audit.

SCAN SCOPE  (production browser surfaces only — mirrors check_taxonomy_authority)
  docs/**/*.js
  docs/**/*.html   (INCLUDING inline <script> blocks)

Force UTF-8 output on Windows (repo has cp1252 glyphs).
"""

import re
import sys
import fnmatch
from pathlib import Path

# Force UTF-8 output on Windows so unicode chars in print() don't crash.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# Posture switch — WARN-ONLY until the interpolating surface reaches zero.
# ---------------------------------------------------------------------------
HARD_FAIL = False

# Audited-safe suppression marker. The reason text after the colon is required.
SUPPRESS = re.compile(r"gaia-html-sink-ok:\s*\S")


# ---------------------------------------------------------------------------
# Sink signatures
# ---------------------------------------------------------------------------

# `.innerHTML =` / `.outerHTML =` assigned a TEMPLATE LITERAL that interpolates.
# We match the assignment opening a backtick, then require a `${` on the same
# line (single-line template — the overwhelming common case for these sinks).
TPL_INTERP = re.compile(
    r"\.(?:inner|outer)HTML\s*=\s*`[^`]*\$\{"
)

# `.innerHTML =` / `.outerHTML =` built by STRING CONCATENATION: a quoted
# fragment immediately followed by `+` (concatenating a dynamic value in).
CONCAT_ASSIGN = re.compile(
    r"\.(?:inner|outer)HTML\s*=\s*(?:['\"][^'\"]*['\"]\s*\+|[A-Za-z_$][\w$.]*\s*\+\s*['\"])"
)

# insertAdjacentHTML(position, <interpolated-or-concatenated>)
INSERT_ADJ = re.compile(
    r"\.insertAdjacentHTML\s*\([^,]+,\s*(?:`[^`]*\$\{|['\"][^'\"]*['\"]\s*\+|[A-Za-z_$][\w$.]*\s*\+)"
)

# document.write / writeln with interpolation or concatenation (not a bare
# static-literal call).
DOC_WRITE = re.compile(
    r"document\.write(?:ln)?\s*\(\s*(?:`[^`]*\$\{|['\"][^'\"]*['\"]\s*\+|[A-Za-z_$][\w$.]*\s*\+)"
)

SINK_PATTERNS = [
    (TPL_INTERP, "innerhtml-template",
     "template-literal interpolation into innerHTML/outerHTML — build via DOM "
     "API (createElement/textContent) or escape each ${} value"),
    (CONCAT_ASSIGN, "innerhtml-concat",
     "string-concatenation into innerHTML/outerHTML — build via DOM API or "
     "escape the concatenated value"),
    (INSERT_ADJ, "insertadjacent-dynamic",
     "dynamic value passed to insertAdjacentHTML — build via DOM API or escape"),
    (DOC_WRITE, "document-write-dynamic",
     "dynamic value passed to document.write — avoid document.write; build via "
     "DOM API"),
]


# ---------------------------------------------------------------------------
# Scope / exclusions
# ---------------------------------------------------------------------------

SCAN_GLOBS = [
    "docs/**/*.js",
    "docs/**/*.html",
]

EXCLUDE_GLOBS = [
    # this guard's own docstring quotes the flagged signatures.
    "scripts/check_html_sinks.py",
    # generated / vendored
    "**/__pycache__/**",
    "docs/assets/**",
    # third-party libraries shipped as-is are out of our authoring surface.
    "docs/**/vendor/**",
    "docs/**/*.min.js",
]

# Inline <script> extraction for .html files. The closing-tag pattern follows
# CodeQL's py/bad-tag-filter guidance: match `</script` then any run of
# whitespace/attribute chars before `>` (HTML lets `</script\t\n foo>` close a
# block), so a crafted end tag can't smuggle script past the guard.
SCRIPT_BLOCK = re.compile(r"<script\b[^>]*>(.*?)</script[^>]*>", re.IGNORECASE | re.DOTALL)


def isComment(line: str) -> bool:
    """JS comment line — prose mention of a sink is not a sink."""
    stripped = line.strip()
    return stripped.startswith("//") or stripped.startswith("*") or stripped.startswith("/*")


def isExcluded(relPath: str) -> bool:
    norm = relPath.replace("\\", "/")
    for pattern in EXCLUDE_GLOBS:
        if fnmatch.fnmatch(norm, pattern):
            return True
    return False


def collectFiles(repoRoot: Path):
    seen = set()
    for globPattern in SCAN_GLOBS:
        for p in repoRoot.glob(globPattern):
            if not p.is_file():
                continue
            rel = p.relative_to(repoRoot).as_posix()
            if rel in seen or isExcluded(rel):
                continue
            seen.add(rel)
            yield p, rel


def scanLine(line: str):
    """Yield (label, rationale) for each sink signature the line trips, unless
    the line carries an audited-safe suppression marker."""
    if isComment(line):
        return
    if SUPPRESS.search(line):
        return
    for pattern, label, rationale in SINK_PATTERNS:
        if pattern.search(line):
            yield label, rationale


def scanText(text: str, isHtml: bool):
    """Yield (lineno, snippet, label, rationale). For HTML, scan only inline
    <script> blocks; line numbers stay relative to the whole file."""
    if isHtml:
        for m in SCRIPT_BLOCK.finditer(text):
            startLine = text.count("\n", 0, m.start(1)) + 1
            block = m.group(1)
            for offset, line in enumerate(block.splitlines()):
                for label, rationale in scanLine(line):
                    yield startLine + offset, line.strip()[:120], label, rationale
    else:
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, rationale in scanLine(line):
                yield lineno, line.strip()[:120], label, rationale


def scan(repoRoot: Path):
    findings = []  # (rel, lineno, snippet, label, rationale)
    for filePath, rel in collectFiles(repoRoot):
        try:
            text = filePath.read_text(encoding="utf-8", errors="replace")
        except (OSError, PermissionError) as exc:
            print(f"  [SKIP] {rel}: {exc}", file=sys.stderr)
            continue
        isHtml = rel.lower().endswith(".html")
        for lineno, snippet, label, rationale in scanText(text, isHtml):
            findings.append((rel, lineno, snippet, label, rationale))
    return findings


def selftest():
    """Classifier contract check (run via `--selftest` in CI). Safe forms must
    NOT flag; interpolated/concatenated sinks MUST flag; suppression needs a
    reason. Returns 0 on pass, 1 on any mismatch."""
    safe = [
        "x.innerHTML = '';",
        'x.innerHTML = "";',
        "x.innerHTML = '<span class=\"static\">hello</span>';",
        "const h = el.innerHTML;",
        "el.innerHTML = someVar;",  # bare identifier — dataflow, CodeQL's job
        "// el.innerHTML = `${x}`",  # comment
        "el.innerHTML = `<i>${x}</i>`;  // gaia-html-sink-ok: x is a fixed enum",
    ]
    unsafe = [
        "el.innerHTML = `<b>${name}</b>`;",
        "el.outerHTML = `<b>${name}</b>`;",
        "el.innerHTML = '<b>' + name + '</b>';",
        "el.insertAdjacentHTML('beforeend', `<i>${x}</i>`);",
        "document.write('<p>' + x + '</p>');",
        "el.innerHTML = `<use href=\"#${x}\"/>`;",
        "el.innerHTML = `<b>${x}</b>`;  // gaia-html-sink-ok:",  # bare marker, no reason
    ]
    bad = 0
    for line in safe:
        if list(scanLine(line)):
            print(f"  SELFTEST FAIL (false positive): {line}")
            bad += 1
    for line in unsafe:
        if not list(scanLine(line)):
            print(f"  SELFTEST FAIL (missed sink): {line}")
            bad += 1
    if bad:
        print(f"SELFTEST: FAIL ({bad} mismatch(es))")
        return 1
    print(f"SELFTEST: PASS ({len(safe) + len(unsafe)} cases)")
    return 0


def main():
    repoRoot = Path(__file__).resolve().parent.parent

    if "--selftest" in sys.argv:
        return selftest()

    print("=== HTML-Sink Guard  (pre-CodeQL, DOM-XSS pattern) ===")
    print(f"Repo root : {repoRoot}")
    print("Flags     : interpolated/concatenated innerHTML/outerHTML/insertAdjacentHTML/document.write")
    print("Fix       : build via DOM API (createElement/textContent) or escape each dynamic value")
    print(f"Mode      : {'HARD-FAIL' if HARD_FAIL else 'WARN-ONLY'}")
    print("Suppress  : trailing `// gaia-html-sink-ok: <reason>` on the sink line")
    print()

    findings = scan(repoRoot)

    if findings:
        byFile = {}
        for entry in findings:
            byFile.setdefault(entry[0], []).append(entry)
        severity = "FAIL" if HARD_FAIL else "WARN"
        print(f"-- UNSAFE HTML SINKS ({len(findings)} hit(s) across {len(byFile)} file(s)) --")
        for path, entries in sorted(byFile.items()):
            print(f"  [{severity}] {path}  ({len(entries)} hit(s))")
            for _rel, lineno, snippet, label, rationale in entries:
                print(f"      L{lineno} [{label}] {snippet}")
                print(f"        -> {rationale}")
        print()
        if HARD_FAIL:
            print(f"RESULT: FAIL — {len(findings)} unsafe sink(s); convert to DOM API, escape, or suppress with reason")
            return 1
        print(f"RESULT: PASS (warn-only) — {len(findings)} unsafe sink(s) tracked; flip HARD_FAIL once at zero")
        return 0

    print("RESULT: PASS — 0 unsafe HTML sinks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
