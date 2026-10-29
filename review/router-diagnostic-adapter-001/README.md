# Router diagnostic adapter v1 — review candidate for issue #25

Standing: **PORTABLE_CORE_IMPLEMENTED / OFFLINE_TESTED / NOT_REGISTERED / NOT_EXECUTED**.
Independent review is unassigned and has not occurred. This directory is not a
ChatGPT tool, a deployed service, a live authorization, or a completion receipt.
Related: https://github.com/sovereign-codex/Codex-control-center/issues/25

## Supported integration decision

Use a dedicated, OAuth-protected remote MCP endpoint with Streamable HTTP and
exactly one write tool: `invoke_router_diagnostic_v1`. Attach the portable core
to a reviewed MCP SDK resource-server handler. It performs no scheduling,
routing decisions, model calls or downstream execution. Reuse the existing Router.

The managed GitHub connector currently exposes no repository-dispatch operation.
Repository changes cannot add an action to that connector. A custom GPT Action
would be a separate GPT surface; it would not register this tool in the current
conversation. A Responses API orchestrator is unnecessary. No new host or paid
service is selected or provisioned by this candidate.

Official documentation inspected 2026-10-29:
- https://developers.openai.com/api/docs/guides/custom-mcp-server
- https://developers.openai.com/plugins/build/auth
- https://docs.github.com/en/rest/repos/repos#create-a-repository-dispatch-event

The MCP endpoint authenticates the end user with OAuth. A separate server-side
GitHub credential broker authenticates the fixed GitHub request. Neither proves
the existing downstream Codex-net-orchestrator App works. Do not extract tokens
from the managed connector or copy existing repository secret values.

## Implemented versus remaining

Implemented: strict bounded input, a versioned synthetic template, two pinned
disabled-policy reads with Git blob recomputation, source revision checks, exact
request grant binding, SQLite reservation committed before POST, fixed HTTPS
destination with no redirects/retries, safe response projection, and a separate
offline evidence-consistency verifier. The one-slot experiment lock survives
restart and blocks all new IDs after reservation. There is deliberately no reset.
The exact accepted input bytes and exact outgoing request bytes/digest are kept
separately from GitHub's later event bytes.

Remaining deployment work: MCP SDK HTTP wrapper; OAuth identity provider and
signature/issuer/audience/expiry/scope verification; secret broker; durable host
and storage; independent evidence acquisition; registration and deployment review.
These are explicit integration seams, not implemented authentication. Do not
expose `Principal`, `Approval`, `Github`, evidence files or service configuration
as tool arguments. There is no runnable live-dispatch CLI in this package.

## Reviewed baseline to recheck, not an execution approval

| Item | Observed identity |
| --- | --- |
| CCC main commit | `d8230a2f6fbc8c633c470f8446078f5f8d41abfb` |
| AVOT main commit | `c6bde43df8077fe4857e359ef35088e610f0a364` |
| CCC policy blob | `febfe44f69ca1c0c02c5394d5edfafb163a939a5` |
| AVOT policy blob | `0b909340619f4ad4519c1aace97fdc72366de2b5` |
| Router workflow blob | `12cee1137514f49c886ecb4aae99bf90673f4545` |

Both disabled policies are unchanged. No production workflow, admission list,
activation pin or receiver was edited. No root or nested AGENTS.md appeared in
the inspected repository tree. Only this review directory is staged.

## Offline validation

From the repository root, Python 3.12+ and Node 24:

```sh
python -m unittest discover -s review/router-diagnostic-adapter-001/tests -v
node review/router-diagnostic-adapter-001/check_router.mjs
```

The Node check imports the actual pure Router contract and passes the generated
synthetic template through it with the checked-in disabled policy. It expects
exactly `policy_disabled`, `receiver_unverified`, and `sender_not_allowed`; it
never invokes the Actions entry point, executor or credential code. These holds
are expected with empty admissions and an unverified receiver. A malformed event
hold would not satisfy the check. Python tests include tampered evidence and
unintended downstream transport. Tests use temporary databases and fake network
services; test success is not a live diagnostic receipt.

