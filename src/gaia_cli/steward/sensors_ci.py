"""Deterministic CI, supply-chain, and dependency-advisory sensors.

Every sensor here is read-only and never touches the network. Inventory comes
from Git through ``gaia_cli.steward.primitives``. Two sensors read optional
inputs that a driver collects under the ignored ``.gaia/steward/inputs/``
directory; when those inputs are absent, stale, or about another repository the
sensor raises ``SensorNotEvaluated`` rather than reporting anything healthy.
A present, valid, fresh input makes the sensor exhaustive over its own debt, so
a healthy re-collection resolves what an earlier one found.

Findings never echo a value read from the repository or a driver input: they
carry structure (rule, path, job id) and, where a value must be referred to, its
type, length and a short sha256 fingerprint (``primitives.redact``).
"""

from __future__ import annotations

import json
import re
import tomllib
from pathlib import Path
from typing import Any, Iterator

import yaml

from gaia_cli.steward.models import Observation, SensorScan, Subject
from gaia_cli.steward.primitives import (
    SensorNotEvaluated,
    SensorUnavailable,
    finding_payload,
    git_root,
    read_text_bounded,
    tracked_files,
)
from gaia_cli.steward.primitives.inputs import origin_repository, parse_instant, require_fresh
from gaia_cli.steward.primitives.redact import describe_value, safe_token, scrub

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
_REPOSITORY = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+")
_BRANCH = re.compile(r"[A-Za-z0-9._/@+-]{1,255}")
_COMMIT = re.compile(r"[0-9A-Fa-f]{6,64}")
_RUN_URL = re.compile(r"https?://[^\s@]+")
_VALUE_LIMIT = 160
_MAX_NOT_AUDITED = 50
_VERSION = re.compile(r"v?\d+(?:\.\d+)*(?:[-._]?(?:a|b|rc|alpha|beta|dev|post|pre)\d*)*(?:\+[0-9A-Za-z.]+)?")


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


def _shown(value: str) -> str:
    """A string echoed on purpose (an identifier): bounded and credential-scrubbed."""

    return scrub(value)[:_VALUE_LIMIT]


