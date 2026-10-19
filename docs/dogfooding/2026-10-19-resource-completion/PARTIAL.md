# Stable resource-session evidence — 2026-10-19

This partial report covers the frozen candidate
`750270b10307455795fcff126664429dc895983a`, its completed local quality gate,
fresh five-project Gate A, Linux H2 metadata replay, exact input recovery and
independent input-integrity checks. The session owner records native execution,
paid judge results and the final resource-gate disposition separately.

The [stable-file manifest](stable-files.json) records original and retained
SHA-256 values and sizes. Identical bytes are retained once. An original command
receipt's relative raw-stream path can be resolved through its corresponding
`source_logical_file` entry to `retained_file`; this avoids copying the same JSON
again as both an artifact and a stdout stream. Large local source dictionaries,
coverage databases and private raw quality logs are represented by hashes;
shareable quality logs are retained. Sanitized logs and inert helpers disclose
both source and retained hashes. No credential values or machine identities
belong in this bundle.

## Frozen candidate and final quality

The [final quality receipt](quality/summary.json) records all 24 checks passing
on unchanged candidate inputs. The [compact source binding](quality/source-input-binding.json)
records all 3,521 tracked files, verified against Git blobs, and the identical
before/after inventory. The [command receipt](quality/commands.json) retains
exits, elapsed times, origin checks and safe-log hashes.

- [Full suite](quality/logs/02-pytest-coverage.log): **2,845 passed, 2 deselected**;
  overall line/branch coverage **93.83%**.
- [Redaction coverage](quality/logs/03-redaction-coverage.log): **100%**, including
  every branch. [Security subset](quality/logs/04-security.log): **205 passed**.
- Lint, formatting, strict type checks, documentation/schema freshness, examples
  and self-audit passed under the shared final gate.
- The [build manifest](quality/build-manifest.json) identifies the candidate
  `0.7.0` wheel, SHA-256
  `1f2a747e8a5efd6b65201b238ae1d0059d59c84f8176da645f7a18554bd2ba1e`.
  Its initial `distribution_acceptance: PENDING` is retained unchanged; the
  subsequent [installed-distribution receipt](quality/distribution.json) is PASS.
  A wheel build does not publish a version or create a tag.

Cross-platform CI and the actual final pushed commit remain separate evidence.

## Fresh five-project Gate A and supplementary collection

[Gate A](gate-a/summary.json) passed after the quality gate: all five pinned
sources stayed clean and unchanged, all 51 commands exited as expected, and
all 32 checks passed. Ten product commands supplied complete Level 0 reports
and source/detection facts. Ten complete JSON comparisons cover findings,
profiles, hints, dependency declarations, source paths and diagnostics; this is
not acceptance by summary counts alone.

The supplementary discover collection [final receipt](discover-preview/final/summary.json)
records five successful read-only previews, 215 selected files, exact selected
source segments, complete prior report/message equality and zero second-pass
redactions. It sent no request. The [initial failed observer attempt](discover-preview/attempt-1/summary.json)
retains its `SyntaxError` and first captured preview; the final run is a separate
record. These previews use uninitialized pinned sources and do not close formal
initialized discover or live-provider acceptance.

## Exact input recovery

The [updated recovery inventory](input-recovery/inventory.json) has **45 of 50
required slots AVAILABLE**, **5 MISSING**, **0 ACCESS_BLOCKED** and **0
HASH_MISMATCH**. The 45 restored slots resolve to **37 distinct byte identities**
under `inputs/`. All stored bytes match prior independent expected SHA-256
values. Duplicate A/B slots share a retained file; the inventory preserves each
slot's original path and variant. Python drivers are inert `.inert.py.txt` files;
original JSON arrays use `.json.txt` without changing their bytes.

The five remaining gaps are the original **val §8.1** metadata manifests.
The five restored **§8.2 H2 supplementary** manifests retain their own distinct
identities. The [bounded Linux search](metadata/original-val8.1-search.json)
checked 9,431 small candidate files and 11 members of three archives across 38
named evidence/task roots, with no original-manifest hash match. It excluded
credentials, caches, environments, model/dataset content, symlink traversal and
unrelated directories. This is a statement about those search boundaries, not
proof of absence everywhere on the machine.

