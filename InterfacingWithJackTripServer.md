# Interfacing with JackTrip Server

This document explains how to run a JackTrip hub server and connect clients to audio streams.

## Server Modes

JackTrip operates in two main modes:

### Hub Server Mode (`-S`)

The hub server acts as a central mixing point for multiple clients. It receives audio from all connected clients and distributes mixed audio back to each client.

**Starting a hub server:**

```bash
jacktrip -S [options]
```

**Common hub server options:**

| Option   | Description                                              |
| -------- | -------------------------------------------------------- |
| `-S`     | Run in Hub Server mode                                   |
| `-t`     | Quit after 10 seconds of no network activity             |
| `-z`     | Set buffer to zeros on underrun (default uses wavetable) |
| `-p #`   | Hub patch mode (0-5, see below)                          |
| `-i`     | Include server audio in mix when patching                |
| `-u`     | Upmix mono clients to stereo                             |
| `-U #`   | Set UDP base port (default: 61002)                       |
| `-q #`   | Queue buffer length (default: 4)                         |
| `-r #`   | Packet redundancy (default: 1)                           |
| `-A`     | Require authentication                                   |
| `--auth` | Enable authentication                                    |

### Hub Patch Modes (`-p`)

The `-p` option controls how audio is mixed and routed to clients:

| Mode | Description                                                                            |
| ---- | -------------------------------------------------------------------------------------- |
| `0`  | Server-to-clients: Each client hears only the server's input                           |
| `1`  | Client loopback: Each client hears their own audio back                                |
| `2`  | Client fan out/in (no loopback): Each client hears all other clients except themselves |
| `3`  | Reserved matrix mode                                                                   |
| `4`  | Full mix: All clients hear all other clients mixed together                            |
| `5`  | No auto patching: Manual JACK port management required                                 |

**Example - Full mix server:**

```bash
jacktrip -S -t -z --hubpatch 4
```

## Running the Hub Server

### Prerequisites: JACK Audio Daemon

The hub server requires a running JACK daemon. Start it with the dummy backend if you don't need physical audio I/O:

```bash
# Start JACK with dummy audio driver (no physical interface needed)
jackd -d dummy -r 48000 -p 1024 &

# Or with Pipewire latency settings
jackd -d dummy -r 48000 -p 1024 -C 0 -P 0 &
```

### Starting the Server

```bash
# Basic server
jacktrip -S

# With full mix and auto timeout
jacktrip -S -t -z --hubpatch 4

# Using container (recommended for production)
podman run --name jacktrip --network=host --shm-size=128M -d jacktrip/jacktrip
```

Container environment variables:

- `SAMPLE_RATE`: Audio sample rate (default: 48000)
- `BUFFER_SIZE`: Frames per period (default: 128)
- `JACK_OPTS`: Custom JACK options
- `JACKTRIP_OPTS`: Custom JackTrip options (default: `-S -t -z --hubpatch 4 --bufstrategy 4 -q auto`)

## Connecting Clients to Audio Streams

### Hub Client Mode (`-C`)

Clients connect to the hub server using the ping-to-server mode:

```bash
jacktrip -C <server_ip_or_hostname>
```

**Basic client connection:**

```bash
# Connect to server at specific IP
jacktrip -C 192.168.1.100

# Connect to server by hostname
jacktrip -C jacktrip.example.com
```

### Client Connection Options

| Option    | Description                                       |
| --------- | ------------------------------------------------- |
| `-C host` | Connect as hub client to specified server         |
| `-B #`    | Set bind port (for multiple clients on same host) |
| `-P #`    | Set peer port (server port, default: 4464)        |
| `-o #`    | Offset both bind and peer ports from default      |
| `-n #`    | Number of input/output channels                   |
| `-R`      | Use RtAudio instead of JACK                       |
| `-T #`    | Set sample rate                                   |
| `-F #`    | Set buffer size                                   |

### Multiple Clients on Same Host

When running multiple clients on one machine, use different bind ports:

```bash
# First client (default bind port 4464)
jacktrip -C 192.168.1.100 -B 4464 -P 4464

# Second client (different bind port)
jacktrip -C 192.168.1.100 -B 4465 -P 4464
```

Note: The peer port should remain at the server's port (default 4464).

## Audio Stream Access

### JACK Ports

When a client connects, JackTrip creates JACK ports for each channel:

**Client sending ports:**

- `jacktrip:send_1` through `jacktrip:send_N` (audio sent to server)

**Client receiving ports:**

- `jacktrip:receive_1` through `jacktrip:receive_N` (mixed audio from server)

Additionally, in hub server mode, these ports are created:

- `jacktrip:broadcast_1` through `jacktrip:broadcast_M` (broadcast outputs with extra latency but better packet loss handling)

### Viewing Available Ports

```bash
# List all JACK ports
jack_lsp

# List only JackTrip ports
jack_lsp | grep jacktrip
```

### Connecting Audio Applications

Use `jack_connect` or `qjackctl` to route audio:

