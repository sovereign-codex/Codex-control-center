# D-017C — Pulse Packet Specification

**Status:** Canonical draft chamber version  
**Recommended formal path:** `docs/continuity/D-017C_PULSE_PACKET_SPEC.md`  
**Recommended repository:** `sovereign-codex/Codex-control-center`  
**Surface boundary:** Draft in ChatGPT → formalize in GitHub → index lightly in Notion

---

## 1. Purpose

The Pulse Packet is the structured output of the **Hall Heartbeat / Agent Pulse Tracker**.

It records what the Heartbeat checked, what is healthy, what is drifting, what requires review, what should be routed, and what remains unresolved.

The Pulse Packet exists so continuity observations do not remain temporary chat reflections. It turns system health into durable, inspectable memory.

---

## 2. Core Role

```text
Hall Heartbeat Audit
→ Pulse Packet
→ Human Review / Agent Routing / Registry Repair / No-Action Confirmation
→ Memory Graph
→ Hall Synthesis
```

A Pulse Packet does not create authority by itself.

It reveals where authority, attention, repair, or review may be needed.

---

## 3. Layer Placement

```text
Layer: L5 — Pulse Layer
Audits: L1 through L4
Feeds: L6 — Hall Layer
May route to: L2 Interpretation Layer or L3 Governance Layer
```

The Pulse Layer observes the Information Continuity Architecture.

It does not replace scheduled tasks, custom agents, runtime packets, ledgers, registries, or human review. It audits the health of their relationships.

---

## 4. Foundational Question

Every Pulse Packet begins from the question:

```text
What relationships are weakening?
```

This applies across:

```text
Signal ↔ Agent
Agent ↔ Packet
Packet ↔ Ledger
Packet ↔ Branch
Branch ↔ Lifecycle Posture
Artifact ↔ Evidence
Claim ↔ Truth Posture
Decision ↔ Authority
Memory ↔ Continuity
```

---

## 5. Required Packet Schema

```yaml
pulse_packet:
  packet_version: "0.1"
  pulse_id: ""
  emitted_at_iso: ""
  pulse_type: ""
  run_mode: "manual | scheduled | event_driven"
  scope: []
  sources_checked: []
  signals_reviewed: []
  agents_reviewed: []
  packets_reviewed: []
  ledgers_reviewed: []
  branches_reviewed: []
  repositories_reviewed: []
  relations_reviewed: []
  health_findings: []
  drift_findings: []
  human_review_needs: []
  recommended_routing: []
  no_action_confirmations: []
  next_pulse_focus: ""
  authority_required: []
  guardrails: []
  verification_state: "unverified | partially_verified | verified"
```

---

## 6. Optional Fields

```yaml
optional:
  related_signal_ids: []
  related_evaluation_ids: []
  related_runtime_packet_ids: []
  related_ledger_event_ids: []
  related_branches: []
  related_repositories: []
  related_agents: []
  related_doctrine_refs: []
  stale_items: []
  orphaned_items: []
  blocked_items: []
  contradiction_refs: []
  notes: ""
```

---

## 7. Pulse Types

### `daily_continuity_pulse`

Lightweight recurring audit for open drift, stale records, unprocessed signals, missing relations, and human-review needs.

### `weekly_synthesis_pulse`

Broader synthesis across open threads, agent handoffs, unresolved decisions, branch posture, truth posture, and priority shifts.

### `branch_memory_pulse`

Focused audit of branch lifecycle posture, branch registry alignment, PR state, merge state, deletion risk, and closeout readiness.

### `signal_processing_pulse`

Focused audit of scheduled task outputs and whether they became Signal Packets, no-action confirmations, watchlist items, or assigned evaluation requests.

### `agent_handoff_pulse`

Focused audit of custom agent outputs, handoff completion, overlap, unresolved evaluations, and stuck processing states.

### `governance_relation_pulse`

Focused audit of Runtime Packet ↔ Ledger, Packet ↔ Branch, Packet ↔ Capability, and other graph-memory edges.

### `coherence_posture_pulse`

Focused audit of truth posture conflicts, aging hypotheses, unresolved contradictions, canon candidates, and doctrine drift.

---

## 8. Drift Types

### `signal_drift`

Important signals were emitted but never interpreted, routed, watchlisted, or closed.

### `interpretation_drift`

Signals or artifacts were interpreted, but the output did not become an Evaluation Packet, review note, runtime packet, ledger event, or no-action confirmation.

### `governance_drift`

Actions occurred but accountability records, authority state, verification state, or ledger relations are incomplete.

### `memory_drift`

Relationships exist in practice but are not preserved as durable memory relations.

### `coherence_drift`

The system no longer clearly knows what it believes, what is uncertain, what is contested, and what remains unresolved.

---

## 9. Health Finding Format

