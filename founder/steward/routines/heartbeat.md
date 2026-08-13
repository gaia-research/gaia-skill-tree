# Heartbeat — the scheduled check

**Status:** Founder operating reference
**Companion to:** `founder/steward/README.md`, this directory's README

Everything else in this directory is a *repair* contract: what a routine is for,
what "done" means, what should make it stop. This file is not one of those. It is
the standing question you point a scheduler at:

> **Is anything happening that a person should know about?**

Most days the answer is no, and the whole design goal is that "no" costs almost
nothing to produce.

---

## What this is for

Class A already runs itself on a daily GitHub Actions pulse
(`.github/workflows/steward.yml`) and costs zero tokens. It needs no heartbeat.

What Class A cannot do is notice that a **dispatch has been outstanding for
days**, that a debt has **escalated to the founder queue** and nobody has looked,
or that the lane is **stalled at capacity** behind work that was never verified.
Those are states of the *lane*, not of the repository, and nothing observes them
unless something asks.

That is all this heartbeat does. It reads receipts and reports. It never
dispatches, never repairs, never merges.

---

## Cadence

**Daily is plenty. Weekly is defensible.**

Resist making it hourly. The lane's own bounds already prevent runaway work —
`maxInFlight` is 1 — so a faster heartbeat cannot make anything safer. It can
only make a quiet system feel busy.

---

## The prompt

Paste this into a scheduled run of whatever you use — a Claude Routine, a Hermes
cron, a CI job on a timer. It names no harness on purpose, for the same reason
every prompt here does: if it only works in one place, that is a defect in the
prompt.

```text
You are running the Gaia Steward heartbeat. This is a read-only status check.
You are not here to fix anything, and you should expect to find nothing.

Run these three, in this order, from the repository root:

  gaia steward scan
  gaia steward lane status
  gaia steward founder

Then answer exactly one question: is there anything a person needs to know?

Report NOTHING and stop if all of the following hold:
  - the scan reports no coverage-unknown sensors
  - the lane has nothing escalated
  - no dispatch has been in flight for more than two days
  - the founder queue is empty

That is the expected outcome. A silent heartbeat is the system working.

Report, briefly, if any of these hold:

  COVERAGE UNKNOWN — a sensor could not complete. This is the one genuine
  alarm here: Steward is blind rather than idle, it will refuse to repair or
  dispatch while blind, and the scan output names which sensor. Say which, and
  say that Class A repair is paused until it is fixed.

  ESCALATED — a debt exhausted its attempt ceiling or a verification escalated.
  It has left the agent lane. Name the debt, the routine it was under, and the
  decision `gaia steward founder` is asking for. Do not retry it and do not
  suggest a stronger reasoner: the ceiling already ruled that out, and what is
  in question is the envelope, not the attempt.

  STALLED — a dispatch has been in flight for more than two days with no
  verdict. The lane is at capacity behind it and nothing else can be picked up.
  Name the debt and how long. Say whether the work was ever handed to anyone.

  FOUNDER QUEUE NON-EMPTY — one or more Class C decisions are waiting. Give the
  decision id, the question, and how many debts each one unblocks. Nothing else.

Rules:
  - Do not run `gaia steward run`, `gaia steward lane next`, or `gaia steward
    verify`. Repair and dispatch are not this job.
  - Do not edit any file, open any issue, or push anything.
  - Do not summarize a healthy repository at length. If everything is fine,
    the correct output is one line saying so, or nothing at all.
  - If a command fails, report the failure verbatim rather than interpreting
    it. A heartbeat that guesses is worse than one that stops.
```

---

## Why it looks like this

Three properties are doing the work, and each is easy to lose by "improving" it:

- **It reports by exception.** A daily digest of a healthy repository trains you
  to stop reading digests. The founder's attention is the scarce resource this
  whole system is built to protect (`STEWARD.md` § 10), and spending it on good
  news spends it on nothing.
- **It cannot act.** The heartbeat and the lane are deliberately different jobs
  with different prompts. A checker that can also repair will eventually repair
  something it only meant to check, and the receipt will not explain why.
- **It treats blindness as louder than debt.** Open debt is information and is
  fine. A sensor that could not run means Steward does not know what is true,
  and it fails closed — no repair, no dispatch — until someone fixes it. That is
  the only line in the report that is actually urgent.

## What it is not

Not a substitute for `gaia steward founder`, which is where Class C decisions
actually get read. The heartbeat only tells you the queue is non-empty; it
deliberately does not try to summarize a governance decision in passing.
