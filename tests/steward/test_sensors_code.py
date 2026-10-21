"""Tests for the pyast primitives and the three code-analysis sensors.

Sensors read Git's inventory, so every scenario is a real fixture repository
(``make_repo``). Each sensor family covers the ten mandatory categories of the
architecture contract section 3: clean, real defect, determinism, missing
input, truncated input, non-git/unavailable dependency, ambiguity, near-miss
false positives, read-only behavior, and recovery.
"""

from __future__ import annotations

import ast
import textwrap
from pathlib import Path
from typing import Any

import pytest

from gaia_cli.steward.primitives import SensorUnavailable
from gaia_cli.steward.primitives.pyast import (
    comment_map,
    function_fingerprint,
    module_imports,
    module_name_for,
    statement_count,
    strongly_connected_components,
    used_names,
)
from gaia_cli.steward.sensors_code import (
    CodeStructureSensor,
    DeadCodeSensor,
    ErrorHandlingSensor,
    skipped_files,
)
from tests.steward.sensor_fixtures import commit_all, make_repo, tree_digest, write_files

NOW = "2026-10-20T00:00:00Z"


def dedent(text: str) -> str:
    return textwrap.dedent(text).lstrip("\n")


def snapshot(sensor: Any, root: Path) -> list[dict[str, Any]]:
    return [observation.to_dict() for observation in sensor.scan(root, NOW)]


def of_kind(observations: list[Any], kind: str) -> list[Any]:
    return [item for item in observations if item.kind == kind]


# A small healthy package: everything is imported, referenced, or an entry point.
BASE: dict[str, str] = {
    "pyproject.toml": '[project]\nname = "fixture"\n[project.scripts]\ngaia = "gaia_cli.main:main"\n',
    "src/gaia_cli/__init__.py": "",
    "src/gaia_cli/core.py": dedent(
        """
        import os


        def where():
            return os.getcwd()
        """
    ),
    "src/gaia_cli/main.py": dedent(
        """
        from gaia_cli import core


        def main():
            return core.where()
        """
    ),
    "scripts/tool.py": dedent(
        """
        import sys


        def run():
            return sys.argv
        """
    ),
    "tests/test_core.py": "from gaia_cli import core\n\n\ndef test_where():\n    assert core.where()\n",
}


def repo(tmp_path: Path, extra: dict[str, str] | None = None, *, drop: tuple[str, ...] = ()) -> Path:
    files = {**BASE, **(extra or {})}
    for name in drop:
        files.pop(name, None)
    return make_repo(tmp_path / "repo", files)


# --------------------------------------------------------------------------
# pyast primitives
# --------------------------------------------------------------------------


class TestModuleNameFor:
    def test_maps_src_layout_scripts_and_packages(self) -> None:
        assert module_name_for("src/gaia_cli/a/b.py") == "gaia_cli.a.b"
        assert module_name_for("src/gaia_cli/a/__init__.py") == "gaia_cli.a"
        assert module_name_for("src/gaia_cli/__init__.py") == "gaia_cli"
        assert module_name_for("scripts/x.py") == "scripts.x"
        assert module_name_for("tests/steward/test_a.py") == "tests.steward.test_a"

    def test_rejects_unimportable_paths(self) -> None:
        assert module_name_for("scripts/my-script.py") is None
        assert module_name_for("scripts/readme.md") is None
        assert module_name_for("src/__init__.py") is None
        assert module_name_for("../escape.py") is None


class TestModuleImports:
    def refs(self, source: str, name: str = "pkg.sub.mod", package: bool = False):
        return module_imports(ast.parse(dedent(source)), name, package)

    def test_absolute_imports(self) -> None:
        refs = self.refs("import os\nimport a.b.c\nimport x as y\nfrom m.n import p, q as r\n")
        assert [(r.target, r.names, r.bound) for r in refs] == [
            ("os", (), ("os",)),
            ("a.b.c", (), ("a",)),
            ("x", (), ("y",)),
            ("m.n", ("p", "q"), ("p", "r")),
        ]
        assert [r.line for r in refs] == [1, 2, 3, 4]

    def test_relative_imports_in_module_and_package(self) -> None:
        in_module = self.refs("from . import sib\nfrom .other import f\nfrom .. import up\nfrom ..up2 import g\n")
        assert [r.target for r in in_module] == ["pkg.sub", "pkg.sub.other", "pkg", "pkg.up2"]
        in_package = self.refs("from . import sib\nfrom .other import f\n", name="pkg.sub", package=True)
        assert [r.target for r in in_package] == ["pkg.sub", "pkg.sub.other"]

    def test_relative_import_above_top_level_has_empty_target(self) -> None:
        refs = self.refs("from ... import x\n", name="top.mod")
        assert refs[0].target == ""

    def test_scope_flags(self) -> None:
        refs = self.refs(
            """
            from typing import TYPE_CHECKING
            import top
            if TYPE_CHECKING:
                import only_types
            else:
                import runtime_else
            def f():
                import local
            class C:
                import in_class
            try:
                import probe
            except ImportError:
                probe = None
            try:
                import not_guarded
            except ValueError:
                pass
            """
        )
        by = {r.target: r for r in refs}
        assert by["top"].module_scope and not by["top"].guarded
        assert by["only_types"].type_checking and not by["only_types"].module_scope
        assert by["runtime_else"].module_scope and not by["runtime_else"].type_checking
        assert by["local"].in_function and not by["local"].module_scope
        assert by["in_class"].in_class and by["in_class"].module_scope
        assert by["probe"].guarded and by["probe"].module_scope
        assert not by["not_guarded"].guarded

    def test_reexport_idiom_and_star(self) -> None:
        refs = self.refs("import x as x\nfrom y import z as z, w\nfrom q import *\n")
        assert refs[0].reexported == ("x",)
        assert refs[1].reexported == ("z",)
        assert refs[2].names == ("*",) and refs[2].bound == ()

    def test_multiline_statement_records_end_line(self) -> None:
        refs = self.refs("from m import (\n    a,\n    b,\n)\n")
        assert (refs[0].line, refs[0].end_line) == (1, 4)


