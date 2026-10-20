"""Deterministic security, mutation-boundary and browser/privacy sensors.

Three read-only sensors, one per concern:

- ``MutationBoundarySensor`` (routine 7) — the ``gaia dev`` authorization
  boundary and unsafe Python execution constructs.
- ``BrowserSinkSensor`` (routine 16) — unsafe markup/navigation sinks in
  hand-authored browser code.
- ``SecretScanSensor`` (routines 16, 14) — credential-shaped strings in tracked
  text files. A match is never stored or printed, only a short fingerprint.

All of them emit drift observations only, one per subject, and are exhaustive
over their own domain so the controller can retire debt whose condition is no
longer observed. Inventory comes from Git via ``primitives.tracked_files``.

Limitations (stated here because the findings are heuristics):

- Python checks are AST-based and structural; they do not track data flow, so
  an ``exec`` of a variable that only ever holds a trusted constant is still
  reported (confidence 0.8, not 1.0).
- Browser checks are lexical (regular expressions over source text). They see
  neither comments-in-strings nor minified control flow, and an escaper that
  exists in a file is not proven to guard a particular sink.
- The write-site analysis for ungated dev commands follows calls inside the
  handler module and a bounded number of ``gaia_cli`` import hops. It cannot
  see dynamic dispatch, so it can miss a write (false negative) and cannot
  tell scratch output from registry output beyond a path-text heuristic.
"""

from __future__ import annotations

import ast
import hashlib
import re
import tomllib
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Iterable

from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.primitives import (
    SensorUnavailable,
    finding_payload,
    git_root,
    parse_python,
    read_text_bounded,
    tracked_files,
)
from gaia_cli.steward.primitives.redact import CREDENTIAL_PATTERNS

_IMPL_PATH = "src/gaia_cli/impl.py"
_DEV_COMMAND_PATH = "src/gaia_cli/commands/dev/__init__.py"
_GATING_NAME = "MUTATING_DEV_COMMANDS"
_PYTHON_ROOTS = ("src/gaia_cli", "scripts")
_CROSS_MODULE_DEPTH = 1
_MAX_WRITE_SITES = 8


def _rel(root: Path, path: Path) -> str:
    return path.relative_to(root).as_posix()


# --------------------------------------------------------------------------
# Mutation boundary
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class _WriteSite:
    path: str
    line: int
    call: str
    scratch: bool

    def to_dict(self) -> dict[str, Any]:
        return {"path": self.path, "line": self.line, "call": self.call}


_SCRATCH_HINT = re.compile(r"generated-output|tempfile|tmp|temp|\.gaia|cache|scratch", re.IGNORECASE)

_ALWAYS_WRITE_ATTRS = frozenset({"write_text", "write_bytes", "unlink", "mkdir", "touch"})
_SHUTIL_WRITES = frozenset({"copy", "copy2", "copyfile", "copytree", "move", "rmtree"})
_OS_WRITES = frozenset(
    {"remove", "unlink", "rename", "replace", "rmdir", "removedirs", "makedirs", "mkdir"}
)


def _dotted(node: ast.AST) -> str:
    """Return ``a.b.c`` for a Name/Attribute chain, else an empty string."""

    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _mode_writes(mode: ast.AST | None) -> bool:
    if isinstance(mode, ast.Constant) and isinstance(mode.value, str):
        return any(flag in mode.value for flag in "wax+")
    return False


def _write_call(call: ast.Call) -> str | None:
    """Return a label if ``call`` is a filesystem write, else ``None``."""

    func = call.func
    positional = len(call.args)
    if isinstance(func, ast.Name):
        if func.id == "open":
            mode = call.args[1] if positional > 1 else _keyword(call, "mode")
            return "open(<write mode>)" if _mode_writes(mode) else None
        return None
    if not isinstance(func, ast.Attribute):
        return None
    attr = func.attr
    owner = _dotted(func.value)
    if owner == "json" and attr == "dump":
        sink = _dotted(call.args[1]) if positional > 1 else ""
        return None if sink in {"sys.stdout", "sys.stderr"} else "json.dump"
    if owner == "shutil" and attr in _SHUTIL_WRITES:
        return f"shutil.{attr}"
    if owner == "os" and attr in _OS_WRITES:
        return f"os.{attr}"
    if attr == "open" and owner not in {"os", "io", "tarfile", "zipfile", "webbrowser", "Image"}:
        mode = call.args[0] if positional else _keyword(call, "mode")
        return "Path.open(<write mode>)" if _mode_writes(mode) else None
    if attr in _ALWAYS_WRITE_ATTRS:
        return f".{attr}"
    # str.replace takes two arguments; Path.replace/rename take one target.
    if attr in {"rename", "replace"} and positional == 1 and not call.keywords:
        return f"Path.{attr}"
    return None


