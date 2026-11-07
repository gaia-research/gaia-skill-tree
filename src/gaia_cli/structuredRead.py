"""Canonical structured-file reads with an explicit failure contract (#2283).

About half of the broad ``except Exception: pass`` handlers in ``src/gaia_cli``
and ``scripts`` wrap a file, JSON or YAML read. Each call site improvised what
a missing, unreadable, undecodable or malformed file should mean, and most
chose silence. This module makes that choice explicit at every call: there is
no default mode and no catch-all.

Modes (keyword ``mode``, required):

``"required"``
    The input must exist and parse. Any failure raises :class:`InputReadError`
    with the path and the failure ``kind``. No default is accepted.
``"optional"``
    Absence is normal: a *missing* file returns the caller's explicit
    ``default`` and reports a :class:`ReadDiagnostic`. A file that exists but
    cannot be read, decoded or parsed is **not** replaced by the default: it
    raises :class:`InputReadError`, because silently treating a corrupt state
    file as empty is how later writes destroy it.
``"bestEffort"``
    For caches and display-only context: any failure returns the explicit
    ``default`` and reports a :class:`ReadDiagnostic`. Never use this for an
    input whose value feeds a write, a published artifact, a validation verdict
    or an authority decision.
``"authority"``
    Security, authorization, budget and other authority inputs fail closed:
    any failure, including absence, raises :class:`AuthorityInputError`. No
    default is accepted, so the caller cannot fall back to a permissive value.

The two defaulting modes require both ``default`` and ``onDiagnostic`` (a
callable receiving the :class:`ReadDiagnostic`), so a fallback is never silent.
Use :func:`logDiagnostic` to log, or a :class:`DiagnosticLog` to collect.

Failure ``kind`` values: ``missing``, ``unreadable`` (permission, directory,
other OS error), ``encoding`` (not valid text in the requested encoding),
``oversize``, ``malformed`` (JSON/YAML syntax, or no frontmatter fence) and
``shape`` (the parsed value is not of the ``expect`` type).

Diagnostics and error messages describe the failure; they never echo file
content.
"""

from __future__ import annotations

import copy
import json
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable, Optional

from gaia_cli.frontmatter import split_frontmatter

__all__ = [
    "AuthorityInputError",
    "DiagnosticLog",
    "InputReadError",
    "MODES",
    "ReadDiagnostic",
    "logDiagnostic",
    "readFrontmatter",
    "readJson",
    "readText",
    "readYaml",
]

MODES = ("required", "optional", "bestEffort", "authority")
DEFAULT_MAX_BYTES = 64 * 1024 * 1024
LOGGER = logging.getLogger("gaia_cli.structuredRead")


class _NoDefault:
    def __repr__(self) -> str:
        return "<no default>"


NODEFAULT: Any = _NoDefault()


@dataclass(frozen=True)
class ReadDiagnostic:
    """A structured record that a read fell back to the caller's default."""

    path: str
    kind: str
    mode: str
    detail: str

    def toDict(self) -> dict[str, str]:
        return {"path": self.path, "kind": self.kind, "mode": self.mode, "detail": self.detail}

    def __str__(self) -> str:
        return f"{self.path}: {self.kind} ({self.mode}): {self.detail}"


class InputReadError(Exception):
    """A structured input could not be used. Carries ``path`` and ``kind``."""

    def __init__(self, path: str, kind: str, detail: str, mode: str) -> None:
        self.path = path
        self.kind = kind
        self.detail = detail
        self.mode = mode
        super().__init__(f"{path}: {kind}: {detail}")


class AuthorityInputError(InputReadError):
    """An authority input could not be used; the caller must fail closed."""


class DiagnosticLog:
    """Collect diagnostics; pass an instance as ``onDiagnostic``."""

    def __init__(self) -> None:
        self.entries: list[ReadDiagnostic] = []

    def __call__(self, diagnostic: ReadDiagnostic) -> None:
        self.entries.append(diagnostic)

    def __len__(self) -> int:
        return len(self.entries)


def logDiagnostic(diagnostic: ReadDiagnostic) -> None:
    """``onDiagnostic`` sink that logs: absence at INFO, anything else at WARNING."""

    level = logging.INFO if diagnostic.kind == "missing" else logging.WARNING
    LOGGER.log(level, "%s", diagnostic)


class _Failure(Exception):
    def __init__(self, kind: str, detail: str) -> None:
        self.kind = kind
        self.detail = detail
        super().__init__(detail)


def _checkContract(mode: str, default: Any, onDiagnostic: Optional[Callable[[ReadDiagnostic], Any]]) -> None:
    if mode not in MODES:
        raise ValueError(f"mode must be one of {', '.join(MODES)}; got {mode!r}")
    if mode in ("required", "authority"):
        if default is not NODEFAULT:
            raise TypeError(f"mode {mode!r} accepts no default: a failure must raise")
        return
    if default is NODEFAULT:
        raise TypeError(f"mode {mode!r} needs an explicit default")
    if not callable(onDiagnostic):
        raise TypeError(f"mode {mode!r} needs an onDiagnostic callable: a fallback is never silent")


def _readBytes(path: Path, maxBytes: int) -> bytes:
    try:
        with open(path, "rb") as handle:
            data = handle.read(maxBytes + 1)
    except FileNotFoundError:
        raise _Failure("missing", "file does not exist") from None
    except PermissionError as exc:
        raise _Failure("unreadable", f"permission denied ({exc.strerror or 'EACCES'})") from None
    except IsADirectoryError:
        raise _Failure("unreadable", "path is a directory") from None
    except NotADirectoryError:
        raise _Failure("missing", "a parent path component is not a directory") from None
    except OSError as exc:
        raise _Failure("unreadable", f"{type(exc).__name__}: {exc.strerror or 'I/O error'}") from None
    if len(data) > maxBytes:
        raise _Failure("oversize", f"exceeds the {maxBytes}-byte read limit")
    return data


