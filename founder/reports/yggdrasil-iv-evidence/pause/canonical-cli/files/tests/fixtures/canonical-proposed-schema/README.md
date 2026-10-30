# Proposed schema fixtures — NOT ADOPTED

These two files are exact copies from the held proposal commit
`bf9097b7a2414aeb47e34c7fcfb2d067df50199c`, paths
`registry/schema/namedSkill.schema.json` and `registry/schema/skillTree.schema.json`.

- namedSkill SHA256: `a74301da361b0ba2055920316a1b473a8f39575854feb1bcc183f32ef370e63c`
- skillTree SHA256: `8aa373fb4bc253d049bf235ae15ae8873f731f7b2dd69750290402e723cb0272`

They are installed ONLY into test-created repositories bearing
`DISPOSABLE_CANONICAL_FIXTURE`. The real native validator reads those actual
schema files; their exact bytes are bound into the workflow input context.
There is no schemaPolicy monkeypatch, permissive lifecycle-field overlay or
production fixture-provider switch.

Negative tests explicitly restore the actual unadopted production schema bytes
and verify native validation/apply refuse them. Positive proposed-schema
validation still does not grant an approval: the production issuer remains
unavailable. Successful apply/recovery tests use a clearly labelled test-only
trusted-port replacement in a separate disposable interpreter.

These fixtures are test contracts, not canonical schema adoption. The two Core
Maintainer approvals and separate founder rollout gate remain held. Existing
legacy raw-schema failures are not removed or weakened by these fixtures.
