# Gaia Steward policy

`POLICY.yaml` is the machine-enforced authority and priority policy for Gaia
Steward. `gaia steward scan` remains report-only. `gaia steward run` is the
explicit local closed loop for one policy-authorized Class A repair; it refuses
unclassified debt, unsafe paths, unknown coverage, and authority beyond its
single executor.

Steward writes ignored local state under `.gaia/steward/` and, only for the
declared Class A executors, the two mirror surfaces below. It does not dispatch,
create issues or pull requests, mutate canonical registry data, use a model, or
call the network.

| Executor | Canonical (read-only) | Writable mirror | Independent proof |
|---|---|---|---|
| `bundled-schema-mirror` | `registry/schema/**` | `src/gaia_cli/data/registry/schema/**` | `python scripts/sync_bundled_schemas.py --check` |
| `agent-skill-mirror` | `.agents/skills/**` | `.claude/skills/**` | `python scripts/sync_agent_skill_mirror.py --check` |

An executor is an authority envelope over a repair that is *registered in code*
(`src/gaia_cli/steward/mirrors.py`). Policy may narrow the authorized set by
omitting an executor; it can never invent one, point one at another surface, or
grant one a writable path outside `allowedWrites`. `maxRepairsPerRun` caps how
many surfaces a single run may change.

The two surfaces are independent. A mirror whose repair cannot be proven — a
mirror-only path that would have to be deleted, a dirty user edit, a symlink —
is recorded in the receipt's `blocked` list and left open; it never suppresses
the other surface's proven repair.

`agent-skill-mirror` treats `skill-creator/**` and Python bytecode as locally
owned by `.claude/skills/`. Those paths are neither compared nor overwritten,
and the repair carries them across its atomic replacement byte-for-byte.

Each checkout permits one debt transaction at a time via the atomic
`.gaia/steward/.scan.lock` directory. A process crash may leave this lock in
place; subsequent scans fail closed, and the lock may be removed manually only
after confirming that no Steward scan is active.

A successful changed run retains the displaced pre-repair mirror under
`.gaia/steward/`. The repair receipt records its repository-relative recovery
path and pre-repair SHA-256 manifest. This recovery is intentionally retained
for manual audit or restoration until a maintainer removes that receipt-recorded
local recovery directory; failed transactions restore the target and clean
their temporary recovery instead.

Authority is a ceiling. A future runtime may downgrade A to B or B to C when
proof becomes ambiguous; it may never upgrade authority automatically.

## Class B — dispatch is report-only

`gaia steward dispatch <debt-id>` renders one policy-bounded Tree Keeper packet.
`--prompt` projects that packet into a complete, harness-neutral prompt you can
paste into any agent:

```bash
gaia steward dispatch <debt-id> --prompt | pbcopy
```

Rendering executes nothing and spends nothing. Each dispatch rule names the
routine's human contract in `promptGuide`, which policy validates must be a
markdown file under `founder/steward/routines/` — see that directory's README
for the routine library and its recommended cadences.

Dispatch rules are a declared set, not a fixed one. Wiring another Class B
routine is a `POLICY.yaml` edit plus a sensor that emits its debt kind; no CLI
change is needed. A rule may only route debt that policy classifies Class B, so
neither a Class A repair nor a Class C governance decision can be handed to an
agent by editing routing.

Each rule also carries `capability`: one sentence about the *reasoning the work
demands*, never about who supplies it. Policy refuses a capability line that
names a model, a provider, or a harness (founder ruling 2026-08-13,
`founder/STEWARD.md` § 9). It gates nothing — it exists so whoever schedules the
work knows whether they are handing over a chore or a judgment call, and so a
stronger reasoner is never mistaken for a wider envelope.

## Class B — the rolling lane

`gaia steward dispatch <debt-id>` answers *render this one*. The lane answers the
question that decides whether maintenance keeps moving while nobody is watching:
**what next, how much at once, and what happens to work that keeps failing.**

```bash
gaia steward lane status                 # what is queued, in flight, escalated
gaia steward lane next --prompt          # hand out the next dispatch the bounds allow
gaia steward lane record <debt-id> --verdict accept --note "who said so"
```

`lane next` writes the same `dispatch` receipt that `gaia steward dispatch`
writes, so verification finds the envelope without knowing which command
produced it. It is the pickup point: an agent or a scheduled routine calls it,
gets a prompt or nothing, and either way it is done.

Almost all of the lane is limits, and code caps each one so editing `POLICY.yaml`
can never grant unbounded autonomy:

| Bound | Shipped | Why it exists |
|---|---:|---|
| `maxInFlight` | 1 | Autonomy that outruns review is not autonomy, it is backlog |
| `maxAttempts` | 2 | A debt that keeps failing bounded repair is telling you the envelope is wrong |
| `cooldownSeconds` | 3600 | A broken loop cannot spend an afternoon rediscovering one rejection |

