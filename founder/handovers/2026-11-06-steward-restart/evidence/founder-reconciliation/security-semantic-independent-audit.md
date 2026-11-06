# Independent semantic-slice audit — #2283

## Verdict: ACCEPT — bounded semantic slice only

**Candidate:** `166e85514e3cd35d1c4e9cba506b1bb0560661f4`  
**Original source:** `d694986b865e158e21c613683021a9b7822f945c`  
**Reviewed matrix:** `docs/agents/security/2283-dispositions.json`

The source/caller/provenance rationale supports the bounded dispositions of **all 39 rows / all 71 original match occurrences**. Results: **39 supported, 0 unsupported, 0 uncertain**. D1 covers 16 rows / 30 occurrences; D2 covers 14 rows / 24 occurrences; D3 covers 9 rows / 17 occurrences. The pattern totals are 63 credential-assignment, 6 bearer-token, and 2 JWT occurrences. Repeated fingerprints at different original lines and occurrences in both mirrors are counted separately.

This accepts classification of those specific lexical matches, **not** whole-file safety, runtime credential handling, proof that a fixture could never have been issued, alert dismissal, scanner-policy activation, or the full reconciliation mission. No original match examined here establishes an embedded actual credential requiring exposure treatment. Any actual credential leak remains Class C. The matrix is evidence, not permission to close debt or an allowlist.

Reviewer: independent `reviewer-shared`, not the candidate builder. Explicit per-dispatch model binding is `openai-codex/gpt-6.1-sol`, HIGH; no nested agents or alternate model route was used. Runtime-provider attestation remains with the separate assigned lane, rather than being inferred from agent-template defaults.

## Scope, method, and independently observed evidence

- Confirmed the review worktree and exact detached HEAD with `pwd` and `git rev-parse HEAD`. `git status --porcelain --untracked-files=no` was empty before inspection.
- Read root and founder `CLAUDE.md`, the graft skill, the complete matrix, `src/gaia_cli/steward/primitives/redact.py`, and the prior `security-mirror-final-independent-review.md`. The latter explicitly had not completed this semantic slice; its tests are not represented as tests run by this reviewer.
- Used graft for orientation/callers, then examined actual source at the finding sites and relevant producers/consumers. Commands included `graft grep '2283-dispositions'`, the bounded caller-context `graft ask`, and `graft callers TokenStore --depth 1`, `graft callers detectCredentialHarvesting --depth 1`, and `graft callers mentions_suite --depth 1`. Graft's detector caller list was incomplete for production composition; direct source inspection also followed `scanNamedSkillFiles` and `push.scanBatchForSecurity`.
- Read original repository bytes in memory with `git show <original-sha>:<path>` and current bytes with Python `Path.read_text/read_bytes`. Source contexts were printed through the existing scrubber; fixture-bearing Python contexts additionally had string literals replaced by length/fingerprint descriptors. No raw candidate credential values are included in this report or saved to scratch.
- **Independently checked all eight D1 mirror pairs:** original `.agents` bytes equal original `.claude` bytes; current `.agents` bytes equal current `.claude` bytes; original canonical bytes equal current canonical bytes. All 24 equality comparisons were true. This is exact byte equality, not an inference from the matrix's duplicate-group labels. The shared assessments below therefore apply to both explicitly listed IDs in each pair.
- For D2, compared original/current parsed Python ASTs. Twelve modules were AST-identical. `tests/test_auth.py` and `tests/test_curation_assessment.py` became identical after excluding docstrings. Thus the reviewed fixture expressions, injection wiring and assertions were retained, not replaced with comments claiming provenance. This is a source-semantic comparison, not execution proof.
- Independently checked the three [REDACTED_SECRET_FORM] in B6 census, Jev, and native curation: each asserted header's suffix equals the corresponding literal installed by `monkeypatch.setenv`. All three checks were true. Inspected the local/injected transport or loopback destination as well.
- Decoded the B7 JWT **offline in memory**: header has only HS256 algorithm; payload has only a numeric subject; signature is 32 bytes; raw-value and redact-input occurrences are identical. It is a static specimen in the SHAPES positive-redaction corpus. The added RFC provenance comment is corroborative, not issuer attestation; I did not independently retrieve the RFC or certify nonissuance.
- Independently checked that the three font-role values are CSS custom-property names. Checked the Firecrawl response is an explicitly truncated provider-key placeholder and the bearer example is a provider-prefixed named API-key placeholder. These checks used the actual source, not just the matrix's explanation.

