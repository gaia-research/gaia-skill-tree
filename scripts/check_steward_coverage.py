#!/usr/bin/env python3
"""Validate the static Steward routine capability inventory (never run sensors)."""
from __future__ import annotations

import argparse
import ast
import fnmatch
import functools
import inspect
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path("founder/steward/routine-coverage.json")
ROUTINES = Path("founder/ROUTINES.md")
SCHEMA_VERSION = 2
STATE_VOCABULARY = {
    "registered": "static",
    "executable": "static",
    "actively-observed": "live",
    "partially-covered": "static",
    "unknown-unavailable": "live",
    "eligible-auto-remediation": "static",
    "human-gated": "static",
}
ROUTINE_FIELDS = {"number", "title", "status", "detectorIds", "bindings", "predicate", "remainingGaps", "owners", "tests"}
DETECTOR_FIELDS = {
    "id", "routineIds", "debtKinds", "trigger", "inputs", "sourceOfTruth", "evidence", "freshness",
    "coverageStatus", "authority", "dedupeKey", "resolutionScope", "owningSkill", "dispositionSkills",
    "proof", "failureBehavior",
}
DEDUPE_KEY = "debt:{kind}:{slug(subject.id)}:{sha256(semanticKey)[:16]}"
DISPOSITION_SKILL = {"A": "gaia-steward-land", "B": "gaia-steward-lane", "C": "gaia-steward-desk"}
OBSERVE_SKILL = "gaia-steward-observe"
DRIVER_INPUT_PREFIX = ".gaia/steward/inputs/"
UNAVAILABLE_BEHAVIOR = "sensor_coverage_unknown: run blocked for Class A, existing debt retained"
NOT_EVALUATED_BEHAVIOR = "receipt.notEvaluated: nothing resolved, nothing reported healthy"


def _defines_function(path: Path, name: str) -> bool:
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return False
    return any(isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.name == name for node in ast.walk(tree))


def _literal(node: ast.AST) -> Any:
    try:
        return ast.literal_eval(node)
    except (ValueError, TypeError):
        return None


