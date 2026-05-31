# WORKFLOW_ROUTING_STANDARD.md

## Purpose

Define the canonical routing contract for Sovereign Intelligence GitHub Actions workflows across Archivist, Control Center, Invariant Lattice, Value Kernel, AVOT Engine, Trace, CodexNet Index, and Interface.

This standard exists to prevent routing drift caused by repository renaming, legacy event names, missing listener workflows, and inconsistent payload shapes.

## Current diagnosis

The original runtime spine exists and is mostly wired:

```text
AVOT-ARCHIVIST -> Codex-control-center -> AVOT-engine -> AVOT-TRACE
```

The expanded architecture exists but is not fully wired:

```text
Invariant-lattice -> Value-kernel -> Codex-net-index -> Codex-interface-
```

The primary restoration need is to standardize route names, payload shape, and sequence before editing multiple workflows.

## Canonical repository names

### Runtime spine

- AVOT-ARCHIVIST
- Codex-control-center
- AVOT-engine
- AVOT-TRACE

### Expanded governance / index / interface layer

- Invariant-lattice
- Value-kernel
- Codex-net-index
- Codex-interface-

## Display names and aliases

- Codex-interface is the display / architecture name.
- Codex-interface- is the current GitHub repository name.
- AVOT-engine-core is a legacy reference and should be replaced with AVOT-engine unless a separate repo is intentionally restored.

## Canonical sequence

1. incoming_signal
2. archivist_ingest
3. control_center_route
4. invariant_check
5. value_check
6. avot_execution
7. trace_log
8. index_update
9. interface_publish
10. avot_result

## Phase 1 restored spine

The first repair phase only stabilizes:

```text
AVOT-ARCHIVIST -> Codex-control-center -> AVOT-engine -> AVOT-TRACE -> Codex-control-center
```

Do not add Invariant-lattice, Value-kernel, Codex-net-index, or Codex-interface- until Phase 1 is stable.

## Phase 2 expanded governance stages

After Phase 1 is stable, insert:

```text
Codex-control-center -> Invariant-lattice -> Value-kernel -> AVOT-engine
```

## Phase 3 index and interface

After Phase 2 is stable, define whether Codex-net-index remains scheduled/manual or receives event-driven index_update events.

Codex-interface- should remain read-only/publish-oriented until the upstream index is stable.

## Allowed repository_dispatch event types

Use these canonical event types moving forward:

- route_event
- engine_handoff
- invariant_check
- value_check
- avot_execution
- trace_log
- index_update
- interface_publish
- avot_result
- workflow_failure

## Legacy event names

The following legacy names are known and must be handled carefully:

- route-event: legacy form of route_event.
- cross-repo-dispatcher: legacy router-selected target; not currently equivalent to engine_handoff.
- trace-event: legacy or alternate trace event type.
- AVOT-engine-core: legacy target reference.

## Required payload fields

Every routed workflow event should carry:

```yaml
trace_id: string
source_repo: string
source_workflow: string
source_event: string
target_stage: string
target_repo: string
status: string
timestamp: string
payload: object
governance: object
runtime_packet: object
```

## Minimal legacy-compatible payload

During transition, workflows may accept legacy payloads, but should normalize them internally:

```yaml
trace_id: string
workflow: string
repo: string
status: string
timestamp: string
```

Normalize to:

```yaml
trace_id: string
source_repo: repo
source_workflow: workflow
source_event: legacy
status: string
timestamp: string
```

## Trace requirements

Every substantive workflow must preserve trace_id.

If trace_id is missing, generate a fallback trace id using the workflow name and run id, but mark the packet as degraded.

Trace events should use:

```yaml
event_type: trace_log
```

until the trace-event legacy path is formally deprecated or migrated.

## Runtime packet requirement

Every workflow that changes state should produce or preserve a runtime packet compatible with RUNTIME_PACKET_STANDARD.md.

At minimum, workflow packets should record:

```yaml
packet_version:
packet_id:
emitted_at:
agent_name:
agent_role:
run_type:
source_surface:
target_surface:
input_artifacts:
output_artifacts:
execution_state:
canon_posture:
summary:
open_conditions:
recommended_next_action:
tracker_write_status:
evidence_links:
```

## Failure behavior

Any workflow failure that can be caught should emit:

```yaml
event_type: workflow_failure
```

with payload:

```yaml
trace_id:
failed_repo:
failed_workflow:
failed_stage:
failure_type:
failure_summary:
next_action:
timestamp:
```

## Current confirmed route edges

### AVOT-ARCHIVIST -> Codex-control-center

Current emitted event: route-event
Canonical event: route_event
Target listener: Control Center Router
Status: confirmed but legacy event name should be normalized.

### Codex-control-center router -> Cross Repo Dispatcher

Current emitted event / target: cross-repo-dispatcher
Dispatcher listener: engine_handoff
Status: mismatch risk.
Required repair: standardize router-to-dispatcher handoff.

### Cross Repo Dispatcher -> AVOT-engine

Current emitted event: avot_execution
Target listener: AVOT Engine Receiver
Status: confirmed with payload mismatch risk.
Required repair: include source_repo and route / target_stage fields.

### AVOT-engine -> AVOT-TRACE

Current emitted event: trace_log
Target listener: AVOT Trace Receiver
Status: confirmed.
Risk: duplicate trace_log and trace-event standards exist.

### AVOT-engine -> Codex-control-center

Current emitted event: avot_result
Status: target receiver still needs verification.

## Known unresolved gaps

- Verify Codex-control-center result receiver workflows.
- Decide whether route-event remains supported or is migrated to route_event.
- Decide whether trace-event is legacy or future canonical trace format.
- Add Invariant-lattice listener only after spine stabilization.
- Add Value-kernel listener only after spine stabilization.
- Keep Codex-net-index scheduled/manual until core spine is clean.
- Treat Codex-interface- as current GitHub repository alias for interface layer.

## Repair discipline

Do not repair multiple repos at once.

First repair PR should target the smallest reversible routing mismatch in Codex-control-center.

Preferred first repair:

- make router emit engine_handoff when the target is cross-repo-dispatcher, or
- make Cross Repo Dispatcher also listen for cross-repo-dispatcher as a legacy alias.

Use PRs as promotion gates and preserve ambiguity until confirmed by runs.
