# JACK in Docker - Current State Summary

## Core Issues

### 1. Memory Lock (mlock) Failure

- **Symptom**: `Cannot lock down 107350048 byte memory area (Cannot allocate memory)`
- **Result**: `Bus error (core dumped)`
- **Scope**: Occurs regardless of:
  - Realtime vs non-realtime mode (`--no-realtime`)
  - Privilege level (`--privileged` mode)
  - Buffer settings (`-p`/`-n` parameters)

The 107MB allocation appears to be an internal JACK ringbuffer/port allocation that is not configurable at runtime.

### 2. Filesystem/Berkeley DB Error

- **Symptom**: `BDB0137 write: No space left on device`
- **Secondary Error**: `Cannot open DB environment: No space left on device`
- **Cause**: JACK runtime state directory issues
- **Fix**: Clean `/tmp/.jack*` before container runs

## Tested Solutions

| Configuration          | Command                                         | Result                                    |
| ---------------------- | ----------------------------------------------- | ----------------------------------------- |
| Standard with IPC_LOCK | `--cap-add=IPC_LOCK --ulimit memlock=104857600` | Failed - ulimit not writable in container |
| Privileged mode        | `--privileged`                                  | Failed - still Bus error                  |
| No realtime            | `jackd --no-realtime`                           | Failed - mlock still attempted            |
| Soft-mode (working)    | `jackd -s -d alsa -d hw:DUOCAPTURE -r 48000`    | **Works**                                 |
| With smaller buffers   | `-p 512 -n 2`                                   | Works in soft-mode                        |

## Working Configuration (Non-ideal)

```bash
jackd -s -d alsa -d hw:DUOCAPTURE -r 48000 -p 512 -n 2
```

**Drawback**: Soft-mode (`-s`) is not true realtime audio.

## Docker Run Commands

### Working (soft-mode):

```bash
docker run --rm -it \
	--device /dev/snd \
	--cap-add SYS_NICE \
	--cap-add SYS_RAWIO \
	ghcr.io/rcwbr/nam-box-jack:local bash

# Inside container:
jackd -s -d alsa -d hw:DUOCAPTURE -r 48000 -p 512 -n 2
```

### Desired (realtime) - Currently Broken:

```bash
docker run --rm -it \
	--device /dev/snd \
	--cap-add SYS_NICE \
	--cap-add SYS_RAWIO \
	--cap-add IPC_LOCK \
	--security-opt seccomp=unconfined \
	--ulimit memlock=-1 \
	ghcr.io/rcwbr/nam-box-jack:local bash

# Inside container:
jackd -d alsa -d hw:DUOCAPTURE -r 48000 # Crashes with Bus error
```

## Next Steps

1. **Root cause investigation** - system calls work but JACK fails:

   - Direct `mlock()` and `mlockall()` both succeed with 107MB+
   - But JACK still reports "Cannot lock down 107350048 byte memory area"
   - `--no-mlock` flag NOT supported in this version (1.9.21) - flag absent from help
   - `JACK_NO_MLOCK` env var does NOT work (not recognized by binary)

1. **Key findings**:

   - ulimit -l shows "unlimited" in container
   - cgroup shows "max" for memory.max
   - Host has 6.9GB available, plenty for 107MB allocation
   - Python ctypes `mlock()` and `mlockall()` both succeed
   - Issue is JACK's specific memory allocation method/alignment

1. **Investigate `/etc/security/limits.d/audio.conf`** - `@audio` group memlock unlimited

1. **Test newer JACK version** (jackd 1.9.22+ which may have no-mlock support)

1. **Consider alternative base image** with different libc/kernel

1. **Check JACK ringbuffer alignment** - allocator may require page-aligned memory

## Environment Variables Tested

| Variable                    | Value        | Result                                   |
| --------------------------- | ------------ | ---------------------------------------- |
| `JACK_NO_MLOCK`             | `1` or `yes` | Ignored (not supported in 1.9.21)        |
| `JACK_NO_AUDIO_RESERVATION` | `1`          | Works - bypasses DBus device reservation |

ericweber@nam-box:~$ docker run --rm -it --device /dev/snd:/dev/snd --cap-add=SYS_NICE --cap-add=SYS_RAWIO --cap-add=IPC_LOCK --entrypoint bash --network=host --shm-size=128M --privileged --name jack ghcr.io/rcwbr/nam-box-jack:local
root@nam-box:/# dbus-daemon --session --fork --address=unix:path=/tmp/dbus-session && export DBUS_SESSION_BUS_ADDRESS=unix:path=/tmp/dbus-session && jackd -d alsa -d hw:DUOCAPTURE -r 48000
jackdmp 1.9.21
Copyright 2001-2005 Paul Davis and others.
Copyright 2004-2016 Grame.
Copyright 2016-2022 Filipe Coelho.
jackdmp comes with ABSOLUTELY NO WARRANTY
This is free software, and you are welcome to redistribute it
under certain conditions; see the file COPYING for details
JACK server starting in realtime mode with priority 10
self-connect-mode is "Don't restrict self connect requests"
audio_reservation_init
Acquire audio card Audio2
creating alsa driver ... hw:DUOCAPTURE|hw:DUOCAPTURE|1024|2|48000|0|0|nomon|swmeter|-|32bit
configuring for 48000Hz, period = 1024 frames (21.3 ms), buffer = 2 periods
ALSA: final selected sample format for capture: 24bit little-endian in 3bytes format
ALSA: use 2 periods for capture
ALSA: final selected sample format for playback: 24bit little-endian in 3bytes format
ALSA: use 2 periods for playback

docker exec -it jack bash
root@nam-box:/# jack_simple_client
