"""Deterministic, local, read-only sensors for Steward V1."""

from __future__ import annotations

import ast
import hashlib
import json
import re
from urllib.parse import urlparse
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Protocol

from jsonschema import Draft7Validator
from jsonschema.exceptions import SchemaError

from gaia_cli.steward.mirrors import (
    AGENT_SKILL_MIRROR,
    BUNDLED_SCHEMA_MIRROR,
    MirrorSpec,
    is_ignored as _is_ignored,
)
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


def _mirror_observation(spec: MirrorSpec, repo_root: Path, observed_at: str) -> Observation:
    canonical = _manifest(repo_root, spec.canonical_root, spec.ignore)
    mirror = _manifest(repo_root, spec.mirror_root, spec.ignore)
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
        kind=spec.debt_kind,
        subject=Subject(type="repository-surface", id=spec.subject_id),
        observed_at=observed_at,
        source=spec.id,
        status="drift" if drift else "healthy",
        current_state=canonical.summary(),
        observed_state=observed_state,
        confidence=1.0,
        provenance={"canonicalPath": spec.canonical_root, "mirrorPath": spec.mirror_root},
    )


class BundledSchemaMirrorSensor:
    """Compare both schema trees recursively and byte-for-byte."""

    id = BUNDLED_SCHEMA_MIRROR.id

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return [_mirror_observation(BUNDLED_SCHEMA_MIRROR, repo_root, observed_at)]


