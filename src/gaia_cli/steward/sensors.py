"""Deterministic, local, read-only sensors for Steward V1."""

from __future__ import annotations

import fnmatch
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, Protocol

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError

from gaia_cli.steward.models import Observation, Subject, stable_json


class Sensor(Protocol):
    id: str

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        """Return observations without changing repository state."""


@dataclass(frozen=True)
class DirectoryManifest:
    root: str
    files: dict[str, str]

    @property
    def digest(self) -> str:
        return hashlib.sha256(stable_json(self.files).encode("utf-8")).hexdigest()

    def summary(self) -> dict[str, object]:
        return {"root": self.root, "fileCount": len(self.files), "digest": self.digest}


def _is_ignored(relative_path: str, patterns: Iterable[str]) -> bool:
    for pattern in patterns:
        if fnmatch.fnmatchcase(relative_path, pattern):
            return True
        if pattern.endswith("/**") and relative_path.startswith(pattern[:-3] + "/"):
            return True
    return False


def _manifest(repo_root: Path, relative_root: str, ignore: Iterable[str] = ()) -> DirectoryManifest:
    directory = repo_root / relative_root
    if not directory.is_dir():
        raise FileNotFoundError(f"required directory does not exist: {relative_root}")
    files: dict[str, str] = {}
    for path in sorted(directory.rglob("*")):
        if not path.is_file():
            continue
        relative = path.relative_to(directory).as_posix()
        if _is_ignored(relative, ignore):
            continue
        files[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
    return DirectoryManifest(root=relative_root, files=files)


def _mirror_observation(
    *,
    kind: str,
    subject_id: str,
    sensor_id: str,
    repo_root: Path,
    canonical_root: str,
    mirror_root: str,
    observed_at: str,
    ignore: Iterable[str] = (),
) -> Observation:
    canonical = _manifest(repo_root, canonical_root, ignore)
    mirror = _manifest(repo_root, mirror_root, ignore)
    canonical_paths = set(canonical.files)
    mirror_paths = set(mirror.files)
    missing = sorted(canonical_paths - mirror_paths)
    extra = sorted(mirror_paths - canonical_paths)
    different = sorted(
        path
        for path in canonical_paths & mirror_paths
        if canonical.files[path] != mirror.files[path]
    )
    drift = bool(missing or extra or different)
    observed_state = mirror.summary()
    observed_state.update(
        {
            "missingFromMirror": missing,
            "extraInMirror": extra,
            "contentMismatch": different,
        }
    )
    return Observation(
        kind=kind,
        subject=Subject(type="repository-surface", id=subject_id),
        observed_at=observed_at,
        source=sensor_id,
        status="drift" if drift else "healthy",
        current_state=canonical.summary(),
        observed_state=observed_state,
        confidence=1.0,
        provenance={"canonicalPath": canonical_root, "mirrorPath": mirror_root},
    )


class BundledSchemaMirrorSensor:
    """Compare both schema trees recursively and byte-for-byte."""

    id = "bundled-schema-mirror"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return [
            _mirror_observation(
                kind="bundled_schema_mirror_drift",
                subject_id="registry-schema",
                sensor_id=self.id,
                repo_root=repo_root,
                canonical_root="registry/schema",
                mirror_root="src/gaia_cli/data/registry/schema",
                observed_at=observed_at,
            )
        ]


class AgentSkillMirrorSensor:
    """Compare the checked-in agent skill mirrors recursively."""

    id = "agent-skill-mirror"
    _LOCAL_ONLY_PATTERNS = ("skill-creator/**", "**/__pycache__/**", "**/*.pyc")

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return [
            _mirror_observation(
                kind="agent_skill_mirror_drift",
                subject_id="agent-skill-mirrors",
                sensor_id=self.id,
                repo_root=repo_root,
                canonical_root=".agents/skills",
                mirror_root=".claude/skills",
                observed_at=observed_at,
                ignore=self._LOCAL_ONLY_PATTERNS,
            )
        ]


class DiscoveryGenericMappingSensor:
    """Surface only explicit, current, unresolved mapping decisions.

    Discovery and archive records are evidence of process, not debt.  A
    packet contributes only when it explicitly says it is ``current`` and
    ``unresolved``; archived and otherwise governed records are ignored.  The
    optional local input is deliberately outside canonical data and exists so
    operators can truthfully exercise the report-only queue on a checkout with
    no current unresolved candidate.  This sensor never selects or writes a
    canonical mapping.
    """

    id = "discovery-generic-mapping"
    _PACKETS_ROOT = "registry-for-review/discovery-packets"
    _LOCAL_INPUT = ".gaia/steward/discovery-mapping-input.json"
    _INPUT_SCHEMA = "steward-discovery-mapping-input-v1"
    _MAX_PACKET_BYTES = 2 * 1024 * 1024

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        mapped_candidates = self._canonical_mapped_candidates(repo_root)
        candidates = self._current_packet_candidates(repo_root)
        candidates.extend(self._local_input_candidates(repo_root))
        # Group by canonical identity, rather than by a display spelling from
        # an external packet.  This must happen before lookup and grouping so
        # ``Owner/Open`` cannot bypass canonical ``owner/open`` coverage.
        unique_candidates: dict[str, tuple[dict[str, str], str, str]] = {}
        for item in sorted(candidates, key=lambda item: (item[0]["candidateId"], item[1], item[0]["candidateDisplayId"])):
            unique_candidates.setdefault(item[0]["candidateId"], item)
        observations: list[Observation] = []
        for candidate_id, (candidate, source_path, digest) in sorted(unique_candidates.items()):
            # A named record for this canonical candidate with a targetSkillId
            # is objective evidence that this mapping was already governed.
            if candidate_id in mapped_candidates:
                continue
            observations.append(Observation(
                kind="generic_mapping",
                subject=Subject(type="generic-mapping-candidate", id=candidate_id),
                observed_at=observed_at,
                source=self.id,
                status="drift",
                current_state={"genericMapping": "unresolved"},
                observed_state={
                    # One exact candidate is one real shared mapping decision;
                    # repository membership is not a decision target.
                    "decisionTarget": f"generic-mapping/{candidate_id}",
                    "candidateId": candidate_id,
                    "candidateDisplayId": candidate["candidateDisplayId"],
                    "sourceRepo": candidate["sourceRepo"],
                    "sourceState": "current",
                    "disposition": "unresolved",
                    "input": source_path,
                    "inputDigest": digest,
                },
                confidence=1.0,
                provenance={
                    "inputPath": source_path,
                    "sourceRepo": candidate["sourceRepo"],
                    "candidateDisplayId": candidate["candidateDisplayId"],
                },
            ))
        return observations

    def _current_packet_candidates(self, repo_root: Path) -> list[tuple[dict[str, str], str, str]]:
        directory = repo_root / self._PACKETS_ROOT
        if not directory.is_dir():
            return []
        result: list[tuple[dict[str, str], str, str]] = []
        for path in sorted(directory.glob("*.json")):
            raw, content = self._read_object(path, repo_root, "discovery packet")
            # Legacy packets with no explicit lifecycle state are intentionally
            # not interpreted as unresolved.
            if raw.get("sourceState") != "current" or raw.get("disposition") != "unresolved":
                continue
            source_repo = raw.get("sourceRepo")
            proposed = raw.get("proposedSkills")
            if not isinstance(source_repo, str) or not source_repo.strip() or not isinstance(proposed, list):
                continue
            digest = hashlib.sha256(content).hexdigest()
            relative_path = path.relative_to(repo_root).as_posix()
            for item in proposed:
                if isinstance(item, dict) and isinstance(item.get("id"), str):
                    candidate = self._candidate_record(item["id"], source_repo)
                    if candidate is not None:
                        result.append((candidate, relative_path, digest))
        return result

    def _local_input_candidates(self, repo_root: Path) -> list[tuple[dict[str, str], str, str]]:
        path = repo_root / self._LOCAL_INPUT
        if not path.exists():
            return []
        # Read exactly once: parsing, validation, and provenance digest below
        # all bind to this same byte sequence, not to a later path read.
        raw, content = self._read_object(path, repo_root, "local discovery mapping input")
        if raw.get("schemaVersion") != self._INPUT_SCHEMA or not isinstance(raw.get("candidates"), list):
            raise ValueError(f"invalid local discovery mapping input: {self._LOCAL_INPUT}")
        digest = hashlib.sha256(content).hexdigest()
        result: list[tuple[dict[str, str], str, str]] = []
        for item in raw["candidates"]:
            if not isinstance(item, dict):
                continue
            candidate_id, source_repo = item.get("candidateId"), item.get("sourceRepo")
            if (
                item.get("sourceState") == "current"
                and item.get("disposition") == "unresolved"
                and isinstance(candidate_id, str)
                and isinstance(source_repo, str)
            ):
                candidate = self._candidate_record(candidate_id, source_repo)
                if candidate is not None:
                    result.append((candidate, self._LOCAL_INPUT, digest))
        return result

    @staticmethod
    def _candidate_record(candidate_id: str, source_repo: str) -> dict[str, str] | None:
        """Return canonical identity while retaining the external spelling.

        Candidate locators are restricted to ASCII slash-separated identifier
        components.  In particular, invalid punctuation is not repaired or
        collapsed: ``owner//open`` cannot collide with ``owner/open``.
        """
        display_id = candidate_id.strip()
        canonical_id = display_id.casefold()
        if not display_id or not source_repo.strip() or not canonical_id.isascii():
            return None
        if not re.fullmatch(r"[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?(?:/[a-z0-9](?:[a-z0-9._-]*[a-z0-9])?)*", canonical_id):
            return None
        return {
            "candidateId": canonical_id,
            "candidateDisplayId": display_id,
            "sourceRepo": source_repo.strip(),
        }

    def _canonical_mapped_candidates(self, repo_root: Path) -> set[str]:
        mapped: set[str] = set()
        directory = repo_root / "registry/named"
        if not directory.is_dir():
            return mapped
        for path in sorted(directory.rglob("*.json")):
            raw, _ = self._read_object(path, repo_root, "named skill")
            candidate_id, target = raw.get("id"), raw.get("targetSkillId")
            if isinstance(candidate_id, str) and isinstance(target, str) and target.strip():
                candidate = self._candidate_record(candidate_id, "canonical")
                if candidate is None:
                    raise ValueError(f"invalid canonical named skill id: {path.relative_to(repo_root)}")
                mapped.add(candidate["candidateId"])
        return mapped

    def _read_object(self, path: Path, repo_root: Path, label: str) -> tuple[dict[str, object], bytes]:
        content = path.read_bytes()
        if len(content) > self._MAX_PACKET_BYTES:
            raise ValueError(f"{label} exceeds safety limit: {path.relative_to(repo_root)}")
        try:
            raw = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid {label}: {path.relative_to(repo_root)}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"{label} must be an object: {path.relative_to(repo_root)}")
        return raw, content


