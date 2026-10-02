> **PENDING — proposal only. Not approved, implemented, filed on GitHub, or adopted as gold.**

# Remaining candidate lifecycle contract beyond the existing list bug

The completed UX-T05 repair fulfils the existing M7-T04 requirement:
visible pending/accepted/ignored text with default --json accepted-rule arrays
unchanged. The following are proposals, not implemented or authorised CLI contracts.

1. Add an explicit `rules list --candidates [--json]` view. Default --json remains the
   current accepted-rule array. The explicit candidate array can include computed
   state plus the existing candidate fields (rationale/evidence/bindings/confidence).
   State is derived from project-rules.yaml and never persisted into Candidate.
2. Add read-only `rules show ID`: display the complete accepted rule or latest
   candidate before approval. Clearly label the source file, field, severity,
   rationale, evidence and copied bindings. Do not silently search/reaccept older
   discoveries; define latest-file selection and unknown-ID exit 2 explicitly.
3. Define reversal before adding removal. `ignore` currently records a candidate but
   does not deactivate an accepted rule, and `accept` can accept an ignored candidate.
   Specify accepted→ignored behavior and whether accepted/ignored can coexist.
   Preferred active-state rule: acceptance takes precedence while an active rule
   exists; deactivation is an explicit rule command, never a display-only ignore.
4. A minimum `rules remove RULE_ID --reason TEXT` can remove the active entry and
   make the lock stale, but loses accepted_at/edited bindings/reason if no history is
   retained. Retaining exact approval provenance needs a reviewed tombstone/history
   design or owned archive; do not invent an unversioned audit-log file. An archived
   copy of the removed rule adds a persisted document/schema and D-41 review.

Amend CLI §1, project-rule ownership §7 and acceptance/state transitions §20.5.
New read-only presentation flags need no schema change; provenance-retaining
deactivation may. Acceptance tests should cover first discovery, full review,
accept/ignore conflicts, duplicate acceptance, reversal, JSON compatibility,
bindings/provenance retention and lock staleness. Do not imply `rules ignore`
currently removes active checks; this is a proposed behavior decision.
