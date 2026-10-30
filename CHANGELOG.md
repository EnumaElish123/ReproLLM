# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/), and this
project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Changed

- SK14 (spec §§3.2, 20, 22): initialize experiment declarations and saved commands,
  export current/historical reports and emit ten schemas through guarded Skill
  writes. Reuse native validation, selection and renderers, with source-bound
  previews, explicit overwrite hashes and preserved partial/unknown write facts.
  Keep historical source-aware privacy in the emitted artifacts as well as replies.

- SK13 (spec §§5, 9–10, 16, 21–22): expose local audit, doctor, profile/task
  inspection, recorded-run inspection, diff and command preview through the
  verified Skill installation. Preserve native results and diagnostics with
  private snapshot-bound paging, explicit completeness and separate worker/CLI
  results. Preserve omitted historical source fields and retain typed source,
  command-argument and environment-name privacy across historical JSON/text,
  diff and audit reports without changing raw comparisons or gate decisions.
  Bind cached views to all trusted Python helpers and guard audit report writes
  by exact target hashes. Pin the compatible
  published source containing the contextual privacy scanning prerequisite;
  retain the previous candidate for verified reuse and rollback.

- SK12 (spec §§16, 21–22): add the Agent Skill entry, capability introduction
  and strict typed request/authorization protocol. Capability-only requests
  require no installation or project scan; installation status remains read-only.
  Distinguish implemented adapter actions from product capabilities and retain
  separate invocation, gate, child-result and completeness fields.

- SK11 (D-30; spec §§16, 22): prepare an isolated Agent Skill tool environment
  from verified source and hash-pinned wheels, with atomic activation, explicit
  updates/rollback, offline reuse and lease-aware uninstall. Check installation
  integrity before executing probes, keep errors private, and include Skill
  scripts in CI type and coverage checks. Existing project environments remain
  outside the installer ownership boundary.

- SK10 (D-30; spec §§22–23): define the Agent Skill's immutable official-source
  installation candidate and separate hash-pinned lightweight runtime/build
  dependencies. Validate source identity, supported Python/platform ranges and
  artifact integrity before preparing an installation; reject unknown sources.

- UXR05: add a four-command first-use tutorial using the bundled standard-library
  configuration probe, with guided setup, saved-command preview/run and optional
  report/diff steps. Distinguish author walkthrough evidence from model evaluation.

- UXR04 (spec §3.2): explain required research fields during interactive init,
  retry invalid answers in place and preserve accepted values. Count actual
  missing declarations, retain unknown/manual fields and point to review/audit.
  Preserve noninteractive manifest bytes and existing write protections; quote
  explicit text without changing its meaning and keep new diagnostics private.

- UXR02 (spec §5.2.1): report invalid saved working-directory characters as
  private usage errors for run and preview, before creating any runtime artifact.

- UXR01 (spec §3.2): treat command privacy-inspection limits as private usage
  errors before writing, including deeply nested quoted JSON arguments.

- UXR03 (spec §21): lead text audits with up to three prioritized next actions
  and an explicit skipped-check caveat. Preserve complete findings, machine output,
  rule results and fail-on behavior; only six human-text fixtures gain the section.

- UXR02 (spec §5.2–§5.2.1): `run` and `run --dry-run` select saved
  `execution.command` when argv is omitted, using finite quoting without a shell.
  Honor saved cwd or an explicit override; keep explicit argv and runtime evidence
  unchanged, and reject invalid saved inputs before creating a run.

- UXR01 (spec §3.2): save an explicitly supplied experiment command with
  `init --command`, validate it before writing, and preserve literal YAML string
  values. Existing initialization and prompts remain unchanged without the option.

- R07-C (spec §12.3.16): finish the accepted captured-view conclusion policy
  for six rules using observed listing, detection and Python-version gaps.
  Preserve concrete violations, positive witnesses and prior credit/skip priorities;
  recover dependency decoder recursion limits with internal `parser_limit` facts.
  Missing-evidence failures may become SKIPPED/INFO, including isolated exit 1→0.
  LlamaFactory's initialized profile check and export pass count follow the reviewed
  forward supplement; historical results and unsupported grammar remain bounded.


- R07-C D-I (spec §12.3.15): retain supported requirements include targets
  rejected by existing candidate checks, then mark remaining missing-pin evidence
  as SKIPPED/INFO after all existing credit and skip priorities. This conservative
  influence is repository-wide, even for unrelated or nonexistent targets; an
  isolated warning or promoted-critical gate can change from exit 1 to 0.
  Preserve reads, graph budgets, inventories, diagnostics and persisted schemas.

- R07-C D-M-CS (spec §12.3.14): record internal `unparsed_conda_specifier`
  only at the existing retained-name Conda specifier-placeholder assignment.
  Preserve the six legacy numeric-range forms, both omission returns, regexes,
  declarations, diagnostics, earlier causes and exact/qualified-lock credit.
  Reuse D-M's repository-wide conservative SKIP policy even for known nonexact
  or unrelated restrictions; an isolated warning/promoted-critical gate can
  change from exit 1 to 0. No grammar/read expansion, engine/schema, dependency,
  historical-record, five-project gold or version-release change.

- R07-C D-M-CE (spec §12.3.13): record internal `unparsed_conda` only when
  the existing native Conda extractor returns without a declaration because its
  name pattern does not match or the matched remainder starts with `::` or `/`.
  Preserve retained ranges/suffixes, diagnostics, earlier causes, partial
  declarations, barriers and exact/qualified-lock credit. Reuse D-M's existing
  repository-wide conservative SKIP policy, including blank or unrelated omitted
  entries; an isolated warning/promoted-critical gate can change from exit 1 to 0.
  No grammar/read expansion, package-name inference, engine/schema, dependency,
  historical-record or version-release change.

- R07-C D-M-PF (spec §12.3.12): record an explicit non-string `version`
  only inside already-traversed Pipfile `packages` / `dev-packages` mappings as
  internal `invalid_structure`. Preserve earlier causes, partial declarations,
  original line fallbacks, shared-helper `allow_bare=False`, barriers and all
  exact/qualified-lock credit. Reuse D-M's priority and repository-wide
  conservative SKIP policy; an isolated warning/promoted-critical gate can change
  from exit 1 to 0. Missing/string versions, whole nonmapping values, transport
  controls and custom categories retain their existing behavior. No new reads,
  grammar, engine/schema, dependency, historical-record or version-release change.

- R07-C D-M-V (spec §12.3.11): record an explicit non-string `version` field
  only inside an already-traversed Poetry dependency mapping as internal
  `invalid_structure`, preserving earlier causes, all declarations, existing line
  values and exact/qualified-lock credit. Reuse D-M's priority and repository-wide
  conservative SKIP policy; an isolated warning/promoted-critical gate can change
  from exit 1 to 0. Missing/string versions, nonmapping alternatives, groups and
  Pipfile keep their existing behavior. No grammar/read expansion, engine/schema,
  dependency, historical-record or version-release change.

- R07-C D-M-E (spec §12.3.10): retain failed extraction of already-reached,
  stripped nonblank environment embedded-pip strings as internal declaration
  uncertainty. Preserve blank filtering, partial declarations, source ordinals,
  diagnostics, prior causes and exact/qualified-lock credit; reuse existing D-M
  priority. Unrelated failed sources can conservatively change remaining used,
  uncredited packages from WARNING to SKIPPED/INFO and an isolated gate from
  exit 1 to 0. No pip/Conda grammar expansion, new reads, engine/schema changes,
  historical rewriting, dependency change or version release.

- R07-C D-M-P (spec §12.3.9): retain actual PEP 621 dependency-string parse
  failures at the two existing extraction sites as internal declaration uncertainty,
  including empty/whitespace strings. Preserve partial declarations, earlier source
  failures, exact/qualified-lock credit, diagnostics and reads; reuse D-M after
  D-F/D-S and D-L. Unrelated failed sources can conservatively change remaining
  used, uncredited packages from WARNING to SKIPPED/INFO and an isolated gate from
  exit 1 to 0. Other grammars, engine, persisted schemas, historical artifacts,
  dependencies and version remain unchanged.

