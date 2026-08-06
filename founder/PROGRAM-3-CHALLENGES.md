# Program 3 — engineering challenges

Live scratchpad. Session opened 2026-08-07. Program 3 = building the prototypes
(skill-heaven doors + skill-hell). EPIC #1336.

Each entry is something standing between us and a product you can use. Called out so you can
pivot rather than discover it late. **Nothing here is a request for a decision unless it says
so.**

---

## C1 — Every new door needs its own probe before it can launch anything

**Status: structural, accepted cost.**

The compiler never ships a route it has not measured. `compileClaude()` and `compilePi()` are
`execSupport: "exec"` because someone probed those harnesses and wrote down what the flags
actually did. `compileCodex()` is `"recipe"` — it prints a plan and refuses to spawn. Hermes
has no route at all.

So "add three more doors" is not three packages. It is three probe campaigns, each producing
an honest record of what suppression actually works on that harness at that version, and only
then a door.

**Why this is right, not bureaucracy:** the pi route carries a comment about a 0.80.10 quirk
where `--no-skills` next to `-p` silently lost suppression. That is precisely the class of bug
that ships a door claiming a clean floor while leaking the user's whole skill set. The probe is
the product.

**Cost shape:** claude and pi are cheap (done / nearly done). Codex is medium — the isolation
flags are unusually good (`--ignore-user-config`, `--ephemeral`, per-session `skills.config`),
so the probe should go smoothly. **Hermes and Grok are unknown** — no data at all. If either
turns out to have no suppression primitive, that door cannot ship a real floor and would be
recipe-only indefinitely.

**Possible pivot:** ship claude + pi + codex as real doors, and treat hermes/grok as
recipe-only "we can tell you what to run" surfaces until someone probes them. That is honest
and costs nothing.

---

## C2 — Zero-manual-update delivery is unsolved (skill-heaven #34)

**Status: unsolved. This is the biggest adoption risk in Program 3.**

Issue #34 states the hard requirement: users should never run `npm install`, `git pull`, or
`brew upgrade` to get new door behaviour. Today none of the delivery paths satisfy it:

- The **launcher** is a monorepo binary run via `node packages/.../bin/*.mjs`. Not installed,
  not on PATH, not updatable.
- The **plugin** ships through the Claude Code marketplace; whether that auto-updates is
  unverified.
- **core** is consumed in-repo. There is no release artifact.

Three doors multiply the problem: a version skew between launcher, plugin, and core produces
exactly the "worked yesterday" bug class that kills trust in a tool like this.

**This does not block prototyping.** It blocks anyone other than you using the result.

**Decision you may want to make early:** whether doors ship as npm packages (`npx claude-heaven`
gets latest for free, at the cost of a network hit per launch) or as a self-updating binary.
Choosing this late means rewriting the entrypoint of every door.

---

## C3 — `/skill-hell` must work with no door active

**Status: shaped, being built.**

Your requirement: `/skill-hell` is invoked inline *whether or not* claude-heaven or pi-heaven is
running. That rules out the summon engine depending on the door's session directory, because in
the no-door case there is not one.

**Resolution taken:** the summon engine owns its own session root
(`mktemp -d gaia-hell-*`), independent of any door, discoverable through a `GAIA_HELL_SESSION`
env var so repeated invocations in one shell share a root. A door can adopt that root; it never
provides it.

Consequence worth knowing: with no door running, nothing tears the session down on exit. The
engine ships an explicit `close` and writes a manifest so an orphaned root is identifiable and
removable. Not elegant, but honest and recoverable.

---

## C4 — Summoned skills are fetched, not verified

**Status: open. Security-shaped. Worth your ruling before this leaves prototype.**

Skill Hell fetches a `SKILL.md` from `raw.githubusercontent.com` at the URL the registry carries
in `links.github`, and writes it into the session where an agent will read it. The content hash
is computed **after** fetch, for the record — it is not checked against anything, because the
registry does not currently publish an expected hash per skill.

So today the trust boundary is "we trust whatever is at that URL right now." A compromised
upstream repo, or a moved branch, changes what gets summoned with no signal.

