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

## C2 — Zero-manual-update delivery

**Status: RULED 2026-08-07 — npx, and we ship the launcher, never a harness.**

> **Founder ruling:** "I'm actually really good with npx, just make sure that it uses the users
> `claude` that is installed. The idea is that we don't ship 'another claude' but the launcher
> that launches a 'heaven' version of it that ships with the almost zero skill launcher."

This resolves the update problem and clarifies what the product *is*.

**The shape.** `npx` distributes a small launcher. The launcher resolves the harness the user
already has on `PATH` and execs it with a composed posture. We never bundle, vendor, or version a
harness. `claude-heaven` already behaves this way — it finds `claude` on `PATH` and execs it — so
this ratifies existing behaviour rather than redirecting it.

**Why it settles C2 cleanly:**

- Nothing to update manually, because nothing is installed. `npx` fetches the current launcher
  each launch.
- No version skew between launcher, plugin, and core — one artifact, fetched together.
- The harness stays whatever the user chose to install. We are not in the business of shipping
  someone else's agent.

**What it costs:** a network round-trip at session start. Acceptable for a launcher measured in
kilobytes, and `npx` caches.

**The one genuine tension — M0 discipline.** Our probes pin a harness version. Under this model
the *harness* version is entirely the user's, and can change under us without warning. That is
correct product behaviour but it means a recorded dose is a statement about a version, never a
standing guarantee. The door should therefore **read and report the harness version it actually
launched**, so any result carries its own provenance. Cheap to build, and it keeps the Index
honest once benchmarking starts.

**Positioning worth keeping in the founder's words:** the value is *"we don't ship another
claude"* — we ship the thing that launches the user's own harness with almost no skills loaded.
That is the pitch, in an era where models do not need the bloat.

---

## C9 — Grok reads Claude's skill directories

**Status: scouted 2026-08-07, door not built.**

Probed live rather than assumed. `grok inspect` — which enumerates from disk and therefore cannot
confabulate — reports **Skills (110)** on a free-tier account, and the sources are the interesting
part:

```
Skills (110)
  └ impeccable      project [claude]
  └ check-work      user
  └ code-review     user
  ...
```

**Grok reads the same `.claude` project and user skill directories Claude does.** So grok's bloat
is not a separate plugin problem — it is the *same scope problem* `--setting-sources` addresses on
Claude, arriving through a different front door.

Levers found:

- **`GROK_HOME`** — documented in grok's own docs as "Override config directory (default:
  `~/.grok`)". Same shape as `CODEX_HOME`; the door can scope it to the session and copy
  `auth.json` in, exactly as codex-heaven does.
- **`grok plugin disable`** exists but mutates global state — **violates P3, do not use it.**
- `--disallowed-tools`, `--no-memory`, `--no-subagents`, `--no-plan`, `--disable-web-search` trim
  the surface further.
- **`grok inspect` is the probe instrument** — a hard, disk-derived count. Use it rather than
  asking the model, which confabulates.

**Open question for the door:** scoping `GROK_HOME` should handle the `user` skills, but the
`project [claude]` ones come from the working directory. Whether those can be scoped away without
changing `--cwd` is unprobed.

**Caveat recorded:** this is a free-tier account without SuperGrok, and the harness may be
partially locked. Findings above are what that account can see; a fuller account may expose more.

---

## C2 (original framing, kept for the record)

**Status when written: unsolved. Was the biggest adoption risk in Program 3.**

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

**Status: RULED 2026-08-07. Content hashing is deferred until after benchmarking. Ship the
working prototype now.**

> **Founder ruling:** "content hash will be added later after benchmarking the skill. I just want
> a working prototype now."

Rationale as recorded: hashing a skill is only meaningful once the Index has something to say
about that skill, and gating a prototype on it would stall the thing the Index exists to measure.
The risk below stands and is accepted knowingly for founder-driven use.

**Carry forward:** this becomes live again the moment summon points at a session that is not the
founder's own. Do not treat the ruling as closing the question — it defers it.

---

### Original framing (kept for the record)

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

## C8 — Summon sessions fill the disk, and nothing reaps them

**Status: SOLVED 2026-08-07. Verified independently.**

> **Founder direction:** "Reaping / Garbage Collection is essential per session. Possibly retained
> in memory cache only for the next session especially for curated ones… leaning towards a more
> long-term option which utilizes memory — a few megabytes won't hurt."

**What shipped:**

- **The clone is discarded after extraction.** It was always transient scaffolding; we were
  keeping a ~100 MB crate to store a ~200 KB envelope.
- **Per-session GC.** Every summon sweeps roots older than 4 hours (`GAIA_HELL_TTL_HOURS`).
  `close` removes its whole root. `gaia-hell gc --dry-run` previews. **A signal-0 PID check
  protects any live session** — reaping a running session's skills mid-task would have been a
  rare, ugly bug.
- **Cross-session retention: a 16 MiB bounded payload cache with LRU eviction**, keyed by
  resolved commit SHA plus repo and subpath. Only extracted skill payloads, never clones.

**Measured, verified independently by the orchestrator:**

| | before | after |
|---|---|---|
| session root | 69–101 MB | **212 KB** |
| re-summon after `close` destroyed the session | full re-clone | **0.831 s** |

