"""Deterministic CI, supply-chain, and dependency-advisory sensors.

Every sensor here is read-only and never touches the network. Inventory comes
from Git through ``gaia_cli.steward.primitives``. Two sensors read optional
inputs that a driver collects under the ignored ``.gaia/steward/inputs/``
directory; when those inputs are absent the sensor raises
``SensorNotEvaluated`` rather than reporting anything healthy.
"""

from __future__ import annotations

import json
import re
import tomllib
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterator

import yaml

from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.primitives import (
    SensorNotEvaluated,
    SensorUnavailable,
    finding_payload,
    git_root,
    read_text_bounded,
    tracked_files,
)

_CI_RUNS_INPUT = Path(".gaia/steward/inputs/ci-runs.json")
_CI_RUNS_SCHEMA = "steward-ci-runs-v1"
_ADVISORIES_INPUT = Path(".gaia/steward/inputs/advisories.json")
_MAX_CI_RUNS = 5000
_FAILING_CONCLUSIONS = frozenset({"failure", "timed_out", "startup_failure"})
_BRANCH_REFS = frozenset({"main", "master"})
_CHECKOUT_ACTION = "actions/checkout"
_HEAD_REF_MARKER = "github.event.pull_request.head"

_PYPROJECT = "pyproject.toml"
_NPM_MANIFEST = "packages/cli-npm/package.json"
_LICENSE_FILES = ("LICENSE", "LICENSE.md", "LICENSE.txt")
_SPDX_IDENTIFIER = re.compile(r"^[A-Za-z0-9.+-]+$")
_REQUIREMENT_NAME = re.compile(r"^\s*([A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)")


def _load_optional_json(root: Path, relative: Path) -> Any:
    """Return a driver-supplied JSON input, or raise the honest sensor state."""

    path = root / relative
    if not path.exists() and not path.is_symlink():
        raise SensorNotEvaluated(f"no {relative.name} supplied; a driver must collect it")
    if not path.is_file():
        raise SensorUnavailable(f"{relative.as_posix()} is not a regular file")
    text = read_text_bounded(path)
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SensorUnavailable(f"{relative.as_posix()} is not valid JSON: {exc.msg}") from exc


def _require_str(mapping: Any, key: str, where: str) -> str:
    value = mapping.get(key) if isinstance(mapping, dict) else None
    if not isinstance(value, str) or not value.strip():
        raise SensorUnavailable(f"{where} requires a non-empty string {key!r}")
    return value


def _parse_timestamp(value: str, where: str) -> datetime:
    text = value[:-1] + "+00:00" if value.endswith("Z") else value
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError as exc:
        raise SensorUnavailable(f"{where} has an unparseable timestamp: {value!r}") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


class CiWorkflowSensor:
    """Hygiene rules for tracked GitHub Actions workflow files."""

    id = "ci-workflow"
    routine_ids = (13,)
    resolution_scope = "exhaustive"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        # Only direct children run on GitHub. Nested trees such as
        # .github/workflows/_disabled/ are tracked but inert, so they are out of scope.
        workflows = [
            path
            for path in tracked_files(root, [".github/workflows"], suffixes=(".yml", ".yaml"))
            if path.count("/") == 2
        ]
        observations: list[Observation] = []
        for relative in workflows:
            findings = _workflow_findings(root / relative)
            if not findings:
                continue
            observations.append(
                Observation(
                    kind="workflow_hygiene",
                    subject=Subject(type="workflow", id=relative),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"findingCount": 0},
                    observed_state=finding_payload(findings),
                    confidence=1.0,
                    provenance={"inventory": "git ls-files .github/workflows"},
                )
            )
        return observations


