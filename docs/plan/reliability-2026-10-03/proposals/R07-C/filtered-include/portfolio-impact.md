# Independent five-project source applicability

Status: source inventory only; no new policy has been accepted or implemented.

The five frozen Git trees contain exactly five `requirements*.txt` roots. Every root is a bounded regular file with no excluded ancestor name, virtualenv marker or physical alias in the inspected path. No root contains a physical line beginning with `-r` or `--requirement` after stripping. Therefore no supported include edge, and hence no reached candidate-filtered include target, occurs in this portfolio.

| Project | Fixed pin | Requirements sources | Supported include lines |
|---|---|---|---|
| lm-evaluation-harness | `b954108c9baaaa934b4ad842033b31a97ee30816` | `lm_eval/tasks/japanese_leaderboard/requirements.txt` (lines 1–4, SHA256 `b00ec29d1fe0efb651376d76f3f396e625adc15d8b0c97a936b8e13d46d1d911`) | 0 |
| FastChat | `587d5cfa1609a43d192cedb8441cac3c17db105d` | none | 0 |
| LlamaFactory | `673048c6a543cbbeaed5b8444b8223dc4e23c721` | `docs/requirements.txt` (lines 1–3, SHA256 `5898e7fda4f69d4b4d79fb84e854ac8e0b75845f2e0b9aad8e9057d91ae56ac6`) | 0 |
| HarmBench | `8e1604d1171fe8a48d8febecd22f600e462bdcdd` | `adversarial_training/alignment-handbook/requirements.txt` (lines 1–26, SHA256 `592459a407b2956d95a7bdc4da80f9af08f9e388be14827ded210d3d45cff5b7`), `requirements.txt` (lines 1–21, SHA256 `a342b21c680e1d3102953f7937c97db58f095791f311953465148a87f25f5e9d`) | 0 |
| llm-dp-finetune | `7f8b5dff4b92aae90ceccce3ec959b48307bed9e` | `requirements.txt` (lines 1–6, SHA256 `6c807ef68820081403e7d7e46d9802a805460ffbd87ed5a2c0a6df8ca5cd18bb`) | 0 |

## Conditional effect forecast

Under a narrow accepted change that only records within-budget candidate-filtered supported include targets, the independent expected five-project delta is empty. Existing captured graphs from product `9903627` have the same five roots, all nodes readable, no include events and no unexpanded targets; their original indexed hashes corroborate the source inventory. Those records are historical, not fresh execution on a proposed candidate.

Zero applicability does not validate the trigger or establish that the new policy passed. No audit/init/lock/export/collector/Gate A, candidate, tests or network/resource operation ran during this P-A. Do not update gold from future current output. Focused adversarial cases and final fresh five-project validation remain required for any accepted P-B.

## Current contract boundary

Specification §12.3.8 (D-G) intentionally covers only normalized targets missing from the final graph at the depth frontier. `deps._RequirementsGraph._node` currently creates an unreadable node for an actually reached candidate rejection without recording a declaration read issue; `_closure` retains an include-unreadable diagnostic. That node is present, so it cannot satisfy D-G’s absent-final-node predicate. Reached candidate exclusions are explicitly OPEN in the current specification. A policy change needs its separate concrete decision; this inventory grants none.

The current rule keeps credit, D-F/D-S, D-L and D-M before D-G, then the bounded warning. No rule/source/spec/gold was modified. Commands, full tree captures, bounded source captures and all exit/timing/hash receipts are retained privately beside this report. Raw source bodies are not duplicated into this Markdown.
