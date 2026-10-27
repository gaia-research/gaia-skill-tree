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

## Isolated Git 2.56.0 re-run and receipt
The first attempt (host Git 2.50.1) was refused by the recorder: `recording refused: local Git version differs from candidate version bound by request`. The guard was not relaxed and the lead/request were not edited. The paired run was then repeated with an isolated Git built from source (nothing installed globally):
- Provenance: `https://mirrors.edge.kernel.org/pub/software/scm/git/git-2.56.0.tar.xz`, sha256 `26c56c296b38c0695b26fa95f475f1d01704d2d38e73465ca30b0b2f5dc789d3` (verified before extraction). Build: `make -j8 prefix=<scratch>/git-2.56.0 NO_GETTEXT=YesPlease NO_TCLTK=YesPlease NO_RUST=YesPlease install` (NO_RUST because cargo is not installed; an earlier attempt without it failed on `cargo: command not found`). `bin/git --version` prints `git version 2.56.0`.
- Native side re-run with `PATH=<scratch>/git-2.56.0/bin:$PATH` (native output digest `sha256:eda34266f10f9980b253619013ec5cbbb2f90a1d7c0c0bb826a226facaff1831`; native.json digest `sha256:06fbd052ce6d2782d02dd237f1352083c2b4c4458691419ddcfd3316af6f4ad4`). The Graft target artifact is unchanged (`8d79b54e...`).
- Recorder wrote the receipt, exit 0: result `inconclusive`, `verification=untrusted-experiment-record`, `admission=blocked`, nativeVersion `2.56.0`, two outputs (native, target). The Graft target artifact is unchanged (`8d79b54e...`).

## Re-run after review fixes (current receipt)
After review fixes (commit `ffa252bc9`) the runner embeds `requestId`, `fixtureDigest` and `protocolDigest` in its native JSON, and the recorder verifies them against the request and the checkout's actual fixture/protocol bytes, rejects identical native/target content, and the runner isolates Git from ambient config and refuses to overwrite its output. The paired run was repeated with the isolated Git 2.56.0 on a rebuilt request (`sha256:ea20770d...39e1`):
- native.json sha256 `4c29f7a565a0c7bb4157e0f3f85a538133de3e96b15580183235720f70839747`; native output digest `sha256:5b082a2ebb7b22d2d1fe76dbf9be849ca14dbf11e7eb5885dc2409b1e63c8be3`; target artifact `8d79b54e...` (Graft queries from the first run, same fixture bytes; not re-queried).
- **Receipt sha256 `4ae634e590457a859003ac41b9dad706dbc38bd0cde7a0ca389d0778d12c195c`**, run id `run-36e681bdbce64928ae624a6f67186a10`; result `inconclusive`, `verification=untrusted-experiment-record`, `admission=blocked`. This supersedes the earlier receipt digest `4f3e69da...` (old runner format).
- Invariance: `git status --porcelain` empty and HEAD `ffa252bc9` unchanged before and after.
- Probe: identical-content target with `--result supported` refused; native with missing or wrong requestId/fixtureDigest/protocolDigest refused. Residual limit: the binding is not authentication; a forger who copies the genuine ids and a self-consistent digest is still accepted.

## Source invariance
Clean on both attempts. `git status --porcelain` was empty before and after every step (graft build, queries, recorder refusal, and the isolated Git 2.56.0 re-run, which used the isolated Git) and HEAD was unchanged (`5ec88137...` for the first attempt, `df75d34e0` for the re-run). Prior failure cause (graft build rewriting tracked `.gitignore`) is prevented by the `/.graft/` ignore entry plus `--no-gitignore --no-ignore` and an out-of-tree `--dir`.

## Interpretation and limitations
Git history tracing and Graft current-code context are different tasks; outputs are complementary, not like-for-like. Per protocol this is inconclusive for superiority; nothing here supports replacement, performance, or admission. One 7-line fixture; no speed, scale or cross-repo generality. Run by the same agent lane that produced the lead, so it is not independent, and reviewer identity is not authenticated. Finding: strict equality between the lead's documentation-tag Git version and the executed Git blocks recording on any host without exactly Git 2.56.0; whether the binding should be the doc tag or the executed version is an open design question.
