# [spec] R07-C D-M: known dependency declaration body failures

Labels: spec
Status: local draft; no external issue has been posted.

At aee6488078c3435dcc33b20a68cca8bda0d0ec57, §12.2 retains repository-wide existential exact credit, while §§12.3.1 and 12.3.4–12.3.5 explicitly retain missing-pin warnings outside the accepted format-lock continuations. A captured unreadable/decode-failed declaration source can conceal an exact declaration anywhere; the current bounded warning is therefore not a proof of global absence.

Review the [concrete proposal](R07-C_declaration_body_failures.md), [normative patch](spec-proposed.patch), [implementation patch](implementation-proposed.patch), [test patch](tests-proposed.patch), source portfolio and full conditional reports before deciding. The proposed new SKIP contract has conservative repository-wide influence, preserves actual credit/reads/diagnostics and adds no persisted field. Requirements participates only when the old graph actually calls the safe body reader and receives None.

Decision requested: accept this bounded D-M contract and exact patches, narrow to manager bodies only, or retain the existing contract. Acceptance must be recorded separately from the immutable PROPOSED snapshot. No release, historical rewrite or gold change is included.
