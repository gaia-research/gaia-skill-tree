"""Class A landing: a verified mirror repair becomes a reviewable branch.

The Class A executors in ``repairs.py`` already know how to repair a mirror in
place, but a repair that only ever lands in a throwaway checkout never reaches
anyone (architecture handover, section 0, defect 4).  This module is the last
inch: it performs the *same* repair inside a fresh, detached ``git worktree``
at the integration branch head, proves parity with the independent sensor,
commits exactly the executor's writable path on a deterministic branch, proves
parity again against the *committed tree*, and optionally pushes that branch.
It never opens a pull request and never merges; the runner emits
``forge.open_pr`` for a driver to perform.

Properties enforced here in code, not left to policy:

* **The target floor.**  ``main``, ``master``, the remote's default branch
  (asked of the remote itself, failing closed when it cannot answer) and any
  name outside ``[A-Za-z0-9._/-]+`` can never be a landing base.
* **The write floor.**  Only paths beneath the executor's writable path may
  enter the commit.  The staged set is asserted before anything is committed,
  and the committed tree is compared with the canonical tree afterwards.
* **The caller's checkout is never touched.**  All mutation happens in a
  temporary worktree outside the repository; the caller's working tree, index
  and HEAD are not read for content and not written.  The only repository-level
  effects are the remote-tracking ref of the base branch, the worktree's admin
  entry (removed again), and - until a push succeeds - the landing branch ref.
* **``steward/a/`` is Steward-owned.**  A local branch in that namespace that
  is not exactly one verified commit on the current base head is stale and is
  deleted and rebuilt; it can never wedge later runs.
"""

from __future__ import annotations

import contextlib
import hashlib
import os
import re
import shutil
import subprocess
import tempfile
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Mapping, Sequence

from gaia_cli.steward.mirrors import MirrorSpec, spec_by_id
from gaia_cli.steward.models import AuthorityClass, Debt
from gaia_cli.steward.policy import RepairExecutorPolicy, StewardPolicy
from gaia_cli.steward.repairs import RepairError, prepare_mirror_repair
from gaia_cli.steward.sensors import AgentSkillMirrorSensor, BundledSchemaMirrorSensor


LANDING_STATUSES = ("branch-pushed", "branch-committed", "already-exists", "no_change", "blocked")

COMMITTER_NAME = "Gaia Steward"
COMMITTER_EMAIL = "steward@gaiaskilltree.invalid"

_SAFE_REF = re.compile(r"[A-Za-z0-9._/-]+")
_FORBIDDEN_BASES = frozenset({"main", "master"})
_BRANCH_PREFIX = "steward/a/"
_ZERO_OID = "0" * 40
_REGULAR_MODES = frozenset({"100644", "100755"})
_HOOK_STUB_PATH = ".githooks/pre-commit"
_GIT_ENV_STRIP = (
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_PREFIX", "GIT_OBJECT_DIRECTORY",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES", "GIT_COMMON_DIR", "GIT_NAMESPACE",
)

# Independent parity proof per executor: the same sensor that observed the drift
# must now report the worktree healthy.
_SENSORS = {
    "agent-skill-mirror": AgentSkillMirrorSensor,
    "bundled-schema-mirror": BundledSchemaMirrorSensor,
}


class LandingError(RuntimeError):
    """A landing was refused before any mutation; nothing was pushed."""


@dataclass(frozen=True)
class LandingPlan:
    debt_id: str
    debt_kind: str
    executor_id: str
    base_branch: str
    branch: str
    fingerprint: str
    remote: str
    writable_path: str

    def to_dict(self) -> dict[str, str]:
        return {
            "debtId": self.debt_id,
            "debtKind": self.debt_kind,
            "executorId": self.executor_id,
            "baseBranch": self.base_branch,
            "branch": self.branch,
            "fingerprint": self.fingerprint,
            "remote": self.remote,
            "writablePath": self.writable_path,
        }


