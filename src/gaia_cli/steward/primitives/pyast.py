"""Pure Python-AST helpers for Steward code-analysis sensors.

Everything here is a small deterministic function over an already parsed
``ast`` tree: no filesystem access, no network, no mutation of its inputs.
Sensors own inventory and failure semantics (``primitives.files``); this module
only answers structural questions about code.

Known approximations are stated next to each function rather than hidden:
static analysis cannot see ``globals()`` tricks, ``getattr`` by string, or
runtime-built imports, so callers must treat results as candidates.
"""

from __future__ import annotations

import ast
import hashlib
import io
import tokenize
from dataclasses import dataclass
from pathlib import PurePosixPath
from typing import Iterable, Mapping

__all__ = [
    "ImportRef",
    "comment_map",
    "function_fingerprint",
    "module_imports",
    "module_name_for",
    "statement_count",
    "strongly_connected_components",
    "used_names",
]

_IMPORT_ERRORS = {"ImportError", "ModuleNotFoundError"}
_BROAD_ERRORS = {"Exception", "BaseException"}


def module_name_for(path: str) -> str | None:
    """Map a repository path to its dotted module name.

    ``src/gaia_cli/a/b.py`` -> ``gaia_cli.a.b`` (the ``src`` layout root is
    dropped), ``src/gaia_cli/a/__init__.py`` -> ``gaia_cli.a`` and
    ``scripts/x.py`` -> ``scripts.x``. Paths that cannot be imported by name
    (not ``.py``, hyphenated or otherwise non-identifier parts) return ``None``.
    """

    pure = PurePosixPath(path)
    if pure.suffix != ".py":
        return None
    parts = list(pure.parts)
    if parts and parts[0] == "src":
        parts = parts[1:]
    if not parts:
        return None
    stem = PurePosixPath(parts[-1]).stem
    parts = parts[:-1] if stem == "__init__" else [*parts[:-1], stem]
    if not parts or not all(part.isidentifier() for part in parts):
        return None
    return ".".join(parts)


@dataclass(frozen=True)
class ImportRef:
    """One import statement, resolved to an absolute target module.

    ``target`` is the module the statement names (``import a.b`` -> ``a.b``;
    ``from . import x`` inside package ``p`` -> ``p``). It is ``""`` when a
    relative import climbs above the top-level package. ``names`` are the
    ``from`` names (``("*",)`` for a star import; empty for ``import x``) and
    ``bound`` the local names the statement creates (``import a.b`` binds
    ``a``). ``reexported`` lists bound names written with the explicit
    ``x as x`` re-export idiom.
    """

    target: str
    names: tuple[str, ...]
    bound: tuple[str, ...]
    line: int
    end_line: int
    module_scope: bool
    type_checking: bool
    in_function: bool
    in_class: bool
    guarded: bool
    reexported: tuple[str, ...] = ()
    is_from: bool = False
    asnames: tuple[str, ...] = ()


def _is_type_checking(test: ast.expr) -> bool:
    if isinstance(test, ast.Name):
        return test.id == "TYPE_CHECKING"
    if isinstance(test, ast.Attribute):
        return test.attr == "TYPE_CHECKING"
    return False


def _handler_names(handler: ast.ExceptHandler) -> set[str]:
    node = handler.type
    if node is None:
        return {"<bare>"}
    elements = node.elts if isinstance(node, ast.Tuple) else [node]
    names: set[str] = set()
    for element in elements:
        if isinstance(element, ast.Name):
            names.add(element.id)
        elif isinstance(element, ast.Attribute):
            names.add(element.attr)
    return names


def _guards_import(node: ast.Try) -> bool:
    """True when a handler would absorb a failed import (feature probing)."""

    catching = _IMPORT_ERRORS | _BROAD_ERRORS | {"<bare>"}
    return any(_handler_names(handler) & catching for handler in node.handlers)


def _resolve_relative(module_name: str, is_package: bool, level: int, module: str | None) -> str:
    package = module_name if is_package else module_name.rpartition(".")[0]
    parts = package.split(".") if package else []
    climb = level - 1
    if climb > len(parts):
        return ""
    base = parts[: len(parts) - climb]
    if module:
        base = [*base, *module.split(".")]
    return ".".join(base)


