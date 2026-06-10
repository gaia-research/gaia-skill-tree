import { loadGraph, loadUserTree } from "../graph/loader.js";
import { resolveIdentity } from "../config/identity.js";
import type { UserSkillTree, GaiaGraph } from "../graph/types.js";

function formatTree(tree: UserSkillTree, graph: GaiaGraph): string {
  const lines: string[] = [
    `# Skill Tree — ${tree.userId}`,
    `**Updated:** ${tree.updatedAt}  `,
    `**Total Unlocked:** ${tree.stats.totalUnlocked}  `,
    `**Deepest Lineage:** ${tree.stats.deepestLineage}`,
    "",
    "## Unlocked Skills",
    "",
  ];

  for (const s of tree.unlockedSkills) {
    const skill = graph.skills.find((sk) => sk.id === s.skillId);
    const name = skill?.name ?? s.skillId;
    const type = skill?.type ?? "unknown";
    lines.push(`- **${name}** (${type}, ${s.level}) — unlocked ${s.unlockedAt} in ${s.unlockedIn}`);
  }

  if (tree.pendingCombinations.length > 0) {
    lines.push("");
    lines.push("## Pending Fusions");
    lines.push("");
    for (const pc of tree.pendingCombinations) {
      const skill = graph.skills.find((s) => s.id === pc.candidateResult);
      const name = skill?.name ?? pc.candidateResult;
      lines.push(`- **${name}** — combine: ${pc.detectedSkills.join(" + ")}`);
      lines.push(`  Level floor: ${pc.levelFloor} · Prompted: ${pc.promptedAt}`);
    }
  }

  return lines.join("\n");
}

export async function getMyTree(username?: string): Promise<string> {
  const user = username ?? resolveIdentity();
  if (!user) {
    return "No Gaia user configured. Set GAIA_USER in your environment or .mcp.json env block, OR create a .gaia/config.json file with a \"gaiaUser\" field at the repo root.";
  }

  const [graph, rawTree] = await Promise.all([
    loadGraph(),
    loadUserTree(user),
  ]);

  if (!rawTree) {
    return `No skill tree found for user "${user}". Your tree is created when you first fuse a skill using gaia_propose.`;
  }

  const tree = rawTree as unknown as UserSkillTree;
  return formatTree(tree, graph);
}
