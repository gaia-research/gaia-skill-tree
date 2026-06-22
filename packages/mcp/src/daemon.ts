import * as fs from "fs";
import * as path from "path";
import * as os from "os";
import { spawn } from "child_process";
import { fileURLToPath } from "url";

const gaiaHome = process.env.GAIA_HOME || path.join(os.homedir(), ".gaia");
const pidFile = path.join(gaiaHome, "mcp.pid");

function ensureGaiaHome(): void {
  if (!fs.existsSync(gaiaHome)) {
    fs.mkdirSync(gaiaHome, { recursive: true });
  }
}

function isProcessRunning(pid: number): boolean {
  try {
    process.kill(pid, 0);
    return true;
  } catch (error: any) {
    return error.code === "EPERM";
  }
}

function getMcpBinPath(): string {
  const currentDir = path.dirname(fileURLToPath(import.meta.url));
  return path.resolve(currentDir, "..", "bin", "gaia-mcp.js");
}

function startDaemon(): void {
  ensureGaiaHome();

  if (fs.existsSync(pidFile)) {
    const pidText = fs.readFileSync(pidFile, "utf8").trim();
    const pid = parseInt(pidText, 10);
    if (!isNaN(pid) && isProcessRunning(pid)) {
      console.log(`MCP daemon is already running (PID: ${pid}).`);
      process.exit(0);
    }
  }

  const binPath = getMcpBinPath();
  if (!fs.existsSync(binPath)) {
    console.error(`MCP server executable not found: ${binPath}`);
    console.error("Please run npm run build in packages/mcp first.");
    process.exit(1);
  }

  const logFile = path.join(gaiaHome, "mcp.log");
  const out = fs.openSync(logFile, "a");
  const err = fs.openSync(logFile, "a");

  const child = spawn(process.execPath, [binPath], {
    detached: true,
    stdio: ["ignore", out, err],
    env: { ...process.env },
  });

  const childPid = child.pid;
  if (childPid) {
    fs.writeFileSync(pidFile, String(childPid), "utf8");
    console.log(`MCP daemon started (PID: ${childPid}).`);
    child.unref();
  } else {
    console.error("Failed to retrieve PID of spawned daemon process.");
    process.exit(1);
  }
}

function stopDaemon(): void {
  if (!fs.existsSync(pidFile)) {
    console.log("MCP daemon is not running.");
    process.exit(0);
  }

  const pidText = fs.readFileSync(pidFile, "utf8").trim();
  const pid = parseInt(pidText, 10);

  if (isNaN(pid)) {
    console.log("Invalid PID file found. Cleaning up.");
    try {
      fs.unlinkSync(pidFile);
    } catch {}
    process.exit(0);
  }

  if (isProcessRunning(pid)) {
    try {
      process.kill(pid, "SIGTERM");
      console.log(`Sent SIGTERM to MCP daemon (PID: ${pid}).`);
      
      let attempts = 0;
      const interval = setInterval(() => {
        if (!isProcessRunning(pid)) {
          clearInterval(interval);
          try {
            fs.unlinkSync(pidFile);
          } catch {}
          console.log("MCP daemon stopped.");
          process.exit(0);
        }
        attempts++;
        if (attempts >= 10) {
          clearInterval(interval);
          try {
            process.kill(pid, "SIGKILL");
            console.log(`Sent SIGKILL to MCP daemon (PID: ${pid}).`);
          } catch {}
          try {
            fs.unlinkSync(pidFile);
          } catch {}
          console.log("MCP daemon stopped.");
          process.exit(0);
        }
      }, 200);
      return;
    } catch (error) {
      console.error(`Failed to stop MCP daemon: ${error}`);
      process.exit(1);
    }
  } else {
    console.log("Stale PID file found. Cleaning up.");
    try {
      fs.unlinkSync(pidFile);
    } catch {}
    process.exit(0);
  }
}

function getStatus(): void {
  if (!fs.existsSync(pidFile)) {
    console.log("MCP daemon is stopped.");
    process.exit(0);
  }

  const pidText = fs.readFileSync(pidFile, "utf8").trim();
  const pid = parseInt(pidText, 10);

  if (isNaN(pid)) {
    console.log("MCP daemon is stopped (stale PID file).");
    process.exit(0);
  }

  if (isProcessRunning(pid)) {
    console.log(`MCP daemon is running (PID: ${pid}).`);
  } else {
    console.log("MCP daemon is stopped (stale PID file).");
  }
}

function main(): void {
  const args = process.argv.slice(2);
  const command = args[0];

  if (command === "start") {
    startDaemon();
  } else if (command === "stop") {
    stopDaemon();
  } else if (command === "status") {
    getStatus();
  } else {
    console.error("Usage: node daemon.js [start|stop|status]");
    process.exit(1);
  }
}

main();
