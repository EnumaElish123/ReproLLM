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
