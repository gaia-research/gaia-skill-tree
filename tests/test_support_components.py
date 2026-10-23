"""Synthetic regression coverage for the isolated support-component lifecycle."""

import hashlib
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gaia_cli.impl import _replace_optional_registry_directory
from gaia_cli.install import list_available, load_manifest, resolve_named_skill_reference, save_manifest, uninstall_skill
from gaia_cli.scanner import scan_skill_mds
from gaia_cli.support import (
    _fetch_pinned_source,
    install_support_components,
    load_support_components,
    resolve_support_components,
    uninstall_target_support,
    validate_support_manifest,
)


COMMIT = "a" * 40
HASH = "b" * 64
LICENSE_TEXT = "MIT License\nCopyright Example Author\n"
LICENSE_HASH = hashlib.sha256(LICENSE_TEXT.encode("utf-8")).hexdigest()


def record(**changes):
    result = {
        "id": "synthetic-support",
        "name": "Synthetic support component",
        "distribution": "example/skills",
        "source": {
            "repository": "https://github.com/example/skills",
            "commit": COMMIT,
            "path": "skills/synthetic-support",
            "pinnedBlobUrl": f"https://github.com/example/skills/blob/{COMMIT}/skills/synthetic-support/SKILL.md",
            "skillSha256": HASH,
            "licensePath": "LICENSE",
            "licenseSha256": LICENSE_HASH,
        },
        "upstreamAuthor": "Example Author",
        "license": "MIT",
        "supports": ["example/target"],
    }
    result.update(changes)
    return result


def write_manifest(root: Path, components=None):
    registry = root / "registry"
    registry.mkdir(parents=True, exist_ok=True)
    components = [record()] if components is None else components
    (registry / "support").mkdir(exist_ok=True)
    (registry / "support" / "components.json").write_text(
        json.dumps({"schemaVersion": 1, "components": components}), encoding="utf-8"
    )
    named_entries = {
        target: {"id": target, "name": target.rsplit("/", 1)[-1]}
        for component in components
        for target in component.get("supports", [])
    }
    (registry / "named-skills.json").write_text(
        json.dumps({"buckets": {"named": list(named_entries.values())}, "awaitingClassification": []}),
        encoding="utf-8",
    )


def setup_target(root: Path):
    registry = root / "registry"
    registry.mkdir(exist_ok=True)
    (registry / "named-skills.json").write_text(
        json.dumps({"buckets": {"named": [{"id": "example/target", "name": "Target"}]}, "awaitingClassification": []}),
        encoding="utf-8",
    )


