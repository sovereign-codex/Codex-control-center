# Infrastructure matrix — initial commissioning read

Observed and documented on **2026-10-10**. This is a point-in-time partial inventory, not a declaration that production is healthy.

| Surface | Status | Evidence | Missing to close gate |
|---|---|---|---|
| `tymehall.org` DNS | **VERIFIED DNS ONLY** | Cloudflare NS `ethan.ns.cloudflare.com` + `laylah.ns.cloudflare.com`; A `188.114.97.7`/`188.114.96.7`, AAAA present in contemporaneous DNS lookup | Inspect Cloudflare zone, origin/deploy and active mappings |
| Public Hall repository | **VERIFIED SOURCE** | [Codex-interface-](https://github.com/sovereign-codex/Codex-interface-) @ `5342cbaf1098391879a15c7ccca752d3fbc241b8` | Verify domain deploy SHA and accessible HTTP |
| Public foyer, learning, Office, Contribution | **VERIFIED SOURCE ONLY** | `index.html`, `projections/cit-learning-v0.1/index.html`, `office/state.json`, `contribute/index.html` | HTTP status, content hashes, mobile QA |
| AGI-0001 machine/publication source | **VERIFIED SOURCE + PRIOR LIVE EVIDENCE** | `scrolls/AGI-0001/publication.json`, historical Notion publication return | Fresh release-candidate HTTP verification |
| `/.well-known/tyme.json` | **VERIFIED SOURCE** | Public GitHub file under `.well-known/` | Fresh production GET and JSON parse |
| Public Office projection | **SOURCE PRESENT / FRESHNESS BLOCKED** | `office/state.json` has September 8 snapshot ID | Confirm actual Oct 2026 state, regeneration and review; no direct private export |
| Notion Office | **ACCESSIBLE INTERNAL CONTENT** | Existing live Notion HQ, governance packets, scroll and receipt contracts | Redacted connection inventory and independent readback of actual production results |
| Automated Office Phase 2 circulation | **NOT PROVEN** | [BRIDGE-INTAKE-001](https://app.notion.com/p/3f5c51d54b75817b8966ed9875906a42) distinguishes shadow receipts from live scheduler execution | Producer ID, actual timestamp, matching terminal receipt, destination and outcome |
| Cloudflare Workers/Pages/Routes/D1/KV/secrets | **UNKNOWN** | No Cloudflare account-level connector available at commissioning | Scoped operator resource inventory; redacted bindings and roles, no secret values |
| Public HTTP | **UNVERIFIED** | Web open and sandbox curl attempts returned inability to fetch; environment/network limitation possible; no outage inference | Independently inspect response headers, status, redirects, content, health and geographic behavior |
| Model-backed deployed CIT | **NOT OBSERVED** | CIT Envelope contract, in-chat prose demonstration and AVOT experiments only | Real authorized provider call, request+return schema, safe runtime and trace |
| GitHub Actions CI | **WORKFLOWS PRESENT** | Hall projection and live-route validation workflow source; cannot infer current green from existence alone | Inspect exact SHA workflow run and status before gate |

## Operator verification procedure

Use a trusted, authenticated Cloudflare operator with **read-only account visibility first**. Never paste tokens into public issues, logs, browser query strings or chat. Collect account-visible resource IDs, routes, Pages project names, Worker script names, bindings **names/types only**, zone ID with sensitive details redacted, D1 existence and schema descriptions, deployment versions, CI source mapping, authorization boundary, rollback procedure, and staging URL. A successful DNS resolution is NOT runtime acceptance.

From an independent internet-connected environment, GET (not only HEAD) at least:

```text
https://tymehall.org/
https://tymehall.org/.well-known/tyme.json
https://tymehall.org/office/state.json
https://tymehall.org/projections/cit-learning-v0.1/
https://tymehall.org/contribute/
https://tymehall.org/scrolls/AGI-0001/
https://tymehall.org/scrolls/AGI-0001/publication.json
```

For each: UTC timestamp, observed HTTP status, redirect chain, content-type, body SHA256, meaningful HTML title/JSON schema, current deployment fingerprint if accessible, and examiner/tool. Note `UNKNOWN` instead of inferring from repository content.

Cloudflare verification closes only with an independently reconstructable deployment mapping: `domain route -> active Cloudflare resource -> revision -> Git commit`, controls review, and a demonstrated staging rollback (before and after fingerprints, restore elapsed time, producer and receipt).
