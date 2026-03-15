# First MVP Sequence

## Goal

Prove one narrow end-to-end governance loop:

**GitHub issue label -> analyzer -> council debate -> markdown artifact -> GitHub comment -> optional profile PR**

This is enough to prove the control-center organism without overbuilding UI.

## Selected repo

Choose one repository with the highest ambiguity between:
- mission
- operational role
- current implementation
- future intention

Recommended candidates:
- `codex-control-center`
- `codex-net-app`
- one repo where interface and governance boundaries are still blurry

## MVP scope

### Included
- GitHub App registration
- Webhook receiver
- Signature verification
- One tracked repository
- One event route: `issues.labeled` with `needs-council`
- Analyzer pass against:
  - README
  - selected manifest file
  - top-level tree
  - existing repo profile if present
- Four or five council roles
- Markdown debate artifact
- Issue comment synthesis
- Optional PR updating `registry/repos/<repo>.yaml`

### Excluded
- Multi-repo governance
- Rich graph UI
- Full contradiction engine
- Autonomous merge execution
- Cross-platform ingestion
- Large database

## Sequence

### Step 1 — Register the GitHub App
Configure:
- repository contents: read
- issues: read/write
- pull requests: read/write
- metadata: read
- webhooks: enabled

Install on one test repo only.

### Step 2 — Stand up the webhook service
Create a route:
- `POST /webhooks/github`

Service must:
- verify GitHub signature
- parse installation and repository metadata
- normalize event into internal event record
- discard untracked repos

### Step 3 — Seed the registry
Create:
- `registry/repos/<repo>.yaml`

Include:
- category
- status
- mission
- operational_role
- next_leverage_point

This gives the analyzer a canonical baseline.

### Step 4 — Add issue label trigger
When an issue receives `needs-council`:
- fetch issue
- fetch repo profile
- fetch README and selected manifest
- build analyzer summary

### Step 5 — Run council debate
Use the following roles:
- Archivist
- Builder
- Skeptic
- Integrator
- Steward

Each role must produce:
- position
- findings
- concerns
- one proposed next step

### Step 6 — Synthesize recommendation
Produce a structured output:
- summary
- agreement points
- unresolved questions
- contradiction flags
- recommendation
- confidence

### Step 7 — Persist state
Write to:
- `state/events/YYYY-MM-DD/<event-id>.json`
- `state/debates/YYYY-MM-DD/<debate-id>.md`
- optionally update `registry/repos/<repo>.yaml`

### Step 8 — Write back to GitHub
Post issue comment containing:
- concise synthesis
- recommendation
- link or embedded excerpt of debate artifact

Optional:
- open PR to update the repo profile or roadmap markdown

## Success criteria

The MVP is successful when one labeled issue causes the system to:
1. receive and verify the event
2. classify the repo using the registry
3. generate a structured council debate
4. persist an auditable artifact
5. post a useful issue comment
6. optionally propose a profile or roadmap update by PR

## Failure modes to watch
- webhook signature mismatch
- installation token scoping errors
- analyzer hallucinating repo purpose
- debate outputs becoming verbose instead of actionable
- PR generation without clear diff target
- UI work distracting from event reliability

## What comes immediately after MVP
- support `needs-analysis`
- add contradiction detection
- add second tracked repo
- build a basic operator view from existing state files rather than inventing a complex UI first
