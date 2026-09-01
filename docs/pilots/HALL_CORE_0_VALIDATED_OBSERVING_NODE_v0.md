# Hall Core 0 — Validated Observing Node v0

Status: validated
Node: `hall-core-0`
Authority ceiling: `observe`

## Milestone

Hall Core 0 has crossed from installation/bootstrap into a validated observing-node state.

Validated gates:

- live HTTPS endpoint at `core.tymehall.org`;
- authenticated GitHub webhook intake using HMAC SHA-256;
- first external `ping` accepted into append-only event storage;
- duplicate delivery redelivery suppressed without advancing sequence;
- first real repository `push` accepted as a distinct event;
- append-only database triggers present;
- database integrity reports `ok`;
- runtime survives deliberate container restart with event state preserved;
- integrity-checked SQLite backup service executes successfully;
- generated backup SHA-256 verifies successfully;
- service identity remains `tyme` and operator identity remains `steward`;
- consequence authority remains disabled: no dispatch, execution, publishing, or promotion.

Observed durable state after the first real push and restart:

```text
event_count: 2
last_sequence: 2
last_event_id: evt:github:ffd10902-a5a3-11f1-92a0-12ac08fc799c
authority_ceiling: observe
database_integrity: ok
append_only_triggers: true
```

## Read-only inspection surface

The Hall Core runtime already exposes bearer-token-protected read projections:

- `GET /v0/snapshot`
- `GET /v0/events?limit=N`
- `GET /v0/events/<event_id>`

These routes are read-only projections over the append-only event store. They do not grant dispatch, execution, publishing, repository mutation, workflow dispatch, work promotion, participant binding, execution authorization, or canon promotion.

The next gate is to validate these read projections against the two accepted live events before adding any richer routing or consequence-bearing behavior.
