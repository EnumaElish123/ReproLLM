<p align="center">
  <picture>
    <source media="(max-width: 600px)" srcset="https://raw.githubusercontent.com/EnumaElish123/ReproLLM/main/docs/assets/readme-hero-compact.svg">
    <img src="https://raw.githubusercontent.com/EnumaElish123/ReproLLM/main/docs/assets/readme-hero.svg" alt="ReproLLM — audit the setup, record the run, explain what changed. A manifest, lockfile and run record provide evidence for audit, diff and export." width="1200">
  </picture>
</p>

<p align="center"><strong>Make LLM experiments reproducible.</strong></p>

<p align="center">
  <a href="https://github.com/EnumaElish123/ReproLLM/actions/workflows/ci.yml"><img src="https://github.com/EnumaElish123/ReproLLM/actions/workflows/ci.yml/badge.svg" alt="CI"></a>
  <a href="https://pypi.org/project/reprollm/"><img src="https://img.shields.io/pypi/v/reprollm" alt="PyPI version"></a>
  <a href="https://pypi.org/project/reprollm/"><img src="https://img.shields.io/pypi/pyversions/reprollm" alt="Supported Python versions"></a>
  <a href="https://github.com/EnumaElish123/ReproLLM/blob/main/LICENSE"><img src="https://img.shields.io/badge/License-Apache%202.0-blue.svg" alt="Apache-2.0 license"></a>
</p>

<p align="center">
  <a href="#quick-start">Quick start</a> ·
  <a href="https://github.com/EnumaElish123/ReproLLM/blob/main/docs/index.md">Documentation</a> ·
  <a href="https://github.com/EnumaElish123/ReproLLM/tree/main/examples">Examples</a> ·
  <a href="#use-in-ci">CI</a> ·
  <a href="#contributing-and-citation">Contribute</a>
</p>

A reproducibility linter, experiment recorder, lockfile system, and drift detector for LLM research. It records the LLM-specific state that other tools ignore — model revision, tokenizer and chat-template hashes, prompt hashes, generation parameters, LLM-as-a-Judge configuration, and the pinnability of closed-source API models — and tells you why two runs differ.

**Check what is missing. Capture what actually ran. Share the evidence.**
ReproLLM works alongside your evaluation scripts and experiment tracker, with
reviewable YAML, JSON and Markdown artifacts in your own repository.

## See what needs attention

An audit connects a finding to its source and a concrete next step:

```text
  ! env.llm_critical_deps_pinned      vllm is used but not pinned to an exact version (suggestion: vllm==<version>)
      requirements.txt (declared as >=0.10)
      fix: Pin vllm exactly, e.g. `vllm==<version>`.
```

