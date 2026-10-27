import copy
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from gaia_cli import frontier
from gaia_cli.frontier import META_VERIFICATION_SCHEMA, build_experiment_receipt, receipt_digest, validate_meta_verification
from test_frontier_protocol import FIXTURE, committedBundle

REPO = Path(__file__).resolve().parent.parent
ART = "evidence/frontier-challenges/synthetic-case/artifacts"
RECEIPT_RUN = "run-" + "0" * 32
VERIFIER_RUN = "verify-" + "1" * 32


def sha(raw: bytes) -> str:
    return "sha256:" + hashlib.sha256(raw).hexdigest()


def verifierNative(root, request, receipt, art, output="SYNTHETIC verifier re-run output"):
    native = json.loads((root / art / "native.json").read_text())
    native.pop("syntheticFixture", None)
    native.update(output=output, outputDigest=sha(output.encode()), verifierNote="SYNTHETIC separate run")
    raw = (json.dumps(native, indent=2) + "\n").encode()
    (root / art / "verifier-native.json").write_bytes(raw)
    return {"label": "native", "contentDigest": sha(raw), "path": f"{art}/verifier-native.json"}


@pytest.fixture
def case(tmp_path):
    """Synthetic committed bundle: a receipt plus separately recorded verifier re-execution artifacts."""
    root, request, art = committedBundle(tmp_path)
    receipt = build_experiment_receipt(root=root, request=request, protocol=request["protocol"]["path"],
        execution_path=f"{art}/native.json", target_path=f"{art}/target.txt", result="supported",
        artifact_root=art, run_id=RECEIPT_RUN, recorded_at="2026-10-28T01:02:03Z")
    raw = b"SYNTHETIC verifier re-execution of target\n"
    (root / art / "verifier-target.txt").write_bytes(raw)
    reexec = [verifierNative(root, request, receipt, art), {"label": "target", "contentDigest": sha(raw), "path": f"{art}/verifier-target.txt"}]
    record = {
        "schemaVersion": "frontier-meta-verification-v1", "verificationId": "synthetic-verification-0001",
        "campaignId": receipt["campaignId"], "requestId": receipt["requestId"],
        "receiptDigest": receipt_digest(receipt), "receiptRunId": receipt["experimentRunId"], "verifierRunId": VERIFIER_RUN,
        "outcome": "substantiated",
        "recommend": {"action": "request-admission-review", "rationale": "Synthetic: re-execution matched the receipt."},
        "counterevidence": {"searched": "Synthetic: searched the protocol's own limitations and vendor notes.", "items": []},
        "reexecution": {"performed": True, "artifacts": reexec, "notes": "Synthetic re-run in a separate session."},
        "independence": "declared-unauthenticated",
        "declaredSession": {"harness": "synthetic", "model": "synthetic", "note": "declared, not authenticated"},
        "limitations": ["Synthetic unit fixture; no real verification occurred."],
        "recordedAtUTC": "2026-10-28T02:00:00Z",
    }
    return root, request, receipt, record


def check(case, record=None, **kwargs):
    root, req, receipt, rec = case
    return validate_meta_verification(rec if record is None else record, receipt, req, repo_root=root, artifact_root=ART, **kwargs)


def test_schema_is_valid_and_complete_record_passes(case):
    Draft202012Validator.check_schema(json.loads(META_VERIFICATION_SCHEMA.read_text()))
    assert check(case) == []


def test_verifier_run_id_must_differ_from_receipt_run_id(case):
    rec = copy.deepcopy(case[3]); rec["verifierRunId"] = RECEIPT_RUN
    assert any("verifierRunId must differ" in e for e in check(case, rec))


@pytest.mark.parametrize("outcome", ["supported", "verified", "confirmed", ""])
def test_outcome_vocabulary_is_closed(case, outcome):
    rec = copy.deepcopy(case[3]); rec["outcome"] = outcome
    assert check(case, rec)


@pytest.mark.parametrize("outcome", ["substantiated", "narrowed", "contradicted", "inconclusive", "execution_failed"])
def test_every_declared_outcome_is_accepted_when_otherwise_valid(case, outcome):
    rec = copy.deepcopy(case[3]); rec["outcome"] = outcome
    if outcome not in {"substantiated", "narrowed"}:
        rec["recommend"]["action"] = "hold"
    assert check(case, rec) == []


def test_substantiated_refused_without_reexecution_artifacts(case):
    rec = copy.deepcopy(case[3])
    rec["reexecution"] = {"performed": False, "artifacts": []}
    errors = check(case, rec)
    assert any("requires verifier re-execution artifacts" in e for e in errors)
    rec["reexecution"] = {"performed": True, "artifacts": []}
    assert check(case, rec)  # schema: performed=true needs artifacts
    rec["reexecution"] = {"performed": False, "artifacts": copy.deepcopy(case[3]["reexecution"]["artifacts"])}
    assert check(case, rec)  # schema: performed=false cannot carry artifacts