def _keyword(call: ast.Call, name: str) -> ast.AST | None:
    for keyword in call.keywords:
        if keyword.arg == name:
            return keyword.value
    return None


class _ModuleInfo:
    """Parsed Python module with its functions and import aliases."""

    def __init__(self, rel: str, tree: ast.Module) -> None:
        self.rel = rel
        self.tree = tree
        self.functions: dict[str, ast.AST] = {}
        self.imports: dict[str, tuple[str, str]] = {}
        package = rel[len("src/"):] if rel.startswith("src/") else rel
        parts = package[:-3].split("/") if package.endswith(".py") else package.split("/")
        if parts and parts[-1] == "__init__":
            parts = parts[:-1]
            self.package = ".".join(parts)
        else:
            self.package = ".".join(parts[:-1])
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                self.functions[node.name] = node
            elif isinstance(node, ast.ClassDef):
                for member in node.body:
                    if isinstance(member, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        self.functions.setdefault(member.name, member)
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom):
                module = self._absolute(node)
                for alias in node.names:
                    self.imports[alias.asname or alias.name] = (module, alias.name)

    def _absolute(self, node: ast.ImportFrom) -> str:
        if node.level == 0:
            return node.module or ""
        base = self.package.split(".") if self.package else []
        if node.level > 1:
            base = base[: len(base) - (node.level - 1)]
        return ".".join([*base, *([node.module] if node.module else [])])


class _ModuleLoader:
    def __init__(self, root: Path) -> None:
        self._root = root
        self._cache: dict[str, _ModuleInfo | None] = {}

    def load(self, dotted: str) -> _ModuleInfo | None:
        if not dotted.startswith("gaia_cli"):
            return None
        if dotted in self._cache:
            return self._cache[dotted]
        info: _ModuleInfo | None = None
        base = self._root / "src" / dotted.replace(".", "/")
        for candidate in (base.with_suffix(".py"), base / "__init__.py"):
            if candidate.is_file():
                tree, error = parse_python(candidate)
                if tree is not None and error is None:
                    info = _ModuleInfo(_rel(self._root, candidate), tree)
                break
        self._cache[dotted] = info
        return info


def _function_write_sites(module: _ModuleInfo, function: ast.AST) -> list[_WriteSite]:
    sites: list[_WriteSite] = []
    for node in ast.walk(function):
        if not isinstance(node, ast.Call):
            continue
        label = _write_call(node)
        if label is None:
            continue
        scratch = bool(_SCRATCH_HINT.search(ast.unparse(node)[:240]))
        sites.append(_WriteSite(module.rel, node.lineno, label, scratch))
    return sites


def _reachable_write_sites(
    loader: _ModuleLoader, module: _ModuleInfo, function_name: str | None
) -> list[_WriteSite]:
    """Collect write sites in a handler and what it calls (bounded)."""

    if function_name is None or function_name not in module.functions:
        entries: list[tuple[_ModuleInfo, ast.AST, int]] = [(module, module.tree, 0)]
    else:
        entries = [(module, module.functions[function_name], 0)]
    seen: set[tuple[str, int]] = set()
    sites: list[_WriteSite] = []
    index = 0
    while index < len(entries):
        current, body, depth = entries[index]
        index += 1
        key = (current.rel, getattr(body, "lineno", 0))
        if key in seen:
            continue
        seen.add(key)
        sites.extend(_function_write_sites(current, body))
        for node in ast.walk(body):
            if not isinstance(node, ast.Call):
                continue
            callee: tuple[_ModuleInfo, ast.AST, int] | None = None
            if isinstance(node.func, ast.Name):
                name = node.func.id
                if name in current.functions:
                    callee = (current, current.functions[name], depth)
                elif name in current.imports and depth < _CROSS_MODULE_DEPTH:
                    source, attr = current.imports[name]
                    target = loader.load(source)
                    if target is not None and attr in target.functions:
                        callee = (target, target.functions[attr], depth + 1)
            elif isinstance(node.func, ast.Attribute) and isinstance(node.func.value, ast.Name):
                alias = node.func.value.id
                if alias in current.imports and depth < _CROSS_MODULE_DEPTH:
                    source, attr = current.imports[alias]
                    target = loader.load(f"{source}.{attr}")
                    if target is not None and node.func.attr in target.functions:
                        callee = (target, target.functions[node.func.attr], depth + 1)
            if callee is not None:
                entries.append(callee)
    unique = {(site.path, site.line, site.call): site for site in sites}
    return [unique[key] for key in sorted(unique)]


