# Current-product declaration-structure observations

Base: `88a26ee270c92c939140fe347b71f2909f8c7d97`. This packet executes only the
existing product. It does not apply or execute the proposed structure policy.

## Inputs, independent expectations and scope

[cases.json](cases.json) freezes 64 cases, 133 UTF-8 fixture files and 2,744 input
bytes. It contains every fixture byte, length and SHA-256, plus independent
current expectations written before execution from the existing source and
specification. Its SHA-256 is
`dc9d976583c066b68382ad248556e7f60d36bebbbe136b9d7d5b02033cc7e78f`.

The comparison includes complete declaration records (including physical/indexed
source positions), declaration-body issues, uncertain directories, qualified
project roots, lock inventories and credit, manifest presence, unparsed count,
Python coverage-gap state, applicability and **complete critical-rule findings**.
It is not an independently specified full audit report. Full unparsed strings,
imports/coverage, reader calls, candidate checks and the two presence-rule
results are also retained for review, without claiming an independent full-output
oracle for every one of those supplementary fields.

| Cases | Independent question |
|---|---|
| S01–S09 | Missing/empty/tool-only controls and present wrong `project`, `tool`, `tool.poetry` containers, including falsey values |
| S10–S20 | PEP 621 list/container/member types; valid empty controls; retained exact members beside unsupported members/groups |
| S21–S27 | Poetry dependency-container failures; multiple-constraint arrays, transport objects and version values kept outside the proposed structure slice |
| S28–S35 | Pipfile section containers versus package-value grammar; retained exact member in the other valid section |
| S36–S47 | Empty/null YAML document versus explicit wrong root; absent dependency field versus null/false/map/string versus empty list |
| S48–S56 | Conda list members, unknown installer mappings, `pip` null/false/map/string versus valid empty; partial exact entries |
| S57–S62 | Repository-wide exact/qualified positive credit, existing D-M/D-F/D-L precedence, no invented package use |
| S63–S64 | Readable requirement grammar and empty pip strings remain outside this structure slice |

The `proposal_mapping` booleans classify 39 fixtures as belonging to the proposed
bounded structure slice. They are prewritten design expectations, **not observed
new typed facts**. All `future_policy_executed` values are false. In particular,
legal Poetry multiple-constraint values and transport dictionaries are controls;
their current lack of exact credit is not evidence that the external format is
invalid. An empty issue inventory never certifies complete dependency grammar.

## Actual observations

[current-observations.json](current-observations.json) records the first actual
run: **64/64 independent expectations matched**, no failures or expectation
corrections. There were 58 FAIL/WARNING critical-rule findings and three existing
SKIPPED/INFO findings (D-M, D-F and D-L respectively). Two positive-credit cases
and one no-known-use case returned no critical-rule findings; no engine PASS
was synthesized by this observer.

Structural failures currently do not add `DeclarationReadIssue` values. Existing
exact entries are retained even when sibling entries are skipped. The examples
with exact torch and incomplete sibling material keep torch credit while numpy
still receives the current missing-pin warning. S57 and S58 show that unrelated
structural failure and malformed siblings do not erase existing exact/qualified
credit. S59–S61 exercise existing uncertainty branches, not proposed ones.

The observer used real `RepoScanner`, dependency parsing, Python AST scanning and
three env rules with an actual `AuditContext`. Controlled inputs are
`GitInfo(is_repo=False)` and an empty installed-version inventory. Thus no Git
subprocess is needed inside product observation and suggestions do not vary by
installed research packages. An audit hook rejects socket operations, process
creation and heavy-framework imports. It observed zero forbidden attempts.

The first run made 133 existing reader calls. Eleven selected source/spec files
matched their candidate Git blobs byte for byte before execution and kept the
same bytes afterward. Twelve read-only Git commands establish those identities;
their exits, times, lengths and output hashes are retained. This is a bounded
source identity check, not a claim that every repository file was inspected.

First-run product observation wall time: **0.368127 seconds**; whole observer:
**1.079540 seconds**; outer command: **1.5139764 seconds**, exit 0. These timings
overlap and must not be added. The public record appends a clearly identified
outer tool receipt to the original record; the original record hash/length and
the exact transformation are bound in that field. Business observations are
unchanged.

## Replay and limits

[observer.json](observer.json) preserves the exact observer source as inert UTF-8
text, its SHA-256 and replay instructions. Extract it to a private file, verify
the hash, then run it in the specified candidate checkout with the locked
environment and a **new** disposable output directory. Do not execute it against
arbitrary newer product bytes or reuse an existing observation directory.

[replay-receipt.json](replay-receipt.json) records extraction and replay of that
archived source. The replay again matched all 64 prewritten expectations, and
all 64 retained `actual` objects were exactly equal to the first run, including
full findings, diagnostics and reader traces. Only timestamps, measured timings
and outer receipt metadata are excluded from cross-run comparison. The replay
observer took 0.877326 seconds, with 0.339697 seconds in product observations;
its original raw record remains hash-bound in the receipt.

This packet does not run the complete CLI/engine, profile override or suppression
pipeline, text/export renderers, pytest, the complete quality gate, the five-project
Gate A, resource Gate B, a package manager, model, provider or paid API. It does
not validate future policy outcomes or promote source-derived expectations into
future P-B acceptance. Those require the separately accepted policy and its
formal regression and final-session gates.