def test_substantiated_needs_every_receipt_output_label(case):
    rec = copy.deepcopy(case[3]); rec["reexecution"]["artifacts"] = rec["reexecution"]["artifacts"][:1]
    assert any("every receipt output label" in e for e in check(case, rec))


def test_substantiated_without_local_integrity_check_is_refused(case):
    root, req, receipt, rec = case
    errors = validate_meta_verification(rec, receipt, req)
    assert any("integrity verification" in e for e in errors)


def test_request_is_mandatory_so_the_receipt_is_always_validated(case):
    root, req, receipt, rec = case
    assert any("request is required" in e for e in validate_meta_verification(rec, receipt, None, repo_root=root, artifact_root=ART))


def test_reexecution_artifacts_must_exist_match_digest_and_not_be_the_receipts_own(case):
    root, _, _, rec = case
    bad = copy.deepcopy(rec); bad["reexecution"]["artifacts"][0]["contentDigest"] = sha(b"other")
    assert any("re-execution artifact digest mismatch: native" in e for e in check(case, bad))
    (root / ART / "verifier-target.txt").unlink()
    assert any("invalid re-execution artifact" in e for e in check(case))
    own = copy.deepcopy(rec)
    receipt = case[2]
    own["reexecution"]["artifacts"][0] = {**receipt["outputs"][0], "label": "native"}
    assert any("reuses an existing output path" in e for e in check(case, own))
    outside = copy.deepcopy(rec); outside["reexecution"]["artifacts"][0]["path"] = "registry/nodes/x.json"
    assert any("invalid re-execution artifact" in e for e in check(case, outside))


def test_copies_of_receipt_outputs_under_new_names_are_refused(case):
    root, req, receipt, rec = case
    for label, source in (("native", "native.json"), ("target", "target.txt")):
        raw = (root / ART / source).read_bytes()
        (root / ART / f"copy-{label}").write_bytes(raw)
    bad = copy.deepcopy(rec)
    bad["reexecution"]["artifacts"] = [{"label": "native", "contentDigest": sha((root / ART / "native.json").read_bytes()), "path": f"{ART}/copy-native"},
                                       {"label": "target", "contentDigest": sha((root / ART / "target.txt").read_bytes()), "path": f"{ART}/copy-target"}]
    errors = check(case, bad)
    assert sum("byte-identical" in e for e in errors) == 2


def test_junk_native_reexecution_does_not_parse_under_the_pinned_protocol(case):
    root, req, receipt, rec = case
    for junk in (b"junk, not json", b"{}", json.dumps({"experiment": "git-log-L-vs-graft-v1", "executionCheck": "passed"}).encode()):
        (root / ART / "verifier-native.json").write_bytes(junk)
        bad = copy.deepcopy(rec); bad["reexecution"]["artifacts"][0]["contentDigest"] = sha(junk)
        assert any("does not parse under the pinned protocol" in e for e in check(case, bad)), junk


def test_reexecution_bound_to_another_request_or_version_is_refused(case):
    root, req, receipt, rec = case
    native = json.loads((root / ART / "verifier-native.json").read_text())
    for patch, needle in (({"requestId": "sha256:" + "e" * 64}, "requestId"), ({"gitVersion": "git version 9.9.9", "executedVersion": "9.9.9"}, "executed version 9.9.9 differs")):
        raw = json.dumps({**native, **patch}).encode()
        (root / ART / "verifier-native.json").write_bytes(raw)
        bad = copy.deepcopy(rec); bad["reexecution"]["artifacts"][0]["contentDigest"] = sha(raw)
        assert any(needle in e for e in check(case, bad)), needle


@pytest.mark.parametrize("alias", ["{ART}/./verifier-native.json", "{ART}//verifier-native.json", "{ART}/sub/../verifier-native.json"])
def test_path_aliases_cannot_evade_the_path_checks(case, alias):
    root, req, receipt, rec = case
    bad = copy.deepcopy(rec); bad["reexecution"]["artifacts"][0]["path"] = alias.format(ART=ART)
    assert any("not normalized" in e or "descendant" in e for e in check(case, bad))
    own = copy.deepcopy(rec)
    own["reexecution"]["artifacts"][0] = {"label": "native", "contentDigest": receipt["outputs"][0]["contentDigest"], "path": f"{ART}/./native.json"}
    assert check(case, own)


