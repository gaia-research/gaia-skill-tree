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
    argv = ["gaia", "--registry", str(repo), "dev", "frontier", *args]
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


def addNamed(repo, owner, slug, name, github, crlf=False):
    path = repo / "registry/named" / owner / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    text = f"---\nid: {owner}/{slug}\nname: {name}\ngenericSkillRef: synthetic-line-history\nstatus: named\ntitle: T\ndescription: SYNTHETIC. line history helper\nlinks:\n  github: {github}\n---\n\nbody\n"
    path.write_bytes(text.replace("\n", "\r\n").encode() if crlf else text.encode())


def test_monorepo_source_does_not_flag_or_drop_sibling_skills(repo):
    for slug in ("alpha", "beta", "gamma"):
        addNamed(repo, "synthetic-mono", slug, f"Synthetic {slug.title()}", f"https://github.com/synthetic-mono/skills/blob/main/skills/{slug}/SKILL.md")
    lead = make_lead(identity={"name": "Unrelated Name", "kind": "installable-agent-capability", "installable": True, "version": "1"})
    lead["source"]["url"] = "https://github.com/synthetic-mono/skills"
    bare = match_candidates(lead, repo)
    assert bare["registeredElsewhere"] is False and bare["ambiguousRepository"]["entries"] == 3
    assert any(c["skillId"].startswith("synthetic-mono/") for c in match_candidates(lead, repo, top=50)["candidates"])
    lead["source"]["url"] = "https://github.com/synthetic-mono/skills/blob/main/skills/beta/SKILL.md"
    exact = match_candidates(lead, repo)
    assert [r["skillId"] for r in exact["registeredAs"]] == ["synthetic-mono/beta"] and exact["registeredAs"][0]["via"] == ["repository"]
    assert exact["ambiguousRepository"] is None
    lead["source"]["url"] = "https://github.com/synthetic-mono/skills/blob/main/skills/delta/SKILL.md"
    assert match_candidates(lead, repo)["registeredElsewhere"] is False


@pytest.mark.parametrize("source", ["https://example.org", [], "text", None, 7])
def test_non_object_or_odd_source_is_a_clean_refusal_or_result(repo, source, tmp_path, capsys):
    lead = make_lead()
    lead["source"] = source
    result = match_candidates(lead, repo)
    assert result["registeredElsewhere"] is False
    path = tmp_path / "odd.json"
    path.write_text(json.dumps(lead))
    code, out = run_cli(["dedupe", "--lead", str(path), "--repo-root", str(repo)], repo, capsys)
    assert code == 1 and "refused" in out.err and "Traceback" not in out.err


def test_crlf_frontmatter_is_loaded_and_counted(repo):
    addNamed(repo, "synthetic-crlf", "windows-skill", "Synthetic Windows Skill", "https://github.com/synthetic-crlf/x/blob/main/a/SKILL.md", crlf=True)
    entries, _, _ = frontierMatch.loadRegistryEntries(repo)
    assert any(e["skillId"] == "synthetic-crlf/windows-skill" for e in entries)


def test_registry_digest_covers_similarity_and_skips_symlinks_and_oversize(repo, monkeypatch):
    _, first, count = frontierMatch.loadRegistryEntries(repo)
    (repo / "registry/similarity.json").write_text('{"pairs": []}')
    _, second, _ = frontierMatch.loadRegistryEntries(repo)
    assert first != second
    outside = repo.parent / "outside.json"
    outside.write_text(json.dumps({"id": "leaked-skill", "name": "Leaked", "description": "x"}))
    (repo / "registry/nodes/basic/link.json").symlink_to(outside)
    entries, _, _ = frontierMatch.loadRegistryEntries(repo)
    assert all(e["skillId"] != "leaked-skill" for e in entries)
    monkeypatch.setattr(frontierMatch, "MAX_REGISTRY_FILE_BYTES", 10)
    assert frontierMatch.loadRegistryEntries(repo)[0] == []


@pytest.mark.parametrize("field", ["VERIFIED", "ApprovedBy", "Signature"])
def test_forbidden_authority_keys_are_casefolded(repo, field):
    lead = make_lead()
    lead["disposition"][field] = "x"
    with pytest.raises(ValueError, match="forbidden authority field"):
        match_candidates(lead, repo)


def test_symlinked_ledger_lead_is_skipped_not_followed(repo):
    outside = repo.parent / "outside-lead.json"
    outside.write_text(json.dumps(make_lead()))
    folder = repo / "evidence/frontier-challenges/synthetic-link"
    folder.mkdir(parents=True)
    (folder / "lead.json").symlink_to(outside)
    result = dedupe_against_ledger(make_lead(), repo)
    assert result["isDuplicate"] is False and result["ledger"]["skipped"]


def test_cli_default_root_is_the_checkout_and_dedupe_fails_closed_on_unread_ledger(repo, tmp_path, capsys):
    lead = tmp_path / "lead.json"
    lead.write_text(json.dumps(make_lead()))
    write_ledger(repo, "synthetic-case-1", make_lead())
    code, out = run_cli(["dedupe", "--lead", str(lead)], repo, capsys)  # no --repo-root: root comes from --registry
    assert code in (0, None) and json.loads(out.out)["isDuplicate"] is True
    # registry path naming the registry directory itself is tolerated
    from gaia_cli.main import main
    import sys
    old, sys.argv = sys.argv, ["gaia", "--registry", str(repo / "registry"), "dev", "frontier", "dedupe", "--lead", str(lead)]
    try:
        main()
    finally:
        sys.argv = old
    assert json.loads(capsys.readouterr().out)["isDuplicate"] is True
    # empty ledger without an explicit root is refused; with one it is a stated "not duplicate"
    shutil.rmtree(repo / "evidence")
    code, out = run_cli(["dedupe", "--lead", str(lead)], repo, capsys)
    assert code == 1 and "not read" in out.err and not out.out.strip()
    code, out = run_cli(["dedupe", "--lead", str(lead), "--repo-root", str(repo)], repo, capsys)
    result = json.loads(out.out)
    assert code in (0, None) and result["isDuplicate"] is False and result["ledger"]["present"] is False


def test_cli_wrong_root_is_refused_for_match(tmp_path, capsys):
    from gaia_cli.main import main
    import sys
    lead = tmp_path / "lead.json"
    lead.write_text(json.dumps(make_lead()))
    old, sys.argv = sys.argv, ["gaia", "--registry", str(tmp_path), "dev", "frontier", "match", "--lead", str(lead)]
    try:
        with pytest.raises(SystemExit) as exit_info:
            main()
    finally:
        sys.argv = old
    assert exit_info.value.code == 1 and "--repo-root" in capsys.readouterr().err
