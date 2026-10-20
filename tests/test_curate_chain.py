"""Focused sequential discovery-chain regression tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.curation.orchestrator import CurationOrchestrator
from gaia_cli.curation.state import CurationRun


def inventory(count: int):
    return [{"candidateId": f"owner/repo/skill-{i}", "namedIdentity": f"Owner/Skill {i}",
             "sourceUrl": f"https://github.com/owner/repo/blob/main/skills/{i}/SKILL.md"}
            for i in range(count)]


def test_cli_accepts_bounded_frozen_inventory_and_preserves_external_refs(tmp_path, monkeypatch):
    from argparse import ArgumentParser
    from gaia_cli.commands.curate import CurateCommand
    monkeypatch.chdir(tmp_path)
    source = tmp_path / "inventory.json"
    source.write_text(json.dumps({"inventorySha256": "frozen", "candidates": inventory(1)}))
    command = CurateCommand()
    parser = ArgumentParser()
    command.configure(parser)
    args = parser.parse_args(["--inventory", str(source), "--batch-id", "batch-7",
                              "--intake-issue-number", "88", "--dry-run"])
    assert command.execute(args) == 0
    state_files = list((tmp_path / ".gaia/curation/runs").glob("*/state.json"))
    run = CurationRun.load(state_files[0])
    assert len(run.inventory) == 1
    assert run.external_refs["batch_id"] == "batch-7"
    assert run.external_refs["intake_issue_number"] == 88


def test_single_candidate_sequentially_checkpoints_then_waits_for_l4(tmp_path):
    seen = []
    def process(candidate, registry):
        seen.append(candidate["candidateId"])
        return {"candidateId": candidate["candidateId"], "packetPath": f"{candidate['candidateId']}.json",
                "packetSha256": "p", "assessmentSha256": "a"}
    run = CurationRun(run_id="one", inventory=inventory(1))
    state = tmp_path / "state.json"
    orchestrator = CurationOrchestrator(run, save_path=state, processor=process)
    orchestrator.run_to_next_gate()
    assert run.current_state == "AWAITING_L4_REVIEW"
    assert seen == ["owner/repo/skill-0"]
    assert len(run.checkpoint["results"]) == 1
    assert json.loads(state.read_text())["current_state"] == "AWAITING_L4_REVIEW"


def test_five_candidates_are_processed_deterministically_and_existing_intake_is_handoff(tmp_path):
    seen = []
    def process(candidate, _registry):
        seen.append(candidate["candidateId"])
        return {"candidateId": candidate["candidateId"], "packetSha256": "p", "assessmentSha256": "a"}
    run = CurationRun(run_id="five", inventory=inventory(5))
    run.external_refs.update(batch_id="batch-existing", intake_issue_number=431, intake_issue_url="https://example.invalid/431")
    CurationOrchestrator(run, save_path=tmp_path / "state.json", processor=process).run_to_next_gate()
    assert seen == [row["candidateId"] for row in inventory(5)]
    assert len(run.checkpoint["results"]) == 5
    assert run.checkpoint["handoff"] == {"status": "AWAITING_L4_REVIEW", "batchId": "batch-existing",
                                         "intakeIssueNumber": 431, "intakeIssueUrl": "https://example.invalid/431",
                                         "downstream": "existing intake only"}


def test_retry_reprocesses_only_failed_candidate_and_preserves_prior_checkpoint(tmp_path):
    calls = []
    def process(candidate, _registry):
        calls.append(candidate["candidateId"])
        if candidate["candidateId"].endswith("skill-1") and calls.count(candidate["candidateId"]) == 1:
            raise RuntimeError("transient source failure")
        return {"candidateId": candidate["candidateId"], "packetSha256": "p", "assessmentSha256": "a"}
    run = CurationRun(run_id="retry", inventory=inventory(3))
    worker = CurationOrchestrator(run, save_path=tmp_path / "state.json", processor=process)
    with pytest.raises(RuntimeError, match="transient"):
        worker.run_to_next_gate()
    assert run.checkpoint["inventoryIndex"] == 1
    assert run.checkpoint["results"][0]["candidateId"] == "owner/repo/skill-0"
    worker.retry_candidate()
    assert calls == ["owner/repo/skill-0", "owner/repo/skill-1", "owner/repo/skill-1", "owner/repo/skill-2"]
    assert len(run.checkpoint["results"]) == 3


def test_local_decision_json_never_crosses_l4_gate(tmp_path):
    run = CurationRun(run_id="gate", current_state="AWAITING_L4_REVIEW", inventory=inventory(1))
    run.decisions["l4_resolution"] = {"approved": True, "target": "pretend"}
    worker = CurationOrchestrator(run, save_path=tmp_path / "state.json", processor=lambda *_: pytest.fail("must not process"))
    worker.run_to_next_gate()
    assert run.current_state == "AWAITING_L4_REVIEW"


def test_resume_with_packet_fails_closed_if_freshness_interface_unavailable(tmp_path, monkeypatch):
    from gaia_cli.commands.curate import CurateCommand
    from argparse import ArgumentParser
    monkeypatch.chdir(tmp_path)
    run = CurationRun(run_id="fresh", current_state="AWAITING_L4_REVIEW")
    run.checkpoint["results"] = [{"packetPath": "missing.json"}]
    run.save(run.run_dir)
    command = CurateCommand()
    parser = ArgumentParser()
    command.configure(parser)
    assert command.execute(parser.parse_args(["--resume", "fresh"])) == 0
    loaded = CurationRun.load(run.run_dir)
    assert any("freshness verifier is unavailable" in row["summary"] for row in loaded.checkpoint["blockers"])
    assert loaded.current_state == "AWAITING_L4_REVIEW"
