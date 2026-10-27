import copy
import hashlib
import importlib.util
import json
import subprocess
from pathlib import Path

import pytest

from gaia_cli.frontier import (
    create_verification_request, dedupe_key, read_only_handoff,
    validate_experiment_receipt, validate_lead, validate_request,
)


def lead(target_revision="a" * 40, digest="sha256:" + "b" * 64):
    return {
        "schemaVersion": "challenger-lead-v1", "contractRevision": "challenger-lead-v1.1",
        "leadId": "git-log-L-graft-001", "campaignId": "frontier-test-campaign-1", "claimId": "git-line-history-task-v1",
        "identity": {"name": "Git git-log -L", "kind": "native-cli", "installable": False, "version": "2.56.0"},
        "source": {"url": "https://raw.githubusercontent.com/git/git/v2.56.0/Documentation/git-log.adoc", "observedAtUTC": "2026-10-26T12:00:00Z", "contentDigest": "sha256:" + "c" * 64, "provider": "Git project at v2.56.0", "capturedBytesPath": "sources/git-log.adoc"},
        "capability": {"claim": "Trace the evolution of a selected source line range or function in one file.", "task": "Explain how a function changed over commit history.", "conditions": "Requires a Git repository and a selected file and line range or function pattern."},
        "comparison": {"comparator": "Graft codebase graph retrieval for locating concepts and source spans.", "baseline": "Compare historical line tracing with present-day code context retrieval."},
        "target": {"skillId": "generic-history", "kind": "generic", "revision": target_revision, "contentDigest": digest, "scopeRationale": "Investigatory overlap only; not a replacement claim."},
        "preliminaryEvidence": [{"polarity": "supports-investigation", "url": "https://git-scm.com/docs/git-log", "summary": "Official manual documents the -L option."}, {"polarity": "counterevidence", "url": "https://example.org/review", "summary": "Historical tracing and graph retrieval may be complementary."}],
        "limitations": ["No superiority or replacement claim.", "No comparative execution result yet."],
        "dedupe": {"key": "12345678", "checkedAtUTC": "2026-10-26T12:00:00Z", "matches": []},
        "independentTest": {"proposal": "Execute the fixed protocol in a disposable fixture and compare the two task outputs.", "traceability": "Bind result to request, source, target, protocol, fixture and outputs."},
        "disposition": {"status": "candidate", "rationale": "Concrete behavior is documented but comparative evidence is absent.", "nextAction": "Meta triage and separate independent verification."}
    }


def test_repeated_observation_not_new_lead_but_revision_changes_key():
    a, b = lead(), lead()
    b["source"]["observedAtUTC"] = "2027-01-01T00:00:00Z"
    assert dedupe_key(a) == dedupe_key(b)
    b["target"]["revision"] = "c" * 40
    assert dedupe_key(a) != dedupe_key(b)


@pytest.mark.parametrize("field", ["verified", "approvedBy", "verificationReceipt", "confidence", "publicChallengeId", "actor", "signature"])
def test_forged_authority_fields_rejected(field):
    item = lead(); item[field] = "self-asserted"
    assert any("forbidden authority field" in error for error in validate_lead(item))


def test_nested_forgery_and_bad_url_rejected():
    item = lead(); item["disposition"]["verifiedBy"] = "reviewer"
    assert validate_lead(item)
    item = lead(); item["source"]["url"] = "file:///etc/passwd"
    assert validate_lead(item)


def test_native_noninstallable_lead_needs_no_skill_markdown():
    assert validate_lead(lead()) == []
    assert lead()["identity"]["installable"] is False


