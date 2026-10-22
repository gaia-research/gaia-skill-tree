"""Lowercase-only named contributor identities across all intake surfaces (#2055).

All fixtures are synthetic tmp_path registries; nothing touches real registry data.
"""

import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from gaia_cli.commands.dev.build import meta_add_command
from gaia_cli.commands.dev.ratify import ratifyCommand
from gaia_cli.commands.dev.rename import meta_rename_command
from gaia_cli.commands.pushFromFile import build_from_file_batch
from gaia_cli.namedIdentity import findIdentityCollisions, identityKey, validateContributor
from gaia_cli.intakeAdapter import buildIntakeYaml
from test_intake_adapter import _basePacket
from test_dev_ratify import (
    _makeDeferredMappedPacket,
    _makeRatifyArgs,
    _makeRegistryDir,
)

pytestmark = [pytest.mark.integration]


@pytest.fixture(autouse=True)
def unitOnlyRatificationGates(monkeypatch):
    """Identity regressions isolate identity behavior; no test simulates production approval."""
    monkeypatch.setattr("gaia_cli.commands.dev.ratify.verifyFreshness", lambda *a, **k: [])
    monkeypatch.setattr("gaia_cli.commands.dev.ratify.verifyPacketAuthorization", lambda *a, **k: [])


def makeRegistry(tmp_path: Path) -> str:
    """Registry with one generic bucket the named skill can reference."""
    nodes = tmp_path / "registry" / "nodes" / "basic"
    nodes.mkdir(parents=True)
    (tmp_path / "registry" / "schema").mkdir()
    (tmp_path / "registry" / "schema" / "meta.json").write_text("{}")
    (nodes / "existing-generic.json").write_text(json.dumps({
        "id": "existing-generic", "name": "Existing Generic", "type": "basic", "level": "1★",
        "description": "An existing generic bucket for identity tests.", "status": "provisional",
        "prerequisites": [], "derivatives": [], "evidence": [], "timeline": [],
        "createdAt": "2026-06-01", "updatedAt": "2026-06-01", "version": "0.1.0",
    }))
    return str(tmp_path)


def writeNamed(root: str, contributor: str, slug: str) -> Path:
    path = Path(root) / "registry" / "named" / contributor / f"{slug}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        f"---\nid: {contributor}/{slug}\nname: Seed\ncontributor: {contributor}\norigin: false\n"
        "genericSkillRef: existing-generic\nstatus: named\nlevel: 2★\ntitle: Seed\n"
        "description: A seeded named skill for tests.\n---\n\nBody.\n",
        encoding="utf-8",
    )
    return path


def addArgs(root: str, contributor: str, skillId: str = "sample-skill", **overrides):
    base = dict(
        registry=root, name="Sample Skill", id=skillId, type="basic",
        description="A sufficiently long sample skill description.", named=True,
        contributor=contributor, generic_ref="existing-generic", status=None, title="sample-skill",
        level=None, extra_fields=None, no_build=True,
    )
    base.update(overrides)
    return SimpleNamespace(**base)


def namedFiles(root: str):
    named = Path(root) / "registry" / "named"
    return sorted(str(path.relative_to(named)) for path in named.glob("**/*.md")) if named.exists() else []


# ---------------------------------------------------------------------------
# gaia dev add
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("contributor", ["ExampleOwner", "Hikari9", "EXAMPLEOWNER"])
def test_add_rejects_mixed_case_without_normalizing(tmp_path, capsys, contributor):
    root = makeRegistry(tmp_path)
    with pytest.raises(SystemExit):
        meta_add_command(addArgs(root, contributor))
    assert f"expected '{contributor.lower()}'" in capsys.readouterr().err
    assert namedFiles(root) == []


def test_add_approved_hikari9_identity(tmp_path):
    root = makeRegistry(tmp_path)
    meta_add_command(addArgs(root, "hikari9", skillId="auto-office"))
    created = Path(root) / "registry" / "named" / "hikari9" / "auto-office.md"
    assert "id: hikari9/auto-office" in created.read_text()


def test_add_lowercase_contributor_unchanged(tmp_path):
    root = makeRegistry(tmp_path)
    meta_add_command(addArgs(root, "exampleowner"))
    assert namedFiles(root) == ["exampleowner/sample-skill.md"]


@pytest.mark.parametrize("existing,candidate", [
    ("ExampleOwner", "exampleowner"),
    ("EXAMPLEOWNER", "exampleowner"),
])
def test_add_rejects_case_variant_of_existing_identity(tmp_path, capsys, existing, candidate):
    root = makeRegistry(tmp_path)
    writeNamed(root, existing, "sample-skill")
    before = namedFiles(root)
    with pytest.raises(SystemExit) as exc:
        meta_add_command(addArgs(root, candidate))
    assert exc.value.code != 0
    err = capsys.readouterr().err
    assert "collides with an existing identity" in err
    assert f"{existing}/sample-skill" in err
    assert "never normalizes" in err
    assert namedFiles(root) == before


