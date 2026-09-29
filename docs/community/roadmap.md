# Roadmap (post-Beta)

Issue-ready items from `docs/plan/backlog.md`; each becomes a GitHub issue
with the matching label and milestone when the tracker is available.

| Priority | Item | Why now |
|---|---|---|
| P1 | `export --template neurips/acl/acm` checklist mapping (M10) | Direct paper-submission value |
| P1 | GitHub Action + `--format github` (M9) | Zero-install adoption path |
| P2 | Provider identity vs compatibility contract (DeepSeek `provider: other` CRITICAL) | Honest severity for OpenAI-compatible vendors |
| P2 | Judge-only profile variant | Five presence CRITICALs on judge-only runs are noise |
| P2 | Nested judge-parameter drift severity (`evaluation.judge.*` MEDIUM gap) | Policy review, spec change first |
| P2 | Dataset content fingerprints (sampled hashing) | Closes the largest "not recorded" gap |
| P3 | `rag` / `agent` profiles | Detected, report-only today |
| P3 | `discover --paper` (paper–code consistency) | D-26; blocked on maintainer decision |
| P3 | SARIF output | CI integrations |

## Good first issues

1. `gen.stop_declared` / `prompt.few_shot_declared` negative corpora from real repositories.
2. Add `wildjailbreak` keyword to the `safety` profile detect block + snapshot.
3. New nvidia-smi fixture: 3-GPU CSV (parsing coverage).
4. FAQ entry for conda users (environment.yml + pip block).
5. `doctor` should print the effective `HF_ENDPOINT` mirror configuration.
6. Examples: add an `llm_judge` example manifest exercising judge bindings.
7. `docs/rules.md` cross-links from each rule to its spec section anchor.
8. A `--json` flag for `reprollm check_no_leaks`-style scanning inside `run` (post-run warning hook).
