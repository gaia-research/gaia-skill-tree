"""Fixtures for PR-maintenance tests: a real throwaway git repository holding real content-engine templates.

Nothing here talks to GitHub. A "pull request" is a census row whose head SHA is a real commit in the fixture repository,
so the content proofs (regenerate from base templates, rebuild the shared indexes) run for real, not against stubs.
"""

from __future__ import annotations

import atexit
import copy
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

REPO = "gaia-research/gaia-skill-tree"
SOURCE = Path(__file__).resolve().parents[3]
VERSION = "9.0.0"
BOT = {"login": "github-actions[bot]", "id": 41898282, "type": "Bot"}
REQUIRED = ["Schema + DAG + Integrity Checks", "Verify branch scope matches changed files"]
# Load the actual generator by file path: pytest also imports tests/contentEngine,
# which can occupy the bare "contentEngine" name in sys.modules during a full suite.
# A sys.path insertion alone cannot override an already-cached module.
import importlib.util  # noqa: E402

sys.path.insert(0, str(SOURCE / "scripts"))
_spec = importlib.util.spec_from_file_location(
    "gaia_steward_weekly_report_generator", SOURCE / "scripts/contentEngine/generate_weekly_report.py"
)
if _spec is None or _spec.loader is None:
    raise RuntimeError("cannot load the canonical weekly report generator")
gen = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(gen)

STAMP = re.compile(r"\?v=[0-9]+\.[0-9]+\.[0-9]+")
GAIAVERSION = re.compile(r'GAIA_VERSION = "[0-9.]+"')


def run(cwd: Path, *args: str) -> str:
    path = os.environ.get("PATH", "/usr/bin:/bin:/usr/local/bin")
    done = subprocess.run(["git", "-C", str(cwd), *args], capture_output=True, text=True, check=True,
                          env={"GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com", "GIT_COMMITTER_NAME": "t",
                               "GIT_COMMITTER_EMAIL": "t@example.com", "PATH": path, "HOME": str(cwd)})
    return done.stdout.strip()


def stamped(text: str, version: str) -> str:
    return GAIAVERSION.sub(f'GAIA_VERSION = "{version}"', STAMP.sub(f"?v={version}", text))


def reportJson(label: str) -> dict:
    base = json.loads((SOURCE / "docs/api/v1/reports/2026-43.json").read_text(encoding="utf-8"))
    year, week = label.split("-")
    base.update(reportId=label, isoYear=int(year), isoWeek=int(week), generatedAt=f"2026-10-{int(week) % 28 + 1:02d}T08:00:00Z")
    return base


