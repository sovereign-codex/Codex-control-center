# Control Center handoff integration 001

**Standing: disabled workflow integration for draft review.**

This change implements one explicit Router → Dispatcher → AVOT-engine transport contract inside Control Center. The checked-in policy has `enabled: false`, no admitted senders, and `receiver.compatible: false`. Both workflows therefore record a hold before the GitHub App token step. No live receiver or credential capability is established by the tests.

The review builds on [PR #21](https://github.com/sovereign-codex/Codex-control-center/pull/21), commit `4ff3b9ab14ecb8582c6129252424ac677ac0f9db`. Its original 16-file local candidate and evidence remain unchanged. The Control Center production baseline remains `4a5def9816bdb6c771559f3105558578edd284c1` until an independently considered merge.

## What changes

| Surface | Implemented behavior |
|---|---|
| `control-center-router.yml` | Retains `route-event` ingress. Reads the Actions event file through Node, validates an explicit destination and caller identity, and prepares a complete `engine_handoff` wrapper. |
| `cross-repo-dispatch.yml` | Retains `engine_handoff` ingress. Requires a separately admitted sender and a persisted Router claim matching the actual received request before preparing one `avot_execution` attempt. |
| `scripts/handoff/normalization.mjs` | Pure normalization derived from the reviewed candidate; no fake transport, ledger, filesystem, or credentials. |
| `scripts/handoff/contract.mjs` | Pure preparation, versioned metadata, sender policy, semantic identity and binding, and payload limits. |
| `scripts/handoff/executor.mjs` | Create-only claim, at most one transport attempt by its verified winner, and a separate create-only outcome. |
| `scripts/handoff/github-service.mjs` | Real GitHub HTTP adapter with fixed endpoints, bounded reads, timeouts, exact blob verification, and no retry or overwrite. |
| `scripts/handoff/run.mjs` | Actions entry point; fresh preparation before credential access, fixed evidence paths, and explicit unsuccessful exits for holds and unverified outcomes. |
| `config/control-center-handoff.json` | Checked-in disabled policy and empty sender bindings. Payloads and environment variables cannot enable it. |

The workflow source no longer places event values in shell script text, output filenames, commit messages, or environment-file assignments. Its only step output is the boolean `ready`. GitHub describes why expression substitution inside shell source can permit [script injection](https://docs.github.com/en/actions/concepts/security/script-injections).

This is a deliberate migration to one reviewed edge. The old substring-based routing and broad destination map are removed in these proposed workflows. Missing request IDs, unknown routes, Tyme-Lab, contradictory destinations, failure-bearing statuses, and other unsupported inputs hold. Legacy `route-event` remains supported; this change does not introduce `route_event` or repair the separate result receiver.

## Wire contract

| Meaning | Value |
|---|---|
| Router ingress | `route-event` |
| Immediate repository and event | `sovereign-codex/Codex-control-center` / `engine_handoff` |
| Final target | `avot-engine-runner` |
| Declared final repository and event | `sovereign-codex/AVOT-engine` / `avot_execution` |
| Contract version | `ccc-handoff/1` |

The caller supplies `request_id` at the root of `client_payload`, whether its producer event is direct or wrapped. Any `event.request_id` declaration must agree. IDs use 1–128 ASCII letters, digits, dots, underscores, colons, or hyphens, beginning with a letter or digit. There is no trace-ID, run-ID, clock, UUID, or diagnostic fallback.

Required producer fields retain the reviewed legacy profile: trace ID, repository, workflow, status, and a real timestamp with explicit timezone. Consistent canonical repository/workflow aliases are accepted. Wrapper fields cannot substitute for absent producer provenance. Optional rich `payload`, `governance`, and `runtime_packet` objects and extensions are preserved; conflicting declarations hold. Producer status and timestamp are never replaced with transport observations.

Both outgoing dispatches use a four-property `client_payload`:

```json
{
  "target": "avot-engine-runner",
  "request_id": "caller-assigned-request-id",
  "event": { "...": "complete normalized producer event" },
  "_ccc_handoff": { "...": "versioned Control Center metadata" }
}
```

Original wrapper extensions move into `_ccc_handoff.wrapper_fields`; their values are retained. The entire normalized event remains under `event`. This bounded outer shape avoids the provider's limit on top-level payload properties. Preparation rejects a full request body above 60,000 UTF-8 bytes, conservatively below GitHub's [repository-dispatch limits](https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event).

`_ccc_handoff` is reserved at the producer wrapper/event root. Router adds the source identity, origin sender, policy and content digests, Router fingerprint, deterministic claim key, source-event annotation origin, preserved wrapper fields, and Router observation. Dispatcher validates that exact structure and adds its own claim key, fingerprint, admitted sender, and observation. Unknown control structure is rejected rather than guessed.

## Identity and evidence

The stable request key is SHA-256 over canonical JSON of:

```json
["ccc-request-identity-v1", "<stage>", "<lowercase-source-repo>", "<source-workflow>", "<request-id>"]
```

Stage distinguishes the Router and Dispatcher claims. Contract version belongs in the binding, not the key; an implementation-version change must not create a new namespace that silently permits replay.

The binding covers contract version, stage, source identity, canonical input digest, complete normalized content, fixed route, admitted sender ID, and the checked-in policy digest. Dispatcher also binds the Router fingerprint. Reusing a key with changed admitted content or policy is a collision.

| Evidence | Exact boundary |
|---|---|
| `actions_event_file_sha256` | Exact bytes read from this runner's `GITHUB_EVENT_PATH`. |
| `client_payload_canonical_sha256` | Canonical serialization of the parsed payload observed at this stage. |
| `source_input_sha256` | Router's canonical input digest, carried and checked through the claim chain. |
| `normalized_content_sha256` | Complete normalized event, target, and preserved wrapper fields. |
| `outbound_request_sha256` | Canonical request object, including destination repository and complete dispatch body. |

GitHub has already parsed the caller's API request. Its original wire whitespace, duplicate-key spelling, or raw body bytes cannot be recovered from an Actions event. This integration explicitly changes the candidate's local raw-JSON identity rule to a canonical observed-payload binding. Whitespace-only differences in the Actions file remain different observation hashes without becoming different semantic requests.

Run IDs, attempts, observation time, and the full Actions-file hash are excluded from the semantic duplicate binding. They remain in evidence and in the particular outbound request. Thus a redelivery can be recognized across Actions runs even when those observations differ.

## Sender authority

Router admits only a policy entry matching the GitHub-supplied sender ID and the declared producer repository/workflow. Dispatcher has a separate sender-ID list. A producer's Router admission does not automatically admit it to Dispatcher.

These are **policy-bound producer declarations**. An admitted GitHub principal, especially a shared App, does not independently prove execution of a named source workflow. Results retain `producer_workflow_execution_verified: false`. The shipped lists are empty; this review does not invent an App-to-producer binding.

Dispatcher does not trust a carried digest or claim key by itself. It derives a fixed Control Center ledger path, reads the Router claim, verifies its canonical bytes and Git blob SHA, and compares identity, binding, observation, and the complete actual incoming request digest. A plausible altered observation therefore fails even if its structural fields look valid.

The handoff carries a deterministic claim key, not the Router claim blob SHA. This avoids a circular dependency between the claim's stored request hash and the request's claimed blob identity. Dispatcher records the fetched Router claim SHA in its own evidence.

## Durable claim and outcome behavior

Claims live at fixed paths in the existing Control Center repository on `main`:

```text
handoff-ledger/v1/<router-or-dispatcher>/<identity-key>/claim.json
handoff-ledger/v1/<router-or-dispatcher>/<identity-key>/outcome.json
```

The production adapter uses the [Contents API](https://docs.github.com/en/rest/repos/contents). Every write omits `sha`, which is required to replace existing content. This client therefore creates records only. Only HTTP `201` with the exact expected Git blob SHA admits a transport attempt; optional returned commit SHAs are retained in persistence evidence.

| Situation | Result |
|---|---|
| Verified new claim | One dispatch attempt may follow. |
| `200`, `409`, `422`, malformed `201`, timeout, or other claim ambiguity | No dispatch. Read existing state to classify it; never infer duplicate from a status code alone. |
| Valid existing claim, same identity and binding | Duplicate; preserve the previous outcome if verifiable. |
| Existing identity, different binding | Collision; no second attempt. |
| Existing claim without a verifiable outcome | Duplicate with outcome unknown; no resume or retry. |
| Verified HTTP `204` from dispatch | Transport accepted; execution remains unverified. |
| Other verified HTTP response | Transport rejected; outcome retained. |
| Transport exception, deadline, redirect, or unverifiable response | Transport uncertain; no retry. |
| Accepted transport but failed outcome write | Acceptance remains recorded locally, persistence is marked failed, and the workflow exits unsuccessfully. |

Each stage has its own claim. Dispatcher verifies Router admission before attempting its own claim. It does not require the Router outcome to be present: delivery can reach Dispatcher before Router records its HTTP response. The verified claim establishes admitted content, not proof that a particular Router run dispatched or executed anything.

There is no expiry, overwrite, reclaim, automatic retry, or automatic recovery of reserved requests. A crash after claim creation can suppress a request that was never sent. This conservative tradeoff avoids a second attempt when the first attempt's result is uncertain. Operators must inspect such cases; changing an ID to bypass an unresolved reservation is not an automatic recovery policy.

Durability depends on GitHub's create/read behavior and on repository writers preserving these records. Git object identity and this client's create-only behavior do not establish immutable institutional custody or remote exactly-once execution. Cross-run concurrency is tested with an injected atomic fake; a live atomicity/permissions probe has not been performed.

Preparation holds make no service calls and do not reserve remote identities. Their evidence is retained as workflow artifacts. This differs from the local specimen's in-memory reservation of some complete-identity holds; a rejected or unauthorized event must not gain a repository-write side effect merely by supplying identifiers.

## Workflow observations and token scope

Both workflows check out the event commit and re-run preparation immediately before execution. They do not accept a saved prepared JSON file as authority. The in-process prepared object is frozen and branded; a fabricated or modified object is rejected by the executor.

App tokens are requested only after successful preparation. Router's requested scope is Control Center; Dispatcher requests AVOT-engine alone. Ledger operations use the workflow's existing `contents: write` token. No new cloud resource, permission widening, broad destination map, TRACE dispatch, or raw-payload Git push is introduced.

The HTTP adapter fixes the API host and allowable repository/event pairs. It rejects redirects, caps record/response sizes, and applies a single 15-second deadline through response reading. Strict JSON parsing rejects nesting beyond 64 levels before recursive validation or hashing. Original HTTP error text and credential values are not included in its errors.

The CLI retains exact event bytes, observations, preparation, and outcome reports at fixed stage paths. The workflows request 30-day artifact retention; actual availability also depends on repository policy and later deletion. These artifacts are operational evidence, not permanent institutional receipts. A successful execution exit requires accepted transport plus a verified outcome write; it never means receiver execution completed.

The four external action revisions are pinned to verified Git commits and use Node 24. The implementation and tests use Node built-ins; no application dependency installation is required.

## Validation and reproduction

Recorded results and input hashes are in [the integration evidence directory](../review/control-center-handoff-integration-001/). The independent suite exercises the real contract, executor, and HTTP adapter with injected service/fetch responses. It does not import the fake review harness into production.

From the repository root on Node 24:

```sh
node --test --test-isolation=none --test-reporter=tap tests/handoff/*.test.mjs
```

Tests cover disabled/unauthorized zero-call holds, explicit identity, complete content, status failures, inert shell/prototype values, payload bounds, stable cross-run duplicates, atomic fake races, collisions, malformed claims, uncertain outcomes, persistence failures, and verified versus forged Dispatcher chains. Separate CLI smoke checks cover prepare/execute for both stages under the shipped disabled policy, using a forbidden-network guard.

## Why activation remains held

The [receiver review](CONTROL_CENTER_HANDOFF_RECEIVER_REVIEW.md) pins AVOT-engine main at `dea4b3f0c05334f8abd33ac4c2abae76b094e6f4`. Its `avot_execution` workflow reads three fields, discards the event, sleeps, writes `completed`, and sends a sparse `avot_result` callback. Rich inference code exists elsewhere but is not connected to that listener.

Before enabling this route:

1. Review a receiver that safely preserves the four-key envelope and emits an attributable receipt while keeping execution unverified unless separately established. A model call is not required merely to prove transport and receipt.
2. Enforce the expected receiver version before effects. `receiver.verified_commit` is a review pin; `repository_dispatch` itself does not select that historical commit.
3. Establish actual sender-to-producer and Dispatcher admission policy, including the explicit caller request-ID source. Existing five-field callers without an ID will hold.
4. Verify current credential scope, ledger write/read behavior, and the receipt binding in a separately authorized bounded probe.
5. Correct the separate completion/return path before using it as acceptance evidence. HTTP acceptance or a receiver's synthetic `completed` value cannot substitute.

This draft completes the Control Center contract implementation and its local verification while preserving those unresolved prerequisites as explicit holds.
