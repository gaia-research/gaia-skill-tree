"""Read-only, reproducible publication rehearsal context (Yggdrasil IV P4 prep).

This module grants no publication approval. It binds a builder replay to the
inputs and policy files it consumed and keeps its output outside the checkout.
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
REQUIRED_OUTPUTS = (
    "registry/named-skills.json", "docs/graph/named/index.json",
    "docs/graph/ledger/data.json", "docs/api/v1/skills/index.json",
    "docs/u/index.html", "docs/badges/registry.json",
)
INPUTS = (
    "registry/gaia.json", "registry/named-skills.json", "registry/nodes",
    "registry/named", "registry/suites", "registry/schema/meta.json",
    "registry/benchmark-sources.json", "META.md", "GOVERNANCE.md",
    "founder/YGGDRASIL_IV_RATIFICATION_2026-10-25.md",
    "docs/agents/curation-authority-map.md", "src/gaia_cli/trustMagnitude.py",
    "src/gaia_cli/benchmarkCatalog.py", "scripts/generateNamedIndex.py",
    "scripts/generateLeaderboardData.py", "scripts/buildApiProjection.py",
    "scripts/generateProfilePages.py", "scripts/generateBadges.py",
)


def evaluation_at_utc_from_env():
    value = os.environ.get("GAIA_EVALUATION_AT_UTC")
    if not value:
        return None
    parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("GAIA_EVALUATION_AT_UTC must be UTC")
    return parsed


def _digest(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _files(path: Path):
    if path.is_file():
        yield path
    elif path.is_dir():
        yield from sorted(p for p in path.rglob("*") if p.is_file())


def create_context(source_root: Path, output_root: Path, evaluation_at_utc: str | None = None) -> dict:
    source_root = source_root.resolve(strict=True)
    output_root = output_root.expanduser().absolute()
    if output_root.is_symlink():
        raise ValueError("publication output root must not be a symlink")
    output_resolved = output_root.resolve(strict=False)
    if output_resolved == source_root or source_root in output_resolved.parents or output_resolved in source_root.parents:
        raise ValueError("publication output root must be disjoint from the source checkout")
    if evaluation_at_utc is None:
        evaluation_at_utc = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    parsed = datetime.fromisoformat(evaluation_at_utc.replace("Z", "+00:00"))
    if parsed.tzinfo is None or parsed.utcoffset().total_seconds() != 0:
        raise ValueError("evaluationAtUTC must be an explicit UTC timestamp")
    revisions = {}
    try:
        revisions["source"] = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=source_root, check=True,
            capture_output=True, text=True,
        ).stdout.strip()
    except (OSError, subprocess.CalledProcessError):
        revisions["source"] = "unavailable"
    inputs = {}
    for rel in INPUTS:
        path = source_root / rel
        if path.exists():
            for file in _files(path):
                inputs[file.relative_to(source_root).as_posix()] = _digest(file.read_bytes())
    policy = {key: inputs.get(key, "missing") for key in (
        "META.md", "GOVERNANCE.md", "registry/schema/meta.json",
        "registry/benchmark-sources.json", "src/gaia_cli/trustMagnitude.py",
        "src/gaia_cli/benchmarkCatalog.py",
    )}
    seed = json.dumps({"inputs": inputs, "revisions": revisions, "policy": policy,
                       "evaluationAtUTC": evaluation_at_utc}, sort_keys=True, separators=(",", ":"))
    snapshot_id = hashlib.sha256(seed.encode()).hexdigest()
    return {
        "mode": MODE, "approval": APPROVAL, "snapshotId": snapshot_id,
        "evaluationAtUTC": evaluation_at_utc, "sourceRevision": revisions["source"],
        "inputDigests": inputs, "policyIdentity": policy,
        "engineIdentity": inputs.get("src/gaia_cli/trustMagnitude.py", "missing"),
        "catalogIdentity": inputs.get("registry/benchmark-sources.json", "missing"),
    }


def stamp_outputs(output_root: Path, context: dict) -> dict:
    """Stamp actual builder artifacts then emit a non-circular digest manifest."""
    output_root = output_root.resolve(strict=True)
    missing = [rel for rel in REQUIRED_OUTPUTS if not (output_root / rel).is_file()]
    if missing:
        raise ValueError("rehearsal incomplete; required builder outputs missing: " + ", ".join(missing))
    context_path = output_root / "publication-context.json"
    context_path.write_text(json.dumps(context, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    for path in sorted(output_root.rglob("*")):
        if not path.is_file() or path == context_path or path.name == "publication-artifacts.json":
            continue
        try:
            raw = path.read_bytes()
            if path.suffix.lower() == ".json":
                payload = json.loads(raw.decode("utf-8"))
                if not isinstance(payload, dict):
                    continue
                prior = payload.get("publicationContext")
                if prior and prior != context:
                    raise ValueError(f"mixed publication context in {path}")
                payload["publicationContext"] = context
                path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
            elif path.suffix.lower() in {".html", ".svg", ".xml"}:
                marker = f"<!-- publication-context:{context['snapshotId']} mode=rehearsal approval=unavailable -->\n".encode()
                if marker not in raw:
                    if path.suffix.lower() in {".svg", ".xml"} and raw.lstrip().startswith(b"<?xml"):
                        declaration_end = raw.find(b"?>") + 2
                        raw = raw[:declaration_end] + b"\n" + marker + raw[declaration_end:].lstrip(b"\r\n")
                        path.write_bytes(raw)
                    else:
                        path.write_bytes(marker + raw)
        except (UnicodeDecodeError, json.JSONDecodeError):
            continue
    artifacts = {}
    for path in sorted(output_root.rglob("*")):
        if path.is_file() and path not in {context_path, output_root / "publication-artifacts.json"}:
            artifacts[path.relative_to(output_root).as_posix()] = _digest(path.read_bytes())
    manifest = {"mode": MODE, "approval": APPROVAL, "snapshotId": context["snapshotId"],
                "artifacts": artifacts}
    (output_root / "publication-artifacts.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return manifest


def verify_outputs(output_root: Path) -> bool:
    """Reject missing, changed, mixed-context or incomplete stamped artifacts."""
    output_root = output_root.resolve(strict=True)
    manifest = json.loads((output_root / "publication-artifacts.json").read_text(encoding="utf-8"))
    context = json.loads((output_root / "publication-context.json").read_text(encoding="utf-8"))
    if manifest.get("mode") != MODE or manifest.get("approval") != APPROVAL or manifest.get("snapshotId") != context.get("snapshotId"):
        return False
    if any(not (output_root / rel).is_file() for rel in REQUIRED_OUTPUTS):
        return False
    expected = manifest.get("artifacts", {})
    for rel, digest in expected.items():
        path = output_root / rel
        if not path.is_file() or _digest(path.read_bytes()) != digest:
            return False
        if path.suffix.lower() == ".json":
            try:
                payload = json.loads(path.read_text(encoding="utf-8"))
                if isinstance(payload, dict) and payload.get("publicationContext") != context:
                    return False
            except (UnicodeDecodeError, json.JSONDecodeError):
                pass
        elif path.suffix.lower() in {".html", ".svg", ".xml"}:
            text = path.read_text(encoding="utf-8")
            if f"publication-context:{context['snapshotId']} mode=rehearsal approval=unavailable" not in text:
                return False
    actual = {p.relative_to(output_root).as_posix() for p in output_root.rglob("*") if p.is_file() and p.name not in {"publication-context.json", "publication-artifacts.json"}}
    return actual == set(expected)