def test_add_rejects_second_spelling_of_contributor_directory(tmp_path, capsys):
    """Same GitHub account under a second directory spelling, different skill slug."""
    root = makeRegistry(tmp_path)
    writeNamed(root, "ExampleOwner", "first-skill")
    before = namedFiles(root)
    with pytest.raises(SystemExit):
        meta_add_command(addArgs(root, "exampleowner", skillId="second-skill"))
    assert "differs from 'exampleowner' only by case" in capsys.readouterr().err
    assert namedFiles(root) == before


def test_add_allows_new_slug_under_existing_exact_contributor_spelling(tmp_path):
    root = makeRegistry(tmp_path)
    writeNamed(root, "exampleowner", "first-skill")
    meta_add_command(addArgs(root, "exampleowner", skillId="second-skill"))
    assert namedFiles(root) == ["exampleowner/first-skill.md", "exampleowner/second-skill.md"]


def test_add_rejects_exact_duplicate(tmp_path, capsys):
    root = makeRegistry(tmp_path)
    writeNamed(root, "exampleowner", "sample-skill")
    with pytest.raises(SystemExit):
        meta_add_command(addArgs(root, "exampleowner"))
    assert "already exists" in capsys.readouterr().err


@pytest.mark.parametrize("contributor", ["bad name", "-leading", "has/slash", "", "naïve"])
def test_add_rejects_malformed_contributor(tmp_path, capsys, contributor):
    root = makeRegistry(tmp_path)
    with pytest.raises(SystemExit):
        meta_add_command(addArgs(root, contributor))
    assert namedFiles(root) == []


def test_add_slug_must_stay_lowercase(tmp_path, capsys):
    root = makeRegistry(tmp_path)
    with pytest.raises(SystemExit):
        meta_add_command(addArgs(root, "exampleowner", skillId="Sample_Skill"))
    assert "Named skill ID 'exampleowner/Sample_Skill' is invalid" in capsys.readouterr().err


# ---------------------------------------------------------------------------
# gaia dev ratify (same rule as add)
# ---------------------------------------------------------------------------


def ratify(tmp_path, contributor, skillName="sample-skill", seed=None):
    packet = _makeDeferredMappedPacket()
    packetPath = tmp_path / "packet.json"
    packetPath.write_text(json.dumps(packet), encoding="utf-8")
    registry = _makeRegistryDir(tmp_path)
    if seed:
        writeNamed(registry, *seed)
    args = _makeRatifyArgs(
        tmp_path, packet, packetPath, registry=registry, contributor=contributor, skill_name=skillName,
    )
    return ratifyCommand(args), packetPath


def test_ratify_records_lowercase_contributor_verbatim(tmp_path):
    rc, packetPath = ratify(tmp_path, "exampleowner")
    assert rc == 0
    named = json.loads(packetPath.read_text(encoding="utf-8"))["l4Resolution"]["named"]
    assert named["contributor"] == "exampleowner"


@pytest.mark.parametrize("seed", [("exampleowner", "sample-skill"), ("ExampleOwner", "sample-skill")])
def test_ratify_rejects_collision_and_leaves_packet_untouched(tmp_path, capsys, seed):
    packet = _makeDeferredMappedPacket()
    original = json.dumps(packet)
    packetPath = tmp_path / "packet.json"
    packetPath.write_text(original, encoding="utf-8")
    registry = _makeRegistryDir(tmp_path)
    writeNamed(registry, *seed)
    args = _makeRatifyArgs(tmp_path, packet, packetPath, registry=registry,
                           contributor="exampleowner", skill_name="sample-skill")
    assert ratifyCommand(args) == 1
    assert packetPath.read_text(encoding="utf-8") == original
    assert "collides with an existing named identity" in capsys.readouterr().err


@pytest.mark.parametrize("contributor", ["bad name", "has/slash", "", "-leading"])
def test_ratify_rejects_the_handles_add_rejects(tmp_path, contributor):
    rc, _ = ratify(tmp_path, contributor)
    assert rc == 1


# ---------------------------------------------------------------------------
# gaia dev rename (named)
# ---------------------------------------------------------------------------


def test_rename_accepts_lowercase_contributor_and_rejects_legacy_collisions(tmp_path, capsys):
    root = makeRegistry(tmp_path)
    writeNamed(root, "acme", "old-slug")
    writeNamed(root, "ExampleOwner", "taken")
    base = dict(registry=root, old_id="acme/old-slug", no_build=True)
    with pytest.raises(SystemExit):
        meta_rename_command(SimpleNamespace(new_id="exampleowner/taken", **base))
    assert "collides with an existing identity" in capsys.readouterr().err
    meta_rename_command(SimpleNamespace(new_id="newowner/new-slug", **base))
    assert (Path(root) / "registry" / "named" / "newowner" / "new-slug.md").exists()


# ---------------------------------------------------------------------------
# gaia push --from-file
# ---------------------------------------------------------------------------


def fromFileEntry(contributor):
    return {
        "id": "sample-skill", "name": "Sample Skill", "type": "basic",
        "description": "A sufficiently long sample skill description.", "prerequisites": [],
        "evidence": [{"grade": "C", "type": "repo", "url": "https://github.com/ExampleOwner/sample-skill"}],
        "named": {
            "contributor": contributor, "skill_name": "sample-skill",
            "links_github": "https://github.com/ExampleOwner/sample-skill/blob/main/SKILL.md",
        },
    }


