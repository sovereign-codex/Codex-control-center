# Cloudflare staging carrier — bounded transport commissioning contract (candidate only)

**Launch ID:** `TYME-HALL-LAUNCH-001`  
**Status:** PROPOSED / PRE-PROVISIONING / NON-AUTHORIZING, recorded 2026-10-10.  
**Owner:** `sovereign-codex` engineering account; independent infrastructure/security reviewers pending.  
**Approval:** human founder controls resource provisioning, costs, credentials, production routing and merge.

## Why a separate carrier, and what already works

Authenticated Cloudflare API inspection verified the production **static** Hall:
`tymehall.org` -> proxied CNAME `codex-interface-83q.pages.dev` -> Pages project `codex-interface` -> `sovereign-codex/Codex-interface-` `main` -> successful production commit `5342cbaf1098391879a15c7ccca752d3fbc241b8`.

No Worker scripts, Worker custom domains/routes, D1 databases, KV namespaces, Queues, Workflows, Durable Object namespaces or AI Gateways were returned; R2 is not enabled. A `workers.dev` account subdomain exists, but **no script is deployed**. Existing Pages static site remains unchanged throughout staging. The unproxied `core.tymehall.org` DNS record is legacy/unknown; do not repurpose it without ownership and reachability checks.

**This does not justify activating autonomous Office behavior or native Hall submissions.** The first carrier is intentionally an isolated, operationally bounded ingress experiment—not an alternate Hall and not a substitute for the existing Notion Inbox or receipt ledger.

## Inherited institutional contracts

