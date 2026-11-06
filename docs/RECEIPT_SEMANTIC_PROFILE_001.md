# Frozen receipt and external custody profile

Semantic profile: `tyme-receipt-semantics/1`.
Portable package: `tyme-evidence-package/2`.
Receipt serialization stays `office-codex-receipt/1`; profile metadata identifies stricter acceptance without rewriting existing receipt bytes. Repository adoption of this profile remains a review decision, not an assertion of canonical standing.

## Receipt timing

The receipt is a frozen review snapshot. It may record an incomplete lifecycle as HOLD evidence; it is not a mutable job-state record. For a completed snapshot, runtime and Office review occur before canonical receipt persistence. `transport.evidence_stored` describes the returned task evidence, not the subsequent persistence of the receipt itself.

After sealing, preserve its identity and bytes. Later persistence and readback observations are separate records referencing its receipt ID and content digest. This avoids embedding the commit/blob identity of a receipt's own eventual bytes within those same bytes.

Both legacy embedded fields must be explicitly null in sealed receipts under this profile: `repository_receipt: null` and `notion_readback: null`. The builder supplies null defaults; validators reject missing placeholders and all non-null embedded custody, including formerly accepted well-shaped objects. Do not edit a legacy signed/hashed receipt to satisfy this rule. Preserve it as legacy evidence and review migration separately.

External envelopes continue using the bridge's existing comparisons: receipt identity, repository/path, persistence commit/blob, reconstructed content, observation time, declared independence and no authority effect. These are consistency checks. No persistence writer, authenticated observer mechanism, or institutional readback service is implemented here.

## Shared rules

- Required strings are trimmed, nonempty, at most 1,024 JavaScript UTF-16 code units, and exclude ASCII control characters (including newline and DEL).
- Evidence, assumptions and uncertainty contain valid strings; evidence references are nonempty.
- Task repository and SHA are both present or both absent/null; supplied SHA is exact lowercase 40-hex.
- Unknown fields are rejected in the receipt and specified nested semantic objects.
- Lifecycle booleans are explicit and ordered. Completed review requires all stages; PASS cannot accompany incomplete review.
- Authority remains READ_ONLY; executor standing and institutional effect remain none; Hall and Canon claims remain false.
- Digest/receipt identity checks are separate from pure semantic checks. Repository `verifyReadback` now requires all three.
- The builder calculates receipt identity and digest and copies nested content so later mutations to its input cannot alter the returned receipt. JavaScript callers must still treat the returned object as immutable; mutating it invalidates the digest.

## Compatibility changes

The raw receipt version is preserved for matching canonicalization and baseline digest. The stricter semantic profile is separately named. Code that previously relied on digest-only `verifyReadback`, unknown fields, long strings, loosely typed evidence, or embedded custody must be reviewed. Most error codes are not API-compatible with the old builder; authority and institutional-effect codes used by its existing tests are retained. This is a review-only integration, not a drop-in compatibility claim.

Package v2 includes `semantic_profile` and `source_role: baseline_reference_only`. Its source head names the reviewed baseline repository, not the candidate implementation. Version 1 packages and mismatched profiles are rejected explicitly. No old package is re-labelled as passing the new profile.

## Remaining gates

1. Review and adopt the profile/custody decision.
2. Require the complete handoff suite on the exact reviewed commit. CI now explicitly checks out and verifies the pull-request head SHA, rather than the temporary merge SHA.
3. Independently review the final changes, including persistence semantics and callers of `verifyReadback`.
4. Identify a real canonical receipt and external custody/readback locations before authenticated retrieval can be tested.
5. Any live rehearsal remains separately scoped and authorized.

## Maintaining the shared source

Edit `scripts/handoff/receipt-semantics.js`, then regenerate `receipt-semantics.mjs` as the same bytes plus `\nexport {TymeReceiptSemantics};\n`. The handoff suite checks this byte equality. The companion offline console package embeds the same source; its browser tests are a separate validation surface.

`tests/fixtures/receipt-semantic-vectors.json` carries the shared acceptance vectors. Two prior tests intentionally change from accepting embedded custody to rejecting it under this profile. No handoff policy, destination binding, credential, or transport activation is changed.
