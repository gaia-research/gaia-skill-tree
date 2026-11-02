# Synthetic unadopted-schema fixtures

These files are exact copies of the pre-adoption schemas from
`origin/dev/yggdrasil-iv` at `f70b55e62b39308a9b1dd78c0b52849d6df19216`:

- `registry/schema/namedSkill.schema.json`
  (`da6336663c3fbe8f66c924261e2ef945d9972838522692e659cf50d4a49f1329`)
- `registry/schema/skillTree.schema.json`
  (`678a2fd8d810002fb5bd57adc1b2984f4ec57314ccbd3658c4f0d70c25df9ed0`)

They deliberately omit the canonical lifecycle evidence fields and typed timeline
linkage. Tests install them only into repositories marked
`DISPOSABLE_CANONICAL_FIXTURE` to prove the production workflow refuses an
unadopted schema before validating staged output or writing targets/journals.

The normal disposable fixture starts from the current adopted production schema
bytes. That separate path proves adopted-schema validation still does not grant
an issuer approval, and that a genuinely invalid staged result produces the
separate `invalid staged output` refusal.
