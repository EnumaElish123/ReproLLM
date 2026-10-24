# D-M-PF independent design review

Status: PROPOSED, no policy accepted or implemented; candidate policy runs 0; manager/solver runs 0. All 45 future acceptance groups in design.json are unexecuted requirements, not passing tests. Current normative spec explicitly excludes Pipfile package-value types; the source agrees. This is a new policy decision, not an already-confirmed specification bug.

## Recommendation A, pending specific acceptance

Within the one existing _parse_pipfile caller, traversing packages then dev-packages after successful TOML decode and parent checks, use only dict + raw version key present + not isinstance(version,str). Record result.declaration_read_issues.setdefault(path, invalid_structure) then continue the original helper allow_bare=False and append. No advance pre-scan, shared-helper change or additional traversal. An entry-only issue does not add an uncertain-directory barrier; parent structural behavior remains its existing contract. Keep line-index fallbacks exactly, including duplicate names across sections and expanded-table fallback.

The present helper returns (None,None) for missing, non-str and blank version. None is not failure evidence. Nonexact/range/transport strings also legitimately lack exact credit. Do not infer failure from helper return, diagnostics, package criticality or lack of an exact pin. Version absence, all strings, whole nonmapping values, alternatives, unknown fields and custom categories are excluded. A transport plus explicit non-str version qualifies only by the field predicate, without inferring transport precedence, manager rejection or hidden exact. TOML has no null.

## Independent official evidence

Official Pipenv v2026.10.2 resolves via annotated tag object f8c4c115b07b293397110a64d5f01a7a3245c474 to commit 83627fdcc2a1fdce8a1daaec3983857382137cbd. Its vendor.txt declares Plette 2.4.0. Vendored PackageSpecfiers optional schema declares version as str; its DataModel base validates optional fields only when present. Upstream Plette v2.4.0 commit fb5bcc588f5a749076af3a8594750e4b9db2580e has the same explicit type boundary. The source models name packages and dev-packages, while official docs also describe custom categories and options/transport mappings. Exact source bytes, hashes, Git blob identities, retrieval time and commit URLs are in source-fetch-record.json and design.json.

Nuance: the very same Package.validate separately accepts direct tomlkit Float/Integer package values. A must not broaden into declaring direct nonmapping numeric values invalid. Official documentation examples distinguish == exact from range/wildcard and demonstrate version absence in transport mappings. ReproLLM's current static Pipfile contract retains allow_bare=False, irrespective of broader manager permissiveness.

Sources prove a present-field extraction/type boundary; they do not prove a recoverable exact pin, actual installer rejection, complete Pipfile invalidity, or the logical necessity of repository-wide SKIP. No Plette, Pipenv, solver, downloader or install was executed. Public documents should paraphrase sources and link exact immutable URLs; retain complete fetched third-party bodies privately.

## Alternatives and compatibility cost

A is defensible as a deliberately chosen continuation of the accepted bounded D-M structure policy. B keeps current captured-view missing-pin WARNING, does not pretend a full repository absence proof, and leaves this field-extraction gap OPEN. NOT_NEEDED is not preferred: the type boundary and current omission exist, although zero real-portfolio applicability may justify deferral. Previous Poetry acceptance supplies no authority for this Pipfile decision.

All captured declarations/order/names/specifier/exact/source/lines, partial siblings, critical-use/applicability, lock sets/association, presence, qualified roots/barriers, diagnostics, graph, read/helper/Requirement call traces, profile/hint/init behavior remain. Same-file prior cause after existing prechecks is preserved by setdefault; the proposal does not refactor existing earlier assignments. The only product change should be one file-level fact in the current loop. No new rule branch/vocabulary/persisted field.

Credit comes first, then D-F/D-S, D-L, D-M, D-G. Qualified lock or exact declaration still wins. Higher-priority full finding bodies remain unchanged; lower-priority D-G paths are never appended. Existing first declaration/import stays first; distinct failed paths append sorted. This slice may enlarge a DM finding's evidence while status is already SKIPPED. It grants and revokes no credit.

The explicitly reviewable cost is global: even an unrelated noncritical malformed entry in another project may replace every remaining current-use uncredited critical-package WARNING/promoted CRITICAL with SKIPPED/INFO. Exact field type itself does not establish hidden exact. Isolated exit1 can become0; independent warning still fails. FAIL-only overrides do not promote SKIP, suppression and thresholds remain. Default text may show Findings PASS with skipped count, default export can lose a formerly notable warning, complete JSON retains SKIP. This is neither complete analysis nor reproducibility certification.

Legacy/manual defaults and historical artifacts are not reinterpreted. D41 is not crossed: no engine, redaction or persisted schema changes; a later necessary change there requires separate explicit review. No dependencies, package version, scanner, grammar, new sources/groups, gold, resource validation, release or manager execution is proposed. P-B only follows specific acceptance of A, exact unapplied normative patch and these conservative costs; begin core/rules/CLI RED tests, then minimal implementation, final quality once and fresh all-five Gate A plus affected consumers.

## Future independent acceptance

The 45 groups in design.json cover both sections, all actual TOML non-string kinds, controls, ordering/line fallbacks, existing parent/read failures, partial credit, qualified/nonqualified locks and unchanged barriers, all uncertainty priorities, no-use applicability, repository-wide effects, complete evidence/presentation/exit semantics, legacy compatibility, existing Poetry/PEP621/environment policies, full internal record equality, privacy/determinism and five-source conditional impact. They are future test requirements only. P-A has no full product gate or Gate A PASS; documentation-only gates must be named NOT_APPLICABLE_DOCUMENTATION_ONLY.
