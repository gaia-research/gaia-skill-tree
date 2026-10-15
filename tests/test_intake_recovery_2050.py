"""Issue-backed recovery of a `gaia push` intake whose batch file was never committed (#2050).

Synthetic fixtures only. Issue bodies come from the real renderer
(`gaia_cli.prWriter.build_intake_issue_body`) so the parser is tested against what
`gaia push` actually posts. Upstream fetching is injected; no test touches the network.
"""

import base64
import copy
import importlib.util
import json
import pathlib

import pytest
import yaml

from gaia_cli.prWriter import build_intake_issue_body
from gaia_cli.push import attach_identity

ROOT = pathlib.Path(__file__).resolve().parents[1]
SCHEMA = ROOT / "registry/schema/skillBatch.schema.json"
WORKFLOW = ROOT / ".github/workflows/intake-approval.yml"

spec = importlib.util.spec_from_file_location("intake_recovery", ROOT / "scripts/intake_recovery.py")
rec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rec)

validateSpec = importlib.util.spec_from_file_location("validate_intake_mod", ROOT / "scripts/validate_intake.py")
validateIntake = importlib.util.module_from_spec(validateSpec)
validateSpec.loader.exec_module(validateIntake)

BATCH_ID = "20261007104057-ExampleSubmitter-sample-repo"
SOURCE_REPO = "ExampleSubmitter/sample-repo"
URL_ONE = "https://github.com/ExampleSubmitter/sample-repo/blob/main/SKILL.md"
URL_TWO = "https://github.com/ExampleSubmitter/sample-repo/blob/main/skills/helper/SKILL.md"
BYTES = {
    URL_ONE: b"---\nname: sample\n---\nSample skill body.\n",
    URL_TWO: b"---\nname: helper\n---\nHelper skill body.\n",
}


def rawOf(url):
    return rec.rawUrlFor(rec.parseSkillBlobUrl(url))


class Fetcher:
    """Injected upstream; records every request so tests can prove nothing was fetched."""

    def __init__(self, contents=None):
        self.contents = {rawOf(url): data for url, data in (contents or BYTES).items()}
        self.calls = []

    def __call__(self, rawUrl):
        self.calls.append(rawUrl)
        if rawUrl not in self.contents:
            raise rec.RecoveryError(f"Upstream source returned HTTP 404: {rawUrl}", rec.EXIT_BLOCKED)
        return self.contents[rawUrl]


def scanSkill(skillId, name):
    skill = {
        "id": skillId, "name": name, "type": "basic",
        "description": f"Candidate skill detected from {SOURCE_REPO} usage: {name}.",
        "sourceRepo": SOURCE_REPO, "lifecycle": "pending",
    }
    return attach_identity(skill, SOURCE_REPO)


def richSkill(skillId, name, url, named=True):
    skill = {
        "id": skillId, "name": name, "type": "basic",
        "description": f"Does the {name} job end to end for reviewers.",
        "sourceRepo": SOURCE_REPO, "lifecycle": "pending", "prerequisites": [],
        "attribution": {"type": "self-made", "upstream_author": "ExampleSubmitter", "skill_file_url": url},
        "evidence": [{"grade": "C", "type": "repo", "url": f"https://github.com/{SOURCE_REPO}", "notes": "pipe | in notes"}],
    }
    if named:
        skill["named"] = {"contributor": "ExampleSubmitter", "skill_name": skillId, "level": "2★", "links_github": url}
    return attach_identity(skill, SOURCE_REPO)


def batchOf(skills, fromFile):
    return {
        "batchId": BATCH_ID, "userId": "ExampleSubmitter", "sourceRepo": SOURCE_REPO,
        "generatedAt": "2026-10-07T10:40:57Z", "batchBranch": "main", "fromFile": fromFile,
        "knownSkills": [], "proposedSkills": skills, "similarity": [],
    }


def issueOf(skills, fromFile, **overrides):
    issue = {
        "number": 4242, "state": "OPEN", "labels": [{"name": "intake"}, {"name": "needs-review"}],
        "body": build_intake_issue_body(batchOf(skills, fromFile)), "author": {"login": "example-submitter"},
    }
    issue.update(overrides)
    return issue


def scanIssue(**overrides):
    return issueOf([scanSkill("sample-skill", "Sample Skill"), scanSkill("helper-skill", "Helper Skill")], False, **overrides)


def richIssue(**overrides):
    return issueOf([richSkill("sample-skill", "Sample Skill", URL_ONE), richSkill("helper-skill", "Helper Skill", URL_TWO)], True, **overrides)


SCAN_FACTS = json.dumps({
    "sample-skill": {"description": "Samples things for reviewers end to end.", "skillFileUrl": URL_ONE},
    "helper-skill": {"description": "Helps the sample skill with its chores.", "skillFileUrl": URL_TWO},
})


