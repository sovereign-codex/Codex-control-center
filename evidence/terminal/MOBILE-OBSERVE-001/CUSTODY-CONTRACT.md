# Proposed custody protocol: TYME-MOBILE-OBSERVE-001

**Status:** Proposed only. Not an approved operational transport or cryptographic attestation.

The minimum durable-custody upgrade is an append-only record of raw bytes, plus independently verifiable observers. Do not retrofit authority into a local receipt.

1. **Freeze source bytes:** Preserve the uploaded OBSERVE JSON unchanged. Keep its raw file SHA-256 distinct from the schema's canonical self-digest.
2. **Preserve continuity dependencies:** Obtain and hash the original WAKE receipt bytes. Check its canonical digest against the prior_receipt reference. Do not regenerate a copy from a transcript and claim it was the original.
3. **Introduce an external, immutable checkpoint:** Publish a candidate evidence manifest under a new review branch or append-only object prefix with create-only semantics. No rewrite of prior identifiers or evidence.
4. **Obtain genuinely independent readback:** From a separate network/runtime, retrieve each published object and compare the raw hashes. Persist request metadata, retrieval coordinates, failure cases, and response bodies when permissible.
5. **Preserve historical distinctions:** Exact GitHub commit existence is confirmed by a separate readback. Historical branch-head ownership/time and public Hall content digest are not independently attested by the packet.
6. **Establish actor trust separately:** Only an approved identity and signer-key policy, external timestamps, and optional third-observer checkpoints could upgrade custody. Hash agreement by itself cannot do so.
7. **Gate operational status:** Require two independent readers, verified custody checks, zero contradictory source claims, and explicit steward approval before any institution-facing integration. This terminal never dispatches or authorizes AVOTs.

### Proposed repository layout (not applied)

```text
evidence/terminal/MOBILE-OBSERVE-001/
  original-observe-receipt.json
  verification-results.json
  evidence-manifest.json
  review.md
  witness/  # only after actual independent execution
```

### Negative acceptance checks

- Changing original receipt bytes without updating the external raw hash fails the packet manifest check.
- Changing a receipt body without recomputing its canonical digest fails the local receipt checker.
- Rehashing a receipt that asserts dispatch, false summary counts, or unsupported Office readback must still be rejected by the schema/invariants.
- A rehashed but otherwise permissible observation *can* pass local checks: it must not be accepted as external provenance without a source-authenticated witness.
- Missing original WAKE bytes remain a chain gap, not a passing full-chain check.
- An absent or mismatched independent Hall replay remains pending; do not substitute page summaries for exact decoded response bytes.