```bash
# Connect microphone input to JackTrip send
jack_connect system:capture_1 jacktrip:send_1

# Connect JackTrip receive to headphones output
jack_connect jacktrip:receive_1 system:playback_1
```

### Recording Received Streams

The utility script `scripts/utility/record_jack_receiving_ports.sh` can record all incoming audio:

```bash
# Start JACK and JackTrip first, wait for connections
./scripts/utility/record_jack_receiving_ports.sh
# Press ESC to stop recording
```

## Authentication

To require authentication on the server:

```bash
# Server with authentication
jacktrip -S -A --certfile /path/to/cert.pem --keyfile /path/to/key.pem --credsfile /path/to/creds.txt
```

To connect as an authenticated client:

```bash
jacktrip -C server_ip --auth --username myuser --password mypass
```

## Monitoring Connections

### Check Connected Clients

On the server, use `jack_lsp` to see client ports appearing when clients connect:

```bash
jack_lsp | grep receive
jack_lsp | grep broadcast
```

### IO Statistics

Enable periodic IO statistics reporting:

```bash
# Server or client with 5-second interval
jacktrip -S -I 5
```

### Verbose Mode

For debugging connection issues:

```bash
jacktrip -S -V
jacktrip -C server_ip -V
```

## Troubleshooting

### Common Issues

1. **No audio passing through**

   - Check JACK is running: `jack_lsp` should show ports
   - Verify client connections with `jack_lsp`
   - Check firewall allows ports 4464 (TCP) and 61000-61100 (UDP)

1. **Connection timeouts**

   - Ensure server is reachable on port 4464
   - Check NAT/firewall settings if connecting across networks
   - Use `-t` flag to handle stale connections

1. **Buffer underruns**

   - Increase queue length: `-q 8` or `-q auto`
   - Try different buffer strategy: `--bufstrategy 2`
   - Check network latency/jitter

### Network Ports

| Port   | Protocol | Purpose                                         |
| ------ | -------- | ----------------------------------------------- |
| 4464   | TCP      | Hub server connection (can be offset with `-o`) |
| 61002+ | UDP      | Audio streaming (configurable with `-U`)        |

## Quick Reference

```bash
# Start hub server (full mix)
jacktrip -S -t -z --hubpatch 4

# Start hub server (client fan-out, no loopback)
jacktrip -S -t -z --hubpatch 2

# Client connect to server
jacktrip -C 192.168.1.100

# Multiple clients on same host
jacktrip -C 192.168.1.100 -B 4464 -P 4464 # Client 1
jacktrip -C 192.168.1.100 -B 4465 -P 4464 # Client 2

# Connect audio apps to JackTrip
jack_connect system:capture_1 jacktrip:send_1
jack_connect jacktrip:receive_1 system:playback_1
```

## WebRTC/WebSocket Connection Troubleshooting

### Symptoms

- WebSocket connection to `wss://[host]:4464/webrtc` fails with code 1006 (abnormal closure)
- Browser console shows: `WebSocket connection ... failed`
- Server logs show "Sending Final UDP Port to Client" instead of "WebRTC connection detected"
- **Log does NOT show "TLS ClientHello detected"** - indicates TLS handshake never started

### Root Cause Analysis

#### The Real Issue: TLS Handshake Never Starts

The browser connects to the WebSocket, but the TLS handshake never begins. Here's why:

1. **Browser expects TLS to be started by server** - A WebSocket client connecting to `wss://` expects the server to respond with TLS immediately
1. **No "TLS ClientHello detected" in logs** - The server detected incoming data but didn't see the TLS header `0x16 0x03 xx`
1. **Connection falls through to classic JackTrip path** - Without TLS, the server treats it as a binary client connection

#### Why TLS Isn't Starting

Looking at the code flow in `UdpHubListener.cpp`:

1. `receivedNewConnection()` is called - socket created
1. `readyRead()` is called when data arrives
1. **Line 334-346**: Check for TLS ClientHello via 3-byte peek
   - If data starts with `0x16 0x03 0x01-0x04`, call `startServerEncryption()`
1. **BUT**: The browser sends WebSocket handshake data, NOT a TLS ClientHello first

**The problem**: Browsers sending `wss://` initiate TLS at the socket level before sending HTTP GET. But in this environment, something is causing the TLS negotiation to fail silently.

#### Key Observations from Logs

```
JackTrip HUB SERVER: Client Connection Received!     # TCP connection made
JackTrip HUB SERVER: Client Connect Received from Address : ::1  # readyRead called
```

Missing:

- "TLS ClientHello detected" - TLS header NOT detected
- "WebRTC connection detected" - never reached the WebRTC path

#### Connection Flow (Broken)

```
Browser → TCP connect to 4464
         → readyRead called
         → Data doesn't start with TLS header
         → Treated as classic JackTrip client
         → Reads binary port, times out
```

### Required Server Configuration

The hub server requires TLS certificates for WebRTC WebSocket connections:

