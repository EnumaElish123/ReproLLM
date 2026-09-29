# M4–M6 Linux resource validation — 2026-09-26 to 2026-09-27

Source: `main` at `ea7049489d9e2053bfa84288fe56c3b60d51b87f`. This session
prepares resources and validates existing functionality; it does not change
ReproLLM implementation, package dependencies, upstream pins or release versions.
Unrelated untracked `plan/` files were left untouched.

Latest reviewed status (2026-09-27): the supplementary DP pair, the approved
DeepSeek real judge pair and lm-eval's real inference/cap-drift checks completed.
The lm-eval snapshot-fidelity defect and DeepSeek audit/profile/provider
limitations remain open. LlamaFactory, local FastChat and HarmBench still await
verified weights and real execution. This is **not** completion of all M4–M6
acceptance gates. Detailed results, failed attempts and remaining human/resource
gates follow chronologically below.

## Authorization and resource status

The maintainer authorized public downloads under `/mnt/share_data/czy/` and
bounded GPU use that does not disturb existing processes. They explicitly
deferred the paid FastChat judge until API configuration is supplied, and allowed
a public-small-model **supplementary** DP case without passing the original
gated Llama-2 case.

Initial observations (2026-09-26; later changes are recorded below):

| Resource | Observation and decision |
|---|---|
| CPU / memory | 128 logical CPUs; approximately 1 TiB RAM; ample for short validation |
| GPUs | Two A800 80 GiB cards; card 0 has about 78 GiB free; card 1 has an existing approximately 14 GiB allocation and is excluded |
| Existing processes | Left running; no process termination, reset, driver change or scheduler modification |
| Driver / toolkit | Driver 535.216.01; system toolkit 12.2.91 exists outside PATH |
| CUDA smoke | Existing isolated torch environment, card 0 only: a 1024×1024 matrix product returned 1024; synchronized successfully; peak allocation 16.12 MiB |
| Post-smoke GPU usage | Returned to the initial readings: 753 MiB on card 0, 14127 MiB on card 1; neither card showed active compute at the checks |
| Download disk | Approximately 186 GiB free; avoid duplicate weight formats and retain 50 GiB reserve |
| Download permission | Initial permission blocker resolved by the maintainer; dedicated `reprollm-validation` directory is writable, owner/group match the session, mode 0750 |
| Official HF endpoint | Unreachable in direct probes; existing proxy also fails; process-local proxy bypass plus `HF_ENDPOINT=https://hf-mirror.com` works |
| API credentials | No paid API request attempted; deferred by maintainer |

The GPU smoke proves basic CUDA compute, not model inference, vLLM compatibility,
M5 capture or M6 real paired-run acceptance.

Detailed primary-source compatibility checks are in
[`m4-m6-resource-compatibility.md`](m4-m6-resource-compatibility.md). They identify
the exact official CUDA compatibility package and torch wheel, a candidate
modern vLLM/LlamaFactory environment, and a separate legacy DP environment.
The DP environment passed package/import checks, a CUDA smoke and real paired
training. The modern environment subsequently passed installation, imports and
real CUDA/vLLM execution on 2026-09-27; see the follow-up below.
No global environment or system driver was modified.

## Preparation artifacts

Small validation drivers, manifests and evidence are outside the ReproLLM
worktree in `../dogfooding/m4-m6-20260926.6OgZhb/` (relative to the repository).
The directory includes:

- `metadata-inputs/`: five reconstructed metadata-only manifests;
- `validate_metadata.py`: exact commands, independent gold assertions and timings;
- `commands.json`: sanitized command records, expected/actual exits and output;
- per-target Level 0/2 reports, hints and offline/two-online locks;
- `download_resources.py`: pinned public download preparation, mount-boundary
  check, free-space reserve, per-file size/LFS integrity checks and inventory.

The initial permission guard exited before downloading. After the maintainer
fixed the directory, preparation resumed there. Qwen2.5-0.5B and DistilGPT2 files
are downloaded with exact-size/LFS SHA-256 verification. The official CUDA
compatibility package was verified and extracted locally, not installed into the
system. Qwen3, Vicuna and classifier weight downloads remain in progress; the
modern isolated environment is now installed. Partial files are preserved for resumable
downloads; existing completed files are verified before reuse.

Following primary-source mirror checks, the same resumed CUDA runtime wheels
use the official PyPI host plus verified Huawei/Tsinghua byte-equivalent mirror
URLs, and Qwen3 shard 2 can additionally use the publisher's fixed ModelScope
URL. Complete-file official SHA-256 and byte counts remain mandatory; no model
revision, package version, existing verified file or gold answer changes with
transport choice. Only this session's download workers were restarted; unrelated
processes were untouched. Transfers retain per-file bandwidth limits.

The planned public weight set is Qwen2.5-0.5B-Instruct, Qwen3-4B-Instruct-2507,
Vicuna-7B-v1.5, HarmBench-Llama-2-13B classifier and DistilGPT2, each at an exact
revision. One weight format per model totals approximately 45.5 GiB, before
environments, caches and small outputs. The protected Llama-2 weight set is
excluded. Every remaining file must pass downloaded-byte integrity checks before use.

Runtime checkouts and evidence are in `cases/` and `evidence/runtime/` beneath
the dedicated resource directory. `runtime_gate.py` captures command exits and
timings, checks available GPU/disk before launch, uses the same validation
environment for ReproLLM and its child, and compares hashes, bindings and exact
semantic leaves. The activated bounded scenarios and their pre-execution gold
are in `val.md` §8.3 and the independent runtime review. A recorded failed child
will remain a failed scenario, even if ReproLLM successfully captures it.

