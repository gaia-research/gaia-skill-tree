"""Focused sequential discovery-chain regression tests."""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.curation.orchestrator import CurationOrchestrator
from gaia_cli.curation.state import CurationRun


def inventory(count: int):
    return [{"candidateId": f"owner/repo/skill-{i}", "namedIdentity": f"owner/skill-{i}",
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


@pytest.mark.parametrize("count", [1, 5])
def test_default_processor_uses_real_prefill_path_with_frozen_source(tmp_path, monkeypatch, count):
    import gaia_cli.prefill as prefill
    from gaia_cli.curation.orchestrator import CurationOrchestrator
    source_text = "---\nname: Actual Source Skill\ndescription: A realistic source description for processing.\n---\nbody\n"
    monkeypatch.setattr(prefill, "fetchCandidateSource", lambda url, fetcher=None: (
        "https://github.com/owner/repo", "https://raw.invalid/SKILL.md", source_text,
        __import__("hashlib").sha256(source_text.encode()).hexdigest()))
    monkeypatch.setattr(prefill, "embeddingStatus", lambda **kwargs: {"status": "fresh"})
    monkeypatch.setattr(prefill, "load_embeddings", lambda _path: {
        "model": "test", "dimensions": 2, "entries": [{"id": "generic-skill", "vector": [1.0, 0.0]}]})
    monkeypatch.setattr(prefill, "embed_query", lambda *args, **kwargs: [1.0, 0.0])
    monkeypatch.setattr(prefill, "search_precomputed", lambda *args, **kwargs: [{"id": "generic-skill", "score": 0.9}])
    # Required artifact presence is mocked, while the default processor, command,
    # packet construction, persistence and reconciliation all execute normally.
    reg = tmp_path / "repo"
    (reg / "graph").mkdir(parents=True)
    (reg / "graph/embeddings.json").write_text("{}")
    (reg / "registry/nodes").mkdir(parents=True)
    (reg / "registry/named").mkdir()  # Complete, explicitly empty named catalog.
    (reg / "registry/nodes/generic.json").write_text(json.dumps({"id": "generic-skill", "name": "Generic Skill"}))
    candidates = [{"candidateId": f"owner/repo/skill-{i}", "namedIdentity": f"owner/skill-{i}",
                  "sourceUrl": f"https://github.com/owner/repo/blob/main/skills/{i}/SKILL.md"}
                 for i in range(count)]
    run = CurationRun(run_id=f"real-{count}", inventory=candidates)
    orchestrator = CurationOrchestrator(run, registry_path=str(reg), save_path=tmp_path / f"{count}.json")
    orchestrator.run_to_next_gate()
    assert run.current_state == "AWAITING_L4_REVIEW"
    assert len(run.checkpoint["results"]) == count
    assert run.checkpoint["reconciliation"]["accounted"] is True
    assert run.checkpoint["reconciliation"]["humanApproved"] is False
    assert all(r["packetSha256"] and r["assessmentSha256"] for r in run.checkpoint["results"])
    for result in run.checkpoint["results"]:
        receipt = result["receipt"]
        assert receipt["assessmentSha256"] == result["assessmentSha256"]
        assert receipt["assessmentPath"]
        assessment_bytes = (reg / receipt["assessmentPath"]).read_bytes()
        assert __import__("hashlib").sha256(assessment_bytes).hexdigest() == receipt["assessmentSha256"]
    report = run.checkpoint["reconciliation"]
    assert report["counts"]["deferred"] == count  # Honest prefill, awaiting semantic/human review.
    assert all(row["reason"] == "PREFILL_AWAITING_WORKER" for row in report["decisions"])
    if count == 1:
        from gaia_cli.commands.curate import CurateCommand
        result = run.checkpoint["results"][0]
        packet_path, assessment_path = Path(result["packetPath"]), reg / result["receipt"]["assessmentPath"]
        original_packet, original_assessment = packet_path.read_bytes(), assessment_path.read_bytes()
        assert CurateCommand._freshness(run, str(reg)) == []
        packet_path.write_bytes(original_packet + b" ")
        assert any("digest mismatch" in error for error in CurateCommand._freshness(run, str(reg)))
        packet_path.write_bytes(original_packet)
        assessment_path.write_bytes(original_assessment + b" ")
        assert any("digest mismatch" in error for error in CurateCommand._freshness(run, str(reg)))
        assessment_path.write_bytes(original_assessment)
        run.inventory[0]["packetInput"]["sourceContent"] += "tampered"
        assert any("frozen source bytes" in error for error in CurateCommand._freshness(run, str(reg)))


def test_partial_source_preparation_resume_does_not_refetch_completed_candidate(tmp_path, monkeypatch):
    import hashlib
    import gaia_cli.prefill as prefill
    source = "---\nname: Prepared\ndescription: A source description with enough detail.\n---\nbody\n"
    digest = hashlib.sha256(source.encode()).hexdigest()
    calls = []
    fail_second = True
    def fetch(url, fetcher=None):
        nonlocal fail_second
        calls.append(url)
        if url.endswith("/1/SKILL.md") and fail_second:
            return "", "", None, None
        return "https://github.com/owner/repo", "https://raw.invalid/SKILL.md", source, digest
    monkeypatch.setattr(prefill, "fetchCandidateSource", fetch)
    monkeypatch.setattr(prefill, "buildGenericSnapshot", lambda _registry: {"generics": []})
    monkeypatch.setattr(prefill, "parseFrontmatter", lambda _content: {
        "name": "Prepared", "description": "A source description with enough detail."})
    run = CurationRun(run_id="partial-prep", inventory=inventory(2))
    worker = CurationOrchestrator(run, save_path=tmp_path / "state.json")
    processed = []
    worker._process = lambda candidate: (processed.append(candidate["candidateId"]) or {
        "candidateId": candidate["candidateId"], "packetSha256": "packet"})
    with pytest.raises(ValueError, match="source fetch unavailable"):
        worker.run_to_next_gate()
    assert run.checkpoint["preparationAttempts"] == {"owner/repo/skill-0": 1, "owner/repo/skill-1": 1}
    assert len(run.checkpoint["preparedSources"]) == 1
    fail_second = False
    worker.retry_candidate()
    assert calls.count(inventory(2)[0]["sourceUrl"]) == 1
    assert calls.count(inventory(2)[1]["sourceUrl"]) == 2
    assert processed == [row["candidateId"] for row in inventory(2)]
    assert run.current_state == "AWAITING_L4_REVIEW"


def test_candidate_retry_limit_is_bounded(tmp_path):
    def fail(candidate, _registry):
        raise RuntimeError("persistent stage failure")
    run = CurationRun(run_id="bounded", inventory=inventory(1))
    worker = CurationOrchestrator(run, save_path=tmp_path / "state.json", processor=fail)
    for attempt in range(3):
        with pytest.raises(RuntimeError, match="persistent stage failure"):
            worker.run_to_next_gate() if attempt == 0 else worker.retry_candidate()
    with pytest.raises(RuntimeError, match="retry budget exhausted"):
        worker.retry_candidate()
    assert run.checkpoint["attempts"]["0"] == 3


def test_global_processing_attempt_budget_stops_dispatch(tmp_path, monkeypatch):
    import gaia_cli.curation.orchestrator as module
    monkeypatch.setattr(module, "MAX_PROCESSING_ATTEMPTS", 2)
    calls = []
    def fail(candidate, _registry):
        calls.append(candidate["candidateId"])
        raise RuntimeError("bounded failure")
    run = CurationRun(run_id="global-budget", inventory=inventory(2))
    worker = CurationOrchestrator(run, save_path=tmp_path / "state.json", processor=fail)
    with pytest.raises(RuntimeError, match="bounded failure"):
        worker.run_to_next_gate()
    with pytest.raises(RuntimeError, match="bounded failure"):
        worker.retry_candidate()
    worker.retry_candidate()
    assert calls == [inventory(2)[0]["candidateId"]] * 2
    assert run.current_state == "AWAITING_L4_REVIEW"
    assert run.checkpoint["budgetExhausted"] is True


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
    assert any("verification failed" in row["summary"] for row in loaded.checkpoint["blockers"])
    assert loaded.current_state == "AWAITING_L4_REVIEW"
