# Writing `reprollm.yaml`

`reprollm.yaml` records one experiment you intend to run. Start with
`reprollm init`, then replace every TODO and run `reprollm audit .`. Values
found by static scanning are candidates: confirm that each one has the role it
plays in this experiment, especially in repositories that support many models
or workflows.

## Map the experiment before filling fields

- `models.primary` is the model being trained or evaluated. Add roles such as
  `judge`, `target`, or `classifier` only when this experiment uses them.
- `datasets.eval` or `datasets.train` names the data role. For Hugging Face
  data, record `id`, `subset`, and `split`. For local data, record repository-
  relative `files`.
- `prompts.<role>` points to the actual prompt source. A task YAML or JSONL
  prompt catalog is valid when that is what the runner reads; it does not need
  to be a standalone text file.
- `generation` describes the primary model's decoding. Judge decoding belongs
  under `evaluation.judge.params`.

## Fields that need judgment

`datasets.<role>.preprocessing` should say what happens between the source data
and the model input. Use `script` when a repository file implements the
transformation; use `description` for behavior that is configured or inline.
When only part of a dataset runs, declare `sampling.n`, `sampling.method`, and
the actual sampling seed.

Each evaluation metric needs a stable implementation reference. Set
`evaluation.metrics[].implementation` to an existing repository-relative file
or an exact package reference such as `evaluate==0.4.3`. Record aggregation and
repetition counts separately.

`execution.command` is the exact command for this experiment, with
`execution.cwd` when it runs below the repository root. Declare seeds only when
the runner or code really consumes them. If a provider or tool exposes no seed,
leave it absent: the resulting finding describes a real reproducibility limit.
Use `bindings` to connect important manifest values to their CLI flags, config
keys, or environment variable names.

Never put credentials in the manifest. `execution.env_requirements` contains
names such as `OPENAI_API_KEY`, without values.

## Repository-wide detections

Profile and `trust_remote_code=True` detection scans the repository, while a
manifest describes one experiment. A multi-purpose framework may therefore
show INFO findings for capabilities used by other workflows. Add a detected
profile only when the selected experiment uses it.

When `model.trust_remote_code_declared` appears, inspect the exact execution
path. Set `models.<role>.trust_remote_code` explicitly to `true` or `false` to
match that path. Do not copy a setting onto an unrelated model merely to clear
a warning.

## Two representative mappings

For lm-evaluation-harness, a task YAML can supply the dataset, prompt template,
generation defaults, filters, metric, and aggregation. The manifest should
still spell those values out and bind them to `--model_args`, `--gen_kwargs`,
`--limit`, and `--seed` so later runtime capture can compare intent with what
executed.

For FastChat MT-Bench, `models.primary` is the answer model and `models.judge`
is the grading model. The MT-Bench question file is the evaluation dataset,
`data/judge_prompts.jsonl` is `prompts.judge`, primary answer settings belong in
`generation`, and the fixed OpenAI grading settings in `common.py` belong in
`evaluation.judge.params`.
