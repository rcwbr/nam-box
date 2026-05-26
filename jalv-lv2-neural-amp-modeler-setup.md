# Jalv LV2 Plugin Host Configuration

This document describes the strategy and steps to configure Jalv (JAck LV2) to host LV2 plugins, specifically the Neural Amp Modeler LV2 plugin.

## Overview

Jalv is a lightweight LV2 host that exposes plugin ports as JACK ports, making LV2 plugins behave like standalone applications. This configuration replaces the simplified approach in `services/nam/Dockerfile` with a proper LV2 toolchain.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    Audio Processing Chain                    │
├─────────────────────────────────────────────────────────────┤
│  Audio Input ──► neural-amp-modeler-lv2 ──► Audio Output   │
│        │              ▲     │                              │
│        │              │     │ Model file                 │
│        └──────────────┼─────┘                              │
│                       │                                    │
│                       ▼                                    │
│                   Jalv Host (JACK backend)                 │
└─────────────────────────────────────────────────────────────┘
```

## Prerequisites

- Linux with JACK audio server
- Meson build system (for building from source)
- CMake (for neural-amp-modeler-lv2)
- Git with submodule support

## Step 1: Build LV2 Core Library

The LV2 core provides headers and the base specification required by all LV2 plugins.

```bash
cd /workspaces/nam-box/subdirs/lv2
meson setup build -Dtests=disabled -Ddocs=disabled -Dplugins=disabled -Dold_headers=false
meson compile -C build
sudo meson install -C build
```

This installs LV2 headers to `/usr/local/include/lv2/` and the pkg-config file for plugin discovery.

## Step 2: Build Jalv

Jalv requires several dependencies that can be built as Meson subprojects:

```bash
cd /workspaces/nam-box/subdirs/jalv

# Configure with JACK backend (recommended for low-latency audio)
meson setup build \
  -Djack=enabled \
  -Dportaudio=disabled \
  -Dgtk3=disabled \
  -Dqt5=disabled \
  -Dqt6=disabled \
  -Dsuil=enabled

meson compile -C build
sudo meson install -C build
```

If building dependencies from source, add fallback paths:

```bash
meson setup build \
  --wrap-mode=nodownload \
  -Dlv2:fallback=true \
  -Dserd:fallback=true \
  -Dsord:fallback=true \
  -Dsratom:fallback=true \
  -Dlilv:fallback=true \
  -Dzix:fallback=true
```

## Step 3: Build Neural Amp Modeler LV2

The plugin requires the NeuralAudio dependency:

```bash
cd /workspaces/nam-box/subdirs/neural-amp-modeler-lv2

# Clone with submodules (NeuralAudio and LV2 headers)
git clone --recurse-submodules -j4 https://github.com/mikeoliphant/neural-amp-modeler-lv2
mkdir build && cd build

# Configure and build
cmake .. -DCMAKE_BUILD_TYPE="Release" -DUSE_NATIVE_ARCH=ON
make -j4
```

The plugin bundle will be created at `build/neural_amp_modeler.lv2/`.

## Step 4: Configure Plugin Discovery

LV2 plugins are discovered via the `LV2_PATH` environment variable. Set it to include the plugin location:

```bash
# For system-wide installation
export LV2_PATH=/usr/local/lib/lv2:/usr/lib/lv2:$HOME/.lv2

# Or for local development
export LV2_PATH=$PWD/build/neural_amp_modeler.lv2:$LV2_PATH
```

To make this persistent, add to your shell profile:

```bash
echo 'export LV2_PATH="$HOME/.lv2:/usr/local/lib/lv2:/usr/lib/lv2"' >> ~/.bashrc
```

## Step 5: Run Jalv with Neural Amp Modeler

### Basic Invocation

```bash
# List available plugins
jalv --list

# Run the Neural Amp Modeler plugin
jalv --plugin "http://github.com/mikeoliphant/neural-amp-modeler-lv2"

