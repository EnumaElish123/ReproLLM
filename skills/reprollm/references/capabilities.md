# ReproLLM capabilities

ReproLLM records LLM experiment identity and explains reproducibility gaps and
semantic drift. Its principle is **LLM discovers. Rules decide. Runtime verifies.**

| User need | Product capability | Typical request |
|---|---|---|
| Find missing experiment facts | Deterministic audit; environment diagnostics; profiles and detected tasks | “Check this repository and tell me what to declare next.” |
| Describe the intended experiment | Manifest initialization, task selection and saved command registration | “Set up this evaluation and save this command.” |
| Fix artifact identity | Model, tokenizer, prompt and dataset identity resolution; lock freshness | “Resolve the versions this manifest refers to.” |
| Record actual execution | Saved/explicit command, input snapshots, bindings, environment evidence and child result | “Run this command in my environment and record it.” |
| Understand differences | Explicit record or recent-success comparison with scoped evidence | “Compare my last two successful experiments.” |
| Share evidence | Current/historical reports and JSON Schemas | “Export the report for this recorded run.” |
| Find project-specific variables | Opt-in endpoint discovery, candidate inspection and separately accepted rules | “Preview what would be sent to discover project parameters.” |
| Maintain project rules | Manual rules, candidate acceptance/ignore, removal and archive restoration | “Remove this rule and retain its recovery archive.” |

The static `about` response lists each action with its current `available` flag.
Only an implemented adapter action is available. A verified installation's READY
state establishes the tool's identity and probes; it does not make every Skill
workflow available or prove credentials, model access or an experiment environment.

The toolkit does not install model/training stacks, infer missing scientific facts,
measure model quality or check paper prose. Tool Python/package evidence is recorder
evidence; child environment and input consumption remain explicitly scoped.

On first use, introduce the relevant capabilities and one or two examples. Later
requests should go directly to the requested task. Natural language is translated
by the Agent into typed actions; the audit engine remains deterministic.
