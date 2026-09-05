from __future__ import annotations

import hashlib
import importlib.util
import shutil
import subprocess
from dataclasses import replace
from pathlib import Path

import pytest

import gaia_cli.steward.repairs as repairs
from gaia_cli.steward.mirrors import AGENT_SKILL_MIRROR, BUNDLED_SCHEMA_MIRROR
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, StewardPolicy


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _repo(tmp_path: Path) -> Path:
    policy = tmp_path / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    script = tmp_path / "scripts/sync_bundled_schemas.py"
    script.parent.mkdir()
    shutil.copyfile(REPO_ROOT / "scripts/sync_bundled_schemas.py", script)
    _write(tmp_path / "registry/schema/root.json", '{"type":"object"}\n')
    _write(tmp_path / "registry/schema/nested/child.json", '{"type":"string"}\n')
    _write(tmp_path / "src/gaia_cli/data/registry/schema/root.json", '{"type":"old"}\n')
    _write(tmp_path / "unrelated.txt", "unchanged\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "."], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "base"],
        cwd=tmp_path,
        check=True,
    )
    return tmp_path


def _executor(root: Path):
    return StewardPolicy.load(root).executor_for("bundled_schema_mirror_drift")


def _repair(root: Path) -> dict[str, object]:
    executor = _executor(root)
    assert executor is not None
    return repairs.repair_mirror(
        root,
        executor,
        state_root=root / ".gaia/steward",
    )


def test_mismatch_and_missing_target_are_repaired_then_second_run_is_noop(tmp_path: Path) -> None:
    root = _repo(tmp_path)

    first = _repair(root)
    second = _repair(root)

    assert first["status"] == "repaired"
    assert first["repairedPaths"] == ["nested/child.json", "root.json"]
    assert second["status"] == "no_change"
    assert (root / "registry/schema/root.json").read_bytes() == (
        root / "src/gaia_cli/data/registry/schema/root.json"
    ).read_bytes()
    assert (root / "registry/schema/nested/child.json").read_bytes() == (
        root / "src/gaia_cli/data/registry/schema/nested/child.json"
    ).read_bytes()


