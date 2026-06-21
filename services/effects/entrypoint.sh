#!/bin/bash
set -e

# Start dbus session bus
dbus-daemon --session --fork --address=unix:path=/dev/shm/dbus-session
export DBUS_SESSION_BUS_ADDRESS=unix:path=/dev/shm/dbus-session

# Start jackd with configured args (default: -d dummy)
if [ -z "$JACKD_ARGS" ]; then
    JACKD_ARGS="-d dummy"
fi
read -r -a jackd_args_arr <<< "$JACKD_ARGS"
jackd "${jackd_args_arr[@]}" &
sleep 2

# Start mod-host in non-forking mode with socket communication
# -n = no-fork, -p = port, -f = feedback port
mod-host -n -p 5555 -f 5556 &
sleep 2

if [ -z "$MOD_DATA_DIR" ]; then
    export MOD_DATA_DIR="/var/mod/data"
fi

mkdir -p "${MOD_DATA_DIR}"

exec mod-ui
