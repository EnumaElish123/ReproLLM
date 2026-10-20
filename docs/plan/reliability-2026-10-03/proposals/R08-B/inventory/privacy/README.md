# R08-B privacy field inventory (P-A only)

No policy is accepted or implemented by this inventory. Current severity comes
from the unchanged ordered table and its single-segment matcher, not from a
field's name. Every source in the machine inventory has exact file bytes, a
SHA-256, line anchors and a logical repository or pinned-DP path.

| Exact field | Current | Recommendation | Evidence boundary |
|---|---|---|---|
| privacy.mechanism.params.target_epsilon | MEDIUM | HIGH, proposed | Actual formal manifest8→4; explicit sigma may override request |
| privacy.mechanism.params.target_delta | MEDIUM | HIGH, proposed | Actual formal0.001 and active constructor mapping; no historical delta mutation |
| privacy.mechanism.params.max_grad_norm | MEDIUM | HIGH, proposed | Actual formal1.0 → wrapper max_grad_norm_dp → fastDP max_grad_norm |
| training.params.num_train_epochs | MEDIUM | Separate training inventory | Actual formal0.125; active engine calibration horizon |

The four exact A4 fields have source support. No contrary evidence to that
bounded proposal was found. This does not establish that changing a recorded
value changes a mathematical privacy guarantee: a non-null noise_multiplier
overrides target_epsilon, defaults may be filled by the engine, and declared
input equality is not child-consumption verification.

The historical consumption receipts explicitly record epsilon, target delta and
epochs. They do not separately record constructor max_grad_norm: that mapping is
supported by the complete config, wrapper and active pinned call, together with
executed clipping evidence. It must not be described as a directly logged native
constructor value.

Do not create aliases. per_sample_max_grad_norm occurs only in commented-out
legacy dp_transformers code. The active upstream dataclass name is
max_grad_norm_dp, but the real formal manifest path ends max_grad_norm.
noise_multiplier is an active source argument and measured output, but no
such privacy.mechanism.params leaf exists in the reviewed formal manifest.

The orthogonal_noise example's delta1.5 is an additive hidden-state offset,
not fastDP target_delta. Its alpha/delta/safe_interval/orth_loss paths remain
separate MEDIUM candidates outside A4. Actual custom.privacy_method.*,
historical custom.privacy.alpha, and historical discover's explicitly declared
custom.privacy.max_grad_norm_dp remain custom paths. Accepted audit WARNING
does not imply a drift HIGH default or prove execution consumed the value.

The historical formal epsilon8→4 MEDIUM and train.yaml SHA HIGH records are
preserved, including all seven explained deltas. The already observed sigma
increase and finite epsilon/accountant outputs remain bound to that earlier
candidate. A future accepted policy needs a separate prospective gold supplement;
do not rewrite the old report or call it validation of a future candidate.

LOW/NONE remain available as exact drift_overrides in a resolved user profile,
before built-in defaults. Preserve that profile's existing content and use the
literal full path; privacy.* does not reach deep params and * is not recursive.
The inventory includes per-field LOW and NONE mapping examples and provenance.

Only public files and historical typed evidence were read. No product, test,
provider, GPU or network work was executed, credentials were not read, and no
repository or old evidence was changed. Physical machine paths are excluded
from the shareable inventory; its logical roots are repository and pinned-dp.
