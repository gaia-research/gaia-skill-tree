## Cost

**$600.16 public-rate equivalent**, measured from this machine's session logs (Mac/herdr phase, 2026-11-06T16:08Z → 2026-11-08T17:45Z). Claude Code: 2026-11-06T16:08Z → closeout. pi: first record 2026-11-07T14:12Z, last 2026-11-08T17:38Z. Every pi record carries its own `usage.cost`. Flash-lead subagent usage lives only inside each tool result's `details.results[].usage`, and is summed from there. The Termux/Pi phase (11-04 → 11-06) ran on another device and is not included.

These are token counts priced at public catalog rates, not a bill. Claude Code Pro/Max usage is not billed per token. Sources:
- Claude Code: `cost.py --run-report --markdown --offline --session f988054e`. Status complete: 1 main transcript and 17 subagent transcripts, USD complete.
- pi: `steward_cost.py` over `cost.py --since 2026-11-05 --all --json` plus pi's own per-call `usage.cost`.

| Bucket | USD | Share | What it bought |
|---|---:|---:|---|
| Claude Code lead (Opus) | $171.75 | 28.6% | Orchestration, ledger mutations, integration, records |
| Claude Code subagents (2 Opus, 15 Sonnet) | $277.40 | 46.2% | Engineering partners: gates #2391/#2392/#2406, #2371/#2397/#2423 fixes, history and closeout drafting |
| Flash lanes: leads (gemini-3.8-flash) | $44.68 | 7.4% | 15 lane-lead sessions |
| Flash lanes: workers (all models) | $89.43 | 14.9% | 30 worker sessions, 7,396 calls; 91.7% of it gemini-3.8-flash ($82.00) |
| Independent reviewers (Terra, Sol, Luna) | $11.81 | 2.0% | 58 review sessions over every merged PR |
| Steward verifiers (Terra) | $3.32 | 0.6% | 43 independent repair verifications |
| Steward builders (Luna) | $0.68 | 0.1% | 44 repair builds |
| Other engineering (pi) | $1.10 | 0.2% | Small engineering lanes |
| **Total** | **$600.16** | | |

**Unit economics, for later analysis:**
- **Per canonical Class B repair:** $12.50 all-in ($600.16 / 48). The repair loop itself (builders + verifiers + independent reviews) cost $15.81, about $0.33 per repair. Coordination and engineering dominate.
- **Per Class B debt removed from the census:** $4.55 ($600.16 / 132, 323 → 191). This includes decision A, which closed 46 drift debts by founder ruling rather than by repair.
- **Flash lanes:** $134.11 (22.3%) for the flash-lead and worker tier, plus non-Flash models running as Flash workers, all counted above. They produced volume, but needed 2–4 independent review rounds per PR. New Flash dispatch was paused on 11-08.
- **Cache:** 2.64 B of the prompt tokens were served from cache. Without caching, the same work would cost several times more.

<details><summary>Full table by harness, model and role</summary>

| Harness | Model | Role | Sessions | Calls | Input | Output | Cache read | Cache write | USD |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|
| claude-code | claude-opus-5-5 | lead (Opus) | 1 |  | 4,534 | 1,184,284 | 598,229,494 | 0 | $171.75 |
| claude-code | claude-sonnet-5-5 | claude-subagent | 15 |  | 4,674 | 2,028,070 | 586,519,703 | 25,677,097 | $143.13 |
| claude-code | claude-opus-5-5 | claude-subagent | 2 |  | 2,036 | 949,060 | 385,107,179 | 7,650,943 | $134.27 |
| pi | gemini-3.8-flash | flash-lane-worker | 14 | 6756 | 31,504,823 | 4,343,213 | 561,109,591 | 0 | $82.00 |
| pi | gemini-3.8-flash | flash-lane | 15 | 2416 | 19,428,646 | 1,239,974 | 339,505,681 | 0 | $44.68 |
| pi | gpt-6.1-terra | independent-review | 45 | 843 | 2,985,224 | 155,222 | 47,224,704 | 0 | $6.12 |
| pi | gpt-6.1-sol | independent-review | 10 | 316 | 1,191,078 | 83,311 | 23,424,640 | 0 | $5.56 |
| pi | gpt-6.1-terra | flash-lane-worker | 12 | 434 | 3,577,984 | 97,602 | 16,308,736 | 0 | $4.88 |
| pi | gpt-6.1-terra | steward-verifier | 43 | 403 | 2,183,444 | 56,544 | 17,012,096 | 0 | $3.32 |
| pi | gpt-6.1-sol | flash-lane-worker | 2 | 159 | 633,687 | 43,212 | 7,732,992 | 0 | $2.47 |
| pi | gpt-6.1-terra | engineering/other | 7 | 138 | 463,265 | 27,388 | 7,922,048 | 0 | $1.00 |
| pi | gpt-6-luna | steward-builder | 44 | 665 | 2,648,457 | 170,751 | 32,558,976 | 0 | $0.68 |
| pi | gpt-6-luna | independent-review | 3 | 108 | 265,525 | 21,840 | 8,831,744 | 0 | $0.13 |
| pi | gpt-6-luna | engineering/other | 3 | 91 | 286,298 | 26,606 | 5,974,784 | 0 | $0.10 |
| pi | deepseek-flash | flash-lane-worker | 1 | 20 | 31,203 | 25,941 | 1,055,360 | 0 | $0.05 |
| pi | gpt-6-luna | flash-lane-worker | 1 | 27 | 80,733 | 14,127 | 1,539,456 | 0 | $0.03 |
| **Total** | | | | | 65,291,611 | 10,467,145 | 2,640,057,184 | 33,328,040 | **$600.16** |

</details>
