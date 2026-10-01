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


class TestParseAndValidateVector:
    def test_valid_envelope(self):
        env = {
            "model": "all-MiniLM-L6-v2",
            "revision": None,
            "vector": [1.0, 0.0, 0.0],
        }
        res = prefill.parseAndValidateVector(
            env,
            expectedModel="all-MiniLM-L6-v2",
            expectedRevision=None,
            expectedDim=3,
        )
        assert res == [1.0, 0.0, 0.0]

    def test_valid_plain_list(self):
        res = prefill.parseAndValidateVector([0.5, 0.5, 0.0], expectedDim=3)
        assert res == [0.5, 0.5, 0.0]

    def test_reject_boolean_in_vector(self):
        with pytest.raises(ValueError, match="invalid or non-finite"):
            prefill.parseAndValidateVector([True, 0.0, 0.0], expectedDim=3)

    def test_reject_nan_and_inf(self):
        with pytest.raises(ValueError, match="invalid or non-finite"):
            prefill.parseAndValidateVector([float("nan"), 0.0, 0.0], expectedDim=3)
        with pytest.raises(ValueError, match="invalid or non-finite"):
            prefill.parseAndValidateVector([float("inf"), 0.0, 0.0], expectedDim=3)

    def test_reject_dimension_mismatch(self):
        with pytest.raises(ValueError, match="dimension"):
            prefill.parseAndValidateVector([1.0, 0.0], expectedDim=3)

    def test_reject_model_mismatch(self):
        env = {"model": "BAAI/bge-small-en-v1.5", "vector": [1.0, 0.0, 0.0]}
        with pytest.raises(ValueError, match="does not match active artifact model"):
            prefill.parseAndValidateVector(env, expectedModel="all-MiniLM-L6-v2", expectedDim=3)

    def test_reject_revision_mismatch(self):
        env = {"model": "all-MiniLM-L6-v2", "revision": "v2", "vector": [1.0, 0.0, 0.0]}
        with pytest.raises(ValueError, match="does not match active artifact revision"):
            prefill.parseAndValidateVector(
                env, expectedModel="all-MiniLM-L6-v2", expectedRevision="v1", expectedDim=3
            )


class TestAntiSpoofingArtifactGate:
    def test_spoofed_artifact_gate_rejected(self):
        """Frontmatter declaring artifactGate: valid-skill without name/description is rejected."""
        spoofed_skill_md = (
            "---\n"
            "artifactGate: valid-skill\n"
            "---\n"
            "# Spoofed Skill\n"
        )
        fake_fetcher = lambda url: spoofed_skill_md.encode("utf-8")
        emb = makeEmbeddings()
        packet = prefill.buildPrefillPacket(
            candidateId="attacker/spoofed",
            name="Spoofed",
            description="Trying to spoof artifactGate",
            canonicalUrl="https://github.com/attacker/spoofed/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
            registryPath=".",
            fetcher=fake_fetcher,
        )
        assert packet["artifactGate"] == "rejected-missing-frontmatter"
        assert packet["lifecycle"] == ["discovered", "fetched", "rejected"]
        assert packet["decision"]["value"] == "NOT_A_SKILL"

    def test_valid_frontmatter_passes(self):
        valid_skill_md = (
            "---\n"
            "name: Legitimate Skill\n"
            "description: A real skill with valid frontmatter.\n"
            "---\n"
            "# Content\n"
        )
        fake_fetcher = lambda url: valid_skill_md.encode("utf-8")
        emb = makeEmbeddings()
        packet = prefill.buildPrefillPacket(
            candidateId="author/legitimate",
            name="Legitimate Skill",
            description="A real skill with valid frontmatter.",
            canonicalUrl="https://github.com/author/legitimate/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
            registryPath=".",
            fetcher=fake_fetcher,
        )
        assert packet["artifactGate"] == "valid-skill"
        assert "mapped" in packet["lifecycle"]
        assert packet["decision"]["value"] == "DEFER"


class TestBoundedFetch:
    def test_fetch_exceeding_1mb_rejected(self):
        huge_bytes = b"x" * (1024 * 1024 + 10)
        fake_fetcher = lambda url: huge_bytes
        host, raw, content, sha = prefill.fetchCandidateSource(
            "https://github.com/owner/repo/blob/main/SKILL.md",
            fetcher=fake_fetcher,
        )
        assert content is None
        assert sha is None


class TestFlagsSemantics:
    def test_implied_fusion_flag_note_is_ambiguity(self):
        options = [
            {"genericId": "g1", "matchTier": "strong", "similarity": 0.85, "rationale": "r1"},
            {"genericId": "g2", "matchTier": "strong", "similarity": 0.82, "rationale": "r2"},
        ]
        flags = prefill.detectImpliedFusionFlags(options, THRESHOLDS)
        assert len(flags) == 1
        note = flags[0]["note"]
        assert "ambiguity" in note or "overlap" in note
        assert "automatic fusion requirement" in note

    def test_named_neighbors_note_is_advisory(self):
        emb = makeEmbeddings()
        packet = prefill.buildPrefillPacket(
            candidateId="author/skill",
            name="Skill",
            description="Skill description.",
            canonicalUrl="https://github.com/author/skill/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
        )
        neighbor_flag = next(f for f in packet["flags"] if f["code"] == "SUITE_COMPONENT_CANDIDATES")
        assert "advisory context only" in neighbor_flag["note"]
        assert "not a suite declaration" in neighbor_flag["note"]


