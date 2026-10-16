from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import yaml

from gaia_cli.steward.repository_hygiene import (
    RepositoryHygieneSensor,
    RepositoryInventoryError,
)


NOW = "2026-10-15T00:00:00Z"


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


def _repo(root: Path) -> Path:
    root.mkdir(parents=True, exist_ok=True)
    _git(root, "init", "--quiet")
    _git(root, "config", "user.name", "Test")
    _git(root, "config", "user.email", "test@example.invalid")
    (root / "README.md").write_text("fixture\n", encoding="utf-8")
    _git(root, "add", "README.md")
    _git(root, "commit", "--quiet", "-m", "fixture")
    return root


def _observation(root: Path, at: str = NOW):
    return RepositoryHygieneSensor().scan(root, at)[0]


def test_clean_git_repository_is_healthy_and_identity_digest_are_stable(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")

    first = _observation(root)
    second = _observation(root, "2026-10-16T00:00:00Z")

    assert first.status == "healthy"
    assert first.kind == "repository_hygiene"
    assert first.source == "repository-hygiene"
    assert first.subject.id == "tracked-class-p-artifacts"
    assert first.debt_id == second.debt_id
    assert first.observed_state["inventoryDigest"] == second.observed_state["inventoryDigest"]
    assert first.observed_state["trackedLeakPaths"] == []


def test_explicit_tracked_class_p_path_is_reported_as_drift(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    (root / "registry").mkdir()
    (root / "registry/gaia.json").write_text("{}\n", encoding="utf-8")
    _git(root, "add", "registry/gaia.json")

    observation = _observation(root)

    assert observation.status == "drift"
    assert observation.observed_state["trackedLeakPaths"] == ["registry/gaia.json"]


def test_known_tracked_catalogs_are_negative_controls_not_leaks(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    files = (
        "registry/real-skills.json",
        "registry/real-skills.md",
        "src/gaia_cli/data/registry/benchmark-sources.json",
    )
    for relative in files:
        path = root / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("intentional tracked catalog\n", encoding="utf-8")
    _git(root, "add", *files)

    observation = _observation(root)

    assert observation.status == "healthy"
    assert observation.observed_state["trackedLeakPaths"] == []
    assert observation.provenance["excludedTrackedCatalogs"] == list(files)


def test_class_s_assets_are_not_inventoried(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    path = root / "docs/graph/gaia.json"
    path.parent.mkdir(parents=True)
    path.write_text("{}\n", encoding="utf-8")
    _git(root, "add", "docs/graph/gaia.json")

    observation = _observation(root)

    assert observation.status == "healthy"
    assert observation.observed_state["trackedLeakPaths"] == []
    assert observation.provenance["excludedClassSDirectory"] == "docs/graph/**"


def test_linked_worktree_root_is_validated_as_its_own_repository_root(tmp_path: Path) -> None:
    primary = _repo(tmp_path / "primary")
    linked = tmp_path / "linked-worktree"
    _git(primary, "worktree", "add", "--quiet", "-b", "fixture-linked", str(linked))

    observation = _observation(linked)

    assert observation.status == "healthy"
    assert observation.provenance["command"].startswith("git ls-files")


def test_non_root_path_is_rejected(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    subdirectory = root / "nested"
    subdirectory.mkdir()

    with pytest.raises(RepositoryInventoryError, match="worktree root"):
        _observation(subdirectory)


def test_non_repository_root_is_rejected(tmp_path: Path) -> None:
    with pytest.raises(RepositoryInventoryError):
        _observation(tmp_path)


@pytest.mark.parametrize(
    "failure",
    [
        FileNotFoundError("git unavailable"),
        subprocess.TimeoutExpired(cmd="git", timeout=5),
    ],
)
def test_unavailable_or_timed_out_git_inventory_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, failure: BaseException
) -> None:
    root = _repo(tmp_path / "repo")

    def fail(*args, **kwargs):
        raise failure

    monkeypatch.setattr("gaia_cli.steward.repository_hygiene.subprocess.run", fail)
    with pytest.raises(RepositoryInventoryError):
        _observation(root)


def test_failed_git_inventory_fails_closed(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo(tmp_path / "repo")
    result = subprocess.CompletedProcess(args=["git"], returncode=2, stdout=b"", stderr=b"index error")
    monkeypatch.setattr("gaia_cli.steward.repository_hygiene.subprocess.run", lambda *a, **k: result)

    with pytest.raises(RepositoryInventoryError, match="exited 2"):
        _observation(root)


def test_truncated_oversized_or_unreadable_inventory_fails_closed(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path / "repo")
    real_run = subprocess.run

    def truncated(*args, **kwargs):
        if "ls-files" in args[0]:
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"registry/gaia.json", stderr=b"")
        return real_run(*args, **kwargs)

    monkeypatch.setattr("gaia_cli.steward.repository_hygiene.subprocess.run", truncated)
    with pytest.raises(RepositoryInventoryError, match="truncated"):
        _observation(root)

    def oversized(*args, **kwargs):
        return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"x" * 16385, stderr=b"")

    monkeypatch.setattr("gaia_cli.steward.repository_hygiene.subprocess.run", oversized)
    with pytest.raises(RepositoryInventoryError, match="size limit"):
        _observation(root)

    def unreadable(*args, **kwargs):
        if "ls-files" in args[0]:
            return subprocess.CompletedProcess(args=args[0], returncode=0, stdout=b"\xff\0", stderr=b"")
        return real_run(*args, **kwargs)

    monkeypatch.setattr("gaia_cli.steward.repository_hygiene.subprocess.run", unreadable)
    with pytest.raises(RepositoryInventoryError, match="unreadable tracked-path"):
        _observation(root)


def test_policy_routes_are_bounded_proposals_with_existing_floors_intact() -> None:
    policy = yaml.safe_load(Path("founder/steward/POLICY.yaml").read_text(encoding="utf-8"))
    assert policy["authority"]["repository_hygiene"] == "B"
    assert policy["priority"]["repository_hygiene"] == {
        "importance": 0.7,
        "decisionImpact": 0.7,
        "exposure": 0.6,
        "freshnessNeed": 0.6,
        "expectedCost": 0.2,
    }
    assert policy["routing"]["budget"] == {"modelCalls": 0, "maxTokens": 0, "maxMinutes": 0}

    rules = policy["routing"]["dispatchRules"]
    expected_allowed = {
        "repository-hygiene": ["scripts/**", "tests/steward/**"],
        "knowledge-contradiction": ["docs/agents/**", "tests/steward/**"],
    }
    forbidden_floor = {
        "founder/**", ".gaia/steward/**", ".github/**", "registry/**",
        "registry/schema/**", "skill-trees/**", ".agents/skills/**",
    }
    for rule_id, allowed in expected_allowed.items():
        rule = rules[rule_id]
        assert rule["authority"] == "B"
        assert rule["allowedPaths"] == allowed
        assert forbidden_floor.issubset(set(rule["forbiddenPaths"]))
        assert not ({"src/**", "src/gaia_cli/**"} & set(rule["allowedPaths"]))
        assert "docs/graph/**" in rule["forbiddenPaths"]
        assert any("independent" in item.lower() for item in rule["proof"])
        assert all("pytest" in command or "git " in command or "python scripts/" in command for command in rule["allowedCommands"])

    hygiene = rules["repository-hygiene"]
    assert hygiene["debtKind"] == "repository_hygiene"
    assert any("proposal" in item.lower() or "founder" in item.lower() for item in hygiene["stopConditions"])
    assert "repository_hygiene" not in policy["repairs"]["executors"]

    knowledge = rules["knowledge-contradiction"]
    assert knowledge["debtKind"] == "knowledge_contradiction"
    assert ".claude/skills/**" in knowledge["forbiddenPaths"]
    assert ".agents/skills/**" in knowledge["forbiddenPaths"]
    assert "CLAUDE.md" not in knowledge["allowedPaths"]
    assert any("root" in item.lower() for item in knowledge["stopConditions"])

    assert policy["authority"]["bundled_schema_mirror_drift"] == "A"
    assert policy["authority"]["agent_skill_mirror_drift"] == "A"
