#!/bin/bash
set -e

# Start dbus session bus
dbus-daemon --session --fork --address=unix:path=/dev/shm/dbus-session
export DBUS_SESSION_BUS_ADDRESS=unix:path=/dev/shm/dbus-session

cd /opt/nam
# Start the Python API (which will manage jackd, jalv, and model loading)
exec uvicorn main:app --host 0.0.0.0 --port 8000