```bash
# Start server with TLS certificates (required for wss://)
jacktrip -S -cert /path/to/cert.pem -key /path/to/key.pem --hubpatch 4
```

### Certificate Requirements

- Certificate must match the hostname (e.g., `*.app.github.dev` for Codespaces)
- Full certificate chain must be in the PEM file (leaf + intermediates)
- Browser will reject self-signed certificates without user intervention

### Debugging Steps

1. **Verify TLS is configured**:

   ```bash
   # Check server logs for:
   # "Loaded TLS certificate"
   # "TLS ClientHello detected" (when browser initiates TLS handshake)
   # "WebRTC connection detected" (when /webrtc path is detected)
   ```

1. **Test HTTPS endpoint**:

   ```bash
   curl -k https://[codespace-name]-4464.app.github.dev/ping
   # Should return: {"status":"OK"}
   # If this fails, TLS/certificate is not working
   ```

1. **Verify port 4464 is forwarded in Codespaces**:

   - Check GitHub Codespaces port forwarding UI
   - Port 4464 must be forwarded for TCP/TLS traffic

1. **Check WebSocket path**:

   - URL must be exactly `/webrtc` (not `/webrtc/` or other variations)
   - Server checks: `requestPath == "/webrtc"` in UdpHubListener.cpp

1. **If "TLS ClientHello detected" is MISSING**:

   - Browser is NOT initiating TLS handshake
   - Check that the URL uses `wss://` (not `ws://`)
   - Browser Security tab may show certificate errors

1. **Use browser dev tools**:

   - Check Network tab for WebSocket connection attempt
   - Look for TLS/SSL errors in Security tab
   - Check Console for certificate error messages

### Connection Flow (Successful)

```
Browser → wss://host:4464/webrtc
        → TLS handshake (browser initiates)
        → Server logs "TLS ClientHello detected"
        → Server sends HTTP 101 Switching Protocols
        → Server logs "WebRTC connection detected"
        → SDP offer/answer exchange
        → ICE candidates exchanged
        → WebRTC data channel established
```

| Component         | File                                                                 |
| ----------------- | -------------------------------------------------------------------- |
| Hub Server TLS    | `jacktrip/src/UdpHubListener.cpp` lines 176-246                      |
| WebSocket Upgrade | `jacktrip/src/webrtc/WebSocketSignalingConnection.cpp` lines 147-212 |
| WebRTC Handler    | `jacktrip/src/webrtc/WebRtcPeerConnection.cpp`                       |
| Browser Client    | `services/webplayer/index.html`                                      |

### Summary: What's Happening

**Browser → WebSocket `wss://...` → TCP connects → BUT no TLS handshake occurs**

The server receives a TCP connection (logs show "Client Connection Received") but:

1. **No "TLS ClientHello detected"** in logs - browser data doesn't start with `0x16 0x03`
1. **No "WebRTC connection detected"** - the HTTP GET for `/webrtc` is never seen as starting with TLS
1. Server falls through to classic JackTrip authentication, reads binary port (17735), times out

**Key finding:** The connection is coming from `::1` (IPv6 localhost), NOT from the external browser!

- `JackTrip HUB SERVER: Client Connect Received from Address : ::1`

This means either:

1. **The browser connection never reached jacktrip-hub** - it went to nginx or another service
1. **The connection is being proxied incorrectly** - data is stripped of TLS before reaching jacktrip

### Most Likely Causes

1. **Codespaces port forwarding routes to wrong service** - port 4464 might be going to nginx instead of jacktrip
1. **nginx proxying TLS termination** - nginx handles TLS, forwards plain HTTP to jacktrip, but jacktrip expects TLS
1. **Certificate mismatch** - browser refuses TLS, falls back or silently fails

### Next Debug Steps

1. Check **Codespaces Ports tab** - which service is port 4464 forwarded to?
1. From browser, open DevTools → Network tab → try connection → check what server responds
1. Verify the WebSocket URL uses `wss://` and matches certificate hostname exactly

### Codespaces Specific Solution

**The fundamental issue: Codespaces terminates TLS at the edge**, so browser WebSocket connections arrive at the container as plain HTTP. JackTrip requires TLS at the socket level to detect browser WebSocket connections.

**Options to work around this limitation:**

1. **Use a VM instead of Codespaces** - deploy to an Azure VM, AWS EC2, or similar where you can do TCP passthrough with TLS termination at the application

1. **Use ngrok or similar tunneling service** with TLS passthrough:

   ```bash
   # Install ngrok
   ngrok tcp 4464
   # Then connect via: wss://<ngrok-id>.ngrok.io/webrtc
   ```

1. **Run the webplayer locally** and connect to the Codespaces jacktrip-hub via `localhost` using port forwarding. The webplayer already serves from `localhost:8080`, so you'd need to forward port 4464 from the host.

1. **Use `ws://` instead of `wss://`** - This would require modifications to JackTrip to accept non-TLS WebSocket connections. Current implementation requires TLS for WebRTC detection.
