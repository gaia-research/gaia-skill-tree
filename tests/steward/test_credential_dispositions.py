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
from gaia_cli.steward.models import AuthorityClass, DispatchPacket, Observation, RoutingBudget, SensorScan, Subject
from gaia_cli.steward.policy import POLICY_RELATIVE_PATH, PolicyError, StewardPolicy
from gaia_cli.steward.routing import RoutingError, render_dispatch
from gaia_cli.steward.sensors_security import (
    SecretScanSensor,
    _SECRET_PATTERNS,
    _SecretTally,
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
    """A value Python itself evaluates: an unquoted attribute path in code (Class B evidence)."""

    return _assign("settings.api_" + "value")


def _shell(line: str) -> str:
    # Assembled so this module never contains a keyword-assignment literal.
    return line.replace("TOK_", "TOK" + "EN")


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
        "contextSha256": item.contextHash,
        "policy": "D2",
        "disposition": "synthetic-fixture",
        "evidence": "Runtime-assembled positive-test value, never issued by any provider.",
        "author": "author-agent",
        "verifiedBy": "verifier-agent",
        "verifiedAt": "2026-11-07T01:00:00Z",
        "verificationReceipt": f"rcpt-{item.finding['fingerprint']}-{index}",
        "founderRuling": records.RULINGID,
    }
    body.update(overrides)
    return body


def _receipt(body: dict, **overrides) -> dict:
    """The receipt the lead's integrate step would record for ``body``'s verification."""

    receipt = {
        "schemaVersion": records.RECEIPTSCHEMA,
        "receiptId": body["verificationReceipt"],
        "action": "agent.verify",
        "outcome": "verified",
        "dispatchRule": records.DISPATCHRULE,
        "reviewDebtId": records.reviewDebtId(body["path"]),
        "builderAgentId": body["author"],
        "verifierAgentId": body["verifiedBy"],
        "recordedAt": "2026-11-07T01:00:00Z",
        "records": [records.contentSha256(body)],
    }
    receipt.update(overrides)
    return receipt


def _put(root: Path, body: dict, name: str | None = None, receipt: bool | dict = True) -> None:
    """Commit a record. ``receipt``: True writes the default receipt once, a dict overrides
    it, False writes none."""

    default = records.recordName(body["debtId"], body["fingerprint"], body.get("occurrence", 0))
    files = {f"{records.RECORDDIR}/{name or default}": json.dumps(body)}
    receiptPath = f"{records.RECEIPTDIR}/{body.get('verificationReceipt')}.json"
    if isinstance(receipt, dict):
        files[receiptPath] = json.dumps(_receipt(body, **receipt))
    elif receipt and not (root / receiptPath).exists():
        who = (body.get("author"), body.get("verifiedBy"))
        if all(isinstance(item, str) and item for item in who) and who[0].casefold() != who[1].casefold():
            files[receiptPath] = json.dumps(_receipt(body))
    write_files(root, files)
    commit_all(root)


def _decide(root: Path, rel: str = SOURCE, **overrides) -> None:
    debt = _live(root, rel).debt_id
    for item, occurrence in _targets(root, rel):
        _put(root, _record(item, occurrence, debt, rel, **overrides))


def _padded(line: str) -> str:
    """The token line with three plain lines either side, so edits at the file ends stay outside its window."""

    return "a1 = 1\na2 = 2\na3 = 3\n" + line + "\nb1 = 1\nb2 = 2\nb3 = 3\n"


def _spread(token: str) -> str:
    """The same token twice, far enough apart that the two contexts differ."""

    return f"a = '{token}'\nx1 = 1\nx2 = 2\nx3 = 3\nx4 = 4\nb = '{token}'\n"


def _block(name: str, token: str | None = None) -> str:
    """A function whose body is the same four lines; the token, when given, sits between lines 2 and 3."""

    body = ["    n1 = 1", "    n2 = 2", "    n3 = 3", "    n4 = 4"]
    if token is not None:
        body = body[:2] + [f"    k = '{token}'"] + body[2:]
    return "\n".join([f"def {name}():", *body]) + "\n"


