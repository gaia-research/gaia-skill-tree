"""Tests for the share-bundle producer (`gaia share`) and the guided
bundle-install consumer (`gaia install <bundle>`) — Issue #128 (CLI half).

NOTE: like test_install.py, these tests drive install resolution through
named-skills.json (pure JSON, no YAML), and mock _run_git so no network or
real clone happens.
"""

import json
import os
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from gaia_cli.share import (
    BUNDLE_KIND,
    BUNDLE_VERSION,
    _looks_like_bundle_ref,
    _normalize_github_url,
    build_share_bundle,
    install_bundle,
    load_bundle,
    render_bundle_tree,
    render_bundle_tree_lines,
    write_bundle,
)
from gaia_cli.install import load_manifest


# ─── fixtures ───────────────────────────────────────────────────────────────


def _write_registry(tmp_path, canonical_skills, named_entries):
    """Write registry/gaia.json and registry/named-skills.json."""
    registry = tmp_path / "registry"
    registry.mkdir(parents=True, exist_ok=True)
    (registry / "gaia.json").write_text(
        json.dumps({"version": "9.9.9", "skills": canonical_skills}),
        encoding="utf-8",
    )
    buckets: dict = {}
    for meta in named_entries:
        ref = meta.get("genericSkillRef", meta["id"].replace("/", "-"))
        buckets.setdefault(ref, []).append(meta)
    (registry / "named-skills.json").write_text(
        json.dumps({"buckets": buckets, "awaitingClassification": []}),
        encoding="utf-8",
    )


def _write_tree(tmp_path, username, unlocked):
    tree_dir = tmp_path / "skill-trees" / username
    tree_dir.mkdir(parents=True, exist_ok=True)
    (tree_dir / "skill-tree.json").write_text(
        json.dumps(
            {
                "userId": username,
                "updatedAt": "2026-06-10",
                "unlockedSkills": unlocked,
                "stats": {"totalUnlocked": len(unlocked)},
            }
        ),
        encoding="utf-8",
    )


def _basic_world(tmp_path, username="alice"):
    """A two-skill tree where b depends on a (canonical prereq edge)."""
    _write_registry(
        tmp_path,
        canonical_skills=[
            {"id": "feat-a", "name": "Feature A", "type": "basic", "level": "2★", "prerequisites": []},
            {"id": "feat-b", "name": "Feature B", "type": "extra", "level": "3★", "prerequisites": ["feat-a"]},
        ],
        named_entries=[
            {
                "id": "alice/skill-a",
                "name": "Skill A",
                "genericSkillRef": "feat-a",
                "level": "2★",
                "type": "basic",
                "links": {"github": "https://github.com/alice/repo/blob/main/skill-a/SKILL.md"},
            },
            {
                "id": "alice/skill-b",
                "name": "Skill B",
                "genericSkillRef": "feat-b",
                "level": "3★",
                "type": "extra",
                "links": {"github": "https://github.com/alice/repo/blob/main/skill-b/SKILL.md"},
            },
        ],
    )
    _write_tree(
        tmp_path,
        username,
        [
            {"skillId": "alice/skill-a", "level": "2★"},
            {"skillId": "alice/skill-b", "level": "3★"},
        ],
    )


# ─── producer ─────────────────────────────────────────────────────────────────


