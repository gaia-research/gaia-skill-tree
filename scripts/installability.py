#!/usr/bin/env python3
"""Offline projection of bounded installability observations.

The publisher never runs an installer and never asks the network. It only
projects observations whose source route and canonical registry content still
match this checkout. Everything else is unknown.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
from datetime import datetime
from pathlib import Path
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
REGISTRY = ROOT / "registry" / "installability"
OBSERVATION_SCHEMA = "gaia.installability-observation/v1"
PROJECTION_SCHEMA = "gaia.installability/v1"
CONTRACTS = REGISTRY / "contracts"
INTRINSIC_CAUSES = {"NOT_A_SKILL_DIR", "NO_SKILL_MD", "DANGLING_SYMLINK"}
CATEGORIES = {"STANDARD", "REPO_ROOT", "SUITE", "NO_SOURCE"}


def canonical_json_bytes(value: object) -> bytes:
    return (
        json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def observation_digest(value: object) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _load_schema(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"cannot read schema {path}: {exc}") from exc


def _validate(document: dict, schema_path: Path, label: str) -> None:
    try:
        import jsonschema

        validator = jsonschema.Draft7Validator(_load_schema(schema_path))
        errors = sorted(validator.iter_errors(document), key=lambda error: list(error.path))
    except ImportError as exc:
        raise RuntimeError("jsonschema is required to publish installability") from exc
    if errors:
        error = errors[0]
        location = ".".join(str(part) for part in error.path) or "$"
        raise ValueError(f"invalid {label} at {location}: {error.message}")


def _safe_json_path(path: Path, root: Path) -> None:
    if path.is_symlink():
        raise ValueError(f"symlink input is not allowed: {path}")
    try:
        path.resolve().relative_to(root.resolve())
    except ValueError as exc:
        raise ValueError(f"path escapes installability root: {path}") from exc


def _skill_path(repo_root: Path, skill_id: str) -> Path | None:
    if not re.fullmatch(r"[^/\s]+/[^/\s]+", skill_id):
        raise ValueError(f"invalid skill id: {skill_id!r}")
    named_root = (repo_root / "registry" / "named").absolute()
    path = Path(str(named_root.joinpath(*skill_id.split("/"))) + ".md")
    try:
        path.relative_to(named_root)
    except ValueError as exc:
        raise ValueError(f"skill path escapes registry: {skill_id!r}") from exc
    cursor = named_root
    for part in path.relative_to(named_root).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            raise ValueError(f"canonical skill path contains a symlink: {skill_id}")
    return path if path.is_file() else None


def _file_digest(path: Path | None) -> str | None:
    if path is None:
        return None
    digest = hashlib.sha256()
    try:
        with path.open("rb") as handle:
            for block in iter(lambda: handle.read(1024 * 1024), b""):
                digest.update(block)
    except OSError as exc:
        raise ValueError(f"cannot read canonical skill {path}: {exc}") from exc
    return digest.hexdigest()


def _route(link: str | None) -> dict | None:
    if not link:
        return None
    parsed = urlsplit(link)
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ValueError("credential-bearing or query-bearing source route")
    if parsed.scheme not in {"http", "https"} or parsed.netloc.lower() != "github.com":
        raise ValueError(f"unsupported source route: {link}")
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) < 2:
        raise ValueError(f"incomplete source route: {link}")
    owner, repo = parts[0], parts[1].removesuffix(".git")
    ref = None
    subpath = ""
    if len(parts) >= 3:
        if parts[2] not in {"blob", "tree"} or len(parts) < 4:
            raise ValueError(f"unsupported GitHub source route: {link}")
        ref = parts[3]
        subpath = "/".join(parts[4:])
    return {"url": link, "owner": owner, "repo": repo, "ref": ref, "subpath": subpath}


def _load_current_index(repo_root: Path) -> tuple[dict[str, dict], str]:
    # The committed Class S mirror is the stable projection scope. The
    # gitignored Class P snapshot may be created as a side effect of another
    # docs step, so it must not change this artifact's bytes or indexPath.
    candidates = [repo_root / "docs" / "graph" / "named" / "index.json"]
    for path in candidates:
        if not path.exists():
            continue
        if path.is_symlink():
            raise ValueError(f"registry index is a symlink: {path}")
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid registry index {path}: {exc}") from exc
        entries = [entry for bucket in data.get("buckets", {}).values() for entry in bucket]
        entries += data.get("awaitingClassification", [])
        current: dict[str, dict] = {}
        for entry in entries:
            skill_id = entry.get("id")
            if not isinstance(skill_id, str) or skill_id in current:
                raise ValueError(f"invalid or duplicate registry skill id: {skill_id!r}")
            current[skill_id] = {
                "sourceRoute": _route((entry.get("links") or {}).get("github")),
                "skillContentSha256": _file_digest(_skill_path(repo_root, skill_id)),
            }
        return current, os.path.relpath(path, repo_root)
    raise ValueError("no canonical named-skill index found")


def _load_observations(observation_dir: Path) -> tuple[list[dict], list[dict]]:
    """Return validated observations and stable top-level observation refs."""
    if observation_dir.is_symlink():
        raise ValueError(f"observation directory is not a real directory: {observation_dir}")
    if not observation_dir.exists():
        return [], []
    if not observation_dir.is_dir():
        raise ValueError(f"observation directory is not a real directory: {observation_dir}")
    observations: list[dict] = []
    refs: list[dict] = []
    for path in sorted(observation_dir.iterdir(), key=lambda item: item.name):
        if path.name.startswith(".") or path.suffix != ".json":
            continue
        _safe_json_path(path, observation_dir)
        if not re.fullmatch(r"[0-9a-f]{64}\.json", path.name):
            raise ValueError(f"observation filename must be <sha256>.json: {path.name}")
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid observation {path}: {exc}") from exc
        _validate(document, CONTRACTS / "observation.schema.json", "observation")
        for observed in document["skills"]:
            _assert_safe_route(observed["sourceRoute"])
        digest = observation_digest(document)
        if path.stem != digest:
            raise ValueError(f"observation filename digest mismatch: {path.name}")
        ids = [entry["id"] for entry in document["skills"]]
        if len(ids) != len(set(ids)) or sorted(ids) != document["scope"]["ids"]:
            raise ValueError(f"observation scope does not match skills: {path.name}")
        observations.append(document)
        refs.append({"digest": digest, "checkedAt": document["checkedAt"], "runId": document["runId"]})
    refs.sort(key=lambda item: (item["checkedAt"], item["digest"], item["runId"]))
    return observations, refs


def _assert_safe_route(route: dict | None) -> None:
    if route is None:
        return
    parsed = urlsplit(route["url"])
    if parsed.username is not None or parsed.password is not None or parsed.query or parsed.fragment:
        raise ValueError("credential-bearing or query-bearing observation route")
    if ".." in Path(route["subpath"]).parts:
        raise ValueError("observation route contains path traversal")


def _parse_time(value: str) -> datetime:
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"invalid observation timestamp: {value!r}") from exc


def _same_route(left: dict | None, right: dict | None) -> bool:
    return left == right


def _current_context(current: dict, skill_id: str) -> dict:
    return current.get(skill_id, {})


def _projection_for_skill(skill_id: str, current: dict, observations: list[dict]) -> dict:
    current_item = _current_context(current, skill_id)
    current_route = current_item.get("sourceRoute")
    current_digest = current_item.get("skillContentSha256")
    candidates: list[tuple[datetime, str, dict, dict]] = []
    mismatches: list[tuple[str, dict, dict]] = []

    for document in observations:
        digest = observation_digest(document)
        for observed in document["skills"]:
            if observed["id"] != skill_id:
                continue
            route_changed = not _same_route(observed["sourceRoute"], current_route)
            content_changed = (
                observed["skillContentSha256"] != current_digest
                or observed["skillContentSha256"] is None
                or current_digest is None
            )
            if route_changed or content_changed:
                reason = "subject-changed" if content_changed else "route-changed"
                mismatches.append((reason, document, observed))
                continue
            candidates.append((_parse_time(document["checkedAt"]), digest, document, observed))

    def base(reason: str, state: str, digest: str | None, observed_at: str | None, observed: dict | None) -> dict:
        return {
            "state": state,
            "reason": reason,
            "observationDigest": digest,
            "observedAt": observed_at,
            "currentSourceRoute": current_route,
            "currentSkillContentSha256": current_digest,
            "observedSourceRoute": observed["sourceRoute"] if observed else None,
            "observedSkillContentSha256": observed["skillContentSha256"] if observed else None,
            "resolvedRevision": observed["resolvedRevision"] if observed else None,
            "deliveredContentSha256": observed["deliveredContentSha256"] if observed else None,
        }

    if not candidates:
        if mismatches:
            reason, document, observed = sorted(
                mismatches,
                key=lambda item: (item[1]["checkedAt"], observation_digest(item[1])),
                reverse=True,
            )[0]
            return base(reason, "unknown", observation_digest(document), document["checkedAt"], observed)
        return base("not-observed", "unknown", None, None, None)

    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    newest_time = candidates[0][0]
    newest = [candidate for candidate in candidates if candidate[0] == newest_time]
    signatures = {
        (candidate[3]["gaiaHealth"], candidate[3]["causeEvidence"]["classifiedCause"], candidate[3]["causeEvidence"]["intrinsicCause"])
        for candidate in newest
    }
    if len(signatures) > 1:
        return base("ambiguous-observation", "unknown", None, newest_time.isoformat().replace("+00:00", "Z"), None)

    _, digest, document, observed = newest[0]
    health = observed["gaiaHealth"]
    category = observed["category"]
    if health == "materialized":
        return base("gaia-materialized", "materializable", digest, document["checkedAt"], observed)
    if health == "refused" and category == "NO_SOURCE" and current_route is None:
        return base("no-source", "not-materializable", digest, document["checkedAt"], observed)
    if health == "failed":
        cause = observed["causeEvidence"]["classifiedCause"]
        intrinsic = observed["causeEvidence"]["intrinsicCause"]
        if intrinsic in INTRINSIC_CAUSES:
            return base("intrinsic-content-failure", "not-materializable", digest, document["checkedAt"], observed)
        if cause == "GIT_CLONE_FAILED":
            return base("inaccessible-at-check", "unknown", digest, document["checkedAt"], observed)
        if cause == "TIMEOUT":
            return base("timeout", "unknown", digest, document["checkedAt"], observed)
        if cause == "SUITE_COMPONENT_FAILED":
            return base("suite-component-failed", "unknown", digest, document["checkedAt"], observed)
        if cause == "UNEXPECTED_SUCCESS":
            return base("contradictory-observation", "unknown", digest, document["checkedAt"], observed)
        return base("unclassified-install-failure", "unknown", digest, document["checkedAt"], observed)
    return base("unexpected-refusal", "unknown", digest, document["checkedAt"], observed)


def build_installability_projection(
    repo_root: Path | str = ROOT,
    observation_dir: Path | str | None = None,
) -> dict:
    """Build the deterministic current-tree projection without network access."""
    repo_root = Path(repo_root).resolve()
    observation_dir = Path(observation_dir) if observation_dir is not None else repo_root / "registry" / "installability" / "observations"
    current, index_path = _load_current_index(repo_root)
    observations, refs = _load_observations(observation_dir)
    projected = {
        skill_id: _projection_for_skill(skill_id, current, observations)
        for skill_id in sorted(current)
    }
    document = {
        "schema": PROJECTION_SCHEMA,
        "indexPath": index_path,
        "observations": refs,
        "skills": projected,
    }
    _validate(document, CONTRACTS / "projection.schema.json", "projection")
    return document

def write_projection(document: dict, output: Path | str) -> bool:
    """Write a projection only if bytes changed; return whether it changed."""
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    encoded = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if output.exists() and output.is_symlink():
        raise ValueError(f"projection output is a symlink: {output}")
    if output.exists() and output.read_text(encoding="utf-8") == encoded:
        return False
    temporary = output.with_name(f".{output.name}.{os.getpid()}.tmp")
    temporary.write_text(encoded, encoding="utf-8")
    os.replace(temporary, output)
    return True


if __name__ == "__main__":
    output = ROOT / "docs" / "graph" / "installability" / "index.json"
    write_projection(build_installability_projection(), output)
    print(output)