def test_symlinked_reexecution_artifact_is_refused(case):
    root, req, receipt, rec = case
    link = root / ART / "verifier-alias.json"
    link.symlink_to(root / ART / "native.json")
    bad = copy.deepcopy(rec); bad["reexecution"]["artifacts"][0] = {"label": "native", "contentDigest": receipt["outputs"][0]["contentDigest"], "path": f"{ART}/verifier-alias.json"}
    assert any("symlinks" in e for e in check(case, bad))


@pytest.mark.parametrize("result", ["inconclusive", "execution_failed", "contradicted"])
def test_positive_outcomes_need_a_supported_receipt(case, result):
    root, req, receipt, rec = case
    other = copy.deepcopy(receipt); other["result"] = result
    other["limitations"] = receipt["limitations"]
    bad = copy.deepcopy(rec); bad["receiptDigest"] = receipt_digest(other)
    errors = validate_meta_verification(bad, other, req, repo_root=root, artifact_root=ART)
    assert any("requires the receipt result to be supported" in e for e in errors)


def test_positive_outcome_refused_against_a_version_mismatch_receipt(tmp_path):
    root, request, art = committedBundle(tmp_path)
    shutil.copy(FIXTURE / "native-host-version.json", root / art / "native.json")
    receipt = build_experiment_receipt(root=root, request=request, protocol=request["protocol"]["path"], execution_path=f"{art}/native.json",
                                       result="inconclusive", artifact_root=art, run_id=RECEIPT_RUN, recorded_at="2026-10-28T01:02:03Z")
    ver = verifierNative(root, request, receipt, art)
    rec = {"schemaVersion": "frontier-meta-verification-v1", "verificationId": "synthetic-verification-0002", "campaignId": receipt["campaignId"],
           "requestId": receipt["requestId"], "receiptDigest": receipt_digest(receipt), "receiptRunId": receipt["experimentRunId"], "verifierRunId": VERIFIER_RUN,
           "outcome": "substantiated", "recommend": {"action": "hold", "rationale": "Synthetic hold rationale."},
           "counterevidence": {"searched": "Synthetic search statement.", "items": []},
           "reexecution": {"performed": True, "artifacts": [ver]}, "independence": "declared-unauthenticated",
           "limitations": ["synthetic"], "recordedAtUTC": "2026-10-28T02:00:00Z"}
    errors = validate_meta_verification(rec, receipt, request, repo_root=root, artifact_root=ART)
    assert any("executed version differs from the documented version" in e for e in errors)
    assert any("requires the receipt result to be supported" in e for e in errors)


def test_narrowed_or_admission_recommendation_needs_reexecution_like_substantiated(case):
    for outcome in ("narrowed", "substantiated"):
        rec = copy.deepcopy(case[3]); rec["outcome"] = outcome; rec["reexecution"] = {"performed": False, "artifacts": []}
        assert any("requires verifier re-execution artifacts" in e for e in check(case, rec))
    rec = copy.deepcopy(case[3]); rec["outcome"] = "narrowed"
    rec["reexecution"] = {"performed": False, "artifacts": []}
    rec["recommend"]["action"] = "hold"
    assert any("requires verifier re-execution artifacts" in e for e in check(case, rec))
    rec["outcome"] = "inconclusive"
    assert check(case, rec) == []



@pytest.mark.parametrize("value", ["verified", "independent", "authenticated", "declared", "", None, True])
def test_independence_can_only_be_declared_unauthenticated(case, value):
    rec = copy.deepcopy(case[3]); rec["independence"] = value
    assert check(case, rec)


@pytest.mark.parametrize("field", ["approval", "approved", "admitted", "admission", "verified", "verifiedBy", "confidence", "publicChallengeId",
                                   "challengeStatus", "actor", "signature", "verifierId", "trustMagnitude", "tm", "stars", "level", "origin", "Approved", "ADMITTED", "reviewer"])
def test_forged_authority_fields_are_refused_anywhere(case, field):
    top = copy.deepcopy(case[3]); top[field] = True
    assert any("forbidden authority field" in e for e in check(case, top))
    nested = copy.deepcopy(case[3]); nested["recommend"][field] = "yes"
    assert any(f"recommend.{field}" in e for e in check(case, nested))
    deep = copy.deepcopy(case[3]); deep["counterevidence"]["items"] = [{"summary": "synthetic summary", "source": "x://y", field: 1}]
    assert any("forbidden authority field" in e for e in check(case, deep))


def test_counterevidence_search_statement_is_required_even_when_empty(case):
    rec = copy.deepcopy(case[3]); del rec["counterevidence"]
    assert check(case, rec)
    rec = copy.deepcopy(case[3]); rec["counterevidence"] = {"items": []}
    assert check(case, rec)
    rec = copy.deepcopy(case[3]); rec["counterevidence"] = {"searched": "Synthetic: searched, found one contrary item.", "items": [{"summary": "Synthetic contrary finding.", "source": "https://example.org/x"}]}
    assert check(case, rec) == []


