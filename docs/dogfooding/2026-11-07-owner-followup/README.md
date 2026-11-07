# Owner follow-up: evidence and documentation acceptance

Date: 2026-11-07 (Asia/Shanghai). Assigned scope and acceptance:
[OWNER-01–05](../../plan/owner-followup-2026-11-07.md).
Starting main: `d73f45f2b5334cd05e382b86b137e37d9aabda12`.

## Tutorial integration: OWNER-02 / #16 / PR #17

Reviewed contributor head `e7581280ad6491d84f26aaf6a0916d31d18100a7`:
three documentation files, no workflow/product/dependency changes. The fork's
[initial CI](https://github.com/EnumaElish123/ReproLLM/actions/runs/42349531962)
was `action_required` awaiting first-contributor workflow approval, not PASS.
The GitHub connector rejected writes with integration HTTP 403. Existing local
Git credentials are used for authorized maintainer operations, without retaining
credential values.

The integration preserves the contributor commit as a merge parent. Maintainer
corrections remove two accidental commit-message lines (one broke a navigation
table), pin the external report and unreleased recorder, replace the install
placeholder, make interpreter selection explicit, refresh the offline lock after
prepare/env, archive before repeat, and distinguish reported local/live results
from an independently checked fixture. This does not merge application PR #2.

### Fresh, isolated fixture checks

Pinned external application:
`b09becc18b1b9cd0e4d6ac04ed61a7dcbb63554b`. The disposable clone contains a
fresh lightweight recorder/fixture environment: CPython 3.12.9, pytest 8.3.5,
27 compatible installed distributions. Local wheel installation was used;
all **148 installed product files** equal fixed `d73f45f` byte-for-byte.
The tutorial's VCS installation command is concrete but was not independently
repeated. Dependencies are recorded separately; a source pin is not a full
dependency lock. No original application/maintainer installation was changed.

The application source was inspected before execution. A process-inherited
guard rejects network connection/name-resolution attempts and heavy
model/provider imports during the checks. No local/live workload was run.

- Application's **20 offline tests pass**.
- **18 command receipts** match independent expected statuses: prepare baseline,
  capture environment, offline lock/check, preview, capture/verify/archive A,
  capture/verify/archive B, repeat diff, prepare/lock/capture/verify rounds-3,
  and drift diff (including the external test invocation).
- Each recorded run completes all eight stages. Report and trace repeat bytes
  are identical; baseline verification and rounds-3 checks pass. These include
  actual fixture client consumption and contiguous, fixture-only traces.
- Repeat diff exits 0 with no HIGH changes. Git bookkeeping from archiving is
  retained as an explained MEDIUM delta; it is not scientific drift.
- Rounds 5→3 diff exits 1, with exactly the two expected HIGH paths:
  `custom.workflow.chat_turn_limit` and the declared config-file hash.
  Accompanying variant/Git/metadata changes remain in the complete comparison.

[Machine-readable receipt](evidence/recipe.json),
[baseline checks](evidence/verify-baseline.json),
[rounds-3 checks](evidence/verify-rounds-3.json). Raw stdout/stderr are retained
privately by label and SHA-256; the public receipt contains no machine paths.
The [tutorial](../../tutorials/single-case-multimodal-app.md) and pinned
application helper provide the replay procedure.

Preparation failures remain recorded and are excluded from acceptance: a
first guard implementation broke SSL import before tests ran; the next attempt
exposed a missing trial environment and inaccessible default pytest temp area
(16 passed, 2 failed, 2 errors). A fresh trial venv and explicit disposable
pytest temp area resolved those prerequisites. A uv temporary-PE-resource access
error was followed by a successful workspace-temp retry and `uv pip check`.
None required changing application or product tests/code.

## Applicable gates and remaining scope

This is handwritten documentation/plan/navigation maintenance under validation
workflow §3. The local full product quality gate, five-project Gate A and Gate B
are **NOT_APPLICABLE_DOCUMENTATION_ONLY**, not PASS. No generated product
documentation is affected. Final content, links, Markdown, privacy, official
form lengths and unchanged product inputs are checked before the final push.
Exact final-main CI is verified separately after push.

Local documentation acceptance checks the destinations of 330 relative links
across 18 changed Markdown/JSON files, table widths, schema-versioned evidence,
added-text identity/path privacy, three ASCII field lengths/hashes and the
absence of product/test/schema/dependency/workflow changes. Unchanged historical
examples are not treated as newly introduced private data. Manual review also
checks public fixed-commit sources, contributor attribution, dated counters,
source-versus-release statements and the M1–M10 disposition. Generated product
freshness is NOT_APPLICABLE because no generated product document changed.

OWNER-01 evidence classification is [published separately](../../adoption/lingshu-2026-11-07.md).

## Public follow-up: OWNER-03 / M2–M5

OWNER-01 is `7f4d419`; corrected PR #17 integration is
`506dd87756161668c7c397f8171c9b626cb0042b`. GitHub confirms #17 merged and #16
closed at 2026-11-07T08:50:32Z. The [maintainer review](https://github.com/EnumaElish123/ReproLLM/pull/17#pullrequestreview-5811145099)
and one [#15 closure follow-up](https://github.com/EnumaElish123/ReproLLM/issues/15#issuecomment-6704715084)
are published using the owner account. No duplicate issue or contributor
identity was created.

The [post-merge GitHub inventory](evidence/github-state.json) has **0 open issues,
0 open PRs, 5 non-owner issues, 2 merged non-owner PRs and 2 contributing accounts**.
The two documented projects remain PI-01 and LS-01 with their different scopes.
README now links fixed public evidence; the adoption ledger preserves its
11-05 and older snapshots. [C01–C08](../../adoption/oss-evidence-2026-11.md)
maps each application claim to an explicit source and limit. PI-01's corrected
judge report was read at `9e3650282f4b72bfb3ccccdc0b4df45bec40ac34` without
re-running its research or recertifying the reported scientific results.

## Application and release handoff: OWNER-04–05 / M6–M10

The [current official-form check and English draft](../../adoption/a03-2026-11-07.md)
record public fields, actual 500-character limits, program/terms sources and
unverified browser conditional behavior. The three ASCII texts are **442 / 430 /
381 characters**, with byte/unit counts and SHA-256 in the linked length receipt.
Older application drafts remain unchanged, including historical resource states
that were superseded by later validation; this session does not repeat those
obsolete states as current blockers.

| Owner-plan item | Actual outcome |
|---|---|
| M1 | Complete: pinned LS-01 claim classification, with reported/private evidence boundaries. |
| M2 | Complete: one maintainer comment on the original #15, with exact fix and source/release distinction. |
| M3–M5 | Complete: refreshed ledger, README cases and source-linked claim index; genuine counts only. |
| M6 | Public official fields, terms and benefits checked; conditional live UI remains UNVERIFIED after browser binding timeouts. No selection/benefit is promised. |
| M7 | Three checked English texts; applicant inputs and primary role confirmed privately. Pro/Codex only selected, no optional security/credits; API-use draft stays unused. |
| M8 | **NOT_SUBMITTED / BLOCKED_BROWSER_URL_VERIFICATION**: browser tool could not confidently verify the current Windows browser URL and stopped UI operation. Live conditional-field review, final complete-form/terms decision and an actual receipt remain required. No fields were entered. |
| M9 | Complete for this scope: fresh PyPI/GitHub state and public docs consistently retain released 0.6.1 versus unreleased source 0.7.0. No release is attempted. |
| M10 | Ongoing genuine maintenance, not a fabricated activity target. No additional adopter, feedback or future outcome is asserted. |

The [release receipt](evidence/release-status.json) confirms 0.6.1 wheel/sdist are
not yanked, Python >=3.10 and retained Alpha metadata. No 0.7.0 index release is
present. The private application handoff now holds user-confirmed personal
fields and benefit choices; these are ignored by Git. No submission identifier
exists. The browser tool's URL-verification stop was respected; no alternate
form-submission mechanism was used.

Remaining resource gates are the existing three authenticated/paid Skill
integrations ([current status](../../skill-status.md)); they remain
BLOCKED_NOT_AUTHORIZED. Claude Code remains maintainer-deferred and the planned
independent Skill cohort remains unobserved. LS-01's private raw local/live and
fixed-probe receipts are unpublished evidence limits, not a request for a paid/GPU
rerun. M8 additionally needs restored authorized browser access or a manual
applicant handoff, live field verification and the final terms/submission decision.
No paid API, GPU, version/tag/release or fabricated external feedback is included.

## Commit and delivery references

| Task | Commit |
|---|---|
| OWNER-01 / M1 | `7f4d419` |
| OWNER-02 / #16 / PR #17 | `506dd87756161668c7c397f8171c9b626cb0042b`, preserving contributor `e7581280ad6491d84f26aaf6a0916d31d18100a7` as a parent |
| OWNER-03 / M2–M5 | `072976f` |
| OWNER-04 / M6–M7 | `4183cc7` |
| OWNER-05 / M8–M10 disposition | The commit containing this final handoff/report update; M8 remains input/terms-dependent and M10 ongoing. |

The first integration push starts
[CI run 42357177853](https://github.com/EnumaElish123/ReproLLM/actions/runs/42357177853).
It does not substitute for the final documentation delivery. For the final
push, check the [main CI workflow](https://github.com/EnumaElish123/ReproLLM/actions/workflows/ci.yml)
against the exact pushed SHA: all five job names/checkouts must match, each
required step must succeed, including the fourteen required Ubuntu 3.12 steps.
The final reply records that run and actual result; the private delivery receipt
retains the API response without introducing a self-referential report commit.
