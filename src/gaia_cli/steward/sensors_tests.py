"""Deterministic test-portfolio sensors (routines 4 and 5).

Three read-only sensors that look at ``tests/`` through Git's inventory and
the Python AST: portfolio hygiene (shadowed tests, unregistered markers, empty
modules), isolation risk (clock, network, home, cwd and environment leaks) and
flake detection over an optional, driver-supplied history file.
"""

from __future__ import annotations

import ast
import json
import tomllib
from pathlib import Path
from typing import Any, Iterable, Mapping

from gaia_cli.steward.models import Observation, Subject
from gaia_cli.steward.primitives.files import (
    SensorNotEvaluated,
    SensorUnavailable,
    finding_payload,
    git_root,
    parse_python,
    read_text_bounded,
    tracked_files,
)

_BUILTIN_MARKERS = frozenset(
    {"parametrize", "skip", "skipif", "xfail", "usefixtures", "filterwarnings", "timeout"}
)
_HISTORY_PATH = ".gaia/steward/inputs/test-history.json"
_HISTORY_SCHEMA = "steward-test-history-v1"
_HISTORY_LIMIT_BYTES = 8 * 1024 * 1024
_HISTORY_MAX_RUNS = 5000
_HISTORY_MAX_RESULTS = 500_000
_HISTORY_STATUSES = frozenset({"passed", "failed", "error", "skipped"})


# --------------------------------------------------------------------------
# shared helpers
# --------------------------------------------------------------------------

def _is_test_module(path: str) -> bool:
    name = path.rsplit("/", 1)[-1]
    return name.endswith(".py") and (name.startswith("test_") or name.endswith("_test.py"))


def _aliases(tree: ast.AST) -> dict[str, str]:
    """Map locally bound import names to their dotted origin."""

    table: dict[str, str] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.asname:
                    table[alias.asname] = alias.name
                else:
                    root = alias.name.split(".")[0]
                    table[root] = root
        elif isinstance(node, ast.ImportFrom) and node.module and not node.level:
            for alias in node.names:
                if alias.name != "*":
                    table[alias.asname or alias.name] = f"{node.module}.{alias.name}"
    return table


def _dotted(node: ast.AST, aliases: Mapping[str, str]) -> str | None:
    if isinstance(node, ast.Name):
        return aliases.get(node.id, node.id)
    if isinstance(node, ast.Attribute):
        base = _dotted(node.value, aliases)
        return None if base is None else f"{base}.{node.attr}"
    return None


def _observation(
    *,
    kind: str,
    subject: Subject,
    source: str,
    observed_at: str,
    findings: list[dict[str, Any]],
    confidence: float,
    provenance: Mapping[str, Any],
) -> Observation:
    return Observation(
        kind=kind,
        subject=subject,
        observed_at=observed_at,
        source=source,
        status="drift",
        current_state={"findingCount": 0},
        observed_state=finding_payload(findings),
        confidence=confidence,
        provenance=dict(provenance),
    )


def _skip_note(skipped: Mapping[str, int]) -> dict[str, int]:
    return {key: skipped[key] for key in sorted(skipped)}


def _load_trees(
    repo_root: Path, paths: Iterable[str]
) -> tuple[dict[str, ast.Module], dict[str, int]]:
    """Parse files; a bad subject is a counted skip, never a sensor crash."""

    trees: dict[str, ast.Module] = {}
    skipped: dict[str, int] = {}
    for relative in paths:
        try:
            tree, error = parse_python(repo_root / relative)
        except SensorUnavailable:
            skipped["unreadable"] = skipped.get("unreadable", 0) + 1
            continue
        if tree is None or error:
            skipped["syntax-error"] = skipped.get("syntax-error", 0) + 1
            continue
        trees[relative] = tree
    return trees, skipped


def _marker_names(entries: Iterable[Any]) -> set[str]:
    names: set[str] = set()
    for entry in entries:
        if not isinstance(entry, str):
            continue
        head = entry.split(":", 1)[0].strip()
        head = head.split("(", 1)[0].strip()
        if head:
            names.add(head)
    return names


# --------------------------------------------------------------------------
# 1. test portfolio
# --------------------------------------------------------------------------

def _scope_label(stack: tuple[str, ...]) -> str:
    return ".".join(stack) if stack else "module"


