# dev-ingest-named — trigger prompts

Used to check that realistic requests select this playbook, and that near misses
do not. Not a skill entry point: this file is a reference asset only.

## Should select dev-ingest-named

- "Intake #2452 has topology and evidence approved and the promotion PR is open. Land the generic, the named skill and the evidence rows."
- "Run the ingest for the evidence-approved batch: create the new fusion generic from the L4 decision, then add the named skill and its verified rows."
- "The L4 ruling made a new generic for this skill. Add it with its prerequisites, add the named implementation, ingest the manifest and appraise it, but don't calibrate yet."
- "Turn the reviewed evidence manifest for this single-skill intake into CLI-written rows and tell me the Trust Magnitude."

## Should not select it (use the named alternative)

- "Fuse all of obra's named skills into a suite capstone." → gaia-fuse-full-suite
- "Set leonxlnx/cook to 3★ based on its Trust Magnitude." → dev-calibrate
- "Add this skill; it maps to the existing design-generation generic." → `gaia dev add --named` directly (generic exists, this playbook stops with GENERIC_EXISTS)
- "Find new evidence for this skill." → ev-discovery / ev-pipeline
- "Is this a new generic or a duplicate?" → gaia-curate (topology is an L4 decision, not an ingest)
- "Open the promotion PR and stage the generated docs." → gaia-review-meta-close