def test_push_from_file_rejects_case_variant_of_canonical_named(tmp_path):
    root = _makeRegistryDir(tmp_path)
    writeNamed(root, "ExampleOwner", "sample-skill")
    batch, errors = build_from_file_batch([fromFileEntry("exampleowner")], {"gaiaUser": "t"}, root, "test/repo")
    assert batch is None
    assert any("collides with an existing canonical named implementation" in e for e in errors)


def test_push_from_file_accepts_lowercase_when_free(tmp_path):
    root = _makeRegistryDir(tmp_path)
    batch, errors = build_from_file_batch([fromFileEntry("exampleowner")], {"gaiaUser": "t"}, root, "test/repo")
    assert errors == []
    assert batch["proposedSkills"][0]["named"]["contributor"] == "exampleowner"


def test_push_from_file_rejects_malformed_contributor(tmp_path):
    root = _makeRegistryDir(tmp_path)
    batch, errors = build_from_file_batch([fromFileEntry("Example Owner")], {"gaiaUser": "t"}, root, "test/repo")
    assert batch is None
    assert any("named.contributor" in e for e in errors)


# ---------------------------------------------------------------------------
# shared helper
# ---------------------------------------------------------------------------


def test_identity_key_is_case_insensitive_but_inputs_are_untouched():
    assert identityKey("ExampleOwner", "x") == identityKey("exampleowner", "x")
    assert "expected 'exampleowner'" in validateContributor("ExampleOwner")
    assert validateContributor("example_owner-1") is None


def test_find_collisions_ignores_deliberate_rename_source(tmp_path):
    root = makeRegistry(tmp_path)
    writeNamed(root, "Acme", "x")
    assert findIdentityCollisions(root, "acme", "x")
    assert findIdentityCollisions(root, "acme", "x", ignoreIds=("Acme/x",)) == [
        "contributor directory 'Acme' already exists and differs from 'acme' only by case"
    ]


@pytest.mark.parametrize("contributor", ["ExampleOwner", "Hikari9", "EXAMPLEOWNER"])
def test_ratify_rejects_mixed_case_without_changing_packet(tmp_path, capsys, contributor):
    packet = _makeDeferredMappedPacket()
    packetPath = tmp_path / "packet.json"
    original = json.dumps(packet)
    packetPath.write_text(original)
    registry = _makeRegistryDir(tmp_path)
    args = _makeRatifyArgs(tmp_path, packet, packetPath, registry=registry,
                           contributor=contributor, skill_name="sample-skill")
    assert ratifyCommand(args) == 1
    assert f"expected '{contributor.lower()}'" in capsys.readouterr().err
    assert packetPath.read_text() == original


@pytest.mark.parametrize("contributor", ["ExampleOwner", "Hikari9", "EXAMPLEOWNER"])
def test_rename_rejects_mixed_case_without_normalizing(tmp_path, capsys, contributor):
    root = makeRegistry(tmp_path)
    original = writeNamed(root, "acme", "old-slug").read_bytes()
    args = SimpleNamespace(registry=root, old_id="acme/old-slug",
                           new_id=f"{contributor}/new-slug", no_build=True)
    with pytest.raises(SystemExit):
        meta_rename_command(args)
    assert f"expected '{contributor.lower()}'" in capsys.readouterr().err
    assert namedFiles(root) == ["acme/old-slug.md"]
    assert (Path(root) / "registry/named/acme/old-slug.md").read_bytes() == original


@pytest.mark.parametrize("contributor", ["ExampleOwner", "Hikari9", "EXAMPLEOWNER"])
def test_push_rejects_mixed_case_without_normalizing(tmp_path, contributor):
    root = _makeRegistryDir(tmp_path)
    entry = fromFileEntry(contributor)
    original = json.dumps(entry)
    batch, errors = build_from_file_batch([entry], {"gaiaUser": "t"}, root, "test/repo")
    assert batch is None
    assert any(f"expected '{contributor.lower()}'" in error for error in errors)
    assert json.dumps(entry) == original
    assert namedFiles(root) == []


@pytest.mark.parametrize("contributor", ["ExampleOwner", "Hikari9", "EXAMPLEOWNER", "bad name", "-leading", "has/slash", "", "naïve"])
def test_adapter_uses_same_contributor_validation(contributor):
    packet = _basePacket()
    packet["l4Resolution"]["named"]["contributor"] = contributor
    original = json.dumps(packet)
    with pytest.raises(ValueError, match="l4Resolution.named.contributor") as exc:
        buildIntakeYaml(packet)
    assert validateContributor(contributor) in str(exc.value)
    assert json.dumps(packet) == original


def test_adapter_preserves_approved_hikari9_identity():
    packet = _basePacket()
    packet["l4Resolution"]["named"] = {"contributor": "hikari9", "skillName": "auto-office"}
    assert buildIntakeYaml(packet)["skills"][0]["named"]["contributor"] == "hikari9"