The prior inventory/hash/metadata audit is an input for historical inventory authentication, not work re-claimed here. This pass does not redo the saved-debt/canonical-comment audit, full tests, 23 controls, full mirror-manifest proof, or upstream adaptation provenance owned by the other review lane.

## Semantic evidence keys

All line numbers in the coverage tables are **original finding lines**. Current contextual citations below account for inserted comments/docstrings. `A` means credential-assignment; `B` means bearer-token; `J` means JWT. A listed fingerprint identifies the lexical match, not necessarily a credential value.

### D1: eight exact mirror groups — 16 rows / 30 occurrences

**S01 — Firecrawl documentation: supported, harmless.** `SKILL.md:253-286` describes browser-auth polling responses, saving the resulting key, and the REST header template. The response is a truncated placeholder, not a complete provider key. The header contains a named API-key placeholder with the provider prefix. The source itself references Firecrawl's skills/CLI/workflow repositories; no request, installation or issuer validation was performed. Context establishes documentation examples independently of that attribution.

**S02 — screenshot contrast identifier: supported, harmless.** `screenshot-contrast.mjs:108-170` derives the identifier from a descriptive prefix, `Date.now()` and `Math.random()`. It is passed into `page.evaluate`, written as `data-impeccable-visual-contrast-target`, and removed in cleanup after screenshot capture. `detector/engines/browser/detect-url.mjs:67-78` calls the function with a page, candidate and viewport. This is a DOM annotation identifier, not auth material; cryptographic randomness is not required to support this classification.

**S03 — browser runtime session expressions: supported, harmless for these static matches.** `live-browser.js:19-26` takes TOKEN from the injected window field; `:9578-9594` interpolates it in two localhost design-system fetches. The producer is `live-server.mjs:1272-1276`, which emits the browser prelude from `state.token`; `:2290` initializes that value with `randomUUID()`. None of the three lexical matches contains a repository-embedded credential. This does not certify the server's script-serving, cross-origin or runtime token-exposure properties.

**S04 — completion request field: supported, harmless.** `live-complete.mjs:23-68` reads `readLiveServerInfo(process.cwd())?.info`, sends its token field to a localhost poll endpoint, and otherwise uses the durable session store. The matched object value is `info.token`, not a literal. `impeccable-paths.mjs:64-77,91-95` supplies the runtime JSON record reader/writer. No session file was opened during review.

**S05 — extracted manual-edit rollback route: supported, harmless.** `live/manual-edit-routes.mjs:17-29,253-270` exports a route factory taking `getToken`; the matched expression selects request JSON/query input and compares it with that supplied getter before rollback. It is not a fixed credential. A bounded search of the bundled scripts found the factory export but no in-bundle production caller; the root server retains its own inline route. I do not infer that this extracted route is installed in the root server, or use its guard to certify the root's other routes.

**S06 — poll URL interpolation: supported, harmless.** `live-poll.mjs:120-169` uses a function parameter in status/poll URLs and throws AUTH_FAILED on 401. Its CLI obtains the record through `readLiveServerInfo` (`:27-33,331-332`) and passes `info.token` to stream/one-shot polling (`:361-369`); `runPollOnce`/`runPollStream` pass it to `fetchNextEvent`. These are dynamic values, not literal secrets. URL/logging safety at runtime is excluded.

**S07 — server request/state/output expressions: supported, harmless for these static matches.** At `live-server.mjs:1758-1759`, the match reads request input and compares it to runtime state before rollback. At `:2212-2213`, stop reads the server-info record and interpolates its token. At `:2290`, the server generates `state.token` using imported `randomUUID`; `:2311-2315` binds loopback, serializes that state, and formats startup output. The latter two matches are real runtime credential persistence/output operations, **not** hardcoded repository credentials and **not** certified safe by this disposition. No server was started and no runtime token was inspected.

