"""Separate resolver and installer for immutable, non-ranked support components."""

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

from gaia_cli.install import _run_git, get_gaia_home


_SCHEMA_NAME = "supportComponent.schema.json"
_MANIFEST_NAME = "components.json"


def support_manifest_path(registry_path: str) -> Path:
    from gaia_cli.registry import registry_dir
    return Path(registry_dir(registry_path)) / "support" / _MANIFEST_NAME


def validate_support_manifest(
    data: object,
    schema_path: str | Path | None = None,
    named_ids: set[str] | None = None,
) -> list[str]:
    """Strictly validate support records; never interpret them as skill nodes."""
    if schema_path is None:
        schema_path = Path(__file__).parent / "data" / "registry" / "schema" / _SCHEMA_NAME
    try:
        import jsonschema
    except ImportError as exc:
        raise RuntimeError("Support component validation requires jsonschema") from exc
    try:
        schema = json.loads(Path(schema_path).read_text(encoding="utf-8"))
        jsonschema.Draft7Validator.check_schema(schema)
        validator = jsonschema.Draft7Validator(schema)
        errors = sorted(
            validator.iter_errors(data),
            key=lambda error: list(map(str, error.absolute_path)),
        )
        messages = [".".join(map(str, error.absolute_path)) + f": {error.message}" for error in errors]
        if isinstance(data, dict) and isinstance(data.get("components"), list):
            seen_ids = set()
            for index, component in enumerate(data["components"]):
                if not isinstance(component, dict):
                    continue
                component_id = component.get("id")
                if not isinstance(component_id, str):
                    continue
                if component_id in seen_ids:
                    messages.append(
                        f"components.{index}.id: duplicate support component id '{component_id}'"
                    )
                seen_ids.add(component_id)
                source = component.get("source")
                distribution = component.get("distribution")
                if not isinstance(source, dict):
                    continue
                repository = source.get("repository")
                commit = source.get("commit")
                source_path = source.get("path")
                if isinstance(repository, str):
                    owner_repo = repository.removeprefix("https://github.com/")
                    if distribution != owner_repo:
                        messages.append(
                            f"components.{index}.distribution: must match source repository '{owner_repo}'"
                        )
                    if isinstance(commit, str) and isinstance(source_path, str):
                        expected_url = f"{repository}/blob/{commit}/{source_path}/SKILL.md"
                        if source.get("pinnedBlobUrl") != expected_url:
                            messages.append(
                                f"components.{index}.source.pinnedBlobUrl: must equal '{expected_url}'"
                            )
                supports = component.get("supports", [])
                if named_ids is not None and isinstance(supports, list):
                    for target in supports:
                        if isinstance(target, str) and target not in named_ids:
                            messages.append(
                                f"components.{index}.supports: target '{target}' is not in the canonical named catalog"
                            )
        return messages
    except (OSError, json.JSONDecodeError) as exc:
        return [f"cannot load support component schema: {exc}"]


def _load_named_catalog_ids(registry_path: str) -> set[str]:
    from gaia_cli.registry import named_skills_index_path

    path = Path(named_skills_index_path(registry_path))
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not load canonical named catalog {path}: {exc}") from exc
    buckets = data.get("buckets") if isinstance(data, dict) else None
    if not isinstance(buckets, dict):
        raise ValueError(f"Invalid canonical named catalog {path}: missing buckets")
    return {
        entry["id"]
        for entries in buckets.values()
        if isinstance(entries, list)
        for entry in entries
        if isinstance(entry, dict) and isinstance(entry.get("id"), str)
    }


def load_support_components(registry_path: str) -> list[dict]:
    """Read optional support data. Missing manifests preserve legacy registries."""
    path = support_manifest_path(registry_path)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Invalid support manifest {path}: {exc}") from exc
    try:
        named_ids = _load_named_catalog_ids(registry_path)
    except ValueError as exc:
        raise ValueError(f"Invalid support manifest {path}: {exc}") from exc
    errors = validate_support_manifest(data, named_ids=named_ids)
    if errors:
        raise ValueError(f"Invalid support manifest {path}: {errors[0]}")
    return data["components"]


def resolve_support_components(target_id: str, registry_path: str) -> list[dict]:
    """Resolve only records explicitly declaring target_id in supports."""
    return [
        record
        for record in load_support_components(registry_path)
        if target_id in record["supports"]
    ]


def _support_receipt_path(location: str) -> Path:
    if location == "global":
        return Path(get_gaia_home()) / "support-install-manifest.json"
    if location != "local":
        raise ValueError(f"Invalid location '{location}'; must be 'local' or 'global'")
    return Path(".gaia") / "support-install-manifest.json"


