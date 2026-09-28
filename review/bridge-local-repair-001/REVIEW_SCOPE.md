# BRIDGE_LOCAL_REPAIR_001: reproducible review projection

Standing: non-canonical review candidate. PR #14 remains unmerged.
This pass repairs review packaging only; no bridge logic was changed.

## Two prior P1 staging findings

1. The staged patch lacked its final LF. Regeneration from the exact archived
   baseline and candidate produces the original valid patch byte-for-byte.
   The previous remote blob equals that patch with only its final LF removed.
2. The handoff required files not in the repository. This projection includes
   the repaired implementation, baseline, original/review/repair tests, runner,
   synthetic fixture, subset-specific checksums, provenance, and test reports.
   README.md and the handoff now reference only included review dependencies.

## Review targets

Primary: candidate/bridge_specimen.py and candidate/test_*.py.
Comparison: baseline/ and bridge_specimen.patch.
Evidence: SOURCE_ARTIFACTS.json, SHA256SUMS, evidence/*.json.
Design: REPAIR_DESIGN_001.md.

The full historical archive is not staged; omitted duplicates and old logs are
not needed for the documented 61-test reproduction. Exact archive-member
mappings distinguish copies from newly adapted projection documentation.

The author's local rerun is evidence, not independent approval. Ask a separate
reviewer to reproduce checks where execution is available and challenge logic.
Do not close findings merely because files now exist or tests pass.

All files stay under this review directory. No runtime/CI wiring, source
contract edits, live incoming/queue paths, provider configuration, model calls,
Office awakening, ingest/receipt, merge, or deployment is part of this change.
Existing automatic repository services are not reconfigured by this package.
