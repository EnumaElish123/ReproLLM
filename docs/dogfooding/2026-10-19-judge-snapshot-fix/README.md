# R02-R judge snapshot repair — 2026-10-19

**The two demonstrated snapshot defects are repaired and VAL-R02 passes on
`75d1b065e9f0e3eeafa8e480e195a2a2ddbe95b5`.** Both real DeepSeek judgments,
complete source capture, semantic pair, self-diff and affected export checks
pass. The shared quality gate and fresh five-project Gate A use these same
product bytes. This is an unreleased repair; no release, tag or publication is
performed.

The assigned scope is the R02-R follow-up in the [backlog](../../plan/backlog.md),
under specification §§5.1, 16, 18–19 and [val §§8.4–8.4.1](../../../val.md#84-approved-deepseekfastchat-supplementary-judge-2026-09-27).
The earlier `750270b` paid A remains a historical capture **FAIL**, with B
**NOT_RUN**. Its inputs, failed run and ledger are unchanged in the
[original resource report](../2026-10-19-resource-completion/README.md).

## Repair and task commit

`75d1b06` — `fix(run): preserve Python and JSONL judge snapshots (R02-R)`.

Python capture now uses bounded syntax and token contexts to distinguish source
code, symbolic lookups, decoded literals, secret keys and comments. A valid
f-string followed by a symbolic API-key assignment no longer causes the whole
`common.py` snapshot to be omitted. Safe source remains byte-identical;
literal secrets, machine identity and actual absolute paths remain protected.
Unknown calls keep secret context, and unsupported/unsafe input still fails
safely.

JSON and JSONL path checks operate on decoded strings. The rubric's role label
`A:` followed by escaped newlines no longer looks like a Windows drive path.
All eight original rows survive unchanged, including unused multi-turn rows.
Real drive paths, UNC/Unix paths, file URIs, contextual secrets, nested serialized
values and malformed unsafe input retain protection. Capture failure isolation
and the child's exit status remain covered.

The tests were written before implementation. Both original minimal symptoms
fail on the parent; the complete public files, real child capture, privacy
controls and an exit-7 child pass after repair. The source fixtures retain
upstream provenance and the Apache-2.0 license. No normative policy, schema,
gold answer, dependency or package version changes. Product version remains
unreleased 0.7.0; captured runs use schema 2.

## Shared local quality and five-project validation

| Layer | Accepted evidence |
|---|---|
| Focused acceptance | 550 run, binding, integration and redaction tests pass; RED failures and later corrections are retained |
| [Final quality](quality/summary.json) | 24 checks PASS; 3,004 tests, 2 slow deselected; 94.02% coverage; core redaction 100% including branches; 345 security tests; lint, format, strict types, ten schemas, generated documents, examples, self-audit and installed distribution checks pass; 572.222 s |
| [Five-project Gate A](gate-a/summary.json) | All five pinned sources and origins verified clean before/after; ten fresh complete L0/facts JSON comparisons, 32 assertions, 51 commands; zero gold deltas; 87.955 s |
| [Affected CPU capture extension](cpu-capture/summary.json) | Ten real stdlib children across all five projects; original common/rubric bytes; four independently witnessed consumed bindings; complete pre/post capture; 670 complete State leaves; five A/B pairs with all 35 differences explained; empty self-diffs; ten selected-run exports with 610 comparisons; 155 commands, 230.321 s |
| [Installed wheel](installation/proof.json) | All 143 payload files match the candidate wheel; Python 3.11.12 and 274 other distributions unchanged; installed origins checked before and after each formal run |
| [Independent observer qualification](tool-selfcheck/judge/summary.json) | 13 positives and 52 negatives pass, including separate rejection of the original missing-Python and changed-JSONL failures, input mutations, real paths and secret contexts |

Source inventory: `770373f46d86f78f256bdf748b7d8773c4a3fb929cd2ef9a3b5996a57af1bfa7`.
Candidate wheel SHA-256: `3d1b83b4488064664e776ddaae495776cd12847e9a0d8690d00e7263d877ece3`.
The independent baseline index is
`06d04134b580257b5c63fc297a50f4635fba874e24f5176737b0b7655bc9cf80`.
The process-local Git compatibility shim is hash-bound in the quality receipt;
its use changes no project source or gold. All commands retain exit status,
elapsed time and complete output through the evidence manifests.

The CPU extension is deliberately separate from a native GPU/model run or paid
judge. Its independent supplement additionally checks 50 committed inputs,
20 manifest/lock snapshots, package metadata and all six judge/four consistency
rules per capture. ReproLLM itself continues to report child consumption and
child environment as unverified; independent witnesses do not change that
product contract.

## Formal DeepSeek A/B

The [fresh authorization](providers/budget-authorization.json) permits CNY 3
total, two attempts, no retry and a
90-second request deadline, bound to this candidate. The four original Variant A
input hashes match val §8.4. The original entry, transport, prompt builder and
parser are retained. The provider model-list check confirms `deepseek-flash`.
The installed candidate first passes the original mocked transport contract,
offline lock/check and pre-child audit.

Only public MT-Bench question 82's first turn, the original `single-v1` rubric
and the fixed synthetic email answer are sent. The request body stays within
4,000 UTF-8 bytes; temperature is 0 and thinking is disabled. No project source
or private research content is sent. This judge scenario requires no GPU.

| Variant | Run | Actual cap | Completion / prompt tokens | Original parser score | Peak-tariff estimate |
|---|---|---|---|---|---|
| [A](judge/a/acceptance.json) | `20261019T050959Z-fd958c` | 256 | 109 / 245 | 7 | CNY 0.001362 |
| [B](judge/b/acceptance.json) | `20261019T051148Z-a5abee` | 384 | 123 / 245 | 7 | CNY 0.001474 |

Both finish with `stop`, exactly one attempt each. A passes complete acceptance
before B is prepared and sent. Scores are observations, not fixed gold. The
[separate new ledger](judge/budget.json) records two `usage_received` entries and
CNY **0.002836** total at the verified peak tariff, below the approved ceiling.
This is a usage-based estimate, not an account invoice. See the
[official tariff](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/) and
retained authorization.

Each run independently checks six input files, eight pre/post input entries,
two output artifacts and eleven persisted run files. All original input bytes
remain unchanged before/after; all four effective bindings agree with the
actual transport. Each current audit has six judge rules PASS. Complete
upstream findings remain visible and identical across variants: 5 critical,
19 warning, 3 info, 30 pass, 14 skipped, zero suppressed. Their presence is not
silently converted to a clean upstream audit.

At FastChat pin `587d5cfa1609a43d192cedb8441cac3c17db105d`, both captures retain:

- `common.py`, 22,379 bytes, SHA-256 `71c3b317322845cb05eb6d9b555b03e5084fa59085d24989ce521fcfa8bdc9a7`.
- The complete eight-row rubric, 10,449 bytes, SHA-256 `fd283293406d024f44c174b094ef48031d0687a4682fd3a56b29b138f80281b6`.

The [complete pair acceptance](judge/pair-acceptance.json) explains every change:
direct `evaluation.judge.params.max_tokens` 256 → 384 is **HIGH**, its original
config hash is **HIGH**, the clean disposable input commit is **MEDIUM**, and
four run/time fields are **NONE**. There are no additional unexplained changes.
The actual `--fail-on HIGH` exit is 1; self-diff is empty; full findings and
profiles agree. Historical pre-R08-A MEDIUM evidence is unchanged.

The [A](judge/a/export-independent-check.json) and
[B](judge/b/export-independent-check.json) selected-run exports pass 77
independent comparisons each (154 total),
with complete projection checks,
including historical snapshots, current-tree audit, all effective sections,
run2 input table, environment/hardware scope, alias limitations, diagnostics
and command receipts. Export acceptance does not substitute for source capture.
The closed-source API alias remains unpinnable and observation-based.
The [independent terminal observer](judge/independent-terminal-observer.json)
adds 214 complete capture/provider/pair comparisons and independently projects
all 114 self-diff leaves, without another product command or provider request.

## Observer corrections and evidence integrity

A's provider request and independent capture verifier succeeded on the first
attempt. A later controller assertion compared a typed `SecretPresent` object
directly with its serialized dictionary. The controller was corrected to check
the typed object's serialization against `{present: true}`; the existing A raw
record then passed. No request or product run was repeated. The original
failed verification, prior controller and hash-bound correction receipt remain
available. B used the corrected observer and passed directly.

Earlier observer qualifications, including a profiles-object shape assumption
in the CPU supplement and safe source strings in the path checker, retain their
failed receipts where applicable. They were corrected against immutable raw
outputs and independently qualified, without changing gold or product bytes.
The terminal observer also corrected a missing expected producer-version field
over the same raw data. Its initial tool response is explicitly retained as a
retrospective transcript, and the reconstructed prior helper is labelled as
such; neither is claimed to be an original captured stream.
The final code received its complete quality gate only after all product fixes.
Subsequent controller, packaging and report changes are validation-tool or
report-only work under the validation workflow; they do not require repeating
the unchanged full product gate.

The stable/dynamic manifests bind every retained source selection to its
original and retained size/hash. Twelve original run trees preserve all 122
original product files byte-for-byte. There are 1,013 hash-bound source selections;
the initial packaging audit checks 502 files, before adding its own receipt,
this session report and closing scans. Other sharing copies explicitly transform local paths,
machine identity and synthetic security canaries; transformed inert helpers
are not executable original replay claims. Large local coverage/inventory or
binary artifacts retain hashes rather than being committed. Packaging audit,
[link checks](closure-checks.json) and an
[exact scan for the configured credentials](credential-scan.json) close the bundle.
The closing scan supersedes the pending scan marker in immutable packaging
receipts; it does not rewrite those earlier receipts. A closing metadata-key
false positive is qualified in a [separate receipt](closing-portability-check.json),
with the original audit unchanged.
No credential value, prefix or length is included in the scan receipt. Original-source trailing whitespace and raw transcript
terminal blank lines are retained deliberately; whitespace diagnostics in those
evidence files are not repaired by changing their hash-bound bytes. Authored
report and tracking-document whitespace checks pass.

## Delivery and remaining scope

The repair task commit and this separate report-only closure are delivered to
`main` after local acceptance. Five-job CI is checked on the actual pushed
closure commit and reported in the session's final reply, without modifying
these immutable run receipts afterward. The pre-existing main-worktree user
changes are preserved byte-for-byte and excluded from commits.

VAL-R01 remains accepted at **`750270b`** for Linux H2 and ten native GPU
children; this repair does not claim a new native matrix on `75d1b06`. VAL-R03
remains **BLOCKED** by the last authenticated HF small-file 403 results and
missing original metadata inputs. Five original §8.1 manifests remain missing.
No HF, GPU/H2, discover, independent trial or full release matrix is rerun by
this targeted repair, and no release readiness is inferred.
