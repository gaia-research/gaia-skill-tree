"""#2131 round-4 verifier FAIL: the shared approval rules (M1, M2, L3, L5, L9).

M1. Bootstrap-by-absence is gone. An index with no authorised Verifier is a denial, whatever its rows say.
    Star levels are normalised (int 4, '4', '4★' are all 4-star), so an index that stores levels as numbers
    is not read as having no Verifiers.
M2. The allowlist needs the sender's user type. The bot logins (github-actions[bot] and codex, jules,
    claude-bot, gemini-bot, github-actions) are trusted only for a Bot with that exact login; mbtiongson1 only
    for a User with the known id. A human account called 'codex' is not trusted.
    C9 M-1 supersedes the old suffix rule: a name merely ending in '[bot]' (dependabot[bot]) is NOT trusted.
L3. One definition of the payload block regex, imported by every consumer (approval, batch, records and the
    workflows). A parity test fails if any copy reappears.
L5. The skip-child-gate label is honoured only when its most recent labeling was by an authorised actor.
L9. Verifier handles match case-insensitively.
"""

from __future__ import annotations

import json
import pathlib

import pytest

from scripts.upstream_watcher import approval, batch, markers, records
from scripts.upstream_watcher.approval import allowlisted, skip_label_authorized, verifier_status

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
WORKFLOWS = REPO_ROOT / ".github" / "workflows"


def _index(tmp_path, data):
    path = tmp_path / "named-skills.json"
    path.write_text(data if isinstance(data, str) else json.dumps(data), encoding="utf-8")
    return str(path)


def _entry(contributor, level):
    return {"contributor": contributor, "level": level}


# ---------------------------------------------------------------------------
# M1: no bootstrap, deny with no Verifier, normalised levels
# ---------------------------------------------------------------------------


def test_an_index_with_only_three_star_rows_denies_everyone(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("bob", "3★")]}})
    for actor in ("bob", "mallory", None):
        assert verifier_status(index, actor) == "no", actor


def test_the_bootstrap_outcome_no_longer_exists(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("bob", "2★")]}})
    assert "bootstrap" not in {verifier_status(index, "mallory"), verifier_status(index, None)}


@pytest.mark.parametrize("level", [4, "4", "4★", "4 ★", "★★★★"])
def test_every_spelling_of_four_star_counts_as_a_verifier(tmp_path, level):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", level)]}})
    assert verifier_status(index, "alice") == "yes"


@pytest.mark.parametrize("level", [3, "3", "3★", "★★★"])
def test_three_star_in_any_spelling_is_not_a_verifier(tmp_path, level):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", level)]}})
    assert verifier_status(index, "alice") == "no"