def _gating_set(tree: ast.Module, rel: str) -> frozenset[str]:
    found: list[frozenset[str]] = []
    for node in ast.walk(tree):
        target: ast.AST | None = None
        value: ast.AST | None = None
        if isinstance(node, ast.Assign) and len(node.targets) == 1:
            target, value = node.targets[0], node.value
        elif isinstance(node, ast.AnnAssign) and node.value is not None:
            target, value = node.target, node.value
        if not (isinstance(target, ast.Name) and target.id == _GATING_NAME):
            continue
        if isinstance(value, ast.Call) and len(value.args) == 1:
            value = value.args[0]
        if not isinstance(value, (ast.Set, ast.List, ast.Tuple)):
            raise SensorUnavailable(f"{rel}: {_GATING_NAME} is not a static collection literal")
        names: set[str] = set()
        for element in value.elts:
            if not (isinstance(element, ast.Constant) and isinstance(element.value, str)):
                raise SensorUnavailable(f"{rel}: {_GATING_NAME} holds a non-literal element")
            names.add(element.value)
        found.append(frozenset(names))
    if not found:
        raise SensorUnavailable(f"{rel}: no {_GATING_NAME} definition was found")
    if len(found) > 1:
        raise SensorUnavailable(f"{rel}: {len(found)} {_GATING_NAME} definitions; cannot choose one")
    return found[0]


def _subparser_variable(tree: ast.Module) -> str:
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Assign)
            and len(node.targets) == 1
            and isinstance(node.targets[0], ast.Name)
            and isinstance(node.value, ast.Call)
            and isinstance(node.value.func, ast.Attribute)
            and node.value.func.attr == "add_subparsers"
            and isinstance(_keyword(node.value, "dest"), ast.Constant)
            and _keyword(node.value, "dest").value == "dev_command"  # type: ignore[union-attr]
        ):
            return node.targets[0].id
    raise SensorUnavailable(f"{_DEV_COMMAND_PATH}: no add_subparsers(dest='dev_command') registration")


def _registered_commands(tree: ast.Module) -> list[str]:
    variable = _subparser_variable(tree)
    names: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "add_parser"
            and isinstance(node.func.value, ast.Name)
            and node.func.value.id == variable
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            names.add(node.args[0].value)
    if not names:
        raise SensorUnavailable(f"{_DEV_COMMAND_PATH}: no dev subcommand registrations were found")
    return sorted(names)


def _dev_command_compare(test: ast.AST) -> str | None:
    if (
        isinstance(test, ast.Compare)
        and isinstance(test.left, ast.Name)
        and test.left.id == "dev_cmd"
        and len(test.ops) == 1
        and isinstance(test.ops[0], ast.Eq)
        and isinstance(test.comparators[0], ast.Constant)
        and isinstance(test.comparators[0].value, str)
    ):
        return test.comparators[0].value
    return None


def _dispatch_table(tree: ast.Module) -> dict[str, tuple[str, str | None]]:
    """Map dev subcommand -> (handler module, handler function) from the if/elif chain."""

    table: dict[str, tuple[str, str | None]] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        name = _dev_command_compare(node.test)
        if name is None or name in table:
            continue
        imports: dict[str, str] = {}
        for statement in node.body:
            if isinstance(statement, ast.ImportFrom) and statement.module:
                for alias in statement.names:
                    imports[alias.asname or alias.name] = statement.module
        called = [
            call.func.id
            for statement in node.body
            for call in ast.walk(statement)
            if isinstance(call, ast.Call) and isinstance(call.func, ast.Name) and call.func.id in imports
        ]
        if called:
            table[name] = (imports[called[0]], called[0])
    return table


def _conditionally_gated(tree: ast.Module) -> frozenset[str]:
    """Names gated by a guard ``if`` that calls ``require_operator`` in its body."""

    names: set[str] = set()
    for node in ast.walk(tree):
        if not isinstance(node, ast.If):
            continue
        calls_guard = any(
            isinstance(call, ast.Call) and _dotted(call.func).endswith("require_operator")
            for statement in node.body
            for call in ast.walk(statement)
        )
        if not calls_guard:
            continue
        for part in ast.walk(node.test):
            name = _dev_command_compare(part)
            if name is not None:
                names.add(name)
    return frozenset(names)


_LEGACY_MODULE = "gaia_cli.impl"
_PYPROJECT = "pyproject.toml"
_ENTRY_HOPS = 3


def _entry_points(root: Path) -> list[tuple[str, str]]:
    """Return ``(module, callable)`` for every ``[project.scripts]`` entry; empty when unknown."""

    if _PYPROJECT not in tracked_files(root, [_PYPROJECT], require_any=False):
        return []
    try:
        data = tomllib.loads(read_text_bounded(root / _PYPROJECT))
    except tomllib.TOMLDecodeError as exc:
        raise SensorUnavailable(f"{_PYPROJECT} is not valid TOML") from exc
    scripts = data.get("project", {}).get("scripts", {})
    entries: list[tuple[str, str]] = []
    if isinstance(scripts, dict):
        for target in scripts.values():
            if isinstance(target, str) and ":" in target:
                module, _, function = target.partition(":")
                entries.append((module.strip(), function.strip().split("[", 1)[0].strip()))
    return sorted(entries)


