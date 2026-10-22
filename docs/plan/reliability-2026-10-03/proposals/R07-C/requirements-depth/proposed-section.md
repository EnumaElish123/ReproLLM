### 12.3.8 Requirements include targets unexpanded at the depth budget (R07-C D-G)

For `env.llm_critical_deps_pinned` only, retain a separate internal fact for a
supported requirements include whose target remains outside the captured graph
because of the existing depth budget. Add
`Declarations.unexpanded_requirement_targets: tuple[str, ...] = ()` after the
existing fields. Its default is empty for legacy/manual values; it is not a
persisted document field and does not extend `DeclarationReadIssue`.

Compute this fact only after all discovered requirements roots have completed
their existing expansion. A target qualifies exactly when an existing readable
captured node contains a `_RequirementInclude` event with a non-None normalized
logical target, and that target has no entry in the final captured node map.
Deduplicate and sort the resulting target paths lexicographically. Under the
existing traversal, active-stack cycles revisit an already captured node;
ordinary supported targets within the budget create a node even when candidate
exclusion or a body-read failure makes it unreadable. A supported edge with no
final target node is therefore the unexpanded depth frontier. Preserve the
current depth limit of 10, with each discovered root at depth 0. Do not use
`closure.complete=False`, `is_exact=False`, or diagnostic text as a substitute
for this typed final-graph predicate.

The final-graph requirement matters: a deep target may be captured later through
another shallower root. If it has a final node, omit it from this new tuple even
if an earlier root retains a depth-limit diagnostic or incomplete closure. A
captured target's own unexpanded child edges can independently contribute their
final missing target paths. Repeated/shared edges contribute one target path;
this is not a claim that every originating edge is reported.

This fact says that the normalized logical target was not expanded. It does
not assert that the target exists, is readable, has passed candidate or physical
path checks, contains any package, or contains an exact declaration. A target
that would be excluded by candidate filtering, absent, or rejected by the
physical read boundary can still qualify if the depth budget prevented those
checks from being reached. Do not perform a new probe to classify it. In
contrast, a target actually reached within the budget has a node and does not
qualify here; actual attempted body-read failures retain §12.3.6, and candidate
exclusions remain outside this new fact. Malformed/unsupported include events
with no normalized target, including rejected absolute/escaping/remote syntax,
do not qualify. No outside-root content is read.

Do not add candidates, roots, include edges, file reads, retries, target
existence checks, scanner calls, package-manager execution, or a higher budget.
Preserve every declaration and its order, source, line, specifier and exact
version; preserve lock inventories and qualification, complete-closure results,
project roots/barriers, manifest/lock presence and all existing diagnostics.
The tuple does not create package use or credit, and it does not change the
requirements-as-lock contract in §12.2. Do not mark an unexpanded target as
unreadable, invalid syntax or invalid structure.

Keep the current canonical in-use set and iteration. Exact-declaration or
qualified-lock credit wins first, followed by D-F/D-S, then D-L, then D-M
(including §12.3.7). Only after those branches, for each remaining package that
would receive the used-but-unpinned FAIL/WARNING, a nonempty
`unexpanded_requirement_targets` produces one SKIPPED/INFO finding. This branch
is independent of primary-Python coverage. Do not add a per-package PASS or
aggregate finding, alter applicability, or alter the existing empty-result
primary-Python veto. Existing higher-priority messages/evidence remain exact
and do not append the lower-priority target paths.

The conservative influence is repository-wide under §12.2's existential exact
policy: an unexpanded target could contain an exact declaration for any currently
used, uncredited critical package. It need not do so, and an unrelated project
can cause SKIP. Do not impose format-lock ownership on this uncertainty or infer
package names from target names. SKIP grants no exact/lock credit and certifies
neither complete dependency capture nor experiment reproducibility.

Keep rule ID, aliases, category, level and display-name mapping. Use this exact
message:

```text
{display} is used; a supported requirements include was not expanded within the depth budget, so missing pin evidence is not established
```

Use this exact fix hint:

```text
Review {display} declarations and unexpanded requirements include targets; restructure the supported include graph within the depth budget before deciding that exact pin evidence is absent.
```

Evidence first retains the existing first captured declaration for the package,
or otherwise its first captured import. Append one `kind: file` item for each
distinct logical target path in lexical order, with `path` equal to that target
and the exact note `{display} include target unexpanded at the depth limit`.
All other optional evidence and finding origin/suppression fields keep their
defaults. A file-kind target item identifies a known reference, not a verified
existing/read file. Keep the existing final engine sort.

FAIL-only severity overrides do not promote this SKIPPED/INFO. Current
suppression, thresholds and determinism remain unchanged; an isolated WARNING
or promoted CRITICAL gate can change from exit 1 to 0, while an independent
qualifying finding can still fail the command. Default text can show PASS with
a skipped count; default export hides SKIP; complete JSON retains the finding.
Do not change renderers, engine, scanner, redaction, schemas, dependencies,
package version, five-project gold or historical artifacts.

This is only the specified final depth frontier. Requirements string/line,
directive, continuation, comment, URL/VCS/editable, constraints and include
syntax support do not expand. Cycles and complete-but-nonexact closures do not
trigger it. Reached candidate exclusions, omitted roots/candidates/use, other
graph uncertainty, manager package-value grammar, listing, README/config/
framework completeness and sufficient certificates remain OPEN R07-C work.
The whole R07-C task is not closed by this slice.