def _workflow_findings(path: Path) -> list[dict[str, str]]:
    try:
        text = read_text_bounded(path)
    except SensorUnavailable as exc:
        # One unreadable workflow is a finding about that subject, not a
        # whole-sensor failure.
        return [{"rule": "unparseable-workflow", "detail": f"unreadable: {exc}"}]
    try:
        document = yaml.safe_load(text)
    except yaml.YAMLError as exc:
        line = getattr(getattr(exc, "problem_mark", None), "line", None)
        where = f" at line {line + 1}" if line is not None else ""
        return [{"rule": "unparseable-workflow", "detail": f"YAML parse error{where}"}]
    if not isinstance(document, dict):
        return [{"rule": "unparseable-workflow", "detail": "workflow is not a mapping"}]

    findings: list[dict[str, str]] = []
    if "permissions" not in document:
        findings.append({"rule": "missing-permissions", "detail": "no top-level permissions key"})

    jobs = document.get("jobs") if isinstance(document.get("jobs"), dict) else {}
    for job_id in sorted(jobs, key=str):
        job = jobs[job_id]
        if not isinstance(job, dict):
            continue
        # A reusable-workflow call job cannot declare timeout-minutes.
        if "uses" not in job and "timeout-minutes" not in job:
            findings.append(
                {"rule": "missing-timeout", "detail": f"job {job_id} has no timeout-minutes"}
            )

    for location, value in _walk_key(document, "permissions"):
        if value == "write-all":
            findings.append({"rule": "write-all-permissions", "detail": f"{location} grants write-all"})

    for location, value in _walk_key(document, "uses"):
        if not isinstance(value, str) or "@" not in value:
            continue
        if value.rsplit("@", 1)[1].strip() in _BRANCH_REFS:
            findings.append({"rule": "branch-pinned-action", "detail": f"{location} uses {value}"})

    if "pull_request_target" in _triggers(document):
        for job_id in sorted(jobs, key=str):
            job = jobs[job_id]
            steps = job.get("steps") if isinstance(job, dict) else None
            if not isinstance(steps, list):
                continue
            for index, step in enumerate(steps):
                if not isinstance(step, dict):
                    continue
                uses = step.get("uses")
                with_block = step.get("with") if isinstance(step.get("with"), dict) else {}
                ref = with_block.get("ref")
                if (
                    isinstance(uses, str)
                    and uses.startswith(_CHECKOUT_ACTION)
                    and isinstance(ref, str)
                    and _HEAD_REF_MARKER in ref
                ):
                    findings.append(
                        {
                            "rule": "pull-request-target-checkout",
                            "detail": (
                                f"job {job_id} step {index} checks out the pull request head "
                                "under pull_request_target"
                            ),
                        }
                    )

    return sorted(findings, key=lambda item: (item["rule"], item["detail"]))


def _triggers(document: dict[str, Any]) -> set[str]:
    # PyYAML parses the bare key ``on`` as boolean True (YAML 1.1).
    raw = document["on"] if "on" in document else document.get(True)
    if isinstance(raw, str):
        return {raw}
    if isinstance(raw, list):
        return {str(item) for item in raw}
    if isinstance(raw, dict):
        return {str(key) for key in raw}
    return set()


def _walk_key(node: Any, key: str, location: str = "$") -> Iterator[tuple[str, Any]]:
    """Yield (location, value) for every mapping entry named ``key``."""

    if isinstance(node, dict):
        for name, value in node.items():
            here = f"{location}.{name}"
            if name == key:
                yield here, value
            yield from _walk_key(value, key, here)
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from _walk_key(value, key, f"{location}[{index}]")