def run(issue, tmp_path, facts="", actor="maintainer-one", permission="maintain",
        rationale="Original batch was never committed; maintainer verified the upstream blobs.",
        fetcher=None, comments=None):
    fetcher = fetcher or Fetcher()
    result = rec.recover(issue, actor, permission, rationale, facts, str(tmp_path), fetcher, comments)
    return result, fetcher


def allKeys(value):
    """Every dict key anywhere inside value."""
    if isinstance(value, dict):
        return set(value) | set().union(*[allKeys(item) for item in value.values()]) if value else set()
    if isinstance(value, list):
        return set().union(*[allKeys(item) for item in value]) if value else set()
    return set()


def noFiles(tmp_path):
    return not (tmp_path / "registry-for-review").exists()


def assertSchemaAndIntakeValid(tmp_path):
    jsonschema = pytest.importorskip("jsonschema")
    batchFile = tmp_path / rec.batchRelPath(BATCH_ID)
    jsonschema.validate(json.loads(batchFile.read_text(encoding="utf-8")), json.loads(SCHEMA.read_text(encoding="utf-8")))
    graph = tmp_path / "canonical.json"
    graph.write_text(json.dumps({"skills": [{"id": "web-search"}]}), encoding="utf-8")
    errors, _warnings, count = validateIntake.validate_intake(str(tmp_path / "registry-for-review"), str(graph), str(SCHEMA))
    assert errors == []
    assert count == 1


# ---------------------------------------------------------------------------
# absent-batch scan intake
# ---------------------------------------------------------------------------


def test_absent_batch_scan_intake_is_reconstructed_honestly(tmp_path):
    issue = scanIssue()
    result, fetcher = run(issue, tmp_path, facts=SCAN_FACTS)
    assert result["status"] == "recovered"

    batch = json.loads((tmp_path / rec.batchRelPath(BATCH_ID)).read_text(encoding="utf-8"))
    receipt = json.loads((tmp_path / rec.receiptRelPath(4242)).read_text(encoding="utf-8"))

    # original identities are preserved
    assert batch["batchId"] == BATCH_ID
    assert batch["generatedAt"] == "2026-10-07T10:40:57Z"
    assert batch["userId"] == "ExampleSubmitter"
    assert [skill["id"] for skill in batch["proposedSkills"]] == ["sample-skill", "helper-skill"]
    assert receipt["original"]["candidateIds"] == ["sample-skill", "helper-skill"]
    assert receipt["original"]["identity"]["skills"][0]["f"] == scanSkill("sample-skill", "Sample Skill")["fingerprint"]

    # reconstruction is declared, never byte-for-byte
    assert receipt["reconstruction"] is True
    assert receipt["originalBytesRecovered"] is False
    assert "original local batch JSON bytes" in receipt["notRecovered"]
    for skill in batch["proposedSkills"]:
        assert "not the original batch bytes" in skill["rationale"]
        assert skill["openQuestions"]

    # source URLs and hashes, actor and rationale are kept
    assert {item["url"]: item["sha256"] for item in receipt["sources"]} == {
        url: rec.sha256Hex(data) for url, data in BYTES.items()
    }
    assert all(item["origin"] == "maintainer-supplied" for item in receipt["sources"])
    assert receipt["authorization"] == {
        "recoveredBy": "maintainer-one", "permission": "maintain",
        "rationale": "Original batch was never committed; maintainer verified the upstream blobs.",
    }
    assert receipt["maintainerSuppliedFacts"]["sample-skill"] == ["description", "skillFileUrl"]

    # nothing fabricated: no evidence rows, no approvals, no similarity, no L4 material
    assert all(skill["evidence"] == [] for skill in batch["proposedSkills"])
    assert batch["similarity"] == []
    assert not allKeys([batch, receipt]) & {"l4Resolution", "humanReview", "approvalRef", "curationHandoff", "assessmentReceiptDigest"}
    assert set(batch) == {"batchId", "userId", "sourceRepo", "generatedAt", "knownSkills", "proposedSkills", "similarity"}

    assertSchemaAndIntakeValid(tmp_path)
    assert len(fetcher.calls) == 2


def test_rich_issue_needs_no_facts_and_keeps_issue_evidence_verbatim(tmp_path):
    result, _ = run(richIssue(), tmp_path)
    batch = result["batch"]
    sample = batch["proposedSkills"][0]
    assert sample["attribution"] == {"type": "self-made", "upstream_author": "ExampleSubmitter", "skill_file_url": URL_ONE}
    assert sample["named"] == {"contributor": "ExampleSubmitter", "skill_name": "sample-skill", "level": "2★", "links_github": URL_ONE}
    assert sample["evidence"] == [{"grade": "C", "type": "repo", "url": f"https://github.com/{SOURCE_REPO}", "notes": "pipe | in notes"}]
    assert sample["description"] == "Does the Sample Skill job end to end for reviewers."
    assert all(item["origin"] == "issue" for item in result["receipt"]["sources"])
    assert result["receipt"]["maintainerSuppliedFacts"] == {}
    assertSchemaAndIntakeValid(tmp_path)


