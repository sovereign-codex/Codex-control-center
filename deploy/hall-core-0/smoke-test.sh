#!/usr/bin/env bash
set -euo pipefail
ENV_FILE=${HALL_ENV_FILE:-/etc/tyme/hall-core.env}
[[ -r ${ENV_FILE} ]] || { echo "Run with sudo" >&2; exit 2; }
DOMAIN=$(sed -n 's/^HALL_DOMAIN=//p' "${ENV_FILE}" | tail -1)
TOKEN=$(sed -n 's/^HALL_READ_TOKEN=//p' "${ENV_FILE}" | tail -1)
curl -fsS "https://${DOMAIN}/healthz" | jq .
curl -fsS "https://${DOMAIN}/readyz" | jq .
curl -fsS -H "Authorization: Bearer ${TOKEN}" "https://${DOMAIN}/v0/snapshot" | jq .