**S08 — status URL expression: supported, harmless.** `live-status.mjs:10-18,25-26` obtains the server-info record and interpolates its field into localhost status. The producer/record path is the same as S04/S07. This is an expression consuming runtime state, not a credential literal.

### D2: fourteen test modules — 14 rows / 24 occurrences

**S09 — B script fake transport and lambda: supported.** Current `test_b_script.py:17,20-34,46-58` defines an ordinary short test sentinel and supplies it to `GhForge` with `FakeTransport`, which consumes canned responses and records requests. The header assertion uses that same sentinel. Current `:210-250` defines an in-memory `LiveForge`; the second original match is a factory-lambda parameter/body returning `replay`, not a literal. Fixture at original line 15; harmless code at original line 248. The class name LiveForge is not evidence of live network activity.

**S10 — B5 identity sentinel: supported, fixture.** Current `test_b5_identity.py:16,19-37` declares a short local sentinel, builds `Transport` over canned response tuples, and injects it into `GhForge` for `/user` identity behavior. No issuer input or default REST transport supplies the matched value.

**S11 — B6 census [REDACTED_SECRET_FORM]: supported, fixture.** Current `test_b6_census_live.py:208-221` monkeypatches the API base to `local_github.base`, sets a local sentinel in the token environment variable and asserts that the corresponding Authorization header arrived but the sentinel did not enter the census. `LocalGitHub` (`:291-327`) is a `ThreadingHTTPServer` on 127.0.0.1 with canned handlers; its fixture also sets local proxy bypass (`:330-335`). “Live” in the filename means real local HTTP behavior, not a real credential or GitHub call.

**S12 — B7 redaction corpus: supported, fixtures, all five occurrences.** Current `test_b7_scrub.py:27-44` defines SHAPES as triples of label/raw/text. The two original JWT occurrences are identical static specimen and redact-input literals. Offline decoding and corpus placement support synthetic-example classification; minimal claims alone would not prove invalidity, and no such global claim is made. The original password, secret and API-key assignments are hand-written corpus examples; the password repeats a simple word, and the others are short deliberately illustrative strings, not values read from an account, environment or credential file. `:48-51` requires raw removal/fingerprint replacement; `:55-77` propagates the corpus through local closure/census/receipt fixtures and asserts raw absence. The existing redactor remains conservative on these shapes. I did not independently attest the comment's RFC-signature attribution or probe any token.

**S13 — B8 dotted scrub examples: supported, fixtures.** Current `test_b8_census.py:95-98` directly passes three short alphabet/digit dotted/ellipsis assignment examples to `scrub` and asserts their raw contents absent. Adjacent `:101-103` contrasts code-access expressions that must remain unchanged. These findings are positive scrub specimens, not environment-derived credentials; no exemption to the production scrubber is justified by this review.

**S14 — B8 refusal lambda: supported, harmless code.** `test_b8_refusal.py:68-97`, particularly `:81-82`, supplies `forgeFactory=lambda repo, token: steward.forge` to the local close driver. The regex crosses the lambda parameter separator into the returned expression. The returned forge is the offline fixture, not a token string; refusal/settlement assertions follow it.

**S15 — full-e2e factory lambda: supported, harmless code.** `test_e_steward_full_e2e.py:126-143` supplies the same kind of factory lambda returning `self.forge`. Setup (`:170-177`) constructs `FakeGitHub` and `FakeForge`; the autouse fixture (`:43-51`) refuses socket connections, name lookup and URL opener activity. The lexical match is neither the fake's credential nor an actual credential.

**S16 — desk planted finding: supported, fixture reference.** Current `test_desk.py:39-40,180-201` defines module-local synthetic sentinels, places SECRET in untrusted finding fields including the matched snippet f-string, renders the desk and serialized form, and asserts those sentinels do not appear. The matched assignment is interpolation of that sentinel, not an embedded issued key in the snippet. Its provenance is the explicit test setup and negative-output assertions, not merely the new provenance comment.

