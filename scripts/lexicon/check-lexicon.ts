// Vocabulary-drift gate for the Skill Heaven / Skill Hell line.
//
// WHY THIS EXISTS. The PR #4 review found the shipped posture set diverging
// from the ratified one ("add-ons" duplicating "curated" under a new label,
// "lean" with no P1 authorisation) and named the cause: "oracle governance
// lacks vocabulary-drift detection." It was right. Measured at the time this
// gate was written, `posture` appeared in 14 docs and `slider` in 11, and the
// oracle's supersession log (549 words) had grown 2.9x longer than the section
// defining what the postures actually are (191 words). Drift was being caught
// by human review, inconsistently, one doc at a time. This makes it a build
// failure instead.
//
// FEDERATED LAYOUT (v5 Program 2, ratified V5-8). The lexicon is no longer one
// flat `core` file. It is a root manifest plus one file per owned namespace,
// split across two HQs:
//
//   gaia-research     core · gaia.research · gaia.brand · gaia.heaven · gaia.mcp
//   gaia-skill-tree   gaia.skills · gaia.trust
//
// `skill-heaven` and `gaia-mcp` own NO namespace — they consume. `gaia.registry`
// is rejected; the namespace is `gaia.skills`.
//
// The root manifest (`founder/lexicon.json`, or `scripts/lexicon/lexicon.json`
// where branch scope demands it) holds the repo-wide config — scopes, exclusions,
// the oracle path, the generated-doc path — and its own namespace's terms. Every
// other owned namespace is a sibling `lexicon.<namespace>.json` holding terms and
// nothing else. `loadHq` merges them into one flat term list and records which
// file owned each term.
//
// ONE TERM, ONE OWNER. A term is defined in exactly one file, ever. Inside an HQ
// the merge rejects a second definition and names both files. Across HQs the
// name-only mirror (`lexicon.foreign.json`) does the same without importing the
// other repo's source — definitions never travel, only names.
//
// This script is vendored byte-identical into the second HQ. Everything
// repo-specific is read from the manifest; if you find yourself adding a path
// literal here, put it on the manifest instead.
//
// WHAT IT CHECKS, over the merged lexicon:
//   1. The lexicon is internally well-formed — no duplicate terms, every
//      `banned` term carries a `replacement`, every state is one of the four.
//   2. No `banned` term appears in any scanned file. Banned means the oracle
//      already retired it (N3's Heaven-0/Heaven-1, N9's hh-launcher, B3's seed).
//   3. No `parked` term appears in user-facing copy or shipped code. Parked
//      means coined-but-unchosen; it is legal in docs/ because you must be able
//      to think in unsettled words, and illegal in front of a reader because
//      shipping one is how it becomes permanent by accident.
//   4. founder/LEXICON.md is in sync with the JSON (it is generated, not
//      hand-written). --emit regenerates it.
//
// WHAT IT DELIBERATELY DOES NOT DO. It does not ban a term this project is
// still arguing about. `lean`, `slider`, `notch` and `budget` are all `parked`,
// not `banned`, because banning them here would settle a live question by
// writing a linter — which is the same failure mode as deciding something in a
// plan doc. Only founder/RATIFICATION.md retires a word; this gate enforces
// what the oracle already ruled.
//
// SCOPES. A term may carry `"scope": ["user-facing"]` to narrow where it is
// enforced. Two terms need this: `lean` (111 files, nearly all `clean` /
// `lean bundle`) and `tier` (42 files, mostly the ratified `auth@tier` stamp
// sense). A blanket rule on those two would cry wolf on day one and get the
// gate switched off by week two, so they are checked only where the word is
// load-bearing.
//
// ESCAPE HATCH. A line carrying `<!-- lexicon-allow -->` is skipped. This is
// required, not a loophole: the oracle's supersession log has to be able to say
// "hh-launcher is retired" without failing the gate that retired it.
//
// KNOWN LIMITATIONS (the gate's edges, stated rather than silently left):
//   * Word-boundary regex over raw text. It does not parse markdown, so a
//     banned term inside a fenced code block is still flagged — intentional
//     (a retired name in a copy-pasteable command is exactly the drift to
//     catch), but it means legitimate historical commands need the marker.
//   * Case-insensitive. `Milim` and `milim` are one term.
//   * Multi-word terms match across single spaces only; a term broken across a
//     line wrap is not caught.
//   * Scope membership is by path glob, so a doc moved between directories
//     silently changes which rules apply to it.
//   * It checks vocabulary, never semantics. A doc can use every word correctly
//     and still describe the product wrongly.
//
// THE BASELINE. Introducing this gate against existing docs produced 39
// findings, every one of them in a doc already queued for rewrite. Two bad
// options: land it non-blocking (it gets ignored by week two) or block every PR
// until the rewrites finish (it gets deleted by week one). So baseline.json
// records the known debt as {file: {term: count}}, and the gate fails only on
// findings ABOVE the baseline — new drift is blocked from day one while the
// backlog burns down. Counts, not line numbers, so ordinary edits don't churn
// it. The outstanding total is printed on every success so it stays visible
// instead of becoming furniture.
//
// CLI:
//   npx tsx scripts/lexicon/check-lexicon.ts            # check (exit 1 on NEW drift)
//   npx tsx scripts/lexicon/check-lexicon.ts --emit     # regenerate LEXICON.md
//   npx tsx scripts/lexicon/check-lexicon.ts --strict   # ignore the baseline
//   npx tsx scripts/lexicon/check-lexicon.ts --update-baseline
//   npx tsx scripts/lexicon/check-lexicon.ts --file a.md --file b.md
import { readFileSync, writeFileSync, readdirSync, statSync, existsSync } from "node:fs";
import { dirname, join, relative, resolve, sep } from "node:path";
import { fileURLToPath } from "node:url";