The states are `queued → dispatched → {queued, escalated, closed}`. There is no
`accepted` state — acceptance *closes* an entry, and the entry records who said
so. A `pending` verdict is deliberately **not** progress: machinery finding
nothing wrong leaves the work outstanding until someone judges it.

**Escalation has somewhere to land.** A debt that exhausts its attempts leaves
the agent lane and appears in `gaia steward founder`, grouped by the routine
whose envelope kept failing — so one ruling can unblock everything that routine
gave up on. That is the permitted B → C downgrade. Nothing promotes a founder
matter back into the lane, and a fresh observation does not re-queue an
escalated entry: the sensor keeps seeing the condition precisely because nobody
has ruled on it yet.

Reconciliation is mechanical in both directions. Debt this scan observed as
drift enters as `queued`; debt no longer observed leaves as `closed`, including
debt that was in flight — a finding that stopped reproducing is resolved whether
or not the agent is what resolved it.

`LaneEmpty` is a distinct error from every other routing failure, so a scheduled
pickup can tell *Steward is idle* from *Steward is broken*. The CLI exits `0`
on an empty lane. Quiet days are the common case and must not page anyone.

## Class C — the founder digest

```bash
gaia steward founder            # the digest a person reads
gaia steward founder --json     # the queue as data, unchanged
```

The digest *is* the human surface. A terse list of decision ids was machine
output wearing a person's clothes.

Three rules shape it, and each is easy to lose by "improving" it:

- **Report by exception.** A digest that summarises a healthy repository at
  length trains you to stop opening it. Nothing to decide → one paragraph, stop.
- **Recommend only what is derivable.** A lane escalation has a mechanically
  obvious shape — bounded repair reached its ceiling, so the envelope is the
  likelier defect — and gets a recommendation. A generic-mapping question turns
  on ontology, and gets an explicit *"Steward has no basis for an opinion here."*
  A recommendation nobody can trace is worse than none.
- **Blindness is louder than debt.** Open debt is information. A sensor that
  could not run means Steward does not know what is true, and routing refuses
  outright rather than printing a queue that looks complete.

Decision labels (`C-5de8`) are a prefix of the decision's own identity hash, not
a position in the list. A positional `C-001` would renumber everything remaining
the moment one decision was resolved, and a label that moves is not a label. If
two would collide, every label lengthens together, so two printings of one queue
never disagree.

Decisions group by the exact question, not by the debt that surfaced it — one
ruling can close several items at once.

## Class B — verification is where autonomy earns its keep

```bash
gaia steward verify <debt-id> --diff candidate.diff --proof proof.json
```

Verification judges a candidate patch against the envelope **its dispatch
receipt recorded**, not one re-derived from today's policy — otherwise a policy
edit made after dispatch would retroactively change what the builder was held
to. Work that was never dispatched cannot be verified at all, and a receipt
edited after publication no longer hashes to its own name and stops counting as
evidence.

One asymmetry makes the whole lane defensible:

> **The machine may reject. The machine may escalate. The machine may never accept.**

Everything a path comparison, a policy lookup, or an exit code can settle is
settled for free: scope against the envelope, proof coverage and exit codes,
whether the finding came from a sensor or was merely asserted, whether the debt
is still Class B, whether guards were weakened, whether unrelated debt appeared
mid-flight. Anything disqualifying ends the verification there, having spent
nothing.

What survives is the part machinery cannot reach — *does this patch resolve the
finding, and does the proof demonstrate that rather than merely exiting zero?*
Only that goes to an independent verifier:

```bash
gaia steward verify <debt-id> --diff candidate.diff --proof proof.json --prompt
```

`--prompt` is **refused** when machinery already decided. Paying a reasoner to
re-derive a fact a path comparison established is exactly the spend the cost
doctrine exists to prevent.

The verifier's prompt is a separate artifact from the builder's context. It
carries the finding as a sensor recorded it, the envelope, the diff, and the
captured proof output — and deliberately no account from the builder of what
they did or why. A verifier reading that account is verifying the account.

Exit codes: `0` pending, `1` reject, `3` escalate. **`0` does not mean accept**
— Steward has no authority to accept, and never returns a code that should be
read as one.

`--proof` takes a `steward-proof-transcript-v1` document:

```json
{
  "schemaVersion": "steward-proof-transcript-v1",
  "entries": [
    {"contractIndex": 1, "command": "python scripts/validate.py", "exitCode": 0, "output": "..."}
  ]
}
```

`contractIndex` is the 1-based position in the packet's proof contract. Every
item needs at least one entry; every entry must have exited zero.