def _request_fixture(tmp_path: Path):
    repo = tmp_path / "repo"; repo.mkdir()
    (repo / "registry/nodes").mkdir(parents=True)
    node = b'{"id":"generic-history","type":"basic","description":"Historical code tracing"}\n'
    (repo / "registry/nodes/generic-history.json").write_bytes(node)
    for rel, value in [("sources/git-log.adoc", b"official source snapshot"), ("protocol.json", b"reviewed protocol v1"), ("fixture.py", b"def score(x): return x + 1\n")]:
        path=repo / rel; path.parent.mkdir(parents=True,exist_ok=True); path.write_bytes(value)
    subprocess.run(["git","-C",str(repo),"init","-q"],check=True)
    subprocess.run(["git","-C",str(repo),"config","user.name","Fixture"],check=True)
    subprocess.run(["git","-C",str(repo),"config","user.email","fixture@example.invalid"],check=True)
    subprocess.run(["git","-C",str(repo),"add","."],check=True)
    subprocess.run(["git","-C",str(repo),"commit","-qm","fixture"],check=True)
    revision=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
    item=lead(revision,"sha256:"+hashlib.sha256(node).hexdigest())
    item["source"]["capturedBytesPath"]="sources/git-log.adoc"
    item["source"]["contentDigest"]="sha256:"+hashlib.sha256(b"official source snapshot").hexdigest()
    (repo/"lead.json").write_text(json.dumps(item),encoding="utf-8")
    request=create_verification_request(item,repo_root=repo,lead_path="lead.json",protocol_path="protocol.json",fixture_path="fixture.py")
    return repo,item,request


def _receipt(request, run_id="run-fixture-0001"):
    return {"schemaVersion":"frontier-experiment-receipt-v1","experimentRunId":run_id,"campaignId":request["campaignId"],"nativeVersion":request["native"]["version"],"requestId":request["requestId"],"leadDigest":request["leadDigest"],"claimDigest":request["claimDigest"],"sourceDigest":request["source"]["contentDigest"],"targetDigest":request["target"]["contentDigest"],"targetRevision":request["target"]["revision"],"historyRef":request["historyRef"],"protocolDigest":request["protocol"]["contentDigest"],"fixtureDigest":request["fixture"]["contentDigest"],"result":"inconclusive","outputs":[],"limitations":["No comparative verifier execution."],"recordedAtUTC":"2026-10-26T12:00:00Z"}


def test_request_binds_real_registry_target_source_protocol_fixture_and_digest(tmp_path):
    _,item,request=_request_fixture(tmp_path)
    assert validate_request(request)==[]
    assert request["target"]["skillId"]=="generic-history"
    assert request["source"]["contentDigest"]==item["source"]["contentDigest"]
    modified=copy.deepcopy(request); modified["claimId"]="other-claim"
    assert validate_request(modified)


def test_named_target_must_resolve_real_frontmatter_and_generic_ref(tmp_path):
    repo,item,_=_request_fixture(tmp_path)
    named=b"---\nid: owner/graft\ngenericSkillRef: generic-history\n---\n# Graft\n"
    path=repo/"registry/named/owner/graft.md"; path.parent.mkdir(parents=True); path.write_bytes(named)
    subprocess.run(["git","-C",str(repo),"add","."],check=True)
    subprocess.run(["git","-C",str(repo),"commit","-qm","add named fixture"],check=True)
    revision=subprocess.check_output(["git","-C",str(repo),"rev-parse","HEAD"],text=True).strip()
    item["target"]={"skillId":"owner/graft","kind":"named","genericSkillId":"generic-history","revision":revision,"contentDigest":"sha256:"+hashlib.sha256(named).hexdigest(),"scopeRationale":"Bounded test target."}
    (repo/"lead.json").write_text(json.dumps(item),encoding="utf-8")
    request=create_verification_request(item,repo_root=repo,lead_path="lead.json",protocol_path="protocol.json",fixture_path="fixture.py")
    assert request["target"]["skillId"]=="owner/graft"
    assert request["target"]["genericSkillId"]=="generic-history"
    item["target"]["genericSkillId"]="other-generic"
    with pytest.raises(ValueError,match="does not match"):
        create_verification_request(item,repo_root=repo,lead_path="lead.json",protocol_path="protocol.json",fixture_path="fixture.py")


