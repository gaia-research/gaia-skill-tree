"""Per-finding credential disposition consumer (#2283): exact match decides, all else stays C.

Fake credentials are assembled at runtime by the helpers imported from the
sensor tests, so this file contains no credential literal.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from gaia_cli.steward import credentialDispositions as records
from gaia_cli.steward.debt import reconcile_debt
from gaia_cli.steward.policy import StewardPolicy
from gaia_cli.steward.sensors_security import SecretScanSensor, _SECRET_PATTERNS
from scripts import steward_credential_disposition as helper
from tests.steward.sensor_fixtures import commit_all, make_repo, write_files
from tests.steward.test_sensors_security import _aws_key, _github_token

NOW = "2026-11-07T00:00:00Z"
SOURCE = "src/fixture.py"
ROOT = Path(__file__).resolve().parents[2]


def _decision(identifier: str, status: str = "decided", **overrides) -> str:
    """A decision record the desk's own validator accepts (unless overridden)."""

    body = {
        "schemaVersion": "steward-decision-v1",
        "id": identifier,
        "status": status,
        "decision": "Fixture decision?",
        "whyItMatters": "Fixture record.",
        "evidence": ["fixture"],
        "recommended": "fixture",
        "alternative": "fixture",
        "unblocks": "fixture",
        "links": ["https://example.invalid/fixture"],
    }
    body.update(overrides)
    return json.dumps(body)


def _decisions() -> dict[str, str]:
    files = {f"{records.DECISIONSDIR}/{records.RULINGID}.json": _decision(records.RULINGID)}
    for identifier in records.POLICYDECISIONS.values():
        files[f"{records.DECISIONSDIR}/{identifier}.json"] = _decision(identifier)
    return files


def _repo(tmp_path: Path, source: str) -> Path:
    return make_repo(tmp_path / "repo", {SOURCE: source, **_decisions()})


def _live(root: Path):
    (observation,) = [item for item in SecretScanSensor().scan(root, NOW) if item.subject.id == SOURCE]
    return observation


def _record(root: Path, finding: dict, liveDebt: str, **overrides) -> dict:
    body = {
        "schemaVersion": records.RECORDSCHEMA,
        "debtId": liveDebt,
        "path": SOURCE,
        "line": finding["line"],
        "pattern": finding["pattern"],
        "fingerprint": finding["fingerprint"],
        "fileSha256": records.fileSha256((root / SOURCE).read_bytes()),
        "policy": "D2",
        "disposition": "synthetic-fixture",
        "evidence": "Runtime-assembled positive-test value, never issued by any provider.",
        "author": "author-agent",
        "verifiedBy": "verifier-agent",
        "verifiedAt": "2026-11-07T01:00:00Z",
        "founderRuling": records.RULINGID,
    }
    body.update(overrides)
    return body


def _put(root: Path, body: dict, name: str | None = None) -> None:
    default = records.recordName(body["debtId"], body["line"], body["fingerprint"], body.get("occurrence", 0))
    rel = f"{records.RECORDDIR}/{name or default}"
    write_files(root, {rel: json.dumps(body)})
    commit_all(root)


def _decide(root: Path, **overrides) -> None:
    drift = _live(root)
    for finding in drift.observed_state["findings"]:
        _put(root, _record(root, finding, drift.debt_id, **overrides))


