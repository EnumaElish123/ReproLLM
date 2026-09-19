# fixture: hf_vllm_eval

HF model + vLLM + datasets evaluation repository. Level 0 expectations: git repo
with a clean tree; dependency manifest present; `requirements.txt` pins
transformers and datasets but not vllm; no python version declared. Level 1/2
manifests arrive in M3 (`manifests/complete.yaml`, `manifests/gaps.yaml`).

Deterministic commit SHA (record via `tests/unit/fixtures/test_materialize_repo.py`):
see the assertion in that test; update both together if the tree changes.

Deterministic HEAD: a93c8fd33a13a51257c71797866669f91564e49d

M4 Level 2 uses the complete manifest and mocked Hub metadata. Model, tokenizer,
chat template, config, and dataset resolve exactly. The fixed environment has no
vLLM distribution, so `gen.backend_version_locked` intentionally warns. The lock
snapshot includes real manifest/file hashes and is committed before audit so
Git findings remain deterministic. Summary (C/W/I/P/S): `0/1/2/42/9`.
