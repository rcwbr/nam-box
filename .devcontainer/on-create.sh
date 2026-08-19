#!/bin/bash
set -ex

# ═══════════════════════════════════════════════════════════════════════════════
# Devcontainer onCreateCommand — runs AS ROOT after the container is created
# but BEFORE postCreateCommand (which runs as the non-root user).
#
# Fixes two issues that block the Hermes WebUI bringup:
#
# 1. Docker TLS cert resolution error:
#    "unable to resolve docker endpoint: open /root/.docker/ca.pem: no such file"
#    The Docker CLI v29 default context has SkipTLSVerify=false. When Docker is
#    invoked as root (e.g. by Compose or container init), it uses HOME=/root
#    and looks for /root/.docker/ca.pem. We create that empty file and also
#    set the container-wide DOCKER_TLS_VERIFY=0 via containerEnv (in
#    devcontainer.json) so the env var is always present, not just in terminal
#    sessions.
#
# 2. Docker socket permission (group) mismatch:
#    /var/run/docker.sock is owned by root:800 (mode 660) but the host has no
#    `docker` group with GID 800. The non-root user can't connect.
#    We create a docker group with the correct GID and add the workspace user.
# ═══════════════════════════════════════════════════════════════════════════════

# ─── Fix 1: Create empty TLS cert files to satisfy CLI cert lookup ──────────
# This covers both /root/.docker/ and the runtime user's HOME.
# The files are empty — they're never actually used because DOCKER_TLS_VERIFY=0
# or the context has skip-tls-verify=true.
for cert_home in /root /home/hermeswebui; do
    if [ -d "$cert_home" ]; then
        mkdir -p "$cert_home/.docker"
        touch "$cert_home/.docker/ca.pem" "$cert_home/.docker/cert.pem" "$cert_home/.docker/key.pem"
        chmod 600 "$cert_home/.docker/ca.pem" "$cert_home/.docker/cert.pem" "$cert_home/.docker/key.pem" 2>/dev/null || true
    fi
done

# ─── Fix 2: Create docker group with matching GID + add runtime user ─────────
DOCKER_SOCK=/var/run/docker.sock
if [ -S "$DOCKER_SOCK" ]; then
    SOCKET_GID=$(stat -c %g "$DOCKER_SOCK")
    # Create the group if it doesn't already exist with this GID
    if ! getent group "$SOCKET_GID" >/dev/null 2>&1; then
        groupadd --gid "$SOCKET_GID" docker
    fi
    # Ensure the group name 'docker' maps to the socket GID
    GROUP_NAME=$(getent group "$SOCKET_GID" | cut -d: -f1)
    if [ -n "$GROUP_NAME" ]; then
        # Add the runtime user to the docker group
        usermod -aG "$GROUP_NAME" hermeswebui 2>/dev/null || \
        gpasswd -a hermeswebui "$GROUP_NAME"
    fi
    echo "✅ Docker socket group GID $SOCKET_GID → group '$GROUP_NAME' created"
    echo "   User 'hermeswebui' added to docker group"
else
    echo "⚠ Docker socket not found at $DOCKER_SOCK — skipping group setup"
    # Fallback: create docker group with default GID 800
    groupadd --gid 800 docker 2>/dev/null || true
    gpasswd -a hermeswebui docker 2>/dev/null || true
fi

# ─── Fix 3: Create a TLS-disabled Docker context (belt and suspenders) ─────────
# The default context may have SkipTLSVerify=false. Create an alternate context
# with TLS explicitly disabled, and make it the default in ~/.docker/config.json
if command -v docker >/dev/null 2>&1; then
    CONTEXT_NAME="tls-disabled"
    docker context create --docker "host=unix:///var/run/docker.sock,skip-tls-verify=true" "$CONTEXT_NAME" 2>/dev/null || true
    docker context use "$CONTEXT_NAME" 2>/dev/null || true
    echo "✅ Docker context '$CONTEXT_NAME' with TLS disabled set as current"
fi

echo ""
echo "✅ onCreateCommand complete — Docker socket + TLS fixes applied"