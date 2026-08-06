#!/usr/bin/env python3
"""Install-parity harness: `gaia install` vs the `skills` npm CLI.

Sweeps every named skill in the registry, installs each one both ways into a
throwaway sandbox, and diffs the result. Fails loudly naming WHICH skill
diverged and WHY; succeeds with timing and health KPIs.

This is a standalone operator tool. It lives in scripts/ (never collected by
pytest — pyproject sets testpaths = ["tests"]) and is deliberately NOT wired
into CI. It is diagnostic, not a gate.

    python scripts/install_parity.py
    python scripts/install_parity.py --only garrytan/health --keep
    python scripts/install_parity.py --category STANDARD --limit 25 --jobs 4
    python scripts/install_parity.py --json generated-output/parity/report.json

Exit codes: 0 = full parity, 1 = at least one failure, 2 = precondition failure.

The two installers are structurally different by construction — gaia symlinks
into a git clone cache, the npm CLI copies real files — so parity is judged on
the *delivered content* plus the *installed directory name*. Link-vs-copy
mechanics and lockfile shape are recorded as KPIs, never as failures.
"""

from __future__ import annotations

import argparse
import concurrent.futures
import hashlib
import json
import os
import shutil
import statistics
import subprocess
import sys
import threading
import time
from collections import Counter, defaultdict
from dataclasses import dataclass, field

REPO_ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT_DIR, "src"))

from gaia_cli.install import _parse_github_url  # noqa: E402

# Pinned so a KPI shift is attributable to a registry change, not a tool
# upgrade. The resolved version is recorded in the JSON report.
DEFAULT_NPX_VERSION = "1.5.21"

# Exactly what the npm CLI's installer skips when it copies a skill directory
# (see installer.ts in vercel-labs/skills). Anything else present on one side
# and absent on the other is a real divergence.
SKIP_DIRS = {".git", "__pycache__", "__pypackages__"}
SKIP_FILES = {"metadata.json"}

STANDARD = "STANDARD"
REPO_ROOT = "REPO_ROOT"
SUITE = "SUITE"
NO_SOURCE = "NO_SOURCE"
CATEGORIES = (STANDARD, REPO_ROOT, SUITE, NO_SOURCE)

# Messages the installer may emit when correctly refusing a NO_SOURCE skill.
# Matched lowercased against combined stdout+stderr.
NO_SOURCE_REFUSALS = (
    "no source repository link",
    "registry-only",
)

PASS = "PASS"
FAIL = "FAIL"

# Where a finding has to be fixed. Splitting this out is the difference between
# "47 failures" and "38 curation edits, 6 installer bugs, 3 dead upstreams" —
# the second is a work plan, the first is a wall.
DATA = "DATA"          # registry curation: fix registry/named/<contrib>/<slug>.md
CLI = "CLI"            # installer defect: fix src/gaia_cli/install.py
POLICY = "POLICY"      # one ruling fixes the whole class; see below
UPSTREAM = "UPSTREAM"  # the source repo moved or went away; not our defect
HARNESS = "HARNESS"    # measurement noise; not a finding about anything
ORIGIN_ORDER = (DATA, CLI, POLICY, UPSTREAM, HARNESS)

# POLICY exists so the report never overstates undecided work: a failure class
# whose fix depends on a ruling nobody has made yet should not be counted as N
# separate curation edits. DIRNAME_MISMATCH used to be the archetype — fixable
# either by renaming the registry slug or by having the installer adopt the
# upstream name — until issue #1446 settled it (Option A: registry slug wins).
# It is now plain DATA. POLICY currently has no members mapped to it; it stays
# defined for the next open question of this shape.

FAILURE_ORIGINS = {
    # DATA — the registry entry describes the wrong thing.
    "NOT_FOUND": DATA,
    "AMBIGUOUS_REF": DATA,
    "NO_SOURCE_LINK": DATA,
    "NOT_A_SKILL_DIR": DATA,
    "NO_SKILL_MD": DATA,
    # Settled by issue #1446 (Option A: registry slug wins) — fix with
    # `gaia dev rename <old-id> <new-id>`, same as any other DATA finding.
    "DIRNAME_MISMATCH": DATA,
    "NPX_NO_SKILL_DISCOVERED": DATA,
    "NPX_FAN_OUT": DATA,
    "SUITE_COMPONENT_FAILED": DATA,
    "CONTENT_MISSING_FILE": DATA,
    "CONTENT_EXTRA_FILE": DATA,
    "CONTENT_BYTES_DIFFER": DATA,
    # A dangling symlink means links.github points at a path that no longer
    # exists upstream. It is DATA, not CLI: hardening the installer only turns
    # a silent success into a loud failure — the skill still does not install
    # until the link is fixed. The CLI gap is real but separate, hence dual.
    "DANGLING_SYMLINK": DATA,
    # CLI — gaia accepted or produced a state it should have rejected.
    "GAIA_INSTALL_FAILED": CLI,
    "UNEXPECTED_SUCCESS": CLI,
    # UPSTREAM / HARNESS.
    "GIT_CLONE_FAILED": UPSTREAM,
    "TIMEOUT": HARNESS,
    "NPX_INSTALL_FAILED": HARNESS,
}

# Codes whose root cause is a bad registry link, but which ALSO show gaia
# failing to validate what it installed. Fixing the data clears the finding;
# hardening the CLI stops the next one landing silently.
DUAL_ORIGIN = {"NOT_A_SKILL_DIR", "NO_SKILL_MD", "DANGLING_SYMLINK"}

print_lock = threading.Lock()


def log(message: str) -> None:
    with print_lock:
        print(message, flush=True)


