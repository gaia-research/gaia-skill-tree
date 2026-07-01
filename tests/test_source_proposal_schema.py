"""Tests for sourceProposal.schema.json and sourceProposalReport.schema.json.

Validates that:
- Valid proposals pass schema validation
- Invalid proposals (bad fields, missing required, extra fields) are rejected
- The report wrapper validates correctly
- The dryRun=true constraint is enforced at the proposal and report levels
"""

from __future__ import annotations

import json
import os

import pytest
import jsonschema

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SCHEMA_DIR = os.path.join(REPO_ROOT, "registry", "schema")
FIXTURES_DIR = os.path.join(REPO_ROOT, "tests", "fixtures")

def loadSchema(name: str) -> dict:
    path = os.path.join(SCHEMA_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def loadFixture(name: str) -> dict:
    path = os.path.join(FIXTURES_DIR, name)
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)

def makeResolver():
    """Create a RefResolver that can resolve $ref across schema files."""
    store = {}
    for fname in os.listdir(SCHEMA_DIR):
        if fname.endswith(".schema.json"):
            spath = os.path.join(SCHEMA_DIR, fname)
            with open(spath, "r", encoding="utf-8") as f:
                s = json.load(f)
            # Register by both $id and filename for local refs
            if "$id" in s:
                store[s["$id"]] = s
            store[fname] = s
    baseUri = "file://" + SCHEMA_DIR + "/"
    return jsonschema.RefResolver(baseUri, {}, store=store)


# ---------------------------------------------------------------------------
# sourceProposal.schema.json — valid proposals
# ---------------------------------------------------------------------------

class TestSourceProposalValid:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.schema = loadSchema("sourceProposal.schema.json")
        self.resolver = makeResolver()

    def test_social_signal_proposal(self):
        data = loadFixture("source_proposal_valid.json")
        jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_github_stars_proposal(self):
        data = loadFixture("source_proposal_valid_github.json")
        jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_reviewed_proposal(self):
        data = loadFixture("source_proposal_valid_reviewed.json")
        jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_minimal_valid_proposal(self):
        """A proposal with only required fields should pass."""
        data = {
            "proposalId": "minimal-test-a1b2c3d4",
            "skillId": "contributor/skill-name",
            "source": "https://example.com/evidence",
            "evidenceType": "social-signal",
            "discoveredAt": "2026-07-02T10:00:00Z",
            "discoveredBy": "nova-gaia",
            "crawlerBackend": "firecrawl-search",
            "confidence": 0.5,
            "rationale": "A minimal but valid rationale for this evidence source.",
            "dryRun": True
        }
        jsonschema.validate(data, self.schema, resolver=self.resolver)


# ---------------------------------------------------------------------------
# sourceProposal.schema.json — invalid proposals
# ---------------------------------------------------------------------------

