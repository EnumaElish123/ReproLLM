# Schema export validation prerequisite

The ISSUE-14/15 final quality gate exposed an existing Windows defect at
`b4d6c71`: all ten CLI schema exports have CRLF bytes while the committed files
and canonical renderer use LF. JSON values agree. Specification section 23
requires fresh exports to match the committed files; this is an existing-contract
correction, not a schema or policy amendment.

Strengthen the existing freshness regression from text reads (which hide newline
translation) to byte reads. The unchanged exporter produces one failure and four
passing controls. Write the canonical renderer's UTF-8 bytes directly, retaining
all fields, filenames, indentation and the final newline. No model/schema fields,
committed JSON schemas, dependencies or version change. The earlier directory
preparation error and both failed quality attempts remain retained.

The final input must rerun the complete quality gate and all-five Gate A. Also
export schemas freshly from each of the five pinned working directories into
separate external output directories; compare the exact ten-file set and every
byte with the unchanged Git schema files. The previous complete pytest pass is
historical evidence, not final acceptance of this correction. Paid APIs, GPU
execution, releases and unrelated changes remain outside the session.
