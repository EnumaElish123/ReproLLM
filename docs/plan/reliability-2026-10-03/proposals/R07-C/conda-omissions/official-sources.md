# D-M-CE official sources and limits

Status: PROPOSED. Sources checked on 2026-10-27 for the R07-C Conda
extraction-omission P-A. No Conda, package manager, solver or proposed product
candidate was executed. These dated public pages are mutable references, not
immutable source snapshots; no fetched-body hash or installed-manager identity
is claimed.

## Primary sources

| Official source | Status/date observed | Relevant support |
|---|---|---|
| [CEP 24: environment.yml](https://conda.org/learn/ceps/cep-0024/) | Approved; updated 2025-04-09 | The `dependencies` section distinguishes MatchSpec string entries from installer mappings and identifies `pip` as an installer subsection. This supports keeping Conda-string extraction separate from YAML structure and embedded-pip extraction. |
| [CEP 29: MatchSpec](https://conda.org/learn/ceps/cep-0029/) | Accepted; updated 2026-03-04 | The Syntax, String matching and Version matching sections describe channel/subdir prefixes, wildcard names, bracket constraints and compound version clauses. The language is broader than this project's bounded extractor. |
| [Conda stable MatchSpec API](https://docs.conda.io/projects/conda/en/stable/dev-guide/api/conda/models/match_spec/) | The retrieved page identifies itself as Conda 26.9.3 documentation | Canonical examples include channel-qualified and subdir-qualified forms. Version equality does not by itself identify an artifact: the reference separately discusses the additional fields or checksum needed for a fully specified package. |

The CEP 29 page's Accepted status and later update date are recorded as observed;
they do not establish that every historical Conda client implements every part
of that document. Likewise, the stable URL can resolve to another documentation
version later. None of these sources proves that this environment installed or
executed a corresponding client.

## Independent product boundary

The sources establish why a string omitted by a deliberately narrower extractor
cannot generally be called invalid Conda syntax. They do not establish that
every omitted string is valid, installable, exact, or recoverable. In particular,
ordinary-looking channel syntax and malformed-looking input can reach the same
existing return branch. Empty strings and arbitrary punctuation need no external
validity judgment for this proposed predicate.

Option A is defined entirely by the existing source's two early returns from
`_add_conda_entry`: failed name-pattern fullmatch, or a successfully captured
head whose remainder starts with `::` or `/`. A new internal `unparsed_conda`
code would identify that omission. It would not call the Conda grammar or
installation process a failure.

The existing numeric-range and complex-suffix routes still append a named,
nonexact declaration and are excluded. A shared `unsupported conda declaration`
diagnostic does not identify the proposed cause. URL-looking `https://...` and
space-before-`::` inputs ordinarily retain a head under the current regex and
are also excluded. Do not normalize them into a newly eligible path or extract
a package from the omitted text.

Repository-wide SKIP is a proposed conservative product choice, not a conclusion
required by any external source. Prior D-M, D-M-E, Poetry or Pipfile acceptance
does not approve D-M-CE, the new reason code, its concrete normative patch, or
its threshold and presentation costs. See [design review](design-review.md).
