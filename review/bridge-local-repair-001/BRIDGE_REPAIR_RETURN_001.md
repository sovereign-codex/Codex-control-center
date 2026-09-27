# BRIDGE_REPAIR_RETURN_001

**Disposition:** LOCAL REPAIR TESTS PASS; INDEPENDENT REVIEW PENDING.  
**Standing:** candidate, non-canonical, non-authorizing.  
**Scope:** the local synthetic specimen only. No Notion or GitHub changes.

## Observed result

The unchanged original suite passed 22/22 tests. The unchanged review suite,
which reproduced eight assertion failures and one uncontrolled exception against
the original code, now passed 9/9. Thirty added repair tests passed. Total:
**61 tests, zero failures, zero errors, zero skips; runner exit 0.**

`evidence/repair_run/test_report.json` binds the result to the exact code, test,
runner and fixture SHA-256 values. `evidence/repair_run/*.log` contains test output.
These are local observations, not an independent reviewer verdict.

## What changed

| Review finding | Local repair | Observed evidence |
|---|---|---|
| BTR-001: verifier/staging disagreement | Both call one pure selected-profile validator. Present permission checks remain separate. | R01-R04 reject the same invalid profiles; P02 checks historical read-back without renewing permission. |
| BTR-002: file existence treated as completion | Replay parses bounded records, rejects symlinks/invalid shapes, and binds them to exact claim/preparation bytes. | R05-R06 and record corruption, missing record, legacy record and collision tests pass. |
| BTR-003: deadline failure lost on replay | Preparation is distinct from completion. A completion outcome is published only after final preparation/read-back passes its deadline check. Late/failing paths remain held. | R07 reports `elapsed_budget`, then `delivery_held_elapsed_budget`. Added post-write/fault tests pass. |
| BTR-004: malformed nested inputs | Explicit nested type and metadata checks produce stable boundary errors. | R08 returns `fixture_input`; additional input and return-shape cases pass. |
| BTR-005: overflowed JSON numbers | The JSON float parser rejects non-finite conversions at every nesting level. | R09 and nested positive/negative overflow, NaN/Infinity tests pass. |

Only `candidate/bridge_specimen.py` changes the existing implementation.
`bridge_specimen.patch` shows that exact change. Original tests, review tests,
fixture and source manifest were copied byte-for-byte. The new test module and
runner are additive. The inherited crosswalk remains unchanged in `baseline/`.

## Timing boundary: explicit and still subject to review

The final monotonic check includes the packet copy, prepared record, pending
outcome-file write and its read-back. One no-overwrite local hard-link operation
then publishes the completion record. Publication is the local commit point.

**This is not a hard end-to-end deadline or preemptive cancellation guarantee.**
The publication syscall and return latency can take additional time after the
last check. Recording a failure is deliberately allowed after timeout. Independent
review must decide whether that timing boundary is acceptable for this specimen;
a live transport must define its own cancellation and uncertain-delivery contract.
No timing claim was upgraded into a remote execution guarantee.

## Exact preservation

The original candidate ZIP remained unchanged:
`0f60db42a77e8b739867c6877360aa46f317dc771753823630a34ecc119d5b22`.
The previous review ZIP also remained unchanged. All 15 original and 35 review
checksum entries were verified before and after repair.

A fresh process running the repaired verifier accepted the archived synthetic
packet/return under the selected fixture profile, and reproduced return digest:
`555212a8fbc342f981664d5e658ea7e76bb485b8e74f809f48af5e0e44122e7d`.
It explicitly reported no model execution, no renewed authorization, no Hall
receipt, no institutional acceptance, and no ready execution handoff.

Repaired implementation SHA-256:
`f45d26951092889c623b86f5e214100ebf8908f6054b643b698482cb402d81c2`.

## Scope and unproven boundaries

No live transport, Codex task, model call, provider provisioning, source-system
write, Archivist ingestion, TRACE receiver, or Hall recovery was performed.
No source repository was cloned, edited or tested in this repair pass. Referenced
contracts and PR standing are inherited, pinned baseline context, not fresh
workspace-state verification.

The tests run as one account/container and use a Python socket guard. They do not
establish hostile-worker isolation or an OS firewall. Injected I/O failures are
not power-loss tests. File fsync and local hard-link publication do not prove
parent-directory durability, distributed exactly-once delivery, authenticated
issuers, live grant revocation, signed evidence, or independent acceptance.

## Next gate

Independent technical review of this exact repaired package, including its timing
scope and local-record semantics. `INDEPENDENT_REVIEW_HANDOFF.md` provides the
entry point. The package is prepared for review; no reviewer has received or
approved it through this run. A clean review permits consideration of the next
explicitly authorized specimen, not automatic deployment or model integration.

**Live transport remains HOLD. No institutional standing changed.**