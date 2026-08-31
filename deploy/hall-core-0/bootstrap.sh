#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID} -eq 0 ]] || { echo "Run with sudo" >&2; exit 2; }
DOMAIN="${HALL_DOMAIN:-}"
[[ -n ${DOMAIN} ]] || { echo "HALL_DOMAIN is required" >&2; exit 2; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"
REF="${HALL_REPO_REF:-main}"
SERVICE_USER="${HALL_SERVICE_USER:-tyme}"
ENV_DIR=/etc/tyme
ENV_FILE=${ENV_DIR}/hall-core.env
DATA_DIR=${HALL_DATA_DIR:-/var/lib/tyme/hall-core}
BACKUP_DIR=/var/lib/tyme/hall-core-backups
COMPOSE=${SCRIPT_DIR}/docker-compose.yml

for command in git docker openssl python3; do command -v "$command" >/dev/null || { echo "Missing $command" >&2; exit 2; }; done
docker compose version >/dev/null
id -u "${SERVICE_USER}" >/dev/null 2>&1 || { echo "Missing service user: ${SERVICE_USER}" >&2; exit 2; }
if id -nG "${SERVICE_USER}" | tr ' ' '\n' | grep -Eq '^(sudo|docker)$'; then
  echo "Service user ${SERVICE_USER} must not belong to sudo or docker" >&2
  exit 2
fi
SERVICE_SHELL=$(getent passwd "${SERVICE_USER}" | cut -d: -f7)
[[ ${SERVICE_SHELL} == /usr/sbin/nologin || ${SERVICE_SHELL} == /bin/false ]] || {
  echo "Service user ${SERVICE_USER} must be non-login" >&2
  exit 2
}

runuser -u "${SERVICE_USER}" -- git -C "${REPO_DIR}" fetch --depth 1 origin "${REF}"
runuser -u "${SERVICE_USER}" -- git -C "${REPO_DIR}" checkout --detach FETCH_HEAD
COMMIT="$(runuser -u "${SERVICE_USER}" -- git -C "${REPO_DIR}" rev-parse HEAD)"
install -d -o root -g "${SERVICE_USER}" -m 0750 "${ENV_DIR}"
install -d -o 10001 -g 10001 -m 0700 "${DATA_DIR}"
install -d -o root -g root -m 0700 "${BACKUP_DIR}"

if [[ ! -f ${ENV_FILE} ]]; then
  umask 077
  cat > "${ENV_FILE}" <<ENV
HALL_DOMAIN=${DOMAIN}
HALL_NODE_ID=hall-core-0
HALL_BUILD_COMMIT=${COMMIT}
HALL_GITHUB_ADAPTER_ID=github-webhook-v0
HALL_GITHUB_WEBHOOK_SECRET=$(openssl rand -hex 32)
HALL_READ_TOKEN=$(openssl rand -hex 32)
HALL_DATA_DIR=${DATA_DIR}
HALL_MAX_BODY_BYTES=1048576
HALL_LOG_LEVEL=INFO
ENV
else
  python3 - "${ENV_FILE}" "${DOMAIN}" "${COMMIT}" "${DATA_DIR}" <<'PY'
from pathlib import Path
import sys
path=Path(sys.argv[1]); updates=dict(HALL_DOMAIN=sys.argv[2],HALL_BUILD_COMMIT=sys.argv[3],HALL_DATA_DIR=sys.argv[4])
out=[]; seen=set()
for line in path.read_text().splitlines():
    key=line.split("=",1)[0] if "=" in line and not line.lstrip().startswith("#") else ""
    if key in updates: out.append(f"{key}={updates[key]}"); seen.add(key)
    else: out.append(line)
for key,value in updates.items():
    if key not in seen: out.append(f"{key}={value}")
path.write_text("\n".join(out)+"\n")
PY
fi
chown root:"${SERVICE_USER}" "${ENV_FILE}"; chmod 0640 "${ENV_FILE}"; chown -R 10001:10001 "${DATA_DIR}"

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE}" config --quiet
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE}" build --pull
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE}" up -d --remove-orphans
install -m 0644 "${SCRIPT_DIR}/systemd/hall-core-backup.service" /etc/systemd/system/
install -m 0644 "${SCRIPT_DIR}/systemd/hall-core-backup.timer" /etc/systemd/system/
systemctl daemon-reload
systemctl enable --now hall-core-backup.timer

for _ in $(seq 1 30); do
  if docker compose --env-file "${ENV_FILE}" -f "${COMPOSE}" exec -T hall-core \
    python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8080/readyz',timeout=3).read()" >/dev/null 2>&1; then
    cat <<EOF
Hall Core 0 is ready at https://${DOMAIN}
Webhook: https://${DOMAIN}/v0/webhooks/github
Secrets: ${ENV_FILE}
Verify: sudo ${SCRIPT_DIR}/smoke-test.sh
Operator identity: steward. Service identity: ${SERVICE_USER}.
Authority ceiling: observe. No dispatch, execution, publishing, or promotion was enabled.
EOF
    exit 0
  fi
  sleep 2
done

docker compose --env-file "${ENV_FILE}" -f "${COMPOSE}" logs --tail=200 >&2
exit 1
