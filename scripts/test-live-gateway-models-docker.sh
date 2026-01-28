#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${ZAGENT_IMAGE:-zagent:local}"
CONFIG_DIR="${ZAGENT_CONFIG_DIR:-$HOME/.zagent}"
WORKSPACE_DIR="${ZAGENT_WORKSPACE_DIR:-$HOME/clawd}"
PROFILE_FILE="${ZAGENT_PROFILE_FILE:-$HOME/.profile}"

PROFILE_MOUNT=()
if [[ -f "$PROFILE_FILE" ]]; then
  PROFILE_MOUNT=(-v "$PROFILE_FILE":/home/node/.profile:ro)
fi

echo "==> Build image: $IMAGE_NAME"
docker build -t "$IMAGE_NAME" -f "$ROOT_DIR/Dockerfile" "$ROOT_DIR"

echo "==> Run gateway live model tests (profile keys)"
docker run --rm -t \
  --entrypoint bash \
  -e COREPACK_ENABLE_DOWNLOAD_PROMPT=0 \
  -e HOME=/home/node \
  -e NODE_OPTIONS=--disable-warning=ExperimentalWarning \
  -e ZAGENT_LIVE_TEST=1 \
  -e ZAGENT_LIVE_GATEWAY_MODELS="${ZAGENT_LIVE_GATEWAY_MODELS:-all}" \
  -e ZAGENT_LIVE_GATEWAY_PROVIDERS="${ZAGENT_LIVE_GATEWAY_PROVIDERS:-}" \
  -e ZAGENT_LIVE_GATEWAY_MODEL_TIMEOUT_MS="${ZAGENT_LIVE_GATEWAY_MODEL_TIMEOUT_MS:-}" \
  -v "$CONFIG_DIR":/home/node/.zagent \
  -v "$WORKSPACE_DIR":/home/node/clawd \
  "${PROFILE_MOUNT[@]}" \
  "$IMAGE_NAME" \
  -lc "set -euo pipefail; [ -f \"$HOME/.profile\" ] && source \"$HOME/.profile\" || true; cd /app && pnpm test:live"