# ---------------------------------------------------------------------------
# incomplete issue
# ---------------------------------------------------------------------------


def test_incomplete_issue_lists_each_missing_fact_and_writes_nothing(tmp_path):
    fetcher = Fetcher()
    with pytest.raises(rec.RecoveryError) as raised:
        run(scanIssue(), tmp_path, facts="", fetcher=fetcher)
    error = raised.value
    assert error.code == rec.EXIT_BLOCKED
    joined = "\n".join(error.lines)
    for skillId in ("sample-skill", "helper-skill"):
        assert f"skills[{skillId}].skillFileUrl" in joined
    assert noFiles(tmp_path)
    assert fetcher.calls == []


def test_partial_facts_still_name_what_remains(tmp_path):
    facts = json.dumps({"sample-skill": {"description": "Samples things for reviewers end to end.", "skillFileUrl": URL_ONE}})
    with pytest.raises(rec.RecoveryError) as raised:
        run(scanIssue(), tmp_path, facts=facts)
    joined = "\n".join(raised.value.lines)
    assert "skills[helper-skill].description" in joined and "skills[helper-skill].skillFileUrl" in joined
    assert "skills[sample-skill]" not in joined
    assert noFiles(tmp_path)


@pytest.mark.parametrize("row", ["Batch ID", "User", "Source repo", "Generated at"])
def test_missing_metadata_rows_are_named(tmp_path, row):
    issue = richIssue()
    issue["body"] = "\n".join(line for line in issue["body"].splitlines() if not line.startswith(f"| {row} |"))
    with pytest.raises(rec.RecoveryError) as raised:
        run(issue, tmp_path)
    assert raised.value.code == rec.EXIT_BLOCKED
    assert any(row in line for line in raised.value.lines)
    assert noFiles(tmp_path)


@pytest.mark.parametrize("batchId", ["../../escape", "a/b", "", ".hidden"])
def test_unsafe_batch_id_is_never_used_as_a_path(tmp_path, batchId):
    issue = richIssue()
    issue["body"] = issue["body"].replace(f"`{BATCH_ID}`", f"`{batchId}`" if batchId else "``")
    with pytest.raises(rec.RecoveryError) as raised:
        run(issue, tmp_path)
    assert raised.value.code == rec.EXIT_BLOCKED
    assert noFiles(tmp_path)


def test_issue_with_unreadable_skill_count_is_blocked(tmp_path):
    issue = richIssue()
    issue["body"] = issue["body"].replace("| Proposed new skills | `2` |", "| Proposed new skills | `5` |")
    with pytest.raises(rec.RecoveryError) as raised:
        run(issue, tmp_path)
    assert any("states 5 proposed skill(s)" in line for line in raised.value.lines)


def test_fusion_without_prerequisites_and_basic_with_prerequisites_are_blocked(tmp_path):
    fusion = richSkill("sample-skill", "Sample Skill", URL_ONE)
    fusion["type"] = "fusion"
    basic = richSkill("helper-skill", "Helper Skill", URL_TWO)
    basic["prerequisites"] = ["web-search"]
    with pytest.raises(rec.RecoveryError) as raised:
        run(issueOf([fusion, basic], True), tmp_path)
    joined = "\n".join(raised.value.lines)
    assert "skills[sample-skill].prerequisites (a fusion needs at least one)" in joined
    assert "skills[helper-skill].prerequisites (a basic skill has none)" in joined
    assert noFiles(tmp_path)


def test_fusion_with_prerequisites_is_carried_over(tmp_path):
    fusion = richSkill("sample-skill", "Sample Skill", URL_ONE)
    fusion["type"] = "fusion"
    fusion["prerequisites"] = ["web-search"]
    result, _ = run(issueOf([fusion, richSkill("helper-skill", "Helper Skill", URL_TWO)], True), tmp_path)
    assert result["batch"]["proposedSkills"][0]["type"] == "fusion"
    assert result["batch"]["proposedSkills"][0]["prerequisites"] == ["web-search"]