# ─────────────────────────────────────────────────────────────────────────────
# Model
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Skill:
    id: str
    contributor: str
    slug: str
    github: str | None
    suite_components: list[str]
    suite_ref: str | None
    category: str
    repo_url: str | None
    branch: str | None
    subpath: str


@dataclass
class Failure:
    code: str
    detail: str

    @property
    def origin(self) -> str:
        return FAILURE_ORIGINS.get(self.code, CLI)

    @property
    def dual(self) -> bool:
        return self.code in DUAL_ORIGIN


@dataclass
class Result:
    skill_id: str
    category: str
    verdict: str = PASS
    failures: list[Failure] = field(default_factory=list)
    gaia_seconds: float = 0.0
    npx_seconds: float = 0.0
    cold: bool = False
    repo_url: str | None = None
    gaia_dirname: str | None = None
    npx_dirname: str | None = None
    gaia_mechanism: str | None = None
    files_compared: int = 0
    npx_discovered: int = 0
    npx_note: str | None = None
    suite_installed: int = 0
    suite_total: int = 0
    suite_ref: str | None = None

    def fail(self, code: str, detail: str) -> None:
        self.verdict = FAIL
        self.failures.append(Failure(code, detail))


# ─────────────────────────────────────────────────────────────────────────────
# Skill enumeration
# ─────────────────────────────────────────────────────────────────────────────


def load_index(repo_root: str) -> tuple[list[dict], str]:
    """Return (entries, source_path).

    registry/named-skills.json is Class P and gitignored, so on a clean
    checkout it is absent. docs/graph/named/index.json is the committed 1:1
    mirror (written by scripts/build_docs.py) and is the normal source.

    Deliberately NOT using gaia_cli.install.list_available() as the primary
    source: without the JSON it silently falls back to scanning frontmatter,
    which loses suiteComponents for suites declared under registry/suites/ —
    i.e. it misclassifies the exact 18 skills that need suite handling.
    """
    candidates = [
        os.path.join(repo_root, "registry", "named-skills.json"),
        os.path.join(repo_root, "docs", "graph", "named", "index.json"),
    ]
    for path in candidates:
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        entries = [e for bucket in data.get("buckets", {}).values() for e in bucket]
        entries += data.get("awaitingClassification", [])
        return sorted(entries, key=lambda e: e.get("id", "")), path
    raise SystemExit(
        "No registry index found. Looked for:\n  "
        + "\n  ".join(candidates)
        + "\nRun `gaia dev docs` to regenerate, or run from the repo root."
    )


def classify(entry: dict) -> str:
    """Classify an index entry.

    SUITE is checked first because install_skill() auto-routes to
    install_suite() whenever suiteComponents is truthy, regardless of --suite
    (src/gaia_cli/install.py:286-296).
    """
    if entry.get("suiteComponents"):
        return SUITE
    github = (entry.get("links") or {}).get("github")
    if not github:
        return NO_SOURCE
    if "/blob/" in github or "/tree/" in github:
        return STANDARD
    return REPO_ROOT


def build_skills(entries: list[dict]) -> list[Skill]:
    skills = []
    for entry in entries:
        skill_id = entry.get("id", "")
        if "/" not in skill_id:
            continue
        contributor, slug = skill_id.split("/", 1)
        github = (entry.get("links") or {}).get("github")
        repo_url = branch = None
        subpath = ""
        if github:
            # Reuse gaia's own parser so the harness targets the exact same
            # source location the installer does, and cannot drift from it.
            repo_url, branch, subpath = _parse_github_url(github)
        skills.append(
            Skill(
                id=skill_id,
                contributor=contributor,
                slug=slug,
                github=github,
                suite_components=list(entry.get("suiteComponents") or []),
                suite_ref=entry.get("suiteRef") or None,
                category=classify(entry),
                repo_url=repo_url,
                branch=branch,
                subpath=subpath,
            )
        )
    return skills


def npx_ref(skill: Skill) -> str:
    """The URL to hand the npm CLI so it resolves the same source as gaia."""
    base = (skill.repo_url or "").removesuffix(".git")
    if skill.branch and skill.subpath:
        return f"{base}/tree/{skill.branch}/{skill.subpath}"
    if skill.branch:
        return f"{base}/tree/{skill.branch}"
    return base


# ─────────────────────────────────────────────────────────────────────────────
# Content comparison
# ─────────────────────────────────────────────────────────────────────────────


def hash_tree(root: str) -> dict[str, str]:
    """Map every file under root to its SHA256, relative-path keyed."""
    digests: dict[str, str] = {}
    for dirpath, dirnames, filenames in os.walk(root):
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIRS]
        for name in filenames:
            if name in SKIP_FILES:
                continue
            full = os.path.join(dirpath, name)
            rel = os.path.relpath(full, root)
            try:
                with open(full, "rb") as f:
                    digest = hashlib.sha256(f.read()).hexdigest()
            except OSError as exc:
                digest = f"UNREADABLE:{exc}"
            digests[rel.replace(os.sep, "/")] = digest
    return digests


def summarize(paths: list[str], limit: int = 6) -> str:
    shown = sorted(paths)[:limit]
    extra = len(paths) - len(shown)
    text = ", ".join(shown)
    return f"{text} (+{extra} more)" if extra > 0 else text


