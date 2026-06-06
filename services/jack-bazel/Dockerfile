FROM --platform=linux/amd64 gcr.io/bazel-public/bazel:9.1.0 AS builder

WORKDIR /workspace

ARG TARGETPLATFORM
RUN --mount=type=bind,source=.,destination=/workspace,rw \
    --mount=type=cache,target=/home/ubuntu/.cache/bazel,uid=1000 \
    export PLATFORM=$(echo "${TARGETPLATFORM}" | sed 's|.*/||;s/$/_platform/') \
    && echo "Building jack for ${TARGETPLATFORM} platform with ${PLATFORM} LLVM toolchain" \
    && bazel \
        --output_user_root=/tmp/bazel_output \
        build \
        --disk_cache=/home/ubuntu/.cache/bazel \
        --platforms=//:${PLATFORM} \
        @jack//...

FROM debian:trixie-slim

# JACK runtime dependencies
RUN apt-get update && apt-get install -y \
    libasound2 \
    libasound2-plugins \
    libsamplerate0 \
    curl \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Debugging tools (can be removed in production)
RUN apt-get update && apt-get install -y \
    gdb \
    strace \
    procps \
    && rm -rf /var/lib/apt/lists/*

# Ensure /dev/shm is writable for JACK ringbuffers
RUN mkdir -p /dev/shm && chmod 1777 /dev/shm

# Create shared directory for JACK client sockets
RUN mkdir -p /jack-sockets && chmod 1777 /jack-sockets

# Create non-root user
RUN useradd -m -s /bin/bash jack && \
    chown -R jack:jack /dev/shm /jack-sockets && \
    usermod -a -G audio jack

# Create the JACK addon directory for driver shared libraries
RUN mkdir -p /usr/local/lib/jack

# Copy the built jackd binary
RUN --mount=type=bind,from=builder,source=/tmp/bazel_output,destination=/tmp/bazel_output,rw \
    cd /tmp/bazel_output/*/execroot/_main/bazel-out/*/bin/external/+http_archive+jack \
    && cp jackd /usr/bin/jackd \
    && mv libjack_internal.so /usr/local/lib/jack/libjack_internal.so \
    && find . -maxdepth 1 -iname "libjack*.so" | xargs -I {} sh -c 'mv $0 /usr/local/lib/jack/$(echo "$0" | sed "s|^\./||;s|libjack|jack|")' {} \
    && find . -maxdepth 1 -iname "lib*.so" | xargs -I {} sh -c 'mv $0 /usr/local/lib/jack/$(echo "$0" | sed "s|^\./||;s|lib||")' {}

USER jack
WORKDIR /home/jack

ENTRYPOINT ["jackd", "-d", "alsa", "-r", "48000"]
