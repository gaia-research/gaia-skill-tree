import copy
import hashlib
import json
import shutil
from pathlib import Path

import pytest

from gaia_cli import frontierMatch
from gaia_cli.frontier import dedupe_key
from gaia_cli.frontierMatch import dedupe_against_ledger, match_candidates

FIXTURE = Path(__file__).parent / "fixtures" / "frontier-match"  # synthetic registry, see SYNTHETIC.txt
REPO = Path(__file__).resolve().parent.parent


def tree_digest(root: Path) -> str:
    digest = hashlib.sha256()
    for path in sorted(p for p in root.rglob("*") if p.is_file()):
        digest.update(path.relative_to(root).as_posix().encode() + b"\0" + path.read_bytes())
    return digest.hexdigest()


def make_lead(**overrides):
    lead = {
        "schemaVersion": "challenger-lead-v1", "contractRevision": "challenger-lead-v1.1",
        "leadId": "synthetic-lead-001", "campaignId": "synthetic-campaign", "claimId": "synthetic-claim",
        "identity": {"name": "Synthetic Line Tracer", "kind": "native-cli", "installable": False, "version": "1.0"},
        "source": {"url": "https://example.org/synthetic/line-tracer", "observedAtUTC": "2026-10-26T12:00:00Z", "contentDigest": "sha256:" + "c" * 64, "provider": "Synthetic", "capturedBytesPath": "sources/x.adoc"},
        "capability": {"claim": "Trace how a function or line range changed across commit history of a file.", "task": "Explain how a function changed over commit history.", "conditions": "Requires a repository."},
        "comparison": {"comparator": "Repository graph retrieval of source spans and callers.", "baseline": "Compare history tracing against graph retrieval."},
        "target": {"skillId": "synthetic-owner/graft-like", "kind": "named", "genericSkillId": "synthetic-codebase-graph", "revision": "a" * 40, "contentDigest": "sha256:" + "b" * 64, "scopeRationale": "Synthetic overlap only."},
        "preliminaryEvidence": [], "limitations": ["synthetic"],
        "dedupe": {"key": "x", "checkedAtUTC": "2026-10-26T12:00:00Z", "matches": []},
        "independentTest": {"proposal": "synthetic proposal text", "traceability": "synthetic traceability text"},
        "disposition": {"status": "candidate", "rationale": "synthetic rationale text", "nextAction": "synthetic next action"},
    }
    lead.update(overrides)
    return lead


@pytest.fixture
def repo(tmp_path):
    root = tmp_path / "repo"
    shutil.copytree(FIXTURE, root)
    return root


def write_ledger(root: Path, case: str, lead: dict):
    folder = root / "evidence" / "frontier-challenges" / case
    folder.mkdir(parents=True, exist_ok=True)
    (folder / "lead.json").write_text(json.dumps(lead), encoding="utf-8")
    return folder / "lead.json"


def test_match_ranks_expected_target_and_is_advisory(repo):
    result = match_candidates(make_lead(), repo)
    assert result["schemaVersion"] == "frontier-match-v1"
    assert result["advisory"] is True and "never admission" in result["authority"]
    assert result["candidates"][0]["skillId"] == "synthetic-line-history"
    ids = [c["skillId"] for c in result["candidates"]]
    assert "synthetic-image-resize" not in ids
    assert [c["rank"] for c in result["candidates"]] == list(range(1, len(ids) + 1))
    assert all(c["rationale"] and 0 < c["score"] <= 1 for c in result["candidates"])
    assert result["registeredElsewhere"] is False and result["registeredAs"] == []
    assert result["declaredTarget"]["exists"] is True and isinstance(result["declaredTarget"]["contentRank"], int)


def test_match_is_deterministic_and_leaves_registry_bytes_unchanged(repo):
    before = tree_digest(repo)
    first = match_candidates(make_lead(), repo)
    second = match_candidates(make_lead(), repo)
    assert first == second
    assert tree_digest(repo) == before
    assert first["registry"]["readOnly"] is True and first["registry"]["digest"].startswith("sha256:")


def test_match_works_without_a_target_block(repo):
    lead = make_lead()
    del lead["target"]
    result = match_candidates(lead, repo)
    assert result["declaredTarget"] is None and result["candidates"]


def test_registered_elsewhere_flag_by_name_and_repository(repo):
    lead = make_lead(identity={"name": "Synthetic Graph Tool", "kind": "installable-agent-capability", "installable": True, "version": "1.0"})
    lead["source"]["url"] = "https://github.com/synthetic-labs/graph-tool"
    result = match_candidates(lead, repo)
    assert result["registeredElsewhere"] is True
    registered = result["registeredAs"][0]
    assert registered["skillId"] == "synthetic-owner/graph-tool" and registered["via"] == ["name", "repository"]
    assert registered["genericSkillId"] == "synthetic-knowledge-graph"
    # The challenger never ranks against itself; its bucket is flagged instead.
    assert all(c["skillId"] != "synthetic-owner/graph-tool" for c in result["candidates"])
    flagged = [c for c in result["candidates"] if any(s["signal"] == "challenger-bucket" for s in c["signals"])]
    assert flagged and all(c["genericSkillId"] == "synthetic-knowledge-graph" for c in flagged)


def test_registered_by_repository_alone_and_similarity_signal(repo):
    lead = make_lead(identity={"name": "Different Display Name", "kind": "installable-agent-capability", "installable": True, "version": "1"})
    lead["source"]["url"] = "https://github.com/Synthetic-Labs/graph-tool/"
    result = match_candidates(lead, repo)
    assert result["registeredAs"][0]["via"] == ["repository"]
    similar = [c for c in result["candidates"] if any(s["signal"] == "similarity-index" for s in c["signals"])]
    assert [c["skillId"] for c in similar] == ["synthetic-owner/graft-like"]


