import { describe, it, expect, vi, beforeEach } from "vitest";
import type { GaiaGraph, UserSkillTree } from "../src/graph/types.js";

const mockGraph: GaiaGraph = {
  version: "0.2.0",
  generatedAt: "2026-04-28",
  meta: { typeLabels: {}, levelLabels: {} },
  skills: [
    { id: "web-search", name: "Web Search", type: "basic", level: "2★", description: "Searches the web", prerequisites: [], derivatives: ["web-scrape", "research"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "parse-html", name: "Parse HTML", type: "basic", level: "2★", description: "Parses HTML documents", prerequisites: [], derivatives: ["web-scrape"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "extract-entities", name: "Extract Entities", type: "basic", level: "2★", description: "Extracts named entities", prerequisites: [], derivatives: ["web-scrape"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "summarize", name: "Summarize", type: "basic", level: "2★", description: "Summarizes text", prerequisites: [], derivatives: ["research"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "cite-sources", name: "Cite Sources", type: "basic", level: "2★", description: "Cites sources", prerequisites: [], derivatives: ["research"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "web-scrape", name: "Web Scrape", type: "extra", level: "3★", description: "Scrapes and structures web data", prerequisites: ["web-search", "parse-html", "extract-entities"], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "research", name: "Research", type: "extra", level: "3★", description: "Researches topics", prerequisites: ["web-search", "summarize", "cite-sources"], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
  ],
  edges: [],
};

const mockTree: UserSkillTree = {
  userId: "testuser",
  updatedAt: "2026-04-28",
  unlockedSkills: [
    { skillId: "web-search", level: "2★", unlockedAt: "2026-04-20", unlockedIn: "test-repo", combinedFrom: [] },
    { skillId: "summarize", level: "2★", unlockedAt: "2026-04-21", unlockedIn: "test-repo", combinedFrom: [] },
  ],
  pendingCombinations: [],
  stats: { totalUnlocked: 2, deepestLineage: 0 },
};

vi.mock("../src/graph/loader.js", () => ({
  loadGraph: vi.fn(() => Promise.resolve(mockGraph)),
  loadUserTree: vi.fn(() => Promise.resolve(mockTree)),
}));

vi.mock("../src/config/identity.js", () => ({
  resolveIdentity: vi.fn(() => "testuser"),
}));

describe("suggest tool", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("suggests fusions when tools map to available skills", async () => {
    const { suggest } = await import("../src/tools/suggest.js");
    const result = await suggest(undefined, ["web_search", "fetch", "extract"]);
    expect(result).toContain("Web Scrape");
    expect(result).toContain("Ready to Fuse");
  });

  it("shows one-away candidates", async () => {
    const { suggest } = await import("../src/tools/suggest.js");
    // user owns web-search + summarize, detect cite-sources is missing
    const result = await suggest(undefined, ["web_search", "summarize"]);
    expect(result).toContain("One Skill Away");
    expect(result).toContain("Research");
  });

  it("shows detected skills section", async () => {
    const { suggest } = await import("../src/tools/suggest.js");
    const result = await suggest(undefined, ["bash"]);
    expect(result).toContain("Detected Skills");
    expect(result).toContain("execute-bash");
  });

  it("handles no context gracefully", async () => {
    const { suggest } = await import("../src/tools/suggest.js");
    const result = await suggest(undefined, undefined);
    // User has owned skills so should still get suggestions
    expect(result).toBeDefined();
  });
});

describe("scanContext tool", () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it("detects skills from connected tools", async () => {
    const { scanContext } = await import("../src/tools/scanContext.js");
    const result = await scanContext(["web_search", "bash", "fetch"], undefined);
    expect(result).toContain("Skills Identified");
    expect(result).toContain("Web Search");
  });

  it("detects fusions from tools", async () => {
    const { scanContext } = await import("../src/tools/scanContext.js");
    const result = await scanContext(["web_search", "fetch", "extract"], undefined);
    expect(result).toContain("Fusions Available");
  });

  it("detects novelty from project signals", async () => {
    const { scanContext } = await import("../src/tools/scanContext.js");
    const result = await scanContext(undefined, [
      "building a PDF to markdown converter with table extraction and OCR",
    ]);
    expect(result).toContain("Novel Capability Detected");
  });

  it("handles empty inputs", async () => {
    const { scanContext } = await import("../src/tools/scanContext.js");
    const result = await scanContext(undefined, undefined);
    expect(result).toContain("Detected 0 skills");
  });
});