@pytest.mark.parametrize("facts,fragment", [
    ("not json", "not valid JSON"),
    ("[]", "keyed by skill id"),
    (json.dumps({"sample-skill": {"evidence": []}}), "unsupported key"),
    (json.dumps({"sample-skill": {"description": 7}}), "unusable value"),
    (json.dumps({"ghost-skill": {"description": "A ghost that the issue never lists."}}), "does not list"),
    (json.dumps({"sample-skill": {"name": "Different Name"}}), "contradicts the issue"),
])
def test_bad_or_conflicting_facts_are_rejected(tmp_path, facts, fragment):
    with pytest.raises(rec.RecoveryError) as raised:
        run(richIssue(), tmp_path, facts=facts)
    assert raised.value.code == rec.EXIT_BLOCKED
    assert fragment in str(raised.value) + "\n".join(raised.value.lines)
    assert noFiles(tmp_path)


def test_fact_may_not_contradict_an_issue_source(tmp_path):
    facts = json.dumps({"sample-skill": {"skillFileUrl": URL_TWO}})
    with pytest.raises(rec.RecoveryError) as raised:
        run(richIssue(), tmp_path, facts=facts)
    assert "contradicts the issue" in "\n".join(raised.value.lines)


# ---------------------------------------------------------------------------
# unauthorized actor / wrong issue
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("permission", ["read", "triage", "none", "", None, "ADMIN"])
def test_unauthorized_actor_is_refused_before_any_work(tmp_path, permission):
    fetcher = Fetcher()
    with pytest.raises(rec.RecoveryError) as raised:
        run(richIssue(), tmp_path, permission=permission, fetcher=fetcher)
    assert raised.value.code == rec.EXIT_REFUSED
    assert "cannot authorize intake recovery" in str(raised.value)
    assert noFiles(tmp_path) and fetcher.calls == []


@pytest.mark.parametrize("permission", ["admin", "maintain", "write"])
def test_each_maintainer_permission_is_accepted(tmp_path, permission):
    result, _ = run(richIssue(), tmp_path, permission=permission)
    assert result["status"] == "recovered"


@pytest.mark.parametrize("rationale", ["", "   ", "short"])
def test_rationale_is_required(tmp_path, rationale):
    with pytest.raises(rec.RecoveryError) as raised:
        run(richIssue(), tmp_path, rationale=rationale)
    assert raised.value.code == rec.EXIT_REFUSED
    assert noFiles(tmp_path)


@pytest.mark.parametrize("override", [{"labels": [{"name": "needs-triage"}]}, {"state": "CLOSED"}])
def test_only_open_intake_issues_are_recoverable(tmp_path, override):
    with pytest.raises(rec.RecoveryError) as raised:
        run(richIssue(**override), tmp_path)
    assert raised.value.code == rec.EXIT_REFUSED
    assert noFiles(tmp_path)


# ---------------------------------------------------------------------------
# malformed sources
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("url", [
    "http://github.com/o/r/blob/main/SKILL.md",
    "https://gitlab.com/o/r/blob/main/SKILL.md",
    "https://github.com/o/r/tree/main/SKILL.md",
    "https://github.com/o/r/blob/main/README.md",
    "https://github.com/o/r/blob/main/SKILL.md?raw=1",
    "https://github.com/o/r/blob/main/SKILL.md#top",
    "https://github.com/o/r/blob/main/../SKILL.md",
    "https://github.com/o/r/blob/main//SKILL.md",
    "https://user@github.com/o/r/blob/main/SKILL.md",
    "https://github.com/o/r/blob/feature/branch/SKILL.md/extra",
    "https://github.com.evil.example/o/r/blob/main/SKILL.md",
    "https://github.com/o/r/blob/main/skill.md",
    " https://github.com/o/r/blob/main/SKILL.md",
    "not a url",
])
def test_malformed_source_urls_are_rejected_before_fetching(tmp_path, url):
    assert rec.parseSkillBlobUrl(url) is None
    facts = json.dumps({
        "sample-skill": {"description": "Samples things for reviewers end to end.", "skillFileUrl": url},
        "helper-skill": {"description": "Helps the sample skill with its chores.", "skillFileUrl": URL_TWO},
    })
    fetcher = Fetcher()
    with pytest.raises(rec.RecoveryError) as raised:
        run(scanIssue(), tmp_path, facts=facts, fetcher=fetcher)
    assert raised.value.code == rec.EXIT_BLOCKED
    assert fetcher.calls == [] and noFiles(tmp_path)


def test_two_skills_may_not_share_one_source(tmp_path):
    facts = json.dumps({
        "sample-skill": {"description": "Samples things for reviewers end to end.", "skillFileUrl": URL_ONE},
        "helper-skill": {"description": "Helps the sample skill with its chores.", "skillFileUrl": URL_ONE},
    })
    with pytest.raises(rec.RecoveryError) as raised:
        run(scanIssue(), tmp_path, facts=facts)
    assert "repeats the source" in "\n".join(raised.value.lines)
    assert noFiles(tmp_path)


