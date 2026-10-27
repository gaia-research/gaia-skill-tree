import copy
import hashlib
import importlib.util
import json
import shutil
import subprocess
from pathlib import Path

import pytest

from gaia_cli import frontier
from gaia_cli.frontier import (
    build_experiment_receipt, create_verification_request, experiment_declaration,
    resolve_artifact, validate_experiment_receipt, validate_protocol,
)
from test_frontier import lead

REPO = Path(__file__).resolve().parent.parent
FIXTURE = Path(__file__).parent / "fixtures" / "frontier-protocol"  # see SYNTHETIC.txt
FIXED = {"run_id": "run-" + "0" * 32, "recorded_at": "2026-10-28T01:02:03Z"}


def loadScript(name):
    spec = importlib.util.spec_from_file_location(name, REPO / "examples/frontier" / f"{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def legacyRoot(tmp_path, native, target=None, artifact_root="generated-output/frontier"):
    """Checkout holding the real git-log-L protocol/fixture bytes plus the stored request and artifacts."""
    request = json.loads((FIXTURE / "request.json").read_text())
    root = tmp_path / "checkout"
    for rel in (request["protocol"]["path"], request["fixture"]["path"]):
        (root / rel).parent.mkdir(parents=True, exist_ok=True)
        shutil.copy(REPO / rel, root / rel)
    out = root / artifact_root
    out.mkdir(parents=True)
    shutil.copy(FIXTURE / "request.json", out / "request.json")
    shutil.copy(FIXTURE / native, out / "native.json")
    if target:
        shutil.copy(FIXTURE / "target-output.txt", out / "target.txt")
    return root, request


@pytest.mark.parametrize("name,native,target,result", [
    ("mismatch", "native-host-version.json", False, "inconclusive"),
    ("equal", "native-documented-version.json", True, "contradicted"),
])
def test_legacy_git_log_L_receipt_is_byte_identical_to_pre_refactor_golden(tmp_path, name, native, target, result):
    root, request = legacyRoot(tmp_path, native, target)
    wrapped = json.loads((FIXTURE / f"golden-receipt-{name}.json").read_text())
    assert "SYNTHETIC" in wrapped["syntheticFixture"]
    golden = json.dumps(wrapped["receipt"], indent=2) + "\n"
    kwargs = dict(root=root, execution_path="generated-output/frontier/native.json", result=result, **FIXED,
                  target_path="generated-output/frontier/target.txt" if target else None)
    # 1. through the protocol file the request pins (legacy file declares no contract itself)
    receipt = build_experiment_receipt(request=request, protocol=request["protocol"]["path"], **kwargs)
    assert json.dumps(receipt, indent=2) + "\n" == golden
    assert validate_experiment_receipt(receipt, request, repo_root=root) == []
    assert "experimentId" not in receipt  # legacy contract: receipt bytes unchanged
    # 2. through the original recorder entry point
    recorder = loadScript("record_experiment")
    old = recorder.build_receipt(root=root, request_rel="generated-output/frontier/request.json",
                                 native_rel="generated-output/frontier/native.json",
                                 target_rel="generated-output/frontier/target.txt" if target else None, result=result)
    old.update(experimentRunId=FIXED["run_id"], recordedAtUTC=FIXED["recorded_at"])
    assert json.dumps(old, indent=2) + "\n" == golden


def test_legacy_protocol_file_is_unmodified():
    request = json.loads((FIXTURE / "request.json").read_text())
    raw = (REPO / request["protocol"]["path"]).read_bytes()
    assert "sha256:" + hashlib.sha256(raw).hexdigest() == request["protocol"]["contentDigest"]


def committedBundle(tmp_path, case="synthetic-case"):
    artifact_root = f"evidence/frontier-challenges/{case}/artifacts"
    root, request = legacyRoot(tmp_path, "native-documented-version.json", True, artifact_root)
    return root, request, artifact_root


def test_committed_bundle_revalidates_under_artifact_root(tmp_path):
    root, request, art = committedBundle(tmp_path)
    receipt = build_experiment_receipt(root=root, request=request, protocol=request["protocol"]["path"],
        execution_path=f"{art}/native.json", target_path=f"{art}/target.txt", result="contradicted", artifact_root=art)
    assert validate_experiment_receipt(receipt, request, repo_root=root, artifact_root=art) == []
    # The default root still refuses a committed bundle, and other cases' roots are not interchangeable.
    assert any("outside generated-output/frontier" in e for e in validate_experiment_receipt(receipt, request, repo_root=root))
    assert any("outside evidence/frontier-challenges/other/artifacts" in e for e in validate_experiment_receipt(receipt, request, repo_root=root, artifact_root="evidence/frontier-challenges/other/artifacts"))
    (root / art / "target.txt").write_text("tampered after the fact")
    assert any("digest mismatch" in e for e in validate_experiment_receipt(receipt, request, repo_root=root, artifact_root=art))


@pytest.mark.parametrize("bad", ["registry/nodes", "evidence", "evidence/frontier-challenges/x/artifacts/sub", "../artifacts", "/tmp/x", "evidence/frontier-challenges/../artifacts"])
def test_unpermitted_artifact_roots_are_refused(tmp_path, bad):
    root, request, art = committedBundle(tmp_path)
    receipt = build_experiment_receipt(root=root, request=request, protocol=request["protocol"]["path"],
        execution_path=f"{art}/native.json", result="inconclusive", artifact_root=art)
    assert any("artifact_root must be" in e for e in validate_experiment_receipt(receipt, request, repo_root=root, artifact_root=bad))
    with pytest.raises(ValueError, match="artifact_root must be"):
        resolve_artifact(root, f"{bad}/x.json", bad)


def test_symlinked_artifact_root_cannot_launder_outside_files(tmp_path):
    root, request, art = committedBundle(tmp_path)
    receipt = build_experiment_receipt(root=root, request=request, protocol=request["protocol"]["path"],
        execution_path=f"{art}/native.json", result="inconclusive", artifact_root=art)
    real = root / art
    moved = root / "elsewhere"
    real.rename(moved)
    real.symlink_to(moved, target_is_directory=True)
    assert any("symlinks" in e for e in validate_experiment_receipt(receipt, request, repo_root=root, artifact_root=art))


def syntheticProtocol(**experiment):
    base = {
        "id": "synthetic-echo-v1", "toolName": "Echo", "runnerLabel": "Synthetic echo runner",
        "expectedArtifactKeys": ["experiment", "executionCheck", "requestId", "fixtureDigest", "protocolDigest", "echoVersion", "output", "outputDigest", "extra"],
        "outputField": "output", "outputDigestField": "outputDigest",
        "versionProbe": {"field": "echoVersion", "pattern": r"echo (\S+)", "label": "echo --version"},
        "resultRule": {"statement": "Synthetic pre-registered rule: only inconclusive is permitted.", "allowedResults": ["inconclusive", "execution_failed"]},
    }
    base.update(experiment)
    return {"schemaVersion": "frontier-protocol-v1", "protocolId": "synthetic-echo-protocol", "revision": "1.0.0",
            "purpose": "Synthetic protocol for unit tests.", "question": "Does the synthetic runner echo?", "experiment": base}


def syntheticRepo(tmp_path, protocol):
    repo = tmp_path / "synthetic"
    (repo / "registry/nodes").mkdir(parents=True)
    node = b'{"id":"generic-history","type":"basic","description":"Historical code tracing"}\n'
    (repo / "registry/nodes/generic-history.json").write_bytes(node)
    for rel, value in [("sources/git-log.adoc", b"official source snapshot"), ("protocol.json", (json.dumps(protocol) + "\n").encode()), ("fixture.py", b"print('x')\n")]:
        path = repo / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(value)
    for cmd in (["init", "-q"], ["config", "user.name", "Fixture"], ["config", "user.email", "f@example.invalid"], ["add", "."], ["commit", "-qm", "fixture"]):
        subprocess.run(["git", "-C", str(repo), *cmd], check=True)
    revision = subprocess.check_output(["git", "-C", str(repo), "rev-parse", "HEAD"], text=True).strip()
    item = lead(revision, "sha256:" + hashlib.sha256(node).hexdigest())
    item["source"]["capturedBytesPath"] = "sources/git-log.adoc"
    item["source"]["contentDigest"] = "sha256:" + hashlib.sha256(b"official source snapshot").hexdigest()
    (repo / "lead.json").write_text(json.dumps(item), encoding="utf-8")
    request = create_verification_request(item, repo_root=repo, lead_path="lead.json", protocol_path="protocol.json", fixture_path="fixture.py")
    out = repo / "generated-output/frontier"
    out.mkdir(parents=True)
    return repo, request, out


def writeNative(out, request, **overrides):
    output = "synthetic echo output"
    native = {"experiment": "synthetic-echo-v1", "executionCheck": "passed", "requestId": request["requestId"],
              "fixtureDigest": request["fixture"]["contentDigest"], "protocolDigest": request["protocol"]["contentDigest"],
              "echoVersion": "echo " + request["native"]["version"], "output": output,
              "outputDigest": "sha256:" + hashlib.sha256(output.encode()).hexdigest(), "extra": 1}
    native.update(overrides)
    (out / "native.json").write_text(json.dumps(native))


def build(repo, request, **kwargs):
    return build_experiment_receipt(root=repo, request=request, protocol="protocol.json",
        execution_path="generated-output/frontier/native.json", **kwargs)


def test_generic_protocol_drives_receipt_and_digest_is_bound_into_request(tmp_path):
    repo, request, out = syntheticRepo(tmp_path, syntheticProtocol())
    writeNative(out, request)
    receipt = build(repo, request)
    assert receipt["protocolDigest"] == request["protocol"]["contentDigest"]
    assert receipt["executedVersion"] == request["native"]["version"]
    assert any("Synthetic echo runner executed" in line for line in receipt["limitations"])
    assert validate_experiment_receipt(receipt, request, repo_root=repo) == []
    # Changing the protocol after the request was bound is refused (digest is part of requestId).
    (repo / "protocol.json").write_text(json.dumps(syntheticProtocol(id="other-id")) + "\n")
    with pytest.raises(ValueError, match="checkout protocol bytes differ"):
        build(repo, request)


def test_generic_protocol_enforces_result_rule_keys_id_and_probe(tmp_path):
    repo, request, out = syntheticRepo(tmp_path, syntheticProtocol())
    writeNative(out, request)
    for result in ("supported", "contradicted"):
        with pytest.raises(ValueError, match="not permitted by the protocol result rule"):
            build(repo, request, result=result)
    writeNative(out, request, experiment="some-other-experiment")
    with pytest.raises(ValueError, match="did not match expected reviewed protocol"):
        build(repo, request)
    native = json.loads((out / "native.json").read_text())
    native["experiment"] = "synthetic-echo-v1"
    del native["extra"]
    (out / "native.json").write_text(json.dumps(native))
    with pytest.raises(ValueError, match="missing expected keys: extra"):
        build(repo, request)
    writeNative(out, request, echoVersion="not a version line")
    with pytest.raises(ValueError, match="recognizable echo --version"):
        build(repo, request)
    writeNative(out, request, echoVersion="echo 9.9.9")
    receipt = build(repo, request, result="execution_failed")
    assert receipt["executedVersion"] == "9.9.9" and any("differs from documented" in x for x in receipt["limitations"])


def test_protocol_path_must_be_the_one_the_request_pins(tmp_path):
    repo, request, out = syntheticRepo(tmp_path, syntheticProtocol())
    writeNative(out, request)
    shutil.copy(repo / "protocol.json", repo / "copy.json")
    with pytest.raises(ValueError, match="does not match the request's pinned protocol"):
        build_experiment_receipt(root=repo, request=request, protocol="copy.json", execution_path="generated-output/frontier/native.json")


def test_protocol_schema_and_unknown_protocols_fail_closed():
    assert validate_protocol(syntheticProtocol()) == []
    broken = syntheticProtocol()
    del broken["experiment"]["resultRule"]
    assert validate_protocol(broken)
    bad = syntheticProtocol(versionProbe={"field": "v", "pattern": r"(a)(b)", "label": "x"})
    assert any("exactly one capture group" in e for e in validate_protocol(bad))
    assert validate_protocol(syntheticProtocol(versionProbe={"field": "v", "pattern": "(", "label": "x"}))
    with pytest.raises(ValueError, match="declares no experiment contract"):
        experiment_declaration({"protocolId": "unknown-protocol"})
    with pytest.raises(ValueError, match="declares no experiment contract"):
        experiment_declaration(["not", "a", "protocol"])
    assert experiment_declaration({"protocolId": "git-log-L-vs-graft-v1"})["toolName"] == "Git"


def test_generic_request_builder_binds_lead_protocol_and_fixture(tmp_path, monkeypatch):
    repo, _, _ = syntheticRepo(tmp_path, syntheticProtocol())
    builder = loadScript("build_verification_request")
    monkeypatch.setattr(builder, "ROOT", repo)
    code = builder.main(["--lead", "lead.json", "--protocol", "protocol.json", "--fixture", "fixture.py",
                         "--request-out", "generated-output/frontier/req.json", "--handoff-out", "generated-output/frontier/handoff.json"])
    assert code == 0
    request = json.loads((repo / "generated-output/frontier/req.json").read_text())
    assert frontier.validate_request(request) == []
    assert request["protocol"]["path"] == "protocol.json"
    assert request["protocol"]["contentDigest"] == "sha256:" + hashlib.sha256((repo / "protocol.json").read_bytes()).hexdigest()
    assert json.loads((repo / "generated-output/frontier/handoff.json").read_text())["canonicalMutation"] == "prohibited"
    # Output paths cannot escape the checkout.
    with pytest.raises(SystemExit):
        builder.main(["--lead", "lead.json", "--protocol", "protocol.json", "--fixture", "fixture.py", "--request-out", "../escape.json"])
    assert not (tmp_path / "escape.json").exists()
    # A malformed v1 protocol is refused before any request is bound.
    (repo / "protocol.json").write_text(json.dumps({"schemaVersion": "frontier-protocol-v1"}))
    with pytest.raises(SystemExit):
        builder.main(["--lead", "lead.json", "--protocol", "protocol.json", "--fixture", "fixture.py"])


def test_default_request_builder_defaults_match_original_example():
    builder = loadScript("build_verification_request")
    assert builder.defaultOutputs(builder.DEFAULT_LEAD) == (
        "generated-output/frontier/git-log-L-graft.verification-request-v1.json",
        "generated-output/frontier/git-log-L-graft.meta-handoff-v1.json")


def test_recorder_cli_accepts_protocol_and_artifact_root(tmp_path, monkeypatch):
    repo, request, out = syntheticRepo(tmp_path, syntheticProtocol())
    art = "evidence/frontier-challenges/synthetic-case/artifacts"
    (repo / art).mkdir(parents=True)
    (repo / art / "request.json").write_text(json.dumps(request))
    writeNative(repo / art, request)
    recorder = loadScript("record_experiment")
    monkeypatch.setattr(recorder, "ROOT", repo)
    args = ["--request", f"{art}/request.json", "--native-output", f"{art}/native.json", "--protocol", "protocol.json",
            "--artifact-root", art, "--output", f"{art}/receipt.json"]
    assert recorder.main(args) == 0
    receipt = json.loads((repo / art / "receipt.json").read_text())
    assert validate_experiment_receipt(receipt, request, repo_root=repo, artifact_root=art) == []
    with pytest.raises(SystemExit):
        recorder.main(args)


# --- review repairs -------------------------------------------------------------------------

def v1Receipt(tmp_path, **experiment):
    repo, request, out = syntheticRepo(tmp_path, syntheticProtocol(**experiment))
    writeNative(out, request)
    return repo, request, out


def test_legacy_default_cannot_override_a_pinned_protocol_that_forbids_supported(tmp_path):
    """A request pinning an inconclusive-only protocol must not yield `supported` via the legacy default."""
    repo, request, out = syntheticRepo(tmp_path, syntheticProtocol())
    writeNative(out, request)
    (out / "target.txt").write_text("synthetic target output")
    recorder = loadScript("record_experiment")
    kwargs = dict(root=repo, request_rel="generated-output/frontier/req.json", native_rel="generated-output/frontier/native.json",
                  target_rel="generated-output/frontier/target.txt")
    (out / "req.json").write_text(json.dumps(request))
    for result in ("supported", "contradicted"):
        with pytest.raises(ValueError, match="not permitted by the protocol result rule"):
            recorder.build_receipt(**kwargs, result=result)
    receipt = recorder.build_receipt(**kwargs, result="inconclusive")
    assert receipt["experimentId"] == "synthetic-echo-v1"
    assert validate_experiment_receipt(receipt, request, repo_root=repo) == []


def test_dict_protocol_is_no_longer_accepted_and_pinned_path_must_match(tmp_path):
    repo, request, out = v1Receipt(tmp_path)
    with pytest.raises(ValueError, match="does not match the request's pinned protocol"):
        build_experiment_receipt(root=repo, request=request, protocol="other.json", execution_path="generated-output/frontier/native.json")
    receipt = build_experiment_receipt(root=repo, request=request, execution_path="generated-output/frontier/native.json")  # protocol defaults to the pinned file
    assert receipt["result"] == "inconclusive"


def test_pinned_file_without_declaration_is_refused(tmp_path):
    repo, request, out = syntheticRepo(tmp_path, {"protocolId": "unknown-protocol"})
    writeNative(out, request)
    with pytest.raises(ValueError, match="declares no experiment contract"):
        build(repo, request)


def test_validator_rejects_forged_result_and_experiment_id_from_pinned_protocol(tmp_path):
    repo, request, out = v1Receipt(tmp_path)
    receipt = build(repo, request)
    forged = dict(receipt, result="supported")
    assert any("not permitted by the pinned protocol result rule" in e for e in validate_experiment_receipt(forged, request, repo_root=repo))
    forged = dict(receipt, experimentId="other-experiment")
    assert any("experimentId does not match" in e for e in validate_experiment_receipt(forged, request, repo_root=repo))


def test_result_must_not_contradict_runner_recorded_result(tmp_path):
    repo, request, out = v1Receipt(tmp_path, resultRule={"statement": "Synthetic rule permitting every result.", "allowedResults": ["supported", "contradicted", "inconclusive", "execution_failed"]})
    (out / "target.txt").write_text("synthetic target output")
    writeNative(out, request, result="contradicted")
    with pytest.raises(ValueError, match="contradicts the runner artifact's recorded result"):
        build(repo, request, result="supported", target_path="generated-output/frontier/target.txt")
    assert build(repo, request, result="contradicted", target_path="generated-output/frontier/target.txt")["result"] == "contradicted"
    writeNative(out, request, result="inconclusive")
    with pytest.raises(ValueError, match="only a paired target artifact"):
        build(repo, request, result="supported")
    assert build(repo, request, result="supported", target_path="generated-output/frontier/target.txt")["result"] == "supported"


def test_version_capture_group_must_actually_capture(tmp_path):
    repo, request, out = v1Receipt(tmp_path, versionProbe={"field": "echoVersion", "pattern": r"echo( \S+)?", "label": "echo --version"})
    writeNative(out, request, echoVersion="echo")
    with pytest.raises(ValueError, match="recognizable echo --version"):
        build(repo, request)


def test_validator_refuses_symlink_aliases_and_unnormalized_output_paths(tmp_path):
    repo, request, out = v1Receipt(tmp_path, resultRule={"statement": "Synthetic rule permitting every result.", "allowedResults": ["supported", "contradicted", "inconclusive", "execution_failed"]})
    (out / "target.txt").write_text("synthetic target output")
    receipt = build(repo, request, result="inconclusive", target_path="generated-output/frontier/target.txt")
    assert validate_experiment_receipt(receipt, request, repo_root=repo) == []
    alias = copy.deepcopy(receipt)
    alias["outputs"][1]["path"] = "generated-output/frontier/./target.txt"
    assert any("not normalized" in e for e in validate_experiment_receipt(alias, request, repo_root=repo))
    (out / "target.txt").unlink()
    (out / "target.txt").symlink_to(out / "native.json")
    alias = copy.deepcopy(receipt)
    alias["outputs"][1]["contentDigest"] = alias["outputs"][0]["contentDigest"]
    errors = validate_experiment_receipt(alias, request, repo_root=repo)
    assert any("symlinks" in e for e in errors)


def test_request_builder_refuses_tracked_and_out_of_area_outputs(tmp_path, monkeypatch):
    repo, _, _ = syntheticRepo(tmp_path, syntheticProtocol())
    builder = loadScript("build_verification_request")
    monkeypatch.setattr(builder, "ROOT", repo)
    base = ["--lead", "lead.json", "--protocol", "protocol.json", "--fixture", "fixture.py"]
    for target in ("lead.json", "protocol.json", "registry/nodes/generic-history.json", "docs/x.json"):
        before = (repo / target).read_bytes() if (repo / target).exists() else None
        with pytest.raises(SystemExit):
            builder.main([*base, "--request-out", target])
        assert ((repo / target).read_bytes() if (repo / target).exists() else None) == before
    # a tracked file under an allowed prefix is also protected
    tracked = repo / "evidence/frontier-challenges/case/request.json"
    tracked.parent.mkdir(parents=True)
    tracked.write_text("{}")
    subprocess.run(["git", "-C", str(repo), "add", "."], check=True)
    with pytest.raises(SystemExit):
        builder.main([*base, "--request-out", "evidence/frontier-challenges/case/request.json"])
    assert tracked.read_text() == "{}"


def test_request_builder_refuses_protocol_with_no_declaration(tmp_path, monkeypatch):
    repo, _, _ = syntheticRepo(tmp_path, {"protocolId": "unknown-protocol"})
    builder = loadScript("build_verification_request")
    monkeypatch.setattr(builder, "ROOT", repo)
    with pytest.raises(SystemExit):
        builder.main(["--lead", "lead.json", "--protocol", "protocol.json", "--fixture", "fixture.py"])
