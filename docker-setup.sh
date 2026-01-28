#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
COMPOSE_FILE="$ROOT_DIR/docker-compose.yml"
EXTRA_COMPOSE_FILE="$ROOT_DIR/docker-compose.extra.yml"
IMAGE_NAME="${ZAGENT_IMAGE:-zagent:local}"
EXTRA_MOUNTS="${ZAGENT_EXTRA_MOUNTS:-}"
HOME_VOLUME_NAME="${ZAGENT_HOME_VOLUME:-}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "Missing dependency: $1" >&2
    exit 1
  fi
}

require_cmd docker
if ! docker compose version >/dev/null 2>&1; then
  echo "Docker Compose not available (try: docker compose version)" >&2
  exit 1
fi

mkdir -p "${ZAGENT_CONFIG_DIR:-$HOME/.zagent}"
mkdir -p "${ZAGENT_WORKSPACE_DIR:-$HOME/clawd}"

export ZAGENT_CONFIG_DIR="${ZAGENT_CONFIG_DIR:-$HOME/.zagent}"
export ZAGENT_WORKSPACE_DIR="${ZAGENT_WORKSPACE_DIR:-$HOME/clawd}"
export ZAGENT_GATEWAY_PORT="${ZAGENT_GATEWAY_PORT:-18789}"
export ZAGENT_BRIDGE_PORT="${ZAGENT_BRIDGE_PORT:-18790}"
export ZAGENT_GATEWAY_BIND="${ZAGENT_GATEWAY_BIND:-lan}"
export ZAGENT_IMAGE="$IMAGE_NAME"
export ZAGENT_DOCKER_APT_PACKAGES="${ZAGENT_DOCKER_APT_PACKAGES:-}"

if [[ -z "${ZAGENT_GATEWAY_TOKEN:-}" ]]; then
  if command -v openssl >/dev/null 2>&1; then
    ZAGENT_GATEWAY_TOKEN="$(openssl rand -hex 32)"
  else
    ZAGENT_GATEWAY_TOKEN="$(python3 - <<'PY'
import secrets
print(secrets.token_hex(32))
PY
)"
  fi
fi
export ZAGENT_GATEWAY_TOKEN

COMPOSE_FILES=("$COMPOSE_FILE")
COMPOSE_ARGS=()

write_extra_compose() {
  local home_volume="$1"
  shift
  local -a mounts=("$@")
  local mount

  cat >"$EXTRA_COMPOSE_FILE" <<'YAML'
services:
  zagent-gateway:
    volumes:
YAML

  if [[ -n "$home_volume" ]]; then
    printf '      - %s:/home/node\n' "$home_volume" >>"$EXTRA_COMPOSE_FILE"
    printf '      - %s:/home/node/.zagent\n' "$ZAGENT_CONFIG_DIR" >>"$EXTRA_COMPOSE_FILE"
    printf '      - %s:/home/node/clawd\n' "$ZAGENT_WORKSPACE_DIR" >>"$EXTRA_COMPOSE_FILE"
  fi

  for mount in "${mounts[@]}"; do
    printf '      - %s\n' "$mount" >>"$EXTRA_COMPOSE_FILE"
  done

  cat >>"$EXTRA_COMPOSE_FILE" <<'YAML'
  zagent-cli:
    volumes:
YAML

  if [[ -n "$home_volume" ]]; then
    printf '      - %s:/home/node\n' "$home_volume" >>"$EXTRA_COMPOSE_FILE"
    printf '      - %s:/home/node/.zagent\n' "$ZAGENT_CONFIG_DIR" >>"$EXTRA_COMPOSE_FILE"
    printf '      - %s:/home/node/clawd\n' "$ZAGENT_WORKSPACE_DIR" >>"$EXTRA_COMPOSE_FILE"
  fi

  for mount in "${mounts[@]}"; do
    printf '      - %s\n' "$mount" >>"$EXTRA_COMPOSE_FILE"
  done

  if [[ -n "$home_volume" && "$home_volume" != *"/"* ]]; then
    cat >>"$EXTRA_COMPOSE_FILE" <<YAML
volumes:
  ${home_volume}:
YAML
  fi
}

