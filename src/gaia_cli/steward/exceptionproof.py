"""Mechanical verification for swallowed exception repairs.

Proves that a candidate patch for a swallowed_exception debt does strictly
what the Class B envelope authorizes:
- Preserves the entire AST outside ExceptHandler nodes.
- Strictly preserves the body of every try block.
- Preserves handler control flow: exact terminal control flow (pass/continue/break/return)
  is preserved; no new raise is introduced; return values and loop semantics are unchanged.
- Allows only valid repairs to except handlers:
  (a) Narrowing the exception type from broad (Exception/BaseException/bare) to specific.
  (b) Adding diagnostic logging before the fallback/terminal statement.
  (c) Adding/updating the documented `# steward: best-effort: <reason>` intent marker.
- Enforces mandatory triage: handlers that feed authorization, budget/spend recording,
  file overwrite, or mutation decisions cannot be marked with best-effort markers and must
  be escalated to engineering.
"""

from __future__ import annotations

import ast
import builtins
import difflib
import re
from typing import Any

from gaia_cli.steward.primitives.pyast import comment_map
from gaia_cli.steward.sensors_code import SourceFile, swallowed_handlers

__all__ = [
    "prove_exception_edit",
    "is_escalated_security_context",
    "is_escalated_try_block",
    "_ESCALATED_LINE_LOCATIONS",
]

_BEST_EFFORT_RE = re.compile(r"steward:\s*best-effort:\s*(\S.*)")

# Canonical built-in exceptions derived directly from Python builtins
_BUILTIN_EXCEPTIONS = frozenset(
    name for name, cls in vars(builtins).items()
    if isinstance(cls, type) and issubclass(cls, BaseException)
)

# Known safe standard library module exceptions
_MODULE_EXCEPTIONS: dict[str, frozenset[str]] = {
    "json": frozenset({"JSONDecodeError"}),
    "yaml": frozenset({"YAMLError", "MarkedYAMLError"}),
    "subprocess": frozenset({"CalledProcessError", "SubprocessError", "TimeoutExpired"}),
    "urllib.error": frozenset({"URLError", "HTTPError"}),
}

_SAFE_LOG_METHODS = {
    "debug",
    "info",
    "warning",
    "warn",
    "error",
    "exception",
}
_SAFE_LOG_NAMES = {"logger", "log", "logging"}

_ESCALATED_MODULES = frozenset({
    "src/gaia_cli/authz.py",
    "src/gaia_cli/auth.py",
    "src/gaia_cli/commands/dev/calibrate.py",
    "src/gaia_cli/commands/dev/timeline.py",
})

_ESCALATED_FUNCTION_NAMES = frozenset({
    "_registry_has_any_verifier",
    "_is_verifier",
    "_has_verifier_skill",
    "_recordSpend",
    "load_manifest",
    "_load_manifest",
    "save_manifest",
    "require_operator",
    "canonicalTransactionLock",
    "preflightLinkCommand",
    "preflightMergeCommand",
    "preflightSplitCommand",
    "preflightRenameCommand",
    "preflightRemoveCommand",
    "preflightReclassifyCommand",
    "_valid_timeline_actions",
    "_preflight_target_skill_exists",
    "calibrate_command",
    "_skill_exists",
    "scan_command",
    "fuse_command",
})

_ESCALATED_LINE_LOCATIONS: dict[str, set[int]] = {
    "src/gaia_cli/jev.py": {838, 839},
    "src/gaia_cli/install.py": {68, 69},
}

_SENSITIVE_IDENTIFIERS = frozenset({
    "spent_usd",
    "budget_file",
    "budget_data",
    "install-manifest",
    "require_operator",
    "canonicalTransactionLock",
    "_recordSpend",
    "load_manifest",
    "save_manifest",
    "custom_state_path",
    "custom_state",
    "custom_state.json",
    "manifest.json",
})


