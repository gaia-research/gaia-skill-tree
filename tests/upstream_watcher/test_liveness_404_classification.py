"""Tests for upstream 404 classification (DELETED vs RENAMED) from upstream git evidence."""

from __future__ import annotations

import argparse
import re
import shlex
import subprocess
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
from urllib.parse import quote

import pytest

from gaia_cli.commands.dev import DevCommand
from gaia_cli.commands.dev.relink import relink_command
from gaia_cli.frontmatter import load_yaml_simple, split_frontmatter
from scripts.lib.github_api import GitHubFetchError
from scripts.upstream_watcher import batch as bt
from scripts.upstream_watcher import issuer
from scripts.upstream_watcher import liveness
from scripts.upstream_watcher import watcher


BLOB_URL = "https://github.com/obra/superpowers/blob/main/skills/writing-skills/SKILL.md"
RAW_URL = "https://raw.githubusercontent.com/obra/superpowers/main/skills/writing-skills/SKILL.md"
SKILL_ID = "obra/writing-skills"
SHA = "a1b2c3d4e5f67890abcdef1234567890abcdef12"


def _fake_fetch_deleted(sha: str = SHA, path: str = "skills/writing-skills/SKILL.md"):
    def _fetch(endpoint: str, **kwargs):
        if "commits?" in endpoint:
            return [{"sha": sha}]
        if f"/commits/{sha}" in endpoint:
            return {
                "sha": sha,
                "files": [
                    {"filename": path, "status": "removed"},
                ],
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    return _fetch


def _fake_fetch_renamed(
    sha: str = SHA,
    old_path: str = "skills/writing-skills/SKILL.md",
    new_path: str = "skills/authoring-skills/SKILL.md",
):
    def _fetch(endpoint: str, **kwargs):
        if "commits?" in endpoint:
            return [{"sha": sha}]
        if f"/commits/{sha}" in endpoint:
            return {
                "sha": sha,
                "files": [
                    {
                        "filename": new_path,
                        "previous_filename": old_path,
                        "status": "renamed",
                    },
                ],
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    return _fetch


# ---------------------------------------------------------------------------
# DELETED fixture
# ---------------------------------------------------------------------------


def test_classify_upstream_404_deleted_blob_url():
    fetch_fn = _fake_fetch_deleted()
    res = liveness.classify_upstream_404(BLOB_URL, SKILL_ID, fetch_json_fn=fetch_fn)

    assert res["classification"] == "DELETED"
    assert res["commitSha"] == SHA
    assert res["proposal"] == (
        f"gaia dev freeze {SKILL_ID} --reason "
        f"'upstream file removed in commit {SHA[:10]} (skills/writing-skills/SKILL.md)'"
    )


def test_classify_upstream_404_deleted_raw_url():
    fetch_fn = _fake_fetch_deleted()
    res = liveness.classify_upstream_404(RAW_URL, SKILL_ID, fetch_json_fn=fetch_fn)

    assert res["classification"] == "DELETED"
    assert res["commitSha"] == SHA
    assert res["proposal"] == (
        f"gaia dev freeze {SKILL_ID} --reason "
        f"'upstream file removed in commit {SHA[:10]} (skills/writing-skills/SKILL.md)'"
    )


# ---------------------------------------------------------------------------
# RENAMED fixture
# ---------------------------------------------------------------------------


def test_classify_upstream_404_renamed_blob_url():
    fetch_fn = _fake_fetch_renamed()
    res = liveness.classify_upstream_404(BLOB_URL, SKILL_ID, fetch_json_fn=fetch_fn)

    assert res["classification"] == "RENAMED"
    assert res["commitSha"] == SHA
    assert res["newPath"] == "skills/authoring-skills/SKILL.md"
    assert res["newUrl"] == "https://github.com/obra/superpowers/blob/main/skills/authoring-skills/SKILL.md"
    assert res["proposal"] == (
        f"gaia dev relink {SKILL_ID} --new-url "
        "https://github.com/obra/superpowers/blob/main/skills/authoring-skills/SKILL.md"
    )


def test_classify_upstream_404_renamed_raw_url():
    fetch_fn = _fake_fetch_renamed()
    res = liveness.classify_upstream_404(RAW_URL, SKILL_ID, fetch_json_fn=fetch_fn)

    assert res["classification"] == "RENAMED"
    assert res["commitSha"] == SHA
    assert res["newPath"] == "skills/authoring-skills/SKILL.md"
    assert res["newUrl"] == "https://github.com/obra/superpowers/blob/main/skills/authoring-skills/SKILL.md"
    assert res["proposal"] == (
        f"gaia dev relink {SKILL_ID} --new-url "
        "https://github.com/obra/superpowers/blob/main/skills/authoring-skills/SKILL.md"
    )


# ---------------------------------------------------------------------------
# Transient / Unknown fixtures
# ---------------------------------------------------------------------------


def test_classify_upstream_404_empty_commits():
    def fetch_empty(endpoint: str, **kwargs):
        return []

    res = liveness.classify_upstream_404(BLOB_URL, SKILL_ID, fetch_json_fn=fetch_empty)
    assert res["classification"] == "UNKNOWN"
    assert "proposal" not in res
    assert "reason" in res


def test_classify_upstream_404_commits_api_network_error():
    def fetch_error(endpoint: str, **kwargs):
        raise ConnectionResetError("network connection reset")

    res = liveness.classify_upstream_404(BLOB_URL, SKILL_ID, fetch_json_fn=fetch_error)
    assert res["classification"] == "UNKNOWN"
    assert "proposal" not in res
    assert "reason" in res


def test_classify_upstream_404_commits_api_500():
    def fetch_500(endpoint: str, **kwargs):
        raise GitHubFetchError("GitHub API HTTP 500", status=500)

    res = liveness.classify_upstream_404(BLOB_URL, SKILL_ID, fetch_json_fn=fetch_500)
    assert res["classification"] == "UNKNOWN"
    assert "proposal" not in res
    assert "reason" in res


def test_classify_upstream_404_commit_details_500():
    def fetch_details_error(endpoint: str, **kwargs):
        if "commits?" in endpoint:
            return [{"sha": SHA}]
        raise GitHubFetchError("HTTP 500 on commit detail", status=500)

    res = liveness.classify_upstream_404(BLOB_URL, SKILL_ID, fetch_json_fn=fetch_details_error)
    assert res["classification"] == "UNKNOWN"
    assert "proposal" not in res
    assert "reason" in res


def test_classify_upstream_404_no_matching_files_in_commit():
    def fetch_unrelated(endpoint: str, **kwargs):
        if "commits?" in endpoint:
            return [{"sha": SHA}]
        return {
            "sha": SHA,
            "files": [
                {"filename": "README.md", "status": "modified"},
                {"filename": "other/SKILL.md", "status": "removed"},
            ],
        }

    res = liveness.classify_upstream_404(BLOB_URL, SKILL_ID, fetch_json_fn=fetch_unrelated)
    assert res["classification"] == "UNKNOWN"
    assert "proposal" not in res
    assert "reason" in res


def test_classify_upstream_404_unparseable_url():
    res = liveness.classify_upstream_404("https://github.com/obra/superpowers", SKILL_ID)
    assert res["classification"] == "UNKNOWN"
    assert "proposal" not in res
    assert "unparseable" in res["reason"]


# ---------------------------------------------------------------------------
# Integration with check_component_liveness
# ---------------------------------------------------------------------------


def test_check_component_liveness_deleted_404():
    registry_map = {
        SKILL_ID: {"links": {"github": BLOB_URL}}
    }
    with patch("scripts.upstream_watcher.liveness.head_check", return_value=404):
        broken = liveness.check_component_liveness([SKILL_ID], registry_map, fetch_json_fn=_fake_fetch_deleted())

    assert len(broken) == 1
    row = broken[0]
    assert row["skillId"] == SKILL_ID
    assert row["status"] == 404
    assert row["classification"] == "DELETED"
    assert row["commitSha"] == SHA
    assert row["proposal"] == (
        f"gaia dev freeze {SKILL_ID} --reason "
        f"'upstream file removed in commit {SHA[:10]} (skills/writing-skills/SKILL.md)'"
    )


def test_check_component_liveness_renamed_410():
    registry_map = {
        SKILL_ID: {"links": {"github": BLOB_URL}}
    }
    with patch("scripts.upstream_watcher.liveness.head_check", return_value=410):
        broken = liveness.check_component_liveness([SKILL_ID], registry_map, fetch_json_fn=_fake_fetch_renamed())

    assert len(broken) == 1
    row = broken[0]
    assert row["skillId"] == SKILL_ID
    assert row["status"] == 410
    assert row["classification"] == "RENAMED"
    assert row["commitSha"] == SHA
    assert row["newPath"] == "skills/authoring-skills/SKILL.md"
    assert row["newUrl"] == "https://github.com/obra/superpowers/blob/main/skills/authoring-skills/SKILL.md"
    assert "gaia dev relink" in row["proposal"]


def test_check_component_liveness_unknown_stays_unknown_without_proposal():
    registry_map = {
        SKILL_ID: {"links": {"github": BLOB_URL}}
    }

    def fetch_error(endpoint: str, **kwargs):
        raise ConnectionError("down")

    with patch("scripts.upstream_watcher.liveness.head_check", return_value=404):
        broken = liveness.check_component_liveness([SKILL_ID], registry_map, fetch_json_fn=fetch_error)

    assert len(broken) == 1
    row = broken[0]
    assert row["skillId"] == SKILL_ID
    assert row["status"] == 404
    assert row["classification"] == "UNKNOWN"
    assert "proposal" not in row


# ---------------------------------------------------------------------------
# Proposal-only assertion: no registry writes occur
# ---------------------------------------------------------------------------


def test_proposal_only_no_registry_writes():
    """Liveness checking and 404 classification are advisory proposals only; registry remains untouched."""
    status_before = subprocess.run(
        ["git", "status", "--porcelain", "registry/"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    registry_map = {
        SKILL_ID: {"links": {"github": BLOB_URL}}
    }

    # Exercise DELETED
    with patch("scripts.upstream_watcher.liveness.head_check", return_value=404):
        broken_del = liveness.check_component_liveness([SKILL_ID], registry_map, fetch_json_fn=_fake_fetch_deleted())
    assert broken_del[0]["proposal"].startswith("gaia dev freeze")

    # Exercise RENAMED
    with patch("scripts.upstream_watcher.liveness.head_check", return_value=404):
        broken_ren = liveness.check_component_liveness([SKILL_ID], registry_map, fetch_json_fn=_fake_fetch_renamed())
    assert broken_ren[0]["proposal"].startswith("gaia dev relink")

    status_after = subprocess.run(
        ["git", "status", "--porcelain", "registry/"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout

    assert status_before == status_after, "Registry directory was modified by liveness checks!"


# ---------------------------------------------------------------------------
# Rendering tests in issuer.py, watcher.py, and batch.py
# ---------------------------------------------------------------------------


def test_issuer_renders_proposal_when_present():
    finding = {
        "finding_type": "update",
        "skillId": "obra/superpowers",
        "currentVersion": "v6.4.1",
        "newVersion": "v7.0.0",
        "releasedAt": "2026-10-10T00:28:58Z",
        "sourceUrl": "https://github.com/obra/superpowers/releases/tag/v7.0.0",
    }
    proposal = "gaia dev freeze obra/writing-skills --reason 'upstream file removed in commit abc (path)'"
    link_liveness = [
        {
            "skillId": SKILL_ID,
            "url": BLOB_URL,
            "status": 404,
            "classification": "DELETED",
            "proposal": proposal,
        }
    ]

    body = issuer.render_umbrella_body(
        finding,
        mode="components",
        component_adds=[],
        component_removes=[],
        link_liveness=link_liveness,
    )

    assert "| Skill | URL | Status | Proposal |" in body
    assert proposal in body


def test_watcher_renders_proposal_when_present():
    proposal = "gaia dev relink obra/writing-skills --new-url https://example.com/new"
    findings = [
        {
            "finding_type": "update",
            "skillId": "obra/superpowers",
            "currentVersion": "v6.4.1",
            "newVersion": "v7.0.0",
            "releasedAt": "2026-10-10T00:28:58Z",
            "sourceUrl": "https://github.com/obra/superpowers/releases/tag/v7.0.0",
            "mode": "components",
            "componentAdds": [],
            "componentRemoves": [],
            "linkLiveness": [
                {
                    "skillId": SKILL_ID,
                    "url": BLOB_URL,
                    "status": 404,
                    "classification": "RENAMED",
                    "proposal": proposal,
                }
            ],
        }
    ]

    summary = watcher._render_report(findings)
    assert f"— proposal: `{proposal}`" in summary


def test_batch_renders_proposal_when_present():
    proposal = "gaia dev freeze obra/writing-skills --reason 'upstream file removed'"
    payload = {
        "skillId": "obra/superpowers",
        "previousVersion": "v6.4.1",
        "newVersion": "v7.0.0",
        "releasedAt": "2026-10-10T00:28:58Z",
        "sourceUrl": "https://github.com/obra/superpowers/releases/tag/v7.0.0",
        "mode": "components",
        "componentAdds": [],
        "componentRemoves": [],
        "linkLiveness": [
            {
                "skillId": SKILL_ID,
                "url": BLOB_URL,
                "status": 404,
                "classification": "DELETED",
                "proposal": proposal,
            }
        ],
        "nameDrift": [],
        "candidates": [],
    }

    body = bt.render_batch_body(payload)
    assert "### Link liveness" in body
    assert "| Skill | URL | Status | Proposal |" in body
    assert proposal in body


# ---------------------------------------------------------------------------
# Ref-specific commit querying, shlex escaping, and filename validation tests
# ---------------------------------------------------------------------------


def test_classify_upstream_404_ref_branch_querying():
    recorded_endpoints = []

    def fetch_fn(endpoint: str, **kwargs):
        recorded_endpoints.append(endpoint)
        if "commits?" in endpoint:
            return [{"sha": SHA}]
        if f"/commits/{SHA}" in endpoint:
            return {
                "sha": SHA,
                "files": [
                    {"filename": "skills/writing-skills/SKILL.md", "status": "removed"},
                ],
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    url = "https://github.com/obra/superpowers/blob/develop/skills/writing-skills/SKILL.md"
    res = liveness.classify_upstream_404(url, SKILL_ID, fetch_json_fn=fetch_fn)

    assert res["classification"] == "DELETED"
    expected_endpoint = (
        f"/repos/obra/superpowers/commits?path=skills/writing-skills/SKILL.md&sha=develop&per_page=1"
    )
    assert expected_endpoint in recorded_endpoints


def test_classify_upstream_404_ref_tag_querying():
    recorded_endpoints = []

    def fetch_fn(endpoint: str, **kwargs):
        recorded_endpoints.append(endpoint)
        if "commits?" in endpoint:
            return [{"sha": SHA}]
        if f"/commits/{SHA}" in endpoint:
            return {
                "sha": SHA,
                "files": [
                    {"filename": "skills/writing-skills/SKILL.md", "status": "removed"},
                ],
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    url = "https://github.com/obra/superpowers/blob/v1.0.0/skills/writing-skills/SKILL.md"
    res = liveness.classify_upstream_404(url, SKILL_ID, fetch_json_fn=fetch_fn)

    assert res["classification"] == "DELETED"
    expected_endpoint = (
        f"/repos/obra/superpowers/commits?path=skills/writing-skills/SKILL.md&sha=v1.0.0&per_page=1"
    )
    assert expected_endpoint in recorded_endpoints


def test_classify_upstream_404_shlex_quote_adversarial_deleted():
    adversarial_path = "skills/weird; name 'with' quotes \"and\" spaces/SKILL.md"
    adversarial_skill_id = "bad; id 'danger' \"skill\""
    adversarial_url = f"https://github.com/obra/superpowers/blob/main/{adversarial_path}"

    def fetch_fn(endpoint: str, **kwargs):
        if "commits?" in endpoint:
            return [{"sha": SHA}]
        if f"/commits/{SHA}" in endpoint:
            return {
                "sha": SHA,
                "files": [
                    {"filename": adversarial_path, "status": "removed"},
                ],
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    res = liveness.classify_upstream_404(adversarial_url, adversarial_skill_id, fetch_json_fn=fetch_fn)

    assert res["classification"] == "DELETED"
    proposal = res["proposal"]

    # Verify that shlex safely parses the arguments without shell-injection issues
    tokens = shlex.split(proposal)
    assert tokens[0] == "gaia"
    assert tokens[1] == "dev"
    assert tokens[2] == "freeze"
    assert tokens[3] == adversarial_skill_id
    assert tokens[4] == "--reason"
    assert tokens[5] == f"upstream file removed in commit {SHA[:10]} ({adversarial_path})"


def test_classify_upstream_404_shlex_quote_adversarial_renamed():
    old_path = "skills/writing-skills/SKILL.md"
    adversarial_new_path = "skills/target; file 'with' quotes \"and\" spaces/SKILL.md"
    adversarial_skill_id = "bad; id 'danger' \"skill\""
    url = f"https://github.com/obra/superpowers/blob/main/{old_path}"

    def fetch_fn(endpoint: str, **kwargs):
        if "commits?" in endpoint:
            return [{"sha": SHA}]
        if f"/commits/{SHA}" in endpoint:
            return {
                "sha": SHA,
                "files": [
                    {
                        "filename": adversarial_new_path,
                        "previous_filename": old_path,
                        "status": "renamed",
                    },
                ],
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    res = liveness.classify_upstream_404(url, adversarial_skill_id, fetch_json_fn=fetch_fn)

    assert res["classification"] == "RENAMED"
    proposal = res["proposal"]

    tokens = shlex.split(proposal)
    expected_new_url = f"https://github.com/obra/superpowers/blob/main/{quote(adversarial_new_path, safe='/')}"
    assert tokens[0] == "gaia"
    assert tokens[1] == "dev"
    assert tokens[2] == "relink"
    assert tokens[3] == adversarial_skill_id
    assert tokens[4] == "--new-url"
    assert tokens[5] == expected_new_url


@pytest.mark.parametrize(
    "bad_filename",
    [
        None,
        "",
        "   ",
        "\t\n  ",
    ],
)
def test_classify_upstream_404_renamed_missing_or_empty_filename(bad_filename):
    old_path = "skills/writing-skills/SKILL.md"

    def fetch_fn(endpoint: str, **kwargs):
        if "commits?" in endpoint:
            return [{"sha": SHA}]
        if f"/commits/{SHA}" in endpoint:
            file_entry = {
                "previous_filename": old_path,
                "status": "renamed",
            }
            if bad_filename is not None:
                file_entry["filename"] = bad_filename
            return {
                "sha": SHA,
                "files": [file_entry],
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    res = liveness.classify_upstream_404(BLOB_URL, SKILL_ID, fetch_json_fn=fetch_fn)

    assert res["classification"] == "UNKNOWN"
    assert "proposal" not in res
    assert "reason" in res


# ---------------------------------------------------------------------------
# gaia dev relink CLI parser and execution tests
# ---------------------------------------------------------------------------


def _make_test_named_registry(
    tmp_path: Path,
    skill_id: str = "testorg/my-skill",
    old_url: str = "https://github.com/testorg/my-skill/blob/main/skills/old/SKILL.md",
) -> tuple[str, Path]:
    owner, slug = skill_id.split("/", 1)
    named_dir = tmp_path / "registry" / "named" / owner
    named_dir.mkdir(parents=True, exist_ok=True)
    skill_file = named_dir / f"{slug}.md"
    content = f"""---
id: {skill_id}
name: My Skill
contributor: {owner}
status: named
level: 2★
installable: true
links:
  github: {old_url}
timeline: []
---

## My Skill

Body content.
"""
    skill_file.write_text(content, encoding="utf-8")
    return str(tmp_path), skill_file


def test_relink_cli_parser_registered_and_parses_args():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")
    dev_parser = subparsers.add_parser("dev")
    DevCommand().configure(dev_parser)

    args = parser.parse_args([
        "dev",
        "relink",
        "testorg/my-skill",
        "--new-url",
        "https://github.com/testorg/my-skill/blob/main/skills/new/SKILL.md",
    ])
    assert args.subcommand == "dev"
    assert args.dev_command == "relink"
    assert args.skill_id == "testorg/my-skill"
    assert args.new_url == "https://github.com/testorg/my-skill/blob/main/skills/new/SKILL.md"
    assert args.dry_run is False
    assert args.user is None


def test_relink_cli_parser_flags():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")
    dev_parser = subparsers.add_parser("dev")
    DevCommand().configure(dev_parser)

    args = parser.parse_args([
        "dev",
        "relink",
        "testorg/my-skill",
        "--new-url",
        "https://github.com/testorg/my-skill/blob/main/skills/new/SKILL.md",
        "--dry-run",
        "--user",
        "maintainer-bot",
    ])
    assert args.dry_run is True
    assert args.user == "maintainer-bot"


def test_relink_cli_parser_missing_required_url():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")
    dev_parser = subparsers.add_parser("dev")
    DevCommand().configure(dev_parser)

    with pytest.raises(SystemExit):
        parser.parse_args(["dev", "relink", "testorg/my-skill"])


def test_relink_cli_parser_missing_skill_id():
    parser = argparse.ArgumentParser()
    subparsers = parser.add_subparsers(dest="subcommand")
    dev_parser = subparsers.add_parser("dev")
    DevCommand().configure(dev_parser)

    with pytest.raises(SystemExit):
        parser.parse_args(["dev", "relink", "--new-url", "https://github.com/testorg/my-skill/blob/main/SKILL.md"])


def test_relink_execution_happy_path(tmp_path):
    registry_path, skill_file = _make_test_named_registry(tmp_path)
    old_url = "https://github.com/testorg/my-skill/blob/main/skills/old/SKILL.md"
    new_url = "https://github.com/testorg/my-skill/blob/main/skills/new/SKILL.md"

    args = SimpleNamespace(
        registry=registry_path,
        skill_id="testorg/my-skill",
        new_url=new_url,
        dry_run=False,
        user="custom-actor",
    )
    result = relink_command(args)
    assert result == 0

    text = skill_file.read_text(encoding="utf-8")
    _fence, fm_text, _body = split_frontmatter(text)
    meta = load_yaml_simple(fm_text)

    assert meta["links"]["github"] == new_url
    assert len(meta["timeline"]) == 1
    event = meta["timeline"][0]
    assert event["action"] == "relinked"
    assert event["details"] == f"Relinked from {old_url} to {new_url}"
    assert event["contributor"] == "custom-actor"
    assert event["previousValue"] == old_url
    assert event["newValue"] == new_url
    assert "timestamp" in event


def test_relink_execution_dry_run(tmp_path, capsys):
    registry_path, skill_file = _make_test_named_registry(tmp_path)
    original_text = skill_file.read_text(encoding="utf-8")
    new_url = "https://github.com/testorg/my-skill/blob/main/skills/new/SKILL.md"

    args = SimpleNamespace(
        registry=registry_path,
        skill_id="testorg/my-skill",
        new_url=new_url,
        dry_run=True,
        user=None,
    )
    result = relink_command(args)
    assert result is None

    assert skill_file.read_text(encoding="utf-8") == original_text
    captured = capsys.readouterr()
    assert "DRY RUN" in captured.out
    assert new_url in captured.out


def test_relink_execution_skill_not_found(tmp_path):
    registry_path, _ = _make_test_named_registry(tmp_path)
    args = SimpleNamespace(
        registry=registry_path,
        skill_id="testorg/nonexistent",
        new_url="https://github.com/testorg/my-skill/blob/main/skills/new/SKILL.md",
        dry_run=False,
        user=None,
    )
    with pytest.raises(SystemExit) as excinfo:
        relink_command(args)
    assert excinfo.value.code == 1


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "   ",
        "https://github.com/testorg/my-skill",
        "https://github.com/testorg/my-skill/tree/main/skills/new",
        "https://gitlab.com/testorg/my-skill/blob/main/SKILL.md",
    ],
)
def test_relink_execution_invalid_url(tmp_path, bad_url):
    registry_path, _ = _make_test_named_registry(tmp_path)
    args = SimpleNamespace(
        registry=registry_path,
        skill_id="testorg/my-skill",
        new_url=bad_url,
        dry_run=False,
        user=None,
    )
    with pytest.raises(SystemExit) as excinfo:
        relink_command(args)
    assert excinfo.value.code == 1


def test_relink_execution_via_dev_command_dispatch(tmp_path, monkeypatch):
    registry_path, skill_file = _make_test_named_registry(tmp_path)
    new_url = "https://github.com/testorg/my-skill/blob/main/skills/dispatch/SKILL.md"

    monkeypatch.setattr("gaia_cli.authz.require_operator", lambda *a, **kw: None)

    args = SimpleNamespace(
        registry=registry_path,
        dev_command="relink",
        skill_id="testorg/my-skill",
        new_url=new_url,
        dry_run=False,
        user="dispatch-user",
    )
    DevCommand().execute(args)

    text = skill_file.read_text(encoding="utf-8")
    _fence, fm_text, _body = split_frontmatter(text)
    meta = load_yaml_simple(fm_text)
    assert meta["links"]["github"] == new_url
    assert meta["timeline"][-1]["action"] == "relinked"


# ---------------------------------------------------------------------------
# URL unquoting and percent-encoding with reserved characters (#, ?, spaces)
# ---------------------------------------------------------------------------


def test_parse_github_file_url_unquotes_reserved_chars():
    # Hash (#) percent-encoded
    url_hash = "https://github.com/owner/repo/blob/main/skills/c%23/SKILL.md"
    assert liveness.parse_github_file_url(url_hash) == ("owner", "repo", "main", "skills/c#/SKILL.md")

    # Space percent-encoded
    url_space = "https://github.com/owner/repo/blob/main/skills/my%20skill/SKILL.md"
    assert liveness.parse_github_file_url(url_space) == ("owner", "repo", "main", "skills/my skill/SKILL.md")

    # Question mark (?) percent-encoded
    url_qm = "https://github.com/owner/repo/blob/main/skills/what%3F/SKILL.md"
    assert liveness.parse_github_file_url(url_qm) == ("owner", "repo", "main", "skills/what?/SKILL.md")

    # Raw URL unquoting
    raw_hash = "https://raw.githubusercontent.com/owner/repo/main/skills/c%23/SKILL.md"
    assert liveness.parse_github_file_url(raw_hash) == ("owner", "repo", "main", "skills/c#/SKILL.md")


def test_classify_upstream_404_url_unquoting_matches_commit_file():
    recorded_endpoints = []
    unquoted_path = "skills/c# sharp/SKILL.md"

    def fetch_fn(endpoint: str, **kwargs):
        recorded_endpoints.append(endpoint)
        if "commits?" in endpoint:
            return [{"sha": SHA}]
        if f"/commits/{SHA}" in endpoint:
            return {
                "sha": SHA,
                "files": [
                    {"filename": unquoted_path, "status": "removed"},
                ],
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    # Pass percent-encoded URL
    encoded_url = "https://github.com/owner/repo/blob/main/skills/c%23%20sharp/SKILL.md"
    res = liveness.classify_upstream_404(encoded_url, "owner/csharp", fetch_json_fn=fetch_fn)

    assert res["classification"] == "DELETED"
    assert any("path=skills/c%23%20sharp/SKILL.md" in ep for ep in recorded_endpoints)
    assert unquoted_path in res["proposal"]


def test_classify_upstream_404_new_path_percent_encoded_with_reserved_chars():
    old_path = "skills/old-path/SKILL.md"
    reserved_new_path = "skills/c# special ? & space/SKILL.md"

    def fetch_fn(endpoint: str, **kwargs):
        if "commits?" in endpoint:
            return [{"sha": SHA}]
        if f"/commits/{SHA}" in endpoint:
            return {
                "sha": SHA,
                "files": [
                    {
                        "filename": reserved_new_path,
                        "previous_filename": old_path,
                        "status": "renamed",
                    },
                ],
            }
        raise AssertionError(f"unexpected endpoint: {endpoint}")

    url = f"https://github.com/owner/repo/blob/main/{old_path}"
    res = liveness.classify_upstream_404(url, "owner/skill", fetch_json_fn=fetch_fn)

    assert res["classification"] == "RENAMED"
    assert res["newPath"] == reserved_new_path
    expected_quoted_url = "https://github.com/owner/repo/blob/main/skills/c%23%20special%20%3F%20%26%20space/SKILL.md"
    assert res["newUrl"] == expected_quoted_url

    tokens = shlex.split(res["proposal"])
    assert tokens[0] == "gaia"
    assert tokens[1] == "dev"
    assert tokens[2] == "relink"
    assert tokens[3] == "owner/skill"
    assert tokens[4] == "--new-url"
    assert tokens[5] == expected_quoted_url


# ---------------------------------------------------------------------------
# Pipe escaping in markdown table rendering tests
# ---------------------------------------------------------------------------


def test_issuer_table_pipe_escaping():
    finding = {
        "finding_type": "update",
        "skillId": "obra/superpowers",
        "currentVersion": "v6.4.1",
        "newVersion": "v7.0.0",
        "releasedAt": "2026-10-10T00:28:58Z",
        "sourceUrl": "https://github.com/obra/superpowers/releases/tag/v7.0.0",
    }
    proposal_with_pipes = "gaia dev freeze obra/writing-skills --reason 'removed | moved | deprecated'"
    link_liveness = [
        {
            "skillId": SKILL_ID,
            "url": BLOB_URL,
            "status": 404,
            "classification": "DELETED",
            "proposal": proposal_with_pipes,
        }
    ]

    body = issuer.render_umbrella_body(
        finding,
        mode="components",
        component_adds=[],
        component_removes=[],
        link_liveness=link_liveness,
    )

    # Verify pipe character inside proposal cell is escaped
    assert r"removed \| moved \| deprecated" in body

    # Verify table row structure: finding the table row and splitting by unescaped pipe
    table_rows = [line for line in body.splitlines() if line.startswith("|") and line.endswith("|") and SKILL_ID in line]
    assert len(table_rows) == 1
    unescaped_pipes = re.split(r"(?<!\\)\|", table_rows[0])
    assert len(unescaped_pipes) == 6


def test_batch_table_pipe_escaping():
    proposal_with_pipes = "gaia dev freeze obra/writing-skills --reason 'opt1 | opt2'"
    payload = {
        "skillId": "obra/superpowers",
        "previousVersion": "v6.4.1",
        "newVersion": "v7.0.0",
        "releasedAt": "2026-10-10T00:28:58Z",
        "sourceUrl": "https://github.com/obra/superpowers/releases/tag/v7.0.0",
        "mode": "components",
        "componentAdds": [],
        "componentRemoves": [],
        "linkLiveness": [
            {
                "skillId": SKILL_ID,
                "url": BLOB_URL,
                "status": 404,
                "classification": "DELETED",
                "proposal": proposal_with_pipes,
            }
        ],
        "nameDrift": [],
        "candidates": [],
    }

    body = bt.render_batch_body(payload)
    assert r"opt1 \| opt2" in body

    table_rows = [line for line in body.splitlines() if line.startswith("|") and line.endswith("|") and SKILL_ID in line]
    assert len(table_rows) == 1
    unescaped_pipes = re.split(r"(?<!\\)\|", table_rows[0])
    assert len(unescaped_pipes) == 6


