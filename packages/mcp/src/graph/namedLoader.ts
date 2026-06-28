import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { fileURLToPath } from "node:url";
import type { NamedSkill, NamedIndex } from "./types.js";
import { resolveRegistryPath } from "../config/identity.js";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const NAMED_INDEX_PATH = join(__dirname, "../../../registry/named-skills.json");

let cachedIndex: NamedIndex | null = null;

export function loadNamedIndex(indexPath?: string): NamedIndex {
  let path = indexPath;
  if (!path) {
    const localPath = resolveRegistryPath();
    if (localPath) {
      const p = join(localPath, "registry", "named-skills.json");
      if (existsSync(p)) {
        path = p;
      }
    }
  }
  if (!path) {
    path = NAMED_INDEX_PATH;
  }
  if (!existsSync(path)) {
    return { generatedAt: "", buckets: {} };
  }
  if (!cachedIndex) {
    const raw = readFileSync(path, "utf-8");
    cachedIndex = JSON.parse(raw) as NamedIndex;
  }
  return cachedIndex;
}

export function getNamedSkillsForGeneric(
  genericSkillId: string,
  indexPath?: string
): NamedSkill[] {
  const index = loadNamedIndex(indexPath);
  return index.buckets[genericSkillId] || [];
}

export function searchNamedSkills(query: string, indexPath?: string): NamedSkill[] {
  const index = loadNamedIndex(indexPath);
  const q = query.toLowerCase().trim();
  const results: NamedSkill[] = [];

  for (const bucket of Object.values(index.buckets)) {
    for (const skill of bucket) {
      if (
        skill.id.toLowerCase().includes(q) ||
        skill.name.toLowerCase().includes(q) ||
        (skill.description && skill.description.toLowerCase().includes(q)) ||
        (skill.tags && skill.tags.some((t) => t.includes(q)))
      ) {
        results.push(skill);
      }
    }
  }

  return results;
}

export function getAllNamedSkills(indexPath?: string): NamedSkill[] {
  const index = loadNamedIndex(indexPath);
  const all: NamedSkill[] = [];
  for (const bucket of Object.values(index.buckets)) {
    all.push(...bucket);
  }
  return all;
}

export function invalidateCache(): void {
  cachedIndex = null;
}