def module_imports(tree: ast.AST, module_name: str, is_package: bool) -> list[ImportRef]:
    """Return every import statement in ``tree`` with resolved targets.

    Absolute and relative imports are resolved against ``module_name``
    (``is_package`` is true for ``__init__`` files, where ``.`` means the
    package itself). ``module_scope`` is true when the import executes while
    the module is loading: not inside a function or method and not inside an
    ``if TYPE_CHECKING:`` body. Class bodies do execute at load time, so they
    count as module scope for dependency purposes (``in_class`` lets a caller
    treat them differently for usage questions). Results are in source order.
    """

    refs: list[ImportRef] = []

    def add_import(node: ast.Import, fn: bool, cls: bool, tc: bool, guard: bool) -> None:
        end = node.end_lineno or node.lineno
        for alias in node.names:
            asname = alias.asname
            bound = asname or alias.name.split(".")[0]
            refs.append(
                ImportRef(
                    target=alias.name,
                    names=(),
                    bound=(bound,),
                    line=node.lineno,
                    end_line=end,
                    module_scope=not fn and not tc,
                    type_checking=tc,
                    in_function=fn,
                    in_class=cls,
                    guarded=guard,
                    reexported=(bound,) if asname is not None and asname == alias.name else (),
                    is_from=False,
                    asnames=(asname or "",),
                )
            )

    def add_from(node: ast.ImportFrom, fn: bool, cls: bool, tc: bool, guard: bool) -> None:
        end = node.end_lineno or node.lineno
        if node.level:
            target = _resolve_relative(module_name, is_package, node.level, node.module)
        else:
            target = node.module or ""
        names = tuple(alias.name for alias in node.names)
        if names == ("*",):
            bound: tuple[str, ...] = ()
            reexported: tuple[str, ...] = ()
            asnames: tuple[str, ...] = ("",)
        else:
            bound = tuple(alias.asname or alias.name for alias in node.names)
            reexported = tuple(
                alias.name for alias in node.names if alias.asname is not None and alias.asname == alias.name
            )
            asnames = tuple(alias.asname or "" for alias in node.names)
        refs.append(
            ImportRef(
                target=target,
                names=names,
                bound=bound,
                line=node.lineno,
                end_line=end,
                module_scope=not fn and not tc,
                type_checking=tc,
                in_function=fn,
                in_class=cls,
                guarded=guard,
                reexported=reexported,
                is_from=True,
                asnames=asnames,
            )
        )

    def walk(statements: Iterable[ast.stmt], fn: bool, cls: bool, tc: bool, guard: bool) -> None:
        # Imports are statements, so only statement lists are traversed;
        # expression subtrees can never contain one.
        for statement in statements:
            if isinstance(statement, ast.Import):
                add_import(statement, fn, cls, tc, guard)
            elif isinstance(statement, ast.ImportFrom):
                add_from(statement, fn, cls, tc, guard)
            elif isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                walk(statement.body, True, cls, tc, guard)
            elif isinstance(statement, ast.ClassDef):
                walk(statement.body, fn, True, tc, guard)
            elif isinstance(statement, ast.If) and _is_type_checking(statement.test):
                # Only the body is type-checking-only; ``else`` runs at runtime.
                walk(statement.body, fn, cls, True, guard)
                walk(statement.orelse, fn, cls, tc, guard)
            elif isinstance(statement, ast.Try) or type(statement).__name__ == "TryStar":
                guards = _guards_import(statement)  # type: ignore[arg-type]
                walk(statement.body, fn, cls, tc, guard or guards)  # type: ignore[attr-defined]
                for handler in statement.handlers:  # type: ignore[attr-defined]
                    walk(handler.body, fn, cls, tc, guard)
                walk(statement.orelse, fn, cls, tc, guard)  # type: ignore[attr-defined]
                walk(statement.finalbody, fn, cls, tc, guard)  # type: ignore[attr-defined]
            elif type(statement).__name__ == "Match":
                for case in statement.cases:  # type: ignore[attr-defined]
                    walk(case.body, fn, cls, tc, guard)
            else:
                for attribute in ("body", "orelse", "finalbody"):
                    nested = getattr(statement, attribute, None)
                    if isinstance(nested, list):
                        walk(nested, fn, cls, tc, guard)

    body = getattr(tree, "body", None)
    if isinstance(body, list):
        walk(body, False, False, False, False)
    refs.sort(key=lambda ref: (ref.line, ref.target, ref.names))
    return refs


