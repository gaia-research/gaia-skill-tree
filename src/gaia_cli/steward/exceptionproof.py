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
- Enforces mandatory triage with a POSITIVE envelope: a handler may be changed at all only
  when its try body is proven side-effect-free or diagnostic-only under a small allowlist
  (pure reads, formatting, optional imports, trusted logging; see ``try_body_envelope``),
  no value the try binds reaches an unclassified call, write or decision guard elsewhere in
  its scope, and the context is outside the known authorization, budget and overwrite
  boundaries. Anything unproven (writes, network, subprocess, state mutation, any call whose
  effect cannot be classified) escalates to engineering. The known-context denylist is an
  extra layer, never the safety argument.
- Trusts a name (a logger, ``sys``, a builtin exception) only after every lexical binding
  form in scope is analysed (``bound_names``), and proves narrowing against the real
  exception class hierarchy, never a breadth label.
"""

from __future__ import annotations

import ast
import builtins
import difflib
import importlib
import re
from typing import Any

from gaia_cli.steward.primitives.pyast import comment_map
from gaia_cli.steward.sensors_code import SourceFile, swallowed_handlers

__all__ = [
    "prove_exception_edit",
    "is_escalated_security_context",
    "is_escalated_try_block",
    "handler_escalation_reason",
    "try_body_envelope",
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


_TRUSTED_MODULES = ("sys", "json", "yaml", "subprocess", "logging", "re")
_SCOPE_NODES = (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda, ast.ClassDef,
                ast.ListComp, ast.SetComp, ast.DictComp, ast.GeneratorExp)


def _alias_bound(alias: ast.alias) -> str:
    return alias.asname or alias.name.split(".")[0]


def bound_names(node: ast.AST, *, descend: bool) -> list[str]:
    """Every name a binding form under ``node`` binds, with repeats.

    Covers assignment, augmented/annotated assignment, walrus, ``for``/``with``/
    ``except ... as``/``del`` targets, tuple and starred unpacking, every argument
    kind (positional-only, regular, ``*args``, keyword-only, ``**kwargs``), imports,
    nested ``def``/``class`` names, ``match`` capture patterns and ``global``/
    ``nonlocal`` declarations. With ``descend=False`` nested scopes contribute only
    their own name, as Python scoping does; with ``descend=True`` everything below
    counts (an over-approximation, which only ever fails closed).
    """

    names: list[str] = []

    def visit(current: ast.AST, top: bool) -> None:
        if isinstance(current, ast.Name) and isinstance(current.ctx, (ast.Store, ast.Del)):
            names.append(current.id)
        elif isinstance(current, ast.arg):
            names.append(current.arg)
        elif isinstance(current, (ast.Import, ast.ImportFrom)):
            names.extend(_alias_bound(alias) for alias in current.names)
        elif isinstance(current, (ast.Global, ast.Nonlocal)):
            names.extend(current.names)
        elif isinstance(current, ast.ExceptHandler) and current.name:
            names.append(current.name)
        elif isinstance(current, (ast.MatchAs, ast.MatchStar)) and current.name:
            names.append(current.name)
        elif isinstance(current, ast.MatchMapping) and current.rest:
            names.append(current.rest)
        if isinstance(current, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) and not top:
            names.append(current.name)
            if not descend:
                return
        elif isinstance(current, _SCOPE_NODES) and not top and not descend:
            return
        for child in ast.iter_child_nodes(current):
            visit(child, False)

    visit(node, True)
    return names


def _global_declarations(tree: ast.Module) -> set[str]:
    return {name for sub in ast.walk(tree) if isinstance(sub, ast.Global) for name in sub.names}


def get_module_scope_provenance(tree: ast.Module) -> dict[str, str]:
    """Trusted module-scope names: allowlisted imports and ``logging.getLogger`` loggers.

    A name is trusted only when its trusted binding is its ONLY binding at module
    scope (any form, anywhere at that scope) and no function declares it ``global``.
    Rejects ``sys = attacker``, ``logger = None``, a second import, ``for logger in``,
    ``with ... as logger`` and the like.
    """

    counts: dict[str, int] = {}
    for name in bound_names(tree, descend=False):
        counts[name] = counts.get(name, 0) + 1
    globals_declared = _global_declarations(tree)
    trusted: dict[str, str] = {}
    for stmt in tree.body:
        if isinstance(stmt, ast.Import):
            for alias in stmt.names:
                if alias.name in _TRUSTED_MODULES and (not alias.asname or alias.asname == alias.name):
                    trusted[alias.name] = alias.name
        elif isinstance(stmt, ast.ImportFrom):
            for alias in stmt.names:
                if stmt.module == "gaia_cli.structuredRead" and alias.name == "logDiagnostic" and alias.asname in (None, "logDiagnostic"):
                    trusted["logDiagnostic"] = "gaia_cli.structuredRead.logDiagnostic"
                elif stmt.module == "logging" and alias.name == "getLogger" and alias.asname in (None, "getLogger"):
                    trusted["getLogger"] = "logging.getLogger"
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign) and len(stmt.targets) == 1 and isinstance(stmt.targets[0], ast.Name):
            target = stmt.targets[0].id
            call = stmt.value
            if target not in ("logger", "log") or not isinstance(call, ast.Call):
                continue
            func = call.func
            if (
                isinstance(func, ast.Attribute)
                and isinstance(func.value, ast.Name)
                and trusted.get(func.value.id) == "logging"
                and func.attr == "getLogger"
            ) or (isinstance(func, ast.Name) and trusted.get(func.id) == "logging.getLogger"):
                trusted[target] = "logging.Logger"
    return {
        name: origin for name, origin in trusted.items()
        if counts.get(name, 0) == 1 and name not in globals_declared
    }


def get_shadowed_names(
    tree: ast.Module,
    func_node: ast.FunctionDef | ast.AsyncFunctionDef | None = None,
    func_chain: tuple[ast.AST, ...] = (),
) -> frozenset[str]:
    """Names that cannot be trusted as builtins or module imports inside this scope.

    The union of every binding in each enclosing function (all forms, nested blocks
    included) and every module-scope binding other than a trusted one. Untrusted
    module-scope names (bound twice, rebound, declared global) are shadowed too.
    """

    trusted = get_module_scope_provenance(tree)
    shadowed: set[str] = {name for name in bound_names(tree, descend=False) if name not in trusted}
    shadowed |= _global_declarations(tree)
    chain = tuple(func_chain) or ((func_node,) if func_node is not None else ())
    for scope in chain:
        shadowed.update(bound_names(scope, descend=True))
    return frozenset(shadowed)


def _is_valid_exception_ref(
    node: ast.expr,
    trusted: dict[str, str],
    shadowed: frozenset[str],
) -> bool:
    """Verify that an AST expression is strictly a verified, side-effect-free exception reference."""
    return _resolve_exception(node, trusted, shadowed) is not None


def _resolve_exception(node: ast.expr, trusted: dict[str, str], shadowed: frozenset[str]) -> type | None:
    """The real exception class a reference denotes, or None when it cannot be proven."""

    if isinstance(node, ast.Name):
        if node.id in _BUILTIN_EXCEPTIONS and node.id not in shadowed:
            return getattr(builtins, node.id)
        return None
    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
        mod_name = node.value.id
        if mod_name in trusted and mod_name not in shadowed:
            actual_mod = trusted[mod_name]
            if node.attr in _MODULE_EXCEPTIONS.get(actual_mod, frozenset()):
                try:
                    module = importlib.import_module(actual_mod)
                except ImportError:
                    return None
                found = getattr(module, node.attr, None)
                if isinstance(found, type) and issubclass(found, BaseException):
                    return found
    return None


def _exception_classes(node: ast.expr | None, trusted: dict[str, str], shadowed: frozenset[str]) -> list[type] | None:
    if node is None:
        return [BaseException]
    elements = node.elts if isinstance(node, ast.Tuple) else [node]
    resolved = [_resolve_exception(el, trusted, shadowed) for el in elements]
    if not elements or any(item is None for item in resolved):
        return None
    return resolved  # type: ignore[return-value]


def _exception_level(node: ast.expr | None) -> int:
    """Return breadth level (kept for callers): 2 = bare/BaseException, 1 = Exception, 0 = other."""
    if node is None:
        return 2
    elements = node.elts if isinstance(node, ast.Tuple) else [node]
    names = {el.id if isinstance(el, ast.Name) else getattr(el, "attr", None) for el in elements}
    if "BaseException" in names:
        return 2
    if "Exception" in names:
        return 1
    return 0


def _is_narrowed(
    old_type: ast.expr | None,
    new_type: ast.expr | None,
    trusted: dict[str, str],
    shadowed: frozenset[str],
) -> bool:
    """True only when the new handler catches a strict subset of what the old one caught.

    Both sides are resolved to real classes (bare except is ``BaseException``). Every
    new class must be a subclass of some old class, and some old class must no longer
    be fully covered. ``Exception`` -> ``KeyboardInterrupt`` is NOT narrowing.
    """

    if new_type is None:
        return False
    new_classes = _exception_classes(new_type, trusted, shadowed)
    old_classes = _exception_classes(old_type, trusted, shadowed)
    if not new_classes or not old_classes:
        return False
    if not all(any(issubclass(new, old) for old in old_classes) for new in new_classes):
        return False
    return not all(any(issubclass(old, new) for new in new_classes) for old in old_classes)


# --------------------------------------------------------------------------
# Positive envelope: is the guarded try body demonstrably safe to leave swallowed?
# --------------------------------------------------------------------------

# Conversions and reads only. Builtins that iterate an arbitrary iterable (list, sorted,
# sum, any, zip, ...) are excluded: iterating an unknown object can consume or mutate it.
_PURE_BUILTINS = frozenset({
    "abs", "ascii", "bool", "callable", "chr", "divmod", "float", "format", "getattr", "hasattr",
    "hash", "hex", "id", "int", "isinstance", "issubclass", "len", "oct", "ord", "range", "repr",
    "round", "slice", "str", "type",
})
_PURE_MODULE_CALLS = {
    "json": frozenset({"loads", "dumps"}),
    "yaml": frozenset({"safe_load"}),
    "re": frozenset({"compile", "match", "search", "fullmatch", "findall", "split", "sub", "escape"}),
}
# Read-only methods, allowed only on a receiver whose type is proven (see _value_kind):
# a str, a JSON value (json.loads / yaml.safe_load output and its items), or a re match.
# A method on a receiver of unknown type (``session.get(url)``, ``requests.get``) is
# never classified as pure, whatever its name.
_STR_METHODS = frozenset({
    "strip", "lstrip", "rstrip", "split", "rsplit", "splitlines", "lower", "upper", "casefold",
    "title", "startswith", "endswith", "decode", "encode", "format", "join", "replace", "partition",
    "rpartition", "count", "find", "rfind", "isdigit", "isalpha", "isalnum", "isspace",
})
_JSON_METHODS = _STR_METHODS | frozenset({"get", "keys", "values", "items", "index"})
_MATCH_METHODS = frozenset({"group", "groups", "groupdict", "start", "end", "span"})
_STR_BUILTINS = frozenset({"str", "repr", "format", "ascii", "hex", "oct", "chr"})
_STR_RETURNING = frozenset({
    "strip", "lstrip", "rstrip", "lower", "upper", "casefold", "title", "format", "join", "replace",
    "decode", "encode",
})


def _value_kind(expr: ast.AST, trusted: dict[str, str], shadowed: frozenset[str]) -> str | None:
    """``"str"``, ``"json"`` or ``"match"`` when the value's type is proven; else None."""

    if isinstance(expr, ast.Constant) and isinstance(expr.value, (str, bytes)):
        return "str"
    if isinstance(expr, ast.JoinedStr):
        return "str"
    if isinstance(expr, ast.Subscript):
        return "json" if _value_kind(expr.value, trusted, shadowed) == "json" else None
    if not isinstance(expr, ast.Call):
        return None
    func = expr.func
    if isinstance(func, ast.Name):
        return "str" if func.id in _STR_BUILTINS and func.id not in shadowed else None
    if not isinstance(func, ast.Attribute):
        return None
    if isinstance(func.value, ast.Name) and func.value.id in ("json", "yaml", "re"):
        module = func.value.id
        if trusted.get(module) != module or module in shadowed:
            return None
        if (module, func.attr) in (("json", "loads"), ("yaml", "safe_load")):
            return "json"
        if module == "re" and func.attr in ("match", "search", "fullmatch"):
            return "match"
        if (module, func.attr) in (("json", "dumps"), ("re", "escape"), ("re", "sub")):
            return "str"
        return None
    receiver = _value_kind(func.value, trusted, shadowed)
    if receiver == "json" and func.attr == "get":
        return "json"
    if receiver in ("str", "json") and func.attr in _STR_RETURNING:
        return "str"
    if receiver == "match" and func.attr == "group":
        return "str"
    return None