- R07-C D-C (spec §12.2): recognize a bounded inline-comment prefix only after
  an ordinary requirements graph line fails its original parse. Preserve the
  original routes and successful parses; reject new URL prefixes and disable
  this fallback for a captured file with any trailing-backslash physical line.
  Newly captured dependencies can change exact/requirements-lock credit, package
  use, profile evidence and init scaffolds; an isolated fail-on gate can change
  in either direction. Existing credit and uncertainty priorities remain.
  No continuation processing, new reads, other-format grammar, schema, historical
  gold, dependency or version change.

- R07-C D-G (spec §12.3.8): record supported requirements include targets absent
  from the final captured graph after the existing depth budget. After exact and
  qualified-lock credit and D-F/D-S, D-L and D-M, remaining used critical packages
  become SKIPPED/INFO with target evidence. This repository-wide uncertainty can
  make an isolated warning/promoted critical gate stop failing; it grants no
  credit. Later shallow capture removes a target from the new fact. No new reads,
  probes, grammar, schema, gold, renderer, dependency or version change.

- R07-C D-M-S (spec §12.3.7): record the approved bounded decoded declaration
  container/member type failures, preserving partial valid declarations, existing
  diagnostics and exact/qualified-lock credit. Remaining used critical packages
  follow D-M's repository-wide SKIPPED/INFO policy after D-F/D-S and D-L; an isolated
  warning/promoted critical gate can stop failing. Missing/correct empty containers
  and top-level YAML null retain their behavior. Package values, string grammar,
  unknown Conda mappings and requirements graphs remain outside this slice.
  No schema, gold, renderer, dependency or version change.

- R07-C D-M (spec §12.3.6): retain known captured dependency-declaration body
  read/decoder failures internally. After existing credit and D-F/D-S/D-L paths,
  remaining critical-package missing-pin warnings become SKIPPED/INFO with
  failed source evidence. Influence is repository-wide under retained existential
  exact semantics, including unrelated failed candidates. Only actual requirements
  body read failures join; readable grammar/structure/include-graph errors remain
  outside. An isolated warning/promoted critical gate can stop failing. No credit,
  presence, renderer, engine, scanner, schema, gold, dependency or version change.

- R07-C D-S: classify the specified decoded format-lock container/name-entry failures as unverified missing-pin evidence through the accepted associated-lock path; retain partial positive credit, legacy empty values, presence semantics and historical gold.

- R07-C D-F (spec §12.3.4): preserve known format-lock body read/decoder failures
  internally. For current in-use critical packages, retain exact and qualified
  credit first; otherwise a failed lock with an existing R06-B qualifying captured
  origin produces SKIPPED/INFO instead of missing-pin WARNING, independently of
  Python coverage. Unassociated failed locks and successful empty/nonmember locks
  keep their existing behavior. An isolated warning/promoted critical gate can
  stop failing; no lock credit, presence, renderer, schema, gold or version change.

- R07-C D-L: when primary-Python analysis is incomplete or unavailable, used-but-unpinned
  critical packages that occur in captured format-lock package sets become SKIPPED/INFO.
  This conservatively allows for missing import-origin lock credit; exact declarations,
  qualified credit, other packages and complete-view behavior retain their contracts.
  An absence-only warning or promoted critical gate may stop failing. This does not
  certify dependency parsing or grant credit to an unassociated lock (spec §12.3.3).

- P-B / R07-C declared-profile absence (spec §§12.3.1–12.3.2): when a declared
  non-core profile has no detection entry and primary-Python candidate coverage
  is incomplete or unavailable, report that profile as SKIPPED/INFO instead of
  an absence-derived FAIL. Keep positive high-confidence mismatches and existing
  empty-result handling. New SKIPPED outcomes do not receive FAIL-only severity
  overrides, so a prior override-triggered failure can stop triggering exit 1.
  Suppression, thresholds, schemas and historical reports retain their contracts;
  broader R07-C dependency/listing/framework coverage remains open.

- P-B / R08-B A4 (spec §18): classify exactly the recorded target_epsilon,
  target_delta and max_grad_norm leaves under privacy.mechanism.params, plus
  training.params.num_train_epochs, as HIGH in newly computed diffs. Existing
  first-match profile LOW/NONE overrides and historical reports are preserved.
  A target-only change can now make explicit --fail-on HIGH exit 1; this does
  not certify privacy guarantees or child consumption. No schema or alias change.

- P-B / R07-C partial A (spec §§11–13): when primary Python candidate analysis
  is incomplete or its internal coverage is unavailable, an empty result from
  `env.llm_critical_deps_pinned` or `exec.profile_detection_mismatch` now yields
  SKIPPED/INFO with a bounded coverage reason instead of a synthetic PASS.
  Existing nonempty findings, all other rules, generated project rules, schemas,
  failure thresholds and R07-B diagnostics keep their contracts. This deliberately
  conservative policy is unreleased; broader mixed-evidence coverage remains open.

- P-B / R06-B (spec §12.2): retain repository-wide exact declaration evidence,
  while format-lock package credit requires a paired manager manifest and an
  actual declaration or nearest-project import origin. Foreign locks and
  uncertain manifest boundaries can now leave a critical package WARNING;
  workspace parent-lock delegation is not inferred. Lock presence, requirements
  closures, rule IDs, severities, thresholds, schemas and five-project gold are
  unchanged. This policy is unreleased; no version or dependencies change.

### Development workflow

- P-A / R07-C D-M-S (spec §§12.2–12.3.6): prepare a closed decoded
  declaration-structure proposal, an unapplied specification amendment, current
  parser/rule observations and independent five-project source expectations.
  Preserve partial positive evidence and distinguish missing/empty values from
  specified wrong types. This is PROPOSED; product behavior, normative spec,
  historical gold, dependencies and release version remain unchanged.

- P-A / R08-B (spec §18): inventory actual privacy/training free-form fields,
  prepare four exact default-HIGH paths with source mappings, compatibility,
  independent conditional experiments and unapplied default/spec/test/gold
  patches. The concrete policy is PROPOSED; current severities, schema,
  historical records and release behavior remain unchanged.

- P-A / R07-C (spec §§11–13): prepare all-rule evidence, eleven original-policy
  observations, complete five-project conditional comparisons, and unapplied
  specification/engine patches for a bounded two-rule synthetic-PASS veto.
  The policy and D-41 patch were unapproved at P-A preparation. The later
  specific acceptance and bounded P-B change are recorded above; the original
  proposal/evidence remain historical snapshots and gold is not rewritten.

- P-A / R06-B (spec §12.2): prepare source-linked dependency and lock-scope
  evidence, a concrete association proposal, compatibility limits and future
  acceptance cases; synchronize current delivery/resource navigation. The
  proposal and its specification patch were unapplied at P-A preparation; that
  session changed no dependency policy, historical gold, schema, package version
  or release behavior. The later accepted P-B change is recorded above.

- P-A / R08-A (spec §18): prepare a bounded direct-judge-parameter proposal,
  current-policy evidence, regression design and unapplied policy/spec/test/gold
  patches. Decisions remain proposed; default severities and historical gold
  are unchanged.

- A03 (spec §§1, 5, 17–20): index dated project and validation facts with their
  sources and limitations, retain a provisional OSS-maintenance narrative,
  and label old adoption metrics and application text as historical. Current
  form matching, independent feedback and submission remain incomplete.

- A02 (spec §§1, 5, 17–19): prepare local trial task cards, candidate installation
  guidance, an empty feedback template and a draft invitation. Separate material
  readiness from real independent trials, issue closure and sustained adoption;
  no invitation is sent and resource gates remain blocked.

