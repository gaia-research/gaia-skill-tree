"""Canonical ratify -> multi-packet push -> intake validation regressions (#2088)."""

import copy
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from gaia_cli.commands.dev.ratify import ratifyCommand
from gaia_cli.commands.pushFromFile import _load_yaml_file, build_from_file_batch, push_from_file_command
from gaia_cli.intakeAdapter import _canonicalDigest, buildIntakeYaml, validateL4Resolution
from gaia_cli.prefill import _importPacketValidator, buildGenericSnapshot, selfValidatePacket
from scripts.validate_intake import validate_intake
from test_dev_ratify import _makeAssessmentReceipt, _makeDeferredMappedPacket, _makeRatifyArgs, _makeRegistryDir

SCHEMA = Path(__file__).resolve().parents[1] / "registry/schema/skillBatch.schema.json"


def ratifiedPacket(tmp_path, target="other-skill", candidate="test/candidate", skillName="candidate", options=None, decision="MAP"):
    packet = _makeDeferredMappedPacket(candidate_id=candidate, mapping_options=options)
    packetPath = tmp_path / f"{skillName}.json"
    packetPath.write_text(json.dumps(packet), encoding="utf-8")
    registry = _makeRegistryDir(tmp_path)
    assessment = _makeAssessmentReceipt(packet, tmp_path, filename=f"{skillName}-assessment.json", registryPath=registry)
    args = _makeRatifyArgs(
        tmp_path, packet, packetPath, generic_id=target, registry=registry, assessment=assessment,
        decision=decision,
        generic_name="Shared Capability" if decision == "NEW_GENERIC" else None,
        generic_description="An identical generic capability definition." if decision == "NEW_GENERIC" else None,
        generic_type="basic" if decision == "NEW_GENERIC" else None,
        skill_name=skillName, skill_file_url=None,
    )
    assert ratifyCommand(args) == 0
    return json.loads(packetPath.read_text(encoding="utf-8")), args.registry


@pytest.mark.parametrize("options", [None, []])
def test_ratify_outside_shortlist_preserves_retrieval(tmp_path, options):
    original = _makeDeferredMappedPacket(mapping_options=options)
    packet, registry = ratifiedPacket(tmp_path, options=options)
    assert packet["mappingOptions"] == original["mappingOptions"]
    assert packet["genericSnapshot"] == original["genericSnapshot"]
    assert packet["l4Resolution"]["humanReview"]["humanOverride"] is True
    trusted = buildGenericSnapshot(registry)["generics"]
    assert selfValidatePacket(packet, trustedGenerics=trusted) == []
    intake = buildIntakeYaml(packet, requireHumanReview=True, trustedGenerics=trusted)
    assert intake["skills"][0]["mapsToGeneric"] == "other-skill"


@pytest.mark.parametrize("mutation", [
    "no-review", "no-override", "string-override", "worker-decision", "no-digest",
    "no-reviewer", "no-approval", "no-reason", "no-attestation", "no-assessment-path",
    "unknown-target", "stale-catalog", "no-trusted-catalog", "stale-retrieval", "vector",
])
def test_outside_shortlist_fails_closed(tmp_path, mutation):
    packet, registry = ratifiedPacket(tmp_path)
    trusted = buildGenericSnapshot(registry)["generics"]
    hr = packet["l4Resolution"]["humanReview"]
    if mutation == "no-review":
        del packet["l4Resolution"]["humanReview"]
    elif mutation == "no-override":
        hr["humanOverride"] = False
    elif mutation == "string-override":
        hr["humanOverride"] = "true"
    elif mutation == "worker-decision":
        packet["decision"]["reasonCode"] = "MAP_EXISTING_GENERIC"
    elif mutation.startswith("no-") and mutation not in ("no-trusted-catalog",):
        field = {"no-digest": "assessmentReceiptDigest", "no-reviewer": "reviewedBy",
                 "no-approval": "approvalRef", "no-reason": "rationale",
                 "no-attestation": "attestation", "no-assessment-path": "assessmentPath"}[mutation]
        del hr[field]
    elif mutation == "unknown-target":
        packet["decision"]["genericId"] = "unknown"
        packet["l4Resolution"]["generic"]["id"] = "unknown"
    elif mutation == "stale-catalog":
        trusted = trusted[:-1]
    elif mutation == "no-trusted-catalog":
        trusted = None
    elif mutation == "stale-retrieval":
        packet["retrieval"] = {"allowStale": True}
    elif mutation == "vector":
        packet["retrieval"] = {"vectorSource": "manual"}
    assert validateL4Resolution(packet, requireHumanReview=True, trustedGenerics=trusted)
    # The standalone mirrored packet validator must also fail closed.
    assert _importPacketValidator()(packet, trusted_generics=trusted)


