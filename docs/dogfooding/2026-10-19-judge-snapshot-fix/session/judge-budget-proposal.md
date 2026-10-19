# Repaired-candidate formal judge replay budget proposal

Status: proposed, not authorized. Candidate: `75d1b065e9f0e3eeafa8e480e195a2a2ddbe95b5`.

The complete local quality gate passes: 3004 tests, 94.02% coverage, 100% core redaction branches, 345 security tests and 24 checks. The isolated modern environment matches all 143 candidate wheel payload files; 274 other distributions are unchanged. All four original Variant A hashes match val.md §8.4. Mocked original transport contracts, isolated lock/check and pre-child audit pass. No completion has been sent.

Request a fresh CNY 3 ceiling for at most two completion attempts, without retries, each with a 90-second wall deadline. Caps are 256 then 384. Endpoint is the official DeepSeek API and model is deepseek-flash. Send only original public MT-Bench question 82 first turn, single-v1 rubric and the original fixed synthetic email answer (at most 4000 UTF-8 JSON bytes). No project source is sent. A must pass complete capture/provider acceptance before B. Stop on any request or acceptance failure.

The freshly checked official /models endpoint returns HTTP 200 and lists the model. Current peak CNY prices per million tokens remain 0.04 cache-hit input, 2 cache-miss input and 8 output, with the original 1Mi-token context reservations 2.0992 / 2.100224. A timeout keeps its reservation and prevents B when the remaining budget is insufficient. Record usage-based estimates rather than claim an invoice.

Budget policy: val.md §8.4.1 requires a newly approved budget. The previous 750270b replay authorization does not carry to this candidate. Original failed A and its ledger remain immutable; use a separate new ledger. No release or publication is included.

Tariff: https://api-docs.deepseek.com/zh-cn/quick_start/pricing/