def is_escalated_try_block(
    try_node: ast.Try,
    func_name: str | None,
    filename: str,
) -> bool:
    """Whether an ast.Try block is an escalated authorization, budget, overwrite, or mutation boundary.

    Uses stable AST structural identity; does NOT rely on line numbers.
    """
    norm = filename.replace("\\", "/")
    # Whole-module escalations: authz.py, auth.py, commands/dev/calibrate.py, commands/dev/timeline.py
    if any(norm == m or norm.endswith("/" + m) or norm.endswith(m) for m in _ESCALATED_MODULES):
        return True
    if any(k in norm for k in ("authz", "auth.", "commands/dev/calibrate", "commands/dev/timeline")):
        return True

    # Escalated functions that feed auth, manifest load/save, mutation, or budget
    if func_name and func_name in _ESCALATED_FUNCTION_NAMES:
        if func_name in ("scan_command", "fuse_command"):
            for sub in ast.walk(try_node):
                if isinstance(sub, ast.Name) and sub.id in ("custom_state_path", "custom_state", "manifest", "manifest_path"):
                    return True
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    if any(k in sub.value for k in ("custom_state", "manifest")):
                        return True
        else:
            return True

    # In jev.py, any try block that feeds budget recording or spent_usd
    if "jev.py" in norm:
        for sub in ast.walk(try_node):
            if isinstance(sub, ast.Name) and sub.id in ("_recordSpend", "spent_usd", "budget_file", "budget_data"):
                return True
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if any(k in sub.value for k in ("spent_usd", "budget")):
                    return True

    # In install.py / impl.py, any try block that touches manifest reading/writing or custom_state
    if "install.py" in norm or "impl.py" in norm:
        for sub in ast.walk(try_node):
            if isinstance(sub, ast.Name) and sub.id in (
                "load_manifest", "save_manifest", "_load_manifest", "custom_state_path", "custom_state"
            ):
                return True
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if any(k in sub.value for k in ("install-manifest", "manifest.json", "custom_state.json", "custom_state")):
                    return True

    # Any try block containing sensitive identifiers anywhere in its body
    for sub in ast.walk(try_node):
        if isinstance(sub, ast.Name) and sub.id in _SENSITIVE_IDENTIFIERS:
            return True
        if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
            if any(k in sub.value for k in ("spent_usd", "install-manifest", "custom_state.json", "manifest.json")):
                return True

    return False


def is_escalated_security_context(
    filename: str,
    func_name: str | None = None,
    line: int | None = None,
    node: ast.AST | None = None,
) -> bool:
    """Whether a file or function context is an escalated security/budget/overwrite boundary."""
    norm = filename.replace("\\", "/")
    if any(norm == m or norm.endswith("/" + m) or norm.endswith(m) for m in _ESCALATED_MODULES):
        return True
    if any(k in norm for k in ("authz", "auth.", "commands/dev/calibrate", "commands/dev/timeline")):
        return True
    if func_name and func_name in _ESCALATED_FUNCTION_NAMES:
        if func_name == "evaluate" and "jev.py" in norm:
            if line is not None and line not in (838, 839) and node is None:
                return False
        if func_name in ("scan_command", "fuse_command") and node is not None:
            if isinstance(node, ast.Try):
                return is_escalated_try_block(node, func_name, filename)
        return True
    for mod_path, lines in _ESCALATED_LINE_LOCATIONS.items():
        if norm == mod_path or norm.endswith("/" + mod_path):
            if line is not None and line in lines:
                return True
    if node is not None:
        if isinstance(node, ast.Try):
            return is_escalated_try_block(node, func_name, filename)
        for sub in ast.walk(node):
            if isinstance(sub, ast.Name) and sub.id in _SENSITIVE_IDENTIFIERS:
                return True
            if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                if any(k in sub.value for k in ("spent_usd", "install-manifest", "custom_state.json", "manifest.json")):
                    return True
    return False


def _ast_equal(n1: Any, n2: Any) -> bool:
    """Compare two AST nodes for structural equality ignoring positions."""
    if type(n1) is not type(n2):
        return False
    if isinstance(n1, (list, tuple)):
        if len(n1) != len(n2):
            return False
        return all(_ast_equal(a, b) for a, b in zip(n1, n2))
    if isinstance(n1, ast.AST):
        for field in n1._fields:
            v1 = getattr(n1, field, None)
            v2 = getattr(n2, field, None)
            if not _ast_equal(v1, v2):
                return False
        return True
    return n1 == n2 and type(n1) is type(n2)