def test_missing_target_and_source_digest_mismatch_fail_closed(tmp_path):
    repo,item,_=_request_fixture(tmp_path)
    item["target"]["skillId"]="does-not-exist"
    with pytest.raises(ValueError,match="does not exist"):
        create_verification_request(item,repo_root=repo,lead_path="lead.json",protocol_path="protocol.json",fixture_path="fixture.py")


def test_captured_source_bytes_must_match_digest(tmp_path):
    repo,item,_=_request_fixture(tmp_path)
    (repo/item["source"]["capturedBytesPath"]).write_bytes(b"modified source")
    with pytest.raises(ValueError,match="source bytes digest mismatch"):
        create_verification_request(item,repo_root=repo,lead_path="lead.json",protocol_path="protocol.json",fixture_path="fixture.py")


def test_receipt_cross_bindings_and_inline_actor_rejected(tmp_path):
    root,_,request=_request_fixture(tmp_path)
    receipt=_receipt(request)
    assert validate_experiment_receipt(receipt,request)==[]
    positive=copy.deepcopy(receipt); positive["result"]="supported"
    assert any("requires actual native and target" in error for error in validate_experiment_receipt(positive,request,repo_root=root))
    out=root/"generated-output/frontier"; out.mkdir(parents=True)
    outputs=[]
    for label,raw in (("native",b"native output"),("target",b"target output")):
        path=out/f"{label}.txt"; path.write_bytes(raw)
        outputs.append({"label":label,"contentDigest":"sha256:"+hashlib.sha256(raw).hexdigest(),"path":path.relative_to(root).as_posix()})
    positive["outputs"]=outputs
    assert validate_experiment_receipt(positive,request,repo_root=root)==[]
    (out/"native.txt").write_bytes(b"tampered")
    assert any("digest mismatch" in error for error in validate_experiment_receipt(positive,request,repo_root=root))
    wrong=copy.deepcopy(receipt); wrong["targetDigest"]="sha256:"+"0"*64
    assert validate_experiment_receipt(wrong,request)
    forged=copy.deepcopy(receipt); forged["actor"]="independent reviewer"
    assert validate_experiment_receipt(forged,request)
    forged=copy.deepcopy(receipt); forged["result"]="verified"
    assert validate_experiment_receipt(forged,request)
    revised=copy.deepcopy(request); revised["claimId"]="changed"; revised["requestId"]="sha256:"+"f"*64
    assert validate_experiment_receipt(receipt,revised)


def test_handoff_unmatched_advisory_is_deferred_and_never_admits(tmp_path):
    _,item,request=_request_fixture(tmp_path)
    handoff=read_only_handoff(item,packet_path="lead.json",request=request)
    assert handoff["verification"]=="unverified-lead"
    assert handoff["canonicalMutation"]=="prohibited"
    assert handoff["advisoryMatch"]=="matched-actionable-request"
    request["target"]["skillId"]="unmatched"
    from gaia_cli.frontier import _canonical, _sha
    request["requestId"]=_sha(_canonical({k:v for k,v in request.items() if k not in {"requestId","createdAtUTC"}}))
    handoff=read_only_handoff(item,packet_path="lead.json",request=request)
    assert handoff["leadDisposition"]=="deferred"
    assert handoff["advisoryMatch"]=="unmatched-advisory-deferred"


def _recording_fixture(tmp_path):
    repo, _, request = _request_fixture(tmp_path)
    directory = repo / "generated-output/frontier"
    directory.mkdir(parents=True)
    (directory / "request.json").write_text(json.dumps(request))
    # Synthetic unit data; not an actual Git/Graft execution or trusted receipt.
    output = "synthetic unit-only native output"
    native = {"experiment": "git-log-L-vs-graft-v1", "executionCheck": "passed",
              "requestId": request["requestId"], "fixtureDigest": request["fixture"]["contentDigest"],
              "protocolDigest": request["protocol"]["contentDigest"],
              "gitVersion": "git version " + request["native"]["version"], "output": output,
              "outputDigest": "sha256:" + hashlib.sha256(output.encode()).hexdigest()}
    (directory / "native.json").write_text(json.dumps(native))
    (directory / "target.txt").write_text("synthetic unit-only target output")
    script = Path(__file__).resolve().parents[1] / "examples/frontier/record_experiment.py"
    spec = importlib.util.spec_from_file_location("frontier_recorder", script)
    recorder = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(recorder)
    kwargs = {"root": repo, "request_rel": "generated-output/frontier/request.json",
              "native_rel": "generated-output/frontier/native.json"}
    return repo, request, recorder, kwargs


