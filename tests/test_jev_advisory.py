"""tests/test_jev_advisory.py — Tests for Jev advisory sidecar adapters, CLI, and mock client.

Verifies:
- Mock client adhering to the shared JevClient contract.
- Read-only adapters across all 6 modes (mapping, issues, upstream, evidence, meta, steward).
- Path validation guarding against writing to canonical registry paths, protected roots, symlinks, or overwriting input.
- Lexical shortlist fallback and Luna fallback on no options, NONE_OF_SHORTLIST, UNCERTAIN, or low confidence (<0.75).
- Steward avoiding fake clean bills on missing fields and inspecting actual scan shapes.
- Preservation of all items on limit exhaustion with fallback packets containing context and questions.
- Dry-run not erasing context and recording zero paid calls.
- Cached responses adding zero new costs.
- Bounded input loading with malformed row preservation and offset pagination.
- CLI argument parsing, clean error handling, and execution with mock client.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Any
import pytest

# Ensure src/ and repo root are importable
_REPO_ROOT = Path(__file__).resolve().parent.parent
_SRC_DIR = _REPO_ROOT / "src"
if str(_SRC_DIR) not in sys.path:
    sys.path.insert(0, str(_SRC_DIR))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from gaia_cli.jevAdvisory import (
    CONFIDENCE_THRESHOLD,
    MAX_INPUT_FILE_BYTES,
    MAX_ITEMS_PER_RUN,
    MAX_REQUEST_BYTES,
    evaluate_evidence_item,
    evaluate_issues_item,
    evaluate_mapping_item,
    evaluate_meta_item,
    evaluate_steward_item,
    evaluate_upstream_item,
    handle_evaluation_result,
    is_canonical_registry_path,
    lexical_shortlist,
    load_generic_nodes,
    load_input,
    rank_duplicate_issue_candidates,
    run_advisory,
    validate_paths,
)
from scripts.jev_advisory import main as cli_main


class MockJevClient:
    """Mock JevClient implementing the shared contract from Worker A."""

    def __init__(
        self,
        stateDir: str = ".gaia/jev",
        *,
        live: bool = False,
        maxCalls: int = 20,
        monthlyLimitUsd: float = 0.5,
        transport: Any = None,
        defaultChoice: str | None = None,
        defaultConfidence: float = 0.9,
        status: str = "advisory",
        reason: str = "ok",
        fallbackAgent: str = "worker-luna",
    ) -> None:
        self.stateDir = stateDir
        self.live = live
        self.maxCalls = maxCalls
        self.monthlyLimitUsd = monthlyLimitUsd
        self.transport = transport
        self.defaultChoice = defaultChoice
        self.defaultConfidence = defaultConfidence
        self.status = status
        self.reason = reason
        self.fallbackAgent = fallbackAgent
        self.calls: list[dict[str, Any]] = []
        self.budgetInitialized = False

    def initializeBudget(self) -> dict[str, Any]:
        self.budgetInitialized = True
        return {"status": "initialized", "month": "2026-08", "limitUsd": self.monthlyLimitUsd}

    def evaluate(self, state: Any, questions: dict[str, Any]) -> dict[str, Any]:
        # Bound assertions per contract
        state_bytes = len(json.dumps(state).encode("utf-8"))
        assert state_bytes <= MAX_REQUEST_BYTES, f"State bytes exceed limit: {state_bytes}"
        assert len(questions) <= 3, f"Too many questions: {len(questions)}"

        if len(self.calls) >= self.maxCalls:
            return {
                "status": "fallback",
                "reason": "limit_reached",
                "answers": {},
                "model": "jev-1.13.0",
                "cached": False,
                "usage": {},
                "estimatedCostUsd": 0.0,
                "reservedUsd": 0.0,
                "fallback": {
                    "agent": self.fallbackAgent,
                    "instruction": "Call limit reached for process. Maintainer or Luna triage required.",
                },
            }

        self.calls.append({"state": state, "questions": questions})

        if self.status == "fallback":
            return {
                "status": "fallback",
                "reason": self.reason,
                "answers": {},
                "model": "jev-1.13.0",
                "cached": False,
                "usage": {},
                "estimatedCostUsd": 0.0,
                "reservedUsd": 0.0,
                "fallback": {
                    "agent": self.fallbackAgent,
                    "instruction": f"Mock fallback triggered: {self.reason}.",
                },
            }

        answers = {}
        for q_id, q_def in questions.items():
            criteria = q_def.get("criteria", {})
            choice = self.defaultChoice if self.defaultChoice in criteria else next(iter(criteria.keys()))
            probs = {opt: 0.0 for opt in criteria}
            probs[choice] = self.defaultConfidence
            rem = max(0.0, 1.0 - self.defaultConfidence)
            other_opts = [o for o in criteria if o != choice]
            if other_opts:
                for o in other_opts:
                    probs[o] = round(rem / len(other_opts), 4)

            answers[q_id] = {
                "type": "choice",
                "choice": choice,
                "confidence": self.defaultConfidence,
                "probabilities": probs,
            }

        return {
            "status": "advisory",
            "reason": self.reason,
            "answers": answers,
            "model": "jev-1.13.0",
            "cached": False,
            "usage": {"input_tokens": 120, "output_tokens": 0},
            "estimatedCostUsd": 0.000005,
            "reservedUsd": 0.003,
        }


# ===========================================================================
# 1. Path validation tests
# ===========================================================================


def test_path_validation_input_equals_output(tmp_path: Path):
    target = str(tmp_path / "same.json")
    with pytest.raises(ValueError, match="must not be the same"):
        validate_paths(target, target)


def test_path_validation_canonical_registry_paths():
    repo_root = str(_REPO_ROOT)
    canonical_paths = [
        os.path.join(repo_root, "registry", "gaia.json"),
        os.path.join(repo_root, "registry", "nodes", "basic", "api-call.json"),
        os.path.join(repo_root, "named-skills.json"),
        os.path.join(repo_root, "package.json"),
    ]
    for p in canonical_paths:
        assert is_canonical_registry_path(p, repo_root) is True
        with pytest.raises(ValueError, match="canonical registry path"):
            validate_paths("some_input.json", p, repo_root)

    safe_output = os.path.join(repo_root, "generated-output", "jev", "report.json")
    assert is_canonical_registry_path(safe_output, repo_root) is False
    validate_paths("some_input.json", safe_output, repo_root)


# ===========================================================================
# 2. Lexical shortlist tests
# ===========================================================================


def test_lexical_shortlist():
    generic_nodes = {
        "api-call": {
            "name": "API Call",
            "description": "Executes HTTP requests and parses JSON responses.",
            "summary": "HTTP API interface.",
        },
        "code-review": {
            "name": "Code Review",
            "description": "Reviews pull requests and analyzes code for bugs.",
            "summary": "Code quality review.",
        },
        "wiki-search": {
            "name": "Wiki Search",
            "description": "Searches documentation and markdown wikis.",
            "summary": "Information retrieval.",
        },
    }

    shortlist = lexical_shortlist("REST Client", "Makes API requests to endpoints", generic_nodes)
    assert len(shortlist) > 0
    assert shortlist[0] == "api-call"

    empty_shortlist = lexical_shortlist("", "", generic_nodes)
    assert empty_shortlist == []


# ===========================================================================
# 3. Mapping mode tests
# ===========================================================================


def test_mapping_with_existing_options():
    packet = {
        "contractVersion": "discovery-packet-v2",
        "candidateId": "anthropic/fetch-api",
        "normalized": {"name": "Fetch API", "description": "Fetches data from remote endpoints."},
        "mappingOptions": [
            {"genericId": "api-call", "similarity": 0.85, "matchTier": "strong"}
        ],
    }
    generic_nodes = {
        "api-call": {"name": "API Call", "description": "Executes HTTP requests."}
    }
    client = MockJevClient(defaultChoice="api-call", defaultConfidence=0.92)

    res = evaluate_mapping_item(packet, client, generic_nodes)
    assert res["status"] == "advisory"
    assert res["advisoryResult"]["choice"] == "api-call"
    assert res["advisoryResult"]["recommendation"] == "map-to-api-call"
    assert res["advisoryResult"]["confidence"] == 0.92
    assert res["advisoryShortlistIncomplete"] is False

    # Original packet must NOT be modified
    assert "advisoryResult" not in packet
    assert packet.get("decision") is None


def test_mapping_no_options_fallback_to_luna():
    packet = {
        "contractVersion": "discovery-packet-v2",
        "candidateId": "alien/unknown-skill",
        "normalized": {"name": "Xylophone", "description": "Musical acoustic vibrations"},
        "mappingOptions": [],
    }
    generic_nodes = {}  # Empty generic nodes -> no lexical matches
    client = MockJevClient()

    res = evaluate_mapping_item(packet, client, generic_nodes)
    assert res["status"] == "fallback"
    assert res["reason"] == "no_shortlist_options"
    assert res["fallback"]["agent"] == "worker-luna"
    assert "Worker Luna should research" in res["fallback"]["instruction"]
    # No calls made to Jev
    assert len(client.calls) == 0


def test_mapping_none_of_shortlist_routes_to_luna():
    packet = {
        "candidateId": "custom/special-tool",
        "name": "Special Tool",
        "description": "Completely novel workflow",
        "mappingOptions": [{"genericId": "api-call"}],
    }
    generic_nodes = {"api-call": {"name": "API Call", "description": "HTTP"}}
    client = MockJevClient(defaultChoice="NONE_OF_SHORTLIST", defaultConfidence=0.88)

    res = evaluate_mapping_item(packet, client, generic_nodes)
    assert res["status"] == "fallback"
    assert res["fallback"]["agent"] == "worker-luna"
    assert res["advisoryResult"]["recommendation"] == "worker-luna-new-generic"
    assert len(client.calls) == 1


def test_mapping_uncertain_or_low_confidence_routes_to_luna():
    packet = {
        "candidateId": "custom/ambiguous-tool",
        "name": "Ambiguous Tool",
        "mappingOptions": [{"genericId": "api-call"}],
    }
    generic_nodes = {"api-call": {"name": "API Call", "description": "HTTP"}}
    # Confidence 0.65 is below 0.75 threshold
    client = MockJevClient(defaultChoice="api-call", defaultConfidence=0.65)

    res = evaluate_mapping_item(packet, client, generic_nodes)
    assert res["status"] == "fallback"
    assert res["fallback"]["agent"] == "worker-luna"
    assert res["advisoryResult"]["confidence"] == 0.65
    assert len(client.calls) == 1


def test_mapping_raw_intake_proposed_skills():
    item = {
        "id": "my-org/my-skill",
        "name": "REST Client",
        "description": "Interacts with REST APIs via HTTP",
    }
    generic_nodes = {
        "api-call": {"name": "API Call", "description": "Executes HTTP requests."}
    }
    client = MockJevClient(defaultChoice="api-call", defaultConfidence=0.85)

    res = evaluate_mapping_item(item, client, generic_nodes)
    assert res["status"] == "advisory"
    assert res["advisoryShortlistIncomplete"] is True
    assert res["advisoryResult"]["choice"] == "api-call"


# ===========================================================================
# 4. Issues mode tests
# ===========================================================================


def test_issues_mode_evaluation():
    issues = [
        {
            "number": 101,
            "title": "[upstream:release] Bump mattpocock/skills to v1.2.0",
            "body": "<!-- gaia-upstream-payload\n{}\n-->",
            "labels": [{"name": "upstream:approved"}],
        },
        {
            "number": 102,
            "title": "Fix broken docs links on landing page",
            "body": "Several anchor tags point to 404s",
            "labels": ["documentation"],
        },
    ]
    client = MockJevClient(defaultChoice="P1", defaultConfidence=0.95)

    res = evaluate_issues_item(issues[0], client, all_issues=issues)
    assert res["number"] == 101
    assert res["isUpstream"] is True
    assert res["upstreamTag"] == "upstream:approved"
    assert res["status"] == "advisory"
    assert res["advisoryResult"]["priorityRecommendation"] == "P1"
    assert res["advisoryResult"]["action"] == "none_read_only"
    # Never labels or closes issues


# ===========================================================================
# 5. Upstream mode tests
# ===========================================================================


def test_upstream_mode_evaluation():
    finding = {
        "skillId": "mattpocock/skills",
        "finding_type": "update",
        "currentVersion": "v1.0.0",
        "newVersion": "v2.0.0",
        "releaseNotes": "BREAKING CHANGE: Removed deprecated v1 endpoints and renamed methods.",
    }
    client = MockJevClient(defaultChoice="breakage", defaultConfidence=0.91)

    res = evaluate_upstream_item(finding, client)
    assert res["status"] == "advisory"
    assert res["skillId"] == "mattpocock/skills"
    assert res["advisoryResult"]["impact"] == "breakage"
    assert res["advisoryResult"]["confidence"] == 0.91


# ===========================================================================
# 6. Evidence mode tests
# ===========================================================================


def test_evidence_mode_evaluation():
    ev_row = {
        "source": "https://arxiv.org/abs/2305.15334",
        "type": "arxiv",
        "notes": "Gorilla generates accurate API calls across TorchHub and HF; 20.43% AST accuracy improvement.",
        "grade": "A",
    }
    client = MockJevClient(defaultChoice="plausible_claim", defaultConfidence=0.88)

    res = evaluate_evidence_item(ev_row, client)
    assert res["status"] == "advisory"
    assert res["advisoryResult"]["semanticConcern"] == "plausible_claim"
    # Does NOT verify HTTP or modify grades
    assert "grade" not in res["advisoryResult"]


# ===========================================================================
# 7. Meta mode tests
# ===========================================================================


def test_meta_mode_evaluation():
    generic_node = {
        "id": "api-call",
        "name": "API Call",
        "description": "Executes HTTP requests and parses JSON responses.",
        "summary": "HTTP interface.",
    }
    client = MockJevClient(defaultChoice="well_scoped", defaultConfidence=0.94)

    res = evaluate_meta_item(generic_node, client)
    assert res["status"] == "advisory"
    assert res["advisoryResult"]["reviewRoute"] == "well_scoped"


# ===========================================================================
# 8. Steward mode tests
# ===========================================================================


def test_steward_mode_valid_debt():
    debt = {
        "id": "drift-node-01",
        "kind": "schema_drift",
        "subject": {"kind": "node", "id": "test-node"},
        "currentState": {"version": "0.1.0"},
        "observedState": {"version": "0.2.0"},
        "status": "open",
    }
    client = MockJevClient(defaultChoice="routine_maintenance", defaultConfidence=0.85)

    res = evaluate_steward_item(debt, client)
    assert res["status"] == "advisory"
    assert res["advisoryResult"]["reviewHint"] == "routine_maintenance"


def test_steward_mode_missing_fields_avoid_fake_clean_bill():
    incomplete_debt = {
        "id": "incomplete-01",
        # Missing kind, subject, currentState, observedState
    }
    client = MockJevClient()

    res = evaluate_steward_item(incomplete_debt, client)
    assert res["status"] == "fallback"
    assert res["reason"] == "missing_required_state_fields"
    assert res["fallback"]["agent"] == "worker-luna"
    assert len(client.calls) == 0  # No call made on invalid shape


# ===========================================================================
# 9. Budget exhaustion / row preservation tests
# ===========================================================================


def test_run_advisory_preserves_all_items_on_limit_exhaustion():
    items = [
        {"id": "skill-1", "name": "Skill One", "mappingOptions": [{"genericId": "api-call"}]},
        {"id": "skill-2", "name": "Skill Two", "mappingOptions": [{"genericId": "api-call"}]},
        {"id": "skill-3", "name": "Skill Three", "mappingOptions": [{"genericId": "api-call"}]},
    ]
    # Allow only 1 call
    client = MockJevClient(maxCalls=1, defaultChoice="api-call")

    report = run_advisory("mapping", items, client)
    assert report["advisoryOnly"] is True
    assert report["summary"]["processedCount"] == 3
    assert report["summary"]["advisoryCount"] == 1
    assert report["summary"]["fallbackCount"] == 2
    assert len(report["items"]) == 3

    # First item succeeded
    assert report["items"][0]["status"] == "advisory"
    # Second item tripped the limit
    assert report["items"][1]["status"] == "fallback"
    assert report["items"][1]["reason"] == "limit_reached"
    # Third item preserved with fallback without calling client
    assert report["items"][2]["status"] == "fallback"
    assert report["items"][2]["reason"] == "limit_reached"
    assert report["items"][2]["fallback"]["agent"] == "worker-luna"
    # Context must be preserved
    assert report["items"][2]["fallback"]["context"]["candidateId"] == "skill-3"
    assert "generic_mapping" in report["items"][2]["fallback"]["questions"]


# ===========================================================================
# 10. Load input & overflow tests
# ===========================================================================


def test_load_input_overflow(tmp_path: Path):
    oversized = [{"id": f"item-{i}", "name": f"Item {i}"} for i in range(MAX_ITEMS_PER_RUN + 10)]
    in_file = tmp_path / "oversized.json"
    in_file.write_text(json.dumps(oversized), encoding="utf-8")

    items, overflow_reported, total_available = load_input("mapping", str(in_file))
    assert overflow_reported is True
    assert total_available == MAX_ITEMS_PER_RUN + 10
    assert len(items) == MAX_ITEMS_PER_RUN


def test_load_input_collect_repo_mapping():
    items, overflow, total = load_input("mapping", collect_repo=True)
    assert isinstance(items, list)
    assert total >= 0


def test_load_input_collect_repo_meta():
    items, overflow, total = load_input("meta", collect_repo=True)
    assert isinstance(items, list)
    assert total > 0


def test_load_input_collect_repo_issues_raises_error():
    with pytest.raises(ValueError, match="does not fetch GitHub issues automatically"):
        load_input("issues", collect_repo=True)


# ===========================================================================
# 11. CLI runner tests
# ===========================================================================


def test_cli_runner_init_budget_only():
    client = MockJevClient()
    code = cli_main(["--init-budget"], client=client)
    assert code == 0
    assert client.budgetInitialized is True


def test_cli_runner_full_run(tmp_path: Path):
    in_file = tmp_path / "input.json"
    out_file = tmp_path / "output.json"
    in_file.write_text(
        json.dumps([
            {"candidateId": "test/skill", "name": "Skill", "mappingOptions": [{"genericId": "api-call"}]}
        ]),
        encoding="utf-8",
    )
    client = MockJevClient(defaultChoice="api-call", defaultConfidence=0.9)

    code = cli_main(
        ["--mode", "mapping", "--input", str(in_file), "--output", str(out_file)],
        client=client,
    )
    assert code == 0
    assert out_file.is_file()

    with open(out_file, "r", encoding="utf-8") as fp:
        report = json.load(fp)
    assert report["schemaVersion"] == "jev-advisory-report-v1"
    assert report["advisoryOnly"] is True
    assert report["summary"]["advisoryCount"] == 1


def test_cli_runner_same_path_rejected(tmp_path: Path):
    in_file = tmp_path / "same.json"
    in_file.write_text("[]", encoding="utf-8")
    client = MockJevClient()

    code = cli_main(
        ["--mode", "mapping", "--input", str(in_file), "--output", str(in_file)],
        client=client,
    )
    assert code == 2


def test_real_jev_client_offline_integration(tmp_path: Path):
    """Test integration with Worker A's real JevClient in offline / dry_run mode."""
    try:
        from gaia_cli.jev import JevClient as RealJevClient
    except ImportError:
        pytest.skip("Real JevClient not available in environment")

    state_dir = tmp_path / "jev_state"
    client = RealJevClient(state_dir, live=False)
    client.initializeBudget()

    in_file = tmp_path / "input.json"
    out_file = tmp_path / "report.json"
    in_file.write_text(
        json.dumps([
            {
                "contractVersion": "discovery-packet-v2",
                "candidateId": "real/skill",
                "normalized": {"name": "Real Skill", "description": "Test skill"},
                "mappingOptions": [{"genericId": "api-call"}],
            }
        ]),
        encoding="utf-8",
    )

    code = cli_main(
        [
            "--mode", "mapping",
            "--input", str(in_file),
            "--output", str(out_file),
            "--state-dir", str(state_dir),
        ],
        client=client,
    )
    assert code == 0
    assert out_file.is_file()

    with open(out_file, "r", encoding="utf-8") as fp:
        report = json.load(fp)

    assert report["schemaVersion"] == "jev-advisory-report-v1"
    assert report["advisoryOnly"] is True
    assert report["summary"]["processedCount"] == 1
    assert report["summary"]["fallbackCount"] == 1
    assert report["items"][0]["status"] == "fallback"
    assert report["items"][0]["reason"] == "dry_run"
    assert report["items"][0]["fallback"]["agent"] == "worker-luna"
    assert report["items"][0]["fallback"]["context"]["candidateId"] == "real/skill"


