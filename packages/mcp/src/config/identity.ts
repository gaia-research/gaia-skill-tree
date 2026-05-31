import { readFileSync, existsSync } from "node:fs";
import { join, dirname } from "node:path";
import { homedir } from "node:os";
import { fileURLToPath } from "node:url";
import type { GaiaConfig } from "../graph/types.js";

function parseGaiaConfig(raw: string): Partial<GaiaConfig> {
  const config: Partial<GaiaConfig> = {};
  for (const line of raw.split("\n")) {
    const trimmed = line.trim();
    if (!trimmed || trimmed.startsWith("#") || !trimmed.includes("=")) continue;
    const [key, ...rest] = trimmed.split("=");
    const value = rest.join("=").trim().replace(/^"(.*)"$/, "$1");

    const k = key.trim();
    if (k === "username" || k === "gaiaUser") config.gaiaUser = value;
    if (k === "gaiaRegistryRef") config.gaiaRegistryRef = value;
    if (k === "localRegistryPath") config.localRegistryPath = value;
  }
  return config;
}

/**
 * Walk up the directory tree starting from `startDir`, looking for a
 * `.gaia/config.toml` or `.gaia/config.json` file. Returns the first config
 * found, or null if none exists before the filesystem root.
 */
function walkUpForConfig(startDir: string): Partial<GaiaConfig> | null {
  let current = startDir;
  while (true) {
    const tomlPath = join(current, ".gaia", "config.toml");
    if (existsSync(tomlPath)) {
      try {
        return parseGaiaConfig(readFileSync(tomlPath, "utf-8"));
      } catch {}
    }
    const jsonPath = join(current, ".gaia", "config.json");
    if (existsSync(jsonPath)) {
      try {
        return JSON.parse(readFileSync(jsonPath, "utf-8"));
      } catch {}
    }

    const parent = dirname(current);
    if (parent === current) {
      // Reached the filesystem root without finding a config
      break;
    }
    current = parent;
  }
  return null;
}

/**
 * Locate `.gaia/config.*` by walking up from the module's own location
 * (reliable regardless of cwd), then fall back to process.cwd() if the
 * module-relative walk finds nothing.
 */
function readLocalConfig(): Partial<GaiaConfig> | null {
  // Primary: walk up from the directory that contains this compiled module file.
  // This resolves correctly even when the MCP host sets cwd to something unrelated.
  const moduleDir = dirname(fileURLToPath(import.meta.url));
  const fromModule = walkUpForConfig(moduleDir);
  if (fromModule) return fromModule;

  // Fallback: walk up from process.cwd() for back-compat with direct repo-root usage.
  const fromCwd = walkUpForConfig(process.cwd());
  if (fromCwd) return fromCwd;

  return null;
}

function readGlobalConfig(): Partial<GaiaConfig> | null {
  const gaiaHome = process.env.GAIA_HOME || join(homedir(), ".gaia");
  const jsonPath = join(gaiaHome, "config.json");
  if (existsSync(jsonPath)) {
    try {
      return JSON.parse(readFileSync(jsonPath, "utf-8"));
    } catch {}
  }
  return null;
}

export function resolveIdentity(): string | null {
  if (process.env.GAIA_USER) {
    return process.env.GAIA_USER;
  }

  const local = readLocalConfig();
  if (local?.gaiaUser) return local.gaiaUser;

  const global = readGlobalConfig();
  if (global?.gaiaUser) return global.gaiaUser;

  return null;
}

export function resolveRegistryUrl(): string | null {
  if (process.env.GAIA_REGISTRY_URL) {
    return process.env.GAIA_REGISTRY_URL;
  }

  const local = readLocalConfig();
  if (local?.gaiaRegistryRef) return local.gaiaRegistryRef;

  const global = readGlobalConfig();
  // Python CLI saves global registry path in 'defaultRegistry', not URL
  // but if it's a URL-like string we can use it.
  const defaultReg = (global as any)?.defaultRegistry;
  if (defaultReg && (defaultReg.startsWith("http://") || defaultReg.startsWith("https://"))) {
    return defaultReg;
  }

  return null;
}

export function resolveRegistryPath(): string | null {
  if (process.env.GAIA_REGISTRY_PATH) {
    return process.env.GAIA_REGISTRY_PATH;
  }

  const local = readLocalConfig();
  if (local?.localRegistryPath) return local.localRegistryPath;

  const global = readGlobalConfig();
  const defaultReg = (global as any)?.defaultRegistry;
  if (defaultReg && !defaultReg.startsWith("http://") && !defaultReg.startsWith("https://")) {
    return defaultReg;
  }

  // Check if the module's walk-up root contains a registry, then fall back to CWD.
  const moduleDir = dirname(fileURLToPath(import.meta.url));
  let current = moduleDir;
  while (true) {
    if (existsSync(join(current, "registry", "gaia.json"))) {
      return current;
    }
    const parent = dirname(current);
    if (parent === current) break;
    current = parent;
  }

  const cwd = process.cwd();
  if (existsSync(join(cwd, "registry", "gaia.json"))) {
    return cwd;
  }

  return null;
}
