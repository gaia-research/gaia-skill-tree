"""Dry-run parity for staged batching (#2283): legacy fanout vs batch vs staged, on recorded fixtures.

The harness is ``parity_2283.py`` (also runnable for the evidence report). Parity means no candidate the legacy
fanout would file or adopt is missing from the batch record, with dispositions intact, while writes drop.
"""

import parity_2283 as parity
import pytest


@pytest.fixture(scope="module")
def live():
    return parity.scenarioLiveFamilies()


@pytest.fixture(scope="module")
def week():
    return parity.scenarioDailyWeek()


def test_live_families_batch_and_staged_cover_every_legacy_candidate(live):
    assert live["candidatesInFindings"] == 104
    assert live["legacy"]["candidatesCovered"] == 104
    assert live["legacy"]["childrenAdopted"] == 96 and live["legacy"]["childrenCreated"] == 8
    assert live["parity"]["legacyCandidatesMissingFromBatch"] == []
    assert live["parity"]["legacyCandidatesMissingFromStaged"] == []
    assert live["batch"]["rows"] == live["staged"]["rows"] == 104


def test_live_families_staged_flush_is_row_for_row_the_unstaged_batch(live):
    assert live["parity"]["stagedRowsEqualBatchRows"] is True


def test_live_families_noise_goes_down_at_each_step(live):
    assert live["staged"]["holdDayWrites"] == 0 and live["staged"]["heldSuites"] == 4
    assert live["staged"]["flushedSuites"] == 4
    assert live["batch"]["writes"] < live["legacy"]["writes"]
    assert live["staged"]["flushDayWrites"] == live["batch"]["writes"]
    assert live["legacy"]["issuesCreated"] == 8 and live["batch"]["issuesCreated"] == 0


def test_a_week_of_daily_releases_loses_no_current_candidate(week):
    assert week["parity"]["candidatesAtFlushMissingFromRows"] == []
    assert week["parity"]["rowsNotInFlushedFinding"] == []


def test_a_week_of_daily_releases_is_one_write_against_the_legacy_stream(week):
    assert week["staged"]["writesPerDay"] == [0, 0, 0, 0, 0, 0, 1]
    assert week["staged"]["umbrellas"] == 1 and week["staged"]["children"] == 0
    assert week["legacy"]["totalWrites"] > 50 and week["legacy"]["childIssuesFiled"] == 5


def test_the_only_legacy_candidate_not_filed_is_the_transient_one_and_it_is_reported(week):
    assert week["parity"]["legacyFiledButAbsentAtFlush"] == ["garrytan/transient"]
    assert week["parity"]["transientReportedNotFiled"] == ["garrytan/gbrain:transient"]
