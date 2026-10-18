# Phase 2 source → Notion transport: evidence reconciliation and next-run acceptance

**Launch:** TYME-HALL-LAUNCH-001 · **Status:** review-only, 2026-10-10 · **Authority:** none
**Owners:** technical coordination `sovereign-codex`; human release authority separate; independent Office/provenance reviewer still required.

## What has actually occurred

1. A one-shot ChatGPT automation `Notion transport probe`, task ID `6ac989a44cd88191b72fad2ff76fefe6`, is now disabled. The scheduler registry reports an October 9 Arizona / October 10 UTC last run; the stored task prompt directed one **test-only** `NO_DURABLE_SIGNAL` write using the Notion connector.
2. A distinct [Notion child receipt, P2-RUNTIME-RECEIPT-20261009-002](https://app.notion.com/p/3f5c51d54b758148aa32d4c533230db6), exists under the already-established [Phase 2 Terminal Receipt Ledger](https://app.notion.com/p/3f2c51d54b75817fa994ff3ee38d24cc). The parent and child were subsequently retrieved through independent connector readback and a provenance addendum was appended.
3. The [Knowledge Curator proof-ceiling review](https://app.notion.com/p/3f5c51d54b7581bdad80d6c85f427b9b) classifies this test receipt **REQUIRES_REVISION**; it does not represent a production qualifying signal, Phase 2 completion or independent conformance certification.
4. Historical test task ID `6ac989a44cd88191b72fad2ff76fefe6` **is not** the enabled production monitor task ID `69950f3cd9308191ada10df6607f4c08`. Historical `P2-RUNTIME-RECEIPT-20261009-002` is **not** a conforming production `P2-RECEIPT-69950f3cd9308191ada10df6607f4c08-YYYYMMDD-0815` receipt.
5. The one-shot receipt has an independent historical readback addendum with source-task distinction and missing `next_review_posture: continue_monitoring` noted as later documentation, not as an original observed runtime field. Original human authorization link and platform execution ID remain unavailable.

**Confirmed narrow result:** a controlled scheduled ChatGPT → Notion child write happened once, with later page retrieval. **Still not proven:** positive signal, full deterministic production receipt, repeated scheduled reliability, authenticated direct HTTP to Cloudflare, Notion actor identity, Office wake, or durable circulation production readiness.

## The first runtime crossing is already an existing connector

The deployed public Hall is Cloudflare Pages, but there is no Worker/D1 carrier in the inspected account. A Worker is **not required** for the first valid Phase 2 production observation. Do not create a new external HTTP dependency until a source operator can sign and attest to an actual scheduler-run envelope. The supported first crossing is:

```text
existing enabled ChatGPT monitor
      |
      | material finding OR null OR bounded error
      v
existing Notion Horizon Signal Inbox (material only)
      +
existing Notion Phase 2 Terminal Receipt Ledger (one state per run)
      |
      v
independent exact-receipt + source-run readback
      |
      v
STOP: no Knowledge Curator wake, Work, GitHub, Hall receipt or Canon
```

**No new scheduled task, policy, phase-3 agent, signal schema, native Hall ingress or production Work.**

## Production task facts to pin and inspect

- Title: `Monitor multi-agent orchestration and AI infrastructure`
- Scheduler ID: `69950f3cd9308191ada10df6607f4c08`
- Enabled at inspection: `true`
- Stated recurrence: weekly Monday 08:15 America/Phoenix
- Next expected scheduled occurrence after Oct 10: **Monday October 12, 2026, 08:15 Arizona**.
- Human-authored monitor text already includes Phase 2 signal qualification, duplicate suppression, exact Notion destination parent IDs, required receipt fields, null/failure behavior, and a no-downstream-wake stop boundary. Leave the existing schedule/prompt unchanged until separately authorized.
- **Scheduled time is not actual execution time.** Record the observed scheduler last-run timestamp separately from the terminal receipt's `scheduled_run`. If platform run identity or connector actor ID is not available, mark it UNKNOWN rather than synthesizing one.

## Preflight and observed acceptance procedure (read only)

1. **Before run:** Snapshot the enabled task ID, prompt revision, recurrence, prior `last_run_time`, current live terminal receipt child IDs, and current Horizon Inbox signal child IDs. Do not create a receipt during baseline capture.
2. **After run:** Inspect the *actual* scheduler last-run marker/available task result, search the existing receipt ledger for deterministic identity `P2-RECEIPT-69950f3cd9308191ada10df6607f4c08-20261012-0815`, and inspect the Horizon Inbox for `SIGNAL-SCAI-P2-20261012-001`. Use independent Notion exact parent/child readback, not the model narrative alone.
3. **If `NO_DURABLE_SIGNAL`:** 0 new Horizon Signal children; 1 uniquely identified receipt with evidence-based reason, `next_review_posture: continue_monitoring`, all stop flags false and `next_state:dormant`. A valid null receipt tests observability **but not** the required positive signal preservation.
4. **If `SIGNAL_PRESERVED`:** 1 qualifying signal child under approved Inbox, source/monitor identity and publication dates, 1 matching terminal receipt under receipt ledger, independently verified content and no unintended wake. Compare source monitor output to persisted payload; score positive proof only after independent review.
5. **If `PHASE2_HANDOFF_FAILED`:** 0 newly inferred signal or alternative destination; 1 terminal failure receipt if the ledger was reachable, otherwise a bounded task-result failure. Missing/ambiguous source or receipt remains UNPROVEN. **Do not manually fabricate a receipt to make the run look successful.**
6. **If duplicate:** preserved count remains unchanged; acknowledge existing exact receipt and compare payload. Do not assume duplicate suppression based only on a search-before-create instruction.
7. **For every observed run:** store producer, actual runtime clock if exposed, scheduled identity, source task and output references, exact receipt ID/Notion parent+child URL, outcome, reviewer, observed `authority_effect:none` and a candid evidence ceiling.
8. **Never conflate:** synthetic local SQLite replay `SYNTHETIC_ACCEPTED`, Notion page creation acknowledgment, Notion independent readback, provider scheduler execution identity, or a material `SIGNAL_PRESERVED` production result.

## Available offline gating harness

`python3 -m unittest discover -s launch/TYME-HALL-LAUNCH-001 -p 'test_phase2_*.py' -v`

`phase2_replay.py` reuses the Phase 2 terminal field set and enforces the already-specified production monitor/deterministic receipt identifiers, no-authority flags, positive/null/failure pathways, and conflict-free append-only local SQLite replay. It cannot authenticate a ChatGPT task, confirm Notion delivery, prove a Worker/D1 resource, or validate an actual signal's materiality.

When an authenticated source adapter is chosen, require cryptographic producer identity and bounds **before** accepting an event. A task ID within JSON is NOT a credential. Do not assume the ChatGPT automation can sign arbitrary HTTP requests; this remains a source transport capability gap.

## Source credential/Worker decision sequence

- **No additional permission is needed** for read-only Cloudflare resource discovery or for offline test coverage.
- **Current valid next step:** independently inspect the existing Monday run's state and Notion output; repair receipt provenance if needed without altering the original outcome.
- **If required:** separately commission a credentialed, scoped staging sender that can actually authenticate to an isolated Worker endpoint. Do not mint a production secret or ask the model to reveal Notion integration credentials.
- **Only after source/auth/retention controls are reviewed:** seek explicit human approval to create one isolated Worker, one D1 database, and scoped server-side secret; preserve the existing Pages custom domain without modification.
- **No automatic Phase 3:** intake-wake and Knowledge Curator activation are different authority transitions and remain on hold.

## Evidence and acceptance state

| Item | Status |
|---|---|
| One-shot scheduled automation → Notion null receipt | **Observed historical** |
| Independent parent/child Notion readback (subsequent session) | **Observed historical** |
| Original one-shot exact authorization source + unique scheduler run ID | **Unverified** |
| Historical receipt conforms to governing production deterministic identity | **No (test-only identity)** |
| Production monitor enabled and prompt has Phase 2 contract | **Verified at scheduler registry inspection** |
| Positive production Phase 2 signal + receipt under correct parents | **Not yet observed** |
| Offline replay/negative/idempotency checks | **CI-verified synthetic behavior** |
| Cloudflare HTTP ingress from scheduled ChatGPT monitor | **Not demonstrated** |
| New Worker / D1 / secret provisioned | **No** |
| Production Phase 2 and Hall release gates | **Remain OPEN** |
