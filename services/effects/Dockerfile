FROM ubuntu:24.04 AS loader

ARG TARGETPLATFORM
SHELL [ "bash", "-c" ]
RUN apt-get update && apt-get install -y \
    wget=1.21.4* \
    && if [[ "${TARGETPLATFORM}" == "linux/arm64" ]]; then \
        BINARY_URL="https://github.com/mikeoliphant/neural-amp-modeler-lv2/releases/download/v0.2.0/neural_amp_modeler_lv2_rpi5.tgz"; \
    elif [[ "${TARGETPLATFORM}" == "linux/amd64" ]]; then \
        BINARY_URL="https://github.com/mikeoliphant/neural-amp-modeler-lv2/releases/download/v0.2.0/neural_amp_modeler_lv2_linux_x64.tgz"; \
    fi \
    && wget "${BINARY_URL}" -O /tmp/neural_amp_modeler_lv2.tgz \
    && wget https://raw.githubusercontent.com/mikeoliphant/NeuralAudio/refs/tags/v0.1.0/Utils/Models/BossWN-feather.nam -O /tmp/BossWN-feather.nam


FROM python:3.12.4 AS builder

RUN apt-get update && apt-get install -y \
    build-essential \
    pkg-config \
    lv2-dev \
    libjack-jackd2-dev \
    liblilv-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/mod-host
RUN --mount=type=bind,from=github-mod-host,target=.,rw \
    make \
    && make install


FROM ubuntu:24.04 AS runtime

RUN apt-get update && apt-get install -y \
    python3 \
    python3-pip \
    jackd2 \
    liblilv-0-0 \
    && rm -rf /var/lib/apt/lists/*

# TODO use pyenv Dockerfile layer
RUN pip3 install --break-system-packages --no-cache-dir fastapi uvicorn[standard] python-multipart

ENV LV2_PATH=/opt/lv2
RUN --mount=type=bind,from=loader,source=/tmp,destination=/tmp \
    mkdir -p ${LV2_PATH} \
    && mkdir -p /opt/nam/models \
    && mkdir -p /var/nam \
    && cd ${LV2_PATH} \
    && tar xf /tmp/neural_amp_modeler_lv2.tgz \
    && cp /tmp/BossWN-feather.nam /opt/nam/models/

COPY --from=builder /usr/local/bin/mod-host /usr/local/bin/mod-host

COPY main.py /opt/nam/main.py
COPY entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]
