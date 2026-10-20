"""State model for scaffolded `gaia curate` runs."""

from __future__ import annotations

import json
import os
import re
import tempfile
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Optional
from uuid import uuid4


STATE_NAMES = [
    "INITIALIZED",
    "RESOLVING_URL",
    "FINDING_SKILL_FILES",
    "FETCHING_SOURCE",
    "SNAPSHOTTING_GENERIC",
    "PREFILLING_MAPPING",
    "BUILDING_DISCOVERY_PACKET",
    "AWAITING_L4_REVIEW",
    "APPLYING_L4_RESOLUTION",
    "DISCOVERING_EVIDENCE",
    "COMPILING_EVIDENCE_LAKE",
    "VERIFYING_STARS",
    "VERIFYING_BENCHMARKS",
    "AUDITING_EVIDENCE",
    "VALIDATING_LINKS",
    "BUILDING_INGEST_PLAN",
    "AWAITING_EVIDENCE_APPROVAL",
    "OPENING_REVIEW_BRANCH",
    "INGESTING_EVIDENCE",
    "APPRAISING_TRUST",
    "PROPOSING_CALIBRATION",
    "AWAITING_CALIBRATION_APPROVAL",
    "APPLYING_CALIBRATION",
    "VALIDATING_REGISTRY",
    "DONE",
]


def _artifact_slot() -> dict[str, Any]:
    return {"path": None, "sha256": None}


def _default_source() -> dict[str, Any]:
    return {
        "repo": None,
        "canonical_skill_file_url": None,
        "content_sha256": None,
        "resolved_commit": None,
        "source_started_at": None,
    }


def _default_artifacts() -> dict[str, dict[str, Any]]:
    return {
        "generic_snapshot": _artifact_slot(),
        "prefill_output": _artifact_slot(),
        "discovery_packet": _artifact_slot(),
        "evidence_lake": _artifact_slot(),
        "ingest_plan": _artifact_slot(),
        "tm_output": _artifact_slot(),
    }


def _default_decisions() -> dict[str, Any]:
    return {
        "mapping_proposal": None,
        "l4_resolution": None,
        "evidence_approval": None,
        "calibration_approval": None,
    }


def _default_external_refs() -> dict[str, Any]:
    return {
        "branch": None,
        "pr_number": None,
        "pr_url": None,
        "intake_issue_number": None,
        "intake_issue_url": None,
    }


def _default_git() -> dict[str, Any]:
    return {
        "base_branch": None,
        "base_commit": None,
        "working_branch": None,
        "created_commits": [],
    }


def _default_rollback() -> dict[str, Any]:
    return {
        "created_files": [],
        "created_branch": None,
        "created_pr": None,
        "created_issue": None,
        "labels_applied": [],
        "comments_posted": [],
        "pre_mutation_commit": None,
    }


@dataclass
class CurationRun:
    """Serializable ledger for one `gaia curate` workflow run."""

    run_id: str = field(default_factory=lambda: uuid4().hex)
    current_state: str = "INITIALIZED"
    input_url: str = ""
    suggested_generic_id: Optional[str] = None
    candidate_id: Optional[str] = None
    named_identity: Optional[str] = None
    candidate_name: Optional[str] = None
    candidate_description: Optional[str] = None
    inventory: list[dict[str, Any]] = field(default_factory=list)
    discover: bool = False
    dry_run: bool = False
    source: dict[str, Any] = field(default_factory=_default_source)
    artifacts: dict[str, dict[str, Any]] = field(default_factory=_default_artifacts)
    decisions: dict[str, Any] = field(default_factory=_default_decisions)
    external_refs: dict[str, Any] = field(default_factory=_default_external_refs)
    git: dict[str, Any] = field(default_factory=_default_git)
    ledger: list[dict[str, Any]] = field(default_factory=list)
    rollback: dict[str, Any] = field(default_factory=_default_rollback)
    # Current blocker records are separate from the append-only historical ledger.
    checkpoint: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if not isinstance(self.run_id, str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}", self.run_id):
            raise ValueError("run_id must be 1–64 ASCII letters, digits, underscores, or hyphens")

    @property
    def run_dir(self) -> Path:
        """Return the default local run directory for this curation run."""
        return Path(".gaia") / "curation" / "runs" / self.run_id

    def save(self, path: str | Path) -> None:
        """Persist this run as formatted JSON at *path*.

        If *path* points to a directory (or has no suffix), the state is written
        to ``path/state.json``. Parent directories are created automatically.
        """
        target = Path(path)
        if target.suffix == "":
            target = target / "state.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        payload = (json.dumps(asdict(self), indent=2) + "\n").encode("utf-8")
        fd, temporary_name = tempfile.mkstemp(prefix=f".{target.name}.", suffix=".tmp", dir=target.parent)
        try:
            with os.fdopen(fd, "wb") as stream:
                stream.write(payload)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary_name, target)
            try:
                dir_fd = os.open(target.parent, os.O_RDONLY)
                try: os.fsync(dir_fd)
                finally: os.close(dir_fd)
            except OSError:
                pass
        finally:
            try: os.unlink(temporary_name)
            except FileNotFoundError: pass

    @classmethod
    def load(cls, path: str | Path) -> "CurationRun":
        """Load a curation run from *path*.

        If *path* points to a directory (or has no suffix), ``state.json`` below
        that directory is loaded.
        """
        target = Path(path)
        if target.suffix == "":
            target = target / "state.json"
        data = json.loads(target.read_text(encoding="utf-8"))
        # Keep old ledgers loadable as fields are added to the local workflow.
        return cls(**{key: value for key, value in data.items() if key in cls.__dataclass_fields__})
