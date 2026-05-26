# Builder stage - compile neural-amp-modeler-lv2 from remote source
FROM python:3 AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    ccache \
    cmake \
    git \
    jackd2 \
    liblilv-dev \
    meson \
    ninja-build

# Configure ccache
ENV CCACHE_DIR=/ccache

# git reset --hard a8ba46997bc26641a9d42f527d8a8dce49b87713 && \
# git reset --hard 8493866b218bf3f390e25b68bdbdafd82ff092a2 && \
# Clone and build Neural Amp Modeler LV2 with submodules
RUN --mount=type=cache,target=/ccache \
    git clone -j$(nproc) --recurse-submodules --branch v0.1.9 https://github.com/mikeoliphant/neural-amp-modeler-lv2 /src/nam-lv2 && \
    cd /src/nam-lv2/build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER_LAUNCHER=ccache -DCMAKE_CXX_COMPILER_LAUNCHER=ccache && \
    make -j$(nproc)

# # Runtime stage - minimal image with just the plugin
FROM python:3 AS final

RUN apt-get update && apt-get install -y \
    jackd2 \
    liblilv-dev \
    jalv \
    && rm -rf /var/lib/apt/lists/*

# Copy built plugin bundle as a proper LV2 bundle directory
COPY --from=builder /src/nam-lv2/build/neural_amp_modeler.lv2 /usr/local/lib/lv2/neural_amp_modeler.lv2

# Create non-root user
RUN useradd -m -s /bin/bash nam

USER nam
WORKDIR /home/nam

ENV LV2_PATH=/usr/local/lib/lv2
# This container provides the plugin; jalv runs separately
CMD ["bash"]