The complete pre-execution A input bundle is retained as
`evidence/runtime-inputs-a.tar.gz`, SHA-256
`9598520f3ebe3ce49f0180826031291cdce6b95c71dadc2a34fc0a6adf4e1921`.
It contains all five manifests and their validation configurations/drivers,
including the synthetic DP text fixture; no weights or credentials. Later input
corrections must retain this original bundle and identify their new bytes.

Pinned GSM8K resources are prepared on the data volume: 7,473 train and 1,319
test rows at `740312add88f781978c0658806c59bc2815b9866`. Independent hashes of
UTF-8, sorted-key, unescaped JSON rows with one trailing newline each are
`9556bf9d7dba73d7fcaaeff6ca814c71684db1d8e8d485d83ec62f1c428b888d` (train)
and `51b901a6559b123df91167acbe3ed6d6d5d404ee6fa0773a4da19fd9d44c767a` (test).
This used an existing datasets interpreter read-only for cache preparation;
no package was installed into that existing environment and no GPU was used.

## Pre-execution findings

1. **Fractional epoch contract mismatch.** Specification §3 declares
   `training.epochs: number?`, but `schemas/manifest.py:234` uses `int | None`.
   Validating a manifest containing 0.125 raises `int_from_float`. This is a
   product implementation/specification discrepancy, not an environment failure.
   A follow-up fix should accept finite numeric epoch values consistently with
   the specification, add integer/fractional regression tests, refresh exported
   schemas and the migration/change note under the schema-review rules. No
   product schema is changed in this validation session. The supplementary DP
   input truthfully records `max_steps: 2` and `training.params.num_train_epochs:
   0.125`, leaving the optional incompatible field absent.
2. **Nested drift-policy coverage gap.** `privacy.*` matches one child segment,
   not `privacy.mechanism.params.target_epsilon`; the latter falls back to
   MEDIUM. The analogous `evaluation.judge.*` pattern misses nested judge
   temperature. This follows current matching semantics but weakens the intended
   sensitive-parameter policy. A follow-up specification proposal should enumerate
   exact nested paths (or deliberately define a recursive pattern) with tests for
   both matched and unrelated leaves. Do not change wildcard semantics silently.
   The real DP pair must explicitly check this MEDIUM leaf, separate from its
   HIGH configuration hash.
3. **Validation-input errors, not product bugs.** Unquoted commas in two YAML
   flow-mapping descriptions created forbidden extra keys. Quoting the strings
   resolved them; all five manifests now pass independent schema validation.
4. **Dependency constraints need separate environments.** Modern vLLM uses
   torch 2.10/CUDA 12.9, whereas the author-pinned DP code uses torch 2.2 and
   transformers 4.29. FastChat's paid-judge extra pins an old OpenAI package and
   conflicts with modern vLLM; it is not installed for local answer coverage.
   HarmBench's original spaCy pin also conflicts with the modern NumPy stack;
   any modern import-support dependency is an explicit adapter-environment
   deviation, not reproduction of its full original requirements.