def strongly_connected_components(graph: Mapping[str, Iterable[str]]) -> list[list[str]]:
    """Iterative Tarjan SCCs, deterministic.

    Nodes that only appear as edge targets are included. Members of each
    component are sorted and components are ordered by their first member, so
    the same graph always yields the same list. Singletons are returned too;
    callers filter on size.
    """

    adjacency: dict[str, list[str]] = {}
    nodes: set[str] = set(graph)
    for source, targets in graph.items():
        ordered = sorted(set(targets))
        adjacency[source] = ordered
        nodes.update(ordered)
    index: dict[str, int] = {}
    lowlink: dict[str, int] = {}
    on_stack: set[str] = set()
    stack: list[str] = []
    components: list[list[str]] = []
    counter = 0

    for root in sorted(nodes):
        if root in index:
            continue
        index[root] = lowlink[root] = counter
        counter += 1
        stack.append(root)
        on_stack.add(root)
        work: list[tuple[str, int]] = [(root, 0)]
        while work:
            node, position = work[-1]
            neighbours = adjacency.get(node, [])
            if position < len(neighbours):
                work[-1] = (node, position + 1)
                neighbour = neighbours[position]
                if neighbour not in index:
                    index[neighbour] = lowlink[neighbour] = counter
                    counter += 1
                    stack.append(neighbour)
                    on_stack.add(neighbour)
                    work.append((neighbour, 0))
                elif neighbour in on_stack:
                    lowlink[node] = min(lowlink[node], index[neighbour])
                continue
            work.pop()
            if work:
                parent = work[-1][0]
                lowlink[parent] = min(lowlink[parent], lowlink[node])
            if lowlink[node] == index[node]:
                component: list[str] = []
                while True:
                    member = stack.pop()
                    on_stack.discard(member)
                    component.append(member)
                    if member == node:
                        break
                components.append(sorted(component))
    components.sort(key=lambda members: members[0])
    return components


def _strip_docstring(body: list[ast.stmt]) -> list[ast.stmt]:
    if (
        body
        and isinstance(body[0], ast.Expr)
        and isinstance(body[0].value, ast.Constant)
        and isinstance(body[0].value.value, str)
    ):
        return body[1:]
    return body


def statement_count(node: ast.FunctionDef | ast.AsyncFunctionDef) -> int:
    """Count statements in a function body (recursively), excluding its docstring."""

    total = 0
    for statement in _strip_docstring(list(node.body)):
        for child in ast.walk(statement):
            if isinstance(child, ast.stmt):
                total += 1
    return total


_SKIPPED_FIELDS = {"type_comment", "type_params", "kind", "returns", "annotation"}


class _Normalizer:
    """Rename local identifiers by order of first appearance, then serialize."""

    def __init__(self, local_names: set[str]) -> None:
        self._locals = local_names
        self._mapping: dict[str, str] = {}

    def rename(self, name: str) -> str:
        if name not in self._locals:
            return name
        if name not in self._mapping:
            self._mapping[name] = f"_{len(self._mapping)}"
        return self._mapping[name]

    def serialize(self, node: object) -> str:
        if isinstance(node, ast.AST):
            kind = type(node).__name__
            parts: list[str] = []
            for field in node._fields:
                if field in _SKIPPED_FIELDS or field == "ctx":
                    continue
                value = getattr(node, field, None)
                if value is None or value == []:
                    continue
                if field == "body" and isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                    value = _strip_docstring(list(value)) or [ast.Pass()]
                if isinstance(value, str) and (
                    (field == "id" and isinstance(node, ast.Name))
                    or (field == "arg" and isinstance(node, ast.arg))
                    or (
                        field == "name"
                        and isinstance(node, (ast.ExceptHandler, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef))
                    )
                ):
                    parts.append(f"{field}={self.rename(value)}")
                    continue
                parts.append(f"{field}={self.serialize(value)}")
            return f"{kind}({','.join(parts)})"
        if isinstance(node, list):
            return "[" + ",".join(self.serialize(item) for item in node) + "]"
        return f"{type(node).__name__}:{node!r}"