- A01-B (spec §§4–5, 15–19, 22): share an offline stdlib replay with two
  isolated installations of the same verified wheel, independent consumption
  receipts, exact snapshot hashes, complete A/B drift, post-consumption mutation
  and selected-run exports. Retain failed preparation attempts and resource
  blockers; no native or paid validation is promoted and no version is published.

- A01-A (spec §§4–5, 16, 22): recover available reviewed input bytes,
  verify their original hashes, and inventory inaccessible formal inputs with
  precise recovery actions. Input recovery does not close resource gates.

- D03: gate publication on the exact candidate's reusable five-job quality
  checks, nonempty preflight release notes, complete hash-bound validation
  evidence and the independently installed wheel from one build. Recheck wheel,
  sdist and evidence after artifact download before either publishing action;
  keep dispatch rehearsals nonpublishing and retain explicit resource blockers.
  No version, tag or publication is introduced by this change.
  Recognize uv's narrowly validated build-directory marker without including
  it in the package manifest or weakening rejection of unexpected files.

- D02: validate one prebuilt wheel in a fresh external environment using the
  shared offline walkthrough, explicit interpreter selection and package-data
  commands. Record wheel hashes, optional build-manifest source association,
  isolation evidence and semantic assertions; reject wrong target versions and
  missing package data. Clarify published versus local development availability
  without changing the package version, maturity classifier or release workflow.

- VOPT-02: use focused checks per task and one complete final session quality
  gate; retain all five product-validation targets and full gold assertions with
  affected extensions. Document explicit documentation/tool-only exceptions,
  environment preflight and immutable baseline reuse; milestone/release resource
  gates remain unchanged.
- VOPT-03: add a read-only complete JSON gold comparison script with safe
  hash-referenced difference reports and explicit audit-metadata handling. It
  neither creates gold answers nor replaces the complete Gate A workflow.

### Specification

- R04-S: accept the concrete recorder/host/inherited-environment contract,
  internal typed State context and the run-specific schema-2 input-baseline
  proposal. Stage compatibility through the local 0.6.2 reader bridge before
  the 0.7.0 minor transition; other persisted schemas remain version 1.

- UX2-S01 / UX2-T01: record maintainer approval of the six product workflow
  improvements. Separate complete framework task inventories from explicitly
  selected experiment tasks; retain the five pinned repositories and add
  source-derived expectations for zero, one and two selected tasks.

### Fixed

- SK13 prerequisite (spec §16): avoid repeated unquoted-key suffix scans in
  contextual privacy handling for large ordinary report values. Preserve quoted
  matches, explicit cursor suffixes, secret replacements and redaction counts;
  add bounded real privacy regressions before the Skill pagination path.

- R07-C (spec §13): restrict standalone comment termination to shell scripts.
  Retain the existing Makefile backslash continuation so a continued Make comment
  cannot create a false framework command; preserve real recipe evidence.

- R07-C (spec §13): keep a standalone shell comment ending in a backslash
  from swallowing the next physical framework command. Preserve command evidence
  line numbers, existing continued commands and pending-line comment behavior.

- R07-C (spec §§13–14): skip task YAML whose static composition exceeds the
  parser recursion limit, preserving other lm-eval and LightEval task candidates
  and recognizable framework evidence. Audit and initialization continue without
  constructing YAML values, exposing parser exception text or changing scan budgets.

- R07-C (spec §13): collect keys from deeply nested decoded configurations
  without recursive Python calls, so audit, initialization and export retain
  the decoded key evidence. Preserve live traversal order, repeated acyclic
  aliases, active-container cycle handling and existing decoder/error boundaries.

- R07-C (spec §13): stop configuration-key traversal at YAML container cycles
  so audit, initialization and export retain healthy key evidence. Preserve
  traversal order and repeated shared aliases outside the current path; config
  values remain excluded from keyword detection.

- R07-C (spec §§3.2, 14): use InspectAI's existing task-name fallback when its
  independent Python parser raises `RecursionError`, so `init` and `init --list-tasks`
  can finish. Retain the fallback grammar, safe sorted candidates and explicit task
  selection; task names do not imply metric implementations.

- R07-C Python parser follow-up (spec §§12.3.1–2, 13): skip a selected source
  when `ast.parse` raises `RecursionError`, retain a fixed safe diagnostic and
  continue scanning siblings. Count it as selected but not parsed under the
  existing coverage policy, preserving successful evidence and warning gates.

- R02-R follow-up (spec §§5.1, 16): retain bounded Python judge source and
  complete JSONL rubrics without changing safe source bytes. Python literal
  and key contexts no longer cross independent statements; JSON path checks
  use decoded strings so escaped newlines remain intact. Keep secret, real
  path, identity, malformed-input and child-exit protections, with exact pinned
  source and whole-run regressions.

- R08-A (spec §18): classify changed, added and removed direct
  `evaluation.judge.params.*` leaves as HIGH by default. Explicit
  `--fail-on HIGH` can now exit 1 for that leaf alone; exact LOW/NONE
  profile overrides, single-segment matching and deeper/privacy/training
  policies are unchanged. Preserve historical diff evidence and apply the
  separately reviewed prospective judge gold supplement to new replays only.

- D03 / D02 handoff: return a safe JSON distribution failure when a command exits
  zero without producing one unique run record, preserving command receipts
  without exposing the private exception message or machine paths.
  Compare installed schemas with only CRLF/LF normalization, retaining strict
  file sets and every other byte so native Windows exports can be validated.

- D01 (spec §§5, 15–19): restore the reviewed bounded GSM8K cap 32→48
  recipe with matching model/data revisions, actual config bindings, independent
  consumption evidence and offline regressions, including a post-consumption
  config rewrite. Preserve GSM8K regex escapes, instruction tokens and relative
  template suffixes in snapshots; recognize parsed division operators only in
  Python file capture while retaining path/secret protection. Native acceptance
  is recorded separately from the stdlib probe and other resource gates.

- R04-B (spec §§5, 15, 17–19): the local 0.7.0 minor transition writes run
  schema 2 with pre-child manifest/lock and file baselines, bounded original-byte
  config observations, and separate post-child change checks. Output hashes stay
  post-child; audit, diff, runs and every export template qualify evidence without
  claiming child consumption. Readers retain schema-1 compatibility without
  rewriting records and reject newer schemas with upgrade guidance. Migration:
  use the 0.6.2 reader bridge before sharing schema-2 records with older tools;
  bridge readers warn/skip them in lists and reject explicit reads safely. Other
  persisted schemas remain version 1; no release or package publication is made.

- R04-A (spec §§4, 5, 12, 17–19): retain recorder and host observations with
  explicit subject/phase, qualify environment consistency and every export
  template, and preserve unknown child verification. The 0.6.2 compatibility
  bridge keeps run schema 1 and gives safe upgrade guidance for newer records
  in runs, diff and export, preserving old record bytes and child exit codes.

- VOPT-01 (spec §22 T-09): preserve the default slow-test exclusion in the
  Windows CI marker override; keep performance budgets in nightly and register
  the slow marker. Coverage, security and platform checks remain unchanged.

- R07-A performance follow-up (spec §13): capture the canonical root once per
  static candidate view, avoid repeated filename normalization and reuse POSIX
  ordinary root-file eligibility. Windows, aliases, complex paths and failed
  metadata checks retain full resolution; explicit candidates and content reads
  keep fresh root checks.

- R07-B (accepted spec §13): report Python file-budget coverage once on default
  stderr for audit, init including task listing and interactive planning, and
  export's current audit. Use actual AST parse successes and candidate, selected,
  active limit and omitted counts; explain selected read/parse skips when present.
  Keep JSON, report files, exported Markdown, rule findings and fail-on thresholds
  unchanged. Preserve detailed verbose diagnostics while suppressing duplicate
  presentation of the same file cap; reject source-text summary impersonation.