@pytest.mark.parametrize("content", [b"", b"\x00\x01binary", b"\xff\xfe not utf8", b"x" * (rec.MAX_SOURCE_BYTES + 1)])
def test_unusable_source_bytes_are_rejected(tmp_path, content):
    fetcher = Fetcher({URL_ONE: content, URL_TWO: BYTES[URL_TWO]})
    with pytest.raises(rec.RecoveryError) as raised:
        run(richIssue(), tmp_path, fetcher=fetcher)
    assert raised.value.code == rec.EXIT_BLOCKED
    assert noFiles(tmp_path)


def test_missing_upstream_blob_is_an_honest_failure_and_writes_nothing(tmp_path):
    with pytest.raises(rec.RecoveryError) as raised:
        run(richIssue(), tmp_path, fetcher=Fetcher({URL_TWO: BYTES[URL_TWO]}))
    assert "HTTP 404" in str(raised.value)
    assert noFiles(tmp_path)


def test_default_fetcher_only_talks_to_raw_github():
    with pytest.raises(rec.RecoveryError):
        rec.defaultFetcher("https://example.com/SKILL.md")
    with pytest.raises(rec.RecoveryError):
        rec.defaultFetcher("http://raw.githubusercontent.com/o/r/main/SKILL.md")


# ---------------------------------------------------------------------------
# replay / idempotency / staleness
# ---------------------------------------------------------------------------


def snapshot(tmp_path):
    return {
        str(path.relative_to(tmp_path)): path.read_bytes()
        for path in sorted(tmp_path.glob("registry-for-review/**/*")) if path.is_file()
    }


def test_replay_is_idempotent_byte_for_byte_even_for_another_maintainer(tmp_path):
    first, _ = run(richIssue(), tmp_path)
    before = snapshot(tmp_path)
    second, _ = run(richIssue(), tmp_path, actor="maintainer-two", permission="admin",
                    rationale="Replaying the same recovery from a second maintainer.")
    assert first["status"] == "recovered" and second["status"] == "already-recovered"
    assert snapshot(tmp_path) == before
    assert json.loads(before[rec.receiptRelPath(4242)])["authorization"]["recoveredBy"] == "maintainer-one"
    assert first["recordDigest"] == second["recordDigest"]


def test_recovery_files_are_deterministic_across_clean_runs(tmp_path):
    one, two = tmp_path / "one", tmp_path / "two"
    one.mkdir()
    two.mkdir()
    run(richIssue(), one)
    run(richIssue(), two)
    assert snapshot(one) == {key: value for key, value in snapshot(two).items()}


def test_changed_upstream_bytes_on_replay_are_rejected_as_stale(tmp_path):
    run(richIssue(), tmp_path)
    before = snapshot(tmp_path)
    moved = Fetcher({URL_ONE: b"---\nname: sample\n---\nChanged upstream.\n", URL_TWO: BYTES[URL_TWO]})
    with pytest.raises(rec.RecoveryError) as raised:
        run(richIssue(), tmp_path, fetcher=moved)
    assert raised.value.code == rec.EXIT_STALE and "Stale" in str(raised.value)
    assert snapshot(tmp_path) == before


def test_existing_original_batch_is_never_overwritten(tmp_path):
    path = tmp_path / rec.batchRelPath(BATCH_ID)
    path.parent.mkdir(parents=True)
    path.write_text('{"original": true}\n', encoding="utf-8")
    with pytest.raises(rec.RecoveryError) as raised:
        run(richIssue(), tmp_path)
    assert raised.value.code == rec.EXIT_REFUSED
    assert path.read_text(encoding="utf-8") == '{"original": true}\n'
    assert not (tmp_path / rec.receiptRelPath(4242)).exists()


def botComment(body, login="github-actions"):
    return {"author": {"login": login}, "body": body}


def test_identical_record_already_on_the_issue_is_not_posted_twice(tmp_path):
    first, _ = run(richIssue(), tmp_path)
    comment = rec.recoveryComment(first)
    other = tmp_path / "again"
    other.mkdir()
    replay, _ = run(richIssue(), other, comments={"comments": [botComment(comment)]})
    assert replay["alreadyRecorded"] is True


def test_a_forged_record_comment_from_a_non_bot_is_ignored(tmp_path):
    first, _ = run(richIssue(), tmp_path)
    comment = rec.recoveryComment(first)
    other = tmp_path / "other"
    other.mkdir()
    replay, _ = run(richIssue(), other, comments={"comments": [botComment(comment, "random-user")]})
    assert replay["alreadyRecorded"] is False


# ---------------------------------------------------------------------------
# normal batch-present intake stays unchanged
# ---------------------------------------------------------------------------


