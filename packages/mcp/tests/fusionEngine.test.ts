import { describe, it, expect } from "vitest";
import { detectCombinations, fusionEngine } from "../src/advisor/fusionEngine.js";
import type { GaiaGraph } from "../src/graph/types.js";

const mockGraph: GaiaGraph = {
  version: "0.2.0",
  generatedAt: "2026-04-28",
  meta: { typeLabels: {}, levelLabels: {}, rarityLabels: {} },
  skills: [
    { id: "web-search", name: "Web Search", type: "basic", level: "2★", rarity: "common", description: "", prerequisites: [], derivatives: ["web-scrape", "research"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "parse-html", name: "Parse HTML", type: "basic", level: "2★", rarity: "common", description: "", prerequisites: [], derivatives: ["web-scrape"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "extract-entities", name: "Extract Entities", type: "basic", level: "2★", rarity: "common", description: "", prerequisites: [], derivatives: ["web-scrape"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "summarize", name: "Summarize", type: "basic", level: "2★", rarity: "common", description: "", prerequisites: [], derivatives: ["research"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "cite-sources", name: "Cite Sources", type: "basic", level: "2★", rarity: "common", description: "", prerequisites: [], derivatives: ["research"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "web-scrape", name: "Web Scrape", type: "extra", level: "3★", rarity: "uncommon", description: "", prerequisites: ["web-search", "parse-html", "extract-entities"], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0", demerits: ["experimental-feature"] },
    { id: "research", name: "Research", type: "extra", level: "3★", rarity: "uncommon", description: "", prerequisites: ["web-search", "summarize", "cite-sources"], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
  ],
  edges: [],
};

describe("fusionEngine", () => {
  it("detects a ready fusion when all prerequisites are available", () => {
    const result = detectCombinations(
      mockGraph,
      [],
      ["web-search", "parse-html", "extract-entities"]
    );
    const ready = result.filter((c) => c.status === "ready");
    expect(ready).toHaveLength(1);
    expect(ready[0].candidateResult).toBe("web-scrape");
  });

  it("detects one-away fusions when missing exactly 1 prerequisite", () => {
    const result = detectCombinations(mockGraph, [], ["web-search", "parse-html"]);
    const oneAway = result.filter((c) => c.status === "one_away");
    expect(oneAway.some((c) => c.candidateResult === "web-scrape")).toBe(true);
    const match = oneAway.find((c) => c.candidateResult === "web-scrape")!;
    expect(match.missingSkills).toEqual(["extract-entities"]);
  });

  it("does not suggest skills the user already owns", () => {
    const result = detectCombinations(
      mockGraph,
      ["web-scrape"],
      ["web-search", "parse-html", "extract-entities"]
    );
    expect(result.find((c) => c.candidateResult === "web-scrape")).toBeUndefined();
  });

  it("uses effective levelFloor when demerits exist", () => {
    const result = detectCombinations(
      mockGraph,
      [],
      ["web-search", "parse-html", "extract-entities"]
    );
    const ready = result.find((c) => c.candidateResult === "web-scrape");
    expect(ready?.levelFloor).toBe("2★");
  });

  it("combines owned and detected skills for fusion detection", () => {
    const result = detectCombinations(
      mockGraph,
      ["web-search", "summarize"],
      ["cite-sources"]
    );
    const ready = result.filter((c) => c.status === "ready");
    expect(ready.some((c) => c.candidateResult === "research")).toBe(true);
  });

  it("returns empty array when no fusions are possible", () => {
    const result = detectCombinations(mockGraph, [], ["summarize"]);
    const ready = result.filter((c) => c.status === "ready");
    expect(ready).toHaveLength(0);
  });

  it("reads graph, owned skills, and detected skills from AdvisorContext", () => {
    const result = fusionEngine.analyze({
      graph: mockGraph,
      ownedSkillIds: ["web-search", "summarize"],
      detectedSkillIds: ["cite-sources"],
    });

    expect(result.some((c) => c.candidateResult === "research" && c.status === "ready")).toBe(true);
  });
});
