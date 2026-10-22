"""#2131 round-3 verifier FAIL, D12: the records ceiling in docs/agents/upstream-watcher.md is the measured one.

The ceiling depends on the candidate id length AND the slug length. Two limits apply and the smaller one
binds: GitHub's 65,536-character issue body (the index), and GitHub's 65,536-character limit on each record
comment (a full 50-row chunk). The doc must state both, and the fail-closed behaviour.
"""

from __future__ import annotations

import pathlib

from scripts.upstream_watcher import batch, prechecks, records
from scripts.upstream_watcher.records import RecordError

DOC = pathlib.Path(__file__).resolve().parents[2] / "docs" / "agents" / "upstream-watcher.md"
EMPTY_INDEX = {"byId": {}, "bySlug": {}}


def _finding(id_len, slug_len, count):
    slug_pad = "%0*d"
    owner_repo_len = id_len - slug_len - 1
    owner = "o" * max(1, owner_repo_len // 2)
    repo = "r" * (owner_repo_len - len(owner) - 1)
    return {
        "finding_type": "update", "skillId": "garrytan/suite", "currentVersion": "v0", "newVersion": "v1",
        "releasedAt": "2026-10-21T00:00:00Z", "sourceUrl": f"https://github.com/{owner}/{repo}/releases/tag/v1",
        "mode": "components", "componentAdds": [slug_pad % (slug_len, n) for n in range(count)],
        "componentRemoves": [], "linkLiveness": [], "nameDrift": [], "upstreamComponentRoot": "skills",
    }


def _rows(finding):
    return [{**row, **prechecks.precheck_row(row, EMPTY_INDEX, {}, {})} for row in batch.candidate_rows(finding)]


def _body_fits(id_len, slug_len, count):
    finding = _finding(id_len, slug_len, count)
    try:
        batch.layout(finding, _rows(finding), previous_version=None)
        return True
    except RecordError:
        return False


def _body_ceiling(id_len, slug_len):
    low, high = 1, 2000
    while low < high:
        middle = (low + high + 1) // 2
        if _body_fits(id_len, slug_len, middle):
            low = middle
        else:
            high = middle - 1
    return low


def _first_chunk_overflows(id_len, slug_len):
    """True when a full 50-row record comment is over GitHub's per-comment limit."""
    finding = _finding(id_len, slug_len, 50)
    try:
        records.render_chunk("0" * 64, 1, 1, _rows(finding))
        return False
    except RecordError:
        return True


def test_the_body_ceiling_matches_the_measured_figures():
    assert _body_ceiling(26, 8) == 844
    assert _body_ceiling(26, 22) == 711


def test_the_doc_states_the_measured_figures_for_both_slug_lengths():
    text = DOC.read_text(encoding="utf-8")
    assert "844" in text and "711" in text
    assert "712" not in text.split("Records ceiling")[1].split("\n")[0], "the withdrawn 712 figure must not stand"


def test_the_per_comment_limit_binds_at_long_ids_and_the_doc_says_so():
    assert not _first_chunk_overflows(282, 8)
    assert _first_chunk_overflows(298, 8)
    assert _first_chunk_overflows(284, 22)
    text = DOC.read_text(encoding="utf-8")
    assert "65,536-character limit on each record comment" in text
    assert "298" in text and "284" in text


def test_the_doc_states_the_fail_closed_outcome_of_a_suite_over_either_limit():
    text = DOC.read_text(encoding="utf-8")
    assert "fails closed" in text and "zero writes" in text