@dataclass(frozen=True)
class LandingResult:
    status: str
    plan: LandingPlan
    base_head: str | None
    commit: str | None
    repaired_paths: tuple[str, ...]
    verification: Mapping[str, object]
    reason: str

    def __post_init__(self) -> None:
        if self.status not in LANDING_STATUSES:
            raise ValueError(f"unknown landing status: {self.status}")

    def to_dict(self) -> dict[str, object]:
        return {
            "status": self.status,
            "plan": self.plan.to_dict(),
            "baseHead": self.base_head,
            "commit": self.commit,
            "repairedPaths": list(self.repaired_paths),
            "verification": dict(self.verification),
            "reason": self.reason,
        }


# --- git plumbing ------------------------------------------------------------


def _git_env() -> dict[str, str]:
    env = {key: value for key, value in os.environ.items() if key not in _GIT_ENV_STRIP}
    env["GIT_TERMINAL_PROMPT"] = "0"
    return env


def _git(
    cwd: Path,
    *args: str,
    check: bool = True,
    config: Sequence[str] = (),
    env: Mapping[str, str] | None = None,
) -> subprocess.CompletedProcess:
    # Hooks never run during a landing: not in the caller's repository, not in
    # the base we check out, for *any* git call (worktree add runs
    # post-checkout, commit runs commit-msg, push runs pre-push).  This is safe
    # because ``.githooks/pre-commit`` has been an ``exit 0`` stub since
    # 7756860e7 (version lockstep is enforced in CI by validate.yml, not by a
    # local hook), and ``_assert_hook_stub`` refuses to land if the base's
    # pre-commit stops being that stub - at which point this override would be
    # skipping a check somebody now relies on.
    command = ["git", "-c", f"core.hooksPath={os.devnull}"]
    for item in config:
        command.extend(["-c", item])
    command.extend(args)
    environment = _git_env()
    if env:
        environment.update(env)
    result = subprocess.run(
        command, cwd=cwd, env=environment, text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise subprocess.CalledProcessError(
            result.returncode, command, output=result.stdout, stderr=result.stderr
        )
    return result


@contextlib.contextmanager
def _without_git_env():
    """Temporarily drop repository-redirecting GIT_* variables, then restore them."""

    saved = {key: os.environ.pop(key) for key in _GIT_ENV_STRIP if key in os.environ}
    try:
        yield
    finally:
        os.environ.update(saved)


def _detail(error: subprocess.CalledProcessError) -> str:
    text = (error.stderr or error.output or "").strip().splitlines()
    return text[-1] if text else f"exit {error.returncode}"


def _validate_ref_name(name: str, label: str) -> str:
    if (
        not isinstance(name, str)
        or not name
        or not _SAFE_REF.fullmatch(name)
        or name.startswith(("-", "/", "."))
        or name.endswith(("/", ".", ".lock"))
        or ".." in name
        or "//" in name
    ):
        raise LandingError(f"{label} {name!r} is not a safe git ref name")
    return name


def _assert_remote(root: Path, remote: str) -> None:
    """The remote must be a configured remote name with a non-option URL."""

    _validate_ref_name(remote, "remote")
    result = _git(root, "remote", "get-url", remote, check=False)
    if result.returncode:
        raise LandingError(f"remote {remote!r} is not configured in this repository")
    url = result.stdout.strip()
    if not url or url.startswith("-"):
        raise LandingError(f"remote {remote!r} has an unsafe URL")


def _remote_default_branch(root: Path, remote: str) -> str:
    """Ask the remote itself which branch is its default; fail closed."""

    result = _git(root, "ls-remote", "--symref", remote, "HEAD", check=False)
    if result.returncode:
        raise LandingError(
            f"cannot determine the default branch of {remote!r} "
            f"({result.stderr.strip().splitlines()[-1] if result.stderr.strip() else result.returncode}); "
            "refusing to land without it"
        )
    prefix = "ref: refs/heads/"
    for line in result.stdout.splitlines():
        if line.startswith(prefix):
            name = line[len(prefix):].split("\t")[0].strip()
            if name:
                return name
    raise LandingError(
        f"{remote!r} did not report a default branch; refusing to land without it"
    )


def _local_default_branch(root: Path, remote: str) -> str | None:
    result = _git(root, "symbolic-ref", "--quiet", f"refs/remotes/{remote}/HEAD", check=False)
    if result.returncode:
        return None
    prefix = f"refs/remotes/{remote}/"
    ref = result.stdout.strip()
    return ref[len(prefix):] if ref.startswith(prefix) else None


def _assert_base_allowed(root: Path, base_branch: str, remote: str) -> None:
    """The hard target floor. Nothing in policy can relax it."""

    _validate_ref_name(base_branch, "base branch")
    _assert_remote(root, remote)
    if base_branch in _FORBIDDEN_BASES:
        raise LandingError(f"refusing to land on protected branch {base_branch!r}")
    default = _remote_default_branch(root, remote)
    if base_branch == default:
        raise LandingError(f"refusing to land on the remote default branch {default!r}")
    local = _local_default_branch(root, remote)
    if local is not None and base_branch == local:
        raise LandingError(f"refusing to land on the remote default branch {local!r}")


def _fetch_base(root: Path, remote: str, base_branch: str) -> str:
    refspec = f"+refs/heads/{base_branch}:refs/remotes/{remote}/{base_branch}"
    try:
        _git(root, "fetch", "--quiet", remote, refspec)
        return _git(root, "rev-parse", "--verify", f"refs/remotes/{remote}/{base_branch}^{{commit}}").stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise LandingError(f"cannot fetch {remote}/{base_branch}: {_detail(exc)}") from exc


def _assert_hook_stub(root: Path, commit: str) -> None:
    """Tripwire for the uniform hooks override (see ``_git``)."""

    listing = _git(root, "ls-tree", commit, "--", _HOOK_STUB_PATH, check=False)
    if listing.returncode or not listing.stdout.strip():
        return  # no pre-commit hook exists in the base: nothing is being skipped
    shown = _git(root, "cat-file", "-p", f"{commit}:{_HOOK_STUB_PATH}", check=False)
    meaningful = [
        line.strip() for line in shown.stdout.splitlines()
        if line.strip() and not line.strip().startswith("#")
    ]
    if shown.returncode or meaningful != ["exit 0"]:
        raise LandingError(
            f"{_HOOK_STUB_PATH} on the base is no longer an 'exit 0' stub; Steward landings "
            "disable git hooks and refuse to land until that assumption is re-reviewed"
        )


def _tree_entries(root: Path, rev: str, path: str) -> dict[str, tuple[str, str, str]]:
    """``{relative path: (mode, kind, oid)}`` for one directory of one revision."""

    try:
        listing = _git(root, "ls-tree", "-r", "-z", rev, "--", path).stdout
    except subprocess.CalledProcessError as exc:
        raise LandingError(f"cannot read tree {path} at {rev[:12]}: {_detail(exc)}") from exc
    prefix = path + "/"
    entries: dict[str, tuple[str, str, str]] = {}
    for entry in filter(None, listing.split("\0")):
        meta, _, name = entry.partition("\t")
        if not name.startswith(prefix):
            continue
        mode, kind, oid = meta.split()
        entries[name[len(prefix):]] = (mode, kind, oid)
    return entries


def _canonical_digest(root: Path, spec: MirrorSpec, commit: str) -> str:
    """Digest of the canonical side as committed at ``commit`` (no checkout)."""

    rows = [
        f"{relative}\0{oid}"
        for relative, (_mode, _kind, oid) in _tree_entries(root, commit, spec.canonical_root).items()
        if not spec.is_ignored(relative)
    ]
    return hashlib.sha256("\n".join(sorted(rows)).encode("utf-8")).hexdigest()


def _fingerprint(debt_id: str, canonical_digest: str) -> str:
    return hashlib.sha256(f"{debt_id}\0{canonical_digest}".encode("utf-8")).hexdigest()


def _branch_name(debt_kind: str, fingerprint: str) -> str:
    return f"{_BRANCH_PREFIX}{debt_kind.replace('_', '-')}-{fingerprint[:12]}"


def _verify_commit(root: Path, spec: MirrorSpec, commit: str, base_head: str) -> str | None:
    """Prove a *committed* tree equals canonical; return why not, or None.

    The sensor and ``--check`` read the filesystem, which can disagree with what
    git actually recorded (ignore rules, attributes).  This reads the commit
    object itself: exactly one non-merge commit on ``base_head``, touching only
    the mirror root, regular file modes only, and the mirror tree identical -
    blob ids and modes - to the canonical tree at ``base_head`` under the
    executor's ignore spec.  Locally owned (ignored) mirror paths must be
    unchanged from the base.
    """

    try:
        revs = _git(root, "rev-list", "--parents", "-n", "1", commit).stdout.split()
        if len(revs) != 2 or revs[0] != commit or revs[1] != base_head:
            return "landing commit is not exactly one non-merge commit on the base head"
        changed = [
            item for item in
            _git(root, "diff-tree", "-r", "--no-commit-id", "--name-only", "-z", base_head, commit).stdout.split("\0")
            if item
        ]
        if not changed:
            return "landing commit changes nothing"
        outside = sorted(item for item in changed if not item.startswith(spec.mirror_root + "/"))
        if outside:
            return "landing commit touches paths outside the writable path: " + ", ".join(outside[:5])
        mirror = _tree_entries(root, commit, spec.mirror_root)
        base_mirror = _tree_entries(root, base_head, spec.mirror_root)
        canonical = _tree_entries(root, base_head, spec.canonical_root)
    except subprocess.CalledProcessError as exc:
        return f"cannot inspect landing commit: {_detail(exc)}"
    except LandingError as exc:
        return str(exc)
    for label, tree in (("mirror", mirror), ("canonical", canonical)):
        bad = sorted(
            relative for relative, (mode, kind, _oid) in tree.items()
            if kind != "blob" or mode not in _REGULAR_MODES
        )
        if bad:
            return f"{label} tree has non-regular entries: " + ", ".join(bad[:5])
    want = {
        relative: (mode, oid) for relative, (mode, _kind, oid) in canonical.items()
        if not spec.is_ignored(relative)
    }
    have = {
        relative: (mode, oid) for relative, (mode, _kind, oid) in mirror.items()
        if not spec.is_ignored(relative)
    }
    if want != have:
        diff = sorted(set(want) ^ set(have) | {key for key in set(want) & set(have) if want[key] != have[key]})
        return "committed mirror tree differs from canonical: " + ", ".join(diff[:5])
    owned = {relative: value for relative, value in mirror.items() if spec.is_ignored(relative)}
    owned_base = {relative: value for relative, value in base_mirror.items() if spec.is_ignored(relative)}
    if owned != owned_base:
        return "committed tree changes locally owned mirror paths"
    return None


def _resolve_executor(policy: StewardPolicy, debt: Debt) -> tuple[RepairExecutorPolicy, MirrorSpec]:
    if debt.authority is not AuthorityClass.A:
        raise LandingError(f"{debt.id} is Class {debt.authority.value}; only Class A debt lands")
    try:
        policy_authority = policy.authority_for(debt.kind)
    except Exception as exc:  # PolicyError: unclassified kinds are never repaired
        raise LandingError(f"{debt.kind} is not classified by policy: {exc}") from exc
    if policy_authority is not AuthorityClass.A:
        raise LandingError(f"policy classifies {debt.kind} as Class {policy_authority.value}, not A")
    executor = policy.executor_for(debt.kind)
    if executor is None:
        raise LandingError(f"policy has no repair executor for {debt.kind}")
    if executor.authority is not AuthorityClass.A:
        raise LandingError(f"executor {executor.id} is not Class A")
    spec = spec_by_id(executor.id)
    if spec is None or spec.debt_kind != debt.kind:
        raise LandingError(f"no registered Class A repair implements executor {executor.id}")
    if executor.canonical_path != spec.canonical_glob or executor.writable_path != spec.writable_glob:
        raise LandingError(f"{executor.id} policy does not match its fixed authority envelope")
    return executor, spec


# --- plan --------------------------------------------------------------------


def plan_class_a_landing(
    repo_root: Path,
    policy: StewardPolicy,
    debt: Debt,
    *,
    base_branch: str,
    remote: str = "origin",
) -> LandingPlan:
    """Decide where a Class A repair would land, deterministically.

    Fetches the base branch (updating only the remote-tracking ref) so the
    branch name can bind the debt to the exact canonical content it would be
    repaired against: same drift on the same base always maps to the same
    branch; new canonical content maps to a new one.
    """

    root = Path(repo_root).resolve()
    executor, spec = _resolve_executor(policy, debt)
    _assert_base_allowed(root, base_branch, remote)
    head = _fetch_base(root, remote, base_branch)
    _assert_hook_stub(root, head)
    fingerprint = _fingerprint(debt.id, _canonical_digest(root, spec, head))
    return LandingPlan(
        debt_id=debt.id,
        debt_kind=debt.kind,
        executor_id=executor.id,
        base_branch=base_branch,
        branch=_branch_name(debt.kind, fingerprint),
        fingerprint=fingerprint,
        remote=remote,
        writable_path=spec.mirror_root,
    )


# --- execute -----------------------------------------------------------------


def _result(
    status: str, plan: LandingPlan, reason: str, *,
    base_head: str | None = None, commit: str | None = None,
    repaired: Sequence[str] = (), verification: Mapping[str, object] | None = None,
) -> LandingResult:
    return LandingResult(
        status=status, plan=plan, base_head=base_head, commit=commit,
        repaired_paths=tuple(repaired), verification=dict(verification or {}), reason=reason,
    )


def _remote_branch_head(root: Path, plan: LandingPlan) -> str | None:
    result = _git(root, "ls-remote", "--heads", plan.remote, f"refs/heads/{plan.branch}", check=False)
    if result.returncode:
        raise LandingError(f"cannot query {plan.remote} for {plan.branch}: {result.stderr.strip()}")
    line = result.stdout.strip().splitlines()
    return line[0].split()[0] if line else None


def _local_branch_head(root: Path, branch: str) -> str | None:
    result = _git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{branch}^{{commit}}", check=False)
    return result.stdout.strip() if result.returncode == 0 else None


def _commit_message(plan: LandingPlan, executor_id: str, paths: Sequence[str]) -> str:
    listed = "\n".join(f"- {path}" for path in paths[:40])
    more = f"\n- ... and {len(paths) - 40} more" if len(paths) > 40 else ""
    return (
        f"chore(steward): repair {plan.debt_kind} ({executor_id})\n\n"
        f"Class A mechanical mirror repair on {plan.remote}/{plan.base_branch}.\n"
        f"Changed paths ({len(paths)}):\n{listed}{more}\n\n"
        f"Steward-Debt: {plan.debt_id}\n"
        f"Steward-Executor: {executor_id}\n"
    )


def _cleanup(root: Path, scratch: Path, worktree: Path) -> None:
    """Remove our own worktree and nothing else.

    Never ``git worktree prune``: that deletes the admin data of every *other*
    worktree whose directory is momentarily missing (moved, unmounted drive).
    """

    admin: Path | None = None
    try:
        text = (worktree / ".git").read_text(encoding="utf-8")
        if text.startswith("gitdir:"):
            admin = Path(text.split(":", 1)[1].strip())
    except OSError:
        pass
    try:
        removed = _git(root, "worktree", "remove", "--force", str(worktree), check=False).returncode == 0
    except OSError:
        removed = False
    shutil.rmtree(scratch, ignore_errors=True)
    if removed or admin is None:
        return
    # git could not remove it; delete only the admin entry that is provably ours.
    try:
        common = Path(_git(root, "rev-parse", "--git-common-dir", check=False).stdout.strip())
        common = common if common.is_absolute() else root / common
        if admin.resolve().parent == (common / "worktrees").resolve():
            shutil.rmtree(admin, ignore_errors=True)
    except OSError:
        pass


def execute_class_a_landing(
    repo_root: Path,
    policy: StewardPolicy,
    plan: LandingPlan,
    *,
    push: bool,
) -> LandingResult:
    """Repair in a throwaway worktree, commit the writable path, optionally push.

    Raises ``LandingError`` when the plan itself is unacceptable (nothing was
    done).  Everything discovered while working - an unprovable repair, a
    dirty mirror, an out-of-envelope diff - is returned as ``blocked`` with the
    reason, and nothing is committed or pushed.
    """

    root = Path(repo_root).resolve()
    # Re-derive authority from live policy and the debt kind rather than
    # trusting the plan object: a plan is data and may be stale or hand-built.
    try:
        executor = policy.executor_for(plan.debt_kind)
        policy_authority = policy.authority_for(plan.debt_kind)
    except Exception as exc:
        raise LandingError(f"policy does not authorize {plan.debt_kind}: {exc}") from exc
    spec = spec_by_id(executor.id) if executor is not None else None
    if executor is None or spec is None or executor.id != plan.executor_id:
        raise LandingError(f"policy no longer authorizes executor {plan.executor_id} for {plan.debt_kind}")
    if executor.authority is not AuthorityClass.A or policy_authority is not AuthorityClass.A:
        raise LandingError(f"{plan.debt_kind} is not Class A")
    if executor.canonical_path != spec.canonical_glob or executor.writable_path != spec.writable_glob:
        raise LandingError(f"{executor.id} policy does not match its fixed authority envelope")
    if plan.writable_path != spec.mirror_root:
        raise LandingError("plan writable path does not match the executor's writable path")
    _validate_ref_name(plan.branch, "landing branch")
    if not plan.branch.startswith(_BRANCH_PREFIX) or plan.branch == plan.base_branch:
        raise LandingError(f"landing branch {plan.branch!r} is outside {_BRANCH_PREFIX}")
    _assert_base_allowed(root, plan.base_branch, plan.remote)

    base_head = _fetch_base(root, plan.remote, plan.base_branch)
    _assert_hook_stub(root, base_head)
    current = _fingerprint(plan.debt_id, _canonical_digest(root, spec, base_head))
    if current != plan.fingerprint:
        return _result(
            "blocked", plan,
            "canonical content on the base branch changed since planning; re-plan",
            base_head=base_head,
        )
    if plan.branch != _branch_name(plan.debt_kind, current):
        raise LandingError("landing branch does not derive from the debt fingerprint")

    existing = _remote_branch_head(root, plan)
    if existing is not None:
        return _result(
            "already-exists", plan,
            f"{plan.remote}/{plan.branch} already exists; not committing or pushing again",
            base_head=base_head, commit=existing,
        )

    local = _local_branch_head(root, plan.branch)
    if local is not None:
        problem = _verify_commit(root, spec, local, base_head)
        if problem is None:
            return _resume_local_branch(root, plan, base_head, local, push)
        # Stale: the namespace is Steward-owned, so rebuild rather than wedge.
        dropped = _git(root, "branch", "-D", plan.branch, check=False)
        if dropped.returncode:
            return _result(
                "blocked", plan,
                f"stale local branch {plan.branch} ({problem}) could not be deleted: "
                f"{dropped.stderr.strip()[-160:]}",
                base_head=base_head, commit=local,
            )

    scratch = Path(tempfile.mkdtemp(prefix="gaia-steward-landing-")).resolve()
    worktree = scratch / "wt"
    try:
        try:
            _git(root, "worktree", "add", "--quiet", "--detach", str(worktree), base_head)
        except subprocess.CalledProcessError as exc:
            return _result("blocked", plan, f"cannot create landing worktree: {_detail(exc)}", base_head=base_head)
        return _land_in_worktree(root, worktree, plan, executor, spec, base_head, push)
    finally:
        _cleanup(root, scratch, worktree)


def _push_branch(
    root: Path, plan: LandingPlan, base_head: str, commit: str,
    repaired: Sequence[str], verification: Mapping[str, object], *, resumed: bool,
) -> LandingResult:
    """Push the landing branch (never forced) and classify what happened."""

    refspec = f"refs/heads/{plan.branch}:refs/heads/{plan.branch}"
    pushed = _git(root, "push", "--quiet", plan.remote, refspec, check=False)
    if pushed.returncode == 0:
        # The branch now lives on the remote; the local ref has served its purpose.
        _git(root, "update-ref", "-d", f"refs/heads/{plan.branch}", commit, check=False)
        return _result(
            "branch-pushed", plan,
            f"pushed {'existing local branch to ' if resumed else ''}{plan.remote}/{plan.branch}",
            base_head=base_head, commit=commit, repaired=repaired, verification=verification,
        )
    detail = pushed.stderr.strip().splitlines()[-1] if pushed.stderr.strip() else str(pushed.returncode)
    # A concurrent run may have created the branch between our check and our
    # push. The push was refused (never forced); report the truth.
    try:
        raced = _remote_branch_head(root, plan)
    except LandingError as exc:
        return _result(
            "blocked", plan, f"push to {plan.remote} was refused ({detail}) and the remote "
            f"could not be queried afterwards: {exc}",
            base_head=base_head, commit=commit, repaired=repaired, verification=verification,
        )
    if raced is not None:
        return _result(
            "already-exists", plan, f"{plan.remote}/{plan.branch} appeared during landing; nothing overwritten",
            base_head=base_head, commit=raced, verification=verification,
        )
    return _result(
        "blocked", plan, f"push to {plan.remote} was refused: {detail}",
        base_head=base_head, commit=commit, repaired=repaired, verification=verification,
    )


def _resume_local_branch(
    root: Path, plan: LandingPlan, base_head: str, head: str, push: bool,
) -> LandingResult:
    """A verified local branch from an earlier unpushed run."""

    changed = [
        item for item in
        _git(root, "diff-tree", "-r", "--no-commit-id", "--name-only", "-z", base_head, head, check=False).stdout.split("\0")
        if item
    ]
    verification = {"resumed": True, "stagedPaths": sorted(changed)}
    if not push:
        return _result(
            "already-exists", plan, f"local branch {plan.branch} already holds this repair",
            base_head=base_head, commit=head, repaired=sorted(changed), verification=verification,
        )
    return _push_branch(root, plan, base_head, head, sorted(changed), verification, resumed=True)


def _land_in_worktree(
    root: Path,
    worktree: Path,
    plan: LandingPlan,
    executor: RepairExecutorPolicy,
    spec: MirrorSpec,
    base_head: str,
    push: bool,
) -> LandingResult:
    def blocked(reason: str, **extra: object) -> LandingResult:
        return _result("blocked", plan, reason, base_head=base_head, **extra)  # type: ignore[arg-type]

    try:
        # ``repairs.py`` shells out to git with the ambient environment; a stray
        # GIT_DIR / GIT_INDEX_FILE would point its cleanliness check elsewhere.
        with _without_git_env():
            transaction = prepare_mirror_repair(worktree, executor, state_root=worktree / ".gaia" / "steward")
    except RepairError as exc:  # RepairBlocked is a subclass
        return blocked(f"repair refused: {exc}")
    if transaction is None:
        return _result(
            "no_change", plan, "mirror already matches canonical on the base branch",
            base_head=base_head, verification={"executor": executor.id, "parity": True},
        )
    try:
        receipt = transaction.receipt()
        transaction.commit()
    except RepairError as exc:
        return blocked(f"repair could not be retained: {exc}")
    repaired = tuple(
        f"{spec.mirror_root}/{path}" for path in sorted(str(item) for item in receipt["repairedPaths"])  # type: ignore[union-attr]
    )

    # Filesystem proof: the sensor that raised the debt must now agree.
    sensor = _SENSORS[executor.id]()
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    statuses = [item.status for item in sensor.scan(worktree, observed_at)]
    verification: dict[str, object] = {
        "executor": executor.id,
        "recursiveParity": True,
        "syncCheck": True,
        "sensor": sensor.id,
        "sensorStatus": "healthy" if statuses and all(item == "healthy" for item in statuses) else "drift",
    }
    if verification["sensorStatus"] != "healthy":
        return blocked("post-repair sensor did not report parity", repaired=repaired, verification=verification)

    try:
        # -f: canonical files that are tracked in the base but match an ignore
        # rule must still be mirrored; the committed-tree proof below is the gate.
        _git(worktree, "add", "-f", "--", spec.mirror_root)
        staged = [
            item for item in
            _git(worktree, "diff", "--cached", "--name-only", "-z").stdout.split("\0") if item
        ]
    except subprocess.CalledProcessError as exc:
        return blocked(f"cannot stage the writable path: {_detail(exc)}", repaired=repaired, verification=verification)
    outside = [item for item in staged if not item.startswith(spec.mirror_root + "/")]
    if outside:
        return blocked(
            "staged paths outside the executor writable path: " + ", ".join(sorted(outside)),
            repaired=repaired, verification=verification,
        )
    if not staged:
        return _result(
            "no_change", plan, "repair changed no tracked path under the writable path",
            base_head=base_head, repaired=repaired, verification=verification,
        )
    verification = {**verification, "stagedPaths": sorted(staged)}

    # Commit on a detached HEAD: no branch ref exists until the commit has
    # succeeded *and* been verified, so a failed commit can never leak a ref.
    try:
        _git(
            worktree, "commit", "--quiet", "-m", _commit_message(plan, executor.id, sorted(staged)),
            config=("commit.gpgsign=false",),
            env={
                "GIT_AUTHOR_NAME": COMMITTER_NAME, "GIT_AUTHOR_EMAIL": COMMITTER_EMAIL,
                "GIT_COMMITTER_NAME": COMMITTER_NAME, "GIT_COMMITTER_EMAIL": COMMITTER_EMAIL,
            },
        )
        commit = _git(worktree, "rev-parse", "HEAD").stdout.strip()
    except subprocess.CalledProcessError as exc:
        return blocked(f"cannot commit: {_detail(exc)}", repaired=repaired, verification=verification)

    # Committed-tree proof (not the filesystem): what git recorded must equal canonical.
    problem = _verify_commit(root, spec, commit, base_head)
    if problem is not None:
        return blocked(f"committed tree failed verification: {problem}", repaired=repaired, verification=verification)
    verification = {**verification, "committedTree": True}

    created = _git(root, "update-ref", f"refs/heads/{plan.branch}", commit, _ZERO_OID, check=False)
    if created.returncode:
        return blocked(
            f"cannot create local branch {plan.branch}: {created.stderr.strip()[-160:]}",
            repaired=repaired, verification=verification,
        )
    if not push:
        return _result(
            "branch-committed", plan, f"committed on local branch {plan.branch}; not pushed",
            base_head=base_head, commit=commit, repaired=staged, verification=verification,
        )
    return _push_branch(root, plan, base_head, commit, staged, verification, resumed=False)