def _local_names(node: ast.FunctionDef | ast.AsyncFunctionDef) -> set[str]:
    names: set[str] = set()
    arguments = node.args
    for argument in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]:
        names.add(argument.arg)
    if arguments.vararg:
        names.add(arguments.vararg.arg)
    if arguments.kwarg:
        names.add(arguments.kwarg.arg)
    for child in ast.walk(node):
        if isinstance(child, ast.Name) and isinstance(child.ctx, (ast.Store, ast.Del)):
            names.add(child.id)
        elif isinstance(child, ast.ExceptHandler) and child.name:
            names.add(child.name)
        elif isinstance(child, (ast.Import, ast.ImportFrom)):
            for alias in child.names:
                names.add(alias.asname or alias.name.split(".")[0])
        elif child is not node and isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(child.name)
    return names


def function_fingerprint(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    """Structural hash of a function: same shape, same fingerprint.

    The docstring is stripped, the function's own name, annotations and
    decorators are ignored, and argument/local identifiers are renamed by order
    of first appearance. Constants, called names, attribute names and global
    reads are kept, so two functions only collide when they do the same thing
    to the same things. The serialization is hand-rolled over ``_fields`` (not
    ``ast.dump``) so the digest does not drift across Python minor versions
    for unchanged code.
    """

    normalizer = _Normalizer(_local_names(node))
    arguments = node.args
    signature = (
        f"pos={len(arguments.posonlyargs) + len(arguments.args)};kwonly={len(arguments.kwonlyargs)};"
        f"vararg={arguments.vararg is not None};kwarg={arguments.kwarg is not None};"
        f"async={isinstance(node, ast.AsyncFunctionDef)}"
    )
    for argument in [*arguments.posonlyargs, *arguments.args, *arguments.kwonlyargs]:
        normalizer.rename(argument.arg)
    body = _strip_docstring(list(node.body))
    payload = signature + "|" + normalizer.serialize(body)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def _names_in_annotation_string(value: str, found: set[str], depth: int = 0) -> None:
    if depth > 3:
        return
    try:
        parsed = ast.parse(value.strip(), mode="eval")
    except (SyntaxError, ValueError):
        return
    for node in ast.walk(parsed):
        if isinstance(node, ast.Name):
            found.add(node.id)
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            _names_in_annotation_string(node.value, found, depth + 1)


def _is_all_name(node: ast.AST) -> bool:
    return isinstance(node, ast.Name) and node.id == "__all__"


def used_names(tree: ast.AST) -> set[str]:
    """Names a module reads.

    Includes every loaded ``Name`` (which covers the root of every attribute
    chain, decorators, and f-string expressions), strings listed in
    ``__all__``, and names inside string annotations such as ``"Foo"`` or
    ``Optional["Bar"]``. It is deliberately generous: a name that appears
    anywhere as a load counts as used, so callers under-report rather than
    over-report. It cannot see ``globals()[...]`` or ``getattr`` by string.
    """

    names: set[str] = set()
    export_roots: list[ast.AST] = []
    annotations: list[ast.expr] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Name):
            if isinstance(node.ctx, ast.Load):
                names.add(node.id)
        elif isinstance(node, ast.arg):
            if node.annotation is not None:
                annotations.append(node.annotation)
        elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if node.returns is not None:
                annotations.append(node.returns)
        elif isinstance(node, ast.AnnAssign):
            annotations.append(node.annotation)
            if _is_all_name(node.target) and node.value is not None:
                export_roots.append(node.value)
        elif isinstance(node, ast.Assign):
            if any(_is_all_name(target) for target in node.targets):
                export_roots.append(node.value)
        elif isinstance(node, ast.AugAssign):
            if _is_all_name(node.target):
                export_roots.append(node.value)
        elif isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Attribute) and _is_all_name(func.value):
                export_roots.extend(node.args)
    for root in export_roots:
        for node in ast.walk(root):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                names.add(node.value)
    for annotation in annotations:
        for node in ast.walk(annotation):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                _names_in_annotation_string(node.value, names)
    return names


def comment_map(text: str) -> dict[int, str]:
    """Map 1-based line number to the comment text on that line.

    Uses ``tokenize`` so ``#`` inside strings is never mistaken for a comment;
    falls back to a conservative line scan only if tokenization itself fails.
    """

    comments: dict[int, str] = {}
    try:
        for token in tokenize.generate_tokens(io.StringIO(text).readline):
            if token.type == tokenize.COMMENT:
                comments[token.start[0]] = token.string
    except (tokenize.TokenError, IndentationError, SyntaxError):
        for number, line in enumerate(text.splitlines(), start=1):
            if "#" in line:
                comments[number] = line[line.index("#") :]
    return comments
