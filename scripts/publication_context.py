"""Fail-closed, read-only publication rehearsal provenance helpers.

Approval is deliberately unavailable. Provenance is a reproducibility record,
not an authenticated approval or filesystem security boundary.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import subprocess
from datetime import datetime, timezone

MODE = "rehearsal"
APPROVAL = "unavailable"
COPY_IGNORES = {".git", ".gaia", ".pi", "__pycache__", ".pytest_cache", "node_modules"}
REQUIRED_OUTPUTS = (
    "registry/named-skills.json", "docs/graph/named/index.json",
    "docs/graph/ledger/data.json", "docs/api/v1/skills/index.json",
    "docs/u/index.html", "docs/badges/registry.json",
)
GENERATED_OUTPUTS = REQUIRED_OUTPUTS + (
    "docs/graph/gaia.json", "docs/graph/gaia.gexf", "docs/graph/gaia.svg",
    "docs/api/v1/leaderboard.json", "docs/api/v1/health.json",
)


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _inventory(root: Path) -> dict[str, str]:
    result = {}
    for path in sorted(root.rglob("*")):
        if any(part in COPY_IGNORES for part in path.relative_to(root).parts):
            continue
        if path.is_symlink():
            raise ValueError(f"symlink in copied source inventory: {path.relative_to(root)}")
        if path.is_file():
            result[path.relative_to(root).as_posix()] = _digest(path.read_bytes())
    return result


def _worktree_roots(source_root: Path) -> list[Path]:
    try:
        raw = subprocess.run(["git", "worktree", "list", "--porcelain"], cwd=source_root,
                             check=True, capture_output=True, text=True).stdout
    except (OSError, subprocess.CalledProcessError):
        return [source_root]
    roots = []
    for line in raw.splitlines():
        if line.startswith("worktree "):
            roots.append(Path(line[9:]).resolve())
    return roots or [source_root]


def load_context(path: str | Path) -> dict:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    if payload.get("mode") != MODE or payload.get("approval") != APPROVAL:
        raise ValueError("invalid publication rehearsal context")
    if payload.get("evaluationAtUTC") != _utc(payload.get("evaluationAtUTC", "")):
        raise ValueError("malformed publication rehearsal time")
    if not payload.get("snapshotId") or not isinstance(payload.get("inputDigests"), dict):
        raise ValueError("incomplete publication rehearsal context")
    return payload


def evaluation_at_utc_from_env():
    path = os.environ.get("GAIA_PUBLICATION_CONTEXT")
    return load_context(path)["evaluationAtUTC"] if path else None


def rehearsal_context_from_env():
    path = os.environ.get("GAIA_PUBLICATION_CONTEXT")
    return load_context(path) if path else None


def _utc(value: str) -> str:
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except (ValueError, AttributeError) as exc:
        raise ValueError("evaluationAtUTC must be an explicit ISO UTC timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("evaluationAtUTC must be an explicit UTC timestamp")
    return parsed.astimezone(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def _snapshot_id(inputs: dict[str, str], revision: str, instant: str) -> str:
    seed = json.dumps({"inputs": inputs, "sourceRevision": revision, "evaluationAtUTC": instant}, sort_keys=True, separators=(",", ":"))
    return _digest(seed.encode())


def create_context(source_root: Path, output_root: Path, evaluation_at_utc: str | None = None) -> dict:
    source_root = source_root.resolve(strict=True)
    output_root = output_root.expanduser().absolute()
    if output_root.exists() or output_root.is_symlink():
        raise ValueError("publication output root must be a new non-symlink path")
    if any(p.is_symlink() for p in (output_root, *output_root.parents)):
        raise ValueError("publication output root must not be under a symlink path")
    resolved = output_root.resolve(strict=False)
    if any(resolved == root or root in resolved.parents or resolved in root.parents for root in _worktree_roots(source_root)):
        raise ValueError("publication output root must be disjoint from every repository worktree")
    instant = _utc(evaluation_at_utc) if evaluation_at_utc else datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    inputs = _inventory(source_root)
    try:
        revision = subprocess.run(["git", "rev-parse", "HEAD"], cwd=source_root, check=True,
                                  capture_output=True, text=True).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revision = "unavailable"
    return {"mode": MODE, "approval": APPROVAL, "snapshotId": _snapshot_id(inputs, revision, instant),
            "evaluationAtUTC": instant, "sourceRevision": revision, "inputDigests": inputs,
            "engineIdentity": inputs.get("src/gaia_cli/trustMagnitude.py", "missing"),
            "policyIdentity": {k: inputs.get(k, "missing") for k in ("META.md", "GOVERNANCE.md", "registry/schema/meta.json")}}


def verify_copied_inputs(output_root: Path, context: dict) -> None:
    """Verify exact pre-build copy bytes; generated surfaces may change afterwards."""
    for rel, expected in context["inputDigests"].items():
        path = output_root / rel
        if not path.is_file() or path.is_symlink() or _digest(path.read_bytes()) != expected:
            raise ValueError(f"copied source input differs from snapshot: {rel}")


def compare_ledger_api(ledger: dict, api: dict) -> list[str]:
    """Compare stored canonical stars and TM wherever both public projections expose a skill."""
    ledger_rows = {str(row.get("skillId")): row for row in ledger.get("rows", []) if row.get("skillId")}
    api_rows = {str(row.get("id")): row for row in api.get("skills", []) if row.get("id")}
    problems = []
    for skill_id in sorted(ledger_rows.keys() & api_rows.keys()):
        lrow, arow = ledger_rows[skill_id], api_rows[skill_id]
        if str(lrow.get("currentStars")) != str(arow.get("level")):
            problems.append(f"{skill_id}: canonical stars differ")
        if round(float(lrow.get("tm", 0)), 2) != round(float(arow.get("trustMagnitude", 0)), 2):
            problems.append(f"{skill_id}: TM differs")
    return problems


def _check_semantic_parity(root: Path) -> None:
    ledger = json.loads((root / "docs/graph/ledger/data.json").read_text(encoding="utf-8"))
    api = json.loads((root / "docs/api/v1/skills/index.json").read_text(encoding="utf-8"))
    problems = compare_ledger_api(ledger, api)
    if problems:
        raise ValueError("cross-surface semantic mismatch: " + "; ".join(problems[:10]))


def stamp_outputs(output_root: Path, context: dict, stages: dict | None = None) -> dict:
    """Write external metadata only; never alter generated, static, or source files."""
    output_root = output_root.resolve(strict=True)
    if context.get("mode") != MODE or context.get("approval") != APPROVAL:
        raise ValueError("invalid rehearsal context")
    if not stages or any(v.get("status") != "success" or not v.get("outputs") for v in stages.values()):
        raise ValueError("rehearsal incomplete: every required generator needs success and output inventory")
    for rel in GENERATED_OUTPUTS:
        if not (output_root / rel).is_file():
            raise ValueError(f"rehearsal incomplete; required generated output missing: {rel}")
    _check_semantic_parity(output_root)
    context_path = output_root / "publication-context.json"
    context_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    artifacts = {}
    for rel in GENERATED_OUTPUTS:
        path = output_root / rel
        artifacts[rel] = _digest(path.read_bytes())
    manifest = {"mode": MODE, "approval": APPROVAL, "snapshotId": context["snapshotId"],
                "evaluationAtUTC": context["evaluationAtUTC"], "stages": stages, "artifacts": artifacts}
    (output_root / "publication-artifacts.json").write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify_outputs(output_root: Path) -> bool:
    """Verify bounded generated output digests and internally consistent context identity."""
    try:
        output_root = output_root.resolve(strict=True)
        manifest = json.loads((output_root / "publication-artifacts.json").read_text(encoding="utf-8"))
        context = json.loads((output_root / "publication-context.json").read_text(encoding="utf-8"))
        if (manifest.get("mode"), manifest.get("approval")) != (MODE, APPROVAL) or (context.get("mode"), context.get("approval")) != (MODE, APPROVAL):
            return False
        if context.get("snapshotId") != _snapshot_id(context.get("inputDigests", {}), context.get("sourceRevision", ""), _utc(context.get("evaluationAtUTC", ""))):
            return False
        if manifest.get("snapshotId") != context.get("snapshotId") or manifest.get("evaluationAtUTC") != context.get("evaluationAtUTC"):
            return False
        if set(manifest.get("artifacts", {})) != set(GENERATED_OUTPUTS):
            return False
        if not manifest.get("stages") or any(v.get("status") != "success" or not v.get("outputs") for v in manifest["stages"].values()):
            return False
        return all((output_root / rel).is_file() and not (output_root / rel).is_symlink() and _digest((output_root / rel).read_bytes()) == digest for rel, digest in manifest["artifacts"].items())
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError):
        return False