def test_recorder_binds_paired_output_and_detects_subsequent_tampering(tmp_path):
    repo, request, recorder, kwargs = _recording_fixture(tmp_path)
    receipt = recorder.build_receipt(**kwargs, target_rel="generated-output/frontier/target.txt")
    assert receipt["result"] == "inconclusive"
    assert {out["label"] for out in receipt["outputs"]} == {"native", "target"}
    assert not any("no target comparison" in line for line in receipt["limitations"])
    assert validate_experiment_receipt(receipt, request, repo_root=repo) == []
    (repo / "generated-output/frontier/target.txt").write_text("changed")
    assert any("digest mismatch" in e for e in validate_experiment_receipt(receipt, request, repo_root=repo))


@pytest.mark.parametrize("result", ["supported", "contradicted"])
def test_recorder_refuses_comparative_outcome_without_target(tmp_path, result):
    _, _, recorder, kwargs = _recording_fixture(tmp_path)
    with pytest.raises(ValueError, match="requires actual native and target"):
        recorder.build_receipt(**kwargs, result=result)


def test_recorder_checks_native_internal_digest_and_distinct_outputs(tmp_path):
    repo, _, recorder, kwargs = _recording_fixture(tmp_path)
    with pytest.raises(ValueError, match="distinct artifacts"):
        recorder.build_receipt(**kwargs, target_rel=kwargs["native_rel"])
    native = repo / kwargs["native_rel"]
    execution = json.loads(native.read_text()); execution["output"] = "tampered"
    native.write_text(json.dumps(execution))
    with pytest.raises(ValueError, match="native recorded output digest"):
        recorder.build_receipt(**kwargs)


def test_recorder_refuses_identical_native_and_target_content(tmp_path):
    repo, _, recorder, kwargs = _recording_fixture(tmp_path)
    directory = repo / "generated-output/frontier"
    (directory / "copy.json").write_bytes((directory / "native.json").read_bytes())
    with pytest.raises(ValueError, match="distinct content"):
        recorder.build_receipt(**kwargs, target_rel="generated-output/frontier/copy.json", result="supported")


@pytest.mark.parametrize("field", ["requestId", "fixtureDigest", "protocolDigest"])
def test_recorder_refuses_native_not_bound_to_request(tmp_path, field):
    repo, _, recorder, kwargs = _recording_fixture(tmp_path)
    native = repo / kwargs["native_rel"]
    execution = json.loads(native.read_text()); execution[field] = "sha256:" + "0" * 64
    native.write_text(json.dumps(execution))
    with pytest.raises(ValueError, match=field):
        recorder.build_receipt(**kwargs)
    del execution[field]
    native.write_text(json.dumps(execution))
    with pytest.raises(ValueError, match=field):
        recorder.build_receipt(**kwargs)


def test_recorder_refuses_checkout_inputs_that_differ_from_request(tmp_path):
    repo, request, recorder, kwargs = _recording_fixture(tmp_path)
    (repo / request["fixture"]["path"]).write_text("changed after request")
    with pytest.raises(ValueError, match="fixture bytes differ"):
        recorder.build_receipt(**kwargs)


