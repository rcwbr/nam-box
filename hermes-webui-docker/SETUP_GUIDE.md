# Adding Hermes WebUI to a GitHub Codespaces Project

This guide explains how to make the **Hermes WebUI** service auto-start when a
GitHub Codespace launches, with its port publicly forwarded, and how to adapt
the generic configuration for any project.

---

## File Layout

The reusable Hermes WebUI configuration lives in a self-contained directory:

```
<project-root>/
├── .devcontainer/
│   ├── devcontainer.json          # Codespace definition — starts & ports
│   ├── post-create.sh             # Builds & starts the WebUI stack
│   └── ...existing devcontainer files...
├── hermes-webui-docker/
│   ├── Dockerfile                 # Extends stock hermes-webui + Docker CLI
│   ├── docker-compose.yml         # Single-container compose spec
│   └── .env.example               # Template for all env vars
└── ...your project files...
```

---

## Prerequisites

Your GitHub Codespace must have:

| Requirement | Why |
|---|---|
| **Docker socket bind-mounted** | The WebUI container needs a Docker daemon to build its own image and to let the agent run `docker build`/`docker compose` from inside the container. |
| **`docker` CLI in the dev container** | Used by `post-create.sh` to build the WebUI image and start the stack. GitHub Codespaces includes Docker by default. |
| **A user namespace where `id -u` / `id -g` are stable** | The UID/GID are detected at post-create time and baked into the image so bind-mounted files have correct ownership. |

> Codespaces created from a `devcontainer.json` image **already** get a Docker
> socket bind-mounted. If your dev container uses a custom image without Docker,
> add it via the `mounts` entry shown in the example `devcontainer.json` below.

---

## Step 1 — Copy the `hermes-webui-docker/` directory

Copy the entire directory into your project:

```bash
cp -r hermes-webui-docker/ /path/to/your-project/hermes-webui-docker/
```

Or, if you're starting from scratch, create the directory with these three
files:

### `hermes-webui-docker/Dockerfile`

```dockerfile
# ── Stage 1: pull the official Docker CLI image as a binary source ──────────
ARG DOCKER_CLI_IMAGE=docker:29.0.2-cli
FROM ${DOCKER_CLI_IMAGE} AS docker_image

# ── Stage 2: extend the Hermes WebUI image ────────────────────────────────────
ARG WEBUI_BASE_IMAGE=ghcr.io/nesquena/hermes-webui:0.52.166
FROM ${WEBUI_BASE_IMAGE}

# ── Stage 3: copy Docker CLI binaries + set up group access ───────────────────
COPY --from=docker_image /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker_image /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
COPY --from=docker_image /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose

# Re-map the container user's UID/GID to match the host user
ARG WANTED_UID=1000
ARG WANTED_GID=1000
RUN groupmod --gid $WANTED_GID hermeswebui 2>/dev/null \
    || groupadd --gid $WANTED_GID hermeswebui \
    ; \
    usermod --uid $WANTED_UID --gid $WANTED_GID hermeswebui

# Give the hermeswebui user access to the Docker socket
ARG DOCKER_GID=800
RUN groupadd --gid $DOCKER_GID docker 2>/dev/null || true && \
    usermod -aG docker hermeswebui
```

### `hermes-webui-docker/docker-compose.yml`

```yaml
services:
  hermes-webui:
    build:
      context: .
      dockerfile: Dockerfile
      args:
        - WEBUI_BASE_IMAGE=${WEBUI_BASE_IMAGE:-ghcr.io/nesquena/hermes-webui:0.52.166}
        - DOCKER_GID=${DOCKER_GID:-800}
        - WANTED_UID=${WANTED_UID:-1000}
        - WANTED_GID=${WANTED_GID:-1000}
    image: ${WEBUI_LOCAL_IMAGE:-hermes-webui:local}
    container_name: ${WEBUI_CONTAINER_NAME:-hermes-webui}
    ports:
      - ${WEBUI_HOST_PORT:-0.0.0.0:8787}:${WEBUI_PORT:-8787}
    volumes:
      - ${HERMES_HOME_HOST_PATH:-${HOME}/.hermes}:/home/hermeswebui/.hermes
      - ${HERMES_WORKSPACE_HOST_PATH:-${HOME}/workspace}:/workspace
      - /var/run/docker.sock:/var/run/docker.sock
    environment:
      - HERMES_WEBUI_HOST=0.0.0.0
      - HERMES_WEBUI_PORT=${WEBUI_PORT:-8787}
      - HERMES_WEBUI_STATE_DIR=/home/hermeswebui/.hermes/webui
      - DOCKER_HOST=unix:///var/run/docker.sock
      - DOCKER_TLS_VERIFY=0
    restart: unless-stopped
```

