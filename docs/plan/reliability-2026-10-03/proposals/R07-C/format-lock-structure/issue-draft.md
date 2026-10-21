# Local spec issue draft — R07-C D-S

Title: Classify bounded associated format-lock structural extraction failures

Label: `spec`. Local draft only; no external issue has been created.

Current §12.3.4 explicitly excludes wrong decoded structures and partial extraction.
The current parsers ignore such structures while retaining `read_issue=None`.
For an existing R06-B qualified use origin, restoring that structure can provide
existing membership credit, so a remaining missing-pin WARNING is unverified.

Review the [D-S proposal](R07-C_associated_lock_structure.md),
[normative patch](spec-proposed.patch), [implementation](implementation-proposed.patch)
and [acceptance draft](tests-proposed.patch). Add only `invalid_structure` for the
explicit finite container/name-entry checks, preserve all positive extracted
membership and exact credit, and reuse D-F association/SKIP output. Retain legacy
empty/null boundaries exactly as listed. No schema, engine, renderer or gold change.

Alternative: keep current bounded WARNING. General manifest/requirements and other
grammar, listing/detection/framework gaps and broad sufficient certificates remain OPEN.
