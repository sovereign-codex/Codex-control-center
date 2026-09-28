# Separate reviewer handoff: PR #14 projection repair

Review the files actually present under `review/bridge-local-repair-001/`.
This replaces the earlier ZIP-oriented handoff whose dependencies were missing
from GitHub. The original full archive is provenance, not a required download.

## Exact implementation

`candidate/bridge_specimen.py` SHA-256:
`f45d26951092889c623b86f5e214100ebf8908f6054b643b698482cb402d81c2`

The implementation, original tests, review regressions, repair tests, runner,
and fixture are unchanged from BRIDGE_LOCAL_REPAIR_001. Verify SHA256SUMS and
SOURCE_ARTIFACTS.json. Compare unchanged tests and fixture against `baseline/`.
Inspect `bridge_specimen.patch`, `REPAIR_DESIGN_001.md`, and the prior five
findings in `evidence/author_review_report.json`.

## Requested activity

Inspect first. Then, where your review environment supports safe scratch
execution, follow README.md to parse/apply the patch to a disposable baseline
copy, compare resulting bytes, and run the 61 tests. Provide no credentials;
disable network where supported. Add counterexamples only in reviewer-owned
scratch space. Do not modify the submitted candidate or push fixes.

If execution is unavailable, label the result STATIC_ONLY. Do not adopt the
author's test count as your own. If a required file is missing or a digest
differs, report NEEDS_INPUT or integrity failure before reviewing that claim.

## Challenges

- Static selected-profile conformance versus current execution permission.
- Exact claim, packet, preparation, and outcome bindings.
- Missing, corrupt, contradictory, symlinked, late, and partial records.
- Write, flush, read-back, failure-record and publication failure paths.
- Hard-link publication timing: deadline checks stop before the final syscall
  and return; a hard end-to-end time guarantee is NOT claimed.
- Native outcomes, exact raw return, no invented inference or receipt.
- Honest same-account, local-filesystem, and non-crash-durable limitations.

Return exact commit/source hashes, scope, tests personally run, findings with
file/line ranges and reproductions, and remaining limitations. Distinguish
package reproducibility, bridge logic, live suitability, and institutional
acceptance. A clean review is not merge/deployment authorization.

No repository writes beyond your review comments, provider changes, live
workflow dispatch, real inference, model installation, or promotion.
Live transport remains HOLD.