# ===========================================================================
# 12. Non-mapping modes 0.75 threshold and UNCERTAIN fallback tests (Issue 1)
# ===========================================================================


def test_non_mapping_modes_low_confidence_and_uncertain_fallback():
    # 1. Issues: low confidence
    client_low = MockJevClient(defaultChoice="P1", defaultConfidence=0.60)
    res_issue = evaluate_issues_item({"number": 201, "title": "Crash", "body": "details"}, client_low)
    assert res_issue["status"] == "fallback"
    assert res_issue["reason"] == "low_confidence"
    assert res_issue["fallback"]["agent"] == "worker-luna"
    assert res_issue["fallback"]["context"]["number"] == 201

    # 1b. Issues: UNCERTAIN choice
    client_unc = MockJevClient(defaultChoice="UNCERTAIN", defaultConfidence=0.90)
    res_issue_unc = evaluate_issues_item({"number": 202, "title": "Vague", "body": "text"}, client_unc)
    assert res_issue_unc["status"] == "fallback"
    assert res_issue_unc["reason"] == "uncertain"

    # 2. Upstream: low confidence
    res_up_low = evaluate_upstream_item(
        {"skillId": "owner/repo", "sourceUrl": "https://github.com/owner/repo", "newVersion": "v2.0"},
        client_low,
    )
    assert res_up_low["status"] == "fallback"
    assert res_up_low["reason"] == "low_confidence"

    # 2b. Upstream: uncertain choice
    client_up_unc = MockJevClient(defaultChoice="uncertain", defaultConfidence=0.90)
    res_up_unc = evaluate_upstream_item(
        {"skillId": "owner/repo", "sourceUrl": "https://github.com/owner/repo", "newVersion": "v2.0"},
        client_up_unc,
    )
    assert res_up_unc["status"] == "fallback"
    assert res_up_unc["reason"] == "uncertain"

    # 3. Evidence: low confidence & uncertain
    res_ev_low = evaluate_evidence_item({"source": "https://arxiv.org/1", "type": "arxiv"}, client_low)
    assert res_ev_low["status"] == "fallback"
    assert res_ev_low["reason"] == "low_confidence"

    client_ev_unc = MockJevClient(defaultChoice="uncertain", defaultConfidence=0.85)
    res_ev_unc = evaluate_evidence_item({"source": "https://arxiv.org/1", "type": "arxiv"}, client_ev_unc)
    assert res_ev_unc["status"] == "fallback"
    assert res_ev_unc["reason"] == "uncertain"

    # 4. Meta: low confidence & uncertain
    res_meta_low = evaluate_meta_item({"id": "some-node", "name": "Node"}, client_low)
    assert res_meta_low["status"] == "fallback"
    assert res_meta_low["reason"] == "low_confidence"

    client_meta_unc = MockJevClient(defaultChoice="uncertain", defaultConfidence=0.90)
    res_meta_unc = evaluate_meta_item({"id": "some-node", "name": "Node"}, client_meta_unc)
    assert res_meta_unc["status"] == "fallback"
    assert res_meta_unc["reason"] == "uncertain"

    # 5. Steward: low confidence & uncertain
    debt = {
        "id": "debt-01",
        "kind": "schema_drift",
        "subject": "skill/test",
        "currentState": {"v": 1},
        "observedState": {"v": 2},
    }
    res_steward_low = evaluate_steward_item(debt, client_low)
    assert res_steward_low["status"] == "fallback"
    assert res_steward_low["reason"] == "low_confidence"

    client_stew_unc = MockJevClient(defaultChoice="uncertain", defaultConfidence=0.90)
    res_steward_unc = evaluate_steward_item(debt, client_stew_unc)
    assert res_steward_unc["status"] == "fallback"
    assert res_steward_unc["reason"] == "uncertain"