## Exact registration and deployment requirements

1. Assign an implementation owner and an independent reviewer. Review the exact
   candidate commit and dependencies. Select a host only through a separate
   reviewed deployment decision. Keep this service separate from Hall orchestration.
2. Serve an HTTPS `/mcp` endpoint using a maintained MCP SDK's Streamable HTTP
   transport. Enforce request size at the HTTP boundary and reject duplicate JSON
   keys before SDK parsing. Register only `tool-definition.json`. Tool annotations
   are hints, not authorization. Serialize the validated two-field argument object
   as the core's input; retain the raw bounded MCP envelope separately only under
   a reviewed redaction policy. Never log Authorization headers or HTTP debug data.
3. Publish `/.well-known/oauth-protected-resource` with the exact resource URL,
   approved authorization server and `router.diagnostic.invoke` scope. Publish
   OAuth authorization-server metadata, authorization/token endpoints, JWKS and
   PKCE S256 support. Use an established identity provider. Configure CIMD if
   supported, otherwise reviewed DCR/static client setup. Copy the exact callback
   URL and client metadata shown by ChatGPT into the allowlist; do not guess them.
   Validate signature, issuer, resource/audience, exp/nbf and scope on every call.
   Return HTTP 401 with a resource-metadata WWW-Authenticate challenge on failure;
   provide MCP `_meta["mcp/www_authenticate"]` when a tool auth challenge is needed.
   OAuth identity alone does not prove a particular chat or user approval message.
   If proving the ChatGPT client is required, validate its documented client mTLS
   certificate at ingress and bind OAuth client identity; do not trust forwarded
   identity headers from the public Internet.
4. Construct `Principal` only from verified server request context. Map the stable
   OAuth subject to the approved operator. Configure `Approval` outside the tool:
   exact diagnostic ID, expected CCC and AVOT commits, expected GitHub sender ID,
   exact template digest, sanitized authorization/review/freeze references, and
   expiry within one hour. Independent reviewer must approve the precise template
   and source revision; the present task does not supply a live grant. Missing
   grant leaves the service inert. Do not provide a tool that grants itself access.
5. Provision server-side GitHub authentication through a reviewed secret store.
   Dispatch needs a repository-scoped GitHub App installation token with Contents
   write for CCC; that permission is broader than one POST, so constrain egress and
   keep credentials private. Readback uses a separate read-only connection with
   Contents read and Actions read for both repositories. Token minting and rotation
   are infrastructure responsibilities, not conversation arguments. Never expose
   keys, PATs, JWTs or installation tokens in output, exceptions or logs.
6. Mount one persistent SQLite database for the whole experiment. Restrict directory
   permissions to 0700 and database to 0600. Use a single host/shared local DB,
   not per-replica ephemeral storage or network filesystems. Database loss, restore
   rollback or write uncertainty is a stop requiring investigation; never initialize
   a replacement to bypass a consumed slot. Keep tombstones for the full diagnostic
   lifetime. Use backups with an operator recovery procedure. A crash after reserve
   and before POST intentionally consumes the slot. This is at-most-one adapter
   attempt, not exactly-once GitHub delivery.
7. Coordinate a source/policy freeze on both main branches and audit dispatch
   listeners before admitting the request. GET then POST is not atomic. Compare
   snapshots again immediately in the deployment wrapper before calling invoke;
   stop on any change. After reservation, timeout/5xx/redirect/unexpected status
   means uncertain; no retries or new IDs, including at proxy/SDK/client layers.
8. In ChatGPT web: Plugins → plus → Add custom MCP server → enter reviewed HTTPS
   Server URL and OAuth configuration → review warning → Create as a plugin →
   install in the permitted workspace. Workspace access and settings must be
   verified; this package does not establish them. Confirm tool discovery exposes
   the exact two-field schema. First run registration/auth rejection checks with
   no grant configured. No dispatch is needed to verify discovery and fail-closed auth.
