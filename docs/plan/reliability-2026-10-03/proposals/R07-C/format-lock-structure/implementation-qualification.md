# R07-C D-S implementation draft qualification

This is an unapplied single-file source draft against 603883fd8b7c7be2eac42d335a182ff654f93918. It adds only a third internal fixed LockReadIssue reason and bounded structure recording in core/deps.py. It does not change env.py, shared format-lock association, schema, engine, scanner, requirements, versions, budgets, or source dependencies.

The existing D-F rule already tests any recorded issue, after exact and qualified-lock credit. The proposal therefore reuses its message, evidence paths, status/severity, suppression and ordering. The intended specification must explicitly extend that same branch to invalid_structure and explain that "parsed" includes bounded package-membership extraction. None remains a non-certificate, not proof of full manager-format grammar validity.

## Exact bounded structures

- uv.lock and poetry.lock: missing package or an empty list is accepted. Every present package value must be a list; each entry must be a mapping with a nonempty str name. Empty names fail, whitespace-only names remain legacy opaque strings. Versions, spelling and other entry contents are unvalidated.
- Pipfile.lock: decoded root must be a mapping. Missing default/develop and empty mappings are accepted; each present default/develop must be a mapping, including explicit null and falsey wrong-type rejection. String package keys and their opaque values retain existing extraction without new checks.
- conda-lock.yml: decoder None remains the legacy accepted empty case (empty document and explicit YAML null). Other roots must be mappings. A present package must be a list, including explicit null rejection; entries follow the same narrow name/container checks as the TOML list.
- Existing unreadable and caught decoder exceptions return first with their original codes. No second reads occur.

## Extraction and diagnostic preservation

Existing valid names are appended exactly as before, including partial lists. New structural uncertainty does not remove existing package credit. Existing falsey-container coalescing is retained for extraction and existing diagnostic behavior, while the original pre-coalescing value supplies the new typed issue. Thus newly detected falsey bad containers do not add unparsed diagnostics; old truthy wrong-container and invalid-name diagnostics retain their exact literals. No raw values or exception text enter a new artifact.

These preservation statements are static design/review claims, not runtime acceptance. The conditional observer and eventual approved P-B tests must independently verify package sets, unparsed arrays, full findings, diagnostics, and exit behavior.

## Static checks

The draft parses; Mypy with the current repository configuration passes for one source file; Ruff format passes; git apply --check passes without applying. Ruff initially classified unchanged imports from the external filename incorrectly; the same draft passed when checked through its actual logical src/reprollm/core/deps.py filename with the repository configuration. No ignore, import reorder, or source mutation was used. The first diagnostic is retained as an explicitly identified transcription, not claimed raw bytes.

AST comparison confirms every other top-level function/class is unchanged; in Declarations only the unverified_lock_paths explanatory docstring changes. All method code ASTs, including qualified credit and associations, are identical. Existing unparsed diagnostic literals/counts are unchanged. The tracked deps.py bytes still equal the base. No product call, test, network, or formal gate ran for this qualification.

## Required decision and remaining boundaries

Current specification 12.3.4 and the seven unsupported-shape tests explicitly leave this behavior out of D-F. This draft must not be applied before concrete D-S acceptance and corresponding normative/test changes. It is not permission for generalized schema validation, package spelling/version checks, filesystem enumeration, manifest/requirements grammar, omitted imports, README/config/framework coverage, or full R07-C closure.
