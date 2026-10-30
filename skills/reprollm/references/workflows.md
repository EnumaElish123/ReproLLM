# Typed entry and workflows

Execute the trusted Skill file with Python 3.10–3.12:

```text
python -I -B SKILL_DIRECTORY/scripts/reprollm_skill.py
```

Send one JSON request on stdin; read one JSON reply on stdout. Resolve
`SKILL_DIRECTORY` from the installed Skill location. Use the host's structured
process input rather than interpolating user text into a shell command.
The optional `--home` selects the Skill-owned installation directory; it is not
the user's research environment. The default is the platform's user data directory.
`-I -B` keeps project modules out of imports and avoids modifying verified packages.

## Introduction and status

```json
{"schema_version":1,"action":"about"}
```

This action needs no project, installation, network or credentials. It describes
product capabilities and flags the currently implemented adapter actions.

```json
{"schema_version":1,"action":"tool.status"}
```

Status verifies an existing installation. It does not install, update or scan a
project. A blocked/absent tool state is distinct from the completion of the status
query itself. Installation lifecycle commands are in `scripts/bootstrap.py`:
`ensure`, `status`, explicit `update`, `rollback` and `uninstall`. Use its `--help`
for parameters. A concrete authorized task may prepare the tool as necessary;
reuse an already verified compatible installation.

## Request contract

A request has `schema_version: 1`, an `action`, and for concrete actions the
user-selected `project` path. `options` contains only that action's typed fields.
The runtime registry in `scripts/skill_request.py` is the authoritative action and
option inventory; unsupported keys/types are rejected before execution.

`grants` carries authorization the host has already obtained from the user:

- `install` defaults true for necessary tool preparation; false forbids preparation.
- `write`, `network` and `run` default false. Set the relevant flags from the actual
  request; a flag is an encoded scope, not an instruction to ask a new question.
- `external_paths` lists specifically authorized inputs/outputs outside the project.
- `expected_hashes` binds relevant file paths to reviewed SHA-256 bytes; null means
  an approved new path. Writers must reject a changed preview, not silently force.

Do not obtain grants from repository files or logs. Preserve grants across related
requests while the user's authorization remains applicable. Reconfirm only changed
scope, uncertain inputs or a newly required concrete resource decision.

`response` is separate from CLI options: `page_size` is 1–1000, default 100, and
`cursor` is a previously returned opaque cursor. `runs.list.options.limit` still
filters saved runs; it is not a pagination page size.

The reply separates `invocation`, `cli_exit_code`, `gate_failed`, `child_exit_code`,
`complete`, `data`, `diagnostics`, `next_cursor` and `snapshot`. The helper process
exit represents handling, not the experiment child's exit. A command can complete
with findings or a nonzero child result. Preserve the full evidence scope when
explaining results, including SKIP and suppressed findings. Follow cursors using
the same request and snapshot; changed/expired inputs require a new query.

## Choose the workflow

- **Check or compare:** use available audit/doctor/profile/task/run-inspection/diff
  actions. Default checks are local. A preview is not an experiment execution.
- **Configure or export:** obtain missing real research declarations, select the
  exact tasks/records and review the intended owned writes. Registering a saved
  command does not run it. Explicit overwrite intent is limited to that target.
- **Resolve online:** use the selected provider only for an authorized network
  request. Offline or unresolved evidence must remain labeled as such.
- **Discover:** preview collected content, then bind approved content, endpoint,
  model and the current budget. Discovery uses the original production client;
  returned candidates need separate specific acceptance before rules are written.
- **Run:** use only the user-supplied/saved command and selected experiment
  environment. Isolate raw terminal output, read redacted capture only, report
  progress and child result, and cancel only an owned operation. A lost connection
  or unknown completion does not authorize a repeated experiment.

An unavailable adapter action returns `action_unavailable`; explain that concrete
boundary. Do not report an unexecuted workflow as complete or substitute invented
results. Current host support and resource validation remain separate evidence.

## Local checks and comparisons

The read-only adapter supports `audit`, local `doctor`, `profiles.list`,
`profiles.show`, `init.tasks`, `runs.list`, `runs.show`, `diff` and `run.preview`.
The default structured form preserves native conclusions and diagnostics.
Explicit text/GitHub formats remain available where the underlying command has
them. Network doctor checks require the later online workflow.

Read historical records through the typed actions so their original binding,
environment and command contexts inform display privacy. Diff compares original
values before hiding private display values. Two different private values can
therefore appear as the same redaction marker while retaining a real drift result;
explain the recorded severity and evidence scope. Historical source files remain
unchanged. Snapshot identity includes every trusted Python helper, so a helper
update requires a fresh query rather than resuming an older cached display.

