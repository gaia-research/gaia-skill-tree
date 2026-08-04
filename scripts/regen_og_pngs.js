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
const DOCS_DIR = 'docs';
const AOV_DIR = path.join(DOCS_DIR, 'assets', 'ascension-overdrive');
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

async function assetDataUri(assetPath) {
  // Re-encode WebP medallions as PNG before handing the SVG to librsvg.  This
  // avoids both local `/assets/...` resolution failures and Cairo/WebP loader
  // differences that otherwise produce a valid PNG with an empty medallion.
  const png = await sharp(assetPath).png().toBuffer();
  return `data:image/png;base64,${png.toString('base64')}`;
}

async function inlineRasterAssets(svgSource) {
  if (!fs.existsSync(AOV_DIR)) return svgSource;
  const files = fs.readdirSync(AOV_DIR)
    .filter((name) => /^aov4-.*-hero\.webp$/.test(name))
    .sort();
  let out = svgSource;
  for (const name of files) {
    const href = `/assets/ascension-overdrive/${name}`;
    if (!out.includes(href)) continue;
    const dataUri = await assetDataUri(path.join(AOV_DIR, name));
    out = out.split(href).join(dataUri);
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
      const source = await inlineRasterAssets(fs.readFileSync(svg, 'utf8'));
      await sharp(Buffer.from(source)).resize(W, H).png().toFile(png);
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