- R07-A (spec §§11/13): apply shared static candidate exclusions before Python,
  dependency, framework, profile and discovery budgets in Git and walk modes.
  Exclude known generated directories and nested environments marked by
  `pyvenv.cfg`, including internal links and explicit requirements/task paths;
  preserve real nested research projects, bounded safe reads and independent
  Git/security file facts. Diagnose uninspectable environment markers safely.

- R06-G validation: construct external sentinel fixtures with fixed UTF-8 bytes
  so Windows newline conversion cannot invalidate the strict unchanged-byte check.
  Preserve every external-read guard and static consumer assertion.

- R05-B (spec §12.2, accepted R05-S C): treat single-equality Conda versions
  without a build as prefixes. Recognize numeric double-equality versions and
  supported export triples with literal ASCII builds; retain their original
  version/build evidence without adding schema fields. Diagnose unsupported forms
  conservatively and keep arbitrary unknown text out of public evidence. Preserve
  embedded pip's Python semantics and existing YAML dependency-entry line indices.

- R06-P (spec §§12.2/13): normalize internal requirements includes and share
  one captured graph for each root's exact-lock qualification and package set.
  Keep source aliases, deduplicate physical declarations, and exclude unreferenced
  siblings. Diagnose cycles, depth exhaustion and unreadable or escaping edges
  at their include lines. Support spaced `-r target` / `--requirement target`;
  report attached and quoted forms as unsupported with safe fixed reasons.
  Preserve independent-root aggregation and existing safe non-include diagnostics.

- R06-A (spec §12.2): retain every dependency and lockfile source when filenames
  repeat, ordering root files before other relative paths. Keep manifest
  qualification separate from selection and share that ordering with Python
  declaration checks; preserve nested declarations and each lock's package evidence.
  Skip malformed candidate containers with fixed source diagnostics while keeping
  valid root facts and lockfile identities.

- R05-A (spec §12.2): distinguish Python exact versions from wildcard, range,
  arbitrary-equality and transport declarations. Recognize supported local,
  pre/post/dev and epoch versions in each format, including Poetry's bare
  version fields; keep declaration, requirements-lock and audit findings in
  agreement. Preserve physical TOML dependency lines with escaped markers.

- R06-G: check the resolved project boundary before static content reads and
  cache reuse, including user profile overrides and inherited-name validation.
  Limit built-in resource reads to shipped names. Refuse external targets with
  safe diagnostics, keep internal symlinks and file/Git/security facts, and
  enforce bounded text reads without changing dependency or detection policy.

- R03: select the last explicit CLI binding, including project-rule aliases, and
  preserve that effective value through State merges and JSON round-trips. Keep
  every original observation and repeated-evidence multiplicity without growing
  overlapping evidence. Audit, diff and export agree with the child; existing
  consistency conflict and drift severity policies remain unchanged.

- R02-R: preserve key context when capturing nested or bound secret values and
  quoted JSON/YAML/TOML text and comments. Apply PEM removal before keyed
  handling and omit ambiguous TOML patches safely. Protect records, snapshots,
  patches and saved output before writes, including saved secret argv; retain source metadata, benign
  experiment values and original file hashes. Privacy failures keep safe child
  evidence and its exit code while draining raw output. Existing runs remain
  unchanged; redacted placeholders do not recover secret-value comparisons.

- R02: reject secrets, absolute paths and machine identity in the final lock
  object or serialized YAML before creating any temporary file. Preserve old
  lock bytes and keep safe parameters unchanged; include nested key context for
  the existing generic secret policy. Hash-only prompts and freshness checks
  retain their contracts. Existing locks are not automatically cleaned.

- R01: validate the final init YAML before writes, replace the manifest atomically
  after preparing missing auxiliary files, and preserve existing bytes and
  permissions on failure. Reject symlinked owned output nodes. Invalid or unsafe
  directory names use `experiment` with editing guidance; legal names retain
  string semantics even when YAML would infer another type. Schema is unchanged.

- UX3-T04: filter `runs list` by exact name, saved status, derived outcome and
  positive limit while preserving default table/JSON output. Add
  `diff --latest-successful [--name TEXT]` to compare the two newest completed
  exit-0 records, older to newer, with full IDs in the existing report. Preserve
  corruption warnings, historical snapshots, explicit input resolution and
  threshold behavior; reject insufficient pairs and invalid selector modes
  without silently choosing alternatives. Persisted schemas are unchanged.

- UX3-T03: add `run --dry-run` for a read-only preview of declared bindings,
  input capture eligibility, required environment-variable presence and local
  lock freshness. It starts no subprocess, makes no request and writes no
  artifacts; values are withheld and input reads are bounded. A completed
  preview with warnings exits 0; invalid required inputs exit 2. Existing
  runtime capture and persisted schemas remain unchanged.

- UX2-T06: add `rules show` and `rules list --candidates` to inspect complete candidate,
  active-rule and archive records with source paths and current status; preserve
  the existing `rules list --json` active-rule array. Reject ignoring active
  candidates and direct users to removal.
- Add `rules remove RULE_ID --reason TEXT` and `rules restore ARCHIVE_ID` with
  immutable archive-first recovery copies, conflict checks, privacy checks and
  best-effort protection against detected concurrent active-file edits. Archives
  record recoverable rules rather than successful removal events; failed active
  updates retain the archive and report the recovery ID. Refresh the lock after
  successful removal or restoration.
- Schema migration: add independent `RuleArchive` v1 documents at
  `.reprollm/rule-archives/<archive_id>.json` and the tenth exported schema,
  `rule_archive.schema.json`. Existing project-rules v1 documents and the other
  nine exported schemas are unchanged; no migration is required. The new schema
  requires explicit maintainer code review under D-41.

- UX2-T05 / UX-T08 extension: include effective Evaluation/Judge/Privacy and
  model/dataset/prompt research details with declared/locked/observed labels.
  Selected runs use their own snapshots and observations; label the current
  audit scope separately. Protect free-form Markdown/HTML and keyed secrets
  before serialization while preserving copyable command text.
- UX2-T04 / UX-T06 judge: add explicitly selected `judge_only` for grading
  existing answers, with its own judge parameters and evaluation evidence.
  Share a narrow primary-model exemption between audit and init; mixed/custom
  profiles retain their requirements. D-44 supersedes only D-06's profile count.
- UX2-T03 / UX-T06: classify `provider: other` with a safe declared HTTP(S)
  endpoint as an opaque API per model role. Preserve unsupported-provider and
  alias warnings, unresolved identity, stale-lock checks and offline behavior;
  avoid demanding unobservable dtype/quantization. No new provider calls or keys.
- UX2-T02 / UX-T04: separate audit findings from the effective exit threshold.
  Group repeated failing warnings with three examples and a shared fix; add
  `--details` to expand every row. Preserve full JSON/GitHub evidence and exits.
- UX2-T01 / UX-T03: keep the complete framework task inventory separate from
  experiment metrics. Add read-only `init --list-tasks`, exact repeatable
  `--task` selection and interactive profile/task prompts. Default init now
  leaves metrics empty for author selection; invalid selectors fail before
  writes. Task names remain Unicode-safe, sorted and deduplicated.

- UX-T08 / M10-T01: remove machine paths and identity from displayed export
  values, and redact keyed credentials before Markdown hides their key context.
  Preserve portable dot-relative paths in the shared run privacy helper while
  keeping explicit Discover field and config traversal checks.
- UX-T08 / M10-T01: render checklist splits, repetitions, metric names, judge
  roles and privacy values from the effective experiment state. Remove
  references to absent evidence sections and guard malformed observed metrics;
  preserve the default export and existing artifact schemas.
- UX-T07 / M9-T01: derive Action counts, summary and annotations from a single
  saved audit report. Preserve finding/error exit codes and upload a generated
  report after finding failures without reusing stale reports after errors.
- UX-T02 / M8-T02: preserve operating-system identity variables in the
  credential-filtered quickstart environment so Windows capture and audit can
  resolve the username for privacy redaction without the Unix-only `pwd` module.
