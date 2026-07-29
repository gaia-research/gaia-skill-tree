// Tests for the vocabulary-drift gate, gaia-skill-tree HQ.
// Run: npx tsx scripts/lexicon/check-lexicon.test.ts
//
// scripts/lexicon/check-lexicon.ts is VENDORED byte-identical from
// gaia-research/gaia-research (Federation Invariant 1: no plane imports another
// plane's source — vendor small pure pieces and prove parity by fixture, D6).
// The parity block below pins the digest of the copy that was reviewed; the
// fixtures below prove the vendored copy behaves on THIS HQ's vocabulary.
//
// Fixtures live in __fixtures__/check-lexicon/ and are named by expectation:
//   good-*  → must produce ZERO findings
//   bad-*   → must produce AT LEAST ONE finding
// Every fixture declares the path it is pretending to live at on its first
// line: <!-- as: docs/agents/x.md -->. The fixture directory is excluded from
// real scans, so these files are only ever seen through this harness.
import { createHash } from "node:crypto";
import { mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";
import {
  aboveBaseline,
  findRoot,
  foreignCollisions,
  globToRegExp,
  loadHq,
  ROOT_CANDIDATES,
  scanText,
  scopesFor,
  tally,
  validateLexicon,
  type Baseline,
  type Finding,
  type Foreign,
  type Lexicon,
} from "./check-lexicon.ts";

const HERE = dirname(fileURLToPath(import.meta.url));
const FIXTURES = join(HERE, "__fixtures__", "check-lexicon");
const ROOT = join(HERE, "..", "..");
const rootPath = findRoot(ROOT)!;
const lex: Lexicon = loadHq(rootPath);
const foreign: Foreign | null = lex.foreign
  ? JSON.parse(readFileSync(join(ROOT, lex.foreign), "utf8"))
  : null;
const vendor = JSON.parse(readFileSync(join(HERE, "vendor.json"), "utf8"));

// fixture basename → substring that must appear in at least one finding message,
// so each test pins WHICH class was caught, not merely that something was.
const REASON_ASSERTS: Record<string, string> = {
  "bad-retired-product-name.md": 'use "Gaia Skill Tree"',
  "bad-legacy-taxonomy-word.md": 'use "Fusion"',
  "bad-retired-evidence-axis.md": 'use "Evidence Grade"',
  "bad-retired-rank-synonym.md": 'use "Ultimate"',
};

let pass = 0;
let fail = 0;

function check(name: string, ok: boolean, detail = "") {
  if (ok) {
    pass++;
    console.log(`  ✓ ${name}`);
  } else {
    fail++;
    console.error(`  ✗ ${name}${detail ? ` — ${detail}` : ""}`);
  }
}

console.log("vendoring parity (D6)");
const digest = createHash("sha256")
  .update(readFileSync(join(HERE, "check-lexicon.ts")))
  .digest("hex");
check(
  "the vendored gate matches the reviewed digest byte-for-byte",
  digest === vendor.sha256,
  `local ${digest.slice(0, 16)}… vs recorded ${String(vendor.sha256).slice(0, 16)}…\n` +
    `    The gate is vendored from ${vendor.source} (${vendor.path}). Do not patch it here:\n` +
    `    change it upstream, re-copy, and update scripts/lexicon/vendor.json in the same PR cycle.`,
);
check("vendor.json names its upstream", !!vendor.source && !!vendor.path);

console.log("\nlexicon schema");
const schemaErrors = validateLexicon(lex, undefined, foreign);
check("the merged lexicon is well-formed", schemaErrors.length === 0, schemaErrors.join("; "));
check(
  "every banned term cites the oracle that retired it and names a replacement",
  lex.terms.filter((t) => t.state === "banned").every((t) => !!t.oracle && !!t.replacement),
);
check(
  "no term is both parked and given a hard replacement",
  lex.terms.every((t) => !(t.state === "parked" && t.replacement)),
);

console.log("\nnamespaces (V5-8 federation)");
const OWNED = ["gaia.skills", "gaia.trust"];
check(
  "this HQ owns exactly gaia.skills and gaia.trust",
  JSON.stringify([...(lex.owns ?? [])].sort()) === JSON.stringify([...OWNED].sort()),
  JSON.stringify(lex.owns),
);
check(
  "gaia.registry is rejected — the namespace is gaia.skills (#1258)",
  !(lex.owns ?? []).includes("gaia.registry"),
);
check(
  "both owned namespaces actually have terms (KC5)",
  OWNED.every((ns) => lex.terms.some((t) => lex.owners?.[t.term.toLowerCase()]?.namespace === ns)),
);
check(
  "every term resolves to exactly one owning file (KC1)",
  lex.terms.every((t) => !!lex.owners?.[t.term.toLowerCase()]?.file) &&
    Object.keys(lex.owners ?? {}).length === lex.terms.length,
);
check(
  "gaia.trust is a peer under core, not a child of gaia.skills",
  JSON.parse(readFileSync(join(HERE, "lexicon.gaia.trust.json"), "utf8")).extends === "core",
);

console.log("\nfederation — the other HQ's terms are theirs (KC2)");
check(
  "the foreign mirror covers all five namespaces the other HQ owns",
  !!foreign &&
    ["core", "gaia.research", "gaia.brand", "gaia.heaven", "gaia.mcp"].every((ns) =>
      Object.values(foreign.terms).includes(ns),
    ),
);
check(
  "the foreign mirror carries names only — never definitions",
  !!foreign && Object.values(foreign.terms).every((v) => typeof v === "string"),
);
check(
  "this HQ defines none of the other HQ's terms",
  foreignCollisions(lex, foreign).length === 0,
  foreignCollisions(lex, foreign).join("; "),
);
check(
  "redefining a foreign term IS an error",
  foreignCollisions(
    { ...lex, terms: [{ term: "floor", state: "canonical", definition: "d" }] },
    foreign,
  ).some((e) => e.includes("gaia.heaven")),
);
check(
  "the three published MCP tool names stay owned by gaia.mcp upstream",
  !!foreign &&
    ["gaia_search", "gaia_inspect", "gaia_status"].every((t) => foreign.terms[t] === "gaia.mcp") &&
    !lex.terms.some((t) => t.term.startsWith("gaia_")),
);

console.log("\nmerge rules");
const TMP = mkdtempSync(join(tmpdir(), "lexicon-hq-"));
const writeHq = (root: object, files: Record<string, object>) => {
  writeFileSync(join(TMP, "lexicon.json"), JSON.stringify(root));
  for (const [ns, body] of Object.entries(files))
    writeFileSync(join(TMP, `lexicon.${ns}.json`), JSON.stringify(body));
  return join(TMP, "lexicon.json");
};
const baseRoot = {
  lexicon: "2",
  hq: "t",
  namespace: "gaia.skills",
  extends: "core",
  owns: ["gaia.skills", "gaia.trust"],
  updated: "2026-07-28",
  scopes: {},
  exclude: [],
  terms: [{ term: "alpha", state: "canonical", definition: "d" }],
};
const nsFile = (ns: string, terms: object[]) => ({
  lexicon: "2",
  namespace: ns,
  extends: "core",
  terms,
});
const throws = (fn: () => unknown, needle: string) => {
  try {
    fn();
    return false;
  } catch (e) {
    return (e as Error).message.includes(needle);
  }
};

check(
  "a namespace declared in `owns` with no file is a hard failure",
  throws(() => loadHq(writeHq(baseRoot, {})), 'declared in "owns"'),
);
check(
  "a term defined in two files fails, naming both",
  throws(
    () =>
      loadHq(
        writeHq(baseRoot, {
          "gaia.trust": nsFile("gaia.trust", [
            { term: "alpha", state: "canonical", definition: "d" },
          ]),
        }),
      ),
    "is defined twice",
  ),
);
check(
  "a namespace file whose declared namespace disagrees with its filename fails",
  throws(
    () =>
      loadHq(
        writeHq(baseRoot, {
          "gaia.trust": nsFile("gaia.skills", [
            { term: "beta", state: "canonical", definition: "d" },
          ]),
        }),
      ),
    "is loaded as",
  ),
);
check(
  "a clean two-file HQ merges into one flat term list",
  (() => {
    const m = loadHq(
      writeHq(baseRoot, {
        "gaia.trust": nsFile("gaia.trust", [{ term: "beta", state: "canonical", definition: "d" }]),
      }),
    );
    return (
      m.terms.length === 2 &&
      m.owners?.["alpha"].namespace === "gaia.skills" &&
      m.owners?.["beta"].namespace === "gaia.trust"
    );
  })(),
);
check(
  "scripts/lexicon/lexicon.json is a recognised root location",
  ROOT_CANDIDATES.includes("scripts/lexicon/lexicon.json"),
);
rmSync(TMP, { recursive: true, force: true });

console.log("\nglob matching");
check("**/*.md matches a root-level file", globToRegExp("**/*.md").test("README.md"));
check("**/*.md matches a nested file", globToRegExp("**/*.md").test("docs/agents/a.md"));
check("founder/**/*.md does not match docs/", !globToRegExp("founder/**/*.md").test("docs/a.md"));
check("brace alternation works", globToRegExp("packages/**/*.{ts,tsx}").test("packages/mcp/src/a.ts"));

console.log("\nscope resolution");
check("README.md is user-facing", scopesFor("README.md", lex).includes("user-facing"));
check("docs/agents is decisive", scopesFor("docs/agents/domain.md", lex).includes("decisive"));
check(
  "founder/ is in no scope — the founder workspace has free reign over vocabulary",
  (() => {
    // Founder docs are working notes, decision logs, and audit trails. They must
    // be able to QUOTE a retired term in order to record the violation it names,
    // and they routinely reason about vocabulary that has not been chosen yet.
    // Gating them made every snapshot a vocabulary negotiation. Founder ruling,
    // 2026-07-29. Shipped copy is still gated — that is where drift costs.
    const files = [
      "founder/MEMORY.md",
      "founder/GAIA_ROADMAP v5 (BUILD).md",
      "founder/handovers/ARC_I.md",
      "founder/reports/design-review-2026-07-20/scout-d-outer.md",
    ];
    return files.every((f) => scopesFor(f, lex).length === 0);
  })(),
);
check(
  "registry data is in no scope — a curated skill description is not this gate's business",
  scopesFor("registry/named/someone/thing.md", lex).length === 0,
);

console.log("\nbaseline");
const f = (file: string, term: string, line: number): Finding => ({
  file,
  term,
  line,
  state: "banned",
  message: "x",
});
const base: Baseline = { findings: { "README.md": { "Gaia Registry": 2 } } };
check(
  "a baselined finding is carried, not reported",
  aboveBaseline([f("README.md", "Gaia Registry", 9)], base).length === 0,
);
check(
  "an extra occurrence beyond the baselined count IS reported",
  aboveBaseline(
    [
      f("README.md", "Gaia Registry", 9),
      f("README.md", "Gaia Registry", 41),
      f("README.md", "Gaia Registry", 77),
    ],
    base,
  ).length === 1,
);
check(
  "a new term in a baselined file IS reported",
  aboveBaseline([f("README.md", "Evidence Class", 90)], base).length === 1,
);
check("no baseline means everything is reported", aboveBaseline([f("a.md", "x", 1)], null).length === 1);
check(
  "tally counts per file and term",
  (() => {
    const t = tally([f("a.md", "x", 1), f("a.md", "x", 2), f("a.md", "y", 3)]);
    return t["a.md"].x === 2 && t["a.md"].y === 1;
  })(),
);

console.log("\nfixtures");
for (const name of readdirSync(FIXTURES).filter((x) => x.endsWith(".md")).sort()) {
  const text = readFileSync(join(FIXTURES, name), "utf8");
  const asPath = text.match(/<!--\s*as:\s*(\S+)\s*-->/)?.[1];
  if (!asPath) {
    check(name, false, "fixture is missing its `<!-- as: path -->` header");
    continue;
  }
  // Strip the header so its own path text cannot trip a term match.
  const body = text.replace(/<!--\s*as:.*?-->/, "");
  const findings = scanText(body, asPath, lex);
  const expectBad = name.startsWith("bad-");
  const gotBad = findings.length > 0;

  let ok = expectBad === gotBad;
  let detail = ok ? "" : `expected ${expectBad ? "≥1" : "0"} findings, got ${findings.length}`;
  if (!ok && findings.length) detail += `: ${findings.map((x) => x.term).join(", ")}`;

  const want = REASON_ASSERTS[name];
  if (ok && want && !findings.some((x) => x.message.includes(want))) {
    ok = false;
    detail = `caught something, but not "${want}" (got: ${findings.map((x) => x.message).join(" | ")})`;
  }
  check(name, ok, detail);
}

console.log(`\n${pass} passed, ${fail} failed`);
process.exit(fail === 0 ? 0 : 1);
