import { readdirSync } from 'node:fs';
import { dirname, join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';

const packageRoot = dirname(dirname(fileURLToPath(import.meta.url)));

function runShell(command) {
  const result = spawnSync(command, {
    cwd: packageRoot,
    shell: true,
    stdio: 'inherit',
  });
  return result.status ?? 1;
}

function runNode(args) {
  const result = spawnSync(process.execPath, args, {
    cwd: packageRoot,
    stdio: 'inherit',
  });
  return result.status ?? 1;
}

function collectTestFiles(dir) {
  const entries = readdirSync(dir, { withFileTypes: true });
  return entries.flatMap((entry) => {
    const fullPath = join(dir, entry.name);
    if (entry.isDirectory()) {
      return collectTestFiles(fullPath);
    }
    return entry.name.endsWith('.test.mjs') ? [fullPath] : [];
  });
}

let status = runShell('npm run build');
if (status !== 0) {
  process.exit(status);
}

status = runShell('npm run prepack');
if (status !== 0) {
  process.exit(status);
}

const testFiles = collectTestFiles(join(packageRoot, 'test'));
const testStatus = runNode(['--test', ...testFiles]);
const cleanupStatus = runShell('npm run postpack');

process.exit(testStatus !== 0 ? testStatus : cleanupStatus);
