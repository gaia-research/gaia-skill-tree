"""Tests for the rank-less generic / inherited-evidence model."""

import json
import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from gaia_cli.evidence import (
    inherited_evidence,
    merge_evidence,
    build_generic_evidence_map,
)

REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class TestInheritedEvidence(unittest.TestCase):
    def test_named_inherits_generic_capability_evidence(self):
        generic = {"id": "automated-testing", "evidence": [
            {"class": "A", "source": "https://arxiv.org/abs/0001"},
        ]}
        named = {"id": "x/pytest", "evidence": [
            {"class": "C", "source": "https://github.com/x/pytest"},
        ]}
        pool = inherited_evidence(named, generic)
        sources = {e["source"] for e in pool}
        self.assertEqual(sources, {"https://arxiv.org/abs/0001", "https://github.com/x/pytest"})

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


class TestRanklessGenerics(unittest.TestCase):
    def test_no_generic_node_has_level_or_demerits(self):
        graph = json.load(open(os.path.join(REPO_ROOT, "registry", "gaia.json"), encoding="utf-8"))
        bad = [s["id"] for s in graph["skills"] if "level" in s or "demerits" in s or "realVariants" in s]
        self.assertEqual(bad, [], f"Generic refs must be rank-less; offenders: {bad}")

    def test_named_skills_retain_levels(self):
        idx = json.load(open(os.path.join(REPO_ROOT, "registry", "named-skills.json"), encoding="utf-8"))
        valid = {"2★", "3★", "4★", "5★", "6★"}
        for entries in idx["buckets"].values():
            for e in entries:
                self.assertIn(e["level"], valid, f"{e['id']} has invalid level {e['level']}")


if __name__ == "__main__":
    unittest.main()
