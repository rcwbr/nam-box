# =============================
# Builder Stage - Bazel (amd64 cross-compiling to arm64)
# =============================
FROM --platform=linux/amd64 gcr.io/bazel-public/bazel:9.1.0 AS builder

WORKDIR /workspace

ARG TARGETPLATFORM
# Cross-compile using --compiler flag for aarch64
RUN --mount=type=bind,source=.,destination=/workspace,rw \
    --mount=type=cache,target=/home/ubuntu/.cache/bazel,uid=1000 \
    echo "Building for ${TARGETPLATFORM} platform with LLVM toolchain" && \
    bazel --output_user_root=/tmp/bazel_output build --disk_cache=/home/ubuntu/.cache/bazel --platforms=//:arm64_platform //:nam_lv2_plugin //:jalv
    # TODO actually use specified platform

# =============================
# Runtime Stage - Minimal
# =============================
FROM debian:trixie-slim

RUN apt-get update && apt-get install -y \
    libjack-jackd2-0 \
    libjack-jackd2-dev \
    libasound2 \
    strace \
    gdb \
    && \
    rm -rf /var/lib/apt/lists/*

# Create LV2 bundle directory
RUN mkdir -p /usr/local/lib/lv2/neural_amp_modeler.lv2

# Create shared directory for JACK client sockets (mounted from jack container)
RUN mkdir -p /jack-sockets && chmod 1777 /jack-sockets

# Copy the built shared library
COPY --from=builder /tmp/bazel_output/*/execroot/_main/bazel-out/*/bin/external/+git_repository+nam_lv2/libneural_amp_modeler.so /usr/local/lib/lv2/neural_amp_modeler.lv2/libneural_amp_modeler.so

# Copy the built jalv executable (statically linked with JACK)
COPY --from=builder /tmp/bazel_output/*/execroot/_main/bazel-out/*/bin/external/+git_repository+jalv/jalv /usr/local/bin/jalv

# Copy LV2 metadata and GUI resources
COPY resources/manifest.ttl.in /usr/local/lib/lv2/neural_amp_modeler.lv2/
COPY resources/neural_amp_modeler.ttl.in /usr/local/lib/lv2/neural_amp_modeler.lv2/
COPY resources/modgui.ttl /usr/local/lib/lv2/neural_amp_modeler.lv2/
COPY resources/modgui /usr/local/lib/lv2/neural_amp_modeler.lv2/

# Process the template files
RUN cd /usr/local/lib/lv2/neural_amp_modeler.lv2 && \
    sed -e 's|@NAM_LV2_ID@|http://github.com/mikeoliphant/neural-amp-modeler-lv2|g' \
        -e 's|@CMAKE_SHARED_MODULE_SUFFIX@|.so|g' \
        manifest.ttl.in > manifest.ttl && \
    sed -e 's|@NAM_LV2_ID@|http://github.com/mikeoliphant/neural-amp-modeler-lv2|g' \
        -e 's|@PROJECT_VERSION_MINOR@|0|g' \
        -e 's|@PROJECT_VERSION_PATCH@|1|g' \
        neural_amp_modeler.ttl.in > neural_amp_modeler.ttl && \
    rm -f manifest.ttl.in neural_amp_modeler.ttl.in

RUN useradd -m -s /bin/bash nam
USER nam
WORKDIR /home/nam
ENV LV2_PATH=/usr/local/lib/lv2
# Debug: uncomment to run jalv at container start
# CMD ["jalv", "http://github.com/mikeoliphant/neural-amp-modeler-lv2"]
CMD ["bash"]
