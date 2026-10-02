# CLI reference

Generated from `--help`; regenerate with `scripts/gen_cli_doc.py`.

## reprollm
```text

 Usage: reprollm [OPTIONS] COMMAND [ARGS]...

 Make LLM experiments reproducible.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --version                       Print the reprollm version and exit.         │
│ --no-color                      Disable colored output.                      │
│ --verbose             -v        Enable verbose output.                       │
│ --quiet               -q        Suppress non-essential output.               │
│ --install-completion            Install completion for the current shell.    │
│ --show-completion               Show completion for the current shell, to    │
│                                 copy it or customize the installation.       │
│ --help                          Show this message and exit.                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Commands ───────────────────────────────────────────────────────────────────╮
│ audit     Audit a repository and print findings (exit 1 at/above --fail-on). │
│ doctor    Diagnose the local environment for ReproLLM.                       │
│ diff      Explain semantic differences between two captured experiments.     │
│ init      Create reprollm.yaml and .reprollm/ from detected experiment       │
│           signals.                                                           │
│ export    Write REPRODUCIBILITY.md from manifest + lock + the selected run.  │
│ discover  Propose project-rule candidates from repository content (JSON      │
│           only).                                                             │
│ lock      Resolve declared experiment state into reprollm.lock.              │
│ run       Execute a command and record its runtime state.                    │
│ schema    Export JSON Schemas.                                               │
│ profiles  Inspect experiment profiles.                                       │
│ rules     Manage project-specific rules.                                     │
│ runs      Inspect recorded runs.                                             │
╰──────────────────────────────────────────────────────────────────────────────╯
```
## reprollm audit
```text

 Usage: reprollm audit [OPTIONS] [path]

 Audit a repository and print findings (exit 1 at/above --fail-on).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   path      <path>  Repository to audit (default: .) [default: .]            │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format                              <text|json|github>  Output format.     │
│                                                           [default: text]    │
│ --output                              <path>              Write the report   │
│                                                           to a file.         │
│ --fail-on                             <critical|warning|  Exit 1 when        │
│                                       never>              findings reach     │
│                                                           this severity.     │
│ --level                               <auto|0|1|2>        Force a lower      │
│                                                           audit level.       │
│                                                           [default: auto]    │
│ --profiles                            <str>               Comma-separated    │
│                                                           profile names      │
│                                                           overriding the     │
│                                                           manifest.          │
│ --show-passed     --no-show-passed                                           │
│ --show-skipped                                                               │
│ --no-color                                                Plain ASCII        │
│                                                           output.            │
│ --help                                                    Show this message  │
│                                                           and exit.          │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm init
```text

 Usage: reprollm init [OPTIONS] [path]

 Create reprollm.yaml and .reprollm/ from detected experiment signals.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   path      <path>  Directory to initialize (default: .) [default: .]        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --force                     Overwrite an existing manifest.                  │
│ --interactive               Prompt for required fields.                      │
│ --profiles           <str>  Comma-separated profile names (default:          │
│                             detected).                                       │
│ --task               <str>  Select an exact task candidate; repeatable.      │
│ --list-tasks                List all safe task candidates without writing    │
│                             files.                                           │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm lock
```text

 Usage: reprollm lock [OPTIONS] [path]

 Resolve declared experiment state into reprollm.lock.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   path      <path>  Repository to lock (default: .) [default: .]             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --offline                   Resolve without making network requests.         │
│ --check                     Check whether the current lock is fresh.         │
│ --verify-api                Verify API model existence when credentials      │
│                             exist.                                           │
│ --hash-large-files          Hash local model weights over 100 MiB.           │
│ --help                      Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm run
```text

 Usage: reprollm run [OPTIONS] [command]...

 Execute a command and record its runtime state.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   command      <str>  Command and arguments after --.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --name                  <str>            Optional run label.                 │
│ --capture-output                         Tee redacted stdout/stderr logs.    │
│ --env-capture           <allowlist|all>  Environment capture policy.         │
│ --no-snapshot                            Hash input files without copying    │
│                                          their contents.                     │
│ --cwd                   <path>           Working directory for the child     │
│                                          command.                            │
│ --help                                   Show this message and exit.         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm runs list
```text

 Usage: reprollm runs list [OPTIONS]

 List recorded runs under .reprollm/runs, newest first.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Emit run summaries as JSON.                                  │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm runs show
```text

 Usage: reprollm runs show [OPTIONS] {run_id}

 Show one run record: command, code, environment, bindings, warnings.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    run_id      <str>  Run ID or unique prefix. [required]                  │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Print run.json exactly as saved.                             │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm diff
