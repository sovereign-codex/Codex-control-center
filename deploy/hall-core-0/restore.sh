#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID} -eq 0 ]] || { echo "Run with sudo" >&2; exit 2; }
[[ ${1:-} == --yes && -f ${2:-} ]] || { echo "Usage: $0 --yes BACKUP.sqlite3" >&2; exit 2; }
BACKUP=$(readlink -f "$2")
[[ $(sqlite3 "${BACKUP}" 'PRAGMA integrity_check;') == ok ]] || { echo "Invalid backup" >&2; exit 1; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE=/etc/tyme/hall-core.env
DATA_DIR=$(sed -n 's/^HALL_DATA_DIR=//p' "${ENV_FILE}" | tail -1); DATA_DIR=${DATA_DIR:-/var/lib/tyme/hall-core}
COMPOSE=${SCRIPT_DIR}/docker-compose.yml
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE}" stop hall-core
[[ ! -f ${DATA_DIR}/hall.db ]] || cp "${DATA_DIR}/hall.db" "${DATA_DIR}/hall.db.before-restore.$(date -u +%Y%m%dT%H%M%SZ)"
rm -f "${DATA_DIR}/hall.db-wal" "${DATA_DIR}/hall.db-shm"
install -o 10001 -g 10001 -m 0600 "${BACKUP}" "${DATA_DIR}/hall.db"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE}" start hall-core
sleep 3
"${SCRIPT_DIR}/smoke-test.sh"