- UX-T05 / M7-T04: list pending and ignored discovery candidates even when no
  project rule has been accepted, and distinguish accepted candidates from
  pending ones. Preserve the existing accepted-rule JSON array.
- UX-T02 / M8-T02: restore completed examples to their reviewed lock and
  implementation hashes; preserve historical lock/export files when refreshing
  examples and fail CI on stale locks. Replace destructive demo commands with
  a disposable standard-library capture, diff and export walkthrough; clarify
  installation, Python requirements, audit levels and credential prerequisites.
- UX-T01 / M7-T03–T04: honor discover exclude globs for contents, source
  snippets, tree paths and manifest context. Include globs add bounded text
  files without bypassing safety exclusions. Add an offline full-message
  preview with `discover --dry-run --show-content`. Apply the 64 KiB source
  limit and whole-file secret rejection to snippets, and check symbolic-link
  targets against the same boundaries. Drop secret-bearing paths from outgoing
  trees and headers, with redacted local diagnostics.

### Documentation

- R00: retain the current reliability baseline, reproducible defect observations,
  quality results and five-project validation inputs for the S1-A batch.

- PLAN-REVISE: update the reliability execution package to v1.2 after code
  review. Add P0 run/capture redaction (R02-R), shared static-content read
  boundaries (R06-G), input-capture phases (R04-B), and the explicit dependency
  specification prerequisite (R05-S). Align sessions, acceptance matrices,
  recipe/evidence dependencies and agent prompts; repairs remain planned.

- PLAN-IMPORT: add the 2026-10-03 reliability execution plans v1.1, copyable
  coding-agent prompts and a current-plan index linked from contributor and
  documentation entry points. Preserve planned task status, pending policy
  decisions and resource-validation boundaries; no product behavior changes.

- UX3-T01: reconcile the roadmap, backlog and UX delivery index with the
  published 0.6.1 baseline and merged, unreleased UX2 improvements; record PR #8
  approval and successful main CI without rewriting historical validation.

- README-T01 / M8-T02–T08: redesign the README around a responsive original
  banner, sourced CLI evidence, research use cases, a minimal first audit,
  artifact workflow and paper/CI examples. Refresh the linked documentation
  index and distinguish published features from unreleased changes; record
  the five-project README study and validation evidence.
- Record the product-trial repairs, complete five-project comparisons and
  [pending specification choices](docs/plan/ux-2026-10-02-proposals/README.md)
  in the [UX session report](docs/dogfooding/2026-10-02-ux-repairs.md).
- Track the three deferred resource-validation groups after 0.6.1 in a
  [resumption checklist](docs/dogfooding/pending-resource-validation.md), linked
  from val.md, the patch report and backlog. Preserve blocked status and the
  independent gold while recording resources, replay steps and closure criteria.

## [0.6.1] - 2026-10-01

### Fixed

- M4-T02 / M11-T01: complete the Hugging Face, Transformers, vLLM,
  OpenAI-compatible and PEFT integration interfaces and consume them in
  detection, lock resolution and metadata capture. Reuse the bounded AST scan,
  resolve adapters once, and avoid HTTP client construction during offline lock.
  Detect literal OpenRouter `base_url` arguments without retaining URLs or keys.
- M9-T01: align the local composite Action with the published Action's
  numeric audit exit code; validate all four CLI exits with successful and
  failed annotation steps.
- M9-T02: emit comma-separated GitHub workflow-command properties and keep
  the file and line from the same evidence item, preserving escaping.
- M7-T04: keep the invalid-candidate retry available after an endpoint rejects
  JSON mode; retain the final failed response and cap all requests at three.
- M11-T01: connect evaluation framework detection and task extraction to `init`;
  pre-fill sorted task candidates, including lm-eval YAMLs with custom tags, without
  executing tags or importing the framework. Authors still confirm selected tasks and
  metric implementations; secret-bearing and machine-specific task names are excluded.
- M8-T02: refresh CLI documentation for GitHub output and checklist templates, repair
  macOS temporary-directory aliases and Windows path separators in quickstart generation,
  fix captured terminal styling and width under GitHub Actions and Windows,
  render CLI documentation with a portable program name and console, show freshness diffs,
  and enforce all generated-document checks in ordinary CI and nightly again.
- M7-T04: include explicitly declared built-in manifest fields in discover's duplicate
  exclusion context, recognize source-snippet evidence, and discard evidence outside the
  sent input files while retaining the candidate's stable ID and lowering confidence.
  Clean returned candidates, failed raw responses and errors before persistence,
  remove unsafe fields/bindings and exact credential echoes, and preserve real
  filenames containing `#L` while normalizing generated snippet locators.
  Preserve valid relative config bindings containing `./` without allowing
  normalization to hide original credential, identity or traversal content.

### Validation

- Local quality gate: 1,437 tests passed; redaction branch coverage remains
  100%; schemas and generated documentation are current. Export snapshots
  change only their two package-version markers.
- The maintainer deferred remote/GPU and unavailable exact judge-input
  validation for this patch; these resource checks are not fresh passes.
  Five-project full Gate A and available command/metadata matrices have zero
  new gold deltas; one real DeepSeek discover request passed independent
  candidate review and acceptance/audit checks. See `val.md` §8.7 and the
  [patch session report](docs/dogfooding/2026-10-01-patch-0.6.1.md).

## [0.6.0] - 2026-09-29

Adoption-sprint release: everything in the M9–M11 track plus the Beta
baseline from M1–M8.

### M9: GitHub Actions integration
- `audit --format github` — workflow-command output for any CI
- `reprollm-action@v1` — published composite Action, bootstrapped in CI

### M10: Paper checklist alignment
- `export --template neurips|acl|acm` — venue-specific checklist mappings
- `docs/checklists.md` — 45-row mapping across three conference checklists
- All five P1 rules confirmed implemented

### M11: Evaluation framework integrations
- `lm_eval`, `lighteval`, `inspect_ai` — detect usage, extract task names
  for init pre-filling, report versions
- `docs/integrations/` — manifest examples and run snippets per framework
- `docs/integrations/card-snippets.md` — HF model/dataset card snippets

### Since 0.5.0 (Beta)
- Windows golden comparison closed at the root (byte-exact canonical form)
- Performance budgets (20k-file audit <10s) in nightly CI
- `py.typed`, `CITATION.cff`, `twine check` clean
- `examples/` with real lockfiles, CI-validated
- Documentation suite: quickstart (CI-regenerated), concepts, FAQ, why,
  CLI reference, diff reading guide
- `lock --offline` constructs no HTTP client (SOCKS-proxy environments)

## [0.5.3] - 2026-09-29

### Added (M11)

- Evaluation framework integrations (`integrations/`): `lm_eval`,
  `lighteval`, `inspect_ai` — each detects usage (imports, CLI invocations),
  extracts task names from framework config files (lm-eval task YAMLs,
  inspect-ai `@task` decorators) for `init` pre-filling, and reports
  installed versions. They never import the target library.
- `docs/integrations/` — manifest examples and recorded-run snippets for
  lm-evaluation-harness, lighteval, and inspect-ai.
- `docs/integrations/card-snippets.md` — copy-paste reproducibility snippets
  for Hugging Face model cards, dataset cards, and paper artifact READMEs.

## [0.5.2] - 2026-09-29

### Added (M10)

- `export --template neurips|acl|acm`: venue-specific checklist mapping
  appended to `REPRODUCIBILITY.md`. ReproLLM provides evidence (field values,
  hashes, run IDs) for conference reproducibility items — never Yes/No
  answers. Items outside ReproLLM's scope are listed honestly as *not
  covered*.
- `docs/checklists.md`: full mapping table across three conference
  checklists (45 rows, versions reviewed 2026-09-29).
- Nine demonstration exports (3 examples × 3 venues) committed under
  `examples/`.
- All five P1 rules confirmed implemented (M3/M4): `code.remote_recorded`,
  `model.trust_remote_code_declared`, `dataset.subset_declared`,
  `gen.stop_declared`, `prompt.few_shot_declared`.

