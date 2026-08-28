# HALL_CORE_0_DROPLET_BOOTSTRAP_v0

Status: bounded implementation candidate  
Runtime class: sovereign continuity  
Substrate class: federated cloud Droplet  
Authority ceiling: observe

## Purpose

Seat the first persistent TYME Hall continuity runtime on a replaceable DigitalOcean
Droplet without making DigitalOcean, GitHub, Notion, Cursor, or the machine itself the
institution.

Hall Core 0 owns the smallest reconstructable continuity loop:

```text
verified ingress
-> accepted event identity
-> provenance and authority posture
-> append-only memory
-> evidence coordinates
-> next valid action
```

It does not absorb TYME cognition. It gives cognition and every external participant a
stable place to return evidence.

## First conformance proof

The first runtime performs only:

```text
GitHub webhook
-> verify X-Hub-Signature-256 over exact bytes
-> bind X-GitHub-Delivery as idempotency key
-> reject mismatched replay
-> normalize HALL_EVENT_ENVELOPE_v0.1
-> append envelope and raw payload to SQLite
-> expose read-only health, event, and snapshot projections
-> stop
```

Acceptance does not route, commission, bind, execute, merge, deploy, publish, or promote.

## Ownership boundary

Hall Core 0 owns accepted event identity, append-only event memory, delivery
deduplication, payload hashes, explicit authority posture, node health, backup, and
restoration.

It does not own Git hosting, Notion deliberation, model inference, TYME attention,
coherence interpretation, AVOT execution, Hall publishing, or Canon promotion.

**Isolation law:** never mount the Docker socket into Hall Core and never place an
unrestricted self-hosted runner or arbitrary agent-code executor on the same node as the
accepted event ledger.

## Initial Droplet

Recommended starting profile:

```text
Ubuntu 24.04 LTS
2 shared vCPU
4 GiB RAM
80 GiB SSD
hostname: hall-core-0
DNS: core.tymehall.org -> Droplet public IP
```

This is an event-memory and orchestration foundation, not a model-inference machine.

## Provisioning gates

### Gate A — substrate

1. Add an SSH public key to DigitalOcean.
2. Create the Ubuntu 24.04 Droplet and paste `deploy/hall-core-0/cloud-init.yaml` into
   user data.
3. Enable DigitalOcean automated Droplet backups as a substrate-level recovery layer.
4. Apply a DigitalOcean Cloud Firewall: TCP 22 from a trusted path where practical;
   TCP 80 and TCP/UDP 443 from the internet.
5. Point `core.tymehall.org` to the Droplet.

Cloud-init hardens and prepares the substrate, disables password and root SSH login,
and deliberately does not activate Hall Core. Runtime activation remains a separate gate.

### Gate B — activate reviewed code

From the DigitalOcean console or SSH:

```bash
sudo HALL_DOMAIN=core.tymehall.org \
  /opt/tyme/Codex-control-center/deploy/hall-core-0/bootstrap.sh
```

The script checks out an exact Git ref, records its commit, creates independent webhook
and read tokens, builds the container, starts TLS through Caddy, installs the backup timer,
and waits for readiness.

Secrets remain in `/etc/tyme/hall-core.env` with restricted permissions. They are not
committed, embedded in images, or written into cloud-init.

### Gate C — verify

```bash
sudo /opt/tyme/Codex-control-center/deploy/hall-core-0/smoke-test.sh
```

Expected pre-webhook state:

```text
status: ready
event_count: 0
authority_ceiling: observe
append_only_triggers: true
database_integrity: ok
```

### Gate D — connect one repository

Configure one GitHub webhook:

```text
Payload URL:  https://core.tymehall.org/v0/webhooks/github
Content type: application/json
Secret:       HALL_GITHUB_WEBHOOK_SECRET from /etc/tyme/hall-core.env
Events:       begin with pull_request and workflow_run only
```

Do not connect the whole organization in the first proof. Inspect the first accepted
event before widening the field of view.

## Runtime endpoints

| Endpoint | Access | Effect |
|---|---|---|
| `GET /healthz` | public | process liveness |
| `GET /readyz` | public | secrets, database, and append-only readiness |
| `POST /v0/webhooks/github` | GitHub HMAC | accept one observation event |
| `GET /v0/snapshot` | Hall read token | minimum reconstructable node state |
| `GET /v0/events` | Hall read token | read accepted envelopes |
| `GET /v0/events/{id}` | Hall read token | read one envelope |

## Backup and restore

A daily systemd timer creates an integrity-checked SQLite backup and SHA-256 sidecar in:

```text
/var/lib/tyme/hall-core-backups/
```

Restore remains explicit:

```bash
sudo /opt/tyme/Codex-control-center/deploy/hall-core-0/restore.sh \
  --yes /var/lib/tyme/hall-core-backups/<backup>.sqlite3
```

The local SQLite backups complement, rather than replace, DigitalOcean Droplet backups. Local retention is not geographic redundancy. Encrypted off-node backup becomes a later
bounded capability after the first restore rehearsal succeeds.

## Acceptance evidence

Bootstrap completion requires more than running containers:

1. exact deployed commit;
2. public health and readiness responses;
3. one signed delivery accepted;
4. exact replay producing no second event;
5. mismatched replay rejected;
6. one verified backup;
7. one restore rehearsal;
8. a Hall Event recording deployment evidence and the next valid action.

## Next boundary

Only after observation, replay, backup, and restore pass should Hall Core add a second
adapter or consequence-bearing capability. The next candidate is a bounded Cursor
comparison in which GitHub carries the branch and PR return while Hall Core independently
records the evidence trail.
