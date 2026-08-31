#!/usr/bin/env bash
set -euo pipefail
[[ ${EUID} -eq 0 ]] || { echo "Run with sudo" >&2; exit 2; }

OPERATOR_USER="${HALL_OPERATOR_USER:-steward}"
SERVICE_USER="${HALL_SERVICE_USER:-tyme}"
REPO_URL="${HALL_REPO_URL:-https://github.com/sovereign-codex/Codex-control-center.git}"
REPO_REF="${HALL_REPO_REF:-}"
REPO_DIR="${HALL_REPO_DIR:-/opt/tyme/Codex-control-center}"
HALL_ROOT="${HALL_ROOT:-/opt/hall}"
DATA_DIR="${HALL_DATA_DIR:-/var/lib/tyme/hall-core}"
BACKUP_DIR="${HALL_BACKUP_DIR:-/var/lib/tyme/hall-core-backups}"

[[ -n ${REPO_REF} ]] || {
  echo "HALL_REPO_REF is required; use a reviewed branch, tag, or commit" >&2
  exit 2
}

for command in git sshd systemctl ufw fail2ban-client docker openssl python3 jq sqlite3 sysctl; do
  command -v "${command}" >/dev/null || { echo "Missing command: ${command}" >&2; exit 2; }
done
docker compose version >/dev/null

id -u "${OPERATOR_USER}" >/dev/null 2>&1 || {
  echo "Missing human operator account: ${OPERATOR_USER}" >&2
  exit 2
}
if ! id -nG "${OPERATOR_USER}" | tr ' ' '\n' | grep -qx sudo; then
  echo "Operator ${OPERATOR_USER} is not in sudo" >&2
  exit 2
fi

if ! id -u "${SERVICE_USER}" >/dev/null 2>&1; then
  useradd --system --user-group --home-dir /opt/tyme --shell /usr/sbin/nologin "${SERVICE_USER}"
fi
usermod --lock --shell /usr/sbin/nologin "${SERVICE_USER}"
for forbidden_group in sudo docker; do
  if id -nG "${SERVICE_USER}" | tr ' ' '\n' | grep -qx "${forbidden_group}"; then
    gpasswd -d "${SERVICE_USER}" "${forbidden_group}"
  fi
done

install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 /opt/tyme
install -d -o "${OPERATOR_USER}" -g "${OPERATOR_USER}" -m 0750 \
  "${HALL_ROOT}" \
  "${HALL_ROOT}/runtime" \
  "${HALL_ROOT}/state" \
  "${HALL_ROOT}/config" \
  "${HALL_ROOT}/logs" \
  "${HALL_ROOT}/backups"
install -d -o 10001 -g 10001 -m 0700 "${DATA_DIR}"
install -d -o root -g root -m 0700 "${BACKUP_DIR}"

if [[ ! -s /home/${OPERATOR_USER}/.ssh/authorized_keys && -s /root/.ssh/authorized_keys ]]; then
  install -d -o "${OPERATOR_USER}" -g "${OPERATOR_USER}" -m 0700 "/home/${OPERATOR_USER}/.ssh"
  install -o "${OPERATOR_USER}" -g "${OPERATOR_USER}" -m 0600 \
    /root/.ssh/authorized_keys "/home/${OPERATOR_USER}/.ssh/authorized_keys"
fi
[[ -s /home/${OPERATOR_USER}/.ssh/authorized_keys ]] || {
  echo "Refusing SSH hardening: ${OPERATOR_USER} has no authorized key" >&2
  exit 2
}
chown -R "${OPERATOR_USER}:${OPERATOR_USER}" "/home/${OPERATOR_USER}/.ssh"
chmod 0700 "/home/${OPERATOR_USER}/.ssh"
chmod 0600 "/home/${OPERATOR_USER}/.ssh/authorized_keys"

cat > /etc/ssh/sshd_config.d/99-hall-core.conf <<'SSH'
PasswordAuthentication no
KbdInteractiveAuthentication no
PubkeyAuthentication yes
PermitRootLogin no
X11Forwarding no
AllowAgentForwarding no
SSH
chmod 0644 /etc/ssh/sshd_config.d/99-hall-core.conf

cat > /etc/sysctl.d/99-hall-core.conf <<'SYSCTL'
net.ipv4.conf.all.accept_redirects = 0
net.ipv4.conf.default.accept_redirects = 0
net.ipv4.tcp_syncookies = 1
kernel.dmesg_restrict = 1
kernel.kptr_restrict = 2
SYSCTL
chmod 0644 /etc/sysctl.d/99-hall-core.conf
sysctl --system >/dev/null

sshd -t
systemctl reload ssh 2>/dev/null || systemctl reload sshd
systemctl enable --now docker
systemctl enable --now fail2ban
systemctl enable --now unattended-upgrades

ufw default deny incoming
ufw default allow outgoing
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw allow 443/udp
ufw --force enable

systemctl is-active --quiet ssh 2>/dev/null || systemctl is-active --quiet sshd
systemctl is-active --quiet docker
systemctl is-active --quiet fail2ban
fail2ban-client status | grep -Eq 'Jail list:.*sshd'

cat > "${HALL_ROOT}/config/hall-core.env" <<EOF
HALL_NODE_ID=hall-core-0
HALL_ROLE=control-plane
HALL_ENV=production-boundary
HALL_STEWARD=${OPERATOR_USER}
HALL_RUNTIME_ROOT=${HALL_ROOT}/runtime
HALL_STATE_ROOT=${HALL_ROOT}/state
HALL_LOG_ROOT=${HALL_ROOT}/logs
HALL_BACKUP_ROOT=${HALL_ROOT}/backups
EOF
chown "${OPERATOR_USER}:${OPERATOR_USER}" "${HALL_ROOT}/config/hall-core.env"
chmod 0640 "${HALL_ROOT}/config/hall-core.env"

if [[ ! -d ${REPO_DIR}/.git ]]; then
  install -d -o "${SERVICE_USER}" -g "${SERVICE_USER}" -m 0750 "$(dirname "${REPO_DIR}")"
  runuser -u "${SERVICE_USER}" -- git clone --filter=blob:none --no-checkout "${REPO_URL}" "${REPO_DIR}"
fi
runuser -u "${SERVICE_USER}" -- git -C "${REPO_DIR}" remote set-url origin "${REPO_URL}"
runuser -u "${SERVICE_USER}" -- git -C "${REPO_DIR}" fetch --depth 1 origin "${REPO_REF}"
runuser -u "${SERVICE_USER}" -- git -C "${REPO_DIR}" checkout --detach FETCH_HEAD
COMMIT=$(runuser -u "${SERVICE_USER}" -- git -C "${REPO_DIR}" rev-parse HEAD)

date -u +%FT%TZ > /var/lib/tyme/live-substrate-reconciled

cat <<EOF
Hall Core 0 live substrate reconciled.
Operator: ${OPERATOR_USER} (human, key-only SSH, password-protected sudo expected)
Service:  ${SERVICE_USER} (locked, non-login, no sudo/docker group)
Repository: ${REPO_DIR}
Commit: ${COMMIT}
Runtime activation: NOT performed
Next gate: verify a fresh ${OPERATOR_USER} SSH session, review DNS/backups, then run bootstrap.sh explicitly.
EOF