@pytest.mark.parametrize("mutation", ["ack", "reviewer", "approval", "reason", "assessment", "target", "snapshot", "retrieval", "vector"])
def test_ratify_override_failure_never_writes(tmp_path, mutation):
    packet = _makeDeferredMappedPacket()
    path = tmp_path / "candidate.json"
    args = _makeRatifyArgs(tmp_path, packet, path, generic_id="other-skill",
                           generic_name=None, generic_description=None, generic_type=None)
    if mutation == "ack":
        args.acknowledge_human_review = False
    elif mutation == "reviewer":
        args.reviewed_by = ""
    elif mutation == "approval":
        args.approval_ref = ""
    elif mutation == "reason":
        args.reason = ""
    elif mutation == "assessment":
        packet["source"]["contentSha256"] = "f" * 64
    elif mutation == "target":
        args.generic_id = "unknown"
    elif mutation == "snapshot":
        packet["genericSnapshot"]["contentSha256"] = "f" * 64
    elif mutation == "retrieval":
        packet["retrieval"] = {"allowStale": True}
    elif mutation == "vector":
        packet["retrieval"] = {"vectorSource": "manual"}
    original = json.dumps(packet)
    path.write_text(original, encoding="utf-8")
    assert ratifyCommand(args) == 1
    assert path.read_text(encoding="utf-8") == original


def writeManifest(root, packets):
    directory = root / "registry-for-review/discovery-packets"
    directory.mkdir(parents=True, exist_ok=True)
    paths = []
    for index, packet in enumerate(packets):
        relative = f"registry-for-review/discovery-packets/{index}.json"
        (root / relative).write_text(json.dumps(packet), encoding="utf-8")
        paths.append(relative)
    manifest = root / "manifest.yml"
    manifest.write_text(json.dumps({"contractVersion": "discovery-packet-manifest-v1", "packetPaths": paths}), encoding="utf-8")
    return manifest, paths


def test_manifest_canonical_end_to_end(tmp_path, monkeypatch, capsys):
    first, registry = ratifiedPacket(tmp_path, skillName="first")
    second, _ = ratifiedPacket(tmp_path, candidate="test/second", skillName="second")
    root = Path(registry)
    manifest, paths = writeManifest(root, [first, second])
    monkeypatch.chdir(root)
    # The actual adapter is imported lazily; spy on its canonical entrypoint.
    with patch("gaia_cli.intakeAdapter.buildIntakeYaml", wraps=buildIntakeYaml) as adapter:
        data, error = _load_yaml_file(str(manifest))
        assert error is None
        assert adapter.call_count == 2
        assert all(call.kwargs["requireHumanReview"] is True for call in adapter.call_args_list)
    assert len(data["skills"]) == 2
    refs = data["curationHandoff"]["packetRefs"]
    for ref, packet, relative in zip(refs, [first, second], paths):
        assert ref == {
            "candidateId": packet["candidateId"], "packetPath": relative,
            "packetContentSha256": _canonicalDigest(packet),
            "sourceContentSha256": packet["source"]["contentSha256"],
        }
    batch, errors = build_from_file_batch(data["skills"], {"gaiaUser": "tester"}, ".", "test/repo",
                                         curationHandoff=data["curationHandoff"])
    assert errors == []
    batches = root / "registry-for-review/skill-batches"
    batches.mkdir()
    (batches / "batch.json").write_text(json.dumps(batch), encoding="utf-8")
    errors, warnings, count = validate_intake(str(batches.parent), str(root / "registry/gaia.json"), str(SCHEMA))
    assert errors == []
    assert count == 1
    assert len(warnings) == 2
    args = SimpleNamespace(fromFile=str(manifest), dry_run=True, yes=True, no_issue=True)
    with patch("gaia_cli.scanner.load_config", return_value={"gaiaUser": "tester"}), patch(
        "gaia_cli.push.write_skill_batch"
    ) as writer, patch("gaia_cli.prWriter.open_intake_issue") as opener:
        assert push_from_file_command(args) == 0
        writer.assert_not_called()
        opener.assert_not_called()
    output = capsys.readouterr().out
    assert "Dry run — batch JSON" in output
    assert all(path in output for path in paths)


