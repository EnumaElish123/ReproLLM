# Validate a candidate wheel

The [roadmap](community/roadmap.md) is the availability source. A package installed
from PyPI and an unreleased source checkout can have different features. The
[quickstart](quickstart.md) is generated from source; candidate acceptance uses
the same command sequence against an independently installed wheel.

## Build once, then validate that artifact

Use a clean checkout of the intended candidate. Record its commit **before**
building, preserve the build log, and bind the resulting bytes to that commit
in a build manifest. For example, from that checkout:

```bash
uv sync --locked --dev
uv run python - <<'PY'
import email.parser
import hashlib
import json
from pathlib import Path
import subprocess
import zipfile

assert not subprocess.check_output(["git", "status", "--porcelain"])
commit = subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip()
subprocess.run(["uv", "build", "--out-dir", "dist"], check=True)
wheels = list(Path("dist").glob("*.whl"))
assert len(wheels) == 1, "Use an empty build output directory"
wheel = wheels[0]
with zipfile.ZipFile(wheel) as archive:
    names = [n for n in archive.namelist() if n.endswith(".dist-info/METADATA")]
    assert len(names) == 1
    metadata = email.parser.BytesParser().parsebytes(archive.read(names[0]))
assert subprocess.check_output(["git", "rev-parse", "HEAD"], text=True).strip() == commit
assert not subprocess.check_output(["git", "diff", "HEAD", "--"])
manifest = {
    "schema_version": 1,
    "source_commit": commit,
    "version": metadata["Version"],
    "artifacts": [{"filename": wheel.name,
                   "sha256": hashlib.sha256(wheel.read_bytes()).hexdigest()}],
}
Path("build-manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
PY
uv run python scripts/validate_distribution.py \
  --wheel dist/reprollm-0.7.0-py3-none-any.whl \
  --build-manifest build-manifest.json \
  --expected-version 0.7.0 \
  --output distribution-result.json
```

Here `0.7.0` is the current local development version, not a new release
announcement. Use the actual candidate filename and expected version. For a
release candidate, `--expected-tag v0.7.0` additionally checks the tag/version
relationship; it neither creates a tag nor publishes anything. Keep manifests,
logs and validation summaries outside the directory uploaded to a package index.

The validator accepts an **already built wheel** and never rebuilds it. It checks
the filename/hash/version association supplied by the build manifest. This
association is build evidence, not an independently authenticated source
attestation. Without a manifest it reports `UNCONFIRMED`; matching version strings
or the validator checkout's HEAD do not establish a wheel's source commit.

## What the gate executes

The runner creates a fresh environment and working directory outside the source
checkout, installs the wheel with its declared runtime dependencies, clears
`PYTHONPATH`/`PYTHONHOME` and disables user-site imports. It verifies package and
CLI import locations, installed metadata, the console entrypoint and the installed
wheel hash. The source checkout supplies external fixtures only.

The installed package then performs the twelve-step offline walkthrough: Level 0
audit, init and Level 1 checks, offline lock/check, two stdlib runs, Level 2 audit,
semantic diff and export. Assertions require the observed cap **32 → 48** and
the exact `generation.max_tokens` HIGH change. All built-in profiles, ten schema
exports and four export templates are exercised through installed commands.
Only `--version` or `--help` succeeding cannot pass this gate.

Installation may access normal package sources. To use prepared dependency
wheels, pass `--no-index --find-links <wheelhouse>`. Install declared dependencies;
do not copy a development environment or omit runtime dependencies. Product
commands in the walkthrough reject Python socket connections and perform no
model/provider requests. This resource-free probe does not validate native
inference; use the separate [bounded lm-eval recipe](../examples/lm_eval_replay/README.md).

The JSON summary records wheel identity, source association, import isolation,
fixture hashes, command exit codes/timings/output hashes and target assertions.
Exit 0 means these checks passed; exit 1 preserves a failed summary. Version or
manifest/hash mismatches fail before installation. Missing package data must
fail its actual consumer command. Source walkthrough success never overrides a
candidate wheel failure.

For local investigation, `--raw-output-dir <private-scratch-directory>` retains
original command streams and generated artifacts. Those files can contain local
installation paths; review and sanitize them before sharing. Portable summaries
use relative paths and logical environment labels.

This is the single distribution validation entry for D02 and the later D03
release gate. The release workflow changes belong to D03. The standalone
[ReproLLM Action](https://github.com/EnumaElish123/reprollm-action) and its published
`v1` tag require their own update; changing this repository does not update them.