const HERE = dirname(fileURLToPath(import.meta.url));
const ROOT = resolve(HERE, "..", "..");

const STATES = ["canonical", "banned", "parked", "frozen"] as const;
type State = (typeof STATES)[number];

export type Term = {
  term: string;
  state: State;
  group?: string;
  oracle?: string;
  definition: string;
  replacement?: string;
  proposed_replacement?: string;
  note?: string;
  scope?: string[];
  /** "exact-case" for ALL-CAPS labels whose lowercase form is ordinary English. */
  match?: "exact-case";
  /**
   * Regexes that exempt a match. A one-word ban is too blunt when the word has
   * more than one sense: `seed` is retired in the determinism sense (B3) but a
   * "seed set" of skills to hand-label is a different thing entirely. Without
   * this the gate flags the wrong sense and gets silenced with markers, which
   * is how a linter dies.
   */
  except?: string[];
};

/**
 * A namespace file: `founder/lexicon.<namespace>.json`. It carries terms and
 * nothing else — scopes, exclusions and paths are repo-wide and live on the
 * root manifest, so a namespace can never quietly widen where it is enforced.
 */
export type NamespaceFile = {
  lexicon: string;
  namespace: string;
  extends: string | null;
  updated?: string;
  about?: string;
  terms: Term[];
};

/**
 * Name-only mirror of the terms the OTHER HQ owns. Definitions are deliberately
 * absent: one term, one owner, one definition, one file. This exists so the gate
 * can reject a redefinition of a foreign term without importing another repo's
 * source (Federation Invariant 1 — vendor small pure pieces, never import).
 */
export type Foreign = {
  contract: string;
  source: string;
  updated?: string;
  about?: string;
  /** term → owning namespace */
  terms: Record<string, string>;
};

/**
 * The merged, in-memory view an HQ's gate runs against: the root manifest's
 * config plus every owned namespace's terms flattened into one list.
 * `owners` records which file defined each term, so a collision can name both.
 */
