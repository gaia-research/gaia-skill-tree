"""Per-finding credential dispositions (#2283): exact match decides, evidence routes.

Fake credentials are assembled at runtime so this file contains no credential
literal (the secret scan covers this repository, including this file).
"""

from __future__ import annotations

import base64
import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

import pytest

from gaia_cli.steward import credentialDispositions as records
from gaia_cli.steward.controller import StewardController
from gaia_cli.steward.debt import reconcile_debt
from gaia_cli.steward.models import AuthorityClass, DispatchPacket, Observation, RoutingBudget, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, PolicyError, StewardPolicy
from gaia_cli.steward.routing import RoutingError, render_dispatch
from gaia_cli.steward.sensors_security import (
    SecretScanSensor,
    _SECRET_PATTERNS,
    _SecretTally,
    _entropy,
    credentialClass,
)
from gaia_cli.steward.verification import evaluate, parse_proof_transcript, parse_unified_diff
from scripts import steward_credential_disposition as helper
from tests.steward.sensor_fixtures import commit_all, make_repo, write_files
from tests.steward.test_sensors_security import _aws_key, _github_token, _private_key_header, _seeded

NOW = "2026-11-07T00:00:00Z"
SOURCE = "src/fixture.py"
ROOT = Path(__file__).resolve().parents[2]
RULE = "credential-review-disposition"


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


def _repo(tmp_path: Path, source: str, **more: str) -> Path:
    return make_repo(tmp_path / "repo", {SOURCE: source, **_decisions(), **more})


def _assign(value: str) -> str:
    # Assembled so this module never contains a keyword-assignment literal.
    return "to" + "ken = " + value + "\n"


def _reference() -> str:
    return _assign("$" + "{GITHUB" + "_REF}")


def _opaque() -> str:
    return base64.b64encode(hashlib.sha256(b"opaque-fixture").digest()).decode().rstrip("=")[:32]


def _b64(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).decode().rstrip("=")


def _jwt(valid: bool = True) -> str:
    if not valid:
        return "eyJ" + "x" * 10 + "." + "y" * 10 + "." + "z" * 10
    return ".".join(
        (
            _b64(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()),
            _b64(json.dumps({"sub": "fixture"}).encode()),
            _b64(hashlib.sha256(b"sig").digest()),
        )
    )


def _live(root: Path, rel: str = SOURCE, kind: str = "credential_leak"):
    (observation,) = [item for item in SecretScanSensor().scan(root, NOW) if item.subject.id == rel and item.kind == kind]
    return observation


def _kinds(root: Path, rel: str = SOURCE) -> dict[str, str]:
    return {item.kind: item.status for item in SecretScanSensor().scan(root, NOW) if item.subject.id == rel}


def _targets(root: Path, rel: str = SOURCE):
    text = (root / rel).read_text(encoding="utf-8")
    located = SecretScanSensor._locate(rel, text, _SecretTally())
    return list(zip(located, records.occurrences([item.finding for item in located])))


