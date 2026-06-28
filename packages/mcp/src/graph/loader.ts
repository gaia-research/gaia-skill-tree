import { getCached, getEtag, putCache } from "../config/cache.js";
import { resolveRegistryPath, resolveRegistryUrl } from "../config/identity.js";
import type { GaiaGraph } from "./types.js";
import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";

const REGISTRY_URL =
  "https://raw.githubusercontent.com/gaia-research/gaia-skill-tree/main/docs/graph/gaia.json";

const USERNAME_RE = /^[a-zA-Z0-9][a-zA-Z0-9-]{0,37}[a-zA-Z0-9]$|^[a-zA-Z0-9]$/;

let cachedGraph: GaiaGraph | null = null;

export async function loadGraph(registryUrl?: string): Promise<GaiaGraph> {
  // Priority: argument > local registry path > local config URL > default URL
  let url = registryUrl;
  if (!url) {
    const localPath = resolveRegistryPath();
    if (localPath) {
      const graphPath = join(localPath, "registry", "gaia.json");
      if (existsSync(graphPath)) {
        url = graphPath;
      }
    }
  }
  if (!url) {
    url = resolveRegistryUrl() ?? REGISTRY_URL;
  }

  // Handle local file path
  if (existsSync(url)) {
    try {
      const data = readFileSync(url, "utf-8");
      cachedGraph = JSON.parse(data);
      return cachedGraph!;
    } catch (err) {
      console.error(`Failed to read local registry at ${url}:`, err);
    }
  }

  const cacheKey = "gaia_graph";
  const cached = getCached(cacheKey);
  if (cached && !cached.stale) {
    if (!cachedGraph) {
      cachedGraph = JSON.parse(cached.data);
    }
    return cachedGraph!;
  }

  const headers: Record<string, string> = {
    Accept: "application/json",
  };

  const etag = getEtag(cacheKey);
  if (etag) {
    headers["If-None-Match"] = etag;
  }

  try {
    const res = await fetch(url, { headers });

    if (res.status === 304 && cached) {
      cachedGraph = JSON.parse(cached.data);
      return cachedGraph!;
    }

    if (!res.ok) {
      if (cached) {
        cachedGraph = JSON.parse(cached.data);
        return cachedGraph!;
      }
      throw new Error(`Failed to fetch registry: ${res.status}`);
    }

    const data = await res.text();
    const newEtag = res.headers.get("etag") ?? "";
    putCache(cacheKey, data, newEtag);
    cachedGraph = JSON.parse(data);
    return cachedGraph!;
  } catch (err) {
    if (cached) {
      cachedGraph = JSON.parse(cached.data);
      return cachedGraph!;
    }
    throw err;
  }
}

export async function loadUserTree(
  username: string,
  registryUrl?: string
): Promise<Record<string, unknown> | null> {
  if (!USERNAME_RE.test(username)) return null;

  const localPath = resolveRegistryPath();
  if (!registryUrl && localPath) {
    const treePath = join(localPath, "skill-trees", username, "skill-tree.json");
    if (existsSync(treePath)) {
      try {
        return JSON.parse(readFileSync(treePath, "utf-8")) as Record<string, unknown>;
      } catch {
        return null;
      }
    }
  }

  const baseUrl =
    registryUrl ??
    resolveRegistryUrl()?.replace("/registry/gaia.json", "") ??
    REGISTRY_URL.replace("/registry/gaia.json", "");
  const url = `${baseUrl}/skill-trees/${encodeURIComponent(username)}/skill-tree.json`;

  try {
    const res = await fetch(url);
    if (!res.ok) return null;
    return (await res.json()) as Record<string, unknown>;
  } catch {
    return null;
  }
}
