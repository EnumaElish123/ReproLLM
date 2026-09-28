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
$ reprollm discover . --experimental --yes       # one temperature-0 request
$ reprollm rules list                            # candidates: pending/ignored
$ reprollm rules accept c-3f9a1b                 # → project rule
$ reprollm rules ignore c-42b0c9                 # → recorded, never re-offered as pending
```

The model responds with JSON only. Invalid JSON is retried once with the parse
error appended; a second failure saves the raw response under
`.reprollm/discover/` and exits 3.

## Candidates are not decisions

Discovery only proposes. A candidate becomes a checked rule through your
explicit `rules accept`; its evidence paths are verified against the actual
payload, and anything citing files you never sent is demoted to `low`
confidence. `--paper` (paper–code consistency) is rejected in Beta.

Output quality varies with the model; treat candidates as review input, not
verdicts — "LLM discovers. Rules decide."
