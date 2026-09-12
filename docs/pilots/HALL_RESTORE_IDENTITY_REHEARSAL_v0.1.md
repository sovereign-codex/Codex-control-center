# Hall restore identity rehearsal v0.1

Status: prepared; live restoration has not been observed.

`bootstrap.sh` builds the Hall image with the service account's numeric UID/GID.
The prior restore script always installed the database as 10001:10001. Restore
now resolves the Compose configuration, checks the existing container identity and
writable data bind mount, and checks directory ownership before any service stop.
An identity or mount mismatch fails closed for explicit operator reconciliation.
It does not change ownership recursively or run the service as root.

## Read-only preflight

From the reviewed checkout on Hall, use the existing operator account and sudo:

```bash
sudo bash deploy/hall-core-0/restore.sh --check /absolute/path/to/verified-backup.sqlite3
```

Replace the backup path with an actual integrity-checked backup. `--check` reads
configuration and container metadata and checks SQLite integrity. It does not stop
the container or replace the database. It reports no tokens or full configuration.
Do not paste the environment file or raw Docker inspection output into chat.

## Isolated restoration gate

Use a locally available, reviewed Hall image (prefer its immutable image ID):

```bash
sudo bash deploy/hall-core-0/rehearse-restore.sh REVIEWED_HALL_IMAGE
```

The harness creates a unique Compose project and separate data under `/var/tmp`,
with synthetic SQLite evidence, no published ports, and `network_mode: none`.
It pulls/builds no images. It copies the repaired restore script unchanged,
executes `--check` and `--yes`, and uses an isolated smoke-test that queries the
container's loopback readiness endpoint. Read-back runs as the image's runtime
user. The production project and database are not selected.

The harness prints a sanitized `receipt.json` only after integrity, identity,
mode, evidence read-back and readiness pass. Its temporary directory is retained
for inspection and contains private test configuration: share only the receipt.
It attempts to remove the isolated container on exit; confirm removal separately.
This synthetic isolated rehearsal does not claim a production-backup restore.

Retain: reviewed source SHA; configured and actual UID/GID; sanitized isolation
description; backup SHA-256; pre/post event counts or known synthetic event IDs;
SQLite integrity result; restored database owner/mode; restored service readiness;
retrieved evidence hash; and the rehearsal outcome. A unit-test pass is not this
live restoration receipt. Recheck the retained evidence independently afterwards.

## Local verification

```bash
python3 -m unittest discover -s deploy/hall-core-0/tests -v
bash -n deploy/hall-core-0/restore.sh
```

Tests cover non-default service IDs, legacy IDs, root/invalid IDs, mismatched
container identity and wrong/read-only mounts. Docker-backed restoration and the
actual droplet's readiness remain execution gates.