### Since 0.5.1

- `reprollm-action` composite Action published at
  `EnumaElish123/reprollm-action@v1` and bootstrapped in ReproLLM's own CI.

## [0.5.1] - 2026-09-29

### Added (M9)

- `audit --format github`: workflow-command output for any CI that speaks
  GitHub Actions annotations — `::error`/`::warning`/`::notice` with
  file/line backlinks from finding evidence, spec-compliant escaping, and a
  summary notice. No Action installation required.
- `action/` — the complete composite Action (`action.yml` + Marketplace
  README), ready for the maintainer to push to the `reprollm/action` repo.
  Inputs: path, fail-on, level, version, check-lock; outputs:
  critical-count, warning-count; steps include a Step Summary table and an
  artifact upload.
- CI now self-audits ReproLLM with `--format github` (bootstrapped
  dogfooding in the Checks tab).

## [0.5.0] — Beta — 2026-09-29

The complete Beta workflow: audit (Level 0/1/2), init, lock, run with
redaction, semantic diff, export, project rules, and experimental discover.

### Added (M8 stabilization)

- `examples/` — three runnable example repositories with real mirror-resolved
  lockfiles, refreshed by `scripts/refresh_examples.py` and audited in CI.
- Documentation suite: CI-regenerated `quickstart.md` (real output, cannot
  rot) and `cli.md`; new `concepts.md`, `why.md`, and a 12-entry `faq.md`;
  README rewritten for the Beta; `docs/diff.md` gained a line-by-line
  output-reading guide.
- Boundary guarantees as regression tests: empty manifest, corrupt lock,
  future `schema_version` (clear upgrade message), manifest-only repo,
  non-UTF-8 filenames — all actionable errors, never tracebacks.
- Performance budgets (20k-file audit < 10 s, init < 15 s) run nightly;
  per-PR runs stay fast.
- Packaging: `py.typed` ships; twine check passes; `CITATION.cff`;
  `scripts/check_no_leaks.py` for post-hoc artifact scans.
- Community: roadmap and good-first-issue catalog under `docs/community/`;
  CONTRIBUTING/SECURITY finalized.

### Fixed

- The Windows golden mismatch is closed at the root: test-written fixtures
  now force LF endings everywhere (the last straggler of the platform-newline
  family), and golden comparisons use a byte-exact canonical form whose
  failure messages carry hex dumps.
- `lock --offline` constructs no HTTP client at all.

## [0.5.0a1] - 2026-09-28

### Added (M7)

- `reprollm export`: deterministic `REPRODUCIBILITY.md` from manifest + lock
  + run — identity tables with revisions/pinnability/digests, code,
  environment, hardware, execution (explicit no-run degradation), an audit
  run embedded verbatim, known limitations, and version footer; whole
  document passes secret redaction.
- Project rules end-to-end: `reprollm rules add/list` write
  `.reprollm/project-rules.yaml`; accepted declarations execute as audit
  rules (`project.*`, severity_origin `project_rule`); their bindings join
  run-time observations (`consistency.custom_fields` has real data; the
  `project_rules_sha256` lock-freshness branch triggers for real).
- Experimental `reprollm discover` (opt-in; time-boxed, delivered):
  offline collector with redaction gating (files whose redaction triggers
  are dropped whole), one temperature-0 JSON request to a user-configured
  OpenAI-compatible endpoint with a confirmed file list, deterministic
  candidate ids, evidence-path demotion, and `rules accept/ignore`/pending
  listing. `--paper` is rejected in Beta.
- Discover candidate schema (§20.4) completes the placeholder; schemas
  re-exported. `docs/export.md`, `docs/project-rules.md`,
  `docs/discover.md`, and `docs/plan/backlog.md`.

### Fixed (M7 dogfooding)

- `lock --offline` no longer constructs an HTTP client at all — a SOCKS
  proxy environment used to crash offline locking at client construction.

### Validation

- Five-repository full flow (init → audit L1 → lock --offline → audit L2 →
  export) completed in disposable worktrees; discover dry-runs verified.
  Real GPU re-pairs (lm-eval clean re-run, HarmBench) remain gated on GPU
  availability; the DeepSeek judge and DistilGPT2 DP pairs are the formal
  standards per val.md §8.5.

### Changed (validation baseline)

- val.md §8.5 (reviewed 2026-09-28): the DeepSeek judge pair and the
  DistilGPT2 privacy fine-tune are promoted from supplements to the formal
  Gate B M5 standards for the FastChat-judge and llm-dp scenarios; the
  credential-gated GPT-4 and Llama-2 originals are retired with their
  residual differences recorded. No pinned commit or other gold changed.

## [0.4.0] - 2026-09-28
<!-- Consolidated release: the unreleased M4 (lock), M5 (run + redaction)
     and M6 (diff) work ships as one 0.4.0 by maintainer decision; versions
     0.2.0/0.3.0 were never tagged or published and exist only as drafts. -->

### Changed (M6, second half)

- Record the second-half validation evidence and prepare gated 0.4.0 release
  notes (M6-T08 preparation). Keep the package version at 0.1.1 until real paired
  model acceptance and the outstanding resource gates are complete.

- Document diff inputs, table v1, version components, verdicts, overrides and
  independent display/exit thresholds; add tested fixture excerpts to the README
  (M6-T07, spec §§6, 17–18). Real paired-model acceptance and release remain pending.

- Add four JSON/text diff goldens: captured prompt/temperature changes, a locked
  model revision, identical inputs and a torch patch update (M6-T06, spec §18).
  The capture scenario commits its changed inputs before measuring commit drift;
  identical inputs have no changes, and torch patch drift is MEDIUM under table v1.

- Migrate Level 2 generation, model identity, custom-field, environment and file
  consistency checks to State leaves and their alternatives (M6-T05, spec §§11,
  12.12, 17). Audit projects current declarations and working files alongside
  runtime observations; standalone diff continues to use historical snapshots.
  Existing audit snapshots and lock/run schemas remain unchanged.
  Invalid lock paths, including empty paths, remain explicit consistency findings
  instead of aborting State projection.

### Added (M6, first half)

- Add `reprollm diff` for run IDs/prefixes, run files/directories and lock files,
  with text/JSON reports, schema validation, display filtering and independent
  exit thresholds (M6-T04, spec §§1, 6, 17–18, 23). Snapshots are contained and
  mandatory when referenced; report values are sanitized after comparison.
  The v1 report adds nullable `filtered_below`; summary always remains complete.

- Compare effective State values with normalized equality, stable severity/section
  ordering, complete counts and source-conflict notes (M6-T03, spec §18).
  The `diff_report` v1 placeholder now requires input references, summary and
  changes. No diff writer was previously released; consumers of the placeholder
  schema must regenerate it. Lock/run schemas are unchanged.

- Ship the normative drift table and resolve ordered profile overrides, dirty-code
  notes and package version components (M6-T02, spec §§6, 18.1–18.2). Patch drift
  lowers severity by one level: torch MEDIUM_HIGH → MEDIUM, following the
  specification rather than the conflicting LOW example in the sprint plan.

- Project manifest, lock and run snapshots into a deterministic experiment State;
  retain every source with provenance and runtime precedence (M6-T01, spec §17).
  Three new State goldens include declared/resolved/observed values; two synthetic
  run fixtures complete projection coverage. Existing lock/run schemas and audit
  snapshots are unchanged. YAML dates in free-form fields project to stable ISO
  strings before deterministic source ordering.

### Added (M5, second half)

- Document runtime capture, structured conflicts, environment policies, raw hashes
  versus redacted snapshots, child-owned artifacts, SLURM placement and private
  reporting; add run/inspection commands to the quick start (M5-T08, spec §§1, 5, 15–16).

- Add a real-child, dirty-repository leakage test covering both environment modes,
  argv, forbidden files, snapshots, patches and captured logs. Run the `security`
  gate separately in CI and before building release distributions (M5-T07,
  spec §§5.1, 16, 22 T-06); any failure blocks publication.

