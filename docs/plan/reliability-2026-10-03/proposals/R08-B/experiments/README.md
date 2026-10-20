# R08-B P-A conditional experiment

Base: `30dc9cae41b2fbcc1657357eff34b3e5a7f26322`. This is a proposal experiment, not implementation acceptance. The four proposed exact defaults remain uninstalled and unapproved.

Independent inputs and expected results were frozen before observation. Thirty Manifest→State cases, public resolver/profile checks, and 32 current-policy CLI calls passed 359 checks. Four exact paths are MEDIUM currently and HIGH only with a public in-memory SeverityTable. CLI has no public table-injection option; the proposed CLI result was not executed. Full reports, input bytes, exit codes, stdout/stderr and hashes are retained.

CLI inputs are synthetic standard run v2 records with identical metadata, command, manifest snapshot and run_id. Only one observed binding differs; no file digest or dirty-code HIGH masks its severity. No child, model, GPU, provider, network or paid request ran. Declared intent severity does not prove effective DP budget or input consumption.

Two tool qualification failures remain explicit: missing rule registration and an unsupported package launcher. They entered zero product CLI calls. Prior local files are hash-indexed; the launcher's private-path diagnostics have explicit sharing transforms with original/retained hashes. The first traceback exists only in the conversation; no invented original-stream hash is supplied.

`tests-proposed.patch` is an unapplied future test draft: syntax/lint/format and patch applicability were checked; future HIGH tests were not run as P-B. The test draft explicitly changes the existing epsilon MEDIUM assertion to HIGH. Before/after inventories bind all protected source, tests, schemas, dependencies and the three user work-in-progress files without copying their contents.