def _logging_call(call: ast.Call, trusted: dict[str, str], shadowed: frozenset[str]) -> bool:
    func = call.func
    if isinstance(func, ast.Name) and func.id == "logDiagnostic":
        return trusted.get("logDiagnostic") == "gaia_cli.structuredRead.logDiagnostic" and "logDiagnostic" not in shadowed
    if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
        name = func.value.id
        return (
            name in _SAFE_LOG_NAMES and func.attr in _SAFE_LOG_METHODS
            and trusted.get(name) == "logging.Logger" and name not in shadowed
        )
    if (
        isinstance(func, ast.Attribute) and isinstance(func.value, ast.Attribute)
        and isinstance(func.value.value, ast.Name) and func.value.value.id == "sys"
        and func.value.attr in ("stderr", "stdout") and func.attr == "write"
    ):
        return trusted.get("sys") == "sys" and "sys" not in shadowed
    return False


def _pure_call(call: ast.Call, trusted: dict[str, str], shadowed: frozenset[str]) -> bool:
    func = call.func
    if isinstance(func, ast.Name):
        return func.id in _PURE_BUILTINS and func.id not in shadowed
    if isinstance(func, ast.Attribute):
        if isinstance(func.value, ast.Name) and func.value.id in _PURE_MODULE_CALLS:
            module = func.value.id
            return trusted.get(module) == module and module not in shadowed and func.attr in _PURE_MODULE_CALLS[module]
        receiver = _value_kind(func.value, trusted, shadowed)
        allowed = {"str": _STR_METHODS, "json": _JSON_METHODS, "match": _MATCH_METHODS}.get(receiver or "", frozenset())
        return func.attr in allowed
    return False


