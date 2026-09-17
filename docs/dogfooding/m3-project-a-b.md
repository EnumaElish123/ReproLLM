# M3 Project A/B dogfooding record

This record covers M3-T10 Level 1 audits. Both manifests were created with
`reprollm init`, completed by hand in disposable local clones, committed there
so Git-state checks saw a clean tree, and kept outside the ReproLLM repository.
No model, GPU, or paid API call ran in M3.

## Targets and commands

| Alias | Repository | Pinned commit | Declared profiles |
|---|---|---|---|
| Project A | `EleutherAI/lm-evaluation-harness` | `b954108c9baaaa934b4ad842033b31a97ee30816` | `inference`, `evaluation` |
| Project B | `lm-sys/FastChat` | `587d5cfa1609a43d192cedb8441cac3c17db105d` | `evaluation`, `llm_judge` |

The validated manifests are stored outside this repository under
`../dogfooding/manifests/`. Project A's SHA-256 is
`39eee344461c486bef31b55cce53789fd17c71e47a637f7d195c9ef9d68ad41a`;
Project B's is
`649372b39a13262ca09649a3d65849b748a778bb0d3c480895cf251ee9920189`.

Each clean disposable clone was audited in both formats:

```console
reprollm audit . --level 1 --no-color --show-skipped --fail-on never
reprollm audit . --level 1 --format json --output "$TMPDIR/report.json" --fail-on never
```

Project A describes a bounded GSM8K run with
`Qwen/Qwen2.5-0.5B-Instruct`, vLLM, deterministic decoding, five-shot task
prompting, and the first 100 test examples. Project B describes one MT-Bench
item: FastChat generates a `lmsys/vicuna-7b-v1.5` answer and grades it with the
`gpt-4o-2024-08-06` snapshot and the repository's judge prompt catalog.

## Results after the dogfooding fix

| Target | CRITICAL | WARNING | INFO | PASS | SKIPPED |
|---|---:|---:|---:|---:|---:|
| Project A | 0 | 14 | 2 | 34 | 3 |
| Project B | 0 | 16 | 2 | 34 | 7 |

All model, dataset, generation, prompt, evaluation, and judge presence checks
passed for the fields used by the two selected experiments. API-model dtype and
quantization checks, local-dataset split/subset checks, and non-vLLM backend
configuration checks skipped for the documented applicability reasons.

## Finding review

