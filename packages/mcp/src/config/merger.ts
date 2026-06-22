import * as fs from "fs";
import * as path from "path";
import * as os from "os";

export function loadJsonFile(filePath: string): any {
  try {
    if (fs.existsSync(filePath)) {
      const content = fs.readFileSync(filePath, "utf8");
      return JSON.parse(content);
    }
  } catch (error) {
    // Ignore error
  }
  return {};
}

export function mergeConfigs(globalConfig: any, localConfig: any): Record<string, string> {
  const extractEnv = (config: any): Record<string, string> => {
    if (!config) {
      return {};
    }

    const envVars: Record<string, string> = {};

    // 1. If it's a flat object of uppercase keys, assume they are environment variables
    for (const key of Object.keys(config)) {
      if (key === key.toUpperCase() && typeof config[key] === "string") {
        envVars[key] = config[key];
      }
    }

    // 2. If it has a top-level "env" object
    if (config.env && typeof config.env === "object") {
      for (const envKey of Object.keys(config.env)) {
        if (config.env[envKey] !== null && config.env[envKey] !== undefined) {
          envVars[envKey] = String(config.env[envKey]);
        }
      }
    }

    // 3. If it has "mcpServers" -> "gaia" -> "env"
    if (
      config.mcpServers &&
      config.mcpServers.gaia &&
      config.mcpServers.gaia.env &&
      typeof config.mcpServers.gaia.env === "object"
    ) {
      const gaiaEnv = config.mcpServers.gaia.env;
      for (const envKey of Object.keys(gaiaEnv)) {
        if (gaiaEnv[envKey] !== null && gaiaEnv[envKey] !== undefined) {
          envVars[envKey] = String(gaiaEnv[envKey]);
        }
      }
    }

    return envVars;
  };

  const globalEnv = extractEnv(globalConfig);
  const localEnv = extractEnv(localConfig);

  return { ...globalEnv, ...localEnv };
}

export function injectConfigEnv(): void {
  const globalPath = path.join(os.homedir(), ".mcp.json");
  const localPath = path.join(process.cwd(), ".mcp.json");

  const globalConfig = loadJsonFile(globalPath);
  const localConfig = loadJsonFile(localPath);

  const mergedEnv = mergeConfigs(globalConfig, localConfig);

  for (const key of Object.keys(mergedEnv)) {
    if (mergedEnv[key] !== undefined) {
      process.env[key] = mergedEnv[key];
    }
  }
}