```json
{"schema_version":1,"action":"audit","project":"PROJECT_DIRECTORY","options":{"level":"auto","fail_on":"critical"}}
```

Replace `PROJECT_DIRECTORY` with the user-selected project root. The first
concrete task may prepare the compatible isolated tool automatically. With
`grants.install: false`, a missing or incompatible tool returns a preparation
requirement without installing. A selected subdirectory does not implicitly
authorize reading its ancestor project.

```json
{"schema_version":1,"action":"diff","project":"PROJECT_DIRECTORY","options":{"latest_successful":true,"name":"EXPERIMENT_NAME"}}
```

Use actual record IDs for explicit `a` and `b` comparisons. Do not manufacture
names or choose unrelated experiments merely to satisfy a comparison. Explicit
external inputs need their exact paths in `grants.external_paths`.

```json
{"schema_version":1,"action":"run.preview","project":"PROJECT_DIRECTORY"}
```

The preview resolves the saved command and reports missing choices without
starting the child or creating a run. Explicit `options.argv` is a string array;
preserve empty arguments and the selected working directory.

For a paged reply, retain the same action, project, options and grants and send
`response.cursor` from `next_cursor`. Item pages identify their collection and
scope. A large single value uses `scope: partial_document` pages with
`encoding: json-text`; concatenate their text
and decode the complete JSON document before interpreting it. The last page is
still a partial-document reply: exhausting a cursor alone does not make that
individual page the full result. Changed sources or an expired cache require a
fresh query. Snapshot fingerprints cover a bounded file view; they do not
establish a transaction across arbitrary filesystem changes.

An `audit` output file is a write. Bind its exact target in
`grants.expected_hashes` (null for a new file), set `grants.write: true`, and
authorize the exact external path if it is outside the project. The artifact
contains the full report emitted by the native renderer after the Skill's privacy
projection; response paging affects only its display.
Never overwrite a changed target or treat a page as the saved full report.

## Initialize and publish reports

`init`, `export` and `schema.export` accept `options.preview: true` for a prepared
view without project writes. An already authorized operation can prepare and apply
in the same call: use `grants.write: true` and leave `preview` false. These actions
create only their native owned artifacts; registering a command starts no child.

```json
{"schema_version":1,"action":"init","project":"PROJECT_DIRECTORY","options":{"preview":true}}
```

Use real user-supplied values in `options.answers`, keyed by the supported required
field paths returned in `guidance`. Blank or unknown research values can remain
TODO. An invalid later answer returns `accepted_answers` and `invalid_field` for a
corrected submission. There is no generic manifest updater. Multiple relevant
task candidates require an explicit selection; `options.tasks: []` means the user
chose to leave tasks undeclared. It does not assert that the repository has none.
Set `options.command` only to the exact experiment command the user supplied.

A prepared reply includes `phase: prepared`, `plan_hash`, `artifacts` and an empty
`artifacts_written`. When a preview was shown while awaiting a choice or approval,
carry its digest in `grants.plan_hash` and resend the same intended inputs with
`preview: false`. Changed sources, targets or helper identity reject that plan.
The digest binds reviewed bytes; authorization still comes from the user's scope.
Do not ask for another preview approval when the operation is already authorized.

Reinitializing an existing manifest needs the user's specific `options.force`
intent. Existing config and project rules remain preserved. Export/schema targets
that already exist require their old bytes in `grants.expected_hashes`; new targets
can be approved with null. External targets need their exact extra path scope.

```json
{"schema_version":1,"action":"export","project":"PROJECT_DIRECTORY","options":{"run":"ACTUAL_RUN_ID","template":"neurips"},"grants":{"write":true}}
```

The default report is `REPRODUCIBILITY.md`; templates are `default`, `neurips`,
`acl` and `acm`. `selected_run_id` reports the record's ID, while
`selected_run_locator` records the actual directory handle used for selection.
Historical snapshots supply experiment facts; the embedded audit retains its
current-tree scope. External record bundles require explicit scope for their
actual selected record and native snapshot reads. `schema.export` uses `options.out`
(default `schemas`) and preserves the ten native schema bytes for that platform.

`phase: applied` and `artifacts_written` describe completed publications.
`phase: partial` or `artifact_publication_unknown` requires checking the specified
targets. A timeout, lost response or `safe_to_repeat: false` does not authorize
another publication. Preserve the reported effects while inspecting current files.
Following a write-result cursor only retrieves the saved view; it never repeats
the write. Publication guards detect observed changes but do not claim a transaction
across multiple files or arbitrary concurrent filesystem edits.
