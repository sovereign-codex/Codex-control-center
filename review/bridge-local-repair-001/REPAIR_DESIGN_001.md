# Repair design 001: local records, not a new institutional envelope

Status: local implementation candidate. The existing crosswalk is preserved.
This file describes only `candidate/bridge_specimen.py`.

## Static profile and current permission are separate

`validate_packet_profile(packet, profile_blob=PROFILE_BLOB)` has no clock, grant
service, filesystem writes, model call or routing decision. It applies the pinned
synthetic fixture profile: split model/envelope requirements, exact capability
set, synthetic sensitivity, no model/accelerator preference, retained ceiling,
teardown flag, supported input shape and bounded metadata fields.

`inspect_packet` first checks the separately supplied FixtureControl and exact
packet identity, then calls the pure validator. `verify_custody` validates exact
controller expectations and digests, then calls the same pure validator. The
verifier has no current permission grant. It can inspect valid historic evidence
without renewing a grant or requiring that its original expiry still be future.

The selected profile is code/caller configuration. The packet cannot select a
weaker profile. The default is the inherited repository blob identity. This does
not resolve institution-wide version migration; no source contract was changed.

The old controller expectation shape is retained (four keys). Unknown extra
fields are rejected. Profile selection belongs to verifier configuration, not an
untrusted expectation-file override. Historical full return bytes remain readable.

## Local stage records

`claim.json` retains the existing exact two-field identity/digest shape.
`delivered.json` is now a versioned PREPARATION record, not a completion verdict.
It carries packet ID/digest, exact claim digest, selected profile, and a strict
transport-only boolean. The name is retained for local test compatibility.

`outcome.pending.json` contains a proposed completion record, bound by SHA-256 to
those exact preparation bytes. Its existence never qualifies as completion.
The code exclusively writes and fsyncs it, reads it back, and performs the final
budget check. Only then does a no-overwrite hard link publish `outcome.json`.

The local commit point is that link publication. The pending name is retained;
there is no cleanup write after commit. Both names refer to the same inode on the
tested local filesystem. This is not immutable or tamper-resistant storage: a
same-account writer can mutate either alias. Replay validates what it reads.
Unsupported link publication fails closed; there is no silent filesystem fallback.

## Timeline

1. Check the test budget, source bytes, present test permission and static profile.
2. Exclusively create a job directory and its immutable intended claim.
3. Write/read back the exact packet, then check the budget.
4. Write/read back the preparation record, then check the budget (R07 checkpoint).
5. Write/read back the proposed completion record, then check the budget again.
6. Publish outcome.json without overwrite; return `delivered`.

If a BoundaryError occurs before publication, try to create `held.json` with a
stable reason and preparation-digest binding, then rethrow the original error.
No exception text, credentials or path inventory is retained. Even if the failure
record itself cannot be written, the unpublished outcome means replay stays held.
Corrupt or partial files are not overwritten, deleted or automatically repaired.

The whole process is single-writer and local. The deadline is checked through
preparation immediately before publication. A finite check cannot preempt a later
blocking syscall. The syscall and function-return latency have no hard bound here.
This limitation is an explicit review item, not a total-time guarantee.

## Replay is observation, not redelivery

Replay verifies the claim, preparation record, actual packet bytes and completion
record. A held record takes precedence over apparent completion. Missing, corrupt,
contradictory, over-budget or symlinked records return a stable BoundaryError.
A fully prepared but unpublished decision is still `interrupted_hold`.

No replay writes, timeout retries, provider substitutions or action dispatches
are admitted. `duplicate_suppressed` is reserved for a conforming, published local
completion record and identical packet bytes. A same-ID/different-payload request
remains an identity collision. The current fixture permission is still checked
before staging/replay. Standalone historical verification is a separate function.

Early failures can leave incomplete claims or preparation records. In those cases
replay may report a structural/interrupted hold rather than the original reason;
partial artifacts and any held record remain available for diagnosis. Success is
not inferred from partial evidence.

## Exact bytes and claims

Hashes prove integrity only relative to independently trusted expectations, not
source honesty, authentic identity or factual truth. The controller is synthetic
trusted test input. The record digests are local correlation/custody metadata, not
signatures. Mutating both content and trusted expectations is outside this model.

Return collection remains an opaque byte-copy operation. Standalone read-back
reports byte and fixture-profile checks only; it does not infer timely delivery
from custody, inspect a live authorization service, or grant institutional standing.
Native executor complete/partial/refused/failed outcomes remain unchanged; no
inference status translation or CIT/TRACE/Archivist integration is implemented.

The deterministic return builder intentionally accepts enough shape to generate
negative-test data from profile-invalid packets. It is not a profile acceptance
entry point. Its output is always marked `none:deterministic-fixture`.

## Error hardening

Inputs, expected metadata, return statuses, model-output shape and timestamps are
checked before field access. Strict boolean checks do not accept JSON number 1 as
true. The JSON float parser rejects overflow such as 1e999, including inside nested
arrays/objects; literal nonstandard constants and duplicate keys remain rejected.
This is a narrow JSON fixture profile, not a general schema-validation service.

## Explicitly absent

No directory fsync / power-loss proof, OS sandbox, hostile-process isolation,
concurrent-writer proof, remote exactly-once contract, signed acknowledgements,
authentication service, live revocation, live worker registration, code-writing
permission, model runtime, Notion binding, Office awakening or institutional receipt.
No synthetic fixture may be placed in a live incoming/dispatch path by this package.
