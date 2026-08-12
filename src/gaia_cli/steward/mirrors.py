"""The exact mirror surfaces Steward is allowed to observe and repair.

One specification drives three independent consumers: the read-only sensor that
observes drift, the machine-enforced policy that authorizes a Class A executor,
and the deterministic repair that installs canonical bytes.  Keeping them on a
single contract is deliberate — a mirror whose sensor and repair disagreed about
which paths are compared would be able to "repair" a surface it never observed.

A spec never widens authority.  It declares fixed roots, a fixed writable path,
a fixed proof command, and the exact set of locally owned paths that are neither
compared nor overwritten.
"""

from __future__ import annotations

import fnmatch
from dataclasses import dataclass
from typing import Iterable


def is_ignored(relative_path: str, patterns: Iterable[str]) -> bool:
    """Return whether one mirror-relative path is locally owned, not mirrored."""

    for pattern in patterns:
        if fnmatch.fnmatchcase(relative_path, pattern):
            return True
        if pattern.endswith("/**") and relative_path.startswith(pattern[:-3] + "/"):
            return True
    return False


@dataclass(frozen=True)
class MirrorSpec:
    """One canonical-to-mirror surface with a fixed authority envelope."""

    id: str
    debt_kind: str
    subject_id: str
    canonical_root: str
    mirror_root: str
    check_script: str
    json_only: bool
    ignore: tuple[str, ...] = ()

    @property
    def canonical_glob(self) -> str:
        return f"{self.canonical_root}/**"

    @property
    def writable_glob(self) -> str:
        return f"{self.mirror_root}/**"

    @property
    def check_command(self) -> str:
        return f"python {self.check_script} --check"

    @property
    def git_status_command(self) -> str:
        return (
            "git status --porcelain=v1 --untracked-files=all -- " + self.mirror_root
        )

    @property
    def stage_prefix(self) -> str:
        return f"class-a-{self.id}-"

    def is_ignored(self, relative_path: str) -> bool:
        return is_ignored(relative_path, self.ignore)

    def allowed_commands(self) -> tuple[str, ...]:
        return (self.git_status_command, self.check_command)


BUNDLED_SCHEMA_MIRROR = MirrorSpec(
    id="bundled-schema-mirror",
    debt_kind="bundled_schema_mirror_drift",
    subject_id="registry-schema",
    canonical_root="registry/schema",
    mirror_root="src/gaia_cli/data/registry/schema",
    check_script="scripts/sync_bundled_schemas.py",
    json_only=True,
)

AGENT_SKILL_MIRROR = MirrorSpec(
    id="agent-skill-mirror",
    debt_kind="agent_skill_mirror_drift",
    subject_id="agent-skill-mirrors",
    canonical_root=".agents/skills",
    mirror_root=".claude/skills",
    check_script="scripts/sync_agent_skill_mirror.py",
    json_only=False,
    # Locally owned paths. They are neither compared nor overwritten, and a
    # repair must carry them across an atomic mirror replacement unchanged.
    ignore=("skill-creator/**", "**/__pycache__/**", "**/*.pyc"),
)

MIRROR_SPECS: tuple[MirrorSpec, ...] = (BUNDLED_SCHEMA_MIRROR, AGENT_SKILL_MIRROR)


def spec_by_id(executor_id: str) -> MirrorSpec | None:
    for spec in MIRROR_SPECS:
        if spec.id == executor_id:
            return spec
    return None


def spec_by_debt_kind(debt_kind: str) -> MirrorSpec | None:
    for spec in MIRROR_SPECS:
        if spec.debt_kind == debt_kind:
            return spec
    return None
