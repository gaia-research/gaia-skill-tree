import argparse
import hashlib
import json
import os
from pathlib import Path

import pytest

from scripts import install_parity
from scripts.installability import (
    assert_no_symlink_components,
    build_installability_projection,
    canonical_source_route,
    observation_digest,
    write_projection,
)


ROOT = Path(__file__).resolve().parents[1]


def _route(ref="main", subpath="SKILL.md", repo="source"):
    return canonical_source_route(
        f"https://github.com/alice/{repo}/blob/{ref}/{subpath}"
    )


def _fixture_repo(tmp_path, *, source=True, content="---\nname: Demo\n---\n\nbody\n"):
    root = tmp_path / "repo"
    skill_path = root / "registry" / "named" / "alice" / "demo.md"
    skill_path.parent.mkdir(parents=True)
    skill_path.write_text(content, encoding="utf-8")
    entry = {"id": "alice/demo", "links": {}}
    if source:
        entry["links"] = {"github": _route()["url"]}
    index = {
        "generatedAt": "2026-09-06",
        "buckets": {"2": [entry]},
        "awaitingClassification": [],
    }
    index_path = root / "docs" / "graph" / "named" / "index.json"
    index_path.parent.mkdir(parents=True)
    index_path.write_text(json.dumps(index), encoding="utf-8")
    return root, skill_path


def _observation(root, skill_path, *, health="materialized", route=None,
                 content_hash=None, cause=None, category="STANDARD",
                 checked_at="2026-09-06T18:00:00Z", run_id="run-1"):
    source_route = route if route is not None else (_route() if category != "NO_SOURCE" else None)
    skill_hash = content_hash or hashlib.sha256(skill_path.read_bytes()).hexdigest()
    document = {
        "schema": "gaia.installability-observation/v1",
        "checkedAt": checked_at,
        "runId": run_id,
        "registryCommit": None,
        "indexPath": "docs/graph/named/index.json",
        "scope": {
            "ids": ["alice/demo"],
            "only": ["alice/demo"],
            "contributors": [],
            "categories": [category],
            "limit": 0,
        },
        "toolVersion": "1",
        "gaiaVersion": "8.1.0",
        "npxVersion": "1.5.21",
        "gaiaCommand": ["python", "-m", "gaia_cli"],
        "timeoutSeconds": 60,
        "jobs": 1,
        "skills": [{
            "id": "alice/demo",
            "category": category,
            "sourceRoute": source_route,
            "resolvedRevision": "a" * 40 if source_route else None,
            "skillContentSha256": skill_hash,
            "deliveredContentSha256": "b" * 64 if health == "materialized" else None,
            "gaiaHealth": health,
            "comparator": {"dirname": "diff", "content": "diff"},
            "causeEvidence": {
                "classifiedCause": cause,
                "intrinsicCause": None,
                "exitCode": 1 if health == "failed" else 0,
                "stderrDigest": None,
                "stderrTail": None,
            },
        }],
    }
    path = root / "registry" / "installability" / "observations"
    path.mkdir(parents=True, exist_ok=True)
    (path / f"{observation_digest(document)}.json").write_text(
        json.dumps(document, indent=2) + "\n", encoding="utf-8"
    )
    return document


def test_no_source_refusal_is_pass_but_refused():
    result = install_parity.Result("alice/demo", install_parity.NO_SOURCE)
    install_parity.check_no_source(result, 1, "", "No source repository link")
    assert result.verdict == install_parity.PASS
    assert result.gaia_health == "refused"
    assert result.gaia_exit_code == 1


def test_gaia_health_is_independent_from_comparator_failure(tmp_path):
    gaia_root = tmp_path / "gaia-root"
    gaia_root.mkdir()
    (gaia_root / "SKILL.md").write_text("skill", encoding="utf-8")
    npx_root = tmp_path / "npx-root"
    npx_root.mkdir()
    (npx_root / "SKILL.md").write_text("different", encoding="utf-8")
    result = install_parity.Result("alice/demo", install_parity.STANDARD)
    resolved = install_parity.check_gaia_health(
        result, {"localPath": str(gaia_root), "id": "alice/demo"}
    )
    install_parity.compare_trees(result, resolved, str(npx_root))
    assert result.gaia_health == "materialized"
    assert result.comparator_content == "diff"
    assert result.verdict == install_parity.FAIL