# ===========================================================================
# 13. Frozen generic snapshot and packet dedupe/rejection (Issue 2)
# ===========================================================================


def test_mapping_uses_frozen_generic_snapshot():
    packet = {
        "candidateId": "anthropic/fetch-api",
        "name": "Fetch API",
        "mappingOptions": [{"genericId": "frozen-api"}],
        "genericSnapshot": {
            "generics": [
                {
                    "id": "frozen-api",
                    "name": "Frozen API",
                    "description": "Exact frozen description from past capture.",
                }
            ]
        },
    }
    client = MockJevClient(defaultChoice="frozen-api", defaultConfidence=0.90)
    # generic_nodes has drifting/different description
    generic_nodes = {"frozen-api": {"name": "Changed Name", "description": "New drift"}}

    res = evaluate_mapping_item(packet, client, generic_nodes)
    assert res["status"] == "advisory"
    assert len(client.calls) == 1
    # Check that frozen description was used in questions criteria
    criteria = client.calls[0]["questions"]["generic_mapping"]["criteria"]
    assert "Exact frozen description" in criteria["frozen-api"]


def test_mapping_empty_mapping_options_no_paid_lexical_call():
    packet = {
        "candidateId": "vendor/tool",
        "name": "API Caller",
        "description": "Calls REST API",
        "mappingOptions": [],  # explicitly empty
    }
    # generic_nodes has matching node that lexical_shortlist would find if run
    generic_nodes = {"api-call": {"name": "API Call", "description": "Calls REST API"}}
    client = MockJevClient()

    res = evaluate_mapping_item(packet, client, generic_nodes)
    assert res["status"] == "fallback"
    assert res["reason"] == "no_shortlist_options"
    assert "broader registry" in res["fallback"]["instruction"]
    assert len(client.calls) == 0  # No paid call burned!