| Finding | Target | Judgment | Disposition |
|---|---|---|---|
| `env.llm_critical_deps_pinned` (13 instances) | A | Correct; WARNING is appropriate. The complete set equals the independent `val.md` gold. | M4 lock work owns resolution. |
| `env.llm_critical_deps_pinned` (15 instances) | B | Correct; WARNING is appropriate. The complete set equals the independent `val.md` gold. | M4 lock work owns resolution. |
| `env.lockfile_present` | A, B | Correct; WARNING is appropriate. Neither pinned checkout has a qualifying lockfile. | M4 lock work owns resolution. |
| `model.trust_remote_code_declared` | A | False positive for the selected experiment. The manifest explicitly declares `false`, matching the vLLM default and command, while unrelated repository code activates the scanner hint. | Fixed by the contract correction in [#1](https://github.com/EnumaElish123/ReproLLM/issues/1): either explicit boolean now satisfies the rule. |
| `exec.profile_detection_mismatch` (`finetuning`) | A, B | Factually correct repository-wide capability, but not part of either selected experiment. INFO is appropriate. | Fix hint now says unrelated repository capabilities need no manifest change. |
| `exec.profile_detection_mismatch` (`inference`) | B, before fix | False positive. `llm_judge` inherits `evaluation`, which inherits `inference`. | Fixed by comparing high-confidence detections with the resolved inheritance closure; regression test added. |
| `exec.run_recorded` | A, B | Correct; INFO is appropriate because `run` arrives in M5. | Expected until a real run record exists. |

No finding needed a severity change. In particular, the selected experiments
had no missing CRITICAL field, while repository environment drift remained at
WARNING and non-executed workflow capabilities remained at INFO.

## Manifest usability findings

The FastChat scaffold filled `models.primary.id` from a static HF-ID hit even
though FastChat is a multi-model framework. The value was a valid candidate but
its semantic role was not known. Generated manifests now label detected values
as candidates and tell the user to verify each experiment role.

The two manifests also required decisions that are not visible from the TODO
list alone: a task YAML can be both prompt and metric implementation; primary
generation settings and judge settings belong in different sections; metric
implementations use a repository-relative file or exact package pin; seeds
must reflect values consumed by the real runner. These points are documented in
[`docs/manifest.md`](../manifest.md).

## Standing five-project Gate A

The release gate was rerun on 2026-09-17 after the local quality gate. All five
canonical checkouts had the exact SHA listed in `val.md`, an empty porcelain
status, and the expected GitHub `origin`. Level 0 used this command for each
checkout:

```console
reprollm audit <checkout> --level 0 --format json \
  --output "$TMPDIR/<name>-L0.json" --fail-on never
```

| Target | Exit | Elapsed | CRITICAL | WARNING | INFO | PASS | SKIPPED |
|---|---:|---:|---:|---:|---:|---:|---:|
| lm-evaluation-harness | 0 | 6.831 s | 0 | 14 | 1 | 8 | 1 |
| FastChat | 0 | 0.578 s | 0 | 16 | 1 | 8 | 1 |
| LlamaFactory | 0 | 0.785 s | 1 | 15 | 1 | 7 | 1 |
| HarmBench | 0 | 0.563 s | 0 | 7 | 1 | 7 | 1 |
| llm-dp-finetune | 0 | 0.276 s | 0 | 7 | 1 | 7 | 1 |

The complete dependency warning sets, rule statuses, profile confidences,
provider/backend/adapter/dataset/trust hints, HF-ID values and source lines,
relative evidence paths, and Python scan counts matched `val.md` §§3–6. The
lm-evaluation-harness diagnostic was exactly `python file scan truncated to 500
of 816 files`; the other four scans were not truncated. There were no gold
deltas.

`init` and the resulting Level 1 audit then ran in fresh shared clones:

```console
reprollm init .
reprollm audit . --format json --output "$TMPDIR/<name>-L1.json" --fail-on never
```

| Target | Profiles generated | Primary candidate | Init | L1 audit | L1 result (C/W/I/P/S) |
|---|---|---|---:|---:|---:|
| lm-evaluation-harness | evaluation, finetuning, inference | TODO | 6.599 s | 6.433 s | 6/26/3/9/16 |
| FastChat | finetuning, inference, llm_judge | `EleutherAI/pythia-160m` | 0.558 s | 0.530 s | 6/30/3/13/17 |
| LlamaFactory | evaluation, finetuning, inference | `Qwen/Qwen3-4B-Instruct-2507` | 0.819 s | 0.825 s | 6/27/3/9/16 |
| HarmBench | evaluation, finetuning, inference, safety | TODO | 0.633 s | 0.627 s | 7/20/3/8/16 |
| llm-dp-finetune | finetuning, privacy | TODO | 0.269 s | 0.267 s | 5/17/1/8/7 |

Every generated manifest loaded immediately and produced a Level 1 report with
exit 0 under `--fail-on never`. Profile order and primary candidates matched
`val.md` §7; detected candidates carried a source comment and role-verification
instruction. M3 activates no Gate B resource scenario, so there was no GPU,
model download, training run, or paid API call.

## Resource boundary

The Project A GPU command and Project B OpenAI judge command were inspected and
recorded but deliberately not executed. Under `val.md`, minimal inference and
paid judge execution activate in M5 and require provisioned GPU/API resources
and an approved budget. M3-T10 validates the audit behavior only.