def _shadowed(tree: ast.Module) -> list[dict[str, Any]]:
    findings: list[dict[str, Any]] = []

    def visit(body: list[ast.stmt], stack: tuple[str, ...]) -> None:
        seen: dict[str, list[int]] = {}
        for statement in body:
            if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if statement.name.startswith("test"):
                    seen.setdefault(statement.name, []).append(statement.lineno)
            elif isinstance(statement, ast.ClassDef):
                if statement.name.startswith("Test") or statement.bases:
                    visit(statement.body, stack + (statement.name,))
        for name, lines in seen.items():
            if len(lines) > 1:
                findings.append({"name": name, "scope": _scope_label(stack), "lines": lines})

    visit(tree.body, ())
    return sorted(findings, key=lambda item: (item["lines"][0], item["name"], item["scope"]))


def _used_markers(tree: ast.Module) -> dict[str, list[int]]:
    aliases = _aliases(tree)
    used: dict[str, list[int]] = {}
    for node in ast.walk(tree):
        if isinstance(node, ast.Attribute) and _dotted(node.value, aliases) == "pytest.mark":
            used.setdefault(node.attr, []).append(node.lineno)
    return used


def _conftest_markers(tree: ast.Module) -> set[str]:
    found: set[str] = set()
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "addinivalue_line"
            and len(node.args) >= 2
            and isinstance(node.args[0], ast.Constant)
            and node.args[0].value == "markers"
            and isinstance(node.args[1], ast.Constant)
        ):
            found |= _marker_names([node.args[1].value])
    return found


def _module_statements(body: list[ast.stmt]) -> Iterable[ast.stmt]:
    """Yield module-level statements, descending into if/try/with blocks."""

    for statement in body:
        yield statement
        if isinstance(statement, (ast.If, ast.For, ast.While, ast.With, ast.AsyncWith)):
            yield from _module_statements(statement.body)
            yield from _module_statements(getattr(statement, "orelse", []))
        elif isinstance(statement, ast.Try):
            for block in (statement.body, statement.orelse, statement.finalbody,
                          *[h.body for h in statement.handlers]):
                yield from _module_statements(block)


def _detectable_tests(tree: ast.Module) -> tuple[int, bool]:
    """Return (static test count, dynamic-generation hint)."""

    count = 0
    dynamic = False
    for statement in _module_statements(tree.body):
        if isinstance(statement, (ast.FunctionDef, ast.AsyncFunctionDef)):
            if statement.name.startswith("test"):
                count += 1
            elif statement.name == "pytest_generate_tests":
                dynamic = True
        elif isinstance(statement, ast.ClassDef):
            if statement.name.startswith("Test") or statement.bases:
                count += sum(
                    1
                    for item in statement.body
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    and item.name.startswith("test")
                )
        elif isinstance(statement, ast.ImportFrom):
            for alias in statement.names:
                if alias.name == "*":
                    dynamic = True
                elif (alias.asname or alias.name).startswith("test"):
                    count += 1
        elif isinstance(statement, (ast.Assign, ast.AnnAssign)):
            targets = statement.targets if isinstance(statement, ast.Assign) else [statement.target]
            for target in targets:
                if isinstance(target, ast.Name) and target.id.startswith("test"):
                    count += 1
    for node in ast.walk(tree):
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id in {"globals", "exec", "setattr"}:
                dynamic = True
    return count, dynamic


