"""Steward V1.4 — the first wired Class B sensor: CLI command-surface drift."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil

import pytest

from gaia_cli.steward.cli_contract import (
    CliContractError,
    discovered_commands,
    documented_commands,
    public_commands,
)
from gaia_cli.steward.sensors import CliContractSensor


REPO_ROOT = Path(__file__).resolve().parents[2]
OBSERVED_AT = "2026-08-13T00:00:00Z"


def _checkout(tmp_path: Path, *, commands: dict[str, str], public: str, contract: str | None) -> Path:
    package = tmp_path / "src/gaia_cli/commands"
    package.mkdir(parents=True)
    (package / "__init__.py").write_text("", encoding="utf-8")
    (package / "base.py").write_text("class Command:\n    name = 'never-a-command'\n", encoding="utf-8")
    for module, source in commands.items():
        (package / f"{module}.py").write_text(source, encoding="utf-8")
    (tmp_path / "src/gaia_cli/impl.py").write_text(public, encoding="utf-8")
    if contract is not None:
        (tmp_path / "CLAUDE.md").write_text(contract, encoding="utf-8")
    return tmp_path


def _one(name: str, class_name: str = "Thing") -> str:
    return (
        f"class {class_name}(Command):\n"
        f"    name = \"{name}\"\n"
        f"\n\nCOMMAND = {class_name}()\n"
    )


# --- reading the three declarations ------------------------------------------


def test_the_real_checkout_surface_is_readable_without_importing_it() -> None:
    """The sensor must never import the code it audits.

    Importing reports on the installed package rather than the checkout in
    front of it, and executes arbitrary repository code to do so.
    """

    discovered = discovered_commands(REPO_ROOT)
    assert "steward" in discovered and discovered["steward"] == "steward"
    assert "dev" in discovered  # a package, not a module
    assert "trust" in discovered  # exported via a COMMANDS list
    assert "base" not in discovered

    public = public_commands(REPO_ROOT)
    assert "help" in public and "steward" in public

    documented = documented_commands(REPO_ROOT)
    assert documented is not None and "init" in documented


def test_both_export_conventions_are_understood(tmp_path: Path) -> None:
    root = _checkout(
        tmp_path,
        commands={
            "single": _one("alpha", "Alpha"),
            "many": (
                'class Beta(Command):\n    name = "beta"\n'
                '\n\nclass Gamma(Command):\n    name = "gamma"\n'
                "\n\nCOMMANDS = [Beta(), Gamma()]\n"
            ),
        },
        public='PUBLIC_COMMANDS = ("alpha", "beta", "gamma", "help")\n',
        contract="Top-level (lifecycle-oriented): `alpha`, `beta`, `gamma`, `help`.\n",
    )
    assert discovered_commands(root) == {"alpha": "single", "beta": "many", "gamma": "many"}


def test_a_surface_that_cannot_be_read_is_reported_not_ignored(tmp_path: Path) -> None:
    """An unreadable declaration is drift, not an absence of drift.

    Silently skipping a command whose name is computed would make the sensor
    agree with itself: it would report a consistent surface precisely because
    it could not see the inconsistent part.
    """

    root = _checkout(
        tmp_path,
        commands={"weird": 'class Weird(Command):\n    name = NAMES[0]\n\n\nCOMMAND = Weird()\n'},
        public='PUBLIC_COMMANDS = ("help",)\n',
        contract="Top-level (lifecycle-oriented): `help`.\n",
    )
    with pytest.raises(CliContractError, match="no literal `name`"):
        discovered_commands(root)


@pytest.mark.parametrize(
    "public, message",
    [
        ('PUBLIC_COMMANDS = [x for x in y]\n', "literal tuple or list"),
        ('PUBLIC_COMMANDS = ("ok", 3)\n', "only string literals"),
        ('SOMETHING_ELSE = ()\n', "declares no PUBLIC_COMMANDS"),
    ],
)
def test_an_unreadable_public_declaration_fails_closed(tmp_path: Path, public: str, message: str) -> None:
    root = _checkout(tmp_path, commands={"a": _one("alpha")}, public=public, contract=None)
    with pytest.raises(CliContractError, match=message):
        public_commands(root)


# --- what the sensor reports -------------------------------------------------


def _observe(root: Path):
    return CliContractSensor().scan(root, OBSERVED_AT)[0]


def test_a_consistent_surface_is_healthy_and_says_nothing(tmp_path: Path) -> None:
    root = _checkout(
        tmp_path,
        commands={"a": _one("alpha")},
        public='PUBLIC_COMMANDS = ("help", "alpha")\n',
        contract="Top-level (lifecycle-oriented): `alpha`, `help`.\n",
    )
    observation = _observe(root)
    assert observation.status == "healthy"
    assert observation.observed_state["violationCount"] == 0


def test_a_dispatchable_command_missing_from_help_is_undiscoverable(tmp_path: Path) -> None:
    root = _checkout(
        tmp_path,
        commands={"a": _one("alpha"), "b": _one("beta", "Beta")},
        public='PUBLIC_COMMANDS = ("help", "alpha")\n',
        contract="Top-level (lifecycle-oriented): `alpha`, `help`.\n",
    )
    observation = _observe(root)
    assert observation.status == "drift"
    assert observation.observed_state["violations"] == [
        {"kind": "undiscoverable", "command": "beta", "detail": "defined in b, absent from PUBLIC_COMMANDS"}
    ]


def test_help_advertising_a_command_with_nothing_behind_it_is_drift(tmp_path: Path) -> None:
    root = _checkout(
        tmp_path,
        commands={"a": _one("alpha")},
        public='PUBLIC_COMMANDS = ("help", "alpha", "ghost")\n',
        contract="Top-level (lifecycle-oriented): `alpha`, `help`.\n",
    )
    violations = _observe(root).observed_state["violations"]
    assert violations == [
        {
            "kind": "advertised-but-absent",
            "command": "ghost",
            "detail": "listed in PUBLIC_COMMANDS with no command behind it",
        }
    ]


def test_help_is_the_one_declared_builtin_and_is_never_reported_missing(tmp_path: Path) -> None:
    """`main()` registers `help` on the parser directly; it has no module."""

    root = _checkout(
        tmp_path,
        commands={"a": _one("alpha")},
        public='PUBLIC_COMMANDS = ("help", "alpha")\n',
        contract="Top-level (lifecycle-oriented): `alpha`, `help`.\n",
    )
    assert _observe(root).status == "healthy"


def test_documented_but_absent_is_reported_and_the_reverse_is_not(tmp_path: Path) -> None:
    """The contract's list is a curated lifecycle subset, so only one direction
    is a lie about the CLI. Reporting "present but undocumented" would bury the
    real finding under every deliberate editorial omission.
    """

    root = _checkout(
        tmp_path,
        commands={"a": _one("alpha"), "b": _one("beta", "Beta")},
        public='PUBLIC_COMMANDS = ("help", "alpha", "beta")\n',
        contract="Top-level (lifecycle-oriented): `alpha`, `retired`, `help`.\n",
    )
    violations = _observe(root).observed_state["violations"]
    assert [item["command"] for item in violations] == ["retired"]
    assert violations[0]["kind"] == "documented-but-absent"


def test_a_contract_that_stopped_describing_the_cli_is_its_own_finding(tmp_path: Path) -> None:
    root = _checkout(
        tmp_path,
        commands={"a": _one("alpha")},
        public='PUBLIC_COMMANDS = ("help", "alpha")\n',
        contract="This document no longer says anything about commands.\n",
    )
    observation = _observe(root)
    assert observation.status == "drift"
    assert observation.observed_state["contract"] == "absent"
    assert observation.observed_state["violations"][0]["kind"] == "contract-missing"


def test_the_sensor_is_deterministic_and_names_its_own_sources(tmp_path: Path) -> None:
    root = _checkout(
        tmp_path,
        commands={"a": _one("alpha"), "b": _one("beta", "Beta")},
        public='PUBLIC_COMMANDS = ("help", "alpha")\n',
        contract="Top-level (lifecycle-oriented): `alpha`, `gone`, `help`.\n",
    )
    first, second = _observe(root), _observe(root)
    assert first.to_dict() == second.to_dict()
    assert first.provenance == {
        "commandsPath": "src/gaia_cli/commands",
        "publicPath": "src/gaia_cli/impl.py",
        "contractPath": "CLAUDE.md",
    }
    # Sorted by kind then command, so a receipt diff is readable.
    assert [item["command"] for item in first.observed_state["violations"]] == ["gone", "beta"]


def test_the_sensor_is_wired_into_the_default_set_and_policy_can_route_it() -> None:
    from gaia_cli.steward.controller import StewardController
    from gaia_cli.steward.policy import StewardPolicy

    assert any(sensor.id == "cli-contract" for sensor in StewardController().sensors)
    rule = StewardPolicy.load(REPO_ROOT).dispatch_rule_for("cli_contract_drift")
    assert rule is not None
    assert rule.prompt_guide == "founder/steward/routines/cli-contract-drift.md"
    # The routine may repair code, never the document it is auditing: deciding
    # what the agent contract should say is not a bounded repair.
    assert "src/gaia_cli/**" in rule.allowed_paths
    assert "founder/**" in rule.forbidden_paths
