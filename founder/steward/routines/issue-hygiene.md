# Routine — GitHub issue hygiene

| | |
|---|---|
| **Policy rule** | `issue-suite-review` (Class B) — dispatch rule in `POLICY.yaml`, routine `issue-hygiene` |
| **Sensor** | `issue-hygiene` — reads the driver census `.gaia/steward/inputs/github-issues.json` and the reconciliation manifest |
| **Debt kinds** | `issue_suite_review` (Class B, this routine); `issue_closure_ready` (Class A, forge-executed, not this routine); `issue_founder_decision` (Class C, founder desk) |
| **Authority** | Class B — proposal only. Closing issues, accepting candidates and registry edits are never part of this routine |
| **Cadence** | On each census refresh, when a suite batch gains candidates, when an umbrella is superseded, or after a founder ruling |
| **Routine catalog** | #18 — GitHub Issue Hygiene |
| **Decision record** | `founder/steward/decisions/steward-issue-closure-authority.json` (closure authority, campaign #2130) |

---

## What it is for

Upstream intake creates one umbrella per release and a child per candidate. Over
time some candidates are already curated in the registry, some duplicate an older
child, and some are waiting for a person to say whether a whole family of
components belongs. Reading those batches by hand does not scale, and a title
match is not evidence that work was preserved.

This routine reviews **exactly one suite batch** and returns a written proposal:
for each candidate, what the registry says and what should happen next. It never
does the next step itself. Closure is a separate, rule-bound forge action
(`issue_closure_ready`) that only fires when the manifest proves preservation.

## When it is worth looking

- A census refresh shows a suite batch with candidates that have no proven disposition.
- A new umbrella supersedes an older one, and the older one's candidates need a lossless mapping.
- A founder ruling lands on a family, so its batch can be reconciled against that ruling.

It is not worth looking at a batch where every row is `issue_closure_ready` or
already closed. The sensor resolves those by itself.

## Envelope to grant

The `POLICY.yaml` packet is authoritative; this routine cannot widen it.

- **May write:** `docs/agents/issue-hygiene/**` (the disposition proposal) and `tests/steward/**` (focused regression tests only).
- **Never writes:** `.gaia/steward/**`, `registry/**`, `skill-trees/**`, `docs/graph/**`, `founder/**`, `.github/**`, `src/**`, `.agents/skills/**`, `.claude/skills/**`.
- **Never does:** close an issue, comment on an issue, accept or reject a candidate on the founder's behalf, change trust or rank, or edit a registry record by hand.
- **May run:** `python -m pytest tests/steward/issuehygiene`, `python scripts/check_steward_coverage.py --check`, and read-only `gh issue view <number> --json number,title,state,labels,body`.

## Objective, in one batch

Given one suite key named in the packet, for each candidate row in that batch:

1. Read the row's census snapshot (`updatedAt`, `bodySha256`, labels) and the candidate payload block.
2. Check the registry for the candidate's suggested ID (`registry/named/<owner>/<slug>.md` and `registry/nodes/**`). Record exact-present, absent, or alias-suspect. A same slug under another contributor handle is alias-suspect, never present.
3. Check the evidence URL against the registry record's `links.github` (blob-normalized) and against any merged pull request in the census.
4. Choose one disposition:
   - **accept-candidate** — the candidate is already curated with the same evidence URL; the child is a duplicate of preserved work.
   - **alias-of-existing:<id>** — the candidate is the same component as an existing registry record under a different identifier; name the record and the proof.
   - **reject-candidate** — the candidate is out of scope, with the reason the batch already carries.
   - **needs-founder** — the proof does not settle the question, or the batch changes a product judgment. Name the question.
5. Write one proposal file for the batch, with per-candidate evidence URLs, the registry checks you ran, and their exact results.

The proposal is a reviewable artifact. A person decides what to do with it.

## Stop conditions

1. The packet names more than one suite batch. Stop and report; do not batch two.
2. A row's registry evidence cannot be read from local repository state. Report the row as unknown; do not guess.
3. A disposition would close an issue, accept a candidate, or change the registry. Stop; that is a different authority.
4. The payload preservation proof for a row is incomplete. Mark it `needs-founder`.
5. The correction needs a registry mutation outside `gaia dev` verbs. Stop and report the verb that would be needed.

## Proof contract

Every disposition must be reproducible from the census and the local registry
state:

- the command that reads the census row (`gh issue view <number> --json ...` or the census file)
- the registry path checked and the exact match result
- the focused test run: `python -m pytest tests/steward/issuehygiene`
- `python scripts/check_steward_coverage.py --check`

An independent reviewer re-runs the same commands before the proposal is used.

## Done means

- Every row in the batch has exactly one disposition and its evidence.
- Alias-suspect rows are never reported as present.
- The diff touches only the allowed paths.
- No issue was closed, commented on, or edited.

## Founder notes

- Closure authority is not granted here. It is the rule-bound `issue_closure_ready` path, recorded in the decision file above, and it is switched off by `issueHygiene.writesEnabled: false`.
- A proposal that says `accept-candidate` is a recommendation. The founder still decides whether the umbrella closes.
- The highest-value dispatch is the batch where a founder question has just been answered. Reconcile that family, then close what the rule proves.