@pytest.mark.parametrize("location", ["local", "global"])
def test_support_installs_into_harness_skill_tree_with_idempotent_receipt(tmp_path, monkeypatch, location):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("gaia_cli.support.get_gaia_home", lambda: str(tmp_path / "home"))
    monkeypatch.setattr("gaia_cli.install.get_gaia_home", lambda: str(tmp_path / "home"))
    write_manifest(tmp_path)
    source_root = tmp_path / "source"
    payload = source_root / "skills" / "synthetic-support"
    payload.mkdir(parents=True)
    (payload / "SKILL.md").write_text("synthetic content\n", encoding="utf-8")
    (source_root / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
    monkeypatch.setattr("gaia_cli.support._fetch_pinned_source", lambda _record, _cache: (payload, source_root / "LICENSE"))

    assert install_support_components("example/target", str(tmp_path), location) is True
    receipt_path = (tmp_path / "home" / "support-install-manifest.json") if location == "global" else (tmp_path / ".gaia" / "support-install-manifest.json")
    first = json.loads(receipt_path.read_text(encoding="utf-8"))
    install_path = Path(first["installed"][0]["localPath"])
    assert install_path.parent == (tmp_path / ".agents" / "skills" if location == "local" else tmp_path / "home" / "skills")
    assert (install_path / "SKILL.md").read_text(encoding="utf-8") == "synthetic content\n"
    assert (install_path / "LICENSE").read_text(encoding="utf-8") == "MIT License\nCopyright Example Author\n"
    assert "synthetic-support" not in {skill_id for skill_id, _ in list_available(str(tmp_path))}
    assert all("synthetic-support" not in item["id"] for item in scan_skill_mds(root=str(tmp_path), extra_dirs=[]))
    assert "level" not in record() and "evidence" not in record() and "trustMagnitude" not in record()

    assert install_support_components("example/target", str(tmp_path), location) is True
    second = json.loads(receipt_path.read_text(encoding="utf-8"))
    assert len(second["installed"]) == 1
    assert second["installed"][0]["installedAt"] == first["installed"][0]["installedAt"]

    uninstall_target_support("example/target", location)
    assert not install_path.exists()
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["installed"] == []


def test_shared_support_payload_remains_until_last_target_is_uninstalled(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("gaia_cli.support.get_gaia_home", lambda: str(tmp_path / "home"))
    monkeypatch.setattr("gaia_cli.install.get_gaia_home", lambda: str(tmp_path / "home"))
    shared = record(supports=["example/target", "example/other"])
    write_manifest(tmp_path, [shared])
    payload = tmp_path / "source" / "synthetic-support"
    payload.mkdir(parents=True)
    (payload / "SKILL.md").write_text("synthetic content\\n", encoding="utf-8")
    (payload / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
    monkeypatch.setattr("gaia_cli.support._fetch_pinned_source", lambda _record, _cache: (payload, payload / "LICENSE"))

    assert install_support_components("example/target", str(tmp_path)) is True
    assert install_support_components("example/other", str(tmp_path)) is True
    receipt = tmp_path / ".gaia" / "support-install-manifest.json"
    installed = json.loads(receipt.read_text(encoding="utf-8"))["installed"][0]
    payload_path = Path(installed["localPath"])
    assert installed["targets"] == ["example/other", "example/target"]

    uninstall_target_support("example/target")
    assert (payload_path / "SKILL.md").is_file()
    assert json.loads(receipt.read_text(encoding="utf-8"))["installed"][0]["targets"] == ["example/other"]
    uninstall_target_support("example/other")
    assert not payload_path.exists()


def test_optional_fetched_support_directory_replaces_and_clears_stale_data(tmp_path):
    source = tmp_path / "release" / "registry" / "support"
    destination = tmp_path / "project" / "registry" / "support"
    source.mkdir(parents=True)
    (source / "components.json").write_text("new", encoding="utf-8")
    destination.mkdir(parents=True)
    (destination / "components.json").write_text("stale", encoding="utf-8")

    _replace_optional_registry_directory(source, destination)
    assert (destination / "components.json").read_text(encoding="utf-8") == "new"
    _replace_optional_registry_directory(source.parent / "missing", destination)
    assert not destination.exists()


def test_manifest_support_targets_must_exist_in_canonical_named_catalog(tmp_path):
    write_manifest(tmp_path)
    (tmp_path / "registry" / "named-skills.json").write_text(
        json.dumps({"buckets": {"named": []}, "awaitingClassification": []}), encoding="utf-8"
    )
    with pytest.raises(ValueError, match="not in the canonical named catalog"):
        load_support_components(str(tmp_path))


def test_legacy_registry_without_manifest_is_compatible_and_not_a_skill(tmp_path):
    setup_target(tmp_path)
    assert load_support_components(str(tmp_path)) == []
    assert resolve_support_components("example/target", str(tmp_path)) == []
    assert "synthetic-support" not in {skill_id for skill_id, _ in list_available(str(tmp_path))}


def test_support_data_stays_out_of_graph_named_tm_and_acquisition_views(tmp_path):
    write_manifest(tmp_path)
    graph_path = tmp_path / "registry" / "gaia.json"
    graph_path.write_text(json.dumps({"skills": [{"id": "example/target"}], "edges": []}), encoding="utf-8")

    named_ids = {
        item["id"]
        for entries in json.loads((tmp_path / "registry" / "named-skills.json").read_text())["buckets"].values()
        for item in entries
    }
    graph_ids = {item["id"] for item in json.loads(graph_path.read_text())["skills"]}
    assert "synthetic-support" not in named_ids
    assert "synthetic-support" not in graph_ids
    assert "synthetic-support" not in {skill_id for skill_id, _ in list_available(str(tmp_path))}
    assert "level" not in record() and "evidence" not in record() and "trustMagnitude" not in record()


def test_support_payload_is_not_discovered_by_capability_scan(tmp_path):
    payload = tmp_path / ".agents" / "skills" / "synthetic-support"
    payload.mkdir(parents=True)
    (payload / "SKILL.md").write_text(
        "---\\nname: synthetic-support\\ndescription: Synthetic component\\n---\\n",
        encoding="utf-8",
    )
    (payload / ".gaia-support-component").write_text("support-only\\n", encoding="utf-8")
    found = scan_skill_mds(root=str(tmp_path), extra_dirs=[])
    assert all("synthetic-support" not in item["id"] for item in found)
    assert resolve_named_skill_reference("synthetic-support", str(tmp_path)) == (None, None)


def test_pinned_fetch_verifies_skill_and_root_license_hashes(tmp_path, monkeypatch):
    source_dir = tmp_path / "cache" / "example" / f"skills-{COMMIT}"
    (source_dir / ".git").mkdir(parents=True)
    skill_dir = source_dir / "skills" / "synthetic-support"
    skill_dir.mkdir(parents=True)
    (skill_dir / "SKILL.md").write_text("pinned skill", encoding="utf-8")
    license_file = source_dir / "LICENSE"
    license_file.write_text(LICENSE_TEXT, encoding="utf-8")
    monkeypatch.setattr(
        "gaia_cli.support.subprocess.run",
        lambda *_args, **_kwargs: SimpleNamespace(returncode=0, stdout=COMMIT),
    )
    pinned = record()
    pinned["source"]["skillSha256"] = hashlib.sha256(b"pinned skill").hexdigest()

    result = _fetch_pinned_source(pinned, tmp_path / "cache")
    assert result == (skill_dir, license_file)

    pinned["source"]["licenseSha256"] = "0" * 64
    assert _fetch_pinned_source(pinned, tmp_path / "cache") is None


def test_support_schema_rejects_ranked_skill_fields_and_unapproved_shape(tmp_path):
    data = {"schemaVersion": 1, "components": [record(level="3★")]}
    assert any("Additional properties are not allowed" in error for error in validate_support_manifest(data))
    data = {"schemaVersion": 1, "components": [record(source={**record()["source"], "commit": "main"})]}
    assert validate_support_manifest(data)
    data = {"schemaVersion": 1, "components": [record(), record()]}
    assert any("duplicate support component id" in error for error in validate_support_manifest(data))
    assert any("distribution" in error for error in validate_support_manifest({"schemaVersion": 1, "components": [record(distribution="other/repo")]}))
    altered_source = {**record()["source"], "pinnedBlobUrl": "https://github.com/example/skills/blob/main/SKILL.md"}
    assert any("pinnedBlobUrl" in error for error in validate_support_manifest({"schemaVersion": 1, "components": [record(source=altered_source)]}))
    assert any("canonical named catalog" in error for error in validate_support_manifest({"schemaVersion": 1, "components": [record()]}, named_ids={"elsewhere/skill"}))


def test_invalid_manifest_fails_install_cleanly(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    (tmp_path / "registry" / "support").mkdir(parents=True)
    (tmp_path / "registry" / "support" / "components.json").write_text("{bad json", encoding="utf-8")
    assert install_support_components("example/target", str(tmp_path)) is False
    assert "could not resolve support components" in capsys.readouterr().err


@pytest.mark.parametrize("collision_kind", ["file", "directory", "dangling_symlink"])
@pytest.mark.parametrize("sibling", ["staging", "backup"])
def test_install_refuses_preexisting_staging_and_backup_paths(tmp_path, monkeypatch, capsys, collision_kind, sibling):
    monkeypatch.chdir(tmp_path)
    write_manifest(tmp_path)
    payload = tmp_path / "source" / "synthetic-support"
    payload.mkdir(parents=True)
    (payload / "SKILL.md").write_text("new payload\n", encoding="utf-8")
    (payload / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
    monkeypatch.setattr("gaia_cli.support._fetch_pinned_source", lambda *_args: (payload, payload / "LICENSE"))

    skill_root = tmp_path / ".agents" / "skills"
    destination = skill_root / "synthetic-support"
    if sibling == "backup":
        destination.mkdir(parents=True)
        (destination / "SKILL.md").write_text("old payload\n", encoding="utf-8")
        (destination / ".gaia-support-component").write_text("support-only\n", encoding="utf-8")
        receipt_path = tmp_path / ".gaia" / "support-install-manifest.json"
        receipt_path.parent.mkdir(parents=True)
        receipt_path.write_text(json.dumps({"installed": [{
            "id": "synthetic-support", "commit": "c" * 40,
            "localPath": str(destination.resolve()), "targets": [],
        }]}), encoding="utf-8")
    collision = skill_root / (
        "synthetic-support.gaia-support-tmp" if sibling == "staging"
        else "synthetic-support.gaia-support-backup"
    )
    collision.parent.mkdir(parents=True, exist_ok=True)
    if collision_kind == "file":
        collision.write_text("do not touch\n", encoding="utf-8")
    elif collision_kind == "directory":
        collision.mkdir()
        (collision / "sentinel").write_text("do not touch\n", encoding="utf-8")
    else:
        collision.symlink_to(collision.parent / "missing-target")

    assert install_support_components("example/target", str(tmp_path)) is False
    assert os.path.lexists(collision)
    if collision_kind == "file":
        assert collision.read_text(encoding="utf-8") == "do not touch\n"
    elif collision_kind == "directory":
        assert (collision / "sentinel").read_text(encoding="utf-8") == "do not touch\n"
    else:
        assert collision.is_symlink() and not collision.exists()
    if sibling == "staging":
        assert not destination.exists()
    else:
        assert (destination / "SKILL.md").read_text(encoding="utf-8") == "old payload\n"
        assert (destination / ".gaia-support-component").is_file()
    assert "existing staging or backup path" in capsys.readouterr().err


def test_receipt_write_failure_rolls_back_new_support_payload(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    write_manifest(tmp_path)
    payload = tmp_path / "source" / "synthetic-support"
    payload.mkdir(parents=True)
    (payload / "SKILL.md").write_text("support payload\\n", encoding="utf-8")
    (payload / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
    monkeypatch.setattr("gaia_cli.support._fetch_pinned_source", lambda _record, _cache: (payload, payload / "LICENSE"))
    monkeypatch.setattr("gaia_cli.support._write_receipts", lambda *_args: (_ for _ in ()).throw(OSError("read-only")))

    assert install_support_components("example/target", str(tmp_path)) is False
    assert not (tmp_path / ".agents" / "skills" / "synthetic-support").exists()
    assert "could not write support install receipt" in capsys.readouterr().err


def test_install_skill_companions_declared_support_after_named_target(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("gaia_cli.support.get_gaia_home", lambda: str(tmp_path / "home"))
    monkeypatch.setattr("gaia_cli.install.get_gaia_home", lambda: str(tmp_path / "home"))
    write_manifest(tmp_path)
    payload = tmp_path / "source" / "synthetic-support"
    payload.mkdir(parents=True)
    (payload / "SKILL.md").write_text("support payload\\n", encoding="utf-8")
    (payload / "LICENSE").write_text(LICENSE_TEXT, encoding="utf-8")
    monkeypatch.setattr("gaia_cli.support._fetch_pinned_source", lambda _record, _cache: (payload, payload / "LICENSE"))
    monkeypatch.setattr("gaia_cli.install.resolve_named_skill_reference", lambda *_args: ("example/target", {"links": {}}))
    monkeypatch.setattr("gaia_cli.install._install_single", lambda *_args, **_kwargs: True)

    from gaia_cli.install import install_skill
    assert install_skill("example/target", str(tmp_path)) is True
    assert (tmp_path / ".agents" / "skills" / "synthetic-support" / "SKILL.md").is_file()


def test_support_install_failure_is_reported_without_receipt(tmp_path, monkeypatch, capsys):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("gaia_cli.support.get_gaia_home", lambda: str(tmp_path / "home"))
    write_manifest(tmp_path)
    monkeypatch.setattr("gaia_cli.support._fetch_pinned_source", lambda *_args: None)
    assert install_support_components("example/target", str(tmp_path)) is False
    assert "support component install failed" in capsys.readouterr().err
    assert json.loads((tmp_path / ".gaia" / "support-install-manifest.json").read_text())["installed"] == []


def test_named_uninstall_releases_only_its_support_reference(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr("gaia_cli.support.get_gaia_home", lambda: str(tmp_path / "home"))
    monkeypatch.setattr("gaia_cli.install.get_gaia_home", lambda: str(tmp_path / "home"))
    target = tmp_path / ".agents" / "skills" / "synthetic-support"
    target.mkdir(parents=True)
    (target / "SKILL.md").write_text("payload", encoding="utf-8")
    (target / ".gaia-support-component").write_text("support-only\\n", encoding="utf-8")
    receipts = {"installed": [{"id": "synthetic-support", "localPath": str(target.resolve()), "targets": ["example/target"]}]}
    receipt_path = tmp_path / ".gaia" / "support-install-manifest.json"
    receipt_path.parent.mkdir(parents=True, exist_ok=True)
    receipt_path.write_text(json.dumps(receipts), encoding="utf-8")
    named = tmp_path / ".agents" / "skills" / "target"
    named.parent.mkdir(parents=True, exist_ok=True)
    named.write_text("mock", encoding="utf-8")
    save_manifest({"installed": [{"id": "example/target", "localPath": str(named)}]})

    assert uninstall_skill("example/target") is True
    assert not target.exists()
    assert json.loads(receipt_path.read_text(encoding="utf-8"))["installed"] == []
