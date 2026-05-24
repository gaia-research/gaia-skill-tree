import { readFileSync, existsSync } from "node:fs";
import { join } from "node:path";
import { homedir } from "node:os";
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

function readLocalConfig(): Partial<GaiaConfig> | null {
  const tomlPath = join(process.cwd(), ".gaia", "config.toml");
  if (existsSync(tomlPath)) {
    try {
      return parseGaiaConfig(readFileSync(tomlPath, "utf-8"));
    } catch {}
  }
  const jsonPath = join(process.cwd(), ".gaia", "config.json");
  if (existsSync(jsonPath)) {
    try {
      return JSON.parse(readFileSync(jsonPath, "utf-8"));
    } catch {}
  }
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

  // Check if CWD is a registry
  const cwd = process.cwd();
  if (existsSync(join(cwd, "registry", "gaia.json"))) {
    return cwd;
  }

  return null;
}