### `hermes-webui-docker/.env.example`

```env
# Host user UID/GID (run: id -u / id -g)
WANTED_UID=1000
WANTED_GID=1000

# Docker socket group GID (run: stat -c %g /var/run/docker.sock)
DOCKER_GID=800

# Base image
WEBUI_BASE_IMAGE=ghcr.io/nesquena/hermes-webui:0.52.166
WEBUI_LOCAL_IMAGE=hermes-webui:local

# WebUI port
WEBUI_PORT=8787
WEBUI_HOST_PORT=0.0.0.0:8787

# Host paths
HERMES_HOME_HOST_PATH=${HOME}/.hermes
HERMES_WORKSPACE_HOST_PATH=${HOME}/workspace

WEBUI_CONTAINER_NAME=hermes-webui
```

> **Full annotated versions** of all three files — with inline comments
> explaining every variable and option — are in `hermes-webui-docker/` in this
> repo. Copy those directly for a richer starting point.

---

## Step 2 — Configure `.devcontainer/devcontainer.json`

You need two additions to your existing (or new) `devcontainer.json`:

### `forwardPorts` — public port exposure

```json
{
  "forwardPorts": [
    {
      "port": 8787,
      "name": "hermes-webui",
      "visibility": "public"
    }
  ]
}
```

- **`port: 8787`** — The container port to forward. Must match `WEBUI_PORT`
  in `.env`.
- **`visibility: "public"`** — Makes the port accessible from anywhere via
  the Codespace's public URL. Use `"private"` if you only need localhost.
  This is the key switch from the default (private) to public.
- **`name`** — A human-readable label shown in the Codespaces UI.

### Docker socket mount

```json
{
  "mounts": [
    {
      "source": "/var/run/docker.sock",
      "target": "/var/run/docker.sock",
      "type": "bind"
    }
  ]
}
```

On Codespaces, the Docker socket **is already** bind-mounted by the platform
when you use the GitHub Codespaces base image. If you use a custom image or
a `Dockerfile` that doesn't inherit from the Codespaces base, you may need to
add this mount explicitly.

### `postCreateCommand`

```json
{
  "postCreateCommand": ".devcontainer/post-create.sh"
}
```

This runs after the dev container is created and mounted. It creates the `.env`
file, detects UID/GID/socket GID, builds the image, and starts the stack.

**Complete example `devcontainer.json`:**

```json
{
  "name": "my-project-codespace",
  "image": "mcr.microsoft.com/devcontainers/base:ubuntu-22.04",
  "mounts": [
    {
      "source": "/var/run/docker.sock",
      "target": "/var/run/docker.sock",
      "type": "bind"
    }
  ],
  "forwardPorts": [
    {
      "port": 8787,
      "name": "hermes-webui",
      "visibility": "public"
    }
  ],
  "postCreateCommand": ".devcontainer/post-create.sh"
}
```

---

## Step 3 — Add the post-create script

Create `.devcontainer/post-create.sh`:

```bash
#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WEBUI_DIR="$PROJECT_ROOT/hermes-webui-docker"

echo "🚀 Starting Hermes WebUI setup..."

# Ensure .env exists
if [ ! -f "$WEBUI_DIR/.env" ]; then
  echo "  → Creating .env from .env.example"
  cp "$WEBUI_DIR/.env.example" "$WEBUI_DIR/.env"
fi

# Detect host UID/GID
HOST_UID="$(id -u)"
HOST_GID="$(id -g)"
sed -i "s/^WANTED_UID=.*/WANTED_UID=${HOST_UID}/" "$WEBUI_DIR/.env"
sed -i "s/^WANTED_GID=.*/WANTED_GID=${HOST_GID}/" "$WEBUI_DIR/.env"

# Detect Docker socket GID
if [ -S /var/run/docker.sock ]; then
  SOCKET_GID="$(stat -c %g /var/run/docker.sock)"
  sed -i "s/^DOCKER_GID=.*/DOCKER_GID=${SOCKET_GID}/" "$WEBUI_DIR/.env"
else
  echo "  ⚠ Docker socket not found — using default GID 800"
fi

# Build (runs inside the dev container, which has Docker available)
echo "  → Building Hermes WebUI image..."
docker build \
  -f "$WEBUI_DIR/Dockerfile" \
  -t hermes-webui:local \
  --build-arg WANTED_UID="$HOST_UID" \
  --build-arg WANTED_GID="$HOST_GID" \
  --build-arg DOCKER_GID="${SOCKET_GID:-800}" \
  "$WEBUI_DIR"

# Start the stack
echo "  → Starting Hermes WebUI..."
docker compose \
  -f "$WEBUI_DIR/docker-compose.yml" \
  --env-file "$WEBUI_DIR/.env" \
  up -d

echo ""
echo "✅ Hermes WebUI is starting up!"
echo "   → Open: https://<codespace-name>-8787.preview.app.github.com"
```