- Audit the latest valid run for file, generation, model, environment and accepted
  custom-field conflicts; preserve all structured evidence and project severities.
  Skip corrupt records with visible warnings and remove the final four runtime
  placeholders (M5-T06, spec §§5, 11, 12.12, 15). Reviewed Level 2 snapshots now
  explain missing evidence; a new post-run snapshot demonstrates a CRITICAL
  temperature conflict and `exec.run_recorded` PASS. Schemas are unchanged.

### Validation (M5-T09 preparation)

- Record unchanged five-project gold results, byte-identical initialization and
  full Level 1 comparisons, and independently specified runtime conflicts/latest
  matching runs. Real inference/training/judge gates remain blocked on provisioned
  resources; see [the validation report](docs/dogfooding/m5-second-half.md).

### Release note (M5, shipped in 0.4.0)

Planned for `0.3.0`: the first release of the **run record schema v1 writer**
and the documented redaction policy. [Draft notes](docs/releases/0.3.0-draft.md)
include sanitized inspection/conflict examples and an isolated packaging preflight
(M5-T10 preparation). Task commits are prepared; resource validation, maintainer review and CI are
still pending; no version bump, tag or publication is claimed.

### Added (M5, first half)

- Expose `run`, `runs list`, and unique-prefix `runs show`, with config defaults,
  child argument/exit preservation, JSON inspection, and a reviewed locked-fixture
  run snapshot showing CLI/config temperature disagreement (M5-T05, spec §§1, 5, 15).
- Execute commands without a shell, write crash evidence before launch and an
  atomic final record, forward signals, tee opt-in redacted logs, and preserve
  child exit codes through metadata-capture failures. Persist portable paths
  and hashed machine identity (M5-T04, spec §5.1 R-01/R-02/R-05/R-06/R-10–R-12).
- Hash repository-contained input and output files, snapshot bounded redacted
  text, and observe declared CLI/config/environment bindings with deterministic
  normalization and complete repeated-flag history (M5-T03, spec §§5, 15–16).
- Capture CPU/GPU metadata through bounded `nvidia-smi` calls, hash GPU UUIDs,
  and capture SLURM/PBS/LSF namespaces with secret names omitted and values
  redacted; malformed or unavailable GPU data is explicit (M5-T02, spec §5.1 R-07/R-08).
- Implement the nine ordered text-redaction classes, segment-based environment
  name checks, allowlisted environment capture, and streaming PEM suppression;
  execute the synthetic positive/negative/name corpus and enforce 100% branch
  coverage for the redaction module in CI (M5-T01, spec §16).
