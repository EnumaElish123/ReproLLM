# Why ReproLLM

Ten reproducibility failures LLM researchers actually hit, and the ReproLLM
answer to each.

1. **"Which model did we actually run?"** — `model.revision_pinned` +
   `lock` resolve the exact HF commit, tokenizer revision, and chat-template
   hash; API models get honest pinnability, never a fake SHA.
2. **"The README says temperature 0."** — `consistency.generation_params`
   compares the manifest against what the run *observed* on the CLI and in
   configs; disagreements are CRITICAL with both values.
3. **"It worked last month."** — `diff` between two runs shows exactly which
   fields drifted (model, data, prompt, backend version) with severity, not
   a wall of JSON.
4. **"The assistant changed under us."** — `models.*` drift is HIGH;
   judge-model pinnability is recorded alongside.
5. **"Which prompt did we use?"** — prompt content hashes, not paths; a
   changed prompt is HIGH drift even when the filename is identical.
6. **"vLLM updated and nothing else changed."** — backend/package versions
   are captured per run; patch bumps are LOW, minor/major are MEDIUM_HIGH.
7. **"We can't reproduce the paper's numbers."** — `export` writes a
   REPRODUCIBILITY.md with every unresolved and unpinnable value listed;
   what you can't reproduce is stated, not hidden.
8. **"The .env was in the repo."** — `env.secret_files_ignored` is CRITICAL;
   run capture redacts every artifact it writes (leak-gated in CI).
9. **"Nobody knows the seed."** — `exec.seed_declared` and friends make
   missing seeds visible findings instead of archaeology.
10. **"Our tool has its own knobs."** — project rules and the experimental
    discover step turn one-off parameters into deterministic checks after a
    single explicit acceptance.

Positioning: MLflow/W&B track metrics; ReproLLM records *identity and drift*.
reprokit-style tools freeze environments generically; ReproLLM knows what an
LLM experiment is (models by role, judges, prompts, generation parameters).