class TestPortfolioSensor:
    """Report shadowed tests, unregistered markers and statically empty test modules."""

    __test__ = False  # not a pytest class despite the name
    id = "test-portfolio"
    routine_ids = (4,)
    resolution_scope = "exhaustive"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        files = tracked_files(root, ["tests"], suffixes=[".py"])
        registered = self._registered_markers(root, files)
        trees, skipped = _load_trees(root, files)
        provenance = {
            "inventory": "git ls-files tests/**/*.py",
            "filesInspected": len(trees),
            "skipped": _skip_note(skipped),
        }
        observations: list[Observation] = []
        for path in sorted(trees):
            tree = trees[path]
            subject = Subject(type="test-file", id=path)
            if _is_test_module(path):
                shadowed = _shadowed(tree)
                if shadowed:
                    observations.append(
                        _observation(
                            kind="shadowed_test", subject=subject, source=self.id,
                            observed_at=observed_at, findings=shadowed, confidence=1.0,
                            provenance=provenance,
                        )
                    )
            used = _used_markers(tree)
            unknown = [
                {"name": name, "lines": sorted(lines)}
                for name, lines in sorted(used.items())
                if name not in registered and name not in _BUILTIN_MARKERS
            ]
            if unknown:
                observations.append(
                    _observation(
                        kind="unregistered_marker", subject=subject, source=self.id,
                        observed_at=observed_at, findings=unknown, confidence=1.0,
                        provenance=provenance,
                    )
                )
            if path.rsplit("/", 1)[-1].startswith("test_"):
                count, dynamic = _detectable_tests(tree)
                if count == 0:
                    observations.append(
                        _observation(
                            kind="empty_test_module", subject=subject, source=self.id,
                            observed_at=observed_at,
                            findings=[{
                                "reason": "no statically detectable test functions or Test classes with test methods",
                                "dynamicGenerationHint": dynamic,
                            }],
                            confidence=0.5 if dynamic else 0.7,
                            provenance=provenance,
                        )
                    )
        return observations

    @staticmethod
    def _registered_markers(root: Path, test_files: list[str]) -> set[str]:
        pyproject = root / "pyproject.toml"
        if not pyproject.is_file():
            raise SensorUnavailable("pyproject.toml is required to resolve registered pytest markers")
        try:
            data = tomllib.loads(read_text_bounded(pyproject))
        except tomllib.TOMLDecodeError as exc:
            raise SensorUnavailable(f"pyproject.toml is not valid TOML: {exc}") from exc
        options = data.get("tool", {}).get("pytest", {}).get("ini_options", {})
        if not isinstance(options, dict):
            raise SensorUnavailable("pyproject.toml [tool.pytest.ini_options] is malformed")
        markers = options.get("markers", [])
        if isinstance(markers, str):
            markers = markers.splitlines()
        registered = _marker_names(markers if isinstance(markers, list) else [])
        conftests = {p for p in test_files if p.rsplit("/", 1)[-1] == "conftest.py"}
        conftests |= set(tracked_files(root, ["conftest.py"], require_any=False))
        for relative in sorted(conftests):
            try:
                tree, _ = parse_python(root / relative)
            except SensorUnavailable:
                continue
            if tree is not None:
                registered |= _conftest_markers(tree)
        return registered


# --------------------------------------------------------------------------
# 2. test isolation
# --------------------------------------------------------------------------

_NETWORK_CALLS = frozenset(
    {
        "requests.get", "requests.post", "requests.put", "requests.delete", "requests.patch",
        "requests.head", "requests.options", "requests.request",
        "urllib.request.urlopen", "socket.create_connection",
        "http.client.HTTPConnection", "http.client.HTTPSConnection",
    }
)
_MOCK_WORDS = frozenset({"monkeypatch", "mock", "patch", "Mock", "MagicMock", "responses", "respx"})
_MOCK_MODULES = frozenset({"unittest.mock", "mock", "responses", "respx", "pytest_httpserver"})
_LOOPBACK = ("localhost", "127.0.0.1", "0.0.0.0", "::1")
_WRITE_ATTRS = frozenset(
    {"write_text", "write_bytes", "mkdir", "touch", "unlink", "rmdir", "write", "rename", "replace"}
)
_WRITE_CALLS = frozenset(
    {"shutil.copy", "shutil.copy2", "shutil.copyfile", "shutil.copytree", "shutil.move",
     "shutil.rmtree", "os.remove", "os.unlink", "os.makedirs", "os.mkdir", "os.rename"}
)


def _uses_mocking(tree: ast.Module, aliases: Mapping[str, str]) -> bool:
    if any(origin in _MOCK_MODULES or origin.split(".")[0] in _MOCK_MODULES for origin in aliases.values()):
        return True
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id in _MOCK_WORDS:
            return True
        if isinstance(node, ast.Attribute) and node.attr in _MOCK_WORDS:
            return True
        if isinstance(node, ast.arg) and node.arg in _MOCK_WORDS:
            return True
    return False


def _redirects_home(tree: ast.Module) -> bool:
    for node in ast.walk(tree):
        if isinstance(node, ast.Constant) and node.value in {"HOME", "USERPROFILE"}:
            return True
        if (
            isinstance(node, ast.Call)
            and isinstance(node.func, ast.Attribute)
            and node.func.attr == "setattr"
        ):
            for arg in node.args:
                if isinstance(arg, ast.Constant) and isinstance(arg.value, str) and (
                    "home" in arg.value or "expanduser" in arg.value
                ):
                    return True
    return False


