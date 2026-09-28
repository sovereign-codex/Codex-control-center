# BRIDGE_LOCAL_REPAIR_001: repository projection return

This document describes Review Projection Repair 01, not a new implementation
repair. The earlier GitHub projection was incomplete and lost the patch's final
newline. Both defects were introduced in staging, not in the preserved archive.

The implementation remains SHA-256
`f45d26951092889c623b86f5e214100ebf8908f6054b643b698482cb402d81c2`.

The patch was regenerated from retained original/repaired bytes and is identical
to the valid archived patch. It parses, passes git apply --check, applies to a
scratch baseline, and produces exactly the candidate's bytes. Original tests,
review regressions, and fixture still match their included baseline copies.

The current local projection rerun passed all 61 tests without skips, failures,
or errors. See evidence/projection_test_report.json for exact source hashes,
environment, and timestamp. This is still author-side reproduction, not an
independent review verdict. The historical 61-test result and earlier five
findings are separately preserved as author_test_report.json and
author_review_report.json in evidence/.

The repository-facing README, scope, and reviewer instructions are adapted to
this dependency-complete subset. SOURCE_ARTIFACTS.json identifies all exact
archive copies; SHA256SUMS is a new projection-only manifest. No absent archive
is required to reproduce the documented checks.

The original archive is unchanged. Neither local test success nor corrected
packaging establishes authenticated live transport, hostile-worker isolation,
power-loss durability, signed evidence, actual provider teardown, or
Archivist/TRACE/Hall acceptance. The hard-link publication syscall and return
remain outside the deadline check's end-to-end guarantee.

GitHub review staging is the only authorized external change in this pass.
No bridge implementation changes, merge, model execution, deployment, live
dispatch or institutional promotion. Request review of the new exact commit.
Live transport remains HOLD.
