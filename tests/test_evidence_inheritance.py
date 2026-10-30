"""Tests for the rank-less generic / inherited-evidence model."""

import json
import os
import sys
import unittest
import pytest
pytestmark = [pytest.mark.integration]


sys.path.insert(
    0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src"))
)

from gaia_cli.evidence import (
    EVIDENCE_TYPE_ALIASES,
    canonicalSourceUrl,
    inherited_evidence,
    merge_evidence,
    build_generic_evidence_map,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestInheritedEvidence(unittest.TestCase):
    def test_named_inherits_generic_capability_evidence(self):
        generic = {
            "id": "automated-testing",
            "evidence": [
                {"class": "A", "source": "https://arxiv.org/abs/0001"},
            ],
        }
        named = {
            "id": "x/pytest",
            "evidence": [
                {"class": "C", "source": "https://github.com/x/pytest"},
            ],
        }
        pool = inherited_evidence(named, generic)
        sources = {e["source"] for e in pool}
        self.assertEqual(
            sources, {"https://arxiv.org/abs/0001", "https://github.com/x/pytest"}
        )

    def test_merge_evidence_edge_cases(self):
        self.assertEqual(merge_evidence(), [])
        self.assertEqual(merge_evidence(None, None), [])
        self.assertEqual(merge_evidence([], []), [])
        self.assertEqual(merge_evidence([{}], [{}]), [{}])
        self.assertEqual(
            merge_evidence(
                None, [{"source": "s1"}], [], [{"source": "s1"}, {"source": "s2"}]
            ),
            [{"source": "s1"}, {"source": "s2"}],
        )

    def test_dedup_by_source(self):
        shared = {"class": "A", "source": "https://arxiv.org/abs/0001"}
        pool = merge_evidence([shared], [dict(shared)])
        self.assertEqual(len(pool), 1)

    def test_no_generic_evidence(self):
        named = {"id": "x/y", "evidence": [{"class": "C", "source": "s"}]}
        self.assertEqual(len(inherited_evidence(named, None)), 1)

    def test_build_generic_evidence_map(self):
        skills = [{"id": "a", "evidence": [{"source": "s"}]}, {"id": "b"}]
        m = build_generic_evidence_map(skills)
        self.assertEqual(m["a"], [{"source": "s"}])
        self.assertEqual(m["b"], [])


class TestWithinTypeDedup(unittest.TestCase):
    """merge_evidence dedups on (type, canonical source), never source alone.

    Regression for the Yggdrasil IV October calibration: a row of a different
    type at the same URL as a legacy row was silently dropped from Trust
    Magnitude. The documented rule is same-source dedup *within type*
    (docs/agents/curation-authority-map.md; ``_dedupeSameSource``).
    """

    URL = "https://github.com/o/r"

    def test_different_types_at_same_url_both_kept(self):
        stars = {"type": "github-stars-own", "source": self.URL, "stars": 100}
        attest = {"type": "self-attestation", "source": self.URL}
        pool = merge_evidence([stars], [attest])
        self.assertEqual(pool, [stars, attest])

    def test_different_types_within_one_group_both_kept(self):
        rows = [
            {"type": "repo", "source": self.URL},
            {"type": "peer-review", "source": self.URL},
        ]
        self.assertEqual(len(merge_evidence(rows)), 2)

    def test_same_type_same_url_first_wins(self):
        first = {"type": "repo-own", "source": self.URL, "commits": 1}
        second = {"type": "repo-own", "source": self.URL, "commits": 2}
        self.assertEqual(merge_evidence([first], [second]), [first])

    def test_legacy_type_alias_normalized(self):
        legacy = {"type": "repo", "source": self.URL}
        modern = {"type": "repo-own", "source": self.URL}
        self.assertEqual(merge_evidence([legacy], [modern]), [legacy])

    def test_source_is_canonicalized(self):
        a = {"type": "repo-own", "source": "https://GitHub.com/o/r/tree/main/x/"}
        b = {"type": "repo-own", "source": "https://github.com/o/r/blob/main/x#frag"}
        self.assertEqual(merge_evidence([a], [b]), [a])

    def test_inherited_cross_type_row_survives(self):
        generic = {"evidence": [{"type": "peer-review", "source": self.URL}]}
        named = {"evidence": [{"type": "repo-own", "source": self.URL}]}
        pool = inherited_evidence(named, generic)
        self.assertEqual([r["type"] for r in pool], ["repo-own", "peer-review"])

    def test_dedup_key_matches_trust_magnitude_normalization(self):
        from gaia_cli import trustMagnitude as tm

        for raw in (
            "https://GitHub.com/o/r/tree/main/",
            "https://github.com/o/r#x",
            "  https://github.com/o/r/  ",
            "",
            None,
        ):
            self.assertEqual(tm._canonicalUrl(raw), canonicalSourceUrl(raw))
        self.assertIs(tm.TYPE_ALIASES, EVIDENCE_TYPE_ALIASES)

    def test_trust_magnitude_counts_both_types_at_one_url(self):
        from gaia_cli.trustMagnitude import computeTrustMagnitude

        base = {"id": "x/y", "evidence": [{"type": "repo-own", "source": self.URL,
                                           "commits": 400, "contributors": 20}]}
        withPeer = {"id": "x/y", "evidence": base["evidence"] + [
            {"type": "peer-review", "source": self.URL, "class": "A", "grade": "C"}
        ]}
        self.assertGreater(
            computeTrustMagnitude(withPeer, {}), computeTrustMagnitude(base, {})
        )

    def test_effective_pool_layers_cross_type_generic_row_as_generic(self):
        from gaia_cli.trustMagnitude import _effectivePool

        generic = {"id": "g", "evidence": [{"type": "peer-review", "source": self.URL}]}
        named = {"id": "x/y", "genericSkillRef": "g",
                 "evidence": [{"type": "repo-own", "source": self.URL}]}
        pool = _effectivePool(named, {"g": generic})
        layers = {r["type"]: r.get("layer") for r in pool}
        self.assertEqual(layers["peer-review"], "generic")
        self.assertNotEqual(layers["repo-own"], "generic")


class TestRanklessGenerics(unittest.TestCase):
    def test_no_generic_node_has_level_or_demerits(self):
        graph = json.load(
            open(os.path.join(REPO_ROOT, "registry", "gaia.json"), encoding="utf-8")
        )
        bad = [
            s["id"]
            for s in graph["skills"]
            if "level" in s or "demerits" in s or "realVariants" in s
        ]
        self.assertEqual(bad, [], f"Generic refs must be rank-less; offenders: {bad}")

    def test_named_skills_retain_levels(self):
        idx = json.load(
            open(
                os.path.join(REPO_ROOT, "registry", "named-skills.json"),
                encoding="utf-8",
            )
        )
        valid = {"1★", "2★", "3★", "4★", "5★", "6★"}
        for entries in idx["buckets"].values():
            for e in entries:
                self.assertIn(
                    e["level"], valid, f"{e['id']} has invalid level {e['level']}"
                )


if __name__ == "__main__":
    unittest.main()
