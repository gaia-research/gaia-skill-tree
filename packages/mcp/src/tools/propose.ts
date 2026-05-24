import { loadGraph, loadUserTree } from "../graph/loader.js";
import { resolveIdentity } from "../config/identity.js";
import { createPullRequest } from "../utils/github.js";
import { scoreNovelty } from "../advisor/noveltyScorer.js";
import type { UserSkillTree, Skill, GaiaGraph } from "../graph/types.js";

interface ProposeInput {
  skillId?: string;
  name?: string;
  description?: string;
  type?: "basic" | "extra" | "unique" | "ultimate";
  prerequisites?: string[];
}

export async function propose(input: ProposeInput): Promise<string> {
  const graph = await loadGraph();
  const user = resolveIdentity();
  const token = process.env.GITHUB_TOKEN ?? process.env.GH_TOKEN;

  if (!user) {
    return "No Gaia user configured. Set GAIA_USER environment variable.";
  }
  if (!token) {
    return "No GitHub token found. Set GITHUB_TOKEN or GH_TOKEN environment variable to open PRs.";
  }

  if (input.skillId) {
    return await claimFusion(input.skillId, user, token, graph);
  }

  if (input.name && input.description) {
    return await proposeNovel(input, user, token, graph);
  }

  return "Provide either a skillId to fuse an existing skill, or name + description to propose a new one.";
}

async function claimFusion(
  skillId: string,
  user: string,
  token: string,
  graph: GaiaGraph
): Promise<string> {
  const skill = graph.skills.find((s: Skill) => s.id === skillId);
  if (!skill) {
    return `Skill "${skillId}" not found in the registry.`;
  }

  const rawTree = await loadUserTree(user);
  const tree: UserSkillTree = rawTree
    ? (rawTree as unknown as UserSkillTree)
    : {
        userId: user,
        updatedAt: new Date().toISOString().split("T")[0],
        unlockedSkills: [],
        pendingCombinations: [],
        stats: { totalUnlocked: 0, highestRarity: "common", deepestLineage: 0 },
      };

  if (tree.unlockedSkills.some((s) => s.skillId === skillId)) {
    return `You already own "${skill.name}".`;
  }

  tree.unlockedSkills.push({
    skillId: skill.id,
    level: skill.level,
    unlockedAt: new Date().toISOString().split("T")[0],
    unlockedIn: "mcp-server",
    combinedFrom: skill.prerequisites,
  });
  tree.stats.totalUnlocked = tree.unlockedSkills.length;
  tree.updatedAt = new Date().toISOString().split("T")[0];
  tree.pendingCombinations = tree.pendingCombinations.filter(
    (p) => p.candidateResult !== skillId
  );

  const branch = `gaia/${user}/fuse-${skillId}`;
  const prUrl = await createPullRequest(token, {
    owner: "mbtiongson1",
    repo: "gaia-skill-tree",
    title: `[skill-tree] ${user}: fuse ${skill.name}`,
    body: `## Skill Fusion\n\n**User:** ${user}\n**Skill:** ${skill.name} (${skill.id})\n**Type:** ${skill.type}\n**Prerequisites met:** ${skill.prerequisites.join(", ")}\n\nClaimed via MCP server.`,
    branch,
    files: [
      {
        path: `skill-trees/${user}/skill-tree.json`,
        content: JSON.stringify(tree, null, 2) + "\n",
      },
    ],
  });

  const prVerb = prUrl.startsWith("http") ? "PR" : "Status";
  return `Fusion claimed! ${prVerb}: ${prUrl}\n\n**${skill.name}** (${skill.type}, ${skill.level}, ${skill.rarity}) added to your tree.`;
}

async function proposeNovel(
  input: ProposeInput,
  user: string,
  token: string,
  graph: GaiaGraph
): Promise<string> {
  const novelty = scoreNovelty(input.description!, graph);

  if (!novelty.isNovel && novelty.closestMatch) {
    return `This skill closely matches existing skill **${novelty.closestMatch.name}** (${Math.round(novelty.closestMatch.similarity * 100)}% similar). Did you mean to fuse "${novelty.closestMatch.id}" instead? If this is genuinely different, rephrase the description to be more specific.`;
  }

  const id = (input.name!)
    .toLowerCase()
    .replace(/[^a-z0-9\s]/g, "")
    .replace(/\s+/g, "-");

  const newSkill: Partial<Skill> = {
    id,
    name: input.name!,
    type: input.type ?? "basic",
    level: "1★",
    rarity: "common",
    description: input.description!,
    prerequisites: input.prerequisites ?? [],
    derivatives: [],
    conditions: "",
    evidence: [
      {
        class: "C",
        source: `proposed-by-${user}-via-mcp`,
        evaluator: user,
        date: new Date().toISOString().split("T")[0],
        notes: "Proposed via Gaia MCP server.",
      },
    ],
    knownAgents: [],
    status: "provisional",
    createdAt: new Date().toISOString().split("T")[0],
    updatedAt: new Date().toISOString().split("T")[0],
    version: "0.1.0",
  };

  const branch = `gaia/${user}/propose-${id}`;
  const prUrl = await createPullRequest(token, {
    owner: "mbtiongson1",
    repo: "gaia-skill-tree",
    title: `[new-skill] Propose: ${input.name}`,
    body: `## New Skill Proposal\n\n**Proposed by:** ${user}\n**Name:** ${input.name}\n**Type:** ${input.type ?? "basic"}\n**Description:** ${input.description}\n**Prerequisites:** ${(input.prerequisites ?? []).join(", ") || "none"}\n\nNovelty score: ${Math.round(novelty.confidence * 100)}%\nClosest existing: ${novelty.closestMatch?.name ?? "none"} (${Math.round((novelty.closestMatch?.similarity ?? 0) * 100)}%)\n\n---\n\n\`\`\`json\n${JSON.stringify(newSkill, null, 2)}\n\`\`\``,
    branch,
    files: [
      {
        path: `proposals/${id}.json`,
        content: JSON.stringify(newSkill, null, 2) + "\n",
      },
    ],
  });

  const prVerb = prUrl.startsWith("http") ? "PR" : "Status";
  return `Novel skill proposed! ${prVerb}: ${prUrl}\n\n**${input.name}** — pending review by maintainers.`;
}
