# M4–M6 resource compatibility research

Research date: 2026-09-26. This note records source-based preparation decisions,
not successful GPU runs. Runtime results belong in the session validation report.
The five upstream commits and existing gold answers remain those in
[`val.md`](../../val.md). No package was installed and no GPU job was started by
this research task.

## 1. vLLM / LlamaFactory environment

The observed host has NVIDIA driver 535.216.01, A800 GPUs, and glibc 2.31.
The harness pin requires `vllm>=0.18`. The vLLM 0.18.0 release's **default**
x86-64 wheel is `manylinux_2_31`, so the host glibc is sufficient. Its optional
CUDA 13.0 wheel is `manylinux_2_35`; that variant is unsuitable here. The versioned
installation page's generic example uses the latter platform tag, so filenames
must be checked against actual release assets, not inferred from the example.
[Release assets](https://github.com/vllm-project/vllm/releases/tag/v0.18.0),
[PyPI release metadata](https://pypi.org/pypi/vllm/0.18.0/json).

vLLM 0.18.0's source selects CUDA 12.9 and pins torch 2.10.0,
torchvision 0.25.0, torchaudio 2.10.0 and flashinfer-python 0.6.6. Its
Transformers constraint is `>=4.56.0,<5`. Conversely, the default PyPI torch
2.10.0 metadata selects CUDA 12.8 libraries. Explicitly select the PyTorch
`cu129` index/backend when constructing this isolated environment; do not mix an
arbitrary existing torch with the vLLM wheel.
[vLLM CUDA selection](https://github.com/vllm-project/vllm/blob/v0.18.0/vllm/envs.py),
[vLLM CUDA dependencies](https://github.com/vllm-project/vllm/blob/v0.18.0/requirements/cuda.txt),
[torch metadata](https://pypi.org/pypi/torch/2.10.0/json),
[versioned installation instructions](https://docs.vllm.ai/en/v0.18.0/getting_started/installation/gpu/).

The official cu129 index lists a Python 3.11 Linux x86-64 torch 2.10.0+cu129 wheel
tagged `manylinux_2_28`. Its index-provided SHA-256 is
`ef82198b7b2f271cda50fa1d7ccd69643ac60dc48c7f38a91510c872b9722028`.
An independent direct HTTP HEAD returned 200 and a one-byte range probe returned
206, both reporting total length `1277929156` bytes; weights/wheels were not
downloaded by this research task.
[Official torch cu129 index](https://download.pytorch.org/whl/cu129/torch/).

Driver 535 is not an automatic rejection: NVIDIA's forward-compatibility matrix
marks `cuda-compat-12-9` with driver 535 as compatible on supported datacenter
GPUs. Ordinary CUDA 12.x minor-version compatibility alone has PTX/JIT
restrictions, making it insufficient evidence for this vLLM workload. Use the
per-application compatibility libraries, then prove actual initialization and
generation. No driver update, reboot or global library replacement is necessary
for this candidate route.
[NVIDIA forward compatibility](https://docs.nvidia.com/deploy/cuda-compatibility/forward-compatibility.html),
[minor-version restrictions](https://docs.nvidia.com/deploy/cuda-compatibility/minor-version-compatibility.html).

Official package independently resolved from NVIDIA's Ubuntu 20.04 package index:

| Property | Value |
|---|---|
| Package | `cuda-compat-12-9` |
| Version | `575.57.08-0ubuntu1` |
| Download | [Official amd64 deb](https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/cuda-compat-12-9_575.57.08-0ubuntu1_amd64.deb) |
| Bytes | `64110116` |
| SHA-256 | `0e67e0011b8cb359cecf5d60c3dd7be9c2a69f1b7eb531a4536b83b02173d87a` |

Source: [NVIDIA Packages.gz](https://developer.download.nvidia.com/compute/cuda/repos/ubuntu2004/x86_64/Packages.gz).

Preparation checklist, with `$RESOURCE_ROOT` denoting the user-provisioned
validation directory:

1. Download only this package into the resource directory and verify its size and
   SHA-256. Use `dpkg-deb -x` into a dedicated child directory; do **not** use
   `dpkg -i`, `apt install`, `ldconfig`, or overwrite a system library.
2. The extracted directory `usr/local/cuda-12.9/compat` is the compatibility-library
   directory. For validation child processes only, set
   `VLLM_ENABLE_CUDA_COMPATIBILITY=1` and
   `VLLM_CUDA_COMPATIBILITY_PATH` to that directory. For standalone torch processes,
   prepend it to that process's `LD_LIBRARY_PATH`, preserving existing entries.
3. Verify package metadata, then import vLLM before torch CUDA initialization.
   First perform a small tensor operation and synchronization, then one bounded
   generation. A successful import alone is not GPU validation.
4. Recheck GPU occupancy immediately before each job; expose only the approved
   card. Use bounded model length, batch size and explicit memory utilization.
   Run stages sequentially. Never terminate another user's process.
5. Errors 803/804, unsupported PTX or allocation failures mean this route did not
   pass. Save sanitized evidence; do not respond by changing the system driver.

The two vLLM environment variables and minimal initialization check are documented
in [vLLM 0.18 troubleshooting](https://docs.vllm.ai/en/v0.18.0/usage/troubleshooting/#cuda-error-the-provided-ptx-was-compiled-with-an-unsupported-toolchain).
The observed toolkit is 12.2.91, available outside the current PATH. A prebuilt
vLLM installation does not require rebuilding with that older toolkit. Docker is
not a preparation fallback here because this session lacks daemon access.

The pinned LlamaFactory permits torch >=2.4, Transformers
`>=4.55.0,<=5.8.0,!=4.57.0,!=5.6.0`, PEFT 0.18.0–0.18.1 and datasets <=4.0.0.
Thus torch 2.10.0/cu129, Transformers 4.57.6, PEFT 0.18.1 and datasets <=4.0.0
have a declared constraint intersection with vLLM 0.18.0. This is a proposed shared
environment, not an assertion that every optional integration works together.
[Pinned LlamaFactory dependencies](https://github.com/hiyouga/LlamaFactory/blob/673048c6a543cbbeaed5b8444b8223dc4e23c721/pyproject.toml).

## 2. Supplementary public-model DP validation

The user authorized a public small-model supplementary case while retaining the
original gated Llama-2 scenario as incomplete. That distinction must survive in
the final gate report; a small GPT-2 run is not evidence that Llama-2/ZeRO or the
original ECHR experiment was reproduced.

The pinned llm-dp implementation dispatches positive epsilon to
`_fine_tune_fast_dp_ZERO`; running the normal entry point without DeepSpeed is not
an acceptable substitute. It also contains a complete, unused
`_fine_tune_fast_dp` single-GPU method that creates the author's `PrivacyEngine`,
attaches it to AdamW and trains through the upstream Trainer. A thin validation
driver can explicitly call **that original method** without editing upstream
code. This is an adapter scenario and must be labeled as such.
[Pinned training implementation](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/src/llm_pft/models/language_model.py),
[upstream launch warning](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/README.md).

Pin the author's fastDP fork at
`3339cf45fa334cac67eb6a38726a8726630e31c2`, independently resolved during this
research. Its package setup is pure Python. Single-GPU `PrivacyEngine` imports
DeepSpeed only in a guarded optional block; distributed-engine dependencies are
inside their constructors. Therefore this source path does not require
DeepSpeed, multiple GPUs or nvcc. Do not install its entire legacy requirements
file into the modern vLLM environment.
[fastDP setup](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/setup.py),
[engine](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/fastDP/privacy_engine.py),
[distributed engine](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/fastDP/privacy_engine_dist_stage23.py).

Source-compatible candidate environment, still requiring a real smoke run:
Python 3.10; torch 2.2.0/cu121; Transformers 4.29.0; tokenizers 0.13.3;
accelerate 0.20.3; datasets 2.18.0; numpy 1.26.4; scipy 1.11.4; pyarrow 15.0.2;
the pinned fastDP source. These conservative secondary pins isolate old Trainer
and NumPy/Arrow interfaces; they are preparation choices, not upstream's complete
lockfile. The upstream troubleshooting section explicitly calls out torch 2.2,
Transformers 4.29 and tokenizers 0.13.3.
[Upstream troubleshooting](https://github.com/jyhong836/llm-dp-finetune/blob/7f8b5dff4b92aae90ceccce3ec959b48307bed9e/README.md),
[official torch 2.2 CUDA wheels](https://pytorch.org/get-started/previous-versions/).

Preferred model: DistilGPT2, a public pretrained 82-million-parameter GPT-2 model.
The mirror accepts the legacy Hub ID `distilgpt2`. Its canonical namespaced ID
initially returned HTTP 403 in one probe, but an independent retry returned HTTP
200 with identical metadata; this is not a stable access restriction. Observed metadata:

| Property | Independently observed value |
|---|---|
| Revision | `2290a62682d06624634c1f46a6ad5be0f47f38aa` |
| Weight format | `model.safetensors` only; avoid downloading both formats |
| Weight bytes | `352824413` |
| LFS SHA-256 | `e1ff18884359fe8beb795a5f414feb85a6ce3d929ad019c0d958c039d2b94a1b` |

Sources: [model-author card](https://huggingface.co/distilbert/distilgpt2),
[observed mirror metadata](https://hf-mirror.com/api/models/distilgpt2/revision/2290a62682d06624634c1f46a6ad5be0f47f38aa?blobs=true).
The LFS hash is a pre-download expectation, not proof of downloaded bytes.

Driver requirements and assertions:

- Use a small declared public/synthetic text fixture, e.g. 16 short examples,
  sequence limit 64, batch 1, accumulation 1, exactly two optimizer updates,
  float32, no evaluation, no external experiment logger. This avoids processing
  private data or claiming any ECHR result.
- Instantiate the upstream GPT2 wrapper using the local pinned pretrained model.
  Supply a thin dataset adapter exposing `get_hf_dataset`, `shuffle`, `select`,
  and length. The original method expects these methods. No Flair/NER path is
  needed for this supplementary fixture.
- The method reads `train_args.resume_from_checkpoint`, absent from the custom
  dataclass declaration; set it explicitly to `None` in the driver. Supply a real
  output directory and a bounded `limit_eval_dataset`; disable periodic saves.
- Assert the attached engine is the optimizer's engine, its installed step is
  `dp_step`, and `engine.steps == 2`; assert finite accountant output, a positive
  noise multiplier, and changed model parameters.
- Observe, without replacing returned values, calls to
  `_per_block_clip_grad` and to the fork's noise-producing path. Assert nonempty
  per-sample norm inputs and actual Gaussian draws with positive standard
  deviation. Record aggregate counts/booleans only, not gradients or noise arrays.
- Check every intended trainable parameter remains represented in the privacy
  engine. The fork can drop unsupported parameters; a completed optimizer loop
  alone does not establish coverage of the intended model.
- Pair epsilon 8 and epsilon 4 with automatic sigma calibration; do not force an
  identical noise multiplier. The engine's automatic clipping fixes effective
  `max_grad_norm` to 1, so changing only the requested clipping threshold would
  not demonstrate a real training change. The later independent specification
  review found that `privacy.*` does not match the nested epsilon field: the leaf
  defaults to MEDIUM, while the changed configuration artifact is HIGH. See
  [`m5-m6-runtime-gold.md`](m5-m6-runtime-gold.md) for the exact-field gold and
  policy gap; do not infer HIGH for this leaf from the aggregate result.

Clipping is performed in
[`autograd_grad_sample.py`](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/fastDP/autograd_grad_sample.py);
noise is added by `torch.normal` inside
[`supported_layers_grad_samplers.py`](https://github.com/jyhong836/fast-differential-privacy/blob/3339cf45fa334cac67eb6a38726a8726630e31c2/fastDP/supported_layers_grad_samplers.py).
These observations establish that clipping/noise/update code executed. They do
not certify a production privacy guarantee, sampling assumptions or secure RNG;
do not publish a private-data privacy claim from this bounded engineering test.

## 3. Minimal HarmBench path

Use the upstream **DirectRequest** baseline for exactly one text behavior, then
one target completion, then the local classifier. DirectRequest returns the
selected behavior and optional context unchanged; it does not search, optimize,
or amplify an attack. The default method config has no attacker model, and its
base class does not launch Ray.
[DirectRequest](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/baselines/direct_request/direct_request.py),
[baseline](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/baselines/baseline.py).

The repository declares `vllm>=0.3.0`, but the classifier script accesses old
internals (`cls.llm_engine.tokenizer.tokenizer`) and constructs an LLM without a
memory cap. The completion script imports API and multimodal modules even for a
local text model. Therefore a vLLM 0.18 environment should not be assumed to run
those original CLI scripts unchanged. Candidate routes are an isolated older
vLLM stack, or a documented thin driver that calls original DirectRequest and
`compute_results_classifier`, obtains the tokenizer through a supported API, and
sets strict memory/context limits. The latter must not be reported as unmodified
CLI coverage. Preserve the original classifier prompt and labeling function.
[Declared dependencies](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/requirements.txt),
[classifier CLI](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/evaluate_completions.py),
[completion CLI](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/generate_completions.py),
[classification function](https://github.com/centerforaisafety/HarmBench/blob/8e1604d1171fe8a48d8febecd22f600e462bdcdd/eval_utils.py).

DirectRequest imports still require torch, Transformers, vLLM, Ray and fschat
through its base/model utilities; classifier utilities import spaCy and datasketch.
A text-only adapter can avoid unrelated provider/multimodal imports without
mocking any model result. Target and classifier should run sequentially, with
separate processes releasing GPU allocations between stages. A returned label
is model output, not an independently known gold label; gold should assert the
bounded data flow, original labeling semantics and ReproLLM capture/drift.

## 4. Independent review of reconstructed metadata manifests

The five new metadata-only manifests were compared with the pinned sources and
`val.md` §8.1 before running ReproLLM. All 18 distinct referenced local files match
the independently recorded SHA-256 values. Selected model IDs match the earlier
scenarios; GSM8K retains `main`/`test`, and ECHR retains `train`. The dated FastChat
judge ID is unchanged. No API call or successful gated download is implied.

| Reconstructed input | New manifest SHA-256 |
|---|---|
| FastChat | `73b25168de2f52cc994f8b1535fdf04898ad8d8839e260f2f10893f38a3d9ae9` |
| HarmBench | `73164c087770e87b62aaa9b45fcb831134b47c8bf36c04716b8e1bca57847aa5` |
| LlamaFactory | `7644338fcc0f7f184bbd031d1b89d6bccc24cacb657e254e1c324df3f13defae` |
| llm-dp-finetune | `4967f1ed18b8f2484f1a8de6b1252dc7049f7deb3ec2afe2a47959b9e12cea36` |
| lm-evaluation-harness | `7a524a1dd41cdca08ca1514cbd5eb4874175bfeff73ae69e94eac2d22fc2bc4f` |

Consequently, the matching local artifact hashes and corresponding remote
revision/config/template expectations can be reused. The previous manifest
hashes, complete experiment-presence findings, and original M3 command scenario
cannot be reused: those exact manifest bytes are missing. Keep this reconstruction
as separately identified metadata coverage, not restoration of the original gold.

## 5. Bounded download-mirror research

Follow-up on 2026-09-26: only public metadata and 1-MiB HTTP ranges were fetched;
no complete wheel/model was downloaded, and running transfers and validation
environments were not changed. Requests used direct HTTPS (`trust_env=False`),
identity encoding and at most two concurrent probes. These short observations
do **not** demonstrate a reliable sustained speed improvement over the active
official downloads. Keep the selected versions, filenames and official hashes;
do not change validation gold or the model endpoint because a mirror exists.

### Exact PyTorch wheel candidates

The [SJTU service documentation](https://mirror.sjtu.edu.cn/docs/pytorch-wheels)
identifies its service as a mirror of official PyTorch wheels. Both SJTU and
NJU's directly observed Simple indexes expose the exact official SHA-256 below:
[SJTU cu121](https://mirror.sjtu.edu.cn/pytorch-wheels/cu121/torch/),
[SJTU cu129](https://mirror.sjtu.edu.cn/pytorch-wheels/cu129/torch/),
[NJU cu121](https://mirrors.nju.edu.cn/pytorch/whl/cu121/torch/),
[NJU cu129](https://mirrors.nju.edu.cn/pytorch/whl/cu129/torch/).
Alibaba Cloud's own [cu121 directory](https://mirrors.aliyun.com/pytorch-wheels/cu121/)
and [cu129 directory](https://mirrors.aliyun.com/pytorch-wheels/cu129/) list the
files; its `/torch/` Simple-index paths returned 404, so these are direct-file
candidates, not verified substitute pip indexes.

| Target | Exact filename | Expected bytes | Official SHA-256 |
|---|---|---:|---|
| DP | `torch-2.2.0+cu121-cp310-cp310-linux_x86_64.whl` | 757270759 | `c441021672ebe2e5afbdb34817aa85e6d32130f94df2da9ad4cb78a9d4b81370` |
| Modern | `torch-2.10.0+cu129-cp311-cp311-manylinux_2_28_x86_64.whl` | 1277929156 | `ef82198b7b2f271cda50fa1d7ccd69643ac60dc48c7f38a91510c872b9722028` |

Authority: [official cu121 index](https://download.pytorch.org/whl/cu121/torch/)
and [official cu129 index](https://download.pytorch.org/whl/cu129/torch/).
The observed cu121 official index links to PyTorch's `download-r2` host.

All six direct candidates returned HTTP 206 for `bytes=0-1048575` with the exact
total lengths above. Times include connection/redirect overhead. Whole-file
estimates simply extrapolate that tiny sample, **not** a download-time promise.

| Candidate | Exact direct URL | 1 MiB total seconds | MiB/s | Naive full-file estimate |
|---|---|---:|---:|---|
| SJTU DP | [wheel](https://mirror.sjtu.edu.cn/pytorch-wheels/cu121/torch-2.2.0%2Bcu121-cp310-cp310-linux_x86_64.whl) | 8.930 | 0.112 | 1.8 h |
| SJTU modern | [wheel](https://mirror.sjtu.edu.cn/pytorch-wheels/cu129/torch-2.10.0%2Bcu129-cp311-cp311-manylinux_2_28_x86_64.whl) | 17.866 | 0.056 | 6.0 h |
| NJU DP | [wheel](https://mirrors.nju.edu.cn/pytorch/whl/cu121/torch-2.2.0%2Bcu121-cp310-cp310-linux_x86_64.whl) | 11.901 | 0.084 | 2.4 h |
| NJU modern | [wheel](https://mirrors.nju.edu.cn/pytorch/whl/cu129/torch-2.10.0%2Bcu129-cp311-cp311-manylinux_2_28_x86_64.whl) | 12.352 | 0.081 | 4.2 h |
| Alibaba DP | [wheel](https://mirrors.aliyun.com/pytorch-wheels/cu121/torch-2.2.0%2Bcu121-cp310-cp310-linux_x86_64.whl) | 3.864 | 0.259 | 47 min |
| Alibaba modern | [wheel](https://mirrors.aliyun.com/pytorch-wheels/cu129/torch-2.10.0%2Bcu129-cp311-cp311-manylinux_2_28_x86_64.whl) | 18.082 | 0.055 | 6.1 h |

SJTU redirects normally to its own `s3.jcloud.sjtu.edu.cn` storage. Second ranges
(`1048576-2097151`) returned the correct offset and length: SJTU DP took 26.064 s,
SJTU modern 19.705 s, and Alibaba DP 4.510 s. This demonstrates range support,
not stable throughput. No challenge, authentication or rate-limit bypass was
attempted. Huawei's [official service page](https://www.huaweicloud.com/product/mirrors)
documents a general mirror service, but the checked `/pytorch/` paths under both
`mirrors.huaweicloud.com` and `repo.huaweicloud.com` returned the 12109-byte HTML
portal rather than wheel indexes. No usable exact Huawei wheel URL was verified.

### Qwen publisher's ModelScope copy

The [Qwen team's official repository](https://github.com/QwenLM/Qwen3#modelscope)
links its ModelScope organization and recommends ModelScope for mainland-China
downloads. The official model's fixed ModelScope revision
`2de2439ea21be1dc5cb21f22f88af07e43393cbb` reports the following weight hashes,
identical to the existing HF revision
`cdbee75f17c01a7cc42f958dc650907174af0554`:

| File | Bytes | Matching SHA-256 |
|---|---:|---|
| `model-00001-of-00003.safetensors` | 3957900840 | `75311d91bb08cf0b882913da464a1e722a31fb44db35208663487efb7a3d8ed6` |
| `model-00002-of-00003.safetensors` | 3987450520 | `0b48adbb1f60e901153d91907ba11ce63bd4b8b584482e730f48808d055dfba1` |
| `model-00003-of-00003.safetensors` | 99630640 | `7dd39ccca5e4de123c74c14af44c9bf2eb75df33b4614382af0134528e060d5d` |

Evidence: [fixed ModelScope file metadata](https://modelscope.cn/api/v1/models/Qwen/Qwen3-4B-Instruct-2507/repo/files?Revision=2de2439ea21be1dc5cb21f22f88af07e43393cbb&Recursive=true),
[pinned HF metadata through the configured public mirror](https://hf-mirror.com/api/models/Qwen/Qwen3-4B-Instruct-2507/revision/cdbee75f17c01a7cc42f958dc650907174af0554?blobs=true).
This establishes weight-file metadata agreement, **not** equality of whole
repository revisions, configuration/tokenizer files, or already downloaded bytes.

- [Fixed shard 2 URL](https://modelscope.cn/models/Qwen/Qwen3-4B-Instruct-2507/resolve/2de2439ea21be1dc5cb21f22f88af07e43393cbb/model-00002-of-00003.safetensors):
  HTTP 206, exact total size, first 1 MiB in 8.929 s (0.112 MiB/s); second 1-MiB
  range in 10.475 s. Naive first-sample extrapolation is 9.4 h for the whole shard.
- [Fixed shard 3 URL](https://modelscope.cn/models/Qwen/Qwen3-4B-Instruct-2507/resolve/2de2439ea21be1dc5cb21f22f88af07e43393cbb/model-00003-of-00003.safetensors):
  HTTP 206, exact total size, first 1 MiB in 4.049 s (0.247 MiB/s); naive whole-shard
  extrapolation is 6.4 min. Both normally redirect to
  `cdn-lfs-cn-1.modelscope.cn`.

If the transfer owner later uses any candidate, verify the completed file's exact
length and full SHA-256 against the authority above **before** installing it or
placing it in the pinned HF snapshot. A correct ZIP prefix, safetensors header,
range offset, mirror-provided hash or file size alone is insufficient. Preserve
the original HF identity/revision and the existing configuration/tokenizer bytes;
switching the transport for identical public weights is not a new model case.
No gated Llama-2 substitute or paid/API path was investigated.

Process note: an initial `uv run python` metadata probe inadvertently rebuilt and
reinstalled only the current local editable ReproLLM package in the repository
environment. Later probes invoked the existing interpreter directly. No tracked
`src/`, `pyproject.toml` or `uv.lock` changes resulted; no external package was
installed and neither validation environment was altered. No installer or repair
command was subsequently run.

### Follow-up: exact cuDNN and cuBLAS PyPI wheels

The next bounded check covered only the two exact modern-environment CUDA wheels
below. Official PyPI release JSON was read first; all three mirror indexes then
listed the same filenames and SHA-256 values. Mirror endpoints came from their
operators' own instructions: [Tsinghua TUNA](https://mirror.tuna.tsinghua.edu.cn/help/pypi/),
[Alibaba Cloud](https://developer.aliyun.com/mirror/pypi), and
[Huawei Cloud](https://www.huaweicloud.com/special/pypi-jingxiang.html).

| Official release metadata | Exact Linux x86-64 filename | Bytes | Official SHA-256 |
|---|---|---:|---|
| [cuDNN 9.10.2.21](https://pypi.org/pypi/nvidia-cudnn-cu12/9.10.2.21/json) | `nvidia_cudnn_cu12-9.10.2.21-py3-none-manylinux_2_27_x86_64.whl` | 706758467 | `949452be657fa16687d0930933f032835951ef0892b37d2d53824d1a84dc97a8` |
| [cuBLAS 12.9.1.4](https://pypi.org/pypi/nvidia-cublas-cu12/12.9.1.4/json) | `nvidia_cublas_cu12-12.9.1.4-py3-none-manylinux_2_27_x86_64.whl` | 581242350 | `453611eb21a7c1f2c2156ed9f3a45b691deda0440ec550860290dc901af5b4c2` |

Each request asked for `bytes=1048576-2097151`, using direct HTTPS,
`Accept-Encoding: identity`, and at most two concurrent requests. All six
responses were HTTP 206 with the exact requested offset, `Content-Length:
1048576`, and the appropriate total file size above. Reads were capped at 1 MiB
and approximately 20 seconds, so the two partial rows are **not** completed
1-MiB throughput measurements. End-to-end rates include connection overhead.

| Exact mirror URL | Bytes actually read | Elapsed seconds | End-to-end MiB/s | Result |
|---|---:|---:|---:|---|
| [TUNA cuDNN](https://pypi.tuna.tsinghua.edu.cn/packages/ba/51/e123d997aa098c61d029f76663dedbfb9bc8dcf8c60cbd6adbe42f76d049/nvidia_cudnn_cu12-9.10.2.21-py3-none-manylinux_2_27_x86_64.whl) | 901120 | 20.079 | 0.043 | Read stopped at time budget |
| [TUNA cuBLAS](https://pypi.tuna.tsinghua.edu.cn/packages/77/3c/aa88abe01f3be3d1f8f787d1d33dc83e76fec05945f9a28fbb41cfb99cd5/nvidia_cublas_cu12-12.9.1.4-py3-none-manylinux_2_27_x86_64.whl) | 1048576 | 8.842 | 0.113 | Range completed |
| [Alibaba cuDNN](https://mirrors.aliyun.com/pypi/packages/ba/51/e123d997aa098c61d029f76663dedbfb9bc8dcf8c60cbd6adbe42f76d049/nvidia_cudnn_cu12-9.10.2.21-py3-none-manylinux_2_27_x86_64.whl) | 688128 | 20.356 | 0.032 | Read stopped at time budget |
| [Alibaba cuBLAS](https://mirrors.aliyun.com/pypi/packages/77/3c/aa88abe01f3be3d1f8f787d1d33dc83e76fec05945f9a28fbb41cfb99cd5/nvidia_cublas_cu12-12.9.1.4-py3-none-manylinux_2_27_x86_64.whl) | 1048576 | 12.878 | 0.078 | Range completed |
| [Huawei cuDNN](https://repo.huaweicloud.com/repository/pypi/packages/ba/51/e123d997aa098c61d029f76663dedbfb9bc8dcf8c60cbd6adbe42f76d049/nvidia_cudnn_cu12-9.10.2.21-py3-none-manylinux_2_27_x86_64.whl) | 1048576 | 4.196 | 0.238 | Range completed |
| [Huawei cuBLAS](https://repo.huaweicloud.com/repository/pypi/packages/77/3c/aa88abe01f3be3d1f8f787d1d33dc83e76fec05945f9a28fbb41cfb99cd5/nvidia_cublas_cu12-12.9.1.4-py3-none-manylinux_2_27_x86_64.whl) | 1048576 | 8.468 | 0.118 | Range completed |

Huawei cuDNN was the fastest tiny sample (0.342 MiB/s for its body alone), but
only modestly above the transfer owner's reported current official-file rate of
about 0.2 MiB/s. No clearly faster sustained alternative was established, so this
research does not recommend interrupting existing transfers. Matching mirror
index hashes and range headers are still not full-file verification: any later
download must match the official length and complete SHA-256 before use. This
follow-up used the existing interpreter directly, installed nothing, and changed
no process, validation environment, download, credential, endpoint or gold.

### Follow-up: one-byte checks for four remaining CUDA wheels

Four additional exact Linux x86-64 releases were checked against their official
PyPI JSON first, then both Huawei and TUNA Simple indexes. All eight indexes
returned HTTP 200 and contained the exact filename with the official SHA-256.
Each direct wheel URL below received **one** `Range: bytes=0-0` request, with
identity encoding, direct HTTPS and at most two requests in flight. All eight
returned HTTP 206, `Content-Length: 1` and `Content-Range: bytes 0-0/<size>`
matching the official size. Only one body byte was read from each URL. No speed
measurement or full download was performed, and no process/environment/GPU was
touched. These existence checks do not predict resumed multi-host throughput.

| Official metadata | Exact filename | Bytes | Official SHA-256 |
|---|---|---:|---|
| [cuSolver 11.7.5.82](https://pypi.org/pypi/nvidia-cusolver-cu12/11.7.5.82/json) | `nvidia_cusolver_cu12-11.7.5.82-py3-none-manylinux_2_27_x86_64.whl` | 338117415 | `15da72d1340d29b5b3cf3fd100e3cd53421dde36002eda6ed93811af63c40d88` |
| [cuSPARSE 12.5.10.65](https://pypi.org/pypi/nvidia-cusparse-cu12/12.5.10.65/json) | `nvidia_cusparse_cu12-12.5.10.65-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 366465088 | `73060ce019ac064a057267c585bf1fd5a353734151f87472ff02b2c5c9984e78` |
| [cuSPARSELt 0.7.1](https://pypi.org/pypi/nvidia-cusparselt-cu12/0.7.1/json) | `nvidia_cusparselt_cu12-0.7.1-py3-none-manylinux2014_x86_64.whl` | 287193691 | `f1bb701d6b930d5a7cea44c19ceb973311500847f81b634d802b7b539dc55623` |
| [NCCL 2.27.5](https://pypi.org/pypi/nvidia-nccl-cu12/2.27.5/json) | `nvidia_nccl_cu12-2.27.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl` | 322348229 | `ad730cf15cb5d25fe849c6e6ca9eb5b76db16a80f13f425ac68d8e2e55624457` |

| Package | Huawei exact URL | TUNA exact URL | Both checks |
|---|---|---|---|
| cuSolver | [wheel](https://repo.huaweicloud.com/repository/pypi/packages/33/40/79b0c64d44d6c166c0964ec1d803d067f4a145cca23e23925fd351d0e642/nvidia_cusolver_cu12-11.7.5.82-py3-none-manylinux_2_27_x86_64.whl) | [wheel](https://pypi.tuna.tsinghua.edu.cn/packages/33/40/79b0c64d44d6c166c0964ec1d803d067f4a145cca23e23925fd351d0e642/nvidia_cusolver_cu12-11.7.5.82-py3-none-manylinux_2_27_x86_64.whl) | Index filename/SHA match; 206, total 338117415 |
| cuSPARSE | [wheel](https://repo.huaweicloud.com/repository/pypi/packages/12/46/b0fd4b04f86577921feb97d8e2cf028afe04f614d17fb5013de9282c9216/nvidia_cusparse_cu12-12.5.10.65-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl) | [wheel](https://pypi.tuna.tsinghua.edu.cn/packages/12/46/b0fd4b04f86577921feb97d8e2cf028afe04f614d17fb5013de9282c9216/nvidia_cusparse_cu12-12.5.10.65-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl) | Index filename/SHA match; 206, total 366465088 |
| cuSPARSELt | [wheel](https://repo.huaweicloud.com/repository/pypi/packages/56/79/12978b96bd44274fe38b5dde5cfb660b1d114f70a65ef962bcbbed99b549/nvidia_cusparselt_cu12-0.7.1-py3-none-manylinux2014_x86_64.whl) | [wheel](https://pypi.tuna.tsinghua.edu.cn/packages/56/79/12978b96bd44274fe38b5dde5cfb660b1d114f70a65ef962bcbbed99b549/nvidia_cusparselt_cu12-0.7.1-py3-none-manylinux2014_x86_64.whl) | Index filename/SHA match; 206, total 287193691 |
| NCCL | [wheel](https://repo.huaweicloud.com/repository/pypi/packages/6e/89/f7a07dc961b60645dbbf42e80f2bc85ade7feb9a491b11a1e973aa00071f/nvidia_nccl_cu12-2.27.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl) | [wheel](https://pypi.tuna.tsinghua.edu.cn/packages/6e/89/f7a07dc961b60645dbbf42e80f2bc85ade7feb9a491b11a1e973aa00071f/nvidia_nccl_cu12-2.27.5-py3-none-manylinux2014_x86_64.manylinux_2_17_x86_64.whl) | Index filename/SHA match; 206, total 322348229 |

These are transport candidates for the **same pinned bytes**, not alternate
versions or an assertion that full mirror files have been verified. After any
single-host or multi-host resumed transfer, verify the completed file against
the official full-file SHA-256 and size above before use. No version, validation
gold or endpoint change is implied.
