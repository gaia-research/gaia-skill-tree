import { describe, it, expect } from "vitest";
import { getAncestors, getDescendants, getLineageDepth, getSkillsByType } from "../src/graph/dag.js";
import type { GaiaGraph } from "../src/graph/types.js";

const mockGraph: GaiaGraph = {
  version: "0.2.0",
  generatedAt: "2026-04-28",
  meta: { typeLabels: {}, levelLabels: {}, rarityLabels: {} },
  skills: [
    { id: "tokenize", name: "Tokenize", type: "basic", level: "1★", rarity: "common", description: "", prerequisites: [], derivatives: ["embed-text"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "embed-text", name: "Embed Text", type: "basic", level: "2★", rarity: "common", description: "", prerequisites: ["tokenize"], derivatives: ["rag-pipeline"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "retrieve", name: "Retrieve", type: "basic", level: "2★", rarity: "common", description: "", prerequisites: [], derivatives: ["rag-pipeline"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "chunk-document", name: "Chunk Document", type: "basic", level: "2★", rarity: "common", description: "", prerequisites: [], derivatives: ["rag-pipeline"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "score-relevance", name: "Score Relevance", type: "basic", level: "2★", rarity: "common", description: "", prerequisites: [], derivatives: ["rag-pipeline"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "rag-pipeline", name: "RAG Pipeline", type: "extra", level: "3★", rarity: "rare", description: "", prerequisites: ["retrieve", "chunk-document", "embed-text", "score-relevance"], derivatives: ["true-oracle"], conditions: "", evidence: [], knownAgents: [], status: "validated", createdAt: "", updatedAt: "", version: "0.1.0" },
    { id: "true-oracle", name: "True Oracle", type: "ultimate", level: "5★", rarity: "legendary", description: "", prerequisites: ["rag-pipeline"], derivatives: [], conditions: "", evidence: [], knownAgents: [], status: "provisional", createdAt: "", updatedAt: "", version: "0.1.0" },
  ],
  edges: [],
};

describe("dag", () => {
  describe("getAncestors", () => {
    it("returns empty for atomic skills with no prerequisites", () => {
      expect(getAncestors(mockGraph, "tokenize")).toHaveLength(0);
    });

    it("returns direct prerequisites", () => {
      const ancestors = getAncestors(mockGraph, "rag-pipeline");
      const ids = ancestors.map((a) => a.id);
      expect(ids).toContain("retrieve");
      expect(ids).toContain("chunk-document");
      expect(ids).toContain("embed-text");
      expect(ids).toContain("score-relevance");
    });

    it("walks transitive ancestors", () => {
      const ancestors = getAncestors(mockGraph, "rag-pipeline");
      const ids = ancestors.map((a) => a.id);
      expect(ids).toContain("tokenize"); // ancestor of embed-text
    });

    it("walks deep lineage for legendary", () => {
      const ancestors = getAncestors(mockGraph, "true-oracle");
      const ids = ancestors.map((a) => a.id);
      expect(ids).toContain("rag-pipeline");
      expect(ids).toContain("embed-text");
      expect(ids).toContain("tokenize");
    });

    it("does not visit cycles or duplicate nodes", () => {
      const ancestors = getAncestors(mockGraph, "rag-pipeline");
      const ids = ancestors.map((a) => a.id);
      const unique = new Set(ids);
      expect(ids.length).toBe(unique.size);
    });
  });

  describe("getDescendants", () => {
    it("returns empty for leaf skills", () => {
      expect(getDescendants(mockGraph, "true-oracle")).toHaveLength(0);
    });

    it("returns direct children", () => {
      const descendants = getDescendants(mockGraph, "retrieve");
      expect(descendants.map((d) => d.id)).toContain("rag-pipeline");
    });

    it("walks transitive descendants", () => {
      const descendants = getDescendants(mockGraph, "tokenize");
      const ids = descendants.map((d) => d.id);
      expect(ids).toContain("embed-text");
      expect(ids).toContain("rag-pipeline");
      expect(ids).toContain("true-oracle");
    });
  });

  describe("getLineageDepth", () => {
    it("returns 0 for atomics with no prerequisites", () => {
      expect(getLineageDepth(mockGraph, "tokenize")).toBe(0);
    });

    it("returns 1 for skills with only atomic prerequisites", () => {
      expect(getLineageDepth(mockGraph, "embed-text")).toBe(1);
    });

    it("returns correct depth for composites", () => {
      // rag-pipeline -> embed-text -> tokenize = depth 2
      expect(getLineageDepth(mockGraph, "rag-pipeline")).toBe(2);
    });

    it("returns correct depth for legendaries", () => {
      expect(getLineageDepth(mockGraph, "true-oracle")).toBe(3);
    });
  });

  describe("getSkillsByType", () => {
    it("filters by type", () => {
      const basics = getSkillsByType(mockGraph, "basic");
      expect(basics.every((s) => s.type === "basic")).toBe(true);
      expect(basics.length).toBe(5);
    });

    it("returns empty array for types not in the graph", () => {
      const emptyResult = getSkillsByType(mockGraph, "fusion" as any);
      expect(emptyResult).toHaveLength(0);
    });
  });
});