@functools.lru_cache(maxsize=4)
def _sensor_ownership(root: Path) -> dict[str, set[str]]:
    """Find sensor id -> emitted Observation kind ownership from source AST."""
    files = list((root / "src/gaia_cli/steward").glob("*.py"))
    mirror_specs: dict[str, str] = {}
    mirror_tree = ast.parse((root / "src/gaia_cli/steward/mirrors.py").read_text(encoding="utf-8"))
    for node in ast.walk(mirror_tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "MirrorSpec":
            values = {kw.arg: _literal(kw.value) for kw in node.keywords}
            if values.get("id") and values.get("debt_kind"):
                mirror_specs[values["id"]] = values["debt_kind"]
    ownership: dict[str, set[str]] = {}
    for file in files:
        tree = ast.parse(file.read_text(encoding="utf-8"))
        for cls in (n for n in ast.walk(tree) if isinstance(n, ast.ClassDef)):
            sensor_id = None
            own_kinds: set[str] = set()
            for item in cls.body:
                if isinstance(item, ast.Assign):
                    targets = [t.id for t in item.targets if isinstance(t, ast.Name)]
                    if "id" in targets:
                        sensor_id = _literal(item.value)
                        if isinstance(item.value, ast.Attribute) and isinstance(item.value.value, ast.Name):
                            sensor_id = mirror_specs.get(item.value.value.id)
                    if "debt_kind" in targets and isinstance(_literal(item.value), str):
                        own_kinds.add(_literal(item.value))
            for call in (n for n in ast.walk(cls) if isinstance(n, ast.Call)):
                # Module-level ``_observation(kind, ...)`` helpers build the
                # Observation for the class; the literal kind is at the call.
                if isinstance(call.func, ast.Name) and call.func.id == "_observation":
                    literal = _literal(call.args[0]) if call.args else None
                    for kw in call.keywords:
                        if kw.arg == "kind":
                            literal = _literal(kw.value)
                    if isinstance(literal, str):
                        own_kinds.add(literal)
                    continue
                if isinstance(call.func, ast.Name) and call.func.id == "Observation":
                    for kw in call.keywords:
                        if kw.arg != "kind":
                            continue
                        value = _literal(kw.value)
                        if isinstance(value, str):
                            own_kinds.add(value)
                        elif (isinstance(kw.value, ast.Attribute) and kw.value.attr == "debt_kind"
                              and isinstance(kw.value.value, ast.Name) and kw.value.value.id == "self"):
                            own_kinds.update(own_kinds)
                        elif (isinstance(kw.value, ast.Attribute) and kw.value.attr == "debt_kind"
                              and isinstance(kw.value.value, ast.Name)):
                            kind = mirror_specs.get(kw.value.value.id)
                            if kind:
                                own_kinds.add(kind)
            if isinstance(sensor_id, str):
                ownership.setdefault(sensor_id, set()).update(own_kinds)
    # Mirror sensors inherit their kind from MirrorSpec through the shared helper.
    for sensor_id, kind in mirror_specs.items():
        ownership.setdefault(sensor_id, set()).add(kind)
    return ownership


@functools.lru_cache(maxsize=4)
def _live_policy(root: Path) -> tuple[dict[str, str], dict[str, tuple[str, str]], dict[str, tuple[str, str]], dict[str, Any], dict[str, tuple[str, str]]]:
    sys.path.insert(0, str(root / "src"))
    from gaia_cli.steward.controller import StewardController
    from gaia_cli.steward.policy import StewardPolicy
    policy = StewardPolicy.load(root)
    registered = {sensor.id: sensor for sensor in StewardController().sensors}
    authority = {kind: value.value for kind, value in policy.authority.items()}
    dispatch = {rule.id: (rule.debt_kind, rule.authority.value) for rule in policy.dispatch_rules.values()}
    executors = {key: (executor.debt_kind, executor.authority.value) for key, executor in policy.repair_executors.items()}
    founder_rules = {
        rule_id: (rule.debt_kind, rule.authority.value)
        for rule_id, rule in policy.founder_rules.items()
    }
    return authority, dispatch, executors, registered, founder_rules


def _tracked(root: Path, prefix: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-z", "--", prefix],
            check=False, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, timeout=30,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0 and bool(result.stdout.strip(b"\0"))


def _skill_exists(root: Path, name: str) -> bool:
    return (root / ".agents/skills" / name / "SKILL.md").is_file()


def _check_hooks(root: Path, hooks: Any, errors: list[str]) -> None:
    expected_hooks = {1922, 1445, 2063}
    hook_owners = [h.get("owner") for h in hooks if isinstance(h, dict)] if isinstance(hooks, list) else []
    if (not isinstance(hooks, list) or len(hook_owners) != len(hooks)
            or any(type(owner) is not int for owner in hook_owners)
            or set(hook_owners) != expected_hooks):
        errors.append("hooks must inventory owners 1922, 1445, and 2063")
        return
    for hook in hooks:
        if set(hook) != {"owner", "status", "producerPaths", "producerFunctions", "requiredProof", "reason"}:
            errors.append(f"hook {hook['owner']}: malformed fields")
            continue
        if hook["status"] != "unknown/not-evaluated":
            errors.append(f"hook {hook['owner']}: absent evidence cannot claim healthy or verified")
        paths, functions = hook["producerPaths"], hook["producerFunctions"]
        if not isinstance(paths, list) or not paths or not all(
                isinstance(p, str) and (root / p).is_file() for p in paths):
            errors.append(f"hook {hook['owner']}: producer paths must exist and be strings")
        if not isinstance(functions, list) or not functions or not isinstance(paths, list) or len(functions) != len(paths):
            errors.append(f"hook {hook['owner']}: producer functions must match paths")
        else:
            for path_name, function in zip(paths, functions):
                if (not isinstance(path_name, str) or not isinstance(function, str)
                        or not _defines_function(root / path_name, function)):
                    errors.append(f"hook {hook['owner']}: producer {path_name}::{function} is not defined")
        if hook["requiredProof"] != ["source-revision", "environment", "fresh-independent-verification"]:
            errors.append(f"hook {hook['owner']}: requiredProof must include source, environment, and fresh independent verification")
        if not isinstance(hook["reason"], str) or not hook["reason"].strip():
            errors.append(f"hook {hook['owner']}: reason must be non-empty")


def _test_paths_ok(root: Path, paths: Any) -> bool:
    return isinstance(paths, list) and all(
        isinstance(x, str) and Path(x).as_posix().startswith("tests/") and ".." not in Path(x).parts and (root / x).is_file()
        for x in paths
    )


def _expected_static_states(kinds: list[str], authority: dict[str, str], executors: dict[str, tuple[str, str]]) -> list[str]:
    states = ["registered", "executable"]
    if any(binding[0] == kind for kind in kinds for binding in executors.values()):
        states.append("eligible-auto-remediation")
    if any(authority.get(kind) == "C" for kind in kinds):
        states.append("human-gated")
    return states


# Tests that exercise the controller, the CLI or this catalog serve every routine.
GENERAL_TEST_PATTERNS = (
    "tests/steward/test_controller*.py",
    "tests/steward/test_cli.py",
    "tests/steward/test_routine_coverage.py",
)
# Steward modules whose literals say nothing about a sensor's inputs.
_NEUTRAL_HELPERS = {"models", "primitives", "policy", "receipts", "debt"}


def _string_literals(tree: ast.AST) -> set[str]:
    return {n.value for n in ast.walk(tree) if isinstance(n, ast.Constant) and isinstance(n.value, str)}


def _helper_modules(path: Path, tree: ast.Module) -> list[Path]:
    """Steward modules the sensor module imports from (one hop), e.g. ``mirrors.py``."""
    found: list[Path] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.level:
            candidates = [node.module.split(".")[0]] if node.module else [alias.name for alias in node.names]
        elif (node.module or "").startswith("gaia_cli.steward."):
            candidates = [node.module.split(".")[2]]
        elif node.module == "gaia_cli.steward":
            candidates = [alias.name for alias in node.names]
        else:
            continue
        for name in candidates:
            if name in _NEUTRAL_HELPERS:
                continue
            candidate = path.parent / f"{name}.py"
            if candidate.is_file() and candidate != path:
                found.append(candidate)
    return found


@functools.lru_cache(maxsize=None)
def _module_literals(source: str) -> frozenset[str]:
    """Literals of one module file plus its imported steward helpers (cached per file)."""
    path = Path(source)
    try:
        tree = ast.parse(path.read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return frozenset()
    literals = _string_literals(tree)
    for helper in _helper_modules(path, tree):
        try:
            literals |= _string_literals(ast.parse(helper.read_text(encoding="utf-8")))
        except (OSError, SyntaxError):
            continue
    return frozenset(literals)


def _sensor_literals(sensor: Any) -> frozenset[str]:
    """String literals in the sensor's module and its imported steward helpers."""
    try:
        source = inspect.getsourcefile(type(sensor))
    except TypeError:
        source = None
    return _module_literals(source) if source else frozenset()


def _names_input(literals: frozenset[str], path: str) -> bool:
    """Whether some literal is the path itself or names something beneath it."""
    wanted = path.rstrip("/")
    for literal in literals:
        shown = literal.strip().rstrip("/")
        if shown == wanted or (wanted not in ("", ".") and shown.startswith(wanted + "/")):
            return True
    return False


@functools.lru_cache(maxsize=None)
def _imported_names(path: str) -> frozenset[str]:
    """Names a module imports from elsewhere, plus attribute names it references."""
    try:
        tree = ast.parse(Path(path).read_text(encoding="utf-8"))
    except (OSError, SyntaxError):
        return frozenset()
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.Attribute):
            names.add(node.attr)
    return frozenset(names)


def _imports_class(root: Path, test: str, class_name: str) -> bool:
    """AST check that a test module imports (or attribute-references) the sensor class."""
    return class_name in _imported_names(str(root / test))


def _is_general_test(test: str) -> bool:
    return any(fnmatch.fnmatchcase(Path(test).as_posix(), pattern) for pattern in GENERAL_TEST_PATTERNS)


def _check_detector(
    root: Path, detector: Any, sensor: Any, ownership: dict[str, set[str]],
    authority: dict[str, str], executors: dict[str, tuple[str, str]], errors: list[str],
) -> None:
    sid = detector.get("id") if isinstance(detector, dict) else None
    label = f"detector {sid!r}"
    if not isinstance(detector, dict) or set(detector) != DETECTOR_FIELDS:
        errors.append(f"{label}: fields must be exactly {sorted(DETECTOR_FIELDS)}")
        return
    declared_routines = list(getattr(sensor, "routine_ids", ()))
    if detector["routineIds"] != declared_routines or not declared_routines:
        errors.append(f"{label}: routineIds {detector['routineIds']!r} must equal the sensor's routine_ids {declared_routines!r}")
    kinds = detector["debtKinds"]
    declared_kinds = list(getattr(sensor, "debt_kinds", ()))
    if not isinstance(kinds, list) or kinds != declared_kinds or not kinds:
        errors.append(f"{label}: debtKinds must equal the sensor's declared debt_kinds {declared_kinds!r}")
        return
    emitted = ownership.get(sid, set())
    if set(kinds) != emitted:
        errors.append(f"{label}: declared debt kinds {sorted(kinds)} differ from kinds emitted in source {sorted(emitted)}")
    if detector["authority"] != {kind: authority.get(kind) for kind in kinds}:
        errors.append(f"{label}: authority must match POLICY.yaml for every debt kind")
    # "Driver input" is a fact about the SENSOR (``driver_inputs``), never about
    # what the catalog says, so a catalog cannot relabel an input to dodge a check.
    declared_driver = tuple(getattr(sensor, "driver_inputs", ()))
    driver = bool(declared_driver)
    for path_text in declared_driver:
        if not isinstance(path_text, str) or not path_text.startswith(DRIVER_INPUT_PREFIX):
            errors.append(f"{label}: sensor driver_inputs must live under {DRIVER_INPUT_PREFIX}")
    catalog_driver = sorted(
        item["path"] for item in detector["inputs"]
        if isinstance(item, dict) and isinstance(item.get("path"), str) and item["path"].startswith(DRIVER_INPUT_PREFIX)
    ) if isinstance(detector["inputs"], list) else []
    if catalog_driver != sorted(p for p in declared_driver if isinstance(p, str)):
        errors.append(
            f"{label}: driver inputs {catalog_driver!r} must equal the sensor's driver_inputs {sorted(declared_driver)!r}"
        )
    literals = _sensor_literals(sensor)
    if not isinstance(detector["inputs"], list) or not detector["inputs"]:
        errors.append(f"{label}: inputs must be a non-empty list")
    else:
        for item in detector["inputs"]:
            if not isinstance(item, dict) or set(item) != {"path", "required"} or not isinstance(item["path"], str) or type(item["required"]) is not bool:
                errors.append(f"{label}: each input needs exactly a string path and a boolean required")
                continue
            if item["path"].startswith(DRIVER_INPUT_PREFIX):
                if item["required"]:
                    errors.append(f"{label}: driver input {item['path']} cannot be required")
            elif not item["required"]:
                errors.append(f"{label}: repository input {item['path']} must be required")
            elif not _tracked(root, item["path"]):
                errors.append(f"{label}: required input {item['path']} is not tracked by Git")
            elif not _names_input(literals, item["path"]):
                errors.append(
                    f"{label}: required input {item['path']} appears nowhere in the sensor's source or its steward helper"
                )
    expected_trigger = "every-scan-with-driver-input" if driver else "every-scan"
    if detector["trigger"] != expected_trigger:
        errors.append(f"{label}: trigger must be {expected_trigger!r}")
    expected_freshness = "driver-input" if driver else "checkout-head"
    if detector["freshness"] != expected_freshness:
        errors.append(f"{label}: freshness must be {expected_freshness!r}")
    failure = detector["failureBehavior"]
    expected_failure = {"unavailable": UNAVAILABLE_BEHAVIOR, "notEvaluated": NOT_EVALUATED_BEHAVIOR if driver else None}
    if failure != expected_failure:
        errors.append(f"{label}: failureBehavior must be {expected_failure!r}")
    for field in ("sourceOfTruth", "evidence"):
        if not isinstance(detector[field], str) or not detector[field].strip():
            errors.append(f"{label}: {field} must be a non-empty string")
    if detector["dedupeKey"] != DEDUPE_KEY:
        errors.append(f"{label}: dedupeKey must be {DEDUPE_KEY!r}")
    scope = getattr(sensor, "resolution_scope", None) or "observed-only"
    if detector["resolutionScope"] != scope:
        errors.append(f"{label}: resolutionScope must be {scope!r}")
    coverage = detector["coverageStatus"]
    expected_static = _expected_static_states(kinds, authority, executors)
    if not isinstance(coverage, dict) or set(coverage) != {"static", "live"}:
        errors.append(f"{label}: coverageStatus must have exactly static and live")
    else:
        if coverage["live"] != "requires-receipt":
            errors.append(f"{label}: a static catalog cannot claim live coverage; live must be 'requires-receipt'")
        if coverage["static"] != expected_static:
            errors.append(f"{label}: static coverage must be {expected_static!r}")
    if detector["owningSkill"] != OBSERVE_SKILL or not _skill_exists(root, OBSERVE_SKILL):
        errors.append(f"{label}: owningSkill must be the existing {OBSERVE_SKILL!r} skill")
    expected_skills = {kind: DISPOSITION_SKILL.get(authority.get(kind, ""), "") for kind in kinds}
    if detector["dispositionSkills"] != expected_skills:
        errors.append(f"{label}: dispositionSkills must route each kind by authority {expected_skills!r}")
    else:
        for skill in set(expected_skills.values()):
            if not _skill_exists(root, skill):
                errors.append(f"{label}: disposition skill {skill!r} does not exist under .agents/skills")
    if not _test_paths_ok(root, detector["proof"]) or not detector["proof"]:
        errors.append(f"{label}: proof must list existing test paths within tests/**")
    else:
        class_name = type(sensor).__name__
        for test in detector["proof"]:
            if not _imports_class(root, test, class_name):
                errors.append(f"{label}: proof test {test} does not import {class_name}")


def _check_binding(
    label: str, index: int, binding: Any, ownership: dict[str, set[str]], registered: dict[str, Any],
    authority: dict[str, str], dispatch_rules: dict, repair_executors: dict, founder_rules: dict, errors: list[str],
) -> tuple[Any, Any] | None:
    if not isinstance(binding, dict) or set(binding) != {"sensorId", "debtKind", "authority", "dispatchRule", "repairExecutor", "founderRule", "bindingStatus"}:
        errors.append(f"{label}: malformed binding fields")
        return None
    sid, kind = binding["sensorId"], binding["debtKind"]
    route, executor, founder_rule = binding["dispatchRule"], binding["repairExecutor"], binding["founderRule"]
    expected_binding_status = "route-bound" if route is not None else "executor-bound" if executor is not None else "founder-routed" if founder_rule is not None else "unrouted"
    if binding["bindingStatus"] != expected_binding_status:
        errors.append(f"{label}: bindingStatus does not match declared live binding")
    if not isinstance(kind, str) or not kind:
        errors.append(f"{label}: debtKind must be a non-empty string")
        return None
    if sid is None:
        if not (index == 3 and kind == "sensor_coverage_unknown"):
            errors.append(f"{label}: null sensorId is only valid for controller sensor_coverage_unknown diagnostics")
    elif not isinstance(sid, str) or sid not in ownership:
        errors.append(f"{label}: unknown sensor claim {sid!r}")
    else:
        if kind not in ownership[sid]:
            errors.append(f"{label}: {sid!r} does not own emitted debt kind {kind!r}")
        if sid not in registered:
            errors.append(f"{label}: sensor {sid!r} exists in source but is not registered")
    declared_authority = binding["authority"]
    if not isinstance(declared_authority, str) or declared_authority != authority.get(kind):
        errors.append(f"{label}: authority mismatch or unknown debt kind {kind!r}")
    if founder_rule is not None:
        if not isinstance(founder_rule, str):
            errors.append(f"{label}: founderRule must be a string or null")
        elif founder_rules.get(founder_rule) != (kind, declared_authority):
            errors.append(f"{label}: founder rule {founder_rule!r} does not authorize {kind!r} at {declared_authority!r}")
    if route is not None:
        if not isinstance(route, str) or route not in dispatch_rules:
            errors.append(f"{label}: fabricated dispatch rule {route!r}")
        elif dispatch_rules[route] != (kind, declared_authority):
            errors.append(f"{label}: dispatch rule {route!r} does not authorize {kind!r} at {declared_authority!r}")
    if executor is not None:
        if not isinstance(executor, str) or executor not in repair_executors:
            errors.append(f"{label}: fabricated repair executor {executor!r}")
        elif repair_executors[executor] != (kind, declared_authority):
            errors.append(f"{label}: repair executor {executor!r} does not authorize {kind!r} at {declared_authority!r}")
    live_routes = {name for name, value in dispatch_rules.items() if value == (kind, declared_authority)}
    live_executors = {name for name, value in repair_executors.items() if value == (kind, declared_authority)}
    live_founder_rules = {name for name, value in founder_rules.items() if value == (kind, declared_authority)}
    if live_routes and (not isinstance(route, str) or route not in live_routes):
        errors.append(f"{label}: missing live dispatch route for {kind!r} at {declared_authority!r}")
    if live_executors and (not isinstance(executor, str) or executor not in live_executors):
        errors.append(f"{label}: missing live repair executor for {kind!r} at {declared_authority!r}")
    if live_founder_rules and (not isinstance(founder_rule, str) or founder_rule not in live_founder_rules):
        errors.append(f"{label}: missing live founder rule for {kind!r} at {declared_authority!r}")
    return (sid, kind)


def validate(root: Path = ROOT, catalog_path: Path | None = None) -> dict[str, Any]:
    path = catalog_path or (root / CATALOG)
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _result([f"cannot read catalog: {exc}"], [], {})
    keys = {"schemaVersion", "stateVocabulary", "routines", "detectors", "hooks"}
    if not isinstance(data, dict) or set(data) != keys or data.get("schemaVersion") != SCHEMA_VERSION:
        return _result([f"catalog must contain schemaVersion: {SCHEMA_VERSION} and exactly {sorted(keys)}"], [], {})
    try:
        routine_text = (root / ROUTINES).read_text(encoding="utf-8")
        headings = re.findall(r"^##\s+(\d+)\.\s+(.+)$", routine_text, re.MULTILINE)
        heading_numbers = [int(number) for number, _ in headings]
        expected_titles = [title.strip() for _, title in headings]
    except OSError as exc:
        return _result([f"cannot read authoritative routine headings: {exc}"], [], {})
    errors: list[str] = []
    if len(expected_titles) != 17:
        errors.append(f"authoritative routines must contain exactly 17 numbered headings; found {len(expected_titles)}")
    if heading_numbers != list(range(1, 18)):
        errors.append(f"authoritative routine heading numbers must be exactly 1..17; found {heading_numbers}")
    vocabulary = data["stateVocabulary"]
    if (not isinstance(vocabulary, dict) or set(vocabulary) != set(STATE_VOCABULARY)
            or any(not isinstance(vocabulary[name], dict) or vocabulary[name].get("evaluation") != evaluation
                   or not isinstance(vocabulary[name].get("meaning"), str) or not vocabulary[name]["meaning"].strip()
                   for name, evaluation in STATE_VOCABULARY.items())):
        errors.append(f"stateVocabulary must define exactly {sorted(STATE_VOCABULARY)} with their static/live evaluation and a meaning")
    _check_hooks(root, data["hooks"], errors)
    rows = data.get("routines")
    if not isinstance(rows, list) or len(rows) != 17:
        return _result(errors + ["catalog must contain exactly 17 routine rows"], [], {})
    title_errors = [f"routine {i}: expected authoritative title {title!r}" for i, (row, title) in enumerate(zip(rows, expected_titles), 1) if not isinstance(row, dict) or row.get("number") != i or row.get("title") != title]
    if title_errors:
        return _result(errors + title_errors, [], {})
    ownership = _sensor_ownership(root)
    authority, dispatch_rules, repair_executors, registered, founder_rules = _live_policy(root)

    detectors = data["detectors"]
    detector_by_id: dict[str, dict] = {}
    if not isinstance(detectors, list):
        errors.append("detectors must be a list")
        detectors = []
    for detector in detectors:
        sid = detector.get("id") if isinstance(detector, dict) else None
        if not isinstance(sid, str):
            errors.append("every detector needs a string id")
            continue
        if sid in detector_by_id:
            errors.append(f"detector {sid!r} is listed twice")
            continue
        if sid not in registered:
            errors.append(f"detector {sid!r} is not a registered sensor")
            continue
        detector_by_id[sid] = detector
        _check_detector(root, detector, registered[sid], ownership, authority, repair_executors, errors)
    missing_contracts = sorted(set(registered) - set(detector_by_id))
    if missing_contracts:
        errors.append(f"registered sensors without a detector contract: {', '.join(missing_contracts)}")

    statuses = {"absent": 0, "partially-covered": 0}
    seen_sensor_ids: set[str] = set()
    for index, (row, title) in enumerate(zip(rows, expected_titles), 1):
        label = f"routine {index}"
        if not isinstance(row, dict) or set(row) != ROUTINE_FIELDS:
            errors.append(f"{label}: fields must be exactly {sorted(ROUTINE_FIELDS)}")
            continue
        expected_detectors = [sid for sid, sensor in registered.items() if index in getattr(sensor, "routine_ids", ())]
        if not isinstance(row["detectorIds"], list) or sorted(row["detectorIds"]) != sorted(expected_detectors) or len(set(row["detectorIds"])) != len(row["detectorIds"]):
            errors.append(f"{label}: detectorIds must be exactly the registered sensors serving it {sorted(expected_detectors)}")
        if not expected_detectors:
            errors.append(f"{label}: no registered detector serves this routine")
        status = row["status"]
        expected_status = "partially-covered" if expected_detectors else "absent"
        if status != expected_status:
            errors.append(f"{label}: status must be {expected_status!r}; a static catalog never claims full coverage")
        else:
            statuses[status] += 1
        if not isinstance(row["predicate"], str) or not row["predicate"].strip():
            errors.append(f"{label}: predicate must be a non-empty string")
        if not isinstance(row["remainingGaps"], list) or not row["remainingGaps"] or not all(isinstance(x, str) and x.strip() for x in row["remainingGaps"]):
            errors.append(f"{label}: remainingGaps must be a non-empty list of non-empty strings")
        if not isinstance(row["owners"], list) or not all(type(x) is int and x > 0 for x in row["owners"]):
            errors.append(f"{label}: owners must be positive issue integers")
        if not _test_paths_ok(root, row["tests"]):
            errors.append(f"{label}: tests must contain existing paths within tests/**")
        else:
            serving = {type(registered[sid]).__name__ for sid in expected_detectors}
            for test in row["tests"]:
                if not _is_general_test(test) and not any(_imports_class(root, test, name) for name in serving):
                    errors.append(
                        f"{label}: test {test} imports no sensor serving this routine "
                        f"and is not a controller, CLI or coverage test"
                    )
        if not isinstance(row["bindings"], list):
            errors.append(f"{label}: bindings must be a list")
            continue
        bound: set[tuple[Any, Any]] = set()
        for binding in row["bindings"]:
            pair = _check_binding(label, index, binding, ownership, registered, authority, dispatch_rules, repair_executors, founder_rules, errors)
            if pair is not None:
                bound.add(pair)
                if isinstance(pair[0], str):
                    seen_sensor_ids.add(pair[0])
        expected_pairs = {(sid, kind) for sid in expected_detectors for kind in getattr(registered[sid], "debt_kinds", ())}
        if index == 3:
            expected_pairs.add((None, "sensor_coverage_unknown"))
        if bound != expected_pairs:
            missing = sorted(f"{sid}:{kind}" for sid, kind in expected_pairs - bound)
            extra = sorted(f"{sid}:{kind}" for sid, kind in bound - expected_pairs)
            errors.append(f"{label}: bindings must cover each detector debt kind exactly (missing {missing}, extra {extra})")
    unaccounted = sorted(set(registered) - seen_sensor_ids)
    if unaccounted:
        errors.append(f"registered sensors not accounted for: {', '.join(unaccounted)}")
    return _result(errors, unaccounted, statuses, len(registered), len(registered) - len(unaccounted), len(dispatch_rules), len(repair_executors))


def live_states(root: Path, receipt: dict[str, Any], catalog_path: Path | None = None) -> dict[str, list[str]]:
    """Derive per-detector live states from one receipt; absence is never healthy."""
    data = json.loads((catalog_path or (root / CATALOG)).read_text(encoding="utf-8"))
    known = set(receipt.get("coverageKnown") or ())
    unknown = set(receipt.get("coverageUnknown") or ())
    not_evaluated = {item.get("sensor") for item in receipt.get("notEvaluated") or () if isinstance(item, dict)}
    partial = {item.get("sensor") for item in receipt.get("partialCoverage") or () if isinstance(item, dict)}
    states: dict[str, list[str]] = {}
    for detector in data["detectors"]:
        sid = detector["id"]
        live = {"actively-observed" if sid in known and sid not in unknown and sid not in not_evaluated else "unknown-unavailable"}
        if sid in partial and "actively-observed" in live:
            # Observed, but some subjects were skipped: nothing it owns was swept.
            live.add("partially-covered")
        states[sid] = sorted(set(detector["coverageStatus"]["static"]) | live)
    return states


def _result(errors: list[str], unaccounted: list[str], statuses: dict[str, int], registered: int = 0, accounted: int = 0, dispatch_rules: int = 0, repair_executors: int = 0) -> dict[str, Any]:
    return {"capabilityOnly": True, "liveHealth": "not-evaluated", "routineCount": 17 if not errors or statuses else 0,
            "statusCounts": statuses, "registeredSensorCount": registered, "accountedSensorCount": accounted,
            "dispatchRuleCount": dispatch_rules, "repairExecutorCount": repair_executors,
            "unaccountedSensors": unaccounted, "dependencyPending": any("dependency pending" in e for e in errors),
            "errors": errors, "ok": not errors}


def lie_catalogs(data: dict[str, Any]) -> dict[str, dict[str, Any]]:
    """Self-consistent catalog lies the checker must reject (used by ``--check`` and the tests).

    Each one is internally tidy and would pass a check that only compares the
    catalog with itself; each is false about the sensor or its tests.
    """
    def clone() -> dict[str, Any]:
        return json.loads(json.dumps(data))

    def detector(copy: dict[str, Any], sensor_id: str) -> dict[str, Any]:
        return next(item for item in copy["detectors"] if item["id"] == sensor_id)

    result: dict[str, dict[str, Any]] = {}
    copy = clone()
    detector(copy, "frontend-contract")["inputs"] = [{"path": "README.md", "required": True}]
    result["readme-as-input"] = copy
    copy = clone()
    detector(copy, "frontend-contract")["inputs"].append({"path": "LICENSE", "required": True})
    result["unrelated-required-input"] = copy
    copy = clone()
    detector(copy, "frontend-contract")["proof"].append("tests/steward/test_primitives.py")
    result["non-importing-proof-test"] = copy
    copy = clone()
    copy["routines"][0]["tests"].append("tests/steward/test_primitives.py")
    result["unrelated-routine-test"] = copy
    copy = clone()
    detector(copy, "frontend-contract")["inputs"].append({"path": DRIVER_INPUT_PREFIX + "x.json", "required": False})
    result["invented-driver-input"] = copy
    copy = clone()
    detector(copy, "ci-health")["inputs"] = [{"path": "docs", "required": True}]
    result["hidden-driver-input"] = copy
    return result


def self_check(root: Path = ROOT) -> list[str]:
    """Return the names of lies the checker wrongly accepted (empty means it still has teeth)."""
    data = json.loads((root / CATALOG).read_text(encoding="utf-8"))
    accepted: list[str] = []
    with tempfile.TemporaryDirectory() as scratch:
        for name, mutated in lie_catalogs(data).items():
            path = Path(scratch) / f"{name}.json"
            path.write_text(json.dumps(mutated), encoding="utf-8")
            if validate(root, path)["ok"]:
                accepted.append(name)
    return accepted


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="also prove the checker still rejects its known catalog lies (README as input, unrelated "
        "input, non-importing proof test, unrelated routine test, flipped driver semantics)",
    )
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    parser.add_argument("--receipt", type=Path, help="also derive live per-detector states from one Steward receipt")
    args = parser.parse_args()
    result = validate()
    if args.check and result["ok"]:
        for name in self_check():
            result["errors"].append(f"self-check: the checker accepted the false catalog {name!r}")
        result["ok"] = not result["errors"]
    if args.receipt is not None:
        try:
            receipt = json.loads(args.receipt.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            result["errors"].append(f"cannot read receipt: {exc}")
            result["ok"] = False
        else:
            if result["ok"]:
                result["liveHealth"] = "receipt"
                result["receiptRunId"] = receipt.get("runId")
                result["liveStates"] = live_states(ROOT, receipt)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Steward coverage check: " + ("ok" if result["ok"] else "FAILED"))
        for error in result["errors"]:
            print(f"- {error}")
        for sensor_id, states in sorted(result.get("liveStates", {}).items()):
            print(f"  {sensor_id}: {', '.join(states)}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
