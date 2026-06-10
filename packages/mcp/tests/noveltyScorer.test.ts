import { describe, it, expect } from "vitest";
import { scoreNovelty, noveltyScorer } from "../src/advisor/noveltyScorer.js";
import type { GaiaGraph } from "../src/graph/types.js";

const mockGraph: GaiaGraph = {
  version: "0.2.0",
  generatedAt: "2026-04-28",
  meta: { typeLabels: {}, levelLabels: {} },
  skills: [
    { id: "web-search", name: "Web Search", type: "basic", level: "2★", description: "Searches the web for information using search engine APIs", prerequisites: [], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "summarize", name: "Summarize", type: "basic", level: "2★", description: "Condenses long text into concise summaries preserving key information", prerequisites: [], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
  ],
  edges: [],
};

describe("noveltyScorer", () => {
  it("flags novel descriptions as novel", () => {
    const result = scoreNovelty("converts PDF documents into structured markdown with table extraction", mockGraph);
    expect(result.isNovel).toBe(true);
    expect(result.confidence).toBeGreaterThan(0.4);
  });

  it("flags similar descriptions as not novel", () => {
    const result = scoreNovelty("searches the web for information using APIs", mockGraph);
    expect(result.isNovel).toBe(false);
    expect(result.closestMatch?.id).toBe("web-search");
  });

  it("returns closestMatch with similarity score", () => {
    const result = scoreNovelty("summarizes text content into brief overviews", mockGraph);
    expect(result.closestMatch).not.toBeNull();
    expect(result.closestMatch!.similarity).toBeGreaterThan(0);
  });

  it("scores novelty from AdvisorContext project signals", () => {
    const result = noveltyScorer.analyze({
      graph: mockGraph,
      projectSignals: ["summarizes text content into brief overviews"],
    });

    expect(result.closestMatch?.id).toBe("summarize");
  });
});