def _unsafe_expr(expr: ast.AST | None, trusted: dict[str, str], shadowed: frozenset[str]) -> str | None:
    """None when ``expr`` is a pure read or formatting; otherwise why not."""

    if expr is None:
        return None
    if isinstance(expr, (ast.Constant, ast.Name)):
        return None if not isinstance(expr, ast.Name) or isinstance(expr.ctx, ast.Load) else "name store"
    if isinstance(expr, ast.Call):
        if not (_pure_call(expr, trusted, shadowed) or _logging_call(expr, trusted, shadowed)):
            return f"call {ast.unparse(expr.func)[:60]} has an effect that cannot be classified"
        receiver = expr.func.value if isinstance(expr.func, ast.Attribute) else None
        parts = [receiver, *expr.args, *(kw.value for kw in expr.keywords)]
        return next((why for why in (_unsafe_expr(part, trusted, shadowed) for part in parts) if why), None)
    if isinstance(expr, (ast.Attribute, ast.Subscript, ast.Starred)):
        if not isinstance(getattr(expr, "ctx", ast.Load()), ast.Load):
            return "attribute or item store"
        parts = [expr.value] + ([expr.slice] if isinstance(expr, ast.Subscript) else [])
        return next((why for why in (_unsafe_expr(part, trusted, shadowed) for part in parts) if why), None)
    if isinstance(expr, (ast.BinOp, ast.UnaryOp, ast.BoolOp, ast.Compare, ast.IfExp, ast.JoinedStr,
                         ast.FormattedValue, ast.Tuple, ast.List, ast.Set, ast.Dict, ast.Slice)):
        for child in ast.iter_child_nodes(expr):
            if isinstance(child, (ast.expr_context, ast.operator, ast.unaryop, ast.boolop, ast.cmpop)):
                continue
            why = _unsafe_expr(child, trusted, shadowed)
            if why:
                return why
        return None
    return f"expression {type(expr).__name__} is not in the pure-read allowlist"


