# R07-C finite proposal scope clarification

The proposed A changes only the named branches of six rules. Existing qualification
contracts remain: an unreadable or invalid pyproject may still yield the original
missing-qualified-manifest CRITICAL when no other witness exists and listing did
not fail; an unreadable requirements closure is still not a qualified lock.
Captured format-lock presence remains a presence witness even if its body failed.
Those bounded outcomes concern qualified captured evidence, not proof that a
physical source file is absent. The new contract does not turn every body gap
into SKIP for every presence rule.

The Makefile correction to the independent existing-contract shell repair is not
a new six-rule policy. The pending implementation patch remains frozen; any
mechanical rebase onto that corrected baseline must preserve all nine proposed
policy postimages except the separately justified existing-contract Makefile
mode fix, with its own source/test commit and independent rebase qualification.