export type Lexicon = {
  lexicon: string;
  /** The HQ repo that owns this lexicon, e.g. "gaia-research". */
  hq?: string;
  /** The root file's own namespace. */
  namespace: string;
  extends: string | null;
  /** Every namespace this HQ owns. Each needs a file; an unrealised one fails. */
  owns?: string[];
  updated: string;
  about?: string;
  /** Repo-relative path of the generated markdown. Config, not convention. */
  generated_doc?: string;
  /** Repo-relative path of the ratification log, or null when the HQ has none. */
  oracle?: string | null;
  /** Repo-relative path of the foreign name-only mirror, or null. */
  foreign?: string | null;
  scopes: Record<string, { about?: string; include: string[] }>;
  exclude: string[];
  terms: Term[];
  /** term (lowercased) → {namespace, file}. Populated by loadHq. */
  owners?: Record<string, { namespace: string; file: string }>;
};

export type Finding = {
  file: string;
  line: number;
  term: string;
  state: State;
  message: string;
};

/**
 * Where a root manifest may live, in order. Two entries, because the two HQs
 * have different branch-scope rules: `gaia-research` keeps its lexicon under
 * `founder/`, while `gaia-skill-tree`'s CI only lets an `infra/*` branch touch
 * `.github/`, `scripts/`, `*.md` and `docs/*.html` — so its JSON lives under
 * `scripts/lexicon/`. Everything else the gate needs is read from the manifest,
 * which is what lets the SCRIPT ITSELF stay byte-identical in both repos. That
 * is the vendoring contract: copy this file, change nothing, prove it by fixture.
 */
export const ROOT_CANDIDATES = ["founder/lexicon.json", "scripts/lexicon/lexicon.json"];

export function findRoot(root = ROOT): string | null {
  for (const c of ROOT_CANDIDATES) if (existsSync(join(root, c))) return join(root, c);
  return null;
}

/**
 * Load one HQ's lexicon: the root manifest plus every `owns` namespace's file.
 *
 * THE MERGE RULE, in full:
 *   1. The root manifest is the only source of scopes, exclusions and paths.
 *      A namespace file that tried to carry them would be widening its own
 *      enforcement, so they are ignored — and `owns` is the only list that
 *      decides which files are loaded at all.
 *   2. The root's own namespace lives in the root file; every OTHER owned
 *      namespace must have a sibling `lexicon.<namespace>.json` next to it.
 *      A namespace in `owns` with no file is a hard failure — that is how
 *      "the six namespaces exist" stays a checked fact rather than a claim.
 *   3. Terms are a flat union. Ownership is recorded per term, so redefinition
 *      fails with BOTH file names rather than a bare "duplicate".
 *
 * Extension, never redefinition: a namespace file may ADD terms and may cite a
 * term another namespace owns, but it may never define one twice.
 */
export function loadHq(rootPath: string): Lexicon {
  const dir = dirname(rootPath);
  const root = JSON.parse(readFileSync(rootPath, "utf8")) as Lexicon;
  const owners: Record<string, { namespace: string; file: string }> = {};
  const terms: Term[] = [];
  const errors: string[] = [];

  const take = (ns: string, file: string, list: Term[]) => {
    for (const t of list ?? []) {
      const key = t.term.toLowerCase();
      const prior = owners[key];
      if (prior) {
        errors.push(
          `"${t.term}" is defined twice: ${prior.file} (${prior.namespace}) and ${file} (${ns}). ` +
            `One term, one owner — extend, never redefine.`,
        );
        continue;
      }
      owners[key] = { namespace: ns, file };
      terms.push(t);
    }
  };

  take(root.namespace, relative(ROOT, rootPath).split(sep).join("/"), root.terms);

  for (const ns of root.owns ?? []) {
    if (ns === root.namespace) continue;
    const abs = join(dir, `lexicon.${ns}.json`);
    const rel = relative(ROOT, abs).split(sep).join("/");
    if (!existsSync(abs)) {
      errors.push(`namespace "${ns}" is declared in "owns" but ${rel} does not exist`);
      continue;
    }
    const f = JSON.parse(readFileSync(abs, "utf8")) as NamespaceFile;
    if (f.namespace !== ns)
      errors.push(`${rel} declares namespace "${f.namespace}" but is loaded as "${ns}"`);
    // A namespace file inherits from the HQ's inheritance root: either the root
    // file's own namespace, or whatever the root itself extends. The second form
    // is what lets the gaia-skill-tree HQ — whose root namespace is `gaia.skills`
    // and which extends the upstream `core` — hold `gaia.trust` as a peer rather
    // than pretending trust vocabulary descends from skills vocabulary.
    const inherits = [root.namespace, root.extends].filter(Boolean) as string[];
    if (!inherits.includes(f.extends ?? ""))
      errors.push(`${rel} must declare extends ${inherits.map((i) => `"${i}"`).join(" or ")}, not "${f.extends}"`);
    if (f.lexicon !== root.lexicon)
      errors.push(`${rel} is schema "${f.lexicon}", root is "${root.lexicon}"`);
    take(ns, rel, f.terms);
  }

  if (errors.length) {
    const e = new Error(`lexicon merge failed:\n    ${errors.join("\n    ")}`);
    (e as Error & { errors: string[] }).errors = errors;
    throw e;
  }
  return { ...root, terms, owners };
}

