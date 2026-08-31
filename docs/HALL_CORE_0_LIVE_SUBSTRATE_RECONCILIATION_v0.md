# HALL_CORE_0_LIVE_SUBSTRATE_RECONCILIATION_v0

Status: review candidate  
Observed checkpoint: 2026-08-31  
Node: `hall-core-0`  
Authority ceiling: observe

## Purpose

Reconcile the reviewed Hall Core 0 deployment contract with the first live DigitalOcean
substrate before runtime activation.

This document records what was actually verified on the node, which repository owns the
contract, and which identities may operate or serve the runtime. It does not authorize
webhook activation, repository mutation, dispatch, execution, publishing, or promotion.

## Canonical ownership

The Hall Core 0 infrastructure and runtime contract remains owned by:

```text
sovereign-codex/Codex-control-center
```

The repository already contains the bounded service, exact-byte GitHub webhook
verification, append-only SQLite ledger, Caddy boundary, backup and restore procedures,
and conformance workflow. Hall Core therefore does not require a new repository.

## Live checkpoint

The first live node was verified with:

```text
provider: DigitalOcean
region: nyc3
hostname: hall-core-0
operating system: Ubuntu 24.04 LTS
vCPU: 2
RAM: 4 GiB
Disk: 80 GiB
public IPv4: provisioned
planned DNS: core.tymehall.org
```

Verified perimeter:

```text
UFW: active
incoming default: deny
outgoing default: allow
allowed: 22/tcp, 80/tcp, 443/tcp, 443/udp
Fail2ban: enabled and active
Fail2ban jail: sshd
SSH password authentication: disabled
Direct root SSH login: disabled
```

Verified human access:

```text
operator user: steward
authentication: iPhone-held ED25519 key through Termius
sudo: separate local steward password
fresh key-only login after SSH hardening: passed
sudo identity boundary: passed
```

Verified runtime baseline:

```text
Docker: present
Git: present
Caddy host package: absent by design; delivered as a constrained container
Hall identity file: /opt/hall/config/hall-core.env
Runtime not activated
DNS not connected
GitHub webhook not connected
```

## Identity separation

### `steward` — human operator

`steward` is the only routine SSH administration identity.

It may:

- authenticate with the approved ED25519 key;
- inspect the node;
- invoke reviewed administrative operations with `sudo`;
- perform explicit activation and recovery gates.

It must not:

- run persistent application processes as itself;
- hold a GitHub write token merely to deploy public reviewed code;
- become an autonomous worker identity;
- bypass evidence, backup, or review gates.

### `tyme` — runtime service identity

`tyme` owns the canonical repository checkout and runtime-readable secret group boundary.

It must be:

- locked;
- non-login;
- absent from `sudo`;
- absent from the `docker` group;
- unable to authenticate through SSH.

The human operator uses `sudo` for bounded Docker and systemd actions. The Hall Core
container never receives the Docker socket.

## Canonical paths

```text
/opt/hall/config/hall-core.env       non-secret node identity
/opt/hall/runtime                    local runtime coordination boundary
/opt/hall/state                      local non-ledger node state
/opt/hall/logs                       node-level operational evidence
/opt/hall/backups                    operator-visible backup coordination

/opt/tyme/Codex-control-center       canonical reviewed repository checkout
/etc/tyme/hall-core.env              runtime secrets; root:tyme 0640
/var/lib/tyme/hall-core              append-only runtime data
/var/lib/tyme/hall-core-backups      integrity-checked local SQLite backups
```

`/opt/hall` describes the node. `/opt/tyme` carries reviewed runtime source. `/var/lib/tyme`
holds mutable service data. `/etc/tyme` holds secrets. These boundaries must not be
collapsed into one repository-owned directory.

## GitHub authentication posture

Hall Core does not need a GitHub personal access token, deploy key with write access, or
self-hosted runner for the first activation.

The repository is public, so the node may perform a read-only HTTPS clone and exact-ref
fetch. GitHub later sends signed webhook observations to Hall Core. This preserves the
separation:

```text
GitHub stores reviewed source
-> steward explicitly activates an exact commit
-> tyme owns the checkout
-> Hall Core accepts signed observations
-> Hall Core does not write back or execute arbitrary repository code
```

## Existing-node reconciliation

For a manually provisioned node that already has a verified `steward` account, review and
run:

```bash
sudo HALL_REPO_REF=<reviewed-commit-or-ref> \
  ./deploy/hall-core-0/reconcile-live-substrate.sh
```

The script is intentionally separate from runtime activation. It:

- verifies the human operator and sudo membership;
- creates or hardens the locked `tyme` service identity;
- removes `tyme` from `sudo` and `docker` if necessary;
- establishes canonical node and service paths;
- enforces key-only SSH and disabled direct root login;
- verifies UFW and Fail2ban;
- checks out one reviewed Git ref as `tyme`;
- records the substrate checkpoint;
- stops before starting Hall Core.

## Fresh-node provisioning

The revised cloud-init contract creates:

- `steward` as a key-capable human operator with a locked local password;
- `tyme` as a locked non-login service identity;
- the SSH, UFW, Fail2ban, sysctl, path, and repository baseline;
- no active Hall runtime.

Because sudo is intentionally password-protected, the provider console remains part of
the first human gate:

```bash
/usr/local/sbin/hall-core-finalize-steward
```

After setting the local password, verify a fresh key-only `steward` SSH connection and
`sudo -v` before activation.

## Activation remains a separate gate

Do not activate until:

1. this reconciliation branch passes conformance;
2. the exact commit is reviewed and merged;
3. `core.tymehall.org` points to the node;
4. DigitalOcean backups and firewall posture are confirmed;
5. the `steward` and `tyme` identity split is verified on the node.

Then, and only then:

```bash
sudo HALL_DOMAIN=core.tymehall.org \
  /opt/tyme/Codex-control-center/deploy/hall-core-0/bootstrap.sh
```

Activation remains observe-only and should initially connect exactly one repository with
`pull_request` and `workflow_run` events.

## Evidence required after activation

- exact deployed commit;
- public health and readiness responses;
- one signed delivery accepted;
- exact replay deduplicated;
- mismatched replay rejected;
- one integrity-checked backup;
- one restore rehearsal;
- one Hall Event recording deployment evidence and the next valid action.
