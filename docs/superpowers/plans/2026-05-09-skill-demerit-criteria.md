# Skill Demerit Criteria Implementation Plan

> **Superseded (May 2026):** The `registry/skills/basic/`, `registry/skills/extra/`, and
> `registry/skills/ultimate/` paths referenced in this document were removed in the May 2026
> registry reorganization. Canonical skill data now lives under `registry/nodes/`. This document
> is preserved for historical reference only.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add canonical skill demerit criteria that lower a 2★+ skill's progression ceiling by one level per demerit, while preserving the existing evidence-backed `level` field as the source-of-truth claim.

**Architecture:** Keep `level` as the claimed canonical tier in `registry/gaia.json`, add an optional `demerits` array on canonical skill nodes, and derive an `effectiveLevel` in shared helpers. Use the derived level for fusion floors, promotion ceilings, stats, and generated projections; use the claimed level for evidence requirements and named-skill governance text. Seed only a short list of obvious examples in the first pass so the meta shifts without a broad reclassification sweep.

**Tech Stack:** JSON Schema Draft 07, Python 3.10+, pytest, TypeScript/Vitest, existing Gaia projection/render scripts.

---

## Decision Lock

- `level` stays canonical and evidence-backed.
- `demerits` is canonical and applies only to `registry/gaia.json` skills in this PR, not `registry/named/**/*.md`.
- Each demerit lowers the derived `effectiveLevel` by exactly one rank.
- Demerits are only valid on claimed levels `II` through `VI`.
- Derived level is floored at `I` so a 2★+ skill can be held back but never pushed below the awakened floor.
- Promotion, fusion, pending-combination `levelFloor`, stats, render JSON, and generated docs use `effectiveLevel`.
- Evidence validation continues to evaluate the claimed `level`, not the reduced `effectiveLevel`.
- Named skills still require claimed 2★+; demerits do not legalize 1★ named skills.

## File Map

- Create: `src/gaia_cli/leveling.py` — single source of truth for demerit math in Python.
- Create: `tests/test_leveling.py` — unit coverage for penalty math and level flooring.
- Create: `tests/fixtures/demerits_level_i.json` — invalid fixture proving demerits are rejected on 1★.
- Create: `tests/fixtures/demerits_unknown_id.json` — invalid fixture proving only canonical demerit ids are accepted.
- Create: `packages/mcp/src/graph/levels.ts` — TypeScript mirror of effective-level math for MCP fusion suggestions.
- Modify: `registry/schema/meta.json` — canonical demerit catalog, labels, eligible levels, and floor.
- Modify: `registry/schema/skill.schema.json` — add optional `demerits` array on skill nodes.
- Modify: `scripts/validate.py` — enforce demerit business rules and extend meta sync checks.
- Modify: `registry/gaia.json` — seed initial demerit usage plus graph-level `demeritLabels`.
- Modify: `src/gaia_cli/promotion.py`, `src/gaia_cli/combinator.py`, `scripts/detectCombinations.py`, `src/gaia_cli/main.py`, `src/gaia_cli/pathEngine.py` — progression logic must use `effectiveLevel`.
- Modify: `packages/mcp/src/graph/types.ts`, `packages/mcp/src/advisor/fusionEngine.ts` — MCP type surface and fusion advice must use `effectiveLevel`.
- Modify: `src/gaia_cli/commands/stats.py`, `src/gaia_cli/cardRenderer.py`, `src/gaia_cli/graph.py`, `scripts/generateProjections.py`, `docs/js/skill-graph.js`, `docs/js/skill-explorer.js` — surface claimed vs effective levels to users.
- Modify: `README.md`, `CONTRIBUTING.md`, `docs/GOVERNANCE.md` — document the rule without changing named-skill floor semantics.
- Modify generated copies: `src/gaia_cli/data/registry/gaia.json`, `src/gaia_cli/data/registry/schema/*.json`, `registry/registry.md`, `registry/combinations.md`, `registry/skills/**/*.md`, `registry/gaia.gexf`, `registry/gaia.svg`, `registry/render/gaia.html`, `docs/graph/*`, `docs/tree.md`.
- Test: `tests/test_validate.py`, `tests/test_leveling.py`, `tests/test_promotion.py`, `tests/test_path_engine.py`, `tests/test_stats.py`, `tests/test_card_renderer.py`, `tests/test_graph.py`, `packages/mcp/tests/fusionEngine.test.ts`, `tests/test_docs_site.py`.

### Task 1: Define the canonical demerit schema and shared level math