/**
 * Terms this HQ defines that another HQ already owns. Cross-HQ redefinition is
 * the failure the foreign mirror exists to catch: within one repo the merge
 * catches it, across repos nothing would.
 */
export function foreignCollisions(lex: Lexicon, foreign: Foreign | null): string[] {
  if (!foreign) return [];
  const owned = new Map(Object.entries(foreign.terms).map(([t, ns]) => [t.toLowerCase(), ns]));
  return lex.terms
    .filter((t) => owned.has(t.term.toLowerCase()))
    .map(
      (t) =>
        `"${t.term}" is owned by ${owned.get(t.term.toLowerCase())} in ${foreign.source} — ` +
        `extend it there, never redefine it here`,
    );
}

/** Convert a glob to a RegExp. Supports **, *, ? and {a,b} alternation. */
export function globToRegExp(glob: string): RegExp {
  let out = "";
  for (let i = 0; i < glob.length; i++) {
    const c = glob[i];
    if (c === "*") {
      if (glob[i + 1] === "*") {
        // `**/` consumes the slash so `**/*.md` also matches a root-level file.
        if (glob[i + 2] === "/") {
          out += "(?:.*/)?";
          i += 2;
        } else {
          out += ".*";
          i += 1;
        }
      } else {
        out += "[^/]*";
      }
    } else if (c === "?") {
      out += "[^/]";
    } else if (c === "{") {
      const close = glob.indexOf("}", i);
      if (close === -1) {
        out += "\\{";
      } else {
        const alts = glob.slice(i + 1, close).split(",");
        out += `(?:${alts.map((a) => a.replace(/[.+^${}()|[\]\\]/g, "\\$&")).join("|")})`;
        i = close;
      }
    } else if (".+^$()|[]\\".includes(c)) {
      out += `\\${c}`;
    } else {
      out += c;
    }
  }
  return new RegExp(`^${out}$`);
}

export function matchesAny(path: string, globs: string[]): boolean {
  return globs.some((g) => globToRegExp(g).test(path));
}

/** Decision ids the oracle actually defines, e.g. {"D12","P1",…}. */
export function oracleEntryIds(oracleText: string): Set<string> {
  return new Set([...oracleText.matchAll(/^\|\s*([A-Z]\d+)\s*\|/gm)].map((m) => m[1]));
}

/**
 * Validate the lexicon's own shape. A malformed lexicon is a hard failure.
 *
 * When `oracleIds` is supplied, every `oracle` citation must resolve to a real
 * entry. A term citing an entry that no longer exists is worse than an
 * uncited one: it carries borrowed authority from something deleted.
 */
