# Lockfile guide

`reprollm.yaml` describes the intended experiment. `reprollm lock` resolves that
description into `reprollm.lock`, a reviewable YAML document with `schema_version: 1`.
An audit automatically enters Level 2 when a lock is present.

```console
reprollm lock .
reprollm audit .
reprollm lock . --check
```

Fill the manifest first. Resolution records model and tokenizer revisions,
chat-template and config hashes, dataset revisions, prompt and declared-file
hashes, metric implementations, installed backend versions, and the local
environment. It downloads small Hub metadata files, never model weights or
dataset contents. A locally declared model's existing weights are hashed only
when their total size is at most 100 MiB, unless `--hash-large-files` is supplied.

## Provenance and confidence

Resolved fields carry their value, source, confidence, optional resolution time,
and a note explaining uncertainty. Declared fields, such as dtype and generation
parameters, pass through unchanged. For example:

```yaml
version:
  value: null
  source: importlib_metadata
  confidence: unresolved
  resolved_at: null
  note: 'distribution not installed: vllm'
```

| Confidence | Meaning |
|---|---|
| `exact` | Obtained from the source, such as an HF commit SHA, local file hash, or installed distribution version. |
| `declared` | Copied from the manifest without online resolution. An offline declared revision has this confidence. |
| `unresolved` | No verified value is available; inspect `source` and `note`. |

Missing packages, access denials, unavailable networks, and unsupported providers
remain explicit. A lock with unresolved entries is still written with exit 0;
the summary lists those entries and Level 2 audit applies the rule severities.
Inspect the lock and audit together rather than treating a successful write as a
claim that everything is reproducible.

## Model pinnability

Pinnability describes the provider's identity contract, separately from whether
this particular resolution attempt succeeded.

| Pinnability | Meaning |
|---|---|
| `exact` | A provider such as Hugging Face supports immutable commits, or local artifacts can be hashed. Check provenance to confirm the value actually resolved. |
| `snapshot_alias` | An API ID ends in a dated `-YYYY-MM-DD` or `@YYYYMMDD` suffix. This is a provider snapshot label, not a weight hash. |
| `unpinnable` | An API alias can change behind the same ID. |

The API judge in the FastChat dogfooding manifest produces these fields:

```yaml
models:
  judge:
    provider: openai
    id: gpt-4o-2024-08-06
    pinnability: snapshot_alias
    revision:
      value: null
      source: provider_no_pinning
      confidence: unresolved
```

API models are not contacted by default. `lock --verify-api` requests model
metadata only when the provider's environment key is present; it records
`exists` or `not_found` without changing the pinnability contract. No inference
request is made. Missing keys yield `verify skipped: no api key`.

## Offline and access-restricted environments

```console
reprollm lock . --offline
reprollm doctor --check-network
```

`--offline` prevents all HTTP, including optional API verification. Declared HF
revisions have `confidence: declared`; undeclared remote revisions remain
`unresolved` with `source: offline`. Local prompt/config/dataset hashes and
installed versions are still captured. Offline mode does not reuse an old lock
or silently promote an unverified SHA to `exact`.

The HF endpoint defaults to `https://huggingface.co`; `HF_ENDPOINT` selects a
mirror. Both lock resolution and the opt-in doctor probe use the same HTTP
client: 10-second request timeout and two retries after connection failures or
server errors. `doctor` without `--check-network` stays local.

For gated/private repositories, supply an authorized `HF_TOKEN` (or
`HUGGING_FACE_HUB_TOKEN`) in the environment. HTTP 401/403 is recorded as
`hf_api_forbidden`; audit's model revision fix hint names `HF_TOKEN`. Credentials
are sent in the Authorization header, never copied into the lock or summary.
Errors contain sanitized classes/sources, not response bodies or raw request
exceptions. Keep keys in the environment, not in `reprollm.yaml`.

## Freshness and file changes

`reprollm lock --check` makes no network requests and writes nothing. It returns
1 if the lock is absent or if the bytes of `reprollm.yaml` or
`.reprollm/project-rules.yaml` have changed. Otherwise it returns 0. Even a comment
edit changes a document hash. `consistency.lock_fresh` reports the same mismatch
as a WARNING in Level 2 audit.

Freshness does not mean upstream branches, API aliases, or local file contents
are unchanged. `consistency.file_hashes` separately compares the current prompt
and declared-file bytes against the lock, reporting CRITICAL for a changed or
missing file. Runtime comparisons arrive in M5. Re-run `lock` deliberately when
adopting new revisions or changed inputs, then review the diff before committing.

## Dataset identity boundary

HF datasets record repository revision, subset, and split. Beta always writes
`content_fingerprint: {status: not_computed}`: no dataset content is downloaded or
fingerprinted (D-22). Local datasets record hashes for explicitly declared files.
An HF revision identifies the repository state; it does not prove the identity
of externally hosted data or the result of preprocessing.

See the normative [lock schema](plan/01_specification.md#4-lock-schema--reprollmlock)
and [rule catalog](rules.md) for exact fields and severities.
