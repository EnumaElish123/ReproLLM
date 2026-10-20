# R07-C coverage interface proposal — bounded design, not implementation

Status: PROPOSED. Source inspected: main `055c5fb` on 2026-10-20. No product,
test, schema, fixture or gold bytes are changed by this design. The root session
prepares the policy decision and D-41 engine review separately.

## Recommendation: narrow option A, a partial R07-C stage

The concrete recommendation after coordination is **known primary-Python gaps
veto an empty-result PASS for exactly two opt-in rules**:
`env.llm_critical_deps_pinned` and `exec.profile_detection_mismatch`. This is a
local policy enhancement, not certification of either mixed evidence pipeline.
All nonempty findings, applies=false results, other built-in rules and dynamic
project rules retain their current contracts. Mixed absence false positives and
upstream enumeration/dependency/framework risks remain OPEN. Do not mark the
whole R07-C task complete after accepting this partial stage.

For these two rules only, if `applies` is true and `check` returns no findings,
an observed gap between primary-Python candidates and parsed files yields the
existing INFO/SKIPPED result with a scope-specific reason. Unobserved or internally
inconsistent coverage yields INFO/SKIPPED with the fixed unavailable reason.
With consistent observed counts and no gap, the existing PASS synthesis remains.
This is a **known-gap veto**, not a proof that no gap in
any domain exists. Its usefulness does not depend on claiming global completeness.

The end-to-end matrix must retain all four required cases and mixed-domain
counterexamples. Existing nonempty absence-derived findings must be explicitly
labelled unchanged known debt, rather than described as verified violations.

## Sealed evidence scope

Support one sealed scope first: **the captured primary Python candidate view**,
after existing repository listing, size filtering and static exclusions. It is
the exact view consumed by `scan_python()`, not all Python files in the tree,
not all profile detection, and not dependency parsing. A result may say that
this view was exhausted; it cannot establish repository-wide absence.

The seam belongs at `PyScanResult` / `scan_python()`: callers need one small
typed coverage assessment, rather than reconstructing five failure classes,
parsing warnings, or duplicating candidate selection. Keep the four existing
count fields and the R07-B CLI diagnostic unchanged. Reuse existing finding
`status: skipped`, INFO severity and safe message/evidence notes for any later
approved policy outcome. No persisted schema field or version is needed for
this narrow design.

Do not attempt to make a global `repository_complete` Boolean. There is no
honest way to compute that from current typed facts.

## Current facts and independent scopes

| Module / operation | Current observed facts | What cannot be concluded |
|---|---|---|
| `core.git.ls_files` | Successful command yields sorted unique NUL-delimited paths. A nonzero result becomes an empty list. `proc.run_cmd` has a default 30-second timeout. | There is **no MAX_FILES constant or count truncation in current source**. Empty success, timeout, missing Git and other nonzero failures are indistinguishable at the listing interface. Do not invent a Git MAX_FILES event. |
| fallback `os.walk` | Sorted/pruned directories, no file-count cap. Default walker behavior can omit unreadable directories without a supplied `onerror`. | No typed enumeration-completion or failure receipt exists. An empty result does not prove an empty tree. |
| `RepoScanner.files` | Drops `.reprollm/runs/**`, then `_size_of` admits regular/resolved files at most 2 MiB. | `_size_of` silently returns None for oversized files, missing/nonregular paths, broken aliases and inspection errors. These paths vanish before Python candidate counting. No typed omitted-path/count/status remains. Metadata may be inspected through an alias; this is not a content-read sandbox claim. |
| `analysis_files` | A cached candidate view applies environment/cache/generated exclusions and marker checks. Unsafe aliases may remain visible to the content-read check; resolved excluded directories are filtered. | Marker/resolve failures and exclusions do not form a typed complete enumeration. Some unsafe paths already vanished in `files`. No atomic filesystem snapshot is established. |
| primary `scan_python` | Candidate count is `.py` paths in `analysis_files`. Selected is `python_files()` with active MAX_PYTHON_FILES, normally 500. Parsed increments only after successful `ast.parse`. | Candidate count is not raw filesystem count. Selected minus parsed is an exact aggregate; it cannot be decomposed into unreadable, binary, size, syntax or unsafe-path counts from the four counters. |
| `read_text` | Default read cap is 512 KiB. None represents path rejection, no regular file, inspection/read failure, oversize, NUL, decode failure and related skips. Syntax failure is handled later by `scan_python`. | Reasons are not returned as a typed result. Some branches emit warnings, others are silent. The warning list is not a typed outcome log and must not be reverse-parsed. |
| caching and aliases | Current resolved target is rechecked even on cache hits; a retargeted alias cannot reuse another target's cached text. Cached text is keyed by logical source and resolved target. | Same-target mutation can reuse cached text. Components/targets can change after validation. Counts describe captured analysis observations, not end-of-command byte identity, descriptor isolation or an atomic filesystem sandbox. |
| generic profile detection | Combines primary AST, dependency declarations, README text, config keys, directory names, file stems and framework signals. Config parse failures silently return no keys. | Python counts cannot certify this union. A failed config parse and a config with no interesting key are not typed apart. Five retained evidence items is an output representation cap, not an analysis-completeness cap. |
| framework detection | Shell/Makefile scans use the shared 512 KiB read limit independently of primary Python selection. Shell tokenization failure can yield no commands. YAML task composition can yield None for multiple reasons. lm-eval stops after a sufficient positive YAML witness. | No typed full-consumer coverage result exists. Positive witness suffices for detection; lack of a witness does not imply every possible source was parsed. |
| task extraction | InspectAI separately reads bounded Python paths and may use a regex fallback on syntax failure. LightEval/lm-eval use their own task-YAML selection and parsing. | Primary AST parsed counts do not describe these separate parsers, their fallbacks or completeness. |
| dependencies | Requirements graph has typed private per-root readability and closure completeness, including cycle/depth/unsupported cases. Depth is 10. Declarations also contain diagnostics strings and R06-B project/uncertain-directory facts. | These are not a typed global dependency-completeness result. Malformed locks can become empty package inventories without a parse-failure status. Some unsupported or wrong-typed declaration structures are skipped silently. `unparsed == []` is not proof of completeness. R06-B uncertainty is only a lock-origin barrier, not dependency semantic coverage. |
| discover | Independent 64 KiB file size, configured character budget and 2,000 tree-entry limits; separate snippet parsing/selection. | Its coverage is neither described nor certified by primary Python counts. This design does not change discover. |

