"""Stage-1 minimum-effort evidence writer (RFC2 §3.2).

Deterministic builder for the three "minimum-effort" evidence rows the crawler
already holds at curation time: ``github-stars-own`` (stargazer count),
``repo-own`` (commits + contributors), and ``self-attestation`` (flat baseline).

These are REAL canonical evidence rows in the same shape ``gaia dev evidence``
writes (see ``commands/dev/evidence.py``) — not a throwaway estimate. Trust
Magnitude, grade, class, and star level are NEVER assigned here: they are derived
canonically at appraisal time from the evidence rows. This module performs NO
web fetch or search — the caller passes in the signals it already fetched during
discovery.

The three row types map to the ``meta.json`` ``evidence.types`` ids of the same
name; ``self-attestation`` is capped at one entry per skill and carries no
numeric payload (its magnitude is a flat baseline).
"""

from __future__ import annotations

import datetime


# The Stage-1 minimum-effort set, in canonical emission order. Web search and
# every richer evidence type (benchmark-result, arxiv, peer-review, richer
# social-signal) are Stage 2 / Phase 0 — never written here.
STAGE_ONE_TYPES = ("github-stars-own", "repo-own", "self-attestation")


def buildStageOneRows(sourceUrl, evaluator, stars=None, commits=None,
                      contributors=None, date=None):
    """Build the Stage-1 minimum-effort evidence rows from already-held signals.

    Produces up to three rows (``github-stars-own``, ``repo-own``,
    ``self-attestation``) in the same canonical shape ``gaia dev evidence``
    writes: ``source``, ``evaluator``, ``date``, ``type``, plus the type-specific
    numeric payload the caller already fetched. Deterministic — the same inputs
    always yield the same rows in the same order.

    NO web fetch or search is performed: ``stars`` / ``commits`` /
    ``contributors`` are signals the crawler already holds and passes in. NO
    grade, class, trustNumber, star level, or Trust Magnitude is set — those are
    derived canonically at appraisal time.

    Args:
        sourceUrl: canonical source URL (the repo already in hand).
        evaluator: contributor handle recording the rows.
        stars: stargazer count for the ``github-stars-own`` row. Omitted when None.
        commits: commit count for the ``repo-own`` row.
        contributors: contributor count for the ``repo-own`` row.
        date: ISO date string; defaults to today (UTC date).

    Returns:
        A list of evidence-row dicts. ``self-attestation`` is always emitted
        (flat baseline, one per skill); ``github-stars-own`` only when ``stars``
        is provided; ``repo-own`` only when ``commits`` or ``contributors`` is
        provided.
    """
    rowDate = date or datetime.date.today().isoformat()

    def baseRow(evidenceType):
        # Exactly the canonical shape gaia dev evidence writes for a fresh row:
        # source / evaluator / date / type. No grade, no trustNumber, no class.
        return {
            "source": sourceUrl,
            "evaluator": evaluator,
            "date": rowDate,
            "type": evidenceType,
        }

    rows = []

    if stars is not None:
        starsRow = baseRow("github-stars-own")
        starsRow["stars"] = stars
        rows.append(starsRow)

    if commits is not None or contributors is not None:
        repoRow = baseRow("repo-own")
        if commits is not None:
            repoRow["commits"] = commits
        if contributors is not None:
            repoRow["contributors"] = contributors
        rows.append(repoRow)

    # self-attestation is the flat baseline — always present, no numeric payload.
    rows.append(baseRow("self-attestation"))

    return rows


def writeStageOneEvidence(evidenceList, sourceUrl, evaluator, stars=None,
                          commits=None, contributors=None, date=None):
    """Append the Stage-1 minimum-effort rows to an existing evidence list.

    Convenience wrapper over :func:`buildStageOneRows` that mutates and returns
    ``evidenceList`` (the ``evidence`` array on a node / named-skill frontmatter),
    appending the built rows in canonical order. Performs NO web fetch and sets
    NO grade / class / star / Trust Magnitude.

    Args:
        evidenceList: the existing evidence array to append to (mutated in place).
        sourceUrl / evaluator / stars / commits / contributors / date: forwarded
            to :func:`buildStageOneRows`.

    Returns:
        The mutated ``evidenceList``.
    """
    if evidenceList is None:
        evidenceList = []
    rows = buildStageOneRows(
        sourceUrl,
        evaluator,
        stars=stars,
        commits=commits,
        contributors=contributors,
        date=date,
    )
    evidenceList.extend(rows)
    return evidenceList