**Files:**
- Create: `src/gaia_cli/leveling.py`
- Create: `tests/test_leveling.py`
- Create: `tests/fixtures/demerits_level_i.json`
- Create: `tests/fixtures/demerits_unknown_id.json`
- Modify: `registry/schema/meta.json`
- Modify: `registry/schema/skill.schema.json`
- Modify: `scripts/validate.py`
- Modify: `tests/test_validate.py`
- Modify: `src/gaia_cli/data/registry/schema/meta.json`
- Modify: `src/gaia_cli/data/registry/schema/skill.schema.json`

- [ ] **Step 1: Write the failing helper and validation tests**

```python
# tests/test_leveling.py
from gaia_cli.leveling import demerit_penalty, effective_level, level_summary


def test_effective_level_drops_one_rank_per_demerit():
    skill = {
        "id": "voice-agent",
        "level": "3★",
        "demerits": ["heavyweight-dependency"],
    }
    assert demerit_penalty(skill) == 1
    assert effective_level(skill) == "II"


def test_effective_level_floors_at_awakened():
    skill = {
        "id": "deployment-automation",
        "level": "2★",
        "demerits": ["niche-integration", "experimental-feature"],
    }
    assert demerit_penalty(skill) == 2
    assert effective_level(skill) == "I"


def test_level_summary_keeps_claimed_and_effective_levels():
    skill = {
        "id": "mcp-integration",
        "level": "3★",
        "demerits": ["niche-integration"],
    }
    assert level_summary(skill) == {
        "baseLevel": "III",
        "effectiveLevel": "II",
        "demerits": ["niche-integration"],
        "penalty": 1,
    }
```

```python
# tests/test_validate.py additions inside TestValidate
    def test_demerits_reject_level_i_skills(self):
        code, out = run_validate(os.path.join(FIXTURES_DIR, "demerits_level_i.json"))
        self.assertEqual(code, 1, "Expected 1★ demerits to fail validation.")
        self.assertIn("only allowed on 2★ or above", out)

    def test_demerits_reject_unknown_catalog_keys(self):
        code, out = run_validate(os.path.join(FIXTURES_DIR, "demerits_unknown_id.json"))
        self.assertEqual(code, 1, "Expected unknown demerits to fail validation.")
        self.assertIn("unknown demerit", out)
```

- [ ] **Step 2: Run the new tests to confirm the gap exists**

Run: `python3 -m pytest tests/test_leveling.py tests/test_validate.py -q`

Expected: FAIL with `ModuleNotFoundError: No module named 'gaia_cli.leveling'` plus missing demerit-validation assertions.

- [ ] **Step 3: Add the demerit catalog to schema metadata and create the shared helper**

```json
// registry/schema/meta.json — add this sibling block next to "levels", "types", and "evidence"
"demerits": {
  "order": [
    "niche-integration",
    "experimental-feature",
    "heavyweight-dependency"
  ],
  "labels": {
    "niche-integration": "Niche integration",
    "experimental-feature": "Experimental feature",
    "heavyweight-dependency": "Heavyweight dependency"
  },
  "descriptions": {
    "niche-integration": "Depends on a narrow vendor ecosystem, paid service, or specialized external integration.",
    "experimental-feature": "Relies on capability areas that are promising but not yet broadly proven or stable.",
    "heavyweight-dependency": "Requires significant environment setup, credentials, installed tooling, or infrastructure."
  },
  "eligibleLevels": ["II", "III", "IV", "V", "VI"],
  "penaltyPerItem": 1,
  "minimumEffectiveLevel": "I"
}
```

```json
// registry/schema/skill.schema.json — add the new property beside "conditions" / "realVariants"
"demerits": {
  "type": "array",
  "items": {
    "type": "string",
    "enum": [
      "niche-integration",
      "experimental-feature",
      "heavyweight-dependency"
    ]
  },
  "uniqueItems": true,
  "description": "Optional 2★+ progression penalties. Each entry lowers the derived effective level by one rank."
},
```