def test_mapping_deterministic_packet_skips():
    client = MockJevClient()
    generic_nodes = {"api-call": {"name": "API Call"}}

    # 1. Duplicated packet
    dup_packet = {
        "candidateId": "c1",
        "exactDedupe": {"matched": True, "matchedCandidateId": "c0"},
        "mappingOptions": [{"genericId": "api-call"}],
    }
    res_dup = evaluate_mapping_item(dup_packet, client, generic_nodes)
    assert res_dup["status"] == "fallback"
    assert res_dup["reason"] == "already_duplicated"
    assert len(client.calls) == 0

    # 2. Deterministically rejected packet
    rej_packet = {
        "candidateId": "c2",
        "artifactGate": "invalid-manifest-missing-entry",
        "mappingOptions": [{"genericId": "api-call"}],
    }
    res_rej = evaluate_mapping_item(rej_packet, client, generic_nodes)
    assert res_rej["status"] == "fallback"
    assert res_rej["reason"] == "deterministically_rejected"
    assert len(client.calls) == 0

    # 3. Already resolved packet
    res_packet = {
        "candidateId": "c3",
        "decision": {"value": "ACCEPTED"},
        "mappingOptions": [{"genericId": "api-call"}],
    }
    res_resolved = evaluate_mapping_item(res_packet, client, generic_nodes)
    assert res_resolved["status"] == "fallback"
    assert res_resolved["reason"] == "already_resolved"
    assert len(client.calls) == 0


