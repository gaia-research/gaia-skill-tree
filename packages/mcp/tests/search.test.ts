import { describe, it, expect } from "vitest";
import { searchSkills, findSkillById, searchAll } from "../src/graph/search.js";
import type { GaiaGraph } from "../src/graph/types.js";

const mockGraph: GaiaGraph = {
  version: "0.2.0",
  generatedAt: "2026-04-28",
  meta: { typeLabels: {}, levelLabels: {} },
  skills: [
    { id: "web-search", name: "Web Search", type: "basic", level: "2★", description: "Searches the web", prerequisites: [], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "web-scrape", name: "Web Scrape", type: "extra", level: "3★", description: "Scrapes websites for data", prerequisites: ["web-search"], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "code-generation", name: "Code Generation", type: "basic", level: "3★", description: "Generates source code", prerequisites: [], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
  ],
  edges: [],
};

describe("search", () => {
  it("finds exact match by ID", () => {
    const results = searchSkills(mockGraph, "web-search");
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe("web-search");
  });

  it("finds exact match by name (case-insensitive)", () => {
    const results = searchSkills(mockGraph, "Web Search");
    expect(results).toHaveLength(1);
    expect(results[0].id).toBe("web-search");
  });

  it("fuzzy matches similar terms", () => {
    const results = searchSkills(mockGraph, "web scraping");
    expect(results.length).toBeGreaterThan(0);
    expect(results[0].id).toBe("web-scrape");
  });

  it("returns empty for completely unrelated query", () => {
    const results = searchSkills(mockGraph, "zzzzzzzzz");
    expect(results).toHaveLength(0);
  });
});

describe("findSkillById", () => {
  it("returns skill for valid ID", () => {
    const skill = findSkillById(mockGraph, "code-generation");
    expect(skill).toBeDefined();
    expect(skill!.name).toBe("Code Generation");
  });

  it("returns undefined for invalid ID", () => {
    expect(findSkillById(mockGraph, "nonexistent")).toBeUndefined();
  });
});

describe("searchAll", () => {
  it("returns generic skills from graph", () => {
    const results = searchAll(mockGraph, "web search");
    const generics = results.filter((r) => r.type === "generic");
    expect(generics.length).toBeGreaterThan(0);
  });

  it("result items have type field", () => {
    const results = searchAll(mockGraph, "code");
    for (const r of results) {
      expect(["generic", "named"]).toContain(r.type);
    }
  });

  it("returns empty when no match", () => {
    const results = searchAll(mockGraph, "zzzzzzzzz");
    expect(results).toHaveLength(0);
  });
});