def test_bundled_only_extra_is_escalated_without_deletion(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    extra = root / "src/gaia_cli/data/registry/schema/bundled-only.json"
    _write(extra, "{}\n")

    with pytest.raises(repairs.RepairBlocked, match="mirror-only paths"):
        _repair(root)

    assert extra.read_text(encoding="utf-8") == "{}\n"
    assert (root / "src/gaia_cli/data/registry/schema/root.json").read_text(encoding="utf-8") == (
        '{"type":"old"}\n'
    )


def test_symlink_and_invalid_canonical_input_are_refused(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    outside = tmp_path / "outside.json"
    _write(outside, "{}\n")
    try:
        (root / "registry/schema/linked.json").symlink_to(outside)
    except OSError:
        pytest.skip("symlinks are unavailable")

    with pytest.raises(repairs.RepairBlocked, match="symlink"):
        _repair(root)

    (root / "registry/schema/linked.json").unlink()
    _write(root / "registry/schema/not-json.txt", "not json\n")
    with pytest.raises(repairs.RepairBlocked, match="not JSON"):
        _repair(root)


def test_dirty_target_is_refused_before_overwrite(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    _write(root / "src/gaia_cli/data/registry/schema/root.json", '{"type":"user-edit"}\n')

    with pytest.raises(repairs.RepairBlocked, match="user edits"):
        _repair(root)

    assert (root / "src/gaia_cli/data/registry/schema/root.json").read_text(encoding="utf-8") == (
        '{"type":"user-edit"}\n'
    )


def test_verification_failure_and_source_race_rollback_exact_target(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    root = _repo(tmp_path)
    target = root / "src/gaia_cli/data/registry/schema/root.json"
    before = target.read_bytes()

    def fail_verification(*args, **kwargs) -> None:
        raise repairs.RepairError("fixture verification failure")

    monkeypatch.setattr(repairs, "_verify", fail_verification)
    with pytest.raises(repairs.RepairError, match="fixture verification failure"):
        _repair(root)
    assert target.read_bytes() == before

    monkeypatch.undo()
    original_verify = repairs._verify

    def mutate_source_then_verify(*args, **kwargs) -> None:
        _write(root / "registry/schema/root.json", '{"type":"changed-during-repair"}\n')
        original_verify(*args, **kwargs)

    monkeypatch.setattr(repairs, "_verify", mutate_source_then_verify)
    with pytest.raises(repairs.RepairBlocked, match="changed during repair"):
        _repair(root)
    assert target.read_bytes() == before


def test_stage_install_failure_restores_displaced_mirror_exactly(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    mirror = root / "src/gaia_cli/data/registry/schema"
    before = {
        path.relative_to(mirror).as_posix(): path.read_bytes()
        for path in mirror.rglob("*")
        if path.is_file()
    }
    real_replace = repairs.os.replace
    replacements = 0

    def fail_second_replace(source, destination) -> None:
        nonlocal replacements
        replacements += 1
        if replacements == 2:
            raise OSError("fixture stage install failure")
        real_replace(source, destination)

    monkeypatch.setattr(repairs.os, "replace", fail_second_replace)

    with pytest.raises(OSError, match="fixture stage install failure"):
        _repair(root)

    after = {
        path.relative_to(mirror).as_posix(): path.read_bytes()
        for path in mirror.rglob("*")
        if path.is_file()
    }
    assert after == before
    assert not list((root / ".gaia/steward").glob(f"{BUNDLED_SCHEMA_MIRROR.stage_prefix}*"))


def test_handoff_race_preserves_target_edit_instead_of_discarding_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _repo(tmp_path)
    target = root / "src/gaia_cli/data/registry/schema/root.json"
    real_replace = repairs.os.replace
    injected = False

    def edit_before_displacement(source, destination) -> None:
        nonlocal injected
        if not injected and Path(source) == root / BUNDLED_SCHEMA_MIRROR.mirror_root:
            injected = True
            target.write_text('{"target":"handoff-edit"}\n', encoding="utf-8")
        real_replace(source, destination)

    monkeypatch.setattr(repairs.os, "replace", edit_before_displacement)
    with pytest.raises(repairs.RepairBlocked, match="changed during handoff"):
        _repair(root)
    assert target.read_text(encoding="utf-8") == '{"target":"handoff-edit"}\n'


def test_success_retains_contained_recovery_and_open_handle_edit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = _repo(tmp_path)
    target = root / "src/gaia_cli/data/registry/schema/root.json"
    target_before = target.read_bytes()
    handle = target.open("r+b")
    real_verify = repairs._verify
    injected = False

    def edit_displaced_inode_then_verify(*args, **kwargs) -> None:
        nonlocal injected
        if not injected:
            injected = True
            handle.seek(0)
            handle.write(b'{"type":"open-handle-edit"}\n')
            handle.truncate()
            handle.flush()
        real_verify(*args, **kwargs)

    monkeypatch.setattr(repairs, "_verify", edit_displaced_inode_then_verify)
    try:
        receipt = _repair(root)
    finally:
        handle.close()

    recovery = receipt["recovery"]
    recovery_path = root / recovery["path"]
    assert recovery_path.is_relative_to(root / ".gaia/steward")
    assert (recovery_path / "root.json").read_bytes() == b'{"type":"open-handle-edit"}\n'
    assert (root / "src/gaia_cli/data/registry/schema/root.json").read_bytes() == (
        root / "registry/schema/root.json"
    ).read_bytes()
    assert recovery["preRepairManifest"]["root.json"] == hashlib.sha256(
        target_before
    ).hexdigest()
    assert recovery["originalTargetPresent"] is True
    assert recovery["retained"] is True


def test_recovery_state_outside_repository_is_refused_before_mutation(tmp_path: Path) -> None:
    root = _repo(tmp_path / "repo")
    target = root / "src/gaia_cli/data/registry/schema/root.json"
    before = target.read_bytes()
    executor = _executor(root)
    assert executor is not None

    with pytest.raises(repairs.RepairBlocked, match="repository-local state"):
        repairs.prepare_mirror_repair(
            root,
            executor,
            state_root=tmp_path / "outside",
        )

    assert target.read_bytes() == before
    assert not (tmp_path / "outside").exists()


def test_repair_changes_only_the_explicit_mirror_allowlist(tmp_path: Path) -> None:
    root = _repo(tmp_path)
    before = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not {".gaia", ".git"}.intersection(path.relative_to(root).parts)
    }

    _repair(root)

    after = {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not {".gaia", ".git"}.intersection(path.relative_to(root).parts)
    }
    changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    assert changed == [
        "src/gaia_cli/data/registry/schema/nested/child.json",
        "src/gaia_cli/data/registry/schema/root.json",
    ]


# --- V1.1: the second Class A closed loop (agent skill mirror) -----------------


def _agent_repo(tmp_path: Path) -> Path:
    """A checkout whose only Class A surface is the agent skill mirror."""

    policy = tmp_path / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    script = tmp_path / "scripts/sync_agent_skill_mirror.py"
    script.parent.mkdir()
    shutil.copyfile(REPO_ROOT / "scripts/sync_agent_skill_mirror.py", script)
    _write(tmp_path / ".agents/skills/alpha/SKILL.md", "# alpha\n")
    _write(tmp_path / ".agents/skills/beta/SKILL.md", "# beta\n")
    _write(tmp_path / ".agents/skills/beta/reference/notes.md", "beta notes\n")
    _write(tmp_path / ".agents/skills/skill-creator/SKILL.md", "# canonical local-only\n")
    _write(tmp_path / ".claude/skills/alpha/SKILL.md", "# stale alpha\n")
    _write(tmp_path / ".claude/skills/skill-creator/SKILL.md", "# mirror local-only\n")
    _write(tmp_path / ".claude/skills/alpha/__pycache__/cached.pyc", "bytecode\n")
    _write(tmp_path / "unrelated.txt", "unchanged\n")
    subprocess.run(["git", "init", "-q"], cwd=tmp_path, check=True)
    subprocess.run(["git", "add", "-A"], cwd=tmp_path, check=True)
    subprocess.run(
        ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "base"],
        cwd=tmp_path,
        check=True,
    )
    return tmp_path


def _agent_repair(root: Path) -> dict[str, object]:
    executor = StewardPolicy.load(root).executor_for("agent_skill_mirror_drift")
    assert executor is not None
    return repairs.repair_mirror(root, executor, state_root=root / ".gaia/steward")


def test_check_script_ignore_set_matches_the_repair_specification() -> None:
    """The independent proof command must compare exactly the mirrored paths."""

    script = REPO_ROOT / "scripts/sync_agent_skill_mirror.py"
    spec = importlib.util.spec_from_file_location("sync_agent_skill_mirror", script)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    assert tuple(module.IGNORE) == AGENT_SKILL_MIRROR.ignore


def test_agent_mirror_drift_is_repaired_then_second_run_is_noop(tmp_path: Path) -> None:
    root = _agent_repo(tmp_path)

    first = _agent_repair(root)
    second = _agent_repair(root)

    assert first["status"] == "repaired"
    assert first["executor"] == "agent-skill-mirror"
    assert first["repairedPaths"] == [
        "alpha/SKILL.md",
        "beta/SKILL.md",
        "beta/reference/notes.md",
    ]
    assert second["status"] == "no_change"
    assert (root / ".claude/skills/alpha/SKILL.md").read_text(encoding="utf-8") == "# alpha\n"
    assert (root / ".claude/skills/beta/reference/notes.md").read_text(encoding="utf-8") == "beta notes\n"


def test_agent_mirror_repair_preserves_locally_owned_paths(tmp_path: Path) -> None:
    """An atomic whole-directory install must not delete unmirrored paths."""

    root = _agent_repo(tmp_path)

    receipt = _agent_repair(root)

    assert sorted(receipt["preservedPaths"]) == [
        "alpha/__pycache__/cached.pyc",
        "skill-creator/SKILL.md",
    ]
    assert (root / ".claude/skills/skill-creator/SKILL.md").read_text(encoding="utf-8") == (
        "# mirror local-only\n"
    )
    assert (root / ".claude/skills/alpha/__pycache__/cached.pyc").read_text(encoding="utf-8") == (
        "bytecode\n"
    )


def test_agent_mirror_only_skill_is_escalated_without_deletion(tmp_path: Path) -> None:
    root = _agent_repo(tmp_path)
    orphan = root / ".claude/skills/claude-only/SKILL.md"
    _write(orphan, "# claude only\n")

    with pytest.raises(repairs.RepairBlocked, match="mirror-only paths"):
        _agent_repair(root)

    assert orphan.read_text(encoding="utf-8") == "# claude only\n"
    assert (root / ".claude/skills/alpha/SKILL.md").read_text(encoding="utf-8") == "# stale alpha\n"


def test_agent_mirror_dirty_target_is_refused_before_overwrite(tmp_path: Path) -> None:
    root = _agent_repo(tmp_path)
    _write(root / ".claude/skills/alpha/SKILL.md", "# user edit\n")

    with pytest.raises(repairs.RepairBlocked, match="user edits"):
        _agent_repair(root)

    assert (root / ".claude/skills/alpha/SKILL.md").read_text(encoding="utf-8") == "# user edit\n"


def _worktree_snapshot(root: Path) -> dict[str, bytes]:
    """Every tracked-worktree file, keyed by repo-relative path.

    `.gaia` is scratch state the repair legitimately writes.  `.git` is
    excluded because git's background maintenance can drop files such as
    `objects/maintenance.lock` into it at any moment, which has nothing to do
    with what the repair touched and would otherwise fail this assertion at
    random.
    """
    skip = {".gaia", ".git"}
    return {
        path.relative_to(root).as_posix(): path.read_bytes()
        for path in root.rglob("*")
        if path.is_file() and not skip & set(path.relative_to(root).parts)
    }


def test_agent_mirror_repair_changes_only_the_mirror_allowlist(tmp_path: Path) -> None:
    root = _agent_repo(tmp_path)
    before = _worktree_snapshot(root)

    _agent_repair(root)

    after = _worktree_snapshot(root)
    changed = sorted(path for path in set(before) | set(after) if before.get(path) != after.get(path))
    assert changed == [
        ".claude/skills/alpha/SKILL.md",
        ".claude/skills/beta/SKILL.md",
        ".claude/skills/beta/reference/notes.md",
    ]


def test_agent_mirror_verification_failure_rolls_back_exact_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    root = _agent_repo(tmp_path)
    mirror = root / ".claude/skills"
    before = {
        path.relative_to(mirror).as_posix(): path.read_bytes()
        for path in mirror.rglob("*")
        if path.is_file()
    }

    def fail_verification(*args, **kwargs) -> None:
        raise repairs.RepairError("fixture verification failure")

    monkeypatch.setattr(repairs, "_verify", fail_verification)
    with pytest.raises(repairs.RepairError, match="fixture verification failure"):
        _agent_repair(root)

    after = {
        path.relative_to(mirror).as_posix(): path.read_bytes()
        for path in mirror.rglob("*")
        if path.is_file()
    }
    assert after == before


def test_executor_may_not_be_redirected_to_another_surface(tmp_path: Path) -> None:
    """Policy is an envelope over a registered repair, never a redirect."""

    root = _agent_repo(tmp_path)
    executor = StewardPolicy.load(root).executor_for("agent_skill_mirror_drift")
    assert executor is not None
    redirected = replace(executor, writable_path="src/gaia_cli/data/registry/schema/**")

    with pytest.raises(repairs.RepairBlocked, match="fixed authority envelope"):
        repairs.prepare_mirror_repair(root, redirected, state_root=root / ".gaia/steward")


def test_repair_preserves_an_empty_locally_owned_directory(tmp_path: Path) -> None:
    """A deliberately empty directory has no file to imply it back into being."""

    root = _agent_repo(tmp_path)
    empty = root / ".claude/skills/skill-creator/scratch"
    empty.mkdir(parents=True)

    receipt = _agent_repair(root)

    assert empty.is_dir()
    assert "skill-creator/scratch" in receipt["preservedDirectories"]


def test_repair_refuses_to_silently_delete_an_unrelated_empty_mirror_directory(
    tmp_path: Path,
) -> None:
    """Deleting is never the conservative choice, even for a stray directory."""

    root = _agent_repo(tmp_path)
    stray = root / ".claude/skills/leftover"
    stray.mkdir(parents=True)

    _agent_repair(root)

    assert stray.is_dir()
