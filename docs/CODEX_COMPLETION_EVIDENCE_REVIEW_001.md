# Codex completion evidence — review candidate 001

Standing: PREPARED / OFFLINE ONLY / NON-AUTHORIZING.
Baseline: `7492b95f3a8268488ea6df1ed2cebae048cf2447`, Control Center PR #29.

## Finding

The baseline transport classifier sets `completion_verified` from the string
`body.status === 'completed'`, including when `body.id` is missing. It has no
expected task/session/request/source context or freshness input. The lifecycle
classifier recognizes event types only. The receipt validator checks structure,
ordered flags, identity/digest integrity and authority ceilings; it does not
authenticate the observations used to populate those flags.

`correlationFor` already binds request/Office/destination/source into a digest.
`runtimeCorrelation` can retain session/task IDs. Neither is consulted by the
baseline completion classifier. `request_fingerprint` is request construction
metadata, not proof that the observed task executed that request or source SHA.

## Smallest safe correction

1. Transport classification always returns `completion_verified: false`.
   Preserve reported state; require a session ID for its reported terminal flag;
   HTTP 202 cannot mark `runtime_completed`, even if its body says completed.
2. Add one pure `checkCodexCompletionEvidence` helper in the existing adapter.
   It checks a normalized task observation against independently retained
   expected context. No network, storage, credentials, clock read, dispatch,
   provider API schema, new service or registry is introduced.
3. Keep receipt semantics, serialization, identity, custody and policies unchanged.

A helper result `valid: true` means only that declared identity and timing
data match. Its `completion_verified` remains false. Do not convert this result
or a reported terminal state into an authenticated completion claim.

This tightens the previous proposal: a matching session ID alone cannot establish
completion of the right task, request or revision, nor authenticate an observer.

## Local input contract

The caller must retain expected context independently of the evidence:

```js
expected = {
  request_id, correlation_sha256,
  session_id, task_id,
  repository, sha,
  started_at
};
evidence = {
  request_id, correlation_sha256,
  session_id, task_id,
  repository, sha,
  kind: 'codex_task_completion',
  status: 'completed',
  completed_at, observed_at, evidence_ref
};
checkCodexCompletionEvidence({ expected, evidence, now, max_age_ms });
```

All listed fields are required and unexpected fields fail closed. This is a local
normalization boundary, not a claim that an OpenAI endpoint returns these fields.
Native task/turn identifiers and provider evidence must be mapped from actual
documented observations. Do not invent a task ID or obtain expected context by
copying the completion evidence.

The identity tuple must match exactly, including repository and a lowercase
40-hex Git SHA. `correlation_sha256` is a full lowercase 64-hex digest, not a
truncated key. This helper compares retained digests; it does not independently
reconstruct/authorize the original assignment or prove the repository checkout.

The caller supplies its trusted observation/check clock and explicit age policy.
Require `started_at <= completed_at <= observed_at <= now`. Both completion
and observation must be within `max_age_ms` of now. Re-observing old completion
must not refresh it. RFC3339/calendar validation reuses `validTimestamp`;
comparisons have JavaScript millisecond precision. Missing timing/policy context
fails closed. No arbitrary default freshness duration is introduced.

No normalized object is appended to or embedded in a sealed receipt. Retain
underlying evidence separately and reference it through existing evidence refs
only after separate custody/authority review. Subsequent custody observations
continue to use external envelopes; do not change receipt bytes after sealing.

## Still not established

A live authenticated completion observer, provider contract/access, checked-out
source proof, task-result/effect verification, provider orchestration wiring,
durable receipt persistence, authenticated readback and independent Office review
remain absent. No existing disabled route is enabled by this code.

Receipt integrity can prove consistent frozen bytes; it cannot prove the truth
of an executor's completion declaration. This patch deliberately does not change
`tyme-receipt-semantics/1` to make an unsupported authentication claim.

## Compatibility and tests

The one baseline test that equated a reported completed session with verified
completion is corrected to require false while retaining reported state. The
other 106 baseline tests remain unchanged. All 107 baseline-group tests pass on
the candidate; 62 additional adversarial/data-boundary tests pass, 169 total.

The new tests cover matching synthetic data without authentication, mismatched
session/task/request/correlation/repository/revision, missing and malformed
identities, pre-assignment/expired/re-observed stale completion, missing/invalid
time context, transport masquerading as task evidence, raw lifecycle events,
HTTP 200/201/202/204 false verification, and nonmutation of retained inputs.

Run from the candidate repository root:

```sh
node --test --test-isolation=none tests/handoff/*.test.mjs
```

No new test makes a provider call or executes an agent. Review the local patch
before any repository adoption. Passing these tests authorizes no live proof.

