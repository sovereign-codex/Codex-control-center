# Local handoff contract

`control-center-handoff-review/1` is a narrow legacy compatibility profile implemented by [candidate/adapter.mjs](candidate/adapter.mjs). It covers normalization and one in-memory fake Control Center request. It does not implement the complete repository routing-envelope schema, wire production workflows, authenticate a producer, or execute the declared destination.

## Input API

Both `normalizeHandoff(input)` and `createReviewHarness(options).run(input)` accept an object with the following fields. Null and other non-object API inputs return a structured `invalid_input` hold.

| Input | Requirement |
|---|---|
| `requestId` | Explicit caller-supplied local request identity: a nonempty string without leading or trailing whitespace. |
| `rawJson` | JSON text whose root is an object. The exact supplied string is retained and hashed as UTF-8. |
| `ingressEventType` | Exactly `route-event`. This profile does not silently accept `route_event` or `engine_handoff` as ingress aliases. |
| `routeDecision.stage` | Exactly `cross-repo-dispatcher`. |
| `routeDecision.target` | Exactly `avot-engine-runner` for the admitted fixture. |
| `routeDecision.targetRepo` | Exactly `sovereign-codex/AVOT-engine` for the admitted fixture. |
| `routeDecision.receivingEventType` | Exactly `avot_execution` for the admitted fixture. |

`routeDecision` must be JSON data. Its complete value is preserved as evidence. The decision cannot invent a destination omitted from the producer input.

The JSON supports two shapes:

```json
{
  "target": "avot-engine-runner",
  "trace_id": "trace-example-001",
  "repo": "sovereign-codex/AVOT-ARCHIVIST",
  "workflow": "archivist-dispatch",
  "status": "received",
  "timestamp": "2026-10-17T16:42:00-07:00"
}
```

```json
{
  "target": "avot-engine-runner",
  "event": {
    "trace_id": "trace-example-001",
    "repo": "sovereign-codex/AVOT-ARCHIVIST",
    "workflow": "archivist-dispatch",
    "status": "received",
    "timestamp": "2026-10-17T16:42:00-07:00"
  }
}
```

An `event` member always selects the wrapped profile and must contain an object. An explicit `target` may occur in the wrapper, event, or both; all declarations must agree with the route decision.

## Producer evidence and normalization

The five legacy producer fields are required: `trace_id`, `repo`, `workflow`, `status`, and `timestamp`. `source_repo` may replace `repo`, and `source_workflow` may replace `workflow`. When both aliases occur, they must agree. A declared legacy `source` must also agree with the admitted repository identity; `source` alone cannot replace the required `repo`/`source_repo` declaration. Every declared identity, status, and timestamp value must be a nonempty, unpadded string.

For a wrapped input, these requirements must be met inside `event`. Wrapper-level declarations can corroborate or contradict producer fields; they cannot substitute for missing producer evidence. No local diagnostic identity, clock value, or wrapper value is used to fill missing producer provenance.

Normalization preserves the producer event and adds consistent `repo`/`source_repo` and `workflow`/`source_workflow` aliases. A producer-declared `source_event` is preserved. If absent, the event receives `source_event: "legacy"`, with evidence explicitly labeling this as `legacy_profile_annotation`, not an observed source event. A wrapper-only `source_event` holds instead of supplying producer evidence or silently becoming a legacy annotation. Producer identity always remains declared and unauthenticated.

The normalized wrapper carries the final `target`; the event's `target` control field is removed from its normalized copy. Original text remains in `evidence.raw_json`. Event extensions survive. Wrapped extensions survive in the recorded request. Optional `payload`, `governance`, and `runtime_packet` must be objects when supplied. Wrapper-only rich fields are also copied into the normalized event. Duplicate rich declarations must be structurally equal; contradictions hold rather than choosing a preferred value.

Timestamp validation requires a real calendar date and explicit known timezone. Timezone-free values, invalid dates, `-00:00`, and leap-second representations are rejected by this profile. The original timestamp string remains unchanged. JSON parsing also rejects duplicate decoded object keys at every depth, including escaped equivalents, non-finite numbers, and unsafe integers. Literal unpaired UTF-16 surrogates in `rawJson` are rejected before hashing so accepted raw strings encode to UTF-8 without replacement. ASCII JSON escape sequences such as `\ud800` retain their distinct raw spelling. These are deliberate limits of this JavaScript fixture profile.

## Immediate request versus final destination

| Concept | Recorded value |
|---|---|
| Admitted ingress | `route-event` |
| Next internal processing stage | `cross-repo-dispatcher` |
| Immediate request repository | `sovereign-codex/Codex-control-center` |
| Immediate request `body.event_type` | `engine_handoff` |
| Immediate request `body.client_payload` | Preserved wrapper containing normalized `target` and `event` |
| Declared final destination target | `avot-engine-runner` |
| Declared final destination repository | `sovereign-codex/AVOT-engine` |
| Declared final receiving event | `avot_execution` |

