"""Read the CLI's declared command surface without executing any of it.

This is the observation half of the first wired Class B sensor. It answers one
question three ways: **which top-level commands does this checkout say it has?**

Everything here is static. `discover_commands()` imports every command module,
which is right for running the CLI and wrong for observing it: a sensor that
imports the code it is auditing reports on the *installed* package rather than
the checkout in front of it, and executes arbitrary repository code to do so.
So the surface is parsed out of the source instead — an AST walk over the same
two conventions the loader relies on (`COMMAND = X()`, `COMMANDS = [X(), Y()]`)
plus the `name` literal on each command class.

The trade is deliberate. Static parsing cannot see a command name computed at
runtime; nothing in this repository computes one, and if something ever does,
this module will report it missing rather than silently agree with itself.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path


COMMANDS_PACKAGE = "src/gaia_cli/commands"
PUBLIC_SOURCE = "src/gaia_cli/impl.py"
CONTRACT_DOCUMENT = "CLAUDE.md"

# `help` has no command module: `main()` registers it on the parser directly.
# It is declared here rather than special-cased at each comparison, so the one
# genuine exception stays visible.
BUILTIN_COMMANDS = frozenset({"help"})

# Modules under the commands package that define no command.
_NON_COMMAND_MODULES = frozenset({"base", "__init__"})

_CONTRACT_LINE = re.compile(r"^Top-level \(lifecycle-oriented\):(?P<body>.*)$", re.MULTILINE)
_BACKTICKED = re.compile(r"`([a-z][a-z0-9-]*)`")

_MAX_SOURCE_BYTES = 1024 * 1024


class CliContractError(ValueError):
    """A declared CLI surface could not be read; coverage is unknown."""


def _parse(path: Path, label: str) -> ast.Module:
    try:
        raw = path.read_bytes()
    except OSError as exc:
        raise CliContractError(f"cannot read {label} at {path}: {exc}") from exc
    if len(raw) > _MAX_SOURCE_BYTES:
        raise CliContractError(f"{label} exceeds the 1 MiB safety limit: {path}")
    try:
        return ast.parse(raw.decode("utf-8"), filename=str(path))
    except (UnicodeDecodeError, SyntaxError) as exc:
        raise CliContractError(f"cannot parse {label} at {path}: {exc}") from exc


def _class_names(tree: ast.Module) -> dict[str, str]:
    """Map each command class in a module to the command name it declares."""

    names: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for statement in node.body:
            if not isinstance(statement, ast.Assign) or len(statement.targets) != 1:
                continue
            target = statement.targets[0]
            if (
                isinstance(target, ast.Name)
                and target.id == "name"
                and isinstance(statement.value, ast.Constant)
                and isinstance(statement.value.value, str)
            ):
                names[node.name] = statement.value.value
    return names


def _exported(tree: ast.Module) -> list[str]:
    """Return the class names a module exports via COMMAND or COMMANDS."""

    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id not in {"COMMAND", "COMMANDS"}:
            continue
        values = (
            node.value.elts
            if isinstance(node.value, (ast.List, ast.Tuple))
            else [node.value]
        )
        exported: list[str] = []
        for value in values:
            if isinstance(value, ast.Call) and isinstance(value.func, ast.Name):
                exported.append(value.func.id)
        return exported
    return []


def _module_sources(package: Path) -> list[tuple[str, Path]]:
    """Every module the command loader would import, in loader order."""

    sources: list[tuple[str, Path]] = []
    for entry in sorted(package.iterdir()):
        if entry.is_file() and entry.suffix == ".py" and entry.stem not in _NON_COMMAND_MODULES:
            sources.append((entry.stem, entry))
        elif entry.is_dir() and (entry / "__init__.py").is_file():
            sources.append((entry.name, entry / "__init__.py"))
    return sources


def discovered_commands(repo_root: Path) -> dict[str, str]:
    """Return `{command name: defining module}` for this checkout."""

    package = repo_root / COMMANDS_PACKAGE
    if not package.is_dir():
        raise CliContractError(f"required directory does not exist: {COMMANDS_PACKAGE}")
    result: dict[str, str] = {}
    for module_name, path in _module_sources(package):
        tree = _parse(path, "command module")
        class_names = _class_names(tree)
        for exported in _exported(tree):
            command = class_names.get(exported)
            if command is None:
                # The module exports something the loader will instantiate but
                # whose name is not a literal. Reporting it rather than
                # ignoring it is the point: an unreadable surface is drift.
                raise CliContractError(
                    f"{module_name} exports {exported} with no literal `name`; the "
                    "command surface cannot be read statically"
                )
            result[command] = module_name
    return result


def public_commands(repo_root: Path) -> tuple[str, ...]:
    """Return the help surface's declared `PUBLIC_COMMANDS` tuple."""

    path = repo_root / PUBLIC_SOURCE
    tree = _parse(path, "public command declaration")
    for node in tree.body:
        if not isinstance(node, ast.Assign) or len(node.targets) != 1:
            continue
        target = node.targets[0]
        if not isinstance(target, ast.Name) or target.id != "PUBLIC_COMMANDS":
            continue
        if not isinstance(node.value, (ast.Tuple, ast.List)):
            raise CliContractError("PUBLIC_COMMANDS must be a literal tuple or list")
        values: list[str] = []
        for element in node.value.elts:
            if not isinstance(element, ast.Constant) or not isinstance(element.value, str):
                raise CliContractError("PUBLIC_COMMANDS must contain only string literals")
            values.append(element.value)
        return tuple(values)
    raise CliContractError(f"{PUBLIC_SOURCE} declares no PUBLIC_COMMANDS")


def documented_commands(repo_root: Path) -> tuple[str, ...] | None:
    """Return the top-level commands the agent contract advertises, if it does.

    Returns ``None`` when the contract carries no such line at all. That is a
    different condition from an empty list and is reported as its own drift:
    a contract that stopped describing the CLI is not a contract that agrees
    with it.
    """

    path = repo_root / CONTRACT_DOCUMENT
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        raise CliContractError(f"cannot read {CONTRACT_DOCUMENT}: {exc}") from exc
    match = _CONTRACT_LINE.search(text)
    if match is None:
        return None
    return tuple(_BACKTICKED.findall(match.group("body")))