- Accept complete JWT padding variants under the maintainer-approved
  [spec correction #3](https://github.com/EnumaElish123/ReproLLM/issues/3), with
  all 27 segment-padding combinations covered. No schema or rule ID changes.

### Release note (M4, shipped in 0.4.0)

Planned for `0.2.0`: the first release of the **lock schema v1 writer**
(`reprollm.lock`, `schema_version: 1`). Existing manifest schema v1 remains
compatible; no schema migration is required.

### Clarified

- Keep only the four runtime consistency placeholders through M4; require an
  empty stub set after M5-T06, with a CI assertion for the current boundary.
  This maintainer-approved clarification changes no schema or rule selection
  ([#2](https://github.com/EnumaElish123/ReproLLM/issues/2), spec §§6.1, 12.12).

### Added (M4, second half)

- Record five-project metadata validation with independently checked HF
  revisions and file hashes, offline/online stability, and authenticated
  gated-file denial without credential leakage; retain Linux H2 as a pending
  manual gate (M4-T08, spec §§4, 12, 22; [validation record](docs/dogfooding/m4-lock.md)).

- Reuse the bounded HF client in `doctor --check-network`, including mirror,
  retry, metadata-validation, and sanitized authentication failure behavior;
  document lock provenance, pinnability, offline resolution and freshness
  (M4-T07, spec §§1, 4, 22 T-04).

- Add reviewed lock and Level 2 audit snapshots for all three complete fixtures,
  with exported-schema validation, an intentionally unavailable vLLM backend,
  API judge pinnability, and a gated-model denial (M4-T06, spec §§4, 10, 22).

### Fixed (M4 dogfooding)

- Recognize supported Apple Git version strings in `doctor` instead of reporting
  a parsing warning for their vendor suffix (M4-T08, spec §1).

### Documentation (M4-T09 preparation)

- Prepare [draft release notes](docs/releases/0.2.0-draft.md) with the real
  FastChat judge lock fragment and isolated wheel/sdist packaging evidence.
  Version bump, tag and publication await the manual Linux validation gate.

### Added (M4, first half)

- Add a bounded Hugging Face Hub HTTP client with mirror support, environment-based
  authentication, sanitized errors, and deterministic retry behavior, backed by a
  hand-written offline response corpus (M4-T01, spec §4.3 and §22 T-04).
- Resolve Hugging Face, API, and local model and dataset identities; hash prompts,
  declared files, metrics, local metadata, adapters, and bounded weights; and capture
  backend and environment provenance in online and offline modes (M4-T02, spec §4).
- Add `reprollm lock` with atomic deterministic YAML writes, offline and optional API
  verification modes, large-weight control, provenance summaries, and a network-free
  `--check` freshness path with exit code 1 for missing or stale locks (M4-T03, spec §§1, 4).
- Load and validate locks during audit, auto-detect Level 2, report manifest and accepted
  project-rule staleness independently, and compare locked prompt/config hashes with the
  current working tree using repository-contained paths (M4-T04, spec §§9–12.12).
- Enforce resolved model, tokenizer, chat-template, dataset, backend, prompt, and judge
  lock metadata with provider-specific severities and provenance evidence; API snapshot
  aliases remain informational while mutable API aliases warn (M4-T05, spec §§12.4–12.9).

## [0.1.1] - 2026-09-17

M3 completes all 38 Level 1 LLM experiment rules and finalizes the seven built-in
profiles: `core`, `inference`, `evaluation`, `llm_judge`, `finetuning`, `privacy`,
and `safety`.

An intentionally incomplete OpenAI judge manifest now reports the missing judge
sampling contract directly:

```text
CRITICAL (1)
  X judge.params_declared      Missing fields: evaluation.judge.params.max_tokens, evaluation.judge.params.temperature
      evaluation.judge.params.max_tokens (absent)
      evaluation.judge.params.temperature (absent)
      fix: Set evaluation.judge.params.max_tokens, evaluation.judge.params.temperature in reprollm.yaml.

28 passed · 0 suppressed · 11 skipped
Result: FAIL (1 critical, 2 warning)
```

### Added (M3, second half)

- Generated rule and profile reference pages with CI freshness checks, a
  documented Level 1 coverage overview, and an enforced 85% CI coverage floor
  (M3-T09, spec §§6, 12, 22–23).
- Complete and intentionally incomplete Level 1 manifests for the HF/vLLM,
  OpenAI judge, and privacy fixtures, with six reviewed JSON snapshots and
  variant-scoped dependency/secret overlays (M3-T08, spec §§3, 6.1, 12, 22).
- Apply `audit.ignore` by canonical rule ID or alias, preserving the original
  severity and mandatory reason in INFO findings. Honor config defaults for
  `fail_on` and `show_passed`, with explicit CLI flags taking precedence;
  suppressed results remain visible and do not affect exit thresholds
  (M3-T07, spec §§1.1, 8, 11, 21).
- Complete built-in profile rule selections and severity overrides, with
  most-derived override origins in audit findings and profile inspection.
  Add 15 explicitly skipped Level 2 placeholders and preserve project-owned
  severity metadata without implementing lock or runtime checks (M3-T06,
  spec §§6.1, 11–12, 18.2).

### Fixed (M3, second half)

- Treat either explicit boolean value for `models.<role>.trust_remote_code` as
  satisfying the repository-wide detection rule, matching the selected
  execution path without encouraging an inaccurate `true` declaration
  ([#1](https://github.com/EnumaElish123/ReproLLM/issues/1), M3-T10, spec §12.4).
- Compare detected profiles with the resolved inheritance closure, so a profile
  inherited by the selected experiment is not reported as undeclared. Clarify
  that unrelated repository capabilities do not need to be added to the
  manifest (M3-T10, spec §§6, 12.3).
- Allow `reprollm profiles show core` while continuing to reject explicitly
  selecting core in a manifest or `audit --profiles` (M3-T06).

### Documentation (M3-T10)

- Mark statically detected model IDs as candidates whose experiment role must
  be verified, add a practical manifest guide, and record Project A/B Level 1
  dogfooding findings and their disposition.

### Added (M3, first half)

- Five training and four privacy rules for training hyperparameters, complete
  LoRA adapters, threat models, nonempty mechanism parameters, privacy metrics
  and attack budgets (M3-T05, spec §§12.10–12.11).
- Six evaluation and four judge rules for metrics and implementation references,
  aggregation, repetitions, safety definitions/budgets, and independently declared
  judge roles and sampling settings (M3-T04, spec §§12.8–12.9).
- Five generation/backend rules and three prompt rules, including conditional
  sampling seeds, vLLM fields, explicit stop/few-shot declarations and prompt
  file existence without reading prompt contents (M3-T03, spec §§12.6–12.7).
- Five Level 1 dataset rules for role declarations, Hugging Face split/subset,
  preprocessing and sampling seeds, with zero-valued seeds preserved (M3-T02,
  spec §12.5).
- Six Level 1 model declaration rules, including per-role API exclusions,
  inference dtype/quantization fallback evidence, adapter detection, and explicit
  remote-code trust declarations (M3-T01, spec §12.4). The trust rule is selected
  by core per the maintainer-approved correction to spec §6.1.

### Fixed (M2-fix corrective sprint, 2026-09-10)

- Audit JSON no longer persists the raw invocation path (absolute paths
  leaked `/home/...`); the target is normalized to `.` or a repository-
  relative POSIX path, and `generated_at` is second-precision UTC (F-01,
  F-02).
- CLI error contract enforced: output-write failures are exit 2 with an
  actionable message; unexpected exceptions exit 3 without a traceback
  (traceback only with `-v`) (F-03).
- A `pyproject.toml` without `[project]`/`[tool.poetry]` no longer counts
  as a dependency manifest (F-04).
- Dependency evidence points at physical declaration lines instead of
  array/mapping indexes; no more `line: 0` (F-05).
- Separator-equivalent keyword spellings (`red team`/`red-team`,
  `dp-sgd`/`dp_sgd`, …) count as one detection concept (F-06).
- Exact `eval`/`evaluation` directory segments are an evaluation signal
  (F-07).
- Scan diagnostics (truncation, syntax errors, unparsed declarations)
  surface on stderr under `-v`; stdout stays one JSON document (F-08).

### Added

- Normative secret fixture corpus (§16.5): positive/negative/env/file
  cases for the M5 redaction classifiers (F-09).

### Changed

- init/doctor domain logic extracted into `core.manifest_scaffold` and
  `core.diagnostics`; CLI commands only parse/prompt/render/exit (F-10).
- Detection signals now come from the profile YAML definitions (user
  overrides honored); only schema-inexpressible semantics stay in Python
  (F-11).

### Added

- Authoritative five-project gold-answer validation matrix (`val.md`), milestone-gated real
  training/inference/API checks, and the M2 corrective sprint plan (M2F-T12).

## [0.1.0] - 2026-09-20

First usable release: **audit Level 0/1 + `init`**.

### Added

- Full `RepoScanner`: gitignore-aware listing with built-in ignores, cached
  reads, python/readme/config/directory helpers, and scan caps (M2-T01).
- `code.clean_tree`, `code.no_untracked`, `code.submodules_initialized`,
  `code.remote_recorded` rules (M2-T02).
- Dependency-declaration parsing (requirements incl. `-r` recursion,
  pyproject PEP 621 + Poetry, environment.yml incl. embedded pip lists,
  Pipfile), lockfile detection, and the six `env.*` rules
  (`dependency_manifest_present`, `lockfile_present`,
  `llm_critical_deps_pinned`, `python_version_declared`,
  `secret_files_ignored`, `reprollm_initialized`) (M2-T03).
- Python AST scanning (imports, HF repo-id constants, `trust_remote_code`,
  Trainer imports) and the forbidden-file matcher of the redaction policy
  (§16.4) (M2-T03).
- Deterministic profile detection per spec §13 with report-only rag/agent;
  detected profiles appear in audit reports and in the Level 0 text output
  with an `init` suggestion (M2-T04, M2-T08).
- Profile loader with inheritance closure, cycle detection, and user
  overrides at `.reprollm/profiles/`; all seven built-in profiles shipped;
  `reprollm profiles list|show` commands (M2-T05).
- `exec.command_declared`, `exec.seed_declared`, `exec.run_recorded`,
  `exec.profile_detection_mismatch` rules and the Level 1 audit path (M2-T06).
- `reprollm init`: manifest scaffolding from detected signals (template-
  rendered, required fields as TODOs, detected HF model ids prefilled,
  `--force`, `--interactive`, `--profiles`) plus `.reprollm/config.yaml`
  and `project-rules.yaml` creation (M2-T07).
- `reprollm` entry point maps `UserError` to exit code 2 (D-11).

### Changed

- Level 0 audits run the full sixteen-rule core profile; all six golden
  fixture snapshots updated (reviewed against the sprint acceptance list).

## [0.0.1] - 2026-09-13

### Added

- Project skeleton, quality tooling (ruff, mypy `--strict`, pytest), CI matrix
  (Linux/macOS/Windows), and trusted-publishing release workflow.
- Pydantic v2 schemas for every persisted document (manifest, lock, run record,
  profile, project rules, config, finding, audit report) with exported JSON
  Schemas and a `reprollm schema export` command.
- Deterministic audit engine (Level 0) with a rule registry, the implicit
  `core` profile, and the first two rules: `code.git_repo`, `code.git_commit`.
- `reprollm audit` (text/JSON output, exit codes per threshold) and
  `reprollm doctor` (environment diagnostics, opt-in network probe).
- Golden fixture repository infrastructure with deterministic commit SHAs and
  snapshot testing.

Not yet usable: `init`, `lock`, `run`, `diff`, `export`, and the full rule
catalog arrive in 0.1.0+ (see `docs/plan/00_architecture_and_decisions.md`).

[Unreleased]: https://github.com/EnumaElish123/ReproLLM/compare/v0.6.1...HEAD
[0.6.1]: https://github.com/EnumaElish123/ReproLLM/compare/v0.6.0...v0.6.1
[0.6.0]: https://github.com/EnumaElish123/ReproLLM/compare/v0.5.3...v0.6.0
[0.5.3]: https://github.com/EnumaElish123/ReproLLM/compare/v0.5.2...v0.5.3
[0.5.2]: https://github.com/EnumaElish123/ReproLLM/compare/v0.5.1...v0.5.2
[0.5.1]: https://github.com/EnumaElish123/ReproLLM/compare/v0.5.0...v0.5.1
[0.5.0]: https://github.com/EnumaElish123/ReproLLM/compare/v0.4.0...v0.5.0
[0.5.0a1]: https://github.com/EnumaElish123/ReproLLM/compare/v0.4.0...v0.5.0a1
[0.4.0]: https://github.com/EnumaElish123/ReproLLM/compare/v0.1.1...v0.4.0
[0.1.1]: https://github.com/EnumaElish123/ReproLLM/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/EnumaElish123/ReproLLM/compare/v0.0.1...v0.1.0
[0.0.1]: https://github.com/EnumaElish123/ReproLLM/releases/tag/v0.0.1