@pytest.mark.parametrize("secondDecision", ["MAP", "NEW_GENERIC"])
def test_manifest_mixed_or_shared_new_generic_packets(tmp_path, monkeypatch, secondDecision):
    first, registry = ratifiedPacket(tmp_path, target="new-capability", skillName="first", decision="NEW_GENERIC")
    second, _ = ratifiedPacket(tmp_path, candidate="test/second", skillName="second",
                               target="new-capability" if secondDecision == "NEW_GENERIC" else "test-skill",
                               decision=secondDecision)
    root = Path(registry)
    manifest, _ = writeManifest(root, [first, second])
    monkeypatch.chdir(root)
    data, error = _load_yaml_file(str(manifest))
    assert error is None
    batch, errors = build_from_file_batch(data["skills"], {"gaiaUser": "tester"}, ".", "test/repo",
                                         curationHandoff=data["curationHandoff"])
    assert errors == []
    directory = writeBatch(root, "mixed", batch["proposedSkills"])
    errors, warnings, _ = validate_intake(str(directory), str(root / "registry/gaia.json"), str(SCHEMA))
    assert errors == []
    assert len(warnings) == (1 if secondDecision == "MAP" else 0)


@pytest.mark.parametrize("mutation", ["missing-review", "deferred", "duplicate-candidate", "bad-json", "plain-yaml", "missing-file"])
def test_manifest_rejects_bad_member_atomically(tmp_path, monkeypatch, mutation):
    first, registry = ratifiedPacket(tmp_path, skillName="first")
    second = copy.deepcopy(first)
    second["candidateId"] = "test/second"
    second["l4Resolution"]["named"]["skillName"] = "second"
    # Portable receipt path avoids deliberately reusing the first candidate's receipt.
    second["l4Resolution"]["humanReview"]["assessmentPath"] = str(tmp_path / "unavailable.json")
    if mutation == "missing-review":
        del second["l4Resolution"]["humanReview"]
    elif mutation == "deferred":
        second["decision"]["value"] = "DEFER"
    elif mutation == "duplicate-candidate":
        second["candidateId"] = first["candidateId"]
    root = Path(registry)
    manifest, paths = writeManifest(root, [first, second])
    if mutation == "bad-json":
        (root / paths[1]).write_text("[broken", encoding="utf-8")
    elif mutation == "plain-yaml":
        (root / paths[1]).write_text("skills: []", encoding="utf-8")
    elif mutation == "missing-file":
        (root / paths[1]).unlink()
    monkeypatch.chdir(root)
    data, error = _load_yaml_file(str(manifest))
    assert data is None
    assert error
    args = SimpleNamespace(fromFile=str(manifest), dry_run=False, yes=True, no_issue=False)
    with patch("gaia_cli.scanner.load_config", return_value={"gaiaUser": "tester"}), patch(
        "gaia_cli.push.write_skill_batch"
    ) as writer, patch("gaia_cli.prWriter.open_intake_issue") as opener:
        assert push_from_file_command(args) == 1
        writer.assert_not_called()
        opener.assert_not_called()


@pytest.mark.parametrize("paths", [[], "not-a-list", [None], ["/tmp/packet.json"], ["https://example.com/packet.json"],
    ["registry-for-review/elsewhere.json"], ["registry-for-review/discovery-packets/../elsewhere.json"],
    ["registry-for-review/discovery-packets/./file.json"], ["registry-for-review/discovery-packets\\file.json"]])