def get_module_scope_provenance(tree: ast.Module) -> dict[str, str]:
    """Inspect top-level module statements for verified, trusted imports and loggers.

    Rejects arbitrary assignments like 'sys = attacker' or 'logger = None'.
    """
    trusted: dict[str, str] = {}
    logger_assign_counts: dict[str, int] = {}
    invalid_logger_targets: set[str] = set()

    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name in ("sys", "json", "yaml", "subprocess", "logging"):
                    if not alias.asname or alias.asname == alias.name:
                        trusted[alias.name] = alias.name
        elif isinstance(stmt, ast.ImportFrom):
            if stmt.module == "gaia_cli.structuredRead":
                for alias in stmt.names:
                    if alias.name == "logDiagnostic" and (not alias.asname or alias.asname == "logDiagnostic"):
                        trusted["logDiagnostic"] = "gaia_cli.structuredRead.logDiagnostic"
            elif stmt.module == "logging":
                for alias in stmt.names:
                    if alias.name == "getLogger" and (not alias.asname or alias.asname == "getLogger"):
                        trusted["getLogger"] = "logging.getLogger"

    # Verify that logger / log is assigned strictly via trusted logging.getLogger(...)
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                if isinstance(target, ast.Name) and target.id in ("logger", "log"):
                    tname = target.id
                    logger_assign_counts[tname] = logger_assign_counts.get(tname, 0) + 1
                    val = stmt.value
                    is_valid = False
                    if isinstance(val, ast.Call):
                        call_func = val.func
                        if isinstance(call_func, ast.Attribute) and isinstance(call_func.value, ast.Name):
                            # Must be logging.getLogger where logging was genuinely imported
                            if (
                                call_func.value.id in trusted
                                and trusted[call_func.value.id] == "logging"
                                and call_func.attr == "getLogger"
                            ):
                                is_valid = True
                        elif isinstance(call_func, ast.Name):
                            # Must be getLogger from logging where getLogger was genuinely imported
                            if trusted.get(call_func.id) == "logging.getLogger":
                                is_valid = True
                    if is_valid and logger_assign_counts[tname] == 1:
                        trusted[tname] = "logging.Logger"
                    else:
                        invalid_logger_targets.add(tname)
                        trusted.pop(tname, None)
        elif isinstance(stmt, ast.AnnAssign):
            if isinstance(stmt.target, ast.Name) and stmt.target.id in ("logger", "log"):
                invalid_logger_targets.add(stmt.target.id)
                trusted.pop(stmt.target.id, None)

    for bad in invalid_logger_targets:
        trusted.pop(bad, None)

    return trusted