def compare_trees(result: Result, gaia_root: str, npx_root: str) -> None:
    gaia_files = hash_tree(gaia_root)
    npx_files = hash_tree(npx_root)
    result.files_compared = len(set(gaia_files) | set(npx_files))

    missing = [p for p in npx_files if p not in gaia_files]
    extra = [p for p in gaia_files if p not in npx_files]
    differing = [
        p for p in gaia_files if p in npx_files and gaia_files[p] != npx_files[p]
    ]

    if missing:
        result.fail(
            "CONTENT_MISSING_FILE",
            f"{len(missing)} file(s) the npm CLI delivered are absent from the "
            f"gaia install: {summarize(missing)}",
        )
    if extra:
        result.fail(
            "CONTENT_EXTRA_FILE",
            f"{len(extra)} file(s) present in the gaia install that the npm CLI "
            f"did not deliver: {summarize(extra)}",
        )
    if differing:
        result.fail(
            "CONTENT_BYTES_DIFFER",
            f"{len(differing)} file(s) differ in content: {summarize(differing)}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Install drivers
# ─────────────────────────────────────────────────────────────────────────────


def run(cmd: list[str], cwd: str, env: dict, timeout: int) -> tuple[int, str, str]:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            timeout=timeout,
            capture_output=True,
            text=True,
        )
        return proc.returncode, proc.stdout, proc.stderr
    except subprocess.TimeoutExpired:
        return 124, "", f"timed out after {timeout}s"
    except FileNotFoundError as exc:
        return 127, "", str(exc)


def install_gaia(cfg, skill: Skill, sandbox: str) -> tuple[int, str, str, float]:
    """Install via the gaia CLI into an isolated sandbox.

    GAIA_HOME is read at call time (install.py:21), so it fully redirects both
    the git clone cache and the global install root. No `gaia init` is needed:
    get_repo_skills_dir() only stats .agents/.claude in CWD, and .gaia/ is
    created lazily by save_manifest().
    """
    cwd = os.path.join(sandbox, "gaia")
    os.makedirs(cwd, exist_ok=True)

    env = dict(os.environ)
    env["GAIA_HOME"] = cfg.gaia_home
    env["PYTHONPATH"] = os.path.join(cfg.repo_root, "src") + os.pathsep + env.get(
        "PYTHONPATH", ""
    )
    env["NO_COLOR"] = "1"

    cmd = list(cfg.gaia_cmd) + ["--registry", cfg.repo_root, "install", skill.id]
    if skill.category == SUITE:
        cmd.append("--suite")

    started = time.monotonic()
    code, out, err = run(cmd, cwd, env, cfg.timeout)
    return code, out, err, time.monotonic() - started


def install_npx(cfg, skill: Skill, sandbox: str) -> tuple[int, str, str, float]:
    """Install via the `skills` npm CLI into an isolated sandbox.

    HOME and XDG_STATE_HOME are per-skill, not per-run, so concurrent workers
    cannot race on the CLI's global .skill-lock.json. DO_NOT_TRACK suppresses
    its telemetry POSTs.
    """
    cwd = os.path.join(sandbox, "npx")
    home = os.path.join(sandbox, "npx-home")
    state = os.path.join(sandbox, "npx-state")
    for path in (cwd, home, state):
        os.makedirs(path, exist_ok=True)

    env = dict(os.environ)
    env["HOME"] = home
    env["XDG_STATE_HOME"] = state
    env["DO_NOT_TRACK"] = "1"
    env["DISABLE_TELEMETRY"] = "1"
    env["NO_COLOR"] = "1"

    cmd = [cfg.npx_bin, "add", npx_ref(skill), "-y", "-a", "claude-code", "-s", "*"]
    started = time.monotonic()
    code, out, err = run(cmd, cwd, env, cfg.timeout)
    return code, out, err, time.monotonic() - started


def cache_dir_for(cfg, skill: Skill) -> str:
    """Mirror install.py:180 — the clone cache dir gaia would use.

    Note the owner segment is the registry CONTRIBUTOR, not the GitHub owner.
    """
    repo_name = (skill.repo_url or "").rstrip("/").split("/")[-1].removesuffix(".git")
    return os.path.join(cfg.gaia_home, "skills", skill.contributor, repo_name)


def purge_cache(cfg, skill: Skill) -> None:
    """Drop a partial clone so it cannot poison later skills from the same repo.

    A timed-out `git clone` leaves a half-written cache dir. gaia treats any
    existing dir as a valid cache and only runs `git pull` on it — whose exit
    status it ignores — so without this every later skill in the group would
    silently install from a broken tree.
    """
    if skill.repo_url:
        shutil.rmtree(cache_dir_for(cfg, skill), ignore_errors=True)


def read_manifest(sandbox: str) -> dict:
    path = os.path.join(sandbox, "gaia", ".gaia", "install-manifest.json")
    if not os.path.exists(path):
        return {"installed": []}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {"installed": []}


def manifest_entry(manifest: dict, skill_id: str) -> dict | None:
    for entry in manifest.get("installed", []):
        if entry.get("id") == skill_id:
            return entry
    return None


def npx_roots(sandbox: str) -> list[str]:
    """Skill dirs the npm CLI materialized.

    The CLI has two layouts: a canonical real copy in .agents/skills with a
    symlink from each agent dir, OR — when a single agent is named explicitly,
    as this harness does with `-a claude-code` — real files written straight
    into .claude/skills. Scan both and dedupe by realpath so a symlinked pair
    counts once, preferring the .agents path as canonical.
    """
    found: dict[str, str] = {}
    for agent_dir in (".agents", ".claude"):
        base = os.path.join(sandbox, "npx", agent_dir, "skills")
        if not os.path.isdir(base):
            continue
        for name in sorted(os.listdir(base)):
            full = os.path.join(base, name)
            if os.path.isdir(full):
                found.setdefault(os.path.realpath(full), full)
    return [found[key] for key in sorted(found)]