class CiHealthSensor:
    """Latest-run failures and retry churn from a driver-supplied run history."""

    id = "ci-health"
    routine_ids = (13,)

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        document = _load_optional_json(root, _CI_RUNS_INPUT)
        if not isinstance(document, dict) or document.get("schemaVersion") != _CI_RUNS_SCHEMA:
            raise SensorUnavailable(f"ci-runs does not declare schema {_CI_RUNS_SCHEMA}")
        repository = _require_str(document, "repository", "ci-runs")
        branch = _require_str(document, "branch", "ci-runs")
        collected_at = _require_str(document, "collectedAt", "ci-runs")
        runs = _validate_runs(document.get("runs"))

        by_workflow: dict[str, list[dict[str, Any]]] = {}
        for run in runs:
            by_workflow.setdefault(run["workflow"], []).append(run)

        observations: list[Observation] = []
        for workflow in sorted(by_workflow):
            group = by_workflow[workflow]
            latest = max(
                group,
                key=lambda run: (_parse_timestamp(run["createdAt"], "ci-runs"), run["runAttempt"]),
            )
            if latest["conclusion"] not in _FAILING_CONCLUSIONS:
                continue
            churn = sum(1 for run in group if run["runAttempt"] > 1)
            finding = {
                "rule": "latest-run-failed",
                "detail": f"most recent run concluded {latest['conclusion']}",
                "conclusion": latest["conclusion"],
                "headSha": latest["headSha"],
                "runAttempt": latest["runAttempt"],
                "url": latest["url"],
            }
            observed_state = finding_payload([finding])
            observed_state.update({"workflow": workflow, "retryChurn": churn, "runCount": len(group)})
            observations.append(
                Observation(
                    kind="ci_failure",
                    subject=Subject(type="workflow-run", id=workflow),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"latestConclusion": "success"},
                    observed_state=observed_state,
                    confidence=1.0,
                    provenance={
                        "input": _CI_RUNS_INPUT.as_posix(),
                        "schemaVersion": _CI_RUNS_SCHEMA,
                        "repository": repository,
                        "branch": branch,
                        "collectedAt": collected_at,
                    },
                )
            )
        return observations


def _validate_runs(runs: Any) -> list[dict[str, Any]]:
    if not isinstance(runs, list):
        raise SensorUnavailable("ci-runs requires a list of runs")
    if len(runs) > _MAX_CI_RUNS:
        raise SensorUnavailable(f"ci-runs exceeds the bounded limit of {_MAX_CI_RUNS} runs")
    validated: list[dict[str, Any]] = []
    for index, run in enumerate(runs):
        where = f"ci-runs run {index}"
        if not isinstance(run, dict):
            raise SensorUnavailable(f"{where} is not an object")
        attempt = run.get("runAttempt")
        if isinstance(attempt, bool) or not isinstance(attempt, int) or attempt < 1:
            raise SensorUnavailable(f"{where} requires an integer runAttempt of at least 1")
        entry: dict[str, Any] = {
            key: _require_str(run, key, where)
            for key in ("workflow", "conclusion", "headSha", "createdAt", "url")
        }
        _parse_timestamp(entry["createdAt"], where)
        entry["runAttempt"] = attempt
        validated.append(entry)
    return validated


