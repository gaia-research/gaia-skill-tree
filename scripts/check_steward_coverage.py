#!/usr/bin/env python3
"""Validate the static Steward routine capability inventory (never run sensors)."""
from __future__ import annotations

import argparse
import ast
import json
import re
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
CATALOG = Path("founder/steward/routine-coverage.json")
ROUTINES = Path("founder/ROUTINES.md")
EXPECTED_SENSOR_IDS = {
    "bundled-schema-mirror", "agent-skill-mirror", "registry-integrity", "cli-contract",
    "discovery-generic-mapping", "taxonomy-script-drift", "upstream-watcher",
    "knowledge-contradiction", "evidence-link-health", "generated-projections",
    "benchmark-freshness", "trust-calibration-drift", "frozen-skill-integrity",
    "repository-hygiene",
}


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


def _live_policy(root: Path) -> tuple[dict[str, str], dict[str, tuple[str, str]], dict[str, tuple[str, str]], set[str], dict[str, tuple[str, str]]]:
    sys.path.insert(0, str(root / "src"))
    from gaia_cli.steward.controller import StewardController
    from gaia_cli.steward.policy import StewardPolicy
    policy = StewardPolicy.load(root)
    registered = {sensor.id for sensor in StewardController().sensors}
    authority = {kind: value.value for kind, value in policy.authority.items()}
    dispatch = {rule.id: (rule.debt_kind, rule.authority.value) for rule in policy.dispatch_rules.values()}
    executors = {key: (executor.debt_kind, executor.authority.value) for key, executor in policy.repair_executors.items()}
    founder_rules = {
        rule_id: (rule.debt_kind, rule.authority.value)
        for rule_id, rule in policy.founder_rules.items()
    }
    return authority, dispatch, executors, registered, founder_rules


