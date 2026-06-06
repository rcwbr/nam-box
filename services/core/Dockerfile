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

FROM python:3.12

RUN apt-get update && apt-get install -y \
    jackd2 \
    jalv \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir fastapi uvicorn[standard] python-multipart

ENV LV2_PATH=/opt/lv2
RUN mkdir -p ${LV2_PATH} \
    && mkdir -p /opt/nam/models \
    && mkdir -p /var/nam

RUN --mount=type=bind,from=loader,source=/tmp,destination=/tmp \
    cd ${LV2_PATH} \
    && tar xf /tmp/neural_amp_modeler_lv2.tgz \
    && cp /tmp/BossWN-feather.nam /opt/nam/models/

# Create default model config
RUN echo "/opt/nam/models/BossWN-feather.nam" > /opt/nam/models/current_model.txt

ENV DBUS_SESSION_BUS_ADDRESS=unix:path=/dev/shm/dbus-session

COPY entrypoint.sh /opt/nam/
RUN chmod +x /opt/nam/entrypoint.sh
COPY main.py /opt/nam/

ENTRYPOINT ["/opt/nam/entrypoint.sh"]
