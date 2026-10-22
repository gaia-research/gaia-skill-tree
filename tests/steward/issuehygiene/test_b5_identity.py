"""Lane B5 closer identity (M3): GhForge reads the login our comments are written as, and comment authors.

The marker proof depends on both. A forge that cannot name its closer makes every marker unproven.
"""

from __future__ import annotations

import json

import pytest

from gaia_cli.steward.issuehygiene.closure import ForgeBlockedError, ForgeItemError
from scripts.steward_issue_reconcile import GhForge

TOKEN = "token-for-test"


class Transport:
    def __init__(self, responses):
        self.responses = list(responses)
        self.requests: list[tuple[str, str]] = []

    def __call__(self, method, url, headers, body):
        self.requests.append((method, url))
        return self.responses.pop(0)


def ok(payload) -> tuple[int, dict, str]:
    return 200, {}, json.dumps(payload)


def test_whoami_reads_the_login_from_the_unscoped_user_endpoint() -> None:
    transport = Transport([ok({"login": "steward-bot"})])

    assert GhForge("o/r", TOKEN, transport).whoami() == "steward-bot"
    assert transport.requests == [("GET", "https://api.github.com/user")]


@pytest.mark.parametrize("response", [
    (403, {}, "{}"),
    ok({"name": "no login field"}),
    ok({"login": "  "}),
])
def test_whoami_that_cannot_be_read_raises_so_no_marker_is_proof(response) -> None:
    with pytest.raises((ForgeBlockedError, ForgeItemError)):
        GhForge("o/r", TOKEN, Transport([response])).whoami()


def test_list_comments_carries_each_comment_author() -> None:
    rows = [
        {"body": "ours", "html_url": "https://github.com/o/r/issues/3#issuecomment-1", "user": {"login": "steward-bot"}},
        {"body": "theirs", "html_url": "https://github.com/o/r/issues/3#issuecomment-2", "user": {"login": "someone"}},
        {"body": "anonymous", "html_url": "https://github.com/o/r/issues/3#issuecomment-3"},
    ]

    comments = GhForge("o/r", TOKEN, Transport([ok(rows)])).listComments(3)

    assert [comment["author"] for comment in comments] == ["steward-bot", "someone", None]
