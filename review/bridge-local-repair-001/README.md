# Review Projection Repair 01

This is the reproducible review subset of BRIDGE_LOCAL_REPAIR_001, staged only
under `review/bridge-local-repair-001/` on PR #14. It is not a deployed bridge.
Start with `REVIEW_SCOPE.md` and `INDEPENDENT_REVIEW_HANDOFF.md`.

The original archive remains unchanged. `SOURCE_ARTIFACTS.json` identifies the
exact archive members copied here. Duplicate historical packages and unrelated
logs are omitted. The manifest here covers this projection, not all 99 original
archive entries. No absent archive is needed for the checks below.

## Reproduce in a Linux review sandbox

Use Python 3.10 or later (standard library only), Git, and ordinary POSIX tools.
Inspect code first. Run without credentials, with network disabled by the host
where available. The tests' Python socket guard is not an OS firewall.

From this directory, run the following as one block. It does not edit candidate
or baseline files. Patch application and test output go to a new scratch folder.

```sh
set -eu
sha256sum -c SHA256SUMS
cmp candidate/test_bridge_specimen.py baseline/test_bridge_specimen.py
cmp candidate/test_review_regressions.py baseline/test_review_regressions.py
cmp candidate/fixtures/packet.json baseline/fixtures/packet.json
git apply --numstat bridge_specimen.patch
PROJECTION="$(pwd -P)"
SCRATCH="$(mktemp -d)"
cp baseline/bridge_specimen.py "$SCRATCH/bridge_specimen.py"
( cd "$SCRATCH"
  git apply --check -p1 "$PROJECTION/bridge_specimen.patch"
  git apply -p1 "$PROJECTION/bridge_specimen.patch"
)
cmp "$SCRATCH/bridge_specimen.py" candidate/bridge_specimen.py
( cd candidate
  python3 -B run_tests.py --output-dir "$SCRATCH/test-results"
)
printf 'Reviewer output: %s\n' "$SCRATCH/test-results"
```

The author's observed count is 22 original + 9 review + 30 repair = 61. Report
your own outcome, including skips/errors and exact reviewed commit and hashes.
`evidence/author_test_report.json` is historical;
`evidence/projection_test_report.json` records this projection's local rerun.
Neither is independent reviewer approval.

`baseline/` contains intentionally unfixed code for comparison; do not deploy it.
Do not run its red regression file directly without explicitly setting
BRIDGE_CANDIDATE_DIR and BRIDGE_REVIEW_OUTPUT to appropriate scratch locations.
The candidate runner handles the intended imports and output location.

A valid digest identifies bytes, not authority, authenticity, or code correctness.
No merge, live transport, model invocation, provider operation, dispatch, Office
awakening, Archivist/TRACE/Hall receipt, or promotion is granted here.
