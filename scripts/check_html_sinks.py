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
POSTURE: HARD-FAIL for new sinks, with counted baseline debt.

html_sinks_baseline.json carries pre-existing sinks by repository-relative path
and label. Only that budget is allowed; every additional sink fails the guard.
Shrink the baseline as sites migrate to DOM APIs or audited markers; never grow
it. A missing or empty baseline hard-fails on every unsafe sink.
Use --baseline <path> to select a baseline, or --dump-baseline to inspect the
current findings as JSON (review only; do not grow the committed baseline).
Use --check-baseline-growth to also reject budget increases against the Git
merge-base with GITHUB_BASE_REF or origin/main (override with --base-ref, e.g.
HEAD~1). A missing baseline at that revision uses a dynamic scan of the base
commit as its budget; unavailable Git history fails in GitHub Actions, or warns
and skips the growth comparison locally.
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

import argparse
import json
import os
import re
import subprocess
import sys
import fnmatch
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

# Force UTF-8 output on Windows so unicode chars in print() don't crash.
if sys.stdout.encoding and sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
if sys.stderr.encoding and sys.stderr.encoding.lower() not in ("utf-8", "utf8"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# New sinks always hard-fail, including when no baseline is available.
# ---------------------------------------------------------------------------
HARD_FAIL = True
DEFAULT_BASELINE = Path(__file__).resolve().parent / "html_sinks_baseline.json"
BASELINE_ABOUT = (
    "Known HTML sink debt at the time the ratchet landed. Every entry is a "
    "pre-existing sink tracked so new sinks can be hard-blocked immediately. "
    "Shrink this file as sinks are migrated to DOM APIs or annotated; never grow it."
)

# Audited-safe suppression marker. The reason text after the colon is required.
SUPPRESS = re.compile(
    r"(?://\s*gaia-html-sink-ok:\s*(\S[^\n\r]*)$|/\*\s*gaia-html-sink-ok:\s*(\S.*?)\s*\*/\s*$)"
)


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
SCRIPT_BLOCK = re.compile(r"<script\b[^>]*>(.*?)</script\s*[^>]*>", re.IGNORECASE | re.DOTALL)
REGEX_LITERAL_PATTERN = re.compile(
    r"^/(?:\[(?:\\.|[^\]\n\\])*\]|\\.|[^/\n\\\[])+/[a-z]*"
)


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


@dataclass
class LexicalState:
    stack: list[str] = field(default_factory=lambda: ["NORMAL"])
    regex_allowed: bool = True
    control_parens: list[bool] = field(default_factory=list)
    brace_stack: list[str] = field(default_factory=list)
    previous_token: str = ""
    # Bounded token context survives newlines for labels and class headers.
    statement_tokens: list[str] = field(default_factory=list)


def extract_trailing_comment(line: str, lexical_state: LexicalState | None = None) -> str | None:
    """Find a trailing JS comment outside literals and template expressions.

    Preserve token context as well as nesting across lines. This is not a full
    JS parser; comments in template expressions cannot authorize suppression.
    """
    lexical_state = lexical_state if lexical_state is not None else LexicalState()
    states = lexical_state.stack
    i = 0
    regexKeywords = {
        "return", "yield", "typeof", "delete", "void", "throw", "instanceof",
        "in", "of", "new", "await", "case", "default", "else", "do",
    }
    controlKeywords = {"if", "while", "for", "with", "switch", "catch"}
    while i < len(line):
        state = states[-1]
        char = line[i]
        if state == "BLOCK_COMMENT":
            end = line.find("*/", i)
            if end == -1:
                return None
            states.pop()
            i = end + 2
            continue
        if state in ("SINGLE_QUOTE", "DOUBLE_QUOTE", "TEMPLATE_LITERAL"):
            if char == "\\":
                i += 2
                continue
            if state == "TEMPLATE_LITERAL" and line.startswith("${", i):
                states.append("TEMPLATE_EXPR")
                lexical_state.regex_allowed = True
                lexical_state.previous_token = ""
                i += 2
                continue
            delimiter = {"SINGLE_QUOTE": "'", "DOUBLE_QUOTE": '"',
                         "TEMPLATE_LITERAL": "`"}[state]
            if char == delimiter:
                states.pop()
                lexical_state.regex_allowed = False
                lexical_state.previous_token = delimiter
        elif char in "'\"`":
            states.append({"'": "SINGLE_QUOTE", '"': "DOUBLE_QUOTE",
                           "`": "TEMPLATE_LITERAL"}[char])
        elif line.startswith("//", i):
            # A line comment in an expression consumes the rest of this line,
            # not a trailing comment in the outer NORMAL state.
            return line[i:] if states == ["NORMAL"] else None
        elif line.startswith("/*", i):
            end = line.find("*/", i + 2)
            if end == -1:
                states.append("BLOCK_COMMENT")
                return None
            if states == ["NORMAL"] and not line[end + 2:].strip():
                return line[i:]
            i = end + 2
            continue
        elif char == "/":
            # Only expression-start contexts permit a regex. In particular,
            # division must not consume a later trailing-comment delimiter.
            match = REGEX_LITERAL_PATTERN.match(line[i:]) if lexical_state.regex_allowed else None
            if match:
                i += match.end()
                lexical_state.regex_allowed = False
                lexical_state.previous_token = "regex"
                continue
            lexical_state.regex_allowed = True  # division's right operand starts here
            lexical_state.previous_token = char
        elif char.isspace():
            pass
        elif char.isalpha() or char in "_$" or char.isdigit():
            end = i + 1
            while end < len(line) and (line[end].isalnum() or line[end] in "_$"):
                end += 1
            token = line[i:end]
            lexical_state.regex_allowed = token in regexKeywords and lexical_state.previous_token != "."
            lexical_state.previous_token = token
            lexical_state.statement_tokens = (lexical_state.statement_tokens + [token])[-16:]
            i = end
            continue
        else:
            if char == "(":
                lexical_state.control_parens.append(lexical_state.previous_token in controlKeywords)
                lexical_state.regex_allowed = True
            elif char == ")":
                # A control header ends at a statement, unlike a call/group.
                lexical_state.regex_allowed = lexical_state.control_parens.pop() if lexical_state.control_parens else False
            elif char == "{":
                # Statement starts (including control headers) open blocks;
                # assignment/argument/return contexts instead open objects.
                prefix = " ".join(lexical_state.statement_tokens)
                identifier = r"[A-Za-z_$][\w$]*"
                label = (re.fullmatch(rf"{identifier} :", prefix) is not None
                         and (not lexical_state.brace_stack
                              or lexical_state.brace_stack[-1] == "BLOCK"))
                classHeader = re.search(
                    rf"(?:^| )class(?: {identifier})?(?: extends {identifier})?$", prefix
                ) is not None
                kind = "BLOCK" if label or classHeader or lexical_state.previous_token in {
                    "", ";", "{", "}", ")", "else", "do", "try", "finally",
                } else "OBJECT"
                # An interpolation starts with an expression, not a statement.
                if state == "TEMPLATE_EXPR" and lexical_state.previous_token == "":
                    kind = "OBJECT"
                lexical_state.brace_stack.append(kind)
                lexical_state.regex_allowed = True
            elif char == "}":
                # The interpolation delimiter itself has no brace-stack entry.
                interpolation_end = state == "TEMPLATE_EXPR" and (
                    len(states) < 2 or states[-2] == "TEMPLATE_LITERAL"
                )
                kind = (lexical_state.brace_stack.pop()
                        if lexical_state.brace_stack and not interpolation_end else "OBJECT")
                lexical_state.regex_allowed = kind == "BLOCK"
            elif line[i:i + 2] in ("++", "--"):
                lexical_state.previous_token = line[i:i + 2]
                i += 2
                continue
            else:
                lexical_state.regex_allowed = char in "=:([{,;!&|?+-*%^~<>"
            if state == "TEMPLATE_EXPR":
                if char == "{":
                    states.append("TEMPLATE_EXPR")
                elif char == "}":
                    states.pop()
            lexical_state.previous_token = char
            if char in ";{}":
                lexical_state.statement_tokens.clear()
            else:
                lexical_state.statement_tokens = (lexical_state.statement_tokens + [char])[-16:]
        i += 1
    return None


def scanLine(line: str, lexical_state: LexicalState | None = None):
    """Yield (label, rationale) for each sink signature the line trips, unless
    the line carries an audited-safe suppression marker."""
    comment = extract_trailing_comment(line, lexical_state)
    if isComment(line):
        return
    if comment is not None and SUPPRESS.match(comment):
        return
    for pattern, label, rationale in SINK_PATTERNS:
        for match in pattern.finditer(line):
            yield label, rationale


def scanText(text: str, isHtml: bool):
    """Yield (lineno, snippet, label, rationale). For HTML, scan only inline
    <script> blocks; line numbers stay relative to the whole file."""
    if isHtml:
        for m in SCRIPT_BLOCK.finditer(text):
            startLine = text.count("\n", 0, m.start(1)) + 1
            block = m.group(1)
            lexical_state = LexicalState()
            for offset, line in enumerate(block.splitlines()):
                for label, rationale in scanLine(line, lexical_state):
                    yield startLine + offset, line.strip()[:120], label, rationale
    else:
        lexical_state = LexicalState()
        for lineno, line in enumerate(text.splitlines(), start=1):
            for label, rationale in scanLine(line, lexical_state):
                yield lineno, line.strip()[:120], label, rationale


def scan(repoRoot: Path):
    findings = []  # (rel, lineno, snippet, label, rationale)
    for filePath, rel in collectFiles(repoRoot):
        try:
            text = filePath.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            raise RuntimeError(f"Scan aborted: unreadable target '{rel}': {exc}") from exc
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
        "el.innerHTML = `<i>${x}</i>`;  /* gaia-html-sink-ok: fixed enum */",
    ]
    unsafe = [
        "el.innerHTML = `<b>${name}</b>`;",
        "el.outerHTML = `<b>${name}</b>`;",
        "el.innerHTML = '<b>' + name + '</b>';",
        "el.insertAdjacentHTML('beforeend', `<i>${x}</i>`);",
        "document.write('<p>' + x + '</p>');",
        "el.innerHTML = `<use href=\"#${x}\"/>`;",
        "el.innerHTML = `<b>${x}</b>`;  // gaia-html-sink-ok:",  # bare marker, no reason
        "el.innerHTML = `<b>${x}</b>`;  /* gaia-html-sink-ok: */",
        'const x = "gaia-html-sink-ok: foo"; el.innerHTML = `${x}`;',
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


def validateBaseline(payload, repoRoot: Path):
    """Reject malformed budgets instead of silently ignoring their contents."""
    if not isinstance(payload, dict):
        raise ValueError("root must be an object")
    unknown = payload.keys() - {"about", "generated", "findings"}
    if unknown:
        raise ValueError(f"unknown top-level keys: {', '.join(sorted(unknown))}")
    if "about" in payload and not isinstance(payload["about"], str):
        raise ValueError("'about' must be a string")
    if "generated" in payload and not isinstance(payload["generated"], str):
        raise ValueError("'generated' must be a string")
    budget = payload.get("findings")
    if not isinstance(budget, dict):
        raise ValueError("findings must be an object")
    validLabels = {label for _pattern, label, _rationale in SINK_PATTERNS}
    for path, labels in budget.items():
        if not isinstance(path, str) or not path or path.startswith("/") or path.startswith("../") or not (repoRoot / path).is_file():
            raise ValueError(f"findings path must name an existing file: {path!r}")
        if not isinstance(labels, dict):
            raise ValueError(f"labels for {path!r} must be an object")
        for label, count in labels.items():
            if not isinstance(label, str) or label not in validLabels:
                raise ValueError(f"unknown sink label for {path!r}: {label!r}")
            if type(count) is not int or count <= 0:
                raise ValueError(f"count for {path!r} [{label}] must be a positive integer")
    return budget


def checkBaselineGrowth(repoRoot: Path, baseline: Path, budget: dict, baseRef: str | None):
    """Compare budgets to the PR base; unavailable history is fatal in CI.

    CI PR bases require the exact event SHA; refs and merge parents are not
    substitutes. Push events require a valid before SHA; initial pushes use
    a zero baseline, and unavailable nonzero SHAs fail closed.
    Outside CI an explicit base overrides discovery. A missing baseline file
    at a resolved revision uses that revision's scanned sinks as its budget.
    """
    def git(*args, strip=True):
        output = subprocess.run(
            ["git", *args], cwd=repoRoot, check=True,
            capture_output=True, text=True, encoding="utf-8", errors="replace",
        ).stdout
        return output.strip() if strip else output

    try:
        relative = baseline.resolve().relative_to(repoRoot.resolve()).as_posix()
    except ValueError as exc:
        raise ValueError(
            f"Cannot check git baseline growth: baseline file '{baseline}' "
            f"is outside repository root '{repoRoot}'."
        ) from exc
    ciBase = os.environ.get("GITHUB_BASE_REF")
    isCi = os.environ.get("GITHUB_ACTIONS") == "true"
    candidates = [baseRef] if baseRef else []
    revision = None
    expectedSha = None
    zeroBaseline = False
    if isCi:
        event = os.environ.get("GITHUB_EVENT_NAME", "").strip().lower()
        isPr = event == "pull_request" or (event in ("pull_request_target", "") and bool(ciBase))
        eventPath = os.environ.get("GITHUB_EVENT_PATH")
        eventData = {}
        try:
            if eventPath:
                eventData = json.loads(Path(eventPath).read_text(encoding="utf-8"))
                if not isinstance(eventData, dict):
                    raise ValueError("Invalid CI event payload: expected an object")
        except (OSError, ValueError) as exc:
            if event == "push":
                raise RuntimeError("CI push event requires valid 'before' commit SHA in event payload") from exc
            if isPr:
                raise RuntimeError("CI PR event requires pull_request.base.sha in event payload") from exc
            raise
        # Event identity wins over ambient refs or unrelated payload keys.
        if event == "push":
            before = eventData.get("before")
            if not isinstance(before, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", before):
                raise RuntimeError("CI push event requires valid 'before' commit SHA in event payload")
            candidates = []
            if before == "0" * 40:
                zeroBaseline = True
            else:
                try:
                    revision = git("rev-parse", "--verify", f"{before}^{{commit}}")
                except (OSError, subprocess.CalledProcessError) as exc:
                    raise RuntimeError(f"CI push base commit {before} cannot be resolved in git") from exc
        elif isPr:
            pr = eventData.get("pull_request")
            base = pr.get("base") if isinstance(pr, dict) else None
            if not isinstance(base, dict) or not base.get("sha"):
                raise RuntimeError("CI PR event requires pull_request.base.sha in event payload")
            expectedSha = base["sha"]
            if not isinstance(expectedSha, str) or not re.fullmatch(r"[0-9a-fA-F]{40}", expectedSha) or set(expectedSha) == {"0"}:
                raise ValueError("Invalid CI PR base SHA")
            expectedSha = expectedSha.lower()
            candidates = [expectedSha]
        # Other CI events require an explicit base; never guess main or a parent.
    elif not baseRef:
        try:
            git("rev-parse", "--verify", "HEAD^2^{commit}")
            revision = git("rev-parse", "--verify", "HEAD^1^{commit}")
        except (OSError, subprocess.CalledProcessError):
            pass
        if ciBase:
            candidates.extend([f"origin/{ciBase}", ciBase])
        candidates.extend(["origin/dev/steward-campaign-2026-11-05",
                           "origin/main", "main", "HEAD~1"])
    for candidate in candidates:
        if revision is not None:
            break
        try:
            if isCi:
                resolved = git("rev-parse", "--verify", f"{candidate}^{{commit}}")
                if expectedSha is not None and resolved != expectedSha:
                    continue
                revision = resolved
            else:
                revision = git("merge-base", "HEAD", candidate)
            break
        except (OSError, subprocess.CalledProcessError):
            continue
    if revision is None and not zeroBaseline:
        if isCi and isPr and ciBase:
            raise ValueError(f"Error: Cannot resolve CI PR base ref '{ciBase}'")
        message = (f"Cannot check baseline growth: Git base unavailable "
                   f"({', '.join(candidates)})")
        if isCi:
            raise ValueError(f"Git base unavailable ({', '.join(candidates)})")
        print(f"[WARN] {message}; continuing sink scan", file=sys.stderr)
        return False
    baseBudget = {}
    if revision is not None:
        if git("ls-tree", "--name-only", revision, "--", relative):
            baseBudget = json.loads(git("show", f"{revision}:{relative}")).get("findings", {})
        else:
            # First baseline introduction may carry existing debt, but cannot
            # hide sinks added by this change. Read the base tree, not HEAD or
            # the worktree (where files may have changed or been deleted).
            paths = git("ls-tree", "-r", "--name-only", "-z", revision, "--", "docs",
                        strip=False).split("\0")
            for path in paths:
                if not path or isExcluded(path) or not any(
                    fnmatch.fnmatch(path, pattern) or
                    fnmatch.fnmatch(path, pattern.replace("**/", ""))
                    for pattern in SCAN_GLOBS
                ):
                    continue
                content = git("show", f"{revision}:{path}", strip=False)
                for _lineno, _snippet, label, _rationale in scanText(
                    content, path.lower().endswith(".html")
                ):
                    labels = baseBudget.setdefault(path, {})
                    labels[label] = labels.get(label, 0) + 1
    grew = False
    for path, labels in sorted(budget.items()):
        if path not in baseBudget:
            print(f"[FAIL] Baseline grew for {path}: new baseline file entry")
            grew = True
            continue
        for label, count in sorted(labels.items()):
            previous = baseBudget[path].get(label, 0)
            if count > previous:
                print(f"[FAIL] Baseline grew for {path} [{label}]: {previous} -> {count}")
                grew = True
    return grew


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[1])
    parser.add_argument("--baseline", type=Path, default=DEFAULT_BASELINE,
                        help="counted sink debt JSON (missing/empty means zero budget)")
    parser.add_argument("--dump-baseline", action="store_true",
                        help="dump current findings as baseline JSON, without changing files")
    parser.add_argument("--check-baseline-growth", action="store_true",
                        help="reject baseline growth since the merge-base with --base-ref")
    parser.add_argument("--base-ref",
                        help="Git base for baseline growth (default: merge first parent, "
                             "GITHUB_BASE_REF, then integration/main/previous revision)")
    parser.add_argument("--selftest", action="store_true", help="check classifier contracts")
    args = parser.parse_args(argv)
    repoRoot = Path(__file__).resolve().parent.parent

    if args.selftest:
        return selftest()

    try:
        findings = scan(repoRoot)
    except RuntimeError as exc:
        print(f"[FAIL] {exc}", file=sys.stderr)
        return 1
    if args.dump_baseline:
        counts = {}
        for rel, _lineno, _snippet, label, _rationale in findings:
            labels = counts.setdefault(rel, {})
            labels[label] = labels.get(label, 0) + 1
        print(json.dumps({"about": BASELINE_ABOUT, "generated": date.today().isoformat(),
                          "findings": dict(sorted(counts.items()))}, indent=2))
        return 0

    budget = {}
    try:
        if args.baseline.exists():
            budget = validateBaseline(
                json.loads(args.baseline.read_text(encoding="utf-8")), repoRoot
            )
    except (OSError, ValueError) as exc:
        print(f"[FAIL] Malformed baseline schema: {exc}", file=sys.stderr)
        return 1
    if args.check_baseline_growth:
        try:
            if checkBaselineGrowth(repoRoot, args.baseline, budget, args.base_ref):
                return 1
        except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as exc:
            print(f"[FAIL] Cannot check baseline growth: {exc}", file=sys.stderr)
            return 1
    is_baseline_empty = not budget
    carried_findings = []
    new_findings = []
    for entry in findings:
        rel, _lineno, _snippet, label, _rationale = entry
        if budget.get(rel, {}).get(label, 0) > 0:
            budget[rel][label] -= 1
            carried_findings.append(entry)
        else:
            new_findings.append(entry)

    print("=== HTML-Sink Guard  (pre-CodeQL, DOM-XSS pattern) ===")
    print(f"Repo root : {repoRoot}")
    print("Flags     : interpolated/concatenated innerHTML/outerHTML/insertAdjacentHTML/document.write")
    print("Fix       : build via DOM API (createElement/textContent) or escape each dynamic value")
    print(f"Mode      : {'HARD-FAIL' if HARD_FAIL else 'WARN-ONLY'} (new sinks)")
    print(f"Baseline  : {args.baseline} ({'empty — zero budget' if is_baseline_empty else 'counted debt'})")
    print("Suppress  : trailing `// gaia-html-sink-ok: <reason>` on the sink line")
    print()

    for severity, entries in (("DEBT", carried_findings), ("FAIL", new_findings)):
        if not entries:
            continue
        print(f"-- {severity}: {len(entries)} unsafe HTML sink(s) --")
        for rel, lineno, snippet, label, rationale in entries:
            print(f"  [{severity}] {rel}:L{lineno} [{label}] {snippet}")
            print(f"        -> {rationale}")
        print()

    if new_findings:
        print(f"RESULT: FAIL — {len(new_findings)} un-baselined unsafe sink(s) found; convert to DOM API, escape, or suppress with reason")
        return 1
    if carried_findings:
        print(f"RESULT: PASS (carried baseline debt: {len(carried_findings)} sink(s)); new sinks are blocked")
    else:
        print("RESULT: PASS — 0 unsafe HTML sinks.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
