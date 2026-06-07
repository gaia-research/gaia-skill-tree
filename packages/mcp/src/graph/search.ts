import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { Skill, GaiaGraph, NamedSkill } from "./types.js";
import { searchNamedSkills } from "./namedLoader.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const SIMILARITY_PATH = join(__dirname, "../../../registry/similarity.json");

function trigrams(s: string): Set<string> {
  const padded = `  ${s.toLowerCase()}  `;
  const set = new Set<string>();
  for (let i = 0; i < padded.length - 2; i++) {
    set.add(padded.slice(i, i + 3));
  }
  return set;
}

function similarity(a: string | Set<string>, b: string | Set<string>): number {
  const ta = typeof a === "string" ? trigrams(a) : a;
  const tb = typeof b === "string" ? trigrams(b) : b;
  let intersection = 0;
  const smaller = ta.size < tb.size ? ta : tb;
  const larger = ta.size < tb.size ? tb : ta;
  for (const t of smaller) {
    if (larger.has(t)) intersection++;
  }
  const union = ta.size + tb.size - intersection;
  return union === 0 ? 0 : intersection / union;
}

export function searchSkills(graph: GaiaGraph, query: string, limit = 5): Skill[] {
  const q = query.toLowerCase().trim();

  const exact = graph.skills.find(
    (s) => s.id === q || s.name.toLowerCase() === q
  );
  if (exact) return [exact];

  const qTrigrams = trigrams(q);

  const scored = graph.skills
    .map((skill) => ({
      skill,
      score: Math.max(
        similarity(qTrigrams, skill.id),
        similarity(qTrigrams, skill.name),
        similarity(qTrigrams, skill.description.slice(0, 80))
      ),
    }))
    .filter((x) => x.score > 0.15)
    .sort((a, b) => b.score - a.score);

  return scored.slice(0, limit).map((x) => x.skill);
}

export function findSkillById(graph: GaiaGraph, id: string): Skill | undefined {
  return graph.skills.find((s) => s.id === id);
}

// --- Embedding-based similarity search ---

interface SimilarityPair {
  a: string;
  b: string;
  score: number;
}

interface SimilarityData {
  generatedAt: string;
  threshold: number;
  pairs: SimilarityPair[];
}

let cachedSimilarity: SimilarityData | null = null;

function loadSimilarityData(path?: string): SimilarityData | null {
  const p = path || SIMILARITY_PATH;
  if (!existsSync(p)) return null;
  if (!cachedSimilarity) {
    cachedSimilarity = JSON.parse(readFileSync(p, "utf-8"));
  }
  return cachedSimilarity;
}

export function searchByEmbeddingSimilarity(
  skillId: string,
  limit = 5
): { id: string; score: number }[] {
  const data = loadSimilarityData();
  if (!data) return [];

  const matches: { id: string; score: number }[] = [];
  for (const pair of data.pairs) {
    if (pair.a === skillId) {
      matches.push({ id: pair.b, score: pair.score });
    } else if (pair.b === skillId) {
      matches.push({ id: pair.a, score: pair.score });
    }
  }

  return matches.sort((a, b) => b.score - a.score).slice(0, limit);
}

// --- Combined search across generic + named skills ---

export interface SearchResult {
  type: "generic" | "named";
  skill?: Skill;
  namedSkill?: NamedSkill;
  score: number;
}

export function searchAll(
  graph: GaiaGraph,
  query: string,
  limit = 10
): SearchResult[] {
  const q = query.toLowerCase().trim();
  const results: SearchResult[] = [];
  const qTrigrams = trigrams(q);

  const genericResults = graph.skills
    .map((skill) => ({
      skill,
      score: Math.max(
        similarity(qTrigrams, skill.id),
        similarity(qTrigrams, skill.name),
        similarity(qTrigrams, skill.description.slice(0, 80))
      ),
    }))
    .filter((x) => x.score > 0.15);

  for (const r of genericResults) {
    results.push({ type: "generic", skill: r.skill, score: r.score });
  }

  const namedResults = searchNamedSkills(query);
  for (const ns of namedResults) {
    const score = Math.max(
      similarity(qTrigrams, ns.id),
      similarity(qTrigrams, ns.name),
      similarity(qTrigrams, ns.description.slice(0, 80))
    );
    results.push({ type: "named", namedSkill: ns, score: Math.max(score, 0.5) });
  }

  return results.sort((a, b) => b.score - a.score).slice(0, limit);
}
