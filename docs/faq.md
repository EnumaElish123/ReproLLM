# FAQ

## The model I use is gated; lock says `hf_api_forbidden`

Gated repositories require model-author approval for your Hugging Face
account, plus a token permitted to read that repository. Logging in or setting
`HF_TOKEN` alone does not grant access; a valid token can still receive 403.
After approval, set `HF_TOKEN` in your shell and run `reprollm lock` again.
ReproLLM uses the token for requests without writing it into its artifacts.
Without access, the affected metadata stays `unresolved`; check the recorded
HTTP error and repository permissions before retrying.

## I'm on a GPU node without internet. Can I still use lock?

Run `reprollm lock .` on the machine with network access to resolve remote
metadata. Transfer the matching manifest, lock, declared input files and
separately prepared model/data resources to the GPU node. `reprollm lock .
--check` checks manifest/project-rule freshness without network access;
`reprollm audit .` checks the available evidence there.

If no online machine is available, `reprollm lock . --offline` hashes local
inputs and records declared values without fetching remote metadata.
Unresolved revisions stay unresolved. Offline mode writes a new lock; it does
not reuse remote resolutions from a previous lock or download model weights.

## Why is my API model a WARNING? I pinned the version!

A dated snapshot alias such as `gpt-4o-2024-08-06` produces an INFO finding
for `model.revision_pinned`; a bare mutable alias such as `gpt-4o` produces a
WARNING. Check the finding's rule ID and the lock's `models.<role>.pinnability`
to identify the cause. Neither alias is an immutable model artifact, and a
dated label cannot establish access to the provider's weights.

## Should I commit `.reprollm/runs/`?

Keep the records for runs your paper reports; `diff` and `export` consume them.
Run directories can also contain input snapshots and captured logs, so inspect
their contents and size before sharing them. Follow your project's storage
and access policy when choosing which records to commit or archive.

## Why does audit show Findings FAIL but exit 0?

`Findings` describes the unresolved CRITICAL and WARNING findings. `Result`
shows the actual exit code and the effective `--fail-on` threshold, including
`.reprollm/config.yaml` settings. The default `critical` threshold exits 0
when only warnings remain; `--fail-on warning` makes those warnings exit 1.
`--fail-on never` disables finding-based failure and still shows every issue.

## How do I see every repeated warning?

The default text report groups failing warnings with the same rule ID and
fix hint. Each group gives the full count, up to three examples with evidence,
and one shared fix. Run `reprollm audit --details` for every individual finding.
`--format json` and `--format github` always retain every finding they report;
text grouping does not change the summary, severity, or exit code.

## How do I silence a rule I disagree with?

`.reprollm/config.yaml`:

```yaml
audit:
  ignore:
    - {rule: code.no_untracked, reason: "generated notebooks"}
```

A reason is mandatory; suppressed findings still appear, marked `suppressed`.

## How do I write a custom profile?

Copy a built-in from `src/reprollm/profiles/` into `.reprollm/profiles/`,
adjust `rules`/`severity_overrides`/`detect`, and declare it in
`experiment.profiles`. Run `reprollm profiles show <name>` to verify the
inheritance chain.

## Does ReproLLM work on Windows?

Core commands (audit, init, lock, export, diff) are tested on Windows in CI.
`run` records the child but GPU/SLURM capture is Linux-first; you get a clear
"unavailable" marker rather than a crash.

## What exactly does `discover` send?

Run `reprollm discover --experimental --dry-run` to see the exact file list and byte counts
before anything is sent. README files, top-level configs, argparse/dataclass
snippets, and the file tree — never secret-pattern files, `data/`,
`checkpoints/`, or anything where redaction triggers (those are dropped and
listed). A live request requires experimental opt-in and either interactive confirmation
or `--yes`. Dry-run sends no model request.

## Why does the lock hash not match my file after I edit it?

That is `consistency.file_hashes` doing its job: the lock recorded what the
file was at lock time. Re-run `reprollm lock` after intentional edits.

## Can I track a parameter ReproLLM doesn't know about?

Yes — add a project rule or accept a discovered candidate:

```bash
reprollm rules add --field custom.my_method.alpha --severity CRITICAL --reason "…"
```

The accepted field is then checked deterministically like a built-in.

## Does export include the audit?

Yes — `reprollm export` runs an audit at export time and embeds its summary
and all CRITICAL/WARNING messages, plus every known limitation (unresolved
revisions, unpinnable models, …) so reviewers see the honest state.

## How fast is audit on a huge repository?

A 20,000-file repository audits in under 10 seconds (nightly performance
gate). Python AST scanning caps at 500 files with a visible `-v` diagnostic.

## Will a newer schema break my committed files?

Readers reject unknown newer `schema_version` with a clear upgrade message.
Pre-1.0 breaking changes only happen at minor bumps with a CHANGELOG
migration note.
