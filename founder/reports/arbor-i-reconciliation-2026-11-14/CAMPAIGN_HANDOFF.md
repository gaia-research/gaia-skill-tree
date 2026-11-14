# PR reconciliation campaign: handoff (2026-11-14)

**Authority:** founder-approved campaign of 2026-11-14 (full in-scope PR reconciliation through an integration branch, final merge on green required checks).
**Integration branch:** `dev/arbor-i-reconciliation-2026-11-14` (the existing Arbor branch carrying the founder handoff from #2451, reused rather than replaced).
**Integration PR:** [#2458](https://github.com/gaia-research/gaia-skill-tree/pull/2458) → `main`.
**Governing handoff:** [`RECONCILIATION.md`](RECONCILIATION.md) (founder gates, preserved unchanged).
**Out of scope, untouched:** #2455 (Cook intake #2452), #2436 (English docs routine), other English-docs lane work.

The final merge SHA, CI run URLs and release state are recorded in § Final gate. That section is filled in from the live run, not predicted.

## 1. Original PR inventory (captured before any retarget)

| PR | Title | Base at capture | Head SHA | Commits |
|---|---|---|---|---|
| #2457 | test(shadow-corpus): judge future-dated evidence against the real clock | `main` | `0c5dfa514fef24116cae18df9e070d0f826fddf5` | 1 |
| #2445 | steward(B): daily pass 2026-11-11 — calibrate qt-qml-review to 3★ | `main` | `cef1e3d59c00d948ad17b60ea799b8012068537c` | 1 |
| #2439 | feat(arbor): Arbor I declaration-first behavioral seed | `main` | `8aeed7ef64c3b07f4c656ebbeb89d6d4dc84435e` | 5 |
| #2450 | chore(auto): release v9.5.0 [skip-gen] | `main` | `602f7e79239972ea19ad3bf8a380c5973abdff17` | 1 (356 generated files) |
| #2451 (merged before campaign) | founder reconciliation handoff | `dev/arbor-i-reconciliation-2026-11-14` | `54bf6c09e9b303554b8d67ec39c48022833307d5` | 1 |
| #2441, #2440 | issues (not PRs) | — | — | — |

`main` at campaign start: `69697dc68781eaa7e8c48bf05fb7892b3964555e`. Integration branch at start: `13923197406d8854a722bd9352d297aa65d5e686` (2 ahead, 2 behind `main`).

## 2. Topology actions

1. `main` merged into the integration branch (`5ea9d765`).
2. #2457 and #2445 were retargeted to the integration branch and merged by merge commit (`0cc681ed` and `a3895994`). Both PRs show merged.
3. Feature PR [#2459](https://github.com/gaia-research/gaia-skill-tree/pull/2459), `cli/arbor-behavioral-identity`, carries:
   - the #2441 repair;
   - the #2440 doctrine;
   - #2439's five commits, merged unchanged by merge commit `a1fecb19`;
   - the seed admission.

   #2439 was retargeted to the integration branch. When #2459 merged (`40fb58cc`), #2439's head became an ancestor of its base, and GitHub shows #2439 as merged.
4. #2450 is a generated release proposal (`sync-artifacts.yml`), not hand-authored work. Its valid decision is a minor bump to 9.5.0 on the beta channel. Its stale generated payload was built from `main` at `69697dc6`, before this campaign. It was **not** merged into the integration branch. See § 6.

No branch was force-pushed. No protected branch was bypassed.

## 3. Commit/patch preservation matrix

| Original | Content | Disposition | Evidence |
|---|---|---|---|
| `54bf6c09` (#2451) | founder RECONCILIATION.md | Preserved directly; already on the integration branch | file unchanged at final HEAD |
| `0c5dfa51` (#2457) | `tests/test_shadow_corpus.py` real-clock fix | Preserved through merge `0cc681ed` | `git merge-base --is-ancestor 0c5dfa51 <final>` |
| `cef1e3d5` (#2445) | qt-qml-review 2★→3★ + timeline event | Preserved through merge `a3895994`. Class S regenerated at integration (§ 5) | `registry/named/theqtcompanyrnd/qt-qml-review.md` level 3★ |
| `fb21d9f6` (#2439) | seed authoring source, `assemble.py`, store doctrine tests | Preserved through merge `a1fecb19` | ancestor of final HEAD |
| `09a3023f` (#2439) | import of seed sources + projection | Preserved through merge. Generated runtime/edges regenerated under the repaired contract; all 23 immutable source files byte-identical | ancestry; `tests/test_arbor_committed_store.py::test_replay_leaves_every_immutable_source_untouched` |
| `137a23e4` (#2439) | re-issue under founder attribution ruling; guard relations withdrawn | Preserved through merge | ancestry |
| `520e5c49` (#2439) | seed HANDOFF.md | Preserved through merge | file present |
| `8aeed7ef` (#2439) | attribution wording, stronger store test | Preserved through merge. `tests/test_arbor_committed_store.py` was then extended (docstring updated; two tests added), not reduced | diff of that file vs `8aeed7ef` only adds |
| `8aeed7ef` (#2439) | `CLAUDE.md` curation line for `docs/graph/arbor/**` | Superseded by an equivalent, corrected line: `gaia dev docs` now regenerates `registry/arbor` too, and only behavioural edits move it | `CLAUDE.md` § Curation PR |
| `602f7e79` (#2450) | version 9.4.0→9.5.0 + 355 regenerated files | Version decision preserved: the merge message carries a `feat(...)` line, so the release workflow re-derives a minor bump to v9.5.0 from the integrated `main`. The stale payload is intentionally excluded and regenerated in place on the same PR branch | § 6 |

Each in-scope PR's diff was checked against the integrated tree. No file from an in-scope PR was reverted or overwritten, except the #2439 generated projections. Those are deterministic outputs and are re-derived from the unchanged sources.

## 4. Engineering: #2441, #2440, #2439

### #2441: behavioural identity and coherent projection

Code is in `src/gaia_cli/arbor.py`, `scripts/build_docs.py`, and `.github/workflows/{validate,meta-guard,arbor-upstream-check}.yml`. Contracts `pin.schema.json` and `instruction-observation.schema.json` are new. `runtime.schema.json` gains `applicability`. Source contracts are unchanged, so every existing digest stays valid.

**Pins**
- One pin per pinned subject records a behavioural identity digest: the canonical record minus standing and history keys.
- Unknown keys stay in the digest, so a new field fails closed.
- `check` re-derives every pin from current bytes or the matching git blob.
- In CI it runs as `--require-history` on a full clone.

**Instruction observations**
- A baseline must hash to the sha256 a claim cites, and must be cited by an immutable declaration of that subject. This is re-verified offline.
- Drift-checks are monotonic, single-fetch and deduplicated.
- A fetch error is reported and never recorded.

**Applicability**
- Knowledge applies only when:
  - the canonical record is behaviour-equivalent to its pin; and
  - its instructions are known: no link, a commit link, or a verified baseline with no recorded drift.
- Mutable-unobserved, unobservable, changed and unavailable all fail closed.
- `pairApplicable` and the interaction and HH lenses follow it.
- Historical profiles are never rebound.

**Coherence**
- Prestige-only edits change no generated Arbor file.
- `gaia dev docs` replays `registry/arbor` and `docs/graph/arbor` together.
- `--check`, `gaia dev arbor check --require-history` (validate.yml) and the committed-store test all compare byte for byte.
- Meta-guard now covers Arbor sources, pins and observations.

**Known limit (documented in the README)**
- Offline CI cannot see upstream drift behind a mutable link.
- Weekly `arbor-upstream-check.yml` (read-only) fails on drift. Recording that drift is a reviewed maintainer action.

**Consequence**
- The legacy `obra/receiving-code-review` record (2026-08) cites no upstream commit, so it is now inapplicable (`mutable-ref-unobserved`).
- Its source is unchanged. A new declaration read from cited bytes would restore applicable knowledge.

**Regression matrix**

`tests/test_arbor_identity.py` covers the eight brief items plus the review additions:
- timeline, evidence and level-only edits;
- behaviour edits, including unknown fields;
- mutable upstream drift and dedupe;
- link change;
- unavailable upstream and missing canonical;
- generic and named records;
- same-owner, cross-owner and named-to-generic edges;
- legacy unpinned store with git backfill;
- forged current and historical pins;
- uncited baseline, unobservable link and fetch error.

### #2440: doctrine

`registry/arbor/README.md` § Doctrine and `founder/ENDGAME.md` §8 now state:
- every canonical skill is an Arbor subject;
- the evidence tiers stay distinct, and no Arbor record grants an invocation permission or an HH stamp;
- Yggdrasil composition may only be cited as the *reason* for a declared hypothesis; `structuralOverlap` stays `not-evaluated`;
- `duplicates` means behavioural overlap, never canonical deduplication;
- attribution pattern, with older records left as issued.

The doctrine cites its founder sources and ratifies **no contract change**. These remain open for founder ratification:
- a structured graph-suggested-hypothesis provenance field;
- computed `structuralOverlap`;
- a structured owner, author, governance or tier field.

Cross-repo Skill Heaven #253 was not edited; it is another repository, and its text should follow the contract once ratified.

### #2439: Arbor I seed

- **Contents:** 20 skill declarations, 27 claims and 3 source-declared edges, all `expert-declared`. `pairsEvaluated` is 0 and the HH lens is absent.
- **Pins:** all 21 seed subjects were pinned. Current canonical bytes still matched every declared hash.
- **Baselines:** 21 instruction baselines were recorded. Each was fetched at the exact cited commit, matched the cited sha256, and is tied to its citing declaration.
- **Drift:** an upstream drift check on 2026-11-14 found 0 of 21 drifted. Note that `addy-osmani/source-driven-development` is canonically linked to tag `0.6.10`, not `main`.
- The unresolved stop-rule precedence (`systematic-debugging` recovering `executing-plans`) stays a caveat inside the record.
- `guard`, `careful` and `freeze` comparisons remain test candidates; the guard relations stay withdrawn.

## 5. Independent review

Both reviews were native Claude Code `general-purpose` subagents on the Sonnet model, read-only and independent of the Opus author. The Pi `@parke.dev/pi-subagent` / Terra route named in the earlier #2441 dispatch comment was **not** used. The 2026-11-14 campaign authorization allows Sonnet reviewers; that disclosure is made here, not hidden.

- **Seed audit (#2439).** Counts were 20 / 27 / 3. Every cited sha256 and every quotation was verified, including ellipsis-joined excerpts, which matched segment by segment. Attribution and unmeasured status hold, and the edges are source-grounded, not structural. **No blocking findings.** Non-blocking:
  - The `garrytan/qa` rationale's "no push or pull request" should read "no push or PR step found": the file has a PR-detection preamble and a "PR Summary" line.
  - `caioribeiroclw-pixel/evidence-attestation` stays low-confidence; its model-led facet is a self-issued attestation.
  - Records are immutable; both caveats are carried here.
- **Repair review (#2441/#2440), round 1.**
  - Blocking: a fail-open for mutable links, and forgeable historical pins.
  - Should-fix: unverified baselines, `refKind: none` for non-blob links, drift-recording semantics, build_docs write-mode error handling, and doctrine overclaiming ratification.
  - All were fixed in `1ed85590`.
- **Round 2.** All findings PASS. Nits fixed in `8b81e9b5`: `--full-history` blob search, and the citation format stated in the error and README. One nit remains: the scheduled drift workflow only fails its run and does not open an issue.

## 6. Release reconciliation (#2450)

- #2450 was produced by `sync-artifacts.yml` from `main@69697dc6`.
- After the integration merge, the propose job runs on the new `main`:
  - it re-derives the bump from the merge message (a `feat(...)` line → minor → **v9.5.0**, beta channel);
  - it runs `gaia dev release minor --sync` and `gaia dev docs`;
  - it force-with-lease updates `chore/auto-release-v9.5.0`, refreshing #2450 in place from the integrated source.
- The previous `action_required` blocker was workflow-run approval for a bot-authored PR. The runs API approve endpoint clears it: it was tested successfully on run 43547143997. A rerun had returned 403 because a rerun is not an approval.
- Finalization (tag, GitHub prerelease, no PyPI for a minor) runs only when the release PR merges, per canonical release governance.

## 7. Final gate

Filled in at merge time: see the PR #2458 description and the closing comment for:
- final integrated HEAD;
- required-check run URLs;
- merge SHA;
- release PR state.
