#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
IMAGE_NAME="${ZAGENT_INSTALL_E2E_IMAGE:-zagent-install-e2e:local}"
INSTALL_URL="${ZAGENT_INSTALL_URL:-https://molt.bot/install.sh}"

OPENAI_API_KEY="${OPENAI_API_KEY:-}"
ANTHROPIC_API_KEY="${ANTHROPIC_API_KEY:-}"
ANTHROPIC_API_TOKEN="${ANTHROPIC_API_TOKEN:-}"
ZAGENT_E2E_MODELS="${ZAGENT_E2E_MODELS:-}"

echo "==> Build image: $IMAGE_NAME"
docker build \
  -t "$IMAGE_NAME" \
  -f "$ROOT_DIR/scripts/docker/install-sh-e2e/Dockerfile" \
  "$ROOT_DIR/scripts/docker/install-sh-e2e"

echo "==> Run E2E installer test"
docker run --rm \
  -e ZAGENT_INSTALL_URL="$INSTALL_URL" \
  -e ZAGENT_INSTALL_TAG="${ZAGENT_INSTALL_TAG:-latest}" \
  -e ZAGENT_E2E_MODELS="$ZAGENT_E2E_MODELS" \
  -e ZAGENT_INSTALL_E2E_PREVIOUS="${ZAGENT_INSTALL_E2E_PREVIOUS:-}" \
  -e ZAGENT_INSTALL_E2E_SKIP_PREVIOUS="${ZAGENT_INSTALL_E2E_SKIP_PREVIOUS:-0}" \
  -e OPENAI_API_KEY="$OPENAI_API_KEY" \
  -e ANTHROPIC_API_KEY="$ANTHROPIC_API_KEY" \
  -e ANTHROPIC_API_TOKEN="$ANTHROPIC_API_TOKEN" \
  "$IMAGE_NAME"