def classify_gaia_failure(code: int, out: str, err: str) -> tuple[str, str]:
    """Map a failed gaia install to a taxonomy code plus a human detail."""
    blob = f"{out}\n{err}"
    lowered = blob.lower()
    if code == 124:
        return "TIMEOUT", err.strip() or "gaia install timed out"
    if "not found in registry" in lowered:
        return "NOT_FOUND", "ref did not resolve in the registry"
    if "ambiguous" in lowered:
        return "AMBIGUOUS_REF", "resolve_named_skill_reference raised ValueError"
    if "no source repository link" in lowered:
        return "NO_SOURCE_LINK", "skill has no links.github"
    if "git error" in lowered or "fatal:" in lowered:
        tail = [ln for ln in blob.splitlines() if ln.strip()][-1:] or ["git failed"]
        return "GIT_CLONE_FAILED", tail[0].strip()
    tail = [ln for ln in blob.splitlines() if ln.strip()][-1:] or ["unknown error"]
    return "GAIA_INSTALL_FAILED", f"exit {code}: {tail[0].strip()}"


# ─────────────────────────────────────────────────────────────────────────────
# Per-category checks
# ─────────────────────────────────────────────────────────────────────────────


def check_gaia_health(result: Result, entry: dict) -> str | None:
    """Validate what gaia actually put on disk. Returns the resolved root."""
    local_path = entry.get("localPath")
    if not local_path:
        result.fail("GAIA_INSTALL_FAILED", "manifest entry has no localPath")
        return None

    result.gaia_dirname = os.path.basename(local_path.rstrip(os.sep))
    result.gaia_mechanism = "link" if os.path.islink(local_path) else "copy"

    # os.path.realpath resolves both symlinks and NTFS junctions; os.readlink
    # does not handle junctions.
    resolved = os.path.realpath(local_path)
    if not os.path.exists(resolved):
        result.fail(
            "DANGLING_SYMLINK",
            f"gaia reported success but {result.gaia_dirname} -> {resolved} "
            "does not exist (_install_single never validates the subpath)",
        )
        return None
    if not os.path.isdir(resolved):
        result.fail(
            "NOT_A_SKILL_DIR",
            f"gaia exited 0 but installed a non-directory: {resolved} "
            "(links.github points at a file that is not a .md)",
        )
        return None
    if not os.path.exists(os.path.join(resolved, "SKILL.md")):
        result.fail("NO_SKILL_MD", f"no SKILL.md in installed tree {resolved}")
        return None
    return resolved


def check_no_source(result: Result, code: int, out: str, err: str) -> None:
    """A NO_SOURCE skill must fail, and must fail with the right message."""
    if code == 0:
        result.fail(
            "UNEXPECTED_SUCCESS",
            "skill has no links.github but gaia install exited 0",
        )
        return
    blob = f"{out}\n{err}".lower()
    # Two honest refusals, not one. A skill can reach NO_SOURCE either by having
    # no links.github at all, or by being curated `installable: false` (which
    # pops the links block). The installer names the second case explicitly, and
    # that message is the more accurate of the two — accept both.
    if not any(phrase in blob for phrase in NO_SOURCE_REFUSALS):
        failure_code, detail = classify_gaia_failure(code, out, err)
        result.fail(
            "GAIA_INSTALL_FAILED",
            f"expected a no-source refusal, got {failure_code}: {detail}",
        )


def check_suite(result: Result, skill: Skill, manifest: dict) -> None:
    """Suites skip the content diff; instead every component must install."""
    result.suite_total = len(skill.suite_components)
    missing = []
    for component in skill.suite_components:
        entry = manifest_entry(manifest, component)
        if entry is None:
            missing.append(f"{component} (no manifest entry)")
            continue
        resolved = os.path.realpath(entry.get("localPath", ""))
        if not os.path.isdir(resolved):
            missing.append(f"{component} (path missing: {resolved})")
            continue
        result.suite_installed += 1
    if missing:
        result.fail(
            "SUITE_COMPONENT_FAILED",
            f"{result.suite_installed}/{result.suite_total} components installed; "
            f"failed: {summarize(missing)}",
        )


# ─────────────────────────────────────────────────────────────────────────────
# Driver for one skill
# ─────────────────────────────────────────────────────────────────────────────