5. **Legacy Accelerate has an undeclared runtime import dependency.** The first
   complete DP import check failed at `accelerate.utils.torch_xla →
   pkg_resources`; a minimal import probe reproduced it twice. Installed
   metadata confirmed setuptools was absent, and Accelerate 0.20.3's declared
   requirements omit it. This is a legacy environment issue, not a ReproLLM
   failure. Explicitly installing `setuptools==80.9.0` in the isolated DP
   environment made both the minimal probe and full fastDP/GPT2 import pass;
   dependency checking also passed. The pin retains the deprecated API required
   by that unmodified upstream version; it is not added to ReproLLM's dependencies.
   The standalone regression probe remains in the clearly marked external
   evidence directory, and initial failed logs are retained in
   `evidence/dp-setup-attempt-1/`. See the
   [official compatibility source](https://github.com/pypa/setuptools/blob/v80.9.0/pkg_resources/__init__.py).
6. **Safe-weight reader omitted from the legacy environment.** The first real
   DP child (`20260926T073353Z-6247a4`) exited 1 before training because
   transformers 4.29 did not find a supported checkpoint. The pinned
   `model.safetensors` file existed and its integrity had passed, but the
   optional `safetensors` reader was not installed. The upstream loader did not
   disable safe loading. A CPU-only regression probe failed on the missing
   reader, then passed after explicitly adding `safetensors==0.4.5` to this
   isolated environment and its reproducible preparation inputs. No weights
   were converted, no additional pickle checkpoint was downloaded, and no
   ReproLLM dependency changed. The failed run remains retained as a failure,
   not a passed training case.
7. **HarmBench imports an additional CPU NLP model eagerly.** Source inspection
   found `spacy.load("en_core_web_sm")` at module scope in `eval_utils.py:216`,
   even though the selected classifier path does not use that NLP pipeline.
   Preparing only the spaCy library would therefore fail the real import check.
   The official `en_core_web_sm` 3.8.0 wheel is included in the modern environment
   preparation, paired with spaCy >=3.8,<3.9; its published wheel SHA-256 is
   `1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85`
   and release-asset size is 12,806,118 bytes. This is a declared adapter-environment
   resource, not a change to HarmBench source or to its classifier model.
   [Publisher release and compatibility](https://github.com/explosion/spacy-models/releases/tag/en_core_web_sm-3.8.0).

## Quality gate

All checks ran against the unchanged implementation:

```text
uv run --no-sync pytest -q: 1225 passed, 1 existing warning, 54.62 s
uv run --no-sync ruff check .: passed
uv run --no-sync ruff format --check .: 252 files already formatted
uv run --no-sync mypy src/: 104 source files, passed
schema export + directory comparison: all 9 schemas unchanged
```

The warning is the pre-existing invalid escape sequence in the deliberate
legacy-source scanner fixture. No real network call was added to tests.

## Gate A and metadata validation

All five original checkouts have their exact `val.md` pins, an origin and a clean
tree. Level 0 commands exit 0 with `--fail-on never`. Assertions cover complete
rule/status sets, exact unpinned-package sets, profile confidences, provider and
backend hints, adapter/dataset/trust hints, HF-ID sets and AST source locations,
relative evidence paths and scan-limit diagnostics. The expected LlamaFactory
tracked `.env.local` CRITICAL and harness 500/816 scan boundary remain present;
neither is suppressed. `doctor --json` exits 0 in each original checkout.

The exact original M3/M4 manifests and earlier external evidence directories
are missing on this host. Hashes cannot reconstruct their bytes. Therefore this
session uses the distinct supplemental metadata inputs in `val.md` §8.2 and
**does not claim exact original-manifest replay**. An independent source review
confirmed all 18 referenced local file hashes before CLI execution. Existing
§8.1 remote revisions/config/template hashes remain the expectations.

Each disposable clone runs an offline lock, two online locks, freshness checks
and Level 2 audits. Input manifests and generated locks are committed only in
those clones, so Git findings refer to clean artifacts. Online-lock equality
excludes only `generated_at`, `resolved_at` and `observed_at`. Every captured
local hash is recalculated independently; all selected remote identities and
config/template hashes are checked, not just summary counts.

All five supplementary metadata scenarios passed their specified assertions.
All offline/online/check/audit commands exited 0; the audit commands deliberately
use `--fail-on never`, so this does not mean these narrow manifests describe
complete runnable experiments.

| Target | Offline lock (s) | Online 1 / 2 (s) | Final L2 audit (s) | Final L2 C/W/I/P/S |
|---|---:|---:|---:|---|
| lm-evaluation-harness | 1.336 | 3.080 / 3.049 | 28.011 | 3/21/4/26/12 |
| FastChat | 1.573 | 2.524 / 4.118 | 1.654 | 4/21/5/26/18 |
| LlamaFactory | 1.292 | 3.219 / 4.463 | 2.401 | 3/23/2/15/12 |
| HarmBench | 1.342 | 3.620 / 3.681 | 1.770 | 5/14/4/16/18 |
| llm-dp-finetune | 1.280 | 3.308 / 3.912 | 0.734 | 4/16/1/17/12 |

No expected remote SHA, config/template hash, local hash or normalized-lock
stability delta was found. `consistency.lock_fresh` and
`consistency.file_hashes` passed throughout. Offline revisions remain unresolved
with `source: offline`. Online Qwen/Vicuna identities resolve exactly; the dated
FastChat judge remains `snapshot_alias` with null provider revision and INFO
evidence. Vicuna has no Hub chat template, correctly recorded as absent.
Llama-2 repo/tokenizer revision metadata resolves, while forbidden config files
remain `unresolved/hf_api_forbidden`; this is denial handling, not successful
gated access. No authenticated denial check was rerun without a credential.

The complete failed-finding lists were reviewed against the new input fields
and specification §12. Their presence gaps are intentional: all five lack a
command/seed; inference/evaluation manifests omit generation settings and
metrics; training manifests omit training settings; the DP metadata manifest
omits privacy declarations. Additional missing dtype, trust, preprocessing,
prompt and safety-definition fields follow those narrow inputs. The repository
dependency warnings and LlamaFactory forbidden file remain baseline findings.
The unresolved vLLM version is expected in ReproLLM's lightweight environment.
No presence finding was reclassified as a metadata-resolution failure or a
passed runtime gate.

The first driver attempt exposed two **driver assertion errors**, not product
defects: a multi-line model call's evidence points to the call start, not
necessarily the literal's line; optional dataset `files` may be null. The driver
now verifies the AST call location and handles the schema's optional field.
Both corrections were rerun; no ReproLLM code or gold expectation was changed.

## Real supplementary DP pair

The original Llama-2/ECHR/ZeRO gate is **not passed** by this case. This is the
authorized public DistilGPT2 single-GPU supplement using the pinned upstream
`_fine_tune_fast_dp` implementation and author-pinned fastDP fork. The child is
`python validation/train_entry.py`, executed through the DP environment's
`reprollm run --capture-output`. Exact upstream pins remain those in `val.md`.

The isolated environment's own CUDA 12.1 smoke returned the expected matrix
value, synchronized, and used 9,043,968 peak allocated bytes. Real runs used
only GPU 0; subsequent readings returned to 753 MiB / 14127 MiB on cards 0/1,
and the pre-existing serving processes remained running.

| Observation | Final A | B |
|---|---|---|
| Run ID | `20260926T074255Z-30f6cd` | `20260926T074121Z-159942` |
| Disposable input commit | `6fab23055e26f6bbb98b4d948b73d5d4321ae301` | `09dd7480bb2be4fb7975aa3d11d7227c3e2687e1` |
| Target epsilon | 8 | 4 |
| Child duration, seconds | 11.650 | 11.751 |
| Complete command elapsed, seconds | 13.305 | 13.487 |
| Exit / actual optimizer steps | 0 / 2 | 0 / 2 |
| DP-covered / intended parameter tensors | 76 / 76 | 76 / 76 |
| Clipping observations / positive noise draws | 2 / 152 | 2 / 152 |
| Noise multiplier | 0.39421386718749996 | 0.5475097656250001 |
| Observed finite losses | 4.5719, 5.0058 | 4.5719, 5.0063 |
| Accountant epsilon | 7.986783183167738 | 3.9982670621285883 |
| Independently checked finite checkpoint tensors | 89 | 89 |
| Final L2 audit C/W/I/P/S | 0/8/0/31/11 | 0/8/0/31/11 |

The initial parameter digest is identical across A/B; final parameter digests
change and differ between A/B. Lower target epsilon increases calibrated noise.
These are engineering observations on synthetic public text, not a privacy
guarantee or paper-result reproduction. Model quality is not a gold assertion.

Independent capture checks passed for actual package versions, four bindings,
all three declared input files, captured output files and their sizes/hashes,
clean Git state, manifest/lock snapshots, and absence of machine identity and
absolute paths from ReproLLM-owned persisted captures. Both final audits pass
`consistency.env_vs_lock`, `consistency.file_hashes`, `consistency.lock_fresh`
and `consistency.model_identity`. The eight warnings are independently explained:
five pre-existing unpinned dependency declarations; missing upstream dependency
lock/Python requirement; and adapter imports detected elsewhere in the repository
despite this full-finetuning manifest. No warning was suppressed.

The pair diff exits 1 with `--fail-on HIGH`, as expected. Its **complete**
non-NONE change set is the configuration-file hash (HIGH), exact epsilon leaf
8 → 4 (MEDIUM), and disposable input commit (MEDIUM). The remaining four changes
are start/end time, duration and run ID (NONE). Self-diff exits 0 with no changes.
Thus the current nested-privacy policy gap is reproduced by real runs, not
hidden by the HIGH file-hash change.

Retained preparation attempts distinguish capture from scenario success:

- A attempt 1 failed before training due to the missing safe-weight reader.
- A attempt 2 (`20260926T073953Z-d44890`) successfully trained, but correctly
  reported `environment.packages.safetensors: only run` at INFO because its lock
  predated the environment repair. This is useful true-positive capture evidence.
- Final A attempt 3 relocked the repaired, unchanged training environment and
  reran the identical epsilon-8 inputs. Its final parameter digest equals that
  of attempt 2. It ran after B; A/B denote parameter variants, not chronology.

Full command records, intermediate failures, captured runs, output checks,
checkpoints and all diff leaves are retained under
`evidence/runtime/llm-dp-finetune/` on the approved data volume. The standalone
`dp_final_check.py` rechecks finite checkpoints, matching initial weights and
packages, noise ordering, accountant bounds, all non-NONE changes and all four
consistency passes. No upstream source or ReproLLM implementation was changed.

## 2026-09-27 verification follow-up — morning checkpoint

The ReproLLM source commit remains unchanged. Checks rerun on this date:

| Check | Actual result |
|---|---|
| `uv run pytest -q` | 1,225 passed in 54.06 s; one existing target-code deprecation warning |
| `uv run ruff check .` | PASS |
| `uv run ruff format --check .` | PASS; 256 files |
| `uv run mypy src/` | PASS; 104 source files |
| Schema export into a fresh evidence directory, then recursive comparison | All nine files identical |
| Both generated-document freshness checks | PASS |
| Full Gate A on all five original pinned clean checkouts | PASS, including complete rule sets, detected profiles, source-verified hints and diagnostics |

Fresh Gate A commands, statuses, timings and full outputs are retained separately
in `evidence/gate-a-20260927/`; previous evidence was not overwritten. Schema
comparison used `evidence/schema-20260927.K3Fz4f/`.

The additional official spaCy resource finished downloading via ranged requests.
Its 12,806,118 bytes and SHA-256
`1932429db727d4bff3deed6b34cfc05df17794f4a52eeb26cf8928f7c1a0fb85`
match the publisher's 3.8.0 release. The interrupted zero-byte single-stream
artifact was preserved; no model version was substituted. Package installation
and real CUDA/vLLM execution remain separate acceptance steps.

**New resource blocker: three corrupted resumed CUDA wheels.** The cuDNN
9.10.2.21, cuSOLVER 11.7.5.82 and cuSPARSE 12.5.10.65 files reached their expected
byte counts but failed official PyPI SHA-256 checks. ZIP decompression also
failed, independently confirming unusable local bytes. Repeating the cuSOLVER
hash check reproduced the same failure in 0.17 s. The inventory was not published
and the waiting installer exited without starting installation.

Ranked hypotheses were damaged retained download fragments, inconsistent mirror
bytes, and a range/content-encoding error. Four sampled official cuSOLVER ranges
matched the local file; the sampled cuSPARSE range matched official, Huawei and
Tsinghua responses (HTTP 206, correct range, no encoding). These small samples
neither explain the whole-file discrepancy nor exonerate every downloaded range.
The original cause remains undetermined; do not attribute it to a mirror, a
library or the filesystem without evidence.

All three failed files, exact actual/expected sizes and hashes, decompression
errors and probe results are preserved in `evidence/corrupt-wheels-20260927/`.
They were moved, not deleted. Fresh transfers use the unchanged downloader,
versions, URLs and final integrity guards; no reused bad bytes, package-version
change, product-code patch or bypass is involved. Recovery is pending until
whole-file verification and environment execution succeed.

The three weight downloaders, modern wheel retry, installer and existing runtime
queue now run in a dedicated detached terminal server (`reprollm-validation`,
session `resources`). Its server was observed with parent PID 1 and its own
session ID, and all six panes were alive. Logs are under `evidence/` with the
`20260927` suffix. Queue inputs were revalidated before launch; all four modern
cases at that checkpoint remained **waiting**, not passed. The prior queue directory is
preserved as `evidence/continuation-queue-interrupted-20260926/`. No paid API is
included in this queue, and no later completion is presumed from its launch.

## DeepSeek FastChat live pair — 2026-09-27

The maintainer approved the temporary adapter and a **CNY 3 total ceiling**.
The independent inputs and acceptance criteria were recorded in `val.md` §8.4
before the first authenticated request. An authenticated `/models` request
returned 200 and listed `deepseek-flash`. Exactly two completion requests were
then made, with no retries; both returned completed, parseable judgments.
There will be no further paid request under this two-attempt scenario.

| Observation | A | B |
|---|---|---|
| Run ID | `20260927T041122Z-75d128` | `20260927T041137Z-f1d944` |
| Disposable commit | `557ab76eaae9fbbcc8a18016fb72694f8c8702d5` | `f310fab3f9dc04263946bb375800f3f271742b02` |
| Effective output cap | 256 | 384 |
| Run-record duration / child exit | 9.247081 s / 0 | 9.784587 s / 0 |
| Prompt tokens / output tokens | 245 / 146 | 245 / 166 |
| Cache-hit / cache-miss prompt tokens | 0 / 245 | 0 / 245 |
| Original FastChat parser's observed score | 7 | 7 |
| Finish reason | `stop` | `stop` |
| Estimated weekend charge, CNY | 0.000829 | 0.000909 |

The score is an observation, not a fixed quality gold. Both runs use the same
public question 82, fixed synthetic email answer, original `single-v1` rubric,
temperature 0 and explicitly disabled thinking. The original FastChat prompt
construction and score parsing are unchanged; provider dispatch/conversation
template and the obsolete network call are explicitly adapted. This does **not**
exercise the old SDK implementation or reproduce an original GPT-4 judge.

The outgoing message digest is identical across runs:
`ea39c83d9ddbd2fed0f5eaaf1379d4939dc7d8463697063398ceb5c8b24be685`.
Request and response model IDs are `deepseek-flash`; the provider returned the
same fingerprint `aeb56401ca74e127821c4f9126dcb669`. Neither an alias nor that
fingerprint is promoted to an immutable revision. The lock correctly retains
`pinnability: unpinnable` and null revision.

Using returned token counters and the independently rechecked
[official CNY tariff](https://api-docs.deepseek.com/zh-cn/quick_start/pricing/),
the total estimated weekend charge is **CNY 0.001738**. The ledger conservatively
settles at peak prices, **CNY 0.003476**, also below CNY 3. No account invoice or
balance was fetched, so these are token-based estimates, not an invoice claim.
Each request reserved the entire published context's peak cost before sending;
the timeout test proves an uncertain charge remains reserved and prevents a
second request when funds are insufficient. Actual responses released unused
reservations. Three network-free transport tests passed with synthetic secrets.

### Runtime and diff verification

- Both ReproLLM records are complete, child exit 0, with clean disposable Git
  state and the exact declared command. Installed package maps match the actual
  child environment. All four config bindings match the consumed model,
  endpoint, temperature and output cap.
- Each record has six captured input files and two output artifacts, independently
  rehashed with byte counts checked. Manifest and lock snapshot hashes match.
  The selected question is additionally identified by the pinned repository and
  local-dataset hash in the lock; it is not claimed as an extra runtime snapshot.
- The real credential appears only as `OPENAI_API_KEY: {present: true}` in env
  capture. Exact-value scans passed for logs, captured runs, outputs and evidence;
  ReproLLM-owned captures also contain no raw hostname, username or absolute path.
  The key was passed through hidden terminal input and transient environment,
  never written into validation source, configuration or argv.
- All six `judge.*` rules pass. `consistency.env_vs_lock`, `file_hashes`,
  `lock_fresh` and `model_identity` pass in both final audits. The complete A/B
  finding lists are identical, not merely their counts.
- The complete non-NONE diff is exactly: config hash HIGH; the actual cap leaf
  `evaluation.judge.params.max_tokens`, 256 → 384, MEDIUM; clean code commit
  MEDIUM. Four remaining time/run-ID fields are NONE. Pair diff exits 1 under
  `--fail-on HIGH`; self-diff exits 0 with zero changes. This reproduces the
  nested-judge severity gap without hiding it behind the HIGH file hash.

Full commands, durations, captures, provider usage, original judgments, proofs,
audits and both diffs are retained in `evidence/runtime/FastChat-deepseek/`.
The no-secret input bundle `evidence/deepseek-validation-inputs-20260927.tar.gz`
has SHA-256 `6fa31edfe86c94be3c1a6b4be17e888aad0322802984d977239d4cb328f17aea`;
it includes A/B manifests and the external adapter/controller. Generated bytecode
is excluded from that bundle; one unchanged cached bytecode file was incidentally
force-staged in the disposable commits, not in ReproLLM or runtime snapshots.

### Complete audit interpretation and follow-up proposals

Both final L2 reports are **6 CRITICAL / 20 WARNING / 3 INFO / 30 PASS / 12 SKIP**,
with no suppression. Successful capture/judge/diff checks are **not** a zero-finding
audit claim. Specification §§6.1 and 12 and the actual narrow manifest explain
every failing group:

- Five CRITICAL presence findings: no general execution seed, no primary model,
  no sampling seed, no general inference backend and no general generation block.
  This is a judge-only run of a deterministic selected public question and a
  fixed synthetic answer; `llm_judge → evaluation → inference → core` still
  selects those general requirements. No unused seed or fictional primary model
  was added to hide the findings. A separately reviewed profile/answer-provenance
  design could distinguish judging stored answers from generating new answers.
- One CRITICAL revision finding: a truthful `provider: other` DeepSeek model
  falls outside the hard-coded API-provider set, so `model.revision_pinned`
  treats its unresolved revision as CRITICAL even though the lock records API
  unpinnability and `judge.pinnability_recorded` passes. This is a real support
  boundary/contract gap, not failed authentication. A follow-up should explicitly
  separate provider identity from API compatibility/pinning capability, with
  schema/spec review and positive/negative tests; never relabel DeepSeek as the
  OpenAI vendor or invent a revision to get a green result.
- Fifteen upstream unpinned-package warnings: accelerate, anthropic, datasets,
  deepspeed, flash_attn, numpy, openai, peft, safetensors, sentencepiece, sglang,
  torch, transformers, vllm and xformers. Their declarations remain unchanged.
  One additional warning is the absent upstream dependency lock. Four model
  warnings concern unknown provider, unspecified dtype/quantization and detected
  upstream trust-remote-code use without a declaration. The API does not expose
  actual weights/dtype; they were not guessed.
- Three INFO findings: undeclared detected finetuning profile, no general stop
  list, and no few-shot declaration. These arise from repository-wide detection
  and the narrow judge-only input, not hidden runtime errors.

The supplement passes the focused M5 real-key/capture and M6 judge-pair checks,
with the above audit limitations explicitly retained. The original GPT-4
snapshot case and M7 export/discover remain unverified; this is not milestone
or release completion.

## Additional local-resource progress — 2026-09-27 noon

Fresh downloads of all three previously corrupted CUDA wheels passed official
whole-file hashes. The unchanged downloader, versions and URLs were used;
only the old partial bytes were removed from the retry path and preserved as
evidence. This supports the damaged-retained-transfer hypothesis but does not
identify when or why the original bytes became corrupted. Modern installation,
dependency consistency, imports and package freeze all passed. A real GPU 0
CUDA matrix product and four-token vLLM generation completed in 44.68 s using
torch 2.10.0+cu129 and vLLM 0.18.0. System drivers and existing services were not
changed.

The six originally resumed large-model parts also failed their final hashes:
Qwen3 shard 2, both Vicuna shards and HarmBench shards 1–3. All complete failed
bytes and expected/actual hashes were preserved under
`evidence/corrupt-model-parts-20260927/`; no failed part was loaded. Fresh
transfers run in `qwen3-fresh`, `vicuna-fresh`, `harmbench-fresh` panes of the
dedicated background session, with unchanged pins, byte guards and disk reserve.
HarmBench's other shards and all previously verified resources are retained.

The first lm-eval run correctly captured a nonzero child exit caused by an
unsupported `bootstrap_iters` config key. A minimal native `EvaluatorConfig`
constructor reproduces the failure in about 0.2 s; removing only that key makes
it pass. Corrected A completed 100 real GSM8K requests. Its verifier initially
used the evaluator's in-memory list layout rather than the pinned logger's
named JSON dictionaries; source lines 353–363 independently establish the
correct `gen_args_0.arg_0` / `arg_1` layout. That verifier-only correction passed
all 100-document / 200-filter-row, context-length, output-bound and finite-metric
checks without rerunning or changing the model outputs. Both initial failures
are retained separately from the successful result. B and the pair subsequently
completed as recorded below; a post-run snapshot review found a separate product
defect, so this is not an unqualified pass of the entire capture gate.

After these validation-only changes: 1,225 root tests passed in 55.46 s with the
same existing warning; ruff check/format passed (254 files), mypy passed (104
source files), all nine schemas matched, both generated docs checks passed, and
full Gate A passed again on all five original clean pinned checkouts. Fresh
evidence is in `evidence/gate-a-paid-20260927/` and
`evidence/schema-paid-20260927.NODkAm/`. Two pre-existing deletions under
`docs/superpowers/specs/` and the user's `plan/` changes were left untouched.

## Real lm-eval pair and post-run review — 2026-09-27

Both variants ran the pinned native evaluator on the same first 100 GSM8K test
documents, five-shot prompts and Qwen2.5-0.5B-Instruct model. The only intended
experimental change is the output cap, 32 to 48; its config and manifest binding
change together. Native execution used cached model/data resources, GPU 0 only,
and no paid API.

| Observation | A (corrected attempt 2) | B (attempt 1) |
|---|---|---|
| Run ID | `20260927T041447Z-96eb66` | `20260927T042220Z-134a1c` |
| Disposable commit | `2a977fd10e221ad3eeb60f95bec629f0a6e2e361` | `0b99b87efb61045d4760b6666cf005fa690a6423` |
| Run-record duration / child exit | 95.633342 s / 0 | 96.608116 s / 0 |
| Documents / logged filter rows | 100 / 200 | 100 / 200 |
| Maximum observed response tokens | 32 | 48 |
| Observed strict / flexible exact match | 0 / 0.03 | 0.05 / 0.09 |

The accuracy values are observations, not gold targets or a claim of a
statistically meaningful improvement. All 100 document hashes and prompt hashes
are identical across variants. Every sample has the original strict-match and
flexible-extract filters; response caps, context bounds and finite metrics pass.

Both full L2 audits are **0 CRITICAL / 14 WARNING / 1 INFO / 46 PASS / 5 SKIP**,
with identical complete finding lists and profiles, and no suppression.
Thirteen package warnings concern upstream unpinned accelerate, anthropic,
datasets, evaluate, lm_eval, numpy, openai, peft, sentencepiece, sglang, torch,
transformers and vllm; the other warning is the missing upstream lock. INFO
reports a detected undeclared finetuning profile. All four applicable runtime
consistency rules pass. Three captured inputs, two output artifacts and four
bindings were verified against the consumed inputs and actual environment.

The complete non-NONE diff is exactly the config hash HIGH,
`generation.max_tokens` 32 → 48 HIGH, and clean code commit MEDIUM. Four
time/run-ID fields are NONE. Pair diff exits 1 under `--fail-on HIGH`; self-diff
exits 0 with no changes. These focused inference and cap-drift checks pass.

A/B outputs are preserved separately in
`evidence/runtime/lm-evaluation-harness/{a,b}/outputs/`. The offline
`final_pair_review.py` additionally checked every raw input against its exact
disposable Git commit, every preserved output's hash and size, the complete
finding lists and complete diff sets for both lm-eval and DeepSeek. Per-case
`final-review.json` records the review, including the defect below. The live
queue's original lm-eval failure is intentionally preserved; its separate
`evidence/continuation-queue/manual-followup.json` points to the later completed
pair without racing or rewriting the queue-owned status.

### New product defect: path redaction changes non-secret experiment values

The post-run review first compared document snapshots with original-byte hashes
and failed. Hashing raw bytes while storing redacted snapshots is intentional
(spec §5.1); equality of those two byte streams is not itself a requirement.
Inspection of the actual differences, however, revealed false-positive path
redaction in both lm-eval variants:

- The literal stop token `</s>` becomes `<<REDACTED:path>>` in both manifest and
  lock snapshots.
- Relative artifact globs `outputs/current/**/*.json` and
  `outputs/current/**/*.jsonl` both become `outputs/current/**<REDACTED:path>`
  in the manifest snapshot.
- Original Git bytes still match every recorded source hash. Input files and
  generated outputs were not modified; the corruption is in captured text.

A minimal call to `RunPrivacy.text` reproduces both false positives with
synthetic root/host/user values, while an actual absolute path is correctly
redacted. `run/privacy.py`'s `_ABSOLUTE_PATH` expression allows a slash after
`<` or `*`, misidentifying a closing token and a relative glob suffix as paths.
The loaded real A-run state confirms that `generation.stop` contains the
altered value, because `diff/state.py` projects the redacted snapshots. A/B
cap-drift still works, but equal corruption on both sides is invisible in that
pair. Different closing-tag stop tokens can collapse to the same text and
therefore mask a stop-token change; this is not proof that the tested cap
change was missed.

**Disposition:** capture fidelity has an open defect; do not mark the whole
lm-eval M5 gate clean based on exit 0 or the audit summary. The final review
records `snapshot_semantics_pass: false`, with each exact changed document.
The verifier checks only these enumerated differences and rejects any extra
rewrite; it does not redefine the gold to accept them. DeepSeek's manifest/lock
snapshots do match their original bytes, so this finding does not invalidate
its checked judge bindings or fee evidence. A follow-up check also confirmed
that both prior DP variants' manifest/lock snapshots exactly match their
committed original bytes; no equivalent document corruption was found there.

**Proposed fix, not implemented:** add tests first for literal closing tokens,
relative globs, real POSIX/Windows/UNC paths and embedded machine identities;
then tighten path recognition at the run-persistence boundary without weakening
secret or identity removal. Add a run → snapshot → state regression preserving
`generation.stop` and artifact globs, plus a paired stop-change diff assertion.
Keep the existing redaction corpus and security coverage gates; any change to
`core/redaction.py` still requires 100% branch coverage. Re-run full quality,
five-project Gate A and affected real capture/diff cases before claiming fixed.
No product source or privacy policy was changed during this validation session.

**Fix implemented 2026-09-28** (commit `fc3f6aa`, separate from this
validation-only session): the absolute-path lookbehind now excludes the
characters preceding closing tokens and glob stars (`<`, `*`) and the match
additionally stops at `>`. New table tests pin closing tokens (`</s>`,
`</think>`, DeepSeek-style markers), relative globs, real POSIX/Windows/UNC
paths, URLs, and machine identities; an end-to-end regression asserts
run → snapshot → State preserves `generation.stop` and artifact globs and
that a paired `</s>` → `</think>` run diff surfaces `generation.stop`.
Secret removal, root relativization, and both coverage gates are unchanged;
five-repository Gate A matches the gold unchanged. The captured A/B evidence
under `evidence/runtime/lm-evaluation-harness/` still contains the corrupted
snapshots as historical fact; a fresh real pair is required before marking
this scenario clean in val.md.

## Remaining acceptance

The one-shot local continuation queue launched on 2026-09-26 did **not** finish.
On 2026-09-27 its worker processes were absent and its last recorded state was
still waiting. There is no termination record establishing the cause. Preserve
that status as interrupted history, not evidence of continued execution or a
pass. The replacement queue started on 2026-09-27, and the corrected lm-eval
pair was completed manually after its initial queue attempt failed. The modern
environment and real CUDA/vLLM smoke are now verified, not remaining blockers.

The queue is designed to wait for successful environment checks and complete verified weights, then
performs the modern CUDA/vLLM smoke and each ready case's A/B sequence through
the existing controller. The eight proposed config/manifest edits were checked
before launch: each pair changes exactly its declared scalar and both manifests
validate. Input hashes are rechecked before execution, generated A outputs are
preserved before B, and GPU/disk guards remain active. Failures are recorded;
neither code nor gold is automatically repaired. An automated pass still needs
full report/delta review. Current queue state and detailed logs are in
`evidence/continuation-queue/`; queued/waiting is **not** passed. The queue does
not include paid APIs, gated Llama-2, global environment changes or a Git push.

- M4 original-input replay remains blocked by missing manifest bytes; supplemental
  Linux/mirror metadata coverage does not erase that limitation.
- The supplementary DP M5 capture/M6 pair passed. The lm-eval real inference
  and cap-drift checks completed, with the snapshot-fidelity defect above still
  open. Neither implies that other scenarios have passed.
- LlamaFactory training, FastChat local answer generation and HarmBench's local
  target/classifier pairs still await full verified model weights, actual
  execution and review. At the final checkpoint their fresh download panes and
  local queue were alive; partial-download progress is not hash verification.
  GPU 0 returned to 753 MiB used / 80,297 MiB free / 0% utilization; GPU 1
  remained at 14,127 MiB used and was not used for validation. Free disk was
  about 87 GiB; the 50 GiB reserve remains enforced. No existing service was
  stopped. Waiting or automated execution alone never counts as acceptance.
- The approved DeepSeek supplementary judge pair completed with exactly two
  paid attempts, estimated CNY 0.001738 off-peak / CNY 0.003476 conservatively
  at peak, below CNY 3. Its full audit retains 6 CRITICAL / 20 WARNING / 3 INFO,
  and the judge-cap leaf remains MEDIUM under current policy; see the explained
  findings above and [official API research](deepseek-api-validation.md).
  The original GPT-4 snapshot scenario is still not verified. No additional
  paid calls are authorized by the completed two-attempt plan.
- Original Llama-2 DP access and execution remain incomplete. DistilGPT2 can
  only add explicitly labeled supplementary single-GPU coverage.
- M6-H2's maintainer assessment of the real diff remains a human acceptance step.
- M7 export/discover remain outside this completed subset; their placeholders
  and API gates are not passed by a FastChat judge request.

No release, tag, merge, push or product-code fix was performed. This session is
not a claim that the M4–M6 resource gates or releases are complete.

## Full report review — FastChat and LlamaFactory — 2026-09-28

This closes the "passed_automated_checks_needs_full_report_review" state of
both queued cases against the §8.3 gold. The review is of evidence the queue
produced on 2026-09-27; no new execution, GPU use or download occurred.

**Common checks (all four runs).** Status `completed`, child exit 0, clean
disposable commits; declared files hashed and snapshotted; bindings observed
for every declared leaf including the intended-change scalar; artifacts hashed
under `outputs/current/`; `run.json` free of absolute paths, usernames and
secret values, hostname stored only as its SHA-256. Manifest and lock
snapshots contain zero path-redaction corruption — verified line by line
after the fidelity defect was found elsewhere (these manifests carry no
closing-token stops, so the pre-fix code did not corrupt them).

**FastChat (answer generation, no paid judge).** Runs
`20260927T064434Z-ee237a` / `20260927T064510Z-70f2ca`, 25.7 s / 16.2 s, Vicuna
7B via the native answer generator, question 81 one-choice/two-turns,
temperature 0.7 / seed 0. The output preserves the native `answer_id` /
`choices` / `model_id` / `question_id` schema with real generated turns. The
complete non-NONE pair diff is exactly: config hash HIGH,
`generation.max_tokens` 32 → 48 HIGH, clean commit MEDIUM — the §8.3 required
leaf and no others. With §8.5's promotion of the DeepSeek judge pair, this
closes FastChat's §8.3 row.

**LlamaFactory (LoRA fine-tune).** Runs `20260927T050707Z-0fde1f` /
`20260927T050751Z-a66341`, 29.3 s / 14.6 s, native LoRA CLI on Qwen3-4B,
16 identity records, cutoff 64. `trainer_log.jsonl` records real optimizer
steps 1–2 with finite decreasing loss (6.1662 → 4.9055) at the declared
learning rate; adapter weights and tokenizer artifacts were produced and
hashed. The complete non-NONE pair diff is exactly: config hash HIGH,
`training.learning_rate` 0.0001 → 0.0002 HIGH, clean commit MEDIUM. This
closes LlamaFactory's §8.3 row.

**Disposition.** Both §8.3 rows for these repositories are complete; the
queue's own status file remains untouched as historical automation state.
Still open at this point: the lm-eval clean re-pair after the fidelity fix,
HarmBench (GPU wait), M6-H2 review material, and M7.

## Final GPU gates — 2026-09-29

Maintainer authorization: shared-GPU execution (relaxed controller guard;
lease, GPU-0 pin, memory-fraction caps and disk reserve retained) and
completion of the pending classifier download.

**lm-evaluation-harness clean re-pair (the fidelity-fix re-run).** Code path:
editable install at main `690fe67` (fix `fc3f6aa` verified active in the
environment before launch). Inputs restored byte-identical from the corrected
2026-09-27 commits; the failed first-queue-era run records were archived so
`name` selection stays unique. Both variants completed exit 0 (~80 s each).
Pair diff is exactly `generation.max_tokens` 32→48 HIGH + config hash HIGH +
commit MEDIUM + four NONE; self-diff empty. **Both snapshot pairs are
byte-identical to the expected privacy-processed sources with zero
path-redaction misfire lines** — the defect fixed in `fc3f6aa` does not
reproduce in real execution. This supersedes the earlier
`snapshot_semantics_pass: false` disposition; the corrupted 2026-09-27
artifacts remain archived unchanged as history.

**HarmBench first full execution.** Root cause of the earlier failure found
and closed: the classifier download was incomplete — shards 1–3 were fully
downloaded bytes that the dead queue never renamed, and tokenizer files were
never fetched. Shards resumed/renamed, tokenizer files downloaded, and every
shard + `tokenizer.model` verified against the official Hub API LFS sha256
(the mirror's ETags are not LFS hashes — noted to prevent repeat
misdiagnosis; `training_args.bin` intentionally not fetched, unused by
inference). Real DirectRequest target (Vicuna 7B, `3321f76e…`) and classifier
(HarmBench-Llama-2-13b-cls, `bda70534…`) ran in separate processes; A
(69.6 s) and B completed exit 0 with five bindings observed (cap, both model
ids and revisions), no privacy violations, and snapshots byte-identical to
each variant's own commit. Pair diff is exactly `generation.max_tokens`
16→24 HIGH + config hash HIGH + commit MEDIUM + four NONE.

All five §8.3 runtime rows are now complete (see val.md §8.5a/§8.5b). GPU
readings returned to pre-run levels; no validation or download process
remains. M4–M6 resource gates: closed for the activated scenarios.

