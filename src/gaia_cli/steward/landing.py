"""Class A landing: a verified mirror repair becomes a reviewable branch.

The Class A executors in ``repairs.py`` already know how to repair a mirror in
place, but a repair that only ever lands in a throwaway checkout never reaches
anyone (architecture handover, section 0, defect 4).  This module is the last
inch: it performs the *same* repair inside a fresh, detached ``git worktree``
at the integration branch head, proves parity with the independent sensor,
commits exactly the executor's writable path on a deterministic branch, and
optionally pushes that branch.  It never opens a pull request and never merges;
the runner emits ``forge.open_pr`` for a driver to perform.

Three properties are enforced here in code, not left to policy:

* **The target floor.**  ``main``, ``master``, the remote's default branch and
  any name outside ``[A-Za-z0-9._/-]+`` can never be a landing base.  Policy
  cannot widen this.
* **The write floor.**  Only paths beneath the executor's writable path may
  enter the commit.  The staged set is asserted before anything is committed.
* **The caller's checkout is never touched.**  All mutation happens in a
  temporary worktree outside the repository; the caller's working tree, index
  and HEAD are not read for content and not written.
"""

from __future__ import annotations

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
    cwd: Path, *args: str, check: bool = True, config: Sequence[str] = ()
) -> subprocess.CompletedProcess:
    command = ["git"]
    for item in config:
        command.extend(["-c", item])
    command.extend(args)
    result = subprocess.run(
        command, cwd=cwd, env=_git_env(), text=True, capture_output=True, check=False
    )
    if check and result.returncode:
        raise subprocess.CalledProcessError(
            result.returncode, command, output=result.stdout, stderr=result.stderr
        )
    return result


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


def _default_branch(root: Path, remote: str) -> str | None:
    result = _git(root, "symbolic-ref", "--quiet", f"refs/remotes/{remote}/HEAD", check=False)
    if result.returncode:
        return None
    prefix = f"refs/remotes/{remote}/"
    ref = result.stdout.strip()
    return ref[len(prefix):] if ref.startswith(prefix) else None


def _assert_base_allowed(root: Path, base_branch: str, remote: str) -> None:
    """The hard target floor. Nothing in policy can relax it."""

    _validate_ref_name(base_branch, "base branch")
    _validate_ref_name(remote, "remote")
    if base_branch in _FORBIDDEN_BASES:
        raise LandingError(f"refusing to land on protected branch {base_branch!r}")
    default = _default_branch(root, remote)
    if default is not None and base_branch == default:
        raise LandingError(f"refusing to land on the remote default branch {default!r}")


def _fetch_base(root: Path, remote: str, base_branch: str) -> str:
    refspec = f"+refs/heads/{base_branch}:refs/remotes/{remote}/{base_branch}"
    try:
        _git(root, "fetch", "--quiet", remote, refspec)
        return _git(root, "rev-parse", "--verify", f"refs/remotes/{remote}/{base_branch}^{{commit}}").stdout.strip()
    except subprocess.CalledProcessError as exc:
        raise LandingError(f"cannot fetch {remote}/{base_branch}: {_detail(exc)}") from exc


def _canonical_digest(root: Path, spec: MirrorSpec, commit: str) -> str:
    """Digest of the canonical side as committed at ``commit`` (no checkout)."""

    try:
        listing = _git(root, "ls-tree", "-r", "-z", commit, "--", spec.canonical_root).stdout
    except subprocess.CalledProcessError as exc:
        raise LandingError(f"cannot read canonical tree at {commit[:12]}: {_detail(exc)}") from exc
    prefix = spec.canonical_root + "/"
    rows: list[str] = []
    for entry in filter(None, listing.split("\0")):
        meta, _, path = entry.partition("\t")
        if not path.startswith(prefix):
            continue
        relative = path[len(prefix):]
        if spec.is_ignored(relative):
            continue
        rows.append(f"{relative}\0{meta.split()[2]}")
    return hashlib.sha256("\n".join(sorted(rows)).encode("utf-8")).hexdigest()


def _fingerprint(debt_id: str, canonical_digest: str) -> str:
    return hashlib.sha256(f"{debt_id}\0{canonical_digest}".encode("utf-8")).hexdigest()


