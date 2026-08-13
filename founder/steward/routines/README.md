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
gaia steward dispatch <debt-id> --prompt   # the full prompt, verbatim
```

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
| [Repository hygiene](repository-hygiene.md) | `repository_hygiene` | Not yet | Weekly | Generated drift, stale branches, orphaned artifacts |
| [CLI contract drift](cli-contract-drift.md) | `cli_contract_drift` | Not yet | Before each release, else monthly | Help, discovery, or config surface changed without its contract |
| [Knowledge contradiction](knowledge-contradiction.md) | `knowledge_contradiction` | Not yet | Monthly, and after any founder ruling | Two source-of-truth documents disagree |

**"Not yet" is honest, not aspirational.** Those routines have a written human
contract and a cadence, but no sensor emits their debt, so `gaia steward
dispatch` will refuse them today. You can still run one by hand from its file.
Wiring a routine is a `POLICY.yaml` edit plus a sensor — no CLI change, since
V1.2 generalized dispatch rules to a declared set. Two details differ between
them: `cli_contract_drift` and `knowledge_contradiction` are already classified
Class B in `POLICY.yaml`, while `repository_hygiene` is not classified at all
and needs an `authority` and `priority` entry as well.

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
