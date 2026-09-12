#!/usr/bin/env bash
# Uses a prebuilt reviewed Hall image. No production volumes or published ports.
set -euo pipefail
[[ ${EUID} -eq 0 ]] || { echo "Run with sudo" >&2; exit 2; }
[[ $# == 1 ]] || { echo "Usage: $0 REVIEWED_HALL_IMAGE" >&2; exit 2; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
IMAGE_ID=$(docker image inspect --format '{{.Id}}' "$1")
IDENTITY=$(docker image inspect --format '{{.Config.User}}' "${IMAGE_ID}")
[[ ${IDENTITY} =~ ^[1-9][0-9]*:[1-9][0-9]*$ ]] || { echo "Image must declare numeric non-root UID:GID" >&2; exit 2; }
WORK=$(mktemp -d /var/tmp/hall-restore-rehearsal.XXXXXXXX)
chmod 0755 "${WORK}"
umask 077
PROJECT="hall-restore-rehearsal-$(basename "${WORK}" | tr '[:upper:].' '[:lower:]-')"
export REHEARSAL_WORK="${WORK}" REHEARSAL_IMAGE="${IMAGE_ID}" REHEARSAL_IDENTITY="${IDENTITY}" REHEARSAL_PROJECT="${PROJECT}"
python3 - <<'PY'
import json, os, secrets, sqlite3
from pathlib import Path
root = Path(os.environ['REHEARSAL_WORK'])
uid, gid = map(int, os.environ['REHEARSAL_IDENTITY'].split(':'))
data = root / 'data'
data.mkdir(mode=0o700)
os.chown(data, uid, gid)
with sqlite3.connect(root / 'backup.sqlite3') as db:
    db.execute('CREATE TABLE rehearsal_evidence (value TEXT NOT NULL)')
    db.execute('INSERT INTO rehearsal_evidence VALUES (?)', ('hall-restore-synthetic-witness-v1',))
service = {
    'image': os.environ['REHEARSAL_IMAGE'],
    'build': {'context': '.', 'args': {'HALL_RUNTIME_UID': str(uid), 'HALL_RUNTIME_GID': str(gid)}},
    'environment': {'HALL_DB_PATH': '/var/lib/hall-core/hall.db', 'HALL_GITHUB_WEBHOOK_SECRET': secrets.token_hex(32), 'HALL_READ_TOKEN': secrets.token_hex(32)},
    'volumes': [{'type': 'bind', 'source': str(data), 'target': '/var/lib/hall-core'}],
    'network_mode': 'none', 'read_only': True, 'tmpfs': ['/tmp'],
    'cap_drop': ['ALL'], 'security_opt': ['no-new-privileges:true'],
}
# JSON is valid YAML. This standalone project has no Caddy, host ports or network.
(root / 'docker-compose.yml').write_text(json.dumps({'name': os.environ['REHEARSAL_PROJECT'], 'services': {'hall-core': service}}))
(root / 'hall-core.env').write_text('')
PY
cp "${SCRIPT_DIR}/restore.sh" "${SCRIPT_DIR}/restore-preflight.py" "${WORK}/"
cat > "${WORK}/smoke-test.sh" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
HERE="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
for attempt in $(seq 1 20); do
  if docker compose --env-file "${HERE}/hall-core.env" -f "${HERE}/docker-compose.yml" exec -T hall-core python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz', timeout=2).read()" >/dev/null 2>&1; then
    exit 0
  fi
  sleep 1
done
echo 'Isolated readiness failed' >&2
exit 1
SH
chmod 0700 "${WORK}/smoke-test.sh"
cleanup() {
  docker compose --env-file "${WORK}/hall-core.env" -f "${WORK}/docker-compose.yml" down >/dev/null 2>&1 || true
  echo "Rehearsal directory retained: ${WORK} (contains private test configuration; share only receipt.json)"
}
trap cleanup EXIT
docker compose --env-file "${WORK}/hall-core.env" -f "${WORK}/docker-compose.yml" up -d --no-build --pull never
HALL_ENV_FILE="${WORK}/hall-core.env" bash "${WORK}/restore.sh" --check "${WORK}/backup.sqlite3"
HALL_ENV_FILE="${WORK}/hall-core.env" bash "${WORK}/restore.sh" --yes "${WORK}/backup.sqlite3"
# Query through the restored container as its actual runtime user, not host root.
docker compose --env-file "${WORK}/hall-core.env" -f "${WORK}/docker-compose.yml" exec -T hall-core python -c "import sqlite3; db=sqlite3.connect('/var/lib/hall-core/hall.db'); assert db.execute('PRAGMA integrity_check').fetchone()[0]=='ok'; assert db.execute('SELECT value FROM rehearsal_evidence').fetchone()[0]=='hall-restore-synthetic-witness-v1'"
export REHEARSAL_SOURCE_SHA="$(git -C "${SCRIPT_DIR}" rev-parse HEAD)"
python3 - <<'PY'
import hashlib, json, os, stat
from datetime import datetime, timezone
from pathlib import Path
root = Path(os.environ['REHEARSAL_WORK'])
identity = os.environ['REHEARSAL_IDENTITY']
info = (root / 'data/hall.db').stat()
assert f'{info.st_uid}:{info.st_gid}' == identity
assert stat.S_IMODE(info.st_mode) == 0o600
receipt = {'kind': 'isolated_restore_rehearsal', 'status': 'passed', 'source_commit': os.environ['REHEARSAL_SOURCE_SHA'], 'image_id': os.environ['REHEARSAL_IMAGE'], 'runtime_identity': identity, 'backup_sha256': hashlib.sha256((root / 'backup.sqlite3').read_bytes()).hexdigest(), 'evidence_sha256': hashlib.sha256(b'hall-restore-synthetic-witness-v1').hexdigest(), 'integrity_check': 'ok', 'runtime_readback': 'passed', 'readyz': 'passed', 'production_restore': 'not_performed', 'observed_at': datetime.now(timezone.utc).isoformat()}
(root / 'receipt.json').write_text(json.dumps(receipt, indent=2) + '\n')
print(json.dumps(receipt, indent=2))
PY
