import { loadGraph, loadUserTree } from "../graph/loader.js";
import { resolveIdentity } from "../config/identity.js";
import { fusionEngine } from "../advisor/fusionEngine.js";
import { skillDetector } from "../advisor/detector.js";
import type { AdvisorContext } from "../advisor/types.js";
import type { UserSkillTree, FusionCandidate, GaiaGraph } from "../graph/types.js";

function formatCandidate(c: FusionCandidate, graph: GaiaGraph): string {
  const skill = graph.skills.find((s) => s.id === c.candidateResult);
  const name = skill?.name ?? c.candidateResult;

  if (c.status === "ready") {
    return `**${name}** (${skill?.type}, ${c.levelFloor}) — READY TO FUSE\n  Combine: ${c.detectedSkills.join(" + ")}\n  Use gaia_propose to claim this fusion.`;
  }
  return `**${name}** (${skill?.type}, ${c.levelFloor}) — ONE AWAY\n  Have: ${c.detectedSkills.join(" + ")}\n  Missing: ${c.missingSkills.join(", ")}`;
}

export async function suggest(
  context?: string[],
  tools?: string[]
): Promise<string> {
  const graph = await loadGraph();
  const user = resolveIdentity();

  let ownedSkillIds: string[] = [];
  let tree: UserSkillTree | null = null;
  if (user) {
    const rawTree = await loadUserTree(user);
    if (rawTree) {
      tree = rawTree as unknown as UserSkillTree;
      ownedSkillIds = tree.unlockedSkills.map((s) => s.skillId);
    }
  }

  const advisorContext: AdvisorContext = {
    graph,
    userTree: tree,
    ownedSkillIds,
    connectedTools: tools ?? [],
    projectSignals: context ?? [],
  };
  const detection = skillDetector.analyze(advisorContext);
  const allDetected = detection.allDetected;

  if (allDetected.length === 0 && ownedSkillIds.length === 0) {
    return "No skills detected yet. Connect more MCP tools or use gaia_scan_context with project signals to detect your skills.";
  }

  const candidates = fusionEngine.analyze(detection.context);

  const lines: string[] = [];

  if (allDetected.length > 0) {
    lines.push(`## Detected Skills\n${allDetected.join(", ")}\n`);
  }

  const ready = candidates.filter((c) => c.status === "ready");
  const oneAway = candidates.filter((c) => c.status === "one_away");

  if (ready.length > 0) {
    lines.push("## Ready to Fuse\n");
    for (const c of ready.slice(0, 5)) {
      lines.push(formatCandidate(c, graph));
      lines.push("");
    }
  }

  if (oneAway.length > 0) {
    lines.push("## One Skill Away\n");
    for (const c of oneAway.slice(0, 5)) {
      lines.push(formatCandidate(c, graph));
      lines.push("");
    }
  }

  if (ready.length === 0 && oneAway.length === 0) {
    lines.push("No fusions available with your current skill set. Keep building!");
    if (allDetected.length > 0) {
      lines.push(`\nYour detected skills (${allDetected.length}): ${allDetected.join(", ")}`);
    }
  }

  return lines.join("\n");
}
