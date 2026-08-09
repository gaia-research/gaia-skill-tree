from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import pytest

from gaia_cli.commands import discover_commands
from gaia_cli.main import PUBLIC_COMMANDS, get_parser, main
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH


REPO_ROOT = Path(__file__).resolve().parents[2]


def _write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")


def _clean_cli_repo(root: Path) -> None:
    policy = root / POLICY_RELATIVE_PATH
    policy.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / POLICY_RELATIVE_PATH, policy)
    sync_script = root / "scripts/sync_bundled_schemas.py"
    sync_script.parent.mkdir(parents=True)
    shutil.copyfile(REPO_ROOT / "scripts/sync_bundled_schemas.py", sync_script)
    schema = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "required": ["id", "type", "prerequisites", "derivatives"],
        "properties": {
            "id": {"type": "string"},
            "type": {"enum": ["basic", "fusion"]},
            "prerequisites": {"type": "array", "items": {"type": "string"}},
            "derivatives": {"type": "array", "items": {"type": "string"}},
        },
    }
    schema_text = json.dumps(schema, sort_keys=True)
    _write(root / "registry/schema/skill.schema.json", schema_text)
    _write(root / "src/gaia_cli/data/registry/schema/skill.schema.json", schema_text)
    meta_text = json.dumps({"types": {"minPrereqs": {"basic": 0, "fusion": 1}}})
    _write(root / "registry/schema/meta.json", meta_text)
    _write(root / "src/gaia_cli/data/registry/schema/meta.json", meta_text)
    node = {"id": "example", "type": "basic", "prerequisites": [], "derivatives": []}
    _write(root / "registry/nodes/basic/example.json", json.dumps(node))
    _write(root / ".agents/skills/example/SKILL.md", "# Example\n")
    _write(root / ".claude/skills/example/SKILL.md", "# Example\n")


def test_steward_is_dynamically_discovered_and_in_public_help() -> None:
    commands = discover_commands()
    parser, _ = get_parser()
    choices = parser._subparsers._group_actions[0].choices

    assert "steward" in commands
    assert "steward" in PUBLIC_COMMANDS
    assert "steward" in choices


def test_steward_scan_json_cli_is_clean_and_report_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_cli_repo(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["gaia", "--registry", str(tmp_path), "steward", "scan", "--json"],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["receipt"]["result"]["status"] == "no_change"
    assert payload["receipt"]["observationsCollected"] == 6
    assert payload["receipt"]["dispatches"] == []
    assert payload["receipt"]["repairs"] == []
    assert payload["state"]["debt"].startswith(str(tmp_path / ".gaia/steward"))


def test_steward_scan_human_output_is_concise(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_cli_repo(tmp_path)
    monkeypatch.setattr(
        sys,
        "argv",
        ["gaia", "--registry", str(tmp_path), "steward", "scan"],
    )

    main()

    output = capsys.readouterr().out
    assert "Gaia Steward scan" in output
    assert "Open debt          0" in output
    assert "Model dispatches   0" in output
    assert "Repairs            0" in output
    assert ".gaia/steward/receipts/" in output


def test_steward_run_clean_is_a_zero_repair_noop(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_cli_repo(tmp_path)
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "steward", "run", "--json"])

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["receipt"]["result"]["status"] == "no_change"
    assert payload["receipt"]["repairs"] == []
    assert payload["final"] is not None


def test_steward_run_repairs_one_schema_debt_with_receipts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_cli_repo(tmp_path)
    target = tmp_path / "src/gaia_cli/data/registry/schema/skill.schema.json"
    target.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "steward", "run", "--json"])

    main()

    payload = json.loads(capsys.readouterr().out)
    repair = payload["receipt"]["repairs"][0]
    assert payload["receipt"]["result"]["status"] == "repaired"
    assert repair["status"] == "repaired"
    assert repair["verified"] == {"recursiveParity": True, "syncCheck": True}
    assert repair["resolved"] is True
    assert target.read_bytes() == (tmp_path / "registry/schema/skill.schema.json").read_bytes()


def test_steward_rejects_unknown_subcommand() -> None:
    parser, _ = get_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--registry", str(REPO_ROOT), "steward", "repair"])

    assert exc.value.code == 2
