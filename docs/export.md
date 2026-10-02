# Exporting REPRODUCIBILITY.md

`reprollm export` turns your manifest, lockfile, and run records into a single
`REPRODUCIBILITY.md` you can commit with your paper artifact (spec §19).

## What it contains

Sections render in a fixed order: experiment identity (models with
revision/pinnability/tokenizer/chat-template, datasets with fingerprint status,
prompts with digests, generation/inference/training parameters), code state,
environment, hardware, execution, an audit run at export time embedded
verbatim, and known limitations (every unresolved, `unpinnable`, or
`not_computed` value plus binding caveats).

On `main` (unreleased), the default report also includes Evaluation, Judge and
Privacy details when present: metric implementations and hashes, aggregation,
repetitions, judge parameters and parser, threat model, privacy mechanism and
attack settings. Model, dataset and prompt details include declared dtype,
quantization, adapters, splits, preprocessing and few-shot settings.

Evidence labels distinguish declarations, locked values and runtime observations.
A run record does not prove that every declared field was observed. When exporting
an older run, experiment details use that run's own available snapshots and
observations. The separately labelled audit summary still checks the current
working tree, current declarations/lock and latest valid run when applicable.
It is not a new validation of the selected historical run.

## Usage

```console
$ reprollm export                    # latest run → REPRODUCIBILITY.md
$ reprollm export --run 20260927T04  # unique run prefix
$ reprollm export --output docs/REPRODUCIBILITY.md
```

Degradation is explicit: with no run record the Execution section says so and
points at `reprollm run`; with no lock the identity tables mark revisions
`not locked`. Output is deterministic for identical inputs — the template
carries no wall clock, only recorded run/lock timestamps. The exported file
itself makes the tree dirty, so a second export embeds that honestly in its
audit summary; delete the artifact between byte-identical comparisons.

Hashes display 12 leading characters. The document passes secret redaction
before it is written; no absolute paths, hostnames, or usernames appear.

Free-form values are checked before serialization and rendered as literal text,
so embedded Markdown links, images or HTML cannot impersonate report evidence.
Displayed command code spans preserve their literal text for copying.