The [license/source record](input-recovery/license-provenance.json), retained
[validation license](inputs/VALIDATION-LICENSE.txt) and prior
[A01 attribution review](../2026-10-18-a01-local/input-readiness.md) document
ownership and pinned upstream dependencies. Recovery restores input identity;
it does not independently pass runtime or provider gates.

## Linux H2 metadata replay

The [qualified H2 receipt](metadata/summary-qualified.json) covers all five
supplementary manifests, all 15 offline/online-1/online-2 modes, and **96 actual
commands**, including **51 product commands**. Every actual command exited 0.
The five original source pins and all candidate bytes stayed unchanged.

Assertions checked all declared local hashes and sizes, exact remote model,
tokenizer and dataset revisions, config/chat-template hashes, complete role/file
sets, schema validity, Level 2, clean disposable Git state, lock freshness and
file consistency. Both online locks are equal after removing only the allowed
schema-owned timestamp locations. All five original checkouts completed doctor;
an anonymous official-HF gpt2 probe through the existing HTTP proxy succeeded.
No HF token, paid endpoint, GPU job or model/data download was used by H2.
Anonymous Llama-2 small-file denial remains `unresolved/hf_api_forbidden` and is
independent of authenticated-access results.

The [initial observer summary](metadata/summary.json) remains failed because
five doctor assertions incorrectly required Git `ok`. The actual Git 2.25.1
status is the documented usable-but-below-recommendation `warn`; every other
doctor item was `ok`. The [same-input qualification](metadata/same-input-qualification.json)
corrects only those five observer predicates, without rerunning a product
command. It independently verifies 192 stream hashes, 51 candidate-origin
receipts, 15 complete reports and 15 full lock comparisons.

The historical report differences are fully disclosed: displayed version
`0.6.1` to `0.7.0`, current timestamps and resulting lock hashes, and the adopted
R04-B recorder-scope message/fix hint for `consistency.env_vs_lock`, which remains
INFO/skipped. Every other finding, hint, path and profile matches the prior
same-input observation. The historical observation supplements the independent
`val.md` assertions; it is not promoted into replacement gold.

## Readiness, installation and independent input integrity

The [readiness receipt](readiness/pre-execution.json) is an immutable snapshot
**before candidate installation and resource execution**. At that check, GPU 0
was the permitted card and met the original strict numerical guard; the two
validation leases were free and the data volume had 78.58 GiB available. GPU 1
was excluded and existing processes were retained. Every native launch still
needs its own immediately preceding guard/lease evidence.

The snapshot's DP ReproLLM `0.6.1` is superseded by the explicit
[phase correction](readiness/phase-correction.json) and current
[modern](installation/modern/proof.json) / [DP](installation/dp/proof.json)
installation proofs. Both isolated environments now verify candidate `0.7.0`
and all 141 package payload files. Installation used no dependency resolution;
274 modern and 82 DP third-party distributions stayed unchanged.

The [native input recovery](input-integrity/native-input-recovery.json) and
[source integrity](input-integrity/native-source-integrity.json) receipts bind
exact restored inputs and upstream runtime source to immutable Git objects.
The [cached-model proof](input-integrity/cached-model-integrity.json) independently
hashed 45 physical files, 48,925,943,574 bytes, against existing fixed SHA-256/LFS
or immutable Git-blob expectations, without network, cache mutation or GPU work.

The [current GSM8K row proof](input-integrity/gsm8k-final.json) checks the fixed
revision's 7,473 training and 1,319 test rows using the original canonical row
serialization and exact expected content hashes. Its referenced
[initial](input-integrity/gsm8k-initial-helper-failure.json) and
[intermediate](input-integrity/gsm8k-intermediate-helper-failure.json) helper
failures are retained by their original hashes. Their overly broad guards
blocked import-time capability probes before dataset reads; the final receipt
limits task-owned scratch probes while rejecting resource/cache/source writes,
network and new children.

This stable package does not itself decide native, paid-judge,
authenticated-success or release acceptance.