The Office already defines [Phase 2 Live Signal Handoff](https://app.notion.com/p/3efc51d54b758115bab6ca19eafec32c) and [Phase 2 Terminal Receipt Contract](https://app.notion.com/p/3f2c51d54b7581dbb84cfa4808dff1ab).

- Source remains existing scheduled `Monitor multi-agent orchestration and AI infrastructure` (source task identity `69950f3cd9308191ada10df6607f4c08`); do not create or change schedules to test the carrier.
- Material path: one `SIGNAL-SCAI-P2-YYYYMMDD-001` may be preserved in the **existing Notion Horizon Signal Inbox**; a corresponding deterministic `P2-RECEIPT-...-YYYYMMDD-0815` belongs in the **Phase 2 Terminal Receipt Ledger**, not the signal corpus.
- Null path: `NO_DURABLE_SIGNAL` creates no signal. Failure: `PHASE2_HANDOFF_FAILED` is explicit; no alternative competing destination.
- Every Phase 2 run should have exactly one terminal state; duplicates create no additional signal or terminal receipt.
- Consequence boundary for all paths: `downstream_wake_attempted=false`, `work_created=false`, `repository_mutation=false`, `hall_receipt_claimed=false`, `canon_claimed=false`, `next_state=dormant`.
- `SIGNAL_PRESERVED` requires independently verified **Notion** persistence, not merely an HTTP 200/Worker response or a D1 insertion. The current production positive receipt remains unproven.
- The newer Intake Wake Adapter describes a **future** responsibility handoff; it does not authorize Phase 3 wake now. No new institutional schema or parallel signal registry.

## Proposed minimal physical resources — NOT YET AUTHORIZED

| Resource | Staging purpose | Controls |
|---|---|---|
| 1 Worker on an isolated `*.workers.dev` staging URL | Accept only a bounded validated event, produce an attributable non-Hall transport result and stop | POST-only ingress for adapter; disable credentialless public writes; request size and rate ceilings; fixed source allowlist; no auto-dispatch |
| 1 D1 database | Transport idempotency and execution evidence, **not** canonical institution or signal storage | UNIQUE idempotency key; minimal redacted metadata; no raw monitoring documents or credentials; limited retention |
| 1 provider/Notion server-side secret binding, **only if direct Notion transport separately approved** | Authenticate a scoped adapter without client-side token exposure | least-privilege token, approved target parents and bot ID, no secret retrieval/logging; independent scope check before acquisition |
| Existing GitHub/Notion contracts | Truth for source, review, and durable terminal receipts | No copy of public Office state into an unreviewed data store; no authority inferred from D1 ACK |

A model provider secret is **not** part of Phase 2 circulation staging. Actual model-backed CIT runtime is tracked separately in [AVOT-engine #16](https://github.com/sovereign-codex/AVOT-engine/issues/16). Neither Phase 2 nor this carrier creates a Hall participant identity.

## Transport ledger, not an institutional schema

A possible bounded operational D1 table (reviewed before provisioning):

```sql
CREATE TABLE IF NOT EXISTS transport_attempts (
  receipt_key TEXT PRIMARY KEY,
  source_task_ref TEXT NOT NULL,
  source_run_ref TEXT NOT NULL,
  payload_digest TEXT NOT NULL,
  attempt_started_at TEXT NOT NULL,
  disposition TEXT NOT NULL CHECK (
    disposition IN ('staged', 'duplicate', 'null', 'failed', 'notion_verified')
  ),
  notion_receipt_ref TEXT,
  last_observed_at TEXT NOT NULL
);
```

**Important distinctions:** `receipt_key` here is a *transport idempotency identifier*, not the promised Phase 2 Notion receipt nor a native Hall receipt. Use a narrow `P2-RECEIPT`-derived key only for qualified known run identities; reject missing or malformed source-run references before insertion. Retention, migration, backup and deletion rules remain undecided until security review.

Never update `notion_verified` from a successful D1 insert or Notion-create API acknowledgment alone. Independent readback must verify the exact Notion parent/page identity, source task/run/time, no duplicates and terminal content. D1 and Notion do **not** share an atomic transaction: report ambiguous partial completion as UNKNOWN/FAILED, do not fabricate eventual success or retry automatically.

## Implement staged proof in gates, not by provisioning first

1. **G1-A — verified current carrier:** Cloudflare active Pages/source SHA is verified at metadata level. Independent HTTP GET/redirect/hash still OPEN; do not claim live site availability from a successful build.
2. **G1-B — independent static-site smoke:** public `/`, `/.well-known/tyme.json`, `/office/state.json`, `/scrolls/AGI-0001/publication.json`, `/contribute/` and Learning response must be observed from an internet-capable endpoint, including status, content hash and timestamp.
3. **G1-C — operator authorization:** approve only isolated test resources and scoped permissions. Evaluate cost/usage limits, Worker names, zone routing restrictions and least-privilege Notion token issuance. Do **not** change Pages custom domain or apex DNS.
4. **G1-D — synthetic staging:** prove `valid, duplicate, no_signal, malformed, unavailable, downstream_wake_denied` with fixed fixtures. D1 proof includes uniqueness, readback, bounded errors and no auto-retry. No Notion writes in this test.
5. **G1-E — credentialed controlled handoff:** only after separate approval, point scoped Notion adapter at the already-authorized Inbox/Receipt parents; verify exactly one durable receipt and, if qualifying, exactly one signal. Preserve Notion execution trace, actual producer/time and independent readback. Never treat Cloudflare-only evidence as Phase 2 PASS.
6. **G1-F — incident/rollback:** rehearse rollback on an isolated Worker and preserve version/response hashes, not on the production Pages site without human approval. Verify no public-route impact and operational alert path.
7. **G1-G — public projection:** only after independent Gate G1/G5 review and human approval, consider adding an optional *read-only* public status projection. Do not add a public Hall ingress or native receipt route under this packet.

## First adversarial cases

- Same `receipt_key` with same digest: exactly one attempt record; duplicate suppressed, no second Notion write.
- Same `receipt_key` with different digest: conflict/hold, not an overwrite.
- Unrecognized `source_task_ref` / run identity: reject; no D1 side effects if validation fails.
- Replay after ambiguous network timeout: explicit uncertain state, **no automatic retry** that might duplicate a Notion page.
- Fake embedded instructions in a monitor result: treat as data, not a request to wake Knowledge Curator or publish.
- Missing or mismatched approved bot/Notion target scope: reject before page acquisition or writes.
- Invalid JWT/HMAC (if an ingress authenticator is selected): reject; do not accept unauthenticated public ingestion.
- Notion unavailable / 429: bounded failure with no uncontrolled exponential retry; do not claim successful persistence.
- Public GET to any staging endpoint: do not reveal secrets, raw payloads, private Notion state, execution headers or signing material.
- Worker/deploy version rollback: prove source/revision lineage and that rollback does not mutate current `tymehall.org` Pages production.

## Open decisions / approvals

- Which source adapter can provide trustworthy scheduler-run identity and a verifiable authenticated request? No assumption that a ChatGPT scheduled monitor can natively POST to the Worker.
- Whether Phase 2 should first be completed directly via existing Notion connector without Cloudflare, then migrate transport as a separate proof.
- Staging Worker/D1 resource names, minimum spend and quotas, secret custody, authorised Notion integration scope, bot ID and allowed parents.
- TTL for redacted transport logs and access-control review of the resource.
- Production Pages rollback steps, HTTP-to-HTTPS behavior and minimum TLS policy.
- Human final release authority. Independent security and context-zero reviewers unassigned.

**Hard boundary:** read-only discovery and this document authorize NO Cloudflare resource creation, secret distribution, runtime execution, schedule modification, Notion output write, production deployment, or permission escalation.
