# Offline judge evidence — synthetic two-A check

Independent readback passed for two actual A-only experiments: the native recorder and Skill. Each used one exact HTTPX mock response with the original FastChat question 82 / single-v1 builder and parser. The parsed score was **8**. There were **zero real provider requests**. Root has accepted this offline component only. This portable independent derivative retains `accepted=false`; full resource and live judge acceptance remain false.

| Family | Actual run ID | Duration | Child exit |
|---|---|---:|---:|
| native | `20261102T011339Z-8419db` | 12.478301 s | 0 |
| skill | `20261102T011502Z-ec2142` | 7.944933 s | 0 |

The actual network guard denied AF_INET and AF_INET6 creation and allowed AF_UNIX. This is an inherited socket-creation boundary for the trusted recipe, not packet capture. All 219 tracked source files and the source index remained unchanged.

The four captured bindings were judge model `deepseek-flash`, endpoint `https://api.deepseek.com`, temperature `0`, and maximum tokens `256`. The upstream builder requested `2048`; the unchanged transport enforced the bounded cap. Recorder Python was `3.12.14`, while the separately identified experiment child used `3.11.12`. Native environment/hardware/command contexts and child input consumption remain **unverified**.

All nine raw run differences are retained in [offline-judge.json](evidence/offline-judge.json): the judgment artifact hash, input commit, duration, end time, lock before/after fingerprints, lock hash, run ID and start time. The only scientific output difference is the actual judgment timestamp. The lock differs in three clock leaves: `generated_at`, `models.judge.observed_at`, and `datasets.eval.revision.resolved_at`. There are no unexplained P1/P2 findings.

The controller command template, from the fixed preparation directory, is:

```bash
<formal-tool-python> -I -B run_offline.py --go root-offline-go.json --go-sha256 e4dbc793452168a0cc6b6564d5f68b868d097cceb59a56cb8c558631bf9d9a67
```

The captured experiment command was `python validation/judge_entry.py`. The JSON includes the exact source-derived native and Skill command templates. Execution receipts retain process exits and raw hashes; they do not retain argv bytes.

This receipt does not establish audit/export coverage, B or A/B replay, the GPU resource gate, real service availability, paid usage or budget authority. The unchanged entry's stdout says “real”; this run is synthetic. Raw paths and machine metadata are excluded from this portable derivative, while original artifact and source SHA-256 references are preserved in the JSON.

Independent report SHA-256: `7cd6a9c371b231fe0cba9abc67236cbcc05f3d28be53f148869b4afe4492d182`.

Root offline component: `final-gate-bindings/offline_judge.json`, SHA-256 `5b3780e2aa553f7f35b6253c82af0686fa91a54d0f91474f2a95a30fe54743d3`, status `ROOT_ACCEPTED_INSTALLED_NATIVE_SKILL_SPLIT_OFFLINE_A_ONLY`.
