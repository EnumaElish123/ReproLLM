# Runtime file capture

`reprollm run` hashes original file bytes. A text snapshot is a separate,
redacted copy: its contents may therefore have a different hash from the
`sha256` recorded in `files[]`. Use that recorded hash to compare the original
input with the lock or working tree; do not use the snapshot to reconstruct
credentials.

Only regular files inside the repository are captured, including files reached
through symlinks that remain inside it. Forbidden names are hashed without a
snapshot. Binary files and text larger than the configured size limit are also
hash-only. More than 200 input files disables snapshots and records a warning.
`--no-snapshot` disables input file snapshots while keeping their hashes.

Manifest binding config paths have `origin: declared` under specification
§5.1 R-04. Additional config paths from project rules have `origin: binding`.
Only declared bindings produce parameter observations; arbitrary flags are
not interpreted as research parameters.
