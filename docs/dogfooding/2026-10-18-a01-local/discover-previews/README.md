# Five-project offline discover previews

These five **supplementary, read-only collector checks** use the accepted
replay's installed candidate wheel. They do not use the missing original M3/M4
manifests, initialize the upstream projects, contact a model or close the formal
live-discover/resource gates.

For each [fixed upstream checkout](../../../../val.md#2-pinned-portfolio), run:

```console
reprollm discover . --experimental --dry-run --show-content --max-chars 30000
```

The actual commands run under D02's isolated Python launcher, which rejects
socket connections/name resolution before importing the installed CLI and does
not forward provider credentials. All five exit 0; requests sent: **0**.
Total accepted wall time is 24.547 seconds. The source checkouts have the exact
pins and are clean before and after each command; no manifest or other file is
written.

[results.json](results.json) records complete safe command receipts, source
identity, file/character counts and hashes of the actual request messages.
The five text reports preserve the selected-file manifests and exclusions.
The full message previews remain private rather than duplicating third-party
source; their original stdout/stderr hashes are retained in the receipts.

The selected content budget is at most 30,000 characters. Message headers and
context add characters, so the rendered user-message size is recorded separately.
Every selected source path is checked against tracked source at the pin, with
no absolute/traversal path, forbidden file or excluded data/output directory.
A second secret-policy check of the actual messages returns zero redactions.
These are contract assertions and observed counts, not a new payload gold.

The first collection helper reached four successful previews before discovering
that lm-eval used a separate verified short checkout path. The final run uses
the existing checkout-location mapping for all five; the earlier raw outputs
and failure are retained in [preparation receipts](../preparation-attempts.json).
No input, policy, gold or product code was changed to complete this check.