@dataclass
class Fixture:
    root: Path
    base: str
    labels: tuple[str, ...]

    def writeReport(self, label: str, *, version: str = VERSION, html: str | None = None, mutate=None) -> None:
        docs = self.root / "docs"
        report = reportJson(label)
        if mutate is not None:
            mutate(report)
        (docs / "api/v1/reports").mkdir(parents=True, exist_ok=True)
        (docs / "api/v1/reports" / f"{label}.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        target = docs / "reports" / label / "index.html"
        gen.renderHtml(report, self.root / "scripts/contentEngine/templates", target)
        target.write_text(stamped(html if html is not None else target.read_text(encoding="utf-8"), version), encoding="utf-8")

    def rebuildIndexes(self, *, version: str = VERSION) -> None:
        docs = self.root / "docs"
        gen._rebuildArchive(docs, self.root / "scripts/contentEngine/templates", docs / "api/v1/reports/index.json",
                            docs / "reports/index.html", "2026-11-04T00:00:00Z", version)
        index = docs / "reports/index.html"
        index.write_text(stamped(index.read_text(encoding="utf-8"), version), encoding="utf-8")

    def commit(self, message: str) -> str:
        run(self.root, "add", "-A")
        run(self.root, "commit", "-q", "--allow-empty", "-m", message)
        return run(self.root, "rev-parse", "HEAD")

    def heldElsewhere(self, name: str) -> str | None:
        """The path of another worktree that has ``name`` checked out, or ``None``."""

        path = None
        for line in run(self.root, "worktree", "list", "--porcelain").splitlines():
            if line.startswith("worktree "):
                path = line[len("worktree "):]
            elif line == f"branch refs/heads/{name}" and path is not None and Path(path).resolve() != self.root.resolve():
                return path
        return None

    def branch(self, name: str, start: str | None = None) -> None:
        # git 2.43 lets `checkout -B` move a branch another worktree holds; newer git refuses with exit 128. Fail the same
        # way on every version so a fixture that depends on the lenient behaviour is caught before it reaches CI.
        held = self.heldElsewhere(name)
        if held is not None:
            raise AssertionError(f"branch {name!r} is checked out in the worktree {held}; use detach() to build on its commit")
        run(self.root, "checkout", "-q", "-B", name, start or self.base)

    def detach(self, start: str) -> None:
        """Move to ``start`` without naming a branch, for building on a commit whose branch a worktree owns."""

        run(self.root, "checkout", "-q", "--detach", start)

    def head(self, label: str, *, version: str = VERSION, dropIndexRow: str | None = None, tamper: bool = False,
             extraFile: str | None = None, indexVersion: str | None = None, name: str | None = None, mutate=None) -> str:
        """A PR head: base plus report ``label`` with its rebuilt indexes, optionally broken in one specific way."""

        self.branch(name or f"docs/content-engine-{label}")
        self.writeReport(label, version=version, mutate=mutate)
        self.rebuildIndexes(version=indexVersion or version)
        if dropIndexRow:
            path = self.root / "docs/api/v1/reports/index.json"
            data = json.loads(path.read_text(encoding="utf-8"))
            data["reports"] = [r for r in data["reports"] if r["reportId"] != dropIndexRow]
            path.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
        if tamper:
            page = self.root / f"docs/reports/{label}/index.html"
            page.write_text(page.read_text(encoding="utf-8").replace("<body>", "<body><!-- injected -->"), encoding="utf-8")
        if extraFile:
            target = self.root / extraFile
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("changed\n", encoding="utf-8")
        return self.commit(f"feat(content-engine): weekly report {label}")


_REPO_CACHE: dict[tuple[tuple[str, ...], str], tuple[Path, str]] = {}


def _initRepoTemplate(labels: tuple[str, ...], version: str) -> tuple[Path, str]:
    template = Path(tempfile.mkdtemp(prefix=f"gaia-repo-template-{os.getpid()}-")) / "repo"
    template.mkdir(parents=True)
    run(template, "init", "-q", "-b", "main")
    shutil.copytree(SOURCE / "scripts/contentEngine", template / "scripts/contentEngine", ignore=shutil.ignore_patterns("__pycache__"))
    shutil.copy(SOURCE / "scripts/publication_context.py", template / "scripts/publication_context.py")
    (template / ".gitignore").write_text(".gaia/\n", encoding="utf-8")
    (template / "pyproject.toml").write_text(f'[project]\nname = "x"\nversion = "{version}"\n', encoding="utf-8")
    for relative in ("founder/steward/POLICY.yaml", "founder/steward/pr-producers.json",
                     "founder/steward/decisions/steward-pr-maintenance-authority.json"):
        (template / relative).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(SOURCE / relative, template / relative)
    fx = Fixture(template, "", labels)
    for label in labels:
        fx.writeReport(label, version=version)
    fx.rebuildIndexes(version=version)
    base = fx.commit("base")
    return template, base


def makeRepo(tmp: Path, labels: tuple[str, ...] = ("2026-42", "2026-43"), version: str = VERSION) -> Fixture:
    key = (tuple(labels), version)
    if key not in _REPO_CACHE:
        _REPO_CACHE[key] = _initRepoTemplate(key[0], key[1])
    template, base = _REPO_CACHE[key]
    root = tmp / "repo"
    if root.exists():
        shutil.rmtree(root)
    root.parent.mkdir(parents=True, exist_ok=True)
    shutil.copytree(template, root, symlinks=True)
    return Fixture(root, base, labels)


def _cleanupRepoTemplates() -> None:
    for template, _ in _REPO_CACHE.values():
        shutil.rmtree(template.parent, ignore_errors=True)


atexit.register(_cleanupRepoTemplates)


def filesOf(fx: Fixture, head: str) -> list[dict]:
    rows = []
    for line in run(fx.root, "diff", "--name-status", fx.base, head).splitlines():
        status, path = line.split("\t", 1)
        rows.append({"path": path, "status": {"A": "added", "M": "modified", "D": "removed"}.get(status[0], "renamed"),
                     "additions": 1, "deletions": 0, "blobSha": "0" * 40})
    return rows


def passing() -> list[dict]:
    return [{"name": n, "status": "completed", "conclusion": "success", "app": "github-actions"} for n in REQUIRED]


def row(fx: Fixture, head: str, label: str, *, number: int = 2270, **over: Any) -> dict:
    body = f"Auto-generated weekly Content Engine report {label}."
    value = {
        "number": number, "title": f"feat(content-engine): weekly report {label}", "state": "open", "draft": False, "merged": False,
        "author": dict(BOT), "headRef": f"docs/content-engine-{label}", "headSha": head, "headRepo": REPO, "baseRef": "main",
        "baseSha": fx.base, "labels": ["content-engine"], "requestedReviewers": [], "mergeable": True, "mergeableState": "clean",
        "body": body, "bodySha256": hashlib.sha256(body.encode()).hexdigest(),
        "commits": [{"sha": head, "authorLogin": BOT["login"], "authorId": BOT["id"], "authorType": "Bot",
                     "committerLogin": BOT["login"], "committerName": BOT["login"], "parents": 1,
                     "message": "feat(content-engine): weekly report\n\nAuto-generated by .github/workflows/weekly-content-engine.yml."}],
        "files": filesOf(fx, head), "reviews": [], "checkRuns": passing(), "comments": [],
        "reviewThreadsUnresolved": 0, "updatedAt": "2026-11-04T17:00:00Z", "mergedAt": None, "mergeCommitSha": None,
    }
    value.update(over)
    if "body" in over:
        value["bodySha256"] = hashlib.sha256(str(over["body"]).encode()).hexdigest()
    return value


def census(rows: list[dict], tip: str, *, fetched: str = "2026-11-04T18:20:00Z", closed: list[dict] | None = None, **over: Any) -> dict:
    doc = {
        "schemaVersion": "steward-pr-census-v1", "repo": REPO, "fetchedAt": fetched, "defaultBranch": "main",
        "baseTips": {"main": tip},
        "protection": {"complete": True, "source": "rulesets", "classicProtection": "unavailable", "requiredChecks": list(REQUIRED),
                       "strict": True, "requiredApprovals": 0},
        "completeness": {"pulls": {"complete": True, "pagesFetched": 1, "expectedPages": 1, "itemCount": len(rows), "independentTotal": len(rows)},
                         "details": {"complete": True, "expected": len(rows), "fetched": len(rows), "failures": []}},
        "pulls": copy.deepcopy(rows), "recentlyClosed": closed or [],
    }
    doc.update(over)
    return doc


def writeCensus(fx: Fixture, doc: dict) -> Path:
    path = fx.root / ".gaia/steward/inputs/github-prs.json"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(doc), encoding="utf-8")
    return path


def utc(text: str = "2026-11-04T18:30:00Z") -> datetime:
    return datetime.strptime(text, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)


def inject(report: Any, key: str, value: Any) -> bool:
    """Set the first value stored under ``key`` anywhere in a report; True when one was found."""

    if isinstance(report, dict):
        for name, item in report.items():
            if name == key:
                report[name] = value
                return True
            if inject(item, key, value):
                return True
    elif isinstance(report, list):
        return any(inject(item, key, value) for item in report)
    return False
