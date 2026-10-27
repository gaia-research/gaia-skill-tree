"""Adversarial caller-boundary regressions for the read-only corpus adapter."""
from argparse import Namespace
import json
from pathlib import Path

import pytest

from gaia_cli import shadowCorpus as sc


def seedRegistry(root: Path, *, unknownVerifier: bool = False) -> Path:
    nodes = root / "registry/nodes"
    named = root / "registry/named/author"
    nodes.mkdir(parents=True)
    named.mkdir(parents=True)
    (nodes / "sample.json").write_text(json.dumps({
        "id": "sample", "type": "basic", "prerequisites": [], "evidence": [],
    }))
    evidence = ([{"type": "verifier-attestation", "verifierId": "unknown-reviewer"}]
                if unknownVerifier else [])
    (named / "sample.md").write_text(
        "---\nid: author/sample\nstatus: named\nlevel: 2★\n"
        "genericSkillRef: sample\nevidence: " + json.dumps(evidence) + "\n---\n# Sample\n"
    )
    return root


def cliArgs(root: Path, *, strict: bool = True, status: str | None = None) -> Namespace:
    return Namespace(registry=str(root), evaluation_at="2026-10-25T00:00:00Z",
                     output_dir=None, stdout=False, json=True,
                     fail_closed=strict, filter_status=status)


@pytest.mark.parametrize("strict", [False, True])
def test_manifest_mismatch_invalidates_report_and_exit(tmp_path, monkeypatch, capsys, strict):
    root = seedRegistry(tmp_path / "repo")
    monkeypatch.setattr(sc, "verifyFileDigestManifest", lambda *a: (
        False, ["file-modified: registry/nodes/sample.json"]))
    assert sc.run_shadow_corpus_cli(cliArgs(root, strict=strict)) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["summary"]["manifestVerification"]["clean"] is False
    assert report["summary"]["overallStatus"] != "evaluated"


@pytest.mark.parametrize("strict", [False, True])
def test_empty_corpus_is_not_a_success(tmp_path, strict, capsys):
    assert sc.run_shadow_corpus_cli(cliArgs(tmp_path, strict=strict)) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["summary"]["targetSkillsCount"] == 0
    assert report["summary"]["overallStatus"] == "not-evaluated"


@pytest.mark.parametrize("status,expectedExit", [("named", 0), ("no-such-status", 1)])
def test_filter_scope_is_explicit_and_empty_selection_fails(tmp_path, status, expectedExit, capsys):
    root = seedRegistry(tmp_path / "repo")
    assert sc.run_shadow_corpus_cli(cliArgs(root, status=status)) == expectedExit
    report = json.loads(capsys.readouterr().out)
    scope = report["summary"]["evaluationScope"]
    assert scope["filterStatus"] == status
    assert scope["mode"] == "status-subset"
    assert scope["availableNamedRecords"] == 1
    assert scope["selectedNamedRecords"] == (1 if expectedExit == 0 else 0)
    assert "Evaluation Scope" in sc.formatImpactSummary(report)


@pytest.mark.parametrize("strict,expectedExit", [(False, 0), (True, 1)])
def test_unknown_verifier_is_observation_not_authority(tmp_path, strict, expectedExit, capsys):
    root = seedRegistry(tmp_path / "repo", unknownVerifier=True)
    assert sc.run_shadow_corpus_cli(cliArgs(root, strict=strict)) == expectedExit
    report = json.loads(capsys.readouterr().out)
    assert report["census"]["unknownVerifiers"][0]["verifier"] == "unknown-reviewer"
    assert report["metadata"]["publicationAuthorized"] is False
    # Strictness governs diagnostic uncertainty, not the scoring formula.
    assert report["summary"]["evaluatedCount"] == 1


@pytest.mark.parametrize("relativePath", [
    "registry/nodes/external.json", "registry/named/author/external.md",
    "registry/benchmark-sources.json", "registry/schema/meta.json",
])
@pytest.mark.parametrize("operation", ["manifest", "census", "cli"])
def test_input_symlinks_are_rejected_before_read(tmp_path, monkeypatch, relativePath, operation):
    root = seedRegistry(tmp_path / "repo")
    outside = tmp_path / "outside.txt"
    outside.write_text('{"id":"external","evidence":[]}')
    link = root / relativePath
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(outside)
    originalOpen = Path.open
    outsideReads = []

    def checkedOpen(path, *args, **kwargs):
        if path.resolve() == outside.resolve():
            outsideReads.append(str(path))
            raise AssertionError("External input bytes were read")
        return originalOpen(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", checkedOpen)
    if operation == "cli":
        assert sc.run_shadow_corpus_cli(cliArgs(root)) == 1
    else:
        action = sc.buildFileDigestManifest if operation == "manifest" else sc.censusRegistry
        with pytest.raises(ValueError, match="[Ss]ymlink"):
            action(root)
    assert outsideReads == []


@pytest.mark.parametrize("directory", [
    "registry", "registry/nodes", "registry/named", "registry/nodes/nested",
])
def test_symlinked_input_directory_is_rejected(tmp_path, directory):
    root = tmp_path / "repo"
    outside = tmp_path / "outside"
    outside.mkdir()
    link = root / directory
    link.parent.mkdir(parents=True)
    link.symlink_to(outside, target_is_directory=True)
    for action in [sc.buildFileDigestManifest, sc.censusRegistry]:
        with pytest.raises(ValueError, match="[Ss]ymlink"):
            action(root)


def test_strict_unknown_handling_does_not_change_scores(tmp_path):
    root = seedRegistry(tmp_path / "repo", unknownVerifier=True)
    advisory = sc.runShadowEvaluation(root, failClosed=False)
    strict = sc.runShadowEvaluation(root, failClosed=True)
    assert advisory["assessments"] == strict["assessments"]
    assert advisory["summary"]["diagnosticValid"] is True
    assert strict["summary"]["validationFindings"] == ["unknown-verifiers"]
