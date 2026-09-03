# fixture: hf_vllm_eval

HF model + vLLM + datasets evaluation repository. Level 0 expectations: git repo
with a clean tree; dependency manifest present; `requirements.txt` pins
transformers and datasets but not vllm; no python version declared. Level 1/2
manifests arrive in M3 (`manifests/complete.yaml`, `manifests/gaps.yaml`).

Deterministic commit SHA (record via `tests/unit/fixtures/test_materialize_repo.py`):
see the assertion in that test; update both together if the tree changes.

Deterministic HEAD: a93c8fd33a13a51257c71797866669f91564e49d