class CiWorkflowSensor:
    """Hygiene rules for tracked GitHub Actions workflow files."""

    id = "ci-workflow"
    debt_kinds = ("workflow_hygiene",)
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
    jobs = document.get("jobs") if isinstance(document.get("jobs"), dict) else {}
    if "permissions" not in document:
        # A job that declares its own permissions is scoped; only a job that
        # inherits the repository default token with no top-level cap is a gap.
        unscoped = [
            str(job_id)
            for job_id in sorted(jobs, key=str)
            if isinstance(jobs[job_id], dict) and "permissions" not in jobs[job_id]
        ]
        if unscoped:
            findings.append(
                {
                    "rule": "missing-permissions",
                    "detail": (
                        "no top-level permissions key and no job-level permissions on job "
                        + ", ".join(_shown(job_id) for job_id in unscoped)
                    ),
                }
            )
    for job_id in sorted(jobs, key=str):
        job = jobs[job_id]
        if not isinstance(job, dict):
            continue
        # A reusable-workflow call job cannot declare timeout-minutes.
        if "uses" not in job and "timeout-minutes" not in job:
            findings.append(
                {"rule": "missing-timeout", "detail": f"job {_shown(str(job_id))} has no timeout-minutes"}
            )

    for location, value in _walk_key(document, "permissions"):
        if value == "write-all":
            findings.append({"rule": "write-all-permissions", "detail": f"{_shown(location)} grants write-all"})

    for location, value in _walk_key(document, "uses"):
        if not isinstance(value, str) or "@" not in value:
            continue
        if value.rsplit("@", 1)[1].strip() in _BRANCH_REFS:
            findings.append(
                {"rule": "branch-pinned-action", "detail": f"{_shown(location)} uses {_shown(value)}"}
            )

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
                                f"job {_shown(str(job_id))} step {index} checks out the pull request head "
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
    """Latest-run failures and retry churn from a driver-supplied run history.

    Exhaustive whenever the input is present, valid, fresh and about this
    checkout's repository: a healthy re-collection then resolves the workflow
    failures an earlier one reported. An absent, stale or foreign input raises
    ``SensorNotEvaluated`` and the controller sweeps nothing.
    """

    id = "ci-health"
    debt_kinds = ("ci_failure",)
    routine_ids = (13,)
    resolution_scope = "exhaustive"
    driver_inputs = (_CI_RUNS_INPUT.as_posix(),)

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        document = _load_optional_json(root, _CI_RUNS_INPUT)
        if not isinstance(document, dict) or document.get("schemaVersion") != _CI_RUNS_SCHEMA:
            raise SensorUnavailable(f"ci-runs does not declare schema {_CI_RUNS_SCHEMA}")
        repository = _require_str(document, "repository", "ci-runs")
        branch = _require_str(document, "branch", "ci-runs")
        if not _REPOSITORY.fullmatch(repository):
            raise SensorUnavailable(f"ci-runs repository is not owner/name {describe_value(repository)}")
        if not _BRANCH.fullmatch(branch):
            raise SensorUnavailable(f"ci-runs branch is not a plain ref name {describe_value(branch)}")
        runs = _validate_runs(document.get("runs"))
        freshness = require_fresh(document, root / _CI_RUNS_INPUT, observed_at, label="ci-runs")

        origin = origin_repository(root)
        if origin is not None and origin.casefold() != repository.casefold():
            raise SensorNotEvaluated("ci-runs is about another repository than this checkout's origin")
        repository_check = "origin-match" if origin is not None else "origin-unknown"

        by_workflow: dict[str, list[dict[str, Any]]] = {}
        for run in runs:
            by_workflow.setdefault(run["group"], []).append(run)

        observations: list[Observation] = []
        for group_key in sorted(by_workflow):
            group = by_workflow[group_key]
            latest = max(
                group,
                key=lambda run: (parse_instant(run["createdAt"], "ci-runs"), run["runAttempt"]),
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
            observed_state.update(
                {"workflow": _shown(latest["workflow"]), "retryChurn": churn, "runCount": len(group)}
            )
            observations.append(
                Observation(
                    kind="ci_failure",
                    subject=Subject(type="workflow-run", id=_shown(group_key)),
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
                        "repositoryCheck": repository_check,
                        "branch": branch,
                        **freshness,
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
        parse_instant(entry["createdAt"], where)
        if not _COMMIT.fullmatch(entry["headSha"]):
            raise SensorUnavailable(f"{where} headSha is not a commit id {describe_value(entry['headSha'])}")
        if not _RUN_URL.fullmatch(entry["url"]):
            raise SensorUnavailable(f"{where} url is not a plain http(s) URL {describe_value(entry['url'])}")
        entry["runAttempt"] = attempt
        entry["group"] = _workflow_group(run, entry["workflow"], where)
        validated.append(entry)
    return validated


def _workflow_group(run: dict[str, Any], name: str, where: str) -> str:
    """Group key: the workflow's path or id when the driver supplied one, else its name.

    Two workflows may share a display name; a path or numeric id does not.
    """

    path = run.get("workflowPath")
    if path is not None:
        if not isinstance(path, str) or not path.strip():
            raise SensorUnavailable(f"{where} workflowPath must be a non-empty string")
        return path
    identifier = run.get("workflowId")
    if identifier is not None:
        if isinstance(identifier, bool) or not isinstance(identifier, (int, str)) or identifier == "":
            raise SensorUnavailable(f"{where} workflowId must be an integer or non-empty string")
        return f"id:{identifier}"
    return name


class SupplyChainSensor:
    """Version lockstep, unpinned dependencies, and license metadata drift."""

    id = "supply-chain"
    debt_kinds = ("version_lockstep_drift", "dependency_pin_drift", "license_metadata_drift")
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
                                        f"pyproject.toml={safe_token(pyproject_version, _VERSION)} "
                                        f"{_NPM_MANIFEST}={safe_token(npm_version, _VERSION)}"
                                    ),
                                }
                            ]
                        ),
                        "versions": {"pyproject": safe_token(pyproject_version, _VERSION), "cliNPM": safe_token(npm_version, _VERSION)},
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
        findings: list[dict[str, str]] = []
        dynamic = SupplyChainSensor._dynamic_fields(project)
        groups: list[tuple[str, Any]] = []
        for field in ("dependencies", "optional-dependencies"):
            if field in dynamic:
                # A set the sensor cannot see is not a healthy set.
                findings.append(
                    {
                        "rule": "dynamic-dependencies",
                        "detail": f"[project].{field} is declared dynamic; pins cannot be checked statically",
                        "group": field,
                        "requirement": "",
                    }
                )
        if "dependencies" not in dynamic:
            groups.append(("dependencies", project.get("dependencies", [])))
        optional = project.get("optional-dependencies", {}) if "optional-dependencies" not in dynamic else {}
        if not isinstance(optional, dict):
            raise SensorUnavailable("[project].optional-dependencies must be a table")
        groups.extend((f"optional-dependencies.{name}", optional[name]) for name in sorted(optional))
        for group, requirements in groups:
            if not isinstance(requirements, list) or not all(isinstance(item, str) for item in requirements):
                raise SensorUnavailable(f"[project].{group} must be a list of strings")
            for requirement in requirements:
                if _is_unpinned(requirement):
                    findings.append(
                        {
                            "rule": "unpinned-dependency",
                            "detail": (
                                f"{group} declares {_shown(requirement.strip())!r} with no version specifier"
                            ),
                            "group": group,
                            "requirement": _shown(requirement.strip()),
                        }
                    )
        return sorted(findings, key=lambda item: (item["group"], item["requirement"]))

    @staticmethod
    def _dynamic_fields(project: dict[str, Any]) -> frozenset[str]:
        dynamic = project.get("dynamic", [])
        if not isinstance(dynamic, list) or not all(isinstance(item, str) for item in dynamic):
            raise SensorUnavailable("[project].dynamic must be a list of strings")
        return frozenset(dynamic)

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

        if "license" in SupplyChainSensor._dynamic_fields(project):
            findings.append(
                {
                    "rule": "license-dynamic",
                    "detail": "[project].license is declared dynamic; the license cannot be checked statically",
                }
            )
            declared = True  # unknown is reported above, not also called "undeclared"

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
                        f"pyproject declares {_shown(pyproject_license)} but {_NPM_MANIFEST} "
                        f"declares {_shown(npm_license.strip())}"
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
    """Known vulnerabilities from a driver-supplied ``pip-audit --format json`` run.

    Exhaustive whenever the input is present, valid and fresh. pip-audit carries
    no timestamp, so the file's modification time is the freshness clock unless
    the driver added ``collectedAt``. Dependencies pip-audit skipped (``name``
    plus ``skip_reason``) were not audited: they are recorded in provenance and
    never counted as clean or as findings. A skipped third-party package is a
    reported skip, so the run never sweeps advisory debt as resolved while some
    dependency went unaudited; only the checkout's own project (pip-audit always
    skips the editable install) is exempt.
    """

    id = "dependency-advisory"
    debt_kinds = ("dependency_advisory",)
    routine_ids = (14,)
    resolution_scope = "exhaustive"
    driver_inputs = (_ADVISORIES_INPUT.as_posix(),)

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return list(self.scan_detailed(repo_root, observed_at).observations)

    def scan_detailed(self, repo_root: Path, observed_at: str) -> SensorScan:
        root = git_root(repo_root)
        document = _load_optional_json(root, _ADVISORIES_INPUT)
        dependencies, not_audited = _validate_advisories(document)
        freshness = require_fresh(document, root / _ADVISORIES_INPUT, observed_at, label="advisories")
        own = _own_project_names(root)
        skipped = tuple(
            {"subjectType": "python-package", "subjectId": entry["name"], "reason": "not audited by pip-audit"}
            for entry in not_audited
            if _normalize_package(entry["name"]) not in own
        )

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
                    provenance={
                        "input": _ADVISORIES_INPUT.as_posix(),
                        "tool": "pip-audit",
                        "dependenciesAudited": len(dependencies),
                        "notAudited": not_audited[:_MAX_NOT_AUDITED],
                        "notAuditedCount": len(not_audited),
                        **freshness,
                    },
                )
            )
        return SensorScan(observations, skipped)


