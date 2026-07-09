"""Unit tests for incremental push (`gaia push --update`, issue #611).

Covers the three pieces that make incremental push work without the CLI ever
becoming stateful:

* skill identity — ``identityKey`` (rename-stable) + ``fingerprint`` (edit-sensitive)
* the 4-way-minus-REMOVED classifier ``classify_against_pending``
* the issue-body identity block round-trip (``_render_identity_block`` /
  ``parse_identity_block`` / ``fetch_pending_identity``)

These are pure functions with no network or filesystem dependency, so this
module stays out of the slow/integration bucket in ``test_push.py``.
"""

import os
import sys

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(REPO_ROOT, "src"))

from gaia_cli.push import (  # noqa: E402
    attach_identity,
    classify_against_pending,
    skill_fingerprint,
    skill_identity_key,
)
from gaia_cli import prWriter  # noqa: E402
from gaia_cli.prWriter import (  # noqa: E402
    IDENTITY_BLOCK_BEGIN,
    IDENTITY_BLOCK_END,
    _render_identity_block,
    fetch_pending_identity,
    parse_identity_block,
)


def _skill(**over):
    base = {
        "id": "foo-bar",
        "name": "Foo Bar",
        "type": "basic",
        "description": "A skill.",
        "sourceRepo": "me/repo",
        "prerequisites": [],
    }
    base.update(over)
    return base


# ── identity: key is rename-stable, fingerprint is edit-sensitive ───────────


class TestIdentity:
    def test_identity_key_uses_ref_not_display_name(self):
        s = _skill()
        key = skill_identity_key(s, "me/repo")
        assert key == "me/repo::foo-bar"

    def test_rename_preserves_key_and_fingerprint(self):
        """A rename changes `name` only → same key, same fingerprint (not a change)."""
        original = attach_identity(_skill(), "me/repo")
        renamed = attach_identity(_skill(name="Completely Different"), "me/repo")
        assert renamed["identityKey"] == original["identityKey"]
        assert renamed["fingerprint"] == original["fingerprint"]

    def test_genericSkillRef_overrides_id_for_key(self):
        """When a genericSkillRef exists it keys on that, not the id."""
        s = _skill(id="local-slug", genericSkillRef="research")
        assert skill_identity_key(s, "me/repo") == "me/repo::research"

    def test_edit_description_changes_fingerprint_only(self):
        original = attach_identity(_skill(), "me/repo")
        edited = attach_identity(_skill(description="Now does more."), "me/repo")
        assert edited["identityKey"] == original["identityKey"]
        assert edited["fingerprint"] != original["fingerprint"]

    def test_edit_prerequisites_changes_fingerprint(self):
        a = skill_fingerprint(_skill(prerequisites=["x"]))
        b = skill_fingerprint(_skill(prerequisites=["x", "y"]))
        assert a != b

    def test_prerequisite_order_does_not_matter(self):
        """Prereqs are sorted before hashing so reordering is not a change."""
        a = skill_fingerprint(_skill(prerequisites=["a", "b"]))
        b = skill_fingerprint(_skill(prerequisites=["b", "a"]))
        assert a == b

    def test_fingerprint_is_16_hex_chars(self):
        fp = skill_fingerprint(_skill())
        assert len(fp) == 16
        int(fp, 16)  # parses as hex

    def test_attach_identity_returns_same_dict(self):
        s = _skill()
        assert attach_identity(s, "me/repo") is s
        assert "identityKey" in s and "fingerprint" in s


# ── classifier: NEW / CHANGED / UNCHANGED ───────────────────────────────────


class TestClassify:
    def test_new_when_key_unseen(self):
        s = attach_identity(_skill(id="brand-new"), "me/repo")
        new, changed, unchanged = classify_against_pending([s], {})
        assert new == [s] and not changed and not unchanged

    def test_unchanged_when_key_and_fingerprint_match(self):
        s = attach_identity(_skill(), "me/repo")
        pending = {s["identityKey"]: s["fingerprint"]}
        new, changed, unchanged = classify_against_pending([s], pending)
        assert unchanged == [s] and not new and not changed

    def test_changed_when_key_matches_but_fingerprint_differs(self):
        s = attach_identity(_skill(), "me/repo")
        pending = {s["identityKey"]: "stale00000000000"}
        new, changed, unchanged = classify_against_pending([s], pending)
        assert changed == [s] and not new and not unchanged

    def test_skill_without_identity_key_treated_as_new(self):
        """A pre-substrate batch entry must never be silently dropped."""
        s = _skill()  # no identityKey/fingerprint
        new, changed, unchanged = classify_against_pending([s], {"me/repo::foo-bar": "x"})
        assert new == [s]

    def test_mixed_batch(self):
        keep = attach_identity(_skill(id="new-one"), "me/repo")
        edited = attach_identity(_skill(id="edited"), "me/repo")
        same = attach_identity(_skill(id="same"), "me/repo")
        pending = {
            edited["identityKey"]: "old-fingerprint0",
            same["identityKey"]: same["fingerprint"],
        }
        new, changed, unchanged = classify_against_pending([keep, edited, same], pending)
        assert new == [keep]
        assert changed == [edited]
        assert unchanged == [same]