```text

 Usage: reprollm diff [OPTIONS] {a} {b}

 Explain semantic differences between two captured experiments.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    a      <str>  Run ID/prefix, run.json, run directory, or lock file.     │
│                    [required]                                                │
│ *    b      <str>  Second run or lock input. [required]                      │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --format              <text|json>                 [default: text]            │
│ --min-severity        <LOW|MEDIUM|MEDIUM_HIGH|HI  Filter displayed changes;  │
│                       GH>                         preserve the full summary. │
│ --fail-on             <HIGH|MEDIUM_HIGH|MEDIUM|L  Exit 1 for drift at or     │
│                       OW|NONE>                    above this level.          │
│ --no-color                                        Disable colored output.    │
│ --help                                            Show this message and      │
│                                                   exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm export
```text

 Usage: reprollm export [OPTIONS] [path]

 Write REPRODUCIBILITY.md from manifest + lock + the selected run.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   path      <path>  Repository to export (default: .) [default: .]           │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --run             <str>   Run ID or unique prefix (default: latest).         │
│ --output          <path>  Output file (default: REPRODUCIBILITY.md).         │
│                           [default: REPRODUCIBILITY.md]                      │
│ --template        <str>   Checklist mapping: default | neurips | acl | acm.  │
│                           [default: default]                                 │
│ --help                    Show this message and exit.                        │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm discover
```text

 Usage: reprollm discover [OPTIONS] [path]

 Propose project-rule candidates from repository content (JSON only).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│   path      <path>  Repository to analyze (default: .) [default: .]          │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --experimental               Acknowledge the experiment.                     │
│ --yes                        Send without confirmation.                      │
│ --dry-run                    Print the payload report; send nothing.         │
│ --paper               <str>  Reserved for post-Beta.                         │
│ --show-content               With --dry-run, show the complete request       │
│                              messages.                                       │
│ --max-chars           <int>  Payload budget override.                        │
│ --help                       Show this message and exit.                     │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm doctor
```text

 Usage: reprollm doctor [OPTIONS]

 Diagnose the local environment for ReproLLM.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json                   Emit JSON.                                          │
│ --check-network          Probe the Hugging Face Hub (network).               │
│ --no-color                                                                   │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm profiles list
```text

 Usage: reprollm profiles list [OPTIONS]

 List available profiles (built-ins plus user overrides).

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Emit JSON.                                                   │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm profiles show
```text

 Usage: reprollm profiles show [OPTIONS] {name}

 Show a profile's inheritance chain, rules, and required fields.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    name      <str>  Profile name. [required]                               │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm rules list
```text

 Usage: reprollm rules list [OPTIONS]

 List accepted project rules and the latest discovery candidates.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --json          Emit JSON.                                                   │
│ --help          Show this message and exit.                                  │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm rules add
```text

 Usage: reprollm rules add [OPTIONS]

 Append a manual project rule to .reprollm/project-rules.yaml.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ *  --field           <str>  Manifest field path, e.g. custom.alpha.          │
│                             [required]                                       │
│ *  --severity        <str>  CRITICAL | WARNING | INFO. [required]            │
│ *  --reason          <str>  Why this field matters (required). [required]    │
│    --id              <str>  Rule id; default project.<last segment>.         │
│    --cli             <str>  CLI flag binding.                                │
│    --config          <str>  Config binding 'path:dotted.key'.                │
│    --env             <str>  Environment variable binding.                    │
│    --help                   Show this message and exit.                      │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm rules accept
```text

 Usage: reprollm rules accept [OPTIONS] {candidate_id}

 Accept a discovered candidate as a project rule (source: discover).

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    candidate_id      <str>  Candidate id, e.g. c-3f9a1b. [required]        │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --severity        <str>  Override the suggested severity.                    │
│ --field           <str>  Override the suggested field path.                  │
│ --help                   Show this message and exit.                         │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm rules ignore
```text

 Usage: reprollm rules ignore [OPTIONS] {candidate_id}

 Record a candidate as ignored so future discoveries mark it.

╭─ Arguments ──────────────────────────────────────────────────────────────────╮
│ *    candidate_id      <str>  Candidate id to ignore. [required]             │
╰──────────────────────────────────────────────────────────────────────────────╯
╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --reason        <str>  Why this candidate is rejected.                       │
│ --help                 Show this message and exit.                           │
╰──────────────────────────────────────────────────────────────────────────────╯
```

## reprollm schema export
```text

 Usage: reprollm schema export [OPTIONS]

 Write all exported JSON Schema files listed in spec §23.

╭─ Options ────────────────────────────────────────────────────────────────────╮
│ --out         <directory>  Directory to write *.schema.json files into.      │
│                            [default: schemas]                                │
│ --help                     Show this message and exit.                       │
╰──────────────────────────────────────────────────────────────────────────────╯
```

