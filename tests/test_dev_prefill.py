"""Tests for the gaia-curate v2 prefill module (deterministic, no model required).

Uses synthetic in-memory embeddings and a stubbed embed_query so no
sentence-transformers download is needed.
"""
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from gaia_cli import prefill


THRESHOLDS = {"strongMap": 0.72, "weakMap": 0.45, "topK": 3}


def makeEmbeddings():
    """Synthetic embeddings: a few generics + named skills on orthogonal-ish axes."""
    return {
        "model": "all-MiniLM-L6-v2",
        "dimensions": 3,
        "generatedAt": "2026-07-29",
        "entries": [
            {"id": "automated-testing", "vector": [1.0, 0.0, 0.0]},
            {"id": "ui-design", "vector": [0.0, 1.0, 0.0]},
            {"id": "ux-design", "vector": [0.0, 0.99, 0.02]},
            {"id": "data-modeling", "vector": [0.0, 0.0, 1.0]},
            {"id": "alice/pytest-magic", "vector": [0.98, 0.05, 0.0]},
            {"id": "bob/figma-flows", "vector": [0.02, 0.98, 0.0]},
        ],
    }


class TestDeriveMatchTier:
    def test_strong(self):
        assert prefill.deriveMatchTier(0.80, THRESHOLDS) == "strong"

    def test_strong_boundary(self):
        assert prefill.deriveMatchTier(0.72, THRESHOLDS) == "strong"

    def test_weak(self):
        assert prefill.deriveMatchTier(0.60, THRESHOLDS) == "weak"

    def test_weak_boundary(self):
        assert prefill.deriveMatchTier(0.45, THRESHOLDS) == "weak"

    def test_dropped(self):
        assert prefill.deriveMatchTier(0.30, THRESHOLDS) is None


class TestRankGenericOptions:
    def test_strong_generic_only(self):
        """A candidate aligned with automated-testing yields a strong generic match, no named."""
        emb = makeEmbeddings()
        options = prefill.rankGenericOptions([1.0, 0.0, 0.0], emb, THRESHOLDS)
        assert options[0]["genericId"] == "automated-testing"
        assert options[0]["matchTier"] == "strong"
        assert 0 <= options[0]["similarity"] <= 1
        # Named ids never appear in generic options.
        assert all("/" not in o["genericId"] for o in options)

    def test_weak_tier_emitted(self):
        """A mid-similarity candidate produces weak options, no strong."""
        emb = makeEmbeddings()
        # Equidistant in the x-y-z octant: cosine to each axis-aligned generic
        # is 1/sqrt(3) ~= 0.577, which falls in the weak band (0.45..0.72).
        import math
        vec = [1.0, 1.0, 1.0]
        options = prefill.rankGenericOptions(vec, emb, THRESHOLDS)
        assert options
        tiers = {o["matchTier"] for o in options}
        assert "weak" in tiers
        assert "strong" not in tiers

    def test_dropped_below_weak(self):
        """A candidate orthogonal to everything drops all options."""
        emb = makeEmbeddings()
        options = prefill.rankGenericOptions([0.0, 0.0, 0.0], emb, THRESHOLDS)
        assert options == []

    def test_topk_cap(self):
        """No more than topK (and never > 3) options are emitted."""
        emb = makeEmbeddings()
        # All-ones aligns partially with several generics.
        options = prefill.rankGenericOptions([0.6, 0.6, 0.6], emb, {"strongMap": 0.4, "weakMap": 0.1, "topK": 3})
        assert len(options) <= 3

    def test_exact_dedupe_of_generic_ids(self):
        """Duplicate generic ids in the ranking collapse to one option."""
        emb = makeEmbeddings()
        emb["entries"].append({"id": "automated-testing", "vector": [1.0, 0.0, 0.0]})
        options = prefill.rankGenericOptions([1.0, 0.0, 0.0], emb, THRESHOLDS)
        ids = [o["genericId"] for o in options]
        assert ids.count("automated-testing") == 1


class TestRankNamedNeighbors:
    def test_named_only(self):
        emb = makeEmbeddings()
        neighbors = prefill.rankNamedNeighbors([1.0, 0.0, 0.0], emb, THRESHOLDS)
        assert neighbors
        assert all("/" in n["id"] for n in neighbors)
        assert neighbors[0]["id"] == "alice/pytest-magic"


