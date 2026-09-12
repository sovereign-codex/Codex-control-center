#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID} -eq 0 ]] || { echo "Run with sudo" >&2; exit 2; }
[[ ( ${1:-} == --yes || ${1:-} == --check ) && -f ${2:-} ]] || { echo "Usage: $0 --check|--yes BACKUP.sqlite3" >&2; exit 2; }
BACKUP=$(readlink -f "$2")
[[ $(sqlite3 "${BACKUP}" 'PRAGMA integrity_check;') == ok ]] || { echo "Invalid backup" >&2; exit 1; }
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE=${HALL_ENV_FILE:-/etc/tyme/hall-core.env}
COMPOSE=${SCRIPT_DIR}/docker-compose.yml
PREFLIGHT=$(python3 "${SCRIPT_DIR}/restore-preflight.py" "${ENV_FILE}" "${COMPOSE}")
mapfile -t RESTORE_FIELDS <<< "${PREFLIGHT}"
RUNTIME_UID=${RESTORE_FIELDS[0]}
RUNTIME_GID=${RESTORE_FIELDS[1]}
DATA_DIR=${RESTORE_FIELDS[2]}
[[ ${BACKUP} != "$(readlink -f "${DATA_DIR}/hall.db")" ]] || { echo "Backup must be separate from the live database" >&2; exit 2; }
if [[ $1 == --check ]]; then
  echo "Restore preflight passed; runtime ${RUNTIME_UID}:${RUNTIME_GID}; no service/database changes performed."
  exit 0
fi
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE}" stop hall-core
[[ ! -f ${DATA_DIR}/hall.db ]] || cp "${DATA_DIR}/hall.db" "${DATA_DIR}/hall.db.before-restore.$(date -u +%Y%m%dT%H%M%SZ)"
rm -f "${DATA_DIR}/hall.db-wal" "${DATA_DIR}/hall.db-shm"
install -o "${RUNTIME_UID}" -g "${RUNTIME_GID}" -m 0600 "${BACKUP}" "${DATA_DIR}/hall.db"
docker compose --env-file "${ENV_FILE}" -f "${COMPOSE}" start hall-core
sleep 3
HALL_ENV_FILE="${ENV_FILE}" "${SCRIPT_DIR}/smoke-test.sh"
