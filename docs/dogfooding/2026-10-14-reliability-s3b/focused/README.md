# S3-B focused evidence

This bundle retains development RED/GREEN observations, compatibility-reader history, snapshot reviews and exact raw-log hashes. It does not qualify final session QA, CI or Gate A.

Use `focused-overview.json` to resolve every original logical source to a portable receipt or a content-addressed complete log. Identical logs are stored once; original raw files remain in task-owned scratch. JSON is parsed before replacing local path/identity strings; integer schema versions and inner document versions are preserved.

The intermediate B runs remain 249 PASS + 1 old-warning-expectation FAIL and 646 PASS + 1 old-version-snapshot FAIL. Their original logs are retained. Reviewed fixes and subsequent targeted checks are separate observations. The root's 32/42 follow-ups have terminal transcript receipts only: no raw log or raw SHA is invented.

Bridge-wheel bytes are not copied. The frozen 0.6.2 binary is referenced by its independently recorded SHA and source payload proof. The later new-writer compatibility Gate remains separate.