def test_runner_embeds_bindings_isolates_git_and_never_overwrites(tmp_path, monkeypatch):
    repo, request, _, kwargs = _recording_fixture(tmp_path)
    script = Path(__file__).resolve().parents[1] / "examples/frontier/run_git_log_L_fixture.py"
    spec = importlib.util.spec_from_file_location("frontier_runner", script)
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    monkeypatch.setenv("GIT_AUTHOR_NAME", "ambient")
    out = tmp_path / "native-out.json"
    args = ["x", "--request", str(repo / kwargs["request_rel"]), "--output", str(out)]
    monkeypatch.setattr("sys.argv", args)
    assert runner.main() == 0
    record = json.loads(out.read_text())
    assert record["requestId"] == request["requestId"]
    assert record["fixtureDigest"] == runner.sha(runner.FIXTURE_PATH.read_bytes())
    assert record["protocolDigest"] == runner.sha(runner.PROTOCOL_PATH.read_bytes())
    before = out.read_bytes()
    with pytest.raises(FileExistsError):
        runner.main()
    assert out.read_bytes() == before


def test_request_refuses_target_revision_that_is_not_a_commit(tmp_path):
    repo, item, _ = _request_fixture(tmp_path)
    blob = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD:fixture.py"], text=True).strip()
    for bogus in (blob, "0" * 40):
        bad = copy.deepcopy(item); bad["target"]["revision"] = bogus
        (repo / "lead.json").write_text(json.dumps(bad))
        with pytest.raises(ValueError, match="resolve to a commit"):
            create_verification_request(bad, repo_root=repo, lead_path="lead.json", protocol_path="protocol.json", fixture_path="fixture.py")


@pytest.mark.parametrize("relative", ["registry/named/new.json", "../escaped.json", "/tmp/absolute.json", "generated-output/frontier/../escaped.json"])
def test_recorder_rejects_outside_paths(tmp_path, relative):
    _, _, recorder, _ = _recording_fixture(tmp_path)
    with pytest.raises(ValueError, match="relative generated-output/frontier"):
        recorder.artifact_path(tmp_path, relative)


def test_recorder_refuses_symlinked_generated_ancestor(tmp_path):
    _, _, recorder, _ = _recording_fixture(tmp_path)
    other = tmp_path / "other"; other.mkdir()
    (other / "registry").mkdir()
    (other / "generated-output").symlink_to(other / "registry", target_is_directory=True)
    with pytest.raises(ValueError, match="symlinks"):
        recorder.artifact_path(other, "generated-output/frontier/new.json")
    assert list((other / "registry").iterdir()) == []


def test_recorder_cli_preserves_existing_receipt_and_treats_target_as_inert(tmp_path, monkeypatch):
    repo, _, recorder, kwargs = _recording_fixture(tmp_path)
    monkeypatch.setattr(recorder, "ROOT", repo)
    marker = repo / "must-not-execute"
    (repo / "generated-output/frontier/target.txt").write_text("$(touch " + str(marker) + ")")
    args = ["--request", kwargs["request_rel"], "--native-output", kwargs["native_rel"],
            "--target-output", "generated-output/frontier/target.txt", "--output", "generated-output/frontier/new-receipt.json"]
    assert recorder.main(args) == 0
    destination = repo / "generated-output/frontier/new-receipt.json"
    before = destination.read_bytes()
    with pytest.raises(SystemExit) as error:
        recorder.main(args)
    assert error.value.code == 2 and destination.read_bytes() == before
    assert not marker.exists()


def test_outage_is_execution_failed_not_negative_and_untrusted_marketing_invalid(tmp_path):
    _,_,request=_request_fixture(tmp_path)
    receipt=_receipt(request); receipt["result"]="execution_failed"
    receipt["limitations"]=["Timeout is execution failure, not counterevidence."]
    assert validate_experiment_receipt(receipt,request)==[]
    for value in ("vendor-marketing", "unrelated", "verified", "supported"):
        bad=copy.deepcopy(receipt); bad["result"]=value
        assert validate_experiment_receipt(bad,request)