**S17 — auth store/keyring tests: supported, four fixture occurrences.** Current `test_auth.py:351-370` saves a short store sentinel, installs a distinct environment sentinel, asserts environment precedence, and tests that `public_dict` hides another ordinary short sentinel. `:380-420` defines and injects `_FakeKeyring` and uses the same short fake-keyring sentinel for save/load and deletion. The autouse fixture (`:56-61`) clears auth-related environment variables and disables real keyring by default; `tests/conftest.py:25` isolates GAIA_HOME under tmp_path. The matched values are test inputs to local storage behavior, not an OAuth response or actual keyring read. Both repeated fake-keyring occurrences are retained in coverage.

**S18 — badge reservation comment: supported, harmless prose.** `test_badge_reconcile.py:840-873` creates temporary manifest/registry/reservation paths, obtains a reservation token from the test predispatch result and races two local CLI processes to consume it. Original line 861 is the comment explaining that race; the regex consumes the word following its colon. It is not a credential literal. No claim is made that every subprocess in this test file was executed or broadly audited.

**S19 — native curation transport assertion: supported, fixture.** Current `test_curation_assessment.py:420-437` installs a synthetic API-key sentinel using monkeypatch and defines a local transport asserting its Bearer header. The enclosing test injects that transport into the Jev client for the curation assessment and verifies two locally fabricated responses; it is not a remote provider validation. The asserted header suffix equals the installed environment sentinel, checked independently in memory.

**S20 — malformed authorization envelope: supported, fixture reference.** Current `test_curation_error_contract.py:44,171-186` defines a module sentinel and embeds the SECRET reference into deliberately incomplete JSON in a temporary envelope file. The test patches verification, invokes ratify, expects refusal and asserts the sentinel is absent from stderr. The matched f-string is a malformed-input redaction test, not a credential recovered from an envelope or provider.

**S21 — installability diagnostic [REDACTED_SECRET_FORM]: supported, fixture.** Current `test_installability.py:122-132` feeds a synthetic URL/auth diagnostic plus repeated padding to `sanitize_diagnostic`, checks bounded output and digest shape, and asserts the password, query and [REDACTED_SECRET_FORM] are absent. The original bearer match is a short explicit test string in this input; no external command or provider supplies it. The new provenance-comment match is addressed separately below.

**S22 — Jev mock header assertion: supported, fixture.** Current `test_jev.py:405-448` sets a synthetic API-key sentinel, injects `mock_transport` when constructing `JevClient`, fabricates the response, asserts its header and checks a tmp_path budget result. The bearer suffix equals the monkeypatched sentinel. `live=True` selects the client path under test, but the explicitly supplied transport prevents this from being evidence of a live provider key.

### D3: nine source/workflow/docs rows — 9 rows / 17 occurrences

**S23 — font-role design tokens: supported, harmless.** `docs/samples/registry-3d-fonts.html:154-173` maps body/handle/display font roles to face labels and CSS custom-property names. All three matched RHS strings have the CSS font-variable form. The sample renders role labels using `ROLE_DESC[role].face` (`:247-250`) and canvas typography, not auth headers. The property name token is design vocabulary.

**S24 — historical redaction specification: supported, harmless examples/pattern prose.** `founder/handovers/2026-10-21-steward-issue-hygiene-architecture.md:388-396` enumerates credential pattern grammar, so the first match is the grammar notation. `:515-519` explicitly contrasts short dotted/ellipsis scrub examples with code access. This corresponds to the still-present redactor's dotted-path negative lookahead and B8 positive tests; no historical value is used as authorization input. No history was edited.

**S25 — issue snapshot proposal: supported, harmless prose/placeholders.** Parsed `founder/issues.json` and examined issue **#494**, rather than treating its entire single JSON line as a credential. The first match crosses “signing secret” prose into the proposed claims-object description; the second is a conceptual query placeholder in an acceptance criterion. The body describes a future badge-token signer/renderer, environment-stored signing material, and scope/acceptance criteria. Neither match is an encoded JWT or a secret assignment used by executable code. This finding does not endorse the proposal's broader security claims.