def check_skill(cfg, skill: Skill, cold: bool) -> Result:
    result = Result(
        skill_id=skill.id,
        category=skill.category,
        cold=cold,
        suite_ref=skill.suite_ref,
    )
    result.repo_url = skill.repo_url
    sandbox = os.path.join(cfg.run_root, "sandboxes", skill.id.replace("/", "__"))
    os.makedirs(sandbox, exist_ok=True)

    try:
        code, out, err, seconds = install_gaia(cfg, skill, sandbox)
        result.gaia_seconds = seconds

        if skill.category == NO_SOURCE:
            check_no_source(result, code, out, err)
            return result

        # Suites are inspected regardless of exit code: install_suite() returns
        # False whenever ANY component fails, so a partial suite exits nonzero.
        # Checking the components first turns "exit 1" into the list of which
        # ones actually failed.
        if skill.category == SUITE:
            check_suite(result, skill, read_manifest(sandbox))
            if code != 0 and result.verdict == PASS:
                # Every named component landed but gaia still failed — the suite
                # root itself, or something else install_suite reported.
                failure_code, detail = classify_gaia_failure(code, out, err)
                result.fail(failure_code, detail)
            return result

        if code != 0:
            failure_code, detail = classify_gaia_failure(code, out, err)
            result.fail(failure_code, detail)
            if failure_code in ("TIMEOUT", "GIT_CLONE_FAILED"):
                purge_cache(cfg, skill)
            return result

        manifest = read_manifest(sandbox)

        entry = manifest_entry(manifest, skill.id)
        if entry is None:
            result.fail(
                "GAIA_INSTALL_FAILED",
                "gaia exited 0 but wrote no manifest entry for this skill",
            )
            return result

        gaia_root = check_gaia_health(result, entry)
        if gaia_root is None:
            # gaia's own install is already broken; running the npm CLI would
            # only add a second, derivative failure.
            return result

        npx_code, npx_out, npx_err, npx_seconds = install_npx(cfg, skill, sandbox)
        result.npx_seconds = npx_seconds
        roots = npx_roots(sandbox)
        result.npx_discovered = len(roots)

        if skill.category == REPO_ROOT:
            # A bare repo link points at a repo that GROUPS skills; it is not
            # itself a skill repo. The npm CLI is therefore not a valid oracle
            # here — it may legitimately find nothing, or find N skills under
            # names of its own choosing. What matters is that `gaia install`
            # produced something that works, which check_gaia_health already
            # confirmed. Everything the npm CLI did is recorded as information,
            # never as a failure.
            result.npx_dirname = os.path.basename(roots[0]) if roots else None
            result.npx_note = (
                "npm CLI found nothing (expected for a grouped-skills repo)"
                if not roots
                else f"npm CLI discovered {len(roots)} skill(s)"
            )
            return result

        if npx_code == 124:
            result.fail("TIMEOUT", "npm CLI install timed out")
            return result
        if not roots:
            if npx_code != 0:
                tail = [ln for ln in npx_err.splitlines() if ln.strip()][-1:]
                result.fail(
                    "NPX_INSTALL_FAILED",
                    f"exit {npx_code}: {tail[0].strip() if tail else 'no output'}",
                )
            else:
                result.fail(
                    "NPX_NO_SKILL_DISCOVERED",
                    f"no skill found at {npx_ref(skill)} (links.github -> "
                    f"{skill.github})",
                )
            return result

        if result.npx_discovered > 1:
            names = [os.path.basename(r) for r in roots]
            result.fail(
                "NPX_FAN_OUT",
                f"a blob/tree link should resolve to exactly one skill, but the "
                f"npm CLI discovered {len(names)}: {summarize(names)}",
            )
            return result

        result.npx_dirname = os.path.basename(roots[0])
        check_dirname(result)
        compare_trees(result, gaia_root, roots[0])
        return result
    finally:
        if not cfg.keep:
            shutil.rmtree(sandbox, ignore_errors=True)


def check_dirname(result: Result) -> None:
    if not result.gaia_dirname or not result.npx_dirname:
        return
    if result.gaia_dirname != result.npx_dirname:
        contributor = result.skill_id.split("/", 1)[0]
        result.fail(
            "DIRNAME_MISMATCH",
            f"gaia:'{result.gaia_dirname}' npx:'{result.npx_dirname}' "
            f"fix: gaia dev rename {result.skill_id} {contributor}/{result.npx_dirname}",
        )


def check_repo_group(cfg, skills: list[Skill], progress) -> list[Result]:
    """Process one repo's skills serially.

    Sharding by repo means the shared git clone cache is never written by two
    workers at once, so no locking is needed — and the first skill of each repo
    naturally measures the cold (clone-inclusive) install time.
    """
    results = []
    for index, skill in enumerate(skills):
        result = check_skill(cfg, skill, cold=(index == 0 and skill.repo_url is not None))
        results.append(result)
        progress(result)
    return results


# ─────────────────────────────────────────────────────────────────────────────
# Preconditions
# ─────────────────────────────────────────────────────────────────────────────


def require_tools(cfg) -> None:
    missing = [tool for tool in ("git", "node", "npm") if shutil.which(tool) is None]
    if missing:
        raise SystemExit(
            f"Missing required tool(s): {', '.join(missing)}. "
            "Install them and re-run."
        )

    code, out, err = run(
        list(cfg.gaia_cmd) + ["--version"],
        cfg.repo_root,
        {**os.environ, "PYTHONPATH": os.path.join(cfg.repo_root, "src")},
        cfg.timeout,
    )
    if code != 0:
        raise SystemExit(
            f"Could not run the gaia CLI ({' '.join(cfg.gaia_cmd)}): "
            f"{(err or out).strip()}"
        )


def install_npx_tool(cfg) -> str:
    """Install the `skills` CLI once per run and return its resolved version.

    Installing once and invoking the bin directly avoids per-skill npx
    resolution overhead and pins the version so KPIs stay comparable.
    """
    prefix = os.path.join(cfg.run_root, "npx-tool")
    os.makedirs(prefix, exist_ok=True)
    log(f"Installing skills@{cfg.npx_version} into {prefix} ...")
    code, out, err = run(
        [
            "npm",
            "install",
            "--prefix",
            prefix,
            "--no-audit",
            "--no-fund",
            "--silent",
            f"skills@{cfg.npx_version}",
        ],
        cfg.run_root,
        dict(os.environ),
        max(cfg.timeout, 300),
    )
    if code != 0:
        raise SystemExit(
            f"Could not install skills@{cfg.npx_version}: {(err or out).strip()}"
        )

    bin_path = os.path.join(prefix, "node_modules", ".bin", "skills")
    if not os.path.exists(bin_path):
        raise SystemExit(f"skills CLI binary not found at {bin_path}")
    cfg.npx_bin = bin_path

    pkg = os.path.join(prefix, "node_modules", "skills", "package.json")
    try:
        with open(pkg, "r", encoding="utf-8") as f:
            return json.load(f).get("version", cfg.npx_version)
    except (OSError, json.JSONDecodeError):
        return cfg.npx_version


