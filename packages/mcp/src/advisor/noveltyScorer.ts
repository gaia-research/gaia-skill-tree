import type { GaiaGraph } from "../graph/types.js";
import { AbstractAdvisor, type AdvisorContext } from "./types.js";

function tokenize(text: string): Set<string> {
  return new Set(
    text
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, " ")
      .split(/\s+/)
      .filter((w) => w.length > 2)
  );
}

function keywordOverlap(a: Set<string>, b: Set<string>): number {
  let intersection = 0;
  for (const word of a) {
    if (b.has(word)) intersection++;
  }
  const union = a.size + b.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

export interface NoveltyResult {
  isNovel: boolean;
  closestMatch: { id: string; name: string; similarity: number } | null;
  confidence: number;
}

function scoreNoveltyDescription(description: string, graph: GaiaGraph): NoveltyResult {
  const queryTokens = tokenize(description);
  let bestMatch: { id: string; name: string; similarity: number } | null = null;
  let bestScore = 0;

  for (const skill of graph.skills) {
    const skillTokens = tokenize(`${skill.name} ${skill.description}`);
    const score = keywordOverlap(queryTokens, skillTokens);
    if (score > bestScore) {
      bestScore = score;
      bestMatch = { id: skill.id, name: skill.name, similarity: score };
    }
  }

  return {
    isNovel: bestScore < 0.3,
    closestMatch: bestMatch,
    confidence: bestScore < 0.1 ? 0.9 : bestScore < 0.2 ? 0.7 : bestScore < 0.3 ? 0.5 : 0.2,
  };
}

export class NoveltyScorer extends AbstractAdvisor<NoveltyResult> {
  constructor() {
    super("novelty-scorer");
  }

  analyze(context: AdvisorContext): NoveltyResult {
    const description = context.proposedDescription ?? context.projectSignals?.join(" ") ?? "";
    return scoreNoveltyDescription(description, this.requireGraph(context));
  }
}

export const noveltyScorer = new NoveltyScorer();

export function scoreNovelty(
  description: string,
  graph: GaiaGraph
): NoveltyResult {
  return noveltyScorer.analyze({ graph, proposedDescription: description });
}