The roadmap already anticipates this — Program 3's Index spec asks *"Can it be safely summoned
by content hash?"* and pairs the stamp with security and provenance (G1). The prototype does not
answer it.

**Not a blocker for a prototype you drive yourself.** It is a blocker before summoning is
pointed at anyone else's session. **Recommendation:** keep it, ship it, and treat
registry-published content hashes as the gate for leaving prototype — not as this session's work.

---

## C5 — The entropy ladder is named but not wired

**Status: naming ratified by you; code partially reflects it.**

You have set the product model: one ladder from `off` through `max`, plus `ultra`.
Code today:

- `POSTURES = [floor, product-floor, curated, native]` — the composition primitives.
- `LEVEL_ALIASES = { off: "floor", low: "curated" }` — the ladder's bottom two rungs.
- `HELL_LEVELS = [med, high, xhigh, max]` — present, and every one of them **hard-errors** at
  the P2 gate.
- `ultra` — exists only as a string in the ledger's arm list.

Two consequences:

1. `off` currently points at `floor`, the doorless benchmark ruler, rather than `product-floor`,
   the launchable one. That is skill-heaven **#24**, already filed, and it is a small fix.
2. The hell rungs refuse rather than compose. Wiring them to the summon engine is what turns
   `med/high/xhigh/max` from a gate into a product — that is the shape of the work after the
   summon engine lands, and it is the natural place for "how much do we summon" to become a
   real dial.

No decision needed. Recorded so the gap between the vocabulary and the code is visible.

---

## C7 — Summon fetched a file; installing a skill means cloning a directory

**Status: caught mid-session, rework dispatched.**

The first summon engine fetched a single `SKILL.md` over HTTP and wrote it into the session.
That is **not how Gaia installs skills**, and it silently produces broken ones.

`src/gaia_cli/install.py` is the real thing, and it does considerably more:

- parses `blob/branch/path` (taking the **dirname** when the path ends `.md`) vs `tree/branch/path`
  (verbatim) vs a bare repo root
- `git clone --single-branch --depth 1` into a cache, or `git pull` if the cache is already a
  valid repo — and rmtree + re-clone if it is a partial clone or the pull fails
- validates the resolved subpath **exists**, is a **directory**, and contains **`SKILL.md`**
  before linking, so a stale link never reports success (issue #1441)
- links or copies the **whole skill directory**
- installs `suiteComponents` recursively, with a `visited` set for cycle safety
- records a manifest entry

Many skills are directories — `SKILL.md` plus `reference/`, `scripts/`, fixtures. A summoned
skill missing its scripts is not a skill, it is a description of one. The impeccable skill in our
own fixtures has both subdirectories.

**Founder ruling: summon must behave exactly like `gaia install`.** The rework ports those
semantics into TypeScript (no shelling out to Python, no dependency on a possibly-outdated
globally installed `gaia`). Session-locking is preserved by putting the git cache **inside** the
session root rather than `~/.gaia/` — repeated summons from one repo still clone only once.

### The metric that comes with it

Cloning is much slower than fetching one file, and high-entropy modes summon many skills. So the
rework measures and reports **install time in seconds** per skill — clone, materialize, total —
and whether the repo cache was **cold or warm**, since that dominates the number and a timing
without it cannot be interpreted.

This is the founder's stated performance worry for the high-entropy end of the ladder, and it is
now a first-class output rather than something to discover during benchmarking.

---

## C6 — Benchmark visibility now has a rule, because a worker broke it

**Status: fixed this session.**

You caught a Sonnet worker probing `pi` through its own Bash tool, which hid the `--model`
argv. The measurement may well have been fine; the point is you could not check it.

Codified as **Rule 0** in the `herdr-dispatch`, `pi-playbook`, and `codex-playbook` skills:
every harness invocation runs in a herdr pane, argv on screen, pane id recorded next to the
result. Ordinary shell work stays on the Bash tool — the rule is specifically about invocations
where model identity is the thing at stake.

Worth noting as a pattern: agents default to the cheapest path to an answer, and the cheapest
path is almost never the observable one. Visibility has to be a stated rule with a stated
reason, or it erodes every session.
