# EXTERNAL_COGNITION_BRIDGE_002

Status: review candidate  
Parent contract: `docs/TYME_EXECUTOR_CONTRACT_v1.md`  
Authority ceiling: one human-gated synthetic execution

## Purpose

Prove that the disposable-executor lifecycle can begin from a Hall-originated packet rather than from an executor-side script assembled by hand.

Bridge 002 is intentionally narrow. It does not automate provider provisioning, Hall dispatch, model routing, executor teardown, or evidence admission. A human remains the explicit gate between each consequence-bearing step.

## What this pilot must prove

```text
Hall creates packet
-> human authorizes bounded execution
-> one disposable executor receives packet
-> one model call runs within packet constraints
-> one structured return envelope is produced
-> Hall receives and validates return
-> Hall records evidence hash
-> executor is destroyed
-> Hall revalidates the retained artifact after teardown
```

## Synthetic packet

The initial Bridge 002 packet should be created on Hall Core before the executor exists.

Recommended Hall path:

```text
/home/steward/hall-evidence/external-executors/bridge-002/TYME-EXEC-BRIDGE-002.packet.json
```

Candidate packet:

```json
{
  "packet_version": "executor-packet-v1",
  "packet_id": "TYME-EXEC-BRIDGE-002",
  "commission_ref": "EXTERNAL_COGNITION_BRIDGE_002",
  "task": "Read the supplied synthetic statement and return a bounded acknowledgement using the declared model return contract.",
  "sensitivity": "synthetic",
  "authority_ceiling": "bounded_execute",
  "executor_requirements": {
    "capabilities": ["text_generation"],
    "preferred_model": "Qwen/Qwen2.5-0.5B-Instruct",
    "preferred_accelerator": "NVIDIA L4"
  },
  "constraints": [
    "Do not invent additional facts.",
    "Do not access external accounts, repositories, APIs, or network resources beyond model retrieval required by the human operator.",
    "Do not mutate Hall, GitHub, Notion, provider configuration, or any external system.",
    "Return JSON only.",
    "Preserve packet_id exactly."
  ],
  "inputs": [
    {
      "type": "synthetic_text",
      "value": "Hall retains institutional continuity; the executor performs only the bounded task it is given."
    }
  ],
  "model_return_contract": {
    "required_fields": [
      "packet_id",
      "summary",
      "status"
    ],
    "json_only": true
  },
  "envelope_contract": {
    "event_type": "external_executor_return",
    "required_fields": [
      "event_type",
      "packet_id",
      "executor",
      "model",
      "timestamp_utc",
      "execution_status",
      "model_output"
    ]
  },
  "teardown_required": true
}
```

## Expected model-level return

The model's content does not need to match these words exactly, but it must satisfy `model_return_contract` and add no unsupported claims.

Example:

```json
{
  "packet_id": "TYME-EXEC-BRIDGE-002",
  "summary": "Bounded packet acknowledged successfully.",
  "status": "complete"
}
```

## Executor return envelope

The executor wrapper must preserve the model response inside a separate evidence envelope rather than treating model text as self-validating institutional truth.

Candidate return:

```json
{
  "event_type": "external_executor_return",
  "packet_id": "TYME-EXEC-BRIDGE-002",
  "executor": "human-provisioned-ephemeral-gpu",
  "model": "Qwen/Qwen2.5-0.5B-Instruct",
  "timestamp_utc": "",
  "accelerator": "NVIDIA L4",
  "prompt_sha256": "",
  "model_output": "",
  "execution_status": "complete",
  "artifacts": [],
  "warnings": []
}
```

The outer object must satisfy `envelope_contract`; the raw content stored in `model_output` must independently satisfy `model_return_contract`.

## Human-gated procedure

### Gate A — Hall packet creation

On `hall-core-0-steward`:

1. create `~/hall-evidence/external-executors/bridge-002/`;
2. write the packet JSON there;
3. validate it with `python3 -m json.tool`;
4. record its SHA-256 before any executor is provisioned.

