# Infrastructure matrix — initial commissioning read

Observed and documented on **2026-10-10**. This is a point-in-time partial inventory, not a declaration that production is healthy.

| Surface | Status | Evidence | Missing to close gate |
|---|---|---|---|
| `tymehall.org` zone / DNS | **VERIFIED CONFIGURATION** | Authenticated Cloudflare API: active, unpaused Free Website zone. DNS CNAME `tymehall.org` -> `codex-interface-83q.pages.dev`, proxied. Nameservers `ethan` / `laylah`. Public resolver A/AAAA are Cloudflare edge addresses, not the DNS management records. | Independent HTTP availability and redirect/content parity |
| Public Hall repository -> production | **VERIFIED DEPLOYMENT METADATA / NOT HTTP** | Cloudflare Pages `codex-interface` is GitHub-linked to `sovereign-codex/Codex-interface-`, production branch `main`, deployed commit **exactly** `5342cbaf1098391879a15c7ccca752d3fbc241b8`. Production deploy `8f2b21b4-9541-471f-b2f7-651373591e4f` success 2026-09-11 23:37 UTC and `tymehall.org` alias. | Independent live route/content smoke and tested rollback |
| Public foyer, learning, Office, Contribution | **VERIFIED SOURCE ONLY** | `index.html`, `projections/cit-learning-v0.1/index.html`, `office/state.json`, `contribute/index.html` | HTTP status, content hashes, mobile QA |
| AGI-0001 machine/publication source | **VERIFIED SOURCE + PRIOR LIVE EVIDENCE** | `scrolls/AGI-0001/publication.json`, historical Notion publication return | Fresh release-candidate HTTP verification |
| `/.well-known/tyme.json` | **VERIFIED SOURCE** | Public GitHub file under `.well-known/` | Fresh production GET and JSON parse |
| Pages project and binding scope | **VERIFIED CONFIGURATION** | One project `codex-interface`, created 2026-08-15; `main` production branch; GitHub production/preview deployment enabled; static root `.` with empty build command; no Pages production/preview environment variables listed. Project `fail_open:true` surfaced but relevance to static deployment not established. | Evaluate secure staging strategy and whether Pages Functions exist; no inference backend verified |
| Pages deployment history | **VERIFIED METADATA** | 126 historical deployments (not all individually inspected). Current canonical production succeeded 2026-09-11 on revision `5342cbaf...`; latest overall deployment is a separate successful preview from 2026-09-11. Historical deployments are NOT a tested rollback procedure. | Pick staging rollback candidate, rehearse and preserve before/after evidence |
| Legacy `core.tymehall.org` DNS | **VERIFIED DNS / ORIGIN UNKNOWN** | Unproxied A record points at `68.183.60.196`. Relationship to previously terminated droplets or to current intended runtime is unverified. | Determine current owner/service and whether to retain or retire; do not mutate DNS until proven |
| Security zone settings | **VERIFIED CONFIG / ASSESSMENT OPEN** | SSL/TLS mode `Full`, Always Use HTTPS `off`, minimum TLS `1.0`, security level `medium`. These require qualified hardening review; the settings alone do not establish observed exploitability or actual HTTP redirect behavior. | Verify HTTPS redirect, minimum-client compatibility, edge certificates, origin policy, and possible move to TLS>=1.2 with human change authorization |
| Public Office projection | **SOURCE PRESENT / FRESHNESS BLOCKED** | `office/state.json` has September 8 snapshot ID | Confirm actual Oct 2026 state, regeneration and review; no direct private export |
| Notion Office | **ACCESSIBLE INTERNAL CONTENT** | Existing live Notion HQ, governance packets, scroll and receipt contracts | Redacted connection inventory and independent readback of actual production results |
| Automated Office Phase 2 circulation | **NOT PROVEN** | [BRIDGE-INTAKE-001](https://app.notion.com/p/3f5c51d54b75817b8966ed9875906a42) distinguishes shadow receipts from live scheduler execution | Producer ID, actual timestamp, matching terminal receipt, destination and outcome |
| Cloudflare compute and storage inventory | **VERIFIED EMPTY FOR LISTED SERVICES** | Account API returned **0** Workers scripts, Worker custom domains, zone Worker routes, D1 databases, KV namespaces, Queues, Workflows, Durable Object namespaces and AI Gateways. R2 list returned `10042 enable R2 through Dashboard` (R2 not enabled), not a permission failure. | Decide staging Worker + D1 + secret design; no resources created; confirm whether any external runtime exists |
| Public HTTP | **UNVERIFIED DUE TO TEST-ENVIRONMENT NETWORK/DNS LIMIT** | ChatGPT web fetch couldn't reach custom or Pages domains; container curl reported DNS resolution failure for both. This does **not** prove a site outage. Cloudflare Pages deployment success is build-level evidence, not independent HTTP 200 proof. | Independent internet-connected GET responses, redirects, content hashes and route parity |
| Model-backed deployed CIT | **NOT OBSERVED** | CIT Envelope contract, in-chat prose demonstration and AVOT experiments only | Real authorized provider call, request+return schema, safe runtime and trace |
| GitHub Actions CI | **WORKFLOWS PRESENT** | Hall projection and live-route validation workflow source; cannot infer current green from existence alone | Inspect exact SHA workflow run and status before gate |

## Read-only Cloudflare API reconciliation — 2026-10-10

**Confirmed account:** one accessible Cloudflare standard account, active `tymehall.org` Free Website zone. All calls were GET and returned only metadata; no deployed resources, DNS, secrets, settings, or permissions were modified.

**Authoritative mapping:** `tymehall.org` (active custom Pages domain + proxied DNS CNAME) -> `codex-interface` Pages project -> `sovereign-codex/Codex-interface-` GitHub production branch `main` -> production deployment `8f2b21b4-9541-471f-b2f7-651373591e4f` -> SHA `5342cbaf1098391879a15c7ccca752d3fbc241b8`.

**Unclosed acceptance:** The exact deployed-source chain is established, but fresh HTTP route status, rollback execution, production rate/abuse controls, secret-provisioning strategy and independent sign-off are not. `LC-02` is **PARTIAL** and release gate `G1` remains **OPEN**.

**Minimal next-stage runtime hypothesis, NOT a deployment approval:** keep the existing Pages static project untouched; prepare a separate Worker staging URL (`workers.dev` or scoped preview route), D1 persistence with an idempotency uniqueness constraint, one server-side secret for approved Office delivery, bounded acceptance receipts, and explicit no-retry/no-autonomy boundaries. Provisioning and production mapping require human approval and independent review.

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
