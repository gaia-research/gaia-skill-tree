"""Issue-backed recovery of a `gaia push` intake whose batch file was never committed (#2050).

Synthetic fixtures only. Issue bodies come from the real renderer
(`gaia_cli.prWriter.build_intake_issue_body`) so the parser is tested against what
`gaia push` actually posts. Upstream fetching is injected; no test touches the network.
"""

import base64
import copy
import importlib.util
import json
import io
import zipfile
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


REPOSITORY = "gaia-research/gaia-skill-tree"
HANDOFFS = {}


def registerHandoff(payload, record=None):
    HANDOFFS[payload["workflowRunId"]] = {"approval": copy.deepcopy(payload), "record": copy.deepcopy(record)}


def fakeGithubApi(endpoint, binary=False):
    """Authenticated server fixture: metadata and immutable bytes live outside issue comments."""
    assert endpoint.startswith(f"repos/{REPOSITORY}/")
    if endpoint.endswith("actions/workflows/intake-approval.yml"):
        return {"id": 71, "path": rec.WORKFLOW_PATH}
    if "/collaborators/" in endpoint:
        return {"permission": "write"}
    if "/attempts/" in endpoint:
        runId = int(endpoint.split("/runs/")[1].split("/")[0])
        payload = HANDOFFS[runId]["approval"]
        return {"id": runId, "run_attempt": payload["workflowRunAttempt"], "workflow_id": 71,
                "path": rec.WORKFLOW_PATH, "repository": {"full_name": REPOSITORY},
                "head_repository": {"full_name": REPOSITORY}, "head_sha": payload["workflowHeadSha"],
                "event": "workflow_dispatch", "status": "completed", "conclusion": "success",
                "actor": {"login": payload["topologyApprovedBy"]},
                "triggering_actor": {"login": payload["topologyApprovedBy"]}}
    if "/runs/" in endpoint and "/artifacts" in endpoint:
        runId = int(endpoint.split("/runs/")[1].split("/")[0])
        payload = HANDOFFS[runId]["approval"]
        return {"artifacts": [{"id": runId, "size_in_bytes": 1000, "expired": False,
                              "name": rec.handoffArtifactName(payload["issue"], runId, payload["workflowRunAttempt"])}]}
    if endpoint.endswith("/zip"):
        assert binary
        artifactId = int(endpoint.split("/artifacts/")[1].split("/")[0])
        stream = io.BytesIO()
        with zipfile.ZipFile(stream, "w") as archive:
            archive.writestr("intake-handoff.json", json.dumps(HANDOFFS[artifactId]))
        return stream.getvalue()
    raise AssertionError(endpoint)


@pytest.fixture(autouse=True)
def authenticatedGithub(monkeypatch):
    HANDOFFS.clear()
    monkeypatch.setattr(rec, "githubApi", fakeGithubApi)
    monkeypatch.setenv("GH_REPO", REPOSITORY)
    monkeypatch.setenv("GITHUB_RUN_ID", "1001")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")
    monkeypatch.setenv("GITHUB_SHA", "a" * 40)


def normalApproval(tmp_path, body="x"):
    batch = batchOf([richSkill("sample-skill", "Sample Skill", URL_ONE)], True)
    path = tmp_path / rec.batchRelPath(BATCH_ID)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(batch), encoding="utf-8")
    payload = json.loads(rec.buildApprovalPayload(rec.batchRelPath(BATCH_ID), 4242, "maintainer-one", str(tmp_path),
                        issueBody=body, runId=1001, runAttempt=1, headSha="a" * 40))
    registerHandoff(payload)
    return {"body": body, "comments": [botComment(approvalComment(json.dumps(payload)))]}


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
        skill["named"] = {"contributor": "examplesubmitter", "skill_name": skillId, "level": "2★", "links_github": url}
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
    assert sample["named"] == {"contributor": "examplesubmitter", "skill_name": "sample-skill", "level": "2★", "links_github": URL_ONE}
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
    comments = normalApproval(tmp_path)
    assert rec.materialize(4242, comments, str(tmp_path), Fetcher()) == {"status": "no-recovery", "files": []}


# ---------------------------------------------------------------------------
# topology -> evidence hand-off (materialize)
# ---------------------------------------------------------------------------


def approvalComment(payload):
    """The topology approval comment exactly as the workflow writes it (header first)."""
    return f"{rec.APPROVAL_HEADER}\n\nThe batch topology is accepted.\n\n<!-- gaia-intake-approval {payload} -->\n"


