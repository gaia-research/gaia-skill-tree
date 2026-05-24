import { spawn } from "node:child_process";
import { resolveRegistryPath } from "../config/identity.js";

/**
 * Standardized way to invoke the Gaia Python CLI from the MCP server.
 * Honours local registry context by passing GAIA_REGISTRY_PATH.
 */
export async function runGaia(args: string[]): Promise<string> {
  const registryPath = resolveRegistryPath();
  const env = {
    ...process.env,
    // Ensure the subprocess uses the same registry context
    ...(registryPath ? { GAIA_REGISTRY_PATH: registryPath } : {}),
    // Force no-color for machine consumption
    NO_COLOR: "1",
    TERM: "dumb",
  };

  return new Promise((resolve, reject) => {
    // We use shell: true to handle environment path resolution better across platforms
    const proc = spawn("gaia", args, {
      env,
      shell: true,
    });

    let stdout = "";
    let stderr = "";

    proc.stdout.on("data", (data) => {
      stdout += data.toString();
    });

    proc.stderr.on("data", (data) => {
      stderr += data.toString();
    });

    proc.on("close", (code) => {
      if (code === 0) {
        resolve(stdout.trim());
      } else {
        const errorMsg = stderr.trim() || stdout.trim() || `Exit code ${code}`;
        reject(new Error(`gaia ${args.join(" ")} failed: ${errorMsg}`));
      }
    });

    proc.on("error", (err) => {
      reject(new Error(`Failed to start gaia CLI: ${err.message}. Ensure gaia is installed and in your PATH.`));
    });
  });
}