def test_manifest_paths_are_bounded(tmp_path, monkeypatch, paths):
    monkeypatch.chdir(tmp_path)
    manifest = tmp_path / "manifest.yml"
    manifest.write_text(json.dumps({"contractVersion": "discovery-packet-manifest-v1", "packetPaths": paths}), encoding="utf-8")
    data, error = _load_yaml_file(str(manifest))
    assert data is None
    assert error


@pytest.mark.parametrize("escape", [False, True])
def test_manifest_rejects_duplicate_paths_and_symlink_escape(tmp_path, monkeypatch, escape):
    packet, registry = ratifiedPacket(tmp_path)
    root = Path(registry)
    manifest, paths = writeManifest(root, [packet])
    link = root / "registry-for-review/discovery-packets/link.json"
    link.symlink_to(tmp_path / "candidate.json" if escape else root / paths[0])
    manifest.write_text(json.dumps({"contractVersion": "discovery-packet-manifest-v1",
                                   "packetPaths": paths + [str(link.relative_to(root))]}), encoding="utf-8")
    monkeypatch.chdir(root)
    data, error = _load_yaml_file(str(manifest))
    assert data is None
    assert "escapes" in error if escape else "Duplicate" in error


def proposedRow(skillName, generic="new-capability"):
    return {
        "id": generic, "name": "Shared capability", "description": "An identical generic definition.",
        "type": "basic", "prerequisites": [], "sourceRepo": "test/repo", "candidateId": f"test/{skillName}",
        "named": {"contributor": "test", "skill_name": skillName, "links_github": f"https://github.com/test/{skillName}/blob/main/SKILL.md"},
        "evidence": [{"grade": "C", "type": "repo", "url": f"https://github.com/test/{skillName}"}],
    }


def writeBatch(root, name, proposals):
    directory = root / "registry-for-review/skill-batches"
    directory.mkdir(parents=True, exist_ok=True)
    batch = {"batchId": name, "userId": "tester", "sourceRepo": "test/repo", "generatedAt": "2026-10-13T00:00:00Z",
             "knownSkills": [], "proposedSkills": proposals, "similarity": []}
    (directory / f"{name}.json").write_text(json.dumps(batch), encoding="utf-8")
    return directory.parent


@pytest.mark.parametrize("generic", ["new-capability", "test-skill"])
def test_repeated_generic_with_distinct_named_candidates_is_valid(tmp_path, generic):
    registry = Path(_makeRegistryDir(tmp_path))
    directory = writeBatch(registry, "one", [proposedRow("first", generic), proposedRow("second", generic)])
    errors, warnings, _ = validate_intake(str(directory), str(registry / "registry/gaia.json"), str(SCHEMA))
    assert errors == []
    assert len(warnings) == (2 if generic == "test-skill" else 0)
    if generic == "test-skill":
        errors, warnings, _ = validate_intake(str(directory), str(registry / "registry/gaia.json"), str(SCHEMA), strict=True)
        assert len(errors) == 2
        assert warnings == []


@pytest.mark.parametrize("mutation", ["name", "description", "type", "prerequisites", "mapping", "named", "candidate", "missing-candidate", "missing-named"])
def test_repeated_generic_invalid_fanout_rejected_in_validator_and_push(tmp_path, mutation):
    first, second = proposedRow("first"), proposedRow("second")
    if mutation in ("name", "description"):
        second[mutation] = "Different generic definition"
    elif mutation == "type":
        second["type"] = "fusion"
    elif mutation == "prerequisites":
        second["prerequisites"] = ["test-skill"]
    elif mutation == "mapping":
        second["mapsToGeneric"] = "test-skill"
    elif mutation == "named":
        second["named"]["skill_name"] = "first"
    elif mutation == "candidate":
        second["candidateId"] = first["candidateId"]
    elif mutation == "missing-candidate":
        del second["candidateId"]
    elif mutation == "missing-named":
        del second["named"]["skill_name"]
    registry = Path(_makeRegistryDir(tmp_path))
    directory = writeBatch(registry, "one", [first, second])
    errors, _, _ = validate_intake(str(directory), str(registry / "registry/gaia.json"), str(SCHEMA))
    assert errors
    batch, errors = build_from_file_batch([first, second], {"gaiaUser": "tester"}, str(registry), "test/repo")
    assert batch is None
    assert errors


