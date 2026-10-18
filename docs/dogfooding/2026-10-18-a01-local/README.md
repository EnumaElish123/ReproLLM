# A01-A / A01-B local evidence session — 2026-10-18

Scope: close the actionable input inventory and the resource-free replay layer
under [the current plan](../../plan/reliability-2026-10-03/06_Validation_and_Adoption.md).
Paid APIs, model execution and version publication are excluded. Formal resource
acceptance remains **BLOCKED**.

## Baseline and artifact identity

- Starting main: `8d713c78d8081f4b69051acc50542ff70b8dd662`; clean and already
  up to date after `git pull --ff-only` through the configured local proxy.
- A01-A task commit: `5b675ae9289ae60245645db7d0616ec6a279dc0a`.
- Product code, profiles, templates, dependencies, schemas and packaging behavior
  are unchanged. No fixture snapshots or validation gold are updated.
- The actual S4-B wheel is reused: `reprollm-0.7.0-py3-none-any.whl`, SHA-256
  `0be12d1d44a07e1ab29459c161cf67fcdc48a0934d1e57d593cc5887ac6049ff`.
  Its original build source stays
  `a4d895d4f30f6f74421d7f1cd96606f9b0baba15`; all 141 package payload files
  independently match the current product source byte for byte.
  See [candidate identity](candidate-wheel.json) and the unchanged
  [build manifest](build-manifest.json). A manifest tag string does not create a tag.

The initial unused build preparation hit Windows path length and sandbox cache
limits. No wheel was produced or substituted; recovery of the already validated
wheel avoided another build. [Preparation receipts](preparation-attempts.json)
retain the bounded failures and raw-log hash.

## A01-A: input inventory and recovery

[Input readiness](input-readiness.md) and [the complete inventory](input-inventory.json)
cover **50 required input slots** with prior independent SHA-256 expectations:

| State | Slots | Meaning |
|---|---:|---|
| AVAILABLE | 12 | Exact original bytes recovered; 8 distinct byte identities |
| MISSING | 5 | Original val §8.1 metadata manifests were already missing historically |
| ACCESS_BLOCKED | 33 | Required bytes are not locally present; the remote evidence connection times out |
| HASH_MISMATCH | 0 | No replacement file was accepted under an original identity |

Twenty public files are retained: twelve case inputs, four supporting dependency
files and four licenses. Original driver text is inert; no driver is executed.
The six lm-eval A/B light inputs are complete. Other native cases, original
metadata, Linux H2 and the formal judge cannot be reconstructed completely yet.
The inventory includes archive members and final Git objects needed for recovery,
and distinguishes original, H2 supplementary and promoted native identities.

The search covered current light repository files, embedded evidence documents,
known task scratch locations and all reachable light Git blobs. It did not
reconstruct missing files from prose, inspect credential contents or scan
unrelated user directories. The SSH failure occurs before authentication and
does not demonstrate a model-author access denial.

Independent checks recomputed all twenty stored hashes and byte sizes, matched
the twelve available inputs to their independent source hashes, validated two
manifests, parsed six YAML inputs and AST-parsed six inert driver copies.
The local `.gitattributes` prevents Git newline conversion of evidence; staged
artifact bytes are checked against working bytes before each task commit.
The unchanged raw build manifest and some Windows artifacts retain CRLF;
original CLI audit streams also end with a blank line. Source/narrative outside
this fidelity bundle passes ordinary Git whitespace checks. Within the bundle,
process-local checks retain trailing-space/indent checks while allowing CRLF
and original EOF blank lines; original evidence is not rewritten for style.

## A01-B: resource-free replay

The executable entry is
[`scripts/a01_local_replay.py`](../../../scripts/a01_local_replay.py).
It reuses D02's installation and import-isolation helpers, D01's hash-reviewed
recipe and the independent standard-library consumer. It adapts only disposable
manifest name/command fields and labels that case supplementary.

The [replay guide](replay-guide.md) documents artifact acquisition, installation,
independent expectations, commands, output checks and remaining limitations.
The [replay package](replay/) contains actual safe run/lock/diff/export evidence,
consumption receipts, complete drift and checksums. The second replay starts
from a separate copy of the public input package and a new clone and environment.

Accepted execution: **44 commands, 6 completed captures, 2 independent installed
environments**, 40.813 seconds wall time. Ordinary commands exit 0; each A/B
`--fail-on HIGH` diff exits the expected 1. Both pairs contain exactly the
three expected non-NONE paths. Independent review confirms all 108 replay
checksums and all 36 snapshot references, sizes and byte hashes.

The tool requires actual consumption of cap 32 / 48, exact input snapshots,
manifest/lock/output hashes, expected complete semantic drift, empty self-diff
and selected historical exports. The consume-then-mutate case must retain
consumed/pre-child cap 32 while exposing post-child cap 96 and its changed hash.
Recorder consumption and child environment remain explicitly unverified; the
independent receipt establishes only this bounded child/config observation.