def legacyPayload(batchPath, issueNumber, approver):
    """Byte-for-byte what the workflow's previous inline Python printed."""
    with open(batchPath, encoding="utf-8") as handle:
        batch = json.load(handle)
    return json.dumps({
        "schemaVersion": 1, "batchId": batch["batchId"], "batchPath": batchPath, "issue": int(issueNumber),
        "topologyApprovedBy": approver, "evidenceReviewStatus": "pending",
    }, separators=(",", ":"))


def test_normal_batch_present_payload_is_byte_identical_to_the_legacy_payload(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    path = pathlib.Path(rec.batchRelPath(BATCH_ID))
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(batchOf([richSkill("sample-skill", "Sample Skill", URL_ONE)], True)), encoding="utf-8")
    assert rec.buildApprovalPayload(str(path), 4242, "maintainer-one", ".") == legacyPayload(str(path), 4242, "maintainer-one")
    assert "recovery" not in json.loads(rec.buildApprovalPayload(str(path), 4242, "maintainer-one", "."))


def test_normal_intake_has_nothing_to_materialize(tmp_path):
    comments = {"comments": [botComment('<!-- gaia-intake-approval {"schemaVersion":1,"issue":4242} -->')]}
    assert rec.materialize(4242, comments, str(tmp_path), Fetcher()) == {"status": "no-recovery", "files": []}
    assert noFiles(tmp_path)


# ---------------------------------------------------------------------------
# topology -> evidence hand-off (materialize)
# ---------------------------------------------------------------------------


def handoff(tmp_path, issueFactory=richIssue):
    """Run topology-stage recovery in one checkout and return the comments it would post."""
    topology = tmp_path / "topology"
    topology.mkdir()
    result, _ = run(issueFactory(), topology, facts=SCAN_FACTS if issueFactory is scanIssue else "")
    payload = rec.buildApprovalPayload(rec.batchRelPath(BATCH_ID), 4242, "maintainer-one", str(topology))
    comments = {"comments": [
        botComment(rec.recoveryComment(result)),
        botComment(f"## Intake topology approved\n\n<!-- gaia-intake-approval {payload} -->"),
    ]}
    return result, comments, json.loads(payload)


def test_approval_payload_binds_the_recovery_record(tmp_path):
    result, _, payload = handoff(tmp_path)
    assert payload["recovery"] == {
        "receiptPath": rec.receiptRelPath(4242),
        "receiptSha256": rec.sha256Hex(rec.canonicalJson(result["receipt"])),
        "batchSha256": result["receipt"]["reconstructedBatch"]["sha256"],
        "reconstruction": True,
    }
    assert payload["evidenceReviewStatus"] == "pending"


@pytest.mark.parametrize("issueFactory", [richIssue, scanIssue])
def test_evidence_stage_materializes_the_recorded_reconstruction(tmp_path, issueFactory):
    result, comments, _ = handoff(tmp_path, issueFactory)
    branch = tmp_path / "promotion"
    branch.mkdir()
    outcome = rec.materialize(4242, comments, str(branch), Fetcher())
    assert outcome == {"status": "materialized", "files": [rec.batchRelPath(BATCH_ID), rec.receiptRelPath(4242)]}
    assert json.loads((branch / rec.batchRelPath(BATCH_ID)).read_text(encoding="utf-8")) == result["batch"]
    assert json.loads((branch / rec.receiptRelPath(4242)).read_text(encoding="utf-8")) == result["receipt"]
    again = rec.materialize(4242, comments, str(branch), Fetcher())
    assert again["status"] == "recovery-already-present" and again["files"] == []


def test_evidence_stage_rejects_stale_upstream(tmp_path):
    _, comments, _ = handoff(tmp_path)
    branch = tmp_path / "promotion"
    branch.mkdir()
    moved = Fetcher({URL_ONE: b"changed after approval\n", URL_TWO: BYTES[URL_TWO]})
    with pytest.raises(rec.RecoveryError) as raised:
        rec.materialize(4242, comments, str(branch), moved)
    assert raised.value.code == rec.EXIT_STALE
    assert noFiles(branch)


def test_evidence_stage_ignores_records_and_approvals_not_written_by_the_bot(tmp_path):
    _, comments, _ = handoff(tmp_path)
    forged = {"comments": [dict(comment, author={"login": "random-user"}) for comment in comments["comments"]]}
    branch = tmp_path / "promotion"
    branch.mkdir()
    assert rec.materialize(4242, forged, str(branch), Fetcher())["status"] == "no-recovery"
    assert noFiles(branch)


def test_evidence_stage_requires_the_approval_to_be_bound_to_the_record(tmp_path):
    _, comments, _ = handoff(tmp_path)
    unbound = {"comments": [comments["comments"][0], botComment('<!-- gaia-intake-approval {"schemaVersion":1,"issue":4242} -->')]}
    branch = tmp_path / "promotion"
    branch.mkdir()
    with pytest.raises(rec.RecoveryError) as raised:
        rec.materialize(4242, unbound, str(branch), Fetcher())
    assert raised.value.code == rec.EXIT_STALE
    assert noFiles(branch)


