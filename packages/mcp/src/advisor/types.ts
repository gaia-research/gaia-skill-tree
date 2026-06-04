import type { GaiaGraph, UserSkillTree } from "../graph/types.js";

export interface AdvisorContext {
  graph?: GaiaGraph;
  userTree?: UserSkillTree | null;
  ownedSkillIds?: string[];
  connectedTools?: string[];
  projectSignals?: string[];
  detectedSkillIds?: string[];
  proposedDescription?: string;
}

export abstract class AbstractAdvisor<TResult> {
  constructor(public readonly id: string) {}

  abstract analyze(context: AdvisorContext): TResult;

  protected requireGraph(context: AdvisorContext): GaiaGraph {
    if (!context.graph) {
      throw new Error(`${this.id} requires AdvisorContext.graph`);
    }
    return context.graph;
  }

  protected ownedSkillIds(context: AdvisorContext): string[] {
    return this.dedupe(
      context.ownedSkillIds ??
        context.userTree?.unlockedSkills.map((skill) => skill.skillId) ??
        []
    );
  }

  protected detectedSkillIds(context: AdvisorContext): string[] {
    return this.dedupe(context.detectedSkillIds ?? []);
  }

  protected dedupe(items: string[]): string[] {
    return [...new Set(items.filter((item) => item.length > 0))];
  }
}

