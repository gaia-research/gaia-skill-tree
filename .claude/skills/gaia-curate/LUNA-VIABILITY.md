# Luna viability receipt

Date: 2026-07-13

A real Hermes Agent one-shot run tested the bounded fixture in `fixtures/luna-viability-page.json` against the separate oracle in `fixtures/luna-viability-expected.json`.

## Runtime

- Harness: Hermes Agent
- Provider: `openai-codex`
- Model: `gpt-5.6-luna`
- Reasoning effort: `minimal`
- API calls: 1
- Tools/research: prohibited by the task contract

## Result

All five candidate-local decisions matched the oracle:

| Candidate | Decision |
|---|---|
| Existing browser implementation | `MAP` to supplied `browser-automation` |
| Exact content duplicate | `DUPLICATE` |
| Malformed non-skill | `NOT_A_SKILL` |
| Ambiguous capability bundle | `DEFER` |
| Copied skill with cited origin | `DUPLICATE` |

Result: **5/5 exact match**. Luna did not invent a generic ID.

## Usage receipt

| Metric | Value |
|---|---:|
| Input tokens | 3,686 |
| Output tokens | 164 |
| Reasoning tokens | 40 |
| Total tokens | 3,850 |
| Estimated cost | $0.00 |
| Cost status | `included` |

The USD field is the Hermes receipt for this subscription-included run, not proof of an external invoice. The test demonstrates viability only for the mechanical five-candidate decision boundary; it does not authorize evidence work or registry mutation.
