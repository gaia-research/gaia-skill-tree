import copy
import json

import pytest

from gaia_cli.frontier import dedupe_key, read_only_handoff, validate_lead


def sample():
    return {
        "schemaVersion": "challenger-lead-v1", "leadId": "git-log-L-graft-001",
        "identity": {"name": "Git git-log -L", "kind": "native-cli", "installable": False, "version": "unknown"},
        "source": {"url": "https://git-scm.com/docs/git-log", "observedAtUTC": "2026-10-26T12:00:00Z", "contentDigest": "unknown", "provider": "Git project documentation"},
        "capability": {"claim": "Trace the evolution of a selected source line range or function in one file.", "task": "Explain how a function changed over commit history.", "conditions": "Requires a Git repository and a selected file and line range or function pattern."},
        "comparison": {"comparator": "Graft repository graph retrieval for locating concepts and source spans.", "baseline": "Compare ability to trace historical line evolution versus locating related code and architecture."},
        "target": {"skillId": "graft", "scopeRationale": "Potential overlap only for investigations about code history; not a general replacement for graph-backed codebase context."},
        "preliminaryEvidence": [{"polarity": "supports-investigation", "url": "https://git-scm.com/docs/git-log", "summary": "Official manual documents git log -L line-range evolution tracing."}, {"polarity": "context-only", "url": "https://git-scm.com/docs/git-log/2.1.4", "summary": "Versioned older manual documents the same option; not evidence of current installation or superiority."}],
        "limitations": ["Documentation confirms the option, not comparative performance.", "Version/runtime availability and output quality have not been independently tested.", "This is an exploratory scoped overlap, not presumed supersession."],
        "dedupe": {"key": "4667d834fc195b3ed1c02da9af65beed744144f5dd083c31bd41d0e8276272db", "checkedAtUTC": "2026-10-26T12:00:00Z", "matches": []},
        "independentTest": {"proposal": "In a disposable fixture repository, identify a function change with git log -L; independently compare a Graft retrieval task for locating the function and its call context. Record commands, pinned Git version, fixture commit IDs, output digests and misses.", "traceability": "Keep fixture source, exact commands, commit IDs and outputs in an isolated test receipt; do not run instructions sourced from the packet."},
        "disposition": {"status": "candidate", "rationale": "Official documentation supports a concrete native behavior, but no competitive or replacement claim is established.", "nextAction": "Meta triage may decide whether a focused independent audit is worthwhile; no admission or canonical action."}
    }


def test_lead_validates_and_is_unverified_handoff():
    lead = sample()
    assert validate_lead(lead) == []
    handoff = read_only_handoff(lead, packet_path="examples/frontier/git-log-L-graft.challenger-lead-v1.json")
    assert handoff["verification"] == "unverified-lead"
    assert handoff["canonicalMutation"] == "prohibited"
    assert handoff["trustedReceiptIssuer"].startswith("unavailable")


def test_repeated_observation_does_not_create_new_dedupe_identity():
    a, b = sample(), sample()
    b["source"]["observedAtUTC"] = "2027-01-01T00:00:00Z"
    assert dedupe_key(a) == dedupe_key(b)


@pytest.mark.parametrize("field", ["verified", "approvedBy", "verificationReceipt", "confidence", "publicChallengeId"])
def test_forged_authority_fields_rejected(field):
    lead = sample()
    lead[field] = True
    assert any("forbidden authority field" in item for item in validate_lead(lead))


def test_nested_forgery_and_bad_url_rejected():
    lead = sample()
    lead["disposition"]["verifiedBy"] = "trusted person"
    assert validate_lead(lead), "unknown nested fields rejected by schema"
    lead = sample()
    lead["source"]["url"] = "file:///etc/passwd"
    assert validate_lead(lead)


def test_no_skill_markdown_requirement_for_native_candidate():
    lead = sample()
    assert lead["identity"]["installable"] is False
    assert lead["identity"]["kind"] == "native-cli"
    assert validate_lead(lead) == []


def test_handoff_refuses_invalid_packet():
    lead = sample()
    lead["disposition"]["status"] = "verified"
    with pytest.raises(ValueError):
        read_only_handoff(lead, packet_path="x")