# ===========================================================================
# 14. Lexical duplicate ranking and incomplete shortlist (Issue 3)
# ===========================================================================


def test_issues_duplicate_candidates_ranked_by_relevance_with_excerpts():
    current_issue = {
        "number": 500,
        "title": "Yaml parser memory leak in scanner",
        "body": "Detailed leak traces in PyYAML scanner block token loop.",
    }
    all_issues = [
        {"number": 1, "title": "Docs website typo", "body": "Misspelling in index.html"},
        {"number": 2, "title": "Add dark mode theme", "body": "CSS stylesheet tweaks"},
        {"number": 3, "title": "Chore bump dependencies", "body": "Bump ruff to v0.5"},
        {
            "number": 4,
            "title": "Memory leak detected in PyYAML parser",
            "body": "Scanner token loop allocates unbounded memory buffers.",
        },
        {"number": 500, "title": current_issue["title"], "body": current_issue["body"]},
    ]
    ranked = rank_duplicate_issue_candidates(current_issue, all_issues, limit=3)
    assert len(ranked) == 1
    assert ranked[0]["number"] == 4
    assert "Scanner token loop" in ranked[0]["excerpt"]

    client = MockJevClient(defaultChoice="P2", defaultConfidence=0.9)
    res = evaluate_issues_item(current_issue, client, all_issues=all_issues)
    assert res["duplicateShortlistIncomplete"] is True
    assert res["proofOfUniqueness"] is False
    assert res["advisoryResult"]["duplicateCandidateCount"] == 1
    assert res["advisoryResult"]["duplicateCandidates"] == [4]


