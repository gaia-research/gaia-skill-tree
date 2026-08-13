from __future__ import annotations

import json
import shutil
import subprocess
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
    subprocess.run(["git", "init", "-q"], cwd=root, check=True)
    subprocess.run(["git", "add", "."], cwd=root, check=True)
    subprocess.run(
        ["git", "-c", "user.name=fixture", "-c", "user.email=fixture@example.test", "commit", "-qm", "base"],
        cwd=root,
        check=True,
    )


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
    assert payload["receipt"]["observationsCollected"] == 7
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
    canonical = tmp_path / "registry/schema/skill.schema.json"
    canonical.write_text('{"type":"string"}\n', encoding="utf-8")
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "steward", "run", "--json"])

    main()

    payload = json.loads(capsys.readouterr().out)
    repair = payload["receipt"]["repairs"][0]
    assert payload["receipt"]["result"]["status"] == "repaired"
    assert repair["status"] == "repaired"
    assert repair["verified"] == {"recursiveParity": True, "syncCheck": True}
    assert repair["resolved"] is True
    assert (tmp_path / "src/gaia_cli/data/registry/schema/skill.schema.json").read_bytes() == canonical.read_bytes()


def test_steward_founder_cli_outputs_controlled_current_nonempty_report_only_queue(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_cli_repo(tmp_path)
    _write(tmp_path / ".gaia/steward/discovery-mapping-input.json", json.dumps({
        "schemaVersion": "steward-discovery-mapping-input-v1",
        "candidates": [{
            "candidateId": "example/open-candidate", "sourceRepo": "example/repo",
            "sourceState": "current", "disposition": "unresolved",
        }],
    }))
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "steward", "founder", "--json"])

    main()

    payload = json.loads(capsys.readouterr().out)
    decisions = payload["artifact"]["decisions"]
    assert len(decisions) == 1
    assert decisions[0]["decisionTarget"] == "generic-mapping/example/open-candidate"
    assert len(decisions[0]["debtIds"]) == 1
    assert payload["receipt"]["result"]["status"] == "reported"
    assert not (tmp_path / ".github").exists()


@pytest.mark.parametrize("candidate_id", ["zzreview/ſ", "owner/K", "owner/ß"])
def test_steward_founder_cli_fails_closed_for_non_ascii_controlled_candidate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    candidate_id: str,
) -> None:
    _clean_cli_repo(tmp_path)
    _write(tmp_path / ".gaia/steward/discovery-mapping-input.json", json.dumps({
        "schemaVersion": "steward-discovery-mapping-input-v1",
        "candidates": [{
            "candidateId": candidate_id, "sourceRepo": "owner/repo",
            "sourceState": "current", "disposition": "unresolved",
        }],
    }))
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(tmp_path), "steward", "founder", "--json"])

    with pytest.raises(SystemExit) as exc:
        main()

    output = capsys.readouterr()
    assert exc.value.code == 2
    assert output.out == ""
    assert "Steward founder failed: sensor coverage is unknown; refusing routing: discovery-generic-mapping" in output.err
    assert not (tmp_path / ".gaia/steward/debt.json").exists()
    assert not list((tmp_path / ".gaia/steward/receipts").glob("*.json"))


def test_steward_routing_commands_are_public_and_parse_json_access() -> None:
    parser, _ = get_parser()

    dispatch = parser.parse_args(
        ["--registry", str(REPO_ROOT), "steward", "dispatch", "debt:fixture", "--json"]
    )
    founder = parser.parse_args(["--registry", str(REPO_ROOT), "steward", "founder", "--json"])

    assert dispatch.steward_command == "dispatch"
    assert dispatch.debt_id == "debt:fixture"
    assert dispatch.json is True
    assert founder.steward_command == "founder"
    assert founder.json is True


def test_steward_rejects_unknown_subcommand() -> None:
    parser, _ = get_parser()

    with pytest.raises(SystemExit) as exc:
        parser.parse_args(["--registry", str(REPO_ROOT), "steward", "repair"])

    assert exc.value.code == 2


# --- V1.2: Tree Keeper prompt from the CLI ------------------------------------


def _open_class_b_debt(root: Path, monkeypatch: pytest.MonkeyPatch, capsys) -> str:
    """Introduce one real Class B integrity violation and return its debt id."""

    _write(
        root / "registry/nodes/basic/broken.json",
        json.dumps(
            {
                "id": "broken",
                "type": "fusion",
                "prerequisites": ["does-not-exist"],
                "derivatives": [],
            }
        ),
    )
    monkeypatch.setattr(sys, "argv", ["gaia", "--registry", str(root), "steward", "scan", "--json"])
    main()
    payload = json.loads(capsys.readouterr().out)
    open_debt = payload["receipt"]["openDebt"]
    assert len(open_debt) == 1, open_debt
    return open_debt[0]


def test_steward_dispatch_prompt_prints_only_the_pasteable_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_cli_repo(tmp_path)
    debt_id = _open_class_b_debt(tmp_path, monkeypatch, capsys)
    monkeypatch.setattr(
        sys,
        "argv",
        ["gaia", "--registry", str(tmp_path), "steward", "dispatch", debt_id, "--prompt"],
    )

    main()

    output = capsys.readouterr().out
    # No status banner may precede the prompt: the whole stdout is the paste.
    assert output.startswith("# Tree Keeper dispatch")
    assert "Class B — bounded autonomous repair" in output
    assert "founder/steward/routines/registry-integrity-review.md" in output
    assert "does-not-exist" in output
    assert "Reasoning calls granted by Steward: **0**" in output
    assert "Gaia Steward dispatch" not in output


def test_steward_dispatch_prompt_json_carries_packet_receipt_and_prompt(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    _clean_cli_repo(tmp_path)
    debt_id = _open_class_b_debt(tmp_path, monkeypatch, capsys)
    monkeypatch.setattr(
        sys,
        "argv",
        ["gaia", "--registry", str(tmp_path), "steward", "dispatch", debt_id, "--prompt", "--json"],
    )

    main()

    payload = json.loads(capsys.readouterr().out)
    assert payload["artifact"]["authority"] == "B"
    assert payload["artifact"]["budget"] == {"modelCalls": 0, "maxTokens": 0, "maxMinutes": 0}
    assert payload["receipt"]["result"]["status"] == "reported"
    assert payload["receipt"]["models"] == []
    assert payload["artifact"]["dispatchId"] in payload["prompt"]
    # Rendering a prompt must not create a second dispatch surface.
    assert payload["receipt"]["repairs"] == []
    assert not (tmp_path / ".github").exists()
