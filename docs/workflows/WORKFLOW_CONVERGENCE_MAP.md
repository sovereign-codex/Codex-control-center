# Workflow A/B/C/D Convergence Map

## Purpose

Map the governed manual pattern validated in Workflow B/C/D onto the future repository-native Workflow A and Codex app workflow.

This document treats Workflow A, B, C, and D as layers of one operating system rather than separate threads.

## Core Thesis

```
event
→ packet
→ registry
→ relation graph
→ review
→ authorized action
→ reflected outcome
```javascript

The Workflow B/C/D sequence has validated the manual and Notion-side version of the same spine that should later govern GitHub Actions and Codex app execution.

## Layer Map

### Workflow A — Repository-Native Automation Spine

Workflow A represents the GitHub-side execution layer:

- GitHub Actions
- workflow_run / workflow_dispatch / repository_dispatch patterns
- branch events
- PR events
- repository artifacts
- Codex app or agent runner execution
- repo-native status checks and logs

### Workflow B — Governed Manual Execution Chamber

Workflow B proved constrained operational behavior:

- request
- attempt
- ledger
- branch
- runtime packet
- PR synthesis
- promotion review
- canon review
- closeout / deletion reflection

### Workflow C — Operational Memory Layer

Workflow C created memory structures:

- Runtime Packet Registry
- Runtime Packet Ingest Protocol
- Registry Linking Pass
- Agent Output Reflection Standard
- dashboard views
- reconstruction validation

### Workflow D — Autonomous Reflection Layer

Workflow D begins discovery and relation-based memory:

- runtime packet auto-ingest draft
- registry auto-linking draft
- agent discovery protocol
- operational command center
- Packet ↔ Branch graph
- Packet ↔ Capability graph
- protocol findings for relation behavior

### Future Codex App Workflow

The future Codex app workflow should combine all layers:

```
Workflow A execution
- Workflow B governance
- Workflow C memory
- Workflow D reflection
```javascript

It should not merely run code. It should emit and consume structured operational evidence.

## Shared Lifecycle Pattern

```
1. Event appears
2. Agent or action receives scoped task
3. Runtime packet is emitted
4. Registry captures packet
5. Relations connect packet to branch, capability, request, attempt, ledger, and review records
6. Review layer evaluates promotion / PR / canon status
7. Action proceeds only if explicitly authorized
8. Outcome is reflected back into memory
9. Next agent discovers state from registries before acting
```javascript

## Shared Runtime Packet Requirements

Future repository-native packets should include:

```
runtime_packet:
	packet_version:
	packet_id:
	emitted_at:
	workflow_id:
	github_run_id:
	event_type:
	actor:
	agent:
	agent_role:
	runtime_mode:
	run_type:
	source_surface:
	target_surface:
	target_repo:
	base_branch:
	working_branch:
	target_path:
	lineage_id:
	parent_packet_id:
	artifact_state:
	canon_posture:
	execution_state:
	verification_state:
	capability_used:
	authorization_basis:
	changed_files:
	commits:
	pr_url:
	issue_url:
	related_branch:
	related_request_id:
	related_attempt_id:
	related_ledger_id:
	related_capability:
	summary:
	next_action:
	do_not_do:
```javascript

## GitHub Actions Boundary Rules

Repository-native automation should obey these rules:

- Prefer explicit `workflow_dispatch`, `repository_dispatch`, or `workflow_run` orchestration for controlled sequences.
- Do not rely on commits made by default automation tokens to recursively trigger downstream workflows.
- Do not let untrusted issue, PR, comment, or external text become unchecked agent instructions.
- Do not grant mutation authority from context discovery alone.
- Do not merge, delete, or promote without explicit governance state.
- Treat GitHub event payloads as evidence, not command authority.

## Notion ↔ GitHub Reflection Points

### GitHub to Notion

GitHub-side actions should reflect:

- workflow run ID
- branch name
- commit SHA
- changed files
- PR URL
- issue URL
- check status
- artifact URLs
- runtime packet
- capability used
- execution / verification state

### Notion to GitHub

Notion should provide:

- latest lineage packet
- branch registry state
- blocked capabilities
- prior attempts
- ledger history
- review status
- human authorization state
- do-not-do constraints

## Review Chain

The review chain remains:

```
Fabricator / Codex Agent
→ PR Synthesist
→ Promotion Reviewer
→ Canon Steward
→ Human or governance decision
→ GitHub action if authorized
→ Reflection back into Runtime Packet Registry
```javascript

## Relation Graph Roadmap

Already started:

```
Runtime Packet Registry ↔ Branch Registry
Runtime Packet Registry ↔ Fabricator Capability Registry
```javascript

Next likely graph edges:

```
Runtime Packet Registry ↔ GitHub Operations Ledger
Runtime Packet Registry ↔ GitHub Write Requests
Runtime Packet Registry ↔ GitHub Write Attempts
Request ↔ Attempt
Attempt ↔ Ledger
Ledger ↔ Branch
Ledger ↔ Capability
PR Packet ↔ Review Packets
```javascript

## Current Protocol Findings to Preserve

### Relation Updates

```
Single relation URL works.
Comma-separated multi-relation URL is accepted but does not append.
Do not overwrite verified relations.
Fetch verification is required after every relation update.
```javascript

### Tool Reliability

```
Search + fetch + update currently works better than SQL-style querying.
Some tool schemas may list query functionality that is not callable in the current execution surface.
Treat tool availability as operationally variable.
```javascript

### Governance

```
Discovery is not authorization.
Registry linkage is not canon promotion.
Packet persistence is not verification.
Verification is not merge approval.
Review is not action authority unless explicitly scoped.
```javascript

## Agentic Workflow Guardrails

Future Codex app workflows should include protections against:

- prompt injection from issue bodies or PR descriptions
- unsafe interpretation of comments as commands
- unreviewed file mutations
- recursive workflow loops
- secret exposure
- branch deletion without explicit approval
- canon promotion by implication
- silent drift between Notion memory and GitHub state

## Codex App Implementation Sequence

### Phase 1 — Packet Emission

Create a GitHub Action or Codex runner that emits a runtime packet after every run.

### Phase 2 — Repo Artifact Persistence

Persist packet as a repo artifact or committed diagnostic file when safe.

### Phase 3 — Notion Reflection

Send or manually ingest the runtime packet into the Runtime Packet Registry.

### Phase 4 — Relation Linking

Link packet to branch, capability, request, attempt, and ledger records.

### Phase 5 — Review Routing

Route to PR Synthesist, Promotion Reviewer, or Canon Steward depending on packet state.

### Phase 6 — Authorized Mutation

Only after review and explicit authorization should the system create PRs, merge, delete branches, or update canonical files.

### Phase 7 — Reflection Closeout

Every final action must emit a closeout packet and update registries.

## Current Evaluation

The system is currently best described as:

```
Operational Memory Graph — Alpha
```javascript

It has working registries and verified relation edges, but it is not yet fully autonomous because:

- multi-relation append format is unresolved
- SQL-style registry queries are unreliable in the current surface
- Packet ↔ Ledger relations are not yet installed
- repository-native Workflow A integration has not yet been mapped into files/workflows
- GitHub mutation authority remains intentionally constrained

## Canon Posture

Staging / architecture convergence map.

This document maps the operating model. It does not authorize new GitHub mutation, branch deletion, PR creation, merge, or canonical promotion.