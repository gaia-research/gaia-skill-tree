"""Contract tests for the security, mutation-boundary and browser/privacy sensors.

Fake credentials are assembled at runtime so this file never contains a literal
that matches a credential pattern (the secret-scan sensor scans this repository).
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Mapping

import pytest

from gaia_cli.steward import sensors_security
from gaia_cli.steward.primitives import SensorUnavailable
from gaia_cli.steward.sensors_security import (
    BrowserSinkSensor,
    MutationBoundarySensor,
    SecretScanSensor,
    _SECRET_PATTERNS,
)
from tests.steward.sensor_fixtures import commit_all, make_repo, tree_digest, write_files

NOW = "2026-10-20T00:00:00Z"


def _seeded(seed: str, length: int) -> str:
    """Deterministic lowercase hex-ish body with no ascending runs."""

    digest = hashlib.sha256(seed.encode()).hexdigest()
    body = (digest * 4)[:length]
    assert "123456" not in body and "abcdef" not in body
    return body


def _github_token(seed: str = "gh") -> str:
    return "ghp" + "_" + _seeded(seed, 36)


def _aws_key(seed: str = "aws") -> str:
    return "AKIA" + _seeded(seed, 16).upper()


def _openai_key(seed: str = "oa") -> str:
    return "sk" + "-" + "7" + _seeded(seed, 47)


def _private_key_header() -> str:
    return "-----" + "BEGIN " + "RSA PRIVATE KEY" + "-----"


def _dumps(observations) -> str:
    return json.dumps([item.to_dict() for item in observations], sort_keys=True)


# --------------------------------------------------------------------------
# Mutation boundary fixtures
# --------------------------------------------------------------------------

IMPL = '''
MUTATING_DEV_COMMANDS = frozenset({"add", "rm"})
'''


def _dev_init(live: str = '"add", "rm"', parsers: str = "add rm list", dispatch: Mapping[str, str] | None = None) -> str:
    dispatch = dispatch or {
        "add": "gaia_cli.commands.dev.writer:addCommand",
        "rm": "gaia_cli.commands.dev.writer:rmCommand",
        "list": "gaia_cli.commands.dev.reader:listCommand",
    }
    registrations = "\n".join(f'        sub.add_parser("{name}")' for name in parsers.split())
    branches = []
    for index, (name, target) in enumerate(dispatch.items()):
        module, function = target.split(":")
        keyword = "if" if index == 0 else "elif"
        branches.append(
            f'        {keyword} dev_cmd == "{name}":\n'
            f"            from {module} import {function}\n"
            f"            {function}(args)\n"
        )
    return f'''
class DevCommand:
    def configure(self, parser):
        sub = parser.add_subparsers(dest="dev_command")
{registrations}

    def execute(self, args):
        dev_cmd = getattr(args, "dev_command", None)
        MUTATING_DEV_COMMANDS = {{{live}}}
        if dev_cmd in MUTATING_DEV_COMMANDS:
            from gaia_cli.authz import require_operator
            require_operator("dev", args.registry)
{"".join(branches)}
'''


WRITER = '''
from pathlib import Path


def addCommand(args):
    Path(args.registry).joinpath("added.json").write_text("{}")


def rmCommand(args):
    Path(args.registry).joinpath("added.json").unlink()
'''

READER = '''
import json
import sys


def listCommand(args):
    text = open(args.registry).read().replace("a", "b")
    json.dump({"ok": text}, sys.stdout)
'''


# The legacy dispatcher only matters when an installed entry point can run it.
LEGACY_ENTRY = {
    "pyproject.toml": '[project]\nname = "x"\n\n[project.scripts]\ngaia = "gaia_cli.impl:main"\n',
}
LIVE_ENTRY = {
    "pyproject.toml": '[project]\nname = "x"\n\n[project.scripts]\ngaia = "gaia_cli.main:main"\n',
}


def _mutation_files(**overrides: str) -> dict[str, str]:
    files = {
        **LEGACY_ENTRY,
        "src/gaia_cli/impl.py": IMPL,
        "src/gaia_cli/commands/dev/__init__.py": _dev_init(),
        "src/gaia_cli/commands/dev/writer.py": WRITER,
        "src/gaia_cli/commands/dev/reader.py": READER,
        "scripts/tool.py": "print('hello')\n",
    }
    files.update(overrides)
    return files


def _mutation(tmp_path: Path, **overrides: str):
    root = make_repo(tmp_path / "repo", _mutation_files(**overrides))
    return root, MutationBoundarySensor().scan(root, NOW)


def _gating(observations):
    return [item for item in observations if item.kind == "ungated_mutation"]


def _execution(observations):
    return [item for item in observations if item.kind == "unsafe_execution"]


class TestUngatedMutation:
    def test_clean_boundary_is_silent(self, tmp_path: Path) -> None:
        _, observations = _mutation(tmp_path)
        assert observations == []

    def test_sensor_contract_shape(self) -> None:
        sensor = MutationBoundarySensor()
        assert (sensor.id, sensor.routine_ids, sensor.resolution_scope) == ("mutation-boundary", (7,), "exhaustive")

    def test_set_disagreement_is_reported_with_full_confidence(self, tmp_path: Path) -> None:
        _, observations = _mutation(
            tmp_path,
            **{"src/gaia_cli/impl.py": 'MUTATING_DEV_COMMANDS = frozenset({"add"})\n'},
        )
        (item,) = _gating(observations)
        assert item.subject.type == "cli-surface"
        assert item.subject.id == "mutating-dev-commands"
        assert item.status == "drift"
        assert item.confidence == 1.0
        assert item.observed_state["findings"] == [{"command": "rm", "inLive": True, "inLegacy": False}]

    def test_ungated_writing_command_is_flagged_with_write_sites(self, tmp_path: Path) -> None:
        files = {
            "src/gaia_cli/commands/dev/__init__.py": _dev_init(
                parsers="add rm list export",
                dispatch={
                    "add": "gaia_cli.commands.dev.writer:addCommand",
                    "rm": "gaia_cli.commands.dev.writer:rmCommand",
                    "list": "gaia_cli.commands.dev.reader:listCommand",
                    "export": "gaia_cli.commands.dev.exporter:exportCommand",
                },
            ),
            "src/gaia_cli/commands/dev/exporter.py": (
                "from pathlib import Path\n\n\n"
                "def exportCommand(args):\n"
                "    Path(args.registry).joinpath('out.json').write_text('{}')\n"
            ),
        }
        _, observations = _mutation(tmp_path, **files)
        (item,) = _gating(observations)
        assert item.subject.id == "dev:export"
        assert item.confidence == 0.7
        (finding,) = item.observed_state["findings"]
        assert finding["handler"] == "gaia_cli.commands.dev.exporter:exportCommand"
        assert finding["writeSites"][0] == {
            "path": "src/gaia_cli/commands/dev/exporter.py",
            "line": 5,
            "call": ".write_text",
        }

    def test_write_reached_through_helper_in_same_module(self, tmp_path: Path) -> None:
        files = {
            "src/gaia_cli/commands/dev/__init__.py": _dev_init(
                parsers="add rm sync",
                dispatch={
                    "add": "gaia_cli.commands.dev.writer:addCommand",
                    "rm": "gaia_cli.commands.dev.writer:rmCommand",
                    "sync": "gaia_cli.commands.dev.syncer:syncCommand",
                },
            ),
            "src/gaia_cli/commands/dev/syncer.py": (
                "import shutil\n\n\n"
                "def _copy(a, b):\n    shutil.copy2(a, b)\n\n\n"
                "def syncCommand(args):\n    _copy(args.a, args.b)\n"
            ),
        }
        _, observations = _mutation(tmp_path, **files)
        (item,) = _gating(observations)
        assert item.subject.id == "dev:sync"
        assert item.observed_state["findings"][0]["writeSites"][0]["call"] == "shutil.copy2"

    def test_write_reached_through_one_import_hop(self, tmp_path: Path) -> None:
        files = {
            "src/gaia_cli/commands/dev/__init__.py": _dev_init(
                parsers="add rm sync",
                dispatch={
                    "add": "gaia_cli.commands.dev.writer:addCommand",
                    "rm": "gaia_cli.commands.dev.writer:rmCommand",
                    "sync": "gaia_cli.commands.dev.syncer:syncCommand",
                },
            ),
            "src/gaia_cli/commands/dev/syncer.py": (
                "from gaia_cli.store import persist\n\n\n"
                "def syncCommand(args):\n    persist(args)\n"
            ),
            "src/gaia_cli/store.py": "import os\n\n\ndef persist(args):\n    os.replace(args.a, args.b)\n",
        }
        _, observations = _mutation(tmp_path, **files)
        (item,) = _gating(observations)
        assert item.observed_state["findings"][0]["writeSites"][0]["path"] == "src/gaia_cli/store.py"

    def test_scratch_only_write_has_reduced_confidence(self, tmp_path: Path) -> None:
        files = {
            "src/gaia_cli/commands/dev/__init__.py": _dev_init(
                parsers="add rm probe",
                dispatch={
                    "add": "gaia_cli.commands.dev.writer:addCommand",
                    "rm": "gaia_cli.commands.dev.writer:rmCommand",
                    "probe": "gaia_cli.commands.dev.probe:probeCommand",
                },
            ),
            "src/gaia_cli/commands/dev/probe.py": (
                "from pathlib import Path\n\n\n"
                "def probeCommand(args):\n"
                "    Path('generated-output/probe.json').write_text('{}')\n"
            ),
        }
        _, observations = _mutation(tmp_path, **files)
        (item,) = _gating(observations)
        assert item.confidence == 0.5
        assert item.observed_state["findings"][0]["writesLookLikeScratch"] is True

    def test_read_only_and_near_miss_calls_are_not_flagged(self, tmp_path: Path) -> None:
        # list uses str.replace (2 args), read-mode open and json.dump to stdout.
        _, observations = _mutation(tmp_path)
        assert _gating(observations) == []

    def test_conditionally_gated_command_is_not_flagged(self, tmp_path: Path) -> None:
        init = _dev_init(
            parsers="add rm arbor",
            dispatch={
                "add": "gaia_cli.commands.dev.writer:addCommand",
                "rm": "gaia_cli.commands.dev.writer:rmCommand",
                "arbor": "gaia_cli.commands.dev.writer:addCommand",
            },
        ).replace(
            "if dev_cmd in MUTATING_DEV_COMMANDS:",
            'if dev_cmd in MUTATING_DEV_COMMANDS or (dev_cmd == "arbor" and args.sub in {"import"}):',
        )
        _, observations = _mutation(tmp_path, **{"src/gaia_cli/commands/dev/__init__.py": init})
        assert _gating(observations) == []

    def test_registered_command_without_dispatch_is_not_invented(self, tmp_path: Path) -> None:
        init = _dev_init(parsers="add rm ghost")
        _, observations = _mutation(tmp_path, **{"src/gaia_cli/commands/dev/__init__.py": init})
        assert _gating(observations) == []

    def test_repeat_scan_is_identical(self, tmp_path: Path) -> None:
        root, first = _mutation(
            tmp_path,
            **{"src/gaia_cli/impl.py": 'MUTATING_DEV_COMMANDS = frozenset({"add"})\n'},
        )
        assert _dumps(first) == _dumps(MutationBoundarySensor().scan(root, NOW))

    def test_recovery_when_sets_are_aligned(self, tmp_path: Path) -> None:
        root, first = _mutation(
            tmp_path,
            **{"src/gaia_cli/impl.py": 'MUTATING_DEV_COMMANDS = frozenset({"add"})\n'},
        )
        assert len(_gating(first)) == 1
        write_files(root, {"src/gaia_cli/impl.py": IMPL})
        commit_all(root)
        assert MutationBoundarySensor().scan(root, NOW) == []

    DIVERGED = {"src/gaia_cli/impl.py": 'MUTATING_DEV_COMMANDS = frozenset({"add"})\n'}

    def test_dead_legacy_dispatcher_is_not_compared(self, tmp_path: Path) -> None:
        # pyproject routes gaia to gaia_cli.main:main, whose own main never calls
        # impl.main, so the legacy set disagreeing with the live one is unreachable.
        main = "import gaia_cli.impl as _impl\n\n\ndef main():\n    return _impl.MUTATING_DEV_COMMANDS\n"
        _, observations = _mutation(
            tmp_path, **LIVE_ENTRY, **self.DIVERGED, **{"src/gaia_cli/main.py": main}
        )
        assert _gating(observations) == []

    def test_dead_legacy_dispatcher_may_be_absent(self, tmp_path: Path) -> None:
        files = _mutation_files(**LIVE_ENTRY)
        del files["src/gaia_cli/impl.py"]
        root = make_repo(tmp_path / "repo", files)
        assert _gating(MutationBoundarySensor().scan(root, NOW)) == []

    def test_dead_legacy_still_reports_a_real_ungated_writer(self, tmp_path: Path) -> None:
        # `rm` writes and is absent from the live gate: a true positive that the
        # legacy comparison never owned.
        init = _dev_init(live='"add"', parsers="add rm list")
        _, observations = _mutation(tmp_path, **LIVE_ENTRY, **{"src/gaia_cli/commands/dev/__init__.py": init})
        assert [item.subject.id for item in _gating(observations)] == ["dev:rm"]

    @pytest.mark.parametrize(
        "main_source",
        [
            "from gaia_cli.impl import main\n",
            "from gaia_cli.impl import main as legacy\n\n\ndef main():\n    return legacy()\n",
            "import gaia_cli.impl as _impl\n\n\ndef main():\n    return _impl.main()\n",
            "from gaia_cli import impl\n\n\ndef helper():\n    return impl.main()\n\n\ndef main():\n    return helper()\n",
        ],
    )
    def test_legacy_dispatcher_reachable_through_the_entry_point_is_compared(
        self, tmp_path: Path, main_source: str
    ) -> None:
        _, observations = _mutation(
            tmp_path, **LIVE_ENTRY, **self.DIVERGED, **{"src/gaia_cli/main.py": main_source}
        )
        (item,) = _gating(observations)
        assert item.subject.id == "mutating-dev-commands"

    def test_sensor_writes_nothing(self, tmp_path: Path) -> None:
        root, _ = _mutation(tmp_path)
        before = tree_digest(root)
        MutationBoundarySensor().scan(root, NOW)
        assert tree_digest(root) == before

    @pytest.mark.parametrize(
        "overrides, reason",
        [
            ({"src/gaia_cli/impl.py": "x = 1\n"}, "no MUTATING_DEV_COMMANDS"),
            ({"src/gaia_cli/impl.py": 'MUTATING_DEV_COMMANDS = frozenset({name for name in ("a",)})\n'}, "not a static"),
            ({"src/gaia_cli/impl.py": "MUTATING_DEV_COMMANDS = frozenset({one, 'two'})\n"}, "non-literal element"),
            ({"src/gaia_cli/impl.py": "def broken(:\n"}, "cannot be parsed"),
            (
                {"src/gaia_cli/commands/dev/__init__.py": 'MUTATING_DEV_COMMANDS = {"add"}\n'},
                "add_subparsers",
            ),
        ],
    )
    def test_unresolvable_boundary_is_unavailable_with_reason(
        self, tmp_path: Path, overrides: dict[str, str], reason: str
    ) -> None:
        root = make_repo(tmp_path / "repo", _mutation_files(**overrides))
        with pytest.raises(SensorUnavailable, match=reason):
            MutationBoundarySensor().scan(root, NOW)

    def test_missing_required_file_is_unavailable(self, tmp_path: Path) -> None:
        files = _mutation_files()
        del files["src/gaia_cli/impl.py"]
        root = make_repo(tmp_path / "repo", files)
        with pytest.raises(SensorUnavailable):
            MutationBoundarySensor().scan(root, NOW)

    def test_non_git_directory_is_unavailable(self, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        plain.mkdir()
        with pytest.raises(SensorUnavailable):
            MutationBoundarySensor().scan(plain, NOW)

    def test_truncated_inventory_is_unavailable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root = make_repo(tmp_path / "repo", _mutation_files())
        from gaia_cli.steward.primitives import files as primitives

        real = primitives._git

        def truncated(root_path, arguments, *, max_bytes):
            output = real(root_path, arguments, max_bytes=max_bytes)
            return output[:-1] if arguments and arguments[0] == "ls-files" else output

        monkeypatch.setattr(primitives, "_git", truncated)
        with pytest.raises(SensorUnavailable, match="truncated"):
            MutationBoundarySensor().scan(root, NOW)


class TestUnsafeExecution:
    def _scan(self, tmp_path: Path, source: str):
        root, observations = _mutation(tmp_path, **{"scripts/tool.py": source})
        return _execution(observations)

    @pytest.mark.parametrize(
        "source, pattern",
        [
            ("import subprocess\nsubprocess.run(f'ls {x}', shell=True)\n", "subprocess-shell-true-nonliteral"),
            ("import subprocess\nsubprocess.check_output(cmd, shell=True)\n", "subprocess-shell-true-nonliteral"),
            ("from subprocess import run\nrun('ls ' + name, shell=True)\n", "subprocess-shell-true-nonliteral"),
            ("eval(user)\n", "eval-nonliteral"),
            ("exec(code)\n", "exec-nonliteral"),
            ("import yaml\nyaml.load(text)\n", "yaml-load-unsafe-loader"),
            ("import yaml as y\ny.load(text, Loader=y.FullLoader)\n", "yaml-load-unsafe-loader"),
            ("import yaml\nyaml.unsafe_load(text)\n", "yaml-unsafe_load-unsafe-loader"),
            ("import pickle\npickle.loads(blob)\n", "pickle-loads"),
            ("import pickle\npickle.load(handle)\n", "pickle-load"),
            ("import tarfile\ntar = tarfile.open('a.tgz')\ntar.extractall('out')\n", "tarfile-extractall-no-filter"),
        ],
    )
    def test_real_defect_is_reported(self, tmp_path: Path, source: str, pattern: str) -> None:
        (item,) = self._scan(tmp_path, source)
        assert item.subject.type == "source-file"
        assert item.subject.id == "scripts/tool.py"
        assert [finding["pattern"] for finding in item.observed_state["findings"]] == [pattern]
        assert item.confidence == 0.8

    @pytest.mark.parametrize(
        "source",
        [
            "import yaml\nyaml.safe_load(text)\n",
            "import yaml\nyaml.load(text, Loader=yaml.SafeLoader)\n",
            "import yaml\nyaml.load(text, yaml.CSafeLoader)\n",
            "import subprocess\nsubprocess.run(['ls', x])\n",
            "import subprocess\nsubprocess.run('ls -l', shell=True)\n",
            "import subprocess\nsubprocess.run(cmd, shell=False)\n",
            "eval('1 + 1')\n",
            "import ast\nast.literal_eval(text)\n",
            "import tarfile\ntar = tarfile.open('a.tgz')\ntar.extractall('out', filter='data')\n",
            "import zipfile\nwith zipfile.ZipFile('a.zip') as archive:\n    archive.extractall('out')\n",
            "import json\njson.loads(text)\n",
        ],
    )
    def test_safe_near_misses_are_not_reported(self, tmp_path: Path, source: str) -> None:
        assert self._scan(tmp_path, source) == []

    def test_unknown_archive_receiver_has_reduced_confidence(self, tmp_path: Path) -> None:
        (item,) = self._scan(tmp_path, "def unpack(archive):\n    archive.extractall('out')\n")
        assert item.confidence == 0.5
        assert item.observed_state["findings"][0]["ambiguous"] is True

    def test_one_observation_per_file_with_pattern_counts(self, tmp_path: Path) -> None:
        source = "import pickle\npickle.loads(a)\npickle.loads(b)\neval(x)\n"
        (item,) = self._scan(tmp_path, source)
        assert item.observed_state["findingCount"] == 3
        assert item.observed_state["patternCounts"] == {"eval-nonliteral": 1, "pickle-loads": 2}

    def test_syntax_error_file_is_counted_not_fatal(self, tmp_path: Path) -> None:
        root, observations = _mutation(
            tmp_path,
            **{"scripts/tool.py": "eval(x)\n", "scripts/broken.py": "def broken(:\n"},
        )
        (item,) = _execution(observations)
        assert item.provenance["filesSkippedSyntaxError"] == 1

    def test_recovery_after_fix(self, tmp_path: Path) -> None:
        root, observations = _mutation(tmp_path, **{"scripts/tool.py": "import yaml\nyaml.load(t)\n"})
        assert len(_execution(observations)) == 1
        write_files(root, {"scripts/tool.py": "import yaml\nyaml.safe_load(t)\n"})
        commit_all(root)
        assert MutationBoundarySensor().scan(root, NOW) == []

    def test_repeat_scan_is_identical(self, tmp_path: Path) -> None:
        root, first = _mutation(tmp_path, **{"scripts/tool.py": "eval(x)\n"})
        assert _dumps(first) == _dumps(MutationBoundarySensor().scan(root, NOW))


# --------------------------------------------------------------------------
# Browser sinks
# --------------------------------------------------------------------------


def _browser(tmp_path: Path, files: Mapping[str, str]):
    root = make_repo(tmp_path / "repo", {"docs/keep.js": "var ok = 1;\n", **files})
    return root, BrowserSinkSensor().scan(root, NOW)


def _patterns(observation) -> list[str]:
    return [item["pattern"] for item in observation.observed_state["findings"]]


class TestBrowserSink:
    def test_sensor_contract_shape(self) -> None:
        sensor = BrowserSinkSensor()
        assert (sensor.id, sensor.routine_ids, sensor.resolution_scope) == ("browser-sink", (16,), "exhaustive")

    def test_clean_files_produce_nothing(self, tmp_path: Path) -> None:
        _, observations = _browser(tmp_path, {"docs/page.html": "<p>safe</p>\n"})
        assert observations == []

    @pytest.mark.parametrize(
        "name, source, pattern",
        [
            ("a.js", "el.innerHTML = userValue;\n", "innerHTML-assignment"),
            ("a.js", "el.innerHTML += '<b>' + name;\n", "innerHTML-assignment"),
            ("a.js", "el.outerHTML = tpl(x);\n", "outerHTML-assignment"),
            ("a.js", "el.insertAdjacentHTML('beforeend', html);\n", "insertAdjacentHTML"),
            ("a.js", "document.write(x);\n", "document.write"),
            ("a.js", "eval(text);\n", "eval"),
            ("a.js", "var f = new Function('a', body);\n", "new-Function"),
            ("a.js", "setTimeout('tick()', 10);\n", "timer-with-string"),
            ("a.js", "setInterval(\"tick()\", 10);\n", "timer-with-string"),
            ("a.html", '<a href="/x" target="_blank">x</a>\n', "target-blank-no-noopener"),
            ("a.html", '<script src="http://cdn.example.org/lib.js"></script>\n', "insecure-http-resource"),
            ("a.html", '<img src="http://example.org/p.png">\n', "insecure-http-resource"),
            ("a.js", "img.src = 'http://example.org/p.png';\n", "insecure-http-resource"),
            ("a.js", "a.target = '_blank';\n", "target-blank-no-noopener"),
        ],
    )
    def test_real_defect_is_reported_with_line(self, tmp_path: Path, name: str, source: str, pattern: str) -> None:
        _, observations = _browser(tmp_path, {f"docs/{name}": source})
        (item,) = observations
        assert item.kind == "browser_sink_risk"
        assert item.subject.id == f"docs/{name}"
        assert item.confidence == 0.6
        assert item.observed_state["findings"] == [{"line": 1, "pattern": pattern}]

    @pytest.mark.parametrize(
        "name, source",
        [
            ("a.js", "el.innerHTML = '';\n"),
            ("a.js", 'el.innerHTML = "<b>static</b>";\n'),
            ("a.js", "el.innerHTML = `\n  <ul><li>static</li></ul>\n`;\n"),
            ("a.js", "el.insertAdjacentHTML('beforeend', '<hr>');\n"),
            ("a.js", "el.textContent = userValue;\n"),
            ("a.js", "if (el.innerHTML === html) {}\n"),
            ("a.js", "// el.innerHTML = userValue;\n"),
            ("a.js", "setTimeout(function () {}, 10);\n"),
            ("a.js", "var r = ast.literal_eval(x); var evaluate = 1; evaluate(2);\n"),
            ("a.html", '<a href="/x" target="_blank" rel="noopener noreferrer">x</a>\n'),
            ("a.html", '<a target="_blank"\n   rel="noopener">x</a>\n'),
            ("a.html", '<script src="http://localhost:3000/x.js"></script>\n'),
            ("a.html", '<script src="https://cdn.example.org/x.js"></script>\n'),
            ("a.html", '<svg xmlns="http://www.w3.org/2000/svg"></svg>\n'),
        ],
    )
    def test_safe_near_misses_are_not_reported(self, tmp_path: Path, name: str, source: str) -> None:
        _, observations = _browser(tmp_path, {f"docs/{name}": source})
        assert observations == []

    def test_template_literal_with_interpolation_is_a_sink(self, tmp_path: Path) -> None:
        _, observations = _browser(tmp_path, {"docs/a.js": "el.innerHTML = `\n<b>${name}</b>\n`;\n"})
        assert _patterns(observations[0]) == ["innerHTML-assignment"]

    def test_escaper_present_lowers_confidence_and_says_so(self, tmp_path: Path) -> None:
        source = "function escapeHtml(s) { return s; }\nel.innerHTML = escapeHtml(value);\n"
        _, observations = _browser(tmp_path, {"docs/a.js": source})
        (item,) = observations
        assert item.confidence == 0.4
        (finding,) = item.observed_state["findings"]
        assert finding["note"] == "escaper present; data-flow not proven"
        assert item.observed_state["escaperPresent"] is True

    def test_escaper_does_not_discount_non_html_sinks(self, tmp_path: Path) -> None:
        source = "function escapeHtml(s) { return s; }\neval(x);\n"
        _, observations = _browser(tmp_path, {"docs/a.js": source})
        assert observations[0].confidence == 0.6

    def test_generated_directories_are_excluded(self, tmp_path: Path) -> None:
        bad = "el.innerHTML = userValue;\n"
        generated = {f"docs/{name}/x.js": bad for name in ("graph", "api", "og", "u", "okf", "experiments")}
        _, observations = _browser(tmp_path, generated)
        assert observations == []

    def test_findings_are_aggregated_per_file_with_counts(self, tmp_path: Path) -> None:
        source = "a.innerHTML = x;\nb.innerHTML = y;\neval(z);\n"
        _, observations = _browser(tmp_path, {"docs/a.js": source})
        (item,) = observations
        assert item.observed_state["findingCount"] == 3
        assert item.observed_state["patternCounts"] == {"eval": 1, "innerHTML-assignment": 2}

    def test_finding_list_is_capped_but_count_is_not(self, tmp_path: Path) -> None:
        source = "".join(f"a{i}.innerHTML = v{i};\n" for i in range(30))
        _, observations = _browser(tmp_path, {"docs/a.js": source})
        state = observations[0].observed_state
        assert state["findingCount"] == 30
        assert len(state["findings"]) == 20 and state["findingsCapped"] is True

    def test_repeat_scan_is_identical(self, tmp_path: Path) -> None:
        root, first = _browser(tmp_path, {"docs/a.js": "eval(x);\n"})
        assert _dumps(first) == _dumps(BrowserSinkSensor().scan(root, NOW))

    def test_recovery_after_fix(self, tmp_path: Path) -> None:
        root, first = _browser(tmp_path, {"docs/a.js": "el.innerHTML = v;\n"})
        assert len(first) == 1
        write_files(root, {"docs/a.js": "el.textContent = v;\n"})
        commit_all(root)
        assert BrowserSinkSensor().scan(root, NOW) == []

    def test_missing_docs_inventory_is_unavailable(self, tmp_path: Path) -> None:
        root = make_repo(tmp_path / "repo", {"README.md": "x\n"})
        with pytest.raises(SensorUnavailable, match="empty"):
            BrowserSinkSensor().scan(root, NOW)

    def test_non_git_directory_is_unavailable(self, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        (plain / "docs").mkdir(parents=True)
        with pytest.raises(SensorUnavailable):
            BrowserSinkSensor().scan(plain, NOW)

    def test_sensor_writes_nothing(self, tmp_path: Path) -> None:
        root, _ = _browser(tmp_path, {"docs/a.js": "eval(x);\n"})
        before = tree_digest(root)
        BrowserSinkSensor().scan(root, NOW)
        assert tree_digest(root) == before


# --------------------------------------------------------------------------
# Secret scan
# --------------------------------------------------------------------------


def _secrets(tmp_path: Path, files: Mapping[str, str | bytes]):
    text = {key: value for key, value in files.items() if isinstance(value, str)}
    root = make_repo(tmp_path / "repo", {"README.md": "clean\n", **text})
    for key, value in files.items():
        if isinstance(value, bytes):
            (root / key).parent.mkdir(parents=True, exist_ok=True)
            (root / key).write_bytes(value)
    commit_all(root)
    return root, SecretScanSensor().scan(root, NOW)


class TestSecretScan:
    def test_sensor_contract_shape(self) -> None:
        sensor = SecretScanSensor()
        assert (sensor.id, sensor.routine_ids, sensor.resolution_scope) == ("secret-scan", (16, 14), "exhaustive")

    def test_clean_repository_produces_nothing(self, tmp_path: Path) -> None:
        _, observations = _secrets(tmp_path, {"src/a.py": "TOKEN = os.environ['TOKEN']\n"})
        assert observations == []

    @pytest.mark.parametrize(
        "pattern, token",
        [
            ("aws-access-key-id", _aws_key()),
            ("github-token", _github_token()),
            ("github-fine-grained-token", "github" + "_pat_" + _seeded("pat", 82)),
            ("anthropic-api-key", "sk" + "-ant-" + _seeded("ant", 40)),
            ("openai-api-key", _openai_key()),
            ("slack-token", "xox" + "b-" + _seeded("slack", 24)),
            ("private-key-block", _private_key_header()),
            ("google-api-key", "AI" + "za" + _seeded("goog", 35)),
        ],
    )
    def test_each_family_is_found_without_storing_the_match(
        self, tmp_path: Path, pattern: str, token: str
    ) -> None:
        _, observations = _secrets(tmp_path, {"src/config.py": f"value = '{token}'\n"})
        (item,) = observations
        assert item.kind == "credential_leak"
        assert item.subject.id == "src/config.py"
        (finding,) = item.observed_state["findings"]
        assert finding == {
            "line": 1,
            "pattern": pattern,
            "fingerprint": hashlib.sha256(token.encode()).hexdigest()[:12],
        }
        assert token not in _dumps(observations)
        assert item.confidence == (1.0 if pattern == "private-key-block" else 0.9)

    def test_anthropic_key_is_not_double_reported_as_openai(self, tmp_path: Path) -> None:
        token = "sk" + "-ant-" + _seeded("ant", 60)
        _, observations = _secrets(tmp_path, {"src/a.py": f"k = '{token}'\n"})
        assert [item["pattern"] for item in observations[0].observed_state["findings"]] == ["anthropic-api-key"]

    @pytest.mark.parametrize(
        "line",
        [
            "ghp" + "_short",
            "sk" + "-learn-to-code-with-a-long-kebab-case-identifier-name-here-ok",
            "AKIA" + "lowercase0000000000",
            "export PATH=/usr/bin  # nothing here",
            "key = \"" + "A" * 12 + "AKIA" + "ABCDEFGHIJKLMNOP" + "ZZZZ\"",
        ],
    )
    def test_near_misses_are_not_reported(self, tmp_path: Path, line: str) -> None:
        _, observations = _secrets(tmp_path, {"src/a.py": line + "\n"})
        assert observations == []

    def test_synthetic_test_fixture_is_exempt_and_counted(self, tmp_path: Path) -> None:
        token = "AKIA" + "IOSFODNN7" + "EXAMPLE"
        files = {
            "tests/test_scanner.py": f"SAMPLE = '{token}'\n",
            "src/real.py": f"k = '{_github_token()}'\n",
        }
        _, observations = _secrets(tmp_path, files)
        (item,) = observations
        assert item.subject.id == "src/real.py"
        assert item.provenance["skippedSyntheticTestFixture"] == 1

    def test_ascending_placeholder_in_tests_is_exempt(self, tmp_path: Path) -> None:
        placeholder = "ghp" + "_" + "abcdef" + "0123456789" + "abcdefghijklmnopqrst"[:20]
        _, observations = _secrets(tmp_path, {"tests/test_a.py": f"t = '{placeholder}'\n"})
        assert observations == []

    def test_exemption_does_not_apply_outside_tests(self, tmp_path: Path) -> None:
        token = "AKIA" + "IOSFODNN7" + "EXAMPLE"
        _, observations = _secrets(tmp_path, {"src/a.py": f"SAMPLE = '{token}'\n"})
        assert len(observations) == 1

    def test_real_looking_secret_in_tests_is_still_reported(self, tmp_path: Path) -> None:
        _, observations = _secrets(tmp_path, {"tests/test_a.py": f"t = '{_github_token('real')}'\n"})
        assert len(observations) == 1

    def test_non_utf8_file_is_still_scanned_and_oversize_is_reported(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        # Previously both were silently skipped and counted; a leak hidden by a
        # stray byte or by growth past the ceiling simply vanished.
        monkeypatch.setattr(sensors_security, "_SECRET_MAX_BYTES", 1024 * 1024)
        files: dict[str, str | bytes] = {
            "src/real.py": f"k = '{_github_token()}'\n",
            "assets/blob.bin": b"\xff\xfe\x00" + _github_token("blob").encode(),
            "assets/big.txt": "x" * (1024 * 1024 + 10),
        }
        root, _ = _secrets(tmp_path, files)
        result = SecretScanSensor().scan_detailed(root, NOW)
        assert sorted(item.subject.id for item in result.observations) == ["assets/blob.bin", "src/real.py"]
        item = next(item for item in result.observations if item.subject.id == "src/real.py")
        assert item.provenance["scannedNonUtf8"] == 1
        assert item.provenance["skippedOversize"] == 1
        assert [(entry["subjectId"], entry["subjectType"]) for entry in result.skipped] == [
            ("assets/big.txt", "source-file")
        ]

    def test_appending_a_non_utf8_byte_does_not_hide_a_leak(self, tmp_path: Path) -> None:
        text = f"k = '{_github_token()}'\n".encode()
        _, observations = _secrets(tmp_path, {"src/a.py": text + b"\xff"})
        assert [item.subject.id for item in observations] == ["src/a.py"]

    def test_findings_are_sorted_and_aggregated_per_file(self, tmp_path: Path) -> None:
        source = f"b = '{_aws_key('two')}'\na = '{_github_token('one')}'\n"
        _, observations = _secrets(tmp_path, {"src/a.py": source})
        (item,) = observations
        assert [finding["line"] for finding in item.observed_state["findings"]] == [1, 2]
        assert item.observed_state["patternCounts"] == {"aws-access-key-id": 1, "github-token": 1}

    def test_repeat_scan_is_identical(self, tmp_path: Path) -> None:
        root, first = _secrets(tmp_path, {"src/a.py": f"k = '{_github_token()}'\n"})
        assert _dumps(first) == _dumps(SecretScanSensor().scan(root, NOW))

    def test_recovery_after_secret_removed(self, tmp_path: Path) -> None:
        root, first = _secrets(tmp_path, {"src/a.py": f"k = '{_github_token()}'\n"})
        assert len(first) == 1
        write_files(root, {"src/a.py": "k = os.environ['K']\n"})
        commit_all(root)
        assert SecretScanSensor().scan(root, NOW) == []

    def test_untracked_secret_file_is_not_inventoried(self, tmp_path: Path) -> None:
        root, _ = _secrets(tmp_path, {})
        (root / "scratch.env").write_text(f"k={_github_token()}\n", encoding="utf-8")
        assert SecretScanSensor().scan(root, NOW) == []

    def test_non_git_directory_is_unavailable(self, tmp_path: Path) -> None:
        plain = tmp_path / "plain"
        plain.mkdir()
        (plain / "a.txt").write_text("x", encoding="utf-8")
        with pytest.raises(SensorUnavailable):
            SecretScanSensor().scan(plain, NOW)

    def test_empty_inventory_is_unavailable(self, tmp_path: Path) -> None:
        root = tmp_path / "empty"
        root.mkdir()
        import subprocess

        subprocess.run(["git", "-C", str(root), "init", "-q"], check=True)
        with pytest.raises(SensorUnavailable, match="empty"):
            SecretScanSensor().scan(root, NOW)

    def test_truncated_inventory_is_unavailable(self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
        root, _ = _secrets(tmp_path, {"src/a.py": "x = 1\n"})
        from gaia_cli.steward.primitives import files as primitives

        real = primitives._git
        monkeypatch.setattr(
            primitives,
            "_git",
            lambda r, a, *, max_bytes: real(r, a, max_bytes=max_bytes)[:-1] if a[0] == "ls-files" else real(r, a, max_bytes=max_bytes),
        )
        with pytest.raises(SensorUnavailable, match="truncated"):
            SecretScanSensor().scan(root, NOW)

    def test_sensor_writes_nothing(self, tmp_path: Path) -> None:
        root, _ = _secrets(tmp_path, {"src/a.py": f"k = '{_github_token()}'\n"})
        before = tree_digest(root)
        SecretScanSensor().scan(root, NOW)
        assert tree_digest(root) == before

    def test_this_test_module_contains_no_credential_literal(self) -> None:
        text = Path(__file__).read_text(encoding="utf-8")
        assert not [name for name, pattern in _SECRET_PATTERNS if pattern.search(text)]