# With sample rate matching your model (typically 48000 Hz)
jalv --plugin "http://github.com/mikeoliphant/neural-amp-modeler-lv2" --sample-rate 48000
```

### Select Model File

After launching, load a model via the plugin's control port or programmatically:

```bash
# Using jack_connect for model path (requires host support)
jack_connect "your-host:control-out" "neural_amp_modeler:Model Path In"
```

For hosts that support atom:Path parameters (Carla, Ardour, REAPER), you can set the model path through the UI.

## Step 6: JACK Audio Routing

Connect Jalv's audio ports to your audio interface:

```bash
# List Jalv ports
jack_lsp | grep neural_amp_modeler

# Connect input/output
jack_connect "system:capture_1" "neural_amp_modeler:left-in"
jack_connect "neural_amp_modeler:left-out" "system:playback_1"
jack_connect "system:capture_2" "neural_amp_modeler:right-in"
jack_connect "neural_amp_modeler:right-out" "system:playback_2"
```

## Docker Deployment Strategy

### Jalv + NAM Plugin in One Container (JACK Separate)

This approach packages Jalv and the Neural Amp Modeler plugin together in one container, with JACK running separately:

```dockerfile
# Builder stage
FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    meson \
    ninja-build \
    libjack-jackd2-dev \
    liblilv-dev \
    libsuil-dev \
    libserd-dev \
    libsord-dev \
    libsratom-dev \
    libzix-dev

# Build LV2
COPY subdirs/lv2 /src/lv2
RUN cd /src/lv2 && \
    meson setup build -Dtests=disabled -Ddocs=disabled -Dold_headers=false && \
    meson compile -C build && \
    meson install -C build && \
    ldconfig

# Build Jalv
COPY subdirs/jalv /src/jalv
RUN cd /src/jalv && \
    meson setup build -Djack=enabled -Dsuil=enabled && \
    meson compile -C build && \
    meson install -C build

# Build Neural Amp Modeler LV2
COPY subdirs/neural-amp-modeler-lv2 /src/nam-lv2
RUN cd /src/nam-lv2 && \
    mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DUSE_NATIVE_ARCH=ON && \
    make -j$(nproc) && \
    make install