def _unsafe_stmt(stmt: ast.stmt, trusted: dict[str, str], shadowed: frozenset[str]) -> str | None:
    if isinstance(stmt, ast.Pass) or (isinstance(stmt, ast.Expr) and isinstance(stmt.value, ast.Constant)):
        return None
    if isinstance(stmt, (ast.Import, ast.ImportFrom)):
        return None  # an optional import
    if isinstance(stmt, ast.Expr):
        if isinstance(stmt.value, ast.Call) and _logging_call(stmt.value, trusted, shadowed):
            return next((w for w in (_unsafe_expr(a, trusted, shadowed) for a in [*stmt.value.args, *(k.value for k in stmt.value.keywords)]) if w), None)
        return _unsafe_expr(stmt.value, trusted, shadowed) or (
            None if isinstance(stmt.value, ast.Call) else "bare expression statement"
        )
    if isinstance(stmt, (ast.Assign, ast.AnnAssign, ast.AugAssign)):
        targets = stmt.targets if isinstance(stmt, ast.Assign) else [stmt.target]
        for target in targets:
            for node in ast.walk(target):
                if isinstance(node, (ast.Attribute, ast.Subscript)):
                    return f"assignment to {ast.unparse(target)[:60]} mutates state"
        return _unsafe_expr(stmt.value, trusted, shadowed)
    if isinstance(stmt, ast.Return):
        return _unsafe_expr(stmt.value, trusted, shadowed)
    if isinstance(stmt, ast.If):
        return _unsafe_expr(stmt.test, trusted, shadowed) or next(
            (w for w in (_unsafe_stmt(s, trusted, shadowed) for s in [*stmt.body, *stmt.orelse]) if w), None
        )
    return f"statement {type(stmt).__name__} is not in the side-effect-free allowlist"