def _set_native_version(repo, kwargs, version, **extra):
    native = repo / kwargs["native_rel"]
    execution = json.loads(native.read_text())
    execution["gitVersion"] = "git version " + version + " (Apple Git-155)"
    execution.update(extra)
    native.write_text(json.dumps(execution))


def test_equal_versions_record_both_fields_without_mismatch_limitation(tmp_path):
    repo, request, recorder, kwargs = _recording_fixture(tmp_path)
    receipt = recorder.build_receipt(**kwargs)
    assert receipt["schemaVersion"] == "frontier-experiment-receipt-v1.1"
    assert receipt["documentedVersion"] == receipt["executedVersion"] == receipt["nativeVersion"] == request["native"]["version"]
    assert not any("differs from documented" in line for line in receipt["limitations"])
    assert validate_experiment_receipt(receipt, request, repo_root=repo) == []


def test_differing_versions_recorded_with_limitation_and_comparative_refused(tmp_path):
    repo, request, recorder, kwargs = _recording_fixture(tmp_path)
    _set_native_version(repo, kwargs, "2.50.1", executedVersion="2.50.1")
    for result in ("supported", "contradicted"):
        with pytest.raises(ValueError, match="only inconclusive or execution_failed"):
            recorder.build_receipt(**kwargs, target_rel="generated-output/frontier/target.txt", result=result)
    for result in ("inconclusive", "execution_failed"):
        receipt = recorder.build_receipt(**kwargs, result=result)
        assert receipt["documentedVersion"] == request["native"]["version"]
        assert receipt["executedVersion"] == receipt["nativeVersion"] == "2.50.1"
        assert any("differs from documented version" in line for line in receipt["limitations"])
        assert validate_experiment_receipt(receipt, request, repo_root=repo) == []
    # A hand-edited receipt cannot bypass the rule in the validator either.
    forged = dict(receipt, result="supported")
    assert any("only inconclusive" in e for e in validate_experiment_receipt(forged, request, repo_root=repo))
    stripped = dict(receipt, limitations=["No comparative verifier execution."])
    assert any("limitation entry required" in e for e in validate_experiment_receipt(stripped, request, repo_root=repo))


def test_tampered_executed_version_in_native_artifact_is_detected(tmp_path):
    repo, _, recorder, kwargs = _recording_fixture(tmp_path)
    _set_native_version(repo, kwargs, "2.50.1", executedVersion="2.56.0")
    with pytest.raises(ValueError, match="executedVersion does not match"):
        recorder.build_receipt(**kwargs)


def test_receipt_schema_v1_still_validates_and_v11_requires_new_fields(tmp_path):
    _, _, request = _request_fixture(tmp_path)
    assert validate_experiment_receipt(_receipt(request), request) == []
    v11 = _receipt(request)
    v11.update(schemaVersion="frontier-experiment-receipt-v1.1", documentedVersion=request["native"]["version"], executedVersion=request["native"]["version"])
    assert validate_experiment_receipt(v11, request) == []
    del v11["executedVersion"]
    assert validate_experiment_receipt(v11, request)
    v11["executedVersion"] = "9.9.9"
    assert any("cross-binding mismatch: nativeVersion" in e for e in validate_experiment_receipt(v11, request))


def test_runner_embeds_executed_version(tmp_path, monkeypatch):
    repo, request, _, kwargs = _recording_fixture(tmp_path)
    script = Path(__file__).resolve().parents[1] / "examples/frontier/run_git_log_L_fixture.py"
    spec = importlib.util.spec_from_file_location("frontier_runner2", script)
    runner = importlib.util.module_from_spec(spec); spec.loader.exec_module(runner)
    out = tmp_path / "native-v.json"
    monkeypatch.setattr("sys.argv", ["x", "--request", str(repo / kwargs["request_rel"]), "--output", str(out)])
    assert runner.main() == 0
    record = json.loads(out.read_text())
    assert record["gitVersion"] == "git version " + record["executedVersion"] or record["gitVersion"].startswith("git version " + record["executedVersion"] + " ")
