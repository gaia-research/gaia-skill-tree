# Founder rulings, 2026-11-08, afternoon and closeout (verbatim)

The Steward lead (Opus, herdr w2H) received these in the #2283 session on 2026-11-08 and logged each one verbatim in the lead state file before acting on it. They follow the morning rulings in `FOUNDER_RULINGS_2026-11-08.md`.

---

## 0. Upstream deletions: freeze or rename (2026-11-07T17:10Z, recorded late)

This ruling was given on 11-07 and acted on in PR #2373, which froze `garrytan/investigate` on main. It was not written into a repo record at the time. The independent verifier of #2417 caught the gap, and it is recorded here verbatim from the session transcript.

Context: a side note said garrytan/investigate's upstream file was deleted, not moved, and offered two options: freeze it or demote it.

> this is a freeze of course. anything "deleted" upstream needs to be checkd if deleted or "renamed". If deleted, freeze. If renamed, rename. continue on your current task as usual, treat this as a micro directive--let your steward agents fix this

## 1. Swallowed-exception route: read-only opens (about 09:30 local)

Context: a side note told the founder that the redesigned "proof of no effect" envelope makes 0 of the open handlers eligible, and that "the next step would be allowing **read-only file opens**, which needs its own proof and review. That's your call whenever you want this debt to start moving."

> allow

Effect: approves widening the `swallowed_exception` route to admit read-only file opens, with their own proof and an independent review. The work was not started before closeout. It is carried in #2404.

## 2. Roster and HyperFrames evidence (about 16:45 local)

> Do not stop any ongoing subagents. Roster: pause future flash dispatches. Focus on steward work. If you need some engineers for the flash lanes, I'm allowing terra/luna only, no other fallback. For Hyperframes downloads: file as issue rfc if this counts as evidence. I'm leaning towards yes, but in a different category that we haven't graded yet. Future, low priority work.

Effect:
- No new antigravity Flash dispatches. Running Flash lanes ran to completion, and new engineering lanes used openai Terra or Luna only.
- RFC #2403 was filed.
- `heygen-com/hyperframes-cli` has no graded evidence today, so it was demoted with the rest of decision A. It can be re-promoted if the RFC lands.

## 3. Closeout directive (about 17:00 local)

> New directive: Find a very nice stopping point for steward. Something that closes out what you are doing so far. That means engineering work, steward work on the batches that you touched. For now leave class C, but lock the decisions somehow so I can pick up later. For repair routes, file the issue. Thats the only "follow-up" we will be doing, including some steward leftovers. My recommendation: stop until trust calibrations--including long-term solutions for it. Once you are done, if you do have leftovers, I want to see one dev PR going to main, marked as green that somehow includes the full "history" of the steward run since 11/05 in the PR body, with a full /cost or /pi-cost number on the jsonls we've been working on, just simply sum them up--I need to see the true cost of steward and even the flash lanes, with good metrics so I can do economic analysis for later. That means unzipping the jsonls. I don't want to see "stray prs" from steward. Closeout the task by merging them to dev and recording the steward fix receipt so I know how much the number of Class B work has gone down. Then finally, do a /memory-snapshot with your learnings and if you were to suggest one or two things to improve steward, what would that be? File those two as issues just for my visibility. This is how I would like you to close out steward.

Effect: see `OPEN_DECISIONS_LOCK_2026-11-08.md`, which locks the Class C items, and the closeout PR to main, which carries the history, cost and receipts.
