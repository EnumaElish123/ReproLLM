# Independent pinned-source inspection for R07-C D-M

This is source inspection and a prewritten expectation, not a ReproLLM execution, Gate A, or conditional product result. All five checkouts have their required public origin and pinned commit and are clean before and after.

| Project | Pin | Captured declaration candidates | Actual requirements nodes | Known body failures | Expected complete deltas |
|---|---|---|---|---|---|
| lm-evaluation-harness | `b954108c9baa` | 2 | 1 | 0 | None |
| FastChat | `587d5cfa1609` | 1 | 0 | 0 | None |
| LlamaFactory | `673048c6a543` | 2 | 1 | 0 | None |
| HarmBench | `8e1604d1171f` | 2 | 2 | 0 | None |
| llm-dp-finetune | `7f8b5dff4b92` | 1 | 1 | 0 | None |

All eight captured logical declaration candidate bodies match their previously independently verified Git blob inventory by byte count and SHA256. All three manager manifests are readable TOML mappings; all five requirements roots are readable UTF-8 bodies. None has a supported include edge, so there are no additional actual graph nodes. No dependency-named path is excluded by the current candidate/listing limits in these checkouts.

## Exact candidate paths

- lm-evaluation-harness: `lm_eval/tasks/japanese_leaderboard/requirements.txt`, `pyproject.toml`.
- FastChat: `pyproject.toml`.
- LlamaFactory: `docs/requirements.txt`, `pyproject.toml`.
- HarmBench: `adversarial_training/alignment-handbook/requirements.txt`, `requirements.txt`.
- llm-dp-finetune: `requirements.txt`.

## Complete-output expectation

The proposed new typed declaration-body failure inventory must be empty for every project. Existing declarations, lock inventory/credit, diagnostics, project barriers, Python coverage, profile/hint detection and rule results therefore follow the existing paths. The expected delta is empty for the complete L0 audit and facts of all five projects, not merely for summary counts. Current initialized L1 audits and generated manifests/config/project-rules/export are likewise expected to retain their complete prior bytes apart from the existing permitted audit metadata exclusions.

`gold-delta-expectation.json` binds all ten complete L0 audit/facts oracle files by size/hash and verifies repository copies equal the immutable originals. No gold is edited or inferred from current product output. Any later conditional observation must compare complete reports and explain every delta.

## Method and limits

The 35 successful commands are read-only Git pin/origin/status/listing checks. All stdout, stderr, arguments, exit statuses and elapsed times are retained in `commands.json`, `raw/` and the attempt receipt. The independent source reader uses bounded safe UTF-8 capture, TOML/YAML document decoding and only existing supported normalized requirements include traversal. It imports no ReproLLM code and runs no product, package-manager, network, credential, GPU, test or quality command. Source byte hashes and checkout identity/clean status are rechecked after inspection.

This settles only the source-derived no-change expectation for these fixed pins. Unsupported readable dependency grammar, decoded shapes, missing/unexpanded/noncandidate nodes, listing completeness and simulated unreadable fixtures are not claimed as covered.
