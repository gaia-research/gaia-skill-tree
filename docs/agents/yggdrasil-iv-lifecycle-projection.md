# Yggdrasil IV lifecycle projection: partial source boundary

This is an engineering checkpoint, not an active public producer. The Explorer
panel remains disabled. `gaia_cli.lifecycleProjection.project_challenges` accepts
a trusted in-process complete challenge source and the existing trusted
`VerificationReceiptResolver`. Neither is configured by default. `None` means
unavailable, not a verified empty collection. An empty tuple is meaningful only
when the trusted source explicitly returns a complete set. A malformed,
foreign, duplicate, or receipt-invalid challenge makes the whole projection
unavailable. The returned domain challenges retain their immutable histories.
The contested bit is derived from all unresolved material challenges; it does
not alter Origin or any numerical value.

## Required next boundary

A separately trusted canonical-consequence source must supply the approved
published consequence for the exact subject and coherent publication snapshot,
including the existing numerical standing and Origin ownership, with its own
validated provenance and history. The caller must explicitly configure this
source alongside the challenge source and receipt resolver. An identifier,
digest, HTTPS URL, approval name, boolean, or raw contributor JSON cannot
serve as that source. Source unavailability must not be represented as an
empty collection or as approval. Technical closure alone cannot restore
standing, rank, or Origin. The specific issuer and canonical consequence types
are deliberately not invented here; coordinate the adapter with Sol's canonical
transaction and history work.

Before connecting this to the named index or API serializer, reconcile it with
the actual publication source and add cross-surface parity tests. Contributor
frontmatter must never pass a `trustLifecycle` field through as trusted output.
The current checkpoint does not implement that boundary, serializer, API
wiring, or browser consumption. It is not acceptable to re-enable the dormant
renderer merely because a payload has the expected shape.

Native route for later evidence: `docs/named/index.html` loads
`named-skills.js`, `trust-lifecycle.js` and `skill-explorer.js`; `openExplorer`
mounts at `#se-tm`. Capture this actual panel at desktop, 390px and 320px and a
keyboard-focus state, labeling any synthetic data. DOM tests do not replace
rendered captures or founder approval.