export function validateLexicon(
  lex: Lexicon,
  oracleIds?: Set<string>,
  foreign?: Foreign | null,
): string[] {
  const errors: string[] = [];
  if (lex.lexicon !== "2") errors.push(`unknown lexicon schema version: ${lex.lexicon}`);
  errors.push(...foreignCollisions(lex, foreign ?? null));
  for (const t of lex.terms) {
    const ns = lex.owners?.[t.term.toLowerCase()]?.namespace;
    if (ns && lex.owns && !lex.owns.includes(ns))
      errors.push(`${t.term}: owned by "${ns}", which this HQ does not declare in "owns"`);
  }

  const seen = new Map<string, number>();
  for (const t of lex.terms) {
    const key = t.term.toLowerCase();
    seen.set(key, (seen.get(key) ?? 0) + 1);
    if (!STATES.includes(t.state)) errors.push(`${t.term}: invalid state "${t.state}"`);
    if (t.state === "banned" && !t.replacement)
      errors.push(`${t.term}: state "banned" requires a "replacement"`);
    if (t.state === "banned" && !t.oracle)
      errors.push(
        `${t.term}: state "banned" requires an "oracle" citation — only RATIFICATION.md retires a word`,
      );
    if (!t.definition?.trim()) errors.push(`${t.term}: missing definition`);
    for (const s of t.scope ?? [])
      if (!lex.scopes[s]) errors.push(`${t.term}: unknown scope "${s}"`);
    for (const p of t.except ?? [])
      try { new RegExp(p); } catch { errors.push(`${t.term}: invalid except pattern "${p}"`); }
    if (oracleIds && t.oracle) {
      for (const id of t.oracle.match(/[A-Z]\d+/g) ?? [])
        if (!oracleIds.has(id))
          errors.push(`${t.term}: cites oracle entry "${id}", which RATIFICATION.md does not define`);
    }
  }
  for (const [term, n] of seen) if (n > 1) errors.push(`duplicate term: "${term}" (${n}x)`);
  return errors;
}

/** Which scopes a repo-relative path belongs to. */
export function scopesFor(path: string, lex: Lexicon): string[] {
  return Object.entries(lex.scopes)
    .filter(([, def]) => matchesAny(path, def.include))
    .map(([name]) => name);
}

function termPattern(t: Term): RegExp {
  const escaped = t.term.replace(/[.*+?^${}()|[\]\\]/g, "\\$&").replace(/ /g, "\\s+");
  // \b fails against a leading/trailing non-word char (e.g. "-only"), so anchor
  // on "not a word character" instead, which behaves for hyphenated terms.
  // Status labels (CURRENT, INVARIANT) match case-sensitively — their lowercase
  // forms are ordinary English and matched 188 innocent lines when they didn't.
  return new RegExp(`(?<![\\w-])${escaped}(?![\\w-])`, t.match === "exact-case" ? "g" : "gi");
}

export function scanText(text: string, path: string, lex: Lexicon): Finding[] {
  const findings: Finding[] = [];
  const inScopes = scopesFor(path, lex);
  const lines = text.split(/\r?\n/);

  for (const t of lex.terms) {
    if (t.state !== "banned" && t.state !== "parked") continue;

    // A term with an explicit scope list is only enforced inside those scopes.
    if (t.scope && !t.scope.some((s) => inScopes.includes(s))) continue;

    // Parked vocabulary is legal in docs and illegal in front of a reader.
    if (t.state === "parked") {
      const exposed = inScopes.includes("user-facing") || inScopes.includes("code");
      if (!exposed) continue;
    }

    const re = termPattern(t);
    lines.forEach((line, i) => {
      // Same-line marker, or the preceding line (the eslint-disable-next-line
      // convention). The preceding-line form exists because a JSX opening tag
      // cannot host a `{/* */}` comment among its attributes, and the homepage's
      // `<section id="skill-heaven-hell">` is exactly that case.
      if (line.includes("lexicon-allow")) return;
      if (i > 0 && lines[i - 1].includes("lexicon-allow")) return;
      re.lastIndex = 0;
      if (!re.test(line)) return;
      if (t.except?.some((p) => new RegExp(p, "i").test(line))) return;
      findings.push({
        file: path,
        line: i + 1,
        term: t.term,
        state: t.state,
        message:
          t.state === "banned"
            ? `retired by ${t.oracle} — use "${t.replacement}"`
            : `parked vocabulary in ${inScopes.includes("code") ? "shipped code" : "user-facing copy"} — unchosen, must not ship`,
      });
    });
  }
  return findings.sort((a, b) => a.line - b.line);
}