def test_match_rejects_forged_authority_and_missing_fields(repo):
    forged = make_lead()
    forged["disposition"]["approvedBy"] = "someone"
    with pytest.raises(ValueError, match="forbidden authority field"):
        match_candidates(forged, repo)
    with pytest.raises(ValueError, match="missing required field"):
        match_candidates(make_lead(capability={"claim": "", "task": "t", "conditions": "c"}), repo)
    with pytest.raises(ValueError):
        match_candidates(make_lead(), repo, top=0)
    with pytest.raises(ValueError, match="no registry"):
        match_candidates(make_lead(), repo / "missing")


def test_dedupe_ignores_timestamps_but_not_target_revision(repo):
    ledger = make_lead()
    ledger["source"]["observedAtUTC"] = "2025-01-01T00:00:00Z"
    ledger["dedupe"]["checkedAtUTC"] = "2025-01-01T00:00:00Z"
    ledger["dedupe"]["key"] = "stale-recorded-key-is-ignored"
    write_ledger(repo, "synthetic-case-1", ledger)
    result = dedupe_against_ledger(make_lead(), repo)
    assert result["isDuplicate"] is True and result["duplicates"][0]["caseId"] == "synthetic-case-1"
    assert result["dedupeKey"] == dedupe_key(make_lead())
    moved = make_lead()
    moved["target"]["revision"] = "d" * 40
    changed = dedupe_against_ledger(moved, repo)
    assert changed["isDuplicate"] is False
    assert changed["related"][0]["match"] == "same-challenger-subject"


def test_dedupe_tolerates_empty_ledger_broken_files_and_excludes_self(repo):
    assert dedupe_against_ledger(make_lead(), repo)["ledger"]["scanned"] == 0
    broken = repo / "evidence" / "frontier-challenges" / "synthetic-case-broken"
    broken.mkdir(parents=True)
    (broken / "lead.json").write_text("{not json", encoding="utf-8")
    own = write_ledger(repo, "synthetic-case-1", make_lead())
    result = dedupe_against_ledger(make_lead(), repo, exclude=own)
    assert result["isDuplicate"] is False and result["ledger"]["scanned"] == 0
    assert result["ledger"]["skipped"][0]["path"].endswith("synthetic-case-broken/lead.json")
    assert dedupe_against_ledger(make_lead(), repo)["isDuplicate"] is True


def test_dedupe_without_target_falls_back_to_subject(repo):
    write_ledger(repo, "synthetic-case-1", make_lead())
    lead = make_lead()
    del lead["target"]
    result = dedupe_against_ledger(lead, repo)
    assert result["dedupeKey"] is None and result["isDuplicate"] is False
    assert result["related"] and result["keyBasis"].startswith("subject-only")


def test_dedupe_leaves_ledger_bytes_unchanged(repo):
    write_ledger(repo, "synthetic-case-1", make_lead())
    before = tree_digest(repo)
    dedupe_against_ledger(make_lead(), repo)
    assert tree_digest(repo) == before


def run_cli(args, repo, capsys):
    from gaia_cli.main import main
    argv = ["gaia", "--registry", str(repo / "registry"), "dev", "frontier", *args]
    import sys
    old, sys.argv = sys.argv, argv
    try:
        code = main()
    except SystemExit as exc:
        code = exc.code
    finally:
        sys.argv = old
    return code, capsys.readouterr()


def test_cli_match_and_dedupe_are_read_only_and_emit_json(repo, tmp_path, capsys):
    lead = tmp_path / "lead.json"
    lead.write_text(json.dumps(make_lead()), encoding="utf-8")
    before = tree_digest(repo)
    code, out = run_cli(["match", "--lead", str(lead), "--top", "2"], repo, capsys)
    assert code in (0, None)
    match = json.loads(out.out)
    assert match["schemaVersion"] == "frontier-match-v1" and len(match["candidates"]) == 2
    write_ledger(repo, "synthetic-case-1", make_lead())
    before = tree_digest(repo)
    code, out = run_cli(["dedupe", "--lead", str(lead), "--fail-on-duplicate"], repo, capsys)
    assert code == 2 and json.loads(out.out)["isDuplicate"] is True
    code, out = run_cli(["dedupe", "--lead", str(lead)], repo, capsys)
    assert code in (0, None)
    assert tree_digest(repo) == before


def test_cli_refuses_bad_lead_without_traceback(repo, tmp_path, capsys):
    bad = tmp_path / "bad.json"
    bad.write_text("[]", encoding="utf-8")
    code, out = run_cli(["match", "--lead", str(bad)], repo, capsys)
    assert code == 1 and "refused" in out.err


def test_real_registry_graphify_is_registered_elsewhere():
    """Read-only check against the checked-out registry; skipped when the named skill is absent."""
    named = REPO / "registry/named/safishamsi/graphify.md"
    if not named.is_file():
        pytest.skip("graphify named skill not present in this checkout")
    before = tree_digest(REPO / "registry/nodes")
    lead = make_lead(identity={"name": "Graphify", "kind": "installable-agent-capability", "installable": True, "version": "0.8.13"})
    lead["source"]["url"] = "https://github.com/Graphify-Labs/graphify"
    del lead["target"]
    result = match_candidates(lead, REPO)
    assert result["registeredElsewhere"] is True
    assert any(item["skillId"] == "safishamsi/graphify" and item["genericSkillId"] == "knowledge-graph-build" for item in result["registeredAs"])
    assert tree_digest(REPO / "registry/nodes") == before