```python
# src/gaia_cli/leveling.py
import json
import os
from functools import lru_cache


@lru_cache(maxsize=1)
def _load_meta():
    candidates = [
        os.path.join(os.path.dirname(__file__), "..", "..", "registry", "schema", "meta.json"),
        os.path.join(os.path.dirname(__file__), "data", "registry", "schema", "meta.json"),
    ]
    for path in candidates:
        resolved = os.path.normpath(path)
        if os.path.isfile(resolved):
            with open(resolved, "r", encoding="utf-8") as f:
                return json.load(f)
    raise FileNotFoundError("Cannot find registry/schema/meta.json")


_META = _load_meta()
LEVEL_ORDER = _META["levels"]["order"]
DEMERIT_ORDER = tuple(_META["demerits"]["order"])
DEMERIT_ELIGIBLE_LEVELS = set(_META["demerits"]["eligibleLevels"])
MIN_EFFECTIVE_LEVEL = _META["demerits"]["minimumEffectiveLevel"]


def level_index(level: str) -> int:
    try:
        return LEVEL_ORDER.index(level)
    except ValueError:
        return -1


def demerit_penalty(skill: dict) -> int:
    return sum(1 for item in (skill.get("demerits", []) or []) if item in DEMERIT_ORDER)


def effective_level(skill: dict) -> str:
    base = skill.get("level", "0")
    if base not in DEMERIT_ELIGIBLE_LEVELS:
        return base
    floor_idx = level_index(MIN_EFFECTIVE_LEVEL)
    base_idx = level_index(base)
    lowered = max(floor_idx, base_idx - demerit_penalty(skill))
    return LEVEL_ORDER[lowered]


def level_summary(skill: dict) -> dict:
    base = skill.get("level", "0")
    effective = effective_level(skill)
    return {
        "baseLevel": base,
        "effectiveLevel": effective,
        "demerits": list(skill.get("demerits", []) or []),
        "penalty": max(level_index(base) - level_index(effective), 0),
    }
```

- [ ] **Step 4: Enforce demerit rules in the validator**

```python
# scripts/validate.py
def validate_demerits(graph):
    errors = []
    allowed = set(_META.get("demerits", {}).get("order", []))
    eligible_levels = set(_META.get("demerits", {}).get("eligibleLevels", []))

    for skill in graph.get("skills", []):
        demerits = skill.get("demerits", []) or []
        if not demerits:
            continue

        if skill.get("level") not in eligible_levels:
            errors.append(
                f"Skill '{skill['id']}' has demerits but claimed level "
                f"{skill.get('level')} is only allowed on 2★ or above."
            )

        unknown = [item for item in demerits if item not in allowed]
        if unknown:
            errors.append(
                f"Skill '{skill['id']}' declares unknown demerit(s): {unknown}."
            )

    return errors
```

```python
# scripts/validate.py — add to main validation flow
errors.extend(validate_demerits(graph))
```

```python
# scripts/validate.py — extend check_meta_sync()
meta_demerit_labels = meta.get("demerits", {}).get("labels", {})
gaia_demerit_labels = gaia_meta.get("demeritLabels", {})
for key, value in gaia_demerit_labels.items():
    if key not in meta_demerit_labels:
        errors.append(f"gaia.json meta.demeritLabels has key '{key}' not in meta.json demerits.labels")
    elif meta_demerit_labels[key] != value:
        errors.append(
            f"demeritLabels mismatch for '{key}': gaia.json has '{value}', "
            f"meta.json has '{meta_demerit_labels[key]}'"
        )
```

- [ ] **Step 5: Sync the bundled schema copies**

Run: `cp registry/schema/meta.json src/gaia_cli/data/registry/schema/meta.json`

Run: `cp registry/schema/skill.schema.json src/gaia_cli/data/registry/schema/skill.schema.json`

Expected: no output; bundled copies now exactly match canonical schema files.

- [ ] **Step 6: Re-run the targeted tests**

Run: `python3 -m pytest tests/test_leveling.py tests/test_validate.py -q`

Expected: PASS for the new helper and validation cases.

- [ ] **Step 7: Commit the schema foundation**

```bash
git add \
  registry/schema/meta.json \
  registry/schema/skill.schema.json \
  src/gaia_cli/leveling.py \
  src/gaia_cli/data/registry/schema/meta.json \
  src/gaia_cli/data/registry/schema/skill.schema.json \
  scripts/validate.py \
  tests/test_leveling.py \
  tests/test_validate.py \
  tests/fixtures/demerits_level_i.json \
  tests/fixtures/demerits_unknown_id.json
git commit -m "feat: add canonical skill demerit schema"
```

### Task 2: Seed the first canonical demerits in the registry

**Files:**
- Modify: `registry/gaia.json`
- Modify: `src/gaia_cli/data/registry/gaia.json`
- Modify: `tests/test_validate.py`

- [ ] **Step 1: Add a failing regression test for the seeded rollout**

```python
# tests/test_validate.py additions inside TestValidate
    def test_seeded_skill_demerits_cover_all_three_categories(self):
        with open(REAL_GRAPH_PATH, encoding="utf-8") as f:
            graph = json.load(f)
        skills = {skill["id"]: skill for skill in graph.get("skills", [])}

        self.assertEqual(skills["mcp-integration"]["demerits"], ["niche-integration"])
        self.assertEqual(skills["multimodal-reasoning"]["demerits"], ["experimental-feature"])
        self.assertEqual(skills["voice-agent"]["demerits"], ["heavyweight-dependency"])
        self.assertEqual(skills["deployment-automation"]["demerits"], ["heavyweight-dependency"])
```