def get_shadowed_names(
    tree: ast.Module,
    func_node: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
) -> frozenset[str]:
    """Collect all names assigned locally or globally that could shadow builtins or imports."""
    shadowed: set[str] = set()

    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
            for t in targets:
                if isinstance(t, ast.Name) and t.id not in ("logger", "log"):
                    shadowed.add(t.id)
        elif isinstance(stmt, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            shadowed.add(stmt.name)
        elif isinstance(stmt, ast.Import):
            for alias in stmt.names:
                name = alias.asname or alias.name.split(".")[0]
                if name not in ("sys", "json", "yaml", "subprocess", "logging"):
                    shadowed.add(name)
        elif isinstance(stmt, ast.ImportFrom):
            for alias in stmt.names:
                name = alias.asname or alias.name
                if not (stmt.module == "gaia_cli.structuredRead" and name == "logDiagnostic") and not (
                    stmt.module == "logging" and name == "getLogger"
                ):
                    shadowed.add(name)

    if func_node is not None:
        for arg in func_node.args.args + func_node.args.kwonlyargs:
            shadowed.add(arg.arg)
        if func_node.args.vararg:
            shadowed.add(func_node.args.vararg.arg)
        if func_node.args.kwarg:
            shadowed.add(func_node.args.kwarg.arg)
        for sub in ast.walk(func_node):
            if isinstance(sub, (ast.Assign, ast.AnnAssign)):
                targets = sub.targets if isinstance(sub, ast.Assign) else [sub.target]
                for t in targets:
                    if isinstance(t, ast.Name):
                        shadowed.add(t.id)
            elif isinstance(sub, (ast.For, ast.AsyncFor)):
                if isinstance(sub.target, ast.Name):
                    shadowed.add(sub.target.id)
            elif isinstance(sub, ast.ExceptHandler) and sub.name:
                shadowed.add(sub.name)

    return frozenset(shadowed)


def _is_valid_exception_ref(
    node: ast.expr,
    trusted: dict[str, str],
    shadowed: frozenset[str],
) -> bool:
    """Verify that an AST expression is strictly a verified, side-effect-free exception reference."""
    if isinstance(node, ast.Name):
        return node.id in _BUILTIN_EXCEPTIONS and node.id not in shadowed
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        mod_name = node.value.id
        if mod_name in trusted and mod_name not in shadowed:
            actual_mod = trusted[mod_name]
            known_attrs = _MODULE_EXCEPTIONS.get(actual_mod)
            if known_attrs and node.attr in known_attrs:
                return True
    return False


def _exception_level(node: ast.expr | None) -> int:
    """Return breadth level:
    2 = bare except or BaseException
    1 = Exception
    0 = specific exception(s)
    """
    if node is None:
        return 2
    elements = node.elts if isinstance(node, ast.Tuple) else [node]
    has_base = False
    has_exception = False
    for el in elements:
        name = None
        if isinstance(el, ast.Name):
            name = el.id
        elif isinstance(el, ast.Attribute):
            name = el.attr
        if name == "BaseException":
            has_base = True
        elif name == "Exception":
            has_exception = True
    if has_base:
        return 2
    if has_exception:
        return 1
    return 0


def _is_narrowed(
    old_type: ast.expr | None,
    new_type: ast.expr | None,
    trusted: dict[str, str],
    shadowed: frozenset[str],
) -> bool:
    if new_type is None:
        return False
    elements = new_type.elts if isinstance(new_type, ast.Tuple) else [new_type]
    if not elements:
        return False
    # All elements must be verified, side-effect-free exception type references
    if not all(_is_valid_exception_ref(el, trusted, shadowed) for el in elements):
        return False
    return _exception_level(new_type) < _exception_level(old_type)


def _is_safe_argument(expr: ast.expr, bound_name: str | None = None) -> bool:
    """Verify an argument to a diagnostic call is strictly pure and side-effect free."""
    if isinstance(expr, ast.Constant):
        return True
    if isinstance(expr, ast.Name):
        return bound_name is not None and expr.id == bound_name
    return False


def _is_diagnostic_or_logging(
    stmt: ast.stmt,
    handler: ast.ExceptHandler | None = None,
    trusted: dict[str, str] | None = None,
    shadowed: frozenset[str] | None = None,
) -> bool:
    """Check if a statement is a strictly safe diagnostic or logging call with verified binding and provenance."""
    if not isinstance(stmt, ast.Expr):
        return False
    if not isinstance(stmt.value, ast.Call):
        return False

    call = stmt.value
    func = call.func
    t = trusted if trusted is not None else {}
    s = shadowed if shadowed is not None else frozenset()

    # Check function target with verified binding:
    # 1. sys.stderr.write(...) or sys.stdout.write(...) -> requires 'sys' in trusted and not shadowed
    # 2. logger.<method>(...) or log.<method>(...) -> requires 'logger' or 'log' in trusted and not shadowed
    # 3. logDiagnostic(...) -> requires 'logDiagnostic' in trusted and not shadowed
    is_safe_target = False
    if isinstance(func, ast.Name) and func.id == "logDiagnostic":
        if t.get("logDiagnostic") == "gaia_cli.structuredRead.logDiagnostic" and "logDiagnostic" not in s:
            is_safe_target = True
    elif isinstance(func, ast.Attribute):
        val = func.value
        if isinstance(val, ast.Name):
            if val.id in _SAFE_LOG_NAMES and func.attr in _SAFE_LOG_METHODS:
                if t.get(val.id) == "logging.Logger" and val.id not in s:
                    is_safe_target = True
        elif isinstance(val, ast.Attribute) and isinstance(val.value, ast.Name):
            if val.value.id == "sys" and val.attr in ("stderr", "stdout") and func.attr == "write":
                if t.get("sys") == "sys" and "sys" not in s:
                    is_safe_target = True

    if not is_safe_target:
        return False

    bound_name = handler.name if handler is not None else None

    # Check that all positional and keyword arguments are safe and pure
    for arg in call.args:
        if not _is_safe_argument(arg, bound_name):
            return False
    for kw in call.keywords:
        if kw.arg == "exc_info":
            if isinstance(kw.value, ast.Constant):
                continue
            if isinstance(kw.value, ast.Name) and bound_name is not None and kw.value.id == bound_name:
                continue
            return False
        elif not _is_safe_argument(kw.value, bound_name):
            return False

    return True


def _is_pass_or_trivial(stmt: ast.stmt) -> bool:
    if isinstance(stmt, ast.Pass):
        return True
    if isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant):
        if stmt.value.value is Ellipsis or isinstance(stmt.value.value, str):
            return True
    return False


