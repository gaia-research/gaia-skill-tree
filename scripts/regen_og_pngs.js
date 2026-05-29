#!/usr/bin/env node
/**
 * Batch-convert all per-skill OG SVGs to PNG using sharp (librsvg bundled).
 * Works on Windows, macOS, Linux without any system-level Cairo install.
 *
 * Usage (from repo root):
 *   npm install --no-save sharp
 *   node scripts/regen_og_pngs.js
 */
const sharp = require('sharp');
const fs = require('fs');
const path = require('path');

const OG_DIR = 'docs/og';
const SKIP = new Set(['social-preview.svg']);
const W = 1200, H = 630;

function rglob(dir) {
  const out = [];
  for (const f of fs.readdirSync(dir, { withFileTypes: true })) {
    const full = path.join(dir, f.name);
    if (f.isDirectory()) out.push(...rglob(full));
    else if (f.name.endsWith('.svg') && !SKIP.has(f.name)) out.push(full);
  }
  return out;
}

(async () => {
  if (!fs.existsSync(OG_DIR)) {
    console.error('ERROR: docs/og/ not found. Run from repo root.');
    process.exit(1);
  }
  const svgs = rglob(OG_DIR);
  if (!svgs.length) { console.log('No SVGs found.'); return; }
  console.log(`Converting ${svgs.length} SVGs → PNGs (${W}×${H})...`);
  let ok = 0, errors = [];
  for (const svg of svgs) {
    const png = svg.replace(/\.svg$/, '.png');
    try {
      await sharp(svg).resize(W, H).png().toFile(png);
      console.log(`  PNG: ${png}`);
      ok++;
    } catch (e) {
      errors.push({ svg, msg: e.message });
      console.error(`  ERR: ${svg} — ${e.message}`);
    }
  }
  console.log(`\nGenerated ${ok}/${svgs.length} PNG(s).`);
  if (errors.length) process.exit(1);
})();