def _module_tree(root: Path, dotted: str) -> ast.Module | None:
    base = Path(*dotted.split("."))
    for candidate in (root / "src" / base.with_suffix(".py"), root / "src" / base / "__init__.py",
                      root / base.with_suffix(".py"), root / base / "__init__.py"):
        if candidate.is_file():
            tree, error = parse_python(candidate)
            return tree if error is None else None
    return None


def _calls_legacy_main(tree: ast.Module, function: str) -> bool:
    """Whether ``function`` is, or (through same-module calls) calls, the legacy ``main``."""

    legacy_aliases: set[str] = set()
    legacy_mains: set[str] = set()
    package, _, leaf = _LEGACY_MODULE.rpartition(".")
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == _LEGACY_MODULE and alias.asname:
                    legacy_aliases.add(alias.asname)
        elif isinstance(node, ast.ImportFrom) and node.level == 0:
            for alias in node.names:
                if node.module == package and alias.name == leaf:
                    legacy_aliases.add(alias.asname or alias.name)
                elif node.module == _LEGACY_MODULE and alias.name == "main":
                    legacy_mains.add(alias.asname or alias.name)
    functions = {
        node.name: node for node in tree.body if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    if function in legacy_mains and function not in functions:
        return True
    pending, seen = [function], set()
    while pending:
        name = pending.pop()
        if name in seen or name not in functions:
            continue
        seen.add(name)
        for node in ast.walk(functions[name]):
            if not isinstance(node, ast.Call):
                continue
            dotted = _dotted(node.func)
            if dotted == f"{_LEGACY_MODULE}.main" or (
                isinstance(node.func, ast.Attribute)
                and node.func.attr == "main"
                and _dotted(node.func.value) in legacy_aliases
            ):
                return True
            if isinstance(node.func, ast.Name):
                if node.func.id in legacy_mains:
                    return True
                pending.append(node.func.id)
    return False


def _legacy_dispatcher_reachable(root: Path) -> bool:
    """True when a ``[project.scripts]`` entry point runs ``gaia_cli.impl.main``.

    The legacy ``MUTATING_DEV_COMMANDS`` set only matters if its dispatcher can
    run. When every entry point routes elsewhere, the legacy module is dead code
    (the dead-code detector's concern) and comparing its set to the live gate
    would report a disagreement nobody can reach.
    """

    for module, function in _entry_points(root):
        if module == _LEGACY_MODULE:
            return True
        tree = _module_tree(root, module)
        if tree is not None and _calls_legacy_main(tree, function):
            return True
    return False


class MutationBoundarySensor:
    """Detect ungated ``gaia dev`` mutations and unsafe Python execution."""

    id = "mutation-boundary"
    debt_kinds = ("ungated_mutation", "unsafe_execution")
    routine_ids = (7,)
    resolution_scope = "exhaustive"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        observations = self._gating_observations(root, observed_at)
        observations.extend(self._execution_observations(root, observed_at))
        return observations

    # -- ungated_mutation -------------------------------------------------

    def _gating_observations(self, root: Path, observed_at: str) -> list[Observation]:
        tracked_files(root, [_DEV_COMMAND_PATH], require_any=True)
        reachable = _legacy_dispatcher_reachable(root)
        legacy_present = bool(tracked_files(root, [_IMPL_PATH], require_any=False))
        if reachable and not legacy_present:
            raise SensorUnavailable(f"{_IMPL_PATH} is an entry point's dispatcher but is not tracked")
        legacy = (
            _gating_set(self._parse_required(root / _IMPL_PATH, _IMPL_PATH), _IMPL_PATH)
            if legacy_present
            else frozenset()
        )
        dev_tree = self._parse_required(root / _DEV_COMMAND_PATH, _DEV_COMMAND_PATH)
        live = _gating_set(dev_tree, _DEV_COMMAND_PATH)
        conditional = _conditionally_gated(dev_tree)
        registered = _registered_commands(dev_tree)
        dispatch = _dispatch_table(dev_tree)

        observations: list[Observation] = []
        # The two sets are compared only when the legacy dispatcher can run.
        disagreements = [
            {"command": name, "inLive": name in live, "inLegacy": name in legacy}
            for name in sorted(live ^ legacy)
        ] if reachable else []
        if disagreements:
            observations.append(
                Observation(
                    kind="ungated_mutation",
                    subject=Subject(type="cli-surface", id="mutating-dev-commands"),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"setsAgree": True},
                    observed_state={
                        **finding_payload(disagreements),
                        "setsAgree": False,
                        "liveSet": {"path": _DEV_COMMAND_PATH, "size": len(live)},
                        "legacySet": {"path": _IMPL_PATH, "size": len(legacy)},
                    },
                    confidence=1.0,
                    provenance={
                        "check": "two MUTATING_DEV_COMMANDS definitions compared via AST",
                        "liveSet": _DEV_COMMAND_PATH,
                        "legacySet": _IMPL_PATH,
                    },
                )
            )

        loader = _ModuleLoader(root)
        unanalysed: list[str] = []
        for name in registered:
            if name in live or name in conditional:
                continue
            handler = dispatch.get(name)
            if handler is None:
                unanalysed.append(name)
                continue
            module = loader.load(handler[0])
            if module is None:
                unanalysed.append(name)
                continue
            sites = _reachable_write_sites(loader, module, handler[1])
            if not sites:
                continue
            scratch_only = all(site.scratch for site in sites)
            finding = {
                "command": name,
                "handler": f"{handler[0]}:{handler[1]}",
                "writeSiteCount": len(sites),
                "writeSites": [site.to_dict() for site in sites[:_MAX_WRITE_SITES]],
                "inLegacySet": name in legacy,
                "writesLookLikeScratch": scratch_only,
            }
            observations.append(
                Observation(
                    kind="ungated_mutation",
                    subject=Subject(type="cli-surface", id=f"dev:{name}"),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"gated": True},
                    observed_state={**finding_payload([finding]), "gated": False},
                    confidence=0.5 if scratch_only else 0.7,
                    provenance={
                        "check": "registered dev subcommand with filesystem writes absent from the live gating set",
                        "gatingSet": _DEV_COMMAND_PATH,
                        "unanalysedCommands": unanalysed,
                        "note": (
                            "writes appear to target scratch/cache paths"
                            if scratch_only
                            else "writes are reachable from the handler; target not proven to be registry state"
                        ),
                    },
                )
            )
        return observations

    @staticmethod
    def _parse_required(path: Path, rel: str) -> ast.Module:
        tree, error = parse_python(path)
        if tree is None:
            raise SensorUnavailable(f"{rel} cannot be parsed: {error}")
        return tree

    # -- unsafe_execution -------------------------------------------------

    def _execution_observations(self, root: Path, observed_at: str) -> list[Observation]:
        paths = tracked_files(root, _PYTHON_ROOTS, suffixes=(".py",))
        observations: list[Observation] = []
        syntax_errors = 0
        for rel in paths:
            tree, error = parse_python(root / rel)
            if tree is None:
                syntax_errors += 1
                continue
            findings = _UnsafeVisitor(tree).findings()
            if not findings:
                continue
            ambiguous = all(item.get("ambiguous") for item in findings)
            observations.append(
                Observation(
                    kind="unsafe_execution",
                    subject=Subject(type="source-file", id=rel),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"unsafeConstructs": 0},
                    observed_state={
                        **finding_payload(findings),
                        "patternCounts": dict(sorted(Counter(item["pattern"] for item in findings).items())),
                    },
                    confidence=0.5 if ambiguous else 0.8,
                    provenance={
                        "check": "AST scan for shell=True, eval/exec, yaml.load, pickle.load, tar extractall",
                        "filesScanned": len(paths),
                        "filesSkippedSyntaxError": syntax_errors,
                    },
                )
            )
        return observations