def _branch_name(debt_kind: str, fingerprint: str) -> str:
    return f"{_BRANCH_PREFIX}{debt_kind.replace('_', '-')}-{fingerprint[:12]}"


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
    try:
        _git(root, "worktree", "remove", "--force", str(worktree), check=False)
        _git(root, "worktree", "prune", check=False)
    finally:
        shutil.rmtree(scratch, ignore_errors=True)


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
    executor = policy.executor_for(plan.debt_kind)
    spec = spec_by_id(executor.id) if executor is not None else None
    if executor is None or spec is None or executor.id != plan.executor_id:
        raise LandingError(f"policy no longer authorizes executor {plan.executor_id} for {plan.debt_kind}")
    if executor.authority is not AuthorityClass.A or policy.authority_for(plan.debt_kind) is not AuthorityClass.A:
        raise LandingError(f"{plan.debt_kind} is not Class A")
    if executor.canonical_path != spec.canonical_glob or executor.writable_path != spec.writable_glob:
        raise LandingError(f"{executor.id} policy does not match its fixed authority envelope")
    if plan.writable_path != spec.mirror_root:
        raise LandingError("plan writable path does not match the executor's writable path")
    _assert_base_allowed(root, plan.base_branch, plan.remote)
    _validate_ref_name(plan.branch, "landing branch")
    if not plan.branch.startswith(_BRANCH_PREFIX) or plan.branch == plan.base_branch:
        raise LandingError(f"landing branch {plan.branch!r} is outside {_BRANCH_PREFIX}")

    base_head = _fetch_base(root, plan.remote, plan.base_branch)
    current = _fingerprint(plan.debt_id, _canonical_digest(root, spec, base_head))
    if current != plan.fingerprint:
        return _result(
            "blocked", plan,
            "canonical content on the base branch changed since planning; re-plan",
            base_head=base_head,
        )

    existing = _remote_branch_head(root, plan)
    if existing is not None:
        return _result(
            "already-exists", plan,
            f"{plan.remote}/{plan.branch} already exists; not committing or pushing again",
            base_head=base_head, commit=existing,
        )

    local = _git(root, "rev-parse", "--verify", "--quiet", f"refs/heads/{plan.branch}^{{commit}}", check=False)
    if local.returncode == 0:
        return _resume_local_branch(root, spec, plan, base_head, local.stdout.strip(), push)

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


def _resume_local_branch(
    root: Path, spec: MirrorSpec, plan: LandingPlan, base_head: str, head: str, push: bool,
) -> LandingResult:
    """A local branch from an earlier unpushed run: reuse it only if it is exact."""

    parent = _git(root, "rev-parse", "--verify", "--quiet", f"{head}^", check=False).stdout.strip()
    changed = [
        item for item in
        _git(root, "diff", "--name-only", "-z", base_head, head, check=False).stdout.split("\0") if item
    ]
    if parent != base_head or not changed or any(not item.startswith(spec.mirror_root + "/") for item in changed):
        return _result(
            "blocked", plan,
            f"local branch {plan.branch} exists but is not a single steward commit on the base head",
            base_head=base_head, commit=head,
        )
    if not push:
        return _result(
            "already-exists", plan, f"local branch {plan.branch} already holds this repair",
            base_head=base_head, commit=head, repaired=changed,
        )
    pushed = _git(root, "push", "--quiet", plan.remote, f"refs/heads/{plan.branch}:refs/heads/{plan.branch}", check=False)
    if pushed.returncode:
        return _result(
            "blocked", plan, f"push to {plan.remote} was refused: {pushed.stderr.strip()[-200:]}",
            base_head=base_head, commit=head, repaired=changed,
        )
    return _result(
        "branch-pushed", plan, f"pushed existing local branch to {plan.remote}/{plan.branch}",
        base_head=base_head, commit=head, repaired=changed,
    )


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

    # Independent parity proof: the sensor that raised the debt must now agree.
    sensor = _SENSORS[executor.id]()
    observed_at = datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")
    statuses = [item.status for item in sensor.scan(worktree, observed_at)]
    verification = {
        "executor": executor.id,
        "recursiveParity": True,
        "syncCheck": True,
        "sensor": sensor.id,
        "sensorStatus": "healthy" if statuses and all(item == "healthy" for item in statuses) else "drift",
    }
    if verification["sensorStatus"] != "healthy":
        return blocked("post-repair sensor did not report parity", repaired=repaired, verification=verification)

    try:
        _git(worktree, "add", "--", spec.mirror_root)
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

    try:
        _git(worktree, "checkout", "--quiet", "-b", plan.branch)
        _git(
            worktree, "commit", "--quiet", "-m", _commit_message(plan, executor.id, sorted(staged)),
            config=(
                f"user.name={COMMITTER_NAME}", f"user.email={COMMITTER_EMAIL}",
                "commit.gpgsign=false", f"core.hooksPath={os.devnull}",
            ),
        )
        commit = _git(worktree, "rev-parse", "HEAD").stdout.strip()
    except subprocess.CalledProcessError as exc:
        return blocked(f"cannot commit on {plan.branch}: {_detail(exc)}", repaired=repaired, verification=verification)

    if not push:
        return _result(
            "branch-committed", plan, f"committed on local branch {plan.branch}; not pushed",
            base_head=base_head, commit=commit, repaired=staged, verification=verification,
        )
    pushed = _git(worktree, "push", "--quiet", plan.remote, f"refs/heads/{plan.branch}:refs/heads/{plan.branch}", check=False)
    if pushed.returncode:
        # A concurrent run may have created the branch between our check and
        # our push. The push was refused (never forced); report the truth.
        raced = _remote_branch_head(root, plan)
        if raced is not None:
            return _result(
                "already-exists", plan, f"{plan.remote}/{plan.branch} appeared during landing; nothing overwritten",
                base_head=base_head, commit=raced, verification=verification,
            )
        return blocked(
            f"push to {plan.remote} was refused: {pushed.stderr.strip().splitlines()[-1] if pushed.stderr.strip() else pushed.returncode}",
            repaired=staged, verification=verification,
        )
    return _result(
        "branch-pushed", plan, f"pushed {plan.remote}/{plan.branch}",
        base_head=base_head, commit=commit, repaired=staged, verification=verification,
    )
