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

OWNER-01 evidence classification is [published separately](../../adoption/lingshu-2026-11-07.md).
Public adoption/application follow-up and remaining identity/submission
dependencies are recorded here when completed. Application submission remains
NOT_SUBMITTED until an actual successful submission is observed. No paid API,
GPU, version/tag/release or fabricated external feedback is included.