def test_an_integer_level_index_is_not_read_as_having_no_verifiers(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", 4), _entry("bob", 2)]}})
    assert verifier_status(index, "alice") == "yes"
    assert verifier_status(index, "mallory") == "no"


def test_missing_unparseable_or_empty_index_is_a_denial(tmp_path):
    assert verifier_status(str(tmp_path / "absent.json"), "alice").startswith("deny-")
    assert verifier_status(_index(tmp_path, "{not json"), "alice").startswith("deny-")
    assert verifier_status(_index(tmp_path, {"buckets": {}}), "alice").startswith("deny-")


# ---------------------------------------------------------------------------
# L9: case-insensitive handles
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("handle", ["Alice", "ALICE", "alice"])
def test_verifier_handles_match_case_insensitively(tmp_path, handle):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", "4★")]}})
    assert verifier_status(index, handle) == "yes"


def test_a_different_handle_is_still_refused(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", "4★")]}})
    assert verifier_status(index, "alicia") == "no"


# ---------------------------------------------------------------------------
# M2: the allowlist needs the sender type (and the id for the human handle)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("login", "sender_type", "sender_id"),
    [
        ("github-actions[bot]", "Bot", 41898282),
        ("codex", "Bot", 1),
        ("jules", "Bot", 2),
        ("claude-bot", "Bot", 3),
        ("gemini-bot", "Bot", 4),
        ("mbtiongson1", "User", 153011150),
    ],
)
def test_allowlisted_senders_pass(login, sender_type, sender_id):
    assert allowlisted(login, sender_type, sender_id) is True


@pytest.mark.parametrize(
    ("login", "sender_type", "sender_id"),
    [
        ("github-actions[bot]", "User", 41898282),  # a human account cannot use a bot name
        ("codex", "User", 99),  # a human account named codex is not trusted
        ("jules", "User", 99),
        ("gemini-bot", "User", 99),
        ("claude-bot", "User", 99),
        ("github-actions", "User", 99),
        ("mbtiongson1", "User", 1),  # the handle with another id
        ("mbtiongson1", "Bot", 153011150),  # the handle with the wrong type
        ("mbtiongson1", None, None),
        ("Codex", "Bot", 1),  # the bot names are exact
        ("alice", "User", 7),  # an ordinary verifier is not allowlisted here (the index decides)
        ("dependabot[bot]", "Bot", 49699333),  # C9 M-1: a '[bot]' suffix alone is not a trusted login
        ("", "Bot", 1),
        (None, "Bot", 1),
    ],
)
def test_everything_else_is_not_allowlisted(login, sender_type, sender_id):
    assert allowlisted(login, sender_type, sender_id) is False


# ---------------------------------------------------------------------------
# L5: the skip-child-gate label is honoured only from an authorised labeler
# ---------------------------------------------------------------------------


def _labeled(event_id, login, label="skip-child-gate", sender_type="User", sender_id=1):
    return {"id": event_id, "event": "labeled", "label": {"name": label},
            "actor": {"login": login, "type": sender_type, "id": sender_id}}


def test_skip_label_from_a_verifier_is_honoured(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", "4★")]}})
    assert skip_label_authorized([_labeled(1, "alice")], index) is True


def test_skip_label_from_a_non_verifier_is_not_honoured(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", "4★")]}})
    assert skip_label_authorized([_labeled(1, "mallory")], index) is False


def test_skip_label_from_an_allowlisted_human_is_honoured(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", "2★")]}})
    assert skip_label_authorized([_labeled(1, "mbtiongson1", sender_id=153011150)], index) is True


def test_skip_label_from_a_human_named_codex_is_not_honoured(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", "4★")]}})
    assert skip_label_authorized([_labeled(1, "codex", sender_type="User", sender_id=5)], index) is False


def test_the_most_recent_skip_labeling_decides(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", "4★")]}})
    events = [_labeled(1, "alice"), _labeled(9, "mallory")]
    assert skip_label_authorized(events, index) is False


def test_other_labels_and_no_labeling_do_not_authorize_a_skip(tmp_path):
    index = _index(tmp_path, {"buckets": {"stars": [_entry("alice", "4★")]}})
    assert skip_label_authorized([_labeled(1, "alice", label="upstream:approved")], index) is False
    assert skip_label_authorized([], index) is False


def test_skip_label_fails_closed_without_an_index(tmp_path):
    assert skip_label_authorized([_labeled(1, "alice")], str(tmp_path / "absent.json")) is False


# ---------------------------------------------------------------------------
# L3: one definition of the payload block regex
# ---------------------------------------------------------------------------


def test_every_consumer_uses_the_same_payload_regex_object():
    assert approval.PAYLOAD_RE is markers.PAYLOAD_RE
    assert batch.PAYLOAD_RE is markers.PAYLOAD_RE
    assert records.PAYLOAD_RE is markers.PAYLOAD_RE


def test_the_one_regex_reads_what_the_writers_write():
    payload = {"payloadVersion": 2, "skillId": "a/b", "candidates": [{"id": "x --> y"}]}
    body = batch.payload_block(payload) + "\n\nprose"
    match = markers.PAYLOAD_RE.search(body)
    assert match and json.loads(match.group(1)) == payload


def test_the_regex_is_not_fooled_by_an_arrow_inside_a_json_string():
    payload = {"payloadVersion": 2, "note": "-->", "candidates": []}
    body = batch.payload_block(payload)
    assert json.loads(markers.PAYLOAD_RE.search(body).group(1)) == payload


def test_workflow_files_import_the_regex_rather_than_copy_it():
    for name in ("upstream-approve.yml", "upstream-close-children.yml"):
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        assert "re.compile(r\"<!-- gaia-upstream-payload" not in text, name
        assert "from scripts.upstream_watcher.markers import PAYLOAD_RE" in text, name