def _record(item, index: int, liveDebt: str, rel: str = SOURCE, **overrides) -> dict:
    body = {
        "schemaVersion": records.RECORDSCHEMA,
        "debtId": liveDebt,
        "path": rel,
        "line": item.finding["line"],
        "pattern": item.finding["pattern"],
        "fingerprint": item.finding["fingerprint"],
        "occurrence": index,
        "lineSha256": item.lineHash,
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
    default = records.recordName(body["debtId"], body["fingerprint"], body["occurrence"])
    write_files(root, {f"{records.RECORDDIR}/{name or default}": json.dumps(body)})
    commit_all(root)


def _decide(root: Path, rel: str = SOURCE, **overrides) -> None:
    debt = _live(root, rel).debt_id
    for item, occurrence in _targets(root, rel):
        _put(root, _record(item, occurrence, debt, rel, **overrides))


def _edit(root: Path, rel: str, transform) -> None:
    path = root / rel
    path.write_text(transform(path.read_text(encoding="utf-8")), encoding="utf-8")
    commit_all(root)


class TestFindingLevelBinding:
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
        assert (entry["policy"], entry["verifiedBy"], entry["fingerprint"], entry["occurrence"]) == (
            "D2", "verifier-agent", before.observed_state["findings"][0]["fingerprint"], 0,
        )
        assert entry["record"].startswith(records.RECORDDIR)
        assert _github_token() not in json.dumps(after.to_dict())

    def test_unrelated_edits_elsewhere_keep_the_finding_decided(self, tmp_path: Path) -> None:
        # (a) a firecrawl/impeccable style churn: lines added above and below, the token line untouched.
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root)
        assert _kinds(root)["credential_leak"] == "healthy"
        _edit(root, SOURCE, lambda text: "# new header\nimport os\n\n" + text + "def later():\n    return 1\n")
        item = _live(root)
        assert item.status == "healthy"
        assert item.observed_state["dispositions"][0]["line"] == 4  # live line moved; identity did not

    def test_reindenting_or_crlf_on_the_token_line_keeps_it_decided(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root)
        _edit(root, SOURCE, lambda text: "    " + text.replace("\n", "\r\n"))
        assert _live(root).status == "healthy"

    def test_changed_token_reopens_the_finding(self, tmp_path: Path) -> None:
        # (b) a different token on the same line is a different finding with no record.
        root = _repo(tmp_path, f"k = '{_github_token('one')}'\n")
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace(_github_token("one"), _github_token("two")))
        item = _live(root)
        assert item.status == "drift"
        assert "decidedFindings" not in item.observed_state

    def test_changed_line_around_the_same_token_reopens_the_finding(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace("k = ", "renamed = "))
        assert _live(root).status == "drift"

    def test_second_identical_token_added_stays_undecided(self, tmp_path: Path) -> None:
        # (c) the reviewed token stays decided; the new copy has no record.
        token = _github_token()
        root = _repo(tmp_path, f"k = '{token}'\n")
        _decide(root)
        _edit(root, SOURCE, lambda text: text + f"copy = '{token}'\n")
        item = _live(root)
        assert item.status == "drift"
        assert item.observed_state["findingCount"] == 2
        assert item.observed_state["undecidedFindingCount"] == 1
        assert [entry["occurrence"] for entry in item.observed_state["decidedFindings"]] == [0]

    def test_second_identical_token_added_above_does_not_inherit_the_review(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, f"k = '{token}'\n")
        _decide(root)
        _edit(root, SOURCE, lambda text: f"copy = '{token}'\n" + text)
        assert _live(root).status == "drift"

    def test_informational_line_number_is_not_matched(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, occurrence), = _targets(root)
        _put(root, _record(item, occurrence, debt, line=999))
        assert _live(root).status == "healthy"

    def test_open_debt_resolves_as_decided_disposition_and_history_is_kept(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        policy = StewardPolicy.load(ROOT)
        opened = reconcile_debt([_live(root)], {}, policy)
        (debt,) = opened.debts
        assert debt.status == "open"
        _decide(root)
        healthy = [item for item in SecretScanSensor().scan(root, NOW) if item.subject.id == SOURCE]
        closed = reconcile_debt(healthy, {debt.id: debt}, policy)
        (marked,) = [item for item in closed.debts if item.kind == "credential_leak"]
        assert (marked.status, marked.resolution) == ("resolved", "decided_disposition")
        assert marked.first_observed_at == debt.first_observed_at
        assert marked.observation_count == debt.observation_count + 1
        assert marked.observed_state["dispositions"][0]["verifiedBy"] == "verifier-agent"
        # The findings the debt was opened with survive resolution, verbatim.
        assert marked.observed_state["priorObservedState"] == dict(debt.observed_state)
        assert marked.observed_state["priorObservedState"]["findings"]
        # A later run that still sees the decided state keeps the preserved evidence.
        again = reconcile_debt(healthy, {marked.id: marked}, policy)
        assert [item for item in again.debts if item.id == marked.id][0].observed_state[
            "priorObservedState"
        ] == dict(debt.observed_state)

    def test_untracked_record_decides_nothing(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, occurrence), = _targets(root)
        body = _record(item, occurrence, debt)
        target = root / records.RECORDDIR / records.recordName(debt, body["fingerprint"], occurrence)
        target.parent.mkdir(parents=True)
        target.write_text(json.dumps(body), encoding="utf-8")
        assert _live(root).status == "drift"


class TestFailClosed:
    @pytest.mark.parametrize(
        "override",
        [
            {"fingerprint": "0" * 12},
            {"lineSha256": "0" * 64},
            {"pattern": "aws-access-key-id"},
            {"occurrence": 1},
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
            {"schemaVersion": "steward-credential-disposition-v1"},
            {"verifiedAt": "yesterday"},
        ],
    )
    def test_any_mismatch_or_invalid_field_stays_open(self, tmp_path: Path, override: dict) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root, **override)
        assert _live(root).status == "drift"

    def test_whole_file_binding_is_gone(self, tmp_path: Path) -> None:
        # A v2 record carrying the retired v1 field is still judged on lineSha256 alone.
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, occurrence), = _targets(root)
        _put(root, _record(item, occurrence, debt, fileSha256="0" * 64))
        assert _live(root).status == "healthy"

    def test_missing_verifier_field_stays_open(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, occurrence), = _targets(root)
        body = _record(item, occurrence, debt)
        del body["verifiedBy"]
        _put(root, body)
        assert _live(root).status == "drift"

    def test_unrelated_finding_in_the_same_file_keeps_the_file_open(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"a = '{_github_token('one')}'\nb = '{_aws_key('two')}'\n")
        debt = _live(root).debt_id
        (first, occurrence), _second = _targets(root)
        _put(root, _record(first, occurrence, debt))
        after = _live(root)
        assert after.status == "drift"
        assert after.observed_state["findingCount"] == 2
        assert after.observed_state["undecidedFindingCount"] == 1
        assert [item["fingerprint"] for item in after.observed_state["decidedFindings"]] == [
            first.finding["fingerprint"]
        ]

    def test_a_record_for_another_file_does_not_decide_this_one(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, f"k = '{token}'\n", **{"src/twin.py": f"k = '{token}'\n"})
        twin = _live(root, "src/twin.py")
        (item, occurrence), = _targets(root, "src/twin.py")
        _put(root, _record(item, occurrence, twin.debt_id, "src/twin.py"))
        after = {obs.subject.id: obs.status for obs in SecretScanSensor().scan(root, NOW) if obs.kind == "credential_leak"}
        assert after == {SOURCE: "drift", "src/twin.py": "healthy"}

    def test_two_claimants_for_one_finding_are_ambiguous(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, occurrence), = _targets(root)
        body = _record(item, occurrence, debt)
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
    def test_an_invalid_second_claimant_still_keeps_the_finding_open(self, tmp_path: Path, invalid: dict) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, occurrence), = _targets(root)
        body = _record(item, occurrence, debt)
        _put(root, body, "valid.json")
        assert _live(root).status == "healthy"
        _put(root, {**body, **invalid}, "invalid-claimant.json")
        after = _live(root)
        assert after.status == "drift"
        assert after.provenance["rejectedDispositionRecords"] == 1

    def test_an_unusable_record_naming_another_occurrence_does_not_block_this_one(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, occurrence), = _targets(root)
        body = _record(item, occurrence, debt)
        _put(root, body, "valid.json")
        _put(root, {**body, "occurrence": 5, "verifiedBy": ""}, "other-occurrence.json")
        assert _live(root).status == "healthy"

    def test_one_record_cannot_resolve_two_same_line_occurrences(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, f"a = '{token}'; b = '{token}'\n")
        debt = _live(root).debt_id
        (first, occurrence), (second, _) = _targets(root)
        assert first.finding == second.finding
        _put(root, _record(first, occurrence, debt))
        one = _live(root)
        assert one.status == "drift"
        assert one.observed_state["findingCount"] == 2
        assert one.observed_state["undecidedFindingCount"] == 1
        assert [item["occurrence"] for item in one.observed_state["decidedFindings"]] == [0]

    def test_each_same_line_occurrence_needs_its_own_record(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, f"a = '{token}'; b = '{token}'\n")
        _decide(root)
        done = _live(root)
        assert done.status == "healthy"
        assert [item["occurrence"] for item in done.observed_state["dispositions"]] == [0, 1]
        assert len({item["record"] for item in done.observed_state["dispositions"]}) == 2

    def test_a_record_for_a_missing_occurrence_decides_nothing(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, _), = _targets(root)
        _put(root, _record(item, 1, debt))
        assert _live(root).status == "drift"

    def test_ruling_record_the_desk_rejects_does_not_authorise_dispositions(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
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
    def test_undecided_ruling_or_policy_record_stays_open(self, tmp_path: Path, missing: str) -> None:
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


class TestEvidenceRouting:
    """Class C only for live-shaped or ambiguous findings; the rest is Class B, by value not path."""

    def test_issuer_token_stays_class_c(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        assert _kinds(root) == {"credential_leak": "drift"}

    def test_reference_value_is_class_b_with_the_class_c_debt_retired_as_reclassified(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference())
        assert _kinds(root) == {"credential_review": "drift", "credential_leak": "healthy"}
        review = _live(root, kind="credential_review")
        assert review.observed_state["classification"] == {"review": 1}
        assert review.observed_state["reclassifiedFrom"] == _live(root).debt_id
        assert _live(root).observed_state["reclassifiedTo"] == "credential_review"

    def test_reclassification_keeps_history_and_opens_a_class_b_debt(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference())
        policy = StewardPolicy.load(ROOT)
        review = _live(root, kind="credential_review")
        old = Observation(
            kind="credential_leak", subject=review.subject, observed_at=NOW, source="secret-scan", status="drift",
            current_state={"credentialMatches": 0}, observed_state={"findingCount": 1, "findings": [{"line": 1}]},
            confidence=0.9,
        )
        (debt,) = reconcile_debt([old], {}, policy).debts
        assert debt.authority is AuthorityClass.C
        scan = [item for item in SecretScanSensor().scan(root, NOW) if item.subject.id == SOURCE]
        after = reconcile_debt(scan, {debt.id: debt}, policy)
        leak = next(item for item in after.debts if item.kind == "credential_leak")
        assert (leak.status, leak.resolution) == ("resolved", "reclassified")
        assert leak.observed_state["priorObservedState"] == dict(debt.observed_state)
        opened = next(item for item in after.debts if item.kind == "credential_review")
        assert (opened.status, opened.authority) == ("open", AuthorityClass.B)

    def test_decided_class_b_file_resolves_both_debts_with_provenance(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference())
        policy = StewardPolicy.load(ROOT)
        before = [item for item in SecretScanSensor().scan(root, NOW) if item.subject.id == SOURCE]
        seeded = reconcile_debt(before, {}, policy)
        review_debt = next(item for item in seeded.debts if item.kind == "credential_review")
        _decide(root)
        after = [item for item in SecretScanSensor().scan(root, NOW) if item.subject.id == SOURCE]
        assert {item.kind: item.status for item in after} == {"credential_leak": "healthy", "credential_review": "healthy"}
        closed = reconcile_debt(after, {review_debt.id: review_debt}, policy)
        (resolved,) = [item for item in closed.debts if item.id == review_debt.id]
        assert (resolved.status, resolved.resolution) == ("resolved", "decided_disposition")
        assert resolved.observed_state["priorObservedState"] == dict(review_debt.observed_state)

    def test_opaque_high_entropy_value_is_ambiguous_and_stays_class_c(self, tmp_path: Path) -> None:
        value = _opaque()
        assert len(value) >= 20 and _entropy(value) >= 4.0
        assert any(c.isdigit() for c in value) and any(c.isalpha() for c in value)
        root = _repo(tmp_path, _assign(f'"{value}"'))
        assert _kinds(root) == {"credential_leak": "drift"}

    def test_plain_word_value_is_class_b(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _assign('"plainvalue"'))
        assert _kinds(root)["credential_review"] == "drift"

    @pytest.mark.parametrize(
        "rel", ["src/a.py", "tests/steward/a.py", ".claude/skills/x/SKILL.md", ".agents/skills/x/SKILL.md", "docs/a.md"]
    )
    def test_the_same_value_routes_the_same_regardless_of_path(self, tmp_path: Path, rel: str) -> None:
        # No downgrading because a file is mirrored or under tests/: only the value counts.
        live = _repo(tmp_path / "live", f"k = '{_github_token()}'\n", **{rel: f"k = '{_github_token()}'\n"})
        assert _kinds(live, rel)["credential_leak"] == "drift" and "credential_review" not in _kinds(live, rel)
        quiet = _repo(tmp_path / "quiet", "x = 1\n", **{rel: _reference()})
        assert _kinds(quiet, rel) == {"credential_review": "drift", "credential_leak": "healthy"}

    def test_one_live_shaped_finding_keeps_the_whole_file_class_c(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference() + f"k = '{_aws_key()}'\n")
        assert _kinds(root) == {"credential_leak": "drift"}

    def test_class_c_findings_still_need_an_exact_record_even_when_decided_ones_are_b(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference() + _reference().replace("GITHUB", "OTHER"))
        debt = _live(root).debt_id
        (first, occurrence), _second = _targets(root)
        _put(root, _record(first, occurrence, debt))
        review = _live(root, kind="credential_review")
        assert review.observed_state["undecidedFindingCount"] == 1
        assert review.observed_state["classification"] == {"review": 1}

    @pytest.mark.parametrize(
        "valid, expected", [(True, "structured"), (False, "review")]
    )
    def test_jwt_is_live_shaped_only_with_a_valid_structure(self, valid: bool, expected: str) -> None:
        token = _jwt(valid)
        pattern = dict(_SECRET_PATTERNS)["jwt"]
        match = pattern.search(f"v = '{token}'")
        assert match is not None
        assert credentialClass("jwt", match.group(0), "", 0) == expected

    def test_private_key_header_is_c_with_or_without_a_body(self) -> None:
        header = _private_key_header()
        body = "\n".join(_seeded(f"key{n}", 64) for n in range(3))
        bare = f"v = '{header}'\n"
        full = f"v = '''{header}\n{body}\n'''\n"
        assert credentialClass("private-key-block", header, bare, bare.index(header) + len(header)) == "ambiguous"
        assert credentialClass("private-key-block", header, full, full.index(header) + len(header)) == "issuer"

    @pytest.mark.parametrize("name", ["credential-assignment", "bearer-token", "aws-secret-access-key"])
    def test_generic_patterns_are_never_issuer_classified(self, name: str) -> None:
        assert credentialClass(name, "x" * 5, "", 0) == "review"

    def test_unknown_pattern_is_never_assumed_benign(self) -> None:
        assert credentialClass("brand-new-pattern", "whatever", "", 0) == "ambiguous"


class TestPolicyAndEnvelope:
    def _policy(self) -> StewardPolicy:
        return StewardPolicy.load(ROOT)

    def test_credential_review_is_class_b_and_credential_leak_stays_class_c(self) -> None:
        policy = self._policy()
        assert policy.authority_for("credential_review") is AuthorityClass.B
        assert policy.authority_for("credential_leak") is AuthorityClass.C

    def test_dispatch_rule_lets_a_builder_write_only_disposition_records(self) -> None:
        rule = self._policy().dispatch_rules[RULE]
        assert rule.debt_kind == "credential_review" and rule.authority is AuthorityClass.B
        assert rule.allowed_paths == ("founder/steward/security-dispositions/**",)
        for forbidden in ("src/**", "tests/**", "scripts/**", ".github/**", "docs/**", "registry/**", "founder/**"):
            assert forbidden in rule.forbidden_paths
        assert any("verifiedBy" in item and "empty" in item for item in rule.proof)
        assert any("steward_credential_disposition.py draft" in item for item in rule.allowed_commands)

    def _packet(self) -> DispatchPacket:
        rule = self._policy().dispatch_rules[RULE]
        return DispatchPacket.create(
            debt={"id": "debt:x", "kind": "credential_review", "source": "secret-scan"},
            evidence={"debtId": "debt:x"},
            authority=AuthorityClass.B,
            rule=RULE,
            routine=rule.routine,
            objective=rule.objective,
            allowed_paths=rule.allowed_paths,
            allowed_commands=rule.allowed_commands,
            forbidden_paths=rule.forbidden_paths,
            stop_conditions=rule.stop_conditions,
            proof=rule.proof,
            budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0),
            capability=rule.capability,
        )

    @staticmethod
    def _diff(path: str) -> str:
        return (
            f"diff --git a/{path} b/{path}\nindex 1111111..2222222 100644\n--- a/{path}\n+++ b/{path}\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )

    def _scope(self, path: str, packet: DispatchPacket | None = None) -> bool:
        packet = packet or self._packet()
        transcript = json.dumps(
            {
                "schemaVersion": "steward-proof-transcript-v1",
                "entries": [
                    {"contractIndex": n, "command": f"check {n}", "exitCode": 0, "output": "ok"}
                    for n in range(1, len(packet.proof) + 1)
                ],
            }
        )
        verdict = evaluate(
            packet=packet,
            change_set=parse_unified_diff(self._diff(path)),
            transcript=parse_proof_transcript(transcript, proof_contract_length=len(packet.proof)),
            debt_source="secret-scan",
            sensor_sources=("secret-scan",),
            baseline_open_debt=["debt:x"],
            current_open_debt=["debt:x"],
            authority_still_class_b=True,
        )
        return verdict.scope_valid

    def test_a_disposition_record_diff_is_in_scope(self) -> None:
        assert self._scope("founder/steward/security-dispositions/abc-1234-0.json")

    @pytest.mark.parametrize(
        "path",
        [
            "src/gaia_cli/auth.py",
            "tests/test_auth.py",
            "scripts/check_security_dispositions.py",
            ".github/workflows/sync-artifacts.yml",
            "founder/steward/POLICY.yaml",
            "founder/steward/decisions/steward-credential-reconciliation-2283.json",
            ".agents/skills/firecrawl/SKILL.md",
        ],
    )
    def test_any_source_policy_or_decision_edit_is_out_of_scope(self, path: str) -> None:
        assert not self._scope(path)

    def test_the_same_scope_allowed_and_forbidden_is_still_forbidden(self) -> None:
        packet = DispatchPacket.create(
            debt={"id": "debt:x", "kind": "credential_review", "source": "secret-scan"},
            evidence={"debtId": "debt:x"}, authority=AuthorityClass.B, rule=RULE, routine="r", objective="o",
            allowed_paths=("a/**",), allowed_commands=("x",), forbidden_paths=("a/**",),
            stop_conditions=("s",), proof=("p",),
            budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0), capability="c",
        )
        assert not self._scope("a/b.json", packet)

    def _policy_text(self, tmp_path: Path, transform) -> Path:
        root = tmp_path / "policyroot"
        target = root / POLICY_RELATIVE_PATH
        target.parent.mkdir(parents=True)
        target.write_text(transform((ROOT / POLICY_RELATIVE_PATH).read_text(encoding="utf-8")), encoding="utf-8")
        return root

    def test_the_exempt_subtree_is_reserved_for_credential_review(self, tmp_path: Path) -> None:
        text = "      allowedPaths:\n        - src/gaia_cli/**\n"
        root = self._policy_text(
            tmp_path,
            lambda body: body.replace(
                text, text + "        - founder/steward/security-dispositions/**\n", 1
            ),
        )
        with pytest.raises(PolicyError, match="reserved"):
            StewardPolicy.load(root)

    def test_founder_wide_write_access_is_still_refused(self, tmp_path: Path) -> None:
        root = self._policy_text(
            tmp_path,
            lambda body: body.replace(
                "        - founder/steward/security-dispositions/**\n      allowedCommands:",
                "        - founder/**\n      allowedCommands:",
                1,
            ),
        )
        with pytest.raises(PolicyError):
            StewardPolicy.load(root)

    def test_credential_review_debt_is_dispatched_under_the_rule_and_credential_leak_is_not(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference() + "\n", **{"other.py": f"k = '{_github_token()}'\n"})
        (root / POLICY_RELATIVE_PATH).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / POLICY_RELATIVE_PATH, root / POLICY_RELATIVE_PATH)
        commit_all(root)
        controller = StewardController(
            sensors=[SecretScanSensor()], clock=lambda: datetime(2026, 11, 7, tzinfo=timezone.utc)
        )
        scan = controller.scan(root)
        review = next(item for item in scan.open_debts if item.kind == "credential_review")
        leak = next(item for item in scan.open_debts if item.kind == "credential_leak")
        assert review.authority is AuthorityClass.B and leak.authority is AuthorityClass.C
        dispatch = render_dispatch(root, review.id, controller=controller)
        assert dispatch.artifact.rule == RULE
        assert dispatch.artifact.allowed_paths == ("founder/steward/security-dispositions/**",)
        with pytest.raises(RoutingError):
            render_dispatch(root, leak.id, controller=controller)


