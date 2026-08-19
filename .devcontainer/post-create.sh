#!/bin/bash
set -euo pipefail

# Codespace post-create: build & start the Hermes WebUI stack
#
# This script runs automatically after the dev container is created (configured
# in .devcontainer/devcontainer.json under "postCreateCommand").
#
# It:
#   1. Generates a .env file from .env.example (if one doesn't exist yet)
#   2. Detects the host UID/GID for correct file ownership
#   3. Detects the Docker socket group GID
#   4. Builds the WebUI image (with Docker CLI + UID/GID remapping)
#   5. Starts the stack in detached mode via hermes-web-ui.docker-compose.yml
#
# The WebUI port is forwarded to the Codespace's public interface automatically
# by GitHub Codespaces (configured via "forwardPorts" in devcontainer.json).
#
# Prerequisites: on-create.sh (onCreateCommand) must have run first to create
#   the docker group, touch empty TLS cert stubs, and set up a TLS-disabled
#   Docker context. This fixes the "open /root/.docker/ca.pem: no such file"
#   error and the "permission denied on /var/run/docker.sock" error.

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEBUI_DIR="$PROJECT_ROOT/hermes-webui-docker"
# Use the top-level wrapper compose that includes hermes-webui-docker/docker-compose.yml
COMPOSE_FILE="$PROJECT_ROOT/hermes-web-ui.docker-compose.yml"

echo "🚀 Starting Hermes WebUI setup..."

# ─── Step 1: Ensure .env exists ──────────────────────────────────────────────
if [ ! -f "$WEBUI_DIR/.env" ]; then
  echo "  -> Creating .env from .env.example"
  cp "$WEBUI_DIR/.env.example" "$WEBUI_DIR/.env"
fi

# ─── Step 2: Detect host UID/GID ─────────────────────────────────────────────
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
echo "  -> Host UID/GID: ${HOST_UID}/${HOST_GID}"

# Update .env with detected UID/GID
sed -i "s/^WANTED_UID=.*/WANTED_UID=${HOST_UID}/" "$WEBUI_DIR/.env"
sed -i "s/^WANTED_GID=.*/WANTED_GID=${HOST_GID}/" "$WEBUI_DIR/.env"

# ─── Step 3: Detect Docker socket group GID ────────────────────────────────────
if [ -S /var/run/docker.sock ]; then
  SOCKET_GID="$(stat -c %g /var/run/docker.sock)"
  echo "  -> Docker socket GID: ${SOCKET_GID}"
  sed -i "s/^DOCKER_GID=.*/DOCKER_GID=${SOCKET_GID}/" "$WEBUI_DIR/.env"
else
  echo "  ⚠ Docker socket not found at /var/run/docker.sock — using default GID 800"
fi

# Safety net: ensure empty TLS cert stub exists (fixes "open /root/.docker/ca.pem")
mkdir -p "$HOME/.docker"
touch "$HOME/.docker/ca.pem" 2>/dev/null || true

# ─── Step 4: Build ────────────────────────────────────────────────────────────
echo "  -> Building Hermes WebUI image..."
docker build \
  -f "$WEBUI_DIR/Dockerfile" \
  -t "${WEBUI_LOCAL_IMAGE:-hermes-webui:local}" \
  --build-arg WANTED_UID="$HOST_UID" \
  --build-arg WANTED_GID="$HOST_GID" \
  --build-arg DOCKER_GID="${SOCKET_GID:-800}" \
  "$WEBUI_DIR"

# ─── Step 5: Start the stack ─────────────────────────────────────────────────
echo "  -> Starting Hermes WebUI..."
docker compose \
  -f "$COMPOSE_FILE" \
  --env-file "$WEBUI_DIR/.env" \
  up -d

echo ""
echo "✅ Hermes WebUI is starting up!"
echo "   -> Open in browser: https://<codespace-name>-8787.preview.app.github.com"
echo "   -> Or check status:  docker compose -f $COMPOSE_FILE ps"