```yaml
health_finding:
  item_ref: ""
  summary: ""
  relation_health: "healthy | partial | degraded | unknown"
  evidence_refs: []
```

Health findings record what is working.

They are important because the Pulse should not only surface problems. It should also preserve no-action confirmations and healthy relationships so future agents do not re-audit the same ground unnecessarily.

---

## 10. Drift Finding Format

```yaml
drift_finding:
  drift_type: "signal_drift | interpretation_drift | governance_drift | memory_drift | coherence_drift"
  item_ref: ""
  summary: ""
  severity: "low | medium | high | critical"
  evidence_refs: []
  recommended_next_action: ""
  human_review_required: false
```

A drift finding does not itself authorize repair. It identifies what may need attention.

---

## 11. Human Review Need Format

```yaml
human_review_need:
  item_ref: ""
  reason: ""
  decision_needed: ""
  urgency: "low | medium | high | critical"
  blocked_until_decision: false
```

Use this when the system detects a decision boundary that should not be crossed automatically.

Examples include PR creation, merge readiness, branch deletion, canon promotion, destructive schema change, unresolved truth posture, or unclear agent authority.

---

## 12. Recommended Routing Format

```yaml
recommended_routing:
  item_ref: ""
  recommended_target: ""
  reason: ""
  expected_output: ""
  authority_required: false
```

Routing may point toward:

```text
Notion Bridge
AVOT Fabricator
Sovereign Repo Cartographer
Promotion Reviewer
Canon Steward
PR Synthesist
Human Review
Watchlist
No Action
```

---

## 13. No-Action Confirmation Format

```yaml
no_action_confirmation:
  item_ref: ""
  reason: ""
  next_check: ""
```

No-action confirmations prevent silence from becoming ambiguity.

A healthy system should be able to say:

```text
This was checked.
No action is needed now.
Here is why.
Here is when to check again.
```

---

## 14. Verification Posture

Pulse Packets should never overstate verification.

Use:

```text
unverified
```

when the Pulse is based on memory, conversation context, or incomplete inspection.

Use:

```text
partially_verified
```

when some relations or sources were fetched and checked, but not the full scope.

Use:

```text
verified
```

only when all stated sources, relations, and claims in the Pulse were directly checked.

---

## 15. Relationship to D-016

D-016 defines the Hall Heartbeat.

D-017C defines the object the Heartbeat emits.

```text
D-016 asks:
What relationships are weakening?

D-017C records:
What was checked, what was healthy, what was drifting, and what needs attention.
```

---

## 16. Relationship to D-017A — Signal Packets

Pulse Packets detect whether scheduled task outputs became:

```text
Signal Packets
Watchlist Items
No-Action Confirmations
Human Review Requests
```

A Signal Processing Pulse should flag scheduled outputs that remain loose threads.

---

## 17. Relationship to D-017B — Evaluation Packets

Pulse Packets detect whether Signal Packets received interpretation.

They should flag:

```text
Signal Packets without Evaluation Packets
Evaluation Packets without handoff targets
Evaluation Packets stuck in draft
Evaluation Packets recommending authority without human review
Evaluation Packets that should have produced Runtime Packets or Ledger Events
```

---

## 18. Relationship to Runtime Packets

Pulse Packets are not Runtime Packets.

A Runtime Packet records an operation or governed action.

A Pulse Packet records a continuity audit.

However, a Pulse Packet may recommend creation of a Runtime Packet when a real operation occurs or needs to be reflected.

---

## 19. Relationship to Ledger Events

Pulse Packets are not Ledger Events by default.

A Ledger Event records accountability, outcome, evidence, and governance meaning.

A Pulse Packet may recommend a Ledger Event when it detects that an important outcome or governance fact lacks durable accountability memory.

---

## 20. Relationship to Branch Registry

Pulse Packets should audit branches according to D-015.

Key branch questions:

```text
Does every open branch have lifecycle posture?
Does every branch have a known purpose?
Does every active branch have packet or ledger lineage?
Is any branch stale?
Is any branch marked for future action without human authorization?
Is any branch safe to close, preserve, review, or escalate?
```

---

## 21. Relationship to Agent Runtime Pulse Tracker

The Agent Runtime Pulse Tracker can store activity traces.

D-017C defines the richer packet object that interprets those traces as continuity health.

A tracker row may say:

```text
Agent ran.
```

A Pulse Packet says:

```text
The agent ran, produced this, left this unresolved, and this relationship is healthy or drifting.
```

---

## 22. Relationship to TYME

TYME should use Pulse Packets as continuity awareness.

A Pulse Packet gives TYME a current map of:

```text
open threads
weakening relationships
stale decisions
missing relations
human review needs
routing priorities
```

TYME should not treat Pulse Packets as automatic authority.

TYME should treat them as state awareness and attention-routing input.

---