_SUBPROCESS_FUNCS = frozenset(
    {"run", "call", "check_call", "check_output", "Popen", "getoutput", "getstatusoutput"}
)
_SAFE_YAML_LOADERS = frozenset({"SafeLoader", "CSafeLoader", "BaseLoader"})


def _literal_command(node: ast.AST | None) -> bool:
    if node is None:
        return False
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return True
    if isinstance(node, (ast.List, ast.Tuple)):
        return all(isinstance(item, ast.Constant) for item in node.elts)
    if isinstance(node, ast.JoinedStr):
        return not any(isinstance(part, ast.FormattedValue) for part in node.values)
    return False


class _UnsafeVisitor:
    """Structural scan of one module for unsafe execution constructs."""

    def __init__(self, tree: ast.Module) -> None:
        self._tree = tree
        self._modules: dict[str, str] = {}
        self._names: dict[str, tuple[str, str]] = {}
        self._zip: set[str] = set()
        self._tar: set[str] = set()
        self._prepare()

    def _prepare(self) -> None:
        for node in ast.walk(self._tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    self._modules[alias.asname or alias.name.split(".")[0]] = alias.name.split(".")[0]
            elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
                for alias in node.names:
                    self._names[alias.asname or alias.name] = (node.module.split(".")[0], alias.name)
            elif isinstance(node, (ast.Assign, ast.withitem)):
                value = node.value if isinstance(node, ast.Assign) else node.context_expr
                targets = (
                    node.targets
                    if isinstance(node, ast.Assign)
                    else ([node.optional_vars] if node.optional_vars is not None else [])
                )
                kind = self._archive_kind(value)
                if kind is None:
                    continue
                for target in targets:
                    if isinstance(target, ast.Name):
                        (self._zip if kind == "zip" else self._tar).add(target.id)

    @staticmethod
    def _archive_kind(value: ast.AST) -> str | None:
        if not isinstance(value, ast.Call):
            return None
        name = _dotted(value.func)
        if name.endswith("ZipFile"):
            return "zip"
        if name.endswith(("tarfile.open", "TarFile", "TarFile.open")):
            return "tar"
        return None

    def _origin(self, func: ast.AST) -> tuple[str, str] | None:
        """Resolve a call target to ``(module, attribute)`` through import aliases."""

        if isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name):
            module = self._modules.get(func.value.id)
            if module is not None:
                return module, func.attr
        if isinstance(func, ast.Name) and func.id in self._names:
            return self._names[func.id]
        return None

    def findings(self) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for node in ast.walk(self._tree):
            if isinstance(node, ast.Call):
                results.extend(self._check(node))
        results.sort(key=lambda item: (item["line"], item["pattern"]))
        return results

    def _check(self, call: ast.Call) -> Iterable[dict[str, Any]]:
        origin = self._origin(call.func)
        line = call.lineno
        if origin is not None and origin[0] == "subprocess" and origin[1] in _SUBPROCESS_FUNCS:
            shell = _keyword(call, "shell")
            if isinstance(shell, ast.Constant) and shell.value is True:
                command = call.args[0] if call.args else _keyword(call, "args")
                if not _literal_command(command):
                    yield {"line": line, "pattern": "subprocess-shell-true-nonliteral"}
        if isinstance(call.func, ast.Name) and call.func.id in {"eval", "exec"} and call.args:
            argument = call.args[0]
            if not (isinstance(argument, ast.Constant) and isinstance(argument.value, str)):
                yield {"line": line, "pattern": f"{call.func.id}-nonliteral"}
        if origin is not None and origin[0] == "yaml" and origin[1] in {"load", "load_all", "unsafe_load"}:
            if origin[1] == "unsafe_load" or not self._safe_loader(call):
                yield {"line": line, "pattern": f"yaml-{origin[1]}-unsafe-loader"}
        if origin is not None and origin[0] in {"pickle", "cPickle", "_pickle"} and origin[1] in {"load", "loads"}:
            yield {"line": line, "pattern": f"pickle-{origin[1]}"}
        if isinstance(call.func, ast.Attribute) and call.func.attr == "extractall":
            if _keyword(call, "filter") is None:
                receiver = call.func.value.id if isinstance(call.func.value, ast.Name) else ""
                if receiver in self._zip:
                    return
                known_tar = receiver in self._tar
                yield {
                    "line": line,
                    "pattern": "tarfile-extractall-no-filter",
                    "ambiguous": not known_tar,
                    **({} if known_tar else {"note": "receiver type not proven to be a tar archive"}),
                }

    @staticmethod
    def _safe_loader(call: ast.Call) -> bool:
        loader = _keyword(call, "Loader") or _keyword(call, "loader")
        if loader is None and len(call.args) > 1:
            loader = call.args[1]
        if loader is None:
            return False
        terminal = _dotted(loader).split(".")[-1]
        return terminal in _SAFE_YAML_LOADERS


