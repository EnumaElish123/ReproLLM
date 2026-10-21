# Independent design review: R07-C D-M-S

Review date: 2026-10-22. Source baseline: `88a26ee270c92c939140fe347b71f2909f8c7d97`.
This is an author-session peer review of the proposed bounded contract. It is not
maintainer acceptance, external adoption, an applied implementation review, or a
passing product-validation receipt. No product, normative specification or test
files were changed by this review.

## Scope reviewed

Extend the existing internal `DeclarationReadIssue` with `invalid_structure` for
the explicitly listed decoded declaration shapes. Reuse the D-M failure map and
rule branch, preserving its external message, evidence, ordering and precedence.
Do not broaden supported package grammar, include traversal, file discovery or
manager-format validation.

The proposed checks use the raw decoded value before existing falsey fallbacks.
Missing fields do not create an issue. Correctly typed empty containers do not
create an issue. These statements concern this narrow detector only; neither is
a complete-format or dependency-coverage certificate.

| Captured source / field | Proposed structural issue | Outside this check |
| --- | --- | --- |
| `pyproject.toml`: present `project`, `tool`, or `tool.poetry` under a mapping `tool` | Value is not a mapping, including falsey wrong types | Contents of unrelated tool tables; absent supported tables |
| Mapping `project`: present `dependencies` | Not a list, or a list has a non-string member | Requirement-string syntax, markers, package names and version semantics |
| Mapping `project`: present `optional-dependencies` | Not a mapping; any group value is not a list; any group list has a non-string member | Extra-name grammar and requirement-string syntax |
| Mapping `tool.poetry`: present `dependencies` | Not a mapping | All individual package values, including multiple-constraint arrays and transport/source dictionaries |
| `Pipfile`: present `packages` or `dev-packages` | Not a mapping | All individual package values and unsupported custom categories |
| `environment.yml` / `.yaml`: decoded root | Non-mapping other than `None` | Decoded `None` retains the existing empty-document/null behavior |
| Mapping environment: present `dependencies` | Not a list; a list member is neither string nor mapping | MatchSpec syntax; unknown installer mappings and selectors |
| Mapping member of environment `dependencies`: present `pip` | Not a list; a list has a non-string member | Pip requirement-string syntax and other mapping keys |

Partial extraction must keep every declaration and exact pin already produced by
the old parser. Recording an issue does not abort valid sibling extraction or
create an additional package-in-use fact. Existing manager qualification, lock
associations, uncertain barriers, diagnostics and presence results stay intact.

## Independent official facts

The [PyPA pyproject specification](https://packaging.python.org/en/latest/specifications/pyproject-toml/#dependencies)
defines project dependencies as strings in an array and optional dependencies as
a table of arrays of strings. Its tool namespace also permits configuration
unrelated to runtime dependencies. This supports the listed container/member
checks, but does not prescribe ReproLLM's audit result or require a tool-only file
to become a dependency manifest.

[Poetry's dependency specification](https://python-poetry.org/docs/dependency-specification/#multiple-constraints-dependencies)
documents arrays of constraint tables for one dependency. It also documents
source-only enrichment and direct-origin dictionaries without a version field.
Consequently, this proposal leaves every individual Poetry package value out of
the new detector. Lack of a version field is not evidence of invalid structure.

[Pipenv's Pipfile documentation](https://pipenv.pypa.io/en/latest/pipfile.html#packages-section)
documents dependency tables and Git, path and file dictionaries without a
version field. Individual package-value validation is excluded here as well.

[Conda CEP 24](https://conda.org/learn/ceps/cep-0024/#dependencies)
defines dependency lists containing strings or subsection dictionaries; `pip`
contains strings in a list. It permits additional installer subsections and
dictionary selectors. Unknown mappings therefore cannot all be classified as
invalid. CEP 24 requires the dependency field for a full environment document;
preserving missing fields and decoded top-level `None` is this proposal's bounded
compatibility choice, not a claim that those documents satisfy CEP 24.

These sources were read on 2026-10-22. The conda user-guide page returned HTTP 429;
the approved CEP supplied the structural evidence instead. No package manager,
solver, provider, model or paid API was executed to establish these facts.

## Policy choices and compatibility costs

1. A present non-mapping `tool` is included even when no qualified dependency
   manifest can be established. Such a damaged ancestor could hide the supported
   Poetry table. This is an explicit conservative policy choice; it may suppress
   missing-pin warnings for unrelated packages elsewhere in the repository.
   Valid tool-only documents, including unrelated tool values, are unchanged.
2. Top-level YAML `None` remains unchanged, while an explicitly present
   `dependencies: null` or `pip: null` is an issue. Other falsey wrong types such
   as `false`, `0`, an empty string or the wrong empty container are also issues
   at checked positions. The distinction follows raw presence and type, not
   truthiness or a claim of complete YAML-format validity.
3. Exact declarations and qualified lock credit still win. D-F/D-S then D-L keep
   their existing findings. Only otherwise missing-pin outcomes reach D-M.
   A structural issue can replace every remaining used-package warning with
   SKIPPED/INFO under the existing repository-wide existential exact policy.
   It grants no pin, does not infer new use and does not prove completeness.
4. The reused message's word `parsed` must explicitly include this bounded
   structural extraction in the proposed normative text. Otherwise a readable,
   successfully decoded document would appear inconsistent with the message.
5. An isolated warning or promoted critical result can stop producing exit 1.
   Independent rule failures still fail normally. Default text may show PASS
   with a skip count and default export hides skips; complete JSON remains the
   audit trail. These inherited D-M costs need prominent acceptance examples.
6. Passing this shape detector says nothing about unsupported grammar, optional
   manager groups, requirements directives/include gaps, unknown package use,
   listing completeness or the broader R07-C task.

## Required draft and acceptance checks

- Test absent fields and all correct empty containers separately from falsey
  wrong types; distinguish top-level YAML `None` from nested explicit null.
- Preserve valid strings and existing exact pins in mixed lists. Verify a second
  uncredited imported package is skipped while the exact/qualified package keeps
  its old credit. A case with no captured critical use must not invent one.
- Keep Poetry constraint arrays, versionless transport/source dictionaries,
  Pipfile transport values, Conda unknown installer mappings and selector mappings
  as negative controls for the new detector.
- Cover unrelated-subproject influence, deterministic failure-path ordering,
  coexistence with D-M body failures and D-F/D-S/D-L precedence. Keep current
  suppression and severity-override behavior distinct from default severity.
- Compare old and conditional declaration inventories, exact versions,
  manifest-presence values, qualified lock sets, project roots, uncertain
  barriers and diagnostics. A conditional result is not P-B acceptance.
- Verify the concrete patch uses the existing decoded object without an extra
  read, a recursion-based general validator or a new discovery pass. Existing
  schema/engine/scanner/redaction/requirements behavior must remain unchanged.
- Review independent five-project source expectations and full findings before
  any prospective gold amendment. Do not treat matching summary counts as proof.

## Review state

The bounded design is coherent enough to prepare a concrete P-A packet, subject
to the limitations above. The actual specification/implementation/test drafts,
their boundary matrices and replay evidence still require separate review.
Maintainer acceptance, P-B RED/GREEN, final product quality and fresh Gate A are
not established by this design review.