The packet hash becomes the outbound evidence identity for the test.

### Gate B — Provision one disposable executor

The human operator may provision one ephemeral GPU executor that satisfies the packet's declared capability requirements.

No public inference port is required. SSH access is sufficient for the pilot.

The executor is not canonical and should contain no unique institutional state.

### Gate C — Transfer only the packet

Copy or paste the exact Hall packet into the executor and verify its SHA-256 there before execution.

If the executor-side packet hash differs from the Hall-side packet hash, stop. Do not execute.

### Gate D — Execute one bounded model call

Run one model call against the packet. The wrapper should:

- hash the effective prompt;
- preserve raw model output;
- validate or at minimum test the raw output against `model_return_contract`;
- build the external executor return envelope;
- save the envelope as JSON.

No retry loop, model race, multi-agent delegation, or alternate-provider fallback is admitted in Bridge 002.

### Gate E — Return to Hall

Transfer the return envelope back to:

```text
/home/steward/hall-evidence/external-executors/bridge-002/TYME-EXEC-BRIDGE-002.return.json
```

Then Hall should:

1. validate JSON syntax;
2. verify `packet_id` matches the issued packet;
3. verify the outer envelope satisfies `envelope_contract`;
4. inspect `execution_status`;
5. verify the raw model-level output satisfies `model_return_contract`;
6. calculate and record the Hall-side return SHA-256.

### Gate F — Destroy executor

After Hall acceptance, stop and terminate the executor.

The saved SSH host entry may remain only as clearly archival metadata or be removed. It must not be treated as a persistent runtime endpoint.

### Gate G — Post-teardown continuity proof

After the executor no longer exists, Hall must again:

```bash
python3 -m json.tool ~/hall-evidence/external-executors/bridge-002/TYME-EXEC-BRIDGE-002.return.json
sha256sum ~/hall-evidence/external-executors/bridge-002/TYME-EXEC-BRIDGE-002.return.json
```

The post-teardown return hash must exactly match the pre-teardown Hall hash.

## Pass criteria

Bridge 002 passes only if all of the following are true:

- Hall created the packet before executor provisioning;
- packet JSON validated;
- packet hash matched on Hall and executor;
- one executor was used;
- one bounded model call was used;
- executor did not widen authority or mutate external systems;
- one structured return envelope came back;
- return packet ID matched the issued packet;
- outer envelope satisfied `envelope_contract`;
- model output satisfied `model_return_contract`;
- Hall validated and hashed the return;
- executor was terminated;
- Hall retained the return independently;
- post-teardown Hall hash matched exactly.

Compact pass statement:

```text
one packet
one executor
one bounded model call
one return envelope
one Hall acceptance
one teardown
zero hidden authority expansion
```

## Failure conditions

Bridge 002 stops immediately if:

- packet hashes differ across transfer;
- the executor cannot meet the declared capability requirement;
- the model output violates `model_return_contract`;
- the outer return violates `envelope_contract`;
- executor tooling requests broader authority than the packet permits;
- return identity is ambiguous;
- Hall cannot independently retain the return;
- teardown leaves unresolved unique institutional state on the executor.

A failed pilot should preserve evidence and stop. It should not be repaired by silently widening scope.

## Explicitly out of scope

- automatic RunPod or other provider provisioning;
- Hall-originated network dispatch;
- persistent inference services;
- public model endpoints;
- automatic model routing;
- multi-agent orchestration;
- automatic retries across providers;
- repository writes from the executor;
- physical actuation;
- promotion of model output into Canon or Invariant Lattice.

## Review question

Does this pilot prove a clean packet-to-return bridge while preserving Hall Core 0's existing observe-only authority boundary?

If yes, the next implementation question is not "how do we add more agents?" It is whether a minimal adapter can automate **packet transport and evidence return** without also acquiring authority to provision, route, approve, validate, or promote.
