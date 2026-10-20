# Supplementary H2 metadata replay — 2026-10-20

Candidate `948d16423023027fff77322b8a872acaba306691`. [Replay summary](summary.json) accepts five targets across offline/two-online modes; this does not claim a complete training environment or that every audit finding is PASS.

[Complete comparisons](complete-historical-comparison.json) preserve 15 complete locks and 15 complete reports. Every original lock/report is included byte for byte under `artifacts/`, with all five exact supplementary input manifests under `inputs/`; [results](results.json) names each artifact and original hash. Only declared schema-owned timestamps and the report lock digest bound to actual lock bytes explain historical differences.

[Command summaries](commands-summary.json), [all check results](checks-summary.json), [source origins](origin-summary.json) and [independent metadata review](peer-review-metadata.json) cover 96 successful commands, 639 checks, 51 product origins, five doctors and one anonymous GPT-2 probe. Full command arguments and every log remain external.

The 192 independently recomputed stream hashes refer to retained stream bytes. For controller-sanitized streams, pre-transform original hashes are retained as identities only; those missing pre-transform contents were not recomputed. See [stream-hash scope](stream-hash-scope.json).

[Layer boundaries](layer-boundaries.json) preserve the five missing original §8.1 manifests and blocked authenticated restricted-file access. These §8.2 supplementary manifests do not replace the original inputs. Native GPU work is in progress and is not packaged as PASS here; paid provider acceptance and R06-B implementation are outside this package.

[Public-source qualifications](public-source-qualification-context.json) preserve two narrowly proven public examples from the separate offline discover review. They contain no request body or literal path and create no exemption for private machine paths or credentials.

[Source index](source-index.json) distinguishes original bytes, deliberate projections and hash-only external evidence. JSON timestamp-location pointers are semantic field paths, not physical filesystem paths. No credentials or environment files were read during packaging.