class RegistryIntegritySensor:
    """Validate generic nodes and their local graph references without mutation."""

    id = "registry-integrity"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        schema_path = repo_root / "registry/schema/skill.schema.json"
        meta_path = repo_root / "registry/schema/meta.json"
        nodes_root = repo_root / "registry/nodes"
        if not schema_path.is_file():
            raise FileNotFoundError("required schema does not exist: registry/schema/skill.schema.json")
        if not meta_path.is_file():
            raise FileNotFoundError("required policy does not exist: registry/schema/meta.json")
        if not nodes_root.is_dir():
            raise FileNotFoundError("required directory does not exist: registry/nodes")

        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        try:
            Draft7Validator.check_schema(schema)
        except SchemaError as exc:
            raise ValueError(f"invalid registry skill schema: {exc.message}") from exc
        validator = Draft7Validator(schema)
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        min_prereqs = meta.get("types", {}).get("minPrereqs", {})
        if not isinstance(min_prereqs, dict) or not all(
            isinstance(kind, str)
            and isinstance(floor, int)
            and not isinstance(floor, bool)
            and floor >= 0
            for kind, floor in min_prereqs.items()
        ):
            raise ValueError("registry/schema/meta.json types.minPrereqs is invalid")

        paths = sorted(nodes_root.rglob("*.json"))
        violations: list[dict[str, str]] = []
        nodes: dict[str, tuple[Path, dict[str, object]]] = {}
        manifest: dict[str, str] = {}
        if not paths:
            violations.append({"path": "registry/nodes", "error": "no JSON node files found"})

        for path in paths:
            relative = path.relative_to(repo_root).as_posix()
            raw = path.read_bytes()
            manifest[relative] = hashlib.sha256(raw).hexdigest()
            try:
                node = json.loads(raw)
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                violations.append({"path": relative, "error": f"invalid JSON: {exc}"})
                continue
            if not isinstance(node, dict):
                violations.append({"path": relative, "error": "node must be a JSON object"})
                continue
            for error in sorted(validator.iter_errors(node), key=lambda item: list(item.path)):
                pointer = "/" + "/".join(str(part) for part in error.path)
                violations.append(
                    {"path": relative, "error": f"schema {pointer}: {error.message}"}
                )
            skill_id = node.get("id")
            if not isinstance(skill_id, str) or not skill_id:
                continue
            if path.stem != skill_id:
                violations.append(
                    {"path": relative, "error": f"filename does not match id {skill_id!r}"}
                )
            if skill_id in nodes:
                first_path = nodes[skill_id][0].relative_to(repo_root).as_posix()
                violations.append(
                    {"path": relative, "error": f"duplicate id {skill_id!r}; first in {first_path}"}
                )
            else:
                nodes[skill_id] = (path, node)

        known_ids = set(nodes)
        for skill_id in sorted(nodes):
            path, node = nodes[skill_id]
            relative = path.relative_to(repo_root).as_posix()
            for field in ("prerequisites", "derivatives"):
                references = node.get(field)
                if not isinstance(references, list):
                    continue
                for reference in references:
                    if isinstance(reference, str) and reference not in known_ids:
                        violations.append(
                            {"path": relative, "error": f"{field} references missing id {reference!r}"}
                        )

        for cycle in _dependency_cycles(nodes):
            violations.append(
                {
                    "path": "registry/nodes",
                    "error": f"dependency cycle detected: {' -> '.join(cycle)}",
                }
            )

        violations.extend(_prerequisite_count_violations(nodes, min_prereqs, repo_root))

        violations.sort(key=lambda item: (item["path"], item["error"]))
        digest = hashlib.sha256(stable_json(manifest).encode("utf-8")).hexdigest()
        observed_state: dict[str, object] = {
            "valid": not violations,
            "nodeCount": len(nodes),
            "violationCount": len(violations),
            "digest": digest,
            "violations": violations,
        }
        return [
            Observation(
                kind="registry_integrity_failed",
                subject=Subject(type="repository-surface", id="registry-nodes"),
                observed_at=observed_at,
                source=self.id,
                status="drift" if violations else "healthy",
                current_state={"valid": True},
                observed_state=observed_state,
                confidence=1.0,
                provenance={
                    "nodesPath": "registry/nodes",
                    "schemaPath": "registry/schema/skill.schema.json",
                    "typePolicyPath": "registry/schema/meta.json",
                },
            )
        ]