- [ ] **Step 2: Run the rollout test before changing data**

Run: `python3 -m pytest tests/test_validate.py -q`

Expected: FAIL because those four canonical skills do not yet declare `demerits`.

- [ ] **Step 3: Seed graph-level labels and the first four canonical examples**

```json
// registry/gaia.json — add to top-level meta
"demeritLabels": {
  "niche-integration": "Niche integration",
  "experimental-feature": "Experimental feature",
  "heavyweight-dependency": "Heavyweight dependency"
},
```

```json
// registry/gaia.json — add these exact demerits to the matching skill objects
{
  "id": "mcp-integration",
  "demerits": ["niche-integration"]
}
{
  "id": "multimodal-reasoning",
  "demerits": ["experimental-feature"]
}
{
  "id": "voice-agent",
  "demerits": ["heavyweight-dependency"]
}
{
  "id": "deployment-automation",
  "demerits": ["heavyweight-dependency"]
}
```

- [ ] **Step 4: Sync the bundled graph copy**

Run: `cp registry/gaia.json src/gaia_cli/data/registry/gaia.json`

Expected: no output; packaged CLI data matches the canonical graph.

- [ ] **Step 5: Re-run validation and the rollout assertions**

Run: `python3 scripts/validate.py --graph registry/gaia.json`

Expected: `All validation checks passed.`

Run: `python3 -m pytest tests/test_validate.py -q`

Expected: PASS including the seeded-demerit assertions.

- [ ] **Step 6: Commit the seeded meta shift**

```bash
git add registry/gaia.json src/gaia_cli/data/registry/gaia.json tests/test_validate.py
git commit -m "feat: seed initial canonical skill demerits"
```

### Task 3: Use effective levels for promotion and fusion logic

**Files:**
- Create: `packages/mcp/src/graph/levels.ts`
- Modify: `src/gaia_cli/promotion.py`
- Modify: `src/gaia_cli/combinator.py`
- Modify: `scripts/detectCombinations.py`
- Modify: `src/gaia_cli/main.py`
- Modify: `src/gaia_cli/pathEngine.py`
- Modify: `packages/mcp/src/graph/types.ts`
- Modify: `packages/mcp/src/advisor/fusionEngine.ts`
- Modify: `tests/test_promotion.py`
- Modify: `tests/test_path_engine.py`
- Modify: `packages/mcp/tests/fusionEngine.test.ts`

- [ ] **Step 1: Write the failing promotion, path, and MCP tests**

```python
# tests/test_promotion.py
def _make_skill(skill_id, name=None, level="0", evidence=None, demerits=None):
    return {
        "id": skill_id,
        "name": name or skill_id.replace("-", " ").title(),
        "type": "basic",
        "level": level,
        "rarity": "common",
        "description": f"Test skill: {skill_id}",
        "prerequisites": [],
        "derivatives": [],
        "conditions": "",
        "evidence": evidence or [],
        "knownAgents": [],
        "status": "provisional",
        "createdAt": "2026-01-01",
        "updatedAt": "2026-01-01",
        "version": "0.1.0",
        "demerits": demerits or [],
    }


def test_level_ii_skill_stops_at_effective_ceiling():
    ev_b = [{"class": "B", "source": "http://x.com", "evaluator": "x", "date": "2026-01-01", "notes": ""}]
    graph = _make_graph(_make_skill("voice-agent", level="III", evidence=ev_b, demerits=["heavyweight-dependency"]))
    tree = _make_tree("alice", [_make_unlocked("voice-agent", "II")])
    eligible = check_promotion_eligibility(graph, tree)
    assert eligible == []
```

```python
# tests/test_path_engine.py addition inside TestComputePaths
    def test_near_unlock_records_effective_level_floor(self, mini_graph):
        mini_graph["skills"][3]["level"] = "III"
        mini_graph["skills"][3]["demerits"] = ["experimental-feature"]
        result = compute_paths(mini_graph, ["skill-a", "skill-b"], [])
        entry = next(e for e in result["nearUnlocks"] if e["skillId"] == "skill-d")
        assert entry["baseLevel"] == "III"
        assert entry["levelFloor"] == "II"
        assert entry["demerits"] == ["experimental-feature"]
```

