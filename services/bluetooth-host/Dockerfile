FROM ubuntu:24.04

# Inspired by https://medium.com/omi-uulm/how-to-run-containerized-bluetooth-applications-with-bluez-dced9ab767f6

# install bluez related packages
RUN apt-get update && apt-get install -y --no-install-recommends \
    bluez \
    dbus \
    sudo \
    pulseaudio-module-bluetooth

COPY ./bluezuser.conf /etc/dbus-1/system.d/
RUN useradd -m bluezuser \
    && adduser bluezuser sudo \
    && passwd -d bluezuser
USER bluezuser

COPY entrypoint /
ENTRYPOINT [ "/entrypoint" ]