# ===========================================================================
# 15. Fallback context preservation & dry-run non-erasure (Issues 4 & 5)
# ===========================================================================


def test_dry_run_preserves_full_context_for_all_items_and_zero_calls():
    items = [
        {"id": "skill-1", "name": "Skill One", "mappingOptions": [{"genericId": "api-call"}]},
        {"id": "skill-2", "name": "Skill Two", "mappingOptions": [{"genericId": "api-call"}]},
    ]
    client = MockJevClient(status="fallback", reason="dry_run")

    report = run_advisory("mapping", items, client)
    assert report["summary"]["totalCalls"] == 0
    assert report["summary"]["totalReservedUsd"] == 0.0
    assert report["summary"]["processedCount"] == 2
    assert report["summary"]["fallbackCount"] == 2

    # Context must NOT be erased for subsequent items
    for idx, itm in enumerate(report["items"]):
        assert itm["status"] == "fallback"
        assert itm["reason"] == "dry_run"
        assert itm["fallback"]["agent"] == "worker-luna"
        assert itm["fallback"]["context"]["candidateId"] == f"skill-{idx+1}"
        assert "generic_mapping" in itm["fallback"]["questions"]


def test_cached_response_zero_new_costs_and_no_calls():
    class CachedMockClient:
        def evaluate(self, state, questions):
            return {
                "status": "advisory",
                "reason": "ok",
                "answers": {
                    "generic_mapping": {
                        "type": "choice",
                        "choice": "api-call",
                        "confidence": 0.95,
                        "probabilities": {"api-call": 1.0},
                    }
                },
                "model": "jev-1.13.0",
                "cached": True,
                "usage": {"input_tokens": 100, "output_tokens": 0},
                "estimatedCostUsd": 0.005,
                "reservedUsd": 0.0,
            }

    items = [{"id": "cached-skill", "mappingOptions": [{"genericId": "api-call"}]}]
    report = run_advisory("mapping", items, CachedMockClient())
    assert report["summary"]["totalCalls"] == 0
    assert report["summary"]["totalReservedUsd"] == 0.0
    assert report["summary"]["totalEstimatedCostUsd"] == 0.0  # Zero new costs for cached!
    assert report["items"][0]["status"] == "advisory"