class TestSourceProposalInvalid:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.schema = loadSchema("sourceProposal.schema.json")
        self.resolver = makeResolver()

    def test_bad_fields_rejected(self):
        data = loadFixture("source_proposal_invalid_fields.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_missing_required_rejected(self):
        data = loadFixture("source_proposal_invalid_missing.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_extra_fields_rejected(self):
        """additionalProperties: false must block unknown fields."""
        data = loadFixture("source_proposal_invalid_extra_fields.json")
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_dryrun_false_rejected(self):
        """Standalone proposals must remain inside the dry-run boundary."""
        data = loadFixture("source_proposal_valid.json")
        data["dryRun"] = False
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_missing_dryrun_rejected(self):
        """Standalone proposals must explicitly declare dryRun: true."""
        data = loadFixture("source_proposal_valid.json")
        del data["dryRun"]
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_confidence_out_of_range(self):
        data = {
            "proposalId": "conf-test-a1b2c3d4",
            "skillId": "contributor/skill-name",
            "source": "https://example.com/evidence",
            "evidenceType": "social-signal",
            "discoveredAt": "2026-07-02T10:00:00Z",
            "discoveredBy": "nova-gaia",
            "crawlerBackend": "test",
            "confidence": 1.5,
            "rationale": "Confidence is above 1.0 which should be rejected."
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_negative_confidence_rejected(self):
        data = {
            "proposalId": "neg-conf-a1b2c3d4",
            "skillId": "contributor/skill-name",
            "source": "https://example.com/evidence",
            "evidenceType": "social-signal",
            "discoveredAt": "2026-07-02T10:00:00Z",
            "discoveredBy": "nova-gaia",
            "crawlerBackend": "test",
            "confidence": -0.1,
            "rationale": "Negative confidence should be rejected by the schema."
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_skillid_must_be_named_format(self):
        """skillId must be contributor/skill-name, not a bare generic ID."""
        data = {
            "proposalId": "bare-id-a1b2c3d4",
            "skillId": "just-a-bare-id",
            "source": "https://example.com/evidence",
            "evidenceType": "social-signal",
            "discoveredAt": "2026-07-02T10:00:00Z",
            "discoveredBy": "nova-gaia",
            "crawlerBackend": "test",
            "confidence": 0.5,
            "rationale": "A bare skill ID without contributor prefix should be rejected."
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_short_rationale_rejected(self):
        data = {
            "proposalId": "short-rat-a1b2c3d4",
            "skillId": "contributor/skill-name",
            "source": "https://example.com/evidence",
            "evidenceType": "social-signal",
            "discoveredAt": "2026-07-02T10:00:00Z",
            "discoveredBy": "nova-gaia",
            "crawlerBackend": "test",
            "confidence": 0.5,
            "rationale": "too short"
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_empty_discoveredby_rejected(self):
        data = {
            "proposalId": "empty-by-a1b2c3d4",
            "skillId": "contributor/skill-name",
            "source": "https://example.com/evidence",
            "evidenceType": "social-signal",
            "discoveredAt": "2026-07-02T10:00:00Z",
            "discoveredBy": "",
            "crawlerBackend": "test",
            "confidence": 0.5,
            "rationale": "Empty discoveredBy string should be rejected."
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_invalid_adversarial_vote_rejected(self):
        data = {
            "proposalId": "bad-vote-a1b2c3d4",
            "skillId": "contributor/skill-name",
            "source": "https://example.com/evidence",
            "evidenceType": "social-signal",
            "discoveredAt": "2026-07-02T10:00:00Z",
            "discoveredBy": "nova-gaia",
            "crawlerBackend": "test",
            "confidence": 0.5,
            "rationale": "Adversarial review with invalid vote enum value.",
            "adversarialReview": {
                "status": "invalid-status",
                "skepticVotes": []
            }
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)


# ---------------------------------------------------------------------------
# sourceProposalReport.schema.json — valid reports
# ---------------------------------------------------------------------------

class TestSourceProposalReportValid:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.schema = loadSchema("sourceProposalReport.schema.json")
        self.resolver = makeResolver()

    def test_full_report(self):
        data = loadFixture("source_proposal_report_valid.json")
        jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_empty_proposals_report(self):
        """A crawl run that found nothing should still be a valid report."""
        data = {
            "reportId": "20260702-empty-001",
            "generatedAt": "2026-07-02T14:00:00Z",
            "generatedBy": "nova-gaia",
            "pipelinePhase": "discovery",
            "dryRun": True,
            "proposals": []
        }
        jsonschema.validate(data, self.schema, resolver=self.resolver)


# ---------------------------------------------------------------------------
# sourceProposalReport.schema.json — invalid reports
# ---------------------------------------------------------------------------

class TestSourceProposalReportInvalid:
    @pytest.fixture(autouse=True)
    def setup(self):
        self.schema = loadSchema("sourceProposalReport.schema.json")
        self.resolver = makeResolver()

    def test_dryrun_false_rejected(self):
        """dryRun must be true in this implementation phase."""
        data = {
            "reportId": "20260702-live-001",
            "generatedAt": "2026-07-02T14:00:00Z",
            "generatedBy": "nova-gaia",
            "pipelinePhase": "discovery",
            "dryRun": False,
            "proposals": []
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_wrong_identity_rejected(self):
        """Only nova-gaia is authorized as generatedBy."""
        data = {
            "reportId": "20260702-wrong-001",
            "generatedAt": "2026-07-02T14:00:00Z",
            "generatedBy": "rogue-bot",
            "pipelinePhase": "discovery",
            "dryRun": True,
            "proposals": []
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_missing_proposals_rejected(self):
        data = {
            "reportId": "20260702-noprops-001",
            "generatedAt": "2026-07-02T14:00:00Z",
            "generatedBy": "nova-gaia",
            "pipelinePhase": "discovery",
            "dryRun": True
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_ingestion_phase_rejected(self):
        """Reports are dry-run only until a publisher exists."""
        data = {
            "reportId": "20260702-ingest-001",
            "generatedAt": "2026-07-02T14:00:00Z",
            "generatedBy": "nova-gaia",
            "pipelinePhase": "ingestion",
            "dryRun": True,
            "proposals": []
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_invalid_phase_rejected(self):
        data = {
            "reportId": "20260702-badphase-001",
            "generatedAt": "2026-07-02T14:00:00Z",
            "generatedBy": "nova-gaia",
            "pipelinePhase": "mutate-everything",
            "dryRun": True,
            "proposals": []
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)

    def test_report_rejects_invalid_nested_proposal(self):
        """An invalid proposal inside a report should fail report validation."""
        data = {
            "reportId": "20260702-nested-001",
            "generatedAt": "2026-07-02T14:00:00Z",
            "generatedBy": "nova-gaia",
            "pipelinePhase": "discovery",
            "dryRun": True,
            "proposals": [
                {
                    "proposalId": "bad",
                    "skillId": "InvalidFormat",
                    "source": "not-a-url",
                    "evidenceType": "WRONG",
                    "confidence": 2.0,
                    "rationale": "short"
                }
            ]
        }
        with pytest.raises(jsonschema.ValidationError):
            jsonschema.validate(data, self.schema, resolver=self.resolver)
