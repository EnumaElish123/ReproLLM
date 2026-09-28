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