**S26 — release workflow variable reference: supported, harmless for the static finding.** `.github/workflows/sync-artifacts.yml:150-177` sources RELEASE_PAT from `${{ secrets.RELEASE_PAT }}`, checks it for emptiness, then expands it into a tag-push URL. The original match is shell-variable expansion, not PAT bytes. Workflow execution, masking, process arguments, remote URL handling and release authorization are not certified by that distinction. The workflow was not run or changed.

**S27 — budget fetch branch: supported, harmless code.** `scripts/jev_ci_budget.py:370-390` tries gh first, then branches on the token parameter and returns `fetch_workflow_runs_http`. The regex spans the branch colon/newline into `return`. The HTTP helper (`:346-360`) formats a Bearer header from its parameter; `main` supplies `args.token` (`:460`). There is no literal value at the finding site.

**S28 — suite-title predicate docstring: supported, harmless prose.** `scripts/upstream_watcher/live.py:464-466` describes whole-token title matching and contrasting suite-name examples. The implementation escapes the suite key in a boundary regex. `canonical_umbrellas` calls it (`:489`) to classify an otherwise unparsed title. The prose word token is not an authentication field. This file was read-only; future source edits require a refreshed source-bound assessment.

**S29 — authentication runtime values/branches: supported, all four harmless static matches.** `src/gaia_cli/auth.py:231-242` gets a token from an injected OAuth HTTP response and branches before returning it; the first lexical match spans that branch. `:395-407` copies `creds.token` to the file-backend record when keyring does not hold it. `:416-436` constructs credentials from the environment override and branches on absence of stored/keyring data. `_env_token` (`:363-368`) reads the declared environment variable names, and `Credentials.public_dict` (`:340-342`) omits token. `TokenStore` is used by CLI identity/store consumers and the isolated tests in S17. Neither runtime copying/storage nor the two branch matches embeds a repository credential. Runtime storage permissions and OAuth flow safety are not comprehensively certified here.

**S30 — Jev missing-key branch: supported, harmless code.** `src/gaia_cli/jev.py:626-643` returns in offline mode, reads the key from TYPESAFE_API_KEY, then branches on missing key before budget reservation/transport. The lexical match spans that branch into `return`. `curation/assessment.py:138-146` consumes `client.evaluate`; the S19/S22 injected-transport tests exercise the relevant parameter path. No literal key is at this source site, and no model/provider call was made in this review.

**S31 — detector rule label: supported, harmless code.** `src/gaia_cli/securityScanner.py:503-514` iterates detector patterns and constructs a Finding with a rule-name f-string; the matched value is label construction, not credential material. Production composition runs through `scanSkillContent`, `scanNamedSkillFiles` (`:605-621`) and `push.py:473`; positive detector tests are callers too. The label is not an allowlist entry, credential decoder or authorization input. This review did not alter or weaken a detector pattern.

## Exact coverage tables

Each row below is supported by its independent semantic evidence key above. Both IDs of every D1 mirror pair are explicit. Original line/fingerprint entries describe occurrences, so duplicated fingerprints remain separate. No additional current-only match is counted toward the original 71.

### D1 — exact mirror-group table