def test_record_is_bound_to_the_exact_receipt(case):
    root, req, receipt, rec = case
    changed = copy.deepcopy(receipt); changed["limitations"] = ["edited after the verification was recorded"]
    errors = validate_meta_verification(rec, changed, req, repo_root=root, artifact_root=ART)
    assert "receipt binding mismatch: receiptDigest" in errors
    for field, value in (("requestId", "sha256:" + "f" * 64), ("receiptRunId", "run-other-0001"), ("campaignId", "other-campaign")):
        bad = copy.deepcopy(rec); bad[field] = value
        assert f"receipt binding mismatch: {field}" in check(case, bad)


def test_request_supplied_revalidates_receipt_and_surfaces_its_errors(case):
    root, req, receipt, rec = case
    (root / ART / "native.json").write_text("{}")
    errors = check(case, rec)
    assert any(e.startswith("receipt: output artifact digest mismatch") for e in errors)


def test_recommending_admission_review_requires_a_positive_or_narrowed_outcome(case):
    rec = copy.deepcopy(case[3]); rec["outcome"] = "contradicted"
    assert any("request-admission-review may only be recommended" in e for e in check(case, rec))
    rec["outcome"] = "narrowed"
    assert check(case, rec) == []


def test_inconclusive_triage_record_needs_no_reexecution_or_root(case):
    root, req, receipt, rec = case
    triage = copy.deepcopy(rec)
    triage.update(outcome="inconclusive", reexecution={"performed": False, "artifacts": []},
                  recommend={"action": "hold", "rationale": "Synthetic triage-only record; nothing was re-executed."})
    assert check(case, triage) == []


def test_non_object_inputs_fail_closed(case):
    assert validate_meta_verification([], case[2], case[1]) == ["record must be a JSON object"]
    assert any("receipt must be a JSON object" in e for e in validate_meta_verification(case[3], [], case[1]))


def run_cli(argv, capsys):
    from gaia_cli.main import main
    old, sys.argv = sys.argv, ["gaia", *argv]
    try:
        code = main()
    except SystemExit as exc:
        code = exc.code
    finally:
        sys.argv = old
    return code, capsys.readouterr()


def test_cli_meta_validate_reports_structural_validity_only(case, tmp_path, capsys):
    root, req, receipt, rec = case
    files = {}
    for name, value in (("record", rec), ("receipt", receipt), ("request", req)):
        files[name] = tmp_path / f"{name}.json"
        files[name].write_text(json.dumps(value))
    base = ["--registry", str(root / "registry"), "dev", "frontier", "meta-validate", "--record", str(files["record"]), "--receipt", str(files["receipt"]),
            "--request", str(files["request"]), "--repo-root", str(root), "--artifact-root", ART]
    code, out = run_cli(base, capsys)
    result = json.loads(out.out)
    assert code in (0, None) and result["structurallyValid"] is True and "not verification" in result["authority"]
    bad = dict(rec, independence="verified")
    files["record"].write_text(json.dumps(bad))
    code, out = run_cli(base, capsys)
    assert code == 1 and json.loads(out.out)["structurallyValid"] is False


def test_cli_meta_validate_uses_checkout_root_and_requires_request(case, tmp_path, capsys):
    root, req, receipt, rec = case
    paths = {}
    for name, value in (("record", rec), ("receipt", receipt), ("request", req)):
        paths[name] = tmp_path / f"{name}2.json"
        paths[name].write_text(json.dumps(value))
    (root / "registry/nodes").mkdir(parents=True)  # a checkout root, as resolve_registry_path returns
    argv = ["--registry", str(root), "dev", "frontier", "meta-validate", "--record", str(paths["record"]), "--receipt", str(paths["receipt"]), "--artifact-root", ART]
    code, out = run_cli([*argv, "--request", str(paths["request"])], capsys)
    assert code in (0, None) and json.loads(out.out)["structurallyValid"] is True
    code, out = run_cli(argv, capsys)  # no --request
    assert code == 2 and "--request" in out.err


@pytest.mark.parametrize("skill", ["gaia-audit", "gaia-meta-audit"])
def test_skills_emit_the_record_and_mirrors_are_identical(skill):
    claude = (REPO / ".claude/skills" / skill / "SKILL.md").read_bytes()
    agents = (REPO / ".agents/skills" / skill / "SKILL.md").read_bytes()
    assert claude == agents
    text = claude.decode()
    for needle in ("frontier-meta-verification-v1", "declared-unauthenticated", "meta-validate", "verifierRunId"):
        assert needle in text