Make it executable:

```bash
chmod +x .devcontainer/post-create.sh
```

---

## Step 4 — `.gitignore`

Add the generated `.env` to `.gitignore` (never commit secrets or
machine-specific paths):

```
hermes-webui-docker/.env
```

---

## Step 5 — Configure Hermes itself

Inside the running WebUI container, you may need to set up your API keys. The
`.env` file mounted from `${HERMES_HOME_HOST_PATH}` (`.hermes`) contains
LLM provider keys, tool keys, and other configuration.

If you don't already have a `~/.hermes` directory on the host:

1. The container will create one on first startup.
2. Once the WebUI is running, use `hermes setup` from the in-container terminal
   to configure your provider and API keys interactively.

Alternatively, copy an existing `~/.hermes` from another machine:

```bash
# On the machine that already has Hermes configured:
tar czf hermes-home.tar.gz ~/.hermes

# On the Codespace host or your local machine:
tar xzf hermes-home.tar.gz -C ~
```

---

## Customization Guide

### Variable Reference

All variables are defined in `hermes-webui-docker/.env.example`. Here's the
full table:

| Variable | Default | Description |
|---|---|---|
| `WANTED_UID` | `1000` | Host user UID — file ownership on bind mounts |
| `WANTED_GID` | `1000` | Host user GID — file ownership on bind mounts |
| `DOCKER_GID` | `800` | GID of host's `docker` group — lets container user talk to Docker socket |
| `WEBUI_BASE_IMAGE` | `ghcr.io/nesquena/hermes-webui:0.52.166` | Stock WebUI image to extend |
| `WEBUI_LOCAL_IMAGE` | `hermes-webui:local` | Tag for the locally-built image |
| `WEBUI_PORT` | `8787` | Port the WebUI listens on inside the container |
| `WEBUI_HOST_PORT` | `0.0.0.0:8787` | Host-side bind for port forwarding (`0.0.0.0` = public, `127.0.0.1` = private) |
| `HERMES_HOME_HOST_PATH` | `${HOME}/.hermes` | Path to your Hermes home directory on the host |
| `HERMES_WORKSPACE_HOST_PATH` | `${HOME}/workspace` | Path to your workspace on the host |
| `WEBUI_CONTAINER_NAME` | `hermes-webui` | Docker container name |
| `HERMES_WEBUI_PASSWORD` | *(unset)* | Optional password for WebUI access |
| `HERMES_SKIP_CHMOD` | *(unset)* | Skip credential-permission fixer on startup |
| `HERMES_HOME_MODE` | *(unset)* | File mode for Hermes home (e.g. `0640`) |

### Common Customizations

**Changing the port:**

```env
WEBUI_PORT=3000
WEBUI_HOST_PORT=0.0.0.0:3000
```

Also update `forwardPorts.port` in `devcontainer.json` to match.

**Private-only access (localhost):**

```env
WEBUI_HOST_PORT=127.0.0.1:8787
```

And set `"visibility": "private"` in `devcontainer.json` (or omit the
object form and use an integer).

**A specific WebUI image version:**

```env
WEBUI_BASE_IMAGE=ghcr.io/nesquena/hermes-webui:0.53.0
```