# --------------------------------------------------------------------------
# Browser sinks
# --------------------------------------------------------------------------

_BROWSER_EXCLUDE = (
    "docs/graph",
    "docs/api",
    "docs/og",
    "docs/u",
    "docs/okf",
    "docs/experiments",
)
_ESCAPER = re.compile(r"escape|esc[A-Z_]|sanitize|DOMPurify")
_HTML_ASSIGN = re.compile(r"\.(innerHTML|outerHTML)\s*\+?=(?!=)\s*")
_INSERT_ADJACENT = re.compile(r"\.insertAdjacentHTML\s*\(\s*[^,()]+,\s*")
_DOCUMENT_WRITE = re.compile(r"\bdocument\.write(?:ln)?\s*\(")
_EVAL = re.compile(r"(?<![\w$])eval\s*\(")
_NEW_FUNCTION = re.compile(r"\bnew\s+Function\s*\(")
_STRING_TIMER = re.compile(r"(?<![\w$.])(?:setTimeout|setInterval)\s*\(\s*[\"'`]")
_TAG = re.compile(r"<(?:a|area|form)\b[^<>]*>", re.IGNORECASE)
_ANY_TAG = re.compile(r"<(script|link|img|iframe)\b[^<>]*>", re.IGNORECASE)
_TARGET_BLANK = re.compile(r"\btarget\s*=\s*\\?[\"']?_blank", re.IGNORECASE)
_REL_NOOPENER = re.compile(r"\brel\s*=\s*\\?[\"'][^\"']*noopener", re.IGNORECASE)
_JS_TARGET_BLANK = re.compile(r"\.target\s*=\s*[\"']_blank[\"']")
_INSECURE_URL = re.compile(
    r"\b(?:src|href)\s*=\s*\\?[\"']?http://(?!(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?:[:/\"'\s>]|$))",
    re.IGNORECASE,
)
_JS_INSECURE_URL = re.compile(
    r"\.(?:src|href)\s*=\s*[\"']http://(?!(?:localhost|127\.0\.0\.1|0\.0\.0\.0|\[::1\])(?:[:/\"']|$))"
)
_COMMENT_LINE = re.compile(r"^\s*(?://|\*|/\*|<!--)")


