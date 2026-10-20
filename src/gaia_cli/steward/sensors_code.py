"""Deterministic code-analysis sensors: dead code, structure, error handling.

Three read-only sensors implement Steward routines 1 to 3:

- ``DeadCodeSensor`` (routine 1): ``unused_import`` and ``orphan_module``.
- ``CodeStructureSensor`` (routine 2): ``import_cycle`` and ``code_duplication``.
- ``ErrorHandlingSensor`` (routine 3): ``swallowed_exception``.

Boundaries inherited from ``founder/ROUTINES.md``: static analysis alone never
proves code is dead, so every finding is a *candidate* carrying a confidence
below 1.0 unless it states an exact structural fact (an import cycle exists);
whether to act on a finding is a judgment these sensors do not make. Intentional
best-effort handlers are honoured through the ``steward: best-effort`` marker.

Inventory is Git's (``tracked_files``) over ``src/gaia_cli`` and ``scripts``.
Files under ``tests/`` count as *consumers* when judging usage and are never
subjects. A file with a syntax error is not fatal and no finding is invented
for it, but it is not silent either: the skipped set is exposed through
``skipped_files`` and through each sensor's ``scan_detailed``, so the
controller reports partial coverage and sweeps none of the sensor's debt while
a file stays unparsed. If every file fails to parse the scan is unavailable.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from functools import cached_property
from pathlib import Path
from typing import Any, Iterable

from gaia_cli.steward.models import Observation, SensorScan, Subject
from gaia_cli.steward.primitives import (
    SensorUnavailable,
    finding_payload,
    parse_python,
    read_text_bounded,
    tracked_files,
)
from gaia_cli.steward.primitives.redact import scrub
from gaia_cli.steward.primitives.pyast import (
    ImportRef,
    comment_map,
    function_fingerprint,
    module_imports,
    module_name_for,
    statement_count,
    strongly_connected_components,
    used_names,
)

__all__ = [
    "CodeStructureSensor",
    "DeadCodeSensor",
    "ErrorHandlingSensor",
    "skipped_files",
]

_PACKAGE_ROOT = "src/gaia_cli"
_SCRIPTS_ROOT = "scripts"
_DATA_EXCLUDE = ("src/gaia_cli/data",)
_DEFAULT_MAX_FILES = 5000
_BEST_EFFORT_MARKER = "steward: best-effort"
_ORPHAN_NOTE = "candidate — requires consumer and external-contract review"
_TEXT_SUFFIXES = {
    ".py", ".sh", ".md", ".json", ".j2", ".ts", ".js", ".mjs", ".cjs", ".html", ".txt",
    ".yaml", ".yml", ".toml", ".cfg", ".ini", ".jsonl", ".ps1", ".cmd", ".bat", "",
}


# --------------------------------------------------------------------------
# Shared corpus loading
# --------------------------------------------------------------------------


@dataclass(frozen=True)
class SourceFile:
    """One parsed tracked Python file."""

    path: str
    text: str
    tree: ast.Module
    module: str | None
    is_package: bool

    @cached_property
    def nodes(self) -> tuple[ast.AST, ...]:
        """Every AST node once, so several detectors share one traversal."""

        return tuple(ast.walk(self.tree))

    @cached_property
    def refs(self) -> list[ImportRef]:
        return module_imports(self.tree, self.module or "_unresolved", self.is_package)


@dataclass(frozen=True)
class Corpus:
    """Parsed files plus the files that could not be parsed (and why)."""

    files: tuple[SourceFile, ...]
    skipped: tuple[dict[str, str], ...] = ()


def _parse_inventory(repo_root: Path, paths: Iterable[str]) -> Corpus:
    files: list[SourceFile] = []
    skipped: list[dict[str, str]] = []
    for path in paths:
        try:
            tree, error = parse_python(repo_root / path)
        except (ValueError, RecursionError) as exc:
            tree, error = None, f"{type(exc).__name__}: {exc}"
        if tree is None:
            skipped.append({"path": path, "reason": error or "unparseable"})
            continue
        files.append(
            SourceFile(
                path=path,
                text=read_text_bounded(repo_root / path),
                tree=tree,
                module=module_name_for(path),
                is_package=path.endswith("/__init__.py"),
            )
        )
    if skipped and not files:
        raise SensorUnavailable(
            f"every one of the {len(skipped)} Python files failed to parse "
            f"(for example: {skipped[0]['reason']})"
        )
    return Corpus(files=tuple(files), skipped=tuple(skipped))


def _scan_skips(skipped: Iterable[dict[str, str]]) -> tuple[dict[str, str], ...]:
    """Corpus skips as ``SensorScan`` records (the debt subject is the file path)."""

    return tuple(
        {"subjectType": "source-file", "subjectId": item["path"], "reason": item["reason"][:200]}
        for item in sorted(skipped, key=lambda entry: entry["path"])
    )


def load_corpus(
    repo_root: Path,
    prefixes: Iterable[str] = (_PACKAGE_ROOT, _SCRIPTS_ROOT),
    *,
    exclude: Iterable[str] = _DATA_EXCLUDE,
    max_files: int = _DEFAULT_MAX_FILES,
    require_any: bool = True,
) -> Corpus:
    """Parse tracked ``.py`` files under every prefix.

    Each prefix is inventoried on its own so that one vanishing domain makes
    the sensor unavailable (blind) instead of quietly narrowing the scan.
    """

    paths: list[str] = []
    for prefix in prefixes:
        paths.extend(
            tracked_files(
                repo_root,
                [prefix],
                suffixes=[".py"],
                exclude=exclude,
                max_files=max_files,
                require_any=require_any,
            )
        )
    return _parse_inventory(repo_root, sorted(set(paths)))


def skipped_files(repo_root: Path, *, max_files: int = _DEFAULT_MAX_FILES) -> list[dict[str, str]]:
    """Files under ``src/gaia_cli`` and ``scripts`` the sensors had to skip.

    Sensors never emit findings for these; this helper is how a skip stays
    visible instead of silently shrinking coverage.
    """

    return sorted(load_corpus(repo_root, max_files=max_files).skipped, key=lambda item: item["path"])


def _observation(
    kind: str,
    subject: Subject,
    observed_at: str,
    source: str,
    current_state: dict[str, Any],
    observed_state: dict[str, Any],
    confidence: float,
    provenance: dict[str, Any],
) -> Observation:
    return Observation(
        kind=kind,
        subject=subject,
        observed_at=observed_at,
        source=source,
        status="drift",
        current_state=current_state,
        observed_state=observed_state,
        confidence=confidence,
        provenance=provenance,
    )


# --------------------------------------------------------------------------
# Routine 1: dead code
# --------------------------------------------------------------------------


def _unused_imports(file: SourceFile) -> list[dict[str, Any]]:
    """Module-level imported names a file never reads (candidates only)."""

    if file.path.endswith("/__init__.py"):
        return []  # re-export surface by convention
    candidates = [
        ref
        for ref in file.refs
        if ref.module_scope and not ref.in_class and not ref.guarded and ref.target != "__future__"
    ]
    if not candidates:
        return []
    used = used_names(file.tree)
    comments = comment_map(file.text)
    findings: list[dict[str, Any]] = []
    for ref in candidates:
        if any(
            "noqa" in comments.get(line, "").lower() or "unused-import" in comments.get(line, "")
            for line in range(ref.line, ref.end_line + 1)
        ):
            continue
        if ref.names == ("*",):
            continue
        for index, bound in enumerate(ref.bound):
            if bound in used or bound in ref.reexported:
                continue
            if ref.is_from:
                name = ref.names[index]
                alias = ref.asnames[index]
                statement = f"from {ref.target} import {name}" + (f" as {alias}" if alias else "")
            else:
                alias = ref.asnames[0]
                statement = f"import {ref.target}" + (f" as {alias}" if alias else "")
            findings.append(
                {
                    "line": ref.line,
                    "name": bound,
                    "statement": statement,
                    "sideEffectPossible": not ref.is_from,
                }
            )
    findings.sort(key=lambda item: (item["line"], item["name"]))
    return findings


_DOTTED = re.compile(r"[A-Za-z_][A-Za-z0-9_]*(?:\.[A-Za-z_][A-Za-z0-9_]*)+")
_PATHLIKE = re.compile(r"[A-Za-z0-9_@./\\-]+\.py")
_IMPORT_CALLS = {"importlib.import_module", "import_module", "__import__", "importlib.__import__"}
_DISCOVERY_CALLS = {
    "pkgutil.iter_modules", "iter_modules", "pkgutil.walk_packages", "walk_packages",
}


def _dotted_call_name(node: ast.expr) -> str:
    parts: list[str] = []
    while isinstance(node, ast.Attribute):
        parts.append(node.attr)
        node = node.value
    if isinstance(node, ast.Name):
        parts.append(node.id)
        return ".".join(reversed(parts))
    return ""


def _constant_prefix(node: ast.expr) -> str:
    """Longest literal prefix of a string-building expression, else ``""``."""

    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        first = node.values[0] if node.values else None
        if isinstance(first, ast.Constant) and isinstance(first.value, str):
            return first.value
        return ""
    if isinstance(node, ast.BinOp):
        if isinstance(node.op, ast.Add):
            return _constant_prefix(node.left)
        if isinstance(node.op, ast.Mod) and isinstance(node.left, ast.Constant) and isinstance(node.left.value, str):
            return node.left.value.split("%", 1)[0]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Attribute)
        and node.func.attr == "format"
        and isinstance(node.func.value, ast.Constant)
        and isinstance(node.func.value.value, str)
    ):
        return node.func.value.value.split("{", 1)[0]
    return ""


def _owning_package(file: SourceFile) -> str:
    if not file.module:
        return ""
    return file.module if file.is_package else file.module.rpartition(".")[0]


@dataclass
class _Dynamic:
    literal_modules: set[str] = field(default_factory=set)
    exempt_packages: dict[str, str] = field(default_factory=dict)
    # Packages whose whole subtree is reachable at runtime. ``iter_modules``
    # only lists direct children, so it is deliberately absent from this set.
    recursive: set[str] = field(default_factory=set)
    unresolved: list[str] = field(default_factory=list)


def _scan_dynamic(file: SourceFile, result: _Dynamic, in_package_root: bool) -> None:
    for node in file.nodes:
        if not isinstance(node, ast.Call):
            continue
        name = _dotted_call_name(node.func)
        if name in _IMPORT_CALLS and node.args:
            argument = node.args[0]
            if isinstance(argument, ast.Constant) and isinstance(argument.value, str):
                if not argument.value.startswith("."):
                    result.literal_modules.add(argument.value)
                continue
            prefix = _constant_prefix(argument)
            package = prefix[:-1] if prefix.endswith(".") else prefix.rpartition(".")[0]
            if package:
                result.exempt_packages.setdefault(
                    package, f"non-literal {name} with prefix {scrub(prefix)[:120]!r} ({file.path}:{node.lineno})"
                )
                result.recursive.add(package)
            elif in_package_root and _owning_package(file):
                owner = _owning_package(file)
                result.exempt_packages.setdefault(
                    owner, f"non-literal {name} without a literal prefix ({file.path}:{node.lineno})"
                )
                result.recursive.add(owner)
            else:
                result.unresolved.append(f"{file.path}:{node.lineno}")
        elif name in _DISCOVERY_CALLS:
            package = _owning_package(file)
            if package:
                result.exempt_packages.setdefault(
                    package, f"runtime module discovery via {name} ({file.path}:{node.lineno})"
                )
                if not name.endswith("iter_modules"):
                    result.recursive.add(package)


def _docstring_ids(file: SourceFile) -> set[int]:
    ids: set[int] = set()
    for node in file.nodes:
        if isinstance(node, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            body = node.body
            if (
                body
                and isinstance(body[0], ast.Expr)
                and isinstance(body[0].value, ast.Constant)
                and isinstance(body[0].value.value, str)
            ):
                ids.add(id(body[0].value))
    return ids


def _string_constants(file: SourceFile) -> list[str]:
    skip = _docstring_ids(file)
    return [
        node.value
        for node in file.nodes
        if isinstance(node, ast.Constant)
        and isinstance(node.value, str)
        and id(node) not in skip
        and len(node.value) <= 300
        and "\n" not in node.value
    ]


def _external_uses(files: Iterable[SourceFile], known: set[str]) -> dict[tuple[str, str], set[str]]:
    """Map ``(module, attribute)`` to the files that reach it from outside.

    An import that no code in its own module reads can still be a deliberate
    compatibility re-export: another file does ``from m import name``, reads
    ``m.name`` through a module alias, patches ``"pkg.m.name"``, or calls
    ``setattr(m, "name", ...)``. Those are consumers, so the import is not dead.
    """

    uses: dict[tuple[str, str], set[str]] = {}
    roots = {module.split(".")[0] for module in known}

    def note(module: str, name: str, path: str) -> None:
        uses.setdefault((module, name), set()).add(path)

    for file in files:
        aliases: dict[str, str] = {}
        for ref in file.refs:
            if ref.is_from:
                for index, name in enumerate(ref.names):
                    if name == "*":
                        continue
                    note(ref.target, name, file.path)
                    submodule = f"{ref.target}.{name}"
                    if submodule in known:
                        aliases[ref.bound[index]] = submodule
            elif ref.asnames[0]:
                aliases[ref.asnames[0]] = ref.target
        watched = set(aliases) | roots
        for node in file.nodes:
            if isinstance(node, ast.Attribute):
                parts = [node.attr]
                inner: ast.expr = node.value
                while isinstance(inner, ast.Attribute):
                    parts.append(inner.attr)
                    inner = inner.value
                if not isinstance(inner, ast.Name) or inner.id not in watched:
                    continue
                parts.append(inner.id)
                parts.reverse()
                if parts[0] in aliases:
                    parts = [*aliases[parts[0]].split("."), *parts[1:]]
                for end in range(1, len(parts)):
                    prefix = ".".join(parts[:end])
                    if prefix in known:
                        note(prefix, parts[end], file.path)
            elif isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value
                if len(value) <= 200 and _DOTTED.fullmatch(value):
                    parts = value.split(".")
                    for end in range(1, len(parts)):
                        note(".".join(parts[:end]), parts[end], file.path)
            elif isinstance(node, ast.Call) and len(node.args) >= 2:
                target, name = node.args[0], node.args[1]
                if (
                    isinstance(target, ast.Name)
                    and target.id in aliases
                    and isinstance(name, ast.Constant)
                    and isinstance(name.value, str)
                ):
                    note(aliases[target.id], name.value, file.path)
    return uses


@dataclass(frozen=True)
class DeadCodeAnalysis:
    """Structured result behind ``DeadCodeSensor.scan`` (also used by tests)."""

    unused_imports: dict[str, list[dict[str, Any]]]
    reexported_by_others: tuple[str, ...]
    orphans: dict[str, dict[str, Any]]
    exempt_packages: dict[str, str]
    exempt_modules: dict[str, str]
    unresolved_dynamic: tuple[str, ...]
    skipped: tuple[dict[str, str], ...]
    surface_count: int


class DeadCodeSensor:
    """Report unused module-level imports and candidate orphan modules."""

    id = "dead-code"
    debt_kinds = ("unused_import", "orphan_module")
    routine_ids = (1,)
    resolution_scope = "exhaustive"

    def __init__(self, *, max_files: int = _DEFAULT_MAX_FILES) -> None:
        self.max_files = max_files

    # -- analysis ----------------------------------------------------------

    def analyze(self, repo_root: Path) -> DeadCodeAnalysis:
        corpus = load_corpus(repo_root, max_files=self.max_files)
        test_paths = tracked_files(
            repo_root, ["tests"], suffixes=[".py"], max_files=self.max_files, require_any=False
        )
        tests = _parse_inventory(repo_root, test_paths)
        surfaces = self._text_surfaces(repo_root)

        unused = {
            file.path: found
            for file in corpus.files
            if (found := _unused_imports(file))
        }
        reexported: list[str] = []
        if unused:
            everything_known = {
                file.module for file in [*corpus.files, *tests.files] if file.module
            }
            uses = _external_uses([*corpus.files, *tests.files], everything_known)
            by_path = {file.path: file for file in corpus.files}
            for path in sorted(unused):
                module = by_path[path].module
                kept = []
                for found in unused[path]:
                    elsewhere = uses.get((module or "", found["name"]), set()) - {path}
                    if elsewhere:
                        reexported.append(f"{path}:{found['name']}")
                    else:
                        kept.append(found)
                if kept:
                    unused[path] = kept
                else:
                    del unused[path]

        package_files = [file for file in corpus.files if file.path.startswith(_PACKAGE_ROOT + "/")]
        known = {file.module for file in package_files if file.module}

        consumed: set[str] = set()
        dynamic = _Dynamic()
        everything = [*corpus.files, *tests.files]
        for file in everything:
            for ref in file.refs:
                if ref.target == file.module:
                    continue
                targets = []
                if ref.target:
                    targets.append(ref.target)
                for name in ref.names:
                    if name != "*" and ref.target:
                        targets.append(f"{ref.target}.{name}")
                for target in targets:
                    if target != file.module:
                        parts = target.split(".")
                        for end in range(1, len(parts) + 1):
                            consumed.add(".".join(parts[:end]))
            _scan_dynamic(file, dynamic, file.path.startswith(_PACKAGE_ROOT + "/"))
        consumed |= dynamic.literal_modules

        references = self._reference_index(surfaces, everything, known, package_files)

        exempt_modules: dict[str, str] = {}
        orphans: dict[str, dict[str, Any]] = {}
        for file in package_files:
            module = file.module
            if not module or file.path.endswith(("/__init__.py", "/__main__.py")):
                continue
            exempt_by = next(
                (
                    (package, reason)
                    for package, reason in sorted(dynamic.exempt_packages.items())
                    if module.startswith(package + ".")
                    and (package in dynamic.recursive or "." not in module[len(package) + 1 :])
                ),
                None,
            )
            if exempt_by:
                exempt_modules[module] = f"discovered dynamically: {exempt_by[1]}"
                continue
            if module in consumed:
                continue
            text_refs = sorted(references.get(module, set()) - {file.path})
            if text_refs:
                continue
            orphans[module] = {
                "path": file.path,
                "module": module,
                "importers": 0,
                "textReferences": 0,
                "note": _ORPHAN_NOTE,
            }
        return DeadCodeAnalysis(
            unused_imports=unused,
            reexported_by_others=tuple(reexported),
            orphans=orphans,
            exempt_packages=dict(sorted(dynamic.exempt_packages.items())),
            exempt_modules=dict(sorted(exempt_modules.items())),
            unresolved_dynamic=tuple(sorted(dynamic.unresolved)),
            skipped=tuple(sorted([*corpus.skipped, *tests.skipped], key=lambda item: item["path"])),
            surface_count=len(surfaces),
        )

    def _text_surfaces(self, repo_root: Path) -> dict[str, str]:
        """Non-source consumers: packaging, task runners, CI, scripts, docs."""

        required = tracked_files(repo_root, ["pyproject.toml"], max_files=self.max_files)
        optional: list[str] = []
        for spec in (
            ["Taskfile.yml", "package.json"],
            [".github/workflows"],
            [_SCRIPTS_ROOT],
            [":(glob)*.md"],
            ["docs/agents"],
        ):
            optional.extend(tracked_files(repo_root, spec, max_files=self.max_files, require_any=False))
        surfaces: dict[str, str] = {}
        for path in sorted({*required, *optional}):
            if Path(path).suffix.lower() not in _TEXT_SUFFIXES:
                continue
            surfaces[path] = read_text_bounded(repo_root / path)
        return surfaces

    @staticmethod
    def _reference_index(
        surfaces: dict[str, str],
        sources: list[SourceFile],
        known: set[str | None],
        package_files: list[SourceFile],
    ) -> dict[str, set[str]]:
        """Map module -> paths that mention its dotted name, ``-m`` form or file path."""

        by_path: dict[str, str] = {}
        for file in package_files:
            if file.module:
                by_path[file.path] = file.module
                by_path[file.path.removeprefix("src/")] = file.module
        index: dict[str, set[str]] = {}

        def scan(source: str, text: str) -> None:
            for token in _DOTTED.findall(text):
                parts = token.split(".")
                for end in range(2, len(parts) + 1):
                    name = ".".join(parts[:end])
                    if name in known:
                        index.setdefault(name, set()).add(source)
            for token in _PATHLIKE.findall(text):
                normalized = token.replace("\\", "/").lstrip("./")
                segments = normalized.split("/")
                for start in range(len(segments)):
                    module = by_path.get("/".join(segments[start:]))
                    if module:
                        index.setdefault(module, set()).add(source)

        for path, text in surfaces.items():
            scan(path, text)
        for file in sources:
            if file.path.startswith("scripts/"):
                continue  # whole file text already scanned as a surface
            scan(file.path, "\n".join(_string_constants(file)))
        return index

    # -- observations ------------------------------------------------------

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return list(self.scan_detailed(repo_root, observed_at).observations)

    def scan_detailed(self, repo_root: Path, observed_at: str) -> SensorScan:
        analysis = self.analyze(repo_root)
        observations: list[Observation] = []
        for path in sorted(analysis.unused_imports):
            findings = analysis.unused_imports[path]
            observations.append(
                _observation(
                    "unused_import",
                    Subject(type="source-file", id=path),
                    observed_at,
                    self.id,
                    {"unusedImports": 0},
                    {"path": path, **finding_payload(findings)},
                    0.8,
                    {
                        "detector": "module-scope import names vs. loaded names in the same file",
                        "caveat": (
                            "a bare `import x` may exist for its side effects, and a public module's "
                            "import may be a re-export for an external caller; "
                            "treat as a candidate, not proof"
                        ),
                        "exempt": [
                            "__init__.py", "from __future__", "__all__", "x as x re-export",
                            "try/except ImportError probes", "# noqa", "TYPE_CHECKING blocks",
                            "string annotations", "names other files import or patch from this module",
                        ],
                        "reexportedByOthersCount": len(analysis.reexported_by_others),
                    },
                )
            )
        confidence = 0.4 if analysis.unresolved_dynamic else 0.6
        for module in sorted(analysis.orphans):
            finding = analysis.orphans[module]
            observations.append(
                _observation(
                    "orphan_module",
                    Subject(type="python-module", id=module),
                    observed_at,
                    self.id,
                    {"hasConsumer": True},
                    {"path": finding["path"], **finding_payload([finding])},
                    confidence,
                    {
                        "detector": (
                            "no tracked .py importer under src/scripts/tests and no mention in "
                            "pyproject, Taskfile, package.json, workflows, scripts, root *.md, docs/agents"
                        ),
                        "note": _ORPHAN_NOTE,
                        "dynamicallyDiscoveredPackages": analysis.exempt_packages,
                        "unresolvedDynamicImports": list(analysis.unresolved_dynamic),
                        "textSurfaceCount": analysis.surface_count,
                    },
                )
            )
        return SensorScan(tuple(observations), _scan_skips(analysis.skipped))


# --------------------------------------------------------------------------
# Routine 2: architecture
# --------------------------------------------------------------------------

_CYCLE_NOTE = (
    "an import cycle exists (exact fact); whether and where to break it is a judgment "
    "about module responsibilities, not something this sensor decides"
)


def _cycle_subject_id(members: list[str]) -> str:
    shown = "|".join(members[:8])
    extra = len(members) - 8
    return f"{shown}|+{extra}" if extra > 0 else shown


class CodeStructureSensor:
    """Report import cycles (existence) and structurally duplicated functions."""

    id = "code-structure"
    debt_kinds = ("import_cycle", "code_duplication")
    routine_ids = (2,)
    resolution_scope = "exhaustive"

    def __init__(self, *, max_files: int = _DEFAULT_MAX_FILES, min_statements: int = 8) -> None:
        self.max_files = max_files
        self.min_statements = min_statements

    # -- cycles ------------------------------------------------------------

    @staticmethod
    def import_graph(files: Iterable[SourceFile]) -> tuple[dict[str, set[str]], dict[tuple[str, str], dict[str, Any]]]:
        package_files = [f for f in files if f.path.startswith(_PACKAGE_ROOT + "/") and f.module]
        known = {f.module for f in package_files}
        graph: dict[str, set[str]] = {module: set() for module in known if module}
        edges: dict[tuple[str, str], dict[str, Any]] = {}
        for file in package_files:
            source = file.module or ""
            for ref in file.refs:
                if not ref.module_scope:
                    continue
                targets: list[str] = []
                if ref.is_from:
                    modules = [f"{ref.target}.{n}" for n in ref.names if n != "*" and f"{ref.target}.{n}" in known]
                    plain = [n for n in ref.names if n == "*" or f"{ref.target}.{n}" not in known]
                    targets.extend(modules)
                    if plain and ref.target in known:
                        targets.append(ref.target)
                elif ref.target in known:
                    targets.append(ref.target)
                for target in targets:
                    if target == source:
                        continue
                    graph[source].add(target)
                    current = edges.get((source, target))
                    if current is None or ref.line < current["line"]:
                        edges[(source, target)] = {"from": source, "to": target, "line": ref.line, "guarded": ref.guarded}
        return graph, edges

    def cycles(self, files: Iterable[SourceFile]) -> list[dict[str, Any]]:
        graph, edges = self.import_graph(files)
        found: list[dict[str, Any]] = []
        for component in strongly_connected_components(graph):
            if len(component) < 2:
                continue
            members = set(component)
            inside = sorted(
                (edge for (src, dst), edge in edges.items() if src in members and dst in members),
                key=lambda item: (item["from"], item["to"]),
            )
            found.append({"members": component, "edges": inside})
        return found

    # -- duplication -------------------------------------------------------

    def duplicates(self, files: Iterable[SourceFile]) -> list[dict[str, Any]]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for file in files:
            for qualname, node in _functions(file.tree):
                count = statement_count(node)
                if count < self.min_statements:
                    continue
                groups.setdefault(function_fingerprint(node), []).append(
                    {"path": file.path, "qualname": qualname, "line": node.lineno, "statements": count}
                )
        result = []
        for fingerprint, places in groups.items():
            if len(places) < 2:
                continue
            result.append(
                {
                    "fingerprint": fingerprint,
                    "statements": max(place["statements"] for place in places),
                    "places": sorted(f"{p['path']}:{p['qualname']}:{p['line']}" for p in places),
                }
            )
        result.sort(key=lambda item: item["fingerprint"])
        return result

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return list(self.scan_detailed(repo_root, observed_at).observations)

    def scan_detailed(self, repo_root: Path, observed_at: str) -> SensorScan:
        corpus = load_corpus(repo_root, max_files=self.max_files)
        observations: list[Observation] = []
        for cycle in self.cycles(corpus.files):
            members = cycle["members"]
            observations.append(
                _observation(
                    "import_cycle",
                    Subject(type="import-cycle", id=_cycle_subject_id(members)),
                    observed_at,
                    self.id,
                    {"importCycle": False},
                    {
                        "memberCount": len(members),
                        "members": members,
                        "note": _CYCLE_NOTE,
                        **finding_payload(cycle["edges"]),
                    },
                    1.0,
                    {
                        "detector": "strongly connected components over src/gaia_cli module-scope imports",
                        "excluded": ["function-local imports", "if TYPE_CHECKING bodies"],
                        "approximation": "implicit parent-package __init__ execution is not modelled as an edge",
                    },
                )
            )
        for group in self.duplicates(corpus.files):
            places = group["places"]
            observations.append(
                _observation(
                    "code_duplication",
                    Subject(type="duplicate-structure", id=f"dup:{group['fingerprint'][:16]}"),
                    observed_at,
                    self.id,
                    {"duplicateStructure": False},
                    {
                        "occurrenceCount": len(places),
                        "statementCount": group["statements"],
                        **finding_payload(places),
                    },
                    0.7,
                    {
                        "detector": "structural function fingerprint (locals normalized, docstring stripped, constants kept)",
                        "minStatements": self.min_statements,
                        "note": "duplication is a candidate for a shared seam, not proof one is warranted",
                    },
                )
            )
        observations.sort(key=lambda item: (item.kind, item.subject.id))
        return SensorScan(tuple(observations), _scan_skips(corpus.skipped))


def _functions(tree: ast.AST) -> list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]]:
    found: list[tuple[str, ast.FunctionDef | ast.AsyncFunctionDef]] = []

    def visit(node: ast.AST, prefix: str) -> None:
        for child in ast.iter_child_nodes(node):
            if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                qualname = f"{prefix}{child.name}"
                found.append((qualname, child))
                visit(child, qualname + ".")
            elif isinstance(child, ast.ClassDef):
                visit(child, f"{prefix}{child.name}.")
            elif isinstance(child, (ast.stmt, ast.ExceptHandler)) or type(child).__name__ == "match_case":
                visit(child, prefix)

    visit(tree, "")
    return found


# --------------------------------------------------------------------------
# Routine 3: error handling
# --------------------------------------------------------------------------

_BROAD = {"Exception", "BaseException"}


def _is_broad(handler: ast.ExceptHandler) -> bool:
    node = handler.type
    if node is None:
        return True
    elements = node.elts if isinstance(node, ast.Tuple) else [node]
    for element in elements:
        if isinstance(element, ast.Name) and element.id in _BROAD:
            return True
        if isinstance(element, ast.Attribute) and element.attr in _BROAD:
            return True
    return False


def _trivial_label(statement: ast.stmt) -> str | None:
    if isinstance(statement, ast.Pass):
        return "pass"
    if isinstance(statement, ast.Continue):
        return "continue"
    if isinstance(statement, ast.Expr) and isinstance(statement.value, ast.Constant):
        if statement.value.value is Ellipsis:
            return "..."
        if isinstance(statement.value.value, str):
            return "docstring"
    if isinstance(statement, ast.Return):
        value = statement.value
        if value is None:
            return "return"
        if isinstance(value, ast.Constant) and value.value is None:
            return "return None"
    return None


def swallowed_handlers(file: SourceFile) -> list[dict[str, Any]]:
    """Broad handlers that do nothing, minus documented best-effort ones."""

    comments: dict[int, str] | None = None
    findings: list[dict[str, Any]] = []
    for node in file.nodes:
        if not isinstance(node, ast.ExceptHandler) or not _is_broad(node):
            continue
        labels = [_trivial_label(statement) for statement in node.body]
        if not node.body or any(label is None for label in labels):
            continue
        if comments is None:
            comments = comment_map(file.text)
        first = node.body[0].lineno
        if any(
            _BEST_EFFORT_MARKER in comments.get(line, "")
            for line in range(node.lineno, first + 1)
        ):
            continue
        findings.append(
            {
                "line": node.lineno,
                "handler": "except" if node.type is None else f"except {scrub(ast.unparse(node.type))[:120]}",
                "body": "; ".join(label for label in labels if label),
            }
        )
    findings.sort(key=lambda item: (item["line"], item["handler"]))
    return findings


class ErrorHandlingSensor:
    """Report broad exception handlers that silently discard the failure."""

    id = "error-handling"
    debt_kinds = ("swallowed_exception",)
    routine_ids = (3,)
    resolution_scope = "exhaustive"

    def __init__(self, *, max_files: int = _DEFAULT_MAX_FILES) -> None:
        self.max_files = max_files

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        return list(self.scan_detailed(repo_root, observed_at).observations)

    def scan_detailed(self, repo_root: Path, observed_at: str) -> SensorScan:
        corpus = load_corpus(repo_root, max_files=self.max_files)
        observations: list[Observation] = []
        for file in corpus.files:
            findings = swallowed_handlers(file)
            if not findings:
                continue
            observations.append(
                _observation(
                    "swallowed_exception",
                    Subject(type="source-file", id=file.path),
                    observed_at,
                    self.id,
                    {"swallowedExceptions": 0},
                    {"path": file.path, **finding_payload(findings)},
                    0.8,
                    {
                        "detector": "broad except handler whose whole body is pass/continue/.../docstring/bare return",
                        "intentMarker": f"# {_BEST_EFFORT_MARKER}",
                        "note": (
                            "intentional best-effort behaviour should be marked, not removed; "
                            "label degraded results honestly"
                        ),
                    },
                )
            )
        return SensorScan(tuple(observations), _scan_skips(corpus.skipped))