def test_tampered_record_is_rejected(tmp_path):
    result, comments, _ = handoff(tmp_path)
    decoded = rec.decodeRecord(comments["comments"][0]["body"])
    decoded["batch"]["proposedSkills"][0]["description"] = "A tampered description for the record."
    tampered = "<!-- gaia-intake-recovery-record %s -->" % base64.b64encode(
        rec.canonicalJson(decoded).encode("utf-8")).decode("ascii")
    branch = tmp_path / "promotion"
    branch.mkdir()
    with pytest.raises(rec.RecoveryError):
        rec.materialize(4242, {"comments": [botComment(tampered), comments["comments"][1]]}, str(branch), Fetcher())
    assert noFiles(branch)


def test_original_batch_in_the_checkout_wins_over_the_record(tmp_path):
    _, comments, _ = handoff(tmp_path)
    branch = tmp_path / "promotion"
    path = branch / rec.batchRelPath(BATCH_ID)
    path.parent.mkdir(parents=True)
    path.write_text('{"original": true}\n', encoding="utf-8")
    outcome = rec.materialize(4242, comments, str(branch), Fetcher())
    assert outcome == {"status": "original-batch-present", "files": []}
    assert path.read_text(encoding="utf-8") == '{"original": true}\n'


# ---------------------------------------------------------------------------
# command line wiring (what the workflow calls)
# ---------------------------------------------------------------------------


def test_cli_recover_payload_materialize_round_trip(tmp_path, capsys):
    issueFile = tmp_path / "issue.json"
    issue = richIssue()
    issue["comments"] = []
    issueFile.write_text(json.dumps(issue), encoding="utf-8")
    topology = tmp_path / "topology"
    topology.mkdir()
    commentFile = tmp_path / "recovery-comment.md"
    code = rec.main(["recover", "--issue-json", str(issueFile), "--actor", "maintainer-one", "--permission", "write",
                     "--rationale", "Batch never committed; sources verified.", "--repo-root", str(topology),
                     "--comment-out", str(commentFile)], fetcher=Fetcher())
    assert code == rec.EXIT_OK
    assert "reconstruction, not original bytes" in capsys.readouterr().out
    assert "gaia-intake-recovery-record" in commentFile.read_text(encoding="utf-8")

    assert rec.main(["payload", "--batch", rec.batchRelPath(BATCH_ID), "--issue", "4242", "--approver", "maintainer-one",
                     "--repo-root", str(topology)]) == rec.EXIT_OK
    payload = capsys.readouterr().out.strip()
    assert json.loads(payload)["recovery"]["reconstruction"] is True

    commentsFile = tmp_path / "comments.json"
    commentsFile.write_text(json.dumps({"comments": [
        botComment(commentFile.read_text(encoding="utf-8")),
        botComment(f"<!-- gaia-intake-approval {payload} -->"),
    ]}), encoding="utf-8")
    branch = tmp_path / "promotion"
    branch.mkdir()
    filesOut = tmp_path / "files.txt"
    assert rec.main(["materialize", "--issue", "4242", "--comments-json", str(commentsFile), "--repo-root", str(branch),
                     "--files-out", str(filesOut)], fetcher=Fetcher()) == rec.EXIT_OK
    assert filesOut.read_text(encoding="utf-8").split() == [rec.batchRelPath(BATCH_ID), rec.receiptRelPath(4242)]


def test_cli_exit_codes_distinguish_refusal_from_blocked(tmp_path, capsys):
    issueFile = tmp_path / "issue.json"
    issueFile.write_text(json.dumps(scanIssue()), encoding="utf-8")
    base = ["recover", "--issue-json", str(issueFile), "--rationale", "A valid long enough rationale.", "--repo-root", str(tmp_path)]
    assert rec.main(base + ["--actor", "intruder", "--permission", "read"], fetcher=Fetcher()) == rec.EXIT_REFUSED
    assert rec.main(base + ["--actor", "maintainer-one", "--permission", "write"], fetcher=Fetcher()) == rec.EXIT_BLOCKED
    assert "skills[sample-skill].skillFileUrl" in capsys.readouterr().err
    assert rec.main(base + ["--actor", "maintainer-one", "--permission", "write", "--no-fetch"], fetcher=Fetcher()) == rec.EXIT_REFUSED
    assert noFiles(tmp_path)


# ---------------------------------------------------------------------------
# workflow wiring: thin YAML, explicit route, gates intact
# ---------------------------------------------------------------------------


def workflow():
    return yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))


def stepsOf(job):
    return workflow()["jobs"][job]["steps"]