The new tool has **26 passing focused regressions**, including forged receipts,
changed snapshots, duplicate/missing drift, wrong wheel identity, path escapes,
secret and machine-path rejection, benign source escapes and clone-byte
preservation. [Regression receipts](replay-regressions.json) retain RED/GREEN
observations. [Replay attempts](replay-attempts.json) preserve rejected earlier
environment/input/guard attempts; only the final frozen-tool run is accepted.

[Focused offline regressions](offline-regressions.md) add **272 passing tests**:
18 HF/lock resolver tests, 9 HF client boundary tests, and 245 synthetic privacy
and fidelity cases. They are mock/synthetic evidence, not successful live access.

The [five-project offline discover previews](discover-previews/README.md) add
five successful, read-only collector commands using the installed candidate
wheel and D02's network guard. All source pins, clean states, selected source
paths, budgets and the second redaction pass are checked. No request is sent.
These supplementary previews use uninitialized pinned source and do not replace
the missing original manifests or formal live-discover validation.

## Validation classification and remaining resources

This is a **validation-tool and documentation session** under the
[authoritative workflow](../../plan/validation-workflow-2026-10-13.md#3-执行频率唯一权威定义).
New tool positive/negative regressions and one final complete quality gate apply.
The initial full run used a Windows token without symlink privilege and an
inaccessible previous temporary directory. It is rejected, with raw hashes in
[quality attempts](quality-attempts.json). The unchanged inputs are rerun in the
established administrator context after six focused permission tests pass.

The [accepted final quality receipt](quality-summary.json) records 20 successful
commands on 497 frozen inputs: **2,800 passed, 4 skipped, 4 deselected**, overall
coverage **93.76%**, redaction line/branch coverage **100%**, and **203 security
tests passed, 2 skipped**. Ruff, formatting, mypy, all four generated-document
freshness checks, examples and self-audit pass. The complete
[tested-file hashes](quality-inputs.json) bind the final tool/source inputs.

Fresh Windows schema exports differ from Git LF bytes only by CRLF. The initial
auxiliary comparison incorrectly required raw LF bytes; the same original
exports were re-compared using the already accepted S4-B/D02 CRLF-only policy.
[Schema comparison](schema-comparison.json) preserves all ten original export
hashes and the raw-equality false result; filename sets and every other byte
remain strict, with added-space/missing-file rejection checks. No export or
product test is relabeled as re-executed by that comparison correction. Linux
CI must still pass its exact-byte schema export check on the pushed commit.
Product five-project Gate A is **NOT_APPLICABLE** because this session changes
no product/default/profile/template/dependency/schema/packaging behavior.
No previous Gate A result is relabeled as a fresh pass.

[Read-only peer review](peer-review.json) was performed by a separate agent in
this same author-operated session. It independently checks input provenance,
license blobs, all replay snapshots/checksums and the five collectors' 215
selected entries against 81 distinct pinned source files. It reports no
remaining must-fix finding; it is not an external user's trial or adoption.

[Resource readiness](resource-readiness.json) records the local GPU query and
specific next actions. The [standing ledger](../pending-resource-validation.md)
retains all historical acceptance boundaries.

| Resource gate | Current blocker | First action when provisioned |
|---|---|---|
| VAL-R01 | Missing/inaccessible exact inputs, isolated Linux framework environments and formal GPU guard; local total VRAM is 16,376 MiB versus at least 70,000 MiB free required | Restore input members and verify hashes, then run the remaining four native pairs on a compliant Linux runner |
| VAL-R02 | Exact local judge bundle inaccessible; no paid execution or current provider/budget provisioned | Restore A/B identity and bounded transport, then obtain the specific current preflight and execution provision |
| VAL-R03 | Original Project C manifest missing; author-approved access and token not provisioned | Restore that manifest, establish independent successful-file expectations, then read only approved small metadata files |

Linux H2 needs no GPU, but its five exact supplementary manifests are inaccessible
and no Linux replay is claimed here. CPU probes and HF mocks do not replace any
native, authenticated-success, paid judge or release resource gate.
Provisioning belongs to the maintainer and the relevant input-store/GPU/provider
account operator, as recorded per item in the resource receipt. If an original
manifest cannot be recovered, a separately reviewed new case is required;
reports, public questions or a same-named substitute do not restore its identity.

## Handoff

Continue restoring the specifically listed unavailable inputs. Keep their exact
hashes and formal status; alternate small-card cases require separate reviewed
inputs and resource limits. P-A policy proposals remain independent decisions.
The shareable local replay can support A02 material preparation, while actual
independent user adoption remains unobserved.

No paid API, model weights, inference/training, model-access request, tag,
package publication or external invitation is performed. Final main CI must be
checked against the actual pushed commit; its confirmation is provided in the
session's final response and local CI receipt, after this report is committed.