Find available tags at
[https://github.com/nesquena/hermes-webui/tags](https://github.com/nesquena/hermes-webui/tags).

**Custom workspace path:**

```env
HERMES_WORKSPACE_HOST_PATH=${HOME}/my-project
```

---

## How It Works (Architecture)

```
┌─────────────────────────────────────────────────────────┐
│  GitHub Codespace (dev container)                       │
│                                                          │
│  .devcontainer/devcontainer.json                         │
│    │  mounts /var/run/docker.sock                       │
│    │  forwards port 8787 (public)                       │
│    │  runs post-create.sh on startup                   │
│    └──┬───────────────────────────────────────────┐    │
│       │                                           │    │
│       ▼                                           │    │
│  post-create.sh                                    │    │
│    1. Creates hermes-webui-docker/.env            │    │
│    2. Detects host UID/GID/socket-GID             │    │
│    3. docker build → hermes-webui:local            │    │
│    4. docker compose up -d                         │    │
│         │                                           │    │
│       ▼                                           │    │
│  ┌─────────────────────────────────┐               │    │
│  │  hermes-webui container        │               │    │
│  │  • stock hermes-webui image    │               │    │
│  │  • + Docker CLI (docker,       │               │    │
│  │    docker-buildx, docker-      │               │    │
│  │    compose)                    │               │    │
│  │  • User remapped to host UID   │               │    │
│  │  • User in docker group        │               │    │
│  │  • ~/.hermes volume-mounted    │               │    │
│  │  • /workspace volume-mounted   │               │    │
│  │  • /var/run/docker.sock mnt'd  │               │    │
│  │  • Listens on :8787            │  ← port 8787   │    │
│  └─────────────────────────────────┘   → public   │    │
└─────────────────────────────────────────────────────────┘
```

The WebUI runs **inside** a Docker container that runs **inside** the Codespace
dev container. The dev container has the Docker socket bind-mounted, so it can
build the WebUI image and manage the WebUI container lifecycle. This gives you
full `docker` support from the agent running in the WebUI — the agent can build
and run additional containers, compose stacks, etc.

---

## Standalone Usage (without Codespaces)

You can also run the Hermes WebUI locally on any machine with Docker installed:

```bash
cd hermes-webui-docker
cp .env.example .env
# Edit .env → set WANTED_UID, WANTED_GID, DOCKER_GID, and any custom paths
docker compose up -d --build
# Then open http://localhost:8787
```

On macOS, the Docker socket group is typically `staff` (check with
`stat -f %g /var/run/docker.sock`). Set `DOCKER_GID` accordingly.

---

## Troubleshooting

### "permission denied" on /var/run/docker.sock

The `DOCKER_GID` in `.env` doesn't match the host's Docker group GID. Fix:

```bash
stat -c %g /var/run/docker.sock   # Linux
stat -f %g /var/run/docker.sock   # macOS
```

Update `DOCKER_GID` in `.env` to match, then rebuild:

```bash
docker compose up -d --build
```

**Codespaces/devcontainer note:** If the host has no `docker` group with the
socket's GID (common in Codespaces where the user is non-root), the
`onCreateCommand` (`.devcontainer/on-create.sh`) must create the group as root
before `postCreateCommand` runs. See the `docker-cli-in-container` skill for the
full pattern: create the group, add the runtime user, and create TLS cert stubs
in `/root/.docker/`.

### "unable to resolve docker endpoint: open /root/.docker/ca.pem: no such file"

The Docker CLI v29 default context has TLS enabled (`SkipTLSVerify=false`).
When invoked as root (e.g. from `onCreateCommand` or container init), it looks
for `/root/.docker/ca.pem`. Fix all three layers:

1. **Env var:** Set `DOCKER_TLS_VERIFY=0` in `containerEnv` in `devcontainer.json`
2. **Context:** Create a TLS-disabled context (`docker context create ... --skip-tls-verify=true`)
3. **Cert stub:** Create empty `ca.pem` in `/root/.docker/` via `onCreateCommand`

See `.devcontainer/on-create.sh` for a ready-made implementation.

### Files in ~/.hermes show as owned by root

The `WANTED_UID`/`WANTED_GID` didn't get set correctly. Verify:

```bash
docker exec hermes-webui id hermeswebui
cat hermes-webui-docker/.env | grep WANTED
```

Update `.env` and rebuild.

### Port 8787 is already in use

Change `WEBUI_PORT` and `WEBUI_HOST_PORT` in `.env` (and the `port` in
`devcontainer.json` `forwardPorts`).

### WebUI won't start — check logs

```bash
docker compose -f hermes-webui-docker/docker-compose.yml logs -f
```
