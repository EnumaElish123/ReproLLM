# Example: hf_vllm_eval

HuggingFace + vLLM evaluation. Shows: dependency pinning warnings, profile detection (inference + evaluation), a fully-completed manifest.

Inspect the completed declaration without executing the model script:

```bash
reprollm audit . --level 1
reprollm lock . --check
```

Audit may exit 1 for the intentionally imperfect research repository; exit 2 means a usage or input error. The committed lock contains historical network metadata, not proof that the model ran here.

To edit the declaration or generate an export, copy this directory outside the ReproLLM checkout first. `init --force` overwrites the completed manifest with a new scaffold. Follow the [resource-free quick start](../../docs/quickstart.md) for the full workflow.