# ─────────────────────────────────────────────────────────────────────────────
# Reporting
# ─────────────────────────────────────────────────────────────────────────────


def percentiles(values: list[float]) -> dict:
    if not values:
        return {"n": 0, "avg": 0.0, "p50": 0.0, "p95": 0.0, "max": 0.0}
    ordered = sorted(values)
    index = min(len(ordered) - 1, int(round(0.95 * (len(ordered) - 1))))
    return {
        "n": len(ordered),
        "avg": round(statistics.fmean(ordered), 2),
        "p50": round(statistics.median(ordered), 2),
        "p95": round(ordered[index], 2),
        "max": round(ordered[-1], 2),
    }


def build_kpis(results: list[Result], cfg, wall_seconds: float, npx_version: str) -> dict:
    by_category = defaultdict(lambda: {"total": 0, "pass": 0, "fail": 0})
    for result in results:
        bucket = by_category[result.category]
        bucket["total"] += 1
        bucket["pass" if result.verdict == PASS else "fail"] += 1

    cold = [r.gaia_seconds for r in results if r.cold and r.gaia_seconds > 0]
    warm = [r.gaia_seconds for r in results if not r.cold and r.gaia_seconds > 0]
    npx = [r.npx_seconds for r in results if r.npx_seconds > 0]

    suites = [r for r in results if r.category == SUITE]
    repo_roots = [r for r in results if r.category == REPO_ROOT]

    return {
        "totals": {
            "swept": len(results),
            "pass": sum(1 for r in results if r.verdict == PASS),
            "fail": sum(1 for r in results if r.verdict == FAIL),
        },
        "byCategory": dict(by_category),
        "timing": {
            "wallSeconds": round(wall_seconds, 2),
            "jobs": cfg.jobs,
            "gaiaCold": percentiles(cold),
            "gaiaWarm": percentiles(warm),
            "gaiaAll": percentiles(cold + warm),
            "npx": percentiles(npx),
        },
        "health": {
            "reposCloned": len({r.repo_url for r in results if r.repo_url}),
            "dirnameMismatches": [
                {"id": r.skill_id, "gaia": r.gaia_dirname, "npx": r.npx_dirname}
                for r in results
                if any(f.code == "DIRNAME_MISMATCH" for f in r.failures)
            ],
            "danglingSymlinks": [
                r.skill_id
                for r in results
                if any(f.code == "DANGLING_SYMLINK" for f in r.failures)
            ],
            "suiteCoverage": {
                "installed": sum(r.suite_installed for r in suites),
                "total": sum(r.suite_total for r in suites),
                "perSuite": {
                    r.skill_id: f"{r.suite_installed}/{r.suite_total}" for r in suites
                },
            },
            "repoRootFanOut": {
                r.skill_id: r.npx_discovered for r in repo_roots if r.npx_discovered
            },
            "filesCompared": sum(r.files_compared for r in results),
        },
        "failureCodes": dict(
            Counter(f.code for r in results for f in r.failures).most_common()
        ),
        "byOrigin": {
            origin: {
                "findings": sum(
                    1 for r in results for f in r.failures if f.origin == origin
                ),
                "skills": len(
                    {
                        r.skill_id
                        for r in results
                        for f in r.failures
                        if f.origin == origin
                    }
                ),
                "codes": dict(
                    Counter(
                        f.code
                        for r in results
                        for f in r.failures
                        if f.origin == origin
                    ).most_common()
                ),
            }
            for origin in ORIGIN_ORDER
        },
        "tooling": {
            "npxVersion": npx_version,
            "gaiaCommand": " ".join(cfg.gaia_cmd),
        },
    }


def render_suite_rollup(failures: list[Result]) -> None:
    """Collapse failing components of one suite into a single shared-shape line.

    Components of a suite fail together for the same upstream-packaging reason
    far more often than they fail independently. Without this, five sibling
    components read as five unrelated defects and get triaged five times.
    """
    grouped: dict[str, list[Result]] = {}
    for result in failures:
        if result.suite_ref:
            grouped.setdefault(result.suite_ref, []).append(result)
    shared = {ref: rs for ref, rs in grouped.items() if len(rs) > 1}
    if not shared:
        return

    print("\n" + "=" * 78)
    print(f"SUITE ROLLUP ({len(shared)} suite(s) with multiple failing components)")
    print("=" * 78)
    print("These are one shape each, not one task per row.")
    for ref in sorted(shared):
        members = sorted(shared[ref], key=lambda r: r.skill_id)
        codes: dict[str, int] = {}
        for result in members:
            for failure in result.failures:
                codes[failure.code] = codes.get(failure.code, 0) + 1
        summary = ", ".join(f"{code}x{n}" for code, n in sorted(codes.items()))
        print(f"\n  {ref}  —  {len(members)} component(s) failing:  {summary}")
        for result in members:
            print(f"      {result.skill_id}")


