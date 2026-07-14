"""Regression test for issue #1144.

The SDK-test and license-check workflows must declare an explicit top-level
read-only ``permissions`` block so they do not inherit repository-default
read-write GITHUB_TOKEN scopes (principle of least privilege).

Scoped intentionally to the two workflows named in #1144: other workflows
(labels-sync, meta-guard, pr-author-identity, ...) legitimately require write
scopes and are out of scope for this fix.
"""

import pathlib

import yaml

WORKFLOWS_DIR = pathlib.Path(__file__).resolve().parents[1] / ".github" / "workflows"

# Workflows named in issue #1144 that run read-only jobs (tests / license check).
READ_ONLY_WORKFLOWS = ["sdk-tests.yml", "license-check.yml"]


def _load(name):
    with open(WORKFLOWS_DIR / name) as fh:
        return yaml.safe_load(fh)


def test_named_workflows_declare_top_level_permissions():
    for name in READ_ONLY_WORKFLOWS:
        doc = _load(name)
        assert "permissions" in doc, f"{name} is missing a top-level permissions block"


def test_named_workflows_default_to_contents_read():
    for name in READ_ONLY_WORKFLOWS:
        perms = _load(name)["permissions"]
        assert perms == {"contents": "read"}, (
            f"{name} should default to read-only contents access, got {perms!r}"
        )