# Runtime stage
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libjack-jackd2-0 \
    liblilv-0-0 \
    libsuil-0-0 \
    libserd-0-0 \
    libsord-0-0 \
    libsratom-0-0 \
    libzix-0-1 \
    && rm -rf /var/lib/apt/lists/*

# Copy built artifacts
COPY --from=builder /usr/local/bin/jalv /usr/local/bin/
COPY --from=builder /usr/local/lib/lv2/neural_amp_modeler.lv2 /usr/local/lib/lv2/

# Create non-root user
RUN useradd -m -s /bin/bash nam
USER nam

ENV LV2_PATH=/usr/local/lib/lv2
ENTRYPOINT ["jalv", "--plugin", "http://github.com/mikeoliphant/neural-amp-modeler-lv2"]
```

### Container Layout (JACK Separate, Jalv+NAM Together)

```
┌─────────────────────────────────────────────────────────────┐
│                        Docker Compose Network                        │
├─────────────────────────────────────────────────────────────┤
│  jack-container (JACK server)                                 │
│  ├─ jackd daemon                                             │
│  ├─ ALSA device access (/dev/snd)                            │
│  └─ IPC shared with jalv-container                           │
│                                                               │
│  jalv-container (LV2 host + plugin)                           │
│  ├─ jalv executable                                           │
│  ├─ neural-amp-modeler-lv2 plugin (bundled)                  │
│  ├─ IPC shared with jack-container                            │
│  └─ Shares /dev/shm for JACK ringbuffers                     │
└─────────────────────────────────────────────────────────────┘
```

## Multi-Container Docker Architecture

For production deployments with isolation and scalability, run JACK, Jalv, and the Neural Amp Modeler as separate containers sharing IPC namespace.

### Container Layout

```
┌─────────────────────────────────────────────────────────────────────┐
│                        Docker Compose Network                        │
├─────────────────────────────────────────────────────────────────────┤
│  jack-container (JACK server)                                         │
│  ├─ jackd daemon                                                     │
│  ├─ IPC shared with jalv-container                                    │
│  └─ ALSA device access (/dev/snd)                                    │
│                                                                       │
│  jalv-container (LV2 host)                                            │
│  ├─ jalv executable                                                    │
│  ├─ neural-amp-modeler-lv2 plugin                                    │
│  ├─ IPC shared with jack-container                                     │
│  └─ Shares /dev/shm for JACK ringbuffers                             │
│                                                                       │
│  model-storage (optional sidecar)                                     │
│  └─ Mounted model files for plugin                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  jack:
    image: ghcr.io/rcwbr/nam-box/jack:local
    ipc: host
    devices:
      - /dev/snd:/dev/snd
    environment:
      - JACK_DRIVER=alsa
      - JACK_SAMPLE_RATE=48000
    volumes:
      - jack-shm:/dev/shm
    cap_add:
      - SYS_NICE
      - IPC_LOCK
    security_opt:
      - seccomp=unconfined
    ulimits:
      memlock: -1

  jalv:
    image: ghcr.io/rcwbr/nam-box/jalv:local
    ipc: "service:jack"
    depends_on:
      jack:
        condition: service_started
    devices:
      - /dev/snd:/dev/snd
    volumes:
      - jack-shm:/dev/shm
      - ./models:/usr/local/share/nam-models:ro
    environment:
      - LV2_PATH=/usr/local/lib/lv2
      - JACK_NO_AUDIO_RESERVATION=1
    command: >
      jalv
      --plugin "http://github.com/mikeoliphant/neural-amp-modeler-lv2"
      --sample-rate 48000
    cap_add:
      - SYS_NICE
      - IPC_LOCK
    security_opt:
      - seccomp=unconfined

volumes:
  jack-shm:
    driver: local
    driver_opts:
      type: tmpfs
      device: tmpfs
      o: size=64m,mode=1777
```

### Container Communication Mechanisms

| Resource | Shared Via | Purpose |
|----------|-------------|---------|
| POSIX shared memory | `ipc:` or `/dev/shm` volume | JACK ringbuffers |
| UNIX domain sockets | `/tmp` or mounted socket dir | JACK client connections |
| Device access | `devices:` | ALSA audio interface |
| Environment | `environment:` | JACK settings, plugin configuration |

### Required Image Modifications

**Jack Container (`services/jack`):**
```dockerfile
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    jackd2 \
    libasound2-plugins

# Ensure JACK can start with IPC
RUN mkdir -p /dev/shm && chmod 1777 /dev/shm

ENTRYPOINT ["jackd", "-d", "alsa", "-r", "48000", "-p", "512"]
```

**Jalv Container (`services/jalv/Dockerfile`):**
This container includes both Jalv and the NAM plugin bundled together:

```dockerfile
# Builder stage - compile Jalv and Neural Amp Modeler LV2
FROM debian:bookworm-slim AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    cmake \
    meson \
    ninja-build \
    libjack-jackd2-dev \
    liblilv-dev \
    libsuil-dev \
    libserd-dev \
    libsord-dev \
    libsratom-dev \
    libzix-dev

# Build LV2
COPY subdirs/lv2 /src/lv2
RUN cd /src/lv2 && \
    meson setup build -Dtests=disabled -Ddocs=disabled -Dold_headers=false && \
    meson compile -C build && \
    meson install -C build && \
    ldconfig

# Build Jalv
COPY subdirs/jalv /src/jalv
RUN cd /src/jalv && \
    meson setup build -Djack=enabled -Dsuil=enabled && \
    meson compile -C build && \
    meson install -C build

# Build Neural Amp Modeler LV2
COPY subdirs/neural-amp-modeler-lv2 /src/nam-lv2
RUN cd /src/nam-lv2 && \
    mkdir build && cd build && \
    cmake .. -DCMAKE_BUILD_TYPE=Release -DUSE_NATIVE_ARCH=ON && \
    make -j$(nproc) && \
    make install

# Runtime stage
FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    libjack-jackd2-0 \
    liblilv-0-0 \
    libsuil-0-0 \
    libserd-0-0 \
    libsord-0-0 \
    libsratom-0-0 \
    libzix-0-1 \
    && rm -rf /var/lib/apt/lists/*

# Copy built artifacts
COPY --from=builder /usr/local/bin/jalv /usr/local/bin/
COPY --from=builder /usr/local/lib/lv2/neural_amp_modeler.lv2 /usr/local/lib/lv2/

# Create non-root user
RUN useradd -m -s /bin/bash jalv
USER jalv
WORKDIR /home/jalv

ENV LV2_PATH=/usr/local/lib/lv2
ENTRYPOINT ["jalv"]
```

### Key Considerations for Multi-Container Setup

1. **IPC Namespace**: The `jalv` container must share the same IPC namespace with `jack` (`ipc: "service:jack"`) for JACK's shared memory to work.

2. **Memory Locking**: Both containers need `IPC_LOCK` capability and `--ulimit memlock=-1` to prevent audio glitches from memory paging.

3. **Sample Rate Matching**: Ensure both containers use the same sample rate (48kHz recommended) as the NAM models.

4. **Startup Order**: The JACK container must start first. Use `depends_on` with `service_started` condition.

5. **Plugin Discovery**: Since Jalv and NAM are bundled in the same container, `LV2_PATH=/usr/local/lib/lv2` discovers the plugin automatically—no named volume needed.

6. **Model Loading**: Models can be mounted via a volume and loaded via the plugin's control port:
   ```bash
   volumes:
     - ./models:/usr/local/share/nam-models:ro
   ```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `LV2_PATH` | Colon-separated paths to search for LV2 plugins | `/usr/lib/lv2:/usr/local/lib/lv2:$HOME/.lv2` |
| `JACK_NO_AUDIO_RESERVATION` | Disable JACK audio device reservation | `0` |
| `JACK_DRIVER` | JACK backend driver | `alsa` |

## Troubleshooting

### Plugin Not Found

```bash
# Verify plugin bundle structure
ls -R neural_amp_modeler.lv2/

# Check with lv2info
lv2info http://github.com/mikeoliphant/neural-amp-modeler-lv2

# Verify LV2_PATH includes the directory containing .lv2
echo $LV2_PATH
```

### JACK Connection Issues

```bash
# Start JACK server
jackd -d alsa -r 48000 -p 512 &

# Or use jack_control
jack_control start
```

### Model Loading Errors

- Ensure the model file path is accessible
- Verify model sample rate matches the host sample rate
- Check that the model format is supported (NAM `.nam` or RTNeural `.json`)

## Validation Checklist

- [ ] LV2 core library installed with headers in `/usr/local/include/lv2/`
- [ ] Jalv built with JACK backend and installed to `/usr/local/bin/jalv`
- [ ] Neural Amp Modeler plugin built to `neural_amp_modeler.lv2/` bundle
- [ ] `LV2_PATH` environment variable includes plugin location
- [ ] JACK server running at matching sample rate (48kHz recommended)
- [ ] Audio routing configured between system and plugin ports
- [ ] Model file loaded and processing audio correctly

## Related Files

- `subdirs/jalv/` - Jalv source code and build configuration
- `subdirs/lv2/` - LV2 core specification library
- `subdirs/neural-amp-modeler-lv2/` - NAM LV2 plugin source
- `services/nam/Dockerfile` - Current naive implementation to replace