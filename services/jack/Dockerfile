FROM debian:bookworm-slim

RUN apt-get update && apt-get install -y \
    jackd2 \
    libasound2-plugins \
    libjack-jackd2-0 && \
    rm -rf /var/lib/apt/lists/*

# Ensure /dev/shm is writable for JACK ringbuffers
RUN mkdir -p /dev/shm && chmod 1777 /dev/shm

# Create non-root user
RUN useradd -m -s /bin/bash jack && \
    chown -R jack:jack /dev/shm

ENTRYPOINT [ "bash", "-c", "dbus-daemon --session --fork --address=unix:path=/tmp/dbus-session && export DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/dbus-session && jackd -d alsa -d hw:DUOCAPTURE -r 48000" ]

# ENTRYPOINT ["jackd", "-d", "alsa", "-r", "48000", "-p", "512"]