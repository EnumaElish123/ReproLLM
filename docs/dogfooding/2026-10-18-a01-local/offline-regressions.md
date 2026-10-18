# A01 local offline regressions — 2026-10-18

This independent branch reran existing HF/lock mocks and synthetic privacy
regressions in the current project environment. It changed no product code or
tests. The exact source commit, command receipts, elapsed times, test counts and
raw-log/JUnit SHA-256 values are in
[offline-regressions.json](offline-regressions.json).

| Scope | Exit | Tests | Elapsed |
|---|---:|---:|---:|
| HF metadata and local/combined lock resolution | 0 | 18 passed | 3.185752 s |
| HF client metadata/file/authorization/error/retry boundaries | 0 | 9 passed | 1.531830 s |
| Core redaction, R02-R persisted surfaces and privacy fidelity | 0 | 245 passed | 5.918232 s |

All selections had zero failures, errors or skips. Their total is **272 passed**;
this is focused regression evidence, not a full session quality or coverage run.

```console
<venv-python> -X utf8 -m pytest -q tests/unit/lock/test_hf_resolver.py tests/unit/lock/test_local_resolver.py tests/unit/lock/test_resolver.py --basetemp <private-review>/p1 --junit-xml <private-review>/hf-metadata-lock-mocks.xml --tb=short
<venv-python> -X utf8 -m pytest -q tests/unit/lock/test_hf_client.py --basetemp <private-review>/p3 --junit-xml <private-review>/hf-client-boundaries.xml --tb=short
<venv-python> -X utf8 -m pytest -q tests/unit/core/test_redaction.py tests/unit/run/test_persisted_privacy.py tests/unit/run/test_privacy_fidelity.py --basetemp <private-review>/p2 --junit-xml <private-review>/r02r-synthetic-privacy.xml --tb=short
```

The process used UTF-8 and the installed Git utilities before inherited PATH
entries. Standard provider/proxy environment variable names were removed from
the child environment. Pytest's session-wide respx guard rejects unmocked HTTPX
requests. The HF results come from fixtures; the runtime children use synthetic
data and the standard library. Client tests check small-file bounds, synthetic
authorization handling, 403 token privacy and bounded retries. The added client
group is a separate execution; the original 18 resolver results were retained.
No model, dataset, credential, provider or GPU
resource gate was executed. Original stdout, stderr and JUnit remain in the
private review scratch directory; only logical locations, byte counts and hashes
are shared.

[Specification §16](../../plan/01_specification.md#16-secret-redaction-policy-d-19-d-20--normative)
requires secret-name presence metadata, value/context redaction, forbidden-file
handling and benign negative cases. These selections exercise synthetic secret
canaries across owned artifacts while preserving safe parameters, source bytes,
relative paths and tokens. They also cover safe failure handling and the child
exit-code contract. They do not claim to detect every unknown secret format or
retroactively clean historical artifacts.

[val.md §8](../../../val.md#8-mandatory-validation-gates) requires actual bounded
executions for formal resource acceptance. Mock revisions/hashes and synthetic
children therefore do not establish real HF resolution, successful authorized
gated-file access, model inference/training or paid judge/discover success.
Formal Gate B remains **BLOCKED**. Product Gate A is **NOT_APPLICABLE** to this
documentation-only review branch under the
[validation workflow](../../plan/validation-workflow-2026-10-13.md#3-执行频率唯一权威定义);
the main session records its own applicable final checks.
