# Launch threat register — release candidate v0

**Status:** risks REGISTERED, controls/probes NOT YET INDEPENDENTLY VERIFIED. Owner: `sovereign-codex`; required sign-off: independent security reviewer + human release authority for production. Each threat requires observed mitigation evidence and explicit fail/hold conditions.

| ID / severity | Threat and asset | Required prevention or detection | Required acceptance evidence |
|---|---|---|---|
| T-01 CRITICAL | Public model source/participant prompt injection claims system, Canon or deploy authority | Treat all retrieved content as data; fixed source allowlist; no privileged tools; hard no-authority output schema | CIT-03 to CIT-05 raw negative fixtures, independent review |
| T-02 CRITICAL | Provider/Notion/Cloudflare secret accidentally in client, logs, issues, build | Server-only secret bindings, key rotation/least privilege, scan outputs and CI logs; deny redirects | Secret inventory names/types without values + staging scan and redacted audit |
| T-03 HIGH | Site routes misbound, phantom deployment, source mismatch | Active Cloudflare mapping to exact Git SHA and public content hash; independent GET probes | G1 route/deployment matrix, provenance and rollback |
| T-04 HIGH | Hidden Office private state projected to public | Explicit publish allowlist and review; synthetic/public source separation | Leak-check for personal/private tokens, private page and internal graph fields |
| T-05 HIGH | Misleading Office snapshot freshness or fabricated live agent work | `as_of` and source/run ID, stale warning; no `Done` conflation with work performed | Oct run producer, execution timestamp, receipt destination and outcome |
| T-06 HIGH | Participants assume Share, GitHub issue, local copy or generated answer is Hall receipt | Explicit external carrier labels; `hall_receipt_claimed=false`, manual review only | Uncoached contributor reconstructs boundary and exit |
| T-07 HIGH | Unbounded public model spend, flooding or denial of service | Request payload size, rate ceilings, fixed model budgets, concurrency/timeouts, degraded answer path | Staging rate-limit/429/timeout test with measured ceilings |
| T-08 HIGH | No safe rollback after compromised release | Versioned deployment, rollback owner, tested restore against staging fingerprints | Timed before/after staging rollback record |
| T-09 HIGH | Cross-model provider substitution silently changes authority or provenance | Model ID logged and schema validated on each run; private information not forwarded across providers by default | Positive and negative cross-endpoint conformance |
| T-10 MEDIUM | No contributor license, IP/warranty or disclosure terms | License/CLA or DCO policy defined; explicit security reporting path and payout terms before bounties | Human-approved contribution policy, independent review |
| T-11 MEDIUM | Context-zero reviewer coached by institutional expectation | Blind review start from live Hall, preserve full raw output and uncertainty | 3 independent categories (machine, technical, general outsider) with raw evidence |
| T-12 MEDIUM | Browser session confusion, perceived anonymity or silent persistence | Participant-controlled copy/export, clear session behavior, no permanent identity without consent | Manual browser reload/tab/device state tests |
| T-13 HIGH | Notion R1 independent scope binding compromised | Independently supplied bot/scope, check identity before page acquisition, fixed GET allowlist | [PR #52](https://github.com/sovereign-codex/Tyme-Lab/pull/52) repeat review and separately credentialed test |
| T-14 HIGH | Notion native transport rate budget/cursor produces silent partial corpus | Profile-bounded call budget, opaque cursors, 180/min conservative limit, report truncation | Boundary fixtures at maximum contract envelope, unresolved threads adjudicated |

## Operational stop criteria

- Any CRITICAL finding unresolved: **NO GO** for public model-backed interaction.
- Missing Cloudflare active deployed SHA/rollback or secrets inventory: **NO GO** for a new production runtime rollout.
- Any private token/data observed in public proof: stop, revoke/rotate with operator, preserve sanitized incident record only.
- Missing model-backed run but other static UI safe: do not advertise "live CIT"; seek separate human approval for a reduced static public-beta posture.
- No independent reviewer: cannot count self-authored test as security certification.
- Mark `UNKNOWN` where instrumentation or account-level visibility is absent. No implicit PASS.

## Privacy policy decision points (UNRESOLVED)

Define (i) raw prompt storage on/off (default OFF), (ii) retention TTL for redacted requests/returns (minimum necessary; avoid indefinite personal capture), (iii) abuse log fields, (iv) allowed public source corpus, (v) privacy notice and deletion procedure, (vi) permitted analytics/cookies, (vii) abuse contact/escalation and security report contact, (viii) Cloudflare/proxy log defaults and vendor subprocessors. Do not claim these settings exist before verified.

## Independent assurance gate

Reviewer must produce `producer`, `actual_executed_at`, exact release candidate SHA, environment URL/ID, test vectors, observed responses, pass/fail/unknown for each threat, required mitigation, follow-up retest and named reviewer. Publication authorization and deployment permission remain human-only.