```ts
// packages/mcp/tests/fusionEngine.test.ts
it("uses effective level as the fusion floor when demerits are present", () => {
  const graph: GaiaGraph = {
    ...mockGraph,
    skills: mockGraph.skills.map((skill) =>
      skill.id === "web-scrape"
        ? { ...skill, demerits: ["experimental-feature"] }
        : skill
    ),
  };
  const result = detectCombinations(graph, [], ["web-search", "parse-html", "extract-entities"]);
  const match = result.find((candidate) => candidate.candidateResult === "web-scrape");
  expect(match?.levelFloor).toBe("II");
});
```

- [ ] **Step 2: Run the failing progression tests**

Run: `python3 -m pytest tests/test_promotion.py tests/test_path_engine.py -q`

Expected: FAIL because promotion and path outputs still use `skill["level"]`.

Run: `npm --prefix packages/mcp test -- --run tests/fusionEngine.test.ts`

Expected: FAIL because MCP fusion candidates still report the claimed level as `levelFloor`.

- [ ] **Step 3: Implement the Python progression ceiling**

```python
# src/gaia_cli/promotion.py
from .leveling import effective_level, level_index


def check_promotion_eligibility(graph_data: dict, tree_data: dict) -> list[dict]:
    eligible = []
    for entry in tree_data.get("unlockedSkills", []):
        skill_id = entry["skillId"]
        current = entry["level"]
        graph_skill = _get_skill_from_graph(graph_data, skill_id)
        if graph_skill is None:
            continue

        ceiling = effective_level(graph_skill)
        if level_index(current) >= level_index(ceiling):
            continue

        target = next_level(current)
        if target is None or level_index(target) > level_index(ceiling):
            continue

        if _meets_evidence_floor(graph_skill, target):
            eligible.append({
                "skillId": skill_id,
                "currentLevel": current,
                "nextLevel": target,
                "suggestedLevel": target,
                "baseLevel": graph_skill.get("level"),
                "effectiveLevel": ceiling,
                "demerits": graph_skill.get("demerits", []),
                "name": graph_skill.get("name", skill_id),
                "evidence": graph_skill.get("evidence", []),
            })
    return eligible
```

```python
# src/gaia_cli/combinator.py
from gaia_cli.leveling import effective_level


def detect_combinations(graph_data, owned_skills, detected_skills):
    combinations = []
    owned_skill_ids = set()
    for skill in owned_skills:
        if isinstance(skill, dict) and "skillId" in skill:
            owned_skill_ids.add(skill["skillId"])
        elif isinstance(skill, str):
            owned_skill_ids.add(skill)

    combined_available = owned_skill_ids.union(set(detected_skills))

    for skill in graph_data.get("skills", []):
        if skill.get("type") not in ["extra", "ultimate"]:
            continue

        prereqs = skill.get("prerequisites", [])
        if not prereqs:
            continue

        if all(prereq in combined_available for prereq in prereqs):
            if skill["id"] not in owned_skill_ids:
                combinations.append({
                    "candidateResult": skill["id"],
                    "levelFloor": effective_level(skill),
                    "baseLevel": skill.get("level"),
                    "demerits": skill.get("demerits", []),
                    "detectedSkills": [p for p in prereqs if p in detected_skills] or prereqs,
                    "status": "new_fusion",
                })

    return combinations
```

```python
# src/gaia_cli/pathEngine.py
from gaia_cli.leveling import effective_level

        if len(missing) == 0:
            near_unlocks.append({
                "skillId": sid,
                "name": skill.get("name", sid),
                "type": skill.get("type"),
                "baseLevel": skill.get("level"),
                "levelFloor": effective_level(skill),
                "demerits": skill.get("demerits", []),
                "satisfiedPrereqs": prereqs,
            })
        elif len(missing) == 1:
            one_away.append({
                "skillId": sid,
                "name": skill.get("name", sid),
                "type": skill.get("type"),
                "baseLevel": skill.get("level"),
                "levelFloor": effective_level(skill),
                "demerits": skill.get("demerits", []),
                "missingPrereq": missing[0],
                "satisfiedPrereqs": [p for p in prereqs if p in available],
            })
```

- [ ] **Step 4: Make the standalone script and MCP engine share the same semantics**

```python
# scripts/detectCombinations.py
import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from gaia_cli.combinator import detect_combinations


def main():
    parser = argparse.ArgumentParser(description="Detect skill combinations")
    parser.add_argument("--graph", required=True, help="Path to gaia.json")
    parser.add_argument("--detected", required=False, default="", help="Comma-separated detected skill IDs")
    parser.add_argument("--owned", required=True, help="Path to user skill-tree.json")
    args = parser.parse_args()

    with open(args.graph, "r", encoding="utf-8") as f:
        graph_data = json.load(f)
    with open(args.owned, "r", encoding="utf-8") as f:
        user_data = json.load(f)

    detected_skills = [s.strip() for s in args.detected.split(",")] if args.detected else []
    owned_skills = user_data.get("unlockedSkills", [])
    print(json.dumps(detect_combinations(graph_data, owned_skills, detected_skills), indent=2))


if __name__ == "__main__":
    main()
```