def _get_best_effort_reason(handler: ast.ExceptHandler, code: str) -> str | None:
    """Retrieve the non-empty reason from a # steward: best-effort: <reason> comment."""
    comments = comment_map(code)
    start = getattr(handler, "lineno", 1)
    end = start
    if handler.body:
        end = max(getattr(stmt, "end_lineno", getattr(stmt, "lineno", start)) for stmt in handler.body)

    for line in range(start, end + 1):
        line_comment = comments.get(line, "")
        match = _BEST_EFFORT_RE.search(line_comment)
        if match:
            reason = match.group(1).strip()
            if reason:
                return reason
    return None


def _verify_handler_edit(
    h1: ast.ExceptHandler,
    h2: ast.ExceptHandler,
    before_code: str,
    after_code: str,
    filename: str = "",
    func_name: str | None = None,
    trusted: dict[str, str] | None = None,
    shadowed: frozenset[str] | None = None,
    is_escalated: bool = False,
) -> list[str]:
    best_effort_1 = _get_best_effort_reason(h1, before_code)
    best_effort_2 = _get_best_effort_reason(h2, after_code)

    # Check AST equality and comment equality: unchanged handlers pass immediately!
    if _ast_equal(h1, h2) and best_effort_1 == best_effort_2:
        return []

    violations: list[str] = []
    line = getattr(h2, "lineno", "?")

    # Escalated security context check on changed handlers:
    if is_escalated:
        return [
            f"line {line}: handler feeds authorization, budget/spend recording, file overwrite, "
            f"or mutation decisions; cannot be resolved autonomously (must be escalated to engineering)"
        ]

    # Preserve exception binding name strictly
    if h1.name != h2.name:
        violations.append(
            f"line {line}: exception handler variable binding changed from "
            f"{h1.name!r} to {h2.name!r} (variable bindings must be strictly preserved)"
        )

    # 1. No new raise statements introduced
    has_raise_before = any(isinstance(n, ast.Raise) for n in ast.walk(h1))
    has_raise_after = any(isinstance(n, ast.Raise) for n in ast.walk(h2))
    if has_raise_after and not has_raise_before:
        violations.append(f"line {line}: new raise statement introduced in except handler")

    # 2. Control flow preservation
    if h1.body:
        term1 = h1.body[-1]
        term2 = h2.body[-1] if h2.body else None

        if isinstance(term1, ast.Return):
            if not isinstance(term2, ast.Return):
                violations.append(f"line {line}: control flow altered: return statement was removed or replaced")
            elif not _ast_equal(term1.value, term2.value):
                violations.append(f"line {line}: return value modified in except handler")
            for n in ast.walk(h2):
                if isinstance(n, ast.Return) and not _ast_equal(n.value, term1.value):
                    violations.append(f"line {line}: return value modified in except handler")

        elif isinstance(term1, ast.Continue):
            if not isinstance(term2, ast.Continue):
                violations.append(f"line {line}: control flow altered: continue statement was removed or replaced")
            for n in ast.walk(h2):
                if isinstance(n, (ast.Break, ast.Return)):
                    violations.append(f"line {line}: control flow altered: {type(n).__name__.lower()} introduced in continue handler")

        elif isinstance(term1, ast.Break):
            if not isinstance(term2, ast.Break):
                violations.append(f"line {line}: control flow altered: break statement was removed or replaced")
            for n in ast.walk(h2):
                if isinstance(n, (ast.Continue, ast.Return)):
                    violations.append(f"line {line}: control flow altered: {type(n).__name__.lower()} introduced in break handler")

        elif _is_pass_or_trivial(term1):
            for n in ast.walk(h2):
                if isinstance(n, (ast.Return, ast.Continue, ast.Break)):
                    violations.append(f"line {line}: control flow altered: {type(n).__name__.lower()} introduced in pass/fallback handler")
                    break

    t = trusted if trusted is not None else {}
    s = shadowed if shadowed is not None else frozenset()

    # 3. Handler body statement preservation:
    old_non_trivial = [stmt for stmt in h1.body if not _is_pass_or_trivial(stmt)]
    new_non_trivial = [stmt for stmt in h2.body if not _is_pass_or_trivial(stmt) and not _is_diagnostic_or_logging(stmt, h2, t, s)]

    if len(old_non_trivial) != len(new_non_trivial) or not all(_ast_equal(s1, s2) for s1, s2 in zip(old_non_trivial, new_non_trivial)):
        violations.append(f"line {line}: existing statements in except handler were reordered, removed, or modified")

    for stmt in h2.body:
        if (
            not any(_ast_equal(stmt, old_s) for old_s in h1.body)
            and not _is_diagnostic_or_logging(stmt, h2, t, s)
            and not _is_pass_or_trivial(stmt)
        ):
            stmt_repr = ast.unparse(stmt) if hasattr(ast, "unparse") else type(stmt).__name__
            violations.append(f"line {line}: disallowed statement in except handler body: {stmt_repr}")

    # 4. Check if changes are: (a) narrowing, (b) adding logging, or (c) best-effort marker
    type_changed = not _ast_equal(h1.type, h2.type)
    if type_changed:
        if not _is_narrowed(h1.type, h2.type, t, s):
            old_desc = ast.unparse(h1.type) if h1.type and hasattr(ast, "unparse") else ("bare except" if h1.type is None else "broad")
            new_desc = ast.unparse(h2.type) if h2.type and hasattr(ast, "unparse") else ("bare except" if h2.type is None else "broad")
            violations.append(f"line {line}: exception type was not narrowed: changed from {old_desc} to {new_desc}")

    has_added_logging = any(_is_diagnostic_or_logging(stmt, h2, t, s) for stmt in h2.body)
    is_narrowed = type_changed and _is_narrowed(h1.type, h2.type, t, s)
    best_effort_reason = _get_best_effort_reason(h2, after_code)

    if not (is_narrowed or has_added_logging or best_effort_reason):
        violations.append(
            f"line {line}: except handler edit must narrow the exception type, add safe diagnostic logging, "
            f"or add # steward: best-effort: <reason> intent marker with non-empty reason"
        )

    return violations


