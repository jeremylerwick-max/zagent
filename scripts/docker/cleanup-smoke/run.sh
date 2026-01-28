#!/usr/bin/env bash
set -euo pipefail

cd /repo

export ZAGENT_STATE_DIR="/tmp/zagent-test"
export ZAGENT_CONFIG_PATH="${ZAGENT_STATE_DIR}/zagent.json"

echo "==> Seed state"
mkdir -p "${ZAGENT_STATE_DIR}/credentials"
mkdir -p "${ZAGENT_STATE_DIR}/agents/main/sessions"
echo '{}' >"${ZAGENT_CONFIG_PATH}"
echo 'creds' >"${ZAGENT_STATE_DIR}/credentials/marker.txt"
echo 'session' >"${ZAGENT_STATE_DIR}/agents/main/sessions/sessions.json"

echo "==> Reset (config+creds+sessions)"
pnpm zagent reset --scope config+creds+sessions --yes --non-interactive

test ! -f "${ZAGENT_CONFIG_PATH}"
test ! -d "${ZAGENT_STATE_DIR}/credentials"
test ! -d "${ZAGENT_STATE_DIR}/agents/main/sessions"

echo "==> Recreate minimal config"
mkdir -p "${ZAGENT_STATE_DIR}/credentials"
echo '{}' >"${ZAGENT_CONFIG_PATH}"

echo "==> Uninstall (state only)"
pnpm zagent uninstall --state --yes --non-interactive

test ! -d "${ZAGENT_STATE_DIR}"

echo "OK"
