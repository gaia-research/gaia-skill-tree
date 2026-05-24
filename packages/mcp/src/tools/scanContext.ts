import { loadGraph, loadUserTree } from "../graph/loader.js";
import { resolveIdentity } from "../config/identity.js";
import { detectCombinations } from "../advisor/fusionEngine.js";
import { detectSkillsFromTools, detectSkillsFromSignals } from "../advisor/detector.js";
import { scoreNovelty } from "../advisor/noveltyScorer.js";
import { runGaia } from "../utils/gaia.js";
import type { UserSkillTree, GaiaGraph } from "../graph/types.js";

export async function scanContext(
  connectedTools?: string[],
  projectSignals?: string[],
  deepScan?: boolean
): Promise<string> {
  const graph = await loadGraph();
  const user = resolveIdentity();

  const detectedFromTools = connectedTools ? detectSkillsFromTools(connectedTools) : [];
  const detectedFromSignals = projectSignals ? detectSkillsFromSignals(projectSignals) : [];
  let allDetected = [...new Set([...detectedFromTools, ...detectedFromSignals])];

  if (deepScan) {
    try {
      const deepOutput = await runGaia(["scan", "--json"]);
      const parsed = JSON.parse(deepOutput);
      if (parsed.matched && Array.isArray(parsed.matched)) {
        for (const skill of parsed.matched) {
          allDetected.push(skill);
        }
      }
    } catch (err) {
      console.warn("Deep scan failed, falling back to heuristic scan:", err);
    }
  }

  allDetected = [...new Set(allDetected)];

  let ownedSkillIds: string[] = [];
  if (user) {
    const rawTree = await loadUserTree(user);
    if (rawTree) {
      const tree = rawTree as unknown as UserSkillTree;
      ownedSkillIds = tree.unlockedSkills.map((s) => s.skillId);
    }
  }

  const candidates = detectCombinations(graph, ownedSkillIds, allDetected);
  const lines: string[] = [];

  lines.push(`## Skill Scan Results\n`);
  lines.push(`**Detected ${allDetected.length} skills** from ${connectedTools?.length ?? 0} tools and ${projectSignals?.length ?? 0} project signals.\n`);

  if (allDetected.length > 0) {
    lines.push("### Skills Identified\n");
    for (const id of allDetected) {
      const skill = graph.skills.find((s) => s.id === id);
      if (skill) {
        lines.push(`- **${skill.name}** (${skill.type}, ${skill.rarity})`);
      } else {
        lines.push(`- ${id} (matched but not in registry)`);
      }
    }
    lines.push("");
  }

  const ready = candidates.filter((c) => c.status === "ready");
  if (ready.length > 0) {
    lines.push("### Fusions Available\n");
    for (const c of ready) {
      const skill = graph.skills.find((s) => s.id === c.candidateResult);
      lines.push(`- **${skill?.name ?? c.candidateResult}** — combine: ${c.detectedSkills.join(" + ")}`);
    }
    lines.push("");
  }

  if (projectSignals && projectSignals.length > 0) {
    const combined = projectSignals.join(" ");
    const novelty = scoreNovelty(combined, graph);
    if (novelty.isNovel) {
      lines.push("### Novel Capability Detected\n");
      lines.push(`This project appears to implement a capability not yet in the Gaia registry.`);
      lines.push(`Confidence: ${Math.round(novelty.confidence * 100)}%`);
      if (novelty.closestMatch) {
        lines.push(`Closest existing skill: **${novelty.closestMatch.name}** (${Math.round(novelty.closestMatch.similarity * 100)}% similar)`);
      }
      lines.push(`\nUse **gaia_propose** to submit this as a new skill to the registry.`);
    }
  }

  return lines.join("\n");
}