class TestRetrievalProvenance:
    def test_packet_binds_retrieval_object(self):
        emb = makeEmbeddings()
        emb["fingerprint"] = "abc123fingerprint"
        packet = prefill.buildPrefillPacket(
            candidateId="author/skill",
            name="Skill",
            description="Skill description.",
            canonicalUrl="https://github.com/author/skill/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
        )
        assert "retrieval" in packet
        retrieval = packet["retrieval"]
        assert retrieval["model"] == "all-MiniLM-L6-v2"
        assert retrieval["fingerprint"] == "abc123fingerprint"
        assert retrieval["thresholds"] == THRESHOLDS

    def test_legacy_artifact_has_no_inferred_revision(self):
        """When embeddings artifact has no manifest/config, revision must be None (never inferred)."""
        emb = makeEmbeddings()  # legacy artifact without config or revision
        packet = prefill.buildPrefillPacket(
            candidateId="author/skill",
            name="Skill",
            description="Skill description.",
            canonicalUrl="https://github.com/author/skill/blob/main/SKILL.md",
            sourceLane="source-repository",
            embeddings=emb,
            thresholds=THRESHOLDS,
            precomputedVector=[1.0, 0.0, 0.0],
        )
        assert packet["retrieval"]["revision"] is None


class TestGenericSnapshot:
    def test_build_generic_snapshot_from_canonical_nodes_no_gaia_json(self, tmp_path):
        """Fresh checkout with nodes/ directory but no gaia.json builds sorted generic snapshot."""
        nodes_basic = tmp_path / "registry" / "nodes" / "basic"
        nodes_fusion = tmp_path / "registry" / "nodes" / "fusion"
        nodes_basic.mkdir(parents=True)
        nodes_fusion.mkdir(parents=True)

        (nodes_basic / "zebra-skill.json").write_text(json.dumps({
            "id": "zebra-skill",
            "name": "Zebra Skill",
            "type": "basic",
        }))
        (nodes_fusion / "alpha-skill.json").write_text(json.dumps({
            "id": "alpha-skill",
            "name": "Alpha Skill",
            "type": "fusion",
        }))

        snapshot = prefill.buildGenericSnapshot(tmp_path)
        assert snapshot is not None
        assert snapshot["command"] == "gaia dev list --generic --json"
        generics = snapshot["generics"]
        assert len(generics) == 2
        # Must be sorted by id
        assert generics[0]["id"] == "alpha-skill"
        assert generics[0]["kind"] == "generic"
        assert generics[1]["id"] == "zebra-skill"
        assert generics[1]["kind"] == "generic"

    def test_empty_nodes_dir_does_not_fallback_to_stale_gaia_json(self, tmp_path):
        """Intentional empty registry with nodes/ directory must not fall back to stale gaia.json."""
        nodes_dir = tmp_path / "registry" / "nodes"
        nodes_dir.mkdir(parents=True)
        # Create stale gaia.json
        (tmp_path / "registry" / "gaia.json").write_text(json.dumps({
            "skills": [{"id": "stale-generic", "name": "Stale"}]
        }))

        snapshot = prefill.buildGenericSnapshot(tmp_path)
        assert snapshot is None

    def test_fallback_to_legacy_gaia_json_when_no_nodes_dir(self, tmp_path):
        """Legacy registry without nodes/ directory falls back to gaia.json."""
        reg_dir = tmp_path / "registry"
        reg_dir.mkdir(parents=True)
        (reg_dir / "gaia.json").write_text(json.dumps({
            "skills": [{"id": "legacy-generic", "name": "Legacy Generic"}]
        }))

        snapshot = prefill.buildGenericSnapshot(tmp_path)
        assert snapshot is not None
        assert len(snapshot["generics"]) == 1
        assert snapshot["generics"][0]["id"] == "legacy-generic"


class TestSafeCandidateSlug:
    def test_valid_slugs(self):
        assert prefill.safeCandidateSlug("owner/repo") == "owner-repo"
        assert prefill.safeCandidateSlug("org/sub-team/repo") == "org-sub-team-repo"
        assert prefill.safeCandidateSlug("simple-id") == "simple-id"

    def test_reject_unsafe_path_traversal(self):
        with pytest.raises(ValueError, match="Unsafe or invalid"):
            prefill.safeCandidateSlug("../traversal")
        with pytest.raises(ValueError, match="Unsafe or invalid"):
            prefill.safeCandidateSlug("foo/../../bar")
        with pytest.raises(ValueError, match="non-empty string"):
            prefill.safeCandidateSlug("")
        with pytest.raises(ValueError, match="Unsafe or invalid"):
            prefill.safeCandidateSlug("bad space/id")