class TestStronglyConnectedComponents:
    def test_finds_cycles_and_singletons(self) -> None:
        graph = {"a": {"b"}, "b": {"c"}, "c": {"a"}, "d": {"a"}, "e": set()}
        assert strongly_connected_components(graph) == [["a", "b", "c"], ["d"], ["e"]]

    def test_includes_target_only_nodes(self) -> None:
        assert strongly_connected_components({"a": {"z"}}) == [["a"], ["z"]]

    def test_two_independent_cycles_are_ordered(self) -> None:
        graph = {"x": {"y"}, "y": {"x"}, "a": {"b"}, "b": {"a"}}
        assert strongly_connected_components(graph) == [["a", "b"], ["x", "y"]]

    def test_deterministic_regardless_of_insertion_order(self) -> None:
        edges = [("a", "b"), ("b", "c"), ("c", "a"), ("c", "d"), ("d", "e"), ("e", "d")]
        forward: dict[str, set[str]] = {}
        backward: dict[str, set[str]] = {}
        for source, target in edges:
            forward.setdefault(source, set()).add(target)
        for source, target in reversed(edges):
            backward.setdefault(source, set()).add(target)
        assert strongly_connected_components(forward) == strongly_connected_components(backward)
        assert strongly_connected_components(forward) == [["a", "b", "c"], ["d", "e"]]

    def test_long_chain_does_not_exhaust_the_stack(self) -> None:
        size = 5000
        graph = {f"n{i:05d}": {f"n{i + 1:05d}"} for i in range(size)}
        graph[f"n{size:05d}"] = {"n00000"}
        components = strongly_connected_components(graph)
        assert len(components) == 1 and len(components[0]) == size + 1


class TestFunctionFingerprint:
    def fp(self, source: str) -> str:
        node = ast.parse(dedent(source)).body[0]
        assert isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
        return function_fingerprint(node)

    def test_ignores_names_docstrings_and_annotations(self) -> None:
        one = self.fp(
            """
            def first(items, limit: int = 3) -> list:
                '''Docstring one.'''
                out = []
                for item in items:
                    if item > limit:
                        out.append(item * 2)
                return out
            """
        )
        two = self.fp(
            """
            def second(rows, cap):
                total = []
                for row in rows:
                    if row > cap:
                        total.append(row * 2)
                return total
            """
        )
        assert one == two

    def test_constants_calls_and_attributes_matter(self) -> None:
        base = "def f(a):\n    return a.go(1)\n"
        assert self.fp(base) != self.fp("def f(a):\n    return a.go(2)\n")
        assert self.fp(base) != self.fp("def f(a):\n    return a.stop(1)\n")
        assert self.fp(base) != self.fp("def f(a):\n    return other.go(1)\n")

    def test_argument_shape_and_async_matter(self) -> None:
        assert self.fp("def f(a):\n    return a\n") != self.fp("def f(a, b):\n    return a\n")
        assert self.fp("def f(a):\n    return a\n") != self.fp("async def f(a):\n    return a\n")

    def test_keyword_names_are_not_normalized_away(self) -> None:
        assert self.fp("def f(a):\n    return g(key=a)\n") != self.fp("def f(a):\n    return g(other=a)\n")

    def test_local_swap_is_distinguished(self) -> None:
        assert self.fp("def f(a, b):\n    return a - b\n") != self.fp("def f(a, b):\n    return b - a\n")

    def test_fingerprint_is_stable_hex(self) -> None:
        value = self.fp("def f():\n    return 1\n")
        assert len(value) == 64 and int(value, 16) >= 0
        assert value == self.fp("def f():\n    return 1\n")


class TestUsedNames:
    def names(self, source: str) -> set[str]:
        return used_names(ast.parse(dedent(source)))

    def test_loads_and_attribute_roots(self) -> None:
        names = self.names("import os\nx = os.path.join('a')\nprint(x)\n")
        assert {"os", "x", "print"} <= names

    def test_stores_do_not_count(self) -> None:
        assert "y" not in self.names("y = 1\n")

    def test_all_exports_count(self) -> None:
        assert {"alpha", "beta", "gamma"} <= self.names(
            "__all__ = ['alpha']\n__all__ += ['beta']\n__all__.extend(['gamma'])\n"
        )

    def test_string_annotations_count(self) -> None:
        names = self.names(
            """
            def f(a: "Alpha", b: Optional["Beta"]) -> "Gamma":
                pass
            delta: "Delta" = None
            """
        )
        assert {"Alpha", "Beta", "Gamma", "Delta"} <= names

    def test_nested_string_annotation_and_garbage(self) -> None:
        assert "Inner" in self.names("def f(a: 'list[\"Inner\"]'):\n    pass\n")
        assert self.names("def f(a: 'not valid ((('):\n    pass\n") == set()  # does not raise


def test_statement_count_excludes_docstring_and_counts_nested() -> None:
    node = ast.parse(
        dedent(
            """
            def f(x):
                '''doc'''
                if x:
                    y = 1
                    z = 2
                return x
            """
        )
    ).body[0]
    assert isinstance(node, ast.FunctionDef)
    assert statement_count(node) == 4


def test_comment_map_ignores_hash_inside_strings() -> None:
    comments = comment_map('x = "# not a comment"  # real\ny = 2\n')
    assert comments == {1: "# real"}


# --------------------------------------------------------------------------
# Shared failure-semantics checks, applied to every sensor
# --------------------------------------------------------------------------

SENSOR_FACTORIES = {
    "dead-code": DeadCodeSensor,
    "code-structure": CodeStructureSensor,
    "error-handling": ErrorHandlingSensor,
}


