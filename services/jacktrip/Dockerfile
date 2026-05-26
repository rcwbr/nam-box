FROM jacktrip/jacktrip

# # Build JackTrip with WebTransport support (msquic)
# FROM ubuntu:22.04 AS builder

# # Install build dependencies
# RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
#     build-essential \
#     meson \
#     ninja-build \
#     git \
#     cmake \
#     libssl-dev \
#     libasound2-dev \
#     libjack-jackd2-dev \
#     python3 \
#     libsystemd-dev \
#     wget \
#     && rm -rf /var/lib/apt/lists/*

# # Clone and build msquic for WebTransport support
# WORKDIR /msquic
# RUN git clone --depth 1 https://github.com/microsoft/msquic.git . \
#     && git submodule update --init

# WORKDIR /msquic/build
# RUN cmake .. -DCMAKE_BUILD_TYPE=Release -DHIREDIS=OFF -DCMAKE_POSITION_INDEPENDENT_CODE=ON
# RUN cmake --build . --config Release -j$(nproc)
# RUN cmake --install . --prefix /usr/local

# # Clone and build JackTrip with msquic for WebTransport
# WORKDIR /build
# RUN git clone --depth 1 https://github.com/jacktrip/jacktrip.git . \
#     && git submodule update --init --recursive

# # Configure with msquic for WebTransport support
# RUN PKG_CONFIG_PATH=/usr/local/lib/pkgconfig meson setup builddir -Dnogui=true -Dmsquic=enabled

# # Build
# RUN meson compile -C builddir -j$(nproc)

# # Runtime image
# FROM ubuntu:22.04

# # Install runtime dependencies
# RUN apt-get update && DEBIAN_FRONTEND=noninteractive apt-get install -y \
#     libasound2 \
#     libjack-jackd2-0 \
#     libssl3 \
#     libsystemd0 \
#     libgcc-s1 \
#     && rm -rf /var/lib/apt/lists/*

# # Copy msquic libraries
# COPY --from=builder /usr/local/lib/libmsquic.so* /usr/lib/

# # Copy built binary
# COPY --from=builder /build/builddir/jacktrip /usr/local/bin/jacktrip

# ENTRYPOINT ["jacktrip"]