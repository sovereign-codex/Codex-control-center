#!/usr/bin/env bash
set -euo pipefail
DB=${HALL_DB_PATH:-/var/lib/tyme/hall-core/hall.db}
DIR=${HALL_BACKUP_DIR:-/var/lib/tyme/hall-core-backups}
[[ -f ${DB} ]] || exit 0
install -d -m 0700 "${DIR}"
STAMP=$(date -u +%Y%m%dT%H%M%SZ)
OUT=${DIR}/hall-core-0-${STAMP}.sqlite3
sqlite3 "${DB}" ".backup '${OUT}'"
[[ $(sqlite3 "${OUT}" 'PRAGMA integrity_check;') == ok ]]
chmod 0600 "${OUT}"
sha256sum "${OUT}" > "${OUT}.sha256"; chmod 0600 "${OUT}.sha256"
find "${DIR}" -type f -name 'hall-core-0-*' -mtime +14 -delete