```ts
// packages/mcp/src/graph/levels.ts
import type { Skill } from "./types.js";

const LEVEL_ORDER = ["0", "I", "II", "III", "IV", "V", "VI"] as const;
const ELIGIBLE = new Set(["II", "III", "IV", "V", "VI"]);
const FLOOR = "I";

export function effectiveLevel(skill: Skill): Skill["level"] {
  if (!ELIGIBLE.has(skill.level)) return skill.level;
  const penalty = (skill.demerits ?? []).length;
  const baseIndex = LEVEL_ORDER.indexOf(skill.level);
  const floorIndex = LEVEL_ORDER.indexOf(FLOOR);
  return LEVEL_ORDER[Math.max(floorIndex, baseIndex - penalty)];
}
```

```ts
// packages/mcp/src/graph/types.ts
export type SkillDemerit =
  | "niche-integration"
  | "experimental-feature"
  | "heavyweight-dependency";

export interface Skill {
  id: string;
  name: string;
  type: "basic" | "extra" | "ultimate";
  level: "0★" | "I" | "II" | "III" | "IV" | "V" | "VI";
  rarity: "common" | "uncommon" | "rare" | "epic" | "legendary";
  description: string;
  prerequisites: string[];
  derivatives: string[];
  conditions: string;
  demerits?: SkillDemerit[];
  evidence: EvidenceEntry[];
  knownAgents: string[];
  status: "provisional" | "validated" | "disputed" | "deprecated";
  createdAt: string;
  updatedAt: string;
  version: string;
}
```

```ts
// packages/mcp/src/advisor/fusionEngine.ts
import { effectiveLevel } from "../graph/levels.js";

      candidates.push({
        candidateResult: skill.id,
        levelFloor: effectiveLevel(skill),
        detectedSkills: met,
        missingSkills: [],
        status: "ready",
      });
```

- [ ] **Step 5: Re-run the targeted progression suite**

Run: `python3 -m pytest tests/test_promotion.py tests/test_path_engine.py -q`

Expected: PASS for effective-level promotion ceilings and near-unlock floors.

Run: `npm --prefix packages/mcp test -- --run tests/fusionEngine.test.ts`

Expected: PASS with `levelFloor` reflecting the derived level instead of the claimed level.

- [ ] **Step 6: Commit the progression logic**

```bash
git add \
  src/gaia_cli/promotion.py \
  src/gaia_cli/combinator.py \
  src/gaia_cli/main.py \
  src/gaia_cli/pathEngine.py \
  scripts/detectCombinations.py \
  packages/mcp/src/graph/types.ts \
  packages/mcp/src/graph/levels.ts \
  packages/mcp/src/advisor/fusionEngine.ts \
  tests/test_promotion.py \
  tests/test_path_engine.py \
  packages/mcp/tests/fusionEngine.test.ts
git commit -m "feat: apply demerit ceilings to progression"
```

### Task 4: Surface claimed vs effective levels in CLI, graphs, and docs

**Files:**
- Modify: `src/gaia_cli/commands/stats.py`
- Modify: `src/gaia_cli/cardRenderer.py`
- Modify: `src/gaia_cli/graph.py`
- Modify: `scripts/generateProjections.py`
- Modify: `docs/js/skill-graph.js`
- Modify: `docs/js/skill-explorer.js`
- Modify: `README.md`
- Modify: `CONTRIBUTING.md`
- Modify: `docs/GOVERNANCE.md`
- Modify: `tests/test_stats.py`
- Modify: `tests/test_card_renderer.py`
- Modify: `tests/test_graph.py`
- Modify: `tests/test_docs_site.py`

- [ ] **Step 1: Write failing output-level tests**

```python
# tests/test_stats.py
def test_collect_stats_tracks_effective_levels_and_demerits(tmp_path):
    write_fixture_registry(tmp_path)
    graph_path = tmp_path / "registry" / "gaia.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["skills"][2]["demerits"] = ["experimental-feature"]
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    stats = collect_stats(tmp_path)

    assert stats["effective_level_counts"]["I"] == 1
    assert stats["effective_level_counts"]["II"] == 2
    assert stats["demerit_counts"]["experimental-feature"] == 1
```

