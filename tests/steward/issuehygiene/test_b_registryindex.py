from __future__ import annotations

import json
from pathlib import Path

from gaia_cli.steward.issuehygiene.registryindex import buildRegistryIndex, normalizeHandle, parseGithubUrl

LIVE_ROOT = Path(__file__).resolve().parents[3]


def writeNamed(root: Path, contributor: str, slug: str, text: str) -> Path:
    target = root / "registry" / "named" / contributor / f"{slug}.md"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(text, encoding="utf-8")
    return target


def skillText(identifier: str, status: str = "named", github: str = "", extra: str = "") -> str:
    contributor, slug = identifier.split("/")
    link = f"links:\n  github: {github}\n" if github else ""
    return f"---\nid: {identifier}\ncontributor: {contributor}\nstatus: {status}\n{link}{extra}---\n\n## Body\n"


def test_parse_github_url_normalizes_tree_query_and_case():
    ref = parseGithubUrl("https://github.com/Obra/Superpowers/tree/main/skills/x/?tab=1")
    assert ref is not None
    assert ref.repo == "obra/superpowers"
    assert ref.ref == "main"
    assert ref.path == "skills/x"
    assert ref.blobUrl() == "https://github.com/obra/superpowers/blob/main/skills/x"
    assert parseGithubUrl("https://example.com/obra/superpowers/blob/main/x") is None
    assert parseGithubUrl(None) is None


def test_handle_normalization_strips_case_dash_and_underscore():
    assert normalizeHandle("addy-osmani") == normalizeHandle("addyosmani") == "addyosmani"
    assert normalizeHandle("my_handle") == "myhandle"


def test_index_records_status_link_upstream_and_hash(tmp_path: Path):
    text = skillText(
        "garrytan/gbrain", github="https://github.com/garrytan/gbrain/blob/v1/README.md",
        extra="installable: false\nupstream:\n  repo: garrytan/gbrain\n  version: v1\n",
    )
    target = writeNamed(tmp_path, "garrytan", "gbrain", text)
    index = buildRegistryIndex(tmp_path)
    record = index.byId("garrytan/gbrain")
    assert record is not None
    assert record.status == "named"
    assert record.installable is False
    assert record.github is not None and record.github.path == "README.md"
    assert record.upstreamRepo == "garrytan/gbrain"
    assert record.upstreamVersion == "v1"
    assert record.path == "registry/named/garrytan/gbrain.md"
    assert record.sha256 == __import__("hashlib").sha256(target.read_bytes()).hexdigest()
    assert index.unreadable == ()


def test_unparsable_files_are_unreadable_not_silently_skipped(tmp_path: Path):
    writeNamed(tmp_path, "obra", "no-front", "just a body\n")
    writeNamed(tmp_path, "obra", "bad-yaml", "---\nid: [unclosed\n---\n")
    writeNamed(tmp_path, "obra", "wrong-id", skillText("obra/other"))
    writeNamed(tmp_path, "obra", "bad-upstream", skillText("obra/bad-upstream", extra="upstream: nope\n"))
    writeNamed(tmp_path, "obra", "ok", skillText("obra/ok"))
    index = buildRegistryIndex(tmp_path)
    reasons = {(entry.pathId, entry.reason) for entry in index.unreadable}
    assert ("obra/no-front", "no-frontmatter") in reasons
    assert ("obra/bad-yaml", "yaml-error") in reasons
    assert ("obra/wrong-id", "id-path-mismatch") in reasons
    assert ("obra/bad-upstream", "upstream-malformed") in reasons
    assert index.byId("obra/ok") is not None
    assert index.byId("obra/other") is None
    assert [entry.reason for entry in index.unreadableNear("obra/ok")] == []


def test_frontmatter_id_must_match_its_path(tmp_path: Path):
    writeNamed(tmp_path, "obra", "first", skillText("obra/same"))
    writeNamed(tmp_path, "obra", "second", skillText("obra/same"))
    index = buildRegistryIndex(tmp_path)
    assert index.byId("obra/same") is None
    assert sorted(entry.reason for entry in index.unreadable) == ["id-path-mismatch", "id-path-mismatch"]


def test_alias_candidates_and_unreadable_near_match(tmp_path: Path):
    writeNamed(tmp_path, "addy-osmani", "agent-skills", skillText("addy-osmani/agent-skills"))
    writeNamed(tmp_path, "garrytan", "agent-skills", skillText("garrytan/agent-skills"))
    writeNamed(tmp_path, "obra", "broken", "no frontmatter here")
    index = buildRegistryIndex(tmp_path)
    aliases = [record.id for record in index.aliasCandidates("addyosmani/agent-skills")]
    assert aliases == ["addy-osmani/agent-skills", "garrytan/agent-skills"]
    assert index.aliasCandidates("addy-osmani/agent-skills") == [index.byId("garrytan/agent-skills")]
    assert index.aliasCandidates("not-an-id") == []
    # an unreadable file with the same slug makes the alias pool unknown
    assert [entry.pathId for entry in index.unreadableNear("addyosmani/broken")] == ["obra/broken"]


def test_github_lookup_ignores_ref(tmp_path: Path):
    writeNamed(
        tmp_path, "obra", "writing-skills",
        skillText("obra/writing-skills", github="https://github.com/obra/superpowers/blob/v6.4.1/skills/writing-skills/SKILL.md"),
    )
    index = buildRegistryIndex(tmp_path)
    ref = parseGithubUrl("https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md")
    assert [record.id for record in index.byGithub(ref)] == ["obra/writing-skills"]
    assert index.byGithub(parseGithubUrl("https://github.com/obra/superpowers/blob/main/other.md")) == []


def test_nodes_are_indexed_and_bad_json_is_unreadable(tmp_path: Path):
    nodes = tmp_path / "registry" / "nodes" / "basic"
    nodes.mkdir(parents=True)
    (nodes / "good.json").write_text(json.dumps({"id": "good-node"}), encoding="utf-8")
    (nodes / "bad.json").write_text("{not json", encoding="utf-8")
    index = buildRegistryIndex(tmp_path)
    assert "good-node" in index.nodes
    assert [entry.reason for entry in index.unreadable] == ["json-error"]


def test_live_registry_indexes_without_unreadable_files():
    index = buildRegistryIndex(LIVE_ROOT)
    assert len(index.named) > 300
    assert index.unreadable == ()
    record = index.byId("garrytan/gbrain")
    assert record is not None and record.upstreamVersion is not None