def _decode(data: bytes, encoding: str) -> str:
    try:
        text = data.decode(encoding)
    except UnicodeDecodeError as exc:
        raise _Failure("encoding", f"not valid {encoding} at byte {exc.start}") from None
    except LookupError:
        raise _Failure("encoding", f"unknown encoding {encoding!r}") from None
    return text[1:] if text.startswith("﻿") else text


def _checkShape(value: Any, expect: Optional[type | tuple[type, ...]]) -> Any:
    if expect is not None and not isinstance(value, expect):
        names = (
            ", ".join(item.__name__ for item in expect) if isinstance(expect, tuple) else expect.__name__
        )
        raise _Failure("shape", f"expected {names}, got {type(value).__name__}")
    return value


def _run(
    path: Any,
    parse: Callable[[str], Any],
    *,
    mode: str,
    default: Any,
    onDiagnostic: Optional[Callable[[ReadDiagnostic], Any]],
    expect: Optional[type | tuple[type, ...]],
    maxBytes: int,
    encoding: str,
) -> Any:
    _checkContract(mode, default, onDiagnostic)
    target = Path(path)
    shown = str(path)
    try:
        return _checkShape(parse(_decode(_readBytes(target, maxBytes), encoding)), expect)
    except _Failure as failure:
        if mode == "authority":
            raise AuthorityInputError(shown, failure.kind, failure.detail, mode) from None
        if mode == "required" or (mode == "optional" and failure.kind != "missing"):
            raise InputReadError(shown, failure.kind, failure.detail, mode) from None
        assert onDiagnostic is not None  # _checkContract guarantees it
        onDiagnostic(ReadDiagnostic(path=shown, kind=failure.kind, mode=mode, detail=failure.detail))
        return copy.deepcopy(default)


def readText(
    path: Any,
    *,
    mode: str,
    default: Any = NODEFAULT,
    onDiagnostic: Optional[Callable[[ReadDiagnostic], Any]] = None,
    maxBytes: int = DEFAULT_MAX_BYTES,
    encoding: str = "utf-8",
) -> Any:
    """Read a text file under the chosen failure ``mode`` (see the module docstring)."""

    return _run(
        path, lambda text: text, mode=mode, default=default, onDiagnostic=onDiagnostic,
        expect=None, maxBytes=maxBytes, encoding=encoding,
    )


def _parseJson(text: str) -> Any:
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise _Failure("malformed", f"invalid JSON at line {exc.lineno} column {exc.colno}: {exc.msg}") from None
    except RecursionError:
        raise _Failure("malformed", "JSON nesting too deep") from None


def readJson(
    path: Any,
    *,
    mode: str,
    default: Any = NODEFAULT,
    onDiagnostic: Optional[Callable[[ReadDiagnostic], Any]] = None,
    expect: Optional[type | tuple[type, ...]] = None,
    maxBytes: int = DEFAULT_MAX_BYTES,
    encoding: str = "utf-8",
) -> Any:
    """Read and parse a JSON file under the chosen failure ``mode``.

    ``expect`` (e.g. ``dict``) turns a parsed value of the wrong type into a
    ``shape`` failure, handled by the same mode.
    """

    return _run(
        path, _parseJson, mode=mode, default=default, onDiagnostic=onDiagnostic,
        expect=expect, maxBytes=maxBytes, encoding=encoding,
    )


def _parseYaml(text: str) -> Any:
    import yaml

    try:
        return yaml.safe_load(text)
    except yaml.YAMLError as exc:
        mark = getattr(exc, "problem_mark", None)
        where = f" at line {mark.line + 1}" if mark is not None else ""
        raise _Failure("malformed", f"invalid YAML{where}: {type(exc).__name__}") from None


def readYaml(
    path: Any,
    *,
    mode: str,
    default: Any = NODEFAULT,
    onDiagnostic: Optional[Callable[[ReadDiagnostic], Any]] = None,
    expect: Optional[type | tuple[type, ...]] = None,
    maxBytes: int = DEFAULT_MAX_BYTES,
    encoding: str = "utf-8",
) -> Any:
    """Read a YAML file with ``yaml.safe_load`` under the chosen failure ``mode``."""

    return _run(
        path, _parseYaml, mode=mode, default=default, onDiagnostic=onDiagnostic,
        expect=expect, maxBytes=maxBytes, encoding=encoding,
    )


def _parseFrontmatter(text: str) -> tuple[dict, str]:
    fence, raw, body = split_frontmatter(text)
    if not fence:
        raise _Failure("malformed", "no closed '---' frontmatter fence")
    meta = _parseYaml(raw)
    if meta is None:
        meta = {}
    if not isinstance(meta, dict):
        raise _Failure("shape", f"frontmatter is {type(meta).__name__}, not a mapping")
    return meta, body


def readFrontmatter(
    path: Any,
    *,
    mode: str,
    default: Any = NODEFAULT,
    onDiagnostic: Optional[Callable[[ReadDiagnostic], Any]] = None,
    maxBytes: int = DEFAULT_MAX_BYTES,
    encoding: str = "utf-8",
) -> Any:
    """Read a Markdown file's YAML frontmatter; returns ``(meta, body)``.

    The fence is split with :func:`gaia_cli.frontmatter.split_frontmatter`. A
    file with no fence is ``malformed``; frontmatter that is not a mapping is a
    ``shape`` failure. Both are handled by ``mode``.
    """

    return _run(
        path, _parseFrontmatter, mode=mode, default=default, onDiagnostic=onDiagnostic,
        expect=None, maxBytes=maxBytes, encoding=encoding,
    )