def handoff(tmp_path, issueFactory=richIssue, name="topology", actor="maintainer-one", existing=None):
    """Run topology-stage recovery in one fresh checkout and return the comments it would post."""
    topology = tmp_path / name
    topology.mkdir()
    issue = issueFactory()
    result, _ = run(issue, topology, facts=SCAN_FACTS if issueFactory is scanIssue else "", actor=actor, comments=existing)
    payload = rec.buildApprovalPayload(rec.batchRelPath(BATCH_ID), 4242, actor, str(topology),
        issueBody=issue["body"], runId=1001 + len(HANDOFFS), runAttempt=1, headSha="a" * 40)
    registerHandoff(json.loads(payload), {"batch": result["batch"], "receipt": result["receipt"]})
    posted = [] if result["alreadyRecorded"] else [botComment(rec.recoveryComment(result))]
    posted.append(botComment(approvalComment(payload)))
    comments = {"body": issue["body"], "comments": list((existing or {}).get("comments", [])) + posted}
    return result, comments, json.loads(payload)


def test_approval_payload_binds_the_recovery_record(tmp_path):
    result, _, payload = handoff(tmp_path)
    assert payload["recovery"] == {
        "receiptPath": rec.receiptRelPath(4242),
        "recordDigest": rec.recordIdentityDigest(result["batch"], result["receipt"]),
        "batchSha256": result["receipt"]["reconstructedBatch"]["sha256"],
        "issueBodySha256": result["receipt"]["issueBodySha256"],
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
    forged = {"body": comments["body"], "comments": [dict(comment, author={"login": "random-user"}) for comment in comments["comments"]]}
    branch = tmp_path / "promotion"
    branch.mkdir()
    with pytest.raises(rec.RecoveryError, match="No authenticated topology approval"):
        rec.materialize(4242, forged, str(branch), Fetcher())
    assert noFiles(branch)


def test_approval_without_recovery_means_nothing_to_materialize(tmp_path):
    comments = normalApproval(tmp_path)
    assert rec.materialize(4242, comments, str(tmp_path), Fetcher())["status"] == "no-recovery"


def test_approval_naming_a_record_that_is_not_on_the_issue_is_stale(tmp_path):
    _, comments, _ = handoff(tmp_path)
    missing = comments
    HANDOFFS[1001]["record"] = None  # immutable handoff must contain the reconstruction
    branch = tmp_path / "promotion"
    branch.mkdir()
    with pytest.raises(rec.RecoveryError) as raised:
        rec.materialize(4242, missing, str(branch), Fetcher())
    assert raised.value.code == rec.EXIT_STALE
    assert noFiles(branch)


def test_tampered_comment_record_cannot_replace_the_immutable_record(tmp_path):
    result, comments, _ = handoff(tmp_path)
    decoded = rec.decodeRecord(comments["comments"][0]["body"])
    decoded["batch"]["proposedSkills"][0]["description"] = "A tampered description for the record."
    tampered = "<!-- gaia-intake-recovery-record %s -->" % base64.b64encode(
        rec.canonicalJson(decoded).encode("utf-8")).decode("ascii")
    branch = tmp_path / "promotion"
    branch.mkdir()
    rec.materialize(4242, {"body": comments["body"], "comments": [botComment(tampered), comments["comments"][1]]}, str(branch), Fetcher())
    assert json.loads((branch / rec.batchRelPath(BATCH_ID)).read_text()) == result["batch"]


def test_original_batch_in_the_checkout_wins_over_the_record(tmp_path):
    _, comments, _ = handoff(tmp_path)
    branch = tmp_path / "promotion"
    path = branch / rec.batchRelPath(BATCH_ID)
    path.parent.mkdir(parents=True)
    path.write_text('{"original": true}\n', encoding="utf-8")
    with pytest.raises(rec.RecoveryError, match="differs from the topology-approved batch"):
        rec.materialize(4242, comments, str(branch), Fetcher())
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
                     "--repo-root", str(topology), "--issue-json", str(issueFile),
                     "--handoff-out", str(tmp_path / "intake-handoff.json")]) == rec.EXIT_OK
    payload = capsys.readouterr().out.strip()
    handoffDoc = json.loads((tmp_path / "intake-handoff.json").read_text())
    registerHandoff(handoffDoc["approval"], handoffDoc["record"])
    assert json.loads(payload)["recovery"]["reconstruction"] is True

    commentsFile = tmp_path / "comments.json"
    commentsFile.write_text(json.dumps({"body": issue["body"], "comments": [
        botComment(commentFile.read_text(encoding="utf-8")),
        botComment(approvalComment(payload)),
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
        "scripts/validate_intake.py", ".intake-tools/scripts/intake_recovery.py payload",
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
    assert run.index(".intake-tools/scripts/intake_recovery.py materialize") < run.index("gh pr list --state open") < run.index('git checkout -b "$branch"')
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


# ---------------------------------------------------------------------------
# forged markers (review finding 1)
# ---------------------------------------------------------------------------


def forgedPair(tmp_path):
    """A record + bound approval an issue author could try to smuggle into a bot comment."""
    result, comments, _ = handoff(tmp_path)
    return comments["comments"][0]["body"], comments["comments"][1]["body"], comments["body"]


@pytest.mark.parametrize("wrap", [
    lambda text: "## Intake topology approval failed\n\n```\n" + text + "\n```\n",   # the real failure-comment shape
    lambda text: "Intro line\n" + text,                                               # header not first
    lambda text: " " + text,                                                          # leading whitespace
])
def test_forged_markers_inside_a_bot_comment_with_another_header_are_ignored(tmp_path, wrap):
    record, approval, body = forgedPair(tmp_path)
    forged = {"body": body, "comments": [botComment(wrap(record)), botComment(wrap(approval))]}
    branch = tmp_path / "promotion"
    branch.mkdir()
    with pytest.raises(rec.RecoveryError, match="No authenticated topology approval"):
        rec.materialize(4242, forged, str(branch), Fetcher())
    assert noFiles(branch)


def test_forged_record_cannot_block_a_normal_intake(tmp_path):
    record, _, body = forgedPair(tmp_path)
    branch = tmp_path / "promotion"
    branch.mkdir()
    comments = normalApproval(branch, body)
    comments["comments"].insert(0, botComment("## Intake topology approval failed\n\n" + record))
    assert rec.materialize(4242, comments, str(branch), Fetcher())["status"] == "no-recovery"


def test_forged_record_with_evil_batch_is_never_materialized(tmp_path):
    result, comments, _ = handoff(tmp_path)
    evil = copy.deepcopy(result["batch"])
    evil["batchId"] = "evil-batch"
    receipt = copy.deepcopy(result["receipt"])
    receipt["reconstructedBatch"] = {"path": rec.batchRelPath("evil-batch"), "sha256": rec.sha256Hex(rec.canonicalJson(evil))}
    marker = f"<!-- gaia-intake-recovery-record {rec.encodeRecord(evil, receipt)} -->"
    payload = rec.buildApprovalPayload(rec.batchRelPath(BATCH_ID), 4242, "x", str(tmp_path / "topology"))
    forgedApproval = json.loads(payload)
    forgedApproval["recovery"]["recordDigest"] = rec.recordIdentityDigest(evil, receipt)
    forgedApproval["recovery"]["batchSha256"] = receipt["reconstructedBatch"]["sha256"]
    attack = {"body": comments["body"], "comments": [
        botComment("## Intake topology approval failed\n\n" + marker),
        botComment("## Intake topology approval failed\n\n<!-- gaia-intake-approval " + json.dumps(forgedApproval) + " -->"),
    ]}
    branch = tmp_path / "promotion"
    branch.mkdir()
    with pytest.raises(rec.RecoveryError, match="No authenticated topology approval"):
        rec.materialize(4242, attack, str(branch), Fetcher())
    assert noFiles(branch)


def test_a_valid_approval_only_selects_the_record_with_its_own_digest(tmp_path):
    result, comments, _ = handoff(tmp_path)
    other = copy.deepcopy(result["batch"])
    other["proposedSkills"][0]["description"] = "A different reconstruction that was never approved."
    receipt = copy.deepcopy(result["receipt"])
    receipt["reconstructedBatch"]["sha256"] = rec.sha256Hex(rec.canonicalJson(other))
    decoy = rec.recoveryComment({"batch": other, "receipt": receipt, "batchPath": rec.batchRelPath(BATCH_ID)})
    mixed = {"body": comments["body"], "comments": [comments["comments"][0], botComment(decoy), comments["comments"][1]]}
    branch = tmp_path / "promotion"
    branch.mkdir()
    rec.materialize(4242, mixed, str(branch), Fetcher())
    written = json.loads((branch / rec.batchRelPath(BATCH_ID)).read_text(encoding="utf-8"))
    assert written == result["batch"]


def test_marker_text_inside_the_rationale_cannot_replace_the_record(tmp_path):
    rationale = "Verified blobs <!-- gaia-intake-recovery-record AAAA --> by hand."
    topology = tmp_path / "topology"
    topology.mkdir()
    result, _ = run(richIssue(), topology, rationale=rationale)
    comment = rec.recoveryComment(result)
    assert "<!-- gaia-intake-recovery-record AAAA" not in comment
    assert rec.decodeRecord(comment)["batch"] == result["batch"]


def test_log_text_is_made_inert():
    assert "<!--" not in rec.sanitizeLog("see <!-- gaia-intake-approval {} --> now")
    assert "-->" not in rec.sanitizeLog("a --> b")


# ---------------------------------------------------------------------------
# replay across fresh checkouts and edited bodies (findings 2 and 3)
# ---------------------------------------------------------------------------


def test_replay_from_a_fresh_checkout_by_another_maintainer_still_materializes(tmp_path):
    first, comments, _ = handoff(tmp_path, name="topology-one")
    again, comments, payload = handoff(
        tmp_path, name="topology-two", actor="maintainer-two", existing=comments)
    assert again["alreadyRecorded"] is True
    assert payload["recovery"]["recordDigest"] == rec.recordIdentityDigest(first["batch"], first["receipt"])
    branch = tmp_path / "promotion"
    branch.mkdir()
    outcome = rec.materialize(4242, comments, str(branch), Fetcher())
    assert outcome["status"] == "materialized"
    receipt = json.loads((branch / rec.receiptRelPath(4242)).read_text(encoding="utf-8"))
    assert receipt["authorization"]["recoveredBy"] == "maintainer-two"  # actor authenticated for this handoff


def test_immaterial_issue_edit_replay_is_idempotent_and_pins_the_new_body(tmp_path):
    _, comments, _ = handoff(tmp_path, name="topology-one")

    def edited():
        issue = richIssue()
        issue["body"] += "\n\nMaintainer note: looks fine.\n"
        return issue

    again, comments, payload = handoff(tmp_path, edited, name="topology-two", existing=comments)
    assert again["alreadyRecorded"] is True
    branch = tmp_path / "promotion"
    branch.mkdir()
    assert rec.materialize(4242, comments, str(branch), Fetcher())["status"] == "materialized"


def test_issue_body_edited_after_approval_requires_re_approval(tmp_path):
    _, comments, _ = handoff(tmp_path)
    comments = dict(comments, body=comments["body"] + "\nEdited after approval.\n")
    branch = tmp_path / "promotion"
    branch.mkdir()
    with pytest.raises(rec.RecoveryError) as raised:
        rec.materialize(4242, comments, str(branch), Fetcher())
    assert raised.value.code == rec.EXIT_STALE
    assert "Re-run the topology approval" in str(raised.value)
    assert noFiles(branch)


def test_missing_issue_body_cannot_be_verified(tmp_path):
    _, comments, _ = handoff(tmp_path)
    comments = {"comments": comments["comments"]}
    branch = tmp_path / "promotion"
    branch.mkdir()
    with pytest.raises(rec.RecoveryError) as raised:
        rec.materialize(4242, comments, str(branch), Fetcher())
    assert raised.value.code == rec.EXIT_STALE


def test_material_issue_edit_makes_a_new_record_and_the_new_approval_selects_it(tmp_path):
    first, comments, _ = handoff(tmp_path, name="topology-one")

    def edited():
        issue = richIssue()
        issue["body"] = issue["body"].replace("Does the Sample Skill job end to end for reviewers.",
                                              "Does the Sample Skill job, now described differently.")
        return issue

    second, comments, _ = handoff(tmp_path, edited, name="topology-two", existing=comments)
    assert second["alreadyRecorded"] is False
    branch = tmp_path / "promotion"
    branch.mkdir()
    assert rec.materialize(4242, comments, str(branch), Fetcher())["status"] == "materialized"
    written = json.loads((branch / rec.batchRelPath(BATCH_ID)).read_text(encoding="utf-8"))
    assert written == second["batch"] and written != first["batch"]


# ---------------------------------------------------------------------------
# N:1 fan-out intakes (finding 5): an explicit, documented honest failure
# ---------------------------------------------------------------------------


def test_n_to_one_fan_out_intake_is_blocked_with_the_route_that_does_work(tmp_path):
    first = richSkill("shared-capability", "First Impl", URL_ONE)
    second = richSkill("shared-capability", "Second Impl", URL_TWO)
    second["named"]["skill_name"] = "second-impl"
    with pytest.raises(rec.RecoveryError) as raised:
        run(issueOf([first, second], True), tmp_path)
    assert raised.value.code == rec.EXIT_BLOCKED
    joined = "\n".join(raised.value.lines)
    assert "N:1 fan-out" in joined and "gaia push --from-file" in joined and "discovery-packet-manifest-v1" in joined
    assert noFiles(tmp_path)


# ---------------------------------------------------------------------------
# workflow hardening (findings 1 and 4)
# ---------------------------------------------------------------------------


def test_workflow_approval_comment_starts_with_the_header_the_script_trusts():
    run = stepNamed("topology-approved", "Validate the intake batch")["run"]
    after = run.split("cat > /tmp/comment.md <<EOF\n", 1)[1]
    assert after.splitlines()[0].strip() == rec.APPROVAL_HEADER
    assert rec.RECORD_HEADER in (ROOT / "scripts/intake_recovery.py").read_text(encoding="utf-8")


def test_failure_comments_neutralize_html_comment_delimiters():
    for job in ("topology-approved", "evidence-approved"):
        failing = [step["run"] for step in stepsOf(job) if "intake-fail-comment.md" in step.get("run", "")]
        assert failing, job
        for run in failing:
            tail = next(line for line in run.splitlines() if "tail -c 4000" in line)
            assert "sed" in tail and "<!--" in tail and "-->" in tail
            failureHeader = next(line.split('echo "', 1)[1].rstrip('"') for line in run.splitlines() if 'echo "## Intake' in line)
            assert not failureHeader.startswith(rec.APPROVAL_HEADER) and not failureHeader.startswith(rec.RECORD_HEADER)


def test_issue_number_input_flows_through_env_and_is_validated_as_an_integer():
    for job in ("topology-approved", "evidence-approved"):
        resolve = stepNamed(job, "Resolve and validate issue")
        assert resolve["env"]["ISSUE_NUMBER_INPUT"] == "${{ inputs.issue_number }}"
        code = "\n".join(line for line in resolve["run"].splitlines() if not line.strip().startswith("#"))
        assert "${{ inputs.issue_number }}" not in code
        assert 'number="$ISSUE_NUMBER_INPUT"' in code
        assert code.index("*[!0-9]*") < code.index('echo "number=$number"')


def test_token_permissions_are_least_privilege_per_job():
    doc = workflow()
    assert doc["permissions"] == {"contents": "read"}
    assert doc["jobs"]["topology-approved"]["permissions"] == {"contents": "read", "issues": "write"}
    assert doc["jobs"]["evidence-approved"]["permissions"] == {
        "actions": "read", "contents": "write", "issues": "write", "pull-requests": "write"}


def test_evidence_job_fetches_the_issue_body_for_the_approval_pin():
    run = stepNamed("evidence-approved", "Create or reuse the batch promotion PR")["run"]
    assert "--json number,body,comments" in run


@pytest.mark.parametrize("field,value", [
    ("repository", {"full_name": "attacker/fork"}),
    ("head_repository", {"full_name": "attacker/fork"}),
    ("workflow_id", 999),
    ("path", ".github/workflows/comment-on-issue.yml"),
    ("event", "pull_request"),
    ("event", "issue_comment"),
    ("status", "in_progress"),
    ("conclusion", "failure"),
    ("head_sha", "b" * 40),
    ("run_attempt", 2),
    ("actor", {"login": "issue-author"}),
    ("triggering_actor", {}),
])
def test_artifact_requires_authenticated_repository_workflow_event_and_identity(tmp_path, field, value):
    _, _, approval = handoff(tmp_path)

    def api(endpoint, binary=False):
        response = fakeGithubApi(endpoint, binary)
        if "/attempts/" in endpoint:
            response[field] = value
        return response

    with pytest.raises(rec.RecoveryError):
        rec.verifyHandoff(approval, api=api, repository=REPOSITORY)


@pytest.mark.parametrize("actor", ["maintainer-one", "rerun-actor"])
def test_original_and_rerun_actors_require_current_permission(tmp_path, actor):
    _, _, approval = handoff(tmp_path)

    def api(endpoint, binary=False):
        response = fakeGithubApi(endpoint, binary)
        if "/attempts/" in endpoint:
            response["triggering_actor"] = {"login": "rerun-actor"}
        if f"/collaborators/{actor}/" in endpoint:
            response = {"permission": "read"}
        return response

    with pytest.raises(rec.RecoveryError, match="maintainer authorization"):
        rec.verifyHandoff(approval, api=api, repository=REPOSITORY)


def test_bot_header_and_a_real_run_id_cannot_forge_approval_bytes(tmp_path):
    _, comments, approval = handoff(tmp_path)
    approval["topologyApprovedBy"] = "issue-author"
    # Even if an attacker finds a successful run, its actor and immutable bytes
    # cannot be rewritten by embedding a marker in a bot-authored comment.
    comments["comments"][-1] = botComment(approvalComment(json.dumps(approval)))
    with pytest.raises(rec.RecoveryError, match="authenticated successful intake workflow event"):
        rec.materialize(4242, comments, str(tmp_path / "promotion"), Fetcher())


@pytest.mark.parametrize("change", ["body", "batch", "record", "issue", "attempt"])
def test_immutable_artifact_must_match_exact_approval_pointer(tmp_path, change):
    _, _, approval = handoff(tmp_path)
    pointer = copy.deepcopy(approval)
    if change == "body":
        pointer["issueBodySha256"] = rec.sha256Hex("attacker revision")
    elif change == "batch":
        pointer["batchSha256"] = "f" * 64
    elif change == "record":
        pointer["recovery"]["recordDigest"] = "f" * 64
    elif change == "issue":
        pointer["issue"] = 9999
    else:
        pointer["workflowRunAttempt"] = 2
    with pytest.raises(rec.RecoveryError):
        rec.verifyHandoff(pointer)


@pytest.mark.parametrize("mutation", ["expired", "missing", "duplicate", "oversize"])
def test_artifacts_fail_closed_when_not_unique_available_and_bounded(tmp_path, mutation):
    _, _, approval = handoff(tmp_path)

    def api(endpoint, binary=False):
        response = fakeGithubApi(endpoint, binary)
        if endpoint.endswith("artifacts?per_page=100"):
            if mutation == "expired":
                response["artifacts"][0]["expired"] = True
            elif mutation == "missing":
                response["artifacts"] = []
            elif mutation == "duplicate":
                response["artifacts"] *= 2
            else:
                response["artifacts"][0]["size_in_bytes"] = rec.MAX_HANDOFF_BYTES + 1
        return response

    with pytest.raises(rec.RecoveryError):
        rec.verifyHandoff(approval, api=api)


def test_comment_only_legacy_recovery_requires_new_authenticated_approval(tmp_path):
    result, _ = run(richIssue(), tmp_path)
    payload = rec.buildApprovalPayload(rec.batchRelPath(BATCH_ID), 4242, "maintainer-one", str(tmp_path))
    comments = {"body": richIssue()["body"], "comments": [
        botComment(rec.recoveryComment(result)), botComment(approvalComment(payload))]}
    with pytest.raises(rec.RecoveryError, match="lacks verified workflow provenance"):
        rec.materialize(4242, comments, str(tmp_path), Fetcher())


@pytest.mark.parametrize("present", ["original", "reconstruction"])
def test_existing_batch_does_not_bypass_current_issue_revision(tmp_path, present):
    if present == "original":
        comments = normalApproval(tmp_path)
    else:
        result, comments, _ = handoff(tmp_path)
        rec.materialize(4242, comments, str(tmp_path), Fetcher())
    comments["body"] += "\nattacker edit after approval\n"
    with pytest.raises(rec.RecoveryError, match="body changed"):
        rec.materialize(4242, comments, str(tmp_path), Fetcher())


def test_existing_reconstruction_does_not_bypass_current_upstream_bytes(tmp_path):
    _, comments, _ = handoff(tmp_path)
    rec.materialize(4242, comments, str(tmp_path), Fetcher())
    moved = Fetcher({URL_ONE: b"changed upstream", URL_TWO: BYTES[URL_TWO]})
    with pytest.raises(rec.RecoveryError, match="upstream SKILL.md bytes changed"):
        rec.materialize(4242, comments, str(tmp_path), moved)


def test_reapproval_in_same_checkout_pins_current_issue_body_without_rewriting_receipt(tmp_path):
    issue = richIssue()
    first, _ = run(issue, tmp_path)
    before = snapshot(tmp_path)
    issue["body"] += "\nHarmless explanatory note\n"
    replay, _ = run(issue, tmp_path)
    assert replay["recordDigest"] == first["recordDigest"]
    assert snapshot(tmp_path) == before
    payload = json.loads(rec.buildApprovalPayload(rec.batchRelPath(BATCH_ID), 4242, "maintainer-one", str(tmp_path),
        issueBody=issue["body"], runId=1001, runAttempt=2, headSha="a" * 40))
    registerHandoff(payload, {"batch": first["batch"], "receipt": first["receipt"]})
    comments = {"body": issue["body"], "comments": [botComment(approvalComment(json.dumps(payload)))]}
    assert rec.materialize(4242, comments, str(tmp_path), Fetcher())["status"] == "recovery-already-present"
    assert payload["issueBodySha256"] != first["receipt"]["issueBodySha256"]


def test_duplicate_markers_are_rejected_even_with_one_valid_pointer(tmp_path):
    _, comments, _ = handoff(tmp_path)
    comments["comments"][-1]["body"] += "\n<!-- gaia-intake-approval {} -->"
    with pytest.raises(rec.RecoveryError, match="Ambiguous topology approval"):
        rec.materialize(4242, comments, str(tmp_path), Fetcher())


def test_workflow_publishes_pointer_only_after_immutable_upload():
    names = [step.get("name") or step.get("uses") for step in stepsOf("topology-approved")]
    assert names.index("Save the immutable topology handoff") < names.index("Publish the topology handoff pointer")
    upload = stepNamed("topology-approved", "Save the immutable topology handoff")
    assert upload["uses"] == "actions/upload-artifact@v4"
    assert "github.run_attempt" in upload["with"]["name"]
    assert upload["with"]["if-no-files-found"] == "error"


@pytest.mark.parametrize("job", ["topology-approved", "evidence-approved"])
@pytest.mark.parametrize("input_name", ["ISSUE_NUMBER_INPUT", "BASE_REF_INPUT"])
def test_workflow_resolve_executes_injected_shell_input_as_data(tmp_path, job, input_name):
    import os
    import subprocess

    step = stepNamed(job, "Resolve and validate issue")
    script = step["run"]
    replacements = {"github.event_name": "workflow_dispatch", "github.actor": "maintainer-one",
                    "github.event.issue.number": "4242", "github.event.sender.login": "maintainer-one"}
    for key, value in replacements.items():
        script = script.replace("${{ " + key + " }}", value)
    stub = tmp_path / "gh"
    stub.write_text("#!/bin/bash\nexit 0\n")
    stub.chmod(0o755)
    marker = tmp_path / "injected"
    payload = f'dev/$(touch "{marker}");`touch "{marker}"`'
    env = dict(os.environ, ISSUE_NUMBER_INPUT="4242", BASE_REF_INPUT="main", GITHUB_REPOSITORY=REPOSITORY,
               GITHUB_OUTPUT=str(tmp_path / "output"), PATH=f"{tmp_path}:{os.environ['PATH']}")
    env[input_name] = payload
    result = subprocess.run(["bash", "-e", "-c", script], env=env, capture_output=True, text=True)
    assert not marker.exists(), result.stdout + result.stderr
    if input_name == "ISSUE_NUMBER_INPUT":
        assert result.returncode != 0


def test_existing_reconstructed_batch_still_carries_missing_sidecar(tmp_path):
    result, comments, _ = handoff(tmp_path)
    path = tmp_path / rec.batchRelPath(BATCH_ID)
    path.parent.mkdir(parents=True)
    path.write_text(json.dumps(result["batch"]))
    outcome = rec.materialize(4242, comments, str(tmp_path), Fetcher())
    assert outcome == {"status": "recovery-already-present", "files": [rec.receiptRelPath(4242)]}
    assert json.loads((tmp_path / rec.receiptRelPath(4242)).read_text()) == result["receipt"]


def test_existing_conflicting_recovery_sidecar_cannot_be_preserved_silently(tmp_path):
    _, comments, _ = handoff(tmp_path)
    rec.materialize(4242, comments, str(tmp_path), Fetcher())
    receipt = tmp_path / rec.receiptRelPath(4242)
    tampered = json.loads(receipt.read_text())
    tampered["authorization"]["recoveredBy"] = "invented-approver"
    receipt.write_text(json.dumps(tampered))
    with pytest.raises(rec.RecoveryError, match="receipt conflicts"):
        rec.materialize(4242, comments, str(tmp_path), Fetcher())
    assert json.loads(receipt.read_text()) == tampered


@pytest.mark.parametrize("transition", ["topology", "evidence"])
def test_issue_cannot_change_between_maintainer_label_event_and_workflow_fetch(transition):
    issue = richIssue()
    event = {"action": "labeled", "label": {"name": f"intake:{transition}-approved"}, "issue": copy.deepcopy(issue)}
    rec.verifyIssueRevision(issue, "issues", event, transition)
    issue["body"] += "\nInjected after the human approval event\n"
    with pytest.raises(rec.RecoveryError, match="authenticated approval event"):
        rec.verifyIssueRevision(issue, "issues", event, transition)


@pytest.mark.parametrize("change", ["action", "number", "label", "event"])
def test_issue_revision_check_requires_correct_authenticated_event(change):
    issue = richIssue()
    event = {"action": "labeled", "label": {"name": "intake:topology-approved"}, "issue": copy.deepcopy(issue)}
    eventName = "issues"
    if change == "action":
        event["action"] = "edited"
    elif change == "number":
        event["issue"]["number"] = 9999
    elif change == "label":
        event["label"]["name"] = "intake:evidence-approved"
    else:
        eventName = "issue_comment"
    with pytest.raises(rec.RecoveryError):
        rec.verifyIssueRevision(issue, eventName, event, "topology")


@pytest.mark.parametrize("digest", [None, "", "f" * 63, "f" * 65, "F" * 64, "../attacker"])
def test_dispatch_requires_exact_maintainer_selected_body_digest(digest):
    with pytest.raises(rec.RecoveryError, match="Dispatch requires issue_body_sha256"):
        rec.verifyIssueRevision(richIssue(), "workflow_dispatch", {}, "topology", digest)


def test_dispatch_body_hash_is_exact_utf8_and_pinned_before_queued_execution():
    issue = richIssue()
    issue["body"] += "\nUnicode note: ✨\n\n"
    digest = rec.sha256Hex(issue["body"])
    rec.verifyIssueRevision(issue, "workflow_dispatch", {}, "topology", digest)
    issue["body"] = issue["body"].rstrip("\n")
    with pytest.raises(rec.RecoveryError, match="revision selected for dispatch"):
        rec.verifyIssueRevision(issue, "workflow_dispatch", {}, "topology", digest)


def test_restoring_old_issue_body_cannot_grant_approval_of_another_event_revision():
    issue = richIssue()
    eventIssue = copy.deepcopy(issue)
    eventIssue["body"] += "\nThe maintainer labeled this different revision\n"
    event = {"action": "labeled", "label": {"name": "intake:topology-approved"}, "issue": eventIssue}
    with pytest.raises(rec.RecoveryError, match="authenticated approval event"):
        rec.verifyIssueRevision(issue, "issues", event, "topology")


def test_dispatch_digest_stays_in_environment_and_revision_checks_precede_work():
    inputs = workflow()[True]["workflow_dispatch"]["inputs"]
    assert inputs["issue_body_sha256"]["required"] is True
    for job, name in [("topology-approved", "Validate the intake batch"),
                      ("evidence-approved", "Create or reuse the batch promotion PR")]:
        step = stepNamed(job, name)
        assert step["env"]["ISSUE_BODY_SHA256"] == "${{ inputs.issue_body_sha256 }}"
        assert "${{ inputs.issue_body_sha256 }}" not in step["run"]
        assert step["run"].index(" check-revision ") < step["run"].index(" payload " if job == "topology-approved" else " materialize ")


@pytest.mark.parametrize("contributor", ["ExampleSubmitter", "Hikari9", "HIKARI9"])
def test_recovery_never_normalizes_mixed_case_named_contributor(tmp_path, contributor):
    skill = richSkill("sample-skill", "Sample Skill", URL_ONE)
    skill["named"]["contributor"] = contributor
    fetcher = Fetcher()
    with pytest.raises(rec.RecoveryError) as raised:
        run(issueOf([skill], True), tmp_path, fetcher=fetcher)
    assert f"expected '{contributor.lower()}'" in "\n".join(raised.value.lines)
    assert "never normalizes identities silently" in "\n".join(raised.value.lines)
    assert fetcher.calls == [] and noFiles(tmp_path)


@pytest.mark.parametrize("value", ["hikari9", "user_name", "user-name", "99", "Hikari9", "bad/name", " spaced ", "", None])
def test_recovery_contributor_contract_matches_shared_identity_validation_when_integrated(value):
    shared = pytest.importorskip("gaia_cli.namedIdentity")
    assert rec.validateContributor(value) == shared.validateContributor(value)


def test_existing_batch_cannot_mint_a_mixed_case_identity_handoff(tmp_path):
    path = tmp_path / rec.batchRelPath(BATCH_ID)
    path.parent.mkdir(parents=True)
    skill = richSkill("sample-skill", "Sample Skill", URL_ONE)
    skill["named"]["contributor"] = "Hikari9"
    path.write_text(json.dumps(batchOf([skill], True)))
    with pytest.raises(rec.RecoveryError, match="expected 'hikari9'"):
        rec.buildApprovalPayload(rec.batchRelPath(BATCH_ID), 4242, "maintainer-one", str(tmp_path))


def test_previously_minted_recovery_artifact_cannot_materialize_mixed_case_identity(tmp_path):
    result, comments, approval = handoff(tmp_path)
    result["batch"]["proposedSkills"][0]["named"]["contributor"] = "Hikari9"
    result["receipt"]["reconstructedBatch"]["sha256"] = rec.sha256Hex(rec.canonicalJson(result["batch"]))
    approval["recovery"]["recordDigest"] = rec.recordIdentityDigest(result["batch"], result["receipt"])
    approval["recovery"]["batchSha256"] = result["receipt"]["reconstructedBatch"]["sha256"]
    approval["batchSha256"] = approval["recovery"]["batchSha256"]
    registerHandoff(approval, {"batch": result["batch"], "receipt": result["receipt"]})
    comments["comments"][-1] = botComment(approvalComment(json.dumps(approval)))
    branch = tmp_path / "promotion"
    with pytest.raises(rec.RecoveryError, match="expected 'hikari9'"):
        rec.materialize(4242, comments, str(branch), Fetcher())
    assert noFiles(branch)
