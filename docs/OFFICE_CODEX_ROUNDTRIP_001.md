# OFFICE-CODEX-ROUNDTRIP-001

**Standing:** REVIEW-ONLY / NON-AUTHORIZING / NO LIVE AGENT OR CODEX EXECUTION

## Objective

Establish the first accountable Office -> Control Center -> Codex -> Evidence -> Office round-trip without manual copy/paste relay.

## Baseline

- repository: `sovereign-codex/Codex-control-center`
- baseline commit: `d8230a2f6fbc8c633c470f8446078f5f8d41abfb`
- existing guarded handoff: merged PRs #21 and #22
- existing handoff policy remains disabled
- existing AVOT-engine route must remain behaviorally unchanged

## Governing finding

Do not replace the restored Control Center handoff.

Extend the handoff contract so a destination is explicit and provider-neutral while preserving the existing GitHub repository-dispatch edge.

Candidate destination classes:

```yaml
destination:
  class: github_dispatch | workspace_agent | codex_agent
  endpoint_id: ""
  declared_role: ""
  operation: ""
  asynchronous: true
```

Unknown destination classes must fail closed.

## Round-trip

```text
Office role A
-> bounded assignment
-> Control Center
-> Codex runtime
-> structured evidence return
-> TRACE / receipt
-> Office role B review
-> STOP
```

## Authority ceiling

Roundtrip 001 is read-only.

Not authorized:

- repository mutation
- branch creation by the executor
- pull request creation
- workflow dispatch
- merge
- deployment
- Canon promotion
- Office standing mutation
- public Hall publication
- autonomous continuation after review

## Correlation invariants

Preserve one institutional request identity through all runtime-specific identifiers.

Required correlations:

- `request_id`
- `trace_id`
- originating Office role / assignment
- destination class
- endpoint identity
- Workspace Agent `conversation_key` and API run ID when used
- Codex session/task identifier when used
- repository + exact SHA when material
- durable return receipt identity

Retries must be idempotent or fail closed. Ambiguous transport outcomes must not be silently retried.

## Workspace Agent adapter

The Workspace Agent trigger is asynchronous. Transport acceptance is not work completion.

Required adapter behavior:

- stable API-channel ID
- token supplied only through secret/runtime configuration
- stable `conversation_key`
- stable idempotency key per source event
- accepted / rejected / uncertain classification
- run metadata capture
- independent destination/result verification
- no secret material in routed payloads, TRACE, logs, or repository content

## Codex adapter

Use the managed OpenAI Agents API / Codex harness for the first proof unless a self-hosted environment is separately required.

Required adapter behavior:

- create or resume a bounded session
- submit one read-only task
- preserve repository/SHA context
- capture session/task identifier
- capture lifecycle status
- capture structured completion
- preserve interruption/failure state
- normalize the result into CIT/TRACE-compatible return evidence

## Common return states

Do not collapse these into one success flag:

```text
transport accepted
runtime started
runtime completed
result returned
evidence stored
review completed
institutional standing
```

## First assignment candidate

> Inspect current Hall-related repositories and return the transport/runtime dependencies required for Public Intelligence Terminal v0. Do not modify repositories, open PRs, dispatch workflows, deploy, or change standing.

Suggested origin: Repo Cartographer or equivalent bounded architecture-mapping role.

Suggested reviewer: Promotion Reviewer or PR Synthesist acting only as semantic/evidence reviewer.

## Acceptance criteria

- [ ] Existing handoff tests remain green.
- [ ] Existing disabled AVOT route behavior remains unchanged.
- [ ] Unknown destination classes fail closed.
- [ ] Credential values never enter event payloads or durable evidence.
- [ ] Stable request identity survives all stages.
- [ ] Exact repo/SHA context survives when material.
- [ ] Transport acceptance remains distinct from execution completion.
- [ ] Codex result returns in structured CIT/TRACE-compatible form.
- [ ] A second Office role can review without manual relay.
- [ ] Durable receipt is independently readable.
- [ ] No unauthorized mutation occurs.
- [ ] The lifecycle stops after review.

## Current holds

1. No Control Center Workspace Agent adapter exists.
2. No Control Center Codex Agents API adapter exists.
3. Existing `result-receiver.yml` predates the guarded handoff and is not sufficient completion evidence.
4. Durable institutional receipt custody is unresolved.
5. Live Workspace Agent API-channel identity and token posture are not established here.
6. No live Codex execution is authorized by this branch.
7. Public Hall / Cloudflare integration is outside this proof.

## Implementation sequence

1. Add destination abstraction to the handoff contract without changing the current GitHub route.
2. Add offline fixtures and negative tests for `workspace_agent` and `codex_agent`.
3. Add a fake/injected Workspace Agent trigger adapter test surface.
4. Add a fake/injected Codex Agents API lifecycle adapter test surface.
5. Define one common return/receipt schema.
6. Run all existing and new offline regression tests.
7. Review the exact branch head.
8. Only after independent review, configure one real Workspace Agent API channel and one bounded Codex runtime.
9. Execute the read-only round-trip.
10. Read back the durable receipt independently; stop.

## Proof criterion

The round-trip passes only if a fresh reviewer can reconstruct who assigned the work, what was authorized, which runtime handled it, what repository state was inspected, what happened, what evidence supports the result, what remains uncertain, who reviewed it, what institutional effect occurred, and where the receipt can be independently retrieved.