def _pure_literal(text: str, position: int) -> bool:
    """True when the expression at ``position`` is one static string literal."""

    length = len(text)
    while position < length and text[position] in " \t\r\n":
        position += 1
    if position >= length or text[position] not in "\"'`":
        return False
    quote = text[position]
    cursor = position + 1
    while cursor < length:
        char = text[cursor]
        if char == "\\":
            cursor += 2
            continue
        if char == quote:
            break
        if quote == "`" and char == "$" and text[cursor + 1:cursor + 2] == "{":
            return False
        if quote != "`" and char == "\n":
            return False
        cursor += 1
    else:
        return False
    cursor += 1
    while cursor < length and text[cursor] in " \t":
        cursor += 1
    return cursor >= length or text[cursor] in ";\r\n})],/"


class BrowserSinkSensor:
    """Lexical scan of hand-authored browser code for unsafe sinks."""

    id = "browser-sink"
    debt_kinds = ("browser_sink_risk",)
    routine_ids = (16,)
    resolution_scope = "exhaustive"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        paths = tracked_files(root, ["docs"], suffixes=(".js", ".html"), exclude=_BROWSER_EXCLUDE)
        observations: list[Observation] = []
        for rel in paths:
            try:
                text = (root / rel).read_text(encoding="utf-8")
            except UnicodeDecodeError:
                continue
            except OSError as exc:
                raise SensorUnavailable(f"cannot read {rel}: {exc}") from exc
            findings = self._findings(text)
            if not findings:
                continue
            escaper_only = all(item.get("escaperPresent") for item in findings)
            observations.append(
                Observation(
                    kind="browser_sink_risk",
                    subject=Subject(type="source-file", id=rel),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"sinkFindings": 0},
                    observed_state={
                        **finding_payload(findings),
                        "patternCounts": dict(sorted(Counter(item["pattern"] for item in findings).items())),
                        "escaperPresent": bool(_ESCAPER.search(text)),
                    },
                    confidence=0.4 if escaper_only else 0.6,
                    provenance={
                        "check": "lexical regular-expression scan; data flow is not traced",
                        "filesScanned": len(paths),
                        "excluded": list(_BROWSER_EXCLUDE),
                    },
                )
            )
        return observations

    @staticmethod
    def _line(text: str, offset: int) -> int:
        return text.count("\n", 0, offset) + 1

    def _findings(self, text: str) -> list[dict[str, Any]]:
        lines = text.split("\n")
        escaper = bool(_ESCAPER.search(text))

        def live(offset: int) -> bool:
            return not _COMMENT_LINE.match(lines[self._line(text, offset) - 1])

        results: list[dict[str, Any]] = []

        for match in _HTML_ASSIGN.finditer(text):
            if not live(match.start()) or _pure_literal(text, match.end()):
                continue
            item: dict[str, Any] = {
                "line": self._line(text, match.start()),
                "pattern": f"{match.group(1)}-assignment",
            }
            if escaper:
                item["escaperPresent"] = True
                item["note"] = "escaper present; data-flow not proven"
            results.append(item)
        for match in _INSERT_ADJACENT.finditer(text):
            if not live(match.start()) or _pure_literal(text, match.end()):
                continue
            item = {"line": self._line(text, match.start()), "pattern": "insertAdjacentHTML"}
            if escaper:
                item["escaperPresent"] = True
                item["note"] = "escaper present; data-flow not proven"
            results.append(item)
        for pattern, label in (
            (_DOCUMENT_WRITE, "document.write"),
            (_EVAL, "eval"),
            (_NEW_FUNCTION, "new-Function"),
            (_STRING_TIMER, "timer-with-string"),
            (_JS_TARGET_BLANK, "target-blank-no-noopener"),
            (_JS_INSECURE_URL, "insecure-http-resource"),
        ):
            for match in pattern.finditer(text):
                if not live(match.start()):
                    continue
                if label == "target-blank-no-noopener" and "noopener" in text:
                    continue
                results.append({"line": self._line(text, match.start()), "pattern": label})
        for tag in _TAG.finditer(text):
            if _TARGET_BLANK.search(tag.group(0)) and not _REL_NOOPENER.search(tag.group(0)):
                if live(tag.start()):
                    results.append(
                        {"line": self._line(text, tag.start()), "pattern": "target-blank-no-noopener"}
                    )
        for tag in _ANY_TAG.finditer(text):
            if _INSECURE_URL.search(tag.group(0)) and live(tag.start()):
                results.append(
                    {"line": self._line(text, tag.start()), "pattern": "insecure-http-resource"}
                )
        unique = {(item["line"], item["pattern"]): item for item in results}
        return [unique[key] for key in sorted(unique)]


