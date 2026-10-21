# Spec proposal: R07-C dependency absence under possible format-lock credit

Labels: spec
Status: local complete issue draft; not published or sent externally.

Current specification §12.3.1 preserves nonempty used-but-unpinned WARNING and leaves its classification OPEN.
Existing A/profile-P decisions exclude the new branch. Python limits cannot hide independently read declarations;
they can hide import origins granting R06-B credit to captured format locks.

Propose bounded D-L with exact rule/spec/test/CHANGELOG patches in this packet: only current unsatisfied in-use
packages with incomplete/unavailable primary-Python coverage AND captured supported-format membership become
per-package SKIPPED/INFO. Exact/qualified credit wins first; other packages and complete views keep old behavior.
Coarse invalid-pair/barrier skips and user-visible failure/text/export changes are explicit compatibility costs.

Proof is relative to a fixed captured dependency view; no new parser/listing completeness or lock credit is claimed.
Four manager hidden-origin observations and full counterpart support the concrete witness. Five pinned portfolios
contain no supported format locks, so prewritten impact is zero delta; formal Gate A remains due after acceptance.

Decision requested: accept concrete D-L normative/rule patches and proceed with P-B, or preserve current policy.
No engine/redaction/schema change, version release or paid/GPU resource authorization is requested.
