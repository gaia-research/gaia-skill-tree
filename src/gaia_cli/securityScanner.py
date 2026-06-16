"""Defensive security scanner for named-skill markdown content.

Runs during ``gaia push`` and ``gaia dev verify``.  Flags obvious hostile
patterns so malicious skills cannot enter the registry without an explicit,
audited override.

This module is intentionally *defensive only*: it inspects skill text and
returns structured findings.  It performs no side effects, does not fetch
remote content, and does not modify files.  The five detector categories are:

* ``shellExec`` — direct shell or interpreter invocations
* ``destructiveFs`` — recursive or root-anchored filesystem deletes
* ``outboundNet`` — HTTP/socket calls to non-allowlisted hosts
* ``promptInjection`` — role-override phrases or unicode tag chars
* ``credentialHarvesting`` — embedded tokens or env-var reads of secrets

Severity ordering (highest first): ``high``, ``medium``, ``low``.
Findings are returned ordered by severity then category for stable output.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable


# Hosts that named-skill markdown is allowed to reference without warning.
# Keep this conservative — additions should be reviewed by maintainers.
DEFAULT_HOST_ALLOWLIST = frozenset(
    {
        "github.com",
        "api.github.com",
        "raw.githubusercontent.com",
        "gist.github.com",
        "arxiv.org",
        "pypi.org",
        "pypi.python.org",
        "claude.ai",
        "anthropic.com",
        "docs.anthropic.com",
        "python.org",
        "docs.python.org",
    }
)


SEVERITY_ORDER = {"high": 0, "medium": 1, "low": 2}


@dataclass(frozen=True)
class Finding:
    """A single security-scanner finding."""

    severity: str
    category: str
    filePath: str
    lineNumber: int
    snippet: str
    rule: str

    def asDict(self) -> dict:
        return {
            "severity": self.severity,
            "category": self.category,
            "filePath": self.filePath,
            "lineNumber": self.lineNumber,
            "snippet": self.snippet,
            "rule": self.rule,
        }


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------


def _truncate(text: str, length: int = 80) -> str:
    text = text.strip()
    if len(text) <= length:
        return text
    return text[: length - 1] + "…"


@dataclass
class _Block:
    """Markdown fenced-code block descriptor."""

    language: str
    isExample: bool
    startLine: int  # 1-indexed start of code (line *after* the opening fence)
    endLine: int    # 1-indexed inclusive end of code (line *before* the closing fence)


def _parseFencedBlocks(text: str) -> list[_Block]:
    """Return fenced code blocks present in ``text``.

    A block is marked ``isExample`` when its first non-blank content line
    contains a ``# example`` or ``# pseudo`` comment marker.  Such blocks are
    treated as illustrative and most detectors downgrade or skip findings
    inside them.
    """
    blocks: list[_Block] = []
    fenceRe = re.compile(r"^(?P<indent>\s{0,3})(?P<fence>```+|~~~+)\s*(?P<lang>[^\s`]*)")
    lines = text.splitlines()
    i = 0
    while i < len(lines):
        m = fenceRe.match(lines[i])
        if not m:
            i += 1
            continue
        fence = m.group("fence")
        lang = m.group("lang").lower()
        startLine = i + 2  # 1-indexed line *after* the fence
        j = i + 1
        while j < len(lines):
            close = re.match(r"^\s{0,3}(?P<fence>```+|~~~+)\s*$", lines[j])
            if close and close.group("fence")[0] == fence[0] and len(close.group("fence")) >= len(fence):
                break
            j += 1
        endLine = j  # j is 0-indexed line of close fence; 1-indexed line above is j
        isExample = False
        for k in range(i + 1, j):
            stripped = lines[k].strip()
            if not stripped:
                continue
            lower = stripped.lower()
            if "# example" in lower or "# pseudo" in lower or "# illustrative" in lower:
                isExample = True
            break
        blocks.append(_Block(language=lang, isExample=isExample, startLine=startLine, endLine=endLine))
        i = j + 1
    return blocks


def _findEnclosingBlock(blocks: list[_Block], lineNumber: int) -> _Block | None:
    for b in blocks:
        if b.startLine <= lineNumber <= b.endLine:
            return b
    return None


# ---------------------------------------------------------------------------
# detectors
# ---------------------------------------------------------------------------


_SHELL_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("subprocess.Popen", re.compile(r"subprocess\.Popen\b")),
    ("subprocess.run", re.compile(r"subprocess\.run\b")),
    ("subprocess.call", re.compile(r"subprocess\.call\b")),
    ("subprocess.check_output", re.compile(r"subprocess\.check_output\b")),
    ("subprocess.check_call", re.compile(r"subprocess\.check_call\b")),
    ("subprocess.getoutput", re.compile(r"subprocess\.getoutput\b")),
    ("os.system", re.compile(r"os\.system\b")),
    ("os.popen", re.compile(r"os\.popen\b")),
    ("os.spawn", re.compile(r"os\.spawn\w*\b")),
    ("eval(", re.compile(r"\beval\s*\(")),
    ("exec(", re.compile(r"\bexec\s*\(")),
    ("commands.getoutput", re.compile(r"commands\.getoutput\b")),
    ("pty.spawn", re.compile(r"pty\.spawn\b")),
)


def detectShellExec(text: str, filePath: str) -> list[Finding]:
    """Flag direct shell-execution APIs found inside code blocks.

    Lines outside fenced code blocks are intentionally ignored — the goal is
    to flag *executable* code embedded in skill markdown, not prose mentioning
    these APIs.  Bash blocks marked ``# example`` / ``# pseudo`` are treated
    as illustrative and skipped.  Other example-marked blocks downgrade the
    finding to ``low`` severity rather than dropping it (so reviewers still
    see them, but the push is not blocked).
    """
    blocks = _parseFencedBlocks(text)
    findings: list[Finding] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        block = _findEnclosingBlock(blocks, idx)
        if block is None:
            continue
        if block.language in {"bash", "sh", "shell", "zsh"} and block.isExample:
            continue
        downgrade = block.isExample or block.language in {"text", "txt", "md", "markdown"}
        for ruleName, pattern in _SHELL_PATTERNS:
            if not pattern.search(line):
                continue
            severity = "low" if downgrade else "high"
            findings.append(
                Finding(
                    severity=severity,
                    category="shellExec",
                    filePath=filePath,
                    lineNumber=idx,
                    snippet=_truncate(line),
                    rule=ruleName,
                )
            )
    return findings


_DESTRUCTIVE_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("rm -rf", re.compile(r"\brm\s+-[a-zA-Z]*r[a-zA-Z]*f|\brm\s+-[a-zA-Z]*f[a-zA-Z]*r", re.IGNORECASE)),
    ("shutil.rmtree", re.compile(r"shutil\.rmtree\b")),
    ("os.removedirs", re.compile(r"os\.removedirs\b")),
    ("Path.unlink", re.compile(r"\.unlink\s*\(")),
    ("os.unlink", re.compile(r"os\.unlink\b")),
    ("os.remove", re.compile(r"os\.remove\b")),
    ("forkBomb", re.compile(r":\(\)\s*\{\s*:\|:&\s*\}\s*;\s*:")),
    ("dd-of-dev", re.compile(r"\bdd\s+[^\n]*of=/dev/")),
    ("mkfs", re.compile(r"\bmkfs(\.\w+)?\s")),
)


def detectDestructiveFs(text: str, filePath: str) -> list[Finding]:
    """Flag recursive or root-anchored filesystem destruction.

    ``rm -rf`` is only flagged ``high`` when its target is root-anchored
    (``/``, ``~``, ``$HOME``, or absolute).  Sandbox examples like
    ``/tmp/x`` inside an ``# example`` block are downgraded to ``low``.
    """
    blocks = _parseFencedBlocks(text)
    findings: list[Finding] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        block = _findEnclosingBlock(blocks, idx)
        if block is None:
            continue
        isExample = block.isExample
        for ruleName, pattern in _DESTRUCTIVE_PATTERNS:
            m = pattern.search(line)
            if not m:
                continue
            if ruleName == "rm -rf":
                tail = line[m.end():].strip()
                token = tail.split()[0] if tail else ""
                token = token.strip("'\"")
                isSandbox = token.startswith("/tmp/") or token.startswith("/var/tmp/")
                isDangerous = (
                    token in {"/", "/*", "~", "~/", "~/*", "$HOME", "$HOME/*", ""}
                    or token.startswith("/")
                    or token.startswith("~")
                    or token.startswith("$HOME")
                )
                if isSandbox and isExample:
                    findings.append(
                        Finding(
                            severity="low",
                            category="destructiveFs",
                            filePath=filePath,
                            lineNumber=idx,
                            snippet=_truncate(line),
                            rule=ruleName,
                        )
                    )
                    continue
                if not isDangerous:
                    continue
                severity = "low" if isExample else "high"
                findings.append(
                    Finding(
                        severity=severity,
                        category="destructiveFs",
                        filePath=filePath,
                        lineNumber=idx,
                        snippet=_truncate(line),
                        rule=ruleName,
                    )
                )
                continue
            if ruleName in {"os.remove", "os.unlink", "Path.unlink"}:
                tail = line[m.end():]
                argMatch = re.match(r"\s*\(?\s*['\"]([^'\"]+)['\"]", tail)
                pathArg = argMatch.group(1) if argMatch else ""
                isAbsolute = (
                    pathArg.startswith("/")
                    or pathArg.startswith("~")
                    or pathArg.startswith("$HOME")
                )
                if isAbsolute:
                    severity = "low" if isExample else "high"
                else:
                    severity = "low" if isExample else "medium"
                findings.append(
                    Finding(
                        severity=severity,
                        category="destructiveFs",
                        filePath=filePath,
                        lineNumber=idx,
                        snippet=_truncate(line),
                        rule=ruleName,
                    )
                )
                continue
            severity = "low" if isExample else "high"
            findings.append(
                Finding(
                    severity=severity,
                    category="destructiveFs",
                    filePath=filePath,
                    lineNumber=idx,
                    snippet=_truncate(line),
                    rule=ruleName,
                )
            )
    return findings


_NET_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("requests", re.compile(r"\brequests\.(get|post|put|delete|patch|head|request|Session)\b")),
    ("urllib.request", re.compile(r"urllib\.request\.(urlopen|Request)\b")),
    ("urllib.urlopen", re.compile(r"\burlopen\s*\(")),
    ("httpx", re.compile(r"\bhttpx\.(get|post|put|delete|patch|head|request|Client|AsyncClient)\b")),
    ("aiohttp", re.compile(r"aiohttp\.(ClientSession|request)\b")),
    ("socket.connect", re.compile(r"\bsocket\.\w+\.connect\s*\(\s*\(|\bs\.connect\s*\(\s*\(")),
    ("urllib3", re.compile(r"\burllib3\.PoolManager\b")),
    ("curl", re.compile(r"\bcurl\b\s+[^\n]*https?://")),
    ("wget", re.compile(r"\bwget\b\s+[^\n]*https?://")),
)

_URL_RE = re.compile(r"https?://([A-Za-z0-9._-]+)")


def _hostFromLine(line: str) -> str | None:
    m = _URL_RE.search(line)
    if not m:
        return None
    return m.group(1).lower()


def detectOutboundNet(
    text: str,
    filePath: str,
    allowlist: Iterable[str] = DEFAULT_HOST_ALLOWLIST,
) -> list[Finding]:
    """Flag HTTP/socket APIs that target non-allowlisted hosts.

    Severity ``medium`` when an explicit host is found and not in the
    allowlist, ``low`` when the URL is variable / not explicit, and
    suppressed entirely for allowlisted hosts and example blocks.
    """
    blocks = _parseFencedBlocks(text)
    allow = {h.lower() for h in allowlist}
    findings: list[Finding] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        block = _findEnclosingBlock(blocks, idx)
        if block is None:
            continue
        if block.isExample:
            continue
        for ruleName, pattern in _NET_PATTERNS:
            if not pattern.search(line):
                continue
            host = _hostFromLine(line)
            if host is None:
                findings.append(
                    Finding(
                        severity="low",
                        category="outboundNet",
                        filePath=filePath,
                        lineNumber=idx,
                        snippet=_truncate(line),
                        rule=ruleName,
                    )
                )
                continue
            hostInAllow = host in allow or any(host.endswith("." + a) for a in allow)
            if hostInAllow:
                continue
            findings.append(
                Finding(
                    severity="medium",
                    category="outboundNet",
                    filePath=filePath,
                    lineNumber=idx,
                    snippet=_truncate(line),
                    rule=f"{ruleName} -> {host}",
                )
            )
    return findings


_INJECTION_PHRASES: tuple[str, ...] = (
    "ignore previous instructions",
    "ignore prior instructions",
    "disregard previous instructions",
    "disregard prior instructions",
    "ignore all previous instructions",
    "you are now",
    "you must now",
    "from now on you are",
    "developer mode",
    "jailbreak",
    "do anything now",
    "dan mode",
)

_ROLE_OVERRIDE_RE = re.compile(r"^\s*(system|assistant|user)\s*:", re.IGNORECASE)
_UNICODE_TAG_RE = re.compile(r"[\U000E0000-\U000E007F]")


def detectPromptInjection(text: str, filePath: str) -> list[Finding]:
    """Flag role-override phrases and invisible-unicode payloads.

    Uses three heuristics:

    * Known injection phrases (case-insensitive substring match).
    * ``system:`` / ``assistant:`` / ``user:`` at the start of a prose line
      (skipped inside code blocks, which often carry transcripts).
    * Unicode tag block ``U+E0000``–``U+E007F`` (invisible payload smuggling).
    """
    findings: list[Finding] = []
    blocks = _parseFencedBlocks(text)
    lines = text.splitlines()
    for idx, line in enumerate(lines, start=1):
        block = _findEnclosingBlock(blocks, idx)
        lower = line.lower()
        for phrase in _INJECTION_PHRASES:
            if phrase in lower:
                findings.append(
                    Finding(
                        severity="high",
                        category="promptInjection",
                        filePath=filePath,
                        lineNumber=idx,
                        snippet=_truncate(line),
                        rule=f"phrase:{phrase}",
                    )
                )
        if block is None or block.language in {"text", "txt", "md", "markdown", ""}:
            roleMatch = _ROLE_OVERRIDE_RE.match(line)
            if roleMatch:
                findings.append(
                    Finding(
                        severity="high",
                        category="promptInjection",
                        filePath=filePath,
                        lineNumber=idx,
                        snippet=_truncate(line),
                        rule=f"role-override:{roleMatch.group(1).lower()}",
                    )
                )
        if _UNICODE_TAG_RE.search(line):
            findings.append(
                Finding(
                    severity="high",
                    category="promptInjection",
                    filePath=filePath,
                    lineNumber=idx,
                    snippet=_truncate(repr(line)),
                    rule="unicodeTag",
                )
            )
    return findings


_TOKEN_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    ("github-token", re.compile(r"\bgh[psorau]_[A-Za-z0-9]{36,}\b")),
    ("anthropic-token", re.compile(r"\bsk-ant-[A-Za-z0-9_-]{32,}\b")),
    ("openai-token", re.compile(r"\bsk-(?!ant-)[A-Za-z0-9]{32,}\b")),
    ("aws-access-key", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("google-oauth", re.compile(r"\bya29\.[0-9A-Za-z_-]+")),
    ("slack-token", re.compile(r"\bxox[abprs]-[0-9A-Za-z-]{10,}\b")),
    ("private-key-block", re.compile(r"-----BEGIN (RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY-----")),
)

_ENV_NAMES: frozenset[str] = frozenset(
    {
        "GH_TOKEN",
        "GITHUB_TOKEN",
        "GITHUB_PAT",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "ANTHROPIC_AUTH_TOKEN",
    }
)
_ENV_GLOBS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bAWS_[A-Z0-9_]*KEY[A-Z0-9_]*\b"),
    re.compile(r"\bAWS_[A-Z0-9_]*SECRET[A-Z0-9_]*\b"),
    re.compile(r"\bAWS_SESSION_TOKEN\b"),
    re.compile(r"\b[A-Z][A-Z0-9_]*_SECRET(_[A-Z0-9_]+)?\b"),
    re.compile(r"\b[A-Z][A-Z0-9_]*_PRIVATE_KEY(_[A-Z0-9_]+)?\b"),
    re.compile(r"\b[A-Z][A-Z0-9_]*_API_KEY(_[A-Z0-9_]+)?\b"),
)
_ENV_READ_RE = re.compile(
    r"""(?:os\.environ\s*\[\s*['"](?P<name1>[A-Z][A-Z0-9_]*)['"]\s*\]"""
    r"""|os\.environ\.get\s*\(\s*['"](?P<name2>[A-Z][A-Z0-9_]*)['"]"""
    r"""|os\.getenv\s*\(\s*['"](?P<name3>[A-Z][A-Z0-9_]*)['"]"""
    r"""|process\.env\.(?P<name4>[A-Z][A-Z0-9_]*))"""
)


def _matchesSensitiveEnv(name: str) -> bool:
    if name in _ENV_NAMES:
        return True
    for pat in _ENV_GLOBS:
        if pat.fullmatch(name):
            return True
    return False


def detectCredentialHarvesting(text: str, filePath: str) -> list[Finding]:
    """Flag literal token shapes and reads of sensitive env vars."""
    findings: list[Finding] = []
    for idx, line in enumerate(text.splitlines(), start=1):
        for ruleName, pattern in _TOKEN_PATTERNS:
            for m in pattern.finditer(line):
                findings.append(
                    Finding(
                        severity="high",
                        category="credentialHarvesting",
                        filePath=filePath,
                        lineNumber=idx,
                        snippet=_truncate(m.group(0)),
                        rule=f"token:{ruleName}",
                    )
                )
        for m in _ENV_READ_RE.finditer(line):
            name = m.group("name1") or m.group("name2") or m.group("name3") or m.group("name4")
            if not name:
                continue
            if _matchesSensitiveEnv(name):
                findings.append(
                    Finding(
                        severity="high",
                        category="credentialHarvesting",
                        filePath=filePath,
                        lineNumber=idx,
                        snippet=_truncate(line),
                        rule=f"envRead:{name}",
                    )
                )
    return findings


# ---------------------------------------------------------------------------
# orchestrator
# ---------------------------------------------------------------------------


_DETECTORS = (
    detectShellExec,
    detectDestructiveFs,
    detectOutboundNet,
    detectPromptInjection,
    detectCredentialHarvesting,
)


def scanSkillContent(
    text: str,
    filePath: str,
    allowlist: Iterable[str] = DEFAULT_HOST_ALLOWLIST,
) -> list[Finding]:
    """Run every detector and return findings sorted by severity then category.

    Severity order: ``high`` < ``medium`` < ``low`` (high listed first).
    Within a severity bucket, findings keep deterministic order
    (category alphabetical, then line number, then rule name).
    """
    findings: list[Finding] = []
    for det in _DETECTORS:
        if det is detectOutboundNet:
            findings.extend(det(text, filePath, allowlist))
        else:
            findings.extend(det(text, filePath))
    findings.sort(
        key=lambda f: (
            SEVERITY_ORDER.get(f.severity, 99),
            f.category,
            f.lineNumber,
            f.rule,
        )
    )
    return findings


def hasHighSeverity(findings: Iterable[Finding]) -> bool:
    return any(f.severity == "high" for f in findings)


def formatFindings(findings: Iterable[Finding]) -> str:
    """Render a human-readable summary of findings (no ANSI colors)."""
    findings = list(findings)
    out: list[str] = []
    counts = {"high": 0, "medium": 0, "low": 0}
    for f in findings:
        counts[f.severity] = counts.get(f.severity, 0) + 1
    out.append(
        f"Security scanner findings: high={counts.get('high', 0)} "
        f"medium={counts.get('medium', 0)} low={counts.get('low', 0)}"
    )
    for sev in ("high", "medium", "low"):
        for f in findings:
            if f.severity != sev:
                continue
            out.append(
                f"  [{sev.upper()}] {f.category}/{f.rule} "
                f"{f.filePath}:{f.lineNumber} :: {f.snippet}"
            )
    return "\n".join(out)


# Convenience scanner for batch entries (used by ``gaia push``).


def scanNamedSkillFiles(
    paths: Iterable[str],
    allowlist: Iterable[str] = DEFAULT_HOST_ALLOWLIST,
) -> list[Finding]:
    """Read each markdown path and accumulate findings across all of them.

    Missing or unreadable files are skipped silently — the scanner is a
    safety net, not a path validator.
    """
    out: list[Finding] = []
    for p in paths:
        try:
            with open(p, "r", encoding="utf-8") as f:
                text = f.read()
        except (OSError, UnicodeDecodeError):
            continue
        out.extend(scanSkillContent(text, p, allowlist))
    out.sort(
        key=lambda f: (
            SEVERITY_ORDER.get(f.severity, 99),
            f.category,
            f.filePath,
            f.lineNumber,
            f.rule,
        )
    )
    return out
