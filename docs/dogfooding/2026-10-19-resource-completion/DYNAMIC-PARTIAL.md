# Provider and failed judge-capture overlay

This is an observation-stage supplement for candidate
`750270b10307455795fcff126664429dc895983a`. The [completed native matrix](native/final-summary.json) contains ten original
children, five independent pairs with 35 total changes, and twenty accepted
native export states. The [final dynamic manifest](dynamic-files.json) binds the
source and retained byte identities. Formal judge capture remains FAIL. No
resource command is launched by packaging this evidence.

## Provider preflights and current authorization

The [direct preflight](providers/preflight.json) retains HF `ConnectError`
results and a successful DeepSeek model-list check. The separate
[HF proxy preflight](providers/preflight-hf-proxy.json) verifies authentication
with HTTP 200 while both gated Llama-2 small files return HTTP 403. Authentication
does not establish model-author file permission. These preflights sent no paid
completion request and retain only credential-presence booleans.

The [current paid authorization](providers/budget-authorization.json) permits
at most two formal judge attempts within CNY 3, with no retry, the original
256/384 caps, 90-second deadlines and conservative reservations. It authorizes
no substitute payload or unrelated spending.

The [latest GPU authorization](providers/gpu-sharing-authorization.json) records
the maintainer's replacement instruction: “只要GPU有空闲显存，即可使用，无需考虑人为设定的资源限制”.
Its policy is `hardware_capacity_only`; prior numerical idle/used/free/disk
thresholds are superseded for the two remaining B validations. GPU 0, the
original bounded workloads and memory fractions, sequential exclusive lease,
and preservation of other processes remain recorded in that authorization.

This receipt binds the two launches in this replay. Standing guidance for later
validation is recorded in [val.md](../../../val.md); the narrow replay receipt
does not reduce the scope of the maintainer's general instruction.

The [initial bounded authorization](providers/gpu-sharing-authorization-initial.json)
and [three followup observations](providers/gpu-sharing-followup-observations.json)
are historical. No child was launched under that initial numerical allowance.
The [phase receipt](providers/sharing-prelaunch-phase.json) refers to that
pre-replacement observation stage. The [retrospective no-launch note](providers/gpu-initial-sharing-no-launch-note.json)
explicitly labels its source as the session transcript, rather than an original
process receipt. It does not invent a missing stdout hash or instantaneous GPU
reading. The final matrix distinguishes eight original strict launches from
two launches under the latest capacity-only direction and retains each guard.

## One real judge A response; capture acceptance FAIL

The [independent provider review](judge/a/provider-review.json) distinguishes
one successful real request from failed complete capture acceptance. The A
child exited 0, the original parser returned observed score 7, all four binding
values matched, and the [transport proof](judge/a/outputs/transport-proof.json)
records cap 256, temperature 0, thinking disabled, model identity, usage and
message digest. Score 7 is an observation, not an expected quality score.
Returned usage gives a peak-tariff estimate of **CNY 0.001394**; an account invoice
was not verified. The [budget ledger](judge/budget.json) records one attempt.
The second completion was not sent after the capture failure; remaining budget
was not reallocated.

The original [run record](judge/a/run/run.json),
[manifest](judge/a/run/manifest.yaml), [lock](judge/a/run/lock.yaml) and exact
`files/` snapshot directory are preserved unchanged. RunRecord uses the current
normative **schema 2**; surrounding evidence receipts use schema 1. Packaging
neither fabricates the missing snapshot nor substitutes a corrected rubric.

Two product findings prevent formal capture acceptance:

1. The required `fastchat/llm_judge/common.py` snapshot is absent even though
   its pre/post input hash remains correct. The
   [CPU diagnosis](judge/diagnosis-judge-snapshot/diagnosis.json) and
   [causal probes](judge/diagnosis-judge-snapshot/causal-probes.json) isolate a
   valid Python f-string being treated as a structured fragment, followed by an
   unsafe-context decision spanning a later independent symbolic API-key
   assignment. The [accepted inert reproducer](judge/diagnosis-judge-snapshot/minimal_valid_repro.inert.py.txt)
   contains no actual secret. Rejected invalid-Python minimization is not used
   as acceptance evidence.
2. Four unrelated multi-turn rubric records have changed non-secret prompt
   templates in the stored snapshot. The
   [CPU diagnosis](judge/diagnosis-judge-rubric/diagnosis.json),
   [causal probes](judge/diagnosis-judge-rubric/causal-probes.json) and
   [inert reproducer](judge/diagnosis-judge-rubric/minimal_jsonl_repro.inert.py.txt)
   show serialized role-label newline escapes being interpreted as Windows
   paths. The selected `single-v1` row stayed unchanged, but that does not pass
   the required complete-file fidelity check.

Both diagnoses preserve the original A capture, execute no additional paid
request or GPU work, and propose a separately scoped product repair with
security/fidelity regression requirements. They do not relabel this run PASS.
The [terminal native review](native-observers/terminal-evidence-review-final-1.json)
confirms all ten children and five exact pairs. The [final local-state check](readiness/final-local-state.json)
confirms all five original checkouts remain clean at their pins and both native
package inventories still match the installation proofs. HarmBench generated
content and content-bearing streams are excluded; their hashes and byte lengths,
original run metadata/inputs, token lengths and classifier results are retained.

The A [failed-state export](judge/a/REPRODUCIBILITY.md) rendered successfully
after the capture failure was known. That execution is separate from the twenty
accepted native export states and does not validate the failed upstream capture.