class SupplyChainSensor:
    """Version lockstep, unpinned dependencies, and license metadata drift."""

    id = "supply-chain"
    routine_ids = (14,)
    resolution_scope = "exhaustive"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        tracked = set(
            tracked_files(root, [_PYPROJECT, _NPM_MANIFEST, *_LICENSE_FILES], require_any=False)
        )
        for required in (_PYPROJECT, _NPM_MANIFEST):
            if required not in tracked:
                raise SensorUnavailable(f"required manifest is not tracked: {required}")

        project = self._pyproject_project(root)
        npm = self._npm_manifest(root)
        pyproject_version = project.get("version")
        if not isinstance(pyproject_version, str) or not pyproject_version:
            raise SensorUnavailable("pyproject.toml declares no static [project].version")
        npm_version = npm.get("version")
        if not isinstance(npm_version, str) or not npm_version:
            raise SensorUnavailable(f"{_NPM_MANIFEST} declares no version")

        observations: list[Observation] = []

        # Same comparison as gaia_cli.versioning.verify_lockstep, restricted to
        # the two tracked manifests; registry/gaia.json is gitignored Class P.
        if pyproject_version != npm_version:
            observations.append(
                Observation(
                    kind="version_lockstep_drift",
                    subject=Subject(type="manifest-versions", id="manifest-versions"),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"versions": "in-lockstep"},
                    observed_state={
                        **finding_payload(
                            [
                                {
                                    "rule": "version-mismatch",
                                    "detail": (
                                        f"pyproject.toml={pyproject_version} "
                                        f"{_NPM_MANIFEST}={npm_version}"
                                    ),
                                }
                            ]
                        ),
                        "versions": {"pyproject": pyproject_version, "cliNPM": npm_version},
                    },
                    confidence=1.0,
                    provenance={
                        "comparison": "gaia_cli.versioning.verify_lockstep (tracked manifests)",
                        "manifests": [_PYPROJECT, _NPM_MANIFEST],
                    },
                )
            )

        pin_findings = self._unpinned_findings(project)
        if pin_findings:
            observations.append(
                Observation(
                    kind="dependency_pin_drift",
                    subject=Subject(type="python-dependencies", id="python-dependencies"),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"unpinnedDependencies": 0},
                    observed_state=finding_payload(pin_findings),
                    confidence=0.8,
                    provenance={
                        "heuristic": "a requirement with no version operator and no direct URL",
                        "manifest": _PYPROJECT,
                    },
                )
            )

        license_findings = self._license_findings(project, npm, tracked)
        if license_findings:
            observations.append(
                Observation(
                    kind="license_metadata_drift",
                    subject=Subject(type="license-metadata", id="license-metadata"),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"licenseMetadata": "consistent"},
                    observed_state=finding_payload(license_findings),
                    confidence=0.9,
                    provenance={"manifests": [_PYPROJECT, _NPM_MANIFEST]},
                )
            )
        return observations

    @staticmethod
    def _pyproject_project(root: Path) -> dict[str, Any]:
        text = read_text_bounded(root / _PYPROJECT)
        try:
            data = tomllib.loads(text)
        except tomllib.TOMLDecodeError as exc:
            raise SensorUnavailable(f"pyproject.toml is not valid TOML: {exc}") from exc
        project = data.get("project")
        if not isinstance(project, dict):
            raise SensorUnavailable("pyproject.toml has no [project] table")
        return project

    @staticmethod
    def _npm_manifest(root: Path) -> dict[str, Any]:
        try:
            data = json.loads(read_text_bounded(root / _NPM_MANIFEST))
        except json.JSONDecodeError as exc:
            raise SensorUnavailable(f"{_NPM_MANIFEST} is not valid JSON: {exc.msg}") from exc
        if not isinstance(data, dict):
            raise SensorUnavailable(f"{_NPM_MANIFEST} is not a JSON object")
        return data

    @staticmethod
    def _unpinned_findings(project: dict[str, Any]) -> list[dict[str, str]]:
        groups: list[tuple[str, Any]] = [("dependencies", project.get("dependencies", []))]
        optional = project.get("optional-dependencies", {})
        if not isinstance(optional, dict):
            raise SensorUnavailable("[project].optional-dependencies must be a table")
        groups.extend((f"optional-dependencies.{name}", optional[name]) for name in sorted(optional))
        findings: list[dict[str, str]] = []
        for group, requirements in groups:
            if not isinstance(requirements, list) or not all(isinstance(item, str) for item in requirements):
                raise SensorUnavailable(f"[project].{group} must be a list of strings")
            for requirement in requirements:
                if _is_unpinned(requirement):
                    findings.append(
                        {
                            "rule": "unpinned-dependency",
                            "detail": f"{group} declares {requirement.strip()!r} with no version specifier",
                            "group": group,
                            "requirement": requirement.strip(),
                        }
                    )
        return sorted(findings, key=lambda item: (item["group"], item["requirement"]))

    @staticmethod
    def _license_findings(
        project: dict[str, Any], npm: dict[str, Any], tracked: set[str]
    ) -> list[dict[str, str]]:
        findings: list[dict[str, str]] = []
        declared = False
        pyproject_license: str | None = None
        license_value = project.get("license")
        if isinstance(license_value, str) and license_value.strip():
            declared = True
            pyproject_license = license_value.strip()
        elif isinstance(license_value, dict) and (license_value.get("text") or license_value.get("file")):
            declared = True
            text = license_value.get("text")
            if isinstance(text, str) and text.strip():
                pyproject_license = text.strip()
        classifiers = project.get("classifiers", [])
        if not isinstance(classifiers, list):
            raise SensorUnavailable("[project].classifiers must be a list")
        if any(isinstance(item, str) and item.startswith("License ::") for item in classifiers):
            declared = True

        license_file = next((name for name in _LICENSE_FILES if name in tracked), None)
        if license_file and not declared:
            findings.append(
                {
                    "rule": "license-undeclared",
                    "detail": f"{license_file} is tracked but pyproject declares no license",
                }
            )

        npm_license = npm.get("license")
        if (
            pyproject_license
            and isinstance(npm_license, str)
            and _SPDX_IDENTIFIER.match(pyproject_license)
            and _SPDX_IDENTIFIER.match(npm_license.strip())
            and pyproject_license.casefold() != npm_license.strip().casefold()
        ):
            findings.append(
                {
                    "rule": "license-mismatch",
                    "detail": (
                        f"pyproject declares {pyproject_license} but {_NPM_MANIFEST} "
                        f"declares {npm_license.strip()}"
                    ),
                }
            )
        return sorted(findings, key=lambda item: (item["rule"], item["detail"]))


