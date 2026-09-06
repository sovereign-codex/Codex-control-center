# TYME_EXECUTOR_CONTRACT_v1

Status: verified reference contract  
Reference proofs: `TYME-EXEC-TEST-001`, `TYME-EXEC-BRIDGE-002`  
Authority ceiling: bounded documentation and human-gated external execution only

## Purpose

Define the minimum contract by which TYME Hall may use replaceable external cognition surfaces while keeping institutional continuity, authority, evidence, and accepted state inside Hall.

This contract is derived from completed disposable-executor proofs on RunPod L4. It does not authorize autonomous provider provisioning, persistent inference APIs, swarm orchestration, repository mutation by executors, public model hosting, or physical actuation.

## Governing rule

**Hall is canonical; executors are replaceable cognition surfaces.**

An executor may reason, transform, infer, compile, simulate, or generate only within an already-authorized packet. It does not own institutional memory, authority, accepted evidence, gate state, or the next valid transition.

## Reference proofs

### TYME-EXEC-TEST-001

The precursor proof completed this lifecycle:

```text
RunPod Secure Cloud L4
-> CUDA / PyTorch validation
-> Qwen/Qwen2.5-0.5B-Instruct
-> structured external_executor_return
-> Hall-side JSON validation
-> Hall-side SHA-256 custody
-> executor termination
-> identical post-teardown Hall hash
```

Accepted Hall-side SHA-256:

```text
ac3c0090cf164defe0463362c705624588f9f93c9e4fcc72e7349becdee4d95f
```

### TYME-EXEC-BRIDGE-002

Bridge 002 then proved the packet originated in Hall, crossed to a disposable external executor, returned in a structured evidence envelope, was validated under Hall custody, and survived executor teardown as institutional evidence.

Canonical packet SHA-256:

```text
a257b9347904d962bce781337672aab17f8581d9d1100f289e2bcd728c65654f
```

Returned envelope SHA-256:

```text
1cc0815c23c59d0b2605de54853cfdb30f961013861e2c665c4f0bd92be5254a
```

Execution receipt SHA-256:

```text
70a3d9ed10657917c4597a4100f6b63c2bbd69507e14bd259d6e44c36b873567
```

Bridge 002 establishes the reference round trip:

```text
Hall canonical packet
-> external disposable executor
-> bounded model execution
-> structured return envelope
-> Hall verification and custody
-> executor teardown
-> Hall continuity preserved
```

## Executor invariants

1. **Hall remains canonical.** Accepted packet identity, authority, evidence, and custody remain Hall-side.
2. **Executors are disposable.** No executor is required for institutional continuity after its return is accepted.
3. **Every execution begins from a bounded packet.** The packet carries stable identity, task scope, constraints, model-return contract, envelope contract, and authority ceiling.
4. **Capability does not imply authority.** Available GPU, model, shell, network, storage, or tool access does not widen the packet's permitted action.
5. **No executor manufactures authority.** It consumes an already-authorized task and cannot self-promote, self-route, or widen scope.
6. **No single component authorizes, executes, and validates its own consequence.** Human or Hall gate, executor, and Hall validation remain distinct roles.
7. **Every execution must return evidence.** A successful model response without a structured return envelope is incomplete.
8. **Hall validates before acceptance.** Schema, packet identity, provenance, status, and content hash are checked before the return becomes institutional evidence.
9. **Secrets are minimal and revocable.** The executor receives only credentials strictly required for the packet and must not become a credential store.
10. **Teardown is part of success.** A disposable executor cycle is not complete until its Hall-retained evidence survives executor destruction.

## Lifecycle

```text
commissioned
-> authorized
-> provisioned
-> capability-checked
-> executing
-> return-produced
-> Hall-received
-> Hall-validated
-> evidence-accepted
-> executor-destroyed
-> continuity-reverified
```

A failure at any stage returns evidence and stops. Failure never silently advances authority.

## Minimum outbound packet

The packet distinguishes the **model-level return contract** from the **executor evidence-envelope contract**. Model content must satisfy the former; the wrapper surrounding that content must satisfy the latter.

```json
{
  "packet_version": "executor-packet-v1",
  "packet_id": "TYME-EXEC-...",
  "commission_ref": "",
  "task": "",
  "sensitivity": "synthetic | public | internal | restricted",
  "authority_ceiling": "bounded_execute",
  "executor_requirements": {
    "capabilities": [],
    "preferred_model": null,
    "preferred_accelerator": null
  },
  "constraints": [],
  "inputs": [],
  "model_return_contract": {
    "required_fields": [],
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

## Minimum return envelope

```json
{
  "event_type": "external_executor_return",
  "packet_id": "TYME-EXEC-...",
  "executor": "",
  "model": "",
  "timestamp_utc": "",
  "accelerator": "",
  "prompt_sha256": "",
  "model_output": "",
  "execution_status": "complete | failed | refused | partial",
  "artifacts": [],
  "warnings": []
}
```

`model_output` preserves the raw model-level return. It is evidence, not self-validating institutional truth. Hall validates the model output against `model_return_contract` and separately validates the outer envelope against `envelope_contract`.

## Hall acceptance gate

A return is accepted only if all required checks pass:

- packet ID matches an issued Hall packet;
- executor identity and declared capability are attributable;
- execution remained within the packet's authority ceiling;
- outer return envelope satisfies `envelope_contract`;
- model-level output satisfies `model_return_contract`;
- required artifacts are present and hashable;
- Hall stores the accepted return independently of the executor;
- post-teardown continuity remains independently verifiable from Hall-retained evidence.

## Failure behavior

| Condition | Required response |
| --- | --- |
| Capability unavailable | Return `failed` or `refused`; do not silently substitute an unapproved surface. |
| Packet ambiguity | Stop and request clarification; do not infer new authority. |
| Model output violates model-return contract | Preserve raw output as evidence, mark validation failure, and do not promote it. |
| Executor envelope violates envelope contract | Preserve the raw envelope, mark validation failure, and do not accept it as institutional evidence. |
| Executor interrupted | Record partial evidence if recoverable; Hall remains authoritative. |
| Hash mismatch after transfer | Reject acceptance and preserve both observed hashes for investigation. |
| Teardown fails | Cycle remains incomplete until residual executor state is resolved. |

## Authority boundary

This contract permits human-gated bounded external execution. It does not alter Hall Core 0's current observe-only institutional authority boundary.

Specifically, this contract does **not** admit:

- autonomous dispatch from Hall Core;
- provider account mutation or automatic GPU provisioning;
- persistent executor identity;
- repository mutation by an executor;
- public inference endpoints;
- multi-agent or swarm execution;
- model self-selection outside packet constraints;
- physical or consequence-bearing actuation;
- self-validation or self-promotion of model output.

## Reference implementation

`docs/pilots/EXTERNAL_COGNITION_BRIDGE_002.md` is the first verified reference implementation of this contract.

It proves that a Hall-originated packet can move through an external cognition surface while preserving canonical authority, evidence custody, and teardown discipline.

## Next valid action

Do not expand to autonomous provider control yet.

The next admissible implementation step is a minimal bridge adapter that may automate **packet transport and evidence return only** while remaining unable to:

- provision or terminate providers on its own authority;
- choose or widen model scope beyond the packet;
- authorize its own work;
- validate its own consequence;
- mutate Hall canon;
- promote model output into institutional truth.

Any broader runtime authority requires a separate contract and review gate.