# ===========================================================================
# 16. Comprehensive path security and state validation (Issue 6)
# ===========================================================================


def test_validate_paths_guards_protected_roots_and_symlinks(tmp_path: Path):
    repo_root = str(_REPO_ROOT)

    # 1. Output cannot be inside registry-for-review/discovery-packets
    disc_packet_out = os.path.join(repo_root, "registry-for-review", "discovery-packets", "test.json")
    with pytest.raises(ValueError, match="canonical registry path"):
        validate_paths("in.json", disc_packet_out, repo_root)

    # 2. Output cannot be inside .gaia/steward
    steward_out = os.path.join(repo_root, ".gaia", "steward", "report.json")
    with pytest.raises(ValueError, match="canonical registry path|inside .gaia/steward"):
        validate_paths("in.json", steward_out, repo_root)

    # 3. Output cannot be inside src/ or scripts/
    src_out = os.path.join(repo_root, "src", "out.json")
    with pytest.raises(ValueError, match="canonical registry path|under generated-output or scratch"):
        validate_paths("in.json", src_out, repo_root)

    # 4. State dir cannot be canonical root
    reg_state = os.path.join(repo_root, "registry")
    with pytest.raises(ValueError, match="State directory cannot be inside"):
        validate_paths("in.json", str(tmp_path / "out.json"), repo_root, state_dir=reg_state)

    # 5. Input colliding with stateDir/cache.json
    state_dir = str(tmp_path / "scratch_state")
    os.makedirs(state_dir, exist_ok=True)
    cache_path = os.path.join(state_dir, "cache.json")
    with pytest.raises(ValueError, match="state directory file"):
        validate_paths(cache_path, str(tmp_path / "out.json"), repo_root, state_dir=state_dir)

    # 6. Symlink output rejected
    real_target = tmp_path / "real_target.json"
    real_target.touch()
    symlink_out = tmp_path / "symlink_out.json"
    symlink_out.symlink_to(real_target)
    with pytest.raises(ValueError, match="cannot be a symlink"):
        validate_paths("in.json", str(symlink_out), repo_root)


# ===========================================================================
# 17. Bounded input read and malformed row preservation (Issue 7)
# ===========================================================================


