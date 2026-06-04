import type { GaiaGraph, FusionCandidate } from "../graph/types.js";
import { effectiveLevel } from "../graph/levels.js";
import { AbstractAdvisor, type AdvisorContext } from "./types.js";

function findFusionCandidates(
  graph: GaiaGraph,
  ownedSkillIds: string[],
  detectedSkillIds: string[]
): FusionCandidate[] {
  const available = new Set([...ownedSkillIds, ...detectedSkillIds]);
  const owned = new Set(ownedSkillIds);
  const candidates: FusionCandidate[] = [];

  for (const skill of graph.skills) {
    if (skill.type === "basic" || skill.type === "unique") continue;
    if (owned.has(skill.id)) continue;
    if (skill.prerequisites.length === 0) continue;

    const met = skill.prerequisites.filter((p) => available.has(p));
    const missing = skill.prerequisites.filter((p) => !available.has(p));

    if (missing.length === 0) {
      candidates.push({
        candidateResult: skill.id,
        levelFloor: effectiveLevel(skill),
        detectedSkills: met,
        missingSkills: [],
        status: "ready",
      });
    } else if (missing.length === 1) {
      candidates.push({
        candidateResult: skill.id,
        levelFloor: effectiveLevel(skill),
        detectedSkills: met,
        missingSkills: missing,
        status: "one_away",
      });
    }
  }

  return candidates.sort((a, b) => {
    if (a.status === "ready" && b.status !== "ready") return -1;
    if (b.status === "ready" && a.status !== "ready") return 1;
    const rarityOrder = ["legendary", "epic", "rare", "uncommon", "common"];
    const aSkill = graph.skills.find((s) => s.id === a.candidateResult);
    const bSkill = graph.skills.find((s) => s.id === b.candidateResult);
    const aIdx = rarityOrder.indexOf(aSkill?.rarity ?? "common");
    const bIdx = rarityOrder.indexOf(bSkill?.rarity ?? "common");
    return aIdx - bIdx;
  });
}

export class FusionEngine extends AbstractAdvisor<FusionCandidate[]> {
  constructor() {
    super("fusion-engine");
  }

  analyze(context: AdvisorContext): FusionCandidate[] {
    return findFusionCandidates(
      this.requireGraph(context),
      this.ownedSkillIds(context),
      this.detectedSkillIds(context)
    );
  }
}

export const fusionEngine = new FusionEngine();

export function detectCombinations(
  graph: GaiaGraph,
  ownedSkillIds: string[],
  detectedSkillIds: string[]
): FusionCandidate[] {
  return fusionEngine.analyze({ graph, ownedSkillIds, detectedSkillIds });
}