## 23. Relationship to QIL

The Pulse Packet is not QIL.

It is an early sensor layer that reveals coherence problems.

QIL later uses these observations to hold truth posture across the wider lattice.

Pulse Packets can feed QIL by preserving:

```text
conflicts
uncertainties
aging hypotheses
canon candidates
contradictions
coherence decay
minority reports
```

---

## 24. Relationship to Hall

The Hall uses Pulse Packets to answer:

```text
What is healthy?
What is drifting?
What requires review?
What is unresolved?
Where should attention gather?
What should wait?
What does the system currently understand about itself?
```

Pulse Packets give the Hall its continuity health stream.

---

## 25. Required Guardrails

Every Pulse Packet should preserve guardrails appropriate to its scope.

Minimum guardrail set:

```text
Observe before acting.
Report before routing.
Recommend before requesting authority.
Do not claim completion without verification.
Do not treat recommendations as authorization.
Do not collapse uncertainty into canon.
Do not treat no-action as neglect.
Do not allow unresolved drift to disappear.
```

For GitHub-related pulses, include:

```text
No PR creation without explicit authorization.
No merge without explicit authorization.
No branch deletion without explicit authorization.
No workflow, setting, or secret changes without explicit authorization.
```

---

## 26. Example Pulse Packet

```yaml
pulse_packet:
  packet_version: "0.1"
  pulse_id: "pulse-20260605-manual-governance-relation-001"
  emitted_at_iso: "2026-06-05T20:00:00Z"
  pulse_type: "governance_relation_pulse"
  run_mode: "manual"

  scope:
    - "Runtime Packet Registry"
    - "GitHub Operations Ledger"
    - "Branch Registry"

  sources_checked:
    - "D-011 Closeout Note"
    - "Runtime Packet Registry"
    - "GitHub Operations Ledger"

  signals_reviewed: []
  agents_reviewed: []

  packets_reviewed:
    - "runtime-packet-d-008-workflow-convergence-map-write-retry-20260603"

  ledgers_reviewed:
    - "D-008-L1 — Workflow Convergence Map Repository Write"

  branches_reviewed:
    - "restoration/workflow-convergence-map"

  repositories_reviewed:
    - "sovereign-codex/Codex-control-center"

  relations_reviewed:
    - "Packet ↔ Ledger"
    - "Packet ↔ Branch"

  health_findings:
    - item_ref: "runtime-packet-d-008-workflow-convergence-map-write-retry-20260603"
      summary: "Packet has verified Ledger Relation and Branch Relation."
      relation_health: "healthy"
      evidence_refs:
        - "D-011 Closeout Note"

  drift_findings: []

  human_review_needs:
    - item_ref: "restoration/workflow-convergence-map"
      reason: "Branch remains staging / architecture proposal with no PR or merge authorization."
      decision_needed: "Human review before PR evaluation."
      urgency: "medium"
      blocked_until_decision: false

  recommended_routing:
    - item_ref: "restoration/workflow-convergence-map"
      recommended_target: "PR Synthesist"
      reason: "Only if human later authorizes PR-readiness evaluation."
      expected_output: "PR-readiness packet"
      authority_required: true

  no_action_confirmations:
    - item_ref: "GitHub mutation"
      reason: "No mutation authorized."
      next_check: "next branch memory pulse"

  next_pulse_focus: "Signal Packet intake and scheduled task output processing."

  authority_required:
    - "human authorization before PR creation"

  guardrails:
    - "Observe before acting."
    - "No PR creation without explicit authorization."
    - "No merge without explicit authorization."
    - "No branch deletion without explicit authorization."

  verification_state: "partially_verified"
```

---

## 27. Success Criteria

A Pulse Packet is successful when it preserves:

```text
what was checked
what is healthy
what is drifting
what needs human review
what routing is recommended
what remains unresolved
what should not happen without authorization
```

The Pulse Packet should make the system more coherent after it is emitted.

---

## 28. Canonical Storage Recommendation

D-017C should be stored as a versioned Markdown specification in GitHub.

Recommended path:

```text
docs/continuity/D-017C_PULSE_PACKET_SPEC.md
```

Notion should hold a lightweight index page with:

```text
title
status
GitHub path
summary
related documents
current canon posture
```

---

## 29. Surface Boundary

```text
ChatGPT = drafting chamber
GitHub = formal contract / versioned specification layer
Notion = index, registry, dashboard, and relation surface
Hall = future interface across all layers
```

D-017C is the first formal example of this boundary.

---

## 30. Recommended Next Action

After human review, prepare a governed Fabricator runtime packet to write this specification to:

```text
sovereign-codex/Codex-control-center
docs/continuity/D-017C_PULSE_PACKET_SPEC.md
```

No PR, merge, branch deletion, or canon claim should be assumed without explicit authorization.