function walk(dir: string, lex: Lexicon, acc: string[] = []): string[] {
  for (const entry of readdirSync(dir)) {
    const abs = join(dir, entry);
    const rel = relative(ROOT, abs).split(sep).join("/");
    if (matchesAny(rel, lex.exclude) || matchesAny(`${rel}/`, lex.exclude)) continue;
    if (entry.startsWith(".") && entry !== ".github") continue;
    const st = statSync(abs);
    if (st.isDirectory()) walk(abs, lex, acc);
    else if (/\.(md|mdx|ts|tsx)$/.test(entry)) acc.push(rel);
  }
  return acc;
}

/** Files in scope: anything a scope's globs claim, minus the exclusions. */
export function filesInScope(lex: Lexicon): string[] {
  const all = walk(ROOT, lex);
  const anyScope = Object.values(lex.scopes).flatMap((s) => s.include);
  return all.filter((f) => matchesAny(f, anyScope)).sort();
}

export type Baseline = { about?: string; generated?: string; findings: Record<string, Record<string, number>> };

export function tally(findings: Finding[]): Record<string, Record<string, number>> {
  const out: Record<string, Record<string, number>> = {};
  for (const f of findings) {
    out[f.file] ??= {};
    out[f.file][f.term] = (out[f.file][f.term] ?? 0) + 1;
  }
  return out;
}

/**
 * Findings above the baseline. A (file, term) pair absent from the baseline is
 * new; a pair present but with more occurrences than recorded is new drift too.
 * Excess is attributed to the last occurrences in the file so the reported line
 * numbers point at something real.
 */
export function aboveBaseline(findings: Finding[], base: Baseline | null): Finding[] {
  if (!base) return findings;
  const budget = new Map<string, number>();
  for (const [file, terms] of Object.entries(base.findings))
    for (const [term, n] of Object.entries(terms)) budget.set(`${file} ${term}`, n);

  const out: Finding[] = [];
  for (const f of findings) {
    const key = `${f.file} ${f.term}`;
    const left = budget.get(key) ?? 0;
    if (left > 0) budget.set(key, left - 1);
    else out.push(f);
  }
  return out;
}