def _is_loopback(call: ast.Call) -> bool:
    if not call.args:
        return False
    first = call.args[0]
    if isinstance(first, ast.Tuple) and first.elts:
        first = first.elts[0]
    return (
        isinstance(first, ast.Constant)
        and isinstance(first.value, str)
        and any(marker in first.value for marker in _LOOPBACK)
    )


def _is_home_call(call: ast.Call, aliases: Mapping[str, str]) -> bool:
    name = _dotted(call.func, aliases)
    if name in {"pathlib.Path.home", "Path.home"}:
        return True
    if name == "os.path.expanduser":
        return bool(
            call.args and isinstance(call.args[0], ast.Constant)
            and isinstance(call.args[0].value, str) and call.args[0].value.startswith("~")
        )
    return False


def _is_write_op(call: ast.Call, aliases: Mapping[str, str]) -> bool:
    if isinstance(call.func, ast.Attribute) and call.func.attr in _WRITE_ATTRS:
        return True
    name = _dotted(call.func, aliases)
    if name in _WRITE_CALLS:
        return True
    if name in {"open", "io.open"} or (isinstance(call.func, ast.Attribute) and call.func.attr == "open"):
        mode = None
        if len(call.args) >= 2 and isinstance(call.args[1], ast.Constant):
            mode = call.args[1].value
        for keyword in call.keywords:
            if keyword.arg == "mode" and isinstance(keyword.value, ast.Constant):
                mode = keyword.value.value
        return isinstance(mode, str) and any(flag in mode for flag in "wax+")
    return False


def _walk_scope(scope: ast.AST) -> Iterable[ast.AST]:
    """Walk a scope without descending into nested function definitions."""

    stack = list(ast.iter_child_nodes(scope))
    while stack:
        node = stack.pop()
        yield node
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
            stack.extend(ast.iter_child_nodes(node))


def _isolation_findings(tree: ast.Module) -> list[dict[str, Any]]:
    aliases = _aliases(tree)
    mocked = _uses_mocking(tree, aliases)
    home_redirected = _redirects_home(tree)
    findings: list[dict[str, Any]] = []

    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            name = _dotted(node.func, aliases)
            if name == "time.sleep" and node.args:
                arg = node.args[0]
                if (
                    isinstance(arg, ast.Constant)
                    and isinstance(arg.value, (int, float))
                    and not isinstance(arg.value, bool)
                    and arg.value >= 1
                ):
                    findings.append({"line": node.lineno, "pattern": "sleep",
                                     "detail": f"time.sleep({arg.value!r}) blocks on the real clock"})
            elif name in _NETWORK_CALLS and not mocked and not _is_loopback(node):
                findings.append({"line": node.lineno, "pattern": "network",
                                 "detail": f"{name} with no monkeypatch/mock/responses/respx in the file"})
            elif name == "os.chdir":
                findings.append({"line": node.lineno, "pattern": "chdir",
                                 "detail": "os.chdir changes process-global cwd; use monkeypatch.chdir"})
            elif name == "os.environ.update":
                findings.append({"line": node.lineno, "pattern": "environ-mutation",
                                 "detail": "os.environ.update leaks past the test; use monkeypatch.setenv"})
        elif isinstance(node, (ast.Assign, ast.AugAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for target in targets:
                if isinstance(target, ast.Subscript) and _dotted(target.value, aliases) == "os.environ":
                    findings.append({"line": node.lineno, "pattern": "environ-mutation",
                                     "detail": "direct os.environ[...] assignment leaks past the test; use monkeypatch.setenv"})

    if not home_redirected:
        scopes: list[ast.AST] = [tree] + [
            n for n in ast.walk(tree) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))
        ]
        reported: set[int] = set()
        for scope in scopes:
            own = [n for n in _walk_scope(scope) if isinstance(n, ast.Call)]
            homes = [c for c in own if _is_home_call(c, aliases)]
            if homes and any(_is_write_op(c, aliases) for c in own):
                for call in homes:
                    if call.lineno not in reported:
                        reported.add(call.lineno)
                        findings.append({"line": call.lineno, "pattern": "home-write",
                                         "detail": "writes near the real home directory; redirect HOME or use tmp_path"})
    return sorted(findings, key=lambda item: (item["line"], item["pattern"], item["detail"]))


