# R08-A / P-B: five-project Gate A

The final **r2** run passes all five base targets, all ten complete JSON comparisons
with zero differences, and all fifteen supplementary CLI diff cases. Product source
is the final-QA candidate `0b36780edaaa6150693dc9dd7330e5ba429a1398`, version 0.7.0.

- 380 recorded commands: 130 product commands (10 base, 30 captures, 90 diffs),
  10 full JSON comparisons, 30 original-checkout identity checks, and 210 disposable
  clone Git commands. 355 exit 0; 25 threshold diffs exit the expected 1.
- Wall time: 176.055400 seconds; command durations sum to 275.893365 seconds.
  These are different measures. Product-command duration is in [attempts.json](attempts.json).
- Every original source pin, public origin and tracked/untracked clean state passes
  before/after. The final QA's complete 498-input inventory, all thirteen oracle files
  and frozen tools pass byte-hash checks before and after execution.

The base layer runs explicit L0 audit and complete facts collection at each pin.
[Comparisons](comparisons/) contain the original complete comparison JSON. Only audit
root timestamp/version use the established exemptions; facts remain strict. Complete
stderr compares after CRLF-to-LF only, while original stream hashes remain physical.
Raw base stdout/stderr are retained once in private storage and are **not** included
in this public directory. The index and command receipts identify their exact hashes.

The fifteen [unfiltered pair diffs](diffs/) retain original bytes. Each source has
default/LOW/NONE inherited-profile cases in separate disposable clones. A/B keep one
clean overlay commit and fixed manifest/profile bytes, capture no config files and
actually consume cap 256/384 through a standard-library child. The full non-NONE
set is precisely target HIGH/LOW plus argv MEDIUM, or argv MEDIUM alone for NONE.
Expected metadata paths/values/status are derived independently from both raw runs.
Repeat JSON, complete filtered summary, hidden-MEDIUM threshold and empty self-diff
pass. `summary.same` is observed and repeat/filter-preserved, not independently counted.
The recorder still labels child consumption unverified; the independent stdout receipt
proves only this named bounded child's cap observation. Hardware capture is explicitly
unavailable in this fixture; real Git and installed-version metadata are retained.
No native framework, model, provider, GPU computation, paid API or gated-file access runs.

The first attempt passed the base layer but its extension was **NOT_EXECUTED** because
the isolated Git template lacked `.git/info`. [Attempts](attempts.json), the original
[r1 commands](attempts/r1-commands.json), complete r1 comparisons and old tool sources
preserve that failure. A four-command pure Git regression proves the mkdir correction;
no product/QA input or old oracle changed. The second attempt uses new clones and
reruns the entire matrix. Earlier evidence directories are unchanged.

[Summary](summary.json), [commands](commands.json), [identity](identity.json),
[oracle provenance](oracle-provenance.json), [independent expectations](expectations.json),
[product inputs](product-inputs.json), [harness regression](harness-fix-regression.json)
and [index](evidence-index.json) bind the result. Tool copies are inert `.py.txt`;
private path mappings are withheld. Raw comparison/diff bytes and original EOF are
protected by `.gitattributes`; no raw artifact is rewritten for formatting. Generated
receipts use LF. All persisted JSON documents retain `schema_version: 1`.

This Gate A does not close VAL-R01, VAL-R02, VAL-R03, native/judge resource acceptance
or the release matrix. See [the session report](../README.md).