| Evidence / result | Paths and exact debt IDs | Original occurrences per path | Rows / matches |
|---|---|---|---|
| S01 — supported harmless | `.agents/skills/firecrawl/SKILL.md` — `debt:credential_leak:agents-skills-firecrawl-skill-md:dd0fc386f410185b`<br>`.claude/skills/firecrawl/SKILL.md` — `debt:credential_leak:claude-skills-firecrawl-skill-md:54ae5604e12e2a9b` | A 256 `764a6efd41a6`; B 286 `7786f66c14fb` | 2 / 4 |
| S02 — supported harmless | `.agents/skills/impeccable/scripts/detector/engines/visual/screenshot-contrast.mjs` — `debt:credential_leak:agents-skills-impeccable-scripts-detector-engine:7c8824c086679135`<br>`.claude/skills/impeccable/scripts/detector/engines/visual/screenshot-contrast.mjs` — `debt:credential_leak:claude-skills-impeccable-scripts-detector-engine:1deecfb89c8de90c` | A 117 `799f18baed47` | 2 / 2 |
| S03 — supported harmless | `.agents/skills/impeccable/scripts/live-browser.js` — `debt:credential_leak:agents-skills-impeccable-scripts-live-browser-js:5f45d00d7f30b9c6`<br>`.claude/skills/impeccable/scripts/live-browser.js` — `debt:credential_leak:claude-skills-impeccable-scripts-live-browser-js:4560dad03a613faa` | A 22 `a75f704f9b05`; A 9584 `0f5b4a4bcda5`; A 9585 `0f5b4a4bcda5` | 2 / 6 |
| S04 — supported harmless | `.agents/skills/impeccable/scripts/live-complete.mjs` — `debt:credential_leak:agents-skills-impeccable-scripts-live-complete-m:0b64558129c498be`<br>`.claude/skills/impeccable/scripts/live-complete.mjs` — `debt:credential_leak:claude-skills-impeccable-scripts-live-complete-m:d8222ce8d9bd957f` | A 63 `db2e24d57724` | 2 / 2 |
| S05 — supported harmless | `.agents/skills/impeccable/scripts/live/manual-edit-routes.mjs` — `debt:credential_leak:agents-skills-impeccable-scripts-live-manual-edi:a972d25ee1973c95`<br>`.claude/skills/impeccable/scripts/live/manual-edit-routes.mjs` — `debt:credential_leak:claude-skills-impeccable-scripts-live-manual-edi:0801364f7f0e77a3` | A 261 `ef9ae85da1c4` | 2 / 2 |
| S06 — supported harmless | `.agents/skills/impeccable/scripts/live-poll.mjs` — `debt:credential_leak:agents-skills-impeccable-scripts-live-poll-mjs:bd8dca1fcdf7945b`<br>`.claude/skills/impeccable/scripts/live-poll.mjs` — `debt:credential_leak:claude-skills-impeccable-scripts-live-poll-mjs:f8f331ec1404ea92` | A 121 `7b132df01592`; A 160 `0fdcab4106d5` | 2 / 4 |
| S07 — supported harmless | `.agents/skills/impeccable/scripts/live-server.mjs` — `debt:credential_leak:agents-skills-impeccable-scripts-live-server-mjs:a671be5f79c2a3ff`<br>`.claude/skills/impeccable/scripts/live-server.mjs` — `debt:credential_leak:claude-skills-impeccable-scripts-live-server-mjs:4df9c2b6ff80b3e6` | A 1758 `ef9ae85da1c4`; A 2213 `e24e481c36cb`; A 2312 `e91023eb493e`; A 2315 `d82b1fd22cbe` | 2 / 8 |
| S08 — supported harmless | `.agents/skills/impeccable/scripts/live-status.mjs` — `debt:credential_leak:agents-skills-impeccable-scripts-live-status-mjs:f32377b5380cfa3e`<br>`.claude/skills/impeccable/scripts/live-status.mjs` — `debt:credential_leak:claude-skills-impeccable-scripts-live-status-mjs:04765e48ffb67e0b` | A 17 `e24e481c36cb` | 2 / 2 |
| **D1 total** | **8 independently byte-checked exact mirror pairs** | | **16 / 30** |

### D2 — individual rows