For a consistent admitted route, the event gains `target_repo`, `target_stage: "avot_execution"`, and `receiving_event_type` when absent. Existing declarations of these fields, `destination.repo`, and `destination.event_type` must agree. `destination.workflow` and `destination.avot` must be absent or null: a non-null declaration holds because this profile has no reviewed mapping for it. The `target_stage` value describes the final fixture stage; it is not the internal `engine_handoff` event.

The final destination is labeled `review_fixture_declaration` with `live_receiver_verified: false`. Only the immediate Control Center request is recorded. No downstream request occurs. Selecting Tyme-Lab produces `missing_receiver`; selecting another unreviewed destination holds. Tyme-Lab named as the producer or inside ordinary payload text does not count as selecting that destination.

## Status and observation semantics

`classifyStatus(raw)` preserves the raw value and separately returns a normalized classification. Negative tokens are checked before exact positive labels. For example, `dispatch_failed`, `route_failed`, `result_failed`, and `result_store_failed` classify as `failure`; `incomplete` stays `incomplete`.

| Category | Handoff behavior |
|---|---|
| `failure`, `incomplete`, `partial`, `skipped`, `blocked`, `unknown` | Hold before transport. Unknown or compound positive-looking labels do not gain success meaning. |
| `progress` | Eligible only if every other contract requirement passes. The implementation uses an explicit label set, not positive substring matching. |
| `reported_completion` | An exact producer completion claim; eligible under the same checks, with receiver completion still unverified. |

Exact completion labels are `success`, `complete`, `completed`, and `execution_completed`. A standalone classifier may trim text for classification, but the input validator still rejects padded required producer strings. The event's `status` and `timestamp` are never replaced by local progress or observation values.

The harness adds `observation.diagnostic_id` and `observation.observed_at` separately. `options.observedAt` selects a fixed fixture time and labels `clock_mode: "fixed_fixture"`; otherwise the harness records its local system observation time. The fixed-time choice is captured at harness creation so later caller mutation of the options object cannot change it. Neither clock mode becomes producer evidence.

## Local duplicate and collision identity

One harness instance owns one in-memory ledger. Its key is the tuple:

```text
[declared_source_repo, declared_source_workflow, caller_request_id]
```

That key binds to a fingerprint of the contract version, exact raw JSON hash, complete route-decision hash, and ingress event type. Route decisions are serialized with sorted object keys for hashing; raw JSON is not normalized. Changing raw whitespace or key order therefore collides under the same identity even if the parsed event is equivalent. Direct and wrapped inputs can normalize identically while retaining different raw identities.

An identical repeat returns `duplicate`, retains `prior_observation`, and makes no new fake attempt. Different bytes, route content, or ingress under the same key return `identity_collision`. Duplicate/collision results still retain current normalization issues and raw evidence; they do not erase the previous outcome.

A hold with a complete ledger key reserves that identity, as do rejection and error outcomes. A missing producer namespace or caller request ID cannot create a key. Correcting a previously recorded request requires a new caller request ID for local review; this creates no execution authority. Equal caller IDs in different declared producer namespaces are separate local identities. Those namespaces are not authenticated.

A fresh harness starts with an empty ledger. Nothing survives process loss, coordinates concurrent processes, or proves remote exactly-once execution. The normalized-event hash is diagnostic evidence, not the duplicate identity rule.

## Fake transport and dispositions

`createReviewHarness` accepts built-in `fakeResponse` data. It does not accept or invoke a live transport. The default is `{ "type": "http", "status": 204 }`; another integer HTTP status from 100 through 599, or `{ "type": "error", "message": "fixture error" }`, may be supplied.

| Disposition | Meaning |
|---|---|
| `hold` | Contract requirements failed; no fake request was recorded. Issues explain the hold. |
| `ready` | Normalization passed. Returned by `normalizeHandoff` before transport simulation. |
| `transport_accepted` | One fake request was recorded and the configured fake response was exactly HTTP 204. |
| `transport_rejected` | One fake request was recorded and the fake HTTP status was anything other than 204, including other 2xx statuses. |
| `transport_error` | One fake request was recorded and the configured response simulated an error; `outcome_unknown` is true. |
| `duplicate` | An identical identity binding already exists in this harness; no new attempt. |
| `identity_collision` | An existing identity binds different evidence; no new attempt. |

There are no retries. Identical repeats after a rejection or error remain duplicates. The `requests` getter returns cloned recorded requests so callers cannot mutate stored evidence through a returned snapshot.

Every harness result keeps `execution.status: "unverified"`, `completed: false`, `completion_claim: false`, and null receiver-run and artifact identities. Transport acceptance, receipt of a producer claim, and local test success cannot establish receiver execution, durable receipt custody, or institutional acceptance. Current credentials, permissions, and live receiver behavior remain outside this specimen's evidence.
