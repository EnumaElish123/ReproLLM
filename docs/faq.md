# FAQ

## The model I use is gated; lock says `hf_api_forbidden`

Gated repositories reject anonymous metadata requests. Export your
`HF_TOKEN`, run `reprollm lock` again, and the token is used for the request
but never written to any file. If you cannot provide a token, the field stays
`unresolved` — honestly, rather than guessed.

## I'm on a GPU node without internet. Can I still use lock?

Run `reprollm lock --offline` on the machine with network access, commit the
`reprollm.lock`, and audit on the GPU node. Offline mode records declared
values with `confidence: declared`; nothing is invented.

## Why is my API model a WARNING? I pinned the version!

You pinned a *snapshot alias* (`gpt-4o-2024-08-06`). The provider can still
change what that alias serves. ReproLLM records it as `snapshot_alias`
pinnability — better than a bare alias, not an immutable artifact. The
finding is informational about the platform's limits, not about your manifest.

## Should I commit `.reprollm/runs/`?

They are small and text-only by design. Commit at least the run(s) your paper
reports; that is what `diff` and `export` consume. Add the rest if you want
full history.

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

Run `reprollm discover --dry-run` to see the exact file list and byte counts
before anything is sent. README files, top-level configs, argparse/dataclass
snippets, and the file tree — never secret-pattern files, `data/`,
`checkpoints/`, or anything where redaction triggers (those are dropped and
listed). Nothing is sent without `--yes`.

## Why does the lock hash not match my file after I edit it?

That is `consistency.file_hashes` doing its job: the lock recorded what the
file was at lock time. Re-run `reprollm lock` after intentional edits.

## Can I track a parameter ReproLLM doesn't know about?

Yes — project rules. `reprollm rules add --field custom.my_method.alpha
--severity CRITICAL --reason "…"` or accept a discovered candidate. From then
on it is checked deterministically like any built-in.

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
