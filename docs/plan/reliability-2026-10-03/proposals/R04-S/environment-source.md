# R04-A environment source and phase proposal

Status: **PROPOSED / REVIEW_READY**. This document is evidence and a concrete
design for R04-A; it does not approve or apply the adjacent schema/spec patches.
Base: `52ecc504b3795c46220f68ef24728e0666638df0`.

The assigned scope is [R04-A](../../03_Scan_and_Runtime_Evidence.md#4-r04-a运行环境的来源和采集时点),
followed by R04-B. The conditional schema criteria are
[R04-S](../../05_Policy_and_Compatibility.md#6-r04-s环境来源与输入时点的条件-schema-方案).
R04-A needs explicit provenance on the internal State; it does not need an
additional persisted run-environment field. R04-B's per-run input checks are a
separate reason for the adjacent run-schema proposal.

## Actual failure and proposed interpretation

The new public regression uses stdlib `venv` without pip. A real child reads a
synthetic `torch-0.0.123.dist-info/METADATA` containing no torch module. The
recorder's `importlib.metadata.version` boundary independently reports no
LLM-critical distributions. Git and GPU command boundaries are unavailable
stubs; the child remains a real subprocess. No heavy package is installed or
imported, and there is no network access.

Independent child witness:

```json
{
  "schema_version": 1,
  "torch": "0.0.123",
  "torch_importable": false,
  "omp_threads": "3"
}
```

The existing run record actually completes with exit 0, warnings `[]`, recorder
packages `{}`, and inherited `OMP_NUM_THREADS: "2"`. These facts are retained;
the child changed its own variable to 3. The current State's Python leaf has
`source: run`, `confidence: observed`, and no typed context. The actual regression
fails precisely at that absent context, after the child witness, exit status,
package collection and inherited baseline have passed.

Before, actual State leaf excerpt:

```json
{
  "value": "<recorder Python version>",
  "source": "run",
  "detail": null,
  "confidence": "observed",
  "alternatives": []
}
```

After, proposed State leaf excerpt:

```json
{
  "value": "<recorder Python version>",
  "source": "run",
  "detail": null,
  "confidence": "observed",
  "context": {
    "subject": "recorder",
    "phase": "post_child",
    "verification": "unverified"
  },
  "alternatives": []
}
```

The context verifies neither a child interpreter nor consumed inputs.
`confidence: observed` still describes the recorded metadata value; the separate
`verification: unverified` states the absence of child-environment/consumption
verification. Equal executable names, Python versions, realpaths or inodes are
not proof of shared site-packages. No child interpreter is probed automatically.

The exact executed test, exit statuses, durations, input hashes and original-log
hashes are in [environmental-red-evidence.json](environmental-red-evidence.json).
The first manifest fixture incorrectly listed implicit `core`; that preparation
failure is preserved as `NOT_PRODUCT_RED`. The corrected legal fixture then
produced genuine RED. No implementation or GREEN is claimed here.

## Source and phase matrix

| Existing fact | Typed subject | Typed phase | Meaning and limit |
|---|---|---|---|
| run environment Python/packages | `recorder` | `post_child` | Interpreter executing ReproLLM; metadata collected after child completion, not child site-packages or start-time inventory |
| run OS/platform | `host` | `post_child` | Host visible to the collector; not a remote/container child attestation |
| run hostname hash | `host` | `pre_child` | Hostname was copied before launch and later hashed; do not label its value post-child merely because `_collect` writes it |
| run hardware | `host` | `post_child` | Actual collector-visible CPU/GPU metadata; `unavailable` remains a valid outcome |
| run environment env/env_capture | `inherited_environment` | `pre_child` | Copied recorder environment passed as the child's baseline; excludes child-internal or launcher rewrites |
| scheduler namespaces | `inherited_environment` | `pre_child` | Captured from that copied environment; no scheduler namespace legitimately gives `scheduler: null` |
| lock Python/packages | `recorder` | `lock_resolution` | Interpreter executing lock resolution; not a future child installation |
| lock platform/GPU | `host` | `lock_resolution` | Host visible during lock resolution |
| Unregistered producer or legacy State without context | `unknown` | `unknown` | Recorded values survive; their subject/phase cannot be reconstructed safely |

Every context uses the proposed closed `verification: unverified` value. The
context is metadata on a leaf, never a new experimental path participating in
drift. Binding location strings in `detail` retain their existing grammar.

## Why environment persistence can remain unchanged

For the explicitly confirmed writer contracts, environment subject/phase is
fixed by the writer, schema and producer version. Existing `schema_version` and
`reprollm_version` therefore provide a durable discriminator on run/lock input.
The reader projects the corresponding context onto State leaves. This preserves
old run bytes and avoids a redundant source matrix on every environment object.

The package map may be empty. Empty dictionaries produce no flattened package
leaf, so consumers must qualify the whole package observation through the
required `environment.python` anchor, including its alternatives and context.
They must not confuse a missing package leaf with missing/unknown capture, nor
infer a child inventory from the empty recorder map. `environment.env_capture`
similarly anchors the inherited-env policy even when the permitted map is empty.

An internal typed context is preferable to a grammar inside `detail`: the
existing `cli:`, `config:` and `env:` prefixes determine run precedence. Using
`env:` for environment provenance would accidentally increase its priority.
The proposed `Leaf.context` is a separate optional internal field, requires
D-41 review, and must survive alternatives, State JSON round-trip and repeated
merge. It must not change `_rank`, `_order_key`, R03's last explicit CLI choice,
existing path names or drift severity.

State is currently internal and is not one of the ten exported artifact schema
models. This does not make a new context field review-free: an old strict State
reader would reject it, and an old State has no producer version from which to
invent context. New State readers accept absent context conservatively; there
is no promise of old-reader compatibility for a serialized new internal State.
The persisted run-schema transition and minor version strategy in R04-S belong
to R04-B, not to a claim that an optional environment field is bidirectionally
compatible. No environment run-schema change is needed for R04-A itself.

## Producer contracts: separate run and lock evidence

[producer-contract-source-evidence.json](producer-contract-source-evidence.json)
contains independent source checks for run and lock. The currently supported
exact versions for each happen to be:

`0.1.1`, `0.4.0`, `0.5.0a1`, `0.5.0`, `0.5.1`, `0.5.2`, `0.5.3`, `0.6.0`, `0.6.1`.

Run evidence starts at its actual writer introduction
`e020e76989b955699bf459781bb5ec6520f53964`; lock evidence starts separately at
`70ff4940a13cb2c5a9a1706a026f5112a3a73960`. Each sampled producer's source is
hashed and establishes the respective call/metadata contract. Package capture
membership changed across releases; these checks establish subject/phase, not
a promise that every historical release recorded today's package list or a
complete inventory.

This is an explicit registry, not an arbitrary `0.x` version range. `0.3.0` is
present in a normative example but was not confirmed as a historical writer by
this source history. Unlisted, forward, custom/local or invalid producer strings
remain unknown. Proposed `0.6.2` and `0.7.0` registrations must be justified by
their actual reviewed writer source when implemented; they are not historical
facts in this table. A claimed version is a declared producer contract, not
authentication of a fork's code.

Recognized legacy run/lock readers recover the contract without rewriting the
document. Old internal State JSON with absent context remains unknown; a leaf's
`source: run` by itself proves no phase. Typed context already present on a new
State must round-trip unchanged instead of being reconstructed from warnings.

## Consumer behavior and concrete before/after choices

| Consumer | Before | Proposed behavior |
|---|---|---|
| State projection | All environment values are undifferentiated run/lock leaves | Attach centralized closed contexts to the existing leaf paths; leave values, binding detail, precedence and alternatives intact |
| `consistency.env_vs_lock` | Both non-null maps make it applicable; equal/empty maps can yield an unqualified runtime PASS | Compare confirmed recorder observations at known compatible phases, `lock_resolution` vs `post_child`; retain version mismatch WARNING and one-sided-presence INFO; PASS explicitly says recorder metadata only, child unverified |
| Unknown/incompatible environment sources | Non-null values are treated like an ordinary runtime match | SKIP with fixed scope guidance; never child-verified success, and do not decide qualification from natural-language warnings |
| Diff changed package/Python leaves | Existing values and severity only | Keep values/severity/fail-on; add safe subject/phase scope using existing `DiffChange.note` |
| Empty/equal diff | “No reproducibility-relevant drift detected” may look like verified child equality | Explicitly limit the text to compared recorded values; child environment and actual consumption remain unverified |
| JSON diff | `summary.same` is recorded-value equality | Keep schema 1; specify that equality is not verification. Context-only differences create no new drift leaf/count or severity |
| Export | Environment shows Python/packages without subject/phase | Retain useful recorder and host values, label their phase, and keep child environment unknown/unverified in limitations |

“Compatible” means a known recorder subject category and allowed observation
phases. It does **not** mean the lock/run used the same actual interpreter,
process, machine, venv or installation prefix. The inherent phase difference
between lock resolution and after-child observation is intentional; literal
phase equality would incorrectly skip all lock/run comparisons. Unknown context
cannot be rescued by matching versions, command names or filesystem identity.

All audit/diff/export qualification reads typed State provenance (D-27), not
warnings or a hidden child probe. Rule IDs, severity table, engine and core
redaction remain unchanged. Raw observations remain evidence even where source
qualification is insufficient; no new child package set is invented.

## Export/template matrix

| Template | Required qualification |
|---|---|
| default | Environment labels recorder Python/packages and phase; host hardware retained; inherited env baseline qualified; child verification limitation always retained for a selected run |
| neurips | Same shared Environment/Hardware/limitations; software-version and compute checklist references point to scoped statements rather than child/software attestation |
| acl | Same shared sections; computational reproducibility pipeline wording does not promote record capture to verified consumption/environment |
| acm | Same shared sections; software environment and Functional/Reusable references retain scope and evidence limitations |

The current template Python/packages table flattens away leaf provenance. A
central export adapter should retain or summarize context in its internal view
model instead of parsing display text. Existing default/custom template API
values remain intact; new scoped display data need not expand a persisted schema.

## Normative edits covered by the adjacent proposal

- §5.1 R-06: the source matrix, host hostname pre-child exception and no automatic
  child equivalence. §16.3: env is the pre-child inherited baseline; existing
  allowlist/secret/privacy rules are unchanged.
- §4 lock environment and §4.3 metadata resolutions: recorder at lock resolution,
  not verified future experiment software. Existing resolved/declared confidence
  remains distinct from the environment subject claim.
- §12.12: scope `consistency.env_vs_lock` to compatible recorder evidence,
  preserving mismatch/presence severities and explicitly scoped PASS/SKIP.
- §17: exact typed context enums, unknown meaning, empty-map anchoring,
  alternatives/round-trip/merge preservation and unchanged precedence.
- §18: recorded-value equality, safe existing change notes, empty-text scope;
  no context-only experimental drift and no child-match inference.
- §19: every existing template includes source/phase and child-unverified
  limitations without omitting useful recorder/host evidence.
- §22 tests: two lightweight interpreter environments/dist-info, no heavy imports,
  no network, capture-failure exit propagation and legacy compatibility.

The adjacent spec patch already chooses recorder-compatible comparison and
existing DiffChange notes. This evidence document identifies the finer hostname
phase, separate lock registry and empty-map anchor requirements for that patch's
review; it does not overwrite the patch.

## Next vertical acceptance slices

1. Current actual RED: real child venv has metadata 0.0.123, recorder map is empty;
   run→State→JSON→merge must retain typed recorder/post-child context and inherited
   pre-child baseline without inventing child package observations.
2. A second stdlib environment pair: A and B share a base executable but different
   dist-info. A plain child command, shell/launcher relay or matching Python version
   never upgrades verification. The fixture may execute its own trusted stdlib
   witness; the product must not probe arbitrary argv interpreters.
3. A child changes synthetic recorder-visible dist-info while it runs. Independent
   before/after metadata receipts establish that package collection is post-child,
   not a start-time snapshot. No real package installation is performed.
4. Known lock/run recorder version equality, mismatch and one-sided presence;
   unknown producer, unknown legacy State and incompatible contexts. Assert scoped
   PASS or SKIP and the existing INFO/WARNING policies separately.
5. Environment capture failure with child exit 7 retains exit 7 and fixed failure
   diagnostics. Host/hardware unavailable and absent scheduler remain honest facts.
6. R03 ordered CLI observations and repeated merge remain unchanged with typed
   context on primaries/alternatives. Test partial and empty package maps explicitly.
7. Diff changed/self/equal and every export template distinguish recorded facts,
   inherited baseline and unverified child evidence; no schema/severity changes in
   diff and no claim that unchanged values establish child consumption.

Full quality, five-project Gate A and affected diff/export replay are still
future implementation acceptance. The existing VAL-R01 snapshot-fidelity defect
remains recorded FAIL; this proposal neither repairs RunPrivacy nor promotes
resource/native execution success into full capture PASS. R04-B and D01 are not
declared complete.