```python
# tests/test_card_renderer.py
def test_render_card_shows_demerit_adjusted_ceiling(extra_skill):
    extra_skill["level"] = "III"
    extra_skill["demerits"] = ["experimental-feature"]
    rendered = render_card(extra_skill)
    assert "Claimed 3★" in rendered
    assert "Potential II" in rendered
    assert "experimental-feature" in rendered
```

```python
# tests/test_graph.py
def test_render_json_includes_effective_level_and_demerits(tmp_path):
    root = make_registry(tmp_path)
    graph_path = root / "registry" / "gaia.json"
    graph = json.loads(graph_path.read_text(encoding="utf-8"))
    graph["skills"][1]["demerits"] = ["experimental-feature"]
    graph_path.write_text(json.dumps(graph), encoding="utf-8")

    out_path = graph_mod.write_graph_artifact(root, fmt="json")
    rendered = json.loads(out_path.read_text(encoding="utf-8"))
    research = next(node for node in rendered["nodes"] if node["id"] == "research")

    assert research["level"] == "III"
    assert research["effectiveLevel"] == "II"
    assert research["demerits"] == ["experimental-feature"]
```

- [ ] **Step 2: Run the presentation tests before changing the renderers**

Run: `python3 -m pytest tests/test_stats.py tests/test_card_renderer.py tests/test_graph.py -q`

Expected: FAIL because current renderers only know about `level`.

- [ ] **Step 3: Thread claimed and effective levels through Python renderers**

```python
# src/gaia_cli/commands/stats.py
from gaia_cli.leveling import effective_level

    effective_level_counts = Counter(effective_level(skill) for skill in skills)
    demerit_counts = Counter(
        demerit
        for skill in skills
        for demerit in (skill.get("demerits", []) or [])
    )

    return {
        "total_skills": len(skills),
        "total_edges": len(edges),
        "type_counts": dict(type_counts),
        "level_counts": dict(level_counts),
        "effective_level_counts": dict(effective_level_counts),
        "demerit_counts": dict(demerit_counts),
        "evidence_counts": {klass: best_evidence_counts.get(klass, 0) for klass in EVIDENCE_ORDER},
        "skills_with_evidence": sum(best_evidence_counts.values()),
        "named_implemented": len(named_items),
        "named_slots": len(named_slots),
        "named_eligible": len(eligible_slots),
        "named_unclaimed": max(len(eligible_slots - named_slots), 0),
    }
```

```python
# src/gaia_cli/graph.py — add effective level to render JSON nodes
from gaia_cli.leveling import effective_level

            nodes.append(
                {
                    "id": skill.get("id"),
                    "label": skill.get("name") or skill.get("id"),
                    "type": skill_type,
                    "level": skill.get("level"),
                    "effectiveLevel": effective_level(skill),
                    "demerits": skill.get("demerits", []),
                    "rarity": skill.get("rarity"),
                    "description": skill.get("description", ""),
                    "x": round(x, 3),
                    "y": round(y, 3),
                    "radius": NODE_RADIUS.get(skill_type, 7),
                }
            )
```

```python
# src/gaia_cli/cardRenderer.py — wherever the level subtitle is rendered
from gaia_cli.leveling import level_summary

summary = level_summary(skill)
level_line = f"Claimed Level {summary['baseLevel']}"
if summary["effectiveLevel"] != summary["baseLevel"]:
    tags = ", ".join(summary["demerits"])
    level_line += f"  ->  Potential {summary['effectiveLevel']} ({tags})"
```

- [ ] **Step 4: Update projections and public docs copy**

```python
# scripts/generateProjections.py
from gaia_cli.leveling import effective_level

def _effective_level_note(skill):
    current = skill.get("level")
    effective = effective_level(skill)
    demerits = skill.get("demerits", []) or []
    if not demerits or effective == current:
        return ""
    return f"{effective} ({', '.join(demerits)})"

            effective_note = _effective_level_note(skill)
            f.write(f"**Level:** {level_label}  \n")
            if effective_note:
                f.write(f"**Potential:** {effective_note}  \n")
```

```markdown
<!-- README.md / CONTRIBUTING.md / docs/GOVERNANCE.md -->
- 2★+ skills may carry canonical demerits: `niche-integration`, `experimental-feature`, and `heavyweight-dependency`.
- Each demerit lowers the skill's derived progression ceiling by one level, floored at 1★.
- Demerits do not reduce the evidence requirement of the claimed level; they only keep progression meta in a lower tier.
- Named skills still require claimed 2★+ even if the generic skill's effective level is lower.
```

