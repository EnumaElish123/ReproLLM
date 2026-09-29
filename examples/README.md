# ReproLLM examples

Runnable example repositories generated from the test fixtures.
Each contains a complete `reprollm.yaml`; audit it, re-init it, export it.

- [hf_vllm_eval](./hf_vllm_eval/) — dependency pinning warnings, profile detection (inference + evaluation), a fully-completed manifest
- [openai_judge_eval](./openai_judge_eval/) — judge-profile detection, unpinnable closed-source models, the .env.example exemption
- [privacy_custom_params](./privacy_custom_params/) — secret-file detection (the tracked .env is a planted fake), custom parameters via project rules, the privacy profile

Regenerate with `uv run python scripts/refresh_examples.py`.
