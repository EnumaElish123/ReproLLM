# Native GPU validation follow-up — 2026-10-20

Candidate: `948d16423023027fff77322b8a872acaba306691`. The original bounded workloads, model/data inputs, pins, and gold remain unchanged.

All 10 native children, 5 complete semantic pairs, 20 export states, 1,291 export comparisons and the 244-check terminal review passed. The 170 command receipts and 340 original streams have a complete digest index. The 84-file original run-tree index includes 64 byte-identical safe persisted nonlog artifacts; its 20 runtime logs remain local and are hash-only. The supplied run directories therefore are not complete log replay trees.

Start with [summary.json](summary.json), [control/terminal-evidence-review.json](control/terminal-evidence-review.json), [original-command-stream-index.json](original-command-stream-index.json), and [original-run-tree-index.json](original-run-tree-index.json). Complete capture, actual-call consumption, structural/numeric output checks, full audit/diff projections and the 20 exports are under `runtime/` and `exports-*`.

The DP epsilon leaf is MEDIUM (8 → 4). Its changed configuration digest is HIGH, explaining pair exit 1 under `--fail-on HIGH`; all self-diffs are empty. HarmBench's four actual argument/engine-log observations independently verify .28/.45, TP1, float16 and length 2048. Those logs show CUDA; GPU0 is tied to launch baseline/guard and unchanged inputs, rather than a direct physical-device query inside the engine.

The top-level driver alone paused for observer qualification while its current child/controller completed naturally, then resumed unchanged. No child, controller, model or API request repeated. The stricter path observer rechecked all 84 original files using the same raw evidence. Original tool failures, corrections, qualification controls and helper freezes are retained.

Commands, controls and helper sources are explicit path/identity sharing projections. Helper sources and projected tool streams are inert and are not claimed executable. Original hashes, retained hashes and every transformation are recorded in [source-index.json](source-index.json) and [retained-files.json](retained-files.json); [audit.json](audit.json) checks the complete package. Exact credentials were not read by the packager; the final repository scan is performed separately.

This package does not close the missing original M3 metadata inputs, authenticated gated HF success, or release readiness. Paid judge requests were not repeated.
