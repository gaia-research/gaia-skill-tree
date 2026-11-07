"""Deterministic reconciliation for a content-engine report PR: a tracked replacement, never a rewrite of the producer's branch.

The producer's pull request stays exactly as it is. The replacement is a new commit on a ``steward/b/`` branch cut from
the destination tip. Everything that depends on the destination (the rendered HTML, both shared indexes, the version
stamps) is *regenerated* with the destination's own generator; the only payload carried over is the producer's canonical
JSON, byte for byte, read from the producer's head commit. The original is closed later, and only through the closure gate.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from gaia_cli.steward.prmaintenance import proofs

# Under docs/ so the repository's branch-scope guard accepts it on its merits (the files are docs/ files); never a bypass label.
BRANCH = "docs/steward-pr-{number}-{label}"
LABEL = re.compile(r"^[0-9]{4}-[0-9]{2}$")
BOT = "github-actions[bot] <41898282+github-actions[bot]@users.noreply.github.com>"
NOBYTECODE = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
STAMPS = (re.compile(r"\?v=[0-9]+\.[0-9]+\.[0-9]+"), re.compile(r'GAIA_VERSION = "[0-9.]+"'))

BUILD = """
import json, sys
from pathlib import Path
work = Path(sys.argv[1]); label = sys.argv[2]; generatedAt = sys.argv[3]; version = sys.argv[4]
sys.path.insert(0, str(work / "scripts"))
from contentEngine import generate_weekly_report as gen
templates = work / "scripts" / "contentEngine" / "templates"
report = json.loads((work / "docs" / "api" / "v1" / "reports" / (label + ".json")).read_text(encoding="utf-8"))
gen.renderHtml(report, templates, work / "docs" / "reports" / label / "index.html")
gen._rebuildArchive(work / "docs", templates, work / "docs" / "api" / "v1" / "reports" / "index.json",
                    work / "docs" / "reports" / "index.html", generatedAt, version)