def render(results: list[Result], kpis: dict) -> None:
    failures = [r for r in results if r.verdict == FAIL]

    if failures:
        width = max(len(r.skill_id) for r in failures)
        headers = {
            DATA: "DATA — registry curation; fix registry/named/<contributor>/<slug>.md",
            CLI: "CLI — installer defect; fix src/gaia_cli/install.py",
            POLICY: (
                "POLICY — one ruling settles the whole class; these are NOT "
                "per-skill tasks.\n"
                "         Decide once, then act."
            ),
            UPSTREAM: "UPSTREAM — source repo moved or unreachable; not a Gaia defect",
            HARNESS: "HARNESS — measurement noise; re-run or raise --timeout",
        }
        findings = [
            (failure, result)
            for result in sorted(failures, key=lambda r: (r.category, r.skill_id))
            for failure in result.failures
        ]
        print("\n" + "=" * 78)
        print(f"FINDINGS ({len(findings)} across {len(failures)} skill(s))")
        for origin in ORIGIN_ORDER:
            group = [(f, r) for f, r in findings if f.origin == origin]
            if not group:
                continue
            print("=" * 78)
            print(f"{headers[origin]}  [{len(group)}]")
            print("=" * 78)
            for failure, result in group:
                mark = "*" if failure.dual else " "
                suite = f"  [suite: {result.suite_ref}]" if result.suite_ref else ""
                print(
                    f"{mark} {result.skill_id:<{width}}  {failure.code:<24}  "
                    f"{failure.detail}{suite}"
                )
        if any(f.dual for f, _ in findings):
            print(
                "\n  * also a CLI gap: gaia installed this without validating it. "
                "Fixing the data clears the finding; hardening the installer stops "
                "the next one landing silently."
            )

        render_suite_rollup(failures)

    print("\n" + "=" * 78)
    print("KPIs")
    print("=" * 78)

    totals = kpis["totals"]
    print(f"Swept       {totals['swept']}   pass {totals['pass']}   fail {totals['fail']}")
    print()
    print(f"{'Category':<12} {'total':>6} {'pass':>6} {'fail':>6}")
    for category in CATEGORIES:
        bucket = kpis["byCategory"].get(category)
        if bucket:
            print(
                f"{category:<12} {bucket['total']:>6} {bucket['pass']:>6} {bucket['fail']:>6}"
            )

    timing = kpis["timing"]
    print()
    print(
        f"{'Install time (s)':<18} {'n':>5} {'avg':>7} {'p50':>7} {'p95':>7} {'max':>7}"
    )
    for label, key in (
        ("gaia cold (clone)", "gaiaCold"),
        ("gaia warm (cached)", "gaiaWarm"),
        ("gaia all", "gaiaAll"),
        ("npm skills CLI", "npx"),
    ):
        stats = timing[key]
        if not stats["n"]:
            print(f"{label:<18} {0:>5} {'—':>7} {'—':>7} {'—':>7} {'—':>7}")
            continue
        print(
            f"{label:<18} {stats['n']:>5} {stats['avg']:>7} {stats['p50']:>7} "
            f"{stats['p95']:>7} {stats['max']:>7}"
        )

    health = kpis["health"]
    coverage = health["suiteCoverage"]
    print()
    print(f"Wall clock          {timing['wallSeconds']}s across {timing['jobs']} job(s)")
    print(f"Repos cloned        {health['reposCloned']}")
    print(f"Files compared      {health['filesCompared']}")
    print(f"Dirname mismatches  {len(health['dirnameMismatches'])}")
    print(f"Dangling symlinks   {len(health['danglingSymlinks'])}")
    if coverage["total"]:
        print(
            f"Suite components    {coverage['installed']}/{coverage['total']} installed"
        )
    if health["repoRootFanOut"]:
        fan_out = sum(health["repoRootFanOut"].values())
        print(
            f"Repo-root fan-out   gaia installs {len(health['repoRootFanOut'])} skill(s); "
            f"the npm CLI discovers {fan_out}"
        )

    if kpis["failureCodes"]:
        print()
        print(f"{'Findings by origin':<12} {'findings':>9} {'skills':>7}")
        for origin in ORIGIN_ORDER:
            bucket = kpis["byOrigin"][origin]
            if bucket["findings"]:
                print(
                    f"{origin:<12} {bucket['findings']:>9} {bucket['skills']:>7}   "
                    + ", ".join(f"{c}×{n}" for c, n in bucket["codes"].items())
                )

        # The whole point of the run: is the next move a data pass or a CLI pass?
        origins = kpis["byOrigin"]
        print()
        print("VERDICT — what the next pass actually is")
        print(
            f"  data updates    {origins[DATA]['skills']:>3} skill(s) need a "
            "registry edit (gaia dev verbs)"
        )
        print(
            f"  cli updates     {origins[CLI]['skills']:>3} skill(s) blocked by an "
            "installer defect"
        )
        if origins[POLICY]["findings"]:
            print(
                f"  decisions         1 ruling clears "
                f"{origins[POLICY]['findings']} finding(s) — not per-skill work"
            )
        if origins[UPSTREAM]["skills"]:
            print(
                f"  upstream        {origins[UPSTREAM]['skills']:>3} skill(s) whose "
                "source moved; re-link or freeze"
            )
        if origins[HARNESS]["skills"]:
            print(
                f"  ignore          {origins[HARNESS]['skills']:>3} measurement "
                "artefact(s); re-run or raise --timeout"
            )

    print()
    print(f"Tooling: skills@{kpis['tooling']['npxVersion']}")


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="install_parity.py",
        description="Diff `gaia install` against the `skills` npm CLI, per skill.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument("--only", action="append", default=[], metavar="ID",
                        help="Only this skill id (repeatable)")
    parser.add_argument("--contributor", action="append", default=[], metavar="NAME",
                        help="Only skills by this contributor (repeatable)")
    parser.add_argument("--category", action="append", default=[], choices=CATEGORIES,
                        help="Only this category (repeatable)")
    parser.add_argument("--limit", type=int, default=0,
                        help="Cap the number of skills swept (0 = no cap)")
    parser.add_argument("--jobs", type=int, default=min(8, os.cpu_count() or 1),
                        help="Parallel workers, sharded by source repo (1 = serial)")
    parser.add_argument("--timeout", type=int, default=600,
                        help="Per-install timeout in seconds. Generous by default: "
                             "some source repos are very large, and a false TIMEOUT "
                             "masks the real signal.")
    parser.add_argument("--npx-version", default=DEFAULT_NPX_VERSION,
                        help=f"Version of the `skills` npm CLI (default {DEFAULT_NPX_VERSION})")
    parser.add_argument("--gaia-bin", default=None,
                        help="Override the gaia command (default: this checkout via -m gaia_cli)")
    parser.add_argument("--json", dest="json_path", default=None, metavar="PATH",
                        help="Write the full machine-readable report here")
    parser.add_argument("--keep", action="store_true",
                        help="Keep sandboxes for inspection instead of deleting them")
    parser.add_argument("--list", action="store_true",
                        help="List the selected skills and their categories, then exit")
    return parser.parse_args(argv)


