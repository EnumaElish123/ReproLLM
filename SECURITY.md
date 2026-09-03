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
  in the release pipeline before publishing; a failure blocks the release.

## Scope

In scope: anything ReproLLM writes (run records, snapshots, patches, logs, lockfiles,
export output, discover payloads), network behavior of `lock`/`discover`/`doctor`, and
command execution semantics of `run`.

Out of scope: the user's own experiment code, secrets the user prints to stdout of their
own command when `--capture-output` was never enabled, and vulnerabilities in
dependencies themselves (report those upstream).