@pytest.fixture(params=sorted(SENSOR_FACTORIES))
def factory(request: pytest.FixtureRequest) -> Any:
    return SENSOR_FACTORIES[request.param]


def test_sensor_contract_attributes() -> None:
    assert DeadCodeSensor.routine_ids == (1,) and DeadCodeSensor.id == "dead-code"
    assert CodeStructureSensor.routine_ids == (2,) and CodeStructureSensor.id == "code-structure"
    assert ErrorHandlingSensor.routine_ids == (3,) and ErrorHandlingSensor.id == "error-handling"
    for sensor in SENSOR_FACTORIES.values():
        assert sensor.resolution_scope == "exhaustive"


def test_clean_fixture_has_zero_drift(tmp_path: Path, factory: Any) -> None:
    assert factory().scan(repo(tmp_path), NOW) == []


def test_repeat_scan_is_identical(tmp_path: Path, factory: Any) -> None:
    root = repo(
        tmp_path,
        {
            "src/gaia_cli/messy.py": dedent(
                """
                import json


                def risky():
                    try:
                        return 1
                    except Exception:
                        pass
                """
            ),
            "src/gaia_cli/lonely.py": "VALUE = 1\n",
        },
    )
    sensor = factory()
    first = snapshot(sensor, root)
    assert first == snapshot(sensor, root)
    assert first == snapshot(factory(), root)


@pytest.mark.parametrize("missing", ["src/gaia_cli", "scripts"])
def test_missing_required_inventory_is_unavailable(tmp_path: Path, factory: Any, missing: str) -> None:
    files = {key: value for key, value in BASE.items() if not key.startswith(missing + "/")}
    root = make_repo(tmp_path / "repo", files)
    with pytest.raises(SensorUnavailable, match="required inventory is empty"):
        factory().scan(root, NOW)


def test_truncated_inventory_is_unavailable_not_partial(tmp_path: Path, factory: Any) -> None:
    root = repo(tmp_path)
    with pytest.raises(SensorUnavailable, match="exceeds the bounded limit"):
        factory(max_files=1).scan(root, NOW)


def test_non_git_directory_is_unavailable(tmp_path: Path, factory: Any) -> None:
    plain = tmp_path / "plain"
    write_files(plain, BASE)
    with pytest.raises(SensorUnavailable):
        factory().scan(plain, NOW)


def test_missing_root_is_unavailable(tmp_path: Path, factory: Any) -> None:
    with pytest.raises(SensorUnavailable):
        factory().scan(tmp_path / "absent", NOW)


def test_undecodable_python_inventory_is_unavailable(tmp_path: Path, factory: Any) -> None:
    root = repo(tmp_path)
    (root / "src/gaia_cli/binary.py").write_bytes(b"\xff\xfe\x00bad")
    commit_all(root)
    with pytest.raises(SensorUnavailable, match="not UTF-8"):
        factory().scan(root, NOW)


def test_scan_is_read_only(tmp_path: Path, factory: Any) -> None:
    root = repo(
        tmp_path,
        {"src/gaia_cli/dirty.py": "import os\n\n\ndef f():\n    try:\n        pass\n    except Exception:\n        pass\n"},
    )
    before = tree_digest(root)
    factory().scan(root, NOW)
    assert tree_digest(root) == before


def test_syntax_error_file_is_skipped_not_fatal(tmp_path: Path, factory: Any) -> None:
    root = repo(tmp_path, {"src/gaia_cli/broken.py": "def (:\n"})
    # No crash, no fabricated finding for the broken file.
    for observation in factory().scan(root, NOW):
        assert observation.subject.id != "src/gaia_cli/broken.py"
    skipped = skipped_files(root)
    assert [item["path"] for item in skipped] == ["src/gaia_cli/broken.py"]
    assert skipped[0]["reason"].startswith("SyntaxError")


def test_skipped_files_empty_for_clean_repo(tmp_path: Path) -> None:
    assert skipped_files(repo(tmp_path)) == []


# --------------------------------------------------------------------------
# DeadCodeSensor: unused_import
# --------------------------------------------------------------------------