class TestSchemaAndHelper:
    def test_schema_file_agrees_with_the_validator(self, tmp_path: Path) -> None:
        jsonschema = pytest.importorskip("jsonschema")
        schema = json.loads((ROOT / "founder/steward/credential-disposition.schema.json").read_text(encoding="utf-8"))
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, occurrence), = _targets(root)
        good = _record(item, occurrence, debt)
        jsonschema.validate(good, schema)
        assert records.validateRecord(good) is None
        for bad in (
            {**good, "policy": "D9"},
            {**good, "fingerprint": "xyz"},
            {**good, "evidence": ""},
            {**good, "lineSha256": "short"},
            {**good, "occurrence": -1},
        ):
            with pytest.raises(jsonschema.ValidationError):
                jsonschema.validate(bad, schema)
            assert records.validateRecord(bad) is not None

    def test_draft_prefills_identity_and_never_sets_the_verifier(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"a = '{_github_token('one')}'\nb = '{_aws_key('two')}'\n")
        debt = _live(root)
        drafts = helper.draftRecords(root, debt.debt_id)
        assert [item["fingerprint"] for item in drafts] == [f["fingerprint"] for f in debt.observed_state["findings"]]
        for item, (located, _) in zip(drafts, _targets(root)):
            assert item["lineSha256"] == located.lineHash
            assert item["debtId"] == debt.debt_id and item["path"] == SOURCE
            assert item["verifiedBy"] == "" and item["author"] == ""
            assert item["policy"] == "" and item["disposition"] == "" and item["evidence"] == ""
            assert "fileSha256" not in item
            assert records.validateRecord(item) is not None  # inert until a human completes it

    def test_draft_accepts_the_review_debt_id_and_emits_the_stable_leak_id(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference())
        leak = _live(root)
        review = _live(root, kind="credential_review")
        (draft,) = helper.draftRecords(root, review.debt_id)
        assert draft["debtId"] == leak.debt_id

    def test_a_completed_draft_decides_the_finding(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference())
        (draft,) = helper.draftRecords(root, _live(root).debt_id)
        draft.update(
            policy="D3", disposition="runtime-header-construction", author="author-agent",
            verifiedBy="verifier-agent", verifiedAt="2026-11-07T01:00:00Z",
            evidence="Environment reference interpolated at runtime, no literal value in the source.",
        )
        _put(root, draft)
        assert _kinds(root) == {"credential_leak": "healthy", "credential_review": "healthy"}

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
        debt = _live(root).debt_id
        assert helper.main(["draft", debt, "--root", str(root), "--write"]) == 0
        (written,) = list((root / records.RECORDDIR).glob("*.json"))
        assert json.loads(written.read_text(encoding="utf-8"))["verifiedBy"] == ""
        assert helper.main(["draft", debt, "--root", str(root), "--write"]) == 1

    def test_this_test_module_contains_no_credential_literal(self) -> None:
        text = Path(__file__).read_text(encoding="utf-8")
        assert not [name for name, pattern in _SECRET_PATTERNS if pattern.search(text)]