def _compare_nodes(
    n1: Any,
    n2: Any,
    before_code: str,
    after_code: str,
    filename: str = "",
    current_func_node: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
    path: str = "",
    trusted: dict[str, str] | None = None,
    after_tree: ast.Module | None = None,
) -> list[str]:
    if type(n1) is not type(n2):
        return [f"AST node type mismatch at {path or 'root'}: {type(n1).__name__} vs {type(n2).__name__}"]

    if isinstance(n1, (ast.FunctionDef, ast.AsyncFunctionDef)):
        current_func_node = n1

    if isinstance(n1, (list, tuple)):
        if len(n1) != len(n2):
            return [f"AST structure mismatch at {path or 'root'}: length changed from {len(n1)} to {len(n2)}"]
        violations: list[str] = []
        for idx, (item1, item2) in enumerate(zip(n1, n2)):
            violations.extend(
                _compare_nodes(item1, item2, before_code, after_code, filename, current_func_node, f"{path}[{idx}]", trusted, after_tree)
            )
        return violations

    if isinstance(n1, ast.Try):
        violations = []
        line = getattr(n2, "lineno", "?")

        # Body of every try block must be strictly identical in AST structure
        if not _ast_equal(n1.body, n2.body):
            violations.append(f"try block body was modified at line {line}")

        if not _ast_equal(n1.orelse, n2.orelse):
            violations.append(f"try block else clause was modified at line {line}")

        if not _ast_equal(n1.finalbody, n2.finalbody):
            violations.append(f"try block finally clause was modified at line {line}")

        func_name = current_func_node.name if current_func_node is not None else None
        is_escalated = is_escalated_try_block(n1, func_name, filename)

        shadowed = frozenset()
        if after_tree is not None:
            shadowed = get_shadowed_names(after_tree, current_func_node)

        if len(n1.handlers) != len(n2.handlers):
            violations.append(
                f"try block handler count changed from {len(n1.handlers)} to {len(n2.handlers)} at line {line}"
            )
        else:
            for h1, h2 in zip(n1.handlers, n2.handlers):
                violations.extend(
                    _verify_handler_edit(h1, h2, before_code, after_code, filename, func_name, trusted, shadowed, is_escalated)
                )

        return violations

    if isinstance(n1, ast.AST):
        violations = []
        for field in n1._fields:
            v1 = getattr(n1, field, None)
            v2 = getattr(n2, field, None)
            violations.extend(
                _compare_nodes(v1, v2, before_code, after_code, filename, current_func_node, f"{path}.{field}", trusted, after_tree)
            )
        return violations

    # Primitive scalar comparison (str, int, float, bool, None, etc.)
    if n1 != n2 or type(n1) is not type(n2):
        return [f"AST value mismatch at {path or 'root'}: {n1!r} != {n2!r}"]

    return []


