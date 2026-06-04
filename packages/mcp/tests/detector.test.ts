import { describe, it, expect } from "vitest";
import { detectSkillsFromTools, detectSkillsFromSignals, skillDetector } from "../src/advisor/detector.js";

describe("detector", () => {
  describe("detectSkillsFromTools", () => {
    it("maps common MCP tool names to skill IDs", () => {
      const result = detectSkillsFromTools(["web_search", "bash", "fetch"]);
      expect(result).toContain("web-search");
      expect(result).toContain("execute-bash");
      expect(result).toContain("parse-html");
    });

    it("handles variant tool names", () => {
      const result = detectSkillsFromTools(["brave_web_search", "run_command"]);
      expect(result).toContain("web-search");
      expect(result).toContain("execute-bash");
    });

    it("falls back to pattern matching for unknown tools", () => {
      const result = detectSkillsFromTools(["my_custom_search_tool"]);
      expect(result).toContain("web-search");
    });

    it("returns empty for unrecognized tools", () => {
      const result = detectSkillsFromTools(["completely_unknown_xyz"]);
      expect(result).toHaveLength(0);
    });

    it("deduplicates results", () => {
      const result = detectSkillsFromTools(["web_search", "brave_search", "google_search"]);
      const webSearchCount = result.filter((s) => s === "web-search").length;
      expect(webSearchCount).toBe(1);
    });
  });

  describe("detectSkillsFromSignals", () => {
    it("detects skills from project signal text", () => {
      const result = detectSkillsFromSignals(["building a web scraper", "using cheerio to parse HTML"]);
      expect(result).toContain("web-scrape");
      expect(result).toContain("parse-html");
    });

    it("returns empty for unrelated signals", () => {
      const result = detectSkillsFromSignals(["configuring database connection pooling"]);
      expect(result).toHaveLength(0);
    });
  });

  describe("SkillDetector", () => {
    it("returns a shared context with combined detected skills", () => {
      const result = skillDetector.analyze({
        connectedTools: ["web_search"],
        projectSignals: ["using cheerio to parse HTML"],
        detectedSkillIds: ["summarize"],
      });

      expect(result.fromTools).toEqual(["web-search"]);
      expect(result.fromSignals).toEqual(["parse-html"]);
      expect(result.allDetected).toEqual(["summarize", "web-search", "parse-html"]);
      expect(result.context.detectedSkillIds).toEqual(result.allDetected);
    });
  });
});