```javascript
// docs/js/skill-graph.js and docs/js/skill-explorer.js
var claimedLevel = skill.level || "";
var effectiveLevel = skill.effectiveLevel || claimedLevel;
var demerits = Array.isArray(skill.demerits) ? skill.demerits : [];
var levelLabel = claimedLevel;
if (effectiveLevel && effectiveLevel !== claimedLevel) {
  levelLabel = claimedLevel + " -> " + effectiveLevel;
}
var demeritLabel = demerits.length
  ? '<div class="skill-demerits">' + demerits.join(", ") + "</div>"
  : "";
```

- [ ] **Step 5: Re-run output and docs checks**

Run: `python3 -m pytest tests/test_stats.py tests/test_card_renderer.py tests/test_graph.py tests/test_docs_site.py -q`

Expected: PASS for claimed-vs-effective output coverage.

Run: `PYTHONPATH=src python3 scripts/build_docs.py --check`

Expected: `Documentation is up to date.` after the docs edits and any marker regeneration.

- [ ] **Step 6: Commit the user-facing surface changes**

```bash
git add \
  src/gaia_cli/commands/stats.py \
  src/gaia_cli/cardRenderer.py \
  src/gaia_cli/graph.py \
  scripts/generateProjections.py \
  docs/js/skill-graph.js \
  docs/js/skill-explorer.js \
  README.md \
  CONTRIBUTING.md \
  docs/GOVERNANCE.md \
  tests/test_stats.py \
  tests/test_card_renderer.py \
  tests/test_graph.py \
  tests/test_docs_site.py
git commit -m "feat: surface demerit-adjusted skill ceilings"
```

### Task 5: Regenerate artifacts, verify drift, and lock the branch

**Files:**
- Modify: `registry/registry.md`
- Modify: `registry/combinations.md`
- Modify: `registry/skills/basic/*.md`
- Modify: `registry/skills/extra/*.md`
- Modify: `registry/skills/ultimate/*.md`
- Modify: `registry/gaia.gexf`
- Modify: `registry/gaia.svg`
- Modify: `registry/render/gaia.html`
- Modify: `docs/graph/gaia.json`
- Modify: `docs/graph/gaia.gexf`
- Modify: `docs/graph/gaia.svg`
- Modify: `docs/tree.md`

- [ ] **Step 1: Regenerate canonical markdown projections**

Run: `python3 scripts/generateProjections.py`

Expected: regenerated `registry/skills/**`, `registry/registry.md`, `registry/combinations.md`, and `generated-output/tree.md`.

- [ ] **Step 2: Regenerate graph artifacts**

Run: `python3 scripts/exportGexf.py`

Run: `PYTHONPATH=src python3 scripts/renderGraphSvg.py`

Run: `python3 -m gaia_cli.main --registry . graph --format html --no-open`

Expected: updated `registry/gaia.gexf`, `registry/gaia.svg`, and `registry/render/gaia.html`.

- [ ] **Step 3: Sync the public docs copies**

Run: `python3 scripts/syncDocsGraphAssets.py`

Expected: synced `docs/graph/*`, `docs/tree.md`, and `docs/graph/named/index.json`.

- [ ] **Step 4: Run the full focused verification suite**

Run: `python3 scripts/validate.py --graph registry/gaia.json`

Expected: `All validation checks passed.`

Run: `python3 scripts/validate.py --check-meta-sync`

Expected: `Meta sync check passed.`

Run: `python3 -m pytest tests/test_leveling.py tests/test_validate.py tests/test_promotion.py tests/test_path_engine.py tests/test_stats.py tests/test_card_renderer.py tests/test_graph.py tests/test_docs_site.py -q`

Expected: PASS across all Python demerit cases.

Run: `npm --prefix packages/mcp test -- --run tests/fusionEngine.test.ts`

Expected: PASS for the MCP-side effective-level logic.

- [ ] **Step 5: Inspect the final diff**

Run: `git status --short`

Expected: only the planned schema, code, docs, tests, and generated artifact files are modified.

- [ ] **Step 6: Commit the generated outputs**

```bash
git add \
  registry/registry.md \
  registry/combinations.md \
  registry/skills \
  registry/gaia.gexf \
  registry/gaia.svg \
  registry/render/gaia.html \
  docs/graph \
  docs/tree.md
git commit -m "chore: regenerate demerit-aware registry artifacts"
```

## Self-Review

- Spec coverage: the plan covers schema shape, canonical data seeding, promotion/fusion semantics, MCP parity, user-facing rendering, docs policy, generated outputs, and verification drift.
- Placeholder scan: no `TBD`, `TODO`, or cross-task hand-waves remain; every task names exact files and concrete commands.
- Type consistency: `demerits`, `effectiveLevel`, `baseLevel`, and `levelFloor` use the same names across Python, TypeScript, tests, and generated outputs.

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-05-09-skill-demerit-criteria.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**