export function renderMarkdown(lex: Lexicon, foreign?: Foreign | null): string {
  const nsOf = (t: Term) => lex.owners?.[t.term.toLowerCase()]?.namespace ?? lex.namespace;
  const namespaces = lex.owns?.length ? lex.owns : [lex.namespace];
  const badge: Record<State, string> = {
    canonical: "✅ canonical",
    banned: "⛔ banned",
    parked: "🅿️ parked",
    frozen: "🧊 frozen",
  };
  const out: string[] = [
    "# LEXICON — vocabulary of record",
    "",
    "<!-- GENERATED FROM founder/lexicon.json — DO NOT EDIT BY HAND. -->",
    "<!-- Regenerate: npx tsx scripts/lexicon/check-lexicon.ts --emit -->",
    "<!-- lexicon-allow -->",
    "",
    `> Schema \`${lex.lexicon}\` · HQ \`${lex.hq ?? "—"}\` · ${lex.terms.length} terms across ${namespaces.length} namespace(s) · updated **${lex.updated}**.`,
    ">",
    "> **One term, one owner.** A term is defined in **exactly one** file, ever. A",
    "> namespace file **adds** terms in its own namespace and may never redefine a",
    "> term another namespace owns — inside this HQ the merge rejects it, across HQs",
    "> the name-only foreign mirror does.",
    "",
    "| Namespace | Owned by | File | Terms |",
    "|---|---|---|---|",
    ...namespaces.map((ns) => {
      const n = lex.terms.filter((t) => nsOf(t) === ns).length;
      const file =
        lex.owners?.[lex.terms.find((t) => nsOf(t) === ns)?.term.toLowerCase() ?? ""]?.file ?? "—";
      return `| \`${ns}\` | \`${lex.hq ?? "—"}\` | \`${file}\` | ${n} |`;
    }),
    "",
    ...(foreign
      ? [
          `Terms owned by **${foreign.source}** are listed name-only in \`${lex.foreign}\` and are`,
          "defined there, never here:",
          "",
          ...Object.entries(foreign.terms)
            .sort(([a], [b]) => a.localeCompare(b))
            .map(([t, ns]) => `- \`${t}\` → \`${ns}\``),
          "",
        ]
      : []),
    "| State | Meaning | Where allowed |",
    "|---|---|---|",
    "| ✅ `canonical` | The word. Use this. | everywhere |",
    "| ⛔ `banned` | The oracle retired it. CI fails. | nowhere (except `**/archived/**`) |",
    "| 🅿️ `parked` | Coined but unchosen. | `docs/` only — never user-facing copy or code |",
    "| 🧊 `frozen` | Meant something specific once. | `**/archived/**` only |",
    "",
    "**A term is `banned` only when `RATIFICATION.md` already retired it.** A term",
    "this project is still arguing about is `parked`. Writing a linter is not a way",
    "to make a decision.",
    "",
  ];

  for (const ns of namespaces) {
    const inNs = lex.terms.filter((t) => nsOf(t) === ns);
    if (!inNs.length) continue;
    out.push(`## \`${ns}\``, "");
    for (const g of [...new Set(inNs.map((t) => t.group ?? "other"))]) {
    out.push(`### ${g}`, "");
    out.push("| Term | State | Oracle | Definition |", "|---|---|---|---|");
    for (const t of inNs.filter((x) => (x.group ?? "other") === g)) {
      const extra = [
        t.replacement ? `**Use \`${t.replacement}\`.**` : "",
        t.proposed_replacement ? `Proposed: \`${t.proposed_replacement}\` (unratified).` : "",
        t.note ? t.note : "",
      ]
        .filter(Boolean)
        .join(" ");
      // Escape backslashes BEFORE pipes, or a definition containing `\|`
      // would round-trip into an unescaped cell break. Order is load-bearing;
      // CodeQL flags the pipe-only form as incomplete sanitisation, correctly.
      const def = `${t.definition}${extra ? ` ${extra}` : ""}`
        .replace(/\\/g, "\\\\")
        .replace(/\|/g, "\\|");
      out.push(`| \`${t.term}\` | ${badge[t.state]} | ${t.oracle ?? "—"} | ${def} |`);
    }
    out.push("");
    }
  }
  return out.join("\n");
}

