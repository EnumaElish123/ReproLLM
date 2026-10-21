# Spec issue draft: bounded decoded declaration-structure conclusions (R07-C D-M-S)

Suggested label: `spec`. Local draft only; no external issue or message sent.

Current specification §12.3.6 explicitly leaves decoded declaration shapes OPEN.
Successful document decoding can still leave supported dependency containers or
entries unextracted. Existing positive declarations may survive beside those gaps.
The current missing-pin warning is a bounded observation, not proof that no exact
declaration exists in that damaged source.

Proposal: accept option A and the adjacent `spec-proposed.patch`. Extend only the
internal declaration issue vocabulary with `invalid_structure`, using the closed
type table in `R07-C_declaration_structure.md`. Preserve partial positive capture,
presence, diagnostics, boundaries and existing priority; reuse D-M only for remaining
currently used packages without credit. Keep explicit top-level YAML None legacy
compatibility and exclude package-value grammar, requirements graphs and unknown
installer mappings. This can conservatively suppress missing-pin gate failures
across a repository; it does not grant credit or certify complete analysis.

Acceptance is specific to the displayed specification and its compatibility costs.
Future implementation requires tests first, focused regression, one final quality
gate, all-five fresh Gate A and affected init/L1/export checks. No schema, engine,
redaction, dependencies, gold, paid calls or publication is included.

Alternatives: retain current bounded warnings, or separately propose broader grammar
coverage with independent evidence. Do not treat this draft as approval.
