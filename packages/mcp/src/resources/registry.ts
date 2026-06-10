import { loadGraph, loadUserTree } from "../graph/loader.js";
import type { GaiaGraph, UserSkillTree } from "../graph/types.js";

export async function getRegistryResource(): Promise<string> {
  const graph = await loadGraph();
  const summary = {
    version: graph.version,
    generatedAt: graph.generatedAt,
    totalSkills: graph.skills.length,
    byType: {
      basic: graph.skills.filter((s) => s.type === "basic").length,
      extra: graph.skills.filter((s) => s.type === "extra").length,
      ultimate: graph.skills.filter((s) => s.type === "ultimate").length,
    },
    totalEdges: graph.edges.length,
    skills: graph.skills.map((s) => ({
      id: s.id,
      name: s.name,
      type: s.type,
      level: s.level,
      prerequisites: s.prerequisites,
    })),
  };
  return JSON.stringify(summary, null, 2);
}

export async function getUserTreeResource(username: string): Promise<string> {
  const rawTree = await loadUserTree(username);
  if (!rawTree) {
    return JSON.stringify({ error: `No skill tree found for user "${username}"` });
  }
  return JSON.stringify(rawTree, null, 2);
}