class TestBundleProducer:
    def test_build_bundle_shape_and_roundtrip(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _basic_world(tmp_path)

        bundle = build_share_bundle("alice", str(tmp_path))
        assert bundle["kind"] == BUNDLE_KIND
        assert bundle["bundleVersion"] == BUNDLE_VERSION
        assert bundle["sharer"] == "alice"
        assert len(bundle["skillMeta"]) == 2
        assert len(bundle["install"]) == 2

        # Round-trip through disk.
        path = write_bundle(bundle, str(tmp_path / "out" / "alice.json"))
        loaded = load_bundle(path)
        assert loaded == bundle

    def test_prereq_edges_translated_to_owned_named_ids(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _basic_world(tmp_path)

        bundle = build_share_bundle("alice", str(tmp_path))
        # feat-b depends on feat-a; alice owns both under named ids → edge b→a.
        assert bundle["skillMeta"]["alice/skill-b"]["prereqs"] == ["alice/skill-a"]
        assert bundle["skillMeta"]["alice/skill-a"]["prereqs"] == []

    def test_install_manifest_carries_blob_url(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _basic_world(tmp_path)

        bundle = build_share_bundle("alice", str(tmp_path))
        entry = next(e for e in bundle["install"] if e["id"] == "alice/skill-a")
        assert entry["github"].endswith("/blob/main/skill-a/SKILL.md")
        assert entry["level"] == "2★"

    def test_starless_skill_is_preview_only(self, tmp_path, monkeypatch):
        """A canonical skill with no named implementation appears in the preview
        but never in the install manifest (it has no installable source)."""
        monkeypatch.chdir(tmp_path)
        _write_registry(
            tmp_path,
            canonical_skills=[
                {"id": "starless-thing", "name": "Starless", "type": "basic", "level": "0★", "prerequisites": []},
            ],
            named_entries=[],
        )
        _write_tree(tmp_path, "bob", [{"skillId": "starless-thing", "level": "1★"}])

        bundle = build_share_bundle("bob", str(tmp_path))
        assert "starless-thing" in bundle["skillMeta"]
        assert bundle["install"] == []

    def test_tree_url_normalized_to_blob(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_registry(
            tmp_path,
            canonical_skills=[{"id": "x", "name": "X", "type": "basic", "level": "1★", "prerequisites": []}],
            named_entries=[
                {
                    "id": "carol/x",
                    "name": "X",
                    "genericSkillRef": "x",
                    "level": "1★",
                    "type": "basic",
                    # tree/ directory-view URL — must be converted to blob/
                    "links": {"github": "https://github.com/carol/repo/tree/main/x"},
                }
            ],
        )
        _write_tree(tmp_path, "carol", [{"skillId": "carol/x", "level": "1★"}])

        bundle = build_share_bundle("carol", str(tmp_path))
        assert bundle["install"][0]["github"] == "https://github.com/carol/repo/blob/main/x"

    def test_missing_tree_raises(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _write_registry(tmp_path, [], [])
        try:
            build_share_bundle("nobody", str(tmp_path))
            assert False, "expected ValueError"
        except ValueError:
            pass


# ─── detection + loading ────────────────────────────────────────────────────


class TestBundleDetectionAndLoad:
    def test_looks_like_bundle_ref(self):
        assert _looks_like_bundle_ref("/tmp/x.json")
        assert _looks_like_bundle_ref("https://example.com/x.json")
        assert _looks_like_bundle_ref("http://example.com/share")
        assert not _looks_like_bundle_ref("alice/skill-a")
        assert not _looks_like_bundle_ref("unique-skill")
        assert not _looks_like_bundle_ref("")

    def test_normalize_github_url(self):
        assert _normalize_github_url("https://github.com/o/r/tree/main/p") == (
            "https://github.com/o/r/blob/main/p"
        )
        assert _normalize_github_url("https://github.com/o/r/blob/main/p") == (
            "https://github.com/o/r/blob/main/p"
        )
        assert _normalize_github_url(None) is None

    def test_load_bundle_rejects_non_bundle_json(self, tmp_path):
        p = tmp_path / "notabundle.json"
        p.write_text(json.dumps({"hello": "world"}), encoding="utf-8")
        try:
            load_bundle(str(p))
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "share bundle" in str(exc)

    def test_load_bundle_missing_file(self, tmp_path):
        try:
            load_bundle(str(tmp_path / "nope.json"))
            assert False, "expected ValueError"
        except ValueError as exc:
            assert "not found" in str(exc)


# ─── preview renderer ─────────────────────────────────────────────────────────


class TestBundlePreview:
    def test_render_nests_prereqs_under_dependent(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _basic_world(tmp_path)
        bundle = build_share_bundle("alice", str(tmp_path))

        text = render_bundle_tree(bundle)
        assert "alice" in text.splitlines()[0]
        # skill-b is the root (nothing depends on it); skill-a is its child.
        lines = render_bundle_tree_lines(bundle)
        b_idx = next(i for i, l in enumerate(lines) if "alice/skill-b" in l)
        a_idx = next(i for i, l in enumerate(lines) if "alice/skill-a" in l)
        assert b_idx < a_idx, "dependent should render before its prerequisite"
        # The child line is indented relative to the root.
        assert lines[a_idx].startswith((" ", "│", "└", "├")) or "    " in lines[a_idx]


# ─── consumer install flow ─────────────────────────────────────────────────────


def _mock_git(monkeypatch, tmp_path):
    """Mock git clone + cache dir so install runs offline."""
    def mock_run_git(args, cwd=None):
        if args and args[0] == "clone":
            os.makedirs(args[-1], exist_ok=True)
        return True

    monkeypatch.setattr("gaia_cli.install._run_git", mock_run_git)
    monkeypatch.setattr(
        "gaia_cli.install.get_global_cache_dir",
        lambda: str(tmp_path / ".gaia" / "skills"),
    )


class TestBundleInstallFlow:
    def test_view_only_installs_nothing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _basic_world(tmp_path)
        bundle = build_share_bundle("alice", str(tmp_path))
        path = write_bundle(bundle, str(tmp_path / "b.json"))

        out = install_bundle(path, str(tmp_path), auto="view", out=lambda *a: None)
        assert out["installed"] == []
        assert set(out["skipped"]) == {"alice/skill-a", "alice/skill-b"}

    def test_quit_installs_nothing(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _basic_world(tmp_path)
        bundle = build_share_bundle("alice", str(tmp_path))
        out = install_bundle(bundle, str(tmp_path), auto="quit", out=lambda *a: None)
        assert out["installed"] == []

    def test_all_installs_via_registry_resolution(self, tmp_path, monkeypatch):
        """When the consumer registry knows the skills, install reuses the
        registry resolution path (install_skill)."""
        monkeypatch.chdir(tmp_path)
        _basic_world(tmp_path)
        _mock_git(monkeypatch, tmp_path)

        bundle = build_share_bundle("alice", str(tmp_path))
        out = install_bundle(bundle, str(tmp_path), auto="all", out=lambda *a: None)

        assert set(out["installed"]) == {"alice/skill-a", "alice/skill-b"}
        assert out["unresolved"] == [] and out["failed"] == []
        manifest = load_manifest()
        assert {e["id"] for e in manifest["installed"]} == {"alice/skill-a", "alice/skill-b"}

    def test_multi_repo_foreign_install_uses_bundle_urls(self, tmp_path, monkeypatch):
        """A bundle spanning repos the consumer's registry does NOT contain
        installs each skill directly from its own source URL."""
        monkeypatch.chdir(tmp_path)
        # Consumer registry is empty → no resolution; must use bundle URLs.
        _write_registry(tmp_path, [], [])
        _mock_git(monkeypatch, tmp_path)

        bundle = {
            "kind": BUNDLE_KIND,
            "bundleVersion": BUNDLE_VERSION,
            "sharer": "dan",
            "skillMeta": {
                "dan/one": {"name": "One", "level": "2★", "type": "basic", "named": True, "prereqs": []},
                "erin/two": {"name": "Two", "level": "3★", "type": "extra", "named": True, "prereqs": []},
            },
            "install": [
                {"id": "dan/one", "name": "One", "level": "2★", "type": "basic",
                 "github": "https://github.com/dan/repo-one/blob/main/one/SKILL.md"},
                {"id": "erin/two", "name": "Two", "level": "3★", "type": "extra",
                 "github": "https://github.com/erin/repo-two/blob/main/two/SKILL.md"},
            ],
        }
        out = install_bundle(bundle, str(tmp_path), auto="all", out=lambda *a: None)

        assert set(out["installed"]) == {"dan/one", "erin/two"}
        manifest = load_manifest()
        repos = {e["repoUrl"] for e in manifest["installed"]}
        assert repos == {
            "https://github.com/dan/repo-one.git",
            "https://github.com/erin/repo-two.git",
        }

    def test_pick_installs_only_chosen(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        _basic_world(tmp_path)
        _mock_git(monkeypatch, tmp_path)
        bundle = build_share_bundle("alice", str(tmp_path))

        # Pick only the first listed skill.
        fake_inputs = iter(["1"])
        out = install_bundle(
            bundle,
            str(tmp_path),
            auto="pick",
            input_fn=lambda *a: next(fake_inputs),
            out=lambda *a: None,
        )
        assert len(out["installed"]) == 1
        assert len(out["skipped"]) == 1

    def test_unresolvable_entry_reported(self, tmp_path, monkeypatch):
        """A chosen entry with neither a registry match nor a github URL is
        reported as unresolved, not silently dropped."""
        monkeypatch.chdir(tmp_path)
        _write_registry(tmp_path, [], [])
        bundle = {
            "kind": BUNDLE_KIND,
            "bundleVersion": BUNDLE_VERSION,
            "sharer": "z",
            "skillMeta": {"z/ghost": {"name": "Ghost", "level": "1★", "type": "basic", "named": True, "prereqs": []}},
            "install": [{"id": "z/ghost", "name": "Ghost", "level": "1★", "type": "basic"}],
        }
        out = install_bundle(bundle, str(tmp_path), auto="all", out=lambda *a: None)
        assert out["unresolved"] == ["z/ghost"]
        assert out["installed"] == []
