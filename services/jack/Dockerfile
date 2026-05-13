FROM python:3.12.4

RUN apt-get update && apt-get install -y jackd2

ENTRYPOINT [ "bash", "-c", "dbus-daemon --session --fork --address=unix:path=/tmp/dbus-session && export DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/dbus-session && jackd -d alsa -d hw:DUOCAPTURE -r 48000" ]
