import assert from 'node:assert/strict';
import { mkdtempSync, rmSync, writeFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { dirname, join, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import test from 'node:test';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);
const pluginRoot = resolve(__dirname, '..');
const gaiaBin = join(pluginRoot, 'dist/bin/gaia.js');
const npmCache = join(tmpdir(), 'gaia-cli-npm-cache');

function run(command, args, options = {}) {
  return spawnSync(command, args, {
    cwd: options.cwd ?? pluginRoot,
    env: { ...process.env, npm_config_cache: npmCache, ...(options.env ?? {}) },
    encoding: 'utf8',
    shell: false,
  });
}

function withTempDir(fn) {
  const dir = mkdtempSync(join(tmpdir(), 'gaia-cli-test-'));
  try {
    return fn(dir);
  } finally {
    rmSync(dir, { recursive: true, force: true });
  }
}

test('binary wrapper runs the Python CLI from outside the repo root', () => {
  withTempDir((cwd) => {
    const result = run(process.execPath, [gaiaBin, '--help'], { cwd });

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Gaia CLI/);
    assert.match(result.stdout, /\bpush\b/);
  });
});

test('programmatic wrapper runs the Python CLI from outside the repo root', () => {
  withTempDir((cwd) => {
    const scriptPath = join(cwd, 'run-gaia.mjs');
    writeFileSync(
      scriptPath,
      [
        `import { runGaiaCli } from ${JSON.stringify(join(pluginRoot, 'dist/index.js'))};`,
        "const code = await runGaiaCli(['--help']);",
        'process.exit(code);',
      ].join('\n'),
    );

    const result = run(process.execPath, [scriptPath], { cwd });

    assert.equal(result.status, 0, result.stderr);
    assert.match(result.stdout, /Gaia CLI/);
  });
});

test('package dry-run includes wrapper files but excludes Python bytecode', () => {
  const result = run('npm', ['pack', '--json', '--dry-run']);

  assert.equal(result.status, 0, result.stderr);
  const [pack] = JSON.parse(result.stdout);
  const files = pack.files.map((file) => file.path);

  assert.ok(files.includes('dist/bin/gaia.js'));
  assert.ok(files.includes('dist/index.js'));
  assert.ok(files.includes('cli/main.py'));
  assert.ok(files.includes('cli/push.py'));
  assert.ok(files.includes('gaia_registry_lib/frontmatter.py'));
  assert.ok(files.includes('gaia_registry_lib/github_api.py'));
  assert.ok(files.includes('gaia_registry_lib/named_iterator.py'));
  assert.ok(!files.some((file) => file.includes('__pycache__')));
  assert.ok(!files.some((file) => file.endsWith('.pyc')));
});

test('packed npm package installs and exposes gaia binary', () => {
  withTempDir((cwd) => {
    const packResult = run('npm', ['pack', '--silent'], { cwd: pluginRoot });
    assert.equal(packResult.status, 0, packResult.stderr);

    const tarball = packResult.stdout.trim().split(/\r?\n/).at(-1);
    assert.ok(tarball, 'npm pack should print a tarball path');
    const tarballPath = join(pluginRoot, tarball);

    try {
      const initResult = run('npm', ['init', '-y'], { cwd });
      assert.equal(initResult.status, 0, initResult.stderr);

      const installResult = run('npm', ['install', tarballPath], { cwd });
      assert.equal(installResult.status, 0, installResult.stderr);

      const helpResult = run(join(cwd, 'node_modules/.bin/gaia'), ['--help'], { cwd });
      assert.equal(helpResult.status, 0, helpResult.stderr);
      assert.match(helpResult.stdout, /Gaia CLI/);
    } finally {
      rmSync(tarballPath, { force: true });
    }
  });
});