class TestImpliedFusionFlags:
    def test_two_strong_generics_flagged(self):
        """ui-design + ux-design both strong => implied fusion flag."""
        emb = makeEmbeddings()
        # Vector between ui-design and ux-design (both near [0,1,0]).
        options = prefill.rankGenericOptions([0.0, 1.0, 0.01], emb, {"strongMap": 0.5, "weakMap": 0.2, "topK": 3})
        flags = prefill.detectImpliedFusionFlags(options, THRESHOLDS)
        assert any(f["code"] == "IMPLIED_FUSION" for f in flags)
        fusion = next(f for f in flags if f["code"] == "IMPLIED_FUSION")
        assert set(fusion["generics"]) <= {"ui-design", "ux-design"}

    def test_single_strong_no_flag(self):
        emb = makeEmbeddings()
        options = prefill.rankGenericOptions([1.0, 0.0, 0.0], emb, THRESHOLDS)
        flags = prefill.detectImpliedFusionFlags(options, THRESHOLDS)
        assert not any(f["code"] == "IMPLIED_FUSION" for f in flags)


class TestBuildPacketSelfValidates:
    def test_packet_is_schema_valid(self):
        emb = makeEmbeddings()
        packet = prefill.buildPrefillPacket(
            candidateId="alice/pytest-magic",
            name="Pytest Magic",
            description="Advanced pytest fixtures and parametrization patterns.",
            canonicalUrl="https://github.com/alice/pytest-magic/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
        )
        assert packet["contractVersion"] == "discovery-packet-v2"
        errors = prefill.selfValidatePacket(packet)
        assert errors == [], f"packet failed validation: {errors}"

    def test_suite_block_carried(self):
        emb = makeEmbeddings()
        packet = prefill.buildPrefillPacket(
            candidateId="alice/pytest-magic",
            name="Pytest Magic",
            description="Advanced pytest fixtures.",
            canonicalUrl="https://github.com/alice/pytest-magic/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
            suite={"role": "component", "suiteId": "alice-testing-suite"},
        )
        assert packet["suite"]["role"] == "component"
        assert prefill.selfValidatePacket(packet) == []

    def test_suite_capstone_fanout(self):
        """Capstone packet with component ids is valid."""
        emb = makeEmbeddings()
        packet = prefill.buildPrefillPacket(
            candidateId="alice/test-suite",
            name="Test Suite",
            description="A full testing suite capstone.",
            canonicalUrl="https://github.com/alice/test-suite/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
            suite={
                "role": "capstone",
                "suiteId": "alice-testing-suite",
                "componentCandidateIds": ["alice/pytest-magic", "alice/coverage"],
            },
        )
        assert packet["suite"]["componentCandidateIds"] == ["alice/pytest-magic", "alice/coverage"]
        assert prefill.selfValidatePacket(packet) == []

    def test_named_neighbors_flag_present(self):
        emb = makeEmbeddings()
        packet = prefill.buildPrefillPacket(
            candidateId="carol/new",
            name="Testing Helper",
            description="Test helper utilities.",
            canonicalUrl="https://github.com/carol/new/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
        )
        codes = {f.get("code") for f in packet["flags"]}
        assert "SUITE_COMPONENT_CANDIDATES" in codes


class TestLoadThresholds:
    def test_reads_meta_curationprefill(self, tmp_path):
        schemaDir = tmp_path / "registry" / "schema"
        schemaDir.mkdir(parents=True)
        (schemaDir / "meta.json").write_text(
            json.dumps({"curationPrefill": {"strongMap": 0.8, "weakMap": 0.5, "topK": 2}}),
            encoding="utf-8",
        )
        thresholds = prefill.loadPrefillThresholds(str(tmp_path))
        assert thresholds["strongMap"] == 0.8
        assert thresholds["weakMap"] == 0.5
        assert thresholds["topK"] == 2

    def test_falls_back_to_defaults(self, tmp_path):
        thresholds = prefill.loadPrefillThresholds(str(tmp_path))
        # No meta.json under tmp_path; bundled snapshot (0.72/0.45/3) or defaults.
        assert thresholds["strongMap"] == prefill.DEFAULT_STRONG_MAP
        assert thresholds["weakMap"] == prefill.DEFAULT_WEAK_MAP


class TestDeterminism:
    def test_same_inputs_same_packet(self):
        emb = makeEmbeddings()
        kwargs = dict(
            candidateId="alice/pytest-magic",
            name="Pytest Magic",
            description="Advanced pytest fixtures.",
            canonicalUrl="https://github.com/alice/pytest-magic/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
        )
        p1 = prefill.buildPrefillPacket(**kwargs)
        p2 = prefill.buildPrefillPacket(**kwargs)
        assert p1 == p2
