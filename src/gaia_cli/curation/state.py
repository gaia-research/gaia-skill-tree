"""State model for scaffolded `gaia curate` runs."""

from __future__ import annotations

import json
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
    discover: bool = False
    dry_run: bool = False
    source: dict[str, Any] = field(default_factory=_default_source)
    artifacts: dict[str, dict[str, Any]] = field(default_factory=_default_artifacts)
    decisions: dict[str, Any] = field(default_factory=_default_decisions)
    external_refs: dict[str, Any] = field(default_factory=_default_external_refs)
    git: dict[str, Any] = field(default_factory=_default_git)
    ledger: list[dict[str, Any]] = field(default_factory=list)
    rollback: dict[str, Any] = field(default_factory=_default_rollback)

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
        target.write_text(json.dumps(asdict(self), indent=2) + "\n", encoding="utf-8")

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
        return cls(**data)