# --------------------------------------------------------------------------
# Secret scan
# --------------------------------------------------------------------------

_SECRET_MAX_BYTES = 1024 * 1024
_SECRET_MAX_FILES = 50000
_SYNTHETIC_MARKERS = re.compile(r"EXAMPLE|FAKE|dummy|xxxx|canary|placeholder|not[-_ ]?real", re.IGNORECASE)
# Hand-typed placeholders climb the alphabet or digits; a real secret does not.
_ASCENDING_RUN = re.compile(r"abcdef|ABCDEF|012345|123456|234567|345678|456789", re.IGNORECASE)

_SECRET_PATTERNS = CREDENTIAL_PATTERNS


def _synthetic_match(rel: str, matched: str, line_text: str) -> bool:
    if not rel.startswith("tests/"):
        return False
    if _SYNTHETIC_MARKERS.search(matched) or _SYNTHETIC_MARKERS.search(line_text):
        return True
    if _ASCENDING_RUN.search(matched):
        return True
    body = re.sub(r"^[A-Za-z_-]+[_-]", "", matched)
    return len(set(body)) <= 4


@dataclass
class _SecretTally:
    scanned: int = 0
    binary: int = 0
    oversize: int = 0
    synthetic: int = 0
    reasons: dict[str, int] = field(default_factory=dict)


class SecretScanSensor:
    """Find credential-shaped strings; store only a fingerprint, never the value."""

    id = "secret-scan"
    debt_kinds = ("credential_leak",)
    routine_ids = (16, 14)
    resolution_scope = "exhaustive"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        paths = tracked_files(root, ["."], max_files=_SECRET_MAX_FILES)
        tally = _SecretTally()
        per_file: list[tuple[str, list[dict[str, Any]]]] = []
        for rel in paths:
            full = root / rel
            try:
                size = full.stat().st_size
                if size > _SECRET_MAX_BYTES:
                    tally.oversize += 1
                    continue
                data = full.read_bytes()
            except OSError as exc:
                raise SensorUnavailable(f"cannot read {rel}: {exc}") from exc
            try:
                text = data.decode("utf-8")
            except UnicodeDecodeError:
                tally.binary += 1
                continue
            tally.scanned += 1
            findings = self._findings(rel, text, tally)
            if findings:
                per_file.append((rel, findings))

        summary = {
            "filesScanned": tally.scanned,
            "skippedBinary": tally.binary,
            "skippedOversize": tally.oversize,
            "skippedSyntheticTestFixture": tally.synthetic,
        }
        observations: list[Observation] = []
        for rel, findings in per_file:
            private = any(item["pattern"] == "private-key-block" for item in findings)
            observations.append(
                Observation(
                    kind="credential_leak",
                    subject=Subject(type="source-file", id=rel),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"credentialMatches": 0},
                    observed_state={
                        **finding_payload(findings),
                        "patternCounts": dict(sorted(Counter(item["pattern"] for item in findings).items())),
                    },
                    confidence=1.0 if private else 0.9,
                    provenance={
                        "check": "credential-shaped regular expressions; matches are fingerprinted, never stored",
                        **summary,
                    },
                )
            )
        return observations

    @staticmethod
    def _findings(rel: str, text: str, tally: _SecretTally) -> list[dict[str, Any]]:
        results: list[dict[str, Any]] = []
        for name, pattern in _SECRET_PATTERNS:
            for match in pattern.finditer(text):
                matched = match.group(0)
                line_start = text.rfind("\n", 0, match.start()) + 1
                line_end = text.find("\n", match.end())
                line_text = text[line_start: len(text) if line_end < 0 else line_end]
                if name == "openai-api-key" and not any(char.isdigit() for char in matched):
                    continue
                if _synthetic_match(rel, matched, line_text):
                    tally.synthetic += 1
                    continue
                results.append(
                    {
                        "line": text.count("\n", 0, match.start()) + 1,
                        "pattern": name,
                        "fingerprint": hashlib.sha256(matched.encode("utf-8")).hexdigest()[:12],
                    }
                )
        return sorted(results, key=lambda item: (item["line"], item["pattern"], item["fingerprint"]))
