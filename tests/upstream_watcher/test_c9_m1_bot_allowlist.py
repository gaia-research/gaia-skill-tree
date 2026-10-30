"""#2131 round-5 verifier MEDIUM, M-1: the allowlist trusts explicit bot logins, not every '[bot]' name.

Before this change any login ending in '[bot]' was trusted for a Bot sender, so any GitHub App that merely
ends its name in '[bot]' (dependabot[bot], renovate[bot], an arbitrary app) could apply upstream:approved or
skip-child-gate. Only the bots named here are trusted, and only for a Bot sender.
"""

import pytest

from scripts.upstream_watcher import approval

TRUSTED = {"github-actions[bot]", "github-actions", "codex", "jules", "claude-bot", "gemini-bot"}


def test_the_trusted_bot_logins_are_exactly_the_named_ones():
    assert set(approval.BOT_NAMES) | {"github-actions[bot]"} == TRUSTED


@pytest.mark.parametrize("login", sorted(TRUSTED))
def test_each_named_bot_is_trusted_for_a_bot_sender(login):
    assert approval.allowlisted(login, "Bot", 1) is True


@pytest.mark.parametrize(
    "login",
    [
        "dependabot[bot]",
        "renovate[bot]",
        "some-app[bot]",
        "evil-app[bot]",
        "codex[bot]",
        "jules[bot]",
    ],
)
def test_an_arbitrary_app_with_a_bot_suffix_is_not_trusted_even_as_a_bot(login):
    assert approval.allowlisted(login, "Bot", 99) is False


def test_the_bot_suffix_alone_is_never_enough_for_a_human_sender():
    assert approval.allowlisted("dependabot[bot]", "User", 99) is False


def test_the_allowlist_is_a_closed_set_and_checks_exact_names():
    # The fix is a set lookup, so a near-miss of a trusted name is not trusted.
    assert approval.allowlisted("github-actions[bot]x", "Bot", 1) is False
    assert approval.allowlisted("Github-Actions[bot]", "Bot", 1) is False