The fixed current values are implementation facts, not additional policy
defaults. Preserve existing active-limit reporting when a test or caller changes
MAX_PYTHON_FILES. The proposed scope must not silently widen if another consumer
later adds a budget or parser.

## Minimal typed result and compatibility path

The selected concrete interface is represented here as inert design text:

```python
@dataclass(frozen=True)
class PythonCandidateCoverage:
    # Fixed scope: captured primary-Python candidate view, not the repository.
    observed: bool
    candidate_count: int
    selected_count: int
    parsed_count: int
    file_limit: int

    def pass_skip_reason(self) -> str | None:
        ...
```

`omitted_count` is candidate minus selected; `selected_unparsed_count` is
selected minus parsed. They are derived properties, not additional independent
mutable counters. For a normally completed scan, require
`0 <= parsed <= selected <= candidate`, `0 <= file_limit` and
`selected <= file_limit`. A zero active budget is not an observation sentinel.
Conceptually, an exhausted view means **consistent observed**
candidate == selected == parsed. A limited view means consistent observed counts
where at least one candidate was omitted or did not parse. Unavailable means
observed is false or the count invariants do not hold. These are explanation
categories, not additional returned or persisted state fields. Check unavailable
before comparing parsed and candidate. Its fixed reason is `Python candidate
coverage is unavailable; no rule-wide PASS is established.` A normal gap uses
the proposed fixed counts message. No reason is returned only for consistent
observed counts with parsed == candidate.

An observed candidate == 0 can exhaust **only this captured view**, including
when the active budget is zero. It never proves the repository contains no
Python. An observed nonempty view with zero budget instead has an ordinary
selection gap. A default unobserved four-zero result is unavailable.

Unknown **upstream** listing/dependency/framework coverage is a separate explicit
limitation: it is not mapped to this unavailable state, does not force a global
SKIP and is not certified by the absence of a primary-Python gap.

The existing default `PyScanResult()` has all zero counters. Do not reinterpret
that synthetic/default object as a completed scan. The selected proposal adds an explicit internal
observation marker, defaulting to absent/unknown, set by `scan_python()` only
after normal completion. Derive the immutable assessment from the existing
counts through one method/property. This keeps callers of the four legacy
fields and old dataclass construction compatible and avoids two authoritative
copies of each count. The marker is not persisted and is not a cryptographic
attestation; this is an internal semantic interface.

No per-cause counts, arbitrary exception text, absolute paths or file content
are exposed. Existing selected-unparsed aggregate handles 512 KiB, binary,
decode, unreadable, path-rejection and syntax cases without guessing which
reason occurred. More precise failures require instrumentation at the actual
read/parse branch in a separately scoped follow-up.