def _support_root(location: str) -> Path:
    from gaia_cli.install import get_repo_skills_dir
    return Path(get_repo_skills_dir(location))


def _read_receipts(location: str) -> dict:
    path = _support_receipt_path(location)
    if not path.exists():
        return {"installed": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict) or not isinstance(data.get("installed"), list):
            raise ValueError("expected an installed list")
        for entry in data["installed"]:
            if (
                not isinstance(entry, dict)
                or not isinstance(entry.get("id"), str)
                or not isinstance(entry.get("localPath"), str)
                or not isinstance(entry.get("targets"), list)
                or any(not isinstance(target, str) for target in entry["targets"])
            ):
                raise ValueError("installed entries require id, localPath, and string targets")
        return data
    except (OSError, json.JSONDecodeError, ValueError) as exc:
        raise ValueError(f"Invalid support install receipt {path}: {exc}") from exc


def _write_receipts(location: str, receipts: dict) -> None:
    path = _support_receipt_path(location)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as temp:
            temp.write(json.dumps(receipts, indent=2) + "\n")
        Path(temp_name).replace(path)
    finally:
        Path(temp_name).unlink(missing_ok=True)


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _fetch_pinned_source(record: dict, cache_root: Path) -> tuple[Path, Path] | None:
    source = record["source"]
    repo_parts = source["repository"].removeprefix("https://github.com/").split("/")
    if len(repo_parts) != 2 or any(part in ("", ".", "..") for part in repo_parts):
        return None
    owner, repo_name = repo_parts
    cache = cache_root / owner / f"{repo_name}-{source['commit']}"
    if not (cache / ".git").is_dir():
        if cache.exists():
            shutil.rmtree(cache)
        cache.parent.mkdir(parents=True, exist_ok=True)
        if not _run_git(["clone", "--no-checkout", "--", source["repository"] + ".git", str(cache)]):
            return None
        if not _run_git(["checkout", "--detach", source["commit"]], cwd=str(cache)):
            return None
    else:
        # Never pull/update a support checkout: the record pins its exact commit.
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"], cwd=cache, capture_output=True, text=True
        )
        if result.returncode != 0:
            return None
        head = result.stdout.strip()
        if head != source["commit"] and not _run_git(["checkout", "--detach", source["commit"]], cwd=str(cache)):
            return None
    result = subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=cache, capture_output=True, text=True
    )
    if result.returncode != 0 or result.stdout.strip() != source["commit"]:
        return None
    skill_dir = cache / source["path"]
    skill_file = skill_dir / "SKILL.md"
    license_file = cache / source["licensePath"]
    try:
        skill_dir.resolve().relative_to(cache.resolve())
        license_file.resolve().relative_to(cache.resolve())
    except ValueError:
        return None
    cursor = cache
    for part in Path(source["path"]).parts:
        cursor = cursor / part
        if cursor.is_symlink():
            return None
    if license_file.is_symlink():
        return None
    if not skill_file.is_file():
        return None
    for directory, child_dirs, child_files in os.walk(skill_dir, followlinks=False):
        if any((Path(directory) / name).is_symlink() for name in child_dirs + child_files):
            return None
    if _sha256(skill_file) != source["skillSha256"]:
        print(f"Error: pinned source hash mismatch for support component '{record['id']}'.", file=sys.stderr)
        return None
    if not license_file.is_file() or _sha256(license_file) != source["licenseSha256"]:
        print(f"Error: pinned license hash mismatch for support component '{record['id']}'.", file=sys.stderr)
        return None
    return skill_dir, license_file