This is an actual excerpt from `reprollm --no-color audit .` on the
[quick-start fixture](docs/quickstart.md#install-and-prepare-a-separate-copy),
before initialization; other findings are omitted. No model runs during audit.

After you record two runs, a semantic diff identifies the fields that changed.
The [executable tour](docs/quickstart.md#explain-the-drift) captures a small Python
probe twice, changing only the declared and observed token limit:

```json
{
  "path": "generation.max_tokens",
  "a": 32,
  "b": 48,
  "severity": "HIGH",
  "status": "changed"
}
```

Excerpt from the generated diff; its other fields are omitted. This is a
standard-library capture exercise, not an inference result. A `HIGH` change
means the runs need review before comparison; it does not measure model quality.

## Why use ReproLLM?

- **Before sharing an experiment:** find missing revisions, dependency pins,
  prompts and reproducibility settings while you can still recover them.
- **When results change:** compare recorded state across runs and see whether
  the model, prompt, sampling settings, judge or environment drifted.
- **When preparing a paper artifact:** export the available evidence and its
  limitations into a document reviewers can inspect.
- **When your method has custom parameters:** declare project rules and bind
  them to real CLI flags, config keys or environment variables.

### Capture the state behind your result

| LLM-specific state | What ReproLLM records or checks |
|---|---|
| **Model identity** | Model and tokenizer revisions, chat-template hashes, dtype, quantization and adapters |
| **Prompt identity** | Content hashes, so an edit remains visible even when the filename stays the same |
| **Generation and backend** | Sampling settings, inference configuration and installed backend versions |
| **LLM-as-a-Judge** | Judge model pinnability, prompt hashes, sampling parameters and repetitions |
| **API model pinnability** | Provider `snapshot_alias` labels versus `unpinnable` mutable aliases; no invented exact revisions |

These sit alongside Git state, dependency declarations, dataset configuration,
training settings and privacy assumptions. Browse the [rule catalog](docs/rules.md)
for individual checks and their fix hints.

**Fits your existing stack.** Keep MLflow, W&B or TensorBoard for metrics and
visualization, and your evaluation framework for executing tasks. ReproLLM adds
reproducibility checks, input identity, runtime evidence and semantic drift.

## Quick start

### 1. Install

Use **Python 3.10 or newer** and Git. ReproLLM does not install PyTorch,
Transformers, vLLM or model weights.

```bash
python --version
python -m venv .venv
```

Activate the environment for your shell:

```bash
# macOS / Linux
source .venv/bin/activate
```

```powershell
# Windows PowerShell
.venv\Scripts\Activate.ps1
```

```bash
python -m pip install reprollm
reprollm --version
```

### 2. Run your first audit

From your research repository:

```bash
reprollm audit .
```

No account, API key, GPU or manifest is needed for the first audit. Without a
manifest, **Level 0** checks repository state and dependencies and suggests
experiment profiles. Audit runs locally and makes no model calls.

> **Reading the result:** findings and the process exit threshold are separate.
> By default, critical findings cause exit `1`; warnings alone exit `0`, even
> when the text verdict says `FAIL`. Use `--fail-on warning` for a stricter gate,
> or `--format json` for structured findings. [Exit-code reference](docs/cli.md)

### 3. Describe the experiment you intend to run

```bash
reprollm init .
# Review reprollm.yaml and replace the TODOs with your actual experiment settings.
reprollm audit .
```

The manifest enables **Level 1** checks. Detection helps you get started; review
suggested models, tasks and profiles for the one experiment you are documenting.
The [manifest guide](docs/manifest.md) explains roles, settings and bindings.

**Want a complete practice run first?** Follow the
[copy-and-run tutorial](https://github.com/EnumaElish123/ReproLLM/blob/main/docs/quickstart.md):
audit → init → offline lock → two captures → diff → export. It uses a disposable
example and only Python's standard library, with no GPU, model download or paid API.

<details>
<summary><strong>Working from the source checkout</strong></summary>

For the latest changes on `main`, clone this repository and use the development
environment. This also includes unreleased fixes listed in the changelog.

```bash
git clone https://github.com/EnumaElish123/ReproLLM.git
cd ReproLLM
uv sync --dev
uv run reprollm --help
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for development checks.

</details>

## From a repository to a research artifact

Start small and add evidence as your experiment becomes ready to run.

| Step | Command | Evidence you gain |
|---|---|---|
| **Check** | `reprollm audit .` | Findings with source locations and fix hints |
| **Declare** | `reprollm init .` | A `reprollm.yaml` scaffold to review and complete |
| **Resolve** | `reprollm lock .` | Revisions, hashes and provenance in `reprollm.lock` |
| **Capture** | `reprollm run -- <your-command>` | A run record, selected snapshots and observed bindings |
| **Compare** | `reprollm diff RUN_A RUN_B --fail-on HIGH` | Field-level drift with severity and source conflicts |
| **Share** | `reprollm export --template neurips` | `REPRODUCIBILITY.md` with a checklist evidence mapping |

`RUN_A` and `RUN_B` are IDs printed by `run` or listed by `reprollm runs list`.
Use your existing evaluation or training command after `run --`. Declare
config files and [bindings](docs/run.md#declare-the-values-you-want-compared) so ReproLLM can compare observed
settings with your manifest; wrapping a process does not reveal every model-internal value.

**Three evidence layers:** the manifest records intent; the lock records resolved
inputs; the run records observations. A manifest plus a lock or run enables
**Level 2** consistency checks. A higher level describes the evidence available,
not a guarantee that the experiment is reproducible.

<details>
<summary><strong>What lives in your repository?</strong></summary>

```text
reprollm.yaml                       # your experiment declaration
reprollm.lock                       # resolved inputs and provenance
.reprollm/
  config.yaml                      # capture and discovery settings
  project-rules.yaml               # accepted or manually declared custom checks
  runs/<run-id>/run.json            # captured runtime record
REPRODUCIBILITY.md                  # exported research evidence
```

Review artifacts before sharing them. Run records stay local unless you choose
to share them; see the [runtime guide](docs/run.md) for capture and export policies.

</details>

### Honest about what cannot be pinned

A Hugging Face commit, a provider's dated API model label and a mutable API alias
provide different guarantees. ReproLLM preserves that distinction: a provider
label does not become an exact revision, and unavailable metadata stays unresolved.

Use `reprollm lock . --offline` on an offline machine; it hashes available inputs
and records unresolved remote values. Use `reprollm lock . --check` to check
manifest/project-rule freshness without network access. See the
[lockfile guide](docs/lockfile.md) for authentication, provenance and API models.

## Pick a starting point

| Example | Explore |
|---|---|
| [HF + vLLM evaluation](examples/hf_vllm_eval/) | Model and prompt identity, generation settings, and a completed manifest |
| [API-based LLM judge](examples/openai_judge_eval/) | Judge configuration, provider labels and unpinnable model identities |
| [Privacy and custom parameters](examples/privacy_custom_params/) | Privacy declarations and method-specific project rules |

These are research fixtures with completed manifests and historical locks.
Copy an example before modifying it. Running its model script requires its own
dependencies and resources; the [resource-free tour](docs/quickstart.md) is separate.

**Composable profiles:** `inference` · `evaluation` · `llm_judge` · `finetuning` ·
`safety` · `privacy`, plus implicit `core`. Explore inheritance, required fields
and detection in the [profile catalog](docs/profiles.md).

**Framework guides:** [lm-eval](docs/integrations/lm-eval.md) ·
[lighteval](docs/integrations/lighteval.md) · [inspect-ai](docs/integrations/inspect-ai.md).
Integrations help detect configuration and record versions; they do not run
benchmarks for you.

## Share evidence with your paper

```bash
reprollm export
reprollm export --template neurips --output REPRODUCIBILITY.neurips.md
reprollm export --template acl --output REPRODUCIBILITY.acl.md
reprollm export --template acm --output REPRODUCIBILITY.acm.md
```

Exports describe models, data, prompts, execution, audit findings and known
limitations. Conference templates add evidence mappings; they do not certify
compliance or answer checklist Yes/No questions on your behalf.

[Export guide](docs/export.md) · [Checklist coverage](docs/checklists.md) ·
[Example artifact](examples/hf_vllm_eval/REPRODUCIBILITY.neurips.md)

## Use in CI

Add an audit to `.github/workflows/reprollm.yml`:

```yaml
name: Reproducibility
on: [push, pull_request]
permissions:
  contents: read
jobs:
  audit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.12"
      - uses: EnumaElish123/reprollm-action@v1
        with:
          fail-on: critical
          check-lock: "false"
```

Level 0 works without a manifest. Enable `check-lock: "true"` once your repository
contains a completed manifest and lock. The Action provides annotations, a job
summary and an audit report. [Action usage and options](https://github.com/EnumaElish123/reprollm-action)

For another CI system, install ReproLLM and use `reprollm audit . --format json`.
GitHub workflow annotations are also available via `--format github`.
The Action is distributed separately; fixes in this repository's
[action source](action/action.yml) do not update its published `v1` tag automatically.

## Local by default, explicit about network access

**LLM discovers. Rules decide. Runtime verifies.** Audit uses deterministic rules.
The optional discovery step proposes project-specific candidates; they become
rules only after you explicitly accept them.

- **Audit, capture, diff and export** need no LLM endpoint. ReproLLM collects no
  telemetry. The command you wrap with `run` can still make its own network calls.
- **Lock** can resolve provider metadata over the network. `--offline` and
  `--check` work without network access; `--verify-api` is an explicit extra check.
- **Discover** is experimental and opt-in. It sends selected repository text to
  your configured endpoint after confirmation. Preview collection first:

```bash
reprollm discover . --experimental --dry-run
```

On **`main` (unreleased)**, add `--show-content` to preview the complete initial
request messages without credentials or a request. See the
[discovery guide](docs/discover.md) for exclusions, size limits and acceptance.

Capture uses environment allowlisting and secret-pattern redaction; forbidden
files are excluded from snapshots and discovery. The opt-in
`reprollm doctor --check-network` also makes a network probe.
[Security policy](SECURITY.md) · [Privacy and capture details](docs/run.md)

## Documentation

| You want to… | Start here |
|---|---|
| Try the whole workflow without a model | [Quick start](docs/quickstart.md) |
| Understand the evidence model | [Concepts](docs/concepts.md) · [Why ReproLLM](docs/why.md) |
| Configure an experiment | [Manifest](docs/manifest.md) · [Profiles](docs/profiles.md) · [Project rules](docs/project-rules.md) |
| Record and compare runs | [Lockfile](docs/lockfile.md) · [Runtime capture](docs/run.md) · [Semantic diff](docs/diff.md) |
| Prepare a paper artifact | [Export](docs/export.md) · [Checklist mapping](docs/checklists.md) |
| Look up a command or check | [CLI reference](docs/cli.md) · [Rule catalog](docs/rules.md) · [FAQ](docs/faq.md) |

## Project status

The audit → lock → run → diff → export workflow and experimental discovery are
available. The latest published package at this update is **0.6.1**. This README
tracks `main`; [Unreleased changes](CHANGELOG.md#unreleased) may not be in PyPI yet.

Quality checks cover Linux, macOS and Windows. Our
[five-project validation](val.md) uses pinned public research repositories;
these are maintainer validation targets, not claims of upstream adoption.
[Current repair evidence](docs/dogfooding/2026-10-02-ux-repairs.md) and
[deferred resource checks](docs/dogfooding/pending-resource-validation.md) distinguish
local checks from real-model/GPU acceptance.

Next work is tracked in the [backlog](docs/plan/backlog.md) and
[pending UX proposals](docs/plan/ux-2026-10-02-proposals/README.md).
ReproLLM records and audits reproducibility-critical state. It does not guarantee
bitwise-identical results, score model quality or fingerprint entire datasets.

## Contributing and citation

Found an unclear finding or a missing research setting? Open a
[bug report](https://github.com/EnumaElish123/ReproLLM/issues/new?template=bug_report.yml)
or propose a [new rule](https://github.com/EnumaElish123/ReproLLM/issues/new?template=new_rule.yml).
The [contributing guide](CONTRIBUTING.md) covers setup, tests and changes.
Report suspected secret leaks through [SECURITY.md](SECURITY.md).

If you use ReproLLM in your research, cite the software using
[CITATION.cff](CITATION.cff) and include your generated `REPRODUCIBILITY.md`
with the artifact. If it helps your workflow, a GitHub star helps others find it.

[Apache-2.0](LICENSE) · [Changelog](CHANGELOG.md) ·
[Documentation index](docs/index.md)
