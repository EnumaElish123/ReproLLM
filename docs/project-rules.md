# Project rules

Project rules are repository-specific requirements you accept once and then
have checked deterministically (spec §7; "LLM discovers. Rules decide.").

## Adding rules

```console
$ reprollm rules add --field custom.privacy_method.alpha --severity CRITICAL \
    --reason "controls noise scale" \
    --config configs/privacy.yaml:method.alpha
$ reprollm rules list
```

Rules live in `.reprollm/project-rules.yaml` (only `reprollm rules` writes
it). Each rule fails when its field is missing or null in `reprollm.yaml`,
with your `--reason` quoted in the fix hint. IDs default to
`project.<last-segment>`; duplicates get `_2` suffixes, or pass `--id`.

## Bindings and consistency

`--cli FLAG`, `--config path:dotted.key`, and `--env VAR` declare where the
field's value lives at runtime. `reprollm run` observes every declared
location; at Level 2, `consistency.custom_fields` compares each observed value
against the manifest declaration — a mismatch is CRITICAL with both values and
sources in the evidence.

Note the boundary: editing a config file *after* a run is file drift
(`consistency.file_hashes`); a value conflict exists when the run observed
something different from what the manifest declares.

## Lock freshness

`reprollm.lock` records `project_rules_sha256`. Accepting a new rule after
locking makes `consistency.lock_fresh` fail until you run `reprollm lock`
again — `rules add` reminds you of this.