class TestIsolationSensor:
    """Heuristically report tests that leak clock, network, home, cwd or environment state."""

    __test__ = False
    id = "test-isolation"
    routine_ids = (5,)
    resolution_scope = "exhaustive"

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        root = git_root(repo_root)
        files = [
            path for path in tracked_files(root, ["tests"], suffixes=[".py"])
            if _is_test_module(path)
        ]
        trees, skipped = _load_trees(root, files)
        provenance = {
            "inventory": "git ls-files tests/**/test_*.py",
            "filesInspected": len(trees),
            "heuristic": True,
            "skipped": _skip_note(skipped),
        }
        observations: list[Observation] = []
        for path in sorted(trees):
            findings = _isolation_findings(trees[path])
            if findings:
                observations.append(
                    _observation(
                        kind="test_isolation_risk",
                        subject=Subject(type="test-file", id=path),
                        source=self.id, observed_at=observed_at,
                        findings=findings, confidence=0.6, provenance=provenance,
                    )
                )
        return observations


# --------------------------------------------------------------------------
# 3. test history
# --------------------------------------------------------------------------

def _load_history(root: Path) -> list[dict[str, Any]]:
    path = root / _HISTORY_PATH
    if not path.is_file():
        raise SensorNotEvaluated(
            f"no test history supplied at {_HISTORY_PATH}; flake detection was not evaluated"
        )
    text = read_text_bounded(path, limit=_HISTORY_LIMIT_BYTES)
    try:
        document = json.loads(text)
    except json.JSONDecodeError as exc:
        raise SensorUnavailable(f"test history is not valid JSON: {exc}") from exc
    if not isinstance(document, dict) or document.get("schemaVersion") != _HISTORY_SCHEMA:
        raise SensorUnavailable(f"test history must declare schemaVersion {_HISTORY_SCHEMA}")
    runs = document.get("runs")
    if not isinstance(runs, list):
        raise SensorUnavailable("test history 'runs' must be a list")
    if len(runs) > _HISTORY_MAX_RUNS:
        raise SensorUnavailable(f"test history exceeds {_HISTORY_MAX_RUNS} runs")
    seen: set[str] = set()
    total = 0
    for run in runs:
        if not isinstance(run, dict):
            raise SensorUnavailable("test history run must be an object")
        run_id, sha, results = run.get("runId"), run.get("sha"), run.get("results")
        if not isinstance(run_id, str) or not run_id or not isinstance(sha, str) or not sha:
            raise SensorUnavailable("test history run needs non-empty string runId and sha")
        if run_id in seen:
            raise SensorUnavailable(f"test history repeats runId {run_id}")
        seen.add(run_id)
        if not isinstance(results, dict):
            raise SensorUnavailable(f"test history run {run_id} results must be an object")
        total += len(results)
        if total > _HISTORY_MAX_RESULTS:
            raise SensorUnavailable("test history exceeds the bounded result count")
        for nodeid, status in results.items():
            if not isinstance(nodeid, str) or status not in _HISTORY_STATUSES:
                raise SensorUnavailable(f"test history run {run_id} has an invalid result entry")
    return runs


class TestHistorySensor:
    """Report tests that both passed and failed on the same commit (optional input)."""

    __test__ = False
    id = "test-history"
    routine_ids = (5,)

    def scan(self, repo_root: Path, observed_at: str) -> list[Observation]:
        try:
            root = repo_root.resolve(strict=True)
        except (OSError, RuntimeError) as exc:
            raise SensorUnavailable(f"repository root is unavailable: {exc}") from exc
        runs = _load_history(root)
        by_node: dict[str, dict[str, list[tuple[str, str]]]] = {}
        for run in runs:
            for nodeid, status in run["results"].items():
                if status == "skipped":
                    continue
                by_node.setdefault(nodeid, {}).setdefault(run["sha"], []).append((run["runId"], status))
        provenance = {"input": _HISTORY_PATH, "schema": _HISTORY_SCHEMA, "runs": len(runs)}
        observations: list[Observation] = []
        for nodeid in sorted(by_node):
            findings: list[dict[str, Any]] = []
            for sha in sorted(by_node[nodeid]):
                entries = sorted(by_node[nodeid][sha])
                passed = [run_id for run_id, status in entries if status == "passed"]
                failed = [
                    {"runId": run_id, "status": status}
                    for run_id, status in entries
                    if status in {"failed", "error"}
                ]
                if passed and failed:
                    findings.append({"sha": sha, "passedRuns": passed, "failedRuns": failed})
            if findings:
                observations.append(
                    _observation(
                        kind="flaky_test",
                        subject=Subject(type="test-node", id=nodeid),
                        source=self.id, observed_at=observed_at,
                        findings=findings, confidence=0.9, provenance=provenance,
                    )
                )
        return observations