def _walk_outside(scope: ast.AST, excluded: ast.AST):
    stack = [scope]
    while stack:
        node = stack.pop()
        if node is excluded:
            continue
        yield node
        stack.extend(ast.iter_child_nodes(node))


def try_body_envelope(
    try_node: ast.Try,
    scope: ast.AST,
    trusted: dict[str, str],
    shadowed: frozenset[str],
) -> str | None:
    """None when the try body is proven side-effect-free or diagnostic-only; else why not.

    Allowlist only: ``pass``, docstrings, optional imports, assignments to plain local
    names, ``return`` and ``if`` over pure expressions, and trusted logging. A pure
    expression is a constant, name, attribute or item read, operator, comparison,
    f-string, literal container, or a call to a pure builtin, a pure ``json``/``yaml``/
    ``re`` function (trusted import) or a conventionally read-only method. Anything
    else - writes, network, subprocess, state mutation, ``with``/loops, any call whose
    effect cannot be classified - is unproven and escalates.

    It also refuses when a name the try binds (or a ``global``/``nonlocal`` name it
    touches) reaches, anywhere else in ``scope``, an unclassified call, an attribute or
    item store, or the test of a branch that performs one: the swallowed default would
    then feed a mutation or decision.
    """

    for stmt in try_node.body:
        why = _unsafe_stmt(stmt, trusted, shadowed)
        if why:
            return f"try body is not proven side-effect-free: {why}"
    # ``else`` runs only when the body succeeded and ``finally`` always: an effect there
    # is silently skipped or reordered by the swallow, so they must be proven too.
    for label, block in (("else", try_node.orelse), ("finally", try_node.finalbody)):
        for stmt in block:
            why = _unsafe_stmt(stmt, trusted, shadowed)
            if why:
                return f"try {label} clause is not proven side-effect-free: {why}"
    bound = set(bound_names(ast.Module(body=list(try_node.body), type_ignores=[]), descend=False))
    declared = {n for sub in ast.walk(scope) if isinstance(sub, (ast.Global, ast.Nonlocal)) for n in sub.names}
    if bound & declared:
        return f"try body assigns global/nonlocal name(s) {sorted(bound & declared)}"
    if not bound:
        return None

    def uses(node: ast.AST) -> bool:
        return any(isinstance(n, ast.Name) and n.id in bound and isinstance(n.ctx, ast.Load) for n in ast.walk(node))

    for node in _walk_outside(scope, try_node):
        if isinstance(node, ast.Call) and not (_pure_call(node, trusted, shadowed) or _logging_call(node, trusted, shadowed)) and uses(node):
            return f"a value bound in the try reaches the unclassified call {ast.unparse(node.func)[:60]}"
        if isinstance(node, (ast.Assign, ast.AugAssign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            if any(isinstance(t, (ast.Attribute, ast.Subscript)) for t in targets) and (uses(node.value) if node.value else False):
                return "a value bound in the try is stored into an attribute or item"
        if isinstance(node, (ast.If, ast.While)) and uses(node.test):
            effects = [n for s in [*node.body, *node.orelse] for n in ast.walk(s)
                       if isinstance(n, ast.Call) and not (_pure_call(n, trusted, shadowed) or _logging_call(n, trusted, shadowed))]
            if effects:
                return f"a value bound in the try guards the unclassified call {ast.unparse(effects[0].func)[:60]}"
    return None


def handler_escalation_reason(tree: ast.Module, try_node: ast.Try, filename: str) -> str | None:
    """Why the handlers of ``try_node`` must be escalated instead of repaired; None when allowed."""

    chain = _enclosing_chain(tree, try_node)
    funcs = [n for n in chain if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
    func_name = funcs[-1].name if funcs else None
    if is_escalated_try_block(try_node, func_name, filename) or is_escalated_security_context(filename, func_name=func_name):
        return "handler feeds authorization, budget/spend recording, file overwrite, or mutation decisions (known context)"
    trusted = get_module_scope_provenance(tree)
    shadowed = get_shadowed_names(tree, func_chain=tuple(funcs))
    scope = funcs[-1] if funcs else tree
    return try_body_envelope(try_node, scope, trusted, shadowed)


def _enclosing_chain(tree: ast.Module, target: ast.AST) -> list[ast.AST]:
    """Function and class nodes enclosing ``target``, outermost first."""

    path: list[ast.AST] = []

    def visit(node: ast.AST, stack: list[ast.AST]) -> bool:
        if node is target:
            path.extend(stack)
            return True
        nested = stack + [node] if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)) else stack
        return any(visit(child, nested) for child in ast.iter_child_nodes(node))

    visit(tree, [])
    return path


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
    is_escalated: bool | str = False,
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
        why = is_escalated if isinstance(is_escalated, str) else (
            "handler feeds authorization, budget/spend recording, file overwrite, or mutation decisions"
        )
        return [f"line {line}: {why}; cannot be resolved autonomously (must be escalated to engineering)"]

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
    before_tree: ast.Module | None = None,
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
                _compare_nodes(item1, item2, before_code, after_code, filename, current_func_node, f"{path}[{idx}]", trusted, after_tree, before_tree)
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
        if before_tree is not None:
            is_escalated: bool | str = handler_escalation_reason(before_tree, n1, filename) or False
        else:
            is_escalated = "the try block's context could not be established"

        shadowed = frozenset()
        if after_tree is not None:
            chain = [n for n in _enclosing_chain(after_tree, n2) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            shadowed = get_shadowed_names(after_tree, func_chain=tuple(chain))

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
                _compare_nodes(v1, v2, before_code, after_code, filename, current_func_node, f"{path}.{field}", trusted, after_tree, before_tree)
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
        before_tree=before_tree,
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
