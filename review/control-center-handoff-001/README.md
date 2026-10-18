# Control Center handoff local candidate

**Candidate:** `CONTROL-CENTER-HANDOFF-001`  
**Standing:** noncanonical local review  
**Contract version:** `control-center-handoff-review/1`

This candidate makes the Router-to-Dispatcher contract reviewable with deterministic fixtures and an in-memory fake transport. It normalizes supported legacy inputs, preserves their evidence, separates the immediate Control Center stage from the declared final destination, and holds missing or contradictory information.

The [pinned routing standard](https://github.com/sovereign-codex/Codex-control-center/blob/4a5def9816bdb6c771559f3105558578edd284c1/WORKFLOW_ROUTING_STANDARD.md) identifies the mismatch between the Router's `cross-repo-dispatcher` event and the Dispatcher's `engine_handoff` listener. This specimen records the proposed internal `engine_handoff` request without invoking either workflow. It is not an implementation of the full routing-envelope schema or production workflow wiring.

## Run the local review

From this directory:

```sh
node run-review.mjs
```

The implementation uses Node built-ins only; no dependency installation is required. It has been tested on **Node v24.19.0**. Compatibility with other versions has not been established. The runner uses Node's [in-process test API](https://nodejs.org/download/release/v24.13.1/docs/api/test.html#runoptions) with `isolation: 'none'`, runs the local tests and demonstration without spawning a child process, and writes local evidence:

| File | Purpose |
|---|---|
| [evidence/test-results.json](evidence/test-results.json) | Machine-readable test result and recorded run context; consult this for the actual test count and outcome. |
| [evidence/tests.tap](evidence/tests.tap) | Detailed test output. |
| [evidence/demo-results.json](evidence/demo-results.json) | Fixture inputs, recorded fake requests, and demonstration outcomes. |

Rerunning regenerates these local evidence files. Passing tests establish the candidate's tested contract behavior. They do not establish GitHub delivery, authentication, receiver execution, or institutional acceptance.

## Files and entry points

| Path | Role |
|---|---|
| [candidate/adapter.mjs](candidate/adapter.mjs) | Exports `normalizeHandoff`, `classifyStatus`, and `createReviewHarness`. The adapter has no network, filesystem, environment, subprocess, or credential access. |
| [CONTRACT.md](CONTRACT.md) | Input profile, normalization, status handling, duplicate identity, and transport semantics. |
| [tests/acceptance.test.mjs](tests/acceptance.test.mjs), [tests/review-regressions.test.mjs](tests/review-regressions.test.mjs) | Independent acceptance assertions in the ten categories below, plus regressions for issues found in review. |
| [fixtures/direct-event.json](fixtures/direct-event.json), [fixtures/nested-event.json](fixtures/nested-event.json) | Equivalent supported producer events with different raw representations. |
| [fixtures/route-decision.json](fixtures/route-decision.json) | Explicit internal stage and AVOT-engine destination declaration. |
| [demo.mjs](demo.mjs), [run-review.mjs](run-review.mjs) | Local demonstration and evidence generation. |
| [BASELINE.json](BASELINE.json) | Pinned source identities, hashes, and snapshot provenance. |

## Acceptance categories

Acceptance test names use the bracketed category IDs from [TYME-HANDOFF-REVIEW-001](https://chatgpt.com/space/page_7cbbaf04401881918ae73bd78a212be8). The separate regression file covers additional source, destination, encoding, API-input, and observation-clock boundaries.

| Category | Contract checked |
|---|---|
| `legacy_shapes` | Direct and wrapped events yield equivalent normalized content while raw representations, rich fields, and extensions survive. |
| `internal_event` | The immediate fake request targets Control Center with exactly `engine_handoff`; final destination metadata stays separate. |
| `conflicting_target` | Missing or contradictory routes, destinations, and rich declarations hold before transport. |
| `missing_provenance` | Required producer fields and caller identity cannot be fabricated; malformed JSON, duplicate keys, and invalid timestamps hold. |
| `failure_status` | Failure-bearing labels retain failure meaning and cannot advance the handoff. |
| `non_success` | Incomplete, partial, skipped, blocked, and unknown outcomes hold; a producer completion claim remains unverified. |
| `identity_collision` | Reusing a declared request identity with different raw bytes, route, or ingress creates a collision. |
| `duplicate` | Exact repeats retain the prior local outcome without another attempt, including prior holds, rejections, and errors. |
| `transport_only` | Fake HTTP acceptance, rejection, and errors preserve distinct outcomes without receiver-completion claims. |
| `missing_receiver` | A selected Tyme-Lab destination holds; other unreviewed destinations are not admitted. |

## Baseline and scope

The baseline is Control Center commit `4a5def9816bdb6c771559f3105558578edd284c1`. `BASELINE.json` records exact pinned Git blob identities and source SHA-256 hashes. Earlier local text materialization added one final LF to each listed source snapshot; the manifest records both byte counts and hashes and names that transformation explicitly. Those snapshots remain unchanged. The candidate package carries their provenance, not copies of production source files.

All new implementation and local evidence belong to this isolated review directory. Existing workflows, the trace normalizer, and `review/bridge-local-repair-001` are unchanged. This work does not create a remote branch or PR, dispatch a workflow, mint a token, alter permissions, run a model, deploy a service, or change Notion or Cloudflare.

## Remaining integration work

The AVOT-engine route is a fixture declaration; its live receiver and current credential state are unverified here. Tyme-Lab still requires a separately reviewed receiver contract. Any later wiring must preserve the request and raw outcome, establish authenticated sender identity and attributable receiver evidence, and verify the resulting receipt independently. This candidate supplies local contract evidence for that review; it does not grant activation or promotion.