class TestUnusedImport:
    def test_real_defect_gives_exact_finding(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {"src/gaia_cli/core.py": "import os\nimport json\nfrom typing import Any\n\nVALUE = json.dumps(1)\n"},
        )
        observations = of_kind(DeadCodeSensor().scan(root, NOW), "unused_import")
        assert len(observations) == 1
        observation = observations[0]
        assert observation.subject.to_dict() == {"type": "source-file", "id": "src/gaia_cli/core.py"}
        assert observation.status == "drift"
        assert observation.confidence == 0.8
        assert observation.observed_state["findingCount"] == 2
        assert observation.observed_state["findings"] == [
            {"line": 1, "name": "os", "statement": "import os", "sideEffectPossible": True},
            {"line": 3, "name": "Any", "statement": "from typing import Any", "sideEffectPossible": False},
        ]
        assert "side effects" in observation.provenance["caveat"]

    def test_alias_and_dotted_import_report_bound_name(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {"src/gaia_cli/core.py": "import os.path\nimport json as js\nfrom a import b as c\n"},
        )
        findings = DeadCodeSensor().scan(root, NOW)[0].observed_state["findings"]
        assert [(f["name"], f["statement"]) for f in findings] == [
            ("os", "import os.path"),
            ("js", "import json as js"),
            ("c", "from a import b as c"),
        ]

    def test_unused_import_in_scripts_is_reported(self, tmp_path: Path) -> None:
        root = repo(tmp_path, {"scripts/tool.py": "import sys\nimport os\n\nprint(sys.argv)\n"})
        observation = of_kind(DeadCodeSensor().scan(root, NOW), "unused_import")[0]
        assert observation.subject.id == "scripts/tool.py"
        assert observation.observed_state["findings"][0]["name"] == "os"

    @pytest.mark.parametrize(
        "source",
        [
            pytest.param("import os\n__all__ = ['os']\n", id="in-all"),
            pytest.param("import os as os\n", id="x-as-x"),
            pytest.param("from os import path as path\n", id="from-as-same"),
            pytest.param("from __future__ import annotations\n", id="future"),
            pytest.param("import os  # noqa\n", id="noqa"),
            pytest.param("import os  # noqa: F401\n", id="noqa-code"),
            pytest.param("from typing import (  # noqa\n    Any,\n)\n", id="noqa-multiline"),
            pytest.param(
                "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from m import Thing\n",
                id="type-checking-block",
            ),
            pytest.param("from m import Thing\n\n\ndef f(x: 'Thing'):\n    return x\n", id="string-annotation"),
            pytest.param("from m import Thing\n\nvalue: 'Thing' = None\n", id="string-ann-assign"),
            pytest.param("try:\n    import yaml\nexcept ImportError:\n    yaml = None\n", id="import-error-probe"),
            pytest.param("try:\n    import yaml\nexcept (ValueError, ModuleNotFoundError):\n    pass\n", id="tuple-probe"),
            pytest.param("def f():\n    import os\n    return 1\n", id="function-local-not-module-level"),
            pytest.param("import os\n\nVALUE = os.sep\n", id="used"),
            pytest.param("import os.path\n\nVALUE = os.path.sep\n", id="dotted-used-by-root"),
            pytest.param("from m import f\n\n@f\ndef g():\n    pass\n", id="used-as-decorator"),
            pytest.param("from m import *\n", id="star"),
        ],
    )
    def test_near_misses_are_not_reported(self, tmp_path: Path, source: str) -> None:
        root = repo(tmp_path, {"src/gaia_cli/core.py": source})
        assert of_kind(DeadCodeSensor().scan(root, NOW), "unused_import") == []

    def test_init_files_are_reexport_surfaces(self, tmp_path: Path) -> None:
        root = repo(tmp_path, {"src/gaia_cli/pkg/__init__.py": "from gaia_cli.core import where\nimport os\n"})
        assert of_kind(DeadCodeSensor().scan(root, NOW), "unused_import") == []

    def test_import_other_files_depend_on_is_a_reexport_not_dead(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/shim.py": "from gaia_cli.core import where\nfrom gaia_cli.core import where as w2\n"
                "import json\nimport sys\n",
                "src/gaia_cli/uses_shim.py": "from gaia_cli.shim import where\nfrom gaia_cli import shim\n"
                "VALUE = shim.json\nprint(where)\n",
                "tests/test_patch.py": "def test_p(monkeypatch):\n    monkeypatch.setattr('gaia_cli.shim.sys', None)\n",
            },
        )
        findings = of_kind(DeadCodeSensor().scan(root, NOW), "unused_import")[0].observed_state["findings"]
        # where (from-import), json (module alias attribute), sys (patch string) are consumed
        # elsewhere; only the unreferenced alias remains.
        assert [f["name"] for f in findings] == ["w2"]

    def test_recovery_removes_the_finding(self, tmp_path: Path) -> None:
        root = repo(tmp_path, {"src/gaia_cli/core.py": "import os\n"})
        assert DeadCodeSensor().scan(root, NOW)
        (root / "src/gaia_cli/core.py").write_text("import os\n\nVALUE = os.sep\n", encoding="utf-8")
        commit_all(root, "fix")
        assert of_kind(DeadCodeSensor().scan(root, NOW), "unused_import") == []


# --------------------------------------------------------------------------
# DeadCodeSensor: orphan_module
# --------------------------------------------------------------------------