| Evidence / result | Source and exact debt ID | Original occurrences | Matches |
|---|---|---|---|
| S09 — supported fixture + harmless code | `tests/steward/issuehygiene/test_b_script.py` — `debt:credential_leak:tests-steward-issuehygiene-test-b-script-py:82d92c373e57e5b6` | A 15 `7eb3777115fa` (fixture); A 248 `7c6791c527dc` (code) | 2 |
| S10 — supported fixture | `tests/steward/issuehygiene/test_b5_identity.py` — `debt:credential_leak:tests-steward-issuehygiene-test-b5-identity-py:affc47d215e53abe` | A 15 `9210a2236f68` | 1 |
| S11 — supported fixture | `tests/steward/issuehygiene/test_b6_census_live.py` — `debt:credential_leak:tests-steward-issuehygiene-test-b6-census-live-p:ec37ccfcb574c2d1` | B 219 `70901d36b258` | 1 |
| S12 — supported fixtures | `tests/steward/issuehygiene/test_b7_scrub.py` — `debt:credential_leak:tests-steward-issuehygiene-test-b7-scrub-py:c82313badc903f74` | J 31 `59b647a4197a`; J 32 `59b647a4197a`; A 34 `100512181d07`; A 35 `5b349ee29dd2`; A 37 `4c46513008e3` | 5 |
| S13 — supported fixtures | `tests/steward/issuehygiene/test_b8_census.py` — `debt:credential_leak:tests-steward-issuehygiene-test-b8-census-py:055f6db7f83bf7eb` | A 94 `88b11cd7d986`; A 95 `817d1450133f`; A 96 `529e66593269` | 3 |
| S14 — supported harmless code | `tests/steward/issuehygiene/test_b8_refusal.py` — `debt:credential_leak:tests-steward-issuehygiene-test-b8-refusal-py:100e8e97ff9a51ef` | A 82 `2198f003c5b0` | 1 |
| S15 — supported harmless code | `tests/steward/issuehygiene/test_e_steward_full_e2e.py` — `debt:credential_leak:tests-steward-issuehygiene-test-e-steward-full-e:8dd6930a15057584` | A 135 `e8ea09ffe951` | 1 |
| S16 — supported fixture reference | `tests/steward/test_desk.py` — `debt:credential_leak:tests-steward-test-desk-py:d1900b51970bdc61` | A 187 `08109091b0eb` | 1 |
| S17 — supported fixtures | `tests/test_auth.py` — `debt:credential_leak:tests-test-auth-py:edc1563abdfa70e4` | A 351 `7105abe1b034`; A 366 `4c7ad6353034`; A 404 `0095a8f1708e`; A 418 `0095a8f1708e` | 4 |
| S18 — supported harmless prose | `tests/test_badge_reconcile.py` — `debt:credential_leak:tests-test-badge-reconcile-py:062a191c5b535bb7` | A 861 `a3522810e912` | 1 |
| S19 — supported fixture | `tests/test_curation_assessment.py` — `debt:credential_leak:tests-test-curation-assessment-py:b8c7a3d24c6492cf` | B 433 `5a3ec2abc81e` | 1 |
| S20 — supported fixture reference | `tests/test_curation_error_contract.py` — `debt:credential_leak:tests-test-curation-error-contract-py:30a58d0ac04e28de` | A 175 `5d47666b7611` | 1 |
| S21 — supported fixture | `tests/test_installability.py` — `debt:credential_leak:tests-test-installability-py:50a878d42ae01243` | B 125 `4d631a121aac` | 1 |
| S22 — supported fixture | `tests/test_jev.py` — `debt:credential_leak:tests-test-jev-py:29db1b7469907462` | B 438 `be6e8e2fecc9` | 1 |
| **D2 total** | **14 rows** | | **24** |

### D3 — individual rows

| Evidence / result | Source and exact debt ID | Original occurrences | Matches |
|---|---|---|---|
| S23 — supported harmless design values | `docs/samples/registry-3d-fonts.html` — `debt:credential_leak:docs-samples-registry-3d-fonts-html:412fc74a40db779e` | A 160 `3751653efd6c`; A 161 `13e1b3d950fb`; A 162 `493df6923d8a` | 3 |
| S24 — supported harmless pattern/examples | `founder/handovers/2026-10-21-steward-issue-hygiene-architecture.md` — `debt:credential_leak:founder-handovers-2026-10-21-steward-issue-hygie:e8be47c2eebc4b65` | A 392 `fbb4c62d3ac3`; A 517 `684ec27b63dc`; A 518 `a261e68349db` | 3 |
| S25 — supported harmless proposal prose | `founder/issues.json` — `debt:credential_leak:founder-issues-json:b132c45b86c3ebcb` | A 1 `821389db4920`; A 1 `b668ec33907d` | 2 |
| S26 — supported harmless shell expression | `.github/workflows/sync-artifacts.yml` — `debt:credential_leak:github-workflows-sync-artifacts-yml:b526f075e4ecd1e6` | A 177 `41e3de627921` | 1 |
| S27 — supported harmless branch | `scripts/jev_ci_budget.py` — `debt:credential_leak:scripts-jev-ci-budget-py:86888e095876410e` | A 387 `98d5d12ef43f` | 1 |
| S28 — supported harmless docstring | `scripts/upstream_watcher/live.py` — `debt:credential_leak:scripts-upstream-watcher-live-py:2393fe51171e5834` | A 465 `39be36177943` | 1 |
| S29 — supported harmless runtime expressions/branches | `src/gaia_cli/auth.py` — `debt:credential_leak:src-gaia-cli-auth-py:2ed435a394e19f87` | A 241 `caf47aa7ff21`; A 405 `be3a74739ccb`; A 420 `114fc3873c35`; A 436 `caf47aa7ff21` | 4 |
| S30 — supported harmless branch | `src/gaia_cli/jev.py` — `debt:credential_leak:src-gaia-cli-jev-py:74fbb7100ac456ad` | A 634 `b17e86ead565` | 1 |
| S31 — supported harmless detector label | `src/gaia_cli/securityScanner.py` — `debt:credential_leak:src-gaia-cli-securityscanner-py:ba7fcb08fe3ef5c9` | A 513 `fc84c742aab2` | 1 |
| **D3 total** | **9 rows** | | **17** |

