# Class B routines — prompts and cadence

**Status:** Founder operating reference
**Companion to:** `founder/steward/POLICY.yaml`, `founder/STEWARD.md` § 6, § 8

Class A closes itself. Class C waits for you. This directory covers the middle:
work that needs interpretation but has a narrow envelope and hard proof.

---

## The one rule that makes this directory safe

> **Cadence is a ceiling on attention, not a clock that creates work.**

A routine does **not** run because it is Tuesday. It runs because Steward found
a finding that maps to its outcome. The cadences below say *how often it is
worth looking*, never *how often something must be repaired*. A routine that
wakes up, finds nothing, and stops has done its job perfectly.

If you ever find yourself dispatching a routine to justify its schedule, the
schedule is wrong — delete it.

---

## Picking a harness

Every routine here is **harness-neutral by construction**. The prompt names no
model, no provider, and no tool surface, because none of those change what the
work *is*. Pick whatever you are holding:

| Harness | Good when | How you start it |
|---|---|---|
| **Claude** (Code, web, or a scheduled Routine) | Long context, repository-wide reading, anything where the diff needs judgment | Paste the prompt into a session with the repo checked out |
| **Hermes** (macOS, local) | Clean-install reproduction, browser or local state, anything needing your real machine | Paste the prompt into a local one-shot run |
| **Codex / anything else** | Bounded code + test work with a clear contract | Paste the prompt |

The prompt is the contract. The harness is a scheduling convenience. If a
routine only works on one harness, that is a defect in the routine, not a
property of the work — file it.

**What the harness owns:** the model, the effort setting, the spend, and the
wall-clock ceiling. Steward's packet carries a zero budget precisely because
Steward is not paying for a report-only dispatch — you are.

**What the harness never owns:** the authority envelope. A stronger model does
not get a wider envelope. That rule is machine-enforced in `POLICY.yaml`, not a
matter of prompt etiquette.

---

## Getting a prompt

Never hand-write one. Ask Steward:

```bash
gaia steward scan                          # what is open?
gaia steward lane next --prompt            # the next thing the bounds allow
gaia steward dispatch <debt-id> --prompt   # or one specific finding, verbatim
```

`lane next` is the one to reach for by default: it respects `maxInFlight`, skips
anything still cooling down after a rejection, and picks by expected maintenance
value rather than by whatever caught your eye. `dispatch` is for when you already
know which finding you want.

**Agents pick work up through the same door.** The `gaia-steward-lane` skill
(mirrored in `.claude/skills/` and `.agents/skills/`) is the agent-facing wrapper
around exactly these commands — so an agent asked "is there anything to fix?"
finds the lane instead of inventing a cleanup pass.

`--prompt` renders only. It runs nothing, changes nothing, and spends nothing —
it reuses the receipt written when the packet was rendered, so the dispatch you
paste is traceable to the scan that justified it.

Piping is the expected use:

```bash
gaia steward dispatch <debt-id> --prompt | pbcopy
```

The routine files in this directory are the **human** contract — what the
routine is for, when it is worth looking, what "done" means, and what should
make you stop. The generated prompt is the **agent** contract. Read the file
once; paste the prompt every time.

---

## Cadence

| Routine | Debt kind | Wired to a sensor? | Worth looking | Trigger that actually matters |
|---|---|---|---|---|
| [Registry integrity review](registry-integrity-review.md) | `registry_integrity_failed` | **Yes** | Every scan (daily pulse) | Any node schema, reference, or DAG violation |
| [CLI contract drift](cli-contract-drift.md) | `cli_contract_drift` | **Yes** | Every scan; matters most before a release | A command exists but is unlisted, is listed but absent, or is documented and gone |
| [Trust calibration drift](trust-calibration-drift.md) | `trust_calibration_drift` | **Partial** | Every scan | Stored rank differs from computed grade; not cache-hash freshness |
| [Repository hygiene](repository-hygiene.md) | `repository_hygiene` | **Partial** | Every scan; weekly review ceiling | One of eight explicitly enumerated Class P paths is tracked in Git |
| [Knowledge contradiction](knowledge-contradiction.md) | `knowledge_contradiction` | **Partial** | Every scan; especially after a contract change | Selected policy/schema contradictions or exact retired trust-guidance claims |
| [GitHub issue hygiene](issue-hygiene.md) | `issue_suite_review` (also `issue_closure_ready`, `issue_founder_decision`) | **Partial** | Each census refresh | A suite batch gains candidates, an umbrella is superseded, or a founder question is answered |

[**Heartbeat**](heartbeat.md) is not a repair routine and is not in that table.
It is the standing scheduled question — *is anything happening a person should
know about?* — and it reports by exception. Daily is plenty.