class TestExactMatch:
    def test_exact_match_marks_the_debt_decided_with_provenance(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        before = _live(root)
        assert before.status == "drift"
        _decide(root)
        after = _live(root)
        assert after.status == "healthy"
        assert after.debt_id == before.debt_id
        state = after.observed_state
        assert state["decidedDisposition"] is True
        assert state["decisionRecord"].endswith(f"{records.RULINGID}.json")
        (entry,) = state["dispositions"]
        assert (entry["policy"], entry["verifiedBy"], entry["fingerprint"]) == (
            "D2", "verifier-agent", before.observed_state["findings"][0]["fingerprint"],
        )
        assert entry["record"].startswith(records.RECORDDIR)
        assert _github_token() not in json.dumps(after.to_dict())

    def test_open_debt_resolves_as_decided_disposition_and_history_is_kept(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        policy = StewardPolicy.load(ROOT)
        opened = reconcile_debt([_live(root)], {}, policy)
        (debt,) = opened.debts
        assert debt.status == "open"
        _decide(root)
        closed = reconcile_debt([_live(root)], {debt.id: debt}, policy)
        (marked,) = closed.debts
        assert (marked.status, marked.resolution) == ("resolved", "decided_disposition")
        assert marked.first_observed_at == debt.first_observed_at
        assert marked.observation_count == debt.observation_count + 1
        assert marked.observed_state["dispositions"][0]["verifiedBy"] == "verifier-agent"
        # The findings the debt was opened with survive resolution, verbatim.
        assert marked.observed_state["priorObservedState"] == dict(debt.observed_state)
        assert marked.observed_state["priorObservedState"]["findings"]
        # A later run that still sees the decided state keeps the preserved evidence.
        again = reconcile_debt([_live(root)], {marked.id: marked}, policy)
        assert again.debts[0].observed_state["priorObservedState"] == dict(debt.observed_state)

    def test_changed_file_reopens_as_drift(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root)
        assert _live(root).status == "healthy"
        # One extra byte; the finding itself is untouched.
        with (root / SOURCE).open("a", encoding="utf-8") as handle:
            handle.write("\n")
        commit_all(root)
        assert _live(root).status == "drift"

    def test_untracked_record_decides_nothing(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        drift = _live(root)
        body = _record(root, drift.observed_state["findings"][0], drift.debt_id)
        target = root / records.RECORDDIR / records.recordName(drift.debt_id, body["line"], body["fingerprint"])
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(body), encoding="utf-8")
        assert _live(root).status == "drift"


class TestFailClosed:
    @pytest.mark.parametrize(
        "override",
        [
            {"fingerprint": "0" * 12},
            {"fileSha256": "0" * 64},
            {"pattern": "aws-access-key-id"},
            {"line": 99},
            {"path": "src/other.py"},
            {"debtId": "debt:credential_leak:src-fixture-py:0000000000000000"},
            {"verifiedBy": ""},
            {"verifiedBy": "Author-Agent "},
            {"author": "verifier-agent"},
            {"policy": "D4"},
            {"policy": ""},
            {"disposition": "ignore"},
            {"evidence": ""},
            {"evidence": "ok"},
            {"founderRuling": "something-else"},
            {"schemaVersion": "v0"},
            {"verifiedAt": "yesterday"},
        ],
    )
    def test_any_mismatch_or_invalid_field_stays_class_c(self, tmp_path: Path, override: dict) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root, **override)
        assert _live(root).status == "drift"

    def test_missing_verifier_field_stays_class_c(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        drift = _live(root)
        body = _record(root, drift.observed_state["findings"][0], drift.debt_id)
        del body["verifiedBy"]
        _put(root, body)
        assert _live(root).status == "drift"

    def test_unrelated_finding_in_the_same_file_keeps_the_file_class_c(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"a = '{_github_token('one')}'\nb = '{_aws_key('two')}'\n")
        drift = _live(root)
        first = drift.observed_state["findings"][0]
        _put(root, _record(root, first, drift.debt_id))
        after = _live(root)
        assert after.status == "drift"
        assert after.observed_state["findingCount"] == 2
        assert after.observed_state["undecidedFindingCount"] == 1
        assert [item["fingerprint"] for item in after.observed_state["decidedFindings"]] == [first["fingerprint"]]

    def test_a_record_for_another_file_does_not_decide_this_one(self, tmp_path: Path) -> None:
        token = _github_token()
        root = make_repo(
            tmp_path / "repo",
            {SOURCE: f"k = '{token}'\n", "src/twin.py": f"k = '{token}'\n", **_decisions()},
        )
        observations = {item.subject.id: item for item in SecretScanSensor().scan(root, NOW)}
        twin = observations["src/twin.py"]
        finding = twin.observed_state["findings"][0]
        sha = records.fileSha256((root / "src/twin.py").read_bytes())
        _put(root, _record(root, finding, twin.debt_id, path="src/twin.py", fileSha256=sha))
        after = {item.subject.id: item.status for item in SecretScanSensor().scan(root, NOW)}
        assert after == {SOURCE: "drift", "src/twin.py": "healthy"}

    def test_two_claimants_for_one_finding_are_ambiguous(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        drift = _live(root)
        body = _record(root, drift.observed_state["findings"][0], drift.debt_id)
        _put(root, body, "first.json")
        _put(root, {**body, "verifiedBy": "other-verifier"}, "second.json")
        assert _live(root).status == "drift"

    @pytest.mark.parametrize(
        "invalid",
        [
            {"verifiedBy": ""},
            {"author": "verifier-agent"},
            {"policy": "D9"},
            {"evidence": "thin"},
            {"occurrence": "later"},
            {"founderRuling": "something-else"},
        ],
    )
    def test_an_invalid_second_claimant_still_keeps_the_finding_class_c(self, tmp_path: Path, invalid: dict) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        drift = _live(root)
        body = _record(root, drift.observed_state["findings"][0], drift.debt_id)
        _put(root, body, "valid.json")
        assert _live(root).status == "healthy"
        _put(root, {**body, **invalid}, "invalid-claimant.json")
        after = _live(root)
        assert after.status == "drift"
        assert after.provenance["rejectedDispositionRecords"] == 1

    def test_an_unusable_record_naming_another_occurrence_does_not_block_this_one(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        drift = _live(root)
        body = _record(root, drift.observed_state["findings"][0], drift.debt_id)
        _put(root, body, "valid.json")
        _put(root, {**body, "occurrence": 5, "verifiedBy": ""}, "other-occurrence.json")
        assert _live(root).status == "healthy"

    def test_one_record_cannot_resolve_two_same_line_occurrences(self, tmp_path: Path) -> None:
        # The reviewer's probe: one token twice on one line shares line, pattern and fingerprint.
        token = _github_token()
        root = _repo(tmp_path, f"a = '{token}'; b = '{token}'\n")
        drift = _live(root)
        first, second = drift.observed_state["findings"]
        assert first == second
        _put(root, _record(root, first, drift.debt_id))
        one = _live(root)
        assert one.status == "drift"
        assert one.observed_state["findingCount"] == 2
        assert one.observed_state["undecidedFindingCount"] == 1
        assert [item["occurrence"] for item in one.observed_state["decidedFindings"]] == [0]

    def test_each_same_line_occurrence_needs_its_own_record(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, f"a = '{token}'; b = '{token}'\n")
        drift = _live(root)
        finding = drift.observed_state["findings"][0]
        _put(root, _record(root, finding, drift.debt_id, occurrence=0))
        _put(root, _record(root, finding, drift.debt_id, occurrence=1))
        done = _live(root)
        assert done.status == "healthy"
        assert [item["occurrence"] for item in done.observed_state["dispositions"]] == [0, 1]
        assert len({item["record"] for item in done.observed_state["dispositions"]}) == 2

    def test_a_record_for_a_missing_occurrence_decides_nothing(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        drift = _live(root)
        _put(root, _record(root, drift.observed_state["findings"][0], drift.debt_id, occurrence=1))
        assert _live(root).status == "drift"

    def test_ruling_record_the_desk_rejects_does_not_authorise_dispositions(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        # id and status say decided, but the desk validator rejects the list-valued unblocks.
        write_files(root, {f"{records.DECISIONSDIR}/{records.RULINGID}.json": _decision(records.RULINGID, unblocks=["x"])})
        commit_all(root)
        _decide(root)
        assert _live(root).status == "drift"

    def test_policy_record_the_desk_rejects_does_not_authorise_dispositions(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        policy = records.POLICYDECISIONS["D2"]
        write_files(root, {f"{records.DECISIONSDIR}/{policy}.json": json.dumps({"id": policy, "status": "decided"})})
        commit_all(root)
        _decide(root)
        assert _live(root).status == "drift"

    def test_ruling_record_whose_id_does_not_match_its_file_is_rejected(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        write_files(root, {f"{records.DECISIONSDIR}/{records.RULINGID}.json": _decision("another-id")})
        commit_all(root)
        _decide(root)
        assert _live(root).status == "drift"

    @pytest.mark.parametrize("missing", [records.RULINGID, *records.POLICYDECISIONS.values()])
    def test_undecided_ruling_or_policy_record_stays_class_c(self, tmp_path: Path, missing: str) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        write_files(root, {f"{records.DECISIONSDIR}/{missing}.json": _decision(missing, "open")})
        commit_all(root)
        policy = next((name for name, identifier in records.POLICYDECISIONS.items() if identifier == missing), "D2")
        _decide(root, policy=policy)
        assert _live(root).status == "drift"

    def test_malformed_record_is_ignored_and_counted(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        write_files(root, {f"{records.RECORDDIR}/bad.json": "{not json"})
        commit_all(root)
        item = _live(root)
        assert item.status == "drift"
        assert item.provenance["rejectedDispositionRecords"] == 1

    def test_no_records_leaves_observations_unchanged(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        item = _live(root)
        assert "rejectedDispositionRecords" not in item.provenance
        assert "decidedFindings" not in item.observed_state


class TestSchemaAndHelper:
    def test_schema_file_agrees_with_the_validator(self, tmp_path: Path) -> None:
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads((ROOT / "founder/steward/credential-disposition.schema.json").read_text(encoding="utf-8"))
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        drift = _live(root)
        good = _record(root, drift.observed_state["findings"][0], drift.debt_id)
        jsonschema.validate(good, schema)
        assert records.validateRecord(good) is None
        for bad in ({**good, "policy": "D9"}, {**good, "fingerprint": "xyz"}, {**good, "evidence": ""}):
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate(bad, schema)
            assert records.validateRecord(bad) is not None

    def test_draft_prefills_identity_and_never_sets_the_verifier(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"a = '{_github_token('one')}'\nb = '{_aws_key('two')}'\n")
        drift = _live(root)
        drafts = helper.draftRecords(root, drift.debt_id)
        assert [item["fingerprint"] for item in drafts] == [f["fingerprint"] for f in drift.observed_state["findings"]]
        for item in drafts:
            assert item["fileSha256"] == records.fileSha256((root / SOURCE).read_bytes())
            assert item["debtId"] == drift.debt_id and item["path"] == SOURCE
            assert item["verifiedBy"] == "" and item["author"] == ""
            assert item["policy"] == "" and item["disposition"] == "" and item["evidence"] == ""
            assert records.validateRecord(item) is not None  # inert until a human completes it

    def test_draft_numbers_same_line_occurrences(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, f"a = '{token}'; b = '{token}'\n")
        drafts = helper.draftRecords(root, _live(root).debt_id)
        assert [item["occurrence"] for item in drafts] == [0, 1]

    def test_draft_unknown_debt_fails(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        with pytest.raises(LookupError):
            helper.draftRecords(root, "debt:credential_leak:nope:0000000000000000")

    def test_draft_write_creates_files_and_refuses_overwrite(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debtId = _live(root).debt_id
        assert helper.main(["draft", debtId, "--root", str(root), "--write"]) == 0
        (written,) = list((root / records.RECORDDIR).glob("*.json"))
        assert json.loads(written.read_text(encoding="utf-8"))["verifiedBy"] == ""
        assert helper.main(["draft", debtId, "--root", str(root), "--write"]) == 1

    def test_this_test_module_contains_no_credential_literal(self) -> None:
        text = Path(__file__).read_text(encoding="utf-8")
        assert not [name for name, pattern in _SECRET_PATTERNS if pattern.search(text)]
