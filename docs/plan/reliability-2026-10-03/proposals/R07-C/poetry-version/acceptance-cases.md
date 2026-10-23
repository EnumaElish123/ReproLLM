# D-M-V future independent acceptance design

Status: DESIGN ONLY; all 48 rows are future P-B requirements, not passing tests. Candidate policy executions: 0. Written from current source/spec and official type evidence, before any candidate implementation.

| ID | Scenario | Independent expected behavior |
|---|---|---|
| T01 | version=false / true | Both decoded bool values cause invalid_structure only in a reached Poetry value mapping; declaration tuple/line and diagnostics unchanged. |
| T02 | version=0 / positive integer | Both zero and nonzero integer are present non-str; do not lose zero through truthy fallback. |
| T03 | version=finite float / inf / nan | All actual TOML decoded floats cause the same shape issue; no coercion to str or numeric exact credit. |
| T04 | version=[] / ["2.5.1"] / mixed list | All explicit version list values trigger, including empty and apparently singleton-exact lists; do not parse list members. |
| T05 | version={} / {nested="2.5.1"} | Both explicit mapping values trigger; do not recursively extract a nested version. |
| T06 | version=TOML local date / time / datetime | Successfully decoded temporal objects are non-str and trigger; fixtures must be actual TOML, not manual null. |
| T07 | version absent in empty package mapping | No new issue; current declaration (None,None) remains. This is not a completeness certificate. |
| T08 | source-only/options-only mapping, no version | No new issue; preserve enrichment/source/optional capture behavior and no invented exact pin. |
| T09 | version=empty or whitespace string | No new issue, preserve helper (None,None); blank is not inferred to be malformed from helper output. |
| T10 | version=bare valid PEP440 exact string | No new issue; retain bare exact credit, including pre/post/dev/local/epoch cases under existing grammar. |
| T11 | version=single non-wildcard == string | No new issue; retain exact version and current helper return shape. |
| T12 | version=range/caret/tilde/wildcard/compound string | No new issue despite exact=None; retain original stripped specifier, nonexact credit rules, and diagnostics. |
| T13 | version=unsupported/invalid grammar string | No new issue from this slice; no full Poetry grammar validation or Requirement invocation is added. |
| T14 | package value directly str/int/float/bool/date/list | Only value mappings with present version qualify; retain all nonmapping alternatives even if unsupported by the existing extractor. |
| T15 | package value valid multiple-constraints list | No new issue; do not descend into each element or invent exact pin from a member. Official valid alternatives are not generalized failures. |
| T16 | package value list containing a mapping version=false | No new issue from this slice: nested alternative is not an existing traversed mapping entry; wider list structure remains OPEN. |
| T17 | transport key plus absent version | No new issue for url/git/path/file/hg/svn/bzr-key combinations; retain old no-exact behavior. |
| T18 | transport key plus string version | No new issue; exact remains None even if string is bare or == exact. Do not grant new transport version credit. |
| T19 | transport key plus non-str version | Triggers the same explicit field type issue. The claim concerns this extractor field only, not complete Poetry validity or actual installation behavior; empty/false transport fields do not exempt it. |
| T20 | noncritical name / python entry mapping has version=false with independent torch use | Issue influences the existing remaining critical-use set repository-wide. Do not infer torch from malformed field; current independent use must be present. |
| T21 | only noncritical malformed Poetry entry and no critical imports | Issue recorded but no new critical applicability/package finding; preserve no-critical-use skip and existing Python empty-result veto behavior. |
| T22 | same-package surviving exact declaration plus malformed Poetry value | Exact-declaration credit wins first; preserve partial declarations, order, and any diagnostics; no SKIP for the credited package. |
| T23 | unrelated malformed nested pyproject plus used critical packages | A may replace every remaining uncredited WARNING/promoted CRITICAL with SKIPPED/INFO. This is an explicit global conservative cost, not a manager-scope lock association. |
| T24 | qualified origin lock credit plus malformed version | Actual qualified-lock credit still wins; lock package membership, origins, association and uncertain barriers remain byte/field equivalent. |
| T25 | D-F and D-S with malformed version | Existing associated format-lock failure wins with its existing message, hint and evidence; new D-M fact does not leak into higher branch evidence. |
| T26 | D-L with incomplete Python/possible lock plus malformed version | Existing D-L wins; source failure remains recorded internally but finding uses D-L contract. |
| T27 | D-G final depth frontier plus malformed version | D-M precedes D-G for remaining uncredited packages; new finding/evidence follows existing D-M contract. |
| T28 | existing same-file D-M-S precheck cause | Prior invalid_structure retained; no overwriting/reason split, and no additional diagnostics. |
| T29 | same-file PEP621 unparsed_requirement before Poetry loop | setdefault retains unparsed_requirement. Do not extend the earlier global structure precheck, which would wrongly reorder the stored cause for this chosen proposal. |
| T30 | multiple bad Poetry values in same file | One issue entry per logical file, no duplicate finding/evidence; retain all existing declarations in encounter order. |
| T31 | multiple failure sources and prior D-M finding | Distinct file paths are lexically sorted in evidence, previous current-use evidence stays first; existing skipped finding can gain a source item. |
| T32 | version key case and extra names | Only exact key version qualifies; Version/unknown extra keys remain unchanged. Do not add package-name, key-whitelist or other property checks. |
| T33 | nonmapping parents / wrong dependencies table type | Existing finite D-M-S parent checks apply; do not inspect unreachable values or replace read/syntax/structure precedence. |
| T34 | Poetry groups / dev-dependencies / PEP735 / build-system only | No new traversals, declarations or issue solely from those unvisited sections; malformed version nested there remains outside this slice. |
| T35 | Pipfile packages/dev-packages explicit version=false | No new issue from this Poetry-only slice; shared helper and Pipfile callers remain unchanged, pending independent evidence/design. |
| T36 | PEP621/environment/requirements sources | Retain prior D-M-P/D-M-E/D-C/D-G contracts and their distinct blank/strip/route semantics; no broad helper policy propagation. |
| T37 | unreadable/undecodable pyproject | Existing unreadable/invalid_syntax only; no value inspection after decoder failure and no retry/read expansion. |
| T38 | not-discovered / filtered / safely refused candidates | Do not add listing, reads, roots, include edges or budget to discover potential field failures. |
| T39 | inline vs expanded Poetry package table and line indices | Same decoded predicate when actually iterated; preserve legacy source_file and existing _TomlLineIndex package key line even if version physical line differs. |
| T40 | manual/legacy Declarations defaults | Existing empty internal dictionary remains default; no persisted schema field/new reason code or inferred issues from historical/manual tuples. |
| T41 | complete original declaration and graph trace comparison | All declaration fields/order, project roots, lock membership/association, manifest/lock presence, graph, reads/Requirement calls/diagnostics remain equal aside from the explicitly added file issue. |
| T42 | isolated ordinary WARNING at fail-on WARNING | Approved A changes qualifying finding to SKIPPED/INFO and may change CLI exit1 to0; exact full JSON must be asserted, not only counts. |
| T43 | FAIL-only promotion, suppression, independent warning and thresholds | Promoted critical failure becomes unpromoted SKIPPED/INFO; suppression and alias still apply; independent qualifying finding still exits1, exit2/3 behavior unaffected. |
| T44 | default text / verbose / JSON / default export | Existing text may show PASS plus skipped count, complete JSON retains finding, default export omits it. No renderer/export implementation changes. |
| T45 | profile detection / hints / init / manifest | Successful declaration inventory and derived profiles/hints/init output should remain unchanged; verify via affected consumers, do not infer it from summary counts. |
| T46 | determinism and privacy | Repeated same logical inputs give byte-identical relevant records; no path/host/user/secret leakage or raw malformed value added to messages. |
| T47 | five pinned projects and independent source impact | Read source before forecasting full rule/profile/hint/diagnostic/init delta. If no reached non-str version field exists, predict zero delta but do not call zero-source audit a trigger-branch validation. |
| T48 | P-B final acceptance and resources | After accepted precise patch: test-first RED/GREEN, final complete quality plus all-five Gate A and affected matrix; resource gates blocked/N-A explicitly. P-A must not claim these future rows executed. |