def _functions(token: str, holder: str) -> str:
    """``alpha`` and ``beta`` with identical bodies; the token sits in ``holder`` only."""

    return _block("alpha", token if holder == "alpha" else None) + "\n" + _block("beta", token if holder == "beta" else None)


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
        # (a) firecrawl/impeccable style churn far from the token: above the window and below it.
        root = _repo(tmp_path, _padded(f"k = '{_github_token()}'"))
        _decide(root)
        assert _kinds(root)["credential_leak"] == "healthy"
        _edit(root, SOURCE, lambda text: "# new header\nimport os\n\n" + text + "def later():\n    return 1\n")
        item = _live(root)
        assert item.status == "healthy"
        assert item.observed_state["dispositions"][0]["line"] == 7  # live line moved; identity did not

    def test_crlf_and_trailing_whitespace_keep_it_decided(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _padded(f"k = '{_github_token()}'"))
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace("\n", "  \r\n"))
        assert _live(root).status == "healthy"

    def test_blank_lines_never_matter(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _padded(f"k = '{_github_token()}'"))
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace("\n", "\n\n"))
        assert _live(root).status == "healthy"

    def test_changed_token_reopens_the_finding(self, tmp_path: Path) -> None:
        # (b) a different token on the same line is a different finding with no record.
        root = _repo(tmp_path, _padded(f"k = '{_github_token('one')}'"))
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace(_github_token("one"), _github_token("two")))
        item = _live(root)
        assert item.status == "drift"
        assert "decidedFindings" not in item.observed_state

    def test_changed_line_around_the_same_token_reopens_the_finding(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _padded(f"k = '{_github_token()}'"))
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace("k = ", "renamed = "))
        assert _live(root).status == "drift"

    def test_an_edit_inside_the_surrounding_window_reopens_the_finding(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _padded(f"k = '{_github_token()}'"))
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace("a3 = 3", "a3 = 33"))
        assert _live(root).status == "drift"

    def test_second_identical_token_added_stays_undecided(self, tmp_path: Path) -> None:
        # (c) the reviewed token stays decided; the new copy, in its own context, has no record.
        token = _github_token()
        root = _repo(tmp_path, _padded(f"k = '{token}'"))
        _decide(root)
        _edit(root, SOURCE, lambda text: text + f"copy = '{token}'\n")
        item = _live(root)
        assert item.status == "drift"
        assert item.observed_state["findingCount"] == 2
        assert item.observed_state["undecidedFindingCount"] == 1
        assert [entry["occurrence"] for entry in item.observed_state["decidedFindings"]] == [0]

    def test_a_duplicate_inserted_before_is_not_decided_and_does_not_decide_the_old_one(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, _functions(token, "alpha"))
        _decide(root)
        assert _live(root).status == "healthy"
        _edit(root, SOURCE, lambda text: _block("gamma", token) + "\n" + text)
        item = _live(root)
        # The new copy sits in another scope (no record for it) and the old one is now the
        # second occurrence (no record claims that): nothing is rebound, nothing is decided.
        assert item.status == "drift"
        assert item.observed_state["findingCount"] == 2
        assert "decidedFindings" not in item.observed_state

    def test_a_line_moved_to_another_function_is_reopened(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, _functions(token, "alpha"))
        _decide(root)
        assert _live(root).status == "healthy"
        # Same token, same neighbouring lines (n1,n2 before / n3,n4 after) -- only the enclosing function differs.
        _edit(root, SOURCE, lambda text: _functions(token, "beta"))
        assert _live(root).status == "drift"

    def test_a_line_moved_back_is_decided_again(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, _functions(token, "alpha"))
        _decide(root)
        _edit(root, SOURCE, lambda text: _functions(token, "beta"))
        _edit(root, SOURCE, lambda text: _functions(token, "alpha"))
        assert _live(root).status == "healthy"

    def test_enclosing_function_renamed_reopens(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, _functions(token, "alpha"))
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace("def alpha():", "def renamed():"))
        assert _live(root).status == "drift"

    def test_identical_blocks_cannot_be_rebound_and_stay_open(self, tmp_path: Path) -> None:
        # A copy-pasted function repeats the token with an identical context: neither can be told apart.
        token = _github_token()
        root = _repo(tmp_path, _block("alpha", token) + "\n" + _block("alpha", token))
        _decide(root)
        item = _live(root)
        assert item.status == "drift"
        assert item.observed_state["findingCount"] == 2
        assert "decidedFindings" not in item.observed_state

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
            {"contextSha256": "0" * 64},
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
            {"schemaVersion": "steward-credential-disposition-v2"},
            {"verifiedAt": "yesterday"},
        ],
    )
    def test_any_mismatch_or_invalid_field_stays_open(self, tmp_path: Path, override: dict) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root, **override)
        assert _live(root).status == "drift"

    def test_retired_binding_fields_are_ignored(self, tmp_path: Path) -> None:
        # Records carrying the retired whole-file or line-only fields are judged on contextSha256 alone.
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, occurrence), = _targets(root)
        _put(root, _record(item, occurrence, debt, fileSha256="0" * 64, lineSha256="0" * 64))
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
        assert first.finding == second.finding and first.contextHash == second.contextHash
        _put(root, _record(first, occurrence, debt))
        one = _live(root)
        assert one.status == "drift"
        assert one.observed_state["findingCount"] == 2
        assert "decidedFindings" not in one.observed_state

    def test_same_line_occurrences_are_identical_and_never_decided_even_with_a_record_each(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, f"a = '{token}'; b = '{token}'\n")
        _decide(root)
        item = _live(root)
        assert item.status == "drift"
        assert "decidedFindings" not in item.observed_state

    def test_identical_findings_in_distinct_contexts_each_need_their_own_record(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, _spread(token))
        debt = _live(root).debt_id
        (first, i0), (second, i1) = _targets(root)
        assert first.contextHash != second.contextHash
        _put(root, _record(first, i0, debt))
        half = _live(root)
        assert half.status == "drift" and half.observed_state["undecidedFindingCount"] == 1
        _put(root, _record(second, i1, debt))
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


