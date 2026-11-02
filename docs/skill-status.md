# Agent Skill: support and remaining work

Updated 2026-11-02. **SK10–SK21 are implemented; there are no remaining code tasks
in the accepted Skill v2 plan.** The delivered scope has local, installed-tool,
GPU and Codex Linux evidence. Three online integration gates still need specific
authorization, so this is not `FULL_ACCEPTED` or a published Skill release.

## What you can use

Install the Skill once, then describe the work in natural language. For a concrete
request, the Agent can prepare an isolated ReproLLM tool environment, audit,
initialize a manifest, lock inputs, run a saved or explicit command, inspect runs,
compare drift, export reports, and discover or manage project rules. An introduction
alone installs nothing. Discovery and execution retain their own authorization.

Start with the [Agent tutorial](tutorials/agent-skill.md), or the
[four-command CLI exercise](tutorials/first-experiment.md).
The [CLI coverage map](plan/skill-2026-10-30/command-coverage.md) covers 25 command
nodes, 85 parameters and 33 typed actions; this inventory is separate from real
provider or host acceptance.

## Verified delivery

The verified Skill directory is `skills/reprollm` at commit
`b526d6ed1d74456e2175bdd880ab134d866e3995` in the
[official repository](https://github.com/EnumaElish123/ReproLLM/tree/b526d6ed1d74456e2175bdd880ab134d866e3995/skills/reprollm).
Its tool installer uses the catalog's own pinned source and dependency hashes;
the Skill commit and installed tool source are different identities.
Installing the published `reprollm` package alone does not install the Skill.

| Evidence | Recorded result |
|---|---|
| Final local quality | 24 checks; 6,731 tests; 91.989757% combined coverage; redaction branch coverage 100% |
| Official delivery CI | Five jobs pass on `b526d6e`: Ubuntu Python 3.10/3.11/3.12, macOS 3.12 and Windows 3.12; Ubuntu 3.12's twelve required steps pass |
| Native/Skill comparisons | Fresh five-project base and CPU checks, public anonymous HF metadata, five GPU A/B pairs, installation channels and seven actual Codex Linux journeys pass within the recorded scope |

See the [final resource report](dogfooding/2026-10-31-skill-final/README.md),
[test correction report](dogfooding/2026-11-02-skill-final-ci-correction/README.md),
[exact-head CI receipt](dogfooding/2026-11-02-skill-final-ci-correction/evidence/delivery-ci.json)
and [CI run](https://github.com/EnumaElish123/ReproLLM/actions/runs/41386824410).
Reports retain their actual candidates and source bridges; earlier failed
attempts remain failures. CI success does not imply every host or resource path
has been exercised.

## Host and platform scope

| Use | Current evidence and boundary |
|---|---|
| Codex on Linux | Seven real host journeys, including first installation, run/export, comparison, reconnection, cancellation and uninstall readback |
| Long operations and experiment control | The validated Linux/pidfd scope; retain the same project, tool home and operation ID across reconnects |
| macOS / Windows | Native CLI and portable unit tests, including installer components, pass in CI; full Agent-host lifecycle and background experiment control are not established by CI |
| Claude Code | Adaptation and the second real-host gate are `DEFERRED_BY_MAINTAINER` |
| Other hosts | No real-host acceptance is claimed |

The catalog currently supports tool Python 3.10–3.12 with venv support. Research
Python, CUDA, model weights and training dependencies remain separately prepared.

## Remaining work

| Item | Status | What completes it |
|---|---|---|
| DeepSeek authenticated metadata | `BLOCKED_NOT_AUTHORIZED` | Confirm the credential's service and destination, then perform the current-candidate authenticated comparison |
| Live discovery | `BLOCKED_NOT_AUTHORIZED` | Accept the exact public input, endpoint/model, request cap and fresh budget; verify returned evidence, explicit candidate acceptance, audit effect and duplicate rejection |
| Formal judge A/B | `BLOCKED_NOT_AUTHORIZED` | Approve the current inputs and a fresh budget; accept A before B, then verify captures and the complete semantic pair |
| Claude Code adaptation / second host | `DEFERRED_BY_MAINTAINER` | Resume the deferred host work and independently exercise its lifecycle and permissions |
| External researcher trial | `UNOBSERVED` | Obtain genuine feedback from the planned 3–5 researchers; author or Agent runs do not count as external adoption |

The three online items are remaining **integration acceptance**, not missing
command implementations. Mock transport and the offline judge capture do not
close them. Past budgets do not carry forward automatically; this status page
does not authorize a request or disclose a credential.

The former missing metadata manifests and Llama-2 permission requirement are
superseded: five formal inputs are versioned and Project C now uses public
DistilGPT2. See the [replacement record](dogfooding/metadata-public-model-2026-10-27/README.md).
They are not additional tasks for the current Skill iteration.

PyPI/Skill-market publication and an MCP server are outside this plan. A future
release needs its own same-candidate acceptance; engineering completion does not
mean release readiness. The [plan](plan/skill-2026-10-30/README.md) and
[acceptance matrix](plan/skill-2026-10-30/acceptance.md) remain authoritative for
scope and criteria.