**The founder's "memory" instinct was right, and the mechanism is simpler than a daemon.** At
this size the OS page cache keeps hot payloads in RAM anyway, so an on-disk payload store *is*
memory-resident in every way that matters — without a background process, a socket, or a crash
lifecycle to own. A RAM disk lost on portability and setup; a daemon lost on complexity.

**A prior of mine was disproved, correctly.** I expected sparse/partial checkout
(`--filter=blob:none`, sparse-checkout of the subpath) to be the real fix. Measured across three
skills it produced smaller transient peaks but was **slower every time**. Rejected on evidence.
Discard-after-extract wins outright.

**Consequence to carry:** earlier "warm" timings in this document and in the session report
described a warm *git* cache, which no longer exists in that form. Warm now means a payload-cache
hit. Old numbers do not describe the current code.

---

### Original framing (kept for the record)

**Status when written: hit for real this session.**

Install parity means summon **clones repos**. A session root is therefore not a few kilobytes of
markdown — it is however large the source repos are. Measured today, from ordinary verification
work: **247 MB across a dozen orphaned session roots**, the largest three at 101 MB, 73 MB and
69 MB. That filled the machine's remaining disk and killed a running worker with `ENOSPC`
mid-task.

This is C3's "orphaned root" footnote turning into the actual constraint. The engine ships an
explicit `close`, but nothing calls it when a session ends abnormally — a crash, a killed pane, a
CLI invocation the user never followed up. Every abandoned summon leaves its clones behind.

**Why this bites hardest exactly where it matters.** The high-entropy rungs — `med` through
`max` — are defined by summoning *more*. The mode with the most product value is the mode that
allocates the most disk, from the most repos, fastest. A ladder whose top rung reliably fills the
user's disk is not shippable.

**Options, roughly in ascending cost:**

1. **Reap on start.** On every summon, delete session roots older than N hours. Cheap, no
   daemon, no lifecycle assumptions. Wrong only if someone wants a long-lived session.
2. **Share the repo cache across sessions.** Clone once per repo into a user-level cache and
   materialize skills from it. This is what `gaia install` already does with
   `~/.gaia/cache`. Kills the duplication outright — the three big roots above are almost
   certainly the same repos cloned repeatedly. Costs the P3 "nothing outside the session" purity
   we deliberately chose.
3. **Sparse/partial clone.** `--filter=blob:none` or sparse-checkout of just the skill subpath.
   Keeps session-locking intact and cuts the size by a lot. Most engineering, best result.

**Recommendation: (1) now, (3) before benchmarking.** Reaping is a few lines and removes the
failure mode today. Sparse checkout is the real fix and it also makes the install-time metric
look dramatically better — worth doing *before* the numbers get recorded, since a benchmark run
on full clones would price a cost we intend to remove.

Option 2 is the one to think hardest about: it trades an invariant we chose on purpose for
speed. Worth it only if sparse clone proves insufficient.

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

---

## C10 — Ambient skill-hell meets the boot-index constraint

**Status: ruled by the founder, one mechanism question remains open.**

Your ruling: skill-hell is the ladder, not a search box. Invoking it *opens a rung* (default
`high`); skills then arrive on their own, each announcing itself with a compact card; they land
in a session directory the agent can reach for later; the root stays warm so a later session
re-attaches instead of re-cloning; nothing ever touches the permanent repo. Explicit summon
survives as the advanced control.

**What blocks a literal reading.** WP13 probed Claude Code 2.1.224 for a mid-session skill load
and found none — boot-time controls and resume only. Claude builds its *skill listing* (name +
description per skill) at startup and reads a body on invoke. A skill directory written at
minute 40 is therefore on disk but not in the listing: the model does not know it exists, so it
never reaches for it. Writing files alone does not make a skill available.

**The mechanism that does work, and is the honest version of what you asked for.** The agent
summons *itself*, through the MCP tool, at the moment it hits a capability gap. The user never
types a summon — which is your requirement — and the tool result is what puts the skill in the
listing, because a tool result is context. So:

- **whole directory to disk** — `reference/`, `scripts/`, fixtures all intact, which is what
  makes the skill genuinely usable rather than quoted
- **card into context** — identity, whatever trust the tree published, cost, path, inspect URL

That split is also cheaper than what we ship today, which pastes the entire `SKILL.md` body into
the transcript on every summon.

`/skill-hell` mid-session then means *arm the lane at rung N* — announce the tool, set how freely
it may fire — rather than *fetch one skill now*.

**The open question is the trigger, and it is yours to call.** Agent-initiated is honest and
ships now, but a skill only arrives if the model recognises its own gap — a model that does not
know what it is missing will not ask. The aggressive alternative is a per-turn hook that summons
against every user message, which is genuinely ambient and genuinely noisier and more expensive.
Recommendation: agent-initiated for the prototype, and let the benchmark decide whether the hook
earns its cost.

**A policy note, flagged not decided.** "Opens to `high` by default" opens the Hell lane, which
P2 currently gates at `med` and above. Reading your instruction as the ruling that opens it for
the launcher path; the benchmark `floor` stays byte-frozen and untouched either way. Say if that
reading is wrong.
