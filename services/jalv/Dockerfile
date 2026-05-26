# =============================================================================
# Runtime Stage - Jalv LV2 Host with NAM LV2 Plugin
# =============================================================================
#
# This image is designed to be used with the nam-bazel build via multi-stage:
#
# FROM ghcr.io/rcwbr/nam-box/jalv AS jalv-runner
# COPY --from=nam-bazel-builder /path/to/built/plugin /usr/local/lib/lv2/
#
# For standalone testing, the NAM LV2 plugin can be mounted at runtime:
# docker run -v /path/to/neural_amp_modeler.lv2:/usr/local/lib/lv2/neural_amp_modeler.lv2 ...
# =============================================================================

FROM debian:trixie-slim

# Jalv runtime dependencies
RUN apt-get update && apt-get install -y \
    libjack-jackd2-0 \
    liblilv-0-0 \
    jalv \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd -m -s /bin/bash jalv

USER jalv
WORKDIR /home/jalv

ENV LV2_PATH=/usr/local/lib/lv2
ENTRYPOINT ["/usr/bin/jalv"]