class TestOrphanModule:
    def test_real_orphan_is_a_low_confidence_candidate(self, tmp_path: Path) -> None:
        root = repo(tmp_path, {"src/gaia_cli/lonely.py": "VALUE = 1\n"})
        observations = of_kind(DeadCodeSensor().scan(root, NOW), "orphan_module")
        assert len(observations) == 1
        observation = observations[0]
        assert observation.subject.to_dict() == {"type": "python-module", "id": "gaia_cli.lonely"}
        assert observation.confidence == 0.6
        assert observation.observed_state["findings"] == [
            {
                "path": "src/gaia_cli/lonely.py",
                "module": "gaia_cli.lonely",
                "importers": 0,
                "textReferences": 0,
                "note": "candidate — requires consumer and external-contract review",
            }
        ]
        assert "deletion" not in str(observation.to_dict()).lower().replace("external-contract", "")

    @pytest.mark.parametrize(
        "extra",
        [
            pytest.param({"tests/test_lonely.py": "import gaia_cli.lonely\n"}, id="test-import"),
            pytest.param({"scripts/use.py": "from gaia_cli import lonely\n"}, id="script-from-package"),
            pytest.param({"src/gaia_cli/other.py": "from . import lonely\n"}, id="relative-sibling"),
            pytest.param({"src/gaia_cli/other.py": "def f():\n    from gaia_cli.lonely import VALUE\n"}, id="function-local"),
            pytest.param(
                {"src/gaia_cli/other.py": "import importlib\nmod = importlib.import_module('gaia_cli.lonely')\n"},
                id="literal-import-module",
            ),
            pytest.param(
                {"pyproject.toml": BASE["pyproject.toml"] + 'other = "gaia_cli.lonely:run"\n'},
                id="entry-point",
            ),
            pytest.param({"Taskfile.yml": "tasks:\n  x:\n    cmds:\n      - python -m gaia_cli.lonely\n"}, id="taskfile-m-form"),
            pytest.param({"package.json": '{"scripts": {"x": "python src/gaia_cli/lonely.py"}}'}, id="package-json-path"),
            pytest.param(
                {".github/workflows/ci.yml": "run: python -m gaia_cli.lonely --check\n"}, id="workflow"
            ),
            pytest.param({"scripts/run.sh": "python src/gaia_cli/lonely.py\n"}, id="script-path"),
            pytest.param({"README.md": "Run `python -m gaia_cli.lonely`.\n"}, id="root-markdown"),
            pytest.param({"docs/agents/guide.md": "See gaia_cli/lonely.py for details.\n"}, id="agents-doc"),
            pytest.param(
                {"src/gaia_cli/other.py": "CMD = ['python', '-m', 'gaia_cli.lonely']\n"}, id="string-constant"
            ),
        ],
    )
    def test_any_consumer_clears_the_candidate(self, tmp_path: Path, extra: dict[str, str]) -> None:
        root = repo(tmp_path, {"src/gaia_cli/lonely.py": "VALUE = 1\n", **extra})
        ids = {item.subject.id for item in of_kind(DeadCodeSensor().scan(root, NOW), "orphan_module")}
        assert "gaia_cli.lonely" not in ids

    def test_docstring_mention_and_self_reference_do_not_count(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/lonely.py": '"""Run python -m gaia_cli.lonely"""\nNAME = "gaia_cli.lonely"\n',
                "src/gaia_cli/other.py": '"""Mentions gaia_cli.lonely only in prose."""\nVALUE = 1\n',
            },
        )
        ids = {o.subject.id for o in of_kind(DeadCodeSensor().scan(root, NOW), "orphan_module")}
        assert "gaia_cli.lonely" in ids

    def test_exclusions_init_main_and_data(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/sub/__init__.py": "",
                "src/gaia_cli/sub/__main__.py": "print('x')\n",
                "src/gaia_cli/data/helper.py": "VALUE = 1\n",
            },
        )
        assert of_kind(DeadCodeSensor().scan(root, NOW), "orphan_module") == []

    def test_dynamic_discovery_exempts_direct_children_only(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/commands/__init__.py": dedent(
                    """
                    import importlib
                    import pkgutil


                    def discover():
                        for _, name, _ in pkgutil.iter_modules(__path__):
                            importlib.import_module(f"gaia_cli.commands.{name}")
                    """
                ),
                "src/gaia_cli/commands/alpha.py": "VALUE = 1\n",
                "src/gaia_cli/commands/deep/__init__.py": "",
                "src/gaia_cli/commands/deep/beta.py": "VALUE = 1\n",
                "src/gaia_cli/other_pkg/__init__.py": "",
                "src/gaia_cli/other_pkg/gamma.py": "VALUE = 1\n",
            },
        )
        observations = of_kind(DeadCodeSensor().scan(root, NOW), "orphan_module")
        ids = sorted(o.subject.id for o in observations)
        # alpha is a discovered command; deep.beta is reachable via import_module's prefix
        # (recorded conservatively); gamma is genuinely unreachable.
        assert ids == ["gaia_cli.other_pkg.gamma"]
        analysis = DeadCodeSensor().analyze(root)
        assert "gaia_cli.commands" in analysis.exempt_packages
        assert "gaia_cli.commands.alpha" in analysis.exempt_modules
        assert "iter_modules" in analysis.exempt_packages["gaia_cli.commands"]

    def test_non_literal_import_module_prefix_is_recorded_and_exempts(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/loader.py": dedent(
                    """
                    import importlib


                    def load(name):
                        return importlib.import_module("gaia_cli.plugins." + name)
                    """
                ),
                "src/gaia_cli/plugins/__init__.py": "",
                "src/gaia_cli/plugins/foo.py": "VALUE = 1\n",
                "tests/test_loader.py": "from gaia_cli.loader import load\n",
                "src/gaia_cli/entry.py": "from gaia_cli import loader\nVALUE = loader\n",
            },
        )
        analysis = DeadCodeSensor().analyze(root)
        assert analysis.exempt_packages["gaia_cli.plugins"].startswith("non-literal importlib.import_module")
        assert "gaia_cli.plugins.foo" in analysis.exempt_modules
        assert "gaia_cli.plugins.foo" not in {o.subject.id for o in DeadCodeSensor().scan(root, NOW)}

    def test_unresolved_dynamic_import_outside_package_lowers_confidence(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/lonely.py": "VALUE = 1\n",
                "tests/test_dyn.py": "import importlib\n\n\ndef load(name):\n    return importlib.import_module(name)\n",
            },
        )
        observation = of_kind(DeadCodeSensor().scan(root, NOW), "orphan_module")[0]
        assert observation.confidence == 0.4
        assert observation.provenance["unresolvedDynamicImports"] == ["tests/test_dyn.py:5"]

    def test_unresolved_dynamic_import_inside_package_exempts_its_package(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/plugins/__init__.py": "import importlib\n\n\ndef load(name):\n    return importlib.import_module(name)\n",
                "src/gaia_cli/plugins/foo.py": "VALUE = 1\n",
            },
        )
        assert of_kind(DeadCodeSensor().scan(root, NOW), "orphan_module") == []

    def test_oversized_consumer_surface_is_unavailable(self, tmp_path: Path) -> None:
        root = repo(tmp_path, {"docs/agents/huge.md": "x" * (2 * 1024 * 1024 + 10)})
        with pytest.raises(SensorUnavailable, match="read limit"):
            DeadCodeSensor().scan(root, NOW)

    def test_missing_pyproject_makes_entry_points_invisible_so_unavailable(self, tmp_path: Path) -> None:
        root = repo(tmp_path, drop=("pyproject.toml",))
        with pytest.raises(SensorUnavailable, match="required inventory is empty"):
            DeadCodeSensor().scan(root, NOW)

    def test_recovery_when_a_consumer_appears(self, tmp_path: Path) -> None:
        root = repo(tmp_path, {"src/gaia_cli/lonely.py": "VALUE = 1\n"})
        assert of_kind(DeadCodeSensor().scan(root, NOW), "orphan_module")
        (root / "src/gaia_cli/main.py").write_text(
            "from gaia_cli import core, lonely\n\n\ndef main():\n    return core.where(), lonely\n",
            encoding="utf-8",
        )
        commit_all(root, "consume")
        assert of_kind(DeadCodeSensor().scan(root, NOW), "orphan_module") == []

    def test_findings_are_aggregated_one_observation_per_subject(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {"src/gaia_cli/lonely.py": "import os\nimport sys\n", "src/gaia_cli/lonely2.py": "import re\n"},
        )
        observations = DeadCodeSensor().scan(root, NOW)
        assert len({(o.kind, o.subject.id) for o in observations}) == len(observations)
        unused = {o.subject.id: o.observed_state["findingCount"] for o in of_kind(observations, "unused_import")}
        assert unused == {"src/gaia_cli/lonely.py": 2, "src/gaia_cli/lonely2.py": 1}


# --------------------------------------------------------------------------
# CodeStructureSensor: import_cycle
# --------------------------------------------------------------------------


class TestImportCycle:
    def test_two_module_cycle_is_an_exact_fact(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/a.py": "from gaia_cli.b import fb\n\n\ndef fa():\n    return fb\n",
                "src/gaia_cli/b.py": "from gaia_cli import a\n\n\ndef fb():\n    return a\n",
            },
        )
        observations = of_kind(CodeStructureSensor().scan(root, NOW), "import_cycle")
        assert len(observations) == 1
        observation = observations[0]
        assert observation.subject.to_dict() == {"type": "import-cycle", "id": "gaia_cli.a|gaia_cli.b"}
        assert observation.confidence == 1.0
        assert observation.observed_state["members"] == ["gaia_cli.a", "gaia_cli.b"]
        assert observation.observed_state["findings"] == [
            {"from": "gaia_cli.a", "to": "gaia_cli.b", "line": 1, "guarded": False},
            {"from": "gaia_cli.b", "to": "gaia_cli.a", "line": 1, "guarded": False},
        ]
        assert "judgment" in observation.observed_state["note"]

    def test_three_cycle_with_relative_imports(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/pkg/__init__.py": "",
                "src/gaia_cli/pkg/x.py": "from . import y\n",
                "src/gaia_cli/pkg/y.py": "from .z import f\n",
                "src/gaia_cli/pkg/z.py": "from .x import g\n",
            },
        )
        observation = of_kind(CodeStructureSensor().scan(root, NOW), "import_cycle")[0]
        assert observation.observed_state["members"] == [
            "gaia_cli.pkg.x",
            "gaia_cli.pkg.y",
            "gaia_cli.pkg.z",
        ]

    def test_member_list_is_truncated_stably(self, tmp_path: Path) -> None:
        size = 10
        files = {
            f"src/gaia_cli/ring/m{i}.py": f"from gaia_cli.ring import m{(i + 1) % size}\n" for i in range(size)
        }
        files["src/gaia_cli/ring/__init__.py"] = ""
        root = repo(tmp_path, files)
        observation = of_kind(CodeStructureSensor().scan(root, NOW), "import_cycle")[0]
        members = [f"gaia_cli.ring.m{i}" for i in range(size)]
        assert observation.subject.id == "|".join(members[:8]) + "|+2"
        assert observation.observed_state["memberCount"] == size
        assert observation.observed_state["members"] == members

    @pytest.mark.parametrize(
        "second",
        [
            pytest.param("def f():\n    from gaia_cli.a import x\n    return x\n", id="function-local-import"),
            pytest.param(
                "from typing import TYPE_CHECKING\nif TYPE_CHECKING:\n    from gaia_cli.a import X\n",
                id="type-checking-import",
            ),
        ],
    )
    def test_non_module_scope_import_does_not_create_a_cycle(self, tmp_path: Path, second: str) -> None:
        root = repo(
            tmp_path,
            {"src/gaia_cli/a.py": "from gaia_cli.b import f\nx = 1\n", "src/gaia_cli/b.py": second},
        )
        assert CodeStructureSensor().scan(root, NOW) == []

    def test_tests_and_scripts_do_not_form_cycles(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "scripts/p.py": "from scripts import q\n",
                "scripts/q.py": "from scripts import p\n",
                "scripts/__init__.py": "",
            },
        )
        assert of_kind(CodeStructureSensor().scan(root, NOW), "import_cycle") == []

    def test_guarded_cycle_edge_is_marked(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/a.py": "import gaia_cli.b\n",
                "src/gaia_cli/b.py": "try:\n    import gaia_cli.a\nexcept ImportError:\n    pass\n",
            },
        )
        edges = of_kind(CodeStructureSensor().scan(root, NOW), "import_cycle")[0].observed_state["findings"]
        assert {(e["from"], e["guarded"]) for e in edges} == {("gaia_cli.a", False), ("gaia_cli.b", True)}

    def test_recovery_when_cycle_is_broken(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {"src/gaia_cli/a.py": "import gaia_cli.b\n", "src/gaia_cli/b.py": "import gaia_cli.a\n"},
        )
        assert of_kind(CodeStructureSensor().scan(root, NOW), "import_cycle")
        (root / "src/gaia_cli/b.py").write_text("def f():\n    import gaia_cli.a\n", encoding="utf-8")
        commit_all(root, "break cycle")
        assert of_kind(CodeStructureSensor().scan(root, NOW), "import_cycle") == []


# --------------------------------------------------------------------------
# CodeStructureSensor: code_duplication
# --------------------------------------------------------------------------

NINE = dedent(
    """
    def {name}({a}, {b}):
        '''Docstring {name}.'''
        {out} = []
        for {item} in {a}:
            if {item} > {b}:
                {out}.append({item} * 2)
            elif {item} == 0:
                {out}.append(0)
        {out}.sort()
        return {out}
    """
)


def dup_source(name: str, a: str = "items", b: str = "limit", out: str = "out", item: str = "item") -> str:
    return NINE.format(name=name, a=a, b=b, out=out, item=item)


class TestCodeDuplication:
    def test_renamed_copies_are_one_duplicate_group(self, tmp_path: Path) -> None:
        root = repo(
            tmp_path,
            {
                "src/gaia_cli/one.py": dup_source("first"),
                "scripts/two.py": dup_source("second", a="rows", b="cap", out="acc", item="row"),
            },
        )
        observations = of_kind(CodeStructureSensor().scan(root, NOW), "code_duplication")
        assert len(observations) == 1
        observation = observations[0]
        assert observation.subject.type == "duplicate-structure"
        assert observation.subject.id.startswith("dup:") and len(observation.subject.id) == 4 + 16
        assert observation.confidence == 0.7
        assert observation.observed_state["findings"] == [
            "scripts/two.py:second:1",
            "src/gaia_cli/one.py:first:1",
        ]
        assert observation.observed_state["occurrenceCount"] == 2
        assert observation.observed_state["statementCount"] == 8

    def test_methods_use_qualified_names_and_same_file_counts(self, tmp_path: Path) -> None:
        method = textwrap.indent(dup_source("handle"), "    ")
        root = repo(
            tmp_path,
            {"src/gaia_cli/two.py": f"class A:\n{method}\nclass B:\n{method}"},
        )
        findings = of_kind(CodeStructureSensor().scan(root, NOW), "code_duplication")[0].observed_state["findings"]
        assert findings == ["src/gaia_cli/two.py:A.handle:2", "src/gaia_cli/two.py:B.handle:14"]

    def test_group_id_is_stable_across_scans_and_independent_of_location(self, tmp_path: Path) -> None:
        first = repo(tmp_path / "x", {"src/gaia_cli/one.py": dup_source("a"), "src/gaia_cli/two.py": dup_source("b")})
        second = repo(tmp_path / "y", {"src/gaia_cli/p.py": dup_source("zzz"), "scripts/q.py": dup_source("yyy")})
        id_one = CodeStructureSensor().scan(first, NOW)[0].subject.id
        id_two = CodeStructureSensor().scan(second, NOW)[0].subject.id
        assert id_one == id_two

    def test_different_constant_or_call_is_not_a_duplicate(self, tmp_path: Path) -> None:
        other = dup_source("second").replace("item * 2", "item * 3")
        root = repo(tmp_path, {"src/gaia_cli/one.py": dup_source("first"), "src/gaia_cli/two.py": other})
        assert of_kind(CodeStructureSensor().scan(root, NOW), "code_duplication") == []

    def test_short_functions_are_not_reported(self, tmp_path: Path) -> None:
        short = "def f(a):\n    x = a + 1\n    y = x * 2\n    return y\n"
        root = repo(tmp_path, {"src/gaia_cli/one.py": short, "src/gaia_cli/two.py": short.replace("def f", "def g")})
        assert of_kind(CodeStructureSensor().scan(root, NOW), "code_duplication") == []

    def test_threshold_is_eight_statements_excluding_docstring(self, tmp_path: Path) -> None:
        seven = "def f(a):\n    '''doc'''\n" + "".join(f"    v{i} = a + {i}\n" for i in range(6)) + "    return a\n"
        eight = seven.replace("    return a\n", "    v9 = 9\n    return a\n")
        root_seven = repo(tmp_path / "s", {"src/gaia_cli/one.py": seven, "src/gaia_cli/two.py": seven.replace("def f", "def g")})
        root_eight = repo(tmp_path / "e", {"src/gaia_cli/one.py": eight, "src/gaia_cli/two.py": eight.replace("def f", "def g")})
        assert of_kind(CodeStructureSensor().scan(root_seven, NOW), "code_duplication") == []
        assert len(of_kind(CodeStructureSensor().scan(root_eight, NOW), "code_duplication")) == 1

    def test_tests_are_consumers_never_subjects(self, tmp_path: Path) -> None:
        root = repo(tmp_path, {"src/gaia_cli/one.py": dup_source("first"), "tests/test_copy.py": dup_source("copy")})
        assert of_kind(CodeStructureSensor().scan(root, NOW), "code_duplication") == []

    def test_recovery_when_copy_is_removed(self, tmp_path: Path) -> None:
        root = repo(tmp_path, {"src/gaia_cli/one.py": dup_source("a"), "src/gaia_cli/two.py": dup_source("b")})
        assert of_kind(CodeStructureSensor().scan(root, NOW), "code_duplication")
        (root / "src/gaia_cli/two.py").write_text("VALUE = 1\n", encoding="utf-8")
        commit_all(root, "dedupe")
        assert of_kind(CodeStructureSensor().scan(root, NOW), "code_duplication") == []


# --------------------------------------------------------------------------
# ErrorHandlingSensor: swallowed_exception
# --------------------------------------------------------------------------


def handler_source(handler: str, body: str) -> str:
    return f"def f():\n    try:\n        risky()\n    {handler}\n{textwrap.indent(body, '        ')}\n    return 1\n"


class TestSwallowedException:
    @pytest.mark.parametrize(
        ("handler", "body", "label", "text"),
        [
            ("except Exception:", "pass", "except Exception", "pass"),
            ("except Exception as exc:", "pass", "except Exception", "pass"),
            ("except BaseException:", "pass", "except BaseException", "pass"),
            ("except:", "pass", "except", "pass"),
            ("except (ValueError, Exception):", "pass", "except (ValueError, Exception)", "pass"),
            ("except Exception:", "...", "except Exception", "..."),
            ("except Exception:", '"""ignored"""', "except Exception", "docstring"),
            ("except Exception:", "return", "except Exception", "return"),
            ("except Exception:", "return None", "except Exception", "return None"),
            ("except builtins.Exception:", "pass", "except builtins.Exception", "pass"),
            ("except Exception:", "pass\ncontinue", "except Exception", "pass; continue"),
        ],
    )
    def test_swallowed_shapes_give_exact_findings(
        self, tmp_path: Path, handler: str, body: str, label: str, text: str
    ) -> None:
        root = repo(tmp_path, {"src/gaia_cli/risky.py": handler_source(handler, body)})
        observations = ErrorHandlingSensor().scan(root, NOW)
        assert len(observations) == 1
        observation = observations[0]
        assert observation.kind == "swallowed_exception"
        assert observation.subject.to_dict() == {"type": "source-file", "id": "src/gaia_cli/risky.py"}
        assert observation.confidence == 0.8
        assert observation.observed_state["findings"] == [{"line": 4, "handler": label, "body": text}]

    def test_continue_inside_loop(self, tmp_path: Path) -> None:
        source = "def f(items):\n    for i in items:\n        try:\n            g(i)\n        except Exception:\n            continue\n"
        root = repo(tmp_path, {"scripts/loop.py": source})
        finding = ErrorHandlingSensor().scan(root, NOW)[0].observed_state["findings"][0]
        assert finding == {"line": 5, "handler": "except Exception", "body": "continue"}

    def test_multiple_handlers_are_one_aggregated_observation(self, tmp_path: Path) -> None:
        source = handler_source("except Exception:", "pass") + handler_source("except:", "pass").replace("def f", "def g")
        root = repo(tmp_path, {"src/gaia_cli/risky.py": source})
        observations = ErrorHandlingSensor().scan(root, NOW)
        assert len(observations) == 1
        assert observations[0].observed_state["findingCount"] == 2

    @pytest.mark.parametrize(
        ("handler", "body"),
        [
            pytest.param("except ValueError:", "pass", id="specific-exception"),
            pytest.param("except (OSError, ValueError):", "pass", id="specific-tuple"),
            pytest.param("except KeyboardInterrupt:", "pass", id="control-flow-exception"),
            pytest.param("except Exception:", "log.warning('failed')", id="logs"),
            pytest.param("except Exception as exc:", "log.warning(exc)\npass", id="logs-then-pass"),
            pytest.param("except Exception:", "raise", id="reraises"),
            pytest.param("except Exception:", "return False", id="returns-sentinel"),
            pytest.param("except Exception:", "return {}", id="returns-empty"),
            pytest.param("except Exception:", "count += 1", id="records-state"),
            pytest.param("except Exception:", "print('x')", id="prints"),
        ],
    )
    def test_near_misses_are_not_reported(self, tmp_path: Path, handler: str, body: str) -> None:
        root = repo(tmp_path, {"src/gaia_cli/risky.py": handler_source(handler, body)})
        assert ErrorHandlingSensor().scan(root, NOW) == []

    @pytest.mark.parametrize(
        "source",
        [
            pytest.param(
                "def f():\n    try:\n        g()\n    except Exception:  # steward: best-effort\n        pass\n",
                id="marker-on-except-line",
            ),
            pytest.param(
                "def f():\n    try:\n        g()\n    except Exception:\n        pass  # steward: best-effort cache write\n",
                id="marker-on-first-body-line",
            ),
            pytest.param(
                "def f():\n    try:\n        g()\n    except Exception:\n        # steward: best-effort\n        pass\n",
                id="marker-on-comment-line-between",
            ),
        ],
    )
    def test_documented_best_effort_marker_is_honoured(self, tmp_path: Path, source: str) -> None:
        root = repo(tmp_path, {"src/gaia_cli/risky.py": source})
        assert ErrorHandlingSensor().scan(root, NOW) == []

    def test_marker_text_in_a_string_or_a_lookalike_comment_does_not_exempt(self, tmp_path: Path) -> None:
        source = (
            "def f():\n    try:\n        g()\n    except Exception:\n        pass\n        'steward: best-effort'\n"
            "def h():\n    try:\n        g()\n    except Exception:  # best effort, steward\n        pass\n"
        )
        root = repo(tmp_path, {"src/gaia_cli/risky.py": source})
        findings = ErrorHandlingSensor().scan(root, NOW)[0].observed_state["findings"]
        assert [f["line"] for f in findings] == [4, 10]

    def test_marker_only_exempts_its_own_handler(self, tmp_path: Path) -> None:
        source = (
            "def f():\n    try:\n        g()\n    except Exception:  # steward: best-effort\n        pass\n"
            "def h():\n    try:\n        g()\n    except Exception:\n        pass\n"
        )
        root = repo(tmp_path, {"src/gaia_cli/risky.py": source})
        findings = ErrorHandlingSensor().scan(root, NOW)[0].observed_state["findings"]
        assert [f["line"] for f in findings] == [9]

    def test_recovery_after_logging_the_failure(self, tmp_path: Path) -> None:
        root = repo(tmp_path, {"src/gaia_cli/risky.py": handler_source("except Exception:", "pass")})
        assert ErrorHandlingSensor().scan(root, NOW)
        (root / "src/gaia_cli/risky.py").write_text(
            handler_source("except Exception as exc:", "log.warning(exc)"), encoding="utf-8"
        )
        commit_all(root, "log it")
        assert ErrorHandlingSensor().scan(root, NOW) == []

    def test_findings_are_capped_but_fully_counted(self, tmp_path: Path) -> None:
        body = "".join(
            f"def f{i}():\n    try:\n        g()\n    except Exception:\n        pass\n" for i in range(25)
        )
        root = repo(tmp_path, {"src/gaia_cli/risky.py": body})
        state = ErrorHandlingSensor().scan(root, NOW)[0].observed_state
        assert state["findingCount"] == 25
        assert len(state["findings"]) == 20 and state["findingsCapped"] is True