def test_duplicate_named_identity_across_different_generic_ids_rejected(tmp_path):
    registry = Path(_makeRegistryDir(tmp_path))
    directory = writeBatch(registry, "one", [proposedRow("first"), proposedRow("first", "other-capability")])
    errors, _, _ = validate_intake(str(directory), str(registry / "registry/gaia.json"), str(SCHEMA))
    assert any("Duplicate named identity" in error for error in errors)


@pytest.mark.parametrize("generic", ["new-capability", "test-skill"])
def test_duplicate_generic_across_batches_only_warns_when_canonical(tmp_path, generic):
    registry = Path(_makeRegistryDir(tmp_path))
    directory = writeBatch(registry, "one", [proposedRow("first", generic)])
    writeBatch(registry, "two", [proposedRow("second", generic)])
    errors, warnings, _ = validate_intake(str(directory), str(registry / "registry/gaia.json"), str(SCHEMA))
    if generic == "new-capability":
        assert any("Duplicate proposed skill" in error for error in errors)
    else:
        assert errors == []
        assert len(warnings) == 2


def test_duplicate_named_identity_across_batches_rejected(tmp_path):
    registry = Path(_makeRegistryDir(tmp_path))
    directory = writeBatch(registry, "one", [proposedRow("first", "test-skill")])
    writeBatch(registry, "two", [proposedRow("first", "other-skill")])
    errors, _, _ = validate_intake(str(directory), str(registry / "registry/gaia.json"), str(SCHEMA))
    assert any("Duplicate named identity" in error for error in errors)


def test_manifest_packet_count_is_bounded(tmp_path, monkeypatch):
    from gaia_cli.commands.pushFromFile import MAX_MANIFEST_PACKETS

    monkeypatch.chdir(tmp_path)
    paths = [f"registry-for-review/discovery-packets/{i}.json" for i in range(MAX_MANIFEST_PACKETS + 1)]
    manifest = tmp_path / "manifest.yml"
    manifest.write_text(json.dumps({"contractVersion": "discovery-packet-manifest-v1", "packetPaths": paths}),
                        encoding="utf-8")
    data, error = _load_yaml_file(str(manifest))
    assert data is None
    assert "bounded maximum" in error


def test_repeated_generic_similarity_hints_are_not_duplicated(tmp_path):
    registry = Path(_makeRegistryDir(tmp_path, skills=[
        {"id": "new-capability-tool", "name": "New Capability Tool", "type": "basic", "prerequisites": []},
    ]))
    rows = [proposedRow("first"), proposedRow("second"), proposedRow("third")]
    batch, errors = build_from_file_batch(rows, {"gaiaUser": "tester"}, str(registry), "test/repo")
    assert errors == []
    assert len(batch["proposedSkills"]) == 3
    pairs = [(link["sourceSkillId"], link["targetSkillId"]) for link in batch["similarity"]]
    assert pairs, "fixture must exercise the similarity path"
    assert len(pairs) == len(set(pairs))


def test_intake_issue_disambiguates_repeated_generic_rows():
    from gaia_cli.prWriter import _build_intake_issue_title, build_intake_issue_body

    shared = {"batchId": "b", "userId": "tester", "sourceRepo": "test/repo", "fromFile": True,
              "knownSkills": [], "similarity": [],
              "proposedSkills": [proposedRow("first"), proposedRow("second")]}
    body = build_intake_issue_body(shared)
    assert "| 1 | `new-capability` (`test/first`) |" in body
    assert "| 2 | `new-capability` (`test/second`) |" in body
    assert _build_intake_issue_title(shared) == "[intake] 2 skills: new-capability"
    distinct = dict(shared, proposedSkills=[proposedRow("first", "alpha-skill"), proposedRow("second", "beta-skill")])
    body = build_intake_issue_body(distinct)
    assert "| 1 | `alpha-skill` |" in body and "(`test/first`)" not in body.split("### Skill details")[0]