"""

CACHEBUST = """
import sys
from pathlib import Path
work = Path(sys.argv[1])
sys.path.insert(0, str(work / "scripts"))
import build_docs
build_docs.build_html_cache_busting(False)
"""


class ReconcileError(RuntimeError):
    """The replacement cannot be built or proven. Nothing was pushed."""


@dataclass(frozen=True)
class Replacement:
    branch: str
    commit: str
    worktree: Path
    label: str
    original: int
    originalHead: str
    files: tuple[str, ...]
    body: str


def git(root: Path, *args: str, timeout: float = 120.0, env: Mapping[str, str] | None = None) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", "--no-replace-objects", "-c", "core.useReplaceRefs=false", "-C", str(root), *args],
        capture_output=True,
        text=True,
        timeout=timeout,
        env=proofs.safeGitEnv(env),
        check=False,
    )


def need(result: subprocess.CompletedProcess, what: str) -> str:
    if result.returncode != 0:
        raise ReconcileError(f"{what} failed: {result.stderr.strip()[:200]}")
    return result.stdout.strip()


def stampAll(text: str, version: str) -> str:
    return STAMPS[1].sub(f'GAIA_VERSION = "{version}"', STAMPS[0].sub(f"?v={version}", text))


def marker(repo: str, number: int, head: str) -> str:
    return f"<!-- gaia-steward:replaces repo={repo} pr={number} head={head[:12]} -->"


def prBody(repo: str, number: int, head: str, label: str, tip: str, proofLines: list[str]) -> str:
    return "\n".join([
        f"Tracked replacement for #{number} (weekly content-engine report {label}), reconciled onto the current destination tip.",
        "",
        marker(repo, number, head),
        "",
        f"- Original: #{number} at head `{head}` (left open and untouched; closed only after this merges, through the closure gate).",
        f"- Destination tip at build: `{tip}`.",
        f"- Carried over byte for byte: `docs/api/v1/reports/{label}.json` (the producer's canonical payload).",
        f"- Regenerated with the destination's own generator: `docs/reports/{label}/index.html`, `docs/reports/index.html`, `docs/api/v1/reports/index.json`, version stamps.",
        "- No other file is touched. Independent verification and GitHub's required checks decide the merge, not this description.",
        "",
        "Proofs at build:",
        *[f"- {line}" for line in proofLines],
    ])


def buildReplacement(root: Path, repo: str, number: int, originalHead: str, label: str, baseSha: str, worktree: Path, *,
                     generatedAt: str | None = None, branch: str | None = None) -> Replacement:
    """Cut the replacement branch in a fresh worktree of ``baseSha`` and commit it. Local only; the caller pushes."""

    if not LABEL.match(label):
        raise ReconcileError(f"{label!r} is not an ISO week label")
    branch = branch or BRANCH.format(number=number, label=label)
    payload = proofs.blob(root, originalHead, f"docs/api/v1/reports/{label}.json")
    originalIndex = proofs.blob(root, originalHead, "docs/api/v1/reports/index.json")
    if payload is None or originalIndex is None:
        raise ReconcileError("the producer's head objects are not local; fetch the pull request head first")
    if not proofs.hasCommit(root, baseSha):
        raise ReconcileError("the destination tip is not local; fetch it first")
    version = proofs.baseVersion(root, baseSha)
    if version is None:
        raise ReconcileError("the destination version could not be read")
    if worktree.exists():
        raise ReconcileError(f"{worktree} already exists; refusing to reuse a worktree")
    need(git(root, "worktree", "add", "-q", "-b", branch, str(worktree), baseSha), "git worktree add")
    try:
        target = worktree / "docs" / "api" / "v1" / "reports" / f"{label}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(payload)
        stamp = generatedAt
        if stamp is None:
            import json

            stamp = json.loads(originalIndex.decode("utf-8")).get("generatedAt") or ""
        if not stamp:
            raise ReconcileError("the producer's index carries no generatedAt to reuse")
        run = subprocess.run([sys.executable, "-c", BUILD, str(worktree), label, stamp, version], capture_output=True, text=True,
                             timeout=180, cwd=worktree, check=False, env=NOBYTECODE)
        if run.returncode != 0:
            raise ReconcileError(f"regeneration failed: {(run.stderr.strip().splitlines() or ['no output'])[-1][:200]}")
        if (worktree / "scripts" / "build_docs.py").exists():
            run = subprocess.run([sys.executable, "-c", CACHEBUST, str(worktree)], capture_output=True, text=True,
                                 timeout=300, cwd=worktree, check=False, env=NOBYTECODE)
            if run.returncode != 0:
                raise ReconcileError(f"the destination's cache-busting step failed: {(run.stderr.strip().splitlines() or ['no output'])[-1][:200]}")
        else:  # a minimal fixture without the build script: apply the same stamp rule directly
            for page in (worktree / "docs" / "reports" / label / "index.html", worktree / "docs" / "reports" / "index.html"):
                page.write_text(stampAll(page.read_text(encoding="utf-8"), version), encoding="utf-8")
        need(git(worktree, "add", "-A", "--", "docs/reports", "docs/api/v1/reports"), "git add")
        changed = need(git(worktree, "diff", "--cached", "--name-only"), "git diff").splitlines()
        stray = need(git(worktree, "status", "--porcelain", "--untracked-files=all"), "git status")
        allowed = {f"docs/reports/{label}/index.html", "docs/reports/index.html", f"docs/api/v1/reports/{label}.json",
                   "docs/api/v1/reports/index.json"}
        if not changed or set(changed) - allowed:
            raise ReconcileError(f"the replacement would touch files outside the report scope: {sorted(set(changed) - allowed)}")
        if any(not line.startswith(("A ", "M ")) for line in stray.splitlines()):
            raise ReconcileError("the worktree holds changes beyond the staged report files")
        message = (f"feat(content-engine): weekly report {label} (reconciled replacement for #{number})\n\n"
                   f"Replaces #{number} at {originalHead}. Payload carried over byte for byte; HTML, shared indexes and version\n"
                   f"stamps regenerated on destination tip {baseSha}.\n\n"
                   f"Co-Authored-By: {BOT}\n")
        need(git(worktree, "-c", "user.name=Claude", "-c", "user.email=noreply@anthropic.com", "commit", "-q", "-m", message), "git commit")
        commit = need(git(worktree, "rev-parse", "HEAD"), "git rev-parse")
        found = [proofs.reportJsonProof(root if proofs.hasCommit(root, commit) else worktree, commit, label),
                 proofs.stampProof(worktree, baseSha, commit, sorted(changed))]
        found += proofs.contentEngineProofs(worktree, baseSha, commit, label)
        failed = [p for p in found if p.state != proofs.PASS]
        if failed:
            raise ReconcileError("the replacement does not pass its own proofs: " + "; ".join(f"{p.name}: {p.detail}" for p in failed))
        return Replacement(branch, commit, worktree, label, number, originalHead, tuple(sorted(changed)),
                           prBody(repo, number, originalHead, label, baseSha, [f"{p.name}: {p.detail}" for p in found]))
    except Exception:
        git(root, "worktree", "remove", "--force", str(worktree))
        git(root, "branch", "-D", branch)
        shutil.rmtree(worktree, ignore_errors=True)
        raise


def refreshReplacement(root: Path, label: str, worktree: Path, baseSha: str, *, number: int, originalHead: str,
                       repo: str = "") -> Replacement:
    """Bring a Steward-owned replacement up to a destination tip that moved, by merging the tip in and regenerating.

    The auto-release restamps every page on each merge, so a replacement built a minute ago can already be behind. This never
    rewrites history: it merges the new tip into the replacement's own branch (conflicts go to the destination, because the four
    report files are regenerated afterwards anyway), regenerates them with the destination's own generator, and re-proves.
    """

    if not LABEL.match(label):
        raise ReconcileError(f"{label!r} is not an ISO week label")
    if not worktree.is_dir() or not proofs.hasCommit(root, baseSha):
        raise ReconcileError("the replacement worktree or the destination tip is not available locally")
    if need(git(worktree, "status", "--porcelain", "--untracked-files=all"), "git status"):
        raise ReconcileError("the replacement worktree has uncommitted changes")
    version = proofs.baseVersion(root, baseSha)
    if version is None:
        raise ReconcileError("the destination version could not be read")
    import json

    indexBytes = (worktree / "docs" / "api" / "v1" / "reports" / "index.json").read_bytes()
    stamp = json.loads(indexBytes.decode("utf-8")).get("generatedAt") or ""
    if not stamp:
        raise ReconcileError("the replacement's index carries no generatedAt to reuse")
    identity = ["-c", "user.name=Claude", "-c", "user.email=noreply@anthropic.com"]
    merged = git(worktree, *identity, "merge", "--no-ff", "--no-edit", "-X", "theirs", "-m",
                 f"Merge destination tip {baseSha[:12]} into the replacement for #{number}", baseSha)
    if merged.returncode != 0:
        git(worktree, "merge", "--abort")
        raise ReconcileError(f"merging the destination tip failed: {merged.stderr.strip()[:200]}")
    run = subprocess.run([sys.executable, "-c", BUILD, str(worktree), label, stamp, version], capture_output=True, text=True,
                         timeout=180, cwd=worktree, check=False, env=NOBYTECODE)
    if run.returncode != 0:
        raise ReconcileError(f"regeneration failed: {(run.stderr.strip().splitlines() or ['no output'])[-1][:200]}")
    if (worktree / "scripts" / "build_docs.py").exists():
        run = subprocess.run([sys.executable, "-c", CACHEBUST, str(worktree)], capture_output=True, text=True,
                             timeout=300, cwd=worktree, check=False, env=NOBYTECODE)
        if run.returncode != 0:
            raise ReconcileError(f"the destination's cache-busting step failed: {(run.stderr.strip().splitlines() or ['no output'])[-1][:200]}")
    else:
        for page in (worktree / "docs" / "reports" / label / "index.html", worktree / "docs" / "reports" / "index.html"):
            page.write_text(stampAll(page.read_text(encoding="utf-8"), version), encoding="utf-8")
    need(git(worktree, "add", "-A", "--", "docs/reports", "docs/api/v1/reports"), "git add")
    if git(worktree, "diff", "--cached", "--quiet").returncode != 0:
        need(git(worktree, *identity, "commit", "-q", "-m",
                 f"feat(content-engine): regenerate report {label} stamps and indexes on destination tip {baseSha[:12]}\n\n"
                 f"Co-Authored-By: {BOT}\n"), "git commit")
    commit = need(git(worktree, "rev-parse", "HEAD"), "git rev-parse")
    changed = need(git(root, "diff", "--name-only", baseSha, commit), "git diff").splitlines()
    allowed = {f"docs/reports/{label}/index.html", "docs/reports/index.html", f"docs/api/v1/reports/{label}.json", "docs/api/v1/reports/index.json"}
    if not changed or set(changed) - allowed:
        raise ReconcileError(f"after the refresh the replacement differs from the tip outside the report scope: {sorted(set(changed) - allowed)}")
    found = [proofs.reportJsonProof(root, commit, label), proofs.stampProof(root, baseSha, commit, sorted(changed))]
    found += proofs.contentEngineProofs(root, baseSha, commit, label)
    failed = [p for p in found if p.state != proofs.PASS]
    if failed:
        raise ReconcileError("the refreshed replacement does not pass its own proofs: " + "; ".join(f"{p.name}: {p.detail}" for p in failed))
    return Replacement(git(worktree, "rev-parse", "--abbrev-ref", "HEAD").stdout.strip(), commit, worktree, label, number, originalHead,
                       tuple(sorted(changed)), prBody(repo, number, originalHead, label, baseSha, [f"{p.name}: {p.detail}" for p in found]))


def asMapping(replacement: Replacement) -> Mapping[str, Any]:
    return {"branch": replacement.branch, "commit": replacement.commit, "worktree": str(replacement.worktree),
            "label": replacement.label, "original": replacement.original, "originalHead": replacement.originalHead,
            "files": list(replacement.files)}
