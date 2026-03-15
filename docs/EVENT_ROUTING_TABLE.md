# Codex Control Center Event Routing Table

This table defines which GitHub events deserve logging, analysis, or full council escalation.

## Event classes

### Class A — Log only
These events should be recorded for state awareness but should not trigger debate.

| Event | Conditions | Action |
|---|---|---|
| `push` | docs-only or trivial file change | append event log, update activity timestamp |
| `pull_request.synchronize` | existing PR, no policy-sensitive files touched | append event log |
| `issues.edited` | title/body typo only | append event log |
| `label.created` | any | append event log |

### Class B — Analyze
These events deserve first-pass analysis but not a full council by default.

| Event | Conditions | Action |
|---|---|---|
| `issues.opened` | any tracked repo | run analyzer, attach lightweight summary, set importance score |
| `pull_request.opened` | touches architecture, schema, or workflow files | run analyzer |
| `push` | README, manifest, schema, or workflow changed | run analyzer |
| `repository.edited` | description/default branch changed | update registry profile |

### Class C — Council escalation
These events trigger formal debate and decision artifacts.

| Event | Conditions | Action |
|---|---|---|
| `issues.labeled` | label = `needs-council` | full council run, issue comment, debate artifact |
| `pull_request.labeled` | label = `needs-council` | full council run, PR review or issue comment |
| `repository.created` | tracked org or tracked installation | create repo profile draft, council classification pass |
| `push` | foundational schema or governance policy changed | council run on downstream impact |
| `issues.opened` | title/body indicates merge/split/archive/foundational change | council run |
| `workflow_dispatch` | manual request | council run with explicit question |

## Routing algorithm

1. Receive GitHub webhook event.
2. Verify signature and installation scope.
3. Normalize event into internal event record.
4. Check tracked repo registry.
5. Determine event class using:
   - repo category
   - files changed
   - labels
   - explicit policy rules
6. Perform one of:
   - log only
   - analyzer pass
   - full council escalation
7. Persist event and outputs to state ledger.
8. Write back to GitHub only if policy threshold is met.

## Escalation guardrails

A full council should not run when:
- the repo status is `archived`
- the event is duplicate/idempotent
- files changed are purely formatting or lockfile updates
- the same question was resolved within the cooldown window
- a human override has set the repo to `parked`

## Required labels

Recommended GitHub labels:
- `needs-council`
- `needs-analysis`
- `contradiction`
- `merge-candidate`
- `park-candidate`
- `canonical-candidate`
- `blocked`
- `foundation-change`

## First live route

For MVP, implement only this route:

`issues.labeled` on a single chosen repo, when label = `needs-council`

Output:
- one analyzer summary
- one council debate markdown artifact
- one issue comment
- optional PR updating the repo profile