VALID_MOUNTS=()
if [[ -n "$EXTRA_MOUNTS" ]]; then
  IFS=',' read -r -a mounts <<<"$EXTRA_MOUNTS"
  for mount in "${mounts[@]}"; do
    mount="${mount#"${mount%%[![:space:]]*}"}"
    mount="${mount%"${mount##*[![:space:]]}"}"
    if [[ -n "$mount" ]]; then
      VALID_MOUNTS+=("$mount")
    fi
  done
fi

if [[ -n "$HOME_VOLUME_NAME" || ${#VALID_MOUNTS[@]} -gt 0 ]]; then
  write_extra_compose "$HOME_VOLUME_NAME" "${VALID_MOUNTS[@]}"
  COMPOSE_FILES+=("$EXTRA_COMPOSE_FILE")
fi
for compose_file in "${COMPOSE_FILES[@]}"; do
  COMPOSE_ARGS+=("-f" "$compose_file")
done
COMPOSE_HINT="docker compose"
for compose_file in "${COMPOSE_FILES[@]}"; do
  COMPOSE_HINT+=" -f ${compose_file}"
done

ENV_FILE="$ROOT_DIR/.env"
upsert_env() {
  local file="$1"
  shift
  local -a keys=("$@")
  local tmp
  tmp="$(mktemp)"
  declare -A seen=()

  if [[ -f "$file" ]]; then
    while IFS= read -r line || [[ -n "$line" ]]; do
      local key="${line%%=*}"
      local replaced=false
      for k in "${keys[@]}"; do
        if [[ "$key" == "$k" ]]; then
          printf '%s=%s\n' "$k" "${!k-}" >>"$tmp"
          seen["$k"]=1
          replaced=true
          break
        fi
      done
      if [[ "$replaced" == false ]]; then
        printf '%s\n' "$line" >>"$tmp"
      fi
    done <"$file"
  fi

  for k in "${keys[@]}"; do
    if [[ -z "${seen[$k]:-}" ]]; then
      printf '%s=%s\n' "$k" "${!k-}" >>"$tmp"
    fi
  done

  mv "$tmp" "$file"
}

upsert_env "$ENV_FILE" \
  ZAGENT_CONFIG_DIR \
  ZAGENT_WORKSPACE_DIR \
  ZAGENT_GATEWAY_PORT \
  ZAGENT_BRIDGE_PORT \
  ZAGENT_GATEWAY_BIND \
  ZAGENT_GATEWAY_TOKEN \
  ZAGENT_IMAGE \
  ZAGENT_EXTRA_MOUNTS \
  ZAGENT_HOME_VOLUME \
  ZAGENT_DOCKER_APT_PACKAGES

echo "==> Building Docker image: $IMAGE_NAME"
docker build \
  --build-arg "ZAGENT_DOCKER_APT_PACKAGES=${ZAGENT_DOCKER_APT_PACKAGES}" \
  -t "$IMAGE_NAME" \
  -f "$ROOT_DIR/Dockerfile" \
  "$ROOT_DIR"

echo ""
echo "==> Onboarding (interactive)"
echo "When prompted:"
echo "  - Gateway bind: lan"
echo "  - Gateway auth: token"
echo "  - Gateway token: $ZAGENT_GATEWAY_TOKEN"
echo "  - Tailscale exposure: Off"
echo "  - Install Gateway daemon: No"
echo ""
docker compose "${COMPOSE_ARGS[@]}" run --rm zagent-cli onboard --no-install-daemon

echo ""
echo "==> Provider setup (optional)"
echo "WhatsApp (QR):"
echo "  ${COMPOSE_HINT} run --rm zagent-cli providers login"
echo "Telegram (bot token):"
echo "  ${COMPOSE_HINT} run --rm zagent-cli providers add --provider telegram --token <token>"
echo "Discord (bot token):"
echo "  ${COMPOSE_HINT} run --rm zagent-cli providers add --provider discord --token <token>"
echo "Docs: https://docs.molt.bot/providers"

echo ""
echo "==> Starting gateway"
docker compose "${COMPOSE_ARGS[@]}" up -d zagent-gateway

echo ""
echo "Gateway running with host port mapping."
echo "Access from tailnet devices via the host's tailnet IP."
echo "Config: $ZAGENT_CONFIG_DIR"
echo "Workspace: $ZAGENT_WORKSPACE_DIR"
echo "Token: $ZAGENT_GATEWAY_TOKEN"
echo ""
echo "Commands:"
echo "  ${COMPOSE_HINT} logs -f zagent-gateway"
echo "  ${COMPOSE_HINT} exec zagent-gateway node dist/index.js health --token \"$ZAGENT_GATEWAY_TOKEN\""
