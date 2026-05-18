## 2026-05-18 - [Optimize JSON schema validation]
**Learning:** Re-instantiating `jsonschema.validate` in a loop is extremely slow because it re-parses the schema every time.
**Action:** When validating many JSON items (like iterating through lists of skills or edges), always compile the schema validator outside the loop using `jsonschema.validators.validator_for(schema)(schema)` and reuse the `validator.validate()` instance.