def test_diagnostics_are_bounded_and_redacted():
    tail, digest = install_parity.sanitize_diagnostic(
        "fatal: https://alice:super-secret@example.com/x?token=abc "
        "Bearer ghp_verysecret\n" + "x" * 5000
    )
    assert tail is not None and len(tail) <= install_parity.MAX_STDERR_TAIL
    assert digest and len(digest) == 64
    assert "super-secret" not in tail
    assert "abc" not in tail
    assert "ghp_verysecret" not in tail


@pytest.mark.parametrize(
    "url,subpath,entrypoint",
    [
        (
            "https://github.com/alice/source/blob/main/health/SKILL.md",
            "health",
            "health/SKILL.md",
        ),
        (
            "https://github.com/alice/source/tree/main/health",
            "health",
            "health",
        ),
        ("https://github.com/alice/source", "", ""),
    ],
)
def test_shared_route_interpretation_preserves_entrypoint(url, subpath, entrypoint):
    route = canonical_source_route(url)
    assert route["subpath"] == subpath
    assert route["entrypoint"] == entrypoint
    assert route["installSubpath"] == subpath


def test_materialized_dirname_mismatch_projects_materializable(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    document = _observation(root, skill_path)
    projection = build_installability_projection(root)
    item = projection["skills"]["alice/demo"]
    assert item["state"] == "materializable"
    assert item["reason"] == "gaia-materialized"
    assert item["observationDigest"] == observation_digest(document)


def test_no_source_projects_negative_even_when_parity_would_pass(tmp_path):
    root, skill_path = _fixture_repo(tmp_path, source=False)
    _observation(root, skill_path, category="NO_SOURCE", health="refused")
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "not-materializable"
    assert item["reason"] == "no-source"


@pytest.mark.parametrize("cause", ["GIT_CLONE_FAILED", "GAIA_INSTALL_FAILED"])
def test_unclassified_install_failures_remain_unknown(tmp_path, cause):
    root, skill_path = _fixture_repo(tmp_path)
    _observation(root, skill_path, health="failed", cause=cause)
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "unknown"
    assert item["reason"] == "unclassified-install-failure" if cause == "GAIA_INSTALL_FAILED" else "inaccessible-at-check"


@pytest.mark.parametrize("cause,category", [("TIMEOUT", "STANDARD"), ("SUITE_COMPONENT_FAILED", "SUITE")])
def test_timeout_and_suite_failure_are_unknown(tmp_path, cause, category):
    root, skill_path = _fixture_repo(tmp_path)
    _observation(root, skill_path, health="failed", cause=cause, category=category)
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "unknown"


def test_route_and_content_changes_are_unknown(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    _observation(root, skill_path, route=_route(repo="old-source"))
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "unknown"
    assert item["reason"] == "route-changed"

    for path in (root / "registry" / "installability" / "observations").glob("*.json"):
        path.unlink()
    _observation(root, skill_path, content_hash="c" * 64)
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "unknown"
    assert item["reason"] == "subject-changed"


def test_conflicting_equally_current_observations_are_ambiguous(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    _observation(root, skill_path, health="materialized", run_id="a")
    _observation(root, skill_path, health="failed", cause="GAIA_INSTALL_FAILED", run_id="b")
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "unknown"
    assert item["reason"] == "ambiguous-observation"


def test_equal_time_provenance_and_comparator_conflicts_are_ambiguous(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    first = _observation(root, skill_path, run_id="a")
    obs_dir = root / "registry" / "installability" / "observations"
    (obs_dir / f"{observation_digest(first)}.json").unlink()
    second = json.loads(json.dumps(first))
    second["skills"][0]["resolvedRevision"] = "c" * 40
    second["skills"][0]["deliveredContentSha256"] = "d" * 64
    second["skills"][0]["comparator"] = {"dirname": "diff", "content": "diff"}
    second["gaiaVersion"] = "different"
    (obs_dir / f"{observation_digest(second)}.json").write_text(
        json.dumps(second), encoding="utf-8"
    )
    (obs_dir / f"{observation_digest(first)}.json").write_text(
        json.dumps(first), encoding="utf-8"
    )
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "unknown"
    assert item["reason"] == "ambiguous-observation"


def test_equal_time_diagnostic_digest_does_not_create_conflict(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    first = _observation(root, skill_path, run_id="a")
    obs_dir = root / "registry" / "installability" / "observations"
    (obs_dir / f"{observation_digest(first)}.json").unlink()
    second = json.loads(json.dumps(first))
    second["runId"] = "b"
    second["checkedAt"] = "2026-09-06T18:00:00+00:00"
    second["skills"][0]["causeEvidence"]["stderrDigest"] = "e" * 64
    second["skills"][0]["causeEvidence"]["stderrTail"] = "different per-run path"
    (obs_dir / f"{observation_digest(second)}.json").write_text(
        json.dumps(second), encoding="utf-8"
    )
    (obs_dir / f"{observation_digest(first)}.json").write_text(
        json.dumps(first), encoding="utf-8"
    )
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "materializable"
    assert item["reason"] == "gaia-materialized"


def test_intrinsic_pinned_content_evidence_is_the_only_failure_negative(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    document = _observation(root, skill_path, health="failed")
    original_digest = observation_digest(document)
    document["skills"][0]["causeEvidence"]["intrinsicCause"] = "NO_SKILL_MD"
    old = root / "registry" / "installability" / "observations" / f"{original_digest}.json"
    old.unlink()
    new_digest = observation_digest(document)
    (old.parent / f"{new_digest}.json").write_text(json.dumps(document), encoding="utf-8")
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "not-materializable"
    assert item["reason"] == "intrinsic-content-failure"


def test_out_of_scope_observation_does_not_add_a_skill(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    document = _observation(root, skill_path)
    document["skills"][0]["id"] = "other/not-in-tree"
    document["scope"]["ids"] = ["other/not-in-tree"]
    obs_dir = root / "registry" / "installability" / "observations"
    for path in obs_dir.glob("*.json"):
        path.unlink()
    (obs_dir / f"{observation_digest(document)}.json").write_text(json.dumps(document), encoding="utf-8")
    projection = build_installability_projection(root)
    assert list(projection["skills"]) == ["alice/demo"]
    assert projection["skills"]["alice/demo"]["reason"] == "not-observed"


def test_route_parser_disagreement_is_unknown(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    _observation(root, skill_path, route=canonical_source_route(
        _route()["url"], install_subpath="wrong-root"
    ))
    item = build_installability_projection(root)["skills"]["alice/demo"]
    assert item["state"] == "unknown"
    assert item["reason"] == "route-changed"


def test_malformed_filename_and_symlink_are_rejected(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    obs_dir = root / "registry" / "installability" / "observations"
    obs_dir.mkdir(parents=True)
    (obs_dir / "not-a-digest.json").write_text("{}", encoding="utf-8")
    with pytest.raises(ValueError, match="filename"):
        build_installability_projection(root)
    (obs_dir / "not-a-digest.json").unlink()
    target = tmp_path / "outside.json"
    target.write_text("{}", encoding="utf-8")
    os.symlink(target, obs_dir / ("a" * 64 + ".json"))
    with pytest.raises(ValueError, match="symlink"):
        build_installability_projection(root)


def test_named_parent_symlink_is_rejected_without_touching_target(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    target = outside / "sentinel"
    target.write_text("untouched", encoding="utf-8")
    named = root / "registry" / "named"
    skill_path.unlink()
    (named / "alice").rmdir()
    named.rmdir()
    os.symlink(outside, named)
    with pytest.raises(ValueError, match="symlink"):
        build_installability_projection(root)
    assert target.read_text(encoding="utf-8") == "untouched"


def test_projection_output_and_observation_destination_reject_symlink_parents(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    projection = build_installability_projection(root)
    outside = tmp_path / "outside"
    outside.mkdir()
    output_parent = root / "docs" / "graph" / "installability"
    output_parent.parent.mkdir(parents=True, exist_ok=True)
    os.symlink(outside, output_parent)
    with pytest.raises(ValueError, match="symlink"):
        write_projection(projection, output_parent / "index.json", anchor=root)
    assert not (outside / "index.json").exists()

    observation_parent = tmp_path / "observation-parent"
    observation_parent.mkdir()
    hostile = tmp_path / "hostile"
    hostile.mkdir()
    os.symlink(hostile, observation_parent / "nested")
    result = install_parity.Result("alice/demo", install_parity.STANDARD)
    result.source_route = _route()
    result.skill_content_sha256 = "a" * 64
    result.gaia_health = "materialized"
    result.gaia_exit_code = 0
    result.delivered_content_sha256 = "b" * 64
    args = argparse.Namespace(only=["alice/demo"], contributor=[], category=[], limit=0)
    cfg = argparse.Namespace(
        repo_root=str(ROOT), gaia_cmd=["python", "-m", "gaia_cli"], timeout=60, jobs=1
    )
    payload = install_parity.observation_payload(
        [result], cfg, args, "run", ROOT / "docs/graph/named/index.json", "1.5.21", "8.1.0",
        checked_at="2026-09-06T18:00:00Z",
    )
    with pytest.raises(ValueError, match="symlink"):
        install_parity.write_observation(str(observation_parent / "nested" / "obs.json"), payload)
    assert not (hostile / "obs.json").exists()
    assert_no_symlink_components(tmp_path / "safe" / "scratch.json")


def test_observation_temp_creation_is_exclusive_and_cleans_only_its_temp(tmp_path):
    result = install_parity.Result("alice/demo", install_parity.STANDARD)
    result.source_route = _route()
    result.skill_content_sha256 = "a" * 64
    result.gaia_health = "materialized"
    result.gaia_exit_code = 0
    result.delivered_content_sha256 = "b" * 64
    args = argparse.Namespace(only=["alice/demo"], contributor=[], category=[], limit=0)
    cfg = argparse.Namespace(
        repo_root=str(ROOT), gaia_cmd=["python", "-m", "gaia_cli"], timeout=60, jobs=1
    )
    payload = install_parity.observation_payload(
        [result], cfg, args, "run", ROOT / "docs/graph/named/index.json", "1.5.21", "8.1.0",
        checked_at="2026-09-06T18:00:00Z",
    )

    for suffix, plant in (("symlink", "symlink"), ("hardlink", "hardlink")):
        destination = tmp_path / suffix / "obs.json"
        destination.parent.mkdir()
        outside = tmp_path / f"{suffix}-target"
        outside.write_text("must remain unchanged", encoding="utf-8")
        old_temp = Path(f"{destination}.tmp.{os.getpid()}")
        if plant == "symlink":
            os.symlink(outside, old_temp)
        else:
            os.link(outside, old_temp)

        digest = install_parity.write_observation(str(destination), payload)
        assert destination.is_file()
        assert json.loads(destination.read_text(encoding="utf-8")) == payload
        assert outside.read_text(encoding="utf-8") == "must remain unchanged"
        assert old_temp.exists()
        assert digest == observation_digest(payload)


def test_projection_is_deterministic_and_validates_schema(tmp_path):
    root, skill_path = _fixture_repo(tmp_path)
    _observation(root, skill_path)
    first = build_installability_projection(root)
    second = build_installability_projection(root)
    assert json.dumps(first, sort_keys=True) == json.dumps(second, sort_keys=True)
    output = tmp_path / "docs" / "graph" / "installability" / "index.json"
    assert write_projection(first, output) is True
    assert write_projection(second, output) is False


def test_observation_payload_is_schema_valid(tmp_path):
    result = install_parity.Result("alice/demo", install_parity.STANDARD)
    result.source_route = _route()
    result.skill_content_sha256 = "a" * 64
    result.gaia_health = "materialized"
    result.gaia_exit_code = 0
    result.delivered_content_sha256 = "b" * 64
    args = argparse.Namespace(only=["alice/demo"], contributor=[], category=[], limit=0)
    cfg = argparse.Namespace(
        repo_root=str(ROOT), gaia_cmd=["python", "-m", "gaia_cli"], timeout=60, jobs=1
    )
    payload = install_parity.observation_payload(
        [result], cfg, args, "run", ROOT / "docs/graph/named/index.json", "1.5.21", "8.1.0",
        checked_at="2026-09-06T18:00:00Z",
    )
    install_parity.validate_observation_payload(payload)