# ── issue-body identity block round-trip ────────────────────────────────────


class TestIdentityBlock:
    def test_render_wraps_in_hidden_html_comment(self):
        block = _render_identity_block("me/repo", [attach_identity(_skill(), "me/repo")])
        assert block.startswith(IDENTITY_BLOCK_BEGIN)
        assert IDENTITY_BLOCK_END in block

    def test_roundtrip_preserves_repo_and_skills(self):
        s1 = attach_identity(_skill(id="one"), "me/repo")
        s2 = attach_identity(_skill(id="two"), "me/repo")
        parsed = parse_identity_block(_render_identity_block("me/repo", [s1, s2]))
        assert parsed["sourceRepo"] == "me/repo"
        keys = {e["k"] for e in parsed["skills"]}
        assert keys == {s1["identityKey"], s2["identityKey"]}

    def test_render_skips_entries_missing_identity(self):
        parsed = parse_identity_block(_render_identity_block("me/repo", [_skill()]))
        assert parsed["skills"] == []

    def test_parse_returns_none_when_block_absent(self):
        assert parse_identity_block("## Just a normal issue body") is None

    def test_parse_returns_none_on_malformed_json(self):
        body = f"{IDENTITY_BLOCK_BEGIN} not-json {IDENTITY_BLOCK_END}"
        assert parse_identity_block(body) is None

    def test_parse_tolerates_surrounding_markdown(self):
        s = attach_identity(_skill(), "me/repo")
        body = "# Title\n\ntext\n\n" + _render_identity_block("me/repo", [s]) + "\nmore text"
        parsed = parse_identity_block(body)
        assert parsed is not None and parsed["sourceRepo"] == "me/repo"


# ── fetch_pending_identity: gh query aggregation + failure modes ─────────────


class _Result:
    def __init__(self, returncode=0, stdout="", stderr=""):
        self.returncode = returncode
        self.stdout = stdout
        self.stderr = stderr


class TestFetchPendingIdentity:
    def test_returns_not_ok_when_gh_not_ready(self, monkeypatch):
        monkeypatch.setattr(prWriter, "_gh_ready", lambda cwd: (False, "no gh"))
        identity, ok = fetch_pending_identity("me/repo")
        assert identity == {} and ok is False

    def test_returns_not_ok_on_gh_error(self, monkeypatch):
        monkeypatch.setattr(prWriter, "_gh_ready", lambda cwd: (True, ""))
        monkeypatch.setattr(prWriter, "_run", lambda cmd, cwd: _Result(returncode=1, stderr="boom"))
        identity, ok = fetch_pending_identity("me/repo")
        assert identity == {} and ok is False

    def test_aggregates_matching_repo_only(self, monkeypatch):
        s = attach_identity(_skill(id="wanted"), "me/repo")
        other = attach_identity(_skill(id="unwanted"), "other/repo")
        mine = _render_identity_block("me/repo", [s])
        theirs = _render_identity_block("other/repo", [other])
        payload = '[{"body": %s}, {"body": %s}]' % (
            __import__("json").dumps(f"body\n{mine}"),
            __import__("json").dumps(f"body\n{theirs}"),
        )
        monkeypatch.setattr(prWriter, "_gh_ready", lambda cwd: (True, ""))
        monkeypatch.setattr(prWriter, "_run", lambda cmd, cwd: _Result(stdout=payload))
        identity, ok = fetch_pending_identity("me/repo")
        assert ok is True
        assert identity == {s["identityKey"]: s["fingerprint"]}

    def test_ok_with_empty_map_when_no_pending(self, monkeypatch):
        monkeypatch.setattr(prWriter, "_gh_ready", lambda cwd: (True, ""))
        monkeypatch.setattr(prWriter, "_run", lambda cmd, cwd: _Result(stdout="[]"))
        identity, ok = fetch_pending_identity("me/repo")
        assert identity == {} and ok is True