def _normalize_package(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _own_project_names(root: Path) -> set[str]:
    """The checkout's own distribution name(s), which pip-audit never resolves."""

    try:
        project = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8")).get("project")
    except (OSError, UnicodeDecodeError, tomllib.TOMLDecodeError):
        return set()
    name = project.get("name") if isinstance(project, dict) else None
    return {_normalize_package(name)} if isinstance(name, str) and name else set()


def _validate_advisories(document: Any) -> tuple[list[dict[str, Any]], list[dict[str, str]]]:
    """Return (audited dependencies, not-audited entries) from pip-audit JSON."""

    if not isinstance(document, dict):
        raise SensorUnavailable("advisories must be a JSON object")
    dependencies = document.get("dependencies")
    if not isinstance(dependencies, list):
        raise SensorUnavailable("advisories requires a dependencies list")
    fixes = document.get("fixes", [])
    if not isinstance(fixes, list):
        raise SensorUnavailable("advisories fixes must be a list when present")
    validated: list[dict[str, Any]] = []
    not_audited: list[dict[str, str]] = []
    for index, dependency in enumerate(dependencies):
        where = f"advisories dependency {index}"
        if not isinstance(dependency, dict):
            raise SensorUnavailable(f"{where} is not an object")
        name = _shown(_require_str(dependency, "name", where))
        if "version" not in dependency and "skip_reason" in dependency:
            # pip-audit could not resolve this package (local, editable, not on
            # the index). It was not audited: say so, never call it clean.
            reason = dependency["skip_reason"]
            if not isinstance(reason, str):
                raise SensorUnavailable(f"{where} skip_reason must be a string")
            not_audited.append({"name": name, "reason": _shown(reason)})
            continue
        version = _shown(_require_str(dependency, "version", where))
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
                {
                    "id": _shown(_require_str(vuln, "id", vuln_where)),
                    "fix_versions": sorted(_shown(item) for item in fix_versions),
                }
            )
        validated.append({"name": name, "version": version, "vulns": parsed_vulns})
    not_audited.sort(key=lambda item: (item["name"], item["reason"]))
    return validated, not_audited
