# [spec] R04-S: qualify recorder evidence and persist pre-child input baselines

Status: LOCAL_DRAFT_NOT_CREATED. Requested label: `spec`.

Current §5.1/§15/§17 lacks persisted input phase/change semantics. A real stdlib
child consumes config temperature 0.1 and rewrites it to 0.9; current run capture
records 0.9 after exit. An independent lightweight child venv exposes torch
0.0.123 metadata while recorder packages are empty; consumers lack typed scope.

Concrete proposal, complete normative/schema patches, actual old record,
explicitly proposed new example, failing public regressions and compatibility
evidence: [R04-S](R04-S_runtime_evidence.md).

Requested decision: accepted source/phase wording and scoped consistency; local
0.6.2 reader bridge then 0.7.0 run-specific schema 2; typed input_capture and
internal State context; conservative legacy unknown; bounded original-byte
config observations. Rule IDs, severities and schema of other documents remain.

This draft is reviewable locally. Current session has no verified authenticated
GitHub issue tool or gh identity, so no remote issue was created. Do not infer
API authorization from Git SSH access or reuse unrelated provider credentials.
