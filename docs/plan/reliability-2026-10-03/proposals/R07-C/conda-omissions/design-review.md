# D-M-CE independent design review

Status: PROPOSED. Reviewed the existing source at `38b59cc` on 2026-10-27.
Proposed policy runs: 0. Manager/solver runs: 0. This review prepares a bounded
P-A; it supplies no product acceptance result. Earlier accepted R07-C slices
do not approve this new slice or its exact specification patch. Wider R07-C
remains OPEN.

## Recommended option A: two existing omission branches

Only `_add_conda_entry`'s two existing early returns qualify:

1. `_CONDA_NAME_RE.fullmatch(entry.strip()) is None`.
2. That match succeeds and its existing `rest.startswith(("::", "/"))`
   predicate is true.

Add `unparsed_conda` to the internal `DeclarationReadIssue` Literal and record
`result.declaration_read_issues.setdefault(path, "unparsed_conda")` at each
return. Retain the existing diagnostics and return placement. There are three
semantic additions; no caller/helper return change or consumer edit is needed.

Use a distinct code because `unparsed_requirement` currently identifies failure
of actual existing `packaging.Requirement` calls under specification
§§12.3.9–12.3.10. Conda's two omission routes are a separate extraction fact.
The new name means this bounded extractor did not emit a declaration for an
actually traversed string. It does not mean Conda rejected the string, the
entire environment is invalid, an installation failed, or an exact pin exists.
Do not infer this fact from absent exact credit, helper output, or diagnostic
prose. Official evidence and its limits are recorded in
[official-sources.md](official-sources.md).

## Exact trigger and retained controls

The existing environment traversal calls `_add_conda_entry` on every string in
an already decoded `dependencies` list. It has no nonblank guard. Empty and
whitespace-only strings therefore qualify when they reach the no-match return;
do not import embedded-pip's nonblank guard. Initial wildcard/punctuation,
some non-ASCII-leading strings and internal newlines can also hit that return.
This is the existing regex outcome, not a newly introduced syntax validator.

`conda-forge::pytorch==2.8.0` and
`conda-forge/linux-64::pytorch==2.8.0` illustrate the second omission branch.
They would record one source-file fact and still emit no new declaration. The
captured head is a prefix, not a newly certified package name; do not infer
torch use from that text. A malformed-looking input taking the same return is
handled by the same predicate without any claim about its manager validity.

| Existing route/control | Proposed cause | Preserved captured behavior |
|---|---|---|
| Either existing omission return | `unparsed_conda`, unless an earlier source cause exists | No declaration appended; original unsupported diagnostic remains |
| Name only | None | Named nonexact declaration |
| Numeric single `=` without build | None | Named prefix constraint, no exact credit |
| Supported numeric `==`, or numeric version plus supported literal build | None | Existing exact credit and evidence |
| `_CONDA_RANGE_RE` numeric range | None | Named nonexact declaration with original range; existing unsupported diagnostic remains |
| Other suffix reaching final append | None | Named nonexact declaration with existing sanitized specifier and diagnostic |
| URL-looking `https://...` | None when the current regex retains the `https` head | Preserve that existing head and sanitized nonexact declaration |
| A space before `::`, such as `conda-forge ::pytorch` | None when the current remainder starts with that space | Preserve the retained head; do not remove inner whitespace |
| Unknown installer/selector mapping | None from D-M-CE | Existing traversal/structure policy |

Retained complex suffixes include bracket constraints, compounds, wildcards,
unsupported version/build text and other text reaching the final append. Their
same unsupported diagnostic must not opt them in. Those remaining extraction
limits stay OPEN. Do not add support, parse or split the remainder, repair
strings, remove comments, normalize beyond existing `strip`, follow a URL/path,
or classify manager validity. Preserve the shared exact-version contract and
the existing `pytorch` to `torch` mapping.

## First cause, traces and inventory preservation

The existing whole-document structure precheck precedes entry traversal and
retains priority. Use `setdefault` so `invalid_structure` or another recorded
cause is not overwritten. Otherwise the actual outer-entry/member traversal
order decides the source's first cause: an earlier failed embedded-pip call
keeps `unparsed_requirement`; an earlier Conda omission keeps `unparsed_conda`
if an embedded-pip failure occurs later. Repeated omissions add no duplicate
source key. Distinct logical source files remain distinct dictionary entries.