def _prerequisite_count_violations(
    nodes: dict[str, tuple[Path, dict[str, object]]],
    min_prereqs: dict[str, int],
    repo_root: Path,
) -> list[dict[str, str]]:
    """Match the bounded type floor in canonical validate_prerequisites_count."""

    violations: list[dict[str, str]] = []
    for skill_id in sorted(nodes):
        path, node = nodes[skill_id]
        skill_type = node.get("type")
        prerequisites = node.get("prerequisites")
        if not isinstance(skill_type, str) or not isinstance(prerequisites, list):
            continue  # JSON Schema reports malformed fields.
        actual = len(prerequisites)
        minimum = min_prereqs.get(skill_type, 0)
        if skill_type == "basic" and actual > 0:
            error = f"basic skill {skill_id!r} must have 0 prerequisites (has {actual})"
        elif actual < minimum:
            error = (
                f"{skill_type} skill {skill_id!r} needs >={minimum} prerequisites "
                f"(has {actual})"
            )
        else:
            continue
        violations.append(
            {"path": path.relative_to(repo_root).as_posix(), "error": error}
        )
    return violations


def _dependency_cycles(
    nodes: dict[str, tuple[Path, dict[str, object]]],
) -> list[tuple[str, ...]]:
    """Return deterministic prerequisite cycles using the canonical edge direction.

    Canonical validation treats each prerequisite as an edge from prerequisite
    to dependent. Derivative metadata is reference-checked but does not define
    the DAG, matching ``scripts.validate.validate_dag``.
    """

    children: dict[str, list[str]] = {skill_id: [] for skill_id in nodes}
    for target_id in sorted(nodes):
        prerequisites = nodes[target_id][1].get("prerequisites")
        if not isinstance(prerequisites, list):
            continue
        for source_id in prerequisites:
            if isinstance(source_id, str) and source_id in children:
                children[source_id].append(target_id)
    for values in children.values():
        values.sort()

    white, gray, black = 0, 1, 2
    color = {skill_id: white for skill_id in nodes}
    stack: list[str] = []
    cycles: set[tuple[str, ...]] = set()

    def visit(skill_id: str) -> None:
        color[skill_id] = gray
        stack.append(skill_id)
        for child_id in children[skill_id]:
            if color[child_id] == white:
                visit(child_id)
            elif color[child_id] == gray:
                start = stack.index(child_id)
                cycles.add(tuple(stack[start:] + [child_id]))
        stack.pop()
        color[skill_id] = black

    for skill_id in sorted(nodes):
        if color[skill_id] == white:
            visit(skill_id)
    return sorted(cycles)


def default_sensors() -> tuple[Sensor, ...]:
    return (
        BundledSchemaMirrorSensor(),
        AgentSkillMirrorSensor(),
        RegistryIntegritySensor(),
        DiscoveryGenericMappingSensor(),
    )