def _is_unpinned(requirement: str) -> bool:
    body = requirement.split(";", 1)[0].strip()
    match = _REQUIREMENT_NAME.match(body)
    if not match:
        return False
    rest = body[match.end():].strip()
    if rest.startswith("["):
        close = rest.find("]")
        if close == -1:
            return False
        rest = rest[close + 1:].strip()
    if not rest:
        return True
    if rest.startswith("@"):
        return False
    return not any(operator in rest for operator in ("<", ">", "=", "!", "~"))


class DependencyAdvisorySensor:
    """Known vulnerabilities from a driver-supplied ``pip-audit --format json`` run."""

    id = "dependency-advisory"
    routine_ids = (14,)

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        dependencies = _validate_advisories(_load_optional_json(root, _ADVISORIES_INPUT))

        grouped: dict[str, dict[str, Any]] = {}
        for dependency in dependencies:
            if not dependency["vulns"]:
                continue
            entry = grouped.setdefault(dependency["name"], {"versions": set(), "findings": []})
            entry["versions"].add(dependency["version"])
            for vuln in dependency["vulns"]:
                entry["findings"].append(
                    {
                        "rule": "known-vulnerability",
                        "detail": (
                            f"{dependency['name']} {dependency['version']} is affected by {vuln['id']}"
                        ),
                        "vulnerabilityId": vuln["id"],
                        "installedVersion": dependency["version"],
                        "fixVersions": vuln["fix_versions"],
                    }
                )

        observations: list[Observation] = []
        for name in sorted(grouped):
            entry = grouped[name]
            findings = sorted(
                entry["findings"], key=lambda item: (item["vulnerabilityId"], item["installedVersion"])
            )
            observed_state = finding_payload(findings)
            observed_state["installedVersions"] = sorted(entry["versions"])
            observations.append(
                Observation(
                    kind="dependency_advisory",
                    subject=Subject(type="python-package", id=name),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"knownVulnerabilities": 0},
                    observed_state=observed_state,
                    confidence=1.0,
                    provenance={"input": _ADVISORIES_INPUT.as_posix(), "tool": "pip-audit"},
                )
            )
        return observations


def _validate_advisories(document: Any) -> list[dict[str, Any]]:
    if not isinstance(document, dict):
        raise SensorUnavailable("advisories must be a JSON object")
    dependencies = document.get("dependencies")
    if not isinstance(dependencies, list):
        raise SensorUnavailable("advisories requires a dependencies list")
    validated: list[dict[str, Any]] = []
    for index, dependency in enumerate(dependencies):
        where = f"advisories dependency {index}"
        if not isinstance(dependency, dict):
            raise SensorUnavailable(f"{where} is not an object")
        name = _require_str(dependency, "name", where)
        version = _require_str(dependency, "version", where)
        vulns = dependency.get("vulns")
        if not isinstance(vulns, list):
            raise SensorUnavailable(f"{where} requires a vulns list")
        parsed_vulns = []
        for vuln_index, vuln in enumerate(vulns):
            vuln_where = f"{where} vulnerability {vuln_index}"
            if not isinstance(vuln, dict):
                raise SensorUnavailable(f"{vuln_where} is not an object")
            fix_versions = vuln.get("fix_versions", [])
            if not isinstance(fix_versions, list) or not all(isinstance(item, str) for item in fix_versions):
                raise SensorUnavailable(f"{vuln_where} requires fix_versions as a string list")
            parsed_vulns.append(
                {"id": _require_str(vuln, "id", vuln_where), "fix_versions": sorted(fix_versions)}
            )
        validated.append({"name": name, "version": version, "vulns": parsed_vulns})
    return validated