def validate(root: Path = ROOT, catalog_path: Path | None = None) -> dict[str, Any]:
    path = catalog_path or (root / CATALOG)
    errors: list[str] = []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        return _result([f"cannot read catalog: {exc}"], [], {})
    if not isinstance(data, dict) or set(data) != {"schemaVersion", "routines", "hooks"} or data.get("schemaVersion") != 1:
        return _result(["catalog must contain schemaVersion: 1, routines, and hooks only"], [], {})
    try:
        routine_text = (root / ROUTINES).read_text(encoding="utf-8")
        headings = re.findall(r"^##\s+(\d+)\.\s+(.+)$", routine_text, re.MULTILINE)
        heading_numbers = [int(number) for number, _ in headings]
        expected_titles = [title.strip() for _, title in headings]
    except OSError as exc:
        return _result([f"cannot read authoritative routine headings: {exc}"], [], {})
    errors = []
    if len(expected_titles) != 17:
        errors.append(f"authoritative routines must contain exactly 17 numbered headings; found {len(expected_titles)}")
    if heading_numbers != list(range(1, 18)):
        errors.append(f"authoritative routine heading numbers must be exactly 1..17; found {heading_numbers}")
    hooks = data["hooks"]
    expected_hooks = {1922, 1445, 2063}
    hook_owners = [h.get("owner") for h in hooks if isinstance(h, dict)] if isinstance(hooks, list) else []
    if (not isinstance(hooks, list) or len(hook_owners) != len(hooks)
            or any(type(owner) is not int for owner in hook_owners)
            or set(hook_owners) != expected_hooks):
        errors.append("hooks must inventory owners 1922, 1445, and 2063")
    else:
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
    rows = data.get("routines")
    if not isinstance(rows, list) or len(rows) != 17:
        return _result(["catalog must contain exactly 17 routine rows"], [], {})
    title_errors = [f"routine {i}: expected authoritative title {title!r}" for i, (row, title) in enumerate(zip(rows, expected_titles), 1) if not isinstance(row, dict) or row.get("number") != i or row.get("title") != title]
    if title_errors:
        return _result(errors + title_errors, [], {})
    ownership = _sensor_ownership(root)
    authority, dispatch_rules, repair_executors, registered, founder_rules = _live_policy(root)
    dispatch_ids, executor_ids = set(dispatch_rules), set(repair_executors)
    if len(registered) != 14 or registered != EXPECTED_SENSOR_IDS:
        errors.append(f"registered sensor dependency pending/drifted: expected 14 sensors including repository-hygiene; found {len(registered)} ({', '.join(sorted(registered))})")
    if len(dispatch_ids) != 5:
        errors.append(f"dispatch-rule inventory drifted: expected 5 live rules, found {len(dispatch_ids)}")
    if len(executor_ids) != 2:
        errors.append(f"repair-executor inventory drifted: expected 2 live executors, found {len(executor_ids)}")
    seen_sensor_ids: set[str] = set()
    statuses = {name: 0 for name in ("absent", "partial", "present-undeliverable", "human-gated", "present")}
    statuses.pop("present")
    for index, (row, title) in enumerate(zip(rows, expected_titles), 1):
        label = f"routine {index}"
        required = {"number", "title", "status", "bindings", "predicate", "remainingGaps", "owners", "tests"}
        if not isinstance(row, dict) or set(row) != required:
            errors.append(f"{label}: fields must be exactly {sorted(required)}")
            continue
        if row["number"] != index or row["title"] != title:
            errors.append(f"{label}: expected exact number/title {index}: {title!r}")
        status = row["status"]
        if not isinstance(status, str) or status not in {"absent", "partial", "present-undeliverable", "human-gated"}:
            errors.append(f"{label}: invalid status {status!r}")
        else:
            statuses[status] += 1
        if not isinstance(row["predicate"], str) or not row["predicate"].strip():
            errors.append(f"{label}: predicate must be a non-empty string")
        if not isinstance(row["remainingGaps"], list) or not row["remainingGaps"] or not all(isinstance(x, str) and x.strip() for x in row["remainingGaps"]):
            errors.append(f"{label}: remainingGaps must be a non-empty list of non-empty strings")
        if not isinstance(row["owners"], list) or not all(type(x) is int and x > 0 for x in row["owners"]):
            errors.append(f"{label}: owners must be positive issue integers")
        if not isinstance(row["tests"], list) or not all(isinstance(x, str) and Path(x).as_posix().startswith("tests/") and ".." not in Path(x).parts and (root / x).is_file() for x in row["tests"]):
            errors.append(f"{label}: tests must contain existing paths within tests/**")
        if not isinstance(row["bindings"], list):
            errors.append(f"{label}: bindings must be a list")
            continue
        for binding in row["bindings"]:
            if not isinstance(binding, dict) or set(binding) != {"sensorId", "debtKind", "authority", "dispatchRule", "repairExecutor", "founderRule", "bindingStatus"}:
                errors.append(f"{label}: malformed binding fields")
                continue
            sid, kind = binding["sensorId"], binding["debtKind"]
            route, executor, founder_rule = binding["dispatchRule"], binding["repairExecutor"], binding["founderRule"]
            expected_binding_status = "route-bound" if route is not None else "executor-bound" if executor is not None else "founder-routed" if founder_rule is not None else "unrouted"
            if binding["bindingStatus"] != expected_binding_status:
                errors.append(f"{label}: bindingStatus does not match declared live binding")
            if not isinstance(kind, str) or not kind:
                errors.append(f"{label}: debtKind must be a non-empty string")
                continue
            if sid is None:
                if not (index == 3 and kind == "sensor_coverage_unknown"):
                    errors.append(f"{label}: null sensorId is only valid for controller sensor_coverage_unknown diagnostics")
            elif not isinstance(sid, str) or sid not in ownership:
                errors.append(f"{label}: unknown sensor claim {sid!r}")
            else:
                seen_sensor_ids.add(sid)
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
            live_routes = {name for name, binding in dispatch_rules.items() if binding == (kind, declared_authority)}
            live_executors = {name for name, binding in repair_executors.items() if binding == (kind, declared_authority)}
            live_founder_rules = {name for name, binding in founder_rules.items() if binding == (kind, declared_authority)}
            if live_routes and (not isinstance(route, str) or route not in live_routes):
                errors.append(f"{label}: missing live dispatch route for {kind!r} at {declared_authority!r}")
            if live_executors and (not isinstance(executor, str) or executor not in live_executors):
                errors.append(f"{label}: missing live repair executor for {kind!r} at {declared_authority!r}")
            if live_founder_rules and (not isinstance(founder_rule, str) or founder_rule not in live_founder_rules):
                errors.append(f"{label}: missing live founder rule for {kind!r} at {declared_authority!r}")
    unaccounted = sorted(registered - seen_sensor_ids)
    if unaccounted:
        errors.append(f"registered sensors not accounted for: {', '.join(unaccounted)}")
    return _result(errors, unaccounted, statuses, len(registered), len(registered) - len(unaccounted), len(dispatch_ids), len(executor_ids))


def _result(errors: list[str], unaccounted: list[str], statuses: dict[str, int], registered: int = 0, accounted: int = 0, dispatch_rules: int = 0, repair_executors: int = 0) -> dict[str, Any]:
    return {"capabilityOnly": True, "liveHealth": "not-evaluated", "routineCount": 17 if not errors or statuses else 0,
            "statusCounts": statuses, "registeredSensorCount": registered, "accountedSensorCount": accounted,
            "dispatchRuleCount": dispatch_rules, "repairExecutorCount": repair_executors,
            "unaccountedSensors": unaccounted, "dependencyPending": any("dependency pending" in e for e in errors),
            "errors": errors, "ok": not errors}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true", help="validate inventory against source and policy")
    parser.add_argument("--json", action="store_true", help="emit machine-readable result")
    args = parser.parse_args()
    result = validate()
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Steward coverage check: " + ("ok" if result["ok"] else "FAILED"))
        for error in result["errors"]:
            print(f"- {error}")
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
