# ReproLLM examples

Example research repositories generated from the test fixtures.
The three fixture-derived examples contain a completed `reprollm.yaml` and a reviewed historical lock.
Use `audit --level 1` and `lock --check` to inspect them. Copy an example outside this checkout before editing it or generating artifacts. Running its model script requires its own dependencies and resources.

The [quick start](../docs/quickstart.md) exercises capture, diff and export with only the Python standard library.

- [hf_vllm_eval](./hf_vllm_eval/) — HuggingFace + vLLM evaluation. Shows: dependency pinning warnings, profile detection (inference + evaluation), a fully-completed manifest.
- [openai_judge_eval](./openai_judge_eval/) — OpenAI LLM-as-a-judge. Shows: judge-profile detection, unpinnable closed-source models, the .env.example exemption.
- [privacy_custom_params](./privacy_custom_params/) — Privacy-preserving fine-tuning. Shows: privacy declarations and profile detection. The fixture's planted fake .env is omitted from this example.
- [lm_eval_replay](./lm_eval_replay/) — Native GSM8K A/B recipe with separate static, standard-library and GPU validation. Its lock is generated in a disposable pinned-framework checkout; follow its README before running.

Regenerate with `uv run python scripts/refresh_examples.py`.