**Partial is not healthy, and a sensor is not the whole routine.** The coverage
catalog at [`../routine-coverage.json`](../routine-coverage.json) reconciles all
18 founder routines with registered sensors, debt kinds, policy authority and
available routes. Validate it from the checkout with
`python scripts/check_steward_coverage.py --check --json`. This is a static
capability inventory; it does not run sensors or establish live repository health.

Issue #2105 adds the hygiene sensor and extends the existing knowledge sensor;
it does not create a second knowledge sensor. The five Class B rules in this
branch include two **founder-review proposals**: `repository-hygiene` and
`knowledge-contradiction`. They remain report/proposal-only, preserve the hard
forbidden-path floor, and grant no deletion or canonical mutation. Changes to
`POLICY.yaml` must receive founder review before integration to main. Class A
still has exactly two mirror repair executors.

Hygiene does not assess stale branches, unused code, all generated outputs or
untracked caller files. Knowledge checks only their explicitly listed active
surfaces, not general semantic consistency or historical handovers. Evidence-link
checks do not establish external HTTP liveness, and metadata checks do not prove
an installation succeeded. Curation assurance (#1922), installability
(#1445/#2063) and trust-cache refresh (#1642) keep their existing owners; missing
independent proof stays unknown rather than becoming calendar-created debt.

`cli_contract_drift` was the second one wired (V1.4), and it is worth knowing how
its sensor works before you read its findings. It never imports the CLI — a
sensor that imports the code it audits reports on the *installed* package rather
than the checkout in front of it, and runs arbitrary repository code to do so.
It parses the source instead, and compares the three places this CLI declares
itself: the command modules, `PUBLIC_COMMANDS`, and the top-level list in
`CLAUDE.md`. Only unambiguous directions are reported. "Documented but absent" is
a lie about the CLI; "present but undocumented" is an editorial choice, and
reporting it would bury the first under every deliberate omission.

Its envelope deliberately cannot reach `CLAUDE.md` or anything under `founder/`.
An agent may reconcile the code to the contract; deciding what the contract
*should say* is not a bounded repair.

`sensor_coverage_unknown` is also Class B but is **undispatchable by
construction**, and deliberately so: routing refuses to render anything while
sensor coverage is unknown, which is precisely the condition that creates that
debt. A blind Steward must not hand out work based on what it could not see.
Treat it as a signal to fix the sensor, not as a routine.

### The envelope has a floor

`POLICY.yaml` cannot grant a dispatch write access to `founder/**` (the policy
that defines authority), `.gaia/steward/**` (the receipts that are the audit
trail), `.github/**` (the gates), `registry/schema/**`, `skill-trees/**`, or
`.agents/skills/**` (the canonical side of a mirror the Class A lane itself may
not write). Every rule must also name those as forbidden, so the rendered
prompt always carries them. Class A envelopes are pinned in code; this is the
equivalent floor for Class B.

Note that "downgrading" a Class A debt kind to Class B is permitted by the
constitution but is **not automatically safer** — it trades a compiled-in
envelope for a free-text one. The floor above is what keeps that trade bounded.

---

## When a routine comes back

Do not read the diff first. Hand it to Steward:

```bash
gaia steward verify <debt-id> --diff candidate.diff --proof proof.json
```

Most of what you would check by eye is mechanical, and Steward checks it for
free: did the change stay inside the envelope, does every proof-contract item
have passing evidence, was the finding observed by a sensor or merely asserted,
is the debt still Class B, were guards weakened, did unrelated debt appear while
the builder worked. Any of those failing ends it — and the machine can only
**reject** or **escalate**. It never accepts. That is deliberate: a check that
never looks at whether the patch does anything must not be able to bless it.

If nothing mechanical objects, the remaining question is real and needs a second
reader:

```bash
gaia steward verify <debt-id> --diff candidate.diff --proof proof.json --prompt
```

Paste that into a *different* session than the one that did the work. It carries
the finding, the envelope, the diff, and the proof output — and none of the
builder's account of what they did. That omission is the whole point.

Three verdicts, three responses:

- **`resolved`** — verify it, then read the diff and the proof. It is a normal PR from there.
- **`blocked`** — a stop condition fired. This is the routine working. Read the
  reason; it usually means the envelope was wrong, not that the agent failed.
- **`escalate`** — the work turned out to need a Class C decision. It belongs in
  `gaia steward founder`, not in a retry with a bigger model.

A dispatch that reports "the finding was not real" is a **successful** dispatch.
False positives are cheaper than manufactured changes, and Steward is measured
on its no-op rate as much as its closure rate.