def prove_exception_edit(before_code: str, after_code: str, filename: str = "") -> list[str]:
    """Analyze the AST and source diff of before_code and after_code for a swallowed_exception edit.

    Returns an empty list [] if valid, or a list of descriptive violation strings if invalid.
    """
    try:
        before_tree = ast.parse(before_code)
    except SyntaxError as exc:
        return [f"before_code failed to parse: SyntaxError: {exc.msg} (line {exc.lineno})"]

    try:
        after_tree = ast.parse(after_code)
    except SyntaxError as exc:
        return [f"after_code failed to parse: SyntaxError: {exc.msg} (line {exc.lineno})"]

    # 1. Source-level diff verification:
    # Ensure that all modified lines are strictly within except clauses and their bodies.
    # No comments, docstrings, imports, or statements outside except handlers may be touched.
    handler_ranges: list[tuple[int, int]] = []
    for node in ast.walk(before_tree):
        if isinstance(node, ast.ExceptHandler):
            start = node.lineno
            end = node.end_lineno if hasattr(node, "end_lineno") and node.end_lineno else start
            if node.body:
                body_end = max(getattr(s, "end_lineno", getattr(s, "lineno", start)) for s in node.body)
                end = max(end, body_end)
            handler_ranges.append((start, end))

    diff_violations: list[str] = []
    before_lines = before_code.splitlines(keepends=True)
    after_lines = after_code.splitlines(keepends=True)
    matcher = difflib.SequenceMatcher(None, before_lines, after_lines)
    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            continue
        change_start = i1 + 1
        change_end = max(i1 + 1, i2)
        in_handler = any(h_start <= change_start and change_end <= h_end for h_start, h_end in handler_ranges)
        if not in_handler:
            diff_violations.append(
                f"diff touches lines {change_start}..{change_end} which are outside any except handler "
                f"(diff must be strictly confined to except clauses and their handler bodies)"
            )

    # 2. AST structural and statement verification
    trusted = get_module_scope_provenance(after_tree)
    ast_violations = _compare_nodes(
        before_tree,
        after_tree,
        before_code,
        after_code,
        filename,
        trusted=trusted,
        after_tree=after_tree,
    )
    all_violations = diff_violations + ast_violations
    if all_violations:
        return all_violations

    # 3. Mechanical sensor verification:
    # Verify that the finding is actually eliminated on the patched file using the canonical sensor logic.
    fname = filename or "test.py"
    b_file = SourceFile(fname, before_code, before_tree, None, False)
    a_file = SourceFile(fname, after_code, after_tree, None, False)
    b_findings = swallowed_handlers(b_file)
    a_findings = swallowed_handlers(a_file)
    if b_findings and len(a_findings) >= len(b_findings):
        return ["edit did not eliminate the swallowed_exception finding in this file"]

    return []
