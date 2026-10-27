# git-log-L-vs-graft-v1 paired run, 2026-10-28

Status: **untrusted experiment record**. Not authenticated independent verification, not public admission, no superiority or performance claim. Result classification: **inconclusive**.

## Environment
macOS 26.4.1 (Darwin 25.4.0); Apple Git 2.50.1 (`/usr/bin/git`); Python 3.14.7; Graft CLI 0.25.0 (0.26.0 available, not upgraded). Checkout HEAD `5ec88137399e29fdc6e17be74fe29236c1e79181` (branch `ygg4-frontier-local`), clean `git status --porcelain` before.

## Commands
1. Native: `python3 examples/frontier/run_git_log_L_fixture.py --output <scratch>/native.json` (temporary repo, `git log -L :score:sample.py` over baseline and update commits; both revisions and both `return value + 1` / `+ 2` bodies present).
2. Request: `python3 examples/frontier/build_verification_request.py`.
3. Target: `graft --dir <scratch>/graft-graph build --only-dir examples/frontier/fixtures --no-gitignore --no-ignore .` (graph kept outside the worktree; 1 file, 3 nodes, 3 edges), then `graft ask "locate function score" . --source`, `graft callers score .`, `graft callers caller . --direction out`, `graft ask "historical line evolution of score across commits" .`, `graft grep "return value" .` (all with `--dir <scratch>/graft-graph`).
4. Recorder: `python3 examples/frontier/record_experiment.py --target-output generated-output/frontier/graft.target-output.txt` with the native/target artifacts copied into the gitignored `generated-output/frontier/`.

## Output digests (sha256)
- native.json `87adbb7d187bd6c9d9336c5af48f0dc773add982d11cb4b4d6a02b80dbec1b8a`; native `git log -L` output `5801c6570b1bbb5bf8281a6439aee53e7f1df4cfcb95a47d841c58b1497c744c`
- combined Graft target output `8d79b54edbdabcb161d77af53cee2bb49621724e273f9ebc06a374691563eed0`
- graft build `1e040c91...`, locate `2a969621...`, callers `cad0985c...`, callers-out `f1925397...`, history ask `d65aa57b...`, grep `277c5175...`

## Observations
- Git `log -L` traced `score` across both fixture commits with the historical bodies.
- Graft located `score` (L1-L3) and `caller` and resolved `caller -> score` in both directions. It returned only the **current** `score` body; the history question returned the same current-code nodes and no historical evolution. Graft historical-line support was therefore not demonstrated.

## Receipt
**No receipt was written.** The recorder refused with exit 2: `recording refused: local Git version differs from candidate version bound by request`. The request binds native version 2.56.0 (the documentation tag in the lead); the executing host Git is 2.50.1. No other Git binary on the host was 2.56.0 (2.53.0 and 2.50.1 found). The guard was not bypassed and the lead was not edited. The recorder's `inconclusive` result, `verification=untrusted-experiment-record` and `admission=blocked` therefore do not apply to this run, because it never reached recording.

## Source invariance
Clean. `git status --porcelain` was empty before and after every step (graft build, queries, recorder refusal) and HEAD stayed `5ec88137...`. Prior failure cause (graft build rewriting tracked `.gitignore`) is prevented by the `/.graft/` ignore entry plus `--no-gitignore --no-ignore` and an out-of-tree `--dir`.

## Interpretation and limitations
Git history tracing and Graft current-code context are different tasks; outputs are complementary, not like-for-like. Per protocol this is inconclusive for superiority; nothing here supports replacement, performance, or admission. One 7-line fixture; no speed, scale or cross-repo generality. Run by the same agent lane that produced the lead, so it is not independent, and reviewer identity is not authenticated. Finding: strict equality between the lead's documentation-tag Git version and the host Git blocks recording on any host without exactly Git 2.56.0.