class TestBindingStrictness:
    """Only edge whitespace and CR/LF are ignored; anything inside the line reopens."""

    def test_non_breaking_space_inside_the_line_reopens_the_finding(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root)
        assert _live(root).status == "healthy"
        _edit(root, SOURCE, lambda text: text.replace("k = ", "k = ", 1))
        assert _live(root).status == "drift"

    def test_extra_internal_space_reopens_the_finding(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace("k = ", "k  = ", 1))
        assert _live(root).status == "drift"

    def test_unicode_change_next_to_the_token_reopens_the_finding(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        _decide(root)
        _edit(root, SOURCE, lambda text: text.replace("k = ", "k​ = ", 1))
        assert _live(root).status == "drift"

    def test_edge_whitespace_and_line_endings_are_ignored(self) -> None:
        assert records.lineSha256("  a b\t\r\n") == records.lineSha256("a b")
        assert records.lineSha256("a b") != records.lineSha256("a  b")
        assert records.lineSha256("a b") != records.lineSha256("a b")
        # A leading non-breaking space is unicode, not ignorable whitespace.
        assert records.lineSha256(" a") != records.lineSha256("a")

    def test_claimant_missing_occurrence_blocks_every_occurrence(self, tmp_path: Path) -> None:
        token = _github_token()
        root = _repo(tmp_path, _spread(token))
        debt = _live(root).debt_id
        (first, _), (second, _) = _targets(root)
        _put(root, _record(second, 1, debt))  # a valid record for the LATER repeat
        _put(root, _record(first, 0, debt, verificationReceipt="rcpt-x"), "orphan.json", receipt=False)
        assert _live(root).status == "drift"
        # Strip occurrence from that orphan: it now claims every occurrence, never just 0.
        orphan = json.loads((root / records.RECORDDIR / "orphan.json").read_text(encoding="utf-8"))
        del orphan["occurrence"]
        _put(root, orphan, "orphan.json", receipt=False)
        item = _live(root)
        assert item.status == "drift"
        assert item.observed_state.get("decidedFindings", []) == []

    def test_a_single_record_missing_occurrence_decides_nothing(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, index), = _targets(root)
        body = _record(item, index, debt)
        del body["occurrence"]
        _put(root, body, "no-occurrence.json", receipt=False)
        assert _live(root).status == "drift"

    def test_missing_occurrence_claimant_beside_a_valid_record_blocks_it(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, index), = _targets(root)
        body = _record(item, index, debt)
        _put(root, body, "valid.json")
        assert _live(root).status == "healthy"
        loose = dict(body)
        del loose["occurrence"]
        _put(root, loose, "loose.json", receipt=False)
        assert _live(root).status == "drift"


class TestVerifierIdentity:
    """verifiedBy is never self-asserted: a committed receipt must back it."""

    def _one(self, tmp_path: Path):
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        debt = _live(root).debt_id
        (item, index), = _targets(root)
        return root, _record(item, index, debt)

    def test_a_self_asserted_verifier_with_no_receipt_decides_nothing(self, tmp_path: Path) -> None:
        root, body = self._one(tmp_path)
        _put(root, body, receipt=False)
        assert _live(root).status == "drift"

    def test_a_backed_verifier_decides(self, tmp_path: Path) -> None:
        root, body = self._one(tmp_path)
        _put(root, body)
        item = _live(root)
        assert item.status == "healthy"
        assert item.observed_state["dispositions"][0]["verificationReceipt"] == body["verificationReceipt"]

    @pytest.mark.parametrize(
        "override",
        [
            {"verifierAgentId": "someone-else"},
            {"builderAgentId": "someone-else"},
            {"builderAgentId": "verifier-agent"},
            {"outcome": "pending"},
            {"action": "agent.dispatch"},
            {"dispatchRule": "another-rule"},
            {"reviewDebtId": "debt:credential_review:src-other-py:0000000000000000"},
            {"records": ["0" * 64]},
            {"records": []},
            {"recordedAt": "yesterday"},
            {"receiptId": "different"},
            {"schemaVersion": "v0"},
        ],
    )
    def test_a_receipt_that_does_not_back_the_record_decides_nothing(self, tmp_path: Path, override: dict) -> None:
        root, body = self._one(tmp_path)
        _put(root, body, receipt=override)
        assert _live(root).status == "drift"

    def test_builder_and_verifier_must_be_different_agents(self, tmp_path: Path) -> None:
        root, body = self._one(tmp_path)
        _put(root, body, receipt={"builderAgentId": "Verifier-Agent ", "verifierAgentId": "verifier-agent"})
        assert _live(root).status == "drift"

    def test_an_untracked_receipt_decides_nothing(self, tmp_path: Path) -> None:
        root, body = self._one(tmp_path)
        _put(root, body, receipt=False)
        target = root / records.RECEIPTDIR / f"{body['verificationReceipt']}.json"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(json.dumps(_receipt(body)), encoding="utf-8")
        assert _live(root).status == "drift"

    def test_reviewed_content_changed_after_verification_decides_nothing(self, tmp_path: Path) -> None:
        root, body = self._one(tmp_path)
        _put(root, body)
        assert _live(root).status == "healthy"
        _put(root, {**body, "evidence": "Different evidence the verifier never saw, far longer."}, receipt=False)
        assert _live(root).status == "drift"

    def test_the_stamp_itself_is_not_part_of_the_reviewed_content(self, tmp_path: Path) -> None:
        root, body = self._one(tmp_path)
        _put(root, body)
        _put(root, {**body, "verifiedAt": "2026-11-08T09:00:00Z"}, receipt=False)
        assert _live(root).status == "healthy"

    def test_a_receipt_for_another_files_dispatch_is_refused(self, tmp_path: Path) -> None:
        root, body = self._one(tmp_path)
        _put(root, body, receipt={"reviewDebtId": records.reviewDebtId("src/another.py")})
        assert _live(root).status == "drift"

    def test_receipts_are_not_mistaken_for_records(self, tmp_path: Path) -> None:
        root, body = self._one(tmp_path)
        _put(root, body)
        assert "rejectedDispositionRecords" not in _live(root).provenance

    def test_the_builder_envelope_cannot_write_receipts(self) -> None:
        rule = StewardPolicy.load(ROOT).dispatch_rules[RULE]
        assert "founder/steward/security-dispositions/receipts/**" in rule.forbidden_paths
        packet = TestPolicyAndEnvelope()._packet()
        assert not TestPolicyAndEnvelope()._scope("founder/steward/security-dispositions/receipts/rcpt-1.json", packet)

    def test_hash_command_matches_the_consumer(self, tmp_path: Path, capsys: pytest.CaptureFixture) -> None:
        root, body = self._one(tmp_path)
        path = tmp_path / "record.json"
        path.write_text(json.dumps(body), encoding="utf-8")
        assert helper.main(["hash", str(path)]) == 0
        assert capsys.readouterr().out.strip() == records.contentSha256(body)
        assert helper.main(["hash", str(tmp_path / "missing.json")]) == 1


class TestEvidenceRouting:
    """Routing defaults to Class C; Class B needs a positively benign value, by value not path."""

    def test_issuer_token_stays_class_c(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, f"k = '{_github_token()}'\n")
        assert _kinds(root) == {"credential_leak": "drift"}

    def test_reference_value_stays_class_c(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference())
        kinds = _kinds(root)
        assert kinds == {"credential_leak": "drift"}
        assert "credential_review" not in kinds

    def test_reclassification_keeps_history_and_opens_a_class_b_debt(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, "x = 1\n")
        policy = StewardPolicy.load(ROOT)
        subject = Subject(type="source-file", id=SOURCE)
        old = Observation(
            kind="credential_leak", subject=subject, observed_at=NOW, source="secret-scan", status="drift",
            current_state={"credentialMatches": 0}, observed_state={"findingCount": 1, "findings": [{"line": 1}]},
            confidence=0.9,
        )
        (debt,) = reconcile_debt([old], {}, policy).debts
        assert debt.authority is AuthorityClass.C
        scan = [
            Observation(
                kind="credential_review", subject=subject, observed_at=NOW, source="secret-scan", status="drift",
                current_state={"credentialMatches": 0},
                observed_state={"reclassifiedFrom": debt.id},
                confidence=0.6,
            ),
            Observation(
                kind="credential_leak", subject=subject, observed_at=NOW, source="secret-scan", status="healthy",
                current_state={"credentialMatches": 0},
                observed_state={"reclassifiedTo": "credential_review"},
                confidence=0.9,
            ),
        ]
        after = reconcile_debt(scan, {debt.id: debt}, policy)
        leak = next(item for item in after.debts if item.kind == "credential_leak")
        assert (leak.status, leak.resolution) == ("resolved", "reclassified")
        assert leak.observed_state["priorObservedState"] == dict(debt.observed_state)
        opened = next(item for item in after.debts if item.kind == "credential_review")
        assert (opened.status, opened.authority) == ("open", AuthorityClass.B)

    def test_decided_file_resolves_both_debts_with_provenance(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference())
        policy = StewardPolicy.load(ROOT)
        before = [item for item in SecretScanSensor().scan(root, NOW) if item.subject.id == SOURCE]
        seeded = reconcile_debt(before, {}, policy)
        leak_debt = next(item for item in seeded.debts if item.kind == "credential_leak")
        subject = Subject(type="source-file", id=SOURCE)
        review_obs = Observation(
            kind="credential_review", subject=subject, observed_at=NOW, source="secret-scan",
            status="drift", current_state={"credentialMatches": 0}, observed_state={}, confidence=0.6,
        )
        review_seeded = reconcile_debt([review_obs], {}, policy)
        review_debt = next(item for item in review_seeded.debts if item.kind == "credential_review")
        _decide(root)
        after = [item for item in SecretScanSensor().scan(root, NOW) if item.subject.id == SOURCE]
        assert {item.kind: item.status for item in after} == {"credential_leak": "healthy", "credential_review": "healthy"}
        closed = reconcile_debt(after, {leak_debt.id: leak_debt, review_debt.id: review_debt}, policy)
        (resolved_review,) = [item for item in closed.debts if item.id == review_debt.id]
        (resolved_leak,) = [item for item in closed.debts if item.id == leak_debt.id]
        assert (resolved_review.status, resolved_review.resolution) == ("resolved", "decided_disposition")
        assert (resolved_leak.status, resolved_leak.resolution) == ("resolved", "decided_disposition")

    @pytest.mark.parametrize(
        "rel, text",
        [
            ("src/a.py", _assign("settings.api_" + "value")),
            ("src/a.py", _assign("process.env." + "API_VALUE")),  # attribute access in Python code
            ("scripts/a.sh", _shell("TOK_=$" + "{GITHUB_REF}\n")),
            ("scripts/a.sh", _shell('export TOK_="$' + '{GITHUB_REF}"\n')),
            ("scripts/a.sh", _shell("TOK_=$TOKEN_VAR\n")),
            (".github/workflows/ci.yml", "    env:\n      to" + "ken: $" + "{{secrets.GH_VALUE}}\n"),
            ("src/a.js", "const to" + "ken = process.env.PROD" + "_KEY\n"),
            ("src/a.ts", "const to" + "ken = process.env.PROD" + "_KEY\n"),
        ],
    )
    def test_reference_looking_values_stay_class_c(self, tmp_path: Path, rel: str, text: str) -> None:
        root = _repo(tmp_path, "x = 1\n", **{rel: text})
        kinds = _kinds(root, rel)
        assert kinds == {"credential_leak": "drift"}, (rel, text)
        assert "credential_review" not in kinds, (rel, text)

    @pytest.mark.parametrize(
        "rel, text",
        [
            # A quoted Python string that merely LOOKS like a reference is a literal.
            ("src/a.py", _assign('"$' + '{GITHUB_REF}"')),
            ("src/a.py", _assign('"$PASS' + 'WORD"')),
            ("src/a.py", _assign('"process.env.' + 'PROD_KEY"')),
            ("src/a.py", _assign("'<your-" + "value>'")),
            ("src/a.py", _assign("'settings.api_" + "value'")),
            # A shell default embeds a literal, however it is spelled.
            ("src/a.py", _assign('"$' + '{TOK' + 'EN:-actualRealSecret123}"')),
            # Placeholder words and common words are strings a real password can equal.
            ("src/a.py", _assign('"secret_password_' + 'test"')),
            ("src/a.py", _assign('"FAKE-' + 'TOKEN"')),
            ("src/a.py", _assign('"change' + 'me"')),
            ("src/a.py", _assign('"EXAM' + 'PLE"')),
            ("src/a.py", _assign('"YOUR_API' + '_KEY"')),
            ("src/a.py", _assign('"x' * 1 + 'xxxxxxx"')),
            # Python code that is not code: comments and multi-line strings.
            ("src/a.py", "# " + _assign("settings.api_" + "value")),
            ("src/a.py", 'x = """\n' + _assign("settings.api_" + "value") + '"""\n'),
            # Shell: single quotes, defaults, comments, heredocs, hostname tails / non-reference suffixes.
            ("scripts/a.sh", _shell("TOK_='$" + "{GITHUB_REF}'\n")),
            ("scripts/a.sh", _shell("TOK_=$" + "{GITHUB_TOKEN:-actualRealSecret123}\n")),
            ("scripts/a.sh", _shell('TOK_="$' + '{X:-realsecret123}"\n')),
            ("scripts/a.sh", _shell("TOK_=$" + "{X:=realsecret123}\n")),
            ("scripts/a.sh", _shell("# TOK_=$" + "{GITHUB_REF}\n")),
            ("scripts/a.sh", _shell("cat <<'EOF'\nTOK_=$" + "{GITHUB_REF}\nEOF\n")),
            ("scripts/a.sh", _shell('TOK_="$' + '{GITHUB_TOKEN}@github.com/o/r.git"\n')),
            # Workflow: outside a run script, single-quoted, defaulted, commented, or with URL/hostname suffix.
            (".github/workflows/ci.yml", "    env:\n      to" + "ken: $" + "{GITHUB_REF}\n"),
            (".github/workflows/ci.yml", "      - run: |\n          echo '" + "tok" + "en=$" + "{GITHUB_REF}'\n"),
            (".github/workflows/ci.yml", "      - run: |\n          echo \"" + "tok" + "en=$" + "{X:-realsecret123}\"\n"),
            (".github/workflows/ci.yml", "      # " + "tok" + "en: $" + "{{secrets.GH_VALUE}}\n"),
            (
                ".github/workflows/ci.yml",
                "jobs:\n  a:\n    steps:\n      - run: |\n"
                '          git push "https://x-access-token:$' + '{RELEASE_PAT}@github.com/o/r.git"\n',
            ),
            # Languages whose evaluation the scanner does not model are never Class B.
            ("docs/a.md", _assign("settings.api_" + "value")),
            ("config/a.json", '{"to' + 'ken": "$' + '{GITHUB_REF}"}\n'),
            ("config/a.yaml", "to" + "ken: $" + "{GITHUB_REF}\n"),
            ("src/a.js", "const to" + 'ken = process.env.PROD_KEY + "suffix"\n'),
            ("src/a.txt", _assign("settings.api_" + "value")),
            ("Makefile", "TOK" + "EN=$" + "{GITHUB_REF}\n"),
        ],
    )
    def test_values_the_language_does_not_evaluate_stay_class_c(self, tmp_path: Path, rel: str, text: str) -> None:
        root = _repo(tmp_path, "x = 1\n", **{rel: text})
        assert _kinds(root, rel) == {"credential_leak": "drift"}, (rel, text)

    @pytest.mark.parametrize(
        "value",
        [
            "correct-horse-battery-staple",  # a passphrase
            "Xk9Re" + "dactedQ2mZ7vLp4",  # mixed case, digits, redaction-like substring
            "re" + "dacted-looking-but-real-1",  # redaction-like substring only
            "plainvalue",
            "abc123def456" + "...",  # truncated token
            "EXAM" + "PLE" + "abcdefghijklmnopqrstuvwxyz0123456789",  # marker fused into a longer value
            "YOUR_KEY-" + "abcdefghijklmnop0123456789qrstuv",  # marker with a large residue
            "Tr0ub4dor" + "3Horse",  # human-chosen password
        ],
    )
    def test_quoted_literals_stay_class_c(self, tmp_path: Path, value: str) -> None:
        root = _repo(tmp_path, _assign(f'"{value}"'))
        assert _kinds(root) == {"credential_leak": "drift"}, value

    @pytest.mark.parametrize(
        "rel",
        ["src/a.py", "tests/steward/a.py", ".claude/skills/x/helper.py", ".agents/skills/x/helper.py", "docs/a.py"],
    )
    def test_the_same_value_routes_the_same_regardless_of_directory(self, tmp_path: Path, rel: str) -> None:
        # No downgrading because a file is mirrored or under tests/: only the value counts.
        live = _repo(tmp_path / "live", f"k = '{_github_token()}'\n", **{rel: f"k = '{_github_token()}'\n"})
        assert _kinds(live, rel)["credential_leak"] == "drift" and "credential_review" not in _kinds(live, rel)
        opaque = _repo(tmp_path / "opaque", "x = 1\n", **{rel: _assign(f'"{_opaque()}"')})
        assert "credential_review" not in _kinds(opaque, rel)
        quoted = _repo(tmp_path / "quoted", "x = 1\n", **{rel: _assign('"$' + '{GITHUB_REF}"')})
        assert _kinds(quoted, rel) == {"credential_leak": "drift"}
        quiet = _repo(tmp_path / "quiet", "x = 1\n", **{rel: _reference()})
        assert _kinds(quiet, rel) == {"credential_leak": "drift"}
        assert "credential_review" not in _kinds(quiet, rel)

    def test_one_live_shaped_finding_keeps_the_whole_file_class_c(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference() + f"k = '{_aws_key()}'\n")
        assert _kinds(root) == {"credential_leak": "drift"}

    def test_one_unproven_finding_keeps_a_file_of_benign_ones_class_c(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference() + _assign('"correct-horse-battery-staple"'))
        assert _kinds(root) == {"credential_leak": "drift"}

    def test_partially_decided_file_stays_class_c_while_findings_remain_undecided(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference() + _reference().replace("api_value", "other_value"))
        debt = _live(root).debt_id
        (first, index), _second = _targets(root)
        _put(root, _record(first, index, debt))
        leak = _live(root)
        assert leak.kind == "credential_leak" and leak.status == "drift"
        assert leak.observed_state["undecidedFindingCount"] == 1
        assert len(leak.observed_state["decidedFindings"]) == 1
        assert "credential_review" not in _kinds(root)


class TestLeadRulingScannerRegressions:
    """Scanner-level regressions (SecretScanSensor end-to-end on a temp git repo).

    Verifies the FINAL LEAD RULING:
    - Verdict-7 eight probes -> Class C (credential_leak: drift) with no credential_review
    - Verdict-6 five probes -> Class C (credential_leak: drift) with no credential_review
    - Four earlier Python literal probes -> Class C (credential_leak: drift) with no credential_review
    - One positive regression where a matching verified disposition record (with receipt)
      is the only thing that moves a finding out of Class C.
    """

    @pytest.mark.parametrize(
        "label, rel, content",
        [
            # Verdict-7 eight probes (formerly bypassed shape-based B routing)
            (
                "v7-fresh-shell-noncomment-hash-tail",
                "scripts/hash.sh",
                _shell('TOK_=$' + 'SECRET#syntheticSuffix123\n'),
            ),
            (
                "v7-fresh-shell-hash-inside-string",
                "scripts/log.sh",
                'echo "to' + 'ken=$' + 'SECRET#syntheticSuffix123"\n',
            ),
            (
                "v7-fresh-js-multiline-concat",
                "src/multi.js",
                'const to' + 'ken = process.env.PROD_KEY\n  + "syntheticSuffix123";\n',
            ),
            (
                "v7-fresh-js-comment-marker-in-string",
                "src/log.js",
                'const log = "to' + 'ken = process.env.PROD_KEY//syntheticSuffix123";\n',
            ),
            (
                "v7-fresh-js-template-literal",
                "src/template.js",
                'const log = `to' + 'ken = process.env.PROD_KEY\nsyntheticSuffix123`;\n',
            ),
            (
                "v7-fresh-workflow-folded-no-inner-spaces",
                ".github/workflows/fold.yml",
                "jobs:\n  build:\n    steps:\n      - run: echo hi\n        env:\n          pass" + "word: ${{secrets.PROD_TOKEN}}\n            syntheticSuffix123\n",
            ),
            (
                "v7-fresh-workflow-hash-no-inner-spaces",
                ".github/workflows/hash.yml",
                "jobs:\n  build:\n    steps:\n      - run: echo hi\n        env:\n          pass" + "word: ${{secrets.PROD_TOKEN}}#syntheticSuffix123\n",
            ),
            (
                "v7-fresh-workflow-block-literal-with-assignment",
                ".github/workflows/block.yml",
                "notes: |\n  pass" + "word: ${{secrets.PROD_TOKEN}}\n  syntheticSuffix123\n",
            ),
            # Verdict-6 five probes
            (
                "v6-shell-escaped-dollar",
                "scripts/diag.sh",
                'echo "pass' + 'word=\\$SECRET"\n',
            ),
            (
                "v6-py-concat-suffix",
                "src/concat.py",
                _assign('settings.api_value + "secretSuffix123"'),
            ),
            (
                "v6-shell-var-quoted-suffix",
                "scripts/suffix.sh",
                _shell('TOK_=$' + 'SECRET"suffixLiteral123"\n'),
            ),
            (
                "v6-workflow-numeric-literal",
                ".github/workflows/numeric.yml",
                "jobs:\n  build:\n    steps:\n      - run: echo hi\n        env:\n          pass" + "word: ${{12345678}}\n",
            ),
            (
                "v6-workflow-fallback-literal",
                ".github/workflows/fallback.yml",
                "jobs:\n  build:\n    steps:\n      - run: echo hi\n        env:\n          pass" + "word: ${{secrets.TOKEN||12345678}}\n",
            ),
            # Four earlier Python literal probes
            (
                "prior-py-literal-dollar-name",
                "src/p1.py",
                _assign('"$PASS' + 'WORD"'),
            ),
            (
                "prior-py-literal-process-env",
                "src/p2.py",
                _assign('"process.env.' + 'PROD_KEY"'),
            ),
            (
                "prior-py-literal-shell-default",
                "src/p3.py",
                _assign('"$' + '{TOK' + 'EN:-actualRealSecret123}"'),
            ),
            (
                "prior-py-literal-placeholder-word",
                "src/p4.py",
                _assign('"secret_pass' + 'word_test"'),
            ),
        ],
    )
    def test_scanner_regressions_stay_class_c(self, tmp_path: Path, label: str, rel: str, content: str) -> None:
        root = _repo(tmp_path, "x = 1\n", **{rel: content})
        kinds = _kinds(root, rel)
        assert kinds == {"credential_leak": "drift"}, (label, rel, kinds)
        assert "credential_review" not in kinds, (label, rel, kinds)

    def test_verified_disposition_record_is_the_only_way_out_of_class_c(self, tmp_path: Path) -> None:
        """A finding leaves Class C ONLY through an independently verified disposition record with receipt."""
        root = _repo(tmp_path, _reference())
        # Absent a matching verified record, finding stays Class C with no credential_review
        kinds_before = _kinds(root)
        assert kinds_before == {"credential_leak": "drift"}
        assert "credential_review" not in kinds_before

        # With a matching verified disposition record (and receipt), finding moves out of Class C to healthy
        _decide(root)
        kinds_after = _kinds(root)
        assert kinds_after == {"credential_leak": "healthy", "credential_review": "healthy"}
        assert "drift" not in kinds_after.values()


class TestNoPathBasedSkip:
    """Founder: no downgrade solely because a file is under tests/. Evidence is per finding."""

    @staticmethod
    def _tokens() -> dict[str, str]:
        return {
            "ascending digits": "gh" + "p_" + "0123456789" + "abcdefghijklmnopqrstuvwxyz",
            "marker word": "gh" + "p_" + "EXAMPLE" + "a" * 29,
            "low variety": "gh" + "p_" + "ab" * 18,
            "all one char": "gh" + "p_" + "a" * 36,
            "ordinary": _github_token(),
        }

    @pytest.mark.parametrize("label", ["ascending digits", "marker word", "low variety", "all one char", "ordinary"])
    @pytest.mark.parametrize("rel", ["tests/example.py", "tests/steward/example.py", "src/example.py"])
    def test_issuer_shaped_match_is_class_c_whatever_the_directory(self, tmp_path: Path, label: str, rel: str) -> None:
        token = self._tokens()[label]
        assert dict(_SECRET_PATTERNS)["github-token"].search(token), label
        root = _repo(tmp_path, "x = 1\n", **{rel: f"k = '{token}'\n"})
        assert _kinds(root, rel) == {"credential_leak": "drift"}

    def test_the_path_skip_no_longer_exists(self, tmp_path: Path) -> None:
        from gaia_cli.steward import sensors_security

        assert not hasattr(sensors_security, "_synthetic_match")
        token = self._tokens()["ascending digits"]
        root = _repo(tmp_path, "x = 1\n", **{"tests/example.py": f"k = '{token}'\n"})
        item = _live(root, "tests/example.py")
        assert "skippedSyntheticTestFixture" not in item.provenance
        assert item.observed_state["findingCount"] == 1

    def test_a_tests_finding_needs_its_own_record_like_any_other(self, tmp_path: Path) -> None:
        token = self._tokens()["ascending digits"]
        root = _repo(tmp_path, "x = 1\n", **{"tests/example.py": f"k = '{token}'\n"})
        assert _live(root, "tests/example.py").status == "drift"
        _decide(root, "tests/example.py")
        assert _live(root, "tests/example.py").status == "healthy"

    def test_a_tests_finding_with_a_reference_value_stays_class_c(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, "x = 1\n", **{"tests/example.py": _reference()})
        kinds = _kinds(root, "tests/example.py")
        assert kinds == {"credential_leak": "drift"}
        assert "credential_review" not in kinds


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
        if path.startswith("founder/steward/security-dispositions/"):
            # A new, valid, unstamped record: the post-diff JSON the checker evaluates.
            return TestPolicyAndEnvelope._unified(path, "", '{\n  "author": "builder-agent"\n}\n')
        return (
            f"diff --git a/{path} b/{path}\nindex 1111111..2222222 100644\n--- a/{path}\n+++ b/{path}\n"
            "@@ -1 +1 @@\n-old\n+new\n"
        )

    @staticmethod
    def _unified(path: str, old: str, new: str) -> str:
        """A real unified diff (one line of context) between two texts, as ``git diff`` would emit."""

        import difflib

        lines = difflib.unified_diff(
            old.splitlines(),
            new.splitlines(),
            f"a/{path}" if old else "/dev/null",
            f"b/{path}" if new else "/dev/null",
            lineterm="",
            n=1,
        )
        return "\n".join(lines) + "\n"

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

    def _custom(self, kind: str, allowed: tuple[str, ...], forbidden: tuple[str, ...]) -> DispatchPacket:
        return DispatchPacket.create(
            debt={"id": "debt:x", "kind": kind, "source": "secret-scan"},
            evidence={"debtId": "debt:x"}, authority=AuthorityClass.B, rule=RULE, routine="r", objective="o",
            allowed_paths=allowed, allowed_commands=("x",), forbidden_paths=forbidden,
            stop_conditions=("s",), proof=("p",),
            budget=RoutingBudget(model_calls=0, max_tokens=0, max_minutes=0), capability="c",
        )

    @pytest.mark.parametrize("kind", ["registry_integrity_failed", "credential_review"])
    @pytest.mark.parametrize(
        "allowed, forbidden, path",
        [
            # The reviewer's escape: a narrower allowed subtree under another rule's forbidden parent.
            (("registry/nodes/**",), ("registry/**",), "registry/nodes/a.json"),
            ((".github/workflows/**",), (".github/**",), ".github/workflows/ci.yml"),
            (("founder/steward/x/**",), ("founder/**",), "founder/steward/x/a.json"),
            ((".agents/skills/x/**",), (".agents/skills/**",), ".agents/skills/x/SKILL.md"),
        ],
    )
    def test_a_narrower_allowed_path_never_overrides_a_forbidden_parent(
        self, kind: str, allowed: tuple[str, ...], forbidden: tuple[str, ...], path: str
    ) -> None:
        assert not self._scope(path, self._custom(kind, allowed, forbidden))

    def test_the_carve_out_belongs_to_credential_review_alone(self) -> None:
        exempt = "founder/steward/security-dispositions/**"
        path = "founder/steward/security-dispositions/a.json"
        assert self._scope(path, self._custom("credential_review", (exempt,), ("founder/**",)))
        for other in ("registry_integrity_failed", "unused_import", "credential_leak", "cli_contract_drift"):
            assert not self._scope(path, self._custom(other, (exempt,), ("founder/**",)))

    def test_the_carve_out_lifts_only_the_founder_wide_ban(self) -> None:
        exempt = "founder/steward/security-dispositions/**"
        path = "founder/steward/security-dispositions/a.json"
        assert not self._scope(path, self._custom("credential_review", (exempt,), ("founder/steward/**",)))
        assert not self._scope(path, self._custom("credential_review", (exempt,), ("founder/**", exempt)))
        assert not self._scope(
            path, self._custom("credential_review", (exempt,), ("founder/**", "founder/steward/security-dispositions/**"))
        )

    def test_the_carve_out_does_not_reach_a_sibling_of_the_exempt_subtree(self) -> None:
        exempt = "founder/steward/security-dispositions/**"
        packet = self._custom("credential_review", (exempt,), ("founder/**",))
        assert not self._scope("founder/steward/POLICY.yaml", packet)
        assert not self._scope("founder/steward/security-dispositions-evil/a.json", packet)

    RECORD = "founder/steward/security-dispositions/abc-1234-0.json"

    def _scope_of(self, diff: str, files: dict[str, str] | None = None) -> bool:
        """Scope verdict for ``diff``, with ``files`` as the checkout the diff applies to."""

        packet = self._packet()
        transcript = json.dumps(
            {
                "schemaVersion": "steward-proof-transcript-v1",
                "entries": [
                    {"contractIndex": n, "command": f"check {n}", "exitCode": 0, "output": "ok"}
                    for n in range(1, len(packet.proof) + 1)
                ],
            }
        )
        reader = (lambda rel: files.get(rel)) if files is not None else None
        verdict = evaluate(
            packet=packet,
            change_set=parse_unified_diff(diff, base=reader),
            transcript=parse_proof_transcript(transcript, proof_contract_length=len(packet.proof)),
            debt_source="secret-scan",
            sensor_sources=("secret-scan",),
            baseline_open_debt=["debt:x"],
            current_open_debt=["debt:x"],
            authority_still_class_b=True,
        )
        self.last_reasons = verdict.reasons
        return verdict.scope_valid

    BASE = (
        "{\n"
        '  "author": "builder-agent",\n'
        '  "verifiedBy":\n'
        '    "",\n'
        '  "verifiedAt":\n'
        '    "",\n'
        '  "verificationReceipt":\n'
        '    "",\n'
        '  "evidence": "specific evidence for the reviewer to reproduce"\n'
        "}\n"
    )

    def _modify(self, old: str, new: str) -> tuple[str, dict[str, str]]:
        return self._unified(self.RECORD, old, new), {self.RECORD: old}

    def test_a_builder_edit_that_leaves_the_stamp_empty_is_in_scope(self) -> None:
        diff, files = self._modify(self.BASE, self.BASE.replace("specific evidence", "better evidence"))
        assert self._scope_of(diff, files)

    def test_null_and_absent_stamps_are_empty(self) -> None:
        old = '{\n  "author": "builder-agent"\n}\n'
        assert self._scope_of(*self._modify(old, '{\n  "author": "builder-agent",\n  "verifiedBy": null\n}\n'))
        assert self._scope_of(*self._modify(old, '{\n  "author": "someone-else"\n}\n'))

    @pytest.mark.parametrize(
        "field, key_line",
        [
            ("verifiedBy", '  "verifiedBy":\n'),
            ("verifiedAt", '  "verifiedAt":\n'),
            ("verificationReceipt", '  "verificationReceipt":\n'),
        ],
    )
    def test_a_multiline_value_change_under_an_unchanged_key_line_is_rejected(self, field: str, key_line: str) -> None:
        # The reviewer's shape: the key line is untouched context and only the value line changes.
        start = self.BASE.index(key_line) + len(key_line)
        end = self.BASE.index("\n", start)
        new = self.BASE[:start] + '    "chosen-value",' + self.BASE[end:]
        diff, files = self._modify(self.BASE, new)
        assert f'+    "chosen-value",' in diff and f"-{key_line.rstrip()}" not in diff
        assert key_line.rstrip() in diff  # the key line appears only as unchanged context
        assert not self._scope_of(diff, files)
        assert any(field in reason for reason in self.last_reasons), self.last_reasons

    @pytest.mark.parametrize("field", ["verifiedBy", "verifiedAt", "verificationReceipt"])
    @pytest.mark.parametrize(
        "value", ['"chosen"', '" "', "7", "true", '["x"]', '{"a": 1}'],
    )
    def test_any_non_empty_stamp_value_is_rejected_for_every_field(self, field: str, value: str) -> None:
        old = '{\n  "author": "builder-agent"\n}\n'
        new = '{\n  "author": "builder-agent",\n  "' + field + '": ' + value + "\n}\n"
        assert not self._scope_of(*self._modify(old, new))
        assert any(field in reason for reason in self.last_reasons)

    @pytest.mark.parametrize(
        "key", ['"VERIFIEDBY"', '"verified\\u0042y"', '" verifiedBy "', '"verificationreceipt"', '"VerifiedAt"']
    )
    def test_escaped_and_variant_keys_are_still_the_stamp(self, key: str) -> None:
        old = '{\n  "author": "builder-agent"\n}\n'
        new = '{\n  "author": "builder-agent",\n  ' + key + ': "chosen"\n}\n'
        assert not self._scope_of(*self._modify(old, new))

    def test_compact_json_is_judged_on_the_whole_record(self) -> None:
        old = '{"author":"builder-agent","verifiedBy":""}\n'
        assert self._scope_of(*self._modify(old, '{"author":"builder-agent","verifiedBy":"","note":"x"}\n'))
        assert not self._scope_of(*self._modify(old, '{"author":"builder-agent","verifiedBy":"chosen"}\n'))

    def test_an_already_stamped_record_cannot_be_carried_through_an_edit(self) -> None:
        # A stamp present in the post-diff record is rejected even if this diff did not add it.
        old = '{\n  "author": "builder-agent",\n  "verifiedBy": "lead-stamped"\n}\n'
        new = old.replace("builder-agent", "another-builder")
        assert not self._scope_of(*self._modify(old, new))

    def test_a_new_record_is_judged_on_its_whole_content(self) -> None:
        assert self._scope_of(self._unified(self.RECORD, "", '{\n  "author": "builder-agent"\n}\n'))
        stamped = '{\n  "author": "builder-agent",\n  "verifiedBy": "chosen"\n}\n'
        assert not self._scope_of(self._unified(self.RECORD, "", stamped))

    def test_a_deleted_record_has_no_post_image_to_stamp(self) -> None:
        old = '{\n  "author": "builder-agent"\n}\n'
        assert self._scope_of(self._unified(self.RECORD, old, ""), {self.RECORD: old})

    def test_fail_closed_when_the_post_diff_json_is_unavailable(self) -> None:
        diff, _ = self._modify(self.BASE, self.BASE.replace("specific", "better"))
        for files in (None, {}, {self.RECORD: self.BASE.replace('"verificationReceipt":\n    ""', '"verificationReceipt":\n    "zzz"')}):
            assert not self._scope_of(diff, files)
            assert any("unavailable" in reason for reason in self.last_reasons), self.last_reasons

    def test_fail_closed_when_the_post_diff_is_not_a_json_object(self) -> None:
        old = '{\n  "author": "builder-agent"\n}\n'
        for broken in ('{\n  "author": "builder-agent",\n}\n', "[1, 2]\n", "not json\n", '"just a string"\n'):
            assert not self._scope_of(*self._modify(old, broken)), broken

    def test_a_non_json_file_under_the_subtree_is_rejected(self) -> None:
        path = "founder/steward/security-dispositions/notes.txt"
        assert not self._scope_of(self._unified(path, "", "hello\n"))

    def test_other_files_are_not_judged_by_the_stamp_check(self) -> None:
        diff = self._unified("src/gaia_cli/auth.py", "", 'x = {"verifiedBy": "x"}\n')
        assert not self._scope_of(diff)  # out of scope for its own reason
        assert not any("disposition record" in reason for reason in self.last_reasons)

    def test_a_stamped_diff_is_reported_in_the_change_set(self) -> None:
        stamped = '{\n  "author": "builder-agent",\n  "verifiedBy": "x"\n}\n'
        change = parse_unified_diff(self._unified(self.RECORD, "", stamped))
        assert [path for path, _ in change.stamped_paths] == [self.RECORD]
        assert change.to_dict()["stampedPaths"][0]["path"] == self.RECORD
        clean = parse_unified_diff(self._unified(self.RECORD, "", '{"author": "x"}\n'))
        assert clean.stamped_paths == () and "stampedPaths" not in clean.to_dict()

    def test_checkout_base_reads_plain_files_only(self, tmp_path: Path) -> None:
        from gaia_cli.steward.verification import checkoutBase

        (tmp_path / "a").mkdir()
        (tmp_path / "a" / "r.json").write_text("{}", encoding="utf-8")
        (tmp_path / "link.json").symlink_to(tmp_path / "a" / "r.json")
        read = checkoutBase(tmp_path)
        assert read("a/r.json") == "{}"
        assert read("a/missing.json") is None
        assert read("link.json") is None
        assert read("../outside.json") is None

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
        root = _repo(tmp_path, "x = 1\n", **{"other.py": f"k = '{_github_token()}'\n"})
        (root / POLICY_RELATIVE_PATH).parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(ROOT / POLICY_RELATIVE_PATH, root / POLICY_RELATIVE_PATH)
        commit_all(root)

        class _TestSecretSensor(SecretScanSensor):
            def scan_detailed(self, repo_root: Path, observed_at: str) -> SensorScan:
                detailed = super().scan_detailed(repo_root, observed_at)
                extra = Observation(
                    kind="credential_review",
                    subject=Subject(type="source-file", id=SOURCE),
                    observed_at=observed_at,
                    source=self.id,
                    status="drift",
                    current_state={"credentialMatches": 0},
                    observed_state={},
                    confidence=0.6,
                )
                return SensorScan(detailed.observations + (extra,), detailed.skipped)

        controller = StewardController(
            sensors=[_TestSecretSensor()], clock=lambda: datetime(2026, 11, 7, tzinfo=timezone.utc)
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
            {**good, "contextSha256": "short"},
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
            assert item["contextSha256"] == located.contextHash
            assert item["debtId"] == debt.debt_id and item["path"] == SOURCE
            assert item["verifiedBy"] == "" and item["author"] == ""
            assert item["policy"] == "" and item["disposition"] == "" and item["evidence"] == ""
            assert "fileSha256" not in item and "lineSha256" not in item
            assert records.validateRecord(item) is not None  # inert until a human completes it

    def test_draft_accepts_the_review_debt_id_and_emits_the_stable_leak_id(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference())
        leak = _live(root)
        review_debt_id = records.reviewDebtId(SOURCE)
        (draft,) = helper.draftRecords(root, review_debt_id)
        assert draft["debtId"] == leak.debt_id

    def test_a_completed_draft_decides_the_finding(self, tmp_path: Path) -> None:
        root = _repo(tmp_path, _reference())
        (draft,) = helper.draftRecords(root, _live(root).debt_id)
        draft.update(
            policy="D3", disposition="runtime-header-construction", author="author-agent",
            verifiedBy="verifier-agent", verifiedAt="2026-11-07T01:00:00Z", verificationReceipt="rcpt-draft",
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