def install_support_components(target_id: str, registry_path: str, location: str = "local") -> bool:
    """Install declared support SKILL.md payloads into the harness skill directory."""
    try:
        records = resolve_support_components(target_id, registry_path)
    except (OSError, ValueError, RuntimeError) as exc:
        print(f"Error: could not resolve support components for '{target_id}': {exc}", file=sys.stderr)
        return False
    if location not in ("local", "global"):
        print(f"Error: Invalid location '{location}'; must be 'local' or 'global'", file=sys.stderr)
        return False
    if not records:
        return True
    root = _support_root(location)
    cache = Path(get_gaia_home()) / "support-sources"
    try:
        receipts = _read_receipts(location)
    except (OSError, ValueError) as exc:
        print(f"Error: could not read support install receipt: {exc}", file=sys.stderr)
        return False
    failures = []
    committed_paths = []
    for record in records:
        # Validate identifiers again at the filesystem boundary.
        support_id = record["id"]
        if not re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", support_id):
            failures.append(support_id)
            continue
        prior = next((item for item in receipts["installed"] if item.get("id") == support_id), None)
        try:
            source_result = _fetch_pinned_source(record, cache)
            source_dir, license_file = source_result if source_result is not None else (None, None)
        except (OSError, subprocess.SubprocessError) as exc:
            print(f"Error: could not fetch support component '{support_id}': {exc}", file=sys.stderr)
            source_dir = None
        if source_dir is None:
            failures.append(support_id)
            continue
        destination = root / support_id
        expected_path = str(destination.resolve())
        if prior and prior.get("commit") == record["source"]["commit"] and prior.get("localPath") == expected_path and (destination / ".gaia-support-component").is_file() and (destination / "SKILL.md").is_file():
            prior["targets"] = sorted(set(prior.get("targets", [])) | {target_id})
            continue
        # Never overwrite an unrelated harness skill or a symlink at the target.
        if destination.is_symlink() or (destination.exists() and (prior is None or not (destination / ".gaia-support-component").is_file())):
            failures.append(support_id)
            print(f"Error: refusing to overwrite existing skill path for support component '{support_id}'.", file=sys.stderr)
            continue
        if prior and prior.get("localPath") != expected_path:
            failures.append(support_id)
            print(f"Error: refusing unsafe managed path for support component '{support_id}'.", file=sys.stderr)
            continue
        destination.parent.mkdir(parents=True, exist_ok=True)
        staging = destination.with_name(destination.name + ".gaia-support-tmp")
        if staging.exists() or staging.is_symlink():
            if staging.is_symlink() or staging.is_file():
                staging.unlink()
            else:
                shutil.rmtree(staging)
        backup = None
        try:
            shutil.copytree(source_dir, staging)
            # The upstream notice may live at repository root, outside the skill directory.
            license_name = Path(record["source"]["licensePath"]).name
            license_destination = staging / license_name
            if license_destination.exists() and _sha256(license_destination) != record["source"]["licenseSha256"]:
                license_destination = staging / f"UPSTREAM-{license_name}"
            shutil.copy2(license_file, license_destination)
            (staging / ".gaia-support-component").write_text("support-only\n", encoding="utf-8")
            if destination.exists():
                backup = destination.with_name(destination.name + ".gaia-support-backup")
                if backup.exists():
                    shutil.rmtree(backup, ignore_errors=True)
                destination.replace(backup)
            staging.replace(destination)
            committed_paths.append((destination, backup))
        except OSError:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)
            if backup and backup.exists() and not destination.exists():
                backup.replace(destination)
            failures.append(support_id)
            continue
        entry = {
            "id": support_id,
            "installedAt": datetime.now(timezone.utc).isoformat(),
            "commit": record["source"]["commit"],
            "skillSha256": record["source"]["skillSha256"],
            "localPath": str(destination.resolve()),
            "location": location,
            "targets": sorted(set((prior or {}).get("targets", [])) | {target_id}),
        }
        if prior:
            receipts["installed"].remove(prior)
        receipts["installed"].append(entry)
    try:
        _write_receipts(location, receipts)
    except OSError as exc:
        for destination, backup in reversed(committed_paths):
            if destination.exists() and (destination / ".gaia-support-component").is_file():
                shutil.rmtree(destination, ignore_errors=True)
            if backup and backup.exists():
                backup.replace(destination)
        print(f"Error: could not write support install receipt: {exc}", file=sys.stderr)
        return False
    for _destination, backup in committed_paths:
        if backup and backup.exists():
            shutil.rmtree(backup, ignore_errors=True)
    if failures:
        print(f"Error: support component install failed: {', '.join(failures)}", file=sys.stderr)
        return False
    return True


def uninstall_target_support(target_id: str, location: str = "local") -> None:
    """Remove target references and delete support payloads no longer referenced."""
    if not _support_receipt_path(location).exists():
        return
    receipts = _read_receipts(location)
    remaining = []
    paths_to_remove = []
    for entry in receipts["installed"]:
        targets = entry.get("targets", [])
        if target_id not in targets:
            remaining.append(entry)
            continue
        entry["targets"] = [target for target in targets if target != target_id]
        if entry["targets"]:
            remaining.append(entry)
            continue
        path = Path(entry.get("localPath", ""))
        root = _support_root(location).resolve()
        try:
            if path.is_symlink() or path.resolve(strict=False).parent != root or not (path / ".gaia-support-component").is_file():
                raise ValueError("not an owned support payload")
            paths_to_remove.append(path)
        except (ValueError, OSError):
            print(f"Warning: refusing to remove unowned support path: {path}", file=sys.stderr)
            remaining.append(entry)
    receipts["installed"] = remaining
    _write_receipts(location, receipts)
    for path in paths_to_remove:
        try:
            if path.is_dir():
                shutil.rmtree(path)
            elif path.exists():
                path.unlink()
        except OSError as exc:
            print(f"Warning: could not remove support payload {path}: {exc}", file=sys.stderr)