def select(skills: list[Skill], args) -> list[Skill]:
    selected = skills
    if args.only:
        wanted = {s.lstrip("/") for s in args.only}
        selected = [s for s in selected if s.id in wanted]
    if args.contributor:
        wanted = set(args.contributor)
        selected = [s for s in selected if s.contributor in wanted]
    if args.category:
        wanted = set(args.category)
        selected = [s for s in selected if s.category in wanted]
    if args.limit > 0:
        selected = selected[: args.limit]
    return selected


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    entries, index_path = load_index(REPO_ROOT_DIR)
    skills = build_skills(entries)
    selected = select(skills, args)

    print(f"Registry index: {os.path.relpath(index_path, REPO_ROOT_DIR)}")
    print(f"Named skills:   {len(skills)} total, {len(selected)} selected")

    if not selected:
        print("No skills matched the given filters.", file=sys.stderr)
        return 2

    if args.list:
        for skill in selected:
            print(f"  {skill.category:<10} {skill.id}")
        return 0

    run_id = time.strftime("%Y%m%dT%H%M%S")
    run_root = os.path.join(REPO_ROOT_DIR, "generated-output", "parity", run_id)
    os.makedirs(run_root, exist_ok=True)

    cfg = argparse.Namespace(
        repo_root=REPO_ROOT_DIR,
        run_root=run_root,
        gaia_home=os.path.join(run_root, "gaia-home"),
        gaia_cmd=([args.gaia_bin] if args.gaia_bin else [sys.executable, "-m", "gaia_cli"]),
        npx_version=args.npx_version,
        npx_bin=None,
        timeout=args.timeout,
        jobs=max(1, args.jobs),
        keep=args.keep,
    )

    try:
        require_tools(cfg)
        npx_version = install_npx_tool(cfg)
    except SystemExit as exc:
        print(f"Precondition failed: {exc}", file=sys.stderr)
        return 2

    # Shard by repo so the shared clone cache is never written concurrently.
    groups: dict[str, list[Skill]] = defaultdict(list)
    for skill in selected:
        groups[skill.repo_url or f"__nosource__{skill.id}"].append(skill)

    print(f"Sandbox root:   {os.path.relpath(run_root, REPO_ROOT_DIR)}")
    print(
        f"Running {len(selected)} skill(s) across {len(groups)} repo group(s), "
        f"{cfg.jobs} job(s)\n"
    )

    done = [0]

    def progress(result: Result) -> None:
        done[0] += 1
        mark = "ok  " if result.verdict == PASS else "FAIL"
        with print_lock:
            print(
                f"[{done[0]:>3}/{len(selected)}] {mark} {result.category:<10} "
                f"{result.skill_id}",
                flush=True,
            )

    started = time.monotonic()
    results: list[Result] = []
    if cfg.jobs == 1:
        for group in groups.values():
            results.extend(check_repo_group(cfg, group, progress))
    else:
        with concurrent.futures.ThreadPoolExecutor(max_workers=cfg.jobs) as pool:
            futures = [
                pool.submit(check_repo_group, cfg, group, progress)
                for group in groups.values()
            ]
            for future in concurrent.futures.as_completed(futures):
                results.extend(future.result())
    wall_seconds = time.monotonic() - started

    results.sort(key=lambda r: r.skill_id)
    kpis = build_kpis(results, cfg, wall_seconds, npx_version)
    render(results, kpis)

    if args.json_path:
        os.makedirs(os.path.dirname(os.path.abspath(args.json_path)), exist_ok=True)
        payload = {
            "runId": run_id,
            "indexPath": os.path.relpath(index_path, REPO_ROOT_DIR),
            "kpis": kpis,
            "results": [
                {
                    "id": r.skill_id,
                    "category": r.category,
                    "verdict": r.verdict,
                    "gaiaSeconds": round(r.gaia_seconds, 3),
                    "npxSeconds": round(r.npx_seconds, 3),
                    "cold": r.cold,
                    "repoUrl": r.repo_url,
                    "gaiaDirname": r.gaia_dirname,
                    "npxDirname": r.npx_dirname,
                    "gaiaMechanism": r.gaia_mechanism,
                    "filesCompared": r.files_compared,
                    "npxDiscovered": r.npx_discovered,
                    "npxNote": r.npx_note,
                    "suiteInstalled": r.suite_installed,
                    "suiteTotal": r.suite_total,
                    "suiteRef": r.suite_ref,
                    "failures": [
                        {
                            "code": f.code,
                            "origin": f.origin,
                            "alsoCliGap": f.dual,
                            "detail": f.detail,
                        }
                        for f in r.failures
                    ],
                }
                for r in results
            ],
        }
        with open(args.json_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)
        print(f"\nReport: {args.json_path}")

    if not cfg.keep:
        shutil.rmtree(run_root, ignore_errors=True)
    else:
        print(f"Sandboxes kept at {run_root}")

    return 1 if kpis["totals"]["fail"] else 0


if __name__ == "__main__":
    sys.exit(main())
