import * as fs from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";

const GAIA_HOME = process.env.GAIA_HOME || join(homedir(), ".gaia");
const CACHE_DIR = join(GAIA_HOME, "cache");
const CACHE_TTL_MS = 5 * 60 * 1000;

function ensureCacheDir(): void {
  if (!fs.existsSync(CACHE_DIR)) {
    fs.mkdirSync(CACHE_DIR, { recursive: true });
  }
}

export function getCachePath(key: string): string {
  return join(CACHE_DIR, `${key.replace(/[^a-z0-9]/gi, "_")}.json`);
}

export function getCached(key: string): { data: string; stale: boolean } | null {
  const p = getCachePath(key);
  if (!fs.existsSync(p)) return null;

  const stats = fs.statSync(p);
  const ageMs = Date.now() - stats.mtimeMs;
  const stale = ageMs > CACHE_TTL_MS;

  try {
    return { data: fs.readFileSync(p, "utf8"), stale };
  } catch {
    return null;
  }
}

export function getEtag(key: string): string | null {
  const p = getCachePath(key) + ".etag";
  if (!fs.existsSync(p)) return null;
  try {
    return fs.readFileSync(p, "utf8");
  } catch {
    return null;
  }
}

export function putCache(key: string, data: string, etag: string): void {
  ensureCacheDir();
  const filePath = getCachePath(key);
  fs.writeFileSync(filePath, data);
  const etagPath = filePath + ".etag";
  if (etag) {
    fs.writeFileSync(etagPath, etag);
  } else if (fs.existsSync(etagPath)) {
    fs.unlinkSync(etagPath);
  }
}
