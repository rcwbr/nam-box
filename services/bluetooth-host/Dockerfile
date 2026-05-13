FROM ubuntu:24.04

# Inspired by https://medium.com/omi-uulm/how-to-run-containerized-bluetooth-applications-with-bluez-dced9ab767f6

# install bluez related packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    dbus \
    sudo


COPY ./bluezuser.conf /etc/dbus-1/system.d/
RUN useradd -m bluezuser \
    && adduser bluezuser sudo \
    && passwd -d bluezuser
USER bluezuser

COPY docker-entrypoint.sh /
ENTRYPOINT [ "/docker-entrypoint.sh" ]
LABEL io.containerd.image.name=ghcr.io/rcwbr/nam-box-bluetooth-host:local