def test_load_input_bounded_read_and_malformed_rows(tmp_path: Path):
    # 1. Bounded size check: file > 2MB rejected
    large_file = tmp_path / "large.json"
    with open(large_file, "wb") as fp:
        fp.write(b" " * (MAX_INPUT_FILE_BYTES + 10))

    with pytest.raises(ValueError, match="exceeds maximum"):
        load_input("mapping", str(large_file))

    # 2. Malformed rows preserved as fallback records rather than dropped
    mixed_file = tmp_path / "mixed.json"
    mixed_data = [
        {"id": "valid-1", "name": "Valid Skill", "mappingOptions": [{"genericId": "api-call"}]},
        "malformed_string_row",
        12345,
        {"id": "valid-2", "name": "Valid Skill 2", "mappingOptions": [{"genericId": "api-call"}]},
    ]
    mixed_file.write_text(json.dumps(mixed_data), encoding="utf-8")

    items, overflow, total = load_input("mapping", str(mixed_file))
    assert total == 4
    assert len(items) == 4
    assert items[1]["_malformed"] is True
    assert items[2]["_malformed"] is True

    client = MockJevClient(defaultChoice="api-call")
    report = run_advisory("mapping", items, client)
    assert report["summary"]["processedCount"] == 4
    assert report["items"][1]["status"] == "fallback"
    assert report["items"][1]["reason"] == "malformed_input_row"
    assert report["items"][2]["status"] == "fallback"
    assert report["items"][2]["reason"] == "malformed_input_row"


def test_actionable_overflow_and_offset_pagination(tmp_path: Path):
    items_data = [{"id": f"item-{i}", "name": f"Item {i}"} for i in range(10)]
    in_file = tmp_path / "paged.json"
    in_file.write_text(json.dumps(items_data), encoding="utf-8")

    items, overflow, total = load_input("mapping", str(in_file), offset=4, limit=3)
    assert overflow is True
    assert total == 10
    assert len(items) == 3
    assert items[0]["id"] == "item-4"

    client = MockJevClient(defaultChoice="api-call")
    report = run_advisory("mapping", items, client, total_available=total, offset=4)
    summary = report["summary"]
    assert summary["offset"] == 4
    assert summary["nextOffset"] == 7
    assert summary["omittedCount"] == 3
    assert summary["omittedIdentifiers"] == ["item-7", "item-8", "item-9"]


# ===========================================================================
# 18. Upstream native facts and missing source handling (Issue 8)
# ===========================================================================


def test_upstream_native_facts_and_missing_source():
    # 1. Deterministic facts and previousVersion alias included
    finding = {
        "skillId": "mattpocock/skills",
        "previousVersion": "v1.0.0",
        "newVersion": "v1.1.0",
        "sourceUrl": "https://github.com/mattpocock/skills",
        "componentAdds": ["new-comp"],
        "componentRemoves": ["old-comp"],
        "linkLiveness": [{"url": "https://example.com", "status": 200}],
    }
    client = MockJevClient(defaultChoice="changed_capability", defaultConfidence=0.92)
    res = evaluate_upstream_item(finding, client)
    assert res["status"] == "advisory"
    assert res["componentAdds"] == ["new-comp"]
    assert res["componentRemoves"] == ["old-comp"]
    assert res["previousVersion"] == "v1.0.0"

    state_sent = client.calls[0]["state"]
    assert state_sent["componentAdds"] == ["new-comp"]
    assert state_sent["componentRemoves"] == ["old-comp"]
    assert state_sent["previousVersion"] == "v1.0.0"

    # 2. Missing source -> no paid call
    finding_no_source = {
        "skillId": "unknown_skill",
        "newVersion": "v2.0.0",
    }
    res_no_src = evaluate_upstream_item(finding_no_source, client)
    assert res_no_src["status"] == "fallback"
    assert res_no_src["reason"] == "missing_source"
    # No new call made
    assert len(client.calls) == 1


# ===========================================================================
# 19. Steward scan shapes and debt inspection (Issue 8)
# ===========================================================================


def test_steward_scan_shapes_and_observation_handling():
    obs = {
        "kind": "upstream_drift",
        "subject": {"type": "repository-surface", "id": "upstream-watcher"},
        "currentState": {"synced": False},
        "observedState": {"synced": True},
        "source": "sensor-upstream",
        "status": "drift",
        "priority": {"score": 0.8},
        "authority": {"class": "curator"},
    }
    client = MockJevClient(defaultChoice="prioritize_triage", defaultConfidence=0.88)
    res = evaluate_steward_item(obs, client)
    assert res["status"] == "advisory"
    assert res["advisoryResult"]["reviewHint"] == "prioritize_triage"
    state_sent = client.calls[0]["state"]
    assert state_sent["kind"] == "upstream_drift"
    assert state_sent["subject"] == "repository-surface:upstream-watcher"
    assert state_sent["priorityScore"] == 0.8
    assert state_sent["authorityClass"] == "curator"


# ===========================================================================
# 20. CLI validation error clean exit (Issue 9)
# ===========================================================================


def test_cli_validation_error_clean_exit(tmp_path: Path, capsys):
    in_file = tmp_path / "valid_in.json"
    in_file.write_text("[]", encoding="utf-8")
    # Output to canonical protected directory should exit cleanly with 2
    bad_output = os.path.join(str(_REPO_ROOT), "registry", "report.json")

    code = cli_main(["--mode", "mapping", "--input", str(in_file), "--output", bad_output])
    assert code == 2
    captured = capsys.readouterr()
    assert "Validation error:" in captured.err