## Actionable observation outside the original 71

**Low severity, evidence hygiene — reword the new comment at `tests/test_installability.py:123`.** Its URL/[REDACTED_SECRET_FORM] wording creates an additional bearer-token lexical match (fingerprint `e77a4a61964d`). Inspection shows ordinary comment prose, not a credential exposure. Prefer wording such as “Synthetic authentication diagnostic examples exercise positive redaction.” Do not add a scanner exception or change the original positive specimen/assertions. This is the independently disclosed current-72-versus-original-71 issue, not a new original disposition, and does not invalidate the bounded semantic classifications above. No implementation was performed.

## Reproduction details and limits

The read-only offline checks used `PYTHONPATH=src python - <<'PY'` snippets with these operations:

```python
# Mirror equality, using actual source bytes rather than row hashes.
original = subprocess.check_output(['git', 'show', base + ':' + canonical])
originalMirror = subprocess.check_output(['git', 'show', base + ':' + mirror])
assert original == originalMirror
assert Path(canonical).read_bytes() == Path(mirror).read_bytes()
assert original == Path(canonical).read_bytes()

# Retained fixture semantics; compare AST, then exclude docstrings where needed.
assert ast.dump(stripDocstrings(ast.parse(before))) == ast.dump(
    stripDocstrings(ast.parse(after)))

# Locate reviewed occurrences without printing their values.
for name, pattern in CREDENTIAL_PATTERNS:
    for match in pattern.finditer(source):
        if (name, fingerprint(match.group())) in reviewedPatternFingerprints:
            line = source.count('\n', 0, match.start()) + 1
            # Printed context only after scrub and/or string-token masking.
```

Here `stripDocstrings` is the local in-memory AST walk described above, not a repository helper added by this review. The mirror checks were executed for all eight groups; the AST comparison for all fourteen D2 modules. Match-location inspection was scoped by the matrix fingerprints, but the semantic conclusions were drawn from the actual containing functions, fixture construction, producers and consumers documented above.

Tool limitations were not hidden as successful checks: local `rg` failed with `/data/data/com.termux/files/usr/bin/rg: cannot execute binary file: Exec format error`; bounded Python source enumeration supplied the needed symbol references. A read of the guessed `live-state-paths.mjs` path returned ENOENT; the actual import was `impeccable-paths.mjs` and was inspected. Another exploratory snippet ended with `FileNotFoundError: [Errno 2] No such file or directory: 'src/gaia_cli/jev_advisory.py'`; that guessed path is not used as evidence for any row. These were local lookup/tool errors, not a model-route substitution or unresolved row.

No tests, scanner controls, canonical scans, ledger runs, issuer contacts, external validity probes, live sessions, releases, forge/GitHub writes, installs, configuration changes, source edits or policy changes were performed by this reviewer. The separate 23-control/full-mirror/runtime-provenance slice remains pending here and must be combined by the parent. The earlier focused test receipts remain prior-review evidence only. No full-mission, integration, activation, rotation or closure acceptance is claimed.