Keep every partial declaration, order, canonical/display name, specifier, exact
value, source and existing line ordinal. Conda and embedded-pip source lines
remain the one-based outer `dependencies` entry ordinal, not newly inferred
YAML physical lines. D-M evidence is file-level; do not add per-entry evidence.
Retain the original diagnostic bytes/order and all existing helper/read traces.

Add no read, retry, candidate, source, parser, package dependency, include edge,
budget or manager invocation. Preserve manifest/lock presence, qualified project
roots, uncertain-directory barriers, same-directory environment ambiguity,
lock inventories and association, exact declarations and qualified-lock credit.
An entry omission adds no ownership barrier. Legacy/manual dictionaries remain
empty by default; no persisted field is added and historical artifacts keep
their bytes and meaning.

## Existing D-M consumption and reviewable cost

The rule already consumes a nonempty declaration-failure dictionary, using only
its sorted logical paths. Retain precedence in full: exact/qualified credit,
then D-F/D-S, D-L, D-M including this proposed cause, then D-G. Earlier branches
keep complete findings and evidence; do not append lower-priority D-G paths to
D-M. Preserve D-M's message, hint, SKIPPED/INFO status, first captured
declaration/import evidence and sorted distinct failed-source evidence. A new
source may enlarge a D-M finding's evidence without changing its existing SKIP.
No new rule branch or aggregate/per-package PASS is needed.

The explicit compatibility cost is repository-wide. Even an unrelated
noncritical channel-qualified entry or a dropped blank string in another
project can replace every remaining currently used, uncredited critical
package's missing-pin WARNING with SKIPPED/INFO. A dropped string need not
conceal any exact pin. This is a deliberately conservative continuation of the
D-M policy, rather than a deduction that Conda grammar proves a hidden exact.
It grants or revokes no credit and infers no unknown package use. SKIP provides
neither a complete-analysis nor a reproducibility certificate.

Keep current applicability, primary-Python empty-result veto and per-package
iteration. Python coverage does not control this declaration-failure branch.
Keep FAIL-only severity overrides, suppression, thresholds and deterministic
sorting. An isolated WARNING or promoted CRITICAL can stop causing exit 1;
independent qualifying findings can still fail. Default text can show
`Findings: PASS` with a skipped count. Default export omits the converted
notable warning/critical finding, while complete JSON retains SKIP and unrelated
findings remain. Profiles, hints and init use the same captured inventory.

## Alternatives and required normative decision

Option B keeps the current captured-view missing-pin WARNING for these
omissions and leaves this gap OPEN. It must not be described as proving full
repository absence. NOT_NEEDED is not supported by source inspection: the two
omission routes exist, although maintainers may explicitly defer their policy.
Option A is recommended for the narrow extraction fact and existing consumer
reuse; its conservative cost still needs specific acceptance.

Prepare a new specification §12.3.13 for the exact predicates, code definition,
controls, traversal/first-cause behavior, preservation and compatibility cost.
Update §12.3.6's finite vocabulary and permitted bounded grammar extension, and
the relevant cross references that currently end at §12.3.12. Preserve §12.2's
Conda exact-version semantics and keep all other Conda grammar outside this
slice. D-M-CE is a local R07-C task label, not an architecture decision D-nn.

No engine, scanner, redaction, persisted schema, dependency, package-version,
five-project gold, historical validation or release change is proposed. No
D-41 protected module is changed by the three semantic additions. A necessary
change to such a module would require its own applicable review.

P-B follows a specific decision on option A, its concrete normative patch and
the costs above. Future tests must distinguish both omission branches from
retained controls, verify first cause and complete internal records/traces,
preserve credit and all uncertainty priorities, and check full findings,
evidence, presentation, exit behavior and unaffected consumers. Product
acceptance would then require the applicable final quality gate and fresh
five-project Gate A with affected extensions. This P-A review claims none of
those product gates as passed.