class AgentSkillMirrorSensor:
    """Compare the checked-in agent skill mirrors recursively."""

    id = AGENT_SKILL_MIRROR.id

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return [_mirror_observation(AGENT_SKILL_MIRROR, repo_root, observed_at)]


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
            # not interpreted as unresolved. A packet that explicitly declares
            # itself current/unresolved is controlled input and must be valid.
            if raw.get("sourceState") != "current" or raw.get("disposition") != "unresolved":
                continue
            source_repo = raw.get("sourceRepo")
            proposed = raw.get("proposedSkills")
            relative_path = path.relative_to(repo_root).as_posix()
            if not isinstance(source_repo, str) or not source_repo.strip() or not isinstance(proposed, list):
                raise ValueError(f"invalid current unresolved discovery packet: {relative_path}")
            digest = hashlib.sha256(content).hexdigest()
            for item in proposed:
                if not isinstance(item, dict) or not isinstance(item.get("id"), str):
                    raise ValueError(f"invalid current unresolved discovery candidate: {relative_path}")
                candidate = self._candidate_record(item["id"], source_repo)
                if candidate is None:
                    raise ValueError(f"invalid current unresolved discovery candidate: {relative_path}")
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
            # Only the explicit current/unresolved state is controlled input.
            # Optional, archived, and processed entries remain safely ignored.
            if item.get("sourceState") != "current" or item.get("disposition") != "unresolved":
                continue
            candidate_id, source_repo = item.get("candidateId"), item.get("sourceRepo")
            if not isinstance(candidate_id, str) or not isinstance(source_repo, str):
                raise ValueError(f"invalid current unresolved local discovery candidate: {self._LOCAL_INPUT}")
            candidate = self._candidate_record(candidate_id, source_repo)
            if candidate is None:
                raise ValueError(f"invalid current unresolved local discovery candidate: {self._LOCAL_INPUT}")
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
        # Validate the submitted spelling before any case-folding.  Unicode
        # characters such as long-s (ſ), Kelvin sign (K), and sharp-s (ß)
        # can fold into ASCII or otherwise alter an identifier after this
        # boundary; accepting them would make controlled input collide with a
        # different canonical mapping.
        if not display_id or not display_id.isascii() or not source_repo.strip():
            return None
        canonical_id = display_id.casefold()
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
        for path in sorted(directory.rglob("*.md")):
            raw = self._read_named_markdown(path, repo_root)
            self._add_canonical_mapping(mapped, raw, path, repo_root)
        # JSON named records are legacy but remain supported when valid.
        for path in sorted(directory.rglob("*.json")):
            raw, _ = self._read_object(path, repo_root, "named skill")
            self._add_canonical_mapping(mapped, raw, path, repo_root)
        return mapped

    def _add_canonical_mapping(
        self, mapped: set[str], raw: dict[str, object], path: Path, repo_root: Path,
    ) -> None:
        candidate_id = raw.get("id")
        target = raw.get("genericSkillRef") or raw.get("targetSkillId")
        if not isinstance(candidate_id, str) or not isinstance(target, str) or not target.strip():
            return
        candidate = self._candidate_record(candidate_id, "canonical")
        if candidate is None:
            raise ValueError(f"invalid canonical named skill id: {path.relative_to(repo_root)}")
        mapped.add(candidate["candidateId"])

    def _read_named_markdown(self, path: Path, repo_root: Path) -> dict[str, object]:
        content = path.read_bytes()
        if len(content) > self._MAX_PACKET_BYTES:
            raise ValueError(f"named skill exceeds safety limit: {path.relative_to(repo_root)}")
        try:
            text = content.decode("utf-8")
            from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
            _fence, frontmatter, _body = split_frontmatter(text)
            raw = load_yaml_simple(frontmatter)
        except Exception as exc:
            raise ValueError(f"invalid named skill: {path.relative_to(repo_root)}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"named skill frontmatter must be an object: {path.relative_to(repo_root)}")
        return raw

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


class CliContractSensor:
    """Compare the CLI's three declarations of its own command surface.

    A CLI has more than one place where it says what it is, and those places
    drift apart quietly. This sensor reads all three statically — never by
    importing the code it is auditing — and reports only differences that are
    exact:

    - a command the loader will dispatch but the help surface never lists, so
      it works and is undiscoverable;
    - a command the help surface advertises with nothing behind it;
    - a command the agent contract documents that does not exist.

    The last direction is deliberately one-way. The contract's list is an
    intentionally curated lifecycle subset, so "documented but absent" is a
    lie about the CLI while "present but undocumented" is an editorial choice.
    Reporting the second would bury the first in noise.
    """

    id = "cli-contract"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        from gaia_cli.steward.cli_contract import (
            BUILTIN_COMMANDS,
            CONTRACT_DOCUMENT,
            PUBLIC_SOURCE,
            discovered_commands,
            documented_commands,
            public_commands,
        )

        discovered = discovered_commands(repo_root)
        public = public_commands(repo_root)
        documented = documented_commands(repo_root)

        dispatchable = set(discovered) | set(BUILTIN_COMMANDS)
        undiscoverable = sorted(set(discovered) - set(public))
        advertised_but_absent = sorted(set(public) - dispatchable)
        if documented is None:
            documented_but_absent: list[str] = []
            contract_state = "absent"
        else:
            documented_but_absent = sorted(set(documented) - dispatchable)
            contract_state = "present"

        violations = [
            {"kind": "undiscoverable", "command": name, "detail": f"defined in {discovered[name]}, absent from PUBLIC_COMMANDS"}
            for name in undiscoverable
        ]
        violations.extend(
            {"kind": "advertised-but-absent", "command": name, "detail": "listed in PUBLIC_COMMANDS with no command behind it"}
            for name in advertised_but_absent
        )
        violations.extend(
            {"kind": "documented-but-absent", "command": name, "detail": f"documented in {CONTRACT_DOCUMENT} but not dispatchable"}
            for name in documented_but_absent
        )
        if contract_state == "absent":
            violations.append({
                "kind": "contract-missing",
                "command": "-",
                "detail": f"{CONTRACT_DOCUMENT} no longer declares a top-level command surface",
            })
        violations.sort(key=lambda item: (item["kind"], item["command"]))

        return [
            Observation(
                kind="cli_contract_drift",
                subject=Subject(type="repository-surface", id="cli-command-surface"),
                observed_at=observed_at,
                source=self.id,
                status="drift" if violations else "healthy",
                current_state={"consistent": True},
                observed_state={
                    "consistent": not violations,
                    "violationCount": len(violations),
                    "discoveredCount": len(discovered),
                    "publicCount": len(public),
                    "contract": contract_state,
                    "violations": violations,
                },
                confidence=1.0,
                provenance={
                    "commandsPath": "src/gaia_cli/commands",
                    "publicPath": PUBLIC_SOURCE,
                    "contractPath": CONTRACT_DOCUMENT,
                },
            )
        ]


class TaxonomyScriptDriftSensor:
    """Verify rank mapping and evidence type lists across scripts/ and src/ use canonical sources."""

    id = "taxonomy-script-drift"
    _EXCLUDED_RELATIVE_PATHS = frozenset({
        "src/gaia_cli/taxonomy.py",
        "src/gaia_cli/steward/sensors.py",
        "scripts/check_taxonomy_authority.py",
        "scripts/check_rank_vocabulary.py",
    })
    _DEAD_TYPE_COMPARE = re.compile(
        r"(?<![\w'\"])type['\"]?\]?\s*[=!]={1,2}\s*['\"](?:unique|ultimate|extra)['\"]",
        re.IGNORECASE,
    )
    _DELETED_SHIM_CALL = re.compile(
        r"(?:(?:trustMagnitude|tm)\.computeBranch\s*\(|(?<![\w.])rank_word\s*\(|(?<![\w.])format_rank_label\s*\()"
    )
    _BANNED_RANK_VOCABULARY = re.compile(r"\b(?:Transcendent|Hardened)\b")

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        violations: list[dict[str, Any]] = []
        canonical_types = self._canonical_evidence_types(repo_root)

        self._check_trust_magnitude_evidence_types(repo_root, canonical_types, violations)
        scanned_files_count = self._scan_scripts_and_src(repo_root, canonical_types, violations)

        violations.sort(
            key=lambda item: (
                item.get("path", ""),
                item.get("line", 0),
                item.get("kind", ""),
                item.get("detail", ""),
            )
        )
        drift = bool(violations)

        observed_state: dict[str, Any] = {
            "consistent": not drift,
            "violationCount": len(violations),
            "scannedFileCount": scanned_files_count,
            "canonicalEvidenceTypeCount": len(canonical_types),
            "violations": violations,
        }

        return [
            Observation(
                kind="taxonomy_script_drift",
                subject=Subject(type="repository-surface", id="taxonomy-script-surface"),
                observed_at=observed_at,
                source=self.id,
                status="drift" if drift else "healthy",
                current_state={"consistent": True},
                observed_state=observed_state,
                confidence=1.0,
                provenance={
                    "scriptsPath": "scripts",
                    "srcPath": "src",
                    "taxonomyPath": "src/gaia_cli/taxonomy.py",
                    "metaPath": "registry/schema/meta.json",
                    "trustMagnitudePath": "src/gaia_cli/trustMagnitude.py",
                },
            )
        ]

    def _canonical_evidence_types(self, repo_root: Path) -> set[str]:
        meta_path = repo_root / "registry/schema/meta.json"
        if not meta_path.is_file():
            meta_path = repo_root / "src/gaia_cli/data/registry/schema/meta.json"
        if not meta_path.is_file():
            return set()
        try:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            types = meta.get("evidence", {}).get("types", [])
            return {
                item["id"]
                for item in types
                if isinstance(item, dict) and isinstance(item.get("id"), str)
            }
        except Exception:
            return set()

    def _check_trust_magnitude_evidence_types(
        self, repo_root: Path, canonical_types: set[str], violations: list[dict[str, Any]]
    ) -> None:
        tm_path = repo_root / "src/gaia_cli/trustMagnitude.py"
        if not tm_path.is_file():
            return
        try:
            tree = ast.parse(tm_path.read_text(encoding="utf-8"))
        except Exception as exc:
            violations.append({
                "path": "src/gaia_cli/trustMagnitude.py",
                "line": 1,
                "kind": "parse-error",
                "detail": f"failed to parse AST: {exc}",
                "error": f"failed to parse AST: {exc}",
            })
            return

        type_weights_keys: set[str] = set()
        for node in tree.body:
            if isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == "TYPE_WEIGHTS":
                        if isinstance(node.value, ast.Dict):
                            for k in node.value.keys:
                                if isinstance(k, ast.Constant) and isinstance(k.value, str):
                                    type_weights_keys.add(k.value)

        if canonical_types and type_weights_keys:
            missing = sorted(canonical_types - type_weights_keys)
            extra = sorted(type_weights_keys - canonical_types)
            if missing or extra:
                violations.append({
                    "path": "src/gaia_cli/trustMagnitude.py",
                    "line": 1,
                    "kind": "evidence-type-mismatch",
                    "detail": (
                        f"TYPE_WEIGHTS keys diverge from meta.json "
                        f"(missing: {missing}, extra: {extra})"
                    ),
                    "error": (
                        f"TYPE_WEIGHTS keys diverge from meta.json "
                        f"(missing: {missing}, extra: {extra})"
                    ),
                })

    def _scan_scripts_and_src(
        self, repo_root: Path, canonical_types: set[str], violations: list[dict[str, Any]]
    ) -> int:
        scanned_files_count = 0
        for directory_name in ("scripts", "src"):
            directory = repo_root / directory_name
            if not directory.is_dir():
                continue
            for path in sorted(directory.rglob("*.py")):
                relative = path.relative_to(repo_root).as_posix()
                if relative in self._EXCLUDED_RELATIVE_PATHS or "/__pycache__/" in f"/{relative}":
                    continue
                scanned_files_count += 1
                try:
                    text = path.read_text(encoding="utf-8", errors="replace")
                except OSError as exc:
                    violations.append({
                        "path": relative,
                        "line": 1,
                        "kind": "read-error",
                        "detail": f"cannot read file: {exc}",
                        "error": f"cannot read file: {exc}",
                    })
                    continue

                for lineno, line in enumerate(text.splitlines(), start=1):
                    stripped = line.strip()
                    if stripped.startswith("#"):
                        continue
                    if self._DEAD_TYPE_COMPARE.search(line):
                        violations.append({
                            "path": relative,
                            "line": lineno,
                            "kind": "type-branch",
                            "detail": f"read-time branch derivation from `type`: {stripped[:120]}",
                            "error": f"read-time branch derivation from `type`: {stripped[:120]}",
                        })
                    if self._DELETED_SHIM_CALL.search(line):
                        violations.append({
                            "path": relative,
                            "line": lineno,
                            "kind": "deleted-shim",
                            "detail": f"call to deleted resolver shim: {stripped[:120]}",
                            "error": f"call to deleted resolver shim: {stripped[:120]}",
                        })
                    if self._BANNED_RANK_VOCABULARY.search(line):
                        violations.append({
                            "path": relative,
                            "line": lineno,
                            "kind": "banned-vocabulary",
                            "detail": f"banned rank vocabulary in script: {stripped[:120]}",
                            "error": f"banned rank vocabulary in script: {stripped[:120]}",
                        })

                if canonical_types:
                    try:
                        tree = ast.parse(text)
                        for node in ast.walk(tree):
                            if isinstance(node, ast.Assign):
                                for target in node.targets:
                                    if (
                                        isinstance(target, ast.Name)
                                        and target.id.endswith("EVIDENCE_TYPES")
                                        and not target.id.startswith("_")
                                    ):
                                        if isinstance(node.value, (ast.List, ast.Tuple, ast.Set)):
                                            for elt in node.value.elts:
                                                if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                                                    if elt.value not in canonical_types:
                                                        violations.append({
                                                            "path": relative,
                                                            "line": getattr(elt, "lineno", 1),
                                                            "kind": "unknown-evidence-type",
                                                            "detail": f"unknown evidence type '{elt.value}' in {target.id}",
                                                            "error": f"unknown evidence type '{elt.value}' in {target.id}",
                                                        })
                    except Exception:
                        pass
        return scanned_files_count


class UpstreamWatcherSensor:
    """Validate upstream tracking configurations and detect un-synced upstream releases or drift."""

    id = "upstream-watcher"
    _NAMED_ROOT = "registry/named"
    _WATCHER_ROOT = ".gaia/upstream-watcher"
    _MAX_PACKET_BYTES = 2 * 1024 * 1024
    _REPO_PATTERN = re.compile(r"^[a-zA-Z0-9][a-zA-Z0-9-]*/[a-zA-Z0-9._-]+$")
    _URL_PATTERN = re.compile(r"^https?://[^\s]+$")
    _GH_URL_PATTERN = re.compile(
        r"^https?://(?:www\.)?github\.com/([a-zA-Z0-9_.-]+)/([a-zA-Z0-9_.-]+)"
        r"(?:/(?:blob|tree|stargazers|commits?|releases?)(?:/[^\s#?]*)?)?"
    )
    _STAR_RE = re.compile(r"(\d+)[★\*]")

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        violations: list[dict[str, str]] = []
        drift_items: list[dict[str, object]] = []
        tracked_skills: list[str] = []
        manifest: dict[str, str] = {}

        named_dir = repo_root / self._NAMED_ROOT
        if named_dir.is_dir():
            for path in sorted(named_dir.rglob("*.md")):
                relative = path.relative_to(repo_root).as_posix()
                raw_bytes = path.read_bytes()
                manifest[relative] = hashlib.sha256(raw_bytes).hexdigest()
                try:
                    raw = self._read_named_markdown(path, repo_root)
                except ValueError as exc:
                    violations.append({"path": relative, "error": str(exc)})
                    continue
                skill_id = raw.get("id")
                if not isinstance(skill_id, str) or not skill_id.strip():
                    violations.append({"path": relative, "error": "missing or invalid skill id"})
                    continue
                self._check_named_skill(raw, relative, skill_id, violations, tracked_skills)

            for path in sorted(named_dir.rglob("*.json")):
                relative = path.relative_to(repo_root).as_posix()
                raw_bytes = path.read_bytes()
                manifest[relative] = hashlib.sha256(raw_bytes).hexdigest()
                try:
                    raw, _ = self._read_object(path, repo_root, "named skill")
                except ValueError as exc:
                    violations.append({"path": relative, "error": str(exc)})
                    continue
                if isinstance(raw, dict):
                    skill_id = raw.get("id")
                    if isinstance(skill_id, str) and skill_id.strip():
                        self._check_named_skill(raw, relative, skill_id, violations, tracked_skills)

        watcher_dir = repo_root / self._WATCHER_ROOT
        if watcher_dir.is_dir():
            for path in sorted(watcher_dir.rglob("*.json")):
                relative = path.relative_to(repo_root).as_posix()
                raw_bytes = path.read_bytes()
                manifest[relative] = hashlib.sha256(raw_bytes).hexdigest()
                try:
                    data, _ = self._read_object(path, repo_root, "upstream watcher manifest")
                except ValueError as exc:
                    violations.append({"path": relative, "error": str(exc)})
                    continue
                self._check_watcher_manifest(data, relative, drift_items, violations)

        violations.sort(key=lambda item: (item["path"], item["error"]))
        drift_items.sort(key=lambda item: (str(item.get("skillId", "")), str(item.get("source", "")), str(item.get("findingType", ""))))
        tracked_skills.sort()

        digest = hashlib.sha256(stable_json(manifest).encode("utf-8")).hexdigest()
        is_healthy = not violations and not drift_items

        observed_state: dict[str, object] = {
            "consistent": is_healthy,
            "trackedCount": len(tracked_skills),
            "trackedSkills": tracked_skills,
            "violationCount": len(violations),
            "driftCount": len(drift_items),
            "violations": violations,
            "drift": drift_items,
            "digest": digest,
        }

        return [
            Observation(
                kind="upstream_drift",
                subject=Subject(type="repository-surface", id="upstream-watcher"),
                observed_at=observed_at,
                source=self.id,
                status="healthy" if is_healthy else "drift",
                current_state={
                    "consistent": True,
                    "trackedSkills": len(tracked_skills),
                },
                observed_state=observed_state,
                confidence=1.0,
                provenance={
                    "namedPath": self._NAMED_ROOT,
                    "watcherPath": self._WATCHER_ROOT,
                },
            )
        ]

    def _check_named_skill(
        self,
        raw: dict[str, object],
        relative: str,
        skill_id: str,
        violations: list[dict[str, str]],
        tracked_skills: list[str],
    ) -> None:
        links = raw.get("links")
        gh_url: str | None = None
        if isinstance(links, dict):
            gh = links.get("github")
            if gh is not None:
                if not isinstance(gh, str) or not self._URL_PATTERN.match(gh.strip()):
                    violations.append({
                        "path": relative,
                        "error": f"skill {skill_id!r} has invalid links.github URL: {gh!r}",
                    })
                else:
                    gh_url = gh.strip()
            canonical_repo = links.get("canonicalRepo")
            if canonical_repo is not None:
                if not isinstance(canonical_repo, str) or not self._URL_PATTERN.match(canonical_repo.strip()):
                    violations.append({
                        "path": relative,
                        "error": f"skill {skill_id!r} has invalid links.canonicalRepo URL: {canonical_repo!r}",
                    })

        upstream = raw.get("upstream")
        if upstream is None:
            return

        if not isinstance(upstream, dict):
            violations.append({
                "path": relative,
                "error": f"skill {skill_id!r} upstream block must be a mapping",
            })
            return

        tracked_skills.append(skill_id)

        level_str = raw.get("level")
        star_level = self._parse_star_level(level_str if isinstance(level_str, str) else None)
        if star_level < 2:
            violations.append({
                "path": relative,
                "error": f"skill {skill_id!r} has upstream tracking configured but is below required 2★ (level: {level_str!r})",
            })

        repo = upstream.get("repo")
        if not isinstance(repo, str) or not self._REPO_PATTERN.match(repo.strip()):
            violations.append({
                "path": relative,
                "error": f"skill {skill_id!r} upstream.repo must match owner/repo pattern (got {repo!r})",
            })
        else:
            repo_str = repo.strip()
            if gh_url and not (isinstance(links, dict) and links.get("canonicalRepo")):
                gh_parsed = self._parse_owner_repo(gh_url)
                if gh_parsed is not None:
                    gh_owner_repo = f"{gh_parsed[0]}/{gh_parsed[1]}"
                    if gh_owner_repo.lower() != repo_str.lower():
                        violations.append({
                            "path": relative,
                            "error": f"skill {skill_id!r} upstream.repo {repo_str!r} does not match links.github repo {gh_owner_repo!r}",
                        })

        version = upstream.get("version")
        if not isinstance(version, str) or not version.strip():
            violations.append({
                "path": relative,
                "error": f"skill {skill_id!r} upstream.version must be a non-empty string",
            })

        mode = upstream.get("mode")
        if mode is not None and mode not in {"components", "version-only"}:
            violations.append({
                "path": relative,
                "error": f"skill {skill_id!r} upstream.mode must be 'components' or 'version-only' (got {mode!r})",
            })

        source_url = upstream.get("sourceUrl")
        if source_url is not None:
            if not isinstance(source_url, str) or not self._URL_PATTERN.match(source_url.strip()):
                violations.append({
                    "path": relative,
                    "error": f"skill {skill_id!r} upstream.sourceUrl must be a valid URL (got {source_url!r})",
                })

    def _check_watcher_manifest(
        self,
        data: object,
        relative: str,
        drift_items: list[dict[str, object]],
        violations: list[dict[str, str]],
    ) -> None:
        items: list[object]
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            if "findings" in data and isinstance(data["findings"], list):
                items = data["findings"]
            elif "releases" in data and isinstance(data["releases"], list):
                items = data["releases"]
            elif "updates" in data and isinstance(data["updates"], list):
                items = data["updates"]
            elif "skills" in data and isinstance(data["skills"], list):
                items = data["skills"]
            elif "drifts" in data and isinstance(data["drifts"], list):
                items = data["drifts"]
            else:
                items = [data]
        else:
            violations.append({"path": relative, "error": "manifest root must be a JSON object or array"})
            return

        for item in items:
            if not isinstance(item, dict):
                continue
            skill_id = item.get("skillId") or item.get("skill_id") or item.get("id")
            if not isinstance(skill_id, str) or not skill_id.strip():
                continue

            finding_type = item.get("finding_type") or item.get("findingType") or item.get("type") or item.get("status")
            curr_ver = item.get("currentVersion") or item.get("current_version") or item.get("storedVersion") or item.get("previousVersion")
            new_ver = item.get("newVersion") or item.get("new_version") or item.get("latestVersion") or item.get("version")
            drift_kind = item.get("driftKind") or item.get("drift_kind") or finding_type or "update"

            is_drift = (
                finding_type in {"update", "bootstrap", "drift", "update_available", "name_drift", "component_drift", "release_detected", "needs-sync"}
                or (new_ver and curr_ver and new_ver != curr_ver)
                or (new_ver and not curr_ver and finding_type != "up_to_date")
                or bool(item.get("status") in {"drift", "update_available", "unresolved"})
            )

            if is_drift:
                drift_items.append({
                    "skillId": skill_id,
                    "source": relative,
                    "findingType": str(drift_kind),
                    "currentVersion": str(curr_ver) if curr_ver is not None else None,
                    "newVersion": str(new_ver) if new_ver is not None else None,
                    "detail": str(item.get("detail") or item.get("notes") or f"upstream release {new_ver} detected (current: {curr_ver})"),
                })

            if item.get("nameDrift") or item.get("name_drift"):
                drift_items.append({
                    "skillId": skill_id,
                    "source": relative,
                    "findingType": "name_drift",
                    "currentVersion": str(curr_ver) if curr_ver is not None else None,
                    "newVersion": str(new_ver) if new_ver is not None else None,
                    "detail": f"upstream name drift detected for {skill_id}",
                })

            if item.get("addedComponents") or item.get("removedComponents"):
                drift_items.append({
                    "skillId": skill_id,
                    "source": relative,
                    "findingType": "component_drift",
                    "currentVersion": str(curr_ver) if curr_ver is not None else None,
                    "newVersion": str(new_ver) if new_ver is not None else None,
                    "detail": f"upstream component drift detected for {skill_id}",
                })

    @classmethod
    def _parse_star_level(cls, level_str: str | None) -> int:
        if not level_str:
            return 0
        m = cls._STAR_RE.search(str(level_str))
        return int(m.group(1)) if m else 0

    @classmethod
    def _parse_owner_repo(cls, url: str) -> tuple[str, str] | None:
        if not url:
            return None
        m = cls._GH_URL_PATTERN.match(url.strip())
        if not m:
            return None
        owner = m.group(1)
        repo = m.group(2).rstrip("/")
        if repo.endswith(".git"):
            repo = repo[:-4]
        return (owner, repo)

    def _read_named_markdown(self, path: Path, repo_root: Path) -> dict[str, object]:
        content = path.read_bytes()
        if len(content) > self._MAX_PACKET_BYTES:
            raise ValueError(f"named skill exceeds safety limit: {path.relative_to(repo_root)}")
        try:
            text = content.decode("utf-8")
            from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
            _fence, frontmatter, _body = split_frontmatter(text)
            raw = load_yaml_simple(frontmatter)
        except Exception as exc:
            raise ValueError(f"invalid named skill: {path.relative_to(repo_root)}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"named skill frontmatter must be an object: {path.relative_to(repo_root)}")
        return raw

    def _read_object(self, path: Path, repo_root: Path, label: str) -> tuple[dict[str, object] | list[object], bytes]:
        content = path.read_bytes()
        if len(content) > self._MAX_PACKET_BYTES:
            raise ValueError(f"{label} exceeds safety limit: {path.relative_to(repo_root)}")
        try:
            raw = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid {label}: {path.relative_to(repo_root)}") from exc
        if not isinstance(raw, (dict, list)):
            raise ValueError(f"{label} must be an object or array: {path.relative_to(repo_root)}")
        return raw, content


class KnowledgeContradictionSensor:
    """Detect contradictions and policy inconsistencies across governance surfaces."""

    id = "knowledge-contradiction"
    _REGISTERED_DEBT_KINDS = frozenset({
        "bundled_schema_mirror_drift",
        "agent_skill_mirror_drift",
        "registry_integrity_failed",
        "sensor_coverage_unknown",
        "cli_contract_drift",
        "generic_mapping",
        "knowledge_contradiction",
        "taxonomy_script_drift",
        "upstream_drift",
        "evidence_link_drift",
        "generated_projection_drift",
        "benchmark_source_drift",
    })
    _VALID_AUTHORITY_CLASSES = frozenset({"A", "B", "C"})

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        violations: list[dict[str, str]] = []
        violations.extend(self._check_policy(repo_root))
        violations.extend(self._check_schema_and_metadata(repo_root))
        violations.extend(self._check_governance_docs(repo_root))
        violations.extend(self._check_claude_workflow(repo_root))

        violations.sort(key=lambda item: (item["source"], item["rule"], item["detail"]))
        drift = bool(violations)

        return [
            Observation(
                kind="knowledge_contradiction",
                subject=Subject(type="repository-surface", id="governance-policy"),
                observed_at=observed_at,
                source=self.id,
                status="drift" if drift else "healthy",
                current_state={"consistent": True},
                observed_state={
                    "consistent": not drift,
                    "violationCount": len(violations),
                    "violations": violations,
                },
                confidence=1.0,
                provenance={
                    "policyPath": "founder/steward/POLICY.yaml",
                    "metaSchemaPath": "registry/schema/meta.json",
                    "skillSchemaPath": "registry/schema/skill.schema.json",
                    "metaDocPath": "META.md",
                    "claudeDocPath": "CLAUDE.md",
                },
            )
        ]

    def _check_policy(self, repo_root: Path) -> list[dict[str, str]]:
        violations: list[dict[str, str]] = []
        policy_file = repo_root / "founder/steward/POLICY.yaml"
        if not policy_file.is_file():
            return violations

        try:
            policy_text = policy_file.read_text(encoding="utf-8")
            import yaml
            policy_data = yaml.safe_load(policy_text)
        except Exception as exc:
            violations.append({
                "source": "founder/steward/POLICY.yaml",
                "rule": "policy-parse",
                "detail": f"failed to parse POLICY.yaml: {exc}",
            })
            return violations

        if not isinstance(policy_data, dict):
            violations.append({
                "source": "founder/steward/POLICY.yaml",
                "rule": "policy-structure",
                "detail": "POLICY.yaml must be a mapping",
            })
            return violations

        authority_map = policy_data.get("authority")
        priority_map = policy_data.get("priority")

        if not isinstance(authority_map, dict):
            violations.append({
                "source": "founder/steward/POLICY.yaml",
                "rule": "authority-declaration",
                "detail": "POLICY.yaml must define a mapping under 'authority'",
            })
        else:
            for debt_kind, auth_val in sorted(authority_map.items()):
                if debt_kind not in self._REGISTERED_DEBT_KINDS:
                    violations.append({
                        "source": "founder/steward/POLICY.yaml",
                        "rule": "registered-debt-kinds",
                        "detail": f"unknown debt kind {debt_kind!r} declared in authority",
                    })
                if auth_val not in self._VALID_AUTHORITY_CLASSES:
                    violations.append({
                        "source": "founder/steward/POLICY.yaml",
                        "rule": "valid-authority-class",
                        "detail": f"invalid authority class {auth_val!r} for debt kind {debt_kind!r}",
                    })

        if not isinstance(priority_map, dict):
            violations.append({
                "source": "founder/steward/POLICY.yaml",
                "rule": "priority-declaration",
                "detail": "POLICY.yaml must define a mapping under 'priority'",
            })
        elif isinstance(authority_map, dict):
            auth_kinds = set(authority_map)
            prio_kinds = set(priority_map)
            if auth_kinds != prio_kinds:
                missing_in_prio = sorted(auth_kinds - prio_kinds)
                extra_in_prio = sorted(prio_kinds - auth_kinds)
                detail_parts: list[str] = []
                if missing_in_prio:
                    detail_parts.append(f"missing in priority: {missing_in_prio}")
                if extra_in_prio:
                    detail_parts.append(f"extra in priority: {extra_in_prio}")
                violations.append({
                    "source": "founder/steward/POLICY.yaml",
                    "rule": "authority-priority-alignment",
                    "detail": f"debt kinds in priority do not match authority: {', '.join(detail_parts)}",
                })

        repairs = policy_data.get("repairs")
        if isinstance(repairs, dict):
            executors = repairs.get("executors")
            if isinstance(executors, dict) and isinstance(authority_map, dict):
                for exec_id, exec_conf in sorted(executors.items()):
                    if isinstance(exec_conf, dict):
                        d_kind = exec_conf.get("debtKind")
                        e_auth = exec_conf.get("authority")
                        if d_kind in authority_map:
                            if authority_map[d_kind] != "A" or e_auth != "A":
                                violations.append({
                                    "source": "founder/steward/POLICY.yaml",
                                    "rule": "repair-executor-authority",
                                    "detail": f"repair executor {exec_id!r} debtKind {d_kind!r} has authority {e_auth!r} (policy authority {authority_map[d_kind]!r}), expected 'A'",
                                })

        routing = policy_data.get("routing")
        if isinstance(routing, dict):
            dispatch_rules = routing.get("dispatchRules")
            if isinstance(dispatch_rules, dict) and isinstance(authority_map, dict):
                for rule_id, rule_conf in sorted(dispatch_rules.items()):
                    if isinstance(rule_conf, dict):
                        d_kind = rule_conf.get("debtKind")
                        r_auth = rule_conf.get("authority")
                        if d_kind in authority_map:
                            if authority_map[d_kind] != "B" or r_auth != "B":
                                violations.append({
                                    "source": "founder/steward/POLICY.yaml",
                                    "rule": "dispatch-rule-authority",
                                    "detail": f"dispatch rule {rule_id!r} debtKind {d_kind!r} has authority {r_auth!r} (policy authority {authority_map[d_kind]!r}), expected 'B'",
                                })
            founder_rules = routing.get("founderRules")
            if isinstance(founder_rules, dict) and isinstance(authority_map, dict):
                for rule_id, rule_conf in sorted(founder_rules.items()):
                    if isinstance(rule_conf, dict):
                        d_kind = rule_conf.get("debtKind")
                        f_auth = rule_conf.get("authority")
                        if d_kind in authority_map:
                            if authority_map[d_kind] != "C" or f_auth != "C":
                                violations.append({
                                    "source": "founder/steward/POLICY.yaml",
                                    "rule": "founder-rule-authority",
                                    "detail": f"founder rule {rule_id!r} debtKind {d_kind!r} has authority {f_auth!r} (policy authority {authority_map[d_kind]!r}), expected 'C'",
                                })

        return violations

    def _check_schema_and_metadata(self, repo_root: Path) -> list[dict[str, str]]:
        violations: list[dict[str, str]] = []
        meta_json_path = repo_root / "registry/schema/meta.json"
        meta_data: dict[str, object] | None = None
        if meta_json_path.is_file():
            try:
                meta_data = json.loads(meta_json_path.read_text(encoding="utf-8"))
            except Exception as exc:
                violations.append({
                    "source": "registry/schema/meta.json",
                    "rule": "meta-json-parse",
                    "detail": f"failed to parse meta.json: {exc}",
                })

        if isinstance(meta_data, dict):
            levels_section = meta_data.get("levels")
            if isinstance(levels_section, dict):
                levels_order = levels_section.get("order")
                levels_labels = levels_section.get("labels")
                if isinstance(levels_order, list) and isinstance(levels_labels, dict):
                    missing_labels = [lvl for lvl in levels_order if lvl not in levels_labels]
                    if missing_labels:
                        violations.append({
                            "source": "registry/schema/meta.json",
                            "rule": "levels-label-coverage",
                            "detail": f"levels.order contains levels without labels: {missing_labels}",
                        })

            types_section = meta_data.get("types")
            meta_types: list[str] = []
            if isinstance(types_section, dict):
                if isinstance(types_section.get("order"), list):
                    meta_types = [t for t in types_section["order"] if isinstance(t, str)]
                elif isinstance(types_section.get("minPrereqs"), dict):
                    meta_types = [t for t in types_section["minPrereqs"] if isinstance(t, str)]

                min_prereqs = types_section.get("minPrereqs")
                if isinstance(min_prereqs, dict) and meta_types:
                    missing_prereqs = [t for t in meta_types if t not in min_prereqs]
                    if missing_prereqs:
                        violations.append({
                            "source": "registry/schema/meta.json",
                            "rule": "types-min-prereqs-coverage",
                            "detail": f"types contains types missing from minPrereqs: {missing_prereqs}",
                        })

            skill_schema_path = repo_root / "registry/schema/skill.schema.json"
            if skill_schema_path.is_file():
                try:
                    schema_data = json.loads(skill_schema_path.read_text(encoding="utf-8"))
                    schema_type_enum = schema_data.get("properties", {}).get("type", {}).get("enum")
                    if isinstance(schema_type_enum, list) and meta_types:
                        if sorted(schema_type_enum) != sorted(meta_types):
                            violations.append({
                                "source": "registry/schema/skill.schema.json",
                                "rule": "skill-type-enum-alignment",
                                "detail": f"skill.schema.json type enum {schema_type_enum} does not match meta.json types {meta_types}",
                            })
                except Exception as exc:
                    violations.append({
                        "source": "registry/schema/skill.schema.json",
                        "rule": "skill-schema-parse",
                        "detail": f"failed to parse skill.schema.json: {exc}",
                    })

        return violations

    def _check_governance_docs(self, repo_root: Path) -> list[dict[str, str]]:
        violations: list[dict[str, str]] = []
        meta_doc_path = repo_root / "META.md"
        meta_json_path = repo_root / "registry/schema/meta.json"
        if not (meta_doc_path.is_file() and meta_json_path.is_file()):
            return violations

        try:
            meta_data = json.loads(meta_json_path.read_text(encoding="utf-8"))
            meta_text = meta_doc_path.read_text(encoding="utf-8")
        except Exception:
            return violations

        if not isinstance(meta_data, dict):
            return violations

        levels_labels = meta_data.get("levels", {}).get("labels") if isinstance(meta_data.get("levels"), dict) else None
        if isinstance(levels_labels, dict):
            level_matches = re.findall(r"\|\s*\*\*([0-6]★)\*\*\s*\|\s*\*\*([^*|\n]+)\*\*", meta_text)
            for tier, raw_label in level_matches:
                label = raw_label.strip()
                label_first_word = label.split()[0]
                expected = levels_labels.get(tier)
                if expected and expected != label and expected != label_first_word:
                    violations.append({
                        "source": "META.md",
                        "rule": "meta-tier-label-contradiction",
                        "detail": f"META.md defines tier {tier} as {label!r}, contradicting meta.json {expected!r}",
                    })

        types_section = meta_data.get("types")
        meta_types: list[str] = []
        if isinstance(types_section, dict):
            if isinstance(types_section.get("order"), list):
                meta_types = [t for t in types_section["order"] if isinstance(t, str)]
            elif isinstance(types_section.get("minPrereqs"), dict):
                meta_types = [t for t in types_section["minPrereqs"] if isinstance(t, str)]

        if meta_types:
            type_matches = re.findall(r"-\s+\*\*`([a-z0-9_-]+)`\*\*\s+—\s+(\d+|≥\s*\d+)\s+prerequisite", meta_text)
            if type_matches:
                doc_types = [t[0] for t in type_matches]
                if sorted(doc_types) != sorted(meta_types):
                    violations.append({
                        "source": "META.md",
                        "rule": "meta-node-type-contradiction",
                        "detail": f"META.md active node types {doc_types} do not match meta.json types {meta_types}",
                    })

        return violations

    def _check_claude_workflow(self, repo_root: Path) -> list[dict[str, str]]:
        violations: list[dict[str, str]] = []
        claude_doc_path = repo_root / "CLAUDE.md"
        if not claude_doc_path.is_file():
            return violations

        try:
            claude_text = claude_doc_path.read_text(encoding="utf-8")
        except Exception as exc:
            violations.append({
                "source": "CLAUDE.md",
                "rule": "claude-doc-read",
                "detail": f"failed to read CLAUDE.md: {exc}",
            })
            return violations

        if "| **schema/**" in claude_text:
            if "registry/schema/" not in claude_text or "src/gaia_cli/data/registry/schema/" not in claude_text:
                violations.append({
                    "source": "CLAUDE.md",
                    "rule": "claude-schema-scope-contradiction",
                    "detail": "CLAUDE.md schema branch scope must list both registry/schema/ and src/gaia_cli/data/registry/schema/",
                })

        return violations


class EvidenceLinkHealthSensor:
    """Scan named skill evidence arrays for URL formats and link integrity."""

    id = "evidence-link-health"
    _NAMED_ROOT = "registry/named"
    _MAX_FILE_BYTES = 2 * 1024 * 1024
    _LINK_FIELDS = ("source", "url", "harnessUrl", "artifact")

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        named_dir = repo_root / self._NAMED_ROOT
        if not named_dir.is_dir():
            return [
                Observation(
                    kind="evidence_link_drift",
                    subject=Subject(type="repository-surface", id="named-evidence-links"),
                    observed_at=observed_at,
                    source=self.id,
                    status="healthy",
                    current_state={"healthy": True},
                    observed_state={
                        "healthy": True,
                        "scannedFiles": 0,
                        "checkedLinks": 0,
                        "violationCount": 0,
                        "violations": [],
                    },
                    confidence=1.0,
                    provenance={"namedRoot": self._NAMED_ROOT},
                )
            ]

        violations: list[dict[str, str]] = []
        scanned_files = 0
        checked_links = 0

        for path in sorted(named_dir.rglob("*.md")):
            relative = path.relative_to(repo_root).as_posix()
            scanned_files += 1
            content = path.read_bytes()
            if len(content) > self._MAX_FILE_BYTES:
                violations.append({
                    "path": relative,
                    "error": f"named skill exceeds safety limit: {relative}",
                })
                continue
            try:
                text = content.decode("utf-8")
                from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
                _fence, frontmatter, _body = split_frontmatter(text)
                if not _fence:
                    violations.append({
                        "path": relative,
                        "error": "invalid frontmatter: missing frontmatter fence",
                    })
                    continue
                raw = load_yaml_simple(frontmatter)
            except Exception as exc:
                violations.append({
                    "path": relative,
                    "error": f"invalid frontmatter: {exc}",
                })
                continue
            if not isinstance(raw, dict):
                violations.append({
                    "path": relative,
                    "error": "named skill frontmatter must be an object",
                })
                continue

            skill_id = raw.get("id")
            evidence_list = raw.get("evidence")
            if evidence_list is None:
                continue
            if not isinstance(evidence_list, list):
                violations.append({
                    "path": relative,
                    "error": f"named skill {skill_id!r} evidence must be a list",
                })
                continue

            for idx, item in enumerate(evidence_list):
                if not isinstance(item, dict):
                    violations.append({
                        "path": relative,
                        "error": f"named skill {skill_id!r} evidence[{idx}] must be an object",
                    })
                    continue

                for field in self._LINK_FIELDS:
                    val = item.get(field)
                    if val is not None:
                        checked_links += 1
                        error = self._check_link(val, path, repo_root)
                        if error:
                            violations.append({
                                "path": relative,
                                "skillId": str(skill_id or path.stem),
                                "field": f"evidence[{idx}].{field}",
                                "error": error,
                            })

                links_dict = item.get("links")
                if isinstance(links_dict, dict):
                    for link_key, link_val in sorted(links_dict.items()):
                        if link_val is not None:
                            checked_links += 1
                            error = self._check_link(link_val, path, repo_root)
                            if error:
                                violations.append({
                                    "path": relative,
                                    "skillId": str(skill_id or path.stem),
                                    "field": f"evidence[{idx}].links.{link_key}",
                                    "error": error,
                                })

        violations.sort(key=lambda item: (item["path"], item.get("field", ""), item["error"]))
        drift = bool(violations)

        return [
            Observation(
                kind="evidence_link_drift",
                subject=Subject(type="repository-surface", id="named-evidence-links"),
                observed_at=observed_at,
                source=self.id,
                status="drift" if drift else "healthy",
                current_state={"healthy": True},
                observed_state={
                    "healthy": not drift,
                    "scannedFiles": scanned_files,
                    "checkedLinks": checked_links,
                    "violationCount": len(violations),
                    "violations": violations,
                },
                confidence=1.0,
                provenance={"namedRoot": self._NAMED_ROOT},
            )
        ]

    @staticmethod
    def _check_link(target: object, file_path: Path, repo_root: Path) -> str | None:
        if not isinstance(target, str):
            return f"link must be a string (got {type(target).__name__})"
        target_str = target.strip()
        if not target_str:
            return "empty link target"

        if target_str.startswith("http://"):
            return f"insecure protocol scheme 'http://' (https:// required): {target_str}"

        if any(c.isspace() for c in target_str):
            return f"invalid URL syntax (contains whitespace): {target_str}"

        import urllib.parse
        parsed = urllib.parse.urlparse(target_str)
        if parsed.scheme:
            scheme = parsed.scheme.lower()
            if scheme != "https":
                return f"unsupported protocol scheme '{scheme}' (https:// required): {target_str}"
            if not parsed.netloc:
                return f"invalid URL syntax (missing domain/netloc): {target_str}"
            netloc = parsed.netloc.lower()
            if netloc == "github.com" or netloc.endswith(".github.com"):
                path_parts = [p for p in parsed.path.split("/") if p]
                if len(path_parts) >= 4 and path_parts[2] == "tree":
                    last_segment = path_parts[-1]
                    if re.search(r"\.[a-zA-Z0-9_-]+$", last_segment):
                        return f"github.com single file link uses '/tree/' instead of '/blob/': {target_str}"
            return None

        # Relative artifact check
        rel_root = repo_root / target_str.lstrip("/")
        rel_file = file_path.parent / target_str
        if not (rel_root.exists() or rel_file.exists()):
            return f"relative artifact does not exist: {target_str}"
        return None


class GeneratedProjectionsSensor:
    """Verify Class S generated artifacts exist, are non-empty, and match canonical named skills."""

    id = "generated-projections"
    _REQUIRED_PROJECTIONS = (
        "docs/graph/gaia.json",
        "docs/graph/named/index.json",
        "docs/api/v1/health.json",
    )
    _NAMED_ROOT = "registry/named"
    _MAX_FILE_BYTES = 20 * 1024 * 1024

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        violations: list[dict[str, str]] = []
        manifest: dict[str, str] = {}
        missing_artifacts: list[str] = []
        empty_artifacts: list[str] = []
        corrupted_artifacts: list[str] = []
        named_index_data: object = None

        for rel_path in self._REQUIRED_PROJECTIONS:
            file_path = repo_root / rel_path
            if not file_path.is_file():
                missing_artifacts.append(rel_path)
                violations.append({
                    "path": rel_path,
                    "error": "required Class S artifact missing",
                })
                continue

            raw_bytes = file_path.read_bytes()
            if len(raw_bytes) == 0:
                empty_artifacts.append(rel_path)
                violations.append({
                    "path": rel_path,
                    "error": "Class S artifact is empty",
                })
                continue

            manifest[rel_path] = hashlib.sha256(raw_bytes).hexdigest()
            try:
                data = json.loads(raw_bytes)
                if not isinstance(data, (dict, list)):
                    corrupted_artifacts.append(rel_path)
                    violations.append({
                        "path": rel_path,
                        "error": "Class S artifact must be a JSON object or array",
                    })
                    continue
                if rel_path == "docs/graph/named/index.json":
                    named_index_data = data
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                corrupted_artifacts.append(rel_path)
                violations.append({
                    "path": rel_path,
                    "error": f"invalid JSON: {exc}",
                })

        canonical_ids = self._canonical_named_skill_ids(repo_root, violations, manifest)

        if named_index_data is not None:
            indexed_ids = self._extract_indexed_skill_ids(named_index_data)
        else:
            indexed_ids = set()

        missing_from_index = sorted(canonical_ids - indexed_ids)
        extra_in_index = sorted(indexed_ids - canonical_ids)

        for skill_id in missing_from_index:
            violations.append({
                "path": "docs/graph/named/index.json",
                "error": f"canonical named skill {skill_id!r} is missing from projection index",
            })
        for skill_id in extra_in_index:
            violations.append({
                "path": "docs/graph/named/index.json",
                "error": f"projection index contains extra un-canonical skill {skill_id!r}",
            })

        violations.sort(key=lambda item: (item["path"], item["error"]))
        drift = bool(violations)
        digest = hashlib.sha256(stable_json(manifest).encode("utf-8")).hexdigest()

        observed_state: dict[str, object] = {
            "consistent": not drift,
            "canonicalNamedCount": len(canonical_ids),
            "indexedNamedCount": len(indexed_ids),
            "missingArtifacts": missing_artifacts,
            "emptyArtifacts": empty_artifacts,
            "corruptedArtifacts": corrupted_artifacts,
            "missingFromIndex": missing_from_index,
            "extraInIndex": extra_in_index,
            "violationCount": len(violations),
            "digest": digest,
            "violations": violations,
        }

        return [
            Observation(
                kind="generated_projection_drift",
                subject=Subject(type="repository-surface", id="class-s-projections"),
                observed_at=observed_at,
                source=self.id,
                status="drift" if drift else "healthy",
                current_state={"consistent": True},
                observed_state=observed_state,
                confidence=1.0,
                provenance={
                    "gaiaGraphPath": "docs/graph/gaia.json",
                    "namedIndexPath": "docs/graph/named/index.json",
                    "healthApiPath": "docs/api/v1/health.json",
                    "canonicalNamedPath": self._NAMED_ROOT,
                },
            )
        ]

    def _canonical_named_skill_ids(
        self,
        repo_root: Path,
        violations: list[dict[str, str]],
        manifest: dict[str, str],
    ) -> set[str]:
        canonical_ids: set[str] = set()
        directory = repo_root / self._NAMED_ROOT
        if not directory.is_dir():
            return canonical_ids

        for path in sorted(directory.rglob("*.md")):
            relative = path.relative_to(repo_root).as_posix()
            raw_bytes = path.read_bytes()
            manifest[relative] = hashlib.sha256(raw_bytes).hexdigest()
            try:
                raw = self._read_named_markdown(path, repo_root)
            except ValueError as exc:
                violations.append({"path": relative, "error": str(exc)})
                continue
            skill_id = raw.get("id")
            if isinstance(skill_id, str) and skill_id.strip():
                canonical_ids.add(skill_id.strip())
            else:
                violations.append(
                    {"path": relative, "error": "missing or invalid skill id in frontmatter"}
                )
        return canonical_ids

    def _extract_indexed_skill_ids(self, data: object) -> set[str]:
        indexed: set[str] = set()
        if isinstance(data, dict):
            buckets = data.get("buckets")
            if isinstance(buckets, dict):
                for items in buckets.values():
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
                                indexed.add(item["id"].strip())
                            elif isinstance(item, str) and item.strip():
                                indexed.add(item.strip())

            awaiting = data.get("awaitingClassification")
            if isinstance(awaiting, list):
                for item in awaiting:
                    if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
                        indexed.add(item["id"].strip())
                    elif isinstance(item, str) and item.strip():
                        indexed.add(item.strip())

            by_contributor = data.get("byContributor")
            if isinstance(by_contributor, dict):
                for items in by_contributor.values():
                    if isinstance(items, list):
                        for item in items:
                            if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
                                indexed.add(item["id"].strip())
                            elif isinstance(item, str) and item.strip():
                                indexed.add(item.strip())

            skills = data.get("skills")
            if isinstance(skills, list):
                for item in skills:
                    if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
                        indexed.add(item["id"].strip())
                    elif isinstance(item, str) and item.strip():
                        indexed.add(item.strip())
        elif isinstance(data, list):
            for item in data:
                if isinstance(item, dict) and isinstance(item.get("id"), str) and item["id"].strip():
                    indexed.add(item["id"].strip())
                elif isinstance(item, str) and item.strip():
                    indexed.add(item.strip())
        return indexed

    def _read_named_markdown(self, path: Path, repo_root: Path) -> dict[str, object]:
        content = path.read_bytes()
        if len(content) > self._MAX_FILE_BYTES:
            raise ValueError(f"named skill exceeds safety limit: {path.relative_to(repo_root)}")
        try:
            text = content.decode("utf-8")
            from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
            _fence, frontmatter, _body = split_frontmatter(text)
            raw = load_yaml_simple(frontmatter)
        except Exception as exc:
            raise ValueError(f"invalid named skill: {path.relative_to(repo_root)}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"named skill frontmatter must be an object: {path.relative_to(repo_root)}")
        return raw


class BenchmarkFreshnessSensor:
    """Validate benchmark source catalog schema and verify benchmark-result evidence rows."""

    id = "benchmark-freshness"
    _CATALOG_PATH = "registry/benchmark-sources.json"
    _SCHEMA_PATH = "registry/schema/benchmarkSourceCatalog.schema.json"
    _NAMED_ROOT = "registry/named"
    _MAX_FILE_BYTES = 20 * 1024 * 1024
    _VERIFIED_LANES = frozenset({"verified", "ci-reproduced", "verifier-attested"})
    _VERIFIED_REQUIRED_FIELDS = ("runAt", "attestor", "datasetHash", "benchmarkInputHash")

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        violations: list[dict[str, str]] = []
        manifest: dict[str, str] = {}
        catalog_benchmarks: dict[str, dict[str, Any]] = {}
        registered_keys: set[str] = set()

        catalog_file = repo_root / self._CATALOG_PATH
        if not catalog_file.is_file():
            violations.append({
                "path": self._CATALOG_PATH,
                "error": f"required catalog file does not exist: {self._CATALOG_PATH}",
            })
        else:
            raw_bytes = catalog_file.read_bytes()
            manifest[self._CATALOG_PATH] = hashlib.sha256(raw_bytes).hexdigest()
            catalog_data: dict[str, Any] | None = None
            try:
                parsed = json.loads(raw_bytes.decode("utf-8"))
                if isinstance(parsed, dict):
                    catalog_data = parsed
                else:
                    violations.append({
                        "path": self._CATALOG_PATH,
                        "error": "catalog root must be a JSON object",
                    })
            except Exception as exc:
                violations.append({
                    "path": self._CATALOG_PATH,
                    "error": f"invalid JSON: {exc}",
                })

            if catalog_data is not None:
                self._validate_catalog(repo_root, catalog_data, violations, catalog_benchmarks, registered_keys)

        named_dir = repo_root / self._NAMED_ROOT
        scanned_rows = 0
        if named_dir.is_dir():
            for path in sorted(named_dir.rglob("*.md")):
                relative = path.relative_to(repo_root).as_posix()
                raw_bytes = path.read_bytes()
                manifest[relative] = hashlib.sha256(raw_bytes).hexdigest()
                try:
                    raw = self._read_named_markdown(path, repo_root)
                except ValueError as exc:
                    violations.append({"path": relative, "error": str(exc)})
                    continue
                skill_id = str(raw.get("id") or path.stem)
                scanned_rows += self._check_named_skill_benchmarks(
                    raw, relative, skill_id, registered_keys, violations
                )

            for path in sorted(named_dir.rglob("*.json")):
                relative = path.relative_to(repo_root).as_posix()
                raw_bytes = path.read_bytes()
                manifest[relative] = hashlib.sha256(raw_bytes).hexdigest()
                try:
                    raw_obj, _ = self._read_object(path, repo_root, "named skill")
                    if isinstance(raw_obj, dict):
                        skill_id = str(raw_obj.get("id") or path.stem)
                        scanned_rows += self._check_named_skill_benchmarks(
                            raw_obj, relative, skill_id, registered_keys, violations
                        )
                except ValueError as exc:
                    violations.append({"path": relative, "error": str(exc)})
                    continue

        violations.sort(key=lambda item: (item["path"], item["error"]))
        drift = bool(violations)
        digest = hashlib.sha256(stable_json(manifest).encode("utf-8")).hexdigest()

        observed_state: dict[str, object] = {
            "consistent": not drift,
            "catalogBenchmarkCount": len(catalog_benchmarks),
            "scannedRowsCount": scanned_rows,
            "violationCount": len(violations),
            "digest": digest,
            "violations": violations,
        }

        return [
            Observation(
                kind="benchmark_source_drift",
                subject=Subject(type="repository-surface", id="benchmark-sources"),
                observed_at=observed_at,
                source=self.id,
                status="drift" if drift else "healthy",
                current_state={"consistent": True},
                observed_state=observed_state,
                confidence=1.0,
                provenance={
                    "catalogPath": self._CATALOG_PATH,
                    "schemaPath": self._SCHEMA_PATH,
                    "namedPath": self._NAMED_ROOT,
                },
            )
        ]

    def _validate_catalog(
        self,
        repo_root: Path,
        catalog_data: dict[str, Any],
        violations: list[dict[str, str]],
        catalog_benchmarks: dict[str, dict[str, Any]],
        registered_keys: set[str],
    ) -> None:
        schema_path = repo_root / self._SCHEMA_PATH
        if not schema_path.is_file():
            schema_path = repo_root / "src/gaia_cli/data/registry/schema/benchmarkSourceCatalog.schema.json"

        if schema_path.is_file():
            try:
                schema = json.loads(schema_path.read_text(encoding="utf-8"))
                Draft7Validator.check_schema(schema)
                validator = Draft7Validator(schema)
                for error in sorted(validator.iter_errors(catalog_data), key=lambda e: list(e.path)):
                    pointer = "/" + "/".join(str(p) for p in error.path)
                    violations.append({
                        "path": self._CATALOG_PATH,
                        "error": f"schema {pointer}: {error.message}",
                    })
            except Exception as exc:
                violations.append({
                    "path": self._CATALOG_PATH,
                    "error": f"schema validation error: {exc}",
                })

        benchmarks = catalog_data.get("benchmarks")
        if not isinstance(benchmarks, list):
            violations.append({
                "path": self._CATALOG_PATH,
                "error": "catalog 'benchmarks' must be an array",
            })
            return

        seen_ids: set[str] = set()
        seen_aliases: dict[str, str] = {}

        for entry in benchmarks:
            if not isinstance(entry, dict):
                violations.append({
                    "path": self._CATALOG_PATH,
                    "error": "benchmark entry must be a JSON object",
                })
                continue

            bench_id = entry.get("id")
            if isinstance(bench_id, str) and bench_id.strip():
                bench_id_clean = bench_id.strip()
                if bench_id_clean in seen_ids:
                    violations.append({
                        "path": self._CATALOG_PATH,
                        "error": f"duplicate benchmarkId in catalog: {bench_id_clean!r}",
                    })
                seen_ids.add(bench_id_clean)
                registered_keys.add(bench_id_clean)
                catalog_benchmarks[bench_id_clean] = entry

                aliases = entry.get("aliases")
                if isinstance(aliases, list):
                    for alias in aliases:
                        if isinstance(alias, str) and alias.strip():
                            alias_clean = alias.strip()
                            if alias_clean in seen_aliases and seen_aliases[alias_clean] != bench_id_clean:
                                violations.append({
                                    "path": self._CATALOG_PATH,
                                    "error": f"duplicate benchmark alias {alias_clean!r} for {seen_aliases[alias_clean]!r} and {bench_id_clean!r}",
                                })
                            seen_aliases[alias_clean] = bench_id_clean
                            registered_keys.add(alias_clean)

                push_block = entry.get("push")
                if isinstance(push_block, dict):
                    push_aliases = push_block.get("aliases")
                    if isinstance(push_aliases, list):
                        for alias in push_aliases:
                            if isinstance(alias, str) and alias.strip():
                                alias_clean = alias.strip()
                                if alias_clean in seen_aliases and seen_aliases[alias_clean] != bench_id_clean:
                                    violations.append({
                                        "path": self._CATALOG_PATH,
                                        "error": f"duplicate benchmark push alias {alias_clean!r} for {seen_aliases[alias_clean]!r} and {bench_id_clean!r}",
                                    })
                                seen_aliases[alias_clean] = bench_id_clean
                                registered_keys.add(alias_clean)

                status = entry.get("status")
                scoring = entry.get("scoring")
                mode = entry.get("mode")

                if isinstance(scoring, dict) and scoring.get("scoresTrustMagnitude"):
                    if status in {"rejected", "retired", "pending", "candidate", "unknown"}:
                        violations.append({
                            "path": self._CATALOG_PATH,
                            "error": f"{bench_id_clean}: status {status!r} must not score Trust Magnitude",
                        })

                if isinstance(push_block, dict) and push_block.get("enabled"):
                    if status != "verified" or mode != "internal-ci":
                        violations.append({
                            "path": self._CATALOG_PATH,
                            "error": f"{bench_id_clean}: push aliases require verified internal-ci status",
                        })

    def _check_named_skill_benchmarks(
        self,
        raw: dict[str, object],
        relative: str,
        skill_id: str,
        registered_keys: set[str],
        violations: list[dict[str, str]],
    ) -> int:
        evidence = raw.get("evidence")
        if not isinstance(evidence, list):
            return 0

        count = 0
        for idx, row in enumerate(evidence):
            if not isinstance(row, dict) or row.get("type") != "benchmark-result":
                continue

            count += 1
            bench_id = row.get("benchmarkId")
            if not isinstance(bench_id, str) or not bench_id.strip():
                violations.append({
                    "path": relative,
                    "error": f"skill {skill_id!r} evidence[{idx}] (type: benchmark-result) missing benchmarkId",
                })
            else:
                clean_bench_id = bench_id.strip()
                if clean_bench_id not in registered_keys:
                    violations.append({
                        "path": relative,
                        "error": f"skill {skill_id!r} evidence[{idx}] references unregistered benchmarkId {clean_bench_id!r}",
                    })

            provenance = row.get("provenance")
            if provenance == "self-attested":
                violations.append({
                    "path": relative,
                    "error": f"skill {skill_id!r} evidence[{idx}] has forbidden provenance 'self-attested'",
                })

            if isinstance(provenance, str) and provenance in self._VERIFIED_LANES:
                for req_field in self._VERIFIED_REQUIRED_FIELDS:
                    val = row.get(req_field)
                    if val is None or val == "":
                        violations.append({
                            "path": relative,
                            "error": f"skill {skill_id!r} evidence[{idx}] verified lane missing required field {req_field!r}",
                        })

            percentile = row.get("percentile")
            if percentile is not None and percentile != "":
                try:
                    pct = float(percentile)
                    if pct < 0 or pct > 100:
                        violations.append({
                            "path": relative,
                            "error": f"skill {skill_id!r} evidence[{idx}] percentile {percentile!r} outside 0..100",
                        })
                except (ValueError, TypeError):
                    violations.append({
                        "path": relative,
                        "error": f"skill {skill_id!r} evidence[{idx}] has non-numeric percentile {percentile!r}",
                    })

        return count

    def _read_named_markdown(self, path: Path, repo_root: Path) -> dict[str, object]:
        content = path.read_bytes()
        if len(content) > self._MAX_FILE_BYTES:
            raise ValueError(f"named skill exceeds safety limit: {path.relative_to(repo_root)}")
        try:
            text = content.decode("utf-8")
            from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
            _fence, frontmatter, _body = split_frontmatter(text)
            raw = load_yaml_simple(frontmatter)
        except Exception as exc:
            raise ValueError(f"invalid named skill: {path.relative_to(repo_root)}") from exc
        if not isinstance(raw, dict):
            raise ValueError(f"named skill frontmatter must be an object: {path.relative_to(repo_root)}")
        return raw

    def _read_object(self, path: Path, repo_root: Path, label: str) -> tuple[dict[str, object] | list[object], bytes]:
        content = path.read_bytes()
        if len(content) > self._MAX_FILE_BYTES:
            raise ValueError(f"{label} exceeds safety limit: {path.relative_to(repo_root)}")
        try:
            raw = json.loads(content)
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise ValueError(f"invalid {label}: {path.relative_to(repo_root)}") from exc
        if not isinstance(raw, (dict, list)):
            raise ValueError(f"{label} must be an object or array: {path.relative_to(repo_root)}")
        return raw, content


def default_sensors() -> tuple[Sensor, ...]:
    return (
        BundledSchemaMirrorSensor(),
        AgentSkillMirrorSensor(),
        RegistryIntegritySensor(),
        CliContractSensor(),
        DiscoveryGenericMappingSensor(),
        TaxonomyScriptDriftSensor(),
        UpstreamWatcherSensor(),
        KnowledgeContradictionSensor(),
        EvidenceLinkHealthSensor(),
        GeneratedProjectionsSensor(),
        BenchmarkFreshnessSensor(),
    )
