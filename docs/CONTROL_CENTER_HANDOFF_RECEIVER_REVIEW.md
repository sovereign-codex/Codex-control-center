# Control Center handoff — AVOT receiver review

## Disposition and integration boundary

**External `avot_execution` activation remains held.** The current AVOT receiver accepts a different payload, simulates completion, and has configured repository and dispatch effects.

The CCC integration uses real service code with `enabled:false`, empty sender/producer bindings, and `receiver.compatible:false`. Injected test services exercise that code locally; the review harness is not a production dependency. A later activation requires the separately reviewed receiver repair below.

## Verified source scope

Read-only audit on **2026-10-18**, with `main` rechecked unchanged at **05:27:42 UTC**:

| Item | Verified value |
|---|---|
| Repository | `sovereign-codex/AVOT-engine` |
| Default-branch commit | `dea4b3f0c05334f8abd33ac4c2abae76b094e6f4` |
| Git tree | `9936597bc7ec02102237c0f0c15390c801612241` |
| Complete recursive inventory | 110 entries, 83 blobs, `truncated:false` |
| Workflow coverage | All **7** workflow files read |
| Repository instructions | No `AGENTS.md` in the complete tree |
| Exact source verification | 24 relevant fetched files matched their Git blob SHA; no newline transformations |

The [pinned tree](https://github.com/sovereign-codex/AVOT-engine/tree/dea4b3f0c05334f8abd33ac4c2abae76b094e6f4) has one `repository_dispatch` listener (`avot_execution`), two `workflow_dispatch` runners, and no `workflow_call` listener:

| Workflow | Trigger |
|---|---|
| `avot-engine-receiver.yml` | `repository_dispatch: avot_execution` |
| `avot-harness.yml` | Manual; required `scenario`, default `quorum-fail` |
| `engine-run.yml` | Manual; no inputs |
| `avot-issue-run.yml` | Issue labeled `run-avot` |
| `inference-contract.yml` | Selected pull-request/push paths |
| `cit-pilot-02-conduction.yml` | Selected pull-request/push paths |
| `monitor-participation-runtime-v0.yml` | Selected pull-request/push paths |

The connector rejected the Actions workflow collection URL as unsupported. Enabled/disabled workflow state was therefore not established. This review describes committed source: it did not execute a workflow, call a receiver, inspect or mint credentials, or establish current token capability.

## Decisive source identities

Every link is pinned to the audited commit.

| Source | Git blob SHA |
|---|---|
| [Dispatch receiver](https://github.com/sovereign-codex/AVOT-engine/blob/dea4b3f0c05334f8abd33ac4c2abae76b094e6f4/.github/workflows/avot-engine-receiver.yml) | `3b8af8bd9bb7c610e9fd8e0607ebd9810b20aeda` |
| [Inference contracts](https://github.com/sovereign-codex/AVOT-engine/blob/dea4b3f0c05334f8abd33ac4c2abae76b094e6f4/src/inference/contracts.ts) | `a3967f01c0727c0fd940215987199575e73dda8e` |
| [Inference round-trip](https://github.com/sovereign-codex/AVOT-engine/blob/dea4b3f0c05334f8abd33ac4c2abae76b094e6f4/src/inference/roundtrip.ts) | `64f1bc4210bd314fdb99a3338a601857ff8c4a02` |
| [Inference return-path builder](https://github.com/sovereign-codex/AVOT-engine/blob/dea4b3f0c05334f8abd33ac4c2abae76b094e6f4/src/inference/return-path.ts) | `1e4688b7f06afc0a24eb0da30d6b5ae8272bcc68` |
| [Loopback model adapter](https://github.com/sovereign-codex/AVOT-engine/blob/dea4b3f0c05334f8abd33ac4c2abae76b094e6f4/src/inference/local-openai-adapter.ts) | `974c533a2430a744232dfa2d28ff784755dfe35c` |
| [CIT conduction](https://github.com/sovereign-codex/AVOT-engine/blob/dea4b3f0c05334f8abd33ac4c2abae76b094e6f4/src/runtime/conduction.ts) | `13c5842fe0675c9851e42caacb00b0641f1bd0da` |
| [Execution contract](https://github.com/sovereign-codex/AVOT-engine/blob/dea4b3f0c05334f8abd33ac4c2abae76b094e6f4/CONTRACT.md) | `aac7fc8a87c4fc12830ffb134f1155c05584d9dd` |

The audit's source copies are analysis evidence and are not added to this repository.

## Payload and return mismatches

The receiver reads only top-level `client_payload.trace_id`, `source`, and `route` (receiver lines 20–25, 42–63). Missing trace becomes `trace_${GITHUB_RUN_ID}`; missing source/route become `unknown`.

| CCC integration requirement | Current receiver behavior |
|---|---|
| `{target,event,request_id,_ccc_handoff}` envelope | Does not read these four fields |
| Complete normalized event and wrapper extensions | Rebuilds only trace/source/route/received_at/status |
| Producer status, timestamp, governance, runtime packet | Does not consume or retain them |
| Request identity and exact-content/evidence bindings | No validation or retention |
| Durable duplicate/collision disposition | Trace-based filenames can overwrite prior records |
| Authenticated observation separate from declarations | Treats incoming source as a string; no producer-run proof |
| Attributable processing result | Writes simulated completion without requested-work evidence |

The incoming file is rebuilt as `{trace_id,source,route,received_at,status:"received"}` (lines 87–102). The separate manual event processor reads `inputs/events`; this receiver writes `inputs/incoming` and never calls that processor.

The callback uses `avot_result` to CCC with only:

```json
{
  "trace_id": "<incoming or synthesized trace>",
  "status": "completed",
  "source": "avot-engine"
}
```

It omits request ID/digest, receiver run/attempt/commit, execution timestamp, artifact reference, and model or result evidence. HTTP 204 becomes `result_sent`; another HTTP status becomes `result_failed` without explicitly failing that step. TRACE calls do not check HTTP acceptance and omit a timestamp. The CCC callback listener and its receipt contract require separate verification.

## Simulated computation and configured effects

The receiver's computation is `sleep 2`, followed by a generated `status:"completed"` result (lines 123–139). Its workflow does not invoke an engine processor, model adapter, result validator, or Value Kernel check.

Configured effects are substantial: `contents:write`, App-token generation, incoming/result files, commits and a push to `main`, four TRACE dispatches, and a Control Center callback. Whether those effects would currently succeed is unverified.

Input fields are interpolated directly into shell source; trace IDs also enter paths and environment-file writes without a receiver-side format check. Real activation requires data-safe parsing.

The richer inference paths above already define request IDs, authority/privacy limits, verification and evidence. Their return-path builder checks request/plan/result identity equality, and their loopback adapter can call a configured model endpoint. **They are disconnected from this dispatch workflow.** Their presence proves neither endpoint provisioning nor model execution.

Open PRs [#13](https://github.com/sovereign-codex/AVOT-engine/pull/13), [#14](https://github.com/sovereign-codex/AVOT-engine/pull/14), and [#17](https://github.com/sovereign-codex/AVOT-engine/pull/17) were checked through summaries and complete changed-file collections. None changes the dispatch receiver or adds a replacement listener.

## Smallest separately reviewed receiver repair

A bounded receiver-specific change must:

1. Parse the versioned four-field envelope as data, preserve the complete event, and validate request/claim/evidence bindings before any configured effect. Keep authenticated transport principal observations distinct from declared source workflow identity.
2. Define a durable receiver admission and duplicate/collision contract. A CCC claim authorizes one transport attempt; it does not establish receiver execution.
3. Replace unqualified simulated completion with explicit processing states. A first transport-only receipt may confirm receipt/retention while execution stays unverified. Any actual processing must enforce its reviewed governance and runtime boundary.
4. Return a matching CCC receipt with request/input identity, receiver run/attempt/commit, actual observation time, and retained artifact references. Transport acceptance, retained receipt, and completed work remain separate outcomes.
5. Review the receiver's commits and outbound calls; do not inherit them implicitly. Bind activation to the reviewed receiver version and require the receiving workflow to reject an incompatible version before effects.

This repair can first establish attributable receipt without introducing a model call. Actual inference activation can then be reviewed against the existing inference contracts. Until those receiver and receipt obligations are satisfied, the CCC policy remains disabled and the outward route remains incompatible.

