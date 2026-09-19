# Security Policy

## Supported versions

ReproLLM is pre-1.0 software. Security fixes are applied to the latest released version
on PyPI and the `main` branch only.

## Reporting a vulnerability

**Do not open a public issue for a security vulnerability.**

Please report privately via GitHub Security Advisories:
<https://github.com/EnumaElish123/ReproLLM/security/advisories/new>

Include, where possible: a description of the issue, steps to reproduce, affected
command(s), and any proof-of-concept. We aim to acknowledge reports within 7 days.

## Redaction is a security boundary

ReproLLM records experiment environments, and "recording the environment" is the
feature most likely to leak secrets. The redaction policy (spec §16) therefore has the
strictest guarantees in the codebase:

- Any change to `src/reprollm/core/redaction.py` must keep **100 % branch coverage** and
  add cases to `tests/fixtures/secrets/`.
- **A redaction bypass is a security bug**, not a normal bug. Examples: a secret value
  pattern that is not redacted in argv, file snapshots, patches, logs, or export output;
  a forbidden file that gets snapshotted; a secret environment variable whose value is
  recorded.
- The leak "golden test" (`tests/integration/test_no_leaks.py`, marker `security`) runs
  separately in CI and in the release pipeline before building distributions;
  a failure blocks publication. It recursively checks run JSON, snapshots, logs
  and a real dirty-tree patch in both environment capture modes.

Saved run data applies the nine name/value pattern classes in specification §16.
Known secret environment variables are presence-only; forbidden inputs such as
`.env` are hashed but never snapshotted. The run persistence layer additionally
removes the current hostname, username and absolute paths. `SSH_AUTH_SOCK` is an
intentional secret-name false positive because it contains the `AUTH` segment.

Pattern-based redaction cannot recognize every confidential value or future token
format. It does not sanitize original terminal output, the child's environment,
or files the child creates itself, including inside the run directory. Logs saved
with `--capture-output` are redacted; the corresponding terminal output remains
unchanged. Review artifacts before publishing them. See [the runtime guide](docs/run.md).

For a bypass report, include the affected version, capture mode and surface,
plus a minimal **synthetic** value that reproduces the issue. Do not attach real
tokens or unreviewed run directories to public issues or pull requests. Revoke
an exposed credential through its provider and report privately using the link above.

## Scope

In scope: anything ReproLLM writes (run records, snapshots, patches, logs, lockfiles,
export output, discover payloads), network behavior of `lock`/`discover`/`doctor`, and
command execution semantics of `run`.

Out of scope: the user's own experiment code and files, original terminal output
(including when `--capture-output` is enabled), and vulnerabilities in
dependencies themselves (report those upstream).
