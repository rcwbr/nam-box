FROM python:3.10.20 AS loader

ARG TARGETPLATFORM
SHELL [ "/bin/bash", "-c" ]
RUN \
    if [[ "${TARGETPLATFORM}" == "linux/arm64" ]]; then \
        BINARY_URL="https://github.com/mikeoliphant/neural-amp-modeler-lv2/releases/download/v0.2.0/neural_amp_modeler_lv2_rpi5.tgz"; \
    elif [[ "${TARGETPLATFORM}" == "linux/amd64" ]]; then \
        BINARY_URL="https://github.com/mikeoliphant/neural-amp-modeler-lv2/releases/download/v0.2.0/neural_amp_modeler_lv2_linux_x64.tgz"; \
    fi \
    && wget --progress=dot:giga "${BINARY_URL}" -O /tmp/neural_amp_modeler_lv2.tgz


FROM python:3.10.20 AS host-builder

RUN apt-get update && apt-get install --no-install-recommends -y \
    lv2-dev=1.18.10* \
    libjack-jackd2-dev=1.9.22* \
    liblilv-dev=0.24.26* \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/mod-host
RUN --mount=type=bind,from=github-mod-host,target=.,rw \
    make \
    && make install


FROM python:3.10.20 AS ui-builder

RUN apt-get update && apt-get install --no-install-recommends -y \
    libjack-jackd2-dev=1.9.22* \
    liblilv-dev=0.24.26* \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /tmp/mod-ui
RUN --mount=type=bind,from=github-mod-ui,target=.,rw \
    make -C utils \
    && cp utils/libmod_utils.so /usr/local/lib/libmod_utils.so


FROM python:3.10.20 AS runtime

RUN apt-get update && apt-get install --no-install-recommends -y \
    dbus-daemon=1.16.2* \
    jackd2=1.9.22* \
    libjack-jackd2-dev=1.9.22* \
    liblilv-0-0=0.24.26* \
    && rm -rf /var/lib/apt/lists/*

ENV LV2_PATH=/opt/lv2
# hadolint ignore=DL3003
RUN --mount=type=bind,from=loader,source=/tmp,destination=/tmp \
    mkdir -p ${LV2_PATH} \
    && mkdir -p /opt/nam/models \
    && mkdir -p /var/nam \
    && cd ${LV2_PATH} \
    && tar xf /tmp/neural_amp_modeler_lv2.tgz

COPY --from=host-builder /usr/local/bin/mod-host /usr/local/bin/mod-host

WORKDIR /tmp/mod-ui
COPY --from=ui-builder /usr/local/lib/libmod_utils.so /usr/local/lib/libmod_utils.so
RUN --mount=type=bind,from=github-mod-ui,target=.,rw \
    cp /usr/local/lib/libmod_utils.so utils/libmod_utils.so \
    && pip install --no-cache-dir --break-system-packages -r requirements.txt \
    && pip install --no-cache-dir --break-system-packages . \
    && pip install --no-cache-dir --upgrade pyserial==3.5 \
    && sed -i 's/collections.MutableMapping/collections.abc.MutableMapping/g' /usr/local/lib/python3.10/site-packages/tornado/httputil.py

COPY entrypoint.sh /entrypoint.sh

ENTRYPOINT [ "/entrypoint.sh" ]