## Engine and rule conclusion constraints

Keep the existing `Rule.check(ctx) -> list[Finding]` interface. A small
per-rule opt-in requirement for empty-result conclusions may refer to this
one typed scope. Its default is no new requirement, preserving unchanged
manifest/Git/lock/State rules and avoiding an unnecessary lazy scan for them.
Engine changes require the concrete D-41 review before implementation.

If this explicitly partial contract is accepted:

1. Evaluate concrete rule evidence before gating an empty-result PASS; never
   short-circuit a real positive violation merely because coverage is limited.
2. An empty list is not automatically proof of absence. For the two named
   opt-in rules, a known limited or unavailable primary view vetoes PASS; existing INFO/SKIPPED
   with a fixed scope-specific reason uses current fields. No such veto for the
   other rules is inferred. Exhausted primary view does not certify the mixed
   rule inputs; unchanged PASS remains the historical bounded evaluation result.
   Default fail-on thresholds are unchanged.
3. Applicability that depends on an absent AST signal needs its own wording:
   limited/unknown evidence is not the same as positively proving not applicable.
   Do not blanket-replace every applies=false outcome. A missing manifest still
   has its existing independent applicability meaning.
4. Narrow A preserves all produced findings as the unchanged legacy contract;
   that preservation does **not** validate absence-derived findings or establish
   that their actual logical premises are justified. Reclassification of those
   branches requires a separately explicit per-rule policy and remains OPEN.
   Do not describe unchanged legacy results as "verified real violations".
5. Only rules named in the accepted policy opt into a new result. Do not map
   every rule to primary-Python completeness, or convert all results to SKIP.
   Unknown upstream scope stays disclosed, not upgraded to true or applied as
   a global veto to otherwise independent conclusions.

Two examples show why the empty-result engine change alone is insufficient:

- `exec.profile_detection_mismatch`: declared-but-not-detected is an absence
  inference across AST + deps + README/config/framework sources. The opposite
  branch (a concrete high-confidence detected profile absent from an explicit
  declared profile list) has an actual witness. Treat these branches separately.
  Primary Python exhaustion cannot justify the first branch.
- `env.llm_critical_deps_pinned`: import/declaration presence is positive, but
  "used and not pinned" also depends on not finding an existential exact
  declaration or qualified lock origin. An unreadable or silently unsupported
  dependency file can hide such an exact declaration. Conversely, an actually
  found exact declaration is sufficient under accepted R06-B despite unknown
  declarations elsewhere. R06-B lock-origin barriers are not a universal
  completeness or failure classifier.

An additional witness/control case is an AST-only hint rule such as
`model.trust_remote_code_declared` (unchanged in narrow A): keep manifest-based applicability distinct;
a found `trust_remote_code=True` plus a missing explicit manifest field remains
an evidence-supported warning even with a capped view. A hint absent because it
lies beyond the cap must say insufficient primary-view evidence rather than
asserting whole-repository absence. With complete primary view but no hint,
only a primary-view conclusion is supported. The current catalog may already
SKIP absent hints; the proposed value here is honest reason/scope, not pretending
that this case currently synthesizes a false PASS. Any demonstration of a
   PASS→SKIP change must choose a rule/branch whose current behavior truly returns
an empty list with applies=true and whose complete evidence requirement has
been independently justified.

## Explicit deferrals

- Raw repository listing completion: add typed Git command outcome and walk
  errors only in a separately reviewed scope. Do not infer them from `[]` or
  from hypothetical MAX_FILES. Record current post-filter scope instead.
- Counts/reasons for paths lost before analysis_files, oversized listing files,
  marker failures and unsafe aliases. Do not rescan outside-root targets.
- Global dependency parsing completeness, unsupported formats/grammar, solver,
  installation or source-association expansion. Keep accepted R06-B policy.
- Aggregate detection/README/config/framework/task coverage and branch-specific
  false-positive suppression. Their own selection/read/parse outcomes need
  typed facts before a global negative conclusion can be certified.
- Discover budgets, runtime capture, persistent coverage schema, global new
  finding status, changed rule IDs/severities/fail-on, dynamic probes or sandbox
  guarantees. No new model/GPU/provider execution is part of this work.

Before approving a wider scope, require independent cases for Git command
failure, walk errors, >2 MiB disappearing Python, 512 KiB selected skips,
binary/decode/syntax failures, broken/outside/retargeted aliases, silent malformed
dependency and config structures, explicit positive witnesses and zero-candidate
views with unknown enumeration. Tests must demonstrate the stated distinction;
count equality alone is not a full-repository oracle.
