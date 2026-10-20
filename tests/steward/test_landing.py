"""Class A landing: a verified mirror repair becomes a reviewable branch.

Every test uses a real fixture repository with genuine agent-skill mirror drift
and a local bare remote in ``tmp_path``.  Nothing here can reach a real origin.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

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