function main(argv: string[]): number {
  const lexPath = findRoot();
  if (!lexPath) {
    console.error(`✗ no lexicon root found (looked for ${ROOT_CANDIDATES.join(", ")})`);
    return 1;
  }
  const rootRel = relative(ROOT, lexPath).split(sep).join("/");

  let lex: Lexicon;
  try {
    lex = loadHq(lexPath);
  } catch (e) {
    console.error(`✗ ${(e as Error).message}`);
    return 1;
  }

  const oraclePath = lex.oracle ? join(ROOT, lex.oracle) : null;
  const oracleIds =
    oraclePath && existsSync(oraclePath)
      ? oracleEntryIds(readFileSync(oraclePath, "utf8"))
      : undefined;
  const foreignPath = lex.foreign ? join(ROOT, lex.foreign) : null;
  const foreign: Foreign | null =
    foreignPath && existsSync(foreignPath)
      ? (JSON.parse(readFileSync(foreignPath, "utf8")) as Foreign)
      : null;

  const schemaErrors = validateLexicon(lex, oracleIds, foreign);
  if (schemaErrors.length) {
    console.error(`✗ the ${lex.hq ?? "local"} lexicon is malformed (root: ${rootRel}):`);
    for (const e of schemaErrors) console.error(`    ${e}`);
    return 1;
  }

  const docRel = lex.generated_doc ?? "LEXICON.md";
  const mdPath = join(ROOT, docRel);
  const rendered = renderMarkdown(lex, foreign);
  if (argv.includes("--emit")) {
    writeFileSync(mdPath, `${rendered}\n`);
    console.log(`✓ wrote ${docRel} (${lex.terms.length} terms, ${(lex.owns ?? []).length} namespaces)`);
    return 0;
  }

  const explicit = argv.reduce<string[]>((acc, a, i) => {
    if (a === "--file" && argv[i + 1]) acc.push(argv[i + 1]);
    return acc;
  }, []);
  const files = explicit.length ? explicit : filesInScope(lex);

  const allFindings: Finding[] = [];
  for (const f of files) {
    const abs = join(ROOT, f);
    if (!existsSync(abs)) {
      console.error(`✗ no such file: ${f}`);
      return 1;
    }
    allFindings.push(...scanText(readFileSync(abs, "utf8"), f, lex));
  }

  const basePath = join(ROOT, "scripts", "lexicon", "baseline.json");
  if (argv.includes("--update-baseline")) {
    const next: Baseline = {
      about:
        "Known vocabulary debt at the time the gate landed. Every entry is drift the gate WOULD flag, parked here so new drift can be blocked immediately instead of waiting for the rewrites. Shrink this file; never grow it. An entry disappears when the doc that owns it is rewritten.",
      generated: new Date().toISOString().slice(0, 10),
      findings: tally(allFindings),
    };
    writeFileSync(basePath, `${JSON.stringify(next, null, 2)}\n`);
    console.log(`✓ baseline updated — ${allFindings.length} known finding(s)`);
    return 0;
  }

  const base: Baseline | null =
    !argv.includes("--strict") && existsSync(basePath)
      ? JSON.parse(readFileSync(basePath, "utf8"))
      : null;
  const findings = aboveBaseline(allFindings, base);
  const carried = allFindings.length - findings.length;

  // LEXICON.md is generated; drift between it and the JSON is a failure too.
  const staleDoc = !existsSync(mdPath) || readFileSync(mdPath, "utf8").trim() !== rendered.trim();
  if (staleDoc && !explicit.length) {
    console.error(`✗ ${docRel} is out of sync with ${rootRel} and its namespace files`);
    console.error("    fix: npx tsx scripts/lexicon/check-lexicon.ts --emit");
  }

  if (findings.length) {
    console.error(`✗ ${findings.length} NEW vocabulary finding(s) above the baseline:\n`);
    let current = "";
    for (const f of findings) {
      if (f.file !== current) {
        console.error(`  ${f.file}`);
        current = f.file;
      }
      console.error(`    ${f.line}: "${f.term}" — ${f.message}`);
    }
    console.error(
      '\n  A line that must mention a retired term (an audit trail, a supersession\n  note) may carry an inline `<!-- lexicon-allow -->` marker.',
    );
  }

  if (findings.length || staleDoc) return 1;
  console.log(
    `✓ lexicon clean — ${lex.terms.length} terms, ${files.length} files scanned, 0 new findings`,
  );
  if (carried > 0) {
    const owed = Object.entries(tally(allFindings))
      .map(([f, terms]) => `${f} (${Object.values(terms).reduce((a, b) => a + b, 0)})`)
      .join(", ");
    console.log(`  carrying ${carried} baselined finding(s) — outstanding rewrite debt: ${owed}`);
  }
  return 0;
}

if (process.argv[1] && resolve(process.argv[1]) === resolve(fileURLToPath(import.meta.url))) {
  process.exit(main(process.argv.slice(2)));
}
