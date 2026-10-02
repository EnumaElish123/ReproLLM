# Discover (experimental)

**Privacy first.** `reprollm discover` is the only command that sends repository
content to an LLM endpoint, and only when *you* opt in: it requires
`--experimental` (or `discover.enabled: true` in `.reprollm/config.yaml`), shows
you the **exact file list** before anything is sent, and needs `--yes` (or an
interactive confirmation) to proceed. The endpoint is yours to choose via
`REPROLLM_LLM_BASE_URL` / `REPROLLM_LLM_API_KEY` / `REPROLLM_LLM_MODEL`.

## What is sent — and never sent

Sent: `README*`, top-level YAML/JSON/TOML configs (≤ 64 KiB each), source
snippets of `argparse.add_argument(...)` and `@dataclass`/hydra config classes,
and the repository tree (≤ 2000 entries) — within a character budget
(`discover.max_chars`, default 60 000).

Never sent: secret-bearing files (§16.4 patterns), any file where secret-value
redaction triggers (such files are dropped whole and listed), `data/`,
`datasets/`, `checkpoints/`, `outputs/`, `wandb/`, lockfiles, binaries, and
anything oversized. All included text still passes value redaction first.

## Usage

```console
$ reprollm discover . --experimental --dry-run   # see the payload, send nothing
$ reprollm discover . --experimental --dry-run --show-content  # full system/user messages
$ reprollm discover . --experimental --yes       # one temperature-0 request
$ reprollm rules list                           # active rules, candidates and archives
$ reprollm rules show c-3f9a1b                   # inspect before accepting
$ reprollm rules accept c-3f9a1b                 # → project rule
$ reprollm rules ignore c-42b0c9 --reason "Outside this experiment"
```

The model responds with JSON only. Invalid JSON is retried once with the parse
error appended; a second failure saves the raw response under
`.reprollm/discover/` and exits 3.

## Candidates are not decisions

Discovery only proposes. A candidate becomes a checked rule through your
explicit `rules accept`; its evidence paths are verified against the actual
payload, and anything citing files you never sent is demoted to `low`
confidence. `--paper` (paper–code consistency) is rejected in Beta.

`rules list` shows active rules, the latest discovery's candidates and saved
recovery copies. Candidate labels are `accepted`, `ignored` or `pending`; an
active accepted rule takes precedence over an earlier ignored record.
`rules list --json` keeps its active-rule array format. Use
`rules list --candidates --json` for complete candidate objects with their current
status and relative discovery-file source. Candidates are sorted by ID; if there
is no discovery file, this view returns `[]`.

Review a candidate's rationale, evidence, confidence, suggested field and bindings
before accepting it:

```console
$ reprollm rules list --candidates
$ reprollm rules show c-3f9a1b
$ reprollm rules accept c-3f9a1b
$ reprollm rules show project.alpha
$ reprollm lock
```

IDs in these examples are illustrative; use those shown by your own `rules list`.
`rules show` prints the complete record and its relative source without changing
files. Candidate inspection uses only the latest discovery file, not older files
containing the same ID. A malformed latest file produces an error. Accepted rules
retain their candidate ID, reason, approval time and bindings in
`.reprollm/project-rules.yaml`; `show` also works for manually added rules.

Repeated acceptance of an active candidate is an error. `rules ignore` applies to
inactive candidates; trying to ignore an accepted candidate reports its active
rule and directs you to `rules remove`. Accepting a previously ignored candidate
is allowed and makes its displayed status `accepted`.

Output quality varies with the model; treat candidates as review input, not
verdicts — "LLM discovers. Rules decide."

## Remove and restore a project rule

Remove an active rule with a reason, then refresh the lock:

```console
$ reprollm rules remove project.alpha --reason "This experiment no longer uses alpha"
$ reprollm rules list
$ reprollm rules show ra-0123456789abcdef
$ reprollm lock
```

Replace `ra-0123456789abcdef` with the archive ID printed by `remove` or `list`.
Removal first saves the complete rule under
`.reprollm/rule-archives/<archive_id>.json`, then removes its entry from the active
rules file. Only active entries enforce checks. The removal reason is stored
separately from the rule's original reason.

A saved archive is an immutable **recovery copy**, not proof that removal
completed. `rules show ARCHIVE_ID` reports a state derived from the current active
rules:

- `inactive`: neither the archived rule ID nor its candidate ID is active.
- `active-identical`: the original rule is still active unchanged.
- `conflict`: an active rule with the same rule ID or candidate ID differs.

If saving succeeds but updating the active file fails, the command exits 2 and
reports the retained archive ID and that the rule was not removed by this command.
Inspect `rules list` and `rules show ARCHIVE_ID` before retrying. Do not infer that
the rule is inactive from the existence of an archive.

Restore an inactive rule using its saved archive:

```console
$ reprollm rules show ra-0123456789abcdef
$ reprollm rules restore ra-0123456789abcdef
$ reprollm rules show project.alpha
$ reprollm lock
```

Restoration preserves the original ID, field, severity, reason, `source`, candidate
ID, `accepted_at` and bindings. It does not require the old discovery file and does
not delete or rewrite the archive. Any active rule with the same rule ID or
candidate ID blocks restoration, even if it is identical. Inspect and resolve the
active rule explicitly; restoration never overwrites it. Run `reprollm lock` after
successful removal or restoration because the project-rules hash has changed.

The commands reject malformed archives, content-ID mismatches and symbolic links
in their owned paths. A newer archive schema asks you to upgrade. Archives and
restored rules must pass privacy checks: secrets, absolute paths, hostnames or
usernames cause an error instead of silently changing the original recovery copy.
`rules show` and `rules list --candidates` redact sensitive variable text in their
output.

Serialize rule changes. Removal and restoration compare the active file with the
bytes they originally read before replacing it, and refuse a detected edit,
deletion or read failure. This is best-effort conflict detection, not an atomic
compare-and-swap guarantee; concurrent writers still require coordination.

## Select additional files and exclude private material

Configure repository-relative, case-sensitive globs in `.reprollm/config.yaml`:

```yaml
schema_version: 1
discover:
  include: ["configs/experiments/*.yaml"]
  exclude: ["internal/**", "notes/private.json"]
```

`include` adds matching small text files to the default selection; it is not
an allowlist replacing the defaults. `exclude` wins over includes and removes
contents, source snippets and tree paths. Globs match the whole POSIX relative
path, with `*` also matching `/`. Hard exclusions, lockfile exclusion, binary
checks, the 64 KiB per-file limit and redaction still apply to explicit includes.
Excluding `reprollm.yaml` also excludes its field-name context from the request.
Symbolic links must resolve inside the repository; the same exclusions apply
to their targets. The 64 KiB limit also applies to source files used for snippets.

The default dry run lists selected, excluded, secret-bearing and truncated
files. Add `--show-content` to inspect the complete initial system/user request
messages, including tree paths, without credentials or a network request.
This option requires `--dry-run`.
