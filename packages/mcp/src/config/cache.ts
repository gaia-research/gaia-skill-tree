import { readFileSync, writeFileSync, mkdirSync, existsSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

interface CacheEntry {
  etag: string;
  lastFetch: number;
  filePath: string;
}

const GAIA_HOME = process.env.GAIA_HOME || join(homedir(), ".gaia");
const CACHE_DIR = join(GAIA_HOME, "cache");
const CACHE_META = join(CACHE_DIR, "meta.json");
const TTL_MS = 5 * 60 * 1000;

function ensureCacheDir(): void {
  if (!existsSync(CACHE_DIR)) {
    mkdirSync(CACHE_DIR, { recursive: true });
  }
}

function readMeta(): Record<string, CacheEntry> {
  try {
    return JSON.parse(readFileSync(CACHE_META, "utf-8"));
  } catch {
    return {};
  }
}

function writeMeta(meta: Record<string, CacheEntry>): void {
  ensureCacheDir();
  writeFileSync(CACHE_META, JSON.stringify(meta, null, 2));
}

export function getCached(key: string): { data: string; stale: boolean } | null {
  const meta = readMeta();
  const entry = meta[key];
  if (!entry) return null;

  try {
    const data = readFileSync(entry.filePath, "utf-8");
    const stale = Date.now() - entry.lastFetch > TTL_MS;
    return { data, stale };
  } catch {
    return null;
  }
}

export function getEtag(key: string): string | null {
  const meta = readMeta();
  return meta[key]?.etag ?? null;
}

export function putCache(key: string, data: string, etag: string): void {
  ensureCacheDir();
  const filePath = join(CACHE_DIR, `${key.replace(/[^a-z0-9]/gi, "_")}.json`);
  writeFileSync(filePath, data);

  const meta = readMeta();
  meta[key] = { etag, lastFetch: Date.now(), filePath };
  writeMeta(meta);
}