def stepNamed(job, prefix):
    return next(step for step in stepsOf(job) if (step.get("name") or "").startswith(prefix))


def test_recovery_inputs_exist_on_workflow_dispatch_only():
    doc = workflow()
    inputs = doc[True]["workflow_dispatch"]["inputs"]
    assert inputs["recovery"]["type"] == "boolean" and inputs["recovery"]["default"] is False
    assert {"recovery_rationale", "recovery_facts"} <= set(inputs)
    assert "recovery" not in doc[True]["issues"]
    validate = stepNamed("topology-approved", "Validate the intake batch")
    assert "workflow_dispatch" in validate["env"]["RECOVERY"]


def test_recovery_inputs_flow_through_env_never_interpolated_into_scripts():
    for job in ("topology-approved", "evidence-approved"):
        for step in stepsOf(job):
            code = "\n".join(line for line in step.get("run", "").splitlines() if not line.strip().startswith("#"))
            for name in ("inputs.recovery", "inputs.recovery_rationale", "inputs.recovery_facts"):
                assert f"${{{{ {name} }}}}" not in code
    env = stepNamed("topology-approved", "Validate the intake batch")["env"]
    assert env["RECOVERY_RATIONALE"] == "${{ inputs.recovery_rationale }}"
    assert env["RECOVERY_FACTS"] == "${{ inputs.recovery_facts }}"
    assert env["PERMISSION"] == "${{ steps.maintainer.outputs.permission }}"


def test_label_event_without_recovery_still_fails_on_an_absent_batch_and_names_the_route():
    run = stepNamed("topology-approved", "Validate the intake batch")["run"]
    guard = run.index('if [ ! -f "$batch" ]')
    assert run.index('if [ "$RECOVERY" != "true" ]') > guard
    assert "workflow_dispatch" in run[guard:run.index("exit 1", guard)]
    assert 'test -f "$batch"' in run  # the original contract is still enforced after recovery


def test_recovery_runs_after_the_maintainer_gate_and_before_every_existing_gate():
    names = [step.get("name") or step.get("uses") for step in stepsOf("topology-approved")]
    assert names.index("Require a repository maintainer") < names.index("actions/checkout@v4")
    run = stepNamed("topology-approved", "Validate the intake batch")["run"]
    positions = [run.index(token) for token in (
        ".intake-tools/scripts/intake_recovery.py recover", 'test -f "$batch"', "scripts/assemble_gaia.py",
        "scripts/validate_intake.py", ".intake-tools/scripts/intake_recovery.py payload", "intake:evidence-review",
    )]
    assert positions == sorted(positions)
    assert stepNamed("topology-approved", "Require a repository maintainer")["id"] == "maintainer"
    assert 'permission=$permission' in stepNamed("topology-approved", "Require a repository maintainer")["run"]


def test_yaml_stays_thin_recovery_logic_lives_in_the_script():
    run = stepNamed("topology-approved", "Validate the intake batch")["run"]
    block = run[run.index('if [ ! -f "$batch" ]'):run.index('test -f "$batch"')]
    assert len([line for line in block.splitlines() if line.strip() and not line.strip().startswith("#")]) <= 16
    for token in ("json.loads", "sha256", "re.search"):
        assert token not in block


def test_evidence_gates_and_single_pr_contract_are_untouched():
    run = stepNamed("evidence-approved", "Create or reuse the batch promotion PR")["run"]
    assert '"intake:evidence-review", "intake:evidence-ready"' in run
    assert run.index("gh pr list --state open") < run.index(".intake-tools/scripts/intake_recovery.py materialize") < run.index('git checkout -b "$branch"')
    assert run.count("gh pr create --draft") == 1
    assert 'branch="review/meta/intake-${ISSUE_NUMBER}"' in run
    assert "xargs git add" in run
    names = [step.get("name") or step.get("uses") for step in stepsOf("evidence-approved")]
    assert names.index("Require a repository maintainer") < names.index("actions/checkout@v4")


def test_tooling_comes_from_the_workflow_commit_not_the_batch_branch():
    """An older batch branch may lack scripts/intake_recovery.py; normal intakes must not break on that."""
    for job in ("topology-approved", "evidence-approved"):
        names = [step.get("name") or step.get("uses") for step in stepsOf(job)]
        tools = stepNamed(job, "Check out the intake tooling")
        assert tools["with"]["ref"] == "${{ github.sha }}"
        assert tools["with"]["path"] == ".intake-tools"
        assert tools["with"]["sparse-checkout"] == "scripts/intake_recovery.py"
        assert names.index("actions/checkout@v4") < names.index(tools["name"])
        for step in stepsOf(job):
            assert "python3 scripts/intake_recovery.py" not in step.get("run", "")
