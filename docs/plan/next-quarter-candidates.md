# Next Quarter Candidate Directions (2027 Q1)

Discussion draft — none of these are scheduled for implementation. Pick from
user feedback after the adoption sprint (M9–M12). Ranked by estimated
adoption impact vs. effort.

## Tier 1: High impact, moderate effort

| Candidate | Why it matters | Effort | Blocked by |
|---|---|---|---|
| Dataset content fingerprints (sampled hashing) | Closes the largest "not recorded" gap; reviewers ask for it | ~1 sprint | Spec decision on sampling scheme |
| `rag` / `agent` profiles | Detected today but report-only; two large user communities | ~0.5 sprint | — |
| Multi-stage / pipeline experiments | Real experiments have stages; single manifest is limiting | ~2 sprints | Schema design |
| SARIF output | GitHub Code Scanning integration; complements the Action | ~0.3 sprint | — |

## Tier 2: Moderate impact, low effort

| Candidate | Why | Effort |
|---|---|---|
| Anthropic / Gemini / Ollama providers | Broader provider coverage for pinnability | ~0.5 sprint |
| `discover --paper` (paper-code consistency) | D-26 reserved; strong differentiation | ~1 sprint (spec first) |
| Heuristic flag parsing (beyond bindings) | Reduce manifest friction for non-declarative users | ~0.5 sprint |
| `--format sarif` alongside `--format github` | Round out CI output options | ~0.2 sprint |

## Tier 3: Worth considering, higher risk

| Candidate | Why risky |
|---|---|
| Hosted validation service | Violates local-first (D-03); would need a new decision |
| IDE integration | Large effort, uncertain adoption path |
| Benchmark-quality scoring | Out of scope (§3 non-goals); slippery slope |

## Decision process

1. After M12, review `docs/adoption.md` and upstream PR feedback
2. Pick 2–3 Tier 1 items for the next sprint cycle
3. Open spec issues for each; design before implementing
