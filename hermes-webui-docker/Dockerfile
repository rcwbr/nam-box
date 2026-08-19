# Dockerfile.hermes-webui-docker
#
# Extends the stock Hermes WebUI image to add the Docker CLI (docker +
# docker-buildx + docker-compose plugins), enabling `docker build`,
# `docker run`, and `docker compose` from within the WebUI container via
# a bind-mounted host Docker socket.
#
# The host Docker socket (/var/run/docker.sock) is NOT baked into the image —
# it's a bind-mount supplied by docker-compose.yml at runtime, so the same
# image is portable across machines.
#
# ── Build args ────────────────────────────────────────────────────────────────
# WEBUI_BASE_IMAGE  The stock hermes-webui image to extend (default: latest known stable)
# DOCKER_GID        GID of the docker group on the host (default: 800)
# DOCKER_CLI_IMAGE  The Docker CLI image to pull binaries from (default: docker:29.0.2-cli)
# WANTED_UID        Host user UID for file ownership on bind mounts (default: 1000)
# WANTED_GID        Host user GID for file ownership on bind mounts (default: 1000)
# ── Usage ─────────────────────────────────────────────────────────────────────
#   docker build -f hermes-webui-docker/Dockerfile \
#     --build-arg WEBUI_BASE_IMAGE=ghcr.io/nesquena/hermes-webui:<tag> \
#     --build-arg DOCKER_GID=$(stat -c %g /var/run/docker.sock) \
#     --build-arg WANTED_UID=$(id -u) \
#     --build-arg WANTED_GID=$(id -g) \
#     -t hermes-webui:local hermes-webui-docker/

# ── Stage 1: pull the official Docker CLI image as a binary source ───────────
ARG DOCKER_CLI_IMAGE=docker:29.0.2-cli
FROM ${DOCKER_CLI_IMAGE} AS docker_image

# ── Stage 2: extend the Hermes WebUI image ────────────────────────────────────
# ARG WEBUI_BASE_IMAGE=ghcr.io/nesquena/hermes-webui:0.52.166
# FROM ${WEBUI_BASE_IMAGE}
FROM ghcr.io/nesquena/hermes-webui:0.52.166

# ── Stage 3: copy Docker CLI binaries + set up group access ───────────────────
# Copy the docker CLI binary + plugins from the docker CLI image.
COPY --from=docker_image /usr/local/bin/docker /usr/local/bin/docker
COPY --from=docker_image /usr/local/libexec/docker/cli-plugins/docker-buildx /usr/local/libexec/docker/cli-plugins/docker-buildx
COPY --from=docker_image /usr/local/libexec/docker/cli-plugins/docker-compose /usr/local/libexec/docker/cli-plugins/docker-compose

# Re-map the container user's UID/GID to match the host user, so bind-mounted
# files are readable/writable without permission issues.
ARG WANTED_UID=1000
ARG WANTED_GID=1000
RUN groupmod --gid $WANTED_GID hermeswebui 2>/dev/null \
    || groupadd --gid $WANTED_GID hermeswebui \
    ; \
    usermod --uid $WANTED_UID --gid $WANTED_GID hermeswebui

# Create a docker group and add the hermeswebui user to it, so the
# non-root user can talk to the bind-mounted Docker socket on the host.
ARG DOCKER_GID=800
RUN groupadd --gid $DOCKER_GID docker 2>/dev/null || true && \
    usermod -aG docker hermeswebui && \
    echo "Docker CLI + buildx + compose installed; hermeswebui (UID:$WANTED_UID, GID:$WANTED_GID) added to docker group (GID $DOCKER_GID)."

# The Docker socket and DOCKER_HOST are configured entirely at runtime via
# the docker-compose.yml bind-mount + environment variable.