9. Only after independent implementation review, host/auth registration review,
   recorded freeze and separately authorized exact live payload: provision one
   expiring grant and allow one call. Leave both repository policies disabled.

## Independent readback procedure (read-only)

Use an independent operator/connection, not the dispatch response or adapter's
assertions. Record acquisition time, source URLs, run/attempt/artifact IDs and
SHA-256 digests for the downloaded bytes. Preserve the sealed request bytes from
SQLite separately. HTTP 204 supplies no run ID and does not establish arrival.

After a separately authorized attempt, the following are read-only examples using
an already configured `gh` connection. Do not put credentials in commands. Set
`RUN_ID` only after inspecting candidate runs; `ARTIFACT_ID` comes from that run's
artifact inventory. Scope/paginate run inventory to the recorded attempt window.

```sh
gh api 'repos/sovereign-codex/Codex-control-center/actions/workflows/control-center-router.yml/runs?event=repository_dispatch&per_page=100' > runs.json
gh api "repos/sovereign-codex/Codex-control-center/actions/runs/$RUN_ID/attempts/1" > run.json
gh api --paginate "repos/sovereign-codex/Codex-control-center/actions/runs/$RUN_ID/attempts/1/jobs?per_page=100" --jq '.jobs[]' > jobs.jsonl
gh api "repos/sovereign-codex/Codex-control-center/actions/runs/$RUN_ID/artifacts" > artifacts.json
gh api "repos/sovereign-codex/Codex-control-center/actions/artifacts/$ARTIFACT_ID/zip" > observations.zip
```

Artifact download is a separate read-only flow that may follow GitHub's signed
download redirect through the trusted connector/CLI. The dispatch transport never
follows redirects. Treat archives as untrusted: inspect entries without extraction,
reject duplicates/paths/oversized entries, and load only the four expected JSON
files (max 256 KiB each, archive max 2 MiB). Record any `execute-*` file as unexpected.
`verify_bundle.py` implements that bounded archive loading. Put the independently
acquired files in a private evidence directory with `request-input.json`, sanitized
`approval.json` matching the Approval dataclass, `run.json`, `jobs.jsonl`, the selected
`artifact.json`, `observations.zip`, and independent `after-snapshot.json`, then run:

```sh
python review/router-diagnostic-adapter-001/verify_bundle.py /path/to/evidence
```

Use `readback.verify` with run metadata, the full attempt-1 jobs list, exact artifact
name, those byte buffers and a fresh independent `Github.snapshot()` using only
read credentials. The verifier checks exact payload, sender, run/attempt, selected
source, event byte digest, structured hold, and skipped token/forwarding steps.
Its output is **consistency only** until the independent reviewer authenticates
the acquisition chain. Fabricated but internally consistent offline fixtures are
not live proof. A failed Actions run is expected; a green run is not acceptance.

Also inventory both repositories' repository_dispatch runs and relevant ledgers
from before the attempt through the declared observation end (recommend >=10 min
after Router completion). Inspect CCC Dispatcher `engine_handoff`, AVOT
`avot_execution`, CCC `handoff-ledger/v1/` claims/outcomes and AVOT receiver receipt
paths from its pinned source. Correlate by exact diagnostic ID, not merely run
time. Paginate completely; compare before/after trees and inspect changed records.
Missing access, artifacts, receiver-path discovery or incomplete pagination means
unknown. Record window endpoints and coverage; bounded absence is not global proof.
Re-read both disabled policies and revisions. This package does not automate that
inventory and does not report downstream execution verified or absence proven.

The independent final receipt must keep `dispatch_transport`, `router_arrival`,
`router_policy`, `custom_app_authentication: not_tested`,
`downstream_execution: not_tested`, and `authority_effect: none` separate. Do not
close issue #25 or any launch/inference gate on offline tests or registration alone